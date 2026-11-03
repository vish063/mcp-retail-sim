"""Small shared helpers (sanitization, etc.). Keep tools.py thin."""

from __future__ import annotations

import re

# Letters, digits, optional hyphen segments — matches fixtures like SKU-1000.
# Pure [A-Za-z0-9]+ would reject those SKUs.
_PRODUCT_ID_RE = re.compile(r"^[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*$")


def sanitize_query(query: str) -> str:
    """Normalize user/agent search text before matching."""
    cleaned = re.sub(r"[\x00-\x1f\x7f]", "", query)
    cleaned = cleaned.strip()
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned


def blank_to_none(value: str | None) -> str | None:
    """Treat None/whitespace as unset (MCP Inspector often sends empty strings)."""
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def parse_optional_bool(value: str | None) -> bool | None:
    """Parse optional bool filter from a string. Blank → unset.

    Accepts true/false/yes/no/1/0 (case-insensitive). String-typed on purpose so
    form UIs do not default unchecked checkboxes to false and empty the catalog.
    """
    cleaned = blank_to_none(value)
    if cleaned is None:
        return None
    token = cleaned.lower()
    if token in {"true", "1", "yes"}:
        return True
    if token in {"false", "0", "no"}:
        return False
    raise ValueError(f"invalid boolean filter: {value!r} (use true/false)")


def parse_optional_float(value: str | None) -> float | None:
    """Parse optional numeric filter from a string. Blank → unset."""
    cleaned = blank_to_none(value)
    if cleaned is None:
        return None
    return float(cleaned)


def sanitize_product_id(product_id: str) -> str | None:
    """Strip and accept only alphanumeric SKUs (hyphens allowed). Return None if invalid."""
    cleaned = product_id.strip()
    if not cleaned or not _PRODUCT_ID_RE.fullmatch(cleaned):
        return None
    return cleaned


def sanitize_cart_id(cart_id: str) -> str | None:
    """Strip and accept alphanumeric cart handles (hyphens allowed)."""
    cleaned = cart_id.strip()
    if not cleaned or not _PRODUCT_ID_RE.fullmatch(cleaned):
        return None
    return cleaned


def sanitize_order_id(order_id: str) -> str | None:
    """Strip and accept alphanumeric order ids (hyphens allowed), e.g. ORD-E2F0C262."""
    cleaned = order_id.strip()
    if not cleaned or not _PRODUCT_ID_RE.fullmatch(cleaned):
        return None
    return cleaned


def sanitize_idempotency_key(idempotency_key: str) -> str | None:
    """Strip and accept alphanumeric idempotency keys (hyphens allowed)."""
    cleaned = idempotency_key.strip()
    if not cleaned or not _PRODUCT_ID_RE.fullmatch(cleaned):
        return None
    return cleaned
