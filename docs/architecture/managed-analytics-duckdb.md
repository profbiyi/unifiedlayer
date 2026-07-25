# Managed Analytics: DuckDB-over-Bucket

**Status:** Design (in build) · **Author:** Engineering · **Date:** 2026-07-25
**Related thesis chapters:** architecture, data governance / risk management

---

## 1. Why this exists

Today the AI features (Ask AI / NL-to-SQL, model generation) do **not** work for real
users, and this is the single biggest gap before pilot onboarding. Three concrete faults:

1. **Wrong database.** `QueryExecutor` runs generated SQL against the *platform's own
   Postgres* (`self.db`). Real users' synced data does not live there — dlt writes it to
   the org's **destination** (their warehouse or a bucket).
2. **Hardcoded schema.** `ai_schema_context.py` advertises tables to the LLM from a
   hardcoded map of **6 connector types** (stripe, paystack, xero, quickbooks, mono,
   truelayer). Any org whose sources are Postgres / MySQL / MongoDB / Sheets / CSV gets an
   **empty schema** → the model correctly answers "no data source connected." Verified live:
   only the one demo org with a supported connector *and* a physically-present table works.
3. **No tenant isolation in the query layer.** Generated SQL like
   `SELECT SUM(amount) FROM paystack_transactions` has no org filter. It is "correct" today
   only because a single org has data. Two orgs sharing a source type would read each
   other's rows. This is a data-governance defect, not just a demo bug.

The fix is not a patch — the analytics/AI **data plane** needs to be built for real, with
tenant isolation and a security-reviewed execution sandbox.

## 2. Product framing: two destination modes

We offer users a choice of where synced data lands:

| Mode | Where data lives | Who computes analytics | Primary user |
|------|------------------|------------------------|--------------|
| **BYO warehouse** | User's Snowflake / BigQuery / external Postgres | Their warehouse (their cost/tools) | Teams with existing data stack |
| **Managed (bucket)** | Object storage — **internal MinIO** *or* **external bucket** (their S3/GCS) | **On the platform, via DuckDB** | SMEs with no data team (our core ICP) |

**Design boundary (important):** on-platform BI + AI (dashboards, Ask AI, model generation)
is a feature of the **managed/bucket** path. BYO-warehouse users own their compute; we do
**not** attempt to run AI SQL against every external warehouse type (unbounded surface +
security exposure). BYO users can adopt the managed bucket later, or bring their own BI.

This is exactly the "best of both worlds" pitch: **the warehouse sits in a bucket, and
DuckDB connects it back to the platform** so the built-in AI can model it, answer questions,
and build dashboards.

## 3. The engine: DuckDB over the bucket

Data lands as **Parquet** in the org's bucket (dlt already has a `filesystem` destination
for s3/gcs/azure_blob). DuckDB reads Parquet directly — no separate warehouse to run.

```
 source ──dlt──▶  bucket (MinIO or S3/GCS)          ┌─ Ask AI (NL→SQL)
                   s3://ul-<orgslug>/<dataset>/*.parquet ─┤─ Model generation (star schema)
                        │                             └─ BI dashboards
                        ▼
                 DuckDB (httpfs + parquet)  ◀── introspection + read-only query
```

DuckDB is embedded (no server), speaks S3 (incl. MinIO via endpoint override), and is fast
on Parquet. One engine serves both storage locations — internal MinIO and external buckets
are the *same code path* with different endpoint/credentials.

### Components to build
- **`DuckDBAnalyticsEngine`** (`backend/services/duckdb_engine.py`) — opens a sandboxed
  DuckDB connection scoped to one org's bucket prefix; introspects tables; executes
  read-only SQL. *(Phase 1 — this PR.)*
- **Schema catalog** — persisted per-org table/column metadata so the LLM context is built
  without rescanning every file on each request (extends/replaces `ai_schema_context`).
- **Managed destination provisioning** — on org setup (managed mode), create the org's
  bucket/prefix and a `Destination` row pointing at it; default new pipelines to it.
- **Wire-in** — `QueryExecutor` and the model-generation service target the engine instead
  of the app Postgres, for managed-mode orgs.

## 4. Internal MinIO vs external bucket — recommendation

**Offer both. Default to internal MinIO. Position external as the data-sovereignty upgrade.**

### Internal MinIO (platform-hosted) — the default
- **Zero setup.** User picks "Managed warehouse" and syncs — no cloud account, no keys.
  This is decisive for SMEs who "can't afford a data team," our core ICP.
- **We control** uptime, backups, lifecycle, and the DuckDB path end-to-end.
- **Revenue-aligned:** storage/retention becomes a natural tier lever (Free vs Pro row/GB
  caps).
- **Cost/ops we own:** storage + egress + running MinIO. Mitigate with per-tier retention
  and Parquet compression.
- **Governance note:** data sits on platform infrastructure. Fine for most, but must be
  disclosed (NDPR/GDPR processor terms).

### External bucket (customer's own S3 / GCS / MinIO) — the sovereignty option
- **Data never leaves the customer's control** — their bucket, their region, their keys.
  This is *gold* for the **NDPR / data-residency** story and for regulated or larger SMEs.
  It directly backs the "Data Sovereignty" section already on the landing page.
- **Slightly more setup:** they provide a bucket + scoped credentials (ideally a
  least-privilege, prefix-scoped key).
- **Same DuckDB engine** queries it with their creds; we store creds encrypted
  (`EncryptedJSON`), never in logs.
