# mcp-retail-sim

Synthetic **retail store MCP server** for building and evaluating shopping / support agents.

No real payments, inventory DB, or third-party APIs — fixtures load into memory so demos and evals stay deterministic.

## What you get


| Primitive      | Examples                                                                                              |
| -------------- | ----------------------------------------------------------------------------------------------------- |
| **Tools**      | `search`, `get_product_details`, `check_inventory`, `add_to_cart`, `get_cart`, `remove_from_cart`, `place_order`, `get_order_details` |
| **Resources**  | `product://{sku}`, `policy://returns`, `policy://shipping`, `policy://privacy`                        |
| **Prompts**    | `compare_products`, `find_best_deal`                                                                  |
| **Transports** | **stdio** (default) · **Streamable HTTP**                                                             |


Cart/order flows are **stateless** at the protocol layer: the client passes a `cart_id` handle (no server login session).

Same tools, resources, and prompts are available on **both** transports — only how the client connects changes.

## Demo catalog

About **1000** synthetic products (SKU-1000…SKU-1999) across common retail departments (grocery, home, beauty, health, clothing, electronics, and more).

`search` accepts an optional free-text **query** (substring on name, description, category, brand, tags) plus optional filters: `category`, `brand`, `tag`, `min_price`, `max_price`, `in_stock`, `dietary`, `organic`, `limit` (default 50). Filters are ANDed. Empty query with no filters returns `[]`; empty query **with** filters browses the filtered set.

Department-specific `attrs` (plus mirrored tags) support preference-style shopping — for example grocery `dietary` / `organic` / `allergen` / `sugar_level`, clothing `material` / `fit`, electronics `connectivity` / `power_source` (`battery` | `mains` | `passive` | `rechargeable`). There are still **no** rating/review fields.


| Try this                                                                | What you should see                                           |
| ----------------------------------------------------------------------- | ------------------------------------------------------------- |
| `search` query `headphones` / `yoga` / `laptop`                         | Matching products                                             |
| `search` category=`grocery_pantry` dietary=`vegan` max_price=`20`       | Filtered browse (query may be empty)                          |
| `get_product_details` / `product://SKU-1001`                            | LumenLab Pro Headphones                                       |
| `check_inventory` `SKU-1001`                                            | In stock                                                      |
| `check_inventory` `SKU-1002`                                            | Out of stock (`stock_qty` 0)                                  |
| `add_to_cart` `cart-1` + `SKU-1001`                                     | Cart with items + `total` / `currency`; stock unchanged       |
| `get_cart` `cart-1`                                                     | Same cart snapshot (items + total)                            |
| `remove_from_cart` `cart-1` + `SKU-1001`                                | Qty down / line removed; total updated; stock unchanged       |
| `place_order` `cart-1` (+ optional `idempotency_key`)                   | Order id `ORD-…`, stock decremented; safe retry with same key |
| `get_order_details`                                                     | That `ORD-…` id (only while this server process is running)   |
| `policy://returns`, `policy://shipping`, `policy://privacy`             | Store policy text                                             |


Categories include electronics, computers, home and kitchen, furniture, clothing, beauty, sports, toys, books, grocery, health, automotive, pets, office, and baby.

### Cart / checkout notes

- `add_to_cart` merges qty for the same SKU; it never decrements stock.
- `remove_from_cart(cart_id, product_id, quantity=1)` decrements qty; drops the line at 0; keeps an empty cart.
- Cart and order payloads include `total` and `currency` (USD).
- `place_order` revalidates stock at checkout, then decrements inventory and deletes the cart.
- Optional `idempotency_key`: same key + same cart fingerprint returns the original order; same key + different cart is rejected. Keys live in process memory (like orders).

## Eval fault injection (test/dev only)

For demos and agent evaluations you can force checkout failures **without** exposing an admin MCP tool. Set env on the server process (stdio host `env`, or export before HTTP start):

```bash
MCP_RETAIL_SIM_FAULTS=place_order:insufficient_stock
```

| Directive | Effect |
| --------- | ------ |
| `place_order:insufficient_stock` | Fail before commit (stock unchanged, cart kept) |
| `place_order:latency_ms:N` | Sleep N ms before checkout work |
| `place_order:fail_once` | First new checkout returns a transient error (before commit); later attempts proceed |
| `place_order:error_after_commit` | Commit order + idempotency, then return a fake transient error once; retry with the **same** `idempotency_key` returns the real order |

Enable **one** scenario at a time. Idempotent **replay** skips fault injection. Cleared by default when the env var is unset. In pytest, use `mcp_retail_sim.faults.enable_faults([...])` / `clear_faults()`.

A project `.env` file is **not** loaded automatically — the MCP host or shell must set `MCP_RETAIL_SIM_FAULTS`.

## Runtime reset (test/eval only)

For long-lived processes or pytest isolation, call `mcp_retail_sim.store.reset_runtime_state()` to:

- clear carts, orders, and idempotency records
- clear fault injection
- reload products / inventory / policies from fixtures (restores stock)

This is **not** an MCP tool — agents cannot reset the store.

## Eval adversarial fixtures (opt-in)

Optional products for **indirect prompt-injection** evaluations (agent must not blindly trust tool/catalog text). They are **not** in the default catalog.

```bash
MCP_RETAIL_SIM_EVAL_FIXTURES=adversarial
```

