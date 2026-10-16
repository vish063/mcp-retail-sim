from mcp_retail_sim.server import mcp

@mcp.prompt()
def compare_products(product1: str, product2: str) -> str:
    """Compare two catalog SKUs. Example: product1=SKU-1000, product2=SKU-1001."""
    return f"""
    compare products {product1} and {product2}.
    use resources product://{product1} and product://{product2} to get the product details.
    summarize the difference in price, features, and other relevant information. 
    """

@mcp.prompt()
def find_best_deal(query: str, budget: float = 100.0) -> str:
    """Find a deal in the synthetic catalog. Example: query=headphones, budget=100."""
    return f"""
    Find the best deal for {query!r} with a budget of {budget}.
    {query!r} is a search string, not a SKU. Do not open product://{query}.
    1. Call the search tool with query {query!r}.
    2. From those results, keep products whose price is within the budget.
    3. For the SKUs you keep, call check_inventory and read product://{{sku}}
       (use the sku field from search, for example product://SKU-1001).
    4. Recommend one in-stock product and summarize price, stock, and why it fits.
    """