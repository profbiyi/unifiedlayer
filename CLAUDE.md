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

---

*This file is read by Claude Code to understand the project context. Update it when major features are added.*
