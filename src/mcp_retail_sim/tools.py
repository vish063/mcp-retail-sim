from typing import Annotated, Any

from pydantic import Field

from mcp_retail_sim.helpers import (
    sanitize_cart_id,
    sanitize_order_id,
    sanitize_product_id,
    sanitize_query,
)
from mcp_retail_sim.server import mcp
from mcp_retail_sim.store import (
    add_to_cart as store_add_to_cart,
    get_order,
    inventory_state,
    place_order as store_place_order,
    product_details,
    search_products,
)

ProductId = Annotated[
    str,
    Field(
        pattern=r"^[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*$",
        description="Alphanumeric product SKU (hyphens ok), e.g. SKU-1000",
    ),
]

CartId = Annotated[
    str,
    Field(
        pattern=r"^[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*$",
        description="Client-generated cart handle, e.g. cart-123",
    ),
]

OrderId = Annotated[
    str,
    Field(
        pattern=r"^[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*$",
        description="Order id from place_order, e.g. ORD-E2F0C262",
    ),
]


@mcp.tool
def search(query: str) -> list[dict]:
    """Search for products"""
    products = search_products(sanitize_query(query))
    return products

@mcp.tool
def get_product_details(product_id: ProductId) -> dict[str, Any] | None:
    """Get product details by SKU."""
    if product_id is None:
        return None
    return product_details(product_id)

@mcp.tool
def check_inventory(product_id: ProductId) -> dict[str, Any] | None:
    """Check inventory for the product"""
    sku = sanitize_product_id(product_id)
    if sku is None:
        return None
    return inventory_state(sku)

@mcp.tool
def add_to_cart(
    cart_id: CartId,
    product_id: ProductId,
    qty: int = 1,
) -> dict[str, Any]:
    """Add a product to a cart (creates cart if needed). Does not decrement stock."""
    cid = sanitize_cart_id(cart_id)
    sku = sanitize_product_id(product_id)
    if cid is None:
        return {"ok": False, "error": "invalid cart_id"}
    if sku is None:
        return {"ok": False, "error": "invalid product_id"}
    return store_add_to_cart(cid, sku, qty)

@mcp.tool
def place_order(cart_id: CartId) -> dict[str, Any]:
    """Place an order from a cart: decrements stock and clears the cart."""
    cid = sanitize_cart_id(cart_id)
    if cid is None:
        return {"ok": False, "error": "invalid cart_id"}
    return store_place_order(cid)

@mcp.tool
def get_order_details(order_id: OrderId) -> dict[str, Any] | None:
    """Get order details by order_id."""
    oid = sanitize_order_id(order_id)
    if oid is None:
        return None
    return get_order(oid)
