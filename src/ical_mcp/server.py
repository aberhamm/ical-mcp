"""ical-mcp: MCP server for Apple Calendar and CalDAV providers."""

from __future__ import annotations

import json
import logging
import sys
from typing import Annotated

from fastmcp import FastMCP
from pydantic import Field

from .caldav import CalDAVClient
from .config import Config
from .errors import CalDAVError, ReadOnlyError

logging.basicConfig(stream=sys.stderr, level=logging.INFO, format="%(name)s: %(message)s")
logger = logging.getLogger("ical-mcp")

mcp = FastMCP(
    "ical-mcp",
    instructions=(
        "Calendar integration via CalDAV. Works with iCloud, Fastmail, Nextcloud, "
        "and other CalDAV providers. All datetimes must be ISO 8601 with timezone offset."
    ),
)

_client: CalDAVClient | None = None
_config: Config | None = None


async def _get_client() -> CalDAVClient:
    global _client, _config
    if _client is not None:
        return _client
    _config = Config.from_env()
    client = CalDAVClient(_config.url, _config.username, _config.password)
    await client.discover()
    _client = client
    return client


def _check_writable(calendar_id: str, calendar_name: str) -> None:
    if _config is None:
        raise ReadOnlyError("Server not initialized.")
    if not _config.is_writable(calendar_id, calendar_name):
        writable = _config.writable_calendars
        if not writable:
            raise ReadOnlyError(
                "All calendars are read-only (ICAL_MCP_WRITABLE_CALENDARS is not set). "
                "Set ICAL_MCP_WRITABLE_CALENDARS to allow writes."
            )
        raise ReadOnlyError(
            f"Calendar '{calendar_name}' is read-only. "
            f"Writable calendars: {', '.join(sorted(writable))}"
        )


@mcp.tool()
async def list_calendars() -> str:
    """List all available calendars.

    Returns calendar names and IDs for use with other tools. Call this first
    to discover which calendars exist before querying or creating events.
    """
    client = await _get_client()
    calendars = client.get_calendars()
    return json.dumps(
        [c.to_dict(writable=_config.is_writable(c.id, c.name) if _config else False) for c in calendars],
        indent=2,
    )


@mcp.tool()
async def get_events(
    start: Annotated[
        str,
        Field(description="Start of date range, ISO 8601 with timezone (e.g. 2026-06-10T00:00:00+00:00)"),
    ],
    end: Annotated[
        str,
        Field(description="End of date range, ISO 8601 with timezone (e.g. 2026-06-17T23:59:59+00:00)"),
    ],
    calendar: Annotated[
        str | None,
        Field(description="Calendar name or ID. Omit to use the default (only works if one calendar exists)."),
    ] = None,
) -> str:
    """Get events within a date range.

    Returns events sorted by start time. Recurring events are returned as
    individual expanded occurrences within the requested range.
    """
    client = await _get_client()
    cal = client.find_calendar(calendar)
    events = await client.get_events(cal, start, end)
    return json.dumps([e.to_dict() for e in events], indent=2)


@mcp.tool()
async def create_event(
    title: Annotated[str, Field(description="Event title")],
    start: Annotated[
        str,
        Field(description="Start datetime, ISO 8601 with timezone (e.g. 2026-06-10T14:00:00-04:00)"),
    ],
    end: Annotated[
        str,
        Field(description="End datetime, ISO 8601 with timezone (e.g. 2026-06-10T15:00:00-04:00)"),
    ],
    calendar: Annotated[
        str | None,
        Field(description="Calendar name or ID. Omit to use the default."),
    ] = None,
    description: Annotated[
        str | None,
        Field(description="Event description or notes"),
    ] = None,
    location: Annotated[
        str | None,
        Field(description="Event location"),
    ] = None,
    all_day: Annotated[
        bool,
        Field(description="Whether this is an all-day event. If true, start/end should be dates (e.g. 2026-06-10)."),
    ] = False,
) -> str:
    """Create a new calendar event.

    Confirm the calendar, date, time, and details with the user before calling.
    Returns the created event with its ID and ETag for future updates.
    """
    client = await _get_client()
    cal = client.find_calendar(calendar)
    _check_writable(cal.id, cal.name)
    event = await client.create_event(
        cal,
        title=title,
        start=start,
        end=end,
        description=description,
        location=location,
        all_day=all_day,
    )
    return json.dumps(event.to_dict(), indent=2)


