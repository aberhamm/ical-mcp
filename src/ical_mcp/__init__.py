"""ical-mcp: MCP server for Apple Calendar and CalDAV providers."""

import argparse

from .server import mcp

__version__ = "0.1.0"


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="ical-mcp",
        description="MCP server for Apple Calendar and CalDAV providers",
    )
    parser.add_argument(
        "--transport",
        choices=["stdio", "http"],
        default="stdio",
        help="stdio for local (Claude Code/Desktop), http for remote/shared (default: stdio)",
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="HTTP server bind address (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8093,
        help="HTTP server port (default: 8093)",
    )
    args = parser.parse_args()

    if args.transport == "http":
        mcp.run(transport="streamable-http", host=args.host, port=args.port)
    else:
        mcp.run(transport="stdio")
