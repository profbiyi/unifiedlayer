"""
Quality Check Pydantic Schemas.

Schemas for quality check API request/response models.
"""

from typing import Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, UUID4

from backend.models.quality import (
    QualityCheckType,
    QualityCheckSeverity,
    QualityCheckStatus,
)


# Quality Check Schemas
class QualityCheckCreate(BaseModel):
    """Schema for creating a quality check."""
    organization_id: int
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    check_type: QualityCheckType
    severity: QualityCheckSeverity = QualityCheckSeverity.HIGH
    config: Dict[str, Any]
    is_active: bool = True


class QualityCheckUpdate(BaseModel):
    """Schema for updating a quality check."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    severity: Optional[QualityCheckSeverity] = None
    config: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


class QualityCheckResponse(BaseModel):
    """Schema for quality check response."""
    id: int
    public_id: UUID4
    organization_id: int
    name: str
    description: Optional[str]
    check_type: QualityCheckType
    severity: QualityCheckSeverity
    config: Dict[str, Any]
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Pipeline Quality Check Schemas
class PipelineQualityCheckCreate(BaseModel):
    """Schema for adding a quality check to a pipeline."""
    quality_check_id: str  # UUID as string
    run_on_success: bool = True
    run_on_failure: bool = False
    override_severity: Optional[QualityCheckSeverity] = None
    is_active: bool = True


class PipelineQualityCheckResponse(BaseModel):
    """Schema for pipeline quality check response."""
    id: int
    pipeline_id: int
    quality_check_id: int
    run_on_success: bool
    run_on_failure: bool
    override_severity: Optional[QualityCheckSeverity]
    is_active: bool
    created_at: datetime

    # Nested quality check info
    quality_check: QualityCheckResponse

    class Config:
        from_attributes = True


# Quality Check Result Schemas
class QualityCheckResultResponse(BaseModel):
    """Schema for quality check result response."""
    id: int
    public_id: UUID4
    pipeline_run_id: int
    pipeline_check_id: int
    status: QualityCheckStatus
    severity: QualityCheckSeverity
    passed: bool
    actual_value: Optional[Dict[str, Any]]
    expected_value: Optional[Dict[str, Any]]
    message: Optional[str]
    details: Optional[Dict[str, Any]]
    execution_time_ms: Optional[float]
    rows_checked: Optional[int]
    executed_at: datetime

    # Computed properties
    check_name: str
    check_type: str

    class Config:
        from_attributes = True
