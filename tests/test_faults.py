import time

import mcp_retail_sim.store as store
from mcp_retail_sim.faults import enable_faults


def setup_function():
    store.reset_runtime_state()


def test_insufficient_stock_fault_blocks_checkout():
    enable_faults(["place_order:insufficient_stock"])
    before = store.inventory_state("SKU-1001")["stock_qty"]
    store.add_to_cart("cart-fault", "SKU-1001", qty=1)

    result = store.place_order("cart-fault")
    assert result["ok"] is False
    assert "insufficient stock" in result["error"]
    assert store.get_cart("cart-fault") is not None
    assert store.inventory_state("SKU-1001")["stock_qty"] == before
    assert store._ORDERS == {}


def test_fail_once_then_succeeds():
    enable_faults(["place_order:fail_once"])
    store.add_to_cart("cart-once", "SKU-1001", qty=1)

    first = store.place_order("cart-once")
    assert first["ok"] is False
    assert "transient" in first["error"]
    assert store.get_cart("cart-once") is not None

    second = store.place_order("cart-once")
    assert second["ok"] is True
    assert second["order"]["order_id"].startswith("ORD-")
    assert store.get_cart("cart-once") is None


def test_error_after_commit_replay_with_idempotency_key():
    enable_faults(["place_order:error_after_commit"])
    before = store.inventory_state("SKU-1001")["stock_qty"]
    store.add_to_cart("cart-eac", "SKU-1001", qty=1)

    first = store.place_order("cart-eac", idempotency_key="checkout-eac-1")
    assert first["ok"] is False
    assert "transient" in first["error"]
    assert store.get_cart("cart-eac") is None
    assert len(store._ORDERS) == 1
    order_id = next(iter(store._ORDERS))
    assert store.inventory_state("SKU-1001")["stock_qty"] == before - 1

    replay = store.place_order("cart-eac", idempotency_key="checkout-eac-1")
    assert replay["ok"] is True
    assert replay["order"]["order_id"] == order_id
    assert store.inventory_state("SKU-1001")["stock_qty"] == before - 1


def test_latency_ms_fault_sleeps():
    enable_faults(["place_order:latency_ms:50"])
    store.add_to_cart("cart-slow", "SKU-1001", qty=1)
    started = time.perf_counter()
    result = store.place_order("cart-slow")
    elapsed_ms = (time.perf_counter() - started) * 1000
    assert result["ok"] is True
    assert elapsed_ms >= 40
