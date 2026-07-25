"""
DuckDB Analytics Engine.

The query engine behind on-platform BI + AI for *managed* (bucket-backed) orgs.
Synced data lands as Parquet in an org's bucket prefix (internal MinIO or an
external S3/GCS bucket); this engine reads that Parquet with DuckDB to power
schema introspection, Ask AI (NL→SQL), and model generation.

Security is a first-class concern here because we execute LLM-generated SQL over
customer data. The engine enforces a sandbox (see ``_lock_down``):

  1. Each engine instance is scoped to exactly ONE org's data location. It never
     opens paths outside that location.
  2. Sources are *materialised* into in-memory DuckDB tables at registration,
     then external access is disabled — so generated SQL can only touch the
     registered tables and cannot ``read_parquet('s3://other-org/...')``, reach
     ``httpfs``, or read local files.
  3. Only a single read-only ``SELECT``/CTE statement is accepted for execution.
  4. Memory, thread, and row limits are enforced.

Phase 1 (this module) supports a local base directory and carries the S3/MinIO
connection plumbing; it is intentionally not yet wired into the live AI path.
See docs/architecture/managed-analytics-duckdb.md.
"""
from __future__ import annotations

import glob
import logging
import os
import re
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import duckdb

logger = logging.getLogger(__name__)

# A statement is accepted only if, after stripping comments/whitespace, it is a
# single SELECT or WITH (CTE) statement. Everything else — DDL, DML, PRAGMA,
# COPY, ATTACH, multiple statements — is rejected before it reaches DuckDB.
_READONLY_RE = re.compile(r"^\s*(select|with)\b", re.IGNORECASE)
_COMMENT_RE = re.compile(r"/\*.*?\*/", re.DOTALL)
_LINE_COMMENT_RE = re.compile(r"--[^\n]*")

# Parquet is the canonical synced format; allow the common alternatives too.
_TABLE_FILE_GLOBS = ("*.parquet", "*.parq")


@dataclass
class EngineResult:
    """Result of a sandboxed query."""
    success: bool
    columns: List[str] = field(default_factory=list)
    rows: List[Dict[str, Any]] = field(default_factory=list)
    row_count: int = 0
    execution_time_ms: int = 0
    truncated: bool = False
    error: Optional[str] = None


class SandboxError(Exception):
    """Raised when a statement violates the read-only sandbox."""


