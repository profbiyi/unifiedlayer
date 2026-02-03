"""
Quality Check API Routes.

Provides endpoints for managing quality checks and viewing results.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
import uuid

from backend.database import get_db
from backend.models.quality import (
    QualityCheck,
    PipelineQualityCheck,
    QualityCheckResult,
    QualityCheckType,
    QualityCheckSeverity,
)
from backend.models.pipeline import Pipeline
from backend.api.schemas.quality import (
    QualityCheckCreate,
    QualityCheckUpdate,
    QualityCheckResponse,
    PipelineQualityCheckCreate,
    PipelineQualityCheckResponse,
    QualityCheckResultResponse,
)
from backend.api.deps import (
    get_current_user,
    check_permission,
    verify_org_access,
)
from backend.models import User

router = APIRouter(
    prefix="/api/v1/quality-checks",
    tags=["Quality Checks"],
)


@router.post("", response_model=QualityCheckResponse)
def create_quality_check(
    check: QualityCheckCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create a new quality check.

    Requires: quality_checks.create permission
    """
    check_permission(current_user, "quality_checks.create", db)
    verify_org_access(current_user, check.organization_id, db)

    # Validate config based on check type
    _validate_check_config(check.check_type, check.config)

    # Create quality check
    db_check = QualityCheck(
        public_id=uuid.uuid4(),
        organization_id=check.organization_id,
        name=check.name,
        description=check.description,
        check_type=check.check_type,
        severity=check.severity,
        config=check.config,
        is_active=check.is_active,
    )

    db.add(db_check)
    db.commit()
    db.refresh(db_check)

    return db_check


