"""
Column Lineage Pydantic Schemas.

Request/response schemas for column-level lineage API endpoints.
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID
from pydantic import BaseModel, Field


class ColumnLineageBase(BaseModel):
    """Base column lineage schema."""
    source_table: str
    source_column: str
    source_schema: Optional[str] = None
    source_database: Optional[str] = None
    target_table: str
    target_column: str
    target_schema: Optional[str] = None
    target_database: Optional[str] = None
    lineage_type: str
    transformation_expression: Optional[str] = None
    confidence_score: int = 100


class ColumnLineageCreate(ColumnLineageBase):
    """Column lineage creation schema."""
    transformation_id: Optional[int] = None
    pipeline_id: Optional[int] = None


class ColumnLineageResponse(ColumnLineageBase):
    """Column lineage response schema."""
    id: int
    public_id: UUID
    transformation_id: Optional[int] = None
    pipeline_id: Optional[int] = None
    dbt_run_id: Optional[int] = None
    organization_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ColumnDependencyResponse(BaseModel):
    """Column dependency response for upstream/downstream queries."""
    table: str
    column: str
    schema: Optional[str] = None
    database: Optional[str] = None
    lineage_type: str
    transformation: Optional[str] = None
    depth: int
    path: List[str] = Field(default_factory=list)


class ColumnLineageGraphNode(BaseModel):
    """Node in column lineage graph."""
    id: str
    table: str
    column: str
    schema: Optional[str] = None
    database: Optional[str] = None
    type: str  # source, target, downstream


class ColumnLineageGraphEdge(BaseModel):
    """Edge in column lineage graph."""
    id: str
    source: str
    target: str
    lineage_type: str
    transformation: Optional[str] = None
    confidence: int = 100


class ColumnLineageGraphResponse(BaseModel):
    """Column lineage graph response."""
    nodes: List[ColumnLineageGraphNode]
    edges: List[ColumnLineageGraphEdge]
    table: str


class ColumnImpactSummary(BaseModel):
    """Summary of column impact analysis."""
    total_downstream_columns: int
    tables_affected: int
    pipelines_affected: int
    transformations_affected: int
    max_depth_reached: int


class AffectedPipeline(BaseModel):
    """Pipeline affected by column change."""
    id: int
    name: str
    is_active: bool


class ColumnImpactAnalysisResponse(BaseModel):
    """Column impact analysis response."""
    source: Dict[str, str]
    summary: ColumnImpactSummary
    downstream_columns: List[ColumnDependencyResponse]
    tables_affected: Dict[str, List[str]]
    affected_pipelines: List[AffectedPipeline]
    affected_transformation_ids: List[int]


class DbtColumnMetadataResponse(BaseModel):
    """dbt column metadata response."""
    id: int
    dbt_project_id: int
    model_name: str
    column_name: str
    description: Optional[str] = None
    data_type: Optional[str] = None
    tests: Optional[List[Dict[str, Any]]] = None
    tags: Optional[List[str]] = None
    meta: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ParseSQLRequest(BaseModel):
    """Request to parse SQL for column lineage."""
    sql: str
    target_table: Optional[str] = None
    target_schema: Optional[str] = None
    target_database: Optional[str] = None
    dialect: str = "postgres"


class ParseSQLResponse(BaseModel):
    """Response from parsing SQL for column lineage."""
    mappings: List[Dict[str, Any]]
    tables_referenced: List[str]
    is_valid: bool
    error: Optional[str] = None


class TableColumnLineageRequest(BaseModel):
    """Request for table column lineage."""
    table_name: str
    column_name: Optional[str] = None


class RefreshLineageResponse(BaseModel):
    """Response from refreshing column lineage."""
    success: bool
    lineage_count: int
    message: Optional[str] = None
