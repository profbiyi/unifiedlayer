"""
SQL Column Lineage Parser.

Parses SQL SELECT statements to extract column-level lineage information
using the sqlglot library. Handles aliases, expressions, JOINs, subqueries,
and various SQL constructs.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple, Any
import logging

try:
    import sqlglot
    from sqlglot import exp
    from sqlglot.optimizer import qualify, optimize
    from sqlglot.optimizer.scope import build_scope
except ImportError:
    raise ImportError(
        "sqlglot is required for column lineage parsing. "
        "Install it with: pip install sqlglot"
    )

from backend.models.column_lineage import ColumnLineageType

logger = logging.getLogger(__name__)


@dataclass
class ColumnDependency:
    """Represents a column dependency extracted from SQL."""
    source_table: str
    source_column: str
    source_schema: Optional[str] = None
    source_database: Optional[str] = None

    @property
    def fqn(self) -> str:
        """Return fully qualified name."""
        parts = [p for p in [
            self.source_database,
            self.source_schema,
            self.source_table,
            self.source_column
        ] if p]
        return ".".join(parts)


@dataclass
class ColumnLineageMapping:
    """Represents a column lineage mapping from source to target."""
    target_table: str
    target_column: str
    target_schema: Optional[str] = None
    target_database: Optional[str] = None
    source_columns: List[ColumnDependency] = field(default_factory=list)
    lineage_type: ColumnLineageType = ColumnLineageType.DIRECT
    transformation_expression: Optional[str] = None
    confidence_score: int = 100

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            "target_table": self.target_table,
            "target_column": self.target_column,
            "target_schema": self.target_schema,
            "target_database": self.target_database,
            "source_columns": [
                {
                    "source_table": sc.source_table,
                    "source_column": sc.source_column,
                    "source_schema": sc.source_schema,
                    "source_database": sc.source_database,
                }
                for sc in self.source_columns
            ],
            "lineage_type": self.lineage_type.value,
            "transformation_expression": self.transformation_expression,
            "confidence_score": self.confidence_score,
        }


class SQLColumnLineageParser:
    """
    Parser for extracting column-level lineage from SQL statements.

    Uses sqlglot for SQL parsing and analysis. Supports:
    - SELECT statements with column aliases
    - Expressions and functions
    - JOINs (INNER, LEFT, RIGHT, FULL, CROSS)
    - Subqueries and CTEs
    - UNION, INTERSECT, EXCEPT
    - Aggregate functions
    - Window functions
    - CASE expressions
    """

    def __init__(
        self,
        dialect: str = "postgres",
        default_schema: Optional[str] = None,
        default_database: Optional[str] = None,
    ):
        """
        Initialize the parser.

        Args:
            dialect: SQL dialect (postgres, bigquery, snowflake, etc.)
            default_schema: Default schema name for unqualified tables
            default_database: Default database name for unqualified tables
        """
        self.dialect = dialect
        self.default_schema = default_schema
        self.default_database = default_database

    def parse_sql(
        self,
        sql: str,
        target_table: Optional[str] = None,
        target_schema: Optional[str] = None,
        target_database: Optional[str] = None,
    ) -> List[ColumnLineageMapping]:
        """
        Parse SQL statement and extract column lineage.

        Args:
            sql: SQL statement to parse
            target_table: Target table name (for CREATE TABLE AS, INSERT INTO)
            target_schema: Target schema name
            target_database: Target database name

        Returns:
            List of ColumnLineageMapping objects
        """
        try:
            # Parse the SQL
            parsed = sqlglot.parse_one(sql, dialect=self.dialect)

            if parsed is None:
                logger.warning("Failed to parse SQL: empty result")
                return []

            # Handle different statement types
            if isinstance(parsed, exp.Create):
                return self._parse_create_table_as(
                    parsed, target_table, target_schema, target_database
                )
            elif isinstance(parsed, exp.Insert):
                return self._parse_insert_statement(
                    parsed, target_schema, target_database
                )
            elif isinstance(parsed, exp.Select):
                return self._parse_select_statement(
                    parsed, target_table, target_schema, target_database
                )
            else:
                logger.debug(f"Unsupported statement type: {type(parsed)}")
                return []

        except Exception as e:
            logger.error(f"Error parsing SQL: {e}")
            return []

    def _parse_create_table_as(
        self,
        stmt: exp.Create,
        target_table: Optional[str],
        target_schema: Optional[str],
        target_database: Optional[str],
    ) -> List[ColumnLineageMapping]:
        """Parse CREATE TABLE AS SELECT statement."""
        # Extract target table from CREATE statement
        table_expr = stmt.find(exp.Table)
        if table_expr:
            target_table = target_table or table_expr.name
            target_schema = target_schema or table_expr.db
            target_database = target_database or table_expr.catalog

        # Get the SELECT part
        select_stmt = stmt.find(exp.Select)
        if select_stmt:
            return self._parse_select_statement(
                select_stmt, target_table, target_schema, target_database
            )
        return []

    def _parse_insert_statement(
        self,
        stmt: exp.Insert,
        target_schema: Optional[str],
        target_database: Optional[str],
    ) -> List[ColumnLineageMapping]:
        """Parse INSERT INTO ... SELECT statement."""
        # Extract target table
        table_expr = stmt.find(exp.Table)
        target_table = table_expr.name if table_expr else None
        target_schema = target_schema or (table_expr.db if table_expr else None)
        target_database = target_database or (table_expr.catalog if table_expr else None)

        # Get the SELECT part
        select_stmt = stmt.expression
        if isinstance(select_stmt, exp.Select):
            return self._parse_select_statement(
                select_stmt, target_table, target_schema, target_database
            )
        return []

    def _parse_select_statement(
        self,
        stmt: exp.Select,
        target_table: Optional[str],
        target_schema: Optional[str],
        target_database: Optional[str],
    ) -> List[ColumnLineageMapping]:
        """Parse SELECT statement and extract column lineage."""
        mappings = []

        # Build scope for qualified column resolution
        try:
            qualified_stmt = qualify.qualify(
                stmt,
                dialect=self.dialect,
                validate_qualify_columns=False,
            )
        except Exception as e:
            logger.debug(f"Could not qualify columns: {e}")
            qualified_stmt = stmt

        # Extract source tables
        source_tables = self._extract_source_tables(qualified_stmt)

        # Process each SELECT expression (column)
        for select_expr in qualified_stmt.expressions:
            mapping = self._process_select_expression(
                select_expr,
                source_tables,
                target_table,
                target_schema,
                target_database,
            )
            if mapping:
                mappings.append(mapping)

        return mappings

    def _extract_source_tables(
        self, stmt: exp.Expression
    ) -> Dict[str, Tuple[str, Optional[str], Optional[str]]]:
        """
        Extract source tables and their aliases from the statement.

        Returns:
            Dict mapping alias -> (table_name, schema, database)
        """
        tables = {}

        for table in stmt.find_all(exp.Table):
            table_name = table.name
            alias = table.alias or table_name
            schema = table.db or self.default_schema
            database = table.catalog or self.default_database

            tables[alias] = (table_name, schema, database)

        # Handle subqueries with aliases
        for subquery in stmt.find_all(exp.Subquery):
            if subquery.alias:
                tables[subquery.alias] = (subquery.alias, None, None)

        return tables

    def _process_select_expression(
        self,
        expr: exp.Expression,
        source_tables: Dict[str, Tuple[str, Optional[str], Optional[str]]],
        target_table: Optional[str],
        target_schema: Optional[str],
        target_database: Optional[str],
    ) -> Optional[ColumnLineageMapping]:
        """Process a single SELECT expression to extract lineage."""
        # Get target column name (alias or column name)
        target_column = self._get_target_column_name(expr)
        if not target_column:
            return None

        # Extract source columns from the expression
        source_columns, lineage_type, transformation = self._extract_source_columns(
            expr, source_tables
        )

        if not source_columns:
            # Handle constants or expressions with no column references
            return ColumnLineageMapping(
                target_table=target_table or "_unknown_",
                target_column=target_column,
                target_schema=target_schema,
                target_database=target_database,
                source_columns=[],
                lineage_type=ColumnLineageType.DERIVED,
                transformation_expression=expr.sql(dialect=self.dialect),
                confidence_score=50,
            )

        return ColumnLineageMapping(
            target_table=target_table or "_unknown_",
            target_column=target_column,
            target_schema=target_schema,
            target_database=target_database,
            source_columns=source_columns,
            lineage_type=lineage_type,
            transformation_expression=transformation,
            confidence_score=100 if lineage_type == ColumnLineageType.DIRECT else 90,
        )

    def _get_target_column_name(self, expr: exp.Expression) -> Optional[str]:
        """Extract the target column name from a SELECT expression."""
        # Check for alias
        if isinstance(expr, exp.Alias):
            return expr.alias

        # Check for column reference
        if isinstance(expr, exp.Column):
            return expr.name

        # For other expressions, try to get a reasonable name
        if hasattr(expr, "alias") and expr.alias:
            return expr.alias

        # Use the expression text as fallback (not ideal)
        return None

    def _extract_source_columns(
        self,
        expr: exp.Expression,
        source_tables: Dict[str, Tuple[str, Optional[str], Optional[str]]],
    ) -> Tuple[List[ColumnDependency], ColumnLineageType, Optional[str]]:
        """
        Extract source column dependencies from an expression.

        Returns:
            Tuple of (source_columns, lineage_type, transformation_expression)
        """
        source_columns = []
        lineage_type = ColumnLineageType.DIRECT
        transformation = None

        # Unwrap alias
        if isinstance(expr, exp.Alias):
            inner_expr = expr.this
        else:
            inner_expr = expr

        # Determine lineage type based on expression type
        if isinstance(inner_expr, exp.Column):
            lineage_type = ColumnLineageType.DIRECT
        elif isinstance(inner_expr, exp.Cast):
            lineage_type = ColumnLineageType.CAST
            transformation = inner_expr.sql(dialect=self.dialect)
        elif isinstance(inner_expr, (exp.Sum, exp.Avg, exp.Count, exp.Min, exp.Max)):
            lineage_type = ColumnLineageType.AGGREGATED
            transformation = inner_expr.sql(dialect=self.dialect)
        elif isinstance(inner_expr, exp.Anonymous):
            # Generic function call
            lineage_type = ColumnLineageType.DERIVED
            transformation = inner_expr.sql(dialect=self.dialect)
        elif not isinstance(inner_expr, exp.Column):
            lineage_type = ColumnLineageType.DERIVED
            transformation = inner_expr.sql(dialect=self.dialect)

        # Find all column references in the expression
        for column in inner_expr.find_all(exp.Column):
            table_alias = column.table or ""
            column_name = column.name

            # Resolve table alias to actual table
            if table_alias in source_tables:
                table_name, schema, database = source_tables[table_alias]
            elif table_alias:
                # Use alias as table name if not found
                table_name = table_alias
                schema = self.default_schema
                database = self.default_database
            else:
                # Try to infer from available tables
                # If single table, use it; otherwise, mark as unknown
                if len(source_tables) == 1:
                    first_alias = list(source_tables.keys())[0]
                    table_name, schema, database = source_tables[first_alias]
                else:
                    table_name = "_unknown_"
                    schema = None
                    database = None

            source_columns.append(ColumnDependency(
                source_table=table_name,
                source_column=column_name,
                source_schema=schema,
                source_database=database,
            ))

        return source_columns, lineage_type, transformation

    def extract_filter_columns(
        self, sql: str
    ) -> List[ColumnDependency]:
        """
        Extract columns used in WHERE/HAVING clauses.

        Args:
            sql: SQL statement

        Returns:
            List of ColumnDependency for filter columns
        """
        try:
            parsed = sqlglot.parse_one(sql, dialect=self.dialect)
            source_tables = self._extract_source_tables(parsed)

            filter_columns = []

            # Find WHERE clause
            where_clause = parsed.find(exp.Where)
            if where_clause:
                filter_columns.extend(
                    self._extract_columns_from_expression(
                        where_clause, source_tables
                    )
                )

            # Find HAVING clause
            having_clause = parsed.find(exp.Having)
            if having_clause:
                filter_columns.extend(
                    self._extract_columns_from_expression(
                        having_clause, source_tables
                    )
                )

            return filter_columns

        except Exception as e:
            logger.error(f"Error extracting filter columns: {e}")
            return []

    def extract_join_columns(
        self, sql: str
    ) -> List[Tuple[ColumnDependency, ColumnDependency]]:
        """
        Extract column pairs used in JOIN conditions.

        Args:
            sql: SQL statement

        Returns:
            List of tuples (left_column, right_column) for join conditions
        """
        try:
            parsed = sqlglot.parse_one(sql, dialect=self.dialect)
            source_tables = self._extract_source_tables(parsed)

            join_pairs = []

            for join in parsed.find_all(exp.Join):
                on_clause = join.args.get("on")
                if on_clause:
                    # Extract equality conditions
                    for eq in on_clause.find_all(exp.EQ):
                        left_col = eq.left
                        right_col = eq.right

                        if isinstance(left_col, exp.Column) and isinstance(right_col, exp.Column):
                            left_dep = self._column_to_dependency(left_col, source_tables)
                            right_dep = self._column_to_dependency(right_col, source_tables)
                            if left_dep and right_dep:
                                join_pairs.append((left_dep, right_dep))

            return join_pairs

        except Exception as e:
            logger.error(f"Error extracting join columns: {e}")
            return []

    def extract_group_by_columns(
        self, sql: str
    ) -> List[ColumnDependency]:
        """
        Extract columns used in GROUP BY clause.

        Args:
            sql: SQL statement

        Returns:
            List of ColumnDependency for group by columns
        """
        try:
            parsed = sqlglot.parse_one(sql, dialect=self.dialect)
            source_tables = self._extract_source_tables(parsed)

            group_columns = []

            group_clause = parsed.find(exp.Group)
            if group_clause:
                for column in group_clause.find_all(exp.Column):
                    dep = self._column_to_dependency(column, source_tables)
                    if dep:
                        group_columns.append(dep)

            return group_columns

        except Exception as e:
            logger.error(f"Error extracting group by columns: {e}")
            return []

    def _extract_columns_from_expression(
        self,
        expr: exp.Expression,
        source_tables: Dict[str, Tuple[str, Optional[str], Optional[str]]],
    ) -> List[ColumnDependency]:
        """Extract all column references from an expression."""
        columns = []

        for column in expr.find_all(exp.Column):
            dep = self._column_to_dependency(column, source_tables)
            if dep:
                columns.append(dep)

        return columns

    def _column_to_dependency(
        self,
        column: exp.Column,
        source_tables: Dict[str, Tuple[str, Optional[str], Optional[str]]],
    ) -> Optional[ColumnDependency]:
        """Convert a sqlglot Column to ColumnDependency."""
        table_alias = column.table or ""
        column_name = column.name

        if table_alias in source_tables:
            table_name, schema, database = source_tables[table_alias]
        elif table_alias:
            table_name = table_alias
            schema = self.default_schema
            database = self.default_database
        else:
            if len(source_tables) == 1:
                first_alias = list(source_tables.keys())[0]
                table_name, schema, database = source_tables[first_alias]
            else:
                table_name = "_unknown_"
                schema = None
                database = None

        return ColumnDependency(
            source_table=table_name,
            source_column=column_name,
            source_schema=schema,
            source_database=database,
        )

    def get_all_referenced_tables(self, sql: str) -> List[str]:
        """
        Get all tables referenced in the SQL statement.

        Args:
            sql: SQL statement

        Returns:
            List of table names (fully qualified where possible)
        """
        try:
            parsed = sqlglot.parse_one(sql, dialect=self.dialect)
            tables = []

            for table in parsed.find_all(exp.Table):
                parts = [p for p in [table.catalog, table.db, table.name] if p]
                tables.append(".".join(parts))

            return list(set(tables))

        except Exception as e:
            logger.error(f"Error extracting tables: {e}")
            return []

    def validate_sql(self, sql: str) -> Tuple[bool, Optional[str]]:
        """
        Validate SQL syntax.

        Args:
            sql: SQL statement

        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            sqlglot.parse_one(sql, dialect=self.dialect)
            return True, None
        except Exception as e:
            return False, str(e)


def parse_transformation_lineage(
    sql: str,
    target_table: str,
    target_schema: Optional[str] = None,
    target_database: Optional[str] = None,
    dialect: str = "postgres",
) -> List[Dict[str, Any]]:
    """
    Convenience function to parse column lineage from a SQL transformation.

    Args:
        sql: SQL statement
        target_table: Target table name
        target_schema: Target schema name
        target_database: Target database name
        dialect: SQL dialect

    Returns:
        List of column lineage mappings as dictionaries
    """
    parser = SQLColumnLineageParser(dialect=dialect)
    mappings = parser.parse_sql(
        sql,
        target_table=target_table,
        target_schema=target_schema,
        target_database=target_database,
    )
    return [m.to_dict() for m in mappings]
