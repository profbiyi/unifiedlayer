# UnifiedLayer - Project Context for Claude

## Overview

UnifiedLayer is a cloud-based data integration and analytics platform for SMEs, similar to Fivetran/Airbyte but focused on the African and UK markets. It enables businesses to sync data from various sources (payment processors, accounting software, banks) to data warehouses, with built-in transformations, quality checks, and business insights.

**Live URLs:**
- Frontend: https://unifiedlayer.io (Railway deployment)
- Backend API: Deployed on Railway
- GitHub: https://github.com/profbiyi/unifiedlayer

## Tech Stack

### Backend
- **Framework:** FastAPI (Python 3.11+)
- **Database:** PostgreSQL with SQLAlchemy ORM
- **Auth:** JWT tokens with bcrypt password hashing, TOTP 2FA support
- **Task Queue:** Celery with Redis (for async pipeline runs)
- **Billing:** Stripe (UK/EU) + Paystack (Africa - NGN, KES, GHS)
- **Deployment:** Railway with Docker

### Frontend
- **Framework:** Next.js 14 (App Router)
- **Styling:** Tailwind CSS + shadcn/ui components
- **State:** TanStack Query (React Query) for server state
- **Charts:** Recharts
- **Animations:** Framer Motion
- **Deployment:** Railway with Docker

## Project Structure

```
data-platform/
├── backend/
│   ├── api/
│   │   ├── main.py              # FastAPI app entry
│   │   └── routes/              # API route modules
│   │       ├── auth.py          # Auth endpoints (login, register, 2FA)
│   │       ├── pipelines.py     # Pipeline CRUD and runs
│   │       ├── sources.py       # Data source management
│   │       ├── destinations.py  # Destination management
│   │       ├── connectors.py    # Connector catalog
│   │       ├── billing.py       # Stripe/Paystack billing
│   │       ├── admin.py         # Super admin cross-org access
│   │       ├── webhooks.py      # Webhook ingestion
│   │       ├── notifications.py # In-app notifications
│   │       ├── transformations.py # SQL transformations
│   │       ├── dbt.py           # dbt orchestration
│   │       ├── alerts.py        # Alerting system
│   │       └── gdpr.py          # GDPR compliance
│   ├── models/                  # SQLAlchemy models
│   │   ├── pipeline.py          # Core models (Org, User, Pipeline, etc.)
│   │   ├── billing.py           # Subscription, Invoice, UsageRecord
│   │   ├── rbac.py              # Roles, Permissions, UserRole
│   │   ├── audit.py             # AuditLog, SuperAdminAccessLog
│   │   ├── transformation.py    # SQLTransformation, TransformationResult
│   │   ├── dbt.py               # DbtProject, DbtRun
│   │   └── notification.py      # Notification model
│   ├── connectors/              # Data source connectors
│   │   ├── sdk.py               # BaseConnector SDK
│   │   ├── stripe_connector.py
│   │   ├── paystack_connector.py
│   │   ├── quickbooks_connector.py
│   │   ├── xero_connector.py
│   │   ├── sage_connector.py
│   │   ├── freeagent_connector.py
│   │   ├── postgres_connector.py
│   │   ├── mysql_connector.py
│   │   ├── mongodb_connector.py
│   │   └── csv_connector.py
│   ├── services/                # Business logic
│   │   ├── billing_service.py   # Stripe/Paystack integration
│   │   ├── pipeline_service.py  # Pipeline execution
│   │   └── alert_service.py     # Slack/email alerting
│   ├── utils/
│   │   └── encrypted_type.py    # EncryptedJSON for credentials
│   └── config.py                # Settings from environment
├── frontend/
│   ├── app/                     # Next.js App Router pages
│   │   ├── (auth)/              # Auth pages (login, register, etc.)
│   │   ├── (dashboard)/         # Protected dashboard pages
│   │   │   ├── overview/        # Main dashboard
│   │   │   ├── pipelines/       # Pipeline management
│   │   │   ├── sources/         # Source management
│   │   │   ├── destinations/    # Destination management
│   │   │   ├── runs/            # Pipeline run history
│   │   │   ├── lineage/         # Data lineage visualization
│   │   │   ├── analytics/       # Usage analytics
│   │   │   ├── insights/        # Business insights (revenue, cash flow)
│   │   │   ├── team/            # Team management
│   │   │   ├── admin/           # Super admin panel
│   │   │   ├── settings/        # User/org settings
│   │   │   │   ├── billing/     # Subscription management
│   │   │   │   ├── security/    # 2FA settings
│   │   │   │   ├── alerts/      # Alert configuration
│   │   │   │   ├── dbt/         # dbt project management
│   │   │   │   └── privacy/     # GDPR controls
│   │   │   └── templates/       # Pipeline templates
│   │   └── developers/          # Public developer portal
│   │       └── connectors/      # Connector catalog
│   ├── components/
│   │   ├── ui/                  # shadcn/ui components
│   │   ├── layout/              # Sidebar, Header
│   │   ├── skeletons/           # Loading skeletons
│   │   ├── animations/          # Page transitions
│   │   ├── pipelines/           # Pipeline-specific components
│   │   ├── sources/             # Source wizard forms
│   │   └── dbt/                 # dbt UI components
│   ├── hooks/queries/           # TanStack Query hooks
│   └── lib/
│       └── api-client.ts        # Axios instance with auth
└── docker-compose.yml           # Local development
```

