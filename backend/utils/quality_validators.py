"""
Data Quality Validators.

Implements various types of quality checks that can be run on pipeline data.
"""

import re
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from sqlalchemy import text

from backend.models.quality import (
    QualityCheck,
    QualityCheckType,
    QualityCheckStatus,
    QualityCheckSeverity,
)

logger = logging.getLogger(__name__)


class QualityCheckResult:
    """Result of a quality check execution."""

    def __init__(
        self,
        passed: bool,
        status: QualityCheckStatus,
        message: str,
        actual_value: Any = None,
        expected_value: Any = None,
        details: Optional[Dict[str, Any]] = None,
        rows_checked: Optional[int] = None,
    ):
        self.passed = passed
        self.status = status
        self.message = message
        self.actual_value = actual_value
        self.expected_value = expected_value
        self.details = details or {}
        self.rows_checked = rows_checked


class QualityValidator:
    """Base class for quality validators."""

    def __init__(self, db: Session, table_name: str):
        """
        Initialize validator.

        Args:
            db: Database session
            table_name: Name of the table to validate
        """
        self.db = db
        self.table_name = table_name

    def validate(self, check: QualityCheck) -> QualityCheckResult:
        """
        Execute the quality check.

        Args:
            check: Quality check configuration

        Returns:
            Quality check result
        """
        raise NotImplementedError("Subclasses must implement validate()")


class RowCountValidator(QualityValidator):
    """Validates row count against thresholds."""

    def validate(self, check: QualityCheck) -> QualityCheckResult:
        """
        Check if row count is within expected range.

        Config format:
            {
                "min_rows": 100,  # Optional
                "max_rows": 10000,  # Optional
                "expected_rows": 5000  # Optional (exact match)
            }
        """
        config = check.config

        try:
            # Count rows
            query = text(f"SELECT COUNT(*) FROM {self.table_name}")
            result = self.db.execute(query)
            actual_count = result.scalar()

            min_rows = config.get("min_rows")
            max_rows = config.get("max_rows")
            expected_rows = config.get("expected_rows")

            # Check exact match
            if expected_rows is not None:
                passed = actual_count == expected_rows
                message = (
                    f"Row count is {actual_count}, expected exactly {expected_rows}"
                    if not passed
                    else f"Row count matches expected: {actual_count}"
                )
                return QualityCheckResult(
                    passed=passed,
                    status=QualityCheckStatus.PASSED if passed else QualityCheckStatus.FAILED,
                    message=message,
                    actual_value=actual_count,
                    expected_value=expected_rows,
                    rows_checked=actual_count,
                )

            # Check range
            passed = True
            reasons = []

            if min_rows is not None and actual_count < min_rows:
                passed = False
                reasons.append(f"below minimum {min_rows}")

            if max_rows is not None and actual_count > max_rows:
                passed = False
                reasons.append(f"above maximum {max_rows}")

            if passed:
                message = f"Row count {actual_count} is within acceptable range"
            else:
                message = f"Row count {actual_count} is {', '.join(reasons)}"

            return QualityCheckResult(
                passed=passed,
                status=QualityCheckStatus.PASSED if passed else QualityCheckStatus.FAILED,
                message=message,
                actual_value=actual_count,
                expected_value={"min": min_rows, "max": max_rows},
                rows_checked=actual_count,
            )

        except Exception as e:
            logger.error(f"Row count check failed: {str(e)}", exc_info=True)
            return QualityCheckResult(
                passed=False,
                status=QualityCheckStatus.ERROR,
                message=f"Error executing row count check: {str(e)}",
                details={"error": str(e)},
            )


