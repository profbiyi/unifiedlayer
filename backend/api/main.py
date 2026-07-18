"""
FastAPI Application.

Main application entry point with authentication, health checks,
metrics, CORS, and error handling.
"""
from datetime import datetime, timezone
from typing import Dict, Any
import logging
import time
import json

from fastapi import FastAPI, APIRouter, Request, status, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from starlette.responses import Response
from sqlalchemy.orm import Session

from backend.config import settings
from backend.database import get_db, init_db, DatabaseHealthCheck
from backend.middleware import RateLimitMiddleware, SecurityHeadersMiddleware, AuthRateLimitMiddleware, RequestIDMiddleware
from backend.utils.errors import ErrorResponse, ErrorCodes, get_request_id
from backend.auth import get_current_user
from backend.models.pipeline import User

# Import API routes
from backend.api.routes import (
    auth,
    two_factor,
    pipelines,
    sources,
    destinations,
    organizations,
    users,
    runs,
    lineage,
    source_discovery,
    destination_discovery,
    api_preview,
    admin,
    invitations,
    roles,
    metrics,
    quality,
    templates,
    billing,
    connectors,
    analytics,
    sme_insights,
    oauth,
    audit,
    api_keys,
    webhooks,
    notifications,
    exports,
    gdpr,
    transformations,
    alerts,
    dbt,
    dashboards,
    recipes,
    ai_assistant,
    onboarding,
    health,
    models,
    cross_source,
    access_requests,
)
from backend.api.routes.anomaly import router as anomaly_router
from backend.api.routes.summaries import router as summaries_router
from backend.api.routes.reports import router as reports_router
from backend.api.routes.whatsapp_test import router as whatsapp_test_router

class CustomJSONResponse(JSONResponse):
    """Custom JSON response that properly serializes datetimes with timezone."""

    def render(self, content: Any) -> bytes:
        return json.dumps(
            content,
            ensure_ascii=False,
            allow_nan=False,
            indent=None,
            separators=(",", ":"),
            default=self._json_serializer,
        ).encode("utf-8")

    @staticmethod
    def _json_serializer(obj):
        """Serialize datetime objects to ISO 8601 with UTC timezone."""
        if isinstance(obj, datetime):
            # If datetime is naive, assume UTC
            if obj.tzinfo is None:
                obj = obj.replace(tzinfo=timezone.utc)
            # Return ISO 8601 format with 'Z' suffix for UTC
            return obj.isoformat().replace('+00:00', 'Z')
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


# Create API v1 router for versioned endpoints
api_v1_router = APIRouter(prefix="/api/v1")

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Prometheus metrics
REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
)
REQUEST_DURATION = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"],
)
PIPELINE_RUNS = Counter(
    "pipeline_runs_total",
    "Total pipeline runs",
    ["pipeline_name", "status"],
)
DATA_ROWS_PROCESSED = Counter(
    "data_rows_processed_total",
    "Total data rows processed",
    ["pipeline_name"],
)

# Configure JSON encoder for FastAPI

def custom_json_dumps(obj):
    """Custom JSON dumps with datetime handling."""
    def default(o):
        if isinstance(o, datetime):
            if o.tzinfo is None:
                o = o.replace(tzinfo=timezone.utc)
            return o.isoformat().replace('+00:00', 'Z')
        raise TypeError(f"Object of type {type(o)} is not JSON serializable")

    return json.dumps(obj, default=default)

# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="""
# UnifiedLayer API

Cloud-based data integration and analytics platform for SMEs. Turn fragmented data into clarity.

## Key Features
- **8+ Source Connectors** — PostgreSQL, MySQL, REST API, M-Pesa, WhatsApp, GoCardless, Xero, Open Banking
- **8+ Destinations** — PostgreSQL, BigQuery, Snowflake, Redshift, S3, GCS, DuckDB
- **Pipeline Orchestration** — Scheduling, retries, CDC, auto-scaling workers
- **Data Lineage** — Table and column-level lineage tracking
- **Data Quality** — 7 built-in quality check types
- **Multi-Tenant** — Organization-based isolation with RBAC
- **Billing** — Stripe integration with usage metering
- **Connector SDK** — Build custom connectors with our plugin system

## Authentication
All endpoints (except `/auth/login`, `/auth/register`, `/billing/plans`, `/connectors/`) require a JWT Bearer token.

```
Authorization: Bearer <your_token>
```

## Rate Limits
- General: 100 requests/minute
- Auth endpoints: 10 requests/minute

