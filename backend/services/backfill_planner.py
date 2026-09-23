"""
Backfill planning: split a large historical load into independent, resumable
chunks so it can run in parallel across workers instead of one monolithic,
time-boxed, /tmp-staged job.

This module is pure (no I/O): it computes the chunk boundaries. Executing the
chunks (fan-out to workers, per-connector ranged extraction, staging) is built
on top of this in later phases. Keeping the planning pure makes it fully
unit-testable and safe to land ahead of the executor.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional


# A single time window shouldn't be so large it recreates the monolith problem,
# nor so small that per-chunk overhead dominates. These are sane defaults.
DEFAULT_MAX_CHUNKS = 2000  # guardrail against pathological plans


@dataclass
class BackfillChunk:
    """One resumable slice of a backfill.

    ``start`` is inclusive, ``end`` is exclusive, so consecutive chunks tile the
    range without overlap or gaps: ``[start, end)``.
    """

    index: int
    kind: str  # "time" | "key"
    column: str
    start: Any
    end: Any
    label: str = ""

    def as_dict(self) -> Dict[str, Any]:
        def _ser(v: Any) -> Any:
            return v.isoformat() if isinstance(v, datetime) else v

        return {
            "index": self.index,
            "kind": self.kind,
            "column": self.column,
            "start": _ser(self.start),
            "end": _ser(self.end),
            "label": self.label,
        }


@dataclass
class BackfillPlan:
    kind: str
    column: str
    chunks: List[BackfillChunk] = field(default_factory=list)

    @property
    def chunk_count(self) -> int:
        return len(self.chunks)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "kind": self.kind,
            "column": self.column,
            "chunk_count": self.chunk_count,
            "chunks": [c.as_dict() for c in self.chunks],
        }


def plan_time_chunks(
    column: str,
    start: datetime,
    end: datetime,
    window: timedelta,
    *,
    max_chunks: int = DEFAULT_MAX_CHUNKS,
) -> BackfillPlan:
    """Tile ``[start, end)`` into consecutive time windows of size ``window``.

    Used when the source has a monotonically-increasing timestamp column
    (created_at / event_time). The final window is clamped to ``end``.
    """
    if window <= timedelta(0):
        raise ValueError("window must be positive")
    if end <= start:
        raise ValueError("end must be after start")

    total = end - start
    approx = -(-total // window)  # ceil division on timedeltas
    if approx > max_chunks:
        raise ValueError(
            f"plan would create {approx} chunks (> max_chunks={max_chunks}); "
            "use a larger window"
        )

    chunks: List[BackfillChunk] = []
    cursor = start
    idx = 0
    while cursor < end:
        nxt = min(cursor + window, end)
        chunks.append(
            BackfillChunk(
                index=idx,
                kind="time",
                column=column,
                start=cursor,
                end=nxt,
                label=f"{cursor.isoformat()} .. {nxt.isoformat()}",
            )
        )
        cursor = nxt
        idx += 1
    return BackfillPlan(kind="time", column=column, chunks=chunks)


def plan_key_chunks(
    column: str,
    min_key: int,
    max_key: int,
    chunk_size: int,
    *,
    max_chunks: int = DEFAULT_MAX_CHUNKS,
) -> BackfillPlan:
    """Tile the inclusive integer key range ``[min_key, max_key]`` into
    ``[start, end)`` windows of ``chunk_size`` rows of id-space.

    Used when the source has an integer primary key but no reliable timestamp.
    ``end`` is exclusive, so the last chunk's ``end`` is ``max_key + 1``.
    """
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    if max_key < min_key:
        raise ValueError("max_key must be >= min_key")

    span = (max_key - min_key) + 1
    approx = -(-span // chunk_size)  # ceil
    if approx > max_chunks:
        raise ValueError(
            f"plan would create {approx} chunks (> max_chunks={max_chunks}); "
            "use a larger chunk_size"
        )

    chunks: List[BackfillChunk] = []
    cursor = min_key
    idx = 0
    exclusive_end = max_key + 1
    while cursor < exclusive_end:
        nxt = min(cursor + chunk_size, exclusive_end)
        chunks.append(
            BackfillChunk(
                index=idx,
                kind="key",
                column=column,
                start=cursor,
                end=nxt,
                label=f"{column} [{cursor}, {nxt})",
            )
        )
        cursor = nxt
        idx += 1
    return BackfillPlan(kind="key", column=column, chunks=chunks)


def choose_partition_column(
    columns: List[Dict[str, Any]],
    *,
    prefer: Optional[List[str]] = None,
) -> Optional[Dict[str, str]]:
    """Pick a partition column from a table's schema.

    Prefers a timestamp column (best backfill semantics), else an integer
    primary/id key. ``columns`` is the ``[{"name","type"}, ...]`` shape the
    managed schema/introspection already produces. Returns ``{"name","strategy"}``
    or ``None`` when nothing suitable exists (caller falls back to a single
    unchunked load).
    """
    prefer = prefer or [
        "created_at", "created", "inserted_at", "event_time",
        "updated_at", "timestamp", "date",
    ]
    by_name = {c.get("name", "").lower(): c for c in columns if c.get("name")}

    # 1) preferred timestamp-ish names, in order
    for name in prefer:
        col = by_name.get(name)
        if col and _is_time_type(col.get("type", "")):
            return {"name": col["name"], "strategy": "time"}

    # 2) any timestamp column
    for col in columns:
        if _is_time_type(col.get("type", "")):
            return {"name": col["name"], "strategy": "time"}

    # 3) an integer id / primary key
    for name in ("id", "pk", "row_id"):
        col = by_name.get(name)
        if col and _is_int_type(col.get("type", "")):
            return {"name": col["name"], "strategy": "key"}
    for col in columns:
        if _is_int_type(col.get("type", "")) and col.get("name", "").lower().endswith("id"):
            return {"name": col["name"], "strategy": "key"}

    return None


def _is_time_type(type_str: str) -> bool:
    t = (type_str or "").lower()
    return any(k in t for k in ("timestamp", "datetime", "date", "time"))


def _is_int_type(type_str: str) -> bool:
    t = (type_str or "").lower()
    return any(k in t for k in ("int", "serial", "bigint", "number", "numeric"))


def utc_now() -> datetime:
    return datetime.now(timezone.utc)
