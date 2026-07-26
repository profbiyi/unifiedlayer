"""
Managed storage provisioning.

The "managed warehouse" option lands an org's synced data as Parquet in a
platform-owned, S3-compatible bucket (internal MinIO, Cloudflare R2, Backblaze
B2, or AWS S3) under a per-org prefix. The same bucket is read back by the
DuckDB engine to power on-platform BI + AI.

This module is the single source of truth for:
  - whether managed storage is enabled (creds present),
  - the per-org prefix (isolation boundary),
  - the dlt-facing Destination config used to WRITE synced data,
  - the DuckDB engine s3 config used to READ it back.

See docs/architecture/managed-analytics-duckdb.md (phase 2).
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from backend.config import settings
from backend.models.pipeline import Destination, DestinationType

# The managed destination is identified per org by this exact name + S3 type,
# so provisioning is idempotent without decrypting every destination's config.
MANAGED_DESTINATION_NAME = "Managed Warehouse"
_FILE_FORMAT = "parquet"
_DEFAULT_DATASET = "main"


class ManagedStorageNotConfigured(RuntimeError):
    """Raised when managed storage is used but no bucket/credentials are set."""


def is_configured() -> bool:
    """True when the platform has a managed bucket + credentials configured."""
    return bool(
        settings.MANAGED_STORAGE_BUCKET
        and settings.MANAGED_STORAGE_ACCESS_KEY
        and settings.MANAGED_STORAGE_SECRET_KEY
    )


def org_prefix(organization_id: int) -> str:
    """The org's isolation boundary within the shared managed bucket."""
    return f"org-{organization_id}"


def _endpoint_host() -> Optional[str]:
    """
    Endpoint as bare host[:port] (no scheme, no trailing slash). Tolerant of an
    endpoint that was configured WITH a scheme (a common mistake) — DuckDB's
    s3_endpoint and dlt both want the host only and add the scheme themselves,
    so a value like ``https://acc.r2.cloudflarestorage.com`` would otherwise
    become ``https://https://…``.
    """
    endpoint = settings.MANAGED_STORAGE_ENDPOINT
    if not endpoint:
        return None
    return endpoint.replace("https://", "").replace("http://", "").strip().rstrip("/")


def _endpoint_url() -> Optional[str]:
    """Full scheme://host endpoint for dlt/s3fs (None ⇒ native AWS S3)."""
    host = _endpoint_host()
    if not host:
        return None
    scheme = "https" if settings.MANAGED_STORAGE_USE_SSL else "http"
    return f"{scheme}://{host}"


def destination_config(organization_id: int) -> Dict[str, Any]:
    """
    The Destination.config stored in the DB for the org's managed warehouse.

    IMPORTANT: this holds only non-secret routing info. The platform's shared
    storage credentials are NEVER persisted here — they are injected at sync
    time from settings (see ``write_credentials`` + pipeline_flow). This is
    deliberate: ``Destination.config`` is surfaced by the destinations API, so
    persisting the platform secret would leak it to org users.
    """
    prefix = org_prefix(organization_id)
    config: Dict[str, Any] = {
        "managed": True,
        "bucket_url": f"s3://{settings.MANAGED_STORAGE_BUCKET}/{prefix}",
        "prefix": prefix,
        "region": settings.MANAGED_STORAGE_REGION,
        "file_format": _FILE_FORMAT,
        "dataset_name": _DEFAULT_DATASET,
    }
    endpoint = _endpoint_url()
    if endpoint:
        config["endpoint_url"] = endpoint
    return config


def write_credentials() -> Dict[str, Any]:
    """
    Platform storage credentials for dlt to WRITE managed data. Resolved from
    settings at sync time and never persisted in the DB. Overlaid onto the s3
    credentials in pipeline_flow when a destination is managed.
    """
    if not is_configured():
        raise ManagedStorageNotConfigured("Managed storage is not configured")
    creds: Dict[str, Any] = {
        "aws_access_key_id": settings.MANAGED_STORAGE_ACCESS_KEY,
        "aws_secret_access_key": settings.MANAGED_STORAGE_SECRET_KEY,
        "region_name": settings.MANAGED_STORAGE_REGION,
    }
    endpoint = _endpoint_url()
    if endpoint:
        creds["endpoint_url"] = endpoint
    return creds


def engine_s3_config(organization_id: int) -> Dict[str, Any]:
    """
    The s3 config dict for ``DuckDBAnalyticsEngine`` to READ an org's managed
    data back. DuckDB's s3_endpoint wants host[:port] with no scheme (None for
    native AWS S3); credentials and prefix scope it to this org only.
    """
    if not is_configured():
        raise ManagedStorageNotConfigured("Managed storage is not configured")
    return {
        "endpoint": _endpoint_host(),  # bare host, or None ⇒ native AWS S3
        "region": settings.MANAGED_STORAGE_REGION,
        "access_key": settings.MANAGED_STORAGE_ACCESS_KEY,
        "secret_key": settings.MANAGED_STORAGE_SECRET_KEY,
        "url_style": settings.MANAGED_STORAGE_URL_STYLE,
        "use_ssl": settings.MANAGED_STORAGE_USE_SSL,
        "bucket": settings.MANAGED_STORAGE_BUCKET,
        "prefix": org_prefix(organization_id),
    }


def get_managed_destination(db: Session, organization_id: int) -> Optional[Destination]:
    """Return the org's managed destination if it exists, else None."""
    return (
        db.query(Destination)
        .filter(
            Destination.organization_id == organization_id,
            Destination.destination_type == DestinationType.S3,
            Destination.name == MANAGED_DESTINATION_NAME,
        )
        .first()
    )


def provision_managed_destination(db: Session, organization_id: int) -> Destination:
    """
    Idempotently create (or refresh) the org's managed warehouse destination.

    Safe to call repeatedly: an existing managed destination has its config
    refreshed (so rotated platform creds/bucket propagate) rather than
    duplicated.
    """
    if not is_configured():
        raise ManagedStorageNotConfigured(
            "Managed storage is not configured (MANAGED_STORAGE_* env vars)"
        )

    existing = get_managed_destination(db, organization_id)
    if existing:
        existing.config = destination_config(organization_id)
        existing.is_active = True
        db.commit()
        db.refresh(existing)
        return existing

    destination = Destination(
        organization_id=organization_id,
        name=MANAGED_DESTINATION_NAME,
        description="Platform-managed warehouse — analytics and AI run on the platform.",
        destination_type=DestinationType.S3,
        config=destination_config(organization_id),
        is_active=True,
    )
    db.add(destination)
    db.commit()
    db.refresh(destination)
    return destination