## Key Features Built

### 1. Authentication & Authorization
- JWT-based auth with access/refresh tokens
- Email verification flow
- Password reset flow
- TOTP-based 2FA (Google Authenticator compatible)
- Role-based access control (SUPER_ADMIN, ORG_ADMIN, ORG_USER)
- API key authentication for programmatic access

### 2. Multi-Tenant Organizations
- Organization-scoped data isolation
- Team invitations with role assignment
- Super admin cross-org access for support (with audit logging)
- 15-minute impersonation sessions

### 3. Data Connectors (11 connectors)
- **Payment:** Stripe, Paystack
- **Accounting:** QuickBooks, Xero, Sage, FreeAgent
- **Banking:** Mono (African banks), TrueLayer (UK Open Banking)
- **Database:** PostgreSQL, MySQL, MongoDB
- **File:** CSV upload

### 4. Pipeline Management
- Visual pipeline builder
- Schedule-based (cron) and manual triggers
- Incremental sync support
- Pipeline templates for quick setup
- Pipeline cloning

### 5. SQL Transformations
- In-pipeline SQL transformations
- Monaco editor with SQL syntax highlighting
- Drag-and-drop ordering
- Execution timeout and error handling
- Continue-on-error option

### 6. dbt Orchestration
- GitHub repo integration for dbt projects
- Run dbt after pipeline sync
- Job tracking and logs
- Multiple projects per organization

### 7. Alerting System
- Slack webhook integration
- Email notifications
- Pipeline failure alerts
- Usage threshold alerts
- Configurable per-pipeline

### 8. Billing & Subscriptions
- **Stripe:** GBP/EUR payments
- **Paystack:** NGN/KES/GHS payments
- Three tiers: Free Trial, Professional (£35/mo), Enterprise
- Usage metering (rows synced, API calls, pipeline runs)
- Customer portal for self-service

### 9. GDPR Compliance
- Data export (JSON/CSV)
- Account deletion with cascade
- Consent tracking
- Data retention policies

### 10. Webhook Ingestion
- Receive webhooks from external services
- Transform and route to destinations
- Signature verification

### 11. Business Insights
- Revenue trends
- Cash flow analysis
- Invoice aging
- Tax summaries (UK VAT/MTD ready)

### 12. UI/UX Polish
- Skeleton loaders for all listing pages
- Page transitions with Framer Motion
- Breadcrumb navigation on detail pages
- Success animations (confetti, checkmarks)
- Dark/light mode

## Database Models

### Core
- `Organization` - Multi-tenant organizations
- `User` - Users with org membership
- `DataSource` - Configured data sources
- `Destination` - Target warehouses
- `Pipeline` - ETL pipeline definitions
- `PipelineRun` - Execution history

### RBAC
- `Role` - SUPER_ADMIN, ORG_ADMIN, ORG_USER
- `Permission` - resource:action pairs
- `UserRole` - Role assignments
- `UserInvitation` - Pending invitations

### Billing
- `Subscription` - Plan and Stripe/Paystack IDs
- `Invoice` - Payment history
- `UsageRecord` - Monthly usage tracking

