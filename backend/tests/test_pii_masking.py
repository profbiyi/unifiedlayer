"""
Tests for PII masking applied during sync.
"""
from backend.services import pii_masking as pm


# ---- value-level strategies ----

def test_partial_masks_email_keeping_domain():
    assert pm.mask_value("jane.doe@example.com", "partial") == "j***@example.com"


def test_partial_masks_generic_string():
    out = pm.mask_value("08031234567", "partial")
    assert out.startswith("08") and out.endswith("67") and "*" in out


def test_redact_null_hash_and_none():
    assert pm.mask_value("secret", "redact") == "***"
    assert pm.mask_value("secret", "null") is None
    assert pm.mask_value(None, "partial") is None
    h = pm.mask_value("secret", "hash")
    assert len(h) == 16 and h == pm.mask_value("secret", "hash")  # deterministic


# ---- column detection ----

def test_looks_like_pii_high_confidence_only():
    assert pm._looks_like_pii("email")
    assert pm._looks_like_pii("customer_phone")
    assert pm._looks_like_pii("bvn")
    # deliberately NOT auto-matched (avoid over-masking):
    assert not pm._looks_like_pii("username")
    assert not pm._looks_like_pii("filename")
    assert not pm._looks_like_pii("company")


# ---- build_mask_map gating ----

def test_build_mask_map_disabled_returns_none():
    assert pm.build_mask_map({"enabled": False, "columns": ["email"]}) is None
    assert pm.build_mask_map({"enabled": True}) is None  # nothing targeted


def test_build_mask_map_explicit_columns():
    fn = pm.build_mask_map({"enabled": True, "strategy": "redact", "columns": ["Email"]})
    row = {"id": 1, "Email": "a@b.com", "name": "keep"}
    out = fn(row)
    assert out["Email"] == "***"
    assert out["name"] == "keep" and out["id"] == 1


def test_build_mask_map_auto_detect():
    fn = pm.build_mask_map({"enabled": True, "auto_detect": True})
    out = fn({"email": "a@b.com", "note": "hi"})
    assert out["email"].endswith("@b.com") and out["note"] == "hi"


# ---- apply_masking_to_source across shapes ----

class _FakeRes:
    def __init__(self):
        self.mapped = None

    def add_map(self, fn):
        self.mapped = fn
        return self


class _FakeSource:
    def __init__(self, resources):
        self.resources = resources


def test_apply_masking_disabled_returns_source_unchanged():
    src = object()
    assert pm.apply_masking_to_source(src, {"enabled": False}) is src


def test_apply_masking_dlt_source_adds_map_per_resource():
    r1, r2 = _FakeRes(), _FakeRes()
    src = _FakeSource({"customers": r1, "charges": r2})
    out = pm.apply_masking_to_source(src, {"enabled": True, "columns": ["email"]})
    assert out is src
    assert callable(r1.mapped) and callable(r2.mapped)


def test_apply_masking_list_of_resources():
    r1, r2 = _FakeRes(), _FakeRes()
    pm.apply_masking_to_source([r1, r2], {"enabled": True, "columns": ["email"]})
    assert callable(r1.mapped) and callable(r2.mapped)


def test_apply_masking_iterator_fallback_masks_rows():
    rows = iter([{"email": "a@b.com"}, {"email": "c@d.com"}])
    out = list(pm.apply_masking_to_source(rows, {"enabled": True, "columns": ["email"]}))
    assert out[0]["email"] == "a***@b.com"
    assert out[1]["email"] == "c***@d.com"
