"""
Data Lineage API routes.

Provides endpoints for table-level and column-level lineage tracking.
"""
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from sqlalchemy.orm import Session
from sqlalchemy import select

from backend.database import get_db
from backend.schemas import (
    LineageNodeCreate,
    LineageNodeResponse,
    LineageEdgeCreate,
    LineageEdgeResponse,
    LineageGraphResponse,
    ColumnLineageResponse,
    ColumnDependencyResponse,
    ColumnLineageGraphResponse,
    ColumnImpactAnalysisResponse,
    ParseSQLRequest,
    ParseSQLResponse,
    RefreshLineageResponse,
    DbtColumnMetadataResponse,
)
from backend.models.lineage import LineageNode, LineageEdge
from backend.models.column_lineage import ColumnLineage, DbtColumnMetadata
from backend.models.pipeline import User, Pipeline, DataSource, Destination, PipelineRun
from backend.models.transformation import SQLTransformation
from backend.auth import get_current_user
from backend.services.column_lineage_service import ColumnLineageService
from backend.services.column_lineage_parser import SQLColumnLineageParser
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/lineage", tags=["Data Lineage"])


@router.get("/nodes", response_model=List[LineageNodeResponse])
async def list_nodes(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    node_type: str = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all lineage nodes."""
    query = db.query(LineageNode)

    if node_type:
        query = query.filter(LineageNode.node_type == node_type)

    nodes = query.offset(skip).limit(limit).all()
    return nodes


@router.get("/nodes/{node_id}", response_model=LineageNodeResponse)
async def get_node(
    node_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a specific lineage node."""
    node = db.query(LineageNode).filter(LineageNode.id == node_id).first()

    if not node:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lineage node not found",
        )

    return node


