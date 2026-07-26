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


def _strip_scheme(url: str) -> str:
    """Bare host[:port] — no scheme, no trailing slash (DuckDB/dlt add the scheme)."""
    return url.replace("https://", "").replace("http://", "").strip().rstrip("/")


def _split_bucket_url(bucket_url: Optional[str]) -> tuple:
    """``s3://bucket/prefix`` -> ('bucket', 'prefix'); prefix may be ''."""
    if not bucket_url:
        return "", ""
    rest = bucket_url.replace("s3://", "").replace("gs://", "").strip("/")
    parts = rest.split("/", 1)
    return parts[0], (parts[1] if len(parts) > 1 else "")


def _endpoint_host() -> Optional[str]:
    """
    Platform endpoint as bare host[:port]. Tolerant of an endpoint configured
    WITH a scheme (a common mistake) — DuckDB's s3_endpoint and dlt want the host
    only, so ``https://acc.r2.cloudflarestorage.com`` would otherwise double up.
    """
    endpoint = settings.MANAGED_STORAGE_ENDPOINT
    if not endpoint:
        return None
    return _strip_scheme(endpoint)


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


def engine_s3_config_for(destination: Destination) -> Dict[str, Any]:
    """
    Build the DuckDB READ config for a managed destination — INTERNAL (platform
    bucket, creds from settings) or EXTERNAL (the customer's own bucket + creds
    stored in the destination config). External = "your data, our AI".

    A destination is external when it carries its own bucket credentials.
    """
    cfg = destination.config or {}
    if cfg.get("aws_access_key_id"):
        bucket, base = _split_bucket_url(cfg.get("bucket_url"))
        host = _strip_scheme(cfg["endpoint_url"]) if cfg.get("endpoint_url") else None
        # Scope reads to the org's own folder so multiple orgs can share a bucket
        # without seeing each other's data (dlt writes under this same dataset).
        dataset = cfg.get("dataset_name") or org_prefix(destination.organization_id)
        prefix = "/".join(p for p in [base, dataset] if p)
        return {
            "endpoint": host,  # None ⇒ native AWS S3
            "region": cfg.get("region") or "us-east-1",
            "access_key": cfg.get("aws_access_key_id"),
            "secret_key": cfg.get("aws_secret_access_key"),
            "url_style": "path" if host else "vhost",
            "use_ssl": True,
            "bucket": bucket,
            "prefix": prefix,
        }
    # Internal platform-managed bucket.
    return engine_s3_config(destination.organization_id)


def resolve_engine_config(db: Session, organization_id: int) -> Dict[str, Any]:
    """Find the org's managed destination and build its DuckDB READ config."""
    dest = get_managed_destination(db, organization_id)
    if not dest:
        raise ManagedStorageNotConfigured("No managed warehouse for this organization")
    return engine_s3_config_for(dest)


def get_managed_destination(db: Session, organization_id: int) -> Optional[Destination]:
    """
    The org's managed warehouse destination, internal OR external. The
    internal-provisioned one is matched by name; an external bucket a customer
    designated managed is matched by ``config.managed`` on any S3 destination.
    """
    dests = (
        db.query(Destination)
        .filter(
            Destination.organization_id == organization_id,
            Destination.destination_type == DestinationType.S3,
        )
        .all()
    )
    for dest in dests:  # internal fast-path
        if dest.name == MANAGED_DESTINATION_NAME:
            return dest
    for dest in dests:  # external: designated managed in its own config
        try:
            if (dest.config or {}).get("managed"):
                return dest
        except Exception:  # noqa: BLE001 — a bad config row shouldn't break lookup
            continue
    return None


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

    # Idempotency keyed on the internal name only — never touch an external
    # managed destination the customer set up.
    existing = (
        db.query(Destination)
        .filter(
            Destination.organization_id == organization_id,
            Destination.destination_type == DestinationType.S3,
            Destination.name == MANAGED_DESTINATION_NAME,
        )
        .first()
    )
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
