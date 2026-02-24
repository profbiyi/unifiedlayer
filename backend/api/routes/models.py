"""
Generated Models API routes.

Provides endpoints for AI-generated dimensional models management.
"""
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from uuid import UUID
import logging

from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel, Field, computed_field

from backend.database import get_db
from backend.models.pipeline import User, Pipeline
from backend.models.data_model import GeneratedModel, ModelGeneration, ModelLayer, ModelStatus
from backend.auth import get_current_user
from backend.rbac.permissions import require_permission
from backend.services.ai_modeler import get_ai_modeler

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/models", tags=["AI Models"])


# ==================== PYDANTIC SCHEMAS ====================


class ColumnSchema(BaseModel):
    """Column definition schema."""
    name: str
    type: str
    description: Optional[str] = None
    source_column: Optional[str] = None


class RelationshipSchema(BaseModel):
    """Relationship definition schema."""
    from_col: Optional[str] = None
    to_table: str
    to_col: str
    fact: Optional[str] = None
    dimension: Optional[str] = None
    join_key: Optional[str] = None


class GeneratedModelResponse(BaseModel):
    """Generated model response schema."""
    public_id: UUID
    name: str
    description: Optional[str]
    layer: ModelLayer
    model_type: str
    source_tables: List[str]
    columns: List[ColumnSchema]
    relationships: List[Dict[str, Any]]
    business_questions: List[str]
    status: ModelStatus
    is_materialized: bool
    materialized_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    @computed_field
    @property
    def id(self) -> str:
        """Return public_id as string for id field."""
        return str(self.public_id)

    class Config:
        from_attributes = True


class GeneratedModelDetailResponse(GeneratedModelResponse):
    """Detailed model response with SQL."""
    sql_definition: str
    ai_reasoning: Optional[str]
    pipeline_id: int
    pipeline_name: Optional[str] = None


