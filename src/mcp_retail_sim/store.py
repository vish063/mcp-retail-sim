"""Fixture-backed in-memory store helpers.

Load products / inventory / policies from package data.
Tools will call these helpers later (search first).
"""

from __future__ import annotations

import hashlib
import json
import uuid
from functools import lru_cache
from importlib.resources import files
from typing import Any
from mcp_retail_sim import eval_fixtures, faults

def _read_json(filename: str) -> Any:
    path = files("mcp_retail_sim").joinpath("data", filename)
    return json.loads(path.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def load_products() -> list[dict[str, Any]]:
    """Load catalog from products.json (cached for process lifetime).

    When eval adversarial fixtures are enabled, append opt-in eval SKUs.
    """
    products: list[dict[str, Any]] = list(_read_json("products.json"))
    if eval_fixtures.adversarial_enabled():
        products.extend(_read_json("eval_adversarial_products.json"))
    return products


@lru_cache(maxsize=1)
def load_inventory() -> dict[str, int]:
    """sku -> stock_qty."""
    rows = _read_json("inventory.json")
    inventory = {row["sku"]: int(row["stock_qty"]) for row in rows}
    if eval_fixtures.adversarial_enabled():
        for row in _read_json("eval_adversarial_inventory.json"):
            inventory[row["sku"]] = int(row["stock_qty"])
    return inventory


@lru_cache(maxsize=1)
def load_policies() -> dict[str, dict[str, Any]]:
    return _read_json("policies.json")


def search_products(
    query: str = "",
    *,
    category: str | None = None,
    brand: str | None = None,
    tag: str | None = None,
    max_price: float | None = None,
    min_price: float | None = None,
    in_stock: bool | None = None,
    dietary: str | None = None,
    organic: bool | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Search catalog by optional free-text query and/or structured filters.

    Query (if non-empty) is a case-insensitive substring of name, description,
    category, brand, or tags. Filters are ANDed. Exact case-insensitive match
    for category, brand, tag, and dietary. Empty query with no filters → [].
    """
    if limit < 1:
        return []

    q = query.strip().lower()
    category_f = category.strip().lower() if category and category.strip() else None
    brand_f = brand.strip().lower() if brand and brand.strip() else None
    tag_f = tag.strip().lower() if tag and tag.strip() else None
    dietary_f = dietary.strip().lower() if dietary and dietary.strip() else None

    has_filter = any(
        v is not None
        for v in (
            category_f,
            brand_f,
            tag_f,
            max_price,
            min_price,
            in_stock,
            dietary_f,
            organic,
        )
    )
    if not q and not has_filter:
        return []

    inventory = load_inventory() if in_stock is not None else None
    matches: list[dict[str, Any]] = []

    for product in load_products():
        tags = product.get("tags") or []
        attrs = product.get("attrs") or {}

        if category_f is not None and str(product.get("category", "")).lower() != category_f:
            continue
        if brand_f is not None and str(product.get("brand", "")).lower() != brand_f:
            continue
        if tag_f is not None and tag_f not in {str(t).lower() for t in tags}:
            continue
        if dietary_f is not None and str(attrs.get("dietary", "")).lower() != dietary_f:
            continue
        if organic is not None and attrs.get("organic") is not organic:
            continue

        try:
            price = float(product.get("price"))
        except (TypeError, ValueError):
            continue
        if max_price is not None and price > max_price:
            continue
        if min_price is not None and price < min_price:
            continue

        if in_stock is not None and inventory is not None:
            sku = product.get("sku")
            qty = inventory.get(sku, 0) if sku in inventory else None
            if qty is None:
                continue
            product_in_stock = qty > 0
            if product_in_stock is not in_stock:
                continue

        if q:
            haystack = " ".join(
                [
                    str(product.get("name", "")),
                    str(product.get("description", "")),
                    str(product.get("category", "")),
                    str(product.get("brand", "")),
                    " ".join(str(t) for t in tags),
                ]
            ).lower()
            if q not in haystack:
                continue

        matches.append(product)
        if len(matches) >= limit:
            break
    return matches

def product_details(product_id: str) -> dict[str, Any] | None:
    """Return one product by SKU/product_id, or None if not found.

    Expects an already-sanitized alphanumeric SKU (see helpers.sanitize_product_id).
    Looks up `sku` in the products list (load_products returns a list, not a dict).
    """
    if not product_id:
        return None
    for product in load_products():
        if product.get("sku") == product_id:
            return product
    return None

def inventory_state(product_id: str) -> dict[str, Any] | None:
    """Return stock info for a SKU, or None if the SKU is unknown.

    Shape: {"sku", "stock_qty", "in_stock"}.
    Note: missing SKU must not be treated as 0 — 0 means known out-of-stock.
    """
    if not product_id:
        return None
    inventory = load_inventory()
    if product_id not in inventory:
        return None
    qty = inventory[product_id]
    return {
        "sku": product_id,
        "stock_qty": qty,
        "in_stock": qty > 0,
    }


# Runtime carts only (not fixture files). Keyed by client-provided cart_id.
# Does not decrement inventory — that happens on place_order.
_CARTS: dict[str, dict[str, Any]] = {}


def _cart_subtotal(items: list[dict[str, Any]]) -> float:
    """Sum of price * qty for cart lines, rounded to cents."""
    return round(sum(float(item["price"]) * int(item["qty"]) for item in items), 2)


def _refresh_cart_totals(cart: dict[str, Any]) -> dict[str, Any]:
    """Ensure cart has total and currency derived from line items."""
    items: list[dict[str, Any]] = cart.get("items") or []
    cart["total"] = _cart_subtotal(items)
    cart["currency"] = "USD"
    return cart


def get_cart(cart_id: str) -> dict[str, Any] | None:
    """Return cart dict (with total) or None if unknown."""
    cart = _CARTS.get(cart_id)
    if cart is None:
        return None
    return _refresh_cart_totals(cart)


def add_to_cart(cart_id: str, product_id: str, qty: int = 1) -> dict[str, Any]:
    """Add (or increase) a line item. Creates the cart if needed.

    Does **not** change inventory. Returns {"ok": True, "cart": ...} or
    {"ok": False, "error": "..."}. Cart includes total and currency.
    """
    if qty < 1:
        return {"ok": False, "error": "qty must be >= 1"}

    product = product_details(product_id)
    if product is None:
        return {"ok": False, "error": f"unknown product_id: {product_id}"}

    stock = inventory_state(product_id)
    if stock is None:
        return {"ok": False, "error": f"no inventory row for: {product_id}"}
    if not stock["in_stock"]:
        return {"ok": False, "error": f"out of stock: {product_id}"}

    cart = _CARTS.setdefault(
        cart_id,
        {"cart_id": cart_id, "items": [], "total": 0.0, "currency": "USD"},
    )
    items: list[dict[str, Any]] = cart["items"]

    existing = next((item for item in items if item["sku"] == product_id), None)
    new_qty = (existing["qty"] if existing else 0) + qty
    if new_qty > stock["stock_qty"]:
        return {
            "ok": False,
            "error": (
                f"requested qty {new_qty} exceeds stock "
                f"{stock['stock_qty']} for {product_id}"
            ),
        }

    if existing:
        existing["qty"] = new_qty
    else:
        items.append(
            {
                "sku": product_id,
                "qty": qty,
                "name": product.get("name"),
                "price": product.get("price"),
                "currency": product.get("currency", "USD"),
            }
        )

    return {"ok": True, "cart": _refresh_cart_totals(cart)}

def store_remove_from_cart(
    cart_id: str,
    product_id: str,
    quantity: int = 1,
) -> dict[str, Any]:
    """Remove a quantity of a product from a cart. Does not change inventory.

    Decrements the line qty; drops the line when qty reaches 0.
    Keeps an empty cart (items=[]) rather than deleting the cart_id.
    Returns {"ok": True, "cart": ...} or {"ok": False, "error": "..."}.
    """
    if quantity < 1:
        return {"ok": False, "error": "quantity must be >= 1"}

    cart = _CARTS.get(cart_id)
    if cart is None:
        return {"ok": False, "error": f"unknown cart_id: {cart_id}"}

    items: list[dict[str, Any]] = cart.get("items") or []
    existing = next((item for item in items if item["sku"] == product_id), None)
    if existing is None:
        return {"ok": False, "error": f"product not in cart: {product_id}"}

    new_qty = int(existing["qty"]) - quantity
    if new_qty > 0:
        existing["qty"] = new_qty
    else:
        cart["items"] = [item for item in items if item["sku"] != product_id]

    return {"ok": True, "cart": _refresh_cart_totals(cart)}



# Runtime orders (created by place_order).
_ORDERS: dict[str, dict[str, Any]] = {}

# Checkout idempotency: key -> {fingerprint, order_id}. Process memory only.
_IDEMPOTENCY: dict[str, dict[str, str]] = {}


def reset_runtime_state() -> None:
    """Reset in-memory runtime state to fixture defaults (test/eval only).

    Clears carts, orders, and idempotency records; clears fault injection;
    reloads products/inventory/policies from package JSON on next access.
    Not exposed as an agent-facing MCP tool.
    """
    _CARTS.clear()
    _ORDERS.clear()
    _IDEMPOTENCY.clear()
    faults.clear_faults()
    load_products.cache_clear()
    load_inventory.cache_clear()
    load_policies.cache_clear()


def get_order(order_id: str) -> dict[str, Any] | None:
    """Return an order by id, or None if unknown."""
    return _ORDERS.get(order_id)


def _cart_fingerprint(cart_id: str, items: list[dict[str, Any]]) -> str:
    """Stable hash of cart_id + sorted (sku, qty, price) lines."""
    lines = sorted(
        (
            str(item["sku"]),
            int(item["qty"]),
            round(float(item["price"]), 2),
        )
        for item in items
    )
    payload = json.dumps(
        {"cart_id": cart_id, "items": lines},
        separators=(",", ":"),
        ensure_ascii=True,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def place_order(
    cart_id: str,
    idempotency_key: str | None = None,
) -> dict[str, Any]:
    """Checkout a cart: validate stock, decrement inventory, create order, clear cart.

    Optional idempotency_key:
    - same key + same cart fingerprint → return the original order (no double charge)
    - same key + different fingerprint → reject
    - omitted → non-idempotent checkout (legacy behavior)

    Idempotency records live in process memory (_IDEMPOTENCY), like orders.
    Returns {"ok": True, "order": ...} or {"ok": False, "error": "..."}.
    """
    cart = _CARTS.get(cart_id)
    items: list[dict[str, Any]] = (cart.get("items") or []) if cart else []
    fingerprint = _cart_fingerprint(cart_id, items) if items else None

    if idempotency_key:
        prior = _IDEMPOTENCY.get(idempotency_key)
        if prior is not None:
            if fingerprint is not None and fingerprint != prior["fingerprint"]:
                return {
                    "ok": False,
                    "error": (
                        "idempotency key reused with a different cart fingerprint"
                    ),
                }
            order = _ORDERS.get(prior["order_id"])
            if order is None:
                return {
                    "ok": False,
                    "error": (
                        f"idempotency record missing order: {prior['order_id']}"
                    ),
                }
            return {"ok": True, "order": order}

    if cart is None:
        return {"ok": False, "error": f"unknown cart_id: {cart_id}"}
    if not items:
        return {"ok": False, "error": "cart is empty"}

    faults.apply_latency_if_configured()
    pre_fault = faults.pre_commit_fault(items)
    if pre_fault is not None:
        return pre_fault

    inventory = load_inventory()

    # Validate all lines before mutating stock.
    for item in items:
        sku = item["sku"]
        qty = int(item["qty"])
        if sku not in inventory:
            return {"ok": False, "error": f"no inventory row for: {sku}"}
        if inventory[sku] < qty:
            return {
                "ok": False,
                "error": (
                    f"insufficient stock for {sku}: "
                    f"need {qty}, have {inventory[sku]}"
                ),
            }

    # Decrement stock (mutates the cached inventory dict for this process).
    for item in items:
        inventory[item["sku"]] -= int(item["qty"])

    order_id = f"ORD-{uuid.uuid4().hex[:8].upper()}"
    order = {
        "order_id": order_id,
        "cart_id": cart_id,
        "items": [dict(item) for item in items],
        "total": _cart_subtotal(items),
        "currency": "USD",
        "status": "placed",
    }
    _ORDERS[order_id] = order

    if idempotency_key and fingerprint is not None:
        _IDEMPOTENCY[idempotency_key] = {
            "fingerprint": fingerprint,
            "order_id": order_id,
        }

    # Cart is consumed after checkout.
    del _CARTS[cart_id]

    post_fault = faults.post_commit_fault()
    if post_fault is not None:
        return post_fault

    return {"ok": True, "order": order}

def get_policy(policy_id: str) -> dict[str, Any] | None:
    """Return a policy by id, or None if unknown."""
    policies = load_policies()
    return policies.get(policy_id)