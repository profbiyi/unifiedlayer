"""
Utilities for working with dlt (data load tool) library.

Provides clean extraction of metrics and statistics from dlt load operations.
"""
import re
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


def extract_load_stats(load_info, pipeline=None) -> Dict[str, Any]:
    """
    Extract statistics from dlt load_info object.

    dlt's load_info API can vary between versions, so this function
    tries multiple extraction methods in order of reliability.

    Args:
        load_info: The LoadInfo object returned by pipeline.run()
        pipeline: Optional dlt pipeline object for additional metrics

    Returns:
        Dictionary with:
        - rows_written: Total rows loaded
        - bytes_written: Total bytes (if available)
        - tables_loaded: Number of tables
        - tables: List of {name, rows} for each table
        - extraction_method: Which method succeeded
    """
    stats = {
        "rows_written": 0,
        "bytes_written": 0,
        "tables_loaded": 0,
        "tables": [],
        "extraction_method": "none",
    }

    if load_info is None:
        logger.warning("load_info is None, returning empty stats")
        return stats

    # Track which tables we've seen to avoid duplicates
    seen_tables = set()

    # Method 1: row_counts attribute (most reliable in recent dlt versions)
    if _extract_from_row_counts(load_info, stats, seen_tables):
        stats["extraction_method"] = "row_counts"
        logger.debug(f"Extracted stats via row_counts: {stats['rows_written']} rows")

    # Method 2: load_packages with jobs
    if stats["rows_written"] == 0:
        if _extract_from_load_packages(load_info, stats, seen_tables):
            stats["extraction_method"] = "load_packages"
            logger.debug(f"Extracted stats via load_packages: {stats['rows_written']} rows")

    # Method 3: metrics from pipeline trace
    if stats["rows_written"] == 0 and pipeline:
        if _extract_from_pipeline_trace(pipeline, stats, seen_tables):
            stats["extraction_method"] = "pipeline_trace"
            logger.debug(f"Extracted stats via pipeline_trace: {stats['rows_written']} rows")

    # Method 4: Parse string representation (last resort)
    if stats["rows_written"] == 0:
        if _extract_from_string(load_info, stats):
            stats["extraction_method"] = "string_parse"
            logger.debug(f"Extracted stats via string_parse: {stats['rows_written']} rows")

    # Method 5: Check for metrics dict directly on load_info
    if stats["rows_written"] == 0:
        if _extract_from_metrics_dict(load_info, stats, seen_tables):
            stats["extraction_method"] = "metrics_dict"
            logger.debug(f"Extracted stats via metrics_dict: {stats['rows_written']} rows")

    # Update tables_loaded count if we got tables but no count
    if stats["tables"] and stats["tables_loaded"] == 0:
        stats["tables_loaded"] = len(stats["tables"])

    # Log final result
    if stats["rows_written"] > 0:
        logger.info(
            f"Load stats extracted via {stats['extraction_method']}: "
            f"{stats['rows_written']} rows across {stats['tables_loaded']} tables"
        )
    else:
        logger.warning(
            "Could not extract row counts from load_info. "
            f"load_info type: {type(load_info).__name__}"
        )

    return stats


def _extract_from_row_counts(load_info, stats: Dict, seen_tables: set) -> bool:
    """Extract from load_info.row_counts dict."""
    try:
        if not hasattr(load_info, 'row_counts'):
            return False

        row_counts = load_info.row_counts
        if not row_counts:
            return False

        for table_name, count in row_counts.items():
            # Skip internal dlt tables
            if table_name.startswith('_dlt_'):
                continue

            if table_name not in seen_tables:
                seen_tables.add(table_name)
                stats["tables"].append({"name": table_name, "rows": count})
                stats["rows_written"] += count
                stats["tables_loaded"] += 1

        return stats["rows_written"] > 0

    except Exception as e:
        logger.debug(f"row_counts extraction failed: {e}")
        return False


