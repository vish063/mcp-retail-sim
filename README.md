# mcp-retail-sim

Synthetic **retail store MCP server** for building and evaluating shopping / support agents.

No real payments, inventory DB, or third-party APIs — fixtures load into memory so demos and evals stay deterministic.

## What you get

| Primitive | Examples |
|---|---|
| **Tools** | `search`, `get_product_details`, `check_inventory`, `add_to_cart`, `place_order`, `get_order_details` |
| **Resources** | `product://{sku}`, `policy://returns`, `policy://shipping`, `policy://privacy` |
| **Prompts** | `compare_products`, `find_best_deal` |
| **Transports** | **stdio** (default) · **Streamable HTTP** |

Cart/order flows are **stateless** at the protocol layer: the client passes a `cart_id` handle (no server login session).

Same tools, resources, and prompts are available on **both** transports — only how the client connects changes.

## Transports

| | **stdio** | **Streamable HTTP** |
|---|---|---|
| **Start** | Client spawns the process | You start the server; it listens on a port |
| **Connect** | Pipes (stdin/stdout) | URL, e.g. `http://127.0.0.1:8050/mcp` |
| **Lifetime** | Usually tied to the client | Long-lived until you stop it |
| **Typical use** | Cursor, Claude Desktop, Inspector spawn | LangChain / remote-style clients, multi-client |

```bash
# stdio (default) — for desktop hosts / Inspector spawn
uv run mcp-retail-sim
# same as:
uv run mcp-retail-sim --transport stdio

# Streamable HTTP — long-lived local server
uv run mcp-retail-sim --transport http --host 127.0.0.1 --port 8050
# MCP endpoint: http://127.0.0.1:8050/mcp
```

CLI flags (HTTP only uses host/port):

| Flag | Default | Meaning |
|---|---|---|
| `--transport` | `stdio` | `stdio` or `http` |
| `--host` | `127.0.0.1` | Bind address for HTTP |
| `--port` | `8050` | Bind port for HTTP |

Once published to PyPI, the same commands work with `uvx mcp-retail-sim` instead of `uv run mcp-retail-sim`.

## Quick start (from this repo)

```bash
cd mcp-retail-sim
uv sync
uv run mcp-retail-sim --help
```

### MCP Inspector

**stdio** — Inspector starts the server for you (do not also run the server yourself):

```bash
npx @modelcontextprotocol/inspector uv run mcp-retail-sim
```

**HTTP** — start the server first, then point Inspector at the URL:

```bash
# terminal 1
uv run mcp-retail-sim --transport http --port 8050

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

For a local checkout before publish, use `uv` + `run` + `mcp-retail-sim` (with working directory set to this project) instead of `uvx`.

### LangChain / HTTP client sketch

```python
# Server must already be running:
#   uv run mcp-retail-sim --transport http --port 8050

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
└─────────────┬───────────────┘
              │
              ▼
┌─────────────────────────────┐
│  In-memory store            │
│  ← fixtures (products,      │
│     inventory, policies)    │
│  + carts / orders           │
└─────────────────────────────┘
```

## Status

MVP: tools, resources, prompts, **stdio + Streamable HTTP**.  
Failure injection is planned (see [`scope.md`](./scope.md)) — not shipped yet.

## License

MIT (planned)
