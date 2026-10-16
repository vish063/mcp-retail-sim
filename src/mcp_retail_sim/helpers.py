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
