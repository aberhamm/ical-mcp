# ical-mcp

MCP server for Apple Calendar and CalDAV providers.

Works with iCloud, Fastmail, Nextcloud, and any CalDAV-compatible calendar. No macOS dependency — runs headless on any platform.

## Quick start

```bash
# Install
uvx ical-mcp

# Or from source
uv sync
uv run ical-mcp
```

## Configuration

Set these environment variables (or copy `.env.example` to `.env`):

| Variable | Required | Description |
|---|---|---|
| `ICAL_MCP_URL` | Yes | CalDAV server URL (e.g. `https://caldav.icloud.com`) |
| `ICAL_MCP_USERNAME` | Yes | Your email / account ID |
| `ICAL_MCP_PASSWORD` | Yes | Password or app-specific password |
| `ICAL_MCP_TIMEZONE` | No | Default timezone (default: `UTC`) |
| `ICAL_MCP_WRITABLE_CALENDARS` | No | Calendars that allow writes (see [Write protection](#write-protection)) |

### iCloud setup

1. Go to [account.apple.com](https://account.apple.com) → Sign-In and Security → App-Specific Passwords
2. Generate a new password (label it "ical-mcp")
3. Set `ICAL_MCP_URL=https://caldav.icloud.com`
4. Set `ICAL_MCP_USERNAME` to your Apple ID email
5. Set `ICAL_MCP_PASSWORD` to the generated app-specific password

## Tools

| Tool | Description |
|---|---|
| `list_calendars` | List all available calendars (shows read/write access per calendar) |
| `get_events` | Query events by date range |
| `create_event` | Create a new event |
| `update_event` | Update an existing event (partial patch, only changed fields) |
| `delete_event` | Delete an event |
| `get_freebusy` | Check busy/free status for a time range |

## Write protection

All calendars are **read-only by default**. You must explicitly opt in to writes:

```bash
# Single calendar (by name or ID)
ICAL_MCP_WRITABLE_CALENDARS=home

# Multiple calendars
ICAL_MCP_WRITABLE_CALENDARS=home,Work

# All calendars (use with caution)
ICAL_MCP_WRITABLE_CALENDARS=*

# Not set or empty — all calendars are read-only
```

`list_calendars` shows `"access": "read-only"` or `"access": "read-write"` for each calendar, so the AI agent knows what it can and can't modify.

Using calendar IDs (UUIDs) instead of names avoids issues with spaces and renames.

## Transport

```bash
# Local use with Claude Code / Claude Desktop (default)
ical-mcp

# Shared HTTP server for multi-agent access
ical-mcp --transport http --port 8093

# Bind to a specific address (e.g. Tailscale IP)
ical-mcp --transport http --host 100.64.0.1 --port 8093
```

## Claude Code configuration

### Local (stdio)

```json
{
  "mcpServers": {
    "ical-mcp": {
      "command": "uvx",
      "args": ["ical-mcp"],
      "env": {
        "ICAL_MCP_URL": "https://caldav.icloud.com",
        "ICAL_MCP_USERNAME": "your@icloud.com",
        "ICAL_MCP_PASSWORD": "xxxx-xxxx-xxxx-xxxx",
        "ICAL_MCP_WRITABLE_CALENDARS": "your-calendar-id"
      }
    }
  }
}
```

### Remote (HTTP)

```json
{
  "mcpServers": {
    "ical-mcp": {
      "url": "http://your-server:8093/mcp"
    }
  }
}
```

## Safety features

- **Per-calendar write protection** — read-only by default, explicit opt-in per calendar
- **Backup before mutate** — every update/delete logs the full iCal data to stderr
- **ETag concurrency** — updates fail if the event was modified elsewhere since last fetch
- **Semantic errors** — clear messages for auth failures, rate limits, conflicts, and read-only violations

## License

MIT
