"""
Tests for the DuckDB analytics engine sandbox.

These run entirely over local Parquet fixtures — no MinIO/S3 needed. They
exercise discovery, introspection, read-only enforcement, sandbox-escape
blocking, and row caps: the security-critical surface of the engine.
"""
import duckdb
import pytest

from backend.services.duckdb_engine import DuckDBAnalyticsEngine, SandboxError


def _write_parquet(path: str, rows_sql: str) -> None:
    """Materialise a small Parquet file from a VALUES query (unsandboxed)."""
    con = duckdb.connect()
    con.execute(f"COPY ({rows_sql}) TO '{path}' (FORMAT PARQUET)")
    con.close()


@pytest.fixture()
def org_data(tmp_path):
    """An org data dir with two Parquet 'tables'."""
    base = tmp_path / "org-12"
    base.mkdir()
    _write_parquet(
        str(base / "payments.parquet"),
        "SELECT * FROM (VALUES (1, 5000, 'NGN', 'success'), "
        "(2, 2500, 'NGN', 'failed'), (3, 7000, 'NGN', 'success')) "
        "AS t(id, amount, currency, status)",
    )
    _write_parquet(
        str(base / "customers.parquet"),
        "SELECT * FROM (VALUES (1, 'Ada'), (2, 'Emeka')) AS t(id, name)",
    )
    return base


@pytest.fixture()
def other_org_file(tmp_path):
    """A Parquet file belonging to a DIFFERENT org — must be unreachable."""
    secret = tmp_path / "org-99" / "secret.parquet"
    secret.parent.mkdir()
    _write_parquet(
        str(secret),
        "SELECT * FROM (VALUES (999, 'leak')) AS t(id, note)",
    )
    return secret


@pytest.fixture()
def org_data_dlt(tmp_path):
    """dlt-style layout: <dataset>/<table>/<parts>.parquet, with a multi-part table."""
    base = tmp_path / "org-20"
    payments = base / "main" / "payments"
    customers = base / "main" / "customers"
    payments.mkdir(parents=True)
    customers.mkdir(parents=True)
    _write_parquet(
        str(payments / "1234.0.parquet"),
        "SELECT * FROM (VALUES (1, 100), (2, 200)) AS t(id, amount)",
    )
    _write_parquet(
        str(payments / "1234.1.parquet"),
        "SELECT * FROM (VALUES (3, 300)) AS t(id, amount)",
    )
    _write_parquet(
        str(customers / "1234.0.parquet"),
        "SELECT * FROM (VALUES (1, 'Ada')) AS t(id, name)",
    )
    return base


def test_register_all_discovers_tables(org_data):
    with DuckDBAnalyticsEngine(base_path=str(org_data)) as engine:
        tables = set(engine.register_all())
        assert tables == {"payments", "customers"}


def test_discovers_dlt_layout_and_unions_parts(org_data_dlt):
    """Table name comes from the dir; multiple part files union into one table."""
    with DuckDBAnalyticsEngine(base_path=str(org_data_dlt)) as engine:
        tables = set(engine.register_all())
        assert tables == {"payments", "customers"}
        result = engine.execute("SELECT COUNT(*) AS n, SUM(amount) AS s FROM payments")
        assert result.success, result.error
        assert result.rows[0]["n"] == 3   # both parts
        assert result.rows[0]["s"] == 600


def test_introspect_returns_columns(org_data):
    with DuckDBAnalyticsEngine(base_path=str(org_data)) as engine:
        engine.register_all()
        schema = engine.introspect()
        assert set(schema.keys()) == {"payments", "customers"}
        payment_cols = {c["name"] for c in schema["payments"]}
        assert {"id", "amount", "currency", "status"} <= payment_cols


def test_execute_valid_select(org_data):
    with DuckDBAnalyticsEngine(base_path=str(org_data)) as engine:
        engine.register_all()
        result = engine.execute(
            "SELECT SUM(amount) AS total FROM payments WHERE status = 'success'"
        )
        assert result.success, result.error
        assert result.rows[0]["total"] == 12000
        assert result.row_count == 1


def test_cte_is_allowed(org_data):
    with DuckDBAnalyticsEngine(base_path=str(org_data)) as engine:
        engine.register_all()
        result = engine.execute(
            "WITH ok AS (SELECT * FROM payments WHERE status='success') "
            "SELECT COUNT(*) AS n FROM ok"
        )
        assert result.success, result.error
        assert result.rows[0]["n"] == 2


@pytest.mark.parametrize(
    "bad_sql",
    [
        "INSERT INTO payments VALUES (4, 1, 'NGN', 'success')",
        "UPDATE payments SET amount = 0",
        "DELETE FROM payments",
        "DROP TABLE payments",
        "CREATE TABLE evil AS SELECT 1",
        "PRAGMA database_list",
        "COPY payments TO '/tmp/x.csv'",
        "ATTACH 'x.db' AS y",
        "SELECT 1; DROP TABLE payments",  # stacked statements
    ],
)
def test_non_select_is_rejected(org_data, bad_sql):
    with DuckDBAnalyticsEngine(base_path=str(org_data)) as engine:
        engine.register_all()
        result = engine.execute(bad_sql)
        assert result.success is False
        assert result.error


def test_sandbox_blocks_reading_other_orgs_file(org_data, other_org_file):
    """After lock-down, generated SQL cannot read arbitrary Parquet paths."""
    with DuckDBAnalyticsEngine(base_path=str(org_data)) as engine:
        engine.register_all()
        result = engine.execute(
            f"SELECT * FROM read_parquet('{other_org_file}')"
        )
        # Either blocked by external-access lock or by function restrictions —
        # in every case it must NOT return the other org's row.
        assert result.success is False
        assert result.error


def test_row_cap_truncates(tmp_path):
    base = tmp_path / "org-big"
    base.mkdir()
    _write_parquet(
        str(base / "nums.parquet"),
        "SELECT i AS id FROM range(50) t(i)",
    )
    with DuckDBAnalyticsEngine(base_path=str(base)) as engine:
        engine.register_all()
        result = engine.execute("SELECT * FROM nums", max_rows=10)
        assert result.success, result.error
        assert result.row_count == 10
        assert result.truncated is True


def test_results_are_json_safe(org_data):
    """Decimal / date / timestamp cells must be coerced (stored in a JSON column)."""
    import json

    with DuckDBAnalyticsEngine(base_path=str(org_data)) as engine:
        engine.register_all()
        result = engine.execute(
            "SELECT CAST(1234.56 AS DECIMAL(18,2)) AS amt, "
            "DATE '2026-07-25' AS d, TIMESTAMP '2026-07-25 10:00:00' AS ts"
        )
        assert result.success, result.error
        row = result.rows[0]
        assert row["amt"] == 1234.56 and isinstance(row["amt"], float)
        assert row["d"] == "2026-07-25"
        assert row["ts"].startswith("2026-07-25T")
        # the whole row must be json.dumps-able
        json.dumps(result.rows)


def test_execute_before_lock_raises(org_data):
    engine = DuckDBAnalyticsEngine(base_path=str(org_data))
    with pytest.raises(SandboxError):
        engine.execute("SELECT 1")
    engine.close()


def test_requires_exactly_one_location(tmp_path):
    with pytest.raises(ValueError):
        DuckDBAnalyticsEngine()  # neither
    with pytest.raises(ValueError):
        DuckDBAnalyticsEngine(base_path=str(tmp_path), s3={"bucket": "x"})  # both
