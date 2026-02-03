"""
Data transformation utilities for pipeline execution.

Applies column mappings, type casts, filters, and exclusions
to data streams flowing through pipelines.
"""
from typing import Iterator, Dict, Any, List, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


def apply_transformations(
    data: Iterator[Dict[str, Any]], config: Dict[str, Any]
) -> Iterator[Dict[str, Any]]:
    """
    Apply column transformations to a data stream.

    Supports:
    - Column exclusion: Remove unwanted columns
    - Column mapping: Rename columns (source -> destination)
    - Type casting: Convert column values to target types
    - Row filters: Filter rows based on column conditions

    Args:
        data: Iterator of row dictionaries from the source.
        config: Pipeline config dict. Looks for a "transformations" key containing:
            - column_mapping: dict of {source_col: dest_col}
            - excluded_columns: list of column names to drop
            - type_casts: dict of {column: target_type}
            - filters: list of {column, operator, value} dicts

    Yields:
        Transformed row dictionaries.
    """
    transforms = config.get("transformations", {})
    if not transforms:
        yield from data
        return

    column_mapping = transforms.get("column_mapping", {})
    excluded_columns = set(transforms.get("excluded_columns", []))
    type_casts = transforms.get("type_casts", {})
    filters = transforms.get("filters", [])

    rows_in = 0
    rows_out = 0

    for row in data:
        rows_in += 1

        # Apply row filters
        if not _passes_filters(row, filters):
            continue

        # Build output row
        output = {}
        for key, value in row.items():
            if key in excluded_columns:
                continue
            out_key = column_mapping.get(key, key)
            out_value = _cast_value(value, type_casts.get(key))
            output[out_key] = out_value

        rows_out += 1
        yield output

    logger.info(
        f"Transformations applied: {rows_in} rows in, {rows_out} rows out "
        f"({rows_in - rows_out} filtered out)"
    )


def _passes_filters(row: Dict[str, Any], filters: List[Dict[str, Any]]) -> bool:
    """
    Check whether a row passes all configured filters.

    Supported operators: =, !=, >, <, contains

    Args:
        row: A single data row.
        filters: List of filter definitions, each with column, operator, value.

    Returns:
        True if the row passes all filters, False otherwise.
    """
    for f in filters:
        column = f.get("column", "")
        operator = f.get("operator", "=")
        filter_value = f.get("value", "")

        if column not in row:
            # If the column doesn't exist in the row, filter it out
            return False

        row_value = row[column]

        try:
            if operator == "=":
                if str(row_value) != str(filter_value):
                    return False
            elif operator == "!=":
                if str(row_value) == str(filter_value):
                    return False
            elif operator == ">":
                if float(row_value) <= float(filter_value):
                    return False
            elif operator == "<":
                if float(row_value) >= float(filter_value):
                    return False
            elif operator == "contains":
                if str(filter_value) not in str(row_value):
                    return False
            else:
                logger.warning(f"Unknown filter operator: {operator}")
        except (ValueError, TypeError) as e:
            logger.warning(
                f"Filter comparison failed for column '{column}' "
                f"(operator={operator}, value={filter_value}): {e}"
            )
            return False

    return True


def _cast_value(value: Any, target_type: Optional[str]) -> Any:
    """
    Cast a value to the specified target type.

    Supported types: string, integer, float, boolean, datetime

    Args:
        value: The original value.
        target_type: Target type string, or None to return value unchanged.

    Returns:
        The cast value, or the original value if casting fails.
    """
    if target_type is None or value is None:
        return value

    try:
        if target_type == "string":
            return str(value)
        elif target_type == "integer":
            return int(float(value))
        elif target_type == "float":
            return float(value)
        elif target_type == "boolean":
            if isinstance(value, bool):
                return value
            if isinstance(value, str):
                return value.lower() in ("true", "1", "yes", "on")
            return bool(value)
        elif target_type == "datetime":
            if isinstance(value, datetime):
                return value.isoformat()
            return str(value)
        else:
            logger.warning(f"Unknown target type: {target_type}")
            return value
    except (ValueError, TypeError) as e:
        logger.warning(
            f"Type cast to '{target_type}' failed for value '{value}': {e}"
        )
        return value
