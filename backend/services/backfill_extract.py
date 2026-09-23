"""
Ranged extraction for chunked backfill (Postgres).

Given a source table and a ``[start, end)`` window on a partition column, produce
a dlt resource that streams ONLY that slice, so a large historical load can be
split into independent, parallelisable chunks instead of one monolithic scan.

Identifiers (schema/table/column) are quoted and quote-escaped, never string-
interpolated raw; callers pass names that came from schema discovery, not from
untrusted request input. Rows stream via a server-side cursor so a wide chunk
never buffers the whole slice in memory.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional, Tuple
from urllib.parse import quote_plus

logger = logging.getLogger(__name__)

DEFAULT_BATCH_SIZE = 50_000


def _pg_url(config: Dict[str, Any]) -> str:
    user = config.get("user") or config.get("username")
    pw = config.get("password", "")
    host = config.get("host")
    port = config.get("port", 5432)
    db = config.get("database")
    sslmode = config.get("sslmode")
    url = (
        f"postgresql://{quote_plus(str(user))}:{quote_plus(str(pw))}"
        f"@{host}:{port}/{db}"
    )
    if sslmode:
        url += f"?sslmode={sslmode}"
    return url


def _qident(name: str) -> str:
    """Quote a Postgres identifier, escaping embedded double quotes."""
    return '"' + str(name).replace('"', '""') + '"'


def _split_table(table: str) -> Tuple[str, str]:
    if "." in table:
        schema, tbl = table.split(".", 1)
        return schema, tbl
    return "public", table


def get_range_bounds(
    config: Dict[str, Any], table: str, column: str
) -> Tuple[Optional[Any], Optional[Any], int]:
    """Return ``(min, max, count)`` of the partition column for planning.

    ``(None, None, 0)`` when the table is empty.
    """
    from sqlalchemy import create_engine, text

    schema, tbl = _split_table(table)
    fq = f"{_qident(schema)}.{_qident(tbl)}"
    q = (
        f"SELECT MIN({_qident(column)}) AS lo, MAX({_qident(column)}) AS hi, "
        f"COUNT(*) AS n FROM {fq}"
    )
    engine = create_engine(_pg_url(config))
    try:
        with engine.connect() as conn:
            row = conn.execute(text(q)).mappings().first()
        if not row:
            return (None, None, 0)
        return (row["lo"], row["hi"], int(row["n"]))
    finally:
        engine.dispose()


def postgres_ranged_source(
    config: Dict[str, Any],
    table: str,
    column: str,
    start: Any,
    end: Any,
    *,
    batch_size: int = DEFAULT_BATCH_SIZE,
    write_disposition: str = "append",
):
    """A dlt resource that streams rows where ``start <= column < end``.

    ``append`` is the right disposition for backfill chunks: each chunk owns a
    disjoint slice, so appending loads every row exactly once with no cross-chunk
    merge coordination.
    """
    import dlt
    from sqlalchemy import create_engine, text

    schema, tbl = _split_table(table)
    fq = f"{_qident(schema)}.{_qident(tbl)}"
    col = _qident(column)
    resource_name = tbl  # dlt table name in the destination

    @dlt.resource(name=resource_name, write_disposition=write_disposition)
    def _rows():
        engine = create_engine(_pg_url(config))
        try:
            with engine.connect().execution_options(stream_results=True) as conn:
                q = text(f"SELECT * FROM {fq} WHERE {col} >= :start AND {col} < :end")
                result = conn.execute(q, {"start": start, "end": end})
                for row in result.mappings():
                    yield dict(row)
        finally:
            engine.dispose()

    return _rows
