"""
Tests for managed storage provisioning (phase 2).

Covers the enable flag, per-org isolation prefix, the dlt-facing write config,
the DuckDB read config bridge, and idempotent provisioning.
"""
import pytest

from backend.config import settings
from backend.models.pipeline import Destination, DestinationType
from backend.services import managed_storage


def _configure(monkeypatch, *, endpoint="minio:9000", use_ssl=False):
    monkeypatch.setattr(settings, "MANAGED_STORAGE_BUCKET", "ul-managed", raising=False)
    monkeypatch.setattr(settings, "MANAGED_STORAGE_ACCESS_KEY", "AKIA_TEST", raising=False)
    monkeypatch.setattr(settings, "MANAGED_STORAGE_SECRET_KEY", "secret_test", raising=False)
    monkeypatch.setattr(settings, "MANAGED_STORAGE_REGION", "eu-west-1", raising=False)
    monkeypatch.setattr(settings, "MANAGED_STORAGE_ENDPOINT", endpoint, raising=False)
    monkeypatch.setattr(settings, "MANAGED_STORAGE_USE_SSL", use_ssl, raising=False)
    monkeypatch.setattr(settings, "MANAGED_STORAGE_URL_STYLE", "path", raising=False)


def _unconfigure(monkeypatch):
    monkeypatch.setattr(settings, "MANAGED_STORAGE_BUCKET", None, raising=False)
    monkeypatch.setattr(settings, "MANAGED_STORAGE_ACCESS_KEY", None, raising=False)
    monkeypatch.setattr(settings, "MANAGED_STORAGE_SECRET_KEY", None, raising=False)


def test_is_configured_toggles(monkeypatch):
    _unconfigure(monkeypatch)
    assert managed_storage.is_configured() is False
    _configure(monkeypatch)
    assert managed_storage.is_configured() is True


def test_org_prefix_is_isolated():
    assert managed_storage.org_prefix(12) == "org-12"
    assert managed_storage.org_prefix(99) == "org-99"


def test_destination_config_with_endpoint(monkeypatch):
    _configure(monkeypatch, endpoint="minio:9000", use_ssl=False)
    cfg = managed_storage.destination_config(12)
    assert cfg["managed"] is True
    assert cfg["bucket_url"] == "s3://ul-managed/org-12"
    assert cfg["prefix"] == "org-12"
    assert cfg["file_format"] == "parquet"
    # MinIO/R2 need a full scheme://host endpoint for dlt; http since use_ssl=False
    assert cfg["endpoint_url"] == "http://minio:9000"


def test_destination_config_never_holds_secrets(monkeypatch):
    """Platform creds must NOT be persisted — Destination.config is API-visible."""
    _configure(monkeypatch)
    cfg = managed_storage.destination_config(12)
    blob = str(cfg).lower()
    assert "secret_test" not in blob
    assert "akia_test" not in blob
    assert "aws_secret_access_key" not in cfg
    assert "aws_access_key_id" not in cfg


def test_write_credentials_resolved_from_settings(monkeypatch):
    _configure(monkeypatch, endpoint="minio:9000", use_ssl=True)
    creds = managed_storage.write_credentials()
    assert creds["aws_access_key_id"] == "AKIA_TEST"
    assert creds["aws_secret_access_key"] == "secret_test"
    assert creds["region_name"] == "eu-west-1"
    assert creds["endpoint_url"] == "https://minio:9000"


def test_destination_config_native_s3_has_no_endpoint(monkeypatch):
    _configure(monkeypatch, endpoint=None)
    cfg = managed_storage.destination_config(7)
    assert "endpoint_url" not in cfg
    assert cfg["bucket_url"] == "s3://ul-managed/org-7"


def test_engine_s3_config_maps_for_duckdb(monkeypatch):
    _configure(monkeypatch, endpoint="minio:9000", use_ssl=False)
    s3 = managed_storage.engine_s3_config(12)
    # DuckDB s3_endpoint expects host:port with NO scheme
    assert s3["endpoint"] == "minio:9000"
    assert s3["bucket"] == "ul-managed"
    assert s3["prefix"] == "org-12"
    assert s3["access_key"] == "AKIA_TEST"
    assert s3["url_style"] == "path"
    assert s3["use_ssl"] is False


def test_endpoint_with_scheme_is_normalized(monkeypatch):
    # A common misconfig: endpoint set WITH https:// (as R2 shows it). Must not
    # produce https://https:// — DuckDB/dlt want the bare host.
    _configure(monkeypatch, endpoint="https://acc.r2.cloudflarestorage.com", use_ssl=True)
    s3 = managed_storage.engine_s3_config(12)
    assert s3["endpoint"] == "acc.r2.cloudflarestorage.com"
    cfg = managed_storage.destination_config(12)
    assert cfg["endpoint_url"] == "https://acc.r2.cloudflarestorage.com"


def test_engine_s3_config_raises_when_unconfigured(monkeypatch):
    _unconfigure(monkeypatch)
    with pytest.raises(managed_storage.ManagedStorageNotConfigured):
        managed_storage.engine_s3_config(12)


def test_provision_is_idempotent(monkeypatch, db, test_org):
    _configure(monkeypatch)
    first = managed_storage.provision_managed_destination(db, test_org.id)
    assert first.destination_type == DestinationType.S3
    assert first.name == managed_storage.MANAGED_DESTINATION_NAME
    assert first.config["prefix"] == f"org-{test_org.id}"

    second = managed_storage.provision_managed_destination(db, test_org.id)
    assert second.id == first.id  # no duplicate row

    count = (
        db.query(Destination)
        .filter(
            Destination.organization_id == test_org.id,
            Destination.name == managed_storage.MANAGED_DESTINATION_NAME,
        )
        .count()
    )
    assert count == 1


def test_provision_raises_when_unconfigured(monkeypatch, db, test_org):
    _unconfigure(monkeypatch)
    with pytest.raises(managed_storage.ManagedStorageNotConfigured):
        managed_storage.provision_managed_destination(db, test_org.id)