class NullCheckValidator(QualityValidator):
    """Validates null values in columns."""

    def validate(self, check: QualityCheck) -> QualityCheckResult:
        """
        Check for null values in specified columns.

        Config format:
            {
                "columns": ["user_id", "email"],
                "max_null_percentage": 5  # Optional, default 0
            }
        """
        config = check.config
        columns = config.get("columns", [])
        max_null_pct = config.get("max_null_percentage", 0)

        if not columns:
            return QualityCheckResult(
                passed=False,
                status=QualityCheckStatus.ERROR,
                message="No columns specified for null check",
            )

        try:
            # Get total row count
            count_query = text(f"SELECT COUNT(*) FROM {self.table_name}")
            total_rows = self.db.execute(count_query).scalar()

            if total_rows == 0:
                return QualityCheckResult(
                    passed=True,
                    status=QualityCheckStatus.PASSED,
                    message="Table is empty, no null values to check",
                    rows_checked=0,
                )

            # Check each column
            failed_columns = []
            null_counts = {}

            for column in columns:
                null_query = text(
                    f"SELECT COUNT(*) FROM {self.table_name} WHERE {column} IS NULL"
                )
                null_count = self.db.execute(null_query).scalar()
                null_pct = (null_count / total_rows) * 100
                null_counts[column] = {"count": null_count, "percentage": null_pct}

                if null_pct > max_null_pct:
                    failed_columns.append(f"{column} ({null_pct:.2f}%)")

            passed = len(failed_columns) == 0

            if passed:
                message = f"All {len(columns)} columns have acceptable null percentages"
            else:
                message = f"Columns with excessive nulls: {', '.join(failed_columns)}"

            return QualityCheckResult(
                passed=passed,
                status=QualityCheckStatus.PASSED if passed else QualityCheckStatus.FAILED,
                message=message,
                actual_value=null_counts,
                expected_value={"max_null_percentage": max_null_pct},
                rows_checked=total_rows,
                details={"failed_columns": failed_columns if not passed else []},
            )

        except Exception as e:
            logger.error(f"Null check failed: {str(e)}", exc_info=True)
            return QualityCheckResult(
                passed=False,
                status=QualityCheckStatus.ERROR,
                message=f"Error executing null check: {str(e)}",
                details={"error": str(e)},
            )


class UniquenessValidator(QualityValidator):
    """Validates column uniqueness."""

    def validate(self, check: QualityCheck) -> QualityCheckResult:
        """
        Check if column values are unique.

        Config format:
            {
                "column": "user_id",
                "allow_duplicates": false  # Optional, default false
            }
        """
        config = check.config
        column = config.get("column")

        if not column:
            return QualityCheckResult(
                passed=False,
                status=QualityCheckStatus.ERROR,
                message="No column specified for uniqueness check",
            )

        try:
            # Count total rows
            total_query = text(f"SELECT COUNT(*) FROM {self.table_name}")
            total_rows = self.db.execute(total_query).scalar()

            # Count distinct values
            distinct_query = text(
                f"SELECT COUNT(DISTINCT {column}) FROM {self.table_name}"
            )
            distinct_count = self.db.execute(distinct_query).scalar()

            # Count duplicates
            duplicate_count = total_rows - distinct_count
            passed = duplicate_count == 0

            if passed:
                message = f"Column '{column}' has all unique values ({total_rows} rows)"
            else:
                message = (
                    f"Column '{column}' has {duplicate_count} duplicate values "
                    f"({distinct_count} unique out of {total_rows} total)"
                )

            return QualityCheckResult(
                passed=passed,
                status=QualityCheckStatus.PASSED if passed else QualityCheckStatus.FAILED,
                message=message,
                actual_value={"total": total_rows, "unique": distinct_count, "duplicates": duplicate_count},
                expected_value={"duplicates": 0},
                rows_checked=total_rows,
            )

        except Exception as e:
            logger.error(f"Uniqueness check failed: {str(e)}", exc_info=True)
            return QualityCheckResult(
                passed=False,
                status=QualityCheckStatus.ERROR,
                message=f"Error executing uniqueness check: {str(e)}",
                details={"error": str(e)},
            )


