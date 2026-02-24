"""
dbt Manifest Parser.

Parses dbt manifest.json to extract column-level metadata, lineage,
and documentation for integration with the column lineage system.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Set
import json
import logging

logger = logging.getLogger(__name__)


@dataclass
class DbtColumn:
    """Represents a column from dbt manifest."""
    name: str
    description: Optional[str] = None
    data_type: Optional[str] = None
    meta: Optional[Dict[str, Any]] = None
    tags: List[str] = field(default_factory=list)
    tests: List[Dict[str, Any]] = field(default_factory=list)
    quote: Optional[bool] = None
    constraints: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class DbtModel:
    """Represents a model from dbt manifest."""
    unique_id: str
    name: str
    schema: str
    database: Optional[str] = None
    alias: Optional[str] = None
    description: Optional[str] = None
    columns: Dict[str, DbtColumn] = field(default_factory=dict)
    depends_on: List[str] = field(default_factory=list)
    meta: Optional[Dict[str, Any]] = None
    tags: List[str] = field(default_factory=list)
    materialized: Optional[str] = None
    raw_code: Optional[str] = None
    compiled_code: Optional[str] = None


@dataclass
class DbtSource:
    """Represents a source from dbt manifest."""
    unique_id: str
    name: str
    source_name: str
    schema: str
    database: Optional[str] = None
    description: Optional[str] = None
    columns: Dict[str, DbtColumn] = field(default_factory=dict)
    meta: Optional[Dict[str, Any]] = None
    tags: List[str] = field(default_factory=list)


@dataclass
class DbtColumnLineage:
    """Represents column-level lineage from dbt."""
    source_model: str
    source_column: str
    target_model: str
    target_column: str
    transformation: Optional[str] = None
    confidence: int = 100


class DbtManifestParser:
    """
    Parser for dbt manifest.json files.

    Extracts models, sources, columns, and lineage information
    from the dbt manifest for integration with column-level lineage tracking.
    """

    def __init__(self, manifest: Dict[str, Any]):
        """
        Initialize parser with manifest data.

        Args:
            manifest: Parsed manifest.json content
        """
        self.manifest = manifest
        self.metadata = manifest.get("metadata", {})
        self.nodes = manifest.get("nodes", {})
        self.sources = manifest.get("sources", {})
        self.parent_map = manifest.get("parent_map", {})
        self.child_map = manifest.get("child_map", {})

        # Parse models and sources
        self._models: Dict[str, DbtModel] = {}
        self._sources: Dict[str, DbtSource] = {}
        self._parse_nodes()
        self._parse_sources()

    @classmethod
    def from_json(cls, json_str: str) -> "DbtManifestParser":
        """
        Create parser from JSON string.

        Args:
            json_str: manifest.json content as string

        Returns:
            DbtManifestParser instance
        """
        manifest = json.loads(json_str)
        return cls(manifest)

    @classmethod
    def from_file(cls, file_path: str) -> "DbtManifestParser":
        """
        Create parser from file path.

        Args:
            file_path: Path to manifest.json

        Returns:
            DbtManifestParser instance
        """
        with open(file_path, "r") as f:
            manifest = json.load(f)
        return cls(manifest)

    def _parse_nodes(self) -> None:
        """Parse model nodes from manifest."""
        for unique_id, node in self.nodes.items():
            if node.get("resource_type") != "model":
                continue

            columns = {}
            for col_name, col_data in node.get("columns", {}).items():
                columns[col_name] = DbtColumn(
                    name=col_name,
                    description=col_data.get("description"),
                    data_type=col_data.get("data_type"),
                    meta=col_data.get("meta"),
                    tags=col_data.get("tags", []),
                    quote=col_data.get("quote"),
                    constraints=col_data.get("constraints", []),
                )

            # Extract tests for columns
            for test_id in self._get_column_tests(unique_id):
                test_node = self.nodes.get(test_id, {})
                if test_node.get("resource_type") == "test":
                    column_name = test_node.get("column_name")
                    if column_name and column_name in columns:
                        columns[column_name].tests.append({
                            "name": test_node.get("name"),
                            "test_metadata": test_node.get("test_metadata"),
                        })

            self._models[unique_id] = DbtModel(
                unique_id=unique_id,
                name=node.get("name"),
                schema=node.get("schema"),
                database=node.get("database"),
                alias=node.get("alias"),
                description=node.get("description"),
                columns=columns,
                depends_on=node.get("depends_on", {}).get("nodes", []),
                meta=node.get("meta"),
                tags=node.get("tags", []),
                materialized=node.get("config", {}).get("materialized"),
                raw_code=node.get("raw_code") or node.get("raw_sql"),
                compiled_code=node.get("compiled_code") or node.get("compiled_sql"),
            )

    def _parse_sources(self) -> None:
        """Parse source nodes from manifest."""
        for unique_id, source in self.sources.items():
            columns = {}
            for col_name, col_data in source.get("columns", {}).items():
                columns[col_name] = DbtColumn(
                    name=col_name,
                    description=col_data.get("description"),
                    data_type=col_data.get("data_type"),
                    meta=col_data.get("meta"),
                    tags=col_data.get("tags", []),
                )

            self._sources[unique_id] = DbtSource(
                unique_id=unique_id,
                name=source.get("name"),
                source_name=source.get("source_name"),
                schema=source.get("schema"),
                database=source.get("database"),
                description=source.get("description"),
                columns=columns,
                meta=source.get("meta"),
                tags=source.get("tags", []),
            )

    def _get_column_tests(self, model_id: str) -> List[str]:
        """Get test node IDs for a model's columns."""
        tests = []
        for child_id in self.child_map.get(model_id, []):
            if child_id.startswith("test."):
                tests.append(child_id)
        return tests

    def get_models(self) -> Dict[str, DbtModel]:
        """Get all parsed models."""
        return self._models

    def get_sources(self) -> Dict[str, DbtSource]:
        """Get all parsed sources."""
        return self._sources

    def get_model(self, model_name: str) -> Optional[DbtModel]:
        """
        Get a model by name.

        Args:
            model_name: Model name (without unique_id prefix)

        Returns:
            DbtModel if found, None otherwise
        """
        for model in self._models.values():
            if model.name == model_name:
                return model
        return None

    def get_model_by_id(self, unique_id: str) -> Optional[DbtModel]:
        """Get a model by its unique ID."""
        return self._models.get(unique_id)

    def get_source(self, source_name: str, table_name: str) -> Optional[DbtSource]:
        """
        Get a source by source name and table name.

        Args:
            source_name: Source name (e.g., "raw_data")
            table_name: Table name within the source

        Returns:
            DbtSource if found, None otherwise
        """
        for source in self._sources.values():
            if source.source_name == source_name and source.name == table_name:
                return source
        return None

    def get_model_columns(self, model_name: str) -> Dict[str, DbtColumn]:
        """
        Get columns for a specific model.

        Args:
            model_name: Model name

        Returns:
            Dictionary of column name to DbtColumn
        """
        model = self.get_model(model_name)
        if model:
            return model.columns
        return {}

    def get_model_dependencies(self, model_name: str) -> List[str]:
        """
        Get upstream dependencies for a model.

        Args:
            model_name: Model name

        Returns:
            List of upstream model/source unique IDs
        """
        model = self.get_model(model_name)
        if model:
            return model.depends_on
        return []

    def get_model_dependents(self, model_name: str) -> List[str]:
        """
        Get downstream dependents of a model.

        Args:
            model_name: Model name

        Returns:
            List of downstream model unique IDs
        """
        model = self.get_model(model_name)
        if model:
            return self.child_map.get(model.unique_id, [])
        return []

    def extract_column_lineage(
        self,
        model_name: str,
        dialect: str = "postgres",
    ) -> List[DbtColumnLineage]:
        """
        Extract column-level lineage for a model by parsing its compiled SQL.

        Args:
            model_name: Model name to analyze
            dialect: SQL dialect for parsing

        Returns:
            List of column lineage relationships
        """
        from backend.services.column_lineage_parser import SQLColumnLineageParser

        model = self.get_model(model_name)
        if not model or not model.compiled_code:
            return []

        # Parse the compiled SQL
        parser = SQLColumnLineageParser(
            dialect=dialect,
            default_schema=model.schema,
            default_database=model.database,
        )

        target_table = model.alias or model.name
        mappings = parser.parse_sql(
            model.compiled_code,
            target_table=target_table,
            target_schema=model.schema,
            target_database=model.database,
        )

        # Convert to DbtColumnLineage
        lineage = []
        for mapping in mappings:
            for source_col in mapping.source_columns:
                # Resolve source table to model/source
                source_model = self._resolve_table_to_model(
                    source_col.source_table,
                    source_col.source_schema,
                )

                lineage.append(DbtColumnLineage(
                    source_model=source_model or source_col.source_table,
                    source_column=source_col.source_column,
                    target_model=model_name,
                    target_column=mapping.target_column,
                    transformation=mapping.transformation_expression,
                    confidence=mapping.confidence_score,
                ))

        return lineage

    def _resolve_table_to_model(
        self,
        table_name: str,
        schema: Optional[str],
    ) -> Optional[str]:
        """
        Resolve a table name to a model or source name.

        Args:
            table_name: Table name from SQL
            schema: Schema name

        Returns:
            Model name if found, None otherwise
        """
        # Check models
        for model in self._models.values():
            model_table = model.alias or model.name
            if model_table == table_name:
                if schema is None or model.schema == schema:
                    return model.name

        # Check sources
        for source in self._sources.values():
            if source.name == table_name:
                if schema is None or source.schema == schema:
                    return f"source.{source.source_name}.{source.name}"

        return None

    def get_all_column_metadata(self) -> List[Dict[str, Any]]:
        """
        Get all column metadata from models and sources.

        Returns:
            List of column metadata dictionaries
        """
        metadata = []

        # From models
        for model in self._models.values():
            for col_name, column in model.columns.items():
                metadata.append({
                    "model_type": "model",
                    "model_name": model.name,
                    "column_name": col_name,
                    "description": column.description,
                    "data_type": column.data_type,
                    "tests": column.tests,
                    "tags": column.tags,
                    "meta": column.meta,
                    "schema": model.schema,
                    "database": model.database,
                })

        # From sources
        for source in self._sources.values():
            for col_name, column in source.columns.items():
                metadata.append({
                    "model_type": "source",
                    "model_name": f"{source.source_name}.{source.name}",
                    "column_name": col_name,
                    "description": column.description,
                    "data_type": column.data_type,
                    "tests": [],
                    "tags": column.tags,
                    "meta": column.meta,
                    "schema": source.schema,
                    "database": source.database,
                })

        return metadata

    def get_column_tests_summary(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get a summary of all column tests by model.

        Returns:
            Dictionary mapping model name to list of column tests
        """
        summary = {}

        for model in self._models.values():
            tests = []
            for col_name, column in model.columns.items():
                for test in column.tests:
                    tests.append({
                        "column": col_name,
                        "test_name": test.get("name"),
                        "test_metadata": test.get("test_metadata"),
                    })
            if tests:
                summary[model.name] = tests

        return summary

    def build_full_lineage_graph(
        self, dialect: str = "postgres"
    ) -> Dict[str, Any]:
        """
        Build a complete column lineage graph for all models.

        Args:
            dialect: SQL dialect for parsing

        Returns:
            Dictionary with nodes (columns) and edges (lineage)
        """
        nodes = []
        edges = []
        processed_models: Set[str] = set()

        for model in self._models.values():
            # Add model columns as nodes
            for col_name, column in model.columns.items():
                nodes.append({
                    "id": f"{model.name}.{col_name}",
                    "model": model.name,
                    "column": col_name,
                    "type": "model",
                    "description": column.description,
                    "data_type": column.data_type,
                })

            # Extract and add lineage edges
            if model.name not in processed_models:
                lineage = self.extract_column_lineage(model.name, dialect)
                for lin in lineage:
                    edges.append({
                        "source": f"{lin.source_model}.{lin.source_column}",
                        "target": f"{lin.target_model}.{lin.target_column}",
                        "transformation": lin.transformation,
                        "confidence": lin.confidence,
                    })
                processed_models.add(model.name)

        # Add source columns as nodes
        for source in self._sources.values():
            source_name = f"source.{source.source_name}.{source.name}"
            for col_name, column in source.columns.items():
                nodes.append({
                    "id": f"{source_name}.{col_name}",
                    "model": source_name,
                    "column": col_name,
                    "type": "source",
                    "description": column.description,
                    "data_type": column.data_type,
                })

        return {
            "nodes": nodes,
            "edges": edges,
            "metadata": {
                "model_count": len(self._models),
                "source_count": len(self._sources),
                "total_columns": len(nodes),
                "total_edges": len(edges),
            },
        }


def parse_dbt_manifest(
    manifest_json: str,
    extract_lineage: bool = True,
    dialect: str = "postgres",
) -> Dict[str, Any]:
    """
    Convenience function to parse dbt manifest and extract all metadata.

    Args:
        manifest_json: manifest.json content as string
        extract_lineage: Whether to extract column lineage
        dialect: SQL dialect for lineage parsing

    Returns:
        Dictionary with models, sources, columns, and optional lineage
    """
    parser = DbtManifestParser.from_json(manifest_json)

    result = {
        "models": {
            name: {
                "name": m.name,
                "schema": m.schema,
                "database": m.database,
                "description": m.description,
                "columns": {
                    col_name: {
                        "name": col.name,
                        "description": col.description,
                        "data_type": col.data_type,
                        "tests": col.tests,
                    }
                    for col_name, col in m.columns.items()
                },
                "depends_on": m.depends_on,
                "materialized": m.materialized,
            }
            for name, m in parser.get_models().items()
        },
        "sources": {
            name: {
                "name": s.name,
                "source_name": s.source_name,
                "schema": s.schema,
                "database": s.database,
                "description": s.description,
                "columns": {
                    col_name: {
                        "name": col.name,
                        "description": col.description,
                        "data_type": col.data_type,
                    }
                    for col_name, col in s.columns.items()
                },
            }
            for name, s in parser.get_sources().items()
        },
        "column_metadata": parser.get_all_column_metadata(),
        "column_tests": parser.get_column_tests_summary(),
    }

    if extract_lineage:
        result["lineage_graph"] = parser.build_full_lineage_graph(dialect)

    return result