class ModelUpdateRequest(BaseModel):
    """Model update request schema."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    sql_definition: Optional[str] = None
    status: Optional[ModelStatus] = None


class GenerateModelsRequest(BaseModel):
    """Request to generate models for a pipeline."""
    tables: Optional[List[str]] = None  # Specific tables to analyze
    schema_name: Optional[str] = None  # Schema/dataset name


class GenerateModelsResponse(BaseModel):
    """Response from model generation."""
    generation_id: str
    status: str
    message: str
    models_count: Optional[int] = None
    questions_count: Optional[int] = None


class ModelGenerationResponse(BaseModel):
    """Model generation run response."""
    public_id: UUID
    pipeline_id: int
    status: str
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    models_generated: Optional[int]
    questions_generated: Optional[int]
    error_message: Optional[str]
    created_at: datetime

    @computed_field
    @property
    def id(self) -> str:
        """Return public_id as string for id field."""
        return str(self.public_id)

    class Config:
        from_attributes = True


class MaterializeResponse(BaseModel):
    """Response from materializing a model."""
    success: bool
    message: str
    view_name: Optional[str] = None
    error: Optional[str] = None


class BusinessQuestionsResponse(BaseModel):
    """Response with generated business questions."""
    questions: List[str]
    model_count: int
    fact_tables: List[str]
    dimension_tables: List[str]


# ==================== HELPER FUNCTIONS ====================


def get_model_or_404(
    model_id: str,
    db: Session,
    organization_id: int
) -> GeneratedModel:
    """Get generated model by public_id or raise 404."""
    try:
        model_uuid = UUID(model_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid model ID format",
        )

    model = db.query(GeneratedModel).filter(
        GeneratedModel.public_id == model_uuid,
        GeneratedModel.organization_id == organization_id,
    ).first()

    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model not found",
        )

    return model


def get_pipeline_or_404(
    pipeline_id: str,
    db: Session,
    organization_id: int
) -> Pipeline:
    """Get pipeline by public_id or raise 404."""
    try:
        pipeline_uuid = UUID(pipeline_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid pipeline ID format",
        )

    pipeline = db.query(Pipeline).filter(
        Pipeline.public_id == pipeline_uuid,
        Pipeline.organization_id == organization_id,
    ).first()

    if not pipeline:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pipeline not found",
        )

    return pipeline


# ==================== BACKGROUND TASKS ====================


def run_model_generation(
    generation_id: int,
    pipeline_id: int,
    organization_id: int,
    tables: Optional[List[str]],
    schema_name: Optional[str],
):
    """Background task to run model generation."""
    from backend.database import get_db_session

    db = get_db_session()
    try:
        # Update generation status to running
        generation = db.query(ModelGeneration).filter(
            ModelGeneration.id == generation_id
        ).first()

        if not generation:
            logger.error(f"Model generation {generation_id} not found")
            return

        generation.status = "running"
        generation.started_at = datetime.now(timezone.utc)
        db.commit()

        # Get pipeline and destination
        pipeline = db.query(Pipeline).filter(Pipeline.id == pipeline_id).first()
        if not pipeline or not pipeline.destination:
            generation.status = "failed"
            generation.error_message = "Pipeline or destination not found"
            generation.completed_at = datetime.now(timezone.utc)
            db.commit()
            return

        # Run AI modeling
        ai_modeler = get_ai_modeler()

        # Analyze schema
        destination = pipeline.destination
        schema_context = ai_modeler.analyze_schema(
            destination_config=destination.config,
            destination_type=destination.destination_type.value,
            tables=tables,
            schema_name=schema_name or destination.config.get("dataset_name"),
        )

        generation.schema_tables_analyzed = schema_context.total_tables
        generation.schema_columns_analyzed = schema_context.total_columns
        db.commit()

        if not schema_context.tables:
            generation.status = "failed"
            generation.error_message = "No tables found to analyze"
            generation.completed_at = datetime.now(timezone.utc)
            db.commit()
            return

        # Generate business questions
        business_questions = ai_modeler.generate_business_questions(schema_context)

        # Generate canonical models
        canonical_models = ai_modeler.generate_canonical_models(schema_context)

        # Generate dimensional models
        dimensional_models = ai_modeler.generate_dimensional_models(
            schema_context,
            canonical_models,
            business_questions,
        )

        # Save models
        all_models = canonical_models + dimensional_models
        for model in all_models:
            ai_modeler._save_model(
                db=db,
                organization_id=organization_id,
                pipeline_id=pipeline_id,
                model=model,
                business_questions=business_questions,
            )

        # Update generation status
        generation.status = "completed"
        generation.completed_at = datetime.now(timezone.utc)
        generation.models_generated = len(all_models)
        generation.questions_generated = len(business_questions)
        db.commit()

        logger.info(
            f"Model generation {generation_id} completed: "
            f"{len(all_models)} models, {len(business_questions)} questions"
        )

    except Exception as e:
        logger.error(f"Model generation {generation_id} failed: {e}", exc_info=True)
        if db:
            generation = db.query(ModelGeneration).filter(
                ModelGeneration.id == generation_id
            ).first()
            if generation:
                generation.status = "failed"
                generation.error_message = str(e)[:1000]
                generation.completed_at = datetime.now(timezone.utc)
                db.commit()
    finally:
        if db:
            db.close()


# ==================== ENDPOINTS ====================


@router.post("/generate/{pipeline_id}", response_model=GenerateModelsResponse, status_code=status.HTTP_202_ACCEPTED)
@require_permission("pipeline", "update")
async def generate_models(
    pipeline_id: str,
    request: GenerateModelsRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Trigger AI model generation for a pipeline.

    **Requires:** pipeline.update permission

    This endpoint starts an asynchronous model generation process that:
    1. Analyzes the destination schema
    2. Generates business questions
    3. Creates canonical models (cleaned, normalized)
    4. Creates dimensional models (fact and dimension tables)

    The generation runs in the background. Use GET /models/generations/{id}
    to check the status.
    """
    pipeline = get_pipeline_or_404(pipeline_id, db, current_user.organization_id)

    if not pipeline.destination:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Pipeline has no destination configured",
        )

    # Check if there's already a running generation
    running = db.query(ModelGeneration).filter(
        ModelGeneration.pipeline_id == pipeline.id,
        ModelGeneration.status.in_(["pending", "running"]),
    ).first()

    if running:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Model generation already in progress for this pipeline",
        )

    # Create generation record
    generation = ModelGeneration(
        organization_id=current_user.organization_id,
        pipeline_id=pipeline.id,
        status="pending",
    )
    db.add(generation)
    db.commit()
    db.refresh(generation)

    # Start background task
    background_tasks.add_task(
        run_model_generation,
        generation_id=generation.id,
        pipeline_id=pipeline.id,
        organization_id=current_user.organization_id,
        tables=request.tables,
        schema_name=request.schema_name,
    )

    logger.info(f"Model generation {generation.id} started for pipeline {pipeline.id}")

    return GenerateModelsResponse(
        generation_id=str(generation.public_id),
        status="pending",
        message="Model generation started. Use GET /models/generations/{id} to check status.",
    )


