import mcp_retail_sim.store as store


def setup_function():
    store._CARTS.clear()
    store._ORDERS.clear()


def test_search_headphones_returns_products():
    hits = store.search_products("headphones")
    assert hits
    assert any("headphone" in hit["name"].lower() for hit in hits)


def test_search_unknown_query_returns_empty():
    assert store.search_products("zzzz-not-a-product") == []


def test_product_details_known_sku():
    product = store.product_details("SKU-1001")
    assert product is not None
    assert product["sku"] == "SKU-1001"


def test_product_details_unknown_sku():
    assert store.product_details("SKU-DOES-NOT-EXIST") is None


def test_inventory_out_of_stock_sku():
    state = store.inventory_state("SKU-1002")
    assert state is not None
    assert state["stock_qty"] == 0
    assert state["in_stock"] is False


def test_add_to_cart_does_not_change_stock():
    before = store.inventory_state("SKU-1001")["stock_qty"]
    result = store.add_to_cart("cart-store", "SKU-1001", qty=1)
    after = store.inventory_state("SKU-1001")["stock_qty"]
    assert result["ok"] is True
    assert after == before


def test_add_to_cart_rejects_out_of_stock():
    result = store.add_to_cart("cart-oos", "SKU-1002", qty=1)
    assert result["ok"] is False
    assert "out of stock" in result["error"]


def test_place_order_decrements_stock_and_clears_cart():
    before = store.inventory_state("SKU-1001")["stock_qty"]
    added = store.add_to_cart("cart-order", "SKU-1001", qty=2)
    assert added["ok"] is True

    placed = store.place_order("cart-order")
    assert placed["ok"] is True
    order = placed["order"]
    assert order["order_id"].startswith("ORD-")
    assert order["total"] > 0
    assert store.get_cart("cart-order") is None
    assert store.get_order(order["order_id"])["status"] == "placed"
    assert store.inventory_state("SKU-1001")["stock_qty"] == before - 2