@mcp.tool()
async def update_event(
    event_id: Annotated[str, Field(description="Event ID (UID) from a previous get_events call")],
    etag: Annotated[str, Field(description="ETag from a previous get_events call (for conflict detection)")],
    calendar: Annotated[
        str | None,
        Field(description="Calendar name or ID where the event lives"),
    ] = None,
    title: Annotated[str | None, Field(description="New title (omit to keep current)")] = None,
    start: Annotated[
        str | None,
        Field(description="New start datetime, ISO 8601 with timezone (omit to keep current)"),
    ] = None,
    end: Annotated[
        str | None,
        Field(description="New end datetime, ISO 8601 with timezone (omit to keep current)"),
    ] = None,
    description: Annotated[
        str | None,
        Field(description="New description (omit to keep current)"),
    ] = None,
    location: Annotated[
        str | None,
        Field(description="New location (omit to keep current)"),
    ] = None,
) -> str:
    """Update an existing calendar event.

    Only send the fields you want to change — unchanged fields are preserved.
    Requires the event's ETag for optimistic concurrency; if the event was
    modified elsewhere, the update will fail with a conflict error.
    """
    client = await _get_client()
    cal = client.find_calendar(calendar)
    _check_writable(cal.id, cal.name)
    event = await client.update_event(
        cal,
        uid=event_id,
        etag=etag,
        title=title,
        start=start,
        end=end,
        description=description,
        location=location,
    )
    return json.dumps(event.to_dict(), indent=2)


@mcp.tool()
async def delete_event(
    event_id: Annotated[str, Field(description="Event ID (UID) to delete")],
    calendar: Annotated[
        str | None,
        Field(description="Calendar name or ID where the event lives"),
    ] = None,
    etag: Annotated[
        str | None,
        Field(description="ETag for conflict detection (recommended but optional)"),
    ] = None,
) -> str:
    """Delete a calendar event.

    Confirm with the user before deleting. Pass the ETag from get_events
    to ensure you're deleting the right version.
    """
    client = await _get_client()
    cal = client.find_calendar(calendar)
    _check_writable(cal.id, cal.name)
    await client.delete_event(cal, event_id, etag=etag)
    return json.dumps({"deleted": event_id, "calendar": cal.name})


@mcp.tool()
async def get_freebusy(
    start: Annotated[
        str,
        Field(description="Start of range, ISO 8601 with timezone"),
    ],
    end: Annotated[
        str,
        Field(description="End of range, ISO 8601 with timezone"),
    ],
    calendar: Annotated[
        str | None,
        Field(description="Calendar name or ID. Omit to check all calendars."),
    ] = None,
) -> str:
    """Check free/busy status for a time range.

    Returns a list of busy time blocks within the requested range.
    Useful for finding available slots before scheduling.
    """
    client = await _get_client()

    if calendar:
        calendars = [client.find_calendar(calendar)]
    else:
        calendars = client.get_calendars()

    busy_blocks: list[dict] = []
    for cal in calendars:
        try:
            events = await client.get_events(cal, start, end)
        except CalDAVError:
            logger.warning("Skipping calendar %s (fetch failed)", cal.name)
            continue
        for event in events:
            if event.status == "cancelled":
                continue
            busy_blocks.append({
                "calendar": cal.name,
                "title": event.title,
                "start": event.start,
                "end": event.end,
                "status": event.status,
            })

    busy_blocks.sort(key=lambda b: b["start"])
    return json.dumps(
        {"busy": busy_blocks, "total_blocks": len(busy_blocks)},
        indent=2,
    )
