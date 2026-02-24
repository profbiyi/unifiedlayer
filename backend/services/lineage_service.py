"""
Lineage Service.

Automatically generates and maintains data lineage from pipeline executions.
"""
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.orm import Session
import logging

from backend.models.lineage import LineageNode, LineageEdge, NodeType, TransformationType
from backend.models.pipeline import Pipeline, PipelineRun

logger = logging.getLogger(__name__)


class LineageService:
    """
    Service for managing data lineage.

    Automatically creates and updates lineage nodes and edges
    based on pipeline configurations and executions.
    """

    def __init__(self, db: Session):
        self.db = db

    def get_or_create_node(
        self,
        node_type: NodeType,
        name: str,
        database_name: Optional[str] = None,
        schema_name: Optional[str] = None,
        table_name: Optional[str] = None,
        column_name: Optional[str] = None,
        description: Optional[str] = None,
        data_type: Optional[str] = None,
        properties: Optional[Dict[str, Any]] = None,
    ) -> LineageNode:
        """
        Get or create a lineage node.

        Args:
            node_type: Type of node (source, destination, table, etc.)
            name: Display name
            database_name: Database name
            schema_name: Schema name
            table_name: Table name
            column_name: Column name
            description: Node description
            data_type: Data type (for columns)
            properties: Additional properties

        Returns:
            LineageNode instance
        """
        # Build FQN
        fqn = LineageNode.create_fqn(
            database=database_name,
            schema=schema_name,
            table=table_name,
            column=column_name,
        )
        if not fqn:
            fqn = f"{node_type.value}:{name}"

        # Check if exists
        node = self.db.query(LineageNode).filter(LineageNode.fqn == fqn).first()

        if node:
            # Update last_seen_at
            node.last_seen_at = datetime.now(timezone.utc)
            if properties:
                node.properties = {**(node.properties or {}), **properties}
            self.db.commit()
            return node

        # Create new node
        node = LineageNode(
            node_type=node_type,
            name=name,
            database_name=database_name,
            schema_name=schema_name,
            table_name=table_name,
            column_name=column_name,
            fqn=fqn,
            description=description,
            data_type=data_type,
            properties=properties,
            last_seen_at=datetime.now(timezone.utc),
        )
        self.db.add(node)
        self.db.commit()
        self.db.refresh(node)

        logger.info(f"Created lineage node: {fqn}")
        return node

    def get_or_create_edge(
        self,
        source_node: LineageNode,
        target_node: LineageNode,
        transformation_type: Optional[TransformationType] = None,
        transformation_logic: Optional[str] = None,
        description: Optional[str] = None,
        properties: Optional[Dict[str, Any]] = None,
    ) -> LineageEdge:
        """
        Get or create a lineage edge between two nodes.

        Args:
            source_node: Source node
            target_node: Target node
            transformation_type: Type of transformation
            transformation_logic: SQL/code for transformation
            description: Edge description
            properties: Additional properties

        Returns:
            LineageEdge instance
        """
        # Check if exists
        edge = self.db.query(LineageEdge).filter(
            LineageEdge.source_node_id == source_node.id,
            LineageEdge.target_node_id == target_node.id,
        ).first()

        if edge:
            # Update last_seen_at
            edge.last_seen_at = datetime.now(timezone.utc)
            if transformation_type:
                edge.transformation_type = transformation_type
            if transformation_logic:
                edge.transformation_logic = transformation_logic
            if properties:
                edge.properties = {**(edge.properties or {}), **properties}
            self.db.commit()
            return edge

        # Create new edge
        edge = LineageEdge(
            source_node_id=source_node.id,
            target_node_id=target_node.id,
            transformation_type=transformation_type,
            transformation_logic=transformation_logic,
            description=description,
            properties=properties,
            last_seen_at=datetime.now(timezone.utc),
        )
        self.db.add(edge)
        self.db.commit()
        self.db.refresh(edge)

        logger.info(f"Created lineage edge: {source_node.fqn} -> {target_node.fqn}")
        return edge

    def record_pipeline_lineage(
        self,
        pipeline: Pipeline,
        tables_loaded: List[str],
        run_id: Optional[int] = None,
    ) -> Tuple[List[LineageNode], List[LineageEdge]]:
        """
        Record lineage for a pipeline execution.

        Creates nodes for source, destination, and tables,
        and edges connecting them.

        Args:
            pipeline: Pipeline that was executed
            tables_loaded: List of table names that were loaded
            run_id: Pipeline run ID

        Returns:
            Tuple of (nodes, edges) created
        """
        nodes = []
        edges = []

        source = pipeline.source
        destination = pipeline.destination

        # Create source node
        source_node = self.get_or_create_node(
            node_type=NodeType.SOURCE,
            name=source.name,
            database_name=source.config.get("database"),
            schema_name=source.config.get("schema", "public"),
            description=source.description,
            properties={
                "source_type": source.source_type.value,
                "source_id": source.id,
                "public_id": str(source.public_id),
            },
        )
        nodes.append(source_node)

        # Create destination node
        dest_node = self.get_or_create_node(
            node_type=NodeType.DESTINATION,
            name=destination.name,
            database_name=destination.config.get("database"),
            schema_name=destination.config.get("dataset_name", "default"),
            description=destination.description,
            properties={
                "destination_type": destination.destination_type.value,
                "destination_id": destination.id,
                "public_id": str(destination.public_id),
            },
        )
        nodes.append(dest_node)

        # Create table nodes and edges
        for table_name in tables_loaded:
            # Source table node
            source_table = self.get_or_create_node(
                node_type=NodeType.TABLE,
                name=table_name,
                database_name=source.config.get("database"),
                schema_name=source.config.get("schema", "public"),
                table_name=table_name,
                properties={
                    "source_id": source.id,
                    "location": "source",
                },
            )
            nodes.append(source_table)

            # Edge from source to source table
            edge1 = self.get_or_create_edge(
                source_node=source_node,
                target_node=source_table,
                description=f"Table in source {source.name}",
            )
            edges.append(edge1)

            # Destination table node
            dest_table = self.get_or_create_node(
                node_type=NodeType.TABLE,
                name=table_name,
                database_name=destination.config.get("database"),
                schema_name=destination.config.get("dataset_name", "default"),
                table_name=table_name,
                properties={
                    "destination_id": destination.id,
                    "location": "destination",
                    "pipeline_id": pipeline.id,
                },
            )
            nodes.append(dest_table)

            # Edge from source table to dest table (the transformation)
            edge2 = self.get_or_create_edge(
                source_node=source_table,
                target_node=dest_table,
                transformation_type=TransformationType.SELECT,
                description=f"Pipeline: {pipeline.name}",
                properties={
                    "pipeline_id": pipeline.id,
                    "pipeline_name": pipeline.name,
                    "run_id": run_id,
                },
            )
            edges.append(edge2)

            # Edge from dest table to destination
            edge3 = self.get_or_create_edge(
                source_node=dest_table,
                target_node=dest_node,
                description=f"Table in destination {destination.name}",
            )
            edges.append(edge3)

        logger.info(
            f"Recorded lineage for pipeline {pipeline.name}: "
            f"{len(nodes)} nodes, {len(edges)} edges"
        )

        return nodes, edges

    def get_impact_analysis(
        self,
        node_id: int,
        max_depth: int = 10,
    ) -> Dict[str, Any]:
        """
        Analyze the impact of changes to a node.

        Shows all downstream nodes that would be affected
        if this node changes.

        Args:
            node_id: Node to analyze
            max_depth: Maximum depth to traverse

        Returns:
            Impact analysis results
        """
        from backend.utils.lineage_traversal import get_downstream_nodes

        node = self.db.query(LineageNode).filter(LineageNode.id == node_id).first()
        if not node:
            return {"error": "Node not found"}

        downstream_nodes, downstream_edges = get_downstream_nodes(
            self.db, node_id, max_depth
        )

        # Categorize impacts
        impacted_tables = [n for n in downstream_nodes if n.node_type == NodeType.TABLE]
        impacted_destinations = [n for n in downstream_nodes if n.node_type == NodeType.DESTINATION]

        # Get affected pipelines
        affected_pipeline_ids = set()
        for edge in downstream_edges:
            if edge.properties and "pipeline_id" in edge.properties:
                affected_pipeline_ids.add(edge.properties["pipeline_id"])

        return {
            "source_node": {
                "id": node.id,
                "name": node.name,
                "fqn": node.fqn,
                "type": node.node_type.value,
            },
            "total_impacted": len(downstream_nodes),
            "impacted_tables": len(impacted_tables),
            "impacted_destinations": len(impacted_destinations),
            "affected_pipelines": list(affected_pipeline_ids),
            "downstream_nodes": [
                {
                    "id": n.id,
                    "name": n.name,
                    "fqn": n.fqn,
                    "type": n.node_type.value,
                }
                for n in downstream_nodes
            ],
        }

    def refresh_pipeline_lineage(self, pipeline_id: int) -> bool:
        """
        Refresh lineage for a specific pipeline.

        Args:
            pipeline_id: Pipeline ID

        Returns:
            True if successful
        """
        pipeline = self.db.query(Pipeline).filter(Pipeline.id == pipeline_id).first()
        if not pipeline:
            return False

        # Get tables from source config
        tables = pipeline.source.config.get("tables", [])

        # If no specific tables, try to detect from last successful run
        if not tables:
            last_run = self.db.query(PipelineRun).filter(
                PipelineRun.pipeline_id == pipeline_id,
                PipelineRun.status == "completed",
            ).order_by(PipelineRun.created_at.desc()).first()

            if last_run and last_run.run_metadata:
                stats = last_run.run_metadata.get("stats", {})
                tables = [t["name"] for t in stats.get("tables", [])]

        if tables:
            self.record_pipeline_lineage(pipeline, tables)
            return True

        return False

    def refresh_all_lineage(self) -> Dict[str, int]:
        """
        Refresh lineage for all pipelines.

        Returns:
            Stats about refreshed lineage
        """
        pipelines = self.db.query(Pipeline).all()
        refreshed = 0
        failed = 0

        for pipeline in pipelines:
            try:
                if self.refresh_pipeline_lineage(pipeline.id):
                    refreshed += 1
                else:
                    failed += 1
            except Exception as e:
                logger.error(f"Failed to refresh lineage for pipeline {pipeline.id}: {e}")
                failed += 1

        return {
            "total_pipelines": len(pipelines),
            "refreshed": refreshed,
            "failed": failed,
        }