## SDKs
- **Python:** `pip install unifiedlayer-sdk` (coming soon)
- **JavaScript:** `npm install @unifiedlayer/sdk` (coming soon)
""",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    default_response_class=CustomJSONResponse,
    openapi_tags=[
        {"name": "Authentication", "description": "Login, register, JWT tokens"},
        {"name": "Pipelines", "description": "Create, manage, and run data pipelines"},
        {"name": "Sources", "description": "Data source management"},
        {"name": "Destinations", "description": "Destination management"},
        {"name": "Runs", "description": "Pipeline execution tracking"},
        {"name": "Lineage", "description": "Data lineage graphs"},
        {"name": "Quality", "description": "Data quality checks"},
        {"name": "dbt Orchestration", "description": "dbt project management and run execution"},
        {"name": "Pipeline dbt Config", "description": "Pipeline dbt transformation configuration"},
        {"name": "Billing", "description": "Subscriptions, usage, and payments"},
        {"name": "Connector SDK", "description": "Available connectors and their schemas"},
        {"name": "Organizations", "description": "Multi-tenant organization management"},
        {"name": "Users", "description": "User management"},
        {"name": "Roles", "description": "Role-based access control"},
        {"name": "Monitoring", "description": "Metrics and health checks"},
    ],
)

# CORS middleware
# Note: When using credentials (cookies), we cannot use "*" as origin
# Must specify exact origins for security
if settings.CORS_ORIGINS == "*":
    # Development mode: allow localhost origins
    cors_origins = [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
    ]
else:
    cors_origins = settings.CORS_ORIGINS.split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,  # Required for HTTPOnly cookies
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID", "X-Idempotency-Key"],
    expose_headers=["X-Request-ID", "X-RateLimit-Limit", "X-RateLimit-Remaining", "X-RateLimit-Reset"],
)

# Request ID middleware (add first so all middlewares have access)
app.add_middleware(RequestIDMiddleware)

# Security middleware
app.add_middleware(SecurityHeadersMiddleware)

# Auth-specific rate limiting (stricter limits for login, password reset, etc.)
app.add_middleware(AuthRateLimitMiddleware)

# General rate limiting middleware
app.add_middleware(
    RateLimitMiddleware,
    requests_per_minute=settings.RATE_LIMIT_PER_MINUTE,
)

# Include API routers under /api/v1 prefix
api_v1_router.include_router(auth.router)
api_v1_router.include_router(two_factor.router)
api_v1_router.include_router(organizations.router)
api_v1_router.include_router(users.router)
api_v1_router.include_router(sources.router)
api_v1_router.include_router(source_discovery.router)
api_v1_router.include_router(api_preview.router)
api_v1_router.include_router(destinations.router)
api_v1_router.include_router(destination_discovery.router)
api_v1_router.include_router(pipelines.router)
api_v1_router.include_router(transformations.router)
api_v1_router.include_router(dbt.router)
api_v1_router.include_router(dbt.pipeline_dbt_router)
api_v1_router.include_router(runs.router)
api_v1_router.include_router(lineage.router)
api_v1_router.include_router(metrics.router)
api_v1_router.include_router(quality.router)

api_v1_router.include_router(templates.router)
api_v1_router.include_router(billing.router)
api_v1_router.include_router(connectors.router)
api_v1_router.include_router(analytics.router)
api_v1_router.include_router(sme_insights.router)
api_v1_router.include_router(oauth.router)
api_v1_router.include_router(audit.router)
api_v1_router.include_router(api_keys.router)
api_v1_router.include_router(webhooks.router)
api_v1_router.include_router(notifications.router)
api_v1_router.include_router(exports.router)
api_v1_router.include_router(gdpr.router)
api_v1_router.include_router(alerts.router)
api_v1_router.include_router(dashboards.router)
api_v1_router.include_router(recipes.router)
api_v1_router.include_router(ai_assistant.router)
api_v1_router.include_router(onboarding.router)
api_v1_router.include_router(health.router)
api_v1_router.include_router(models.router)
api_v1_router.include_router(cross_source.router)
api_v1_router.include_router(anomaly_router)
api_v1_router.include_router(summaries_router)
api_v1_router.include_router(reports_router)
api_v1_router.include_router(whatsapp_test_router)

# RBAC routers
api_v1_router.include_router(admin.router)
api_v1_router.include_router(invitations.router)
api_v1_router.include_router(roles.router)
api_v1_router.include_router(access_requests.router)

# Add versioned API router to app
app.include_router(api_v1_router)


@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Add request processing time header and collect metrics."""
    start_time = time.time()

    response = await call_next(request)

    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)

    # Record metrics
    REQUEST_COUNT.labels(
        method=request.method,
        endpoint=request.url.path,
        status=response.status_code,
    ).inc()

    REQUEST_DURATION.labels(
        method=request.method,
        endpoint=request.url.path,
    ).observe(process_time)

    return response


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all HTTP requests."""
    logger.info(
        f"Request: {request.method} {request.url.path} "
        f"from {request.client.host if request.client else 'unknown'}"
    )

    response = await call_next(request)

    logger.info(
        f"Response: {request.method} {request.url.path} "
        f"status={response.status_code}"
    )

    return response


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors with standardized error response."""
    request_id = get_request_id(request)
    logger.error(f"Validation error [{request_id}]: {exc.errors()}")

    error = ErrorResponse(
        code=ErrorCodes.VALIDATION_ERROR,
        message="Request validation failed",
        status=status.HTTP_422_UNPROCESSABLE_ENTITY,
        request_id=request_id,
        details={"errors": exc.errors()},
    )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=error.to_dict(),
    )


