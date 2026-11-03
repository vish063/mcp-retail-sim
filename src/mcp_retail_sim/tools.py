from typing import Annotated, Any

from mcp.types import ToolAnnotations
from pydantic import BeforeValidator, Field

from mcp_retail_sim.helpers import (
    blank_to_none,
    parse_optional_bool,
    parse_optional_float,
    sanitize_cart_id,
    sanitize_idempotency_key,
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
    get_cart as store_get_cart,
    store_remove_from_cart,
)

# MCP hints for hosts/UIs (not enforced by this server).
_READ_ONLY = ToolAnnotations(
    read_only_hint=True,
    destructive_hint=False,
    idempotent_hint=True,
    open_world_hint=False,
)
_CART_WRITE = ToolAnnotations(
    read_only_hint=False,
    destructive_hint=False,
    idempotent_hint=False,
    open_world_hint=False,
)
_CART_REMOVE = ToolAnnotations(
    read_only_hint=False,
    destructive_hint=True,
    idempotent_hint=False,
    open_world_hint=False,
)
_CHECKOUT = ToolAnnotations(
    read_only_hint=False,
    destructive_hint=True,
    # Optional idempotency_key can make retries safe, but omitting the key is not.
    idempotent_hint=False,
    open_world_hint=False,
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

IdempotencyKey = Annotated[
    str,
    BeforeValidator(_strip_id),
    Field(
        pattern=_ID_PATTERN,
        description=(
            "Client-stable checkout attempt id, e.g. checkout-run-1. "
            "Same key + same cart returns the original order; "
            "same key + different cart is rejected."
        ),
    ),
]


Query = Annotated[
    str,
    Field(
        description=(
            "Optional substring matched against name, description, category, brand, and tags. "
            "Try headphones, laptop, coffee, vegan, organic, yoga, or tv. "
            "May be empty when using filters alone."
        ),
    ),
]


@mcp.tool(annotations=_READ_ONLY)
def search(
    query: Query = "",
    category: str | None = None,
    brand: str | None = None,
    tag: str | None = None,
    max_price: str | None = None,
    min_price: str | None = None,
    in_stock: str | None = None,
    dietary: str | None = None,
    organic: str | None = None,
    limit: int = 50,
) -> list[dict]:
    """Search the synthetic catalog (about 1000 products).

    Free-text query and structured filters can be combined (AND).
    Leave filter fields empty/unset to ignore them (do not pass false/0 unless
    you intend that filter). Examples: query=headphones;
    category=grocery_pantry + dietary=vegan + max_price=20;
    query empty + category=beauty + organic=true.
    """
    return search_products(
        sanitize_query(query),
        category=blank_to_none(category),
        brand=blank_to_none(brand),
        tag=blank_to_none(tag),
        max_price=parse_optional_float(max_price),
        min_price=parse_optional_float(min_price),
        in_stock=parse_optional_bool(in_stock),
        dietary=blank_to_none(dietary),
        organic=parse_optional_bool(organic),
        limit=limit,
    )

@mcp.tool(annotations=_READ_ONLY)
def get_product_details(product_id: ProductId) -> dict[str, Any] | None:
    """Get one product by SKU. Example: SKU-1001 (LumenLab Pro Headphones)."""
    sku = sanitize_product_id(product_id) if product_id else None
    if sku is None:
        return None
    return product_details(sku)

@mcp.tool(annotations=_READ_ONLY)
def check_inventory(product_id: ProductId) -> dict[str, Any] | None:
    """Check stock for a SKU.

    Example in stock: SKU-1001. Example out of stock: SKU-1002.
    Returns stock_qty and in_stock. Does not change inventory.
    """
    sku = sanitize_product_id(product_id)
    if sku is None:
        return None
    return inventory_state(sku)

@mcp.tool(annotations=_CART_WRITE)
def add_to_cart(
    cart_id: CartId,
    product_id: ProductId,
    qty: int = 1,
) -> dict[str, Any]:
    """Add a product to a cart. Does not decrement stock.

    Example: cart_id=cart-1, product_id=SKU-1001, qty=1.
    Use any new cart id; the cart is created if it does not exist.
    On success returns the cart with items, total, and currency.
    Fails if the SKU is unknown or out of stock (try SKU-1002 to see that error).
    """
    cid = sanitize_cart_id(cart_id)
    sku = sanitize_product_id(product_id)
    if cid is None:
        return {"ok": False, "error": "invalid cart_id"}
    if sku is None:
        return {"ok": False, "error": "invalid product_id"}
    return store_add_to_cart(cid, sku, qty)

@mcp.tool(annotations=_CHECKOUT)
def place_order(
    cart_id: CartId,
    idempotency_key: IdempotencyKey | None = None,
) -> dict[str, Any]:
    """Check out a cart created by add_to_cart.

    Example: cart_id=cart-1 after adding SKU-1001.
    Optional idempotency_key makes checkout safely retryable: the same key with
    the same cart fingerprint returns the original order; a reused key with a
    different cart is rejected. Omitting the key keeps legacy one-shot behavior.
    Decrements stock, returns an order_id like ORD-XXXXXXXX, and deletes the cart.
    """
    cid = sanitize_cart_id(cart_id)
    if cid is None:
        return {"ok": False, "error": "invalid cart_id"}
    key = None
    if idempotency_key is not None:
        key = sanitize_idempotency_key(idempotency_key)
        if key is None:
            return {"ok": False, "error": "invalid idempotency_key"}
    return store_place_order(cid, idempotency_key=key)

@mcp.tool(annotations=_READ_ONLY)
def get_order_details(order_id: OrderId) -> dict[str, Any] | None:
    """Read an order created by place_order.

    Pass the order_id from that response, for example ORD-E2F0C262.
    Orders exist only in this server process; a new process has none.
    """
    oid = sanitize_order_id(order_id)
    if oid is None:
        return None
    return get_order(oid)

@mcp.tool(annotations=_READ_ONLY)
def get_cart(cart_id: CartId) -> dict[str, Any] | None:
    """Read a cart created by add_to_cart.

    Example: cart_id=cart-1 after adding SKU-1001.
    Returns a cart with items and total. Does not change cart.
    """
    cid = sanitize_cart_id(cart_id)
    if cid is None:
        return None
    return store_get_cart(cid)

@mcp.tool(annotations=_CART_REMOVE)
def remove_from_cart(
    cart_id: CartId,
    product_id: ProductId,
    quantity: int = 1,
) -> dict[str, Any]:
    """Remove a quantity of a product from a cart. Does not change inventory.

    Example: cart_id=cart-1, product_id=SKU-1001, quantity=1.
    Decrements qty; removes the line when qty reaches 0. Empty carts are kept.
    On success returns the updated cart with items, total, and currency.
    """
    cid = sanitize_cart_id(cart_id)
    sku = sanitize_product_id(product_id)
    if cid is None:
        return {"ok": False, "error": "invalid cart_id"}
    if sku is None:
        return {"ok": False, "error": "invalid product_id"}
    return store_remove_from_cart(cid, sku, quantity)