"""Tests for CalDAVClient._resolve_event_url.

Covers the iCloud quirk where the resource filename (set at PUT time)
diverges from the VEVENT UID after server-side sync, so the naive
`{calendar}/{uid}.ics` path 404s and we must fall back to a UID-filtered
calendar-query to discover the real href.
"""

from __future__ import annotations

import asyncio

import httpx

from ical_mcp.caldav import CalDAVClient
from ical_mcp.models import Calendar

BASE = "https://caldav.example.com"
CAL_URL = f"{BASE}/123/calendars/home"
CALENDAR = Calendar(id="home", name="Matthew", url=CAL_URL)


def _client_with(handler) -> CalDAVClient:
    client = CalDAVClient(BASE, "user", "pass")
    client._client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return client


def test_resolve_fast_path_direct_filename() -> None:
    """When the filename equals the UID, the direct URL is used as-is."""

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "GET" and request.url.path.endswith("/fast-uid.ics"):
            return httpx.Response(200, text="BEGIN:VCALENDAR\r\nEND:VCALENDAR\r\n")
        return httpx.Response(404)

    client = _client_with(handler)
    url = asyncio.run(client._resolve_event_url(CALENDAR, "fast-uid"))
    assert url == f"{CAL_URL}/fast-uid.ics"


def test_resolve_fallback_when_uid_not_filename() -> None:
    """iCloud case: GET {uid}.ics 404s; resolver finds the real href by UID query."""
    real_uid = "ICLOUD-REWRITTEN-UID"
    filename = "original-put-uuid"
    report_seen = {"hit": False}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "GET" and request.url.path.endswith(f"/{real_uid}.ics"):
            return httpx.Response(404)
        if request.method == "REPORT":
            report_seen["hit"] = True
            assert real_uid in request.content.decode()  # UID prop-filter present
            body = (
                '<?xml version="1.0"?>'
                '<D:multistatus xmlns:D="DAV:">'
                "<D:response>"
                f"<D:href>/123/calendars/home/{filename}.ics</D:href>"
                '<D:propstat><D:prop><D:getetag>"abc"</D:getetag></D:prop>'
                "<D:status>HTTP/1.1 200 OK</D:status></D:propstat>"
                "</D:response>"
                "</D:multistatus>"
            )
            return httpx.Response(207, text=body)
        return httpx.Response(404)

    client = _client_with(handler)
    url = asyncio.run(client._resolve_event_url(CALENDAR, real_uid))
    assert report_seen["hit"] is True
    assert url == f"{CAL_URL}/{filename}.ics"