@app.exception_handler(ValidationError)
async def pydantic_validation_exception_handler(request: Request, exc: ValidationError):
    """Handle Pydantic validation errors with standardized error response."""
    request_id = get_request_id(request)
    logger.error(f"Pydantic validation error [{request_id}]: {exc.errors()}")

    error = ErrorResponse(
        code=ErrorCodes.VALIDATION_ERROR,
        message="Data validation failed",
        status=status.HTTP_422_UNPROCESSABLE_ENTITY,
        request_id=request_id,
        details={"errors": exc.errors()},
    )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=error.to_dict(),
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions with standardized error response."""
    request_id = get_request_id(request)
    logger.error(f"Unhandled exception [{request_id}]: {str(exc)}", exc_info=True)

    # In production, don't leak internal error details
    message = str(exc) if settings.DEBUG else "An internal error occurred"

    error = ErrorResponse(
        code=ErrorCodes.INTERNAL_ERROR,
        message=message,
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        request_id=request_id,
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error.to_dict(),
    )


@app.on_event("startup")
async def startup_event():
    """Initialize application on startup."""
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"Environment: {settings.ENVIRONMENT}")

    # CRITICAL: Require ENCRYPTION_KEY in production
    if not getattr(settings, 'ENCRYPTION_KEY', None):
        if settings.ENVIRONMENT == "production":
            raise RuntimeError(
                "ENCRYPTION_KEY is required in production. "
                "Generate one with: python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'"
            )
        else:
            logger.error(
                "SECURITY WARNING: ENCRYPTION_KEY not set - "
                "connector credentials stored in plaintext!"
            )
    if not getattr(settings, 'STRIPE_SECRET_KEY', None):
        logger.warning("STRIPE_SECRET_KEY is not set — Stripe billing features will be unavailable")
    if not getattr(settings, 'PAYSTACK_SECRET_KEY', None):
        logger.warning("PAYSTACK_SECRET_KEY is not set — Paystack billing features will be unavailable")

    # Production readiness validation
    prod_warnings = settings.validate_production_settings()
    for warning in prod_warnings:
        logger.warning(f"Production config issue: {warning}")

    # In production, use alembic migrations (skip create_all to avoid conflicts)
    # In development, auto-create tables for convenience
    if settings.ENVIRONMENT != "production":
        try:
            init_db()
            logger.info("Database initialized successfully")
        except Exception as e:
            logger.warning(f"init_db skipped or failed (may already exist): {str(e)}")
    else:
        logger.info("Production mode - skipping init_db (use alembic migrations)")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on application shutdown."""
    logger.info(f"Shutting down {settings.APP_NAME}")


@app.get("/", tags=["Root"])
async def root() -> Dict[str, Any]:
    """Root endpoint."""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "status": "running",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/health", tags=["Health"])
async def health_check() -> Dict[str, Any]:
    """
    Health check endpoint.

    Returns application health status.
    """
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": settings.APP_VERSION,
    }


def _check_redis() -> bool:
    """Ping Redis so /health/ready reports whether it is actually connected."""
    try:
        import redis

        client = redis.from_url(settings.REDIS_URL, socket_connect_timeout=3)
        return bool(client.ping())
    except Exception:
        return False


@app.get("/health/ready", tags=["Health"])
async def readiness_check(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Readiness check endpoint.

    Checks if application is ready to serve requests.
    """
    checks = {
        "database": DatabaseHealthCheck.check(),
        "redis": _check_redis(),
    }

    all_healthy = all(checks.values())

    return {
        "status": "ready" if all_healthy else "not ready",
        "checks": checks,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/health/live", tags=["Health"])
async def liveness_check() -> Dict[str, Any]:
    """
    Liveness check endpoint.

    Simple check to verify the application is running.
    """
    return {
        "status": "alive",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/metrics", tags=["Monitoring"])
async def metrics(current_user: User = Depends(get_current_user)):
    """
    Prometheus metrics endpoint.

    Returns metrics in Prometheus format.
    Restricted to super admins only.
    """
    from fastapi import HTTPException
    if not (current_user.is_superuser or current_user.is_super_admin()):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Metrics endpoint is restricted to super admins.",
        )
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )


@app.get("/stats", tags=["Monitoring"])
async def stats(current_user: User = Depends(get_current_user)) -> Dict[str, Any]:
    """
    Application statistics endpoint.

    Returns various statistics about the application.
    Requires authentication.
    """
    db_stats = DatabaseHealthCheck.get_stats()

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "database": db_stats,
        "environment": settings.ENVIRONMENT,
        "version": settings.APP_VERSION,
    }


@app.get("/config", tags=["System"])
async def config(current_user: User = Depends(get_current_user)) -> Dict[str, Any]:
    """
    Configuration endpoint (non-sensitive values only).

    Returns non-sensitive configuration values.
    Requires authentication.
    """
    return {
        "app_name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "debug": settings.DEBUG,
        "api_host": settings.API_HOST,
        "api_port": settings.API_PORT,
        "cors_origins": settings.CORS_ORIGINS,
        "rate_limit_enabled": settings.RATE_LIMIT_ENABLED,
        "data_quality_enabled": settings.DATA_QUALITY_ENABLED,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "backend.api.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        workers=settings.API_WORKERS,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
    )
