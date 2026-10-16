from mcp_retail_sim.helpers import sanitize_product_id
from mcp_retail_sim.server import mcp
from mcp_retail_sim.store import get_policy, inventory_state, product_details


def _policy_text(policy_id: str) -> str:
    policy = get_policy(policy_id)
    if policy is None:
        return f"Policy not found: {policy_id}"
    title = policy.get("title", policy_id)
    body = policy.get("body", "")
    return f"# {title}\n\n{body}"


@mcp.resource("policy://returns")
def returns_policy() -> str:
    """Get returns policy"""
    return _policy_text("returns")


@mcp.resource("policy://shipping")
def shipping_policy() -> str:
    """Get shipping policy"""
    return _policy_text("shipping")


@mcp.resource("policy://privacy")
def privacy_policy() -> str:
    """Get privacy policy"""
    return _policy_text("privacy")


@mcp.resource("product://{sku}")
def product_page(sku: str) -> str:
    """Readable product page document (for prompts / context).

    For compact facts in a tool loop, use get_product_details instead.
    """
    product_id = sanitize_product_id(sku)
    if product_id is None:
        return f"Invalid product SKU: {sku}"

    product = product_details(product_id)
    if product is None:
        return f"Product not found: {product_id}"

    stock = inventory_state(product_id)
    if stock is None:
        stock_line = "- **Stock:** unknown"
    else:
        label = "in stock" if stock["in_stock"] else "out of stock"
        stock_line = f"- **Stock:** {stock['stock_qty']} ({label})"

    tags = ", ".join(product.get("tags") or []) or "—"
    attrs = product.get("attrs") or {}
    attr_lines = "\n".join(f"- **{k}:** {v}" for k, v in attrs.items()) or "- —"

    return f"""# {product.get("name", product_id)}

            - **SKU:** `{product.get("sku", product_id)}`
            - **Brand:** {product.get("brand", "—")}
            - **Category:** {product.get("category", "—")}
            - **Price:** {product.get("price")} {product.get("currency", "USD")}
            {stock_line}
            - **Tags:** {tags}

            ## Description

            {product.get("description", "")}

            ## Attributes

            {attr_lines}
            """