### Features
- `SQLTransformation` - SQL transforms per pipeline
- `DbtProject` - dbt GitHub configurations
- `DbtRun` - dbt execution history
- `Notification` - In-app notifications
- `WebhookEvent` - Ingested webhooks
- `AuditLog` - User action audit trail

## API Endpoints Summary

### Auth (`/auth`)
- POST `/login` - Get access token
- POST `/register` - Create account
- GET `/me` - Current user
- POST `/2fa/setup` - Start 2FA setup
- POST `/2fa/verify-setup` - Complete 2FA
- POST `/verify-email` - Verify email token

### Pipelines (`/pipelines`)
- GET/POST `/` - List/create pipelines
- GET/PUT/DELETE `/{id}` - Pipeline CRUD
- POST `/{id}/run` - Trigger run
- GET `/{id}/runs` - Run history

### Sources (`/sources`)
- GET/POST `/` - List/create sources
- GET/PUT/DELETE `/{id}` - Source CRUD
- POST `/{id}/test` - Test connection

### Billing (`/billing`)
- GET `/plans` - Available plans
- GET `/subscription` - Current subscription
- POST `/checkout` - Stripe checkout
- POST `/paystack/checkout` - Paystack checkout
- GET `/usage` - Current usage

### Admin (`/admin`) - Super admin only
- GET `/organizations` - All orgs
- GET `/organizations/{slug}` - Org details
- POST `/impersonate/start` - Start impersonation
- POST `/impersonate/stop` - End impersonation

## Environment Variables

### Backend
```
DATABASE_URL=postgresql://...
SECRET_KEY=your-jwt-secret
ENCRYPTION_KEY=32-byte-fernet-key
STRIPE_SECRET_KEY=sk_...
STRIPE_WEBHOOK_SECRET=whsec_...
PAYSTACK_SECRET_KEY=sk_...
REDIS_URL=redis://...
FRONTEND_URL=https://unifiedlayer.io
```

### Frontend
```
NEXT_PUBLIC_API_URL=https://api.unifiedlayer.io
```

## Deployment

Both services deploy on Railway via GitHub push to `main`:

- **Backend:** Python + FastAPI in Docker
- **Frontend:** Next.js in Docker with static optimization

Railway handles:
- PostgreSQL database
- Redis for Celery
- Environment variables
- SSL/HTTPS
- Health checks

## Pricing Tiers

| Feature | Free Trial | Professional | Enterprise |
|---------|-----------|--------------|------------|
| Price | Free (30 days) | From £35/mo | Custom |
| Rows/month | 5,000 | 100,000 | Unlimited |
| Connectors | 1 | 5 | Unlimited |
| Team members | 1 | 3 | Unlimited |
| Pipelines | 1 | 10 | Unlimited |

## Common Tasks

### Adding a new connector
1. Create `backend/connectors/{name}_connector.py`
2. Extend `BaseConnector` from SDK
3. Implement `extract()`, `get_schema()`, `test_connection()`
4. Add to connector registry
5. Add form to `frontend/components/sources/forms/`

### Adding a new API endpoint
1. Create route in `backend/api/routes/`
2. Add router to `main.py`
3. Create Pydantic schemas in `backend/schemas/`
4. Add TanStack Query hook in `frontend/hooks/queries/`

### Adding a new database column or table (schema change)
Always use Alembic — never edit models without a migration:
```bash
# 1. Make your changes to the SQLAlchemy model in backend/models/
# 2. Generate the migration (run from repo root)
alembic revision --autogenerate -m "add_column_foo_to_pipelines"
# 3. Review the generated file in alembic/versions/ — check it looks right
# 4. Commit both the model change and the migration file together
# 5. On next deploy, startup.sh runs `alembic upgrade head` automatically
```
**Rule**: If you add a model to `backend/models/`, also import it in
`backend/models/__init__.py` or `Base.metadata.create_all()` / Alembic will fail
with `NoReferencedTableError` at startup.

### Running locally
```bash
# Backend
cd backend
pip install -r requirements.txt
uvicorn backend.api.main:app --reload

# Frontend
cd frontend
npm install
npm run dev
```

## Recent Changes (Feb 2026)

