"""
Cross-Source Modeling API routes.

Provides endpoints for analyzing data across multiple sources,
detecting relationships, and generating unified models.
"""
import logging
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.auth import get_current_user
from backend.models.pipeline import User
from backend.services.cross_source_modeler import (
    get_cross_source_modeler,
    EnrichmentConfig,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/cross-source", tags=["Cross-Source Modeling"])


# ============================================================
# Schemas
# ============================================================

class AnalyzeSourcesRequest(BaseModel):
    """Request to analyze multiple sources."""
    source_ids: Optional[List[int]] = Field(
        None,
        description="Specific source IDs to analyze (None = all org sources)"
    )


class SuggestedJoinResponse(BaseModel):
    """A suggested join between sources."""
    id: str
    left_source: str
    left_table: str
    left_column: str
    right_source: str
    right_table: str
    right_column: str
    confidence: float
    reasoning: str
    join_type: str
    sample_matches: List[List[str]]


class CrossSourceAnalysisResponse(BaseModel):
    """Result of cross-source analysis."""
    sources_analyzed: int
    tables_found: int
    suggested_joins: List[SuggestedJoinResponse]


class ConfirmJoinsRequest(BaseModel):
    """Request to confirm joins and generate unified models."""
    confirmed_join_ids: List[str] = Field(
        ...,
        description="IDs of suggested joins to use"
    )
    custom_joins: Optional[List[dict]] = Field(
        default=[],
        description="Additional user-defined joins"
    )
    primary_source: str = Field(
        ...,
        description="Name of the primary source (base for fact tables)"
    )


class UnifiedModelResponse(BaseModel):
    """Response with generated unified models."""
    models_created: int
    model_ids: List[str]
    message: str


class AutoModelSettingsRequest(BaseModel):
    """Request to update auto-modeling settings."""
    enabled: bool = Field(..., description="Enable or disable auto-modeling")
    cross_source_enabled: bool = Field(
        default=False,
        description="Enable cross-source modeling (analyzes all sources together)"
    )


class AutoModelSettingsResponse(BaseModel):
    """Current auto-modeling settings."""
    auto_model_enabled: bool
    cross_source_enabled: bool
    last_model_generation: Optional[str]
    models_generated: int


# ============================================================
# Endpoints
# ============================================================

@router.post("/analyze", response_model=CrossSourceAnalysisResponse)
async def analyze_sources(
    request: AnalyzeSourcesRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Analyze multiple sources to detect cross-source relationships.

    Returns suggested joins based on:
    - Column name patterns (email, customer_id, etc.)
    - Data type compatibility
    - Sample value overlap
    - AI-enhanced relationship detection
    """
    modeler = get_cross_source_modeler()

    try:
        cross_schema = modeler.get_org_sources_schemas(
            db=db,
            org_id=current_user.organization_id,
            source_ids=request.source_ids,
        )

        # Enhance with AI if available
        enhanced_joins = modeler.enhance_joins_with_ai(cross_schema)

        return CrossSourceAnalysisResponse(
            sources_analyzed=len(cross_schema.sources),
            tables_found=len(cross_schema.all_tables),
            suggested_joins=[
                SuggestedJoinResponse(
                    id=j.id,
                    left_source=j.left_source,
                    left_table=j.left_table,
                    left_column=j.left_column,
                    right_source=j.right_source,
                    right_table=j.right_table,
                    right_column=j.right_column,
                    confidence=j.confidence,
                    reasoning=j.reasoning,
                    join_type=j.join_type,
                    sample_matches=[list(m) for m in j.sample_matches],
                )
                for j in enhanced_joins
            ],
        )

    except Exception as e:
        logger.error(f"Cross-source analysis failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Analysis failed: {str(e)}",
        )


@router.post("/generate", response_model=UnifiedModelResponse)
async def generate_unified_models(
    request: ConfirmJoinsRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Generate unified dimensional models using confirmed joins.

    User must first call /analyze to get suggested joins,
    then confirm which joins to use for model generation.
    """
    modeler = get_cross_source_modeler()

    try:
        # Re-analyze to get fresh schema
        cross_schema = modeler.get_org_sources_schemas(
            db=db,
            org_id=current_user.organization_id,
        )

        if not cross_schema.sources:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No sources found to model",
            )

        # Find confirmed joins
        confirmed_joins = [
            j for j in cross_schema.suggested_joins
            if j.id in request.confirmed_join_ids
        ]

        # Build enrichment config
        enrichment_sources = [
            name for name in cross_schema.sources.keys()
            if name != request.primary_source
        ]

        config = EnrichmentConfig(
            confirmed_joins=confirmed_joins,
            custom_joins=request.custom_joins or [],
            primary_source=request.primary_source,
            enrichment_sources=enrichment_sources,
        )

        # Generate unified models
        models = modeler.generate_unified_models(
            db=db,
            org_id=current_user.organization_id,
            cross_schema=cross_schema,
            enrichment_config=config,
        )

        return UnifiedModelResponse(
            models_created=len(models),
            model_ids=[str(m.public_id) for m in models],
            message=f"Created {len(models)} unified models combining data from {len(cross_schema.sources)} sources",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unified model generation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Model generation failed: {str(e)}",
        )


@router.get("/settings", response_model=AutoModelSettingsResponse)
async def get_auto_model_settings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get current auto-modeling settings for the organization.
    """
    from backend.models.pipeline import Organization

    org = db.query(Organization).filter(
        Organization.id == current_user.organization_id
    ).first()

    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )

    # Get settings from org config (or defaults)
    org_config = org.config or {}
    auto_model_settings = org_config.get("auto_model", {})

    # Count models generated
    from backend.models.data_model import GeneratedModel
    models_count = db.query(GeneratedModel).filter(
        GeneratedModel.organization_id == org.id
    ).count()

    return AutoModelSettingsResponse(
        auto_model_enabled=auto_model_settings.get("enabled", False),
        cross_source_enabled=auto_model_settings.get("cross_source", False),
        last_model_generation=auto_model_settings.get("last_generation"),
        models_generated=models_count,
    )


@router.put("/settings", response_model=AutoModelSettingsResponse)
async def update_auto_model_settings(
    request: AutoModelSettingsRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Update auto-modeling settings for the organization.

    When enabled:
    - Single-source: AI generates models after each pipeline sync
    - Cross-source: AI analyzes all sources together for unified models
    """
    from backend.models.pipeline import Organization

    org = db.query(Organization).filter(
        Organization.id == current_user.organization_id
    ).first()

    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )

    # Update org config
    org_config = org.config or {}
    org_config["auto_model"] = {
        "enabled": request.enabled,
        "cross_source": request.cross_source_enabled,
        "updated_at": str(datetime.now(timezone.utc)),
        "updated_by": current_user.id,
    }

    # Preserve existing last_generation if present
    if org.config and "auto_model" in org.config:
        org_config["auto_model"]["last_generation"] = org.config["auto_model"].get("last_generation")

    org.config = org_config
    db.commit()

    logger.info(
        f"Auto-model settings updated for org {org.id}: "
        f"enabled={request.enabled}, cross_source={request.cross_source_enabled}"
    )

    # Count models
    from backend.models.data_model import GeneratedModel
    models_count = db.query(GeneratedModel).filter(
        GeneratedModel.organization_id == org.id
    ).count()

    return AutoModelSettingsResponse(
        auto_model_enabled=request.enabled,
        cross_source_enabled=request.cross_source_enabled,
        last_model_generation=org_config["auto_model"].get("last_generation"),
        models_generated=models_count,
    )


@router.get("/sources")
async def list_available_sources(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    List all sources available for cross-source modeling.
    """
    from backend.models.pipeline import Pipeline

    pipelines = db.query(Pipeline).filter(
        Pipeline.organization_id == current_user.organization_id,
        Pipeline.is_active,
    ).all()

    sources = {}
    for p in pipelines:
        if p.source and p.source_id not in sources:
            sources[p.source_id] = {
                "id": p.source_id,
                "name": p.source.name,
                "type": p.source.source_type.value if p.source.source_type else "unknown",
                "has_synced_data": True,  # Has at least one pipeline
            }

    return {
        "sources": list(sources.values()),
        "total": len(sources),
    }
