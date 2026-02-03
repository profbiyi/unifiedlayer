"""
Data quality validation module.

Provides data quality checks and validation using Great Expectations.
"""
from typing import Dict, Any, List, Optional
import pandas as pd
import logging

logger = logging.getLogger(__name__)


class DataQualityChecker:
    """
    Data quality validation using Great Expectations.

    Provides common data quality checks for pipeline data.
    """

    def __init__(self):
        """Initialize data quality checker."""
        pass

    def check_null_values(
        self,
        df: pd.DataFrame,
        columns: List[str],
        threshold: float = 0.05,
    ) -> Dict[str, Any]:
        """
        Check for null values in specified columns.

        Args:
            df: DataFrame to check
            columns: Columns to check
            threshold: Maximum allowed null percentage

        Returns:
            Validation results
        """
        results = {}

        for col in columns:
            if col not in df.columns:
                results[col] = {"error": "Column not found"}
                continue

            null_count = df[col].isnull().sum()
            total_count = len(df)
            null_percentage = (null_count / total_count) * 100 if total_count > 0 else 0

            passed = null_percentage <= (threshold * 100)

            results[col] = {
                "passed": passed,
                "null_count": int(null_count),
                "total_count": int(total_count),
                "null_percentage": round(null_percentage, 2),
                "threshold": threshold * 100,
            }

        return results

    def check_unique_values(
        self,
        df: pd.DataFrame,
        columns: List[str],
    ) -> Dict[str, Any]:
        """
        Check uniqueness of values in columns.

        Args:
            df: DataFrame to check
            columns: Columns to check

        Returns:
            Validation results
        """
        results = {}

        for col in columns:
            if col not in df.columns:
                results[col] = {"error": "Column not found"}
                continue

            total_count = len(df)
            unique_count = df[col].nunique()
            duplicate_count = total_count - unique_count

            results[col] = {
                "unique_count": int(unique_count),
                "duplicate_count": int(duplicate_count),
                "is_unique": duplicate_count == 0,
            }

        return results

    def check_data_types(
        self,
        df: pd.DataFrame,
        expected_types: Dict[str, str],
    ) -> Dict[str, Any]:
        """
        Check data types of columns.

        Args:
            df: DataFrame to check
            expected_types: Expected data types {column: type}

        Returns:
            Validation results
        """
        results = {}

        for col, expected_type in expected_types.items():
            if col not in df.columns:
                results[col] = {"error": "Column not found"}
                continue

            actual_type = str(df[col].dtype)
            matches = expected_type.lower() in actual_type.lower()

            results[col] = {
                "expected_type": expected_type,
                "actual_type": actual_type,
                "matches": matches,
            }

        return results

    def check_value_range(
        self,
        df: pd.DataFrame,
        column: str,
        min_value: Optional[float] = None,
        max_value: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Check if values are within expected range.

        Args:
            df: DataFrame to check
            column: Column to check
            min_value: Minimum allowed value
            max_value: Maximum allowed value

        Returns:
            Validation results
        """
        if column not in df.columns:
            return {"error": "Column not found"}

        violations = []

        if min_value is not None:
            below_min = df[df[column] < min_value]
            if not below_min.empty:
                violations.append(f"{len(below_min)} values below {min_value}")

        if max_value is not None:
            above_max = df[df[column] > max_value]
            if not above_max.empty:
                violations.append(f"{len(above_max)} values above {max_value}")

        return {
            "column": column,
            "min_value": min_value,
            "max_value": max_value,
            "violations": violations,
            "passed": len(violations) == 0,
        }

    def validate_dataframe(
        self,
        df: pd.DataFrame,
        rules: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Validate DataFrame against a set of rules.

        Args:
            df: DataFrame to validate
            rules: Validation rules

        Returns:
            Complete validation results
        """
        results = {
            "row_count": len(df),
            "column_count": len(df.columns),
            "checks": {},
        }

        # Null value checks
        if "null_checks" in rules:
            results["checks"]["null_values"] = self.check_null_values(
                df,
                rules["null_checks"]["columns"],
                rules["null_checks"].get("threshold", 0.05),
            )

        # Uniqueness checks
        if "unique_checks" in rules:
            results["checks"]["unique_values"] = self.check_unique_values(
                df,
                rules["unique_checks"]["columns"],
            )

        # Data type checks
        if "type_checks" in rules:
            results["checks"]["data_types"] = self.check_data_types(
                df,
                rules["type_checks"],
            )

        # Overall pass/fail
        all_passed = all(
            check.get("passed", True)
            for check_type in results["checks"].values()
            for check in (check_type.values() if isinstance(check_type, dict) else [check_type])
            if isinstance(check, dict)
        )

        results["overall_passed"] = all_passed

        return results


# Global instance
data_quality_checker = DataQualityChecker()
