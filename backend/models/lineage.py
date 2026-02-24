"""
Data Lineage ORM Models.

Defines database models for tracking data lineage at table and column level.
"""
from datetime import datetime
from typing import Optional
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
)
from sqlalchemy.orm import relationship
import enum

from backend.database import Base


class NodeType(str, enum.Enum):
    """Lineage node type enumeration."""
    TABLE = "table"
    COLUMN = "column"
    VIEW = "view"
    TRANSFORMATION = "transformation"
    SOURCE = "source"
    DESTINATION = "destination"


class TransformationType(str, enum.Enum):
    """Transformation type enumeration."""
    SELECT = "select"
    FILTER = "filter"
    JOIN = "join"
    AGGREGATE = "aggregate"
    UNION = "union"
    PIVOT = "pivot"
    UNPIVOT = "unpivot"
    CAST = "cast"
    CUSTOM = "custom"


class LineageNode(Base):
    """
    Lineage Node model.

    Represents a node in the data lineage graph (table, column, view, etc.).
    """
    __tablename__ = "lineage_nodes"

    id = Column(Integer, primary_key=True, index=True)

    # Node identification
    node_type = Column(SQLEnum(NodeType), nullable=False, index=True)
    name = Column(String(255), nullable=False, index=True)

    # Hierarchy: database.schema.table.column
    database_name = Column(String(255), nullable=True)
    schema_name = Column(String(255), nullable=True)
    table_name = Column(String(255), nullable=True)
    column_name = Column(String(255), nullable=True)

    # Full qualified name (FQN): database.schema.table.column
    fqn = Column(String(1024), nullable=False, unique=True, index=True)

    # Metadata
    description = Column(Text, nullable=True)
    data_type = Column(String(100), nullable=True)

    # Additional properties in JSON format
    properties = Column(JSON, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Last seen timestamp (for garbage collection)
    last_seen_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    outgoing_edges = relationship(
        "LineageEdge",
        foreign_keys="LineageEdge.source_node_id",
        back_populates="source_node",
        cascade="all, delete-orphan",
    )
    incoming_edges = relationship(
        "LineageEdge",
        foreign_keys="LineageEdge.target_node_id",
        back_populates="target_node",
        cascade="all, delete-orphan",
    )

    def __repr__(self):
        return f"<LineageNode(id={self.id}, type='{self.node_type}', fqn='{self.fqn}')>"

    @staticmethod
    def create_fqn(
        database: Optional[str] = None,
        schema: Optional[str] = None,
        table: Optional[str] = None,
        column: Optional[str] = None,
    ) -> str:
        """
        Create a fully qualified name from components.

        Args:
            database: Database name
            schema: Schema name
            table: Table name
            column: Column name

        Returns:
            Fully qualified name
        """
        parts = [p for p in [database, schema, table, column] if p]
        return ".".join(parts)


class LineageEdge(Base):
    """
    Lineage Edge model.

    Represents a relationship/transformation between two lineage nodes.
    """
    __tablename__ = "lineage_edges"
    __table_args__ = (
        UniqueConstraint("source_node_id", "target_node_id", name="unique_edge"),
    )

    id = Column(Integer, primary_key=True, index=True)

    source_node_id = Column(Integer, ForeignKey("lineage_nodes.id", ondelete="CASCADE"), nullable=False, index=True)
    target_node_id = Column(Integer, ForeignKey("lineage_nodes.id", ondelete="CASCADE"), nullable=False, index=True)

    # Transformation type
    transformation_type = Column(SQLEnum(TransformationType), nullable=True)

    # Transformation logic (SQL, Python code, etc.)
    transformation_logic = Column(Text, nullable=True)

    # Description of the transformation
    description = Column(Text, nullable=True)

    # Additional properties in JSON format
    properties = Column(JSON, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Last seen timestamp (for garbage collection)
    last_seen_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    source_node = relationship(
        "LineageNode",
        foreign_keys=[source_node_id],
        back_populates="outgoing_edges",
    )
    target_node = relationship(
        "LineageNode",
        foreign_keys=[target_node_id],
        back_populates="incoming_edges",
    )

    def __repr__(self):
        return (
            f"<LineageEdge(id={self.id}, "
            f"source={self.source_node_id}, "
            f"target={self.target_node_id}, "
            f"type='{self.transformation_type}')>"
        )