class DuckDBAnalyticsEngine:
    """
    Sandboxed DuckDB engine scoped to a single org's data location.

    Lifecycle:
        engine = DuckDBAnalyticsEngine(base_path="/data/org-12")
        engine.register_all()          # discover + materialise tables, then lock
        schema = engine.introspect()   # {table: [{"name","type"}, ...]}
        result = engine.execute(sql)   # read-only SELECT only
        engine.close()

    Or as a context manager:
        with DuckDBAnalyticsEngine(base_path=...) as engine:
            engine.register_all()
            ...
    """

    DEFAULT_MAX_ROWS = 1000
    HARD_MAX_ROWS = 10000
    DEFAULT_MEMORY_LIMIT = "512MB"
    DEFAULT_THREADS = 2

    def __init__(
        self,
        *,
        base_path: Optional[str] = None,
        s3: Optional[Dict[str, Any]] = None,
        memory_limit: str = DEFAULT_MEMORY_LIMIT,
        threads: int = DEFAULT_THREADS,
    ):
        """
        Args:
            base_path: Local directory holding the org's Parquet (one subdir or
                file per table). Exactly one of base_path / s3 must be given.
            s3: S3/MinIO config: {endpoint, region, access_key, secret_key,
                url_style, use_ssl, bucket, prefix}. Same code path for internal
                MinIO and external buckets.
            memory_limit: DuckDB memory cap (e.g. "512MB").
            threads: DuckDB worker threads.
        """
        if bool(base_path) == bool(s3):
            raise ValueError("Provide exactly one of base_path or s3")

        self.base_path = base_path
        self.s3 = s3
        self._conn = duckdb.connect(database=":memory:")
        self._registered: Dict[str, str] = {}
        self._locked = False

        self._conn.execute(f"SET memory_limit='{memory_limit}'")
        self._conn.execute(f"SET threads={int(threads)}")
        if s3:
            self._configure_s3(s3)

    # ---- setup -----------------------------------------------------------

    def _configure_s3(self, s3: Dict[str, Any]) -> None:
        """Point DuckDB's httpfs at the bucket (works for AWS S3 and MinIO)."""
        self._conn.execute("INSTALL httpfs")
        self._conn.execute("LOAD httpfs")
        settings = {
            "s3_region": s3.get("region", "us-east-1"),
            "s3_endpoint": s3.get("endpoint"),           # e.g. minio:9000 for MinIO
            "s3_access_key_id": s3.get("access_key"),
            "s3_secret_access_key": s3.get("secret_key"),
            "s3_url_style": s3.get("url_style", "path"),  # MinIO needs path-style
            "s3_use_ssl": "true" if s3.get("use_ssl", True) else "false",
        }
        for key, value in settings.items():
            if value is None:
                continue
            # Booleans already stringified above; quote the rest.
            literal = value if key == "s3_use_ssl" else f"'{value}'"
            self._conn.execute(f"SET {key}={literal}")

    def _source_uri(self, relative: str) -> str:
        if self.s3:
            prefix = self.s3["prefix"].rstrip("/")
            bucket = self.s3["bucket"]
            return f"s3://{bucket}/{prefix}/{relative}"
        return os.path.join(self.base_path, relative)

    @staticmethod
    def _safe_identifier(name: str) -> str:
        """Derive a safe SQL table identifier from a file/dir name."""
        stem = re.sub(r"\.(parquet|parq)$", "", os.path.basename(name.rstrip("/")))
        ident = re.sub(r"[^A-Za-z0-9_]", "_", stem).strip("_").lower()
        if not ident:
            ident = "table"
        if ident[0].isdigit():
            ident = f"t_{ident}"
        return ident

    def register_table(self, table_name: str, relative_path: str) -> None:
        """
        Materialise one Parquet source (file, dir, or glob) as an in-memory table.

        Must be called before the sandbox is locked (register_all locks after).
        """
        if self._locked:
            raise SandboxError("Engine is locked; register tables before locking")
        ident = self._safe_identifier(table_name)
        uri = self._source_uri(relative_path)
        # If a directory was given, read all parquet parts under it.
        if not self.s3 and os.path.isdir(uri):
            uri = os.path.join(uri, "**", "*.parquet")
        # Materialise now (external access still enabled) so that after lock-down
        # the data is resident and no file/network access is needed to query it.
        self._conn.execute(
            f'CREATE TABLE "{ident}" AS SELECT * FROM read_parquet(?, union_by_name=true)',
            [uri],
        )
        self._registered[ident] = uri
        logger.info("Registered table '%s' from %s", ident, uri)

    def register_all(self) -> List[str]:
        """
        Discover every Parquet table under the org's location, materialise each,
        then lock the sandbox. Returns the registered table names.

        For local base_path: each top-level ``*.parquet`` file or subdirectory
        (dlt writes one dir per table) becomes a table.
        """
        if self.s3:
            # S3 discovery is handled by the catalog in a later phase; callers
            # register known tables explicitly for now.
            raise NotImplementedError(
                "register_all() for S3 requires the catalog (phase 3); "
                "use register_table() with known names for now"
            )

        entries: List[str] = []
        for pattern in _TABLE_FILE_GLOBS:
            entries.extend(glob.glob(os.path.join(self.base_path, pattern)))
        # dlt-style: one subdirectory per table
        for child in sorted(os.listdir(self.base_path)) if os.path.isdir(self.base_path) else []:
            child_path = os.path.join(self.base_path, child)
            if os.path.isdir(child_path) and glob.glob(os.path.join(child_path, "**", "*.parquet"), recursive=True):
                entries.append(child_path)

        for entry in sorted(set(entries)):
            try:
                self.register_table(os.path.basename(entry), os.path.basename(entry))
            except Exception as exc:  # noqa: BLE001 — one bad table shouldn't sink the rest
                logger.warning("Skipping unreadable source %s: %s", entry, exc)

        self._lock_down()
        return list(self._registered.keys())

    def _lock_down(self) -> None:
        """Disable all external access. After this, only registered tables exist."""
        # Data is already materialised; no legitimate query needs file/network.
        self._conn.execute("SET enable_external_access=false")
        self._locked = True
        logger.info("DuckDB sandbox locked (%d tables)", len(self._registered))

    # ---- introspection ---------------------------------------------------

    def introspect(self) -> Dict[str, List[Dict[str, str]]]:
        """Return {table_name: [{"name","type"}, ...]} for registered tables."""
        schema: Dict[str, List[Dict[str, str]]] = {}
        for table in self._registered:
            cols = self._conn.execute(
                "SELECT column_name, data_type FROM information_schema.columns "
                "WHERE table_name = ? ORDER BY ordinal_position",
                [table],
            ).fetchall()
            schema[table] = [{"name": c[0], "type": c[1]} for c in cols]
        return schema

    # ---- execution -------------------------------------------------------

    def _assert_readonly(self, sql: str) -> None:
        stripped = _LINE_COMMENT_RE.sub("", _COMMENT_RE.sub("", sql)).strip()
        if not stripped:
            raise SandboxError("Empty statement")
        if ";" in stripped.rstrip(";"):
            raise SandboxError("Multiple statements are not allowed")
        if not _READONLY_RE.match(stripped):
            raise SandboxError("Only a single read-only SELECT/CTE is allowed")

    def execute(
        self,
        sql: str,
        *,
        max_rows: int = DEFAULT_MAX_ROWS,
        timeout_seconds: int = 30,
    ) -> EngineResult:
        """Execute a single read-only SELECT against the org's registered tables."""
        if not self._locked:
            raise SandboxError("Call register_all() before execute()")
        max_rows = min(max_rows, self.HARD_MAX_ROWS)
        start = time.time()
        try:
            self._assert_readonly(sql)
        except SandboxError as exc:
            return EngineResult(success=False, error=str(exc))

        try:
            self._conn.execute(f"SET statement_timeout='{int(timeout_seconds)}s'")
        except duckdb.Error:
            pass  # older builds: rely on row cap + memory limit

        try:
            rel = self._conn.execute(sql)
            columns = [d[0] for d in rel.description] if rel.description else []
            fetched = rel.fetchmany(max_rows + 1)
            truncated = len(fetched) > max_rows
            fetched = fetched[:max_rows]
            rows = [dict(zip(columns, r)) for r in fetched]
            return EngineResult(
                success=True,
                columns=columns,
                rows=rows,
                row_count=len(rows),
                execution_time_ms=int((time.time() - start) * 1000),
                truncated=truncated,
            )
        except duckdb.Error as exc:
            return EngineResult(
                success=False,
                error=str(exc).splitlines()[0][:300],
                execution_time_ms=int((time.time() - start) * 1000),
            )

    # ---- lifecycle -------------------------------------------------------

    @property
    def tables(self) -> List[str]:
        return list(self._registered.keys())

    def close(self) -> None:
        try:
            self._conn.close()
        except Exception:  # noqa: BLE001
            pass

    def __enter__(self) -> "DuckDBAnalyticsEngine":
        return self

    def __exit__(self, *exc) -> None:
        self.close()