@router.get("", response_model=List[QualityCheckResponse])
def list_quality_checks(
    organization_id: int = Query(..., description="Organization ID"),
    check_type: Optional[QualityCheckType] = Query(None, description="Filter by check type"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List all quality checks for an organization.

    Requires: quality_checks.read permission
    """
    check_permission(current_user, "quality_checks.read", db)
    verify_org_access(current_user, organization_id, db)

    query = db.query(QualityCheck).filter(
        QualityCheck.organization_id == organization_id
    )

    if check_type is not None:
        query = query.filter(QualityCheck.check_type == check_type)

    if is_active is not None:
        query = query.filter(QualityCheck.is_active == is_active)

    checks = query.order_by(QualityCheck.created_at.desc()).all()

    return checks


@router.get("/{check_id}", response_model=QualityCheckResponse)
def get_quality_check(
    check_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get a specific quality check by ID.

    Requires: quality_checks.read permission
    """
    check_permission(current_user, "quality_checks.read", db)

    # Get check by public_id
    check = (
        db.query(QualityCheck)
        .filter(QualityCheck.public_id == uuid.UUID(check_id))
        .first()
    )

    if not check:
        raise HTTPException(status_code=404, detail="Quality check not found")

    verify_org_access(current_user, check.organization_id, db)

    return check


@router.put("/{check_id}", response_model=QualityCheckResponse)
def update_quality_check(
    check_id: str,
    update: QualityCheckUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Update a quality check.

    Requires: quality_checks.update permission
    """
    check_permission(current_user, "quality_checks.update", db)

    # Get check by public_id
    check = (
        db.query(QualityCheck)
        .filter(QualityCheck.public_id == uuid.UUID(check_id))
        .first()
    )

    if not check:
        raise HTTPException(status_code=404, detail="Quality check not found")

    verify_org_access(current_user, check.organization_id, db)

    # Update fields
    if update.name is not None:
        check.name = update.name
    if update.description is not None:
        check.description = update.description
    if update.severity is not None:
        check.severity = update.severity
    if update.config is not None:
        _validate_check_config(check.check_type, update.config)
        check.config = update.config
    if update.is_active is not None:
        check.is_active = update.is_active

    db.commit()
    db.refresh(check)

    return check


@router.delete("/{check_id}")
def delete_quality_check(
    check_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Delete a quality check.

    Requires: quality_checks.delete permission
    """
    check_permission(current_user, "quality_checks.delete", db)

    # Get check by public_id
    check = (
        db.query(QualityCheck)
        .filter(QualityCheck.public_id == uuid.UUID(check_id))
        .first()
    )

    if not check:
        raise HTTPException(status_code=404, detail="Quality check not found")

    verify_org_access(current_user, check.organization_id, db)

    db.delete(check)
    db.commit()

    return {"message": "Quality check deleted successfully"}


@router.get("/pipelines/{pipeline_id}/checks", response_model=List[PipelineQualityCheckResponse])
def list_pipeline_quality_checks(
    pipeline_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List quality checks configured for a pipeline.

    Requires: pipelines.read permission
    """
    check_permission(current_user, "pipelines.read", db)

    # Get pipeline by public_id
    pipeline = (
        db.query(Pipeline)
        .filter(Pipeline.public_id == uuid.UUID(pipeline_id))
        .first()
    )

    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found")

    verify_org_access(current_user, pipeline.organization_id, db)

    # Get all quality checks for this pipeline
    pipeline_checks = (
        db.query(PipelineQualityCheck)
        .filter(PipelineQualityCheck.pipeline_id == pipeline.id)
        .all()
    )

    return pipeline_checks


@router.post("/pipelines/{pipeline_id}/checks", response_model=PipelineQualityCheckResponse)
def add_quality_check_to_pipeline(
    pipeline_id: str,
    check: PipelineQualityCheckCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Add a quality check to a pipeline.

    Requires: pipelines.update permission
    """
    check_permission(current_user, "pipelines.update", db)

    # Get pipeline by public_id
    pipeline = (
        db.query(Pipeline)
        .filter(Pipeline.public_id == uuid.UUID(pipeline_id))
        .first()
    )

    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found")

    verify_org_access(current_user, pipeline.organization_id, db)

    # Get quality check by public_id
    quality_check = (
        db.query(QualityCheck)
        .filter(QualityCheck.public_id == uuid.UUID(check.quality_check_id))
        .first()
    )

    if not quality_check:
        raise HTTPException(status_code=404, detail="Quality check not found")

    # Verify quality check belongs to same organization
    if quality_check.organization_id != pipeline.organization_id:
        raise HTTPException(
            status_code=403,
            detail="Quality check and pipeline must belong to the same organization"
        )

    # Check if already exists
    existing = (
        db.query(PipelineQualityCheck)
        .filter(
            PipelineQualityCheck.pipeline_id == pipeline.id,
            PipelineQualityCheck.quality_check_id == quality_check.id,
        )
        .first()
    )

    if existing:
        raise HTTPException(
            status_code=409,
            detail="Quality check already added to this pipeline"
        )

    # Create pipeline quality check
    pipeline_check = PipelineQualityCheck(
        pipeline_id=pipeline.id,
        quality_check_id=quality_check.id,
        run_on_success=check.run_on_success,
        run_on_failure=check.run_on_failure,
        override_severity=check.override_severity,
        is_active=check.is_active,
    )

    db.add(pipeline_check)
    db.commit()
    db.refresh(pipeline_check)

    return pipeline_check


@router.delete("/pipelines/{pipeline_id}/checks/{check_id}")
def remove_quality_check_from_pipeline(
    pipeline_id: str,
    check_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Remove a quality check from a pipeline.

    Requires: pipelines.update permission
    """
    check_permission(current_user, "pipelines.update", db)

    # Get pipeline by public_id
    pipeline = (
        db.query(Pipeline)
        .filter(Pipeline.public_id == uuid.UUID(pipeline_id))
        .first()
    )

    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found")

    verify_org_access(current_user, pipeline.organization_id, db)

    # Get quality check by public_id
    quality_check = (
        db.query(QualityCheck)
        .filter(QualityCheck.public_id == uuid.UUID(check_id))
        .first()
    )

    if not quality_check:
        raise HTTPException(status_code=404, detail="Quality check not found")

    # Find and delete the pipeline quality check
    pipeline_check = (
        db.query(PipelineQualityCheck)
        .filter(
            PipelineQualityCheck.pipeline_id == pipeline.id,
            PipelineQualityCheck.quality_check_id == quality_check.id,
        )
        .first()
    )

    if not pipeline_check:
        raise HTTPException(
            status_code=404,
            detail="Quality check not found for this pipeline"
        )

    db.delete(pipeline_check)
    db.commit()

    return {"message": "Quality check removed from pipeline"}


@router.get("/pipelines/{pipeline_id}/runs/{run_id}/results", response_model=List[QualityCheckResultResponse])
def get_quality_check_results(
    pipeline_id: str,
    run_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get quality check results for a pipeline run.

    Requires: pipelines.read permission
    """
    check_permission(current_user, "pipelines.read", db)

    # Get pipeline by public_id
    pipeline = (
        db.query(Pipeline)
        .filter(Pipeline.public_id == uuid.UUID(pipeline_id))
        .first()
    )

    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found")

    verify_org_access(current_user, pipeline.organization_id, db)

    # Get pipeline run
    from backend.models import PipelineRun
    run = (
        db.query(PipelineRun)
        .filter(
            PipelineRun.public_id == uuid.UUID(run_id),
            PipelineRun.pipeline_id == pipeline.id,
        )
        .first()
    )

    if not run:
        raise HTTPException(status_code=404, detail="Pipeline run not found")

    # Get quality check results
    results = (
        db.query(QualityCheckResult)
        .filter(QualityCheckResult.pipeline_run_id == run.id)
        .order_by(QualityCheckResult.executed_at.desc())
        .all()
    )

    return results


def _validate_check_config(check_type: QualityCheckType, config: dict):
    """Validate quality check configuration based on type."""
    if check_type == QualityCheckType.ROW_COUNT:
        if "min_rows" not in config and "max_rows" not in config:
            raise HTTPException(
                status_code=400,
                detail="ROW_COUNT check requires 'min_rows' or 'max_rows' in config"
            )

    elif check_type == QualityCheckType.NULL_CHECK:
        if "columns" not in config:
            raise HTTPException(
                status_code=400,
                detail="NULL_CHECK requires 'columns' in config"
            )
        if not isinstance(config["columns"], list):
            raise HTTPException(
                status_code=400,
                detail="NULL_CHECK 'columns' must be a list"
            )

    elif check_type == QualityCheckType.UNIQUENESS:
        if "column" not in config:
            raise HTTPException(
                status_code=400,
                detail="UNIQUENESS check requires 'column' in config"
            )

    elif check_type == QualityCheckType.VALUE_RANGE:
        if "column" not in config:
            raise HTTPException(
                status_code=400,
                detail="VALUE_RANGE check requires 'column' in config"
            )
        if "min" not in config and "max" not in config:
            raise HTTPException(
                status_code=400,
                detail="VALUE_RANGE check requires 'min' or 'max' in config"
            )

    elif check_type == QualityCheckType.PATTERN_MATCH:
        if "column" not in config or "pattern" not in config:
            raise HTTPException(
                status_code=400,
                detail="PATTERN_MATCH check requires 'column' and 'pattern' in config"
            )

    elif check_type == QualityCheckType.FRESHNESS:
        if "timestamp_column" not in config or "max_age_hours" not in config:
            raise HTTPException(
                status_code=400,
                detail="FRESHNESS check requires 'timestamp_column' and 'max_age_hours' in config"
            )

    elif check_type == QualityCheckType.CUSTOM_SQL:
        if "query" not in config:
            raise HTTPException(
                status_code=400,
                detail="CUSTOM_SQL check requires 'query' in config"
            )