1. Created beautiful connectors catalog page at `/developers/connectors`
2. Added skeleton loaders, page transitions, breadcrumbs
3. Fixed production issues (fonts, TypeScript errors, middleware)
4. Updated pricing display (Professional from £35/mo, Free is 30-day trial)
5. Added super admin cross-org access with audit logging
6. Completed SQL transformations and dbt orchestration features
7. Added alerting system with Slack/email integration
8. Added AI Assistant (NL-to-SQL) with `/ask` page — requires `OPENAI_API_KEY`
9. Added Health Monitoring (ResourceHealth, HealthCheckLog models + `/health` routes)
10. Added Onboarding wizard with role-based source recommendations
11. Added Column Lineage tables and parser service
12. Added Cross-Source Modeling + Generated Models
13. Added Celery task queue with dbt tasks and health check tasks
14. Removed self-registration — super admin invites users only
15. Added AI Conversation tables (migrations: 2026021701/2026021702)
16. Added Onboarding progress table (migration: 2026021702)
17. Added Generated Models table (migration: 2026022001)

## Engineering Fixes (Feb 2026 — commits 577b17a → cb74f98)

### CI Pipeline (all 193 tests now green)
- Rewrote `backend/tests/test_uk_connectors.py` to match actual connector implementations
  (class-level `metadata`, `_session.get` mocking, flat config schema, list-style `tables` arg)
- Fixed `test_connector_sdk.py`: removed unused `ConnectorCapabilities` import (Ruff F401)
- Fixed `test_billing.py`: `p["name"]` → `p["plan"]` (field is `plan` in `PlanDetailsResponse`)
- Fixed `test_email_verification.py`: mock `_refresh()` sets `obj.two_factor_enabled = False`
  (Pydantic v2 rejects `None` for a `bool` field even when the column default is `False`)
- Removed `docker-build` job from `.github/workflows/ci.yml` — Railway builds from source
  directly; DockerHub credentials were never configured and the job was always failing

### Railway Deployment Crash (NoReferencedTableError)
- **Root cause**: `startup.sh` runs `Base.metadata.create_all()` which failed because
  `ColumnLineage` has `ForeignKey("dbt_runs.id")` but `DbtRun`/`DbtProject` from
  `backend/models/dbt.py` were never imported into `backend/models/__init__.py`.
  SQLAlchemy couldn't resolve the FK → `NoReferencedTableError` → exit 1 → uvicorn
  never started → Railway healthcheck always timed out.
- **Fix**: Added to `backend/models/__init__.py`:
  - `DbtProject`, `PipelineDbtConfig`, `DbtRun`, `DbtRunStatus` from `models/dbt.py`
  - `OnboardingProgress`, `OnboardingStatus` from `models/onboarding.py`
  - `OnboardingUserRole` alias (avoids name clash with RBAC `UserRole`)
- **Rule**: Any SQLAlchemy model that is referenced by a ForeignKey in another model
  **must** be imported in `models/__init__.py` or `create_all()` / Alembic will fail.

### Super Admin Password Preservation
- `create_super_admin.py` previously overwrote the super admin password on **every** deploy
  (back to `SUPER_ADMIN_PASSWORD` env var or the `Admin123!` default), reverting any
  password change made in the app.
- **Fix**: Script now skips existing users entirely and only ensures `is_active`,
  `is_superuser`, and `email_verified` are `True`. Password is only set on first creation.

### Deployment Strategy: Switched from `create_all()` to Alembic
- **Old behaviour**: `startup.sh` called `Base.metadata.create_all()` on every deploy.
  This is `CREATE TABLE IF NOT EXISTS` — safe for existing rows but **cannot add new
  columns to existing tables**. Any schema change (new column, index, constraint) would
  silently be missing in production and cause 500 errors.
- **New behaviour** (`backend/scripts/startup.sh`):
  1. Detect whether the DB was previously managed by `create_all()` (has app tables but
     no `alembic_version` row). If so: call `create_all()` once to fill any missing tables,
     then `alembic stamp head` to mark the schema as fully migrated.
  2. On a fresh DB: `alembic upgrade head` runs all migrations to create tables.
  3. On an already-migrated DB: `alembic upgrade head` applies only pending migrations.
- **Customer data safety**: existing rows are **never** touched by this process.
  `RESET_DATABASE=true` env var is the only way to wipe data — it must be set explicitly
  in Railway and should never be set in production.

