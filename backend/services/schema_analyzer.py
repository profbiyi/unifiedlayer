"""
Schema Analyzer Service.

Analyzes raw table schemas from the destination for AI-powered modeling.
Connects to destinations (PostgreSQL, Snowflake, BigQuery, etc.), extracts
table structures, samples data, and detects relationships.
"""
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)


@dataclass
class ColumnInfo:
    """Information about a table column."""
    name: str
    data_type: str
    nullable: bool
    default: Optional[str] = None
    primary_key: bool = False
    foreign_key: Optional[str] = None  # "table.column" format
    description: Optional[str] = None


@dataclass
class TableSchema:
    """Schema information for a single table."""
    name: str
    schema_name: str
    columns: List[ColumnInfo]
    row_count: int = 0
    sample_data: List[Dict[str, Any]] = field(default_factory=list)
    primary_keys: List[str] = field(default_factory=list)
    foreign_keys: List[Dict[str, str]] = field(default_factory=list)
    description: Optional[str] = None


@dataclass
class SchemaContext:
    """Complete schema context for AI modeling."""
    tables: List[TableSchema]
    destination_type: str
    dataset_name: str
    detected_relationships: List[Dict[str, str]]
    total_tables: int
    total_columns: int


class SchemaAnalyzer:
    """
    Service for analyzing schemas from destination databases.

    Extracts table structures, samples data, and detects relationships
    to provide context for AI-powered dimensional modeling.
    """

    def __init__(self):
        self.engine: Optional[Engine] = None
        self.destination_type: str = ""

    def connect(self, destination_config: Dict[str, Any], destination_type: str) -> None:
        """
        Connect to the destination database.

        Args:
            destination_config: Destination configuration with credentials
            destination_type: Type of destination (postgres, snowflake, bigquery, etc.)
        """
        self.destination_type = destination_type
        connection_string = self._build_connection_string(destination_config, destination_type)

        logger.info(f"Connecting to {destination_type} destination")
        self.engine = create_engine(connection_string)

    def _build_connection_string(
        self,
        config: Dict[str, Any],
        destination_type: str
    ) -> str:
        """Build connection string based on destination type."""
        if destination_type == "postgres":
            host = config.get("host", "localhost")
            port = config.get("port", 5432)
            database = config.get("database", "")
            username = config.get("username") or config.get("user", "")
            password = config.get("password", "")
            sslmode = config.get("sslmode", "prefer")

            # Handle Neon PostgreSQL (use unpooled endpoint)
            if "neon.tech" in host:
                host = host.replace("-pooler", "")
                return f"postgresql://{username}:{password}@{host}:{port}/{database}?sslmode=require"

            return f"postgresql://{username}:{password}@{host}:{port}/{database}?sslmode={sslmode}"

        elif destination_type == "snowflake":
            account = config.get("host") or config.get("account", "")
            if account.endswith(".snowflakecomputing.com"):
                account = account.replace(".snowflakecomputing.com", "")

            username = config.get("username") or config.get("user", "")
            password = config.get("password", "")
            database = config.get("database", "")
            warehouse = config.get("warehouse", "")
            schema = config.get("schema", "PUBLIC")

            return (
                f"snowflake://{username}:{password}@{account}/{database}/{schema}"
                f"?warehouse={warehouse}"
            )

        elif destination_type == "bigquery":
            project_id = config.get("project_id", "")
            config.get("credentials_json", {})
            # BigQuery connection via SQLAlchemy requires google-cloud-bigquery
            # Using project ID in connection string
            return f"bigquery://{project_id}"

        elif destination_type == "duckdb":
            database_path = config.get("database_path", ":memory:")
            return f"duckdb:///{database_path}"

        elif destination_type == "redshift":
            host = config.get("host", "")
            port = config.get("port", 5439)
            database = config.get("database", "")
            username = config.get("username") or config.get("user", "")
            password = config.get("password", "")

            return f"redshift+psycopg2://{username}:{password}@{host}:{port}/{database}"

        else:
            raise ValueError(f"Unsupported destination type: {destination_type}")

    def analyze_tables(
        self,
        tables: Optional[List[str]] = None,
        schema_name: Optional[str] = None,
        sample_rows: int = 5
    ) -> SchemaContext:
        """
        Analyze table schemas from the destination.

        Args:
            tables: Specific tables to analyze (None = all tables)
            schema_name: Schema/dataset to analyze
            sample_rows: Number of rows to sample from each table

        Returns:
            SchemaContext with complete schema information
        """
        if not self.engine:
            raise RuntimeError("Not connected to destination. Call connect() first.")

        inspector = inspect(self.engine)

        # Get schema/dataset name
        if not schema_name:
            schema_name = self._get_default_schema()

        # Get list of tables to analyze
        available_tables = inspector.get_table_names(schema=schema_name)
        logger.info(f"Found {len(available_tables)} tables in schema '{schema_name}'")

        if tables:
            # Filter to requested tables
            target_tables = [t for t in tables if t in available_tables]
        else:
            target_tables = available_tables

        if not target_tables:
            logger.warning("No tables found to analyze")
            return SchemaContext(
                tables=[],
                destination_type=self.destination_type,
                dataset_name=schema_name,
                detected_relationships=[],
                total_tables=0,
                total_columns=0,
            )

        # Analyze each table
        table_schemas: List[TableSchema] = []
        total_columns = 0

        for table_name in target_tables:
            logger.info(f"Analyzing table: {table_name}")
            table_schema = self._analyze_table(
                inspector, table_name, schema_name, sample_rows
            )
            table_schemas.append(table_schema)
            total_columns += len(table_schema.columns)

        # Detect relationships between tables
        relationships = self._detect_relationships(table_schemas)

        return SchemaContext(
            tables=table_schemas,
            destination_type=self.destination_type,
            dataset_name=schema_name,
            detected_relationships=relationships,
            total_tables=len(table_schemas),
            total_columns=total_columns,
        )

    def _get_default_schema(self) -> str:
        """Get default schema based on destination type."""
        if self.destination_type in ("postgres", "redshift"):
            return "public"
        elif self.destination_type == "snowflake":
            return "PUBLIC"
        elif self.destination_type == "bigquery":
            return "default"
        elif self.destination_type == "duckdb":
            return "main"
        return "public"

    def _analyze_table(
        self,
        inspector,
        table_name: str,
        schema_name: str,
        sample_rows: int
    ) -> TableSchema:
        """Analyze a single table and return its schema."""
        # Get columns
        columns_info = inspector.get_columns(table_name, schema=schema_name)
        pk_constraint = inspector.get_pk_constraint(table_name, schema=schema_name)
        fk_constraints = inspector.get_foreign_keys(table_name, schema=schema_name)

        primary_keys = pk_constraint.get("constrained_columns", []) if pk_constraint else []

        # Build foreign key lookup
        fk_lookup: Dict[str, str] = {}
        fk_list: List[Dict[str, str]] = []
        for fk in fk_constraints:
            for i, col in enumerate(fk.get("constrained_columns", [])):
                referred_table = fk.get("referred_table", "")
                referred_col = fk["referred_columns"][i] if i < len(fk.get("referred_columns", [])) else ""
                fk_lookup[col] = f"{referred_table}.{referred_col}"
                fk_list.append({
                    "from_column": col,
                    "to_table": referred_table,
                    "to_column": referred_col,
                })

        # Build column list
        columns: List[ColumnInfo] = []
        for col in columns_info:
            col_name = col["name"]
            columns.append(ColumnInfo(
                name=col_name,
                data_type=str(col["type"]),
                nullable=col.get("nullable", True),
                default=str(col.get("default")) if col.get("default") else None,
                primary_key=col_name in primary_keys,
                foreign_key=fk_lookup.get(col_name),
                description=col.get("comment"),
            ))

        # Get row count
        row_count = self._get_row_count(table_name, schema_name)

        # Get sample data
        sample_data = self._get_sample_data(table_name, schema_name, sample_rows)

        return TableSchema(
            name=table_name,
            schema_name=schema_name,
            columns=columns,
            row_count=row_count,
            sample_data=sample_data,
            primary_keys=primary_keys,
            foreign_keys=fk_list,
        )

    def _get_row_count(self, table_name: str, schema_name: str) -> int:
        """Get approximate row count for a table."""
        try:
            with self.engine.connect() as conn:
                # Use quoted identifiers
                query = text(f'SELECT COUNT(*) FROM "{schema_name}"."{table_name}"')
                result = conn.execute(query)
                return result.scalar() or 0
        except Exception as e:
            logger.warning(f"Could not get row count for {table_name}: {e}")
            return 0

    def _get_sample_data(
        self,
        table_name: str,
        schema_name: str,
        limit: int
    ) -> List[Dict[str, Any]]:
        """Get sample rows from a table."""
        try:
            with self.engine.connect() as conn:
                query = text(f'SELECT * FROM "{schema_name}"."{table_name}" LIMIT {limit}')
                result = conn.execute(query)
                rows = result.fetchall()
                columns = result.keys()

                sample_data = []
                for row in rows:
                    row_dict = {}
                    for i, col in enumerate(columns):
                        value = row[i]
                        # Convert to JSON-serializable format
                        if value is not None:
                            row_dict[col] = self._serialize_value(value)
                        else:
                            row_dict[col] = None
                    sample_data.append(row_dict)

                return sample_data

        except Exception as e:
            logger.warning(f"Could not get sample data for {table_name}: {e}")
            return []

    def _serialize_value(self, value: Any) -> Any:
        """Convert value to JSON-serializable format."""
        from datetime import date, datetime
        from decimal import Decimal
        import uuid as uuid_module

        if isinstance(value, (datetime, date)):
            return value.isoformat()
        elif isinstance(value, Decimal):
            return float(value)
        elif isinstance(value, uuid_module.UUID):
            return str(value)
        elif isinstance(value, bytes):
            return value.hex()
        elif isinstance(value, (list, tuple)):
            return [self._serialize_value(v) for v in value]
        elif isinstance(value, dict):
            return {k: self._serialize_value(v) for k, v in value.items()}
        else:
            return value

    def _detect_relationships(
        self,
        tables: List[TableSchema]
    ) -> List[Dict[str, str]]:
        """
        Detect relationships between tables based on:
        1. Explicit foreign keys
        2. Naming conventions (e.g., user_id -> users.id)
        3. Column name patterns

        Returns list of relationships.
        """
        relationships: List[Dict[str, str]] = []
        table_names = {t.name for t in tables}
        pk_lookup: Dict[str, List[str]] = {t.name: t.primary_keys for t in tables}

        for table in tables:
            # Add explicit foreign keys
            for fk in table.foreign_keys:
                relationships.append({
                    "from_table": table.name,
                    "from_column": fk["from_column"],
                    "to_table": fk["to_table"],
                    "to_column": fk["to_column"],
                    "type": "explicit_fk",
                })

            # Detect implicit relationships via naming conventions
            for col in table.columns:
                # Skip if already has explicit FK
                if col.foreign_key:
                    continue

                # Pattern 1: column_name ends with _id
                if col.name.endswith("_id"):
                    potential_table = col.name[:-3]  # Remove _id
                    # Check plural form
                    potential_tables = [
                        potential_table,
                        potential_table + "s",
                        potential_table + "es",
                    ]

                    for pt in potential_tables:
                        if pt in table_names and pt != table.name:
                            # Found potential relationship
                            target_pks = pk_lookup.get(pt, ["id"])
                            target_pk = target_pks[0] if target_pks else "id"
                            relationships.append({
                                "from_table": table.name,
                                "from_column": col.name,
                                "to_table": pt,
                                "to_column": target_pk,
                                "type": "inferred_by_naming",
                                "confidence": "medium",
                            })
                            break

        return relationships

    def get_schema_summary(self, context: SchemaContext) -> str:
        """
        Generate a text summary of the schema for AI prompts.

        Args:
            context: SchemaContext from analyze_tables()

        Returns:
            Human-readable schema summary
        """
        lines = [
            "## Database Schema Summary",
            f"- Destination: {context.destination_type}",
            f"- Dataset/Schema: {context.dataset_name}",
            f"- Total Tables: {context.total_tables}",
            f"- Total Columns: {context.total_columns}",
            "",
            "## Tables",
        ]

        for table in context.tables:
            lines.append(f"\n### {table.name}")
            lines.append(f"Rows: {table.row_count:,}")

            lines.append("Columns:")
            for col in table.columns:
                pk_marker = " [PK]" if col.primary_key else ""
                fk_marker = f" [FK -> {col.foreign_key}]" if col.foreign_key else ""
                nullable = "" if col.nullable else " NOT NULL"
                lines.append(f"  - {col.name}: {col.data_type}{pk_marker}{fk_marker}{nullable}")

            if table.sample_data:
                lines.append("Sample Data (first row):")
                sample = table.sample_data[0]
                for key, value in list(sample.items())[:5]:  # First 5 columns
                    lines.append(f"  - {key}: {value}")
                if len(sample) > 5:
                    lines.append(f"  ... and {len(sample) - 5} more columns")

        if context.detected_relationships:
            lines.append("\n## Detected Relationships")
            for rel in context.detected_relationships:
                rel_type = rel.get("type", "unknown")
                confidence = f" ({rel.get('confidence', 'high')})" if rel_type == "inferred_by_naming" else ""
                lines.append(
                    f"  - {rel['from_table']}.{rel['from_column']} -> "
                    f"{rel['to_table']}.{rel['to_column']}{confidence}"
                )

        return "\n".join(lines)

    def close(self) -> None:
        """Close the database connection."""
        if self.engine:
            self.engine.dispose()
            self.engine = None
            logger.info("Database connection closed")


def get_schema_analyzer() -> SchemaAnalyzer:
    """Factory function for SchemaAnalyzer."""
    return SchemaAnalyzer()
