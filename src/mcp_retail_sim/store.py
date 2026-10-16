"""Fixture-backed in-memory store helpers.

Load products / inventory / policies from package data.
Tools will call these helpers later (search first).
"""

from __future__ import annotations

import json
import uuid
from functools import lru_cache
from importlib.resources import files
from typing import Any


def _read_json(filename: str) -> Any:
    path = files("mcp_retail_sim").joinpath("data", filename)
    return json.loads(path.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def load_products() -> list[dict[str, Any]]:
    """Load catalog from products.json (cached for process lifetime)."""
    return _read_json("products.json")


@lru_cache(maxsize=1)
def load_inventory() -> dict[str, int]:
    """sku -> stock_qty."""
    rows = _read_json("inventory.json")
    return {row["sku"]: int(row["stock_qty"]) for row in rows}


@lru_cache(maxsize=1)
def load_policies() -> dict[str, dict[str, Any]]:
    return _read_json("policies.json")


def search_products(query: str, *, limit: int = 20) -> list[dict[str, Any]]:
    """Return products whose name, description, category, or brand match query.

    Matching is case-insensitive substring match on those fields.
    Empty / whitespace-only query returns an empty list.
    """
    q = query.strip().lower()
    if not q:
        return []

    matches: list[dict[str, Any]] = []
    for product in load_products():
        haystack = " ".join(
            [
                str(product.get("name", "")),
                str(product.get("description", "")),
                str(product.get("category", "")),
                str(product.get("brand", "")),
            ]
        ).lower()
        if q in haystack:
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


def get_cart(cart_id: str) -> dict[str, Any] | None:
    """Return cart dict or None if unknown."""
    return _CARTS.get(cart_id)


def add_to_cart(cart_id: str, product_id: str, qty: int = 1) -> dict[str, Any]:
    """Add (or increase) a line item. Creates the cart if needed.

    Does **not** change inventory. Returns {"ok": True, "cart": ...} or
    {"ok": False, "error": "..."}.
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
        {"cart_id": cart_id, "items": []},
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

    return {"ok": True, "cart": cart}


# Runtime orders (created by place_order).
_ORDERS: dict[str, dict[str, Any]] = {}


def get_order(order_id: str) -> dict[str, Any] | None:
    """Return an order by id, or None if unknown."""
    return _ORDERS.get(order_id)


def place_order(cart_id: str) -> dict[str, Any]:
    """Checkout a cart: validate stock, decrement inventory, create order, clear cart.

    Returns {"ok": True, "order": ...} or {"ok": False, "error": "..."}.
    """
    cart = _CARTS.get(cart_id)
    if cart is None:
        return {"ok": False, "error": f"unknown cart_id: {cart_id}"}

    items: list[dict[str, Any]] = cart.get("items") or []
    if not items:
        return {"ok": False, "error": "cart is empty"}

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

    subtotal = sum(float(item["price"]) * int(item["qty"]) for item in items)
    order_id = f"ORD-{uuid.uuid4().hex[:8].upper()}"
    order = {
        "order_id": order_id,
        "cart_id": cart_id,
        "items": [dict(item) for item in items],
        "total": round(subtotal, 2),
        "currency": "USD",
        "status": "placed",
    }
    _ORDERS[order_id] = order

    # Cart is consumed after checkout.
    del _CARTS[cart_id]

    return {"ok": True, "order": order}

def get_policy(policy_id: str) -> dict[str, Any] | None:
    """Return a policy by id, or None if unknown."""
    policies = load_policies()
    return policies.get(policy_id)