## New Features Added (Routes, Models, Services)

### New Backend Routes (all registered in main.py under /api/v1)
- `/ai` — AI Assistant (NL-to-SQL): `backend/api/routes/ai_assistant.py`
- `/health` — Health monitoring: `backend/api/routes/health.py`
- `/onboarding` — Onboarding wizard: `backend/api/routes/onboarding.py`
- `/models` — Generated data models: `backend/api/routes/models.py`
- `/cross-source` — Cross-source modeling: `backend/api/routes/cross_source.py`
- `/dashboards` — Auto dashboards: `backend/api/routes/dashboards.py`
- `/recipes` — Pipeline recipes: `backend/api/routes/recipes.py`

### New Models
- `backend/models/ai.py` — AIConversation, AIMessage (MessageRole, ChartType enums)
- `backend/models/health.py` — ResourceHealth, HealthCheckLog (ResourceType, HealthStatus enums)
- `backend/models/onboarding.py` — OnboardingProgress (UserRole, OnboardingStatus enums)
- `backend/models/data_model.py` — GeneratedModel
- `backend/models/column_lineage.py` — ColumnLineage

### New Services
- `backend/services/nl_to_sql.py` — NL to SQL conversion (OpenAI)
- `backend/services/ai_schema_context.py` — Schema context builder for AI
- `backend/services/sql_validator.py` — SQL safety validation
- `backend/services/query_executor.py` — Execute SQL queries
- `backend/services/auto_visualize.py` — Auto chart type detection
- `backend/services/health_monitor.py` — Source/pipeline/destination health checks
- `backend/services/onboarding_service.py` — Onboarding progress tracking
- `backend/services/cross_source_modeler.py` — Cross-source data modeling
- `backend/services/dashboard_service.py` — Auto-dashboard generation
- `backend/services/column_lineage_service.py` — Column lineage tracking
- `backend/services/column_lineage_parser.py` — Parse SQL for column lineage
- `backend/services/dbt_executor.py` — dbt execution service
- `backend/services/dbt_manifest_parser.py` — Parse dbt manifests

### New Frontend Pages
- `/ask` — AI chat interface (components in `frontend/components/ai/`)
- `/models` — Generated data models list
- `/models/[id]` — Model detail with analyze tab
- `/onboarding` — Onboarding wizard
- `/settings/ai-modeling` — AI modeling settings

### Celery Tasks
- `backend/celery_app.py` — Celery app config (broker: Redis)
- `backend/tasks/dbt_tasks.py` — Async dbt job execution
- `backend/tasks/health_checks.py` — Periodic health check tasks

## DBA2 Repositioning (July 2026 — branch `dba2/africa-first`, PR #1)

UnifiedLayer is the prototype artefact for Ahmed's DBA Year 2 thesis (Africa-centric
data integration for fintech SMEs, Nigeria + France). The public site must stay
**Africa-first** — the thesis jury will visit unifiedlayer.io in December 2026.

**Backup of the previous (Europe-positioned) version:** branch `backup/europe-positioning`,
tag `backup/europe-version-2026-07-13`, archive `~/Desktop/unifiedlayer-backup-europe-2026-07-13.tar.gz`.

Changes:
- Landing page: Africa-first hero + "Built for Africa First" card, new Data Sovereignty
  section (local residency, NDPR/GDPR), visible pricing (From £35/mo, local currencies),
  15-day guided trial copy (was 30-day self-serve)
- `/request-access` public form replaces all mailto Request Access / Contact Sales links.
  Gated trial model: form → discovery call → 15-day guided trial → feedback form
- `AccessRequest` model (`backend/models/access_request.py`) + migration `2026071301`
  + routes (`backend/api/routes/access_requests.py`): public POST, super-admin GET/PATCH
  with funnel statuses (new → contacted → discovery_scheduled → qualified → trial_active / declined)
- Tests: `backend/tests/test_access_requests.py`
- Demo scenarios: `python -m backend.scripts.seed_demo_scenarios` seeds 3 demo orgs
  (NairaLink Payments = payment provider, KoboVault Wallet = mobile wallet,
  SwiftCredit MFB = micro-lender) with sources, warehouse destinations, scheduled
  pipelines, and ~45 days of run history for the demo video. Idempotent by org slug.
  Demo admin password: `DEMO_ADMIN_PASSWORD` env (default `DemoTrial2026!`).