@router.get("/generations", response_model=List[ModelGenerationResponse])
@require_permission("pipeline", "read")
async def list_generations(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    pipeline_id: Optional[str] = Query(None, description="Filter by pipeline"),
    status_filter: Optional[str] = Query(None, alias="status"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    List model generation runs.

    **Requires:** pipeline.read permission
    """
    query = db.query(ModelGeneration).filter(
        ModelGeneration.organization_id == current_user.organization_id
    )

    if pipeline_id:
        pipeline = get_pipeline_or_404(pipeline_id, db, current_user.organization_id)
        query = query.filter(ModelGeneration.pipeline_id == pipeline.id)

    if status_filter:
        query = query.filter(ModelGeneration.status == status_filter)

    generations = query.order_by(ModelGeneration.created_at.desc()).offset(skip).limit(limit).all()
    return generations


@router.get("/generations/{generation_id}", response_model=ModelGenerationResponse)
@require_permission("pipeline", "read")
async def get_generation(
    generation_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get model generation details.

    **Requires:** pipeline.read permission
    """
    try:
        gen_uuid = UUID(generation_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid generation ID format",
        )

    generation = db.query(ModelGeneration).filter(
        ModelGeneration.public_id == gen_uuid,
        ModelGeneration.organization_id == current_user.organization_id,
    ).first()

    if not generation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Generation not found",
        )

    return generation


@router.get("", response_model=List[GeneratedModelResponse])
@require_permission("pipeline", "read")
async def list_models(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    pipeline_id: Optional[str] = Query(None, description="Filter by pipeline"),
    layer: Optional[ModelLayer] = Query(None, description="Filter by layer"),
    model_type: Optional[str] = Query(None, description="Filter by type (fact, dimension, canonical)"),
    status_filter: Optional[ModelStatus] = Query(None, alias="status"),
    is_materialized: Optional[bool] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    List all generated models for the organization.

    **Requires:** pipeline.read permission
    """
    query = db.query(GeneratedModel).filter(
        GeneratedModel.organization_id == current_user.organization_id
    )

    if pipeline_id:
        pipeline = get_pipeline_or_404(pipeline_id, db, current_user.organization_id)
        query = query.filter(GeneratedModel.pipeline_id == pipeline.id)

    if layer:
        query = query.filter(GeneratedModel.layer == layer)

    if model_type:
        query = query.filter(GeneratedModel.model_type == model_type)

    if status_filter:
        query = query.filter(GeneratedModel.status == status_filter)

    if is_materialized is not None:
        query = query.filter(GeneratedModel.is_materialized == is_materialized)

    models = query.order_by(GeneratedModel.created_at.desc()).offset(skip).limit(limit).all()
    return models


@router.get("/{model_id}", response_model=GeneratedModelDetailResponse)
@require_permission("pipeline", "read")
async def get_model(
    model_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get model details including SQL definition.

    **Requires:** pipeline.read permission
    """
    model = get_model_or_404(model_id, db, current_user.organization_id)

    # Add pipeline name
    pipeline = db.query(Pipeline).filter(Pipeline.id == model.pipeline_id).first()

    response = GeneratedModelDetailResponse(
        public_id=model.public_id,
        name=model.name,
        description=model.description,
        layer=model.layer,
        model_type=model.model_type,
        source_tables=model.source_tables or [],
        columns=model.columns or [],
        relationships=model.relationships or [],
        business_questions=model.business_questions or [],
        status=model.status,
        is_materialized=model.is_materialized,
        materialized_at=model.materialized_at,
        created_at=model.created_at,
        updated_at=model.updated_at,
        sql_definition=model.sql_definition,
        ai_reasoning=model.ai_reasoning,
        pipeline_id=model.pipeline_id,
        pipeline_name=pipeline.name if pipeline else None,
    )

    return response


@router.put("/{model_id}", response_model=GeneratedModelDetailResponse)
@require_permission("pipeline", "update")
async def update_model(
    model_id: str,
    update_data: ModelUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Update a generated model.

    **Requires:** pipeline.update permission

    Use this to edit the SQL definition, description, or status.
    """
    model = get_model_or_404(model_id, db, current_user.organization_id)

    if update_data.name is not None:
        model.name = update_data.name

    if update_data.description is not None:
        model.description = update_data.description

    if update_data.sql_definition is not None:
        model.sql_definition = update_data.sql_definition
        # Reset materialized state if SQL changed
        if model.is_materialized:
            model.is_materialized = False
            model.materialized_at = None

    if update_data.status is not None:
        model.status = update_data.status

    db.commit()
    db.refresh(model)

    logger.info(f"Model {model.id} updated by user {current_user.id}")

    # Add pipeline name for response
    pipeline = db.query(Pipeline).filter(Pipeline.id == model.pipeline_id).first()

    return GeneratedModelDetailResponse(
        public_id=model.public_id,
        name=model.name,
        description=model.description,
        layer=model.layer,
        model_type=model.model_type,
        source_tables=model.source_tables or [],
        columns=model.columns or [],
        relationships=model.relationships or [],
        business_questions=model.business_questions or [],
        status=model.status,
        is_materialized=model.is_materialized,
        materialized_at=model.materialized_at,
        created_at=model.created_at,
        updated_at=model.updated_at,
        sql_definition=model.sql_definition,
        ai_reasoning=model.ai_reasoning,
        pipeline_id=model.pipeline_id,
        pipeline_name=pipeline.name if pipeline else None,
    )


@router.post("/{model_id}/materialize", response_model=MaterializeResponse)
@require_permission("pipeline", "update")
async def materialize_model(
    model_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Create the actual view in the destination database.

    **Requires:** pipeline.update permission

    This executes the model's SQL definition against the destination
    to create a real database view.
    """
    model = get_model_or_404(model_id, db, current_user.organization_id)

    if model.is_materialized:
        return MaterializeResponse(
            success=True,
            message="Model is already materialized",
            view_name=model.name,
        )

    if not model.sql_definition:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Model has no SQL definition",
        )

    # Get destination config
    pipeline = db.query(Pipeline).filter(Pipeline.id == model.pipeline_id).first()
    if not pipeline or not pipeline.destination:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Pipeline destination not found",
        )

    destination = pipeline.destination

    try:
        # Connect to destination and execute SQL
        from backend.services.schema_analyzer import get_schema_analyzer

        analyzer = get_schema_analyzer()
        analyzer.connect(destination.config, destination.destination_type.value)

        with analyzer.engine.connect() as conn:
            # Execute the CREATE VIEW statement
            conn.execute(text(model.sql_definition))
            conn.commit()

        analyzer.close()

        # Update model status
        model.is_materialized = True
        model.materialized_at = datetime.now(timezone.utc)
        model.materialized_by_id = current_user.id
        model.status = ModelStatus.DEPLOYED
        db.commit()

        logger.info(f"Model {model.name} materialized by user {current_user.id}")

        return MaterializeResponse(
            success=True,
            message=f"View '{model.name}' created successfully",
            view_name=model.name,
        )

    except Exception as e:
        logger.error(f"Failed to materialize model {model.id}: {e}")
        return MaterializeResponse(
            success=False,
            message="Failed to create view",
            error=str(e)[:500],
        )


@router.delete("/{model_id}", status_code=status.HTTP_204_NO_CONTENT)
@require_permission("pipeline", "delete")
async def delete_model(
    model_id: str,
    drop_view: bool = Query(False, description="Also drop the view from destination"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Delete a generated model.

    **Requires:** pipeline.delete permission

    Set drop_view=true to also drop the view from the destination database.
    """
    model = get_model_or_404(model_id, db, current_user.organization_id)

    if drop_view and model.is_materialized:
        # Get destination and drop view
        pipeline = db.query(Pipeline).filter(Pipeline.id == model.pipeline_id).first()
        if pipeline and pipeline.destination:
            try:
                from backend.services.schema_analyzer import get_schema_analyzer

                analyzer = get_schema_analyzer()
                analyzer.connect(
                    pipeline.destination.config,
                    pipeline.destination.destination_type.value
                )

                with analyzer.engine.connect() as conn:
                    conn.execute(text(f"DROP VIEW IF EXISTS {model.name}"))
                    conn.commit()

                analyzer.close()
                logger.info(f"View {model.name} dropped from destination")

            except Exception as e:
                logger.warning(f"Failed to drop view {model.name}: {e}")

    db.delete(model)
    db.commit()

    logger.info(f"Model {model_id} deleted by user {current_user.id}")
    return None


@router.get("/pipeline/{pipeline_id}/questions", response_model=BusinessQuestionsResponse)
@require_permission("pipeline", "read")
async def get_pipeline_questions(
    pipeline_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get all business questions for models in a pipeline.

    **Requires:** pipeline.read permission
    """
    pipeline = get_pipeline_or_404(pipeline_id, db, current_user.organization_id)

    models = db.query(GeneratedModel).filter(
        GeneratedModel.pipeline_id == pipeline.id
    ).all()

    # Collect unique questions
    all_questions = set()
    fact_tables = []
    dimension_tables = []

    for model in models:
        for q in model.business_questions or []:
            all_questions.add(q)

        if model.model_type == "fact":
            fact_tables.append(model.name)
        elif model.model_type == "dimension":
            dimension_tables.append(model.name)

    return BusinessQuestionsResponse(
        questions=list(all_questions),
        model_count=len(models),
        fact_tables=fact_tables,
        dimension_tables=dimension_tables,
    )