def _extract_from_load_packages(load_info, stats: Dict, seen_tables: set) -> bool:
    """Extract from load_info.load_packages."""
    try:
        if not hasattr(load_info, 'load_packages'):
            return False

        for package in load_info.load_packages:
            # Get tables from schema_update
            if hasattr(package, 'schema_update') and package.schema_update:
                for table_name in package.schema_update.keys():
                    if table_name.startswith('_dlt_'):
                        continue
                    if table_name not in seen_tables:
                        seen_tables.add(table_name)
                        stats["tables"].append({"name": table_name, "rows": 0})
                        stats["tables_loaded"] += 1

            # Get row counts from jobs
            if hasattr(package, 'jobs'):
                for job_key, job_info in (package.jobs.items() if isinstance(package.jobs, dict) else [(None, j) for j in package.jobs]):
                    if hasattr(job_info, 'metrics') and job_info.metrics:
                        rows = (
                            job_info.metrics.get("rows", 0) or
                            job_info.metrics.get("rows_count", 0) or
                            job_info.metrics.get("row_count", 0)
                        )
                        stats["rows_written"] += rows

        return stats["tables_loaded"] > 0

    except Exception as e:
        logger.debug(f"load_packages extraction failed: {e}")
        return False


def _extract_from_pipeline_trace(pipeline, stats: Dict, seen_tables: set) -> bool:
    """Extract from pipeline.last_trace."""
    try:
        if not hasattr(pipeline, 'last_trace') or not pipeline.last_trace:
            return False

        trace = pipeline.last_trace

        # Try to get metrics from trace
        if hasattr(trace, 'metrics') and trace.metrics:
            metrics = trace.metrics
            if 'rows' in metrics:
                stats["rows_written"] = metrics['rows']
                return True

        # Try steps in trace
        if hasattr(trace, 'steps'):
            for step in trace.steps:
                if hasattr(step, 'metrics') and step.metrics:
                    rows = step.metrics.get('rows', 0)
                    stats["rows_written"] += rows

        return stats["rows_written"] > 0

    except Exception as e:
        logger.debug(f"pipeline_trace extraction failed: {e}")
        return False


def _extract_from_string(load_info, stats: Dict) -> bool:
    """Extract row count from string representation."""
    try:
        load_info_str = str(load_info)

        # Pattern 1: "X rows" or "X row"
        row_match = re.search(r'(\d+)\s*rows?', load_info_str, re.IGNORECASE)
        if row_match:
            stats["rows_written"] = int(row_match.group(1))
            return True

        # Pattern 2: "loaded X" where X is a number
        loaded_match = re.search(r'loaded\s+(\d+)', load_info_str, re.IGNORECASE)
        if loaded_match:
            stats["rows_written"] = int(loaded_match.group(1))
            return True

        # Pattern 3: Count tables mentioned
        table_matches = re.findall(r"'([^']+)'\s*:\s*(\d+)", load_info_str)
        for table_name, count in table_matches:
            if not table_name.startswith('_dlt_'):
                stats["tables"].append({"name": table_name, "rows": int(count)})
                stats["rows_written"] += int(count)

        return stats["rows_written"] > 0

    except Exception as e:
        logger.debug(f"string extraction failed: {e}")
        return False


def _extract_from_metrics_dict(load_info, stats: Dict, seen_tables: set) -> bool:
    """Extract from load_info.metrics if it exists as a dict."""
    try:
        # Check for metrics attribute
        if hasattr(load_info, 'metrics') and load_info.metrics:
            metrics = load_info.metrics
            if isinstance(metrics, dict):
                stats["rows_written"] = metrics.get('rows', 0) or metrics.get('total_rows', 0)
                return stats["rows_written"] > 0

        # Check for asdict() method
        if hasattr(load_info, 'asdict'):
            info_dict = load_info.asdict()
            if 'row_counts' in info_dict:
                for table_name, count in info_dict['row_counts'].items():
                    if not table_name.startswith('_dlt_') and table_name not in seen_tables:
                        seen_tables.add(table_name)
                        stats["tables"].append({"name": table_name, "rows": count})
                        stats["rows_written"] += count
                return stats["rows_written"] > 0

        return False

    except Exception as e:
        logger.debug(f"metrics_dict extraction failed: {e}")
        return False


def get_load_summary(load_info) -> str:
    """
    Get a human-readable summary of the load operation.

    Args:
        load_info: The LoadInfo object from pipeline.run()

    Returns:
        Summary string
    """
    stats = extract_load_stats(load_info)

    if stats["rows_written"] == 0:
        return "No rows loaded"

    if stats["tables"]:
        table_summaries = [f"{t['name']}: {t['rows']} rows" for t in stats["tables"][:5]]
        table_str = ", ".join(table_summaries)
        if len(stats["tables"]) > 5:
            table_str += f" (and {len(stats['tables']) - 5} more tables)"
        return f"Loaded {stats['rows_written']} total rows: {table_str}"

    return f"Loaded {stats['rows_written']} rows across {stats['tables_loaded']} tables"
