import mcp_retail_sim.store as store


def setup_function():
    store.reset_runtime_state()


def test_search_headphones_returns_products():
    hits = store.search_products("headphones")
    assert hits
    assert any("headphone" in hit["name"].lower() for hit in hits)


def test_search_unknown_query_returns_empty():
    assert store.search_products("zzzz-not-a-product") == []


def test_search_blank_query_without_filters_returns_empty():
    assert store.search_products("") == []
    assert store.search_products("   ") == []


def test_search_matches_dietary_tags():
    hits = store.search_products("vegan")
    assert hits
    assert any(
        "vegan" in (hit.get("tags") or [])
        or (hit.get("attrs") or {}).get("dietary") == "vegan"
        for hit in hits
    )


def test_search_filter_only_category_and_dietary():
    hits = store.search_products(
        "",
        category="grocery_pantry",
        dietary="vegan",
        max_price=40.0,
        in_stock=True,
        limit=20,
    )
    assert hits
    for hit in hits:
        assert hit["category"] == "grocery_pantry"
        assert hit["attrs"]["dietary"] == "vegan"
        assert float(hit["price"]) <= 40.0
        assert store.inventory_state(hit["sku"])["in_stock"] is True


def test_search_filters_combine_with_query():
    hits = store.search_products(
        "tea",
        category="grocery_pantry",
        organic=True,
        limit=20,
    )
    assert hits
    for hit in hits:
        assert hit["category"] == "grocery_pantry"
        assert hit["attrs"].get("organic") is True
        assert "tea" in (
            hit["name"] + hit["description"] + hit["category"] + hit["brand"] + " ".join(hit.get("tags") or [])
        ).lower()


def test_search_in_stock_false_finds_oos_sku():
    hits = store.search_products(
        "",
        category="electronics",
        in_stock=False,
        limit=50,
    )
    assert hits
    assert any(h["sku"] == "SKU-1002" for h in hits)
    for hit in hits:
        assert store.inventory_state(hit["sku"])["in_stock"] is False


def test_grocery_attrs_include_single_allergen():
    product = store.product_details("SKU-1302")
    assert product is not None
    attrs = product["attrs"]
    assert attrs["dietary"] in {"vegan", "vegetarian", "omnivore_ok"}
    assert isinstance(attrs["organic"], bool)
    assert attrs["sugar_level"] in {"low", "standard"}
    assert attrs["allergen"] in {"none", "nuts", "gluten", "dairy"}
    assert attrs["pack_size"] in {"single", "family"}


def test_electronics_power_source_enum():
    product = store.product_details("SKU-1001")
    assert product is not None
    assert product["attrs"]["power_source"] in {
        "battery",
        "mains",
        "passive",
        "rechargeable",
    }
    assert product["attrs"]["connectivity"] in {
        "bluetooth",
        "usb-c",
        "wifi",
        "wired",
    }


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


def test_add_to_cart_includes_total():
    product = store.product_details("SKU-1001")
    assert product is not None
    unit = float(product["price"])

    result = store.add_to_cart("cart-total", "SKU-1001", qty=2)
    assert result["ok"] is True
    cart = result["cart"]
    assert cart["total"] == round(unit * 2, 2)
    assert cart["currency"] == "USD"

    fetched = store.get_cart("cart-total")
    assert fetched is not None
    assert fetched["total"] == cart["total"]
    assert fetched["currency"] == "USD"


def test_add_to_cart_rejects_out_of_stock():
    result = store.add_to_cart("cart-oos", "SKU-1002", qty=1)
    assert result["ok"] is False
    assert "out of stock" in result["error"]


def test_remove_from_cart_decrements_qty_and_total():
    product = store.product_details("SKU-1001")
    assert product is not None
    unit = float(product["price"])

    added = store.add_to_cart("cart-rm", "SKU-1001", qty=3)
    assert added["ok"] is True

    removed = store.store_remove_from_cart("cart-rm", "SKU-1001", quantity=1)
    assert removed["ok"] is True
    cart = removed["cart"]
    assert cart["items"][0]["qty"] == 2
    assert cart["total"] == round(unit * 2, 2)

    removed_all = store.store_remove_from_cart("cart-rm", "SKU-1001", quantity=2)
    assert removed_all["ok"] is True
    empty = removed_all["cart"]
    assert empty["items"] == []
    assert empty["total"] == 0.0
    assert store.get_cart("cart-rm") is not None


def test_remove_from_cart_unknown_cart_or_sku():
    assert store.store_remove_from_cart("missing", "SKU-1001")["ok"] is False
    store.add_to_cart("cart-rm2", "SKU-1001", qty=1)
    bad = store.store_remove_from_cart("cart-rm2", "SKU-1003")
    assert bad["ok"] is False
    assert "product not in cart" in bad["error"]


def test_place_order_decrements_stock_and_clears_cart():
    before = store.inventory_state("SKU-1001")["stock_qty"]
    added = store.add_to_cart("cart-order", "SKU-1001", qty=2)
    assert added["ok"] is True
    assert added["cart"]["total"] > 0

    placed = store.place_order("cart-order")
    assert placed["ok"] is True
    order = placed["order"]
    assert order["order_id"].startswith("ORD-")
    assert order["total"] > 0
    assert store.get_cart("cart-order") is None
    assert store.get_order(order["order_id"])["status"] == "placed"
    assert store.inventory_state("SKU-1001")["stock_qty"] == before - 2


def test_place_order_idempotent_replay_returns_same_order():
    before = store.inventory_state("SKU-1001")["stock_qty"]
    store.add_to_cart("cart-idem", "SKU-1001", qty=1)

    first = store.place_order("cart-idem", idempotency_key="checkout-run-1")
    assert first["ok"] is True
    order_id = first["order"]["order_id"]
    assert store.get_cart("cart-idem") is None
    assert store.inventory_state("SKU-1001")["stock_qty"] == before - 1

    # Retry after cart is gone: same key returns original order, no extra stock hit.
    replay = store.place_order("cart-idem", idempotency_key="checkout-run-1")
    assert replay["ok"] is True
    assert replay["order"]["order_id"] == order_id
    assert store.inventory_state("SKU-1001")["stock_qty"] == before - 1
    assert store._IDEMPOTENCY["checkout-run-1"]["order_id"] == order_id


def test_place_order_idempotent_conflict_different_fingerprint():
    store.add_to_cart("cart-a", "SKU-1001", qty=1)
    first = store.place_order("cart-a", idempotency_key="checkout-reuse")
    assert first["ok"] is True

    store.add_to_cart("cart-a", "SKU-1001", qty=2)
    conflict = store.place_order("cart-a", idempotency_key="checkout-reuse")
    assert conflict["ok"] is False
    assert "different cart fingerprint" in conflict["error"]


def test_reset_runtime_state_restores_inventory_and_clears_runtime():
    baseline = store.inventory_state("SKU-1001")["stock_qty"]
    store.add_to_cart("cart-reset", "SKU-1001", qty=2)
    placed = store.place_order("cart-reset", idempotency_key="checkout-reset-1")
    assert placed["ok"] is True
    assert store.inventory_state("SKU-1001")["stock_qty"] == baseline - 2
    assert store._ORDERS
    assert store._IDEMPOTENCY

    store.reset_runtime_state()

    assert store.get_cart("cart-reset") is None
    assert store._ORDERS == {}
    assert store._IDEMPOTENCY == {}
    assert store.inventory_state("SKU-1001")["stock_qty"] == baseline
