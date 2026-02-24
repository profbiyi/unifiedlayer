"""
SQL Transformation ORM Models.

Defines database models for SQL transformations that run after
data is loaded to the destination.
"""
from datetime import datetime, timezone
from typing import Optional
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


class TransformationStatus(str, enum.Enum):
    """Transformation execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class SQLTransformation(Base):
    """
    SQL Transformation model.

    Represents a SQL transformation that runs against the destination
    after data is loaded. Multiple transformations can be defined per
    pipeline and they execute in order.
    """
    __tablename__ = "sql_transformations"

    id = Column(Integer, primary_key=True, index=True)
    public_id = Column(UUID(as_uuid=True), unique=True, nullable=False, default=uuid.uuid4, index=True)
    pipeline_id = Column(Integer, ForeignKey("pipelines.id", ondelete="CASCADE"), nullable=False, index=True)

    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    # SQL query to execute
    sql_query = Column(Text, nullable=False)

    # Target table for results (optional - if not set, SQL runs as statement)
    target_table = Column(String(255), nullable=True)

    # Write mode: replace, append, merge
    write_mode = Column(String(50), nullable=True, default="replace")

    # Execution order (lower numbers execute first)
    execution_order = Column(Integer, nullable=False, default=0)

    # Whether this transformation is active
    is_active = Column(Boolean, default=True, nullable=False)

    # Continue on error (if True, pipeline continues even if this transform fails)
    continue_on_error = Column(Boolean, default=False, nullable=False)

    # Timeout in seconds (0 = no timeout)
    timeout_seconds = Column(Integer, nullable=False, default=300)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    pipeline = relationship("Pipeline", back_populates="sql_transformations")
    execution_results = relationship("TransformationResult", back_populates="transformation", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<SQLTransformation(id={self.id}, name='{self.name}', order={self.execution_order})>"


class TransformationResult(Base):
    """
    Transformation Result model.

    Records the result of executing a transformation during a pipeline run.
    """
    __tablename__ = "transformation_results"

    id = Column(Integer, primary_key=True, index=True)
    public_id = Column(UUID(as_uuid=True), unique=True, nullable=False, default=uuid.uuid4, index=True)
    pipeline_run_id = Column(Integer, ForeignKey("pipeline_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    transformation_id = Column(Integer, ForeignKey("sql_transformations.id", ondelete="CASCADE"), nullable=False, index=True)

    status = Column(SQLEnum(TransformationStatus), default=TransformationStatus.PENDING, nullable=False)

    # Execution timing
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Float, nullable=True)

    # Result metrics
    rows_affected = Column(Integer, nullable=True)

    # Error information
    error_message = Column(Text, nullable=True)
    error_traceback = Column(Text, nullable=True)

    # Additional metadata (query plan, etc.)
    result_metadata = Column(JSON, nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    pipeline_run = relationship("PipelineRun", back_populates="transformation_results")
    transformation = relationship("SQLTransformation", back_populates="execution_results")

    def __repr__(self):
        return f"<TransformationResult(id={self.id}, transformation_id={self.transformation_id}, status='{self.status}')>"
