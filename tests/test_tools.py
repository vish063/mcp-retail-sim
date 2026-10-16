import mcp_retail_sim.store as store
from mcp_retail_sim.tools import (
    add_to_cart,
    check_inventory,
    get_order_details,
    get_product_details,
    place_order,
    search,
)


def setup_function():
    store._CARTS.clear()
    store._ORDERS.clear()


def test_search_tool_finds_headphones():
    hits = search("headphones")
    assert hits
    assert hits[0]["sku"].startswith("SKU-")


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

    placed = place_order(" cart-1 ")
    assert placed["ok"] is True
    order_id = placed["order"]["order_id"]

    order = get_order_details(f" {order_id} ")
    assert order is not None
    assert order["order_id"] == order_id
    assert check_inventory("SKU-1001")["stock_qty"] == before - 1
