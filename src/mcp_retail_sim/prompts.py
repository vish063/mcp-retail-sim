from mcp_retail_sim.server import mcp

@mcp.prompt()
def compare_products(product1: str, product2: str) -> str:
    """Compare products and return the differences."""
    return f"""
    compare products {product1} and {product2}.
    use resources product://{product1} and product://{product2} to get the product details.
    summarize the difference in price, features, and other relevant information. 
    """

@mcp.prompt()
def find_best_deal(query: str, budget: float = 100.0) -> str:
    """Find the best deal for a product within a budget."""
    return f"""
    find the best deal for {query} within a budget of {budget}.
    use resources product://{query} to get the product details. 
    search tool, check inventory, and find the best deal.
    summarize the best deal and return the details.
    """