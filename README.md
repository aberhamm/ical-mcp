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
| `ICAL_MCP_READ_ONLY` | No | Block write operations (default: `false`) |

### iCloud setup

1. Go to [account.apple.com](https://account.apple.com) → Sign-In and Security → App-Specific Passwords
2. Generate a new password (label it "ical-mcp")
3. Set `ICAL_MCP_URL=https://caldav.icloud.com`
4. Set `ICAL_MCP_USERNAME` to your Apple ID email
5. Set `ICAL_MCP_PASSWORD` to the generated app-specific password

## Tools

| Tool | Description |
|---|---|
| `list_calendars` | List all available calendars |
| `get_events` | Query events by date range |
| `create_event` | Create a new event |
| `update_event` | Update an existing event (partial patch) |
| `delete_event` | Delete an event |
| `get_freebusy` | Check busy/free status for a time range |

## Claude Desktop configuration

```json
{
  "mcpServers": {
    "ical-mcp": {
      "command": "uvx",
      "args": ["ical-mcp"],
      "env": {
        "ICAL_MCP_URL": "https://caldav.icloud.com",
        "ICAL_MCP_USERNAME": "your@icloud.com",
        "ICAL_MCP_PASSWORD": "xxxx-xxxx-xxxx-xxxx"
      }
    }
  }
}
```

## License

MIT
