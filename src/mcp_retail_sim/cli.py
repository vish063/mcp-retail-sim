"""CLI entry for mcp-retail-sim (stdio or Streamable HTTP)."""

from __future__ import annotations

import argparse

from mcp_retail_sim.server import mcp
import mcp_retail_sim.tools  # noqa: F401 — register tools
import mcp_retail_sim.resources  # noqa: F401 — register resources
import mcp_retail_sim.prompts  # noqa: F401 — register prompts


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="mcp-retail-sim",
        description="Synthetic retail MCP server (stdio or Streamable HTTP).",
    )
    parser.add_argument(
        "--transport",
        choices=("stdio", "http"),
        default="stdio",
        help="MCP transport (default: stdio)",
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="HTTP bind host (default: 127.0.0.1; used only for http)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8050,
        help="HTTP bind port (default: 8050; used only for http)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    if args.transport == "stdio":
        mcp.run(transport="stdio")
    else:
        mcp.run(transport="http", host=args.host, port=args.port)
