"""
Timezone-safe datetime helpers.

Several columns are plain ``DateTime`` (``timestamp without time zone``), so values
read back from PostgreSQL are timezone-naive even though we write UTC into them.
Comparing such a naive value against an aware ``datetime.now(timezone.utc)`` raises
``TypeError: can't compare offset-naive and offset-aware datetimes``.

``ensure_aware`` normalizes a value to an aware UTC datetime (treating a naive value
as UTC, which is what we store), so comparisons never raise regardless of whether the
datetime came fresh from the ORM or was just assigned in memory.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional


def utcnow() -> datetime:
    """Current time as an aware UTC datetime."""
    return datetime.now(timezone.utc)


def ensure_aware(dt: Optional[datetime]) -> Optional[datetime]:
    """Return ``dt`` as an aware UTC datetime (naive values are assumed to be UTC)."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt
