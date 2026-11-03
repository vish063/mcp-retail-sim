"""Test/eval-only checkout fault injection.

Configured via MCP_RETAIL_SIM_FAULTS (comma-separated) or enable_faults().
Never expose these controls as agent-facing MCP tools.

Supported directives:
  place_order:insufficient_stock
  place_order:latency_ms:N
  place_order:fail_once
  place_order:error_after_commit
"""

from __future__ import annotations

import os
import time
from typing import Any

_ENV_VAR = "MCP_RETAIL_SIM_FAULTS"

_insufficient_stock: bool = False
_latency_ms: int = 0
_fail_once_remaining: int = 0
_error_after_commit_remaining: int = 0


def clear_faults() -> None:
    """Disable all faults and reset one-shot counters."""
    global _insufficient_stock, _latency_ms
    global _fail_once_remaining, _error_after_commit_remaining
    _insufficient_stock = False
    _latency_ms = 0
    _fail_once_remaining = 0
    _error_after_commit_remaining = 0


def _apply_directives(directives: list[str]) -> None:
    """Replace current fault config with the given directive tokens."""
    clear_faults()
    global _insufficient_stock, _latency_ms
    global _fail_once_remaining, _error_after_commit_remaining

    for raw in directives:
        token = raw.strip()
        if not token:
            continue
        parts = token.split(":")
        if len(parts) < 2 or parts[0] != "place_order":
            continue
        kind = parts[1]
        if kind == "insufficient_stock":
            _insufficient_stock = True
        elif kind == "latency_ms" and len(parts) >= 3:
            try:
                _latency_ms = max(0, int(parts[2]))
            except ValueError:
                _latency_ms = 0
        elif kind == "fail_once":
            _fail_once_remaining = 1
        elif kind == "error_after_commit":
            _error_after_commit_remaining = 1


def enable_faults(directives: list[str]) -> None:
    """Enable faults from an explicit list (pytest / in-process)."""
    _apply_directives(directives)


def configure_from_env() -> None:
    """Load faults from MCP_RETAIL_SIM_FAULTS. Empty/unset clears faults."""
    raw = os.environ.get(_ENV_VAR, "").strip()
    if not raw:
        clear_faults()
        return
    _apply_directives(raw.split(","))


def apply_latency_if_configured() -> None:
    """Sleep when place_order:latency_ms:N is configured."""
    if _latency_ms > 0:
        time.sleep(_latency_ms / 1000.0)


def pre_commit_fault(items: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Return an error response to abort checkout before stock mutation, or None.

    Priority: insufficient_stock (sticky) then fail_once (one-shot).
    """
    global _fail_once_remaining

    if _insufficient_stock:
        if not items:
            return {
                "ok": False,
                "error": "insufficient stock (fault injection)",
            }
        item = items[0]
        sku = str(item["sku"])
        qty = int(item["qty"])
        return {
            "ok": False,
            "error": f"insufficient stock for {sku}: need {qty}, have 0",
        }

    if _fail_once_remaining > 0:
        _fail_once_remaining -= 1
        return {"ok": False, "error": "transient checkout error"}

    return None


def post_commit_fault() -> dict[str, Any] | None:
    """After a successful commit, optionally return a fake failure once.

    Order and idempotency are already saved; a retry with the same key should
    return the real order.
    """
    global _error_after_commit_remaining

    if _error_after_commit_remaining > 0:
        _error_after_commit_remaining -= 1
        return {"ok": False, "error": "transient checkout error"}
    return None