class ValueRangeValidator(QualityValidator):
    """Validates values are within specified range."""

    def validate(self, check: QualityCheck) -> QualityCheckResult:
        """
        Check if column values are within range.

        Config format:
            {
                "column": "age",
                "min": 0,
                "max": 150
            }
        """
        config = check.config
        column = config.get("column")
        min_value = config.get("min")
        max_value = config.get("max")

        if not column:
            return QualityCheckResult(
                passed=False,
                status=QualityCheckStatus.ERROR,
                message="No column specified for range check",
            )

        try:
            # Count total rows
            total_query = text(f"SELECT COUNT(*) FROM {self.table_name}")
            total_rows = self.db.execute(total_query).scalar()

            # Build WHERE clause
            conditions = []
            if min_value is not None:
                conditions.append(f"{column} < {min_value}")
            if max_value is not None:
                conditions.append(f"{column} > {max_value}")

            if not conditions:
                return QualityCheckResult(
                    passed=False,
                    status=QualityCheckStatus.ERROR,
                    message="No min or max value specified for range check",
                )

            where_clause = " OR ".join(conditions)
            out_of_range_query = text(
                f"SELECT COUNT(*) FROM {self.table_name} WHERE {where_clause}"
            )
            out_of_range_count = self.db.execute(out_of_range_query).scalar()

            passed = out_of_range_count == 0

            if passed:
                message = f"All values in '{column}' are within range [{min_value}, {max_value}]"
            else:
                message = (
                    f"{out_of_range_count} values in '{column}' are out of range "
                    f"[{min_value}, {max_value}]"
                )

            return QualityCheckResult(
                passed=passed,
                status=QualityCheckStatus.PASSED if passed else QualityCheckStatus.FAILED,
                message=message,
                actual_value={"out_of_range": out_of_range_count},
                expected_value={"min": min_value, "max": max_value},
                rows_checked=total_rows,
            )

        except Exception as e:
            logger.error(f"Range check failed: {str(e)}", exc_info=True)
            return QualityCheckResult(
                passed=False,
                status=QualityCheckStatus.ERROR,
                message=f"Error executing range check: {str(e)}",
                details={"error": str(e)},
            )


class PatternMatchValidator(QualityValidator):
    """Validates values match a regex pattern."""

    def validate(self, check: QualityCheck) -> QualityCheckResult:
        """
        Check if column values match regex pattern.

        Config format:
            {
                "column": "email",
                "pattern": "^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$"
            }
        """
        config = check.config
        column = config.get("column")
        pattern = config.get("pattern")

        if not column or not pattern:
            return QualityCheckResult(
                passed=False,
                status=QualityCheckStatus.ERROR,
                message="Column and pattern required for pattern match check",
            )

        try:
            # Validate regex pattern
            try:
                re.compile(pattern)
            except re.error as e:
                return QualityCheckResult(
                    passed=False,
                    status=QualityCheckStatus.ERROR,
                    message=f"Invalid regex pattern: {str(e)}",
                )

            # Note: This is a simplified check using PostgreSQL SIMILAR TO
            # For production, you might want to fetch all values and check in Python
            # or use PostgreSQL's regex operators

            total_query = text(f"SELECT COUNT(*) FROM {self.table_name}")
            total_rows = self.db.execute(total_query).scalar()

            # Using PostgreSQL ~ operator for regex
            matching_query = text(
                f"SELECT COUNT(*) FROM {self.table_name} WHERE {column}::text ~ :pattern"
            )
            matching_rows = self.db.execute(matching_query, {"pattern": pattern}).scalar()

            non_matching = total_rows - matching_rows
            passed = non_matching == 0

            if passed:
                message = f"All values in '{column}' match the pattern"
            else:
                message = f"{non_matching} values in '{column}' do not match the pattern"

            return QualityCheckResult(
                passed=passed,
                status=QualityCheckStatus.PASSED if passed else QualityCheckStatus.FAILED,
                message=message,
                actual_value={"matching": matching_rows, "non_matching": non_matching},
                expected_value={"pattern": pattern},
                rows_checked=total_rows,
            )

        except Exception as e:
            logger.error(f"Pattern match check failed: {str(e)}", exc_info=True)
            return QualityCheckResult(
                passed=False,
                status=QualityCheckStatus.ERROR,
                message=f"Error executing pattern match check: {str(e)}",
                details={"error": str(e)},
            )


