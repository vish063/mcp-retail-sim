from mcp_retail_sim.resources import (
    privacy_policy,
    product_page,
    returns_policy,
    shipping_policy,
)


def test_returns_policy_text():
    text = returns_policy()
    assert text.startswith("# Returns")
    assert "30 days" in text


def test_shipping_policy_text():
    text = shipping_policy()
    assert "Shipping" in text
    assert "3–5 business days" in text or "3-5 business days" in text


def test_privacy_policy_text():
    text = privacy_policy()
    assert "Privacy" in text
    assert "synthetic" in text.lower()


def test_product_page_known_sku():
    text = product_page(" SKU-1001 ")
    assert "SKU-1001" in text
    assert "Headphones" in text
    assert "in stock" in text


def test_product_page_unknown_sku():
    assert product_page("SKU-DOES-NOT-EXIST") == "Product not found: SKU-DOES-NOT-EXIST"


def test_product_page_invalid_sku():
    assert "Invalid product SKU" in product_page("SKU 1001")
