# ical-mcp

CalDAV-based MCP server for Apple Calendar (iCloud) and other CalDAV providers. No macOS dependency — works headless on any platform.

## Development

```bash
cd /Users/matthew/_projects/ical-mcp
uv sync
uv run pytest
uv run ical-mcp                                          # stdio (local)
uv run ical-mcp --transport http --port 8093             # HTTP (shared)
```

## Architecture

- `src/ical_mcp/__init__.py` — CLI entry point with --transport/--host/--port flags
- `src/ical_mcp/server.py` — FastMCP server with 6 tools (list_calendars, get_events, create_event, update_event, delete_event, get_freebusy)
- `src/ical_mcp/caldav.py` — CalDAV HTTP client (discovery, PROPFIND, REPORT, PUT, DELETE)
- `src/ical_mcp/ical.py` — iCal (RFC 5545) generation and parsing
- `src/ical_mcp/models.py` — Calendar and Event dataclasses
- `src/ical_mcp/config.py` — Env var configuration with provider auto-detection and per-calendar write protection
- `src/ical_mcp/errors.py` — Semantic error types
- `docs/mac-studio-deploy.md` — Deployment handoff for Mac Studio (HTTP mode, LaunchDaemon)

## Key design decisions

- CalDAV over the network, not EventKit/AppleScript — works headless
- Zero CalDAV/iCal library dependencies — raw HTTP + string-templated iCal
- ISO 8601 with timezone offset required on all timestamps
- Calendar names or IDs (not URLs) in the tool interface
- ETag-based optimistic concurrency on update/delete
- All calendars read-only by default; ICAL_MCP_WRITABLE_CALENDARS opts in per calendar
- Backup before mutate — full iCal logged to stderr before any update/delete
- Two transports: stdio (local, default) and streamable-http (shared/remote)

## Testing

```bash
uv run pytest                    # all tests
uv run pytest tests/test_ical.py # just iCal format tests
uv run pytest -x                 # stop on first failure
```