class FreshnessValidator(QualityValidator):
    """Validates data freshness based on timestamp."""

    def validate(self, check: QualityCheck) -> QualityCheckResult:
        """
        Check if data is fresh (recent).

        Config format:
            {
                "timestamp_column": "created_at",
                "max_age_hours": 24
            }
        """
        config = check.config
        timestamp_column = config.get("timestamp_column")
        max_age_hours = config.get("max_age_hours")

        if not timestamp_column or max_age_hours is None:
            return QualityCheckResult(
                passed=False,
                status=QualityCheckStatus.ERROR,
                message="timestamp_column and max_age_hours required for freshness check",
            )

        try:
            # Get most recent timestamp
            max_ts_query = text(
                f"SELECT MAX({timestamp_column}) FROM {self.table_name}"
            )
            max_timestamp = self.db.execute(max_ts_query).scalar()

            if max_timestamp is None:
                return QualityCheckResult(
                    passed=False,
                    status=QualityCheckStatus.FAILED,
                    message=f"No data found in column '{timestamp_column}'",
                    rows_checked=0,
                )

            # Calculate age
            now = datetime.now(timezone.utc)
            if max_timestamp.tzinfo is None:
                max_timestamp = max_timestamp.replace(tzinfo=timezone.utc)

            age = now - max_timestamp
            age_hours = age.total_seconds() / 3600

            passed = age_hours <= max_age_hours

            if passed:
                message = f"Data is fresh: most recent record is {age_hours:.1f} hours old"
            else:
                message = (
                    f"Data is stale: most recent record is {age_hours:.1f} hours old "
                    f"(max allowed: {max_age_hours} hours)"
                )

            return QualityCheckResult(
                passed=passed,
                status=QualityCheckStatus.PASSED if passed else QualityCheckStatus.FAILED,
                message=message,
                actual_value={"age_hours": age_hours, "most_recent": str(max_timestamp)},
                expected_value={"max_age_hours": max_age_hours},
            )

        except Exception as e:
            logger.error(f"Freshness check failed: {str(e)}", exc_info=True)
            return QualityCheckResult(
                passed=False,
                status=QualityCheckStatus.ERROR,
                message=f"Error executing freshness check: {str(e)}",
                details={"error": str(e)},
            )


class CustomSQLValidator(QualityValidator):
    """Executes custom SQL query for validation."""

    def validate(self, check: QualityCheck) -> QualityCheckResult:
        """
        Execute custom SQL query and compare result.

        Config format:
            {
                "query": "SELECT COUNT(*) FROM table WHERE condition",
                "expected_result": 0,  # Expected scalar result
                "operator": "eq"  # eq, ne, gt, lt, gte, lte
            }
        """
        config = check.config
        query = config.get("query")
        expected_result = config.get("expected_result")
        operator = config.get("operator", "eq")

        if not query:
            return QualityCheckResult(
                passed=False,
                status=QualityCheckStatus.ERROR,
                message="No query specified for custom SQL check",
            )

        try:
            # Execute query
            result = self.db.execute(text(query))
            actual_result = result.scalar()

            # Compare results
            operators = {
                "eq": lambda a, e: a == e,
                "ne": lambda a, e: a != e,
                "gt": lambda a, e: a > e,
                "lt": lambda a, e: a < e,
                "gte": lambda a, e: a >= e,
                "lte": lambda a, e: a <= e,
            }

            if operator not in operators:
                return QualityCheckResult(
                    passed=False,
                    status=QualityCheckStatus.ERROR,
                    message=f"Invalid operator: {operator}",
                )

            passed = operators[operator](actual_result, expected_result)

            if passed:
                message = f"Custom SQL check passed: {actual_result} {operator} {expected_result}"
            else:
                message = f"Custom SQL check failed: {actual_result} not {operator} {expected_result}"

            return QualityCheckResult(
                passed=passed,
                status=QualityCheckStatus.PASSED if passed else QualityCheckStatus.FAILED,
                message=message,
                actual_value=actual_result,
                expected_value=expected_result,
                details={"query": query, "operator": operator},
            )

        except Exception as e:
            logger.error(f"Custom SQL check failed: {str(e)}", exc_info=True)
            return QualityCheckResult(
                passed=False,
                status=QualityCheckStatus.ERROR,
                message=f"Error executing custom SQL check: {str(e)}",
                details={"error": str(e), "query": query},
            )


# Validator registry
VALIDATORS = {
    QualityCheckType.ROW_COUNT: RowCountValidator,
    QualityCheckType.NULL_CHECK: NullCheckValidator,
    QualityCheckType.UNIQUENESS: UniquenessValidator,
    QualityCheckType.VALUE_RANGE: ValueRangeValidator,
    QualityCheckType.PATTERN_MATCH: PatternMatchValidator,
    QualityCheckType.FRESHNESS: FreshnessValidator,
    QualityCheckType.CUSTOM_SQL: CustomSQLValidator,
}


def execute_quality_check(
    db: Session,
    check: QualityCheck,
    table_name: str,
) -> QualityCheckResult:
    """
    Execute a quality check.

    Args:
        db: Database session
        check: Quality check configuration
        table_name: Name of the table to validate

    Returns:
        Quality check result
    """
    validator_class = VALIDATORS.get(check.check_type)

    if not validator_class:
        return QualityCheckResult(
            passed=False,
            status=QualityCheckStatus.ERROR,
            message=f"Unknown check type: {check.check_type}",
        )

    validator = validator_class(db, table_name)
    return validator.validate(check)
