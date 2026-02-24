"""
Column Lineage Service.

Manages column-level lineage tracking, integrating SQL parsing
and dbt manifest parsing to provide comprehensive lineage information.
"""
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple, Set
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
import logging

from backend.models.column_lineage import (
    ColumnLineage,
    ColumnLineageType,
    DbtColumnMetadata,
)
from backend.models.transformation import SQLTransformation
from backend.models.pipeline import Pipeline
from backend.models.dbt import DbtRun
from backend.services.column_lineage_parser import (
    SQLColumnLineageParser,
)
from backend.services.dbt_manifest_parser import DbtManifestParser

logger = logging.getLogger(__name__)


class ColumnLineageService:
    """
    Service for managing column-level lineage.

    Provides methods to:
    - Record lineage from SQL transformations
    - Parse and store dbt manifest lineage
    - Query upstream/downstream column dependencies
    - Perform impact analysis at column level
    """

    def __init__(self, db: Session):
        """
        Initialize the service.

        Args:
            db: SQLAlchemy database session
        """
        self.db = db

    def record_transformation_lineage(
        self,
        transformation: SQLTransformation,
        organization_id: int,
        dialect: str = "postgres",
    ) -> List[ColumnLineage]:
        """
        Parse and record column lineage from a SQL transformation.

        Args:
            transformation: SQLTransformation to analyze
            organization_id: Organization ID for scoping
            dialect: SQL dialect for parsing

        Returns:
            List of created ColumnLineage records
        """
        parser = SQLColumnLineageParser(dialect=dialect)

        # Parse the SQL
        mappings = parser.parse_sql(
            transformation.sql_query,
            target_table=transformation.target_table,
        )

        created_lineages = []

        for mapping in mappings:
            for source_col in mapping.source_columns:
                lineage = self._create_or_update_lineage(
                    source_table=source_col.source_table,
                    source_column=source_col.source_column,
                    source_schema=source_col.source_schema,
                    source_database=source_col.source_database,
                    target_table=mapping.target_table,
                    target_column=mapping.target_column,
                    target_schema=mapping.target_schema,
                    target_database=mapping.target_database,
                    lineage_type=mapping.lineage_type,
                    transformation_expression=mapping.transformation_expression,
                    transformation_id=transformation.id,
                    pipeline_id=transformation.pipeline_id,
                    organization_id=organization_id,
                    confidence_score=mapping.confidence_score,
                )
                created_lineages.append(lineage)

        logger.info(
            f"Recorded {len(created_lineages)} column lineage entries "
            f"for transformation {transformation.id}"
        )

        return created_lineages

    def record_dbt_lineage(
        self,
        dbt_run: DbtRun,
        organization_id: int,
        dialect: str = "postgres",
    ) -> Tuple[List[ColumnLineage], List[DbtColumnMetadata]]:
        """
        Parse dbt manifest and record column lineage and metadata.

        Args:
            dbt_run: DbtRun with manifest_json
            organization_id: Organization ID for scoping
            dialect: SQL dialect for parsing

        Returns:
            Tuple of (lineage_records, metadata_records)
        """
        if not dbt_run.manifest_json:
            logger.warning(f"No manifest.json for dbt run {dbt_run.id}")
            return [], []

        parser = DbtManifestParser(dbt_run.manifest_json)

        created_lineages = []
        created_metadata = []

        # Extract and store column metadata
        for model in parser.get_models().values():
            for col_name, column in model.columns.items():
                metadata = self._create_or_update_column_metadata(
                    dbt_project_id=dbt_run.dbt_project_id,
                    model_name=model.name,
                    column_name=col_name,
                    description=column.description,
                    data_type=column.data_type,
                    tests=[{"name": t.get("name")} for t in column.tests],
                    tags=column.tags,
                    meta=column.meta,
                )
                created_metadata.append(metadata)

        # Extract and store column lineage
        for model in parser.get_models().values():
            lineage_entries = parser.extract_column_lineage(model.name, dialect)

            for entry in lineage_entries:
                lineage = self._create_or_update_lineage(
                    source_table=entry.source_model,
                    source_column=entry.source_column,
                    target_table=entry.target_model,
                    target_column=entry.target_column,
                    lineage_type=ColumnLineageType.DERIVED,
                    transformation_expression=entry.transformation,
                    dbt_run_id=dbt_run.id,
                    organization_id=organization_id,
                    confidence_score=entry.confidence,
                )
                created_lineages.append(lineage)

        logger.info(
            f"Recorded {len(created_lineages)} column lineage entries "
            f"and {len(created_metadata)} column metadata entries "
            f"from dbt run {dbt_run.id}"
        )

        return created_lineages, created_metadata

    def _create_or_update_lineage(
        self,
        source_table: str,
        source_column: str,
        target_table: str,
        target_column: str,
        organization_id: int,
        source_schema: Optional[str] = None,
        source_database: Optional[str] = None,
        target_schema: Optional[str] = None,
        target_database: Optional[str] = None,
        lineage_type: ColumnLineageType = ColumnLineageType.DIRECT,
        transformation_expression: Optional[str] = None,
        transformation_id: Optional[int] = None,
        pipeline_id: Optional[int] = None,
        dbt_run_id: Optional[int] = None,
        confidence_score: int = 100,
    ) -> ColumnLineage:
        """Create or update a column lineage record."""
        # Check for existing
        existing = self.db.query(ColumnLineage).filter(
            and_(
                ColumnLineage.source_table == source_table,
                ColumnLineage.source_column == source_column,
                ColumnLineage.target_table == target_table,
                ColumnLineage.target_column == target_column,
                ColumnLineage.transformation_id == transformation_id,
                ColumnLineage.pipeline_id == pipeline_id,
            )
        ).first()

        if existing:
            # Update existing
            existing.lineage_type = lineage_type
            existing.transformation_expression = transformation_expression
            existing.confidence_score = confidence_score
            existing.dbt_run_id = dbt_run_id
            existing.updated_at = datetime.now(timezone.utc)
            self.db.commit()
            return existing

        # Create new
        lineage = ColumnLineage(
            source_database=source_database,
            source_schema=source_schema,
            source_table=source_table,
            source_column=source_column,
            target_database=target_database,
            target_schema=target_schema,
            target_table=target_table,
            target_column=target_column,
            lineage_type=lineage_type,
            transformation_expression=transformation_expression,
            transformation_id=transformation_id,
            pipeline_id=pipeline_id,
            dbt_run_id=dbt_run_id,
            organization_id=organization_id,
            confidence_score=confidence_score,
        )

        self.db.add(lineage)
        self.db.commit()
        self.db.refresh(lineage)

        return lineage

    def _create_or_update_column_metadata(
        self,
        dbt_project_id: int,
        model_name: str,
        column_name: str,
        description: Optional[str] = None,
        data_type: Optional[str] = None,
        tests: Optional[List[Dict]] = None,
        tags: Optional[List[str]] = None,
        meta: Optional[Dict] = None,
    ) -> DbtColumnMetadata:
        """Create or update dbt column metadata."""
        existing = self.db.query(DbtColumnMetadata).filter(
            and_(
                DbtColumnMetadata.dbt_project_id == dbt_project_id,
                DbtColumnMetadata.model_name == model_name,
                DbtColumnMetadata.column_name == column_name,
            )
        ).first()

        if existing:
            existing.description = description
            existing.data_type = data_type
            existing.tests = tests
            existing.tags = tags
            existing.meta = meta
            existing.updated_at = datetime.now(timezone.utc)
            self.db.commit()
            return existing

        metadata = DbtColumnMetadata(
            dbt_project_id=dbt_project_id,
            model_name=model_name,
            column_name=column_name,
            description=description,
            data_type=data_type,
            tests=tests,
            tags=tags,
            meta=meta,
        )

        self.db.add(metadata)
        self.db.commit()
        self.db.refresh(metadata)

        return metadata

    def get_column_lineage(
        self,
        table_name: str,
        organization_id: int,
        column_name: Optional[str] = None,
    ) -> List[ColumnLineage]:
        """
        Get all column lineage for a table (or specific column).

        Args:
            table_name: Table name to query
            organization_id: Organization ID for scoping
            column_name: Optional specific column

        Returns:
            List of ColumnLineage records
        """
        query = self.db.query(ColumnLineage).filter(
            and_(
                ColumnLineage.organization_id == organization_id,
                or_(
                    ColumnLineage.source_table == table_name,
                    ColumnLineage.target_table == table_name,
                ),
            )
        )

        if column_name:
            query = query.filter(
                or_(
                    ColumnLineage.source_column == column_name,
                    ColumnLineage.target_column == column_name,
                )
            )

        return query.all()

    def get_upstream_columns(
        self,
        table_name: str,
        column_name: str,
        organization_id: int,
        max_depth: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Trace column upstream to find all source columns.

        Args:
            table_name: Target table name
            column_name: Target column name
            organization_id: Organization ID for scoping
            max_depth: Maximum traversal depth

        Returns:
            List of upstream column information
        """
        visited: Set[Tuple[str, str]] = set()
        upstream = []

        self._trace_upstream_recursive(
            table_name=table_name,
            column_name=column_name,
            organization_id=organization_id,
            depth=0,
            max_depth=max_depth,
            visited=visited,
            results=upstream,
        )

        return upstream

    def _trace_upstream_recursive(
        self,
        table_name: str,
        column_name: str,
        organization_id: int,
        depth: int,
        max_depth: int,
        visited: Set[Tuple[str, str]],
        results: List[Dict[str, Any]],
    ) -> None:
        """Recursively trace upstream columns."""
        if depth >= max_depth:
            return

        key = (table_name, column_name)
        if key in visited:
            return
        visited.add(key)

        # Find all lineage where this column is the target
        lineages = self.db.query(ColumnLineage).filter(
            and_(
                ColumnLineage.organization_id == organization_id,
                ColumnLineage.target_table == table_name,
                ColumnLineage.target_column == column_name,
            )
        ).all()

        for lineage in lineages:
            result = {
                "table": lineage.source_table,
                "column": lineage.source_column,
                "schema": lineage.source_schema,
                "database": lineage.source_database,
                "lineage_type": lineage.lineage_type.value,
                "transformation": lineage.transformation_expression,
                "depth": depth + 1,
                "path": [
                    f"{table_name}.{column_name}",
                    f"{lineage.source_table}.{lineage.source_column}",
                ],
            }
            results.append(result)

            # Recurse upstream
            self._trace_upstream_recursive(
                table_name=lineage.source_table,
                column_name=lineage.source_column,
                organization_id=organization_id,
                depth=depth + 1,
                max_depth=max_depth,
                visited=visited,
                results=results,
            )

    def get_downstream_columns(
        self,
        table_name: str,
        column_name: str,
        organization_id: int,
        max_depth: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Trace column downstream to find all dependent columns.

        Args:
            table_name: Source table name
            column_name: Source column name
            organization_id: Organization ID for scoping
            max_depth: Maximum traversal depth

        Returns:
            List of downstream column information
        """
        visited: Set[Tuple[str, str]] = set()
        downstream = []

        self._trace_downstream_recursive(
            table_name=table_name,
            column_name=column_name,
            organization_id=organization_id,
            depth=0,
            max_depth=max_depth,
            visited=visited,
            results=downstream,
        )

        return downstream

    def _trace_downstream_recursive(
        self,
        table_name: str,
        column_name: str,
        organization_id: int,
        depth: int,
        max_depth: int,
        visited: Set[Tuple[str, str]],
        results: List[Dict[str, Any]],
    ) -> None:
        """Recursively trace downstream columns."""
        if depth >= max_depth:
            return

        key = (table_name, column_name)
        if key in visited:
            return
        visited.add(key)

        # Find all lineage where this column is the source
        lineages = self.db.query(ColumnLineage).filter(
            and_(
                ColumnLineage.organization_id == organization_id,
                ColumnLineage.source_table == table_name,
                ColumnLineage.source_column == column_name,
            )
        ).all()

        for lineage in lineages:
            result = {
                "table": lineage.target_table,
                "column": lineage.target_column,
                "schema": lineage.target_schema,
                "database": lineage.target_database,
                "lineage_type": lineage.lineage_type.value,
                "transformation": lineage.transformation_expression,
                "depth": depth + 1,
                "path": [
                    f"{table_name}.{column_name}",
                    f"{lineage.target_table}.{lineage.target_column}",
                ],
            }
            results.append(result)

            # Recurse downstream
            self._trace_downstream_recursive(
                table_name=lineage.target_table,
                column_name=lineage.target_column,
                organization_id=organization_id,
                depth=depth + 1,
                max_depth=max_depth,
                visited=visited,
                results=results,
            )

    def get_column_impact_analysis(
        self,
        table_name: str,
        column_name: str,
        organization_id: int,
        max_depth: int = 10,
    ) -> Dict[str, Any]:
        """
        Perform impact analysis for a column.

        Shows all downstream columns and pipelines that would be affected
        if this column changes.

        Args:
            table_name: Source table name
            column_name: Source column name
            organization_id: Organization ID for scoping
            max_depth: Maximum traversal depth

        Returns:
            Impact analysis results
        """
        downstream = self.get_downstream_columns(
            table_name=table_name,
            column_name=column_name,
            organization_id=organization_id,
            max_depth=max_depth,
        )

        # Get affected pipelines
        affected_pipeline_ids = set()
        affected_transformation_ids = set()

        for col in downstream:
            lineages = self.db.query(ColumnLineage).filter(
                and_(
                    ColumnLineage.organization_id == organization_id,
                    ColumnLineage.target_table == col["table"],
                    ColumnLineage.target_column == col["column"],
                )
            ).all()

            for lineage in lineages:
                if lineage.pipeline_id:
                    affected_pipeline_ids.add(lineage.pipeline_id)
                if lineage.transformation_id:
                    affected_transformation_ids.add(lineage.transformation_id)

        # Get pipeline details
        affected_pipelines = []
        if affected_pipeline_ids:
            pipelines = self.db.query(Pipeline).filter(
                Pipeline.id.in_(affected_pipeline_ids)
            ).all()
            affected_pipelines = [
                {"id": p.id, "name": p.name, "is_active": p.is_active}
                for p in pipelines
            ]

        # Group downstream by table
        tables_affected = {}
        for col in downstream:
            table = col["table"]
            if table not in tables_affected:
                tables_affected[table] = []
            tables_affected[table].append(col["column"])

        return {
            "source": {
                "table": table_name,
                "column": column_name,
            },
            "summary": {
                "total_downstream_columns": len(downstream),
                "tables_affected": len(tables_affected),
                "pipelines_affected": len(affected_pipeline_ids),
                "transformations_affected": len(affected_transformation_ids),
                "max_depth_reached": max_depth,
            },
            "downstream_columns": downstream,
            "tables_affected": tables_affected,
            "affected_pipelines": affected_pipelines,
            "affected_transformation_ids": list(affected_transformation_ids),
        }

    def get_table_column_lineage_graph(
        self,
        table_name: str,
        organization_id: int,
    ) -> Dict[str, Any]:
        """
        Get column lineage graph for a table.

        Returns nodes (columns) and edges (lineage) suitable for visualization.

        Args:
            table_name: Table name
            organization_id: Organization ID for scoping

        Returns:
            Graph structure with nodes and edges
        """
        lineages = self.get_column_lineage(
            table_name=table_name,
            organization_id=organization_id,
        )

        nodes = {}
        edges = []

        for lineage in lineages:
            # Add source column node
            source_id = f"{lineage.source_table}.{lineage.source_column}"
            if source_id not in nodes:
                nodes[source_id] = {
                    "id": source_id,
                    "table": lineage.source_table,
                    "column": lineage.source_column,
                    "schema": lineage.source_schema,
                    "database": lineage.source_database,
                    "type": "source" if lineage.source_table != table_name else "target",
                }

            # Add target column node
            target_id = f"{lineage.target_table}.{lineage.target_column}"
            if target_id not in nodes:
                nodes[target_id] = {
                    "id": target_id,
                    "table": lineage.target_table,
                    "column": lineage.target_column,
                    "schema": lineage.target_schema,
                    "database": lineage.target_database,
                    "type": "target" if lineage.target_table == table_name else "downstream",
                }

            # Add edge
            edges.append({
                "id": str(lineage.id),
                "source": source_id,
                "target": target_id,
                "lineage_type": lineage.lineage_type.value,
                "transformation": lineage.transformation_expression,
                "confidence": lineage.confidence_score,
            })

        return {
            "nodes": list(nodes.values()),
            "edges": edges,
            "table": table_name,
        }

    def delete_lineage_for_transformation(
        self,
        transformation_id: int,
    ) -> int:
        """
        Delete all lineage records for a transformation.

        Args:
            transformation_id: Transformation ID

        Returns:
            Number of records deleted
        """
        deleted = self.db.query(ColumnLineage).filter(
            ColumnLineage.transformation_id == transformation_id
        ).delete()
        self.db.commit()
        return deleted

    def delete_lineage_for_pipeline(
        self,
        pipeline_id: int,
    ) -> int:
        """
        Delete all lineage records for a pipeline.

        Args:
            pipeline_id: Pipeline ID

        Returns:
            Number of records deleted
        """
        deleted = self.db.query(ColumnLineage).filter(
            ColumnLineage.pipeline_id == pipeline_id
        ).delete()
        self.db.commit()
        return deleted

    def refresh_transformation_lineage(
        self,
        transformation_id: int,
        organization_id: int,
        dialect: str = "postgres",
    ) -> List[ColumnLineage]:
        """
        Refresh column lineage for a transformation.

        Deletes existing lineage and re-parses the SQL.

        Args:
            transformation_id: Transformation ID
            organization_id: Organization ID
            dialect: SQL dialect

        Returns:
            New lineage records
        """
        # Get transformation
        transformation = self.db.query(SQLTransformation).filter(
            SQLTransformation.id == transformation_id
        ).first()

        if not transformation:
            raise ValueError(f"Transformation {transformation_id} not found")

        # Delete existing lineage
        self.delete_lineage_for_transformation(transformation_id)

        # Re-record lineage
        return self.record_transformation_lineage(
            transformation=transformation,
            organization_id=organization_id,
            dialect=dialect,
        )
