"""
SQL Validator Service.

Validates SQL queries to ensure they are safe to execute.
"""
import re
import logging
from dataclasses import dataclass
from typing import List, Optional, Set

import sqlglot
from sqlglot import exp

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of SQL validation."""
    is_valid: bool
    sql: str  # Possibly modified SQL (with LIMIT added, etc.)
    errors: List[str]
    warnings: List[str]


class SQLValidator:
    """
    Validates SQL queries for safety and correctness.

    Ensures queries are:
    - Read-only (SELECT only)
    - Using allowed tables
    - Not using dangerous functions
    - Within complexity limits
    """

    # Dangerous SQL keywords and patterns
    FORBIDDEN_KEYWORDS = {
        "insert", "update", "delete", "drop", "truncate", "alter",
        "create", "grant", "revoke", "execute", "exec", "call",
        "copy", "vacuum", "reindex", "cluster", "load",
    }

    # Dangerous PostgreSQL functions
    FORBIDDEN_FUNCTIONS = {
        "pg_read_file", "pg_read_binary_file", "pg_ls_dir",
        "pg_stat_file", "pg_sleep", "pg_terminate_backend",
        "pg_cancel_backend", "pg_reload_conf", "pg_rotate_logfile",
        "lo_import", "lo_export", "dblink", "dblink_exec",
        "set_config", "current_setting",
    }

    # Maximum query complexity
    MAX_JOINS = 5
    MAX_SUBQUERIES = 3
    DEFAULT_LIMIT = 1000

    def __init__(self, allowed_tables: Optional[Set[str]] = None):
        """
        Initialize validator.

        Args:
            allowed_tables: Set of table names the user can query.
                           If None, all tables are allowed.
        """
        self.allowed_tables = allowed_tables

    def validate(self, sql: str) -> ValidationResult:
        """
        Validate a SQL query for safety.

        Args:
            sql: The SQL query to validate

        Returns:
            ValidationResult with validity status and any errors
        """
        errors = []
        warnings = []
        sql = sql.strip()

        if not sql:
            return ValidationResult(
                is_valid=False,
                sql=sql,
                errors=["Empty SQL query"],
                warnings=[],
            )

        # Check for forbidden keywords (case-insensitive)
        sql_lower = sql.lower()
        for keyword in self.FORBIDDEN_KEYWORDS:
            # Match whole words only
            if re.search(rf"\b{keyword}\b", sql_lower):
                errors.append(f"Forbidden keyword: {keyword.upper()}")

        # Check for forbidden functions
        for func in self.FORBIDDEN_FUNCTIONS:
            if re.search(rf"\b{func}\s*\(", sql_lower):
                errors.append(f"Forbidden function: {func}")

        # Check for command injection patterns
        if re.search(r";\s*\w", sql):
            errors.append("Multiple statements not allowed")

        if re.search(r"--", sql):
            warnings.append("SQL comments detected")

        # If basic checks fail, return early
        if errors:
            return ValidationResult(
                is_valid=False,
                sql=sql,
                errors=errors,
                warnings=warnings,
            )

        # Parse and validate with sqlglot
        try:
            parsed = sqlglot.parse_one(sql, dialect="postgres")

            # Must be a SELECT statement
            if not isinstance(parsed, exp.Select):
                errors.append("Only SELECT statements are allowed")
                return ValidationResult(
                    is_valid=False,
                    sql=sql,
                    errors=errors,
                    warnings=warnings,
                )

            # Check tables if restrictions are set
            if self.allowed_tables:
                tables = self._extract_tables(parsed)
                for table in tables:
                    if table.lower() not in {t.lower() for t in self.allowed_tables}:
                        errors.append(f"Table not allowed: {table}")

            # Check complexity
            join_count = len(list(parsed.find_all(exp.Join)))
            if join_count > self.MAX_JOINS:
                errors.append(f"Too many JOINs ({join_count} > {self.MAX_JOINS})")

            subquery_count = len(list(parsed.find_all(exp.Subquery)))
            if subquery_count > self.MAX_SUBQUERIES:
                warnings.append(f"Many subqueries ({subquery_count})")

        except Exception as e:
            errors.append(f"SQL parse error: {str(e)}")
            return ValidationResult(
                is_valid=False,
                sql=sql,
                errors=errors,
                warnings=warnings,
            )

        return ValidationResult(
            is_valid=len(errors) == 0,
            sql=sql,
            errors=errors,
            warnings=warnings,
        )

    def _extract_tables(self, parsed: exp.Expression) -> List[str]:
        """Extract all table names from a parsed query."""
        tables = []
        for table in parsed.find_all(exp.Table):
            if table.name:
                tables.append(table.name)
        return tables

    def sanitize(self, sql: str, max_rows: int = DEFAULT_LIMIT) -> str:
        """
        Add safety limits to a query.

        Adds LIMIT clause if not present.

        Args:
            sql: The SQL query
            max_rows: Maximum rows to return

        Returns:
            Sanitized SQL with limits
        """
        sql = sql.strip().rstrip(";")

        try:
            parsed = sqlglot.parse_one(sql, dialect="postgres")

            # Check if LIMIT already exists
            if parsed.find(exp.Limit):
                # Ensure existing limit isn't too high
                limit_exp = parsed.find(exp.Limit)
                if limit_exp and limit_exp.expression:
                    try:
                        existing_limit = int(limit_exp.expression.this)
                        if existing_limit > max_rows:
                            # Replace with our limit
                            limit_exp.set("expression", exp.Literal.number(max_rows))
                            return parsed.sql(dialect="postgres")
                    except (ValueError, AttributeError):
                        pass
                return sql
            else:
                # Add LIMIT
                parsed = parsed.limit(max_rows)
                return parsed.sql(dialect="postgres")

        except Exception as e:
            logger.warning(f"Could not parse SQL for sanitization: {e}")
            # Fallback: append LIMIT if not present
            if "limit" not in sql.lower():
                return f"{sql} LIMIT {max_rows}"
            return sql


def get_sql_validator(allowed_tables: Optional[Set[str]] = None) -> SQLValidator:
    """Factory function for SQLValidator."""
    return SQLValidator(allowed_tables)