## Known Issues / Open Bugs (as of 2026-03-05)

### Fixed ✅ (all resolved in commits 577b17a → bc3e1ac)
- ~~Broken Alembic migration chain~~ — fixed, all `down_revision` values corrected
- ~~Missing health tables migration~~ — migration `2026_02_24_0001-add_health_tables.py` added
- ~~API key prefix mismatch (`dpk_` vs `dp_live_`)~~ — dead `create_api_key`/`verify_api_key` removed from `auth.py`
- ~~`.env.local` pointing to Prefect (4200)~~ — fixed to `http://localhost:8000/api/v1`
- ~~`__import__` hack in `cross_source.py`~~ — replaced with top-level import
- ~~OAuth columns added via raw SQL in startup~~ — removed from startup; lives only in migration
- ~~`models/__init__.py` missing `DbtRun`, `DbtProject`, `OnboardingProgress`~~ — fixed (caused Railway crash)
- ~~Super admin password reset on every deploy~~ — fixed; existing users are left untouched
- ~~`create_all()` used in production~~ — replaced with `alembic upgrade head` (with stamp fallback)
- ~~Railway crash: `weasyprint` import raises `OSError` on `python:3.11-slim`~~ — fixed; `except (ImportError, OSError)` in `pdf_service.py`
- ~~Railway crash: migrations `2026022503` + `2026030501` not idempotent~~ — fixed; `DO $$ BEGIN...EXCEPTION WHEN duplicate_object` + `IF NOT EXISTS` throughout
- ~~PostgreSQL enum DDL error in CI tests~~ — `writemodeEnum`/`schemaContractEnum` renamed to
  `write_mode_enum`/`schema_contract_enum` (snake_case); `server_default` removed from model
  columns so `create_all()` generates no `DEFAULT` clause (Python-side `default=` handles it);
  migration retains `server_default` for the `ADD COLUMN` on production tables (commits 0bce68f/bc3e1ac)

### Medium
1. **No Celery beat schedule for health checks** — Health tasks run on-demand only, not periodically
2. **Unauthenticated `/config` endpoint** — Exposes CORS config, rate limit settings, etc.
3. **`/stats` and `/metrics` are unauthenticated** — Prometheus metrics and DB stats exposed publicly

### Low
4. **`ScrollArea` ref may not work for auto-scroll in `/ask` page** — shadcn ScrollArea doesn't
   always forward refs; auto-scroll on new messages may silently fail.
5. **No tests for new features** — AI assistant, health, onboarding, cross-source, column lineage
   have zero test coverage.

## API URL Convention (IMPORTANT)
- Backend routes are ALL under `/api/v1` prefix
- `NEXT_PUBLIC_API_URL` in production = `https://api.unifiedlayer.io/api/v1`
- In local dev = `http://localhost:8000/api/v1` (NOT just `http://localhost:8000`)
- The `.env.local` has a bug: it points to Prefect (4200) — fix to `http://localhost:8000/api/v1`

## API Key Convention (IMPORTANT)
- API keys are generated with prefix `dp_live_` (see `backend/api/routes/api_keys.py`)
- Keys are validated with `dp_live_` prefix in `backend/auth.py:get_current_user_or_api_key()`
- The `create_api_key()` / `verify_api_key()` helper functions in `auth.py` use `dpk_` prefix
  and are dead code — do NOT use them. All API key management goes through the routes.

## Environment Variables (Additional)
- `OPENAI_API_KEY` — Required for AI Assistant (/ask) feature; gracefully degrades if missing
- `REDIS_URL` — Required for Celery task queue (dbt tasks, health checks)
- `SUPER_ADMIN_EMAIL` — Super admin email (default: `admin@unifiedlayer.io`)
- `SUPER_ADMIN_PASSWORD` — Super admin password set on **first deploy only** (default: `Admin123!`).
  After first creation the password is never overwritten by deploys. Set this in Railway before
  first deploy, then change the password in-app afterwards.
- `RESET_DATABASE` — Set to `true` to wipe the entire DB schema on next deploy.
  **NEVER set this in production.** Only for dev environment resets.

---

*This file is read by Claude Code to understand the project context. Update it when major features are added.*
