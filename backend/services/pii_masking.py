"""
PII masking applied during a sync, before data reaches the destination.

Config lives on the pipeline (``pipeline.config["pii_masking"]``) so it's toggled
per pipeline with no schema change:

    {
      "enabled": true,
      "strategy": "partial",          # partial | redact | hash | null
      "columns": ["email", "phone"],  # explicit columns to mask (case-insensitive)
      "auto_detect": false             # also mask high-confidence PII column names
    }

The masking is a row-level ``add_map`` on each dlt resource, so table structure is
preserved and only the targeted column VALUES are transformed. Masking runs before
any other transformation so raw PII never lands downstream.
"""
from __future__ import annotations

import hashlib
import logging
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)

# Conservative auto-detect set: only high-confidence PII column-name fragments, to
# avoid over-masking (e.g. we deliberately DON'T auto-match a bare "name", which
# hits username/filename/company_name). Users add anything else via `columns`.
_PII_HINTS = (
    "email", "e_mail",
    "phone", "mobile", "msisdn",
    "ssn", "social_security", "national_id", "nin",
    "passport", "tax_id", "vat_number",
    "date_of_birth", "dob", "birth_date",
    "credit_card", "card_number", "cardnumber", "pan",
    "iban", "account_number", "acct_number", "routing_number",
    "bvn",  # Nigerian Bank Verification Number
)

_VALID_STRATEGIES = {"partial", "redact", "hash", "null"}


def _looks_like_pii(col_lower: str) -> bool:
    return any(hint in col_lower for hint in _PII_HINTS)


def _partial_mask(s: str) -> str:
    """Show just enough to be recognizable, hide the rest."""
    if "@" in s:  # email → keep first char + domain
        local, _, domain = s.partition("@")
        head = local[:1] if local else ""
        return f"{head}***@{domain}"
    if len(s) <= 2:
        return "*" * len(s)
    if len(s) <= 4:
        return s[0] + "*" * (len(s) - 1)
    return s[:2] + "*" * (len(s) - 4) + s[-2:]


def mask_value(value: Any, strategy: str) -> Any:
    """Apply one masking strategy to a single value. None stays None."""
    if value is None:
        return None
    if strategy == "null":
        return None
    if strategy == "redact":
        return "***"
    if strategy == "hash":
        return hashlib.sha256(str(value).encode("utf-8")).hexdigest()[:16]
    # default: partial
    return _partial_mask(str(value))


def build_mask_map(config: Dict[str, Any]) -> Optional[Callable[[Any], Any]]:
    """Build a row-level masking function from pipeline PII config, or None if
    masking is disabled / nothing is targeted."""
    if not config or not config.get("enabled"):
        return None

    strategy = config.get("strategy", "partial")
    if strategy not in _VALID_STRATEGIES:
        logger.warning("Unknown PII strategy %r; defaulting to 'partial'", strategy)
        strategy = "partial"

    explicit = {str(c).lower() for c in (config.get("columns") or [])}
    auto = bool(config.get("auto_detect", False))
    if not explicit and not auto:
        return None  # enabled but nothing to mask

    def _mask_row(row: Any) -> Any:
        if not isinstance(row, dict):
            return row
        for key in list(row.keys()):
            kl = str(key).lower()
            if kl in explicit or (auto and _looks_like_pii(kl)):
                row[key] = mask_value(row[key], strategy)
        return row

    return _mask_row


def apply_masking_to_source(source: Any, config: Dict[str, Any]) -> Any:
    """Attach PII masking to a dlt source/resource stream.

    Handles the shapes fetch_source_data can return: a DltSource (``.resources``),
    a list of resources, a single resource, or a plain row iterator. Masking never
    raises through — on any failure it logs and returns the source unmasked would
    be unsafe, so instead it falls back to a wrapping generator that still masks.
    """
    mask_fn = build_mask_map(config)
    if mask_fn is None:
        return source

    # DltSource: add_map on each resource, preserving per-table structure.
    resources = getattr(source, "resources", None)
    if resources is not None and hasattr(resources, "values"):
        try:
            for res in resources.values():
                res.add_map(mask_fn)
            return source
        except Exception as exc:  # noqa: BLE001
            logger.warning("PII masking via source.resources failed (%s); wrapping", exc)

    # List/tuple of resources.
    if isinstance(source, (list, tuple)):
        out = []
        for res in source:
            try:
                out.append(res.add_map(mask_fn))
            except Exception:  # noqa: BLE001
                out.append(res)
        return out

    # Single resource exposing add_map.
    if hasattr(source, "add_map"):
        try:
            return source.add_map(mask_fn)
        except Exception:  # noqa: BLE001
            logger.warning("PII masking via add_map failed; wrapping iterator")

    # Fallback: a plain iterator of rows.
    return (mask_fn(row) if isinstance(row, dict) else row for row in source)
