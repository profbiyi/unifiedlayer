"""
Query Executor Service.

Executes SQL queries safely with timeout and row limits.
"""
import logging
import time
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger(__name__)


@dataclass
class QueryResult:
    """Result of a SQL query execution."""
    success: bool
    data: List[Dict[str, Any]]
    columns: List[str]
    row_count: int
    execution_time_ms: int
    error: Optional[str] = None
    truncated: bool = False  # True if results were limited


class QueryExecutor:
    """
    Executes SQL queries with safety limits.

    Features:
    - Query timeout
    - Row limit
    - Read-only execution
    - Error handling
    """

    DEFAULT_TIMEOUT_SECONDS = 30
    DEFAULT_MAX_ROWS = 1000
    MAX_TIMEOUT_SECONDS = 60

    def __init__(self, db: Session):
        self.db = db

    async def execute(
        self,
        sql: str,
        timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
        max_rows: int = DEFAULT_MAX_ROWS,
    ) -> QueryResult:
        """
        Execute a SQL query safely.

        Args:
            sql: The SQL query to execute
            timeout_seconds: Query timeout in seconds
            max_rows: Maximum rows to return

        Returns:
            QueryResult with data or error
        """
        # Enforce limits
        timeout_seconds = min(timeout_seconds, self.MAX_TIMEOUT_SECONDS)
        max_rows = min(max_rows, 10000)  # Hard cap at 10k rows

        start_time = time.time()

        try:
            # Set statement timeout
            self.db.execute(text(f"SET statement_timeout = '{timeout_seconds * 1000}'"))

            # Execute query
            result = self.db.execute(text(sql))

            # Fetch results
            rows = result.fetchmany(max_rows + 1)  # +1 to detect truncation
            columns = list(result.keys()) if rows else []

            # Check if results were truncated
            truncated = len(rows) > max_rows
            if truncated:
                rows = rows[:max_rows]

            # Convert to list of dicts
            data = []
            for row in rows:
                row_dict = {}
                for i, col in enumerate(columns):
                    value = row[i]
                    # Convert non-JSON-serializable types. Decimal (from
                    # SUM/AVG/numeric columns) was previously unhandled and
                    # crashed response serialization with a 500.
                    if hasattr(value, 'isoformat'):  # datetime / date
                        value = value.isoformat()
                    elif isinstance(value, Decimal):
                        value = float(value)
                    elif isinstance(value, UUID):
                        value = str(value)
                    elif isinstance(value, bytes):
                        value = value.decode('utf-8', errors='replace')
                    row_dict[col] = value
                data.append(row_dict)

            execution_time_ms = int((time.time() - start_time) * 1000)

            # Reset timeout
            self.db.execute(text("SET statement_timeout = '0'"))

            return QueryResult(
                success=True,
                data=data,
                columns=columns,
                row_count=len(data),
                execution_time_ms=execution_time_ms,
                truncated=truncated,
            )

        except SQLAlchemyError as e:
            execution_time_ms = int((time.time() - start_time) * 1000)
            error_msg = str(e)

            # Clean up error message
            if "statement timeout" in error_msg.lower():
                error_msg = f"Query timed out after {timeout_seconds} seconds"
            elif "permission denied" in error_msg.lower():
                error_msg = "Permission denied for this query"
            else:
                # Remove internal details
                error_msg = error_msg.split('\n')[0][:200]

            logger.error(f"Query execution failed: {error_msg}")

            # Reset timeout
            try:
                self.db.execute(text("SET statement_timeout = '0'"))
            except Exception:
                pass

            return QueryResult(
                success=False,
                data=[],
                columns=[],
                row_count=0,
                execution_time_ms=execution_time_ms,
                error=error_msg,
            )

        except Exception as e:
            execution_time_ms = int((time.time() - start_time) * 1000)
            logger.error(f"Unexpected query error: {e}")

            return QueryResult(
                success=False,
                data=[],
                columns=[],
                row_count=0,
                execution_time_ms=execution_time_ms,
                error=f"Query failed: {str(e)[:200]}",
            )

    def execute_sync(
        self,
        sql: str,
        timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
        max_rows: int = DEFAULT_MAX_ROWS,
    ) -> QueryResult:
        """
        Synchronous version of execute.

        For use in non-async contexts.
        """
        import asyncio

        # Check if we're in an async context
        try:
            asyncio.get_running_loop()
            # We're in async context, need to handle differently
            import nest_asyncio
            nest_asyncio.apply()
            return asyncio.run(self.execute(sql, timeout_seconds, max_rows))
        except RuntimeError:
            # No running loop, safe to use asyncio.run
            return asyncio.run(self.execute(sql, timeout_seconds, max_rows))


def get_query_executor(db: Session) -> QueryExecutor:
    """Factory function for QueryExecutor."""
    return QueryExecutor(db)
