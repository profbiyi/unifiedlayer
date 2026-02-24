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

## Known Issues / Open Bugs (as of 2026-02-24)

### Critical
1. **Missing Alembic migration for health tables** — `ResourceHealth` and `HealthCheckLog`
   models exist (`backend/models/health.py`) but have NO migration file. Health endpoints
   will 500 on first use in production unless tables are manually created.

2. **Broken Alembic migration chain** — Several recent migrations have `down_revision = None`
   instead of pointing to their predecessor:
   - `celery_task_id_dbt_runs` → should point to `add_oauth_columns`
   - `2026021701` (AI tables) → should point to `add_column_lineage` or `celery_task_id_dbt_runs`
   - `2026022001` (generated_models) → should point to `2026021702`
   This creates multiple migration heads; `alembic upgrade head` may fail or leave gaps.

3. **API key prefix mismatch** — `auth.py:create_api_key()` generates keys with `dpk_` prefix,
   but `auth.py:get_current_user_or_api_key()` validates keys with `dp_live_` prefix. The
   `api_keys.py` route correctly uses `dp_live_`. The `create_api_key()` / `verify_api_key()`
   functions in `auth.py` are dead/broken code. All API key logic should go through the route.

### High
4. **`.env.local` has wrong API URL** — `NEXT_PUBLIC_API_URL=http://localhost:4200` (Prefect)
   instead of `http://localhost:8000` (backend). Breaks local development.

5. **`NEXT_PUBLIC_API_URL` must include `/api/v1`** — The frontend hooks call paths like
   `/sources`, `/ai/ask`, etc. The backend serves these at `/api/v1/sources`, `/api/v1/ai/ask`.
   For this to work, `NEXT_PUBLIC_API_URL` in production must be set to
   `https://api.unifiedlayer.io/api/v1` (NOT just the domain). `.env.example` is misleading.

### Medium
6. **Hacky `__import__` in cross_source.py:301** — Should use a top-level `from datetime import datetime, timezone`
7. **No Celery beat schedule for health checks** — Health tasks run on-demand only, not periodically
8. **Unauthenticated `/config` endpoint** — Exposes CORS config, rate limit settings, etc.
9. **`/stats` and `/metrics` are unauthenticated** — Prometheus metrics and DB stats exposed publicly
10. **OAuth columns added via raw SQL in startup** — Should be purely in the alembic migration

### Low
11. **`ScrollArea` ref may not work for auto-scroll in `/ask` page** — shadcn ScrollArea doesn't
    always forward refs; auto-scroll on new messages may silently fail.
12. **No tests for new features** — AI assistant, health, onboarding, cross-source, column lineage
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

---

*This file is read by Claude Code to understand the project context. Update it when major features are added.*
