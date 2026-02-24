"""
Data Model ORM Models.

Defines database models for AI-generated dimensional models,
including canonical and dimensional layers.
"""
from datetime import datetime, timezone
from typing import Optional
import uuid as uuid_module
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
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from backend.database import Base


class ModelLayer(str, enum.Enum):
    """Data model layer enumeration."""
    RAW = "raw"
    CANONICAL = "canonical"
    DIMENSIONAL = "dimensional"


class ModelStatus(str, enum.Enum):
    """Model status enumeration."""
    DRAFT = "draft"  # Generated but not reviewed
    APPROVED = "approved"  # Reviewed and approved
    DEPLOYED = "deployed"  # View created in destination
    DEPRECATED = "deprecated"  # No longer in use


class GeneratedModel(Base):
    """
    Generated Model entity.

    Represents an AI-generated data model (canonical or dimensional)
    that can be materialized as a view in the destination.
    """
    __tablename__ = "generated_models"

    id = Column(Integer, primary_key=True, index=True)
    public_id = Column(UUID(as_uuid=True), unique=True, nullable=False, default=uuid_module.uuid4, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    pipeline_id = Column(Integer, ForeignKey("pipelines.id", ondelete="CASCADE"), nullable=False, index=True)

    # Model metadata
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)

    # Model classification
    layer = Column(SQLEnum(ModelLayer), nullable=False, default=ModelLayer.DIMENSIONAL)
    model_type = Column(String(50), nullable=False)  # fact, dimension, canonical

    # Source information
    source_tables = Column(JSON, nullable=False, default=list)  # List of source table names

    # Model definition
    sql_definition = Column(Text, nullable=False)  # CREATE VIEW SQL

    # Column definitions
    # Format: [{"name": "col", "type": "VARCHAR", "description": "..."}]
    columns = Column(JSON, nullable=False, default=list)

    # Relationships to other models
    # Format: [{"from_col": "x", "to_table": "y", "to_col": "z"}]
    relationships = Column(JSON, nullable=False, default=list)

    # Business context
    # List of questions this model helps answer
    business_questions = Column(JSON, nullable=False, default=list)

    # AI reasoning for why this model was created
    ai_reasoning = Column(Text, nullable=True)

    # Status and deployment
    status = Column(SQLEnum(ModelStatus), nullable=False, default=ModelStatus.DRAFT, index=True)
    is_materialized = Column(Boolean, default=False, nullable=False)
    materialized_at = Column(DateTime, nullable=True)
    materialized_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    organization = relationship("Organization", backref="generated_models")
    pipeline = relationship("Pipeline", backref="generated_models")
    materialized_by = relationship("User", backref="materialized_models")

    def __repr__(self):
        return f"<GeneratedModel(id={self.id}, name='{self.name}', layer='{self.layer}')>"

    @property
    def column_names(self) -> list:
        """Get list of column names."""
        return [col.get("name") for col in (self.columns or [])]

    @property
    def is_fact_table(self) -> bool:
        """Check if this is a fact table."""
        return self.model_type == "fact"

    @property
    def is_dimension(self) -> bool:
        """Check if this is a dimension table."""
        return self.model_type == "dimension"


class ModelGeneration(Base):
    """
    Model Generation Run entity.

    Tracks each auto-modeling run for a pipeline.
    """
    __tablename__ = "model_generations"

    id = Column(Integer, primary_key=True, index=True)
    public_id = Column(UUID(as_uuid=True), unique=True, nullable=False, default=uuid_module.uuid4, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    pipeline_id = Column(Integer, ForeignKey("pipelines.id", ondelete="CASCADE"), nullable=False, index=True)
    pipeline_run_id = Column(Integer, ForeignKey("pipeline_runs.id", ondelete="SET NULL"), nullable=True, index=True)

    # Generation status
    status = Column(String(50), nullable=False, default="pending")  # pending, running, completed, failed
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    # Results
    models_generated = Column(Integer, nullable=True)
    questions_generated = Column(Integer, nullable=True)

    # Error information
    error_message = Column(Text, nullable=True)

    # Metadata
    schema_tables_analyzed = Column(Integer, nullable=True)
    schema_columns_analyzed = Column(Integer, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    organization = relationship("Organization", backref="model_generations")
    pipeline = relationship("Pipeline", backref="model_generations")
    pipeline_run = relationship("PipelineRun", backref="model_generations")

    def __repr__(self):
        return f"<ModelGeneration(id={self.id}, pipeline_id={self.pipeline_id}, status='{self.status}')>"
