"""
Data Quality Models.

Defines database models for quality checks, rules, and results.
"""

from datetime import datetime, timezone
from typing import Optional, Dict, Any
import uuid
import enum

from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    Boolean,
    Text,
    ForeignKey,
    JSON,
    Enum as SQLEnum,
    Float,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from backend.database import Base


class QualityCheckType(str, enum.Enum):
    """Quality check type enumeration."""
    ROW_COUNT = "row_count"              # Check row count against threshold
    NULL_CHECK = "null_check"            # Check for null values in columns
    UNIQUENESS = "uniqueness"            # Check column uniqueness
    VALUE_RANGE = "value_range"          # Check values are within range
    PATTERN_MATCH = "pattern_match"      # Check values match regex pattern
    FRESHNESS = "freshness"              # Check data freshness (timestamp)
    CUSTOM_SQL = "custom_sql"            # Custom SQL query check


class QualityCheckStatus(str, enum.Enum):
    """Quality check result status."""
    PASSED = "passed"
    FAILED = "failed"
    WARNING = "warning"
    SKIPPED = "skipped"
    ERROR = "error"


class QualityCheckSeverity(str, enum.Enum):
    """Quality check severity level."""
    CRITICAL = "critical"  # Pipeline fails if check fails
    HIGH = "high"          # Warning, doesn't fail pipeline
    MEDIUM = "medium"      # Informational warning
    LOW = "low"            # Informational only


class QualityCheck(Base):
    """
    Quality Check configuration.

    Defines a reusable quality check that can be applied to pipelines.
    """
    __tablename__ = "quality_checks"

    id = Column(Integer, primary_key=True, index=True)
    public_id = Column(UUID(as_uuid=True), unique=True, nullable=False, default=uuid.uuid4, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)

    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    check_type = Column(SQLEnum(QualityCheckType), nullable=False)
    severity = Column(SQLEnum(QualityCheckSeverity), nullable=False, default=QualityCheckSeverity.HIGH)

    # Check configuration (type-specific)
    config = Column(JSON, nullable=False)
    # Example configs:
    # ROW_COUNT: {"min_rows": 100, "max_rows": 10000}
    # NULL_CHECK: {"columns": ["user_id", "email"], "max_null_percentage": 5}
    # UNIQUENESS: {"column": "user_id"}
    # VALUE_RANGE: {"column": "age", "min": 0, "max": 150}
    # PATTERN_MATCH: {"column": "email", "pattern": "^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$"}
    # FRESHNESS: {"timestamp_column": "created_at", "max_age_hours": 24}
    # CUSTOM_SQL: {"query": "SELECT COUNT(*) FROM table WHERE condition", "expected_result": 0}

    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    organization = relationship("Organization", foreign_keys=[organization_id])
    pipeline_checks = relationship("PipelineQualityCheck", back_populates="quality_check", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<QualityCheck(id={self.id}, name='{self.name}', type='{self.check_type}')>"


class PipelineQualityCheck(Base):
    """
    Association between pipelines and quality checks.

    Links quality checks to specific pipelines.
    """
    __tablename__ = "pipeline_quality_checks"

    id = Column(Integer, primary_key=True, index=True)
    pipeline_id = Column(Integer, ForeignKey("pipelines.id", ondelete="CASCADE"), nullable=False, index=True)
    quality_check_id = Column(Integer, ForeignKey("quality_checks.id", ondelete="CASCADE"), nullable=False, index=True)

    # When to run this check
    run_on_success = Column(Boolean, default=True, nullable=False)  # Run after successful extraction
    run_on_failure = Column(Boolean, default=False, nullable=False)  # Run even if pipeline fails

    # Override severity for this pipeline
    override_severity = Column(SQLEnum(QualityCheckSeverity), nullable=True)

    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    pipeline = relationship("Pipeline", foreign_keys=[pipeline_id])
    quality_check = relationship("QualityCheck", back_populates="pipeline_checks")
    results = relationship("QualityCheckResult", back_populates="pipeline_check", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<PipelineQualityCheck(pipeline_id={self.pipeline_id}, check_id={self.quality_check_id})>"


class QualityCheckResult(Base):
    """
    Quality Check execution result.

    Stores the result of running a quality check for a pipeline run.
    """
    __tablename__ = "quality_check_results"

    id = Column(Integer, primary_key=True, index=True)
    public_id = Column(UUID(as_uuid=True), unique=True, nullable=False, default=uuid.uuid4, index=True)

    pipeline_run_id = Column(Integer, ForeignKey("pipeline_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    pipeline_check_id = Column(Integer, ForeignKey("pipeline_quality_checks.id", ondelete="CASCADE"), nullable=False, index=True)

    status = Column(SQLEnum(QualityCheckStatus), nullable=False, index=True)
    severity = Column(SQLEnum(QualityCheckSeverity), nullable=False)

    # Check results
    passed = Column(Boolean, nullable=False)
    actual_value = Column(JSON, nullable=True)  # Actual measured value
    expected_value = Column(JSON, nullable=True)  # Expected value from config
    message = Column(Text, nullable=True)  # Human-readable result message
    details = Column(JSON, nullable=True)  # Additional details

    # Metrics
    execution_time_ms = Column(Float, nullable=True)  # How long check took
    rows_checked = Column(Integer, nullable=True)  # Number of rows analyzed

    executed_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)

    # Relationships
    pipeline_run = relationship("PipelineRun", foreign_keys=[pipeline_run_id])
    pipeline_check = relationship("PipelineQualityCheck", back_populates="results")

    def __repr__(self):
        return f"<QualityCheckResult(id={self.id}, status='{self.status}', passed={self.passed})>"

    @property
    def check_name(self) -> str:
        """Get the quality check name."""
        return self.pipeline_check.quality_check.name if self.pipeline_check and self.pipeline_check.quality_check else "Unknown"

    @property
    def check_type(self) -> str:
        """Get the quality check type."""
        return self.pipeline_check.quality_check.check_type if self.pipeline_check and self.pipeline_check.quality_check else "unknown"
