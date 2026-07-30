"""
Tests for dlt load-stats extraction.

Regression: dlt 1.24's load_info has no row_counts attribute, so run stats
reported 0 rows even when data landed. The reliable source is the normalize
step's per-table row_counts on the pipeline trace.
"""
from backend.utils.dlt_helpers import extract_load_stats


class _FakeNormalizeInfo:
    def __init__(self, row_counts):
        self.row_counts = row_counts


class _FakeTrace:
    def __init__(self, row_counts):
        self.last_normalize_info = _FakeNormalizeInfo(row_counts)


class _FakePipeline:
    def __init__(self, row_counts):
        self.last_trace = _FakeTrace(row_counts)


class _EmptyLoadInfo:
    """Mimics dlt 1.24 LoadInfo: no row_counts / load_packages attributes."""


def test_row_counts_from_normalize_trace():
    pipeline = _FakePipeline({"customers": 12, "charges": 16, "_dlt_pipeline_state": 1})
    stats = extract_load_stats(_EmptyLoadInfo(), pipeline=pipeline)

    assert stats["rows_written"] == 28  # _dlt_ tables excluded
    assert stats["tables_loaded"] == 2
    assert {t["name"] for t in stats["tables"]} == {"customers", "charges"}
    assert stats["extraction_method"] == "pipeline_trace"


def test_no_pipeline_and_empty_load_info_is_zero_not_crash():
    stats = extract_load_stats(_EmptyLoadInfo(), pipeline=None)
    assert stats["rows_written"] == 0
    assert stats["extraction_method"] == "none"


def test_none_load_info_is_safe():
    stats = extract_load_stats(None)
    assert stats["rows_written"] == 0
