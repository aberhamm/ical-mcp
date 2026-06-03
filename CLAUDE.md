# ical-mcp

CalDAV-based MCP server for Apple Calendar (iCloud) and other CalDAV providers. No macOS dependency — works headless on any platform.

## Development

```bash
cd /Users/matthew/_projects/ical-mcp
uv sync
uv run pytest
uv run ical-mcp
```

## Architecture

- `src/ical_mcp/server.py` — FastMCP server with 6 tools (list_calendars, get_events, create_event, update_event, delete_event, get_freebusy)
- `src/ical_mcp/caldav.py` — CalDAV HTTP client (discovery, PROPFIND, REPORT, PUT, DELETE)
- `src/ical_mcp/ical.py` — iCal (RFC 5545) generation and parsing
- `src/ical_mcp/models.py` — Calendar and Event dataclasses
- `src/ical_mcp/config.py` — Env var configuration with provider auto-detection
- `src/ical_mcp/errors.py` — Semantic error types

## Key design decisions

- CalDAV over the network, not EventKit/AppleScript — works headless
- Zero CalDAV/iCal library dependencies — raw HTTP + string-templated iCal
- ISO 8601 with timezone offset required on all timestamps
- Calendar names (not URLs) in the tool interface
- ETag-based optimistic concurrency on update/delete
- Read-only mode via ICAL_MCP_READ_ONLY env var

## Testing

```bash
uv run pytest                    # all tests
uv run pytest tests/test_ical.py # just iCal format tests
uv run pytest -x                 # stop on first failure
```
