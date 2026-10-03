"""Proves the async request path works end-to-end (asyncpg + AsyncSession).

Hits /health/async-db, which awaits `SELECT 1` through an AsyncSession. No fixture
data is needed, so this validates the async stack itself (driver, engine, session,
dependency) against the CI Postgres.
"""


def test_async_db_roundtrip(client):
    resp = client.get("/health/async-db")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["driver"] == "async (asyncpg)"
