# mcp-retail-sim — Scope and status

> Maintainer checklist. Public docs live in `README.md`.

**Goal:** A reusable retail MCP simulator (tools + resources + prompts + stdio and Streamable HTTP) that anyone can `uvx` / `uv run` and point shopping, support, or evaluation agents at.

**Non-goals:** real DB, OAuth, elicitation, subscriptions, tasks extension, OpenTelemetry, multi-server gateway, LangChain/LangGraph/FastAPI inside this package.

---

## Done

### Data and store

- [x] `products.json` — about 1000 products, 15 categories, no stock on the product row (SKU-1000..SKU-1999; broader coverage in high-volume departments)
- [x] Richer department `attrs` + mirrored tags (grocery/beauty/health, clothing/sports, electronics/computers/home_kitchen): dietary, organic, single allergen, sugar_level, material/fit/activity, connectivity, power_source battery enum — still no ratings
- [x] `inventory.json` — `{ sku, stock_qty }`, including some zero-stock SKUs
- [x] `policies.json` — returns, shipping, privacy
- [x] `store.py` — load fixtures, search, product lookup, inventory, in-memory carts / orders / idempotency
- [x] Search: optional query (substring on name/description/category/brand/tags) + optional filters (category, brand, tag, min/max price, in_stock, dietary, organic, limit; default 50; tool filters are strings so blank ≠ false/0)
- [x] `reset_runtime_state()` — test/eval helper clears carts/orders/idempotency/faults and reloads fixtures (restores stock); not an MCP tool
- [x] `add_to_cart` does not change stock; cart includes `total` / `currency`
- [x] `place_order` revalidates stock, decrements inventory, deletes the cart
- [x] Optional checkout `idempotency_key` + cart fingerprint (replay / conflict)
- [x] `faults.py` — env / test-only fault injection (not an MCP tool)
- [x] `eval_fixtures.py` + `eval_adversarial_*.json` — opt-in adversarial/control SKUs for prompt-injection evals (`MCP_RETAIL_SIM_EVAL_FIXTURES=adversarial`); payloads look like normal grocery items (no in-band “eval fixture” labels)

### Tools (names in code)

| Tool | Status | Notes |
|---|---|---|
| `search` | done | Query + filters (category/brand/tag/price/stock/dietary/organic/limit) |
| `get_product_details` | done | Example `SKU-1001`. Leading/trailing spaces are stripped |
| `check_inventory` | done | `{ sku, stock_qty, in_stock }`. `SKU-1002` is out of stock |
| `add_to_cart` | done | `cart_id`, `product_id`, `qty`. Creates the cart; returns total |
| `get_cart` | done | Cart with items + total |
| `remove_from_cart` | done | `quantity` default 1; drop line at 0; total updated |
| `place_order` | done | Optional `idempotency_key`; stock revalidation; clears cart |
| `get_order_details` | done | Only for orders created in this process |

- [x] Structured dict returns and clear errors for bad SKUs, empty carts, and oversell
- [x] Tool annotations (`readOnlyHint` / `destructiveHint` / `idempotentHint` / `openWorldHint`)

### Fault injection (eval / pytest only)

Env: `MCP_RETAIL_SIM_FAULTS` (comma-separated). Configure in MCP host `env` or process environment. Not loaded from `.env` automatically.

| Directive | Notes |
|---|---|
| `place_order:insufficient_stock` | Pre-commit failure |
| `place_order:latency_ms:N` | Sleep N ms |
| `place_order:fail_once` | One pre-commit transient error |
| `place_order:error_after_commit` | Commit then fake error once (idempotency eval) |

- [x] Wired in `store.place_order`; idempotent replay skips faults
- [x] Tests in `tests/test_faults.py`
- [x] No agent-facing fault/reset MCP tool

### Resources and prompts

- [x] `product://{sku}` markdown page (catalog + stock)
- [x] `policy://returns`, `policy://shipping`, `policy://privacy`
- [x] Prompts `compare_products` and `find_best_deal` are registered, with example args in the descriptions
- [x] `find_best_deal` tells the agent to `search` first, then read `product://{{sku}}` from the results (query is not a SKU)

### Transports and CLI

- [x] `cli.py`: default `--transport stdio`; `--transport http --host --port` (default `127.0.0.1:8050`, path `/mcp`)
- [x] `configure_from_env()` called from `cli.main` before `mcp.run`
- [x] Console script: `mcp_retail_sim.cli:main`
- [x] README: `uvx` for users, `uv run` for a checkout, Inspector for both PyPI and local
- [x] No debug `print` on stdout in the server path

### Packaging / tests

- [x] `requires-python = ">=3.10"`; package version **0.1.1** in `pyproject.toml` / `__init__.py`
- [x] MIT `LICENSE`; author name only (no email in metadata)
- [x] Fixtures are inside the wheel (`importlib.resources`)
- [x] `.gitignore`
- [x] Published **0.1.0** to TestPyPI and PyPI (older tree)
- [x] Tests: store, tools, resources, prompts, faults (`uv run pytest`)
- [ ] Republish so `uvx` matches this repo (cart tools, idempotency, faults, 1000 SKUs, attrs)

---

## Feature coverage (shopping / support agents)

| Capability | Status |
|---|---|
| Catalog search + product details + inventory | done |
| Cart create / read / remove lines + totals | done |
| Checkout with stock revalidation | done |
| Idempotent checkout (optional key) | done |
| Test/dev fault injection (env, not MCP tools) | done |
| Runtime reset helper (inventory + carts/orders/idempotency/faults) | done (`reset_runtime_state`) |
| Adversarial product fixture (prompt-injection eval) | done (opt-in; separate JSON; not default catalog) |

---

## Left (optional / later)

1. **Republish** (e.g. 0.1.2) so PyPI/`uvx` matches this tree.
2. Concurrency locking around checkout (tools may run in threads).

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
├── AGENTS.md
├── pyproject.toml
├── tests/
└── src/mcp_retail_sim/
    ├── cli.py
    ├── __main__.py
    ├── server.py
    ├── store.py
    ├── faults.py
    ├── eval_fixtures.py
    ├── helpers.py
    ├── tools.py
    ├── resources.py
    ├── prompts.py
    └── data/
        ├── products.json
        ├── inventory.json
        ├── policies.json
        ├── eval_adversarial_products.json
        └── eval_adversarial_inventory.json
```

---

## Demo facts (for Inspector)

- Search examples: `headphones`, `vegan`, `organic`, `yoga`, `laptop`, `coffee`
- In stock: `SKU-1001`. Out of stock: `SKU-1002`
- Cart: `cart-1` + `SKU-1001` → `get_cart` → `place_order` (optional `idempotency_key`)
- Orders / idempotency / carts disappear when the process exits

---

## Progress log

| Date | Note |
|---|---|
| Start | Scope locked; `uv init` |
| MVP build | Fixtures, store, tools, resources, prompts, stdio + HTTP CLI |
| Publish | 0.1.0 on TestPyPI and PyPI |
| Expansion | 1000 SKUs, richer attrs/tags, get_cart, remove_from_cart, cart totals, idempotent checkout, faults.py + tests; docs framed for general retail-agent use |
