from typing import Annotated, Any

from pydantic import BeforeValidator, Field

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

def _strip_id(value: object) -> object:
    """Drop surrounding whitespace before the ID pattern is checked."""
    if isinstance(value, str):
        return value.strip()
    return value


_ID_PATTERN = r"^[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*$"

ProductId = Annotated[
    str,
    BeforeValidator(_strip_id),
    Field(
        pattern=_ID_PATTERN,
        description="Alphanumeric product SKU (hyphens ok), e.g. SKU-1001",
    ),
]

CartId = Annotated[
    str,
    BeforeValidator(_strip_id),
    Field(
        pattern=_ID_PATTERN,
        description="Client-generated cart handle, e.g. cart-123",
    ),
]

OrderId = Annotated[
    str,
    BeforeValidator(_strip_id),
    Field(
        pattern=_ID_PATTERN,
        description="Order id from place_order, e.g. ORD-E2F0C262",
    ),
]


Query = Annotated[
    str,
    Field(
        description=(
            "Substring matched against name, description, category, and brand. "
            "Try headphones, laptop, coffee, yoga, or tv. A random word often returns []."
        ),
    ),
]


@mcp.tool
def search(query: Query) -> list[dict]:
    """Search the synthetic catalog (about 500 products).

    Example queries that return rows: headphones, laptop, coffee, yoga, tv, jacket.
    Matching is a case-insensitive substring of name, description, category, or brand.
    """
    products = search_products(sanitize_query(query))
    return products

@mcp.tool
def get_product_details(product_id: ProductId) -> dict[str, Any] | None:
    """Get one product by SKU. Example: SKU-1001 (LumenLab Pro Headphones)."""
    sku = sanitize_product_id(product_id) if product_id else None
    if sku is None:
        return None
    return product_details(sku)

@mcp.tool
def check_inventory(product_id: ProductId) -> dict[str, Any] | None:
    """Check stock for a SKU.

    Example in stock: SKU-1001. Example out of stock: SKU-1002.
    Returns stock_qty and in_stock. Does not change inventory.
    """
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
    """Add a product to a cart. Does not decrement stock.

    Example: cart_id=cart-1, product_id=SKU-1001, qty=1.
    Use any new cart id; the cart is created if it does not exist.
    Fails if the SKU is unknown or out of stock (try SKU-1002 to see that error).
    """
    cid = sanitize_cart_id(cart_id)
    sku = sanitize_product_id(product_id)
    if cid is None:
        return {"ok": False, "error": "invalid cart_id"}
    if sku is None:
        return {"ok": False, "error": "invalid product_id"}
    return store_add_to_cart(cid, sku, qty)

@mcp.tool
def place_order(cart_id: CartId) -> dict[str, Any]:
    """Check out a cart created by add_to_cart.

    Example: cart_id=cart-1 after adding SKU-1001.
    Decrements stock, returns an order_id like ORD-XXXXXXXX, and deletes the cart.
    """
    cid = sanitize_cart_id(cart_id)
    if cid is None:
        return {"ok": False, "error": "invalid cart_id"}
    return store_place_order(cid)

@mcp.tool
def get_order_details(order_id: OrderId) -> dict[str, Any] | None:
    """Read an order created by place_order.

    Pass the order_id from that response, for example ORD-E2F0C262.
    Orders exist only in this server process; a new process has none.
    """
    oid = sanitize_order_id(order_id)
    if oid is None:
        return None
    return get_order(oid)
