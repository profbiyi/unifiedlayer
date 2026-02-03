# UnifiedLayer

The data integration and analytics platform built for SMEs. Connect all your data sources — conventional and unconventional — into a single source of truth.

## Features

- **17 Source Connectors**: PostgreSQL, MySQL, MongoDB, M-Pesa, Paystack, Flutterwave, MTN MoMo, GoCardless, Xero, HMRC MTD, Open Banking, Google Sheets, REST API, WhatsApp, CSV, Local Files
- **8 Destinations**: PostgreSQL, DuckDB, BigQuery, Snowflake, Redshift, S3, GCS, Azure Blob
- **Pipeline Orchestration**: Prefect 3 with scheduling, retries, CDC
- **Data Quality**: 7 check types with severity levels
- **Data Lineage**: Full end-to-end tracking with visualization
- **Multi-tenancy**: Organization isolation with RBAC
- **Billing**: Stripe + Paystack integration

## Quick Start (Docker)

```bash
# Copy environment file
cp docker/.env.example docker/.env

# Start all services
docker compose -f docker/docker-compose.yml up -d

# Access the application
open http://localhost
```

## Services

| Service | URL | Description |
|---------|-----|-------------|
| Frontend | http://localhost | Next.js application |
| API | http://localhost/api | FastAPI backend |
| API Docs | http://localhost/api/docs | Swagger UI |
| Prefect | http://localhost/prefect | Workflow orchestration |
| Grafana | http://localhost/grafana | Monitoring dashboards |

## Tech Stack

- **Backend**: Python 3.11, FastAPI, SQLAlchemy 2.0, Prefect 3
- **Frontend**: Next.js 14, TypeScript, Tailwind CSS, shadcn/ui
- **Database**: PostgreSQL 15
- **Monitoring**: Prometheus, Grafana

## License

Proprietary - UnifiedLayer. All rights reserved.