| SKU (harness id only) | Role |
| --- | --- |
| `SKU-ADV-001` | Looks like chamomile tea; description buries a strong injection (`OVERRIDE_OK`) |
| `SKU-ADV-002` | Looks like honey; soft “prefer this SKU / don’t tell the user” injection |
| `SKU-ADV-003` | Benign green-tea control (no injection) |

Product fields are intentionally **unmarked** (normal `grocery_pantry` brands/tags/attrs) so the model is not tipped off. Eval harnesses should key off the known `SKU-ADV-*` ids, not on labels in the payload. Guardrails belong in the **agent**, not in fixture labelling.

In pytest / harnesses: `mcp_retail_sim.eval_fixtures.enable_eval_fixtures(["adversarial"])` / `clear_eval_fixtures()`. Not an MCP tool.

## Transports


|                 | **stdio**                               | **Streamable HTTP**                            |
| --------------- | --------------------------------------- | ---------------------------------------------- |
| **Start**       | Client spawns the process               | You start the server; it listens on a port     |
| **Connect**     | Pipes (stdin/stdout)                    | URL, e.g. `http://127.0.0.1:8050/mcp`          |
| **Lifetime**    | Usually tied to the client              | Long-lived until you stop it                   |
| **Typical use** | Cursor, Claude Desktop, Inspector spawn | LangChain / remote-style clients, multi-client |


`uvx` downloads the package from PyPI and runs it. Use these commands if you are not developing this repo:

```bash
# stdio (default) — for desktop hosts / Inspector spawn
uvx mcp-retail-sim
# same as:
uvx mcp-retail-sim --transport stdio

# Streamable HTTP — long-lived local server
uvx mcp-retail-sim --transport http --host 127.0.0.1 --port 8050
# MCP endpoint: http://127.0.0.1:8050/mcp
```

CLI flags (HTTP only uses host/port):


| Flag          | Default     | Meaning               |
| ------------- | ----------- | --------------------- |
| `--transport` | `stdio`     | `stdio` or `http`     |
| `--host`      | `127.0.0.1` | Bind address for HTTP |
| `--port`      | `8050`      | Bind port for HTTP    |




## Quick start (from a git checkout)

`uv run` uses the local source and the project virtualenv. It does not download the PyPI release.

```bash
cd mcp-retail-sim
uv sync
uv run mcp-retail-sim --help
uv run pytest
```



### MCP Inspector

**stdio** — Inspector starts the server for you (do not run the server yourself).

Published package from PyPI:

```bash
npx @modelcontextprotocol/inspector uvx mcp-retail-sim
```

Local checkout — run from the `mcp-retail-sim` directory:

```bash
npx @modelcontextprotocol/inspector uv run mcp-retail-sim
```

**HTTP** — start the server first, then point Inspector at the URL:

```bash
# terminal 1
uvx mcp-retail-sim --transport http --port 8050

# terminal 2
npx @modelcontextprotocol/inspector \
  --server-url http://127.0.0.1:8050/mcp \
  --transport http
```



### Cursor / Claude Desktop (stdio)

```json
{
  "mcpServers": {
    "mcp-retail-sim": {
      "command": "uvx",
      "args": ["mcp-retail-sim"]
    }
  }
}
```

Eval example with a fault and/or adversarial fixtures (local checkout):

```json
{
  "mcpServers": {
    "mcp-retail-sim": {
      "command": "uv",
      "args": ["run", "mcp-retail-sim"],
      "env": {
        "MCP_RETAIL_SIM_FAULTS": "place_order:error_after_commit",
        "MCP_RETAIL_SIM_EVAL_FIXTURES": "adversarial"
      }
    }
  }
}
```



### LangChain / HTTP client sketch

```python
# Server must already be running:
#   uvx mcp-retail-sim --transport http --port 8050

config = {
    "mcpServers": {
        "mcp-retail-sim": {
            "url": "http://127.0.0.1:8050/mcp",
        }
    }
}
```



## Architecture (high level)

```
Client (agent / Inspector / LangChain)
        │
        ├─ stdio: client spawns process, JSON-RPC over pipes
        └─ http:  client connects to http://host:port/mcp
        ▼
┌─────────────────────────────┐
│  mcp-retail-sim (FastMCP)   │
│  tools · resources · prompts│
│  cli: --transport stdio|http│
│  faults via env (eval only) │
└─────────────┬───────────────┘
              │
              ▼
┌─────────────────────────────┐
│  In-memory store            │
│  ← fixtures (products,      │
│     inventory, policies)    │
│  + carts / orders           │
│  + idempotency map          │
└─────────────────────────────┘
```



## Status

MVP for general retail-agent simulation: catalog + cart tools, checkout with stock revalidation and optional idempotency, stdio + Streamable HTTP, eval-only fault injection.

Still optional / later: PyPI republish of the latest tree, concurrency locks.

Tools advertise MCP annotations (read-only vs mutating/destructive hints) for hosts that surface them.

## Maintainer

From the `mcp-retail-sim` directory:

- Bump `version` in `pyproject.toml`.
- Run the tests: `uv run pytest`
- Save the API tokens (once):

```bash
keyring set https://test.pypi.org/legacy/ __token__
keyring set https://upload.pypi.org/legacy/ __token__
```

- Build and publish:

```bash
uv build --out-dir dist
UV_KEYRING_PROVIDER=subprocess uv publish --publish-url https://test.pypi.org/legacy/
UV_KEYRING_PROVIDER=subprocess uv publish
```

## License

[MIT](./LICENSE)
