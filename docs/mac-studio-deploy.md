# Deploying ical-mcp on Mac Studio (ms-128g-bln)

Handoff doc for the MCP management agent on the Mac Studio.

## What this is

ical-mcp is a CalDAV-based MCP server for Apple Calendar (iCloud). It provides 6 tools: `list_calendars`, `get_events`, `create_event`, `update_event`, `delete_event`, `get_freebusy`. It talks to iCloud over HTTPS — no macOS Calendar.app dependency, fully headless.

**Repo:** https://github.com/aberhamm/ical-mcp

## Target deployment

- **Host:** ms-128g-bln (Mac Studio M4 Max, 128GB)
- **Tailscale IP:** 100.72.204.108
- **SSH:** matthew@100.72.204.108
- **Transport:** HTTP (streamable-http) on port 8093
- **Bind address:** 100.72.204.108 (Tailscale only — not 0.0.0.0)

## Installation

```bash
ssh matthew@100.72.204.108

# Clone and install
cd ~/apps
git clone https://github.com/aberhamm/ical-mcp.git
cd ical-mcp
uv sync

# Verify it runs
uv run ical-mcp --help
```

## Configuration

Create `~/apps/ical-mcp/.env` with:

```bash
ICAL_MCP_URL=https://caldav.icloud.com
ICAL_MCP_USERNAME=thenamesabe@gmail.com
ICAL_MCP_PASSWORD=kmgr-zsrw-tfix-zepe
ICAL_MCP_TIMEZONE=Europe/Berlin
ICAL_MCP_WRITABLE_CALENDARS=A249E35C-8070-471D-A395-12590D441844
```

The writable calendar ID is "Claude Calendar" — the only calendar that accepts writes. All others (Matthew, Matthew Other, Bene and Matt Events, No Conflicts) are read-only by default.

## Running in HTTP mode

```bash
# Test manually first
cd ~/apps/ical-mcp
set -a && source .env && set +a
uv run ical-mcp --transport http --host 100.72.204.108 --port 8093
```

Verify from another machine on the tailnet:
```bash
curl -X POST http://100.72.204.108:8093/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"test"}},"id":1}'
```

## LaunchDaemon setup

First, create the wrapper script at `~/apps/ical-mcp/run.sh`:

```bash
#!/bin/bash
set -a
source /Users/matthew/apps/ical-mcp/.env
set +a
exec /Users/matthew/.local/bin/uv --directory /Users/matthew/apps/ical-mcp run ical-mcp --transport http --host 100.72.204.108 --port 8093
```

```bash
chmod +x ~/apps/ical-mcp/run.sh
```

Then create `/Library/LaunchDaemons/com.ical-mcp.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.ical-mcp</string>
    <key>UserName</key>
    <string>matthew</string>
    <key>ProgramArguments</key>
    <array>
        <string>/Users/matthew/apps/ical-mcp/run.sh</string>
    </array>
    <key>EnvironmentVariables</key>
    <dict>
        <key>HOME</key>
        <string>/Users/matthew</string>
        <key>PATH</key>
        <string>/Users/matthew/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin</string>
    </dict>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/var/log/ical-mcp.log</string>
    <key>StandardErrorPath</key>
    <string>/var/log/ical-mcp.err</string>
    <key>WorkingDirectory</key>
    <string>/Users/matthew/apps/ical-mcp</string>
</dict>
</plist>
```

Credentials stay in `~/apps/ical-mcp/.env` (gitignored) and are sourced by the wrapper script — the plist itself contains no secrets.

Create the log files and load it:
```bash
sudo touch /var/log/ical-mcp.log /var/log/ical-mcp.err
sudo chown matthew:staff /var/log/ical-mcp.log /var/log/ical-mcp.err
sudo launchctl bootstrap system /Library/LaunchDaemons/com.ical-mcp.plist

# Check status
sudo launchctl list | grep ical-mcp
tail -f /var/log/ical-mcp.err
```

### Ordering note

This service binds to the Tailscale IP. With `KeepAlive: true`, if the bind fails at boot before Tailscale is ready, launchd restarts it automatically until it succeeds.

## How agents connect

Any agent or service on the tailnet can connect to the MCP server:

```json
{
  "mcpServers": {
    "ical-mcp": {
      "url": "http://100.72.204.108:8093/mcp"
    }
  }
}
```

For n8n: use the CalDAV community node (`n8n-nodes-caldav-calendar`) pointed at `https://caldav.icloud.com` with the same credentials, OR make HTTP requests to the MCP server.

## Write protection

- All calendars are **read-only by default**
- Only "Claude Calendar" (`A249E35C-8070-471D-A395-12590D441844`) accepts writes
- `list_calendars` tool shows `"access": "read-only"` or `"read-write"` per calendar
- Every update/delete logs a full iCal backup to stderr before mutating
- ETag-based concurrency prevents overwriting events modified elsewhere
- To add more writable calendars: comma-separate IDs in `ICAL_MCP_WRITABLE_CALENDARS`
- To make all writable: `ICAL_MCP_WRITABLE_CALENDARS=*` (not recommended)

## Available calendars

| Calendar | ID | Access |
|---|---|---|
| Matthew | `home` | read-only |
| Matthew Other | `A04F69A6-13E9-499E-BBB9-3EF5984EB4EB` | read-only |
| No Conflicts | `CBA3D553-D03D-4641-AD86-204CDB7F15FF` | read-only |
| Claude Calendar | `A249E35C-8070-471D-A395-12590D441844` | **read-write** |
| Bene and Matt Events | `de04d3e8...` | read-only |

## Credential notes

- The password is an iCloud **app-specific password**, not the main Apple ID password
- It does NOT expire on its own, but is revoked instantly if the main Apple ID password is changed
- If auth starts failing (401), a new app-specific password must be generated at https://account.apple.com
- The password has access to CalDAV (calendar) only — it cannot access iCloud Drive, Photos, or make purchases
