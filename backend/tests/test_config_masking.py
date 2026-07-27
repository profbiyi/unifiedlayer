"""
Tests for connection-config secret masking in API responses.

Sources/destinations store credentials at rest; the API must never return them
in plaintext (any org user could read them). Responses mask secret values;
routing fields stay visible; updates preserve the stored secret when the mask
is sent back.
"""
from datetime import datetime, timezone
from uuid import uuid4

from backend.schemas.base import (
    MASKED_SECRET,
    DestinationResponse,
    mask_secret_config,
)


def test_mask_hides_secrets_keeps_routing():
    cfg = {
        "host": "db.example.com",
        "bucket": "my-bucket",
        "region": "eu-west-3",
        "dataset_name": "main",
        "endpoint_url": "https://acc.r2.cloudflarestorage.com",
        "aws_access_key_id": "AKIA123",
        "aws_secret_access_key": "supersecret",
        "password": "hunter2",
        "api_key": "sk_live_x",
    }
    m = mask_secret_config(cfg)
    # routing fields untouched
    for k in ("host", "bucket", "region", "dataset_name", "endpoint_url"):
        assert m[k] == cfg[k]
    # every credential masked
    for k in ("aws_access_key_id", "aws_secret_access_key", "password", "api_key"):
        assert m[k] == MASKED_SECRET


def test_mask_handles_empty_and_none():
    assert mask_secret_config(None) is None
    assert mask_secret_config({}) == {}
    # an empty secret has nothing to hide -> left as-is
    assert mask_secret_config({"password": ""})["password"] == ""


def test_destination_response_masks_config():
    resp = DestinationResponse(
        name="s3",
        description=None,
        destination_type="s3",
        config={"bucket": "b", "region": "eu", "aws_secret_access_key": "shh"},
        public_id=uuid4(),
        organization_id=1,
        is_active=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    assert resp.config["bucket"] == "b"
    assert resp.config["region"] == "eu"
    assert resp.config["aws_secret_access_key"] == MASKED_SECRET