@router.post("/nodes", response_model=LineageNodeResponse, status_code=status.HTTP_201_CREATED)
async def create_node(
    node_data: LineageNodeCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new lineage node."""
    # Check if FQN already exists
    existing = db.query(LineageNode).filter(LineageNode.fqn == node_data.fqn).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Node with this FQN already exists",
        )

    node = LineageNode(
        node_type=node_data.node_type,
        name=node_data.name,
        database_name=node_data.database_name,
        schema_name=node_data.schema_name,
        table_name=node_data.table_name,
        column_name=node_data.column_name,
        fqn=node_data.fqn,
        description=node_data.description,
        data_type=node_data.data_type,
        properties=node_data.properties,
    )

    db.add(node)
    db.commit()
    db.refresh(node)

    logger.info(f"Lineage node created: {node.id} - {node.fqn}")
    return node


@router.get("/edges", response_model=List[LineageEdgeResponse])
async def list_edges(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all lineage edges."""
    edges = db.query(LineageEdge).offset(skip).limit(limit).all()
    return edges


@router.post("/edges", response_model=LineageEdgeResponse, status_code=status.HTTP_201_CREATED)
async def create_edge(
    edge_data: LineageEdgeCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new lineage edge."""
    edge = LineageEdge(
        source_node_id=edge_data.source_node_id,
        target_node_id=edge_data.target_node_id,
        transformation_type=edge_data.transformation_type,
        transformation_logic=edge_data.transformation_logic,
        description=edge_data.description,
        properties=edge_data.properties,
    )

    db.add(edge)
    db.commit()
    db.refresh(edge)

    logger.info(f"Lineage edge created: {edge.id}")
    return edge


@router.get("/graph/{table_fqn}", response_model=LineageGraphResponse)
async def get_lineage_graph(
    table_fqn: str,
    depth: int = Query(3, ge=1, le=10),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get lineage graph for a specific table.

    Returns upstream and downstream lineage up to specified depth.
    """
    # Find the root node
    root_node = db.query(LineageNode).filter(LineageNode.fqn == table_fqn).first()

    if not root_node:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Table not found in lineage",
        )

    # Get full lineage graph using recursive traversal
    from backend.utils.lineage_traversal import get_full_lineage_graph

    nodes, edges = get_full_lineage_graph(
        db=db,
        node_id=root_node.id,
        max_depth=10,  # Traverse up to 10 levels deep
    )

    return {
        "nodes": nodes,
        "edges": edges,
    }


@router.get("/upstream/{table_fqn}", response_model=List[LineageNodeResponse])
async def get_upstream_lineage(
    table_fqn: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get all upstream (source) tables for a given table."""
    root_node = db.query(LineageNode).filter(LineageNode.fqn == table_fqn).first()

    if not root_node:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Table not found in lineage",
        )

    # Get all upstream nodes recursively
    from backend.utils.lineage_traversal import get_upstream_nodes

    upstream_nodes, _ = get_upstream_nodes(
        db=db,
        node_id=root_node.id,
        max_depth=10,
    )

    return upstream_nodes


@router.get("/downstream/{table_fqn}", response_model=List[LineageNodeResponse])
async def get_downstream_lineage(
    table_fqn: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get all downstream (target) tables for a given table."""
    root_node = db.query(LineageNode).filter(LineageNode.fqn == table_fqn).first()

    if not root_node:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Table not found in lineage",
        )

    # Get all downstream nodes recursively
    from backend.utils.lineage_traversal import get_downstream_nodes

    downstream_nodes, _ = get_downstream_nodes(
        db=db,
        node_id=root_node.id,
        max_depth=10,
    )

    return downstream_nodes


@router.get("/impact/{node_id}")
async def get_impact_analysis(
    node_id: int,
    max_depth: int = Query(10, ge=1, le=20),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Get impact analysis for a lineage node.

    Shows all downstream nodes that would be affected if this node changes.
    """
    from backend.services.lineage_service import LineageService

    lineage_service = LineageService(db)
    return lineage_service.get_impact_analysis(node_id, max_depth)


@router.post("/refresh")
async def refresh_all_lineage(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Refresh lineage for all pipelines in the organization."""
    from backend.services.lineage_service import LineageService

    lineage_service = LineageService(db)
    return lineage_service.refresh_all_lineage()


@router.post("/refresh/{pipeline_id}")
async def refresh_pipeline_lineage(
    pipeline_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, bool]:
    """Refresh lineage for a specific pipeline."""
    from backend.services.lineage_service import LineageService

    lineage_service = LineageService(db)
    success = lineage_service.refresh_pipeline_lineage(pipeline_id)
    return {"success": success}


@router.get("/pipeline-graph")
async def get_pipeline_lineage_graph(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Get pipeline-level lineage graph for the current organization.

    Returns a graph structure with nodes (sources, pipelines, destinations)
    and edges (relationships between them) suitable for visualization.
    """
    org_id = current_user.organization_id

    # Fetch all sources for the organization
    sources_stmt = select(DataSource).where(DataSource.organization_id == org_id)
    sources = db.execute(sources_stmt).scalars().all()

    # Fetch all destinations for the organization
    destinations_stmt = select(Destination).where(Destination.organization_id == org_id)
    destinations = db.execute(destinations_stmt).scalars().all()

    # Fetch all pipelines for the organization
    pipelines_stmt = select(Pipeline).where(Pipeline.organization_id == org_id)
    pipelines = db.execute(pipelines_stmt).scalars().all()

    # Build nodes
    nodes = []

    # Add source nodes
    for source in sources:
        # Count pipelines using this source
        pipeline_count = sum(1 for p in pipelines if p.source_id == source.id)

        nodes.append({
            "id": f"source-{source.id}",
            "type": "source",
            "data": {
                "id": source.id,
                "public_id": str(source.public_id),
                "name": source.name,
                "sourceType": source.source_type,
                "connectionString": source.connection_string,
                "pipelineCount": pipeline_count,
            }
        })

    # Add pipeline nodes
    for pipeline in pipelines:
        # Get latest run status
        latest_run = db.execute(
            select(PipelineRun)
            .where(PipelineRun.pipeline_id == pipeline.id)
            .order_by(PipelineRun.created_at.desc())
            .limit(1)
        ).scalar_one_or_none()

        latest_status = latest_run.status if latest_run else None

        nodes.append({
            "id": f"pipeline-{pipeline.id}",
            "type": "pipeline",
            "data": {
                "id": pipeline.id,
                "public_id": str(pipeline.public_id),
                "name": pipeline.name,
                "description": pipeline.description,
                "isActive": pipeline.is_active,
                "schedule": pipeline.schedule,
                "latestStatus": latest_status,
                "sourceId": pipeline.source_id,
                "destinationId": pipeline.destination_id,
            }
        })

    # Add destination nodes
    for destination in destinations:
        # Count pipelines using this destination
        pipeline_count = sum(1 for p in pipelines if p.destination_id == destination.id)

        nodes.append({
            "id": f"destination-{destination.id}",
            "type": "destination",
            "data": {
                "id": destination.id,
                "public_id": str(destination.public_id),
                "name": destination.name,
                "destinationType": destination.destination_type,
                "connectionString": destination.connection_string,
                "pipelineCount": pipeline_count,
            }
        })

    # Build edges
    edges = []

    for pipeline in pipelines:
        # Edge from source to pipeline
        edges.append({
            "id": f"source-{pipeline.source_id}-to-pipeline-{pipeline.id}",
            "source": f"source-{pipeline.source_id}",
            "target": f"pipeline-{pipeline.id}",
            "type": "default",
            "animated": pipeline.is_active,
        })

        # Edge from pipeline to destination
        edges.append({
            "id": f"pipeline-{pipeline.id}-to-destination-{pipeline.destination_id}",
            "source": f"pipeline-{pipeline.id}",
            "target": f"destination-{pipeline.destination_id}",
            "type": "default",
            "animated": pipeline.is_active,
        })

    return {
        "nodes": nodes,
        "edges": edges,
        "stats": {
            "sources": len(sources),
            "pipelines": len(pipelines),
            "destinations": len(destinations),
            "activePipelines": sum(1 for p in pipelines if p.is_active),
        }
    }


# ============================================================================
# Column-Level Lineage Endpoints
# ============================================================================


@router.get("/columns/{table_name}", response_model=List[ColumnLineageResponse])
async def get_column_lineage_for_table(
    table_name: str,
    column_name: str = Query(None, description="Optional specific column"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get column lineage for a table.

    Returns all column lineage relationships where the table
    is either source or target.
    """
    service = ColumnLineageService(db)
    lineages = service.get_column_lineage(
        table_name=table_name,
        organization_id=current_user.organization_id,
        column_name=column_name,
    )
    return lineages


@router.get(
    "/columns/{table_name}/{column_name}/upstream",
    response_model=List[ColumnDependencyResponse]
)
async def get_column_upstream(
    table_name: str,
    column_name: str,
    max_depth: int = Query(10, ge=1, le=50, description="Maximum traversal depth"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Trace column upstream to find all source columns.

    Returns all source columns that flow into this column,
    traversing through transformations and pipelines.
    """
    service = ColumnLineageService(db)
    upstream = service.get_upstream_columns(
        table_name=table_name,
        column_name=column_name,
        organization_id=current_user.organization_id,
        max_depth=max_depth,
    )
    return upstream


@router.get(
    "/columns/{table_name}/{column_name}/downstream",
    response_model=List[ColumnDependencyResponse]
)
async def get_column_downstream(
    table_name: str,
    column_name: str,
    max_depth: int = Query(10, ge=1, le=50, description="Maximum traversal depth"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Trace column downstream to find all dependent columns.

    Returns all columns that depend on this column,
    traversing through transformations and pipelines.
    """
    service = ColumnLineageService(db)
    downstream = service.get_downstream_columns(
        table_name=table_name,
        column_name=column_name,
        organization_id=current_user.organization_id,
        max_depth=max_depth,
    )
    return downstream


@router.get(
    "/columns/{table_name}/{column_name}/impact",
    response_model=ColumnImpactAnalysisResponse
)
async def get_column_impact_analysis(
    table_name: str,
    column_name: str,
    max_depth: int = Query(10, ge=1, le=50, description="Maximum traversal depth"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Perform impact analysis for a column.

    Shows all downstream columns, tables, and pipelines that
    would be affected if this column changes or is removed.
    """
    service = ColumnLineageService(db)
    impact = service.get_column_impact_analysis(
        table_name=table_name,
        column_name=column_name,
        organization_id=current_user.organization_id,
        max_depth=max_depth,
    )
    return impact


@router.get(
    "/columns/{table_name}/graph",
    response_model=ColumnLineageGraphResponse
)
async def get_column_lineage_graph(
    table_name: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get column lineage graph for a table.

    Returns nodes (columns) and edges (lineage relationships)
    suitable for visualization.
    """
    service = ColumnLineageService(db)
    graph = service.get_table_column_lineage_graph(
        table_name=table_name,
        organization_id=current_user.organization_id,
    )
    return graph


@router.post("/columns/parse-sql", response_model=ParseSQLResponse)
async def parse_sql_for_lineage(
    request: ParseSQLRequest = Body(...),
    current_user: User = Depends(get_current_user),
):
    """
    Parse SQL to extract column lineage mappings.

    Analyzes the SQL statement and returns the column-level
    lineage it would create, without persisting to the database.
    """
    parser = SQLColumnLineageParser(
        dialect=request.dialect,
    )

    # Validate SQL first
    is_valid, error = parser.validate_sql(request.sql)

    if not is_valid:
        return ParseSQLResponse(
            mappings=[],
            tables_referenced=[],
            is_valid=False,
            error=error,
        )

    # Parse lineage
    mappings = parser.parse_sql(
        request.sql,
        target_table=request.target_table,
        target_schema=request.target_schema,
        target_database=request.target_database,
    )

    # Get referenced tables
    tables = parser.get_all_referenced_tables(request.sql)

    return ParseSQLResponse(
        mappings=[m.to_dict() for m in mappings],
        tables_referenced=tables,
        is_valid=True,
        error=None,
    )


@router.post(
    "/columns/transformation/{transformation_id}/refresh",
    response_model=RefreshLineageResponse
)
async def refresh_transformation_column_lineage(
    transformation_id: int,
    dialect: str = Query("postgres", description="SQL dialect"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Refresh column lineage for a SQL transformation.

    Re-parses the transformation SQL and updates the column lineage.
    """
    # Verify transformation exists and belongs to user's org
    transformation = db.query(SQLTransformation).filter(
        SQLTransformation.id == transformation_id
    ).first()

    if not transformation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transformation not found",
        )

    pipeline = db.query(Pipeline).filter(
        Pipeline.id == transformation.pipeline_id,
        Pipeline.organization_id == current_user.organization_id,
    ).first()

    if not pipeline:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this transformation",
        )

    service = ColumnLineageService(db)

    try:
        lineages = service.refresh_transformation_lineage(
            transformation_id=transformation_id,
            organization_id=current_user.organization_id,
            dialect=dialect,
        )

        return RefreshLineageResponse(
            success=True,
            lineage_count=len(lineages),
            message=f"Refreshed {len(lineages)} column lineage entries",
        )

    except Exception as e:
        logger.error(f"Error refreshing transformation lineage: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error refreshing lineage: {str(e)}",
        )


@router.get(
    "/columns/dbt/{model_name}/metadata",
    response_model=List[DbtColumnMetadataResponse]
)
async def get_dbt_column_metadata(
    model_name: str,
    dbt_project_id: int = Query(..., description="dbt project ID"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get dbt column metadata for a model.

    Returns column descriptions, data types, and tests
    extracted from dbt manifest.
    """
    from backend.models.dbt import DbtProject

    # Verify project belongs to user's org
    project = db.query(DbtProject).filter(
        DbtProject.id == dbt_project_id,
        DbtProject.organization_id == current_user.organization_id,
    ).first()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="dbt project not found",
        )

    metadata = db.query(DbtColumnMetadata).filter(
        DbtColumnMetadata.dbt_project_id == dbt_project_id,
        DbtColumnMetadata.model_name == model_name,
    ).all()

    return metadata


@router.delete("/columns/transformation/{transformation_id}")
async def delete_transformation_column_lineage(
    transformation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Delete all column lineage for a transformation.
    """
    # Verify transformation exists and belongs to user's org
    transformation = db.query(SQLTransformation).filter(
        SQLTransformation.id == transformation_id
    ).first()

    if not transformation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transformation not found",
        )

    pipeline = db.query(Pipeline).filter(
        Pipeline.id == transformation.pipeline_id,
        Pipeline.organization_id == current_user.organization_id,
    ).first()

    if not pipeline:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this transformation",
        )

    service = ColumnLineageService(db)
    deleted = service.delete_lineage_for_transformation(transformation_id)

    return {
        "success": True,
        "deleted_count": deleted,
    }


@router.delete("/columns/pipeline/{pipeline_id}")
async def delete_pipeline_column_lineage(
    pipeline_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Delete all column lineage for a pipeline.
    """
    # Verify pipeline belongs to user's org
    pipeline = db.query(Pipeline).filter(
        Pipeline.id == pipeline_id,
        Pipeline.organization_id == current_user.organization_id,
    ).first()

    if not pipeline:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pipeline not found",
        )

    service = ColumnLineageService(db)
    deleted = service.delete_lineage_for_pipeline(pipeline_id)

    return {
        "success": True,
        "deleted_count": deleted,
    }
