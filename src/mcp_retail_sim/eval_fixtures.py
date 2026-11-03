"""Opt-in synthetic evaluation fixtures (not agent-facing MCP tools).

Enable via MCP_RETAIL_SIM_EVAL_FIXTURES=adversarial (comma-separated) or
enable_eval_fixtures([...]) in tests/harnesses.
"""

from __future__ import annotations

import os

_ENV_VAR = "MCP_RETAIL_SIM_EVAL_FIXTURES"

_adversarial_enabled: bool = False


def adversarial_enabled() -> bool:
    """True when adversarial eval products should be merged into the catalog."""
    return _adversarial_enabled


def clear_eval_fixtures() -> None:
    """Disable all eval fixture packs and refresh cached catalog/inventory."""
    global _adversarial_enabled
    _adversarial_enabled = False
    _clear_catalog_caches()


def enable_eval_fixtures(packs: list[str]) -> None:
    """Enable named eval fixture packs (pytest / in-process harness)."""
    global _adversarial_enabled
    normalized = {p.strip().lower() for p in packs if p.strip()}
    _adversarial_enabled = "adversarial" in normalized
    _clear_catalog_caches()


def configure_from_env() -> None:
    """Load eval fixture packs from MCP_RETAIL_SIM_EVAL_FIXTURES."""
    raw = os.environ.get(_ENV_VAR, "").strip()
    if not raw:
        clear_eval_fixtures()
        return
    enable_eval_fixtures(raw.split(","))


def _clear_catalog_caches() -> None:
    """Drop cached products/inventory so the next load sees the new flag."""
    from mcp_retail_sim import store

    store.load_products.cache_clear()
    store.load_inventory.cache_clear()