- **We don't bear storage cost;** we do bear read/egress when querying.

### Recommendation matrix
| Concern | Internal MinIO | External bucket |
|---|---|---|
| Setup friction | ✅ none | ⚠️ bucket + key |
| Data sovereignty / NDPR | ⚠️ on our infra | ✅ their infra |
| Who pays storage | Us (tier it) | Them |
| Ops burden | Us | Them (bucket) + us (query) |
| Best for | SMEs, fast onboarding | Regulated / data-conscious / larger |

**Verdict:** internal MinIO as the frictionless default that gets pilot SMEs to value
fastest; external bucket as a one-toggle upgrade that turns our data-residency promise into
something real and demonstrable. Same engine, minimal extra code — worth doing both.

### Where does internal MinIO run?
- **Recommended:** a dedicated MinIO service on Railway (or a managed S3-compatible bucket,
  e.g. Cloudflare R2 / Backblaze B2 fronted as "internal") with a platform-owned key.
  R2/B2 have zero egress and are cheaper to operate than self-hosted MinIO — worth
  evaluating as the "internal" backing even though we brand it as managed. The engine treats
  all of these identically (S3 API + endpoint override).
- One bucket, **prefix per org** (`s3://ul-managed/org-<id>/...`), OR bucket per org. Prefix
  is simpler and cheaper; isolation is enforced in the engine (see §5).

## 5. Tenant isolation & security (risk-management core)

Running **LLM-generated SQL over customer data** is the sensitive heart of the feature. The
sandbox is a first-class requirement, not an afterthought — and it's the concrete substance
for the thesis risk-management chapter.

**Isolation**
- Each org maps to exactly one bucket **prefix** (or bucket). The engine is constructed with
  that prefix and only ever registers/opens paths under it.
- Generated SQL never receives a raw path; it references **registered views/table names**
  the engine created from the org's prefix. The LLM cannot name another org's data because
  it never sees other prefixes and cannot `read_parquet('s3://...other-org...')` (blocked,
  below).

**DuckDB sandbox** (enforced at connection construction)
- `SET enable_external_access=false` after registering the org's sources — blocks
  `read_csv`/`read_parquet` of arbitrary paths, `httpfs` to arbitrary hosts, and local
  `file://` access. Only pre-registered org views remain queryable.
- **Read-only:** reject any statement that isn't a single `SELECT`/CTE via the existing
  `sql_validator` (extended for DuckDB), plus a per-connection read-only guarantee.
- **Resource limits:** `SET memory_limit`, `SET threads`, statement timeout, and a hard row
  cap (already in `QueryExecutor`).
- **No secrets in prompts or logs:** bucket creds live in `EncryptedJSON`; the LLM sees
  schema only (table/column names + types), never credentials or rows beyond the result cap.

**Credential handling**
- The platform's shared managed-storage credentials are **never persisted** in a
  `Destination.config` row (that field is surfaced by the destinations API). The managed
  destination stores only non-secret routing info (bucket URL, prefix, region, endpoint);
  the real keys are injected from settings at sync time (`managed_storage.write_credentials`)
  and used server-side only by the DuckDB engine. Org-supplied external-bucket creds are
  stored via `EncryptedJSON` and likewise never returned.

**Auditability**
- Every AI query logged with org, user, generated SQL, row count, duration (feeds the audit
  trail + the thesis governance narrative).

## 6. Data layout & catalog
- dlt `filesystem` destination writes Parquet under `s3://<bucket>/<org-prefix>/<dataset>/<table>/`.
- A **catalog** table records, per org: table name, source, columns (name/type), row-count
  estimate, last-synced. Built/refreshed after each sync (cheap: read Parquet footer/schema,
  no full scan). The LLM schema context is built from the catalog — replacing the hardcoded
  6-connector map with the org's **actual** tables. This is what makes Ask AI work for every
  connector.

## 7. Phased delivery
1. **Engine foundation** *(this PR)* — `DuckDBAnalyticsEngine`: sandboxed connect, Parquet
   introspection, read-only execute, with unit tests over local Parquet fixtures. Additive;
   not yet wired to any live path. Adds `duckdb` dependency.
2. **Managed destination** — provision internal-MinIO prefix per org; `Destination` type +
   creation flow; default managed pipelines to it.
3. **Catalog + schema context** — populate catalog after sync; build LLM context from it;
   retire the hardcoded map.
4. **Wire AI to the engine** — Ask AI + model generation execute via
   `DuckDBAnalyticsEngine` for managed-mode orgs (Postgres path stays for legacy/BYO).
5. **External bucket option** — user-provided S3/GCS creds; same engine; sovereignty toggle
   in the connect flow.
6. **Hardening** — load/perf, retention tiers, full audit surfacing.

## 8. Open decisions
- **Internal backing:** self-hosted MinIO on Railway vs Cloudflare R2 / Backblaze B2 as the
  managed backing (recommend evaluating R2/B2 for cost + zero egress).
- **Bucket-per-org vs prefix-per-org** (recommend prefix; revisit if a customer demands
  hard bucket isolation).
- **BYO-warehouse AI:** confirm we scope on-platform AI to managed mode for the pilot.

## 9. Non-goals (for now)
- Running AI SQL against external warehouses (Snowflake/BigQuery) directly.
- Real-time/streaming query; this is batch analytics over synced Parquet.
- User-authored raw SQL editor against the bucket (future).
