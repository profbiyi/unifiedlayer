"""
Column-Level Lineage ORM Models.

Defines database models for tracking column-level data lineage,
enabling fine-grained impact analysis and data governance.
"""
from datetime import datetime, timezone
import uuid
import enum

from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    Text,
    ForeignKey,
    JSON,
    Enum as SQLEnum,
    UniqueConstraint,
    Index,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from backend.database import Base


class ColumnLineageType(str, enum.Enum):
    """Column lineage transformation type."""
    DIRECT = "direct"  # Direct column mapping (e.g., SELECT col)
    DERIVED = "derived"  # Derived from expression (e.g., col1 + col2)
    AGGREGATED = "aggregated"  # Aggregation (e.g., SUM(col))
    CAST = "cast"  # Type cast (e.g., CAST(col AS INT))
    FILTERED = "filtered"  # Column used in filter (WHERE/HAVING)
    JOINED = "joined"  # Column used in join condition
    GROUPED = "grouped"  # Column used in GROUP BY


class ColumnLineage(Base):
    """
    Column Lineage model.

    Represents a column-level lineage relationship between source and target columns.
    Tracks how data flows from source columns to target columns through transformations.
    """
    __tablename__ = "column_lineage"
    __table_args__ = (
        UniqueConstraint(
            "source_table", "source_column", "target_table", "target_column",
            "transformation_id", "pipeline_id",
            name="unique_column_lineage"
        ),
        Index("ix_column_lineage_source", "source_table", "source_column"),
        Index("ix_column_lineage_target", "target_table", "target_column"),
        Index("ix_column_lineage_pipeline", "pipeline_id"),
        Index("ix_column_lineage_transformation", "transformation_id"),
    )

    id = Column(Integer, primary_key=True, index=True)
    public_id = Column(
        UUID(as_uuid=True),
        unique=True,
        nullable=False,
        default=uuid.uuid4,
        index=True
    )

    # Source column information
    source_database = Column(String(255), nullable=True)
    source_schema = Column(String(255), nullable=True)
    source_table = Column(String(255), nullable=False, index=True)
    source_column = Column(String(255), nullable=False, index=True)
    source_data_type = Column(String(100), nullable=True)

    # Target column information
    target_database = Column(String(255), nullable=True)
    target_schema = Column(String(255), nullable=True)
    target_table = Column(String(255), nullable=False, index=True)
    target_column = Column(String(255), nullable=False, index=True)
    target_data_type = Column(String(100), nullable=True)

    # Lineage type and transformation details
    lineage_type = Column(
        SQLEnum(ColumnLineageType),
        default=ColumnLineageType.DIRECT,
        nullable=False
    )
    transformation_expression = Column(Text, nullable=True)

    # Foreign keys (optional - can be null for dbt-sourced lineage)
    transformation_id = Column(
        Integer,
        ForeignKey("sql_transformations.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )
    pipeline_id = Column(
        Integer,
        ForeignKey("pipelines.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )
    dbt_run_id = Column(
        Integer,
        ForeignKey("dbt_runs.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    # Organization scope
    organization_id = Column(
        Integer,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Additional metadata
    confidence_score = Column(Integer, default=100, nullable=False)
    properties = Column(JSON, nullable=True)

    # Timestamps
    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    transformation = relationship(
        "SQLTransformation",
        backref="column_lineages",
        foreign_keys=[transformation_id]
    )
    pipeline = relationship(
        "Pipeline",
        backref="column_lineages",
        foreign_keys=[pipeline_id]
    )
    dbt_run = relationship(
        "DbtRun",
        backref="column_lineages",
        foreign_keys=[dbt_run_id]
    )
    organization = relationship(
        "Organization",
        backref="column_lineages",
        foreign_keys=[organization_id]
    )

    def __repr__(self):
        return (
            f"<ColumnLineage(id={self.id}, "
            f"source='{self.source_table}.{self.source_column}', "
            f"target='{self.target_table}.{self.target_column}')>"
        )

    @property
    def source_fqn(self) -> str:
        """Return fully qualified name for source column."""
        parts = [p for p in [
            self.source_database,
            self.source_schema,
            self.source_table,
            self.source_column
        ] if p]
        return ".".join(parts)

    @property
    def target_fqn(self) -> str:
        """Return fully qualified name for target column."""
        parts = [p for p in [
            self.target_database,
            self.target_schema,
            self.target_table,
            self.target_column
        ] if p]
        return ".".join(parts)


class DbtColumnMetadata(Base):
    """
    dbt Column Metadata model.

    Stores column-level metadata extracted from dbt manifest.json,
    including descriptions, tests, and data types.
    """
    __tablename__ = "dbt_column_metadata"
    __table_args__ = (
        UniqueConstraint(
            "dbt_project_id", "model_name", "column_name",
            name="unique_dbt_column"
        ),
        Index("ix_dbt_column_model", "model_name"),
    )

    id = Column(Integer, primary_key=True, index=True)

    dbt_project_id = Column(
        Integer,
        ForeignKey("dbt_projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Model and column identification
    model_name = Column(String(255), nullable=False, index=True)
    column_name = Column(String(255), nullable=False, index=True)

    # Column metadata from dbt
    description = Column(Text, nullable=True)
    data_type = Column(String(100), nullable=True)
    is_nullable = Column(String(10), nullable=True)

    # Tests applied to this column
    tests = Column(JSON, nullable=True)

    # Tags and meta from dbt
    tags = Column(JSON, nullable=True)
    meta = Column(JSON, nullable=True)

    # Source model (for lineage)
    depends_on = Column(JSON, nullable=True)

    # Timestamps
    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    dbt_project = relationship(
        "DbtProject",
        backref="column_metadata",
        foreign_keys=[dbt_project_id]
    )

    def __repr__(self):
        return (
            f"<DbtColumnMetadata(id={self.id}, "
            f"model='{self.model_name}', column='{self.column_name}')>"
        )
