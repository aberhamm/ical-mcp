"""ical-mcp: MCP server for Apple Calendar and CalDAV providers."""

from .server import mcp

__version__ = "0.1.0"


def main() -> None:
    mcp.run()
