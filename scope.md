# mcp-retail-sim — Scope and status

> Maintainer checklist. Public docs live in `README.md`.

**Goal:** A retail MCP simulator (tools + resources + prompts + stdio and Streamable HTTP) that others can `uvx` and point agents at.

**Non-goals:** real DB, OAuth, elicitation, subscriptions, tasks extension, OpenTelemetry, multi-server gateway.

---

## Done

### Data and store

- [x] `products.json` — about 500 products, 15 categories, no stock on the product row
- [x] `inventory.json` — `{ sku, stock_qty }`, including some zero-stock SKUs
- [x] `policies.json` — returns, shipping, privacy
- [x] `store.py` — load fixtures, search, product lookup, inventory, in-memory carts and orders
- [x] Search matches name, description, category, and brand (case-insensitive substring)
- [x] `add_to_cart` does not change stock; `place_order` decrements stock and deletes the cart

### Tools (names in code)

| Tool | Status | Notes |
|---|---|---|
| `search` | done | Hints: headphones, laptop, coffee, yoga, tv, jacket |
| `get_product_details` | done | Example `SKU-1001`. Leading/trailing spaces are stripped |
| `check_inventory` | done | `{ sku, stock_qty, in_stock }`. `SKU-1002` is out of stock |
| `add_to_cart` | done | `cart_id`, `product_id`, `qty`. Creates the cart |
| `place_order` | done | Returns `ORD-…`, clears the cart |
| `get_order_details` | done | Only for orders created in this process |

- [x] Structured dict returns and clear errors for bad SKUs, empty carts, and oversell
- [ ] Tool annotations (`readOnlyHint` / `destructiveHint`) — not added

### Resources and prompts

- [x] `product://{sku}` markdown page (catalog + stock)
- [x] `policy://returns`, `policy://shipping`, `policy://privacy`
- [x] Prompts `compare_products` and `find_best_deal` are registered, with example args in the descriptions
- [x] `find_best_deal` tells the agent to `search` first, then read `product://{{sku}}` from the results (query is not a SKU)

### Transports and CLI

- [x] `cli.py`: default `--transport stdio`; `--transport http --host --port` (default `127.0.0.1:8050`, path `/mcp`)
- [x] Console script: `mcp_retail_sim.cli:main`
- [x] README: `uvx` for users, `uv run` for a checkout, Inspector for both PyPI and local
- [x] No debug `print` on stdout in the server path

### Packaging

- [x] `requires-python = ">=3.10"`
- [x] MIT `LICENSE`; author name only (no email in metadata)
- [x] Fixtures are inside the wheel (`importlib.resources`)
- [x] `.gitignore`
- [x] Published **0.1.0** to TestPyPI and PyPI
- [ ] Republish — PyPI 0.1.0 does not include later local edits (search hints, SKU whitespace trim, README Inspector local command)

---

## Left (before calling the MVP finished)

1. **Failure injection** — not started. Planned: `faults.py`, seeded latency, error rate, force out-of-stock, catalog vs inventory conflict.
2. **Tests** — store, tools, resources, and prompts are covered. Still missing: one fault-injection case after `faults.py` exists.
3. **Publish the next version** (for example `0.1.1`) so `uvx` matches this repo.
4. **Optional:** `readOnlyHint` / `destructiveHint` on tools.

---

## Explicitly later

- [ ] OAuth scopes on HTTP
- [ ] Elicitation on `place_order`
- [ ] Subscriptions
- [ ] Tasks extension
- [ ] OpenTelemetry
- [ ] SQLite
- [ ] Docker
- [ ] npm client

---

## Layout (actual)

```
mcp-retail-sim/
├── README.md
├── LICENSE
├── scope.md
├── pyproject.toml
└── src/mcp_retail_sim/
    ├── cli.py            # stdio | http
    ├── __main__.py       # python -m → cli.main
    ├── server.py
    ├── store.py
    ├── helpers.py
    ├── tools.py
    ├── resources.py
    ├── prompts.py
    └── data/
        ├── products.json
        ├── inventory.json
        └── policies.json
```

`faults.py` and `tests/` are not created yet.

---

## Demo facts (for Inspector)

- Search examples that return rows: `headphones`, `laptop`, `coffee`, `yoga`, `tv`, `jacket`
- In stock: `SKU-1001`. Out of stock: `SKU-1002`
- Cart example: `cart-1` + `SKU-1001`, then `place_order`
- Orders disappear when the process exits

---

## Progress log

| Date | Note |
|---|---|
| Start | Scope locked; `uv init` |
| MVP build | Fixtures, store, tools, resources, prompts, stdio + HTTP CLI |
| Publish | 0.1.0 on TestPyPI and PyPI. Later doc/hint/whitespace fixes are local only |
