from mcp_retail_sim.prompts import compare_products, find_best_deal


def test_compare_products_uses_sku_resources():
    text = compare_products("SKU-1000", "SKU-1001")
    assert "SKU-1000" in text
    assert "SKU-1001" in text
    assert "product://SKU-1000" in text
    assert "product://SKU-1001" in text


def test_find_best_deal_treats_query_as_search_text():
    text = find_best_deal("headphones", budget=100)
    assert "headphones" in text
    assert "100" in text
    assert "search string, not a SKU" in text
    assert "Do not open product://headphones" in text
    assert "Call the search tool" in text
    assert "check_inventory" in text
    assert "product://{sku}" in text
    assert "product://SKU-1001" in text
