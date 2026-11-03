import asyncio

import mcp_retail_sim.store as store
import mcp_retail_sim.tools  # noqa: F401 — register tools
from mcp_retail_sim.server import mcp
from mcp_retail_sim.tools import (
    add_to_cart,
    check_inventory,
    get_cart,
    get_order_details,
    get_product_details,
    place_order,
    search,
)


def setup_function():
    store.reset_runtime_state()


def test_tool_annotations_are_registered():
    tools = asyncio.run(mcp.list_tools())
    by_name = {t.name: t for t in tools}

    def ann(name: str):
        a = by_name[name].annotations
        assert a is not None
        return a

    assert ann("search").read_only_hint is True
    assert ann("get_product_details").read_only_hint is True
    assert ann("check_inventory").read_only_hint is True
    assert ann("get_cart").read_only_hint is True
    assert ann("get_order_details").read_only_hint is True

    assert ann("add_to_cart").read_only_hint is False
    assert ann("add_to_cart").destructive_hint is False

    assert ann("remove_from_cart").destructive_hint is True
    assert ann("place_order").destructive_hint is True
    assert ann("place_order").idempotent_hint is False
    assert ann("place_order").open_world_hint is False


def test_search_tool_finds_headphones():
    hits = search("headphones")
    assert hits
    assert hits[0]["sku"].startswith("SKU-")


def test_search_tool_blank_filters_do_not_hide_query_hits():
    """Inspector-style empty strings must mean unset, not organic=false / max_price=0."""
    hits = search(
        "headphones",
        category="",
        brand="",
        tag="",
        max_price="",
        min_price="",
        in_stock="",
        dietary="",
        organic="",
    )
    assert hits
    assert any("headphone" in h["name"].lower() for h in hits)


def test_search_tool_string_bool_and_price_filters():
    hits = search(
        "",
        category="grocery_pantry",
        dietary="vegan",
        max_price="40",
        in_stock="true",
        limit=20,
    )
    assert hits
    for hit in hits:
        assert hit["category"] == "grocery_pantry"
        assert hit["attrs"]["dietary"] == "vegan"
        assert float(hit["price"]) <= 40.0


def test_search_tool_blank_query_returns_empty():
    assert search("   ") == []


def test_get_product_details_strips_whitespace():
    product = get_product_details(" SKU-1001 ")
    assert product is not None
    assert product["sku"] == "SKU-1001"


def test_get_product_details_rejects_bad_id():
    assert get_product_details("SKU 1001") is None


def test_check_inventory_out_of_stock():
    state = check_inventory("SKU-1002")
    assert state is not None
    assert state["in_stock"] is False


def test_tool_checkout_flow():
    before = check_inventory("SKU-1001")["stock_qty"]
    added = add_to_cart(" cart-1 ", " SKU-1001 ", qty=1)
    assert added["ok"] is True
    assert added["cart"]["total"] > 0
    assert added["cart"]["currency"] == "USD"

    cart = get_cart(" cart-1 ")
    assert cart is not None
    assert cart["total"] == added["cart"]["total"]

    placed = place_order(" cart-1 ", idempotency_key=" checkout-tool-1 ")
    assert placed["ok"] is True
    order_id = placed["order"]["order_id"]
    assert placed["order"]["total"] == cart["total"]

    replay = place_order(" cart-1 ", idempotency_key="checkout-tool-1")
    assert replay["ok"] is True
    assert replay["order"]["order_id"] == order_id
    assert check_inventory("SKU-1001")["stock_qty"] == before - 1

    order = get_order_details(f" {order_id} ")
    assert order is not None
    assert order["order_id"] == order_id
    assert check_inventory("SKU-1001")["stock_qty"] == before - 1
