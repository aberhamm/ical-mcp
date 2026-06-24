"""CalDAV client for calendar discovery and event CRUD.

Implements the CalDAV subset needed for iCloud and other providers:
PROPFIND discovery chain, REPORT calendar-query, and PUT/DELETE
for event lifecycle. No external CalDAV library — just httpx.
"""

from __future__ import annotations

import logging
import uuid
from urllib.parse import urljoin
from xml.etree import ElementTree as ET
from xml.sax.saxutils import escape as _xml_escape

import httpx

from .errors import AuthError, CalDAVError, ConflictError, NotFoundError, RateLimitError
from .ical import generate_vcalendar, parse_vcalendar, _to_ical_datetime
from .models import Calendar, Event

logger = logging.getLogger(__name__)

NS_DAV = "DAV:"
NS_CALDAV = "urn:ietf:params:xml:ns:caldav"
NS_CS = "http://calendarserver.org/ns/"
NS_APPLE = "http://apple.com/ns/ical/"


class CalDAVClient:
    def __init__(self, url: str, username: str, password: str) -> None:
        self._base_url = url.rstrip("/")
        self._client = httpx.AsyncClient(
            auth=httpx.BasicAuth(username, password),
            follow_redirects=True,
            timeout=30.0,
            headers={"User-Agent": "ical-mcp/0.1.0"},
        )
        self._principal_url: str | None = None
        self._calendar_home: str | None = None
        self._calendars: dict[str, Calendar] = {}

    async def close(self) -> None:
        await self._client.aclose()

    async def discover(self) -> None:
        self._principal_url = await self._find_principal()
        self._calendar_home = await self._find_calendar_home(self._principal_url)
        await self.refresh_calendars()
        logger.info(
            "Discovered %d calendar(s) at %s",
            len(self._calendars),
            self._base_url,
        )

    # -- Calendar operations --------------------------------------------------

    async def refresh_calendars(self) -> None:
        body = (
            '<?xml version="1.0" encoding="utf-8"?>'
            f'<D:propfind xmlns:D="{NS_DAV}" xmlns:C="{NS_CALDAV}" '
            f'xmlns:CS="{NS_CS}" xmlns:A="{NS_APPLE}">'
            "<D:prop>"
            "<D:displayname/>"
            "<D:resourcetype/>"
            "<C:supported-calendar-component-set/>"
            "<A:calendar-color/>"
            "<CS:getctag/>"
            "</D:prop>"
            "</D:propfind>"
        )
        resp = await self._propfind(self._calendar_home, body, depth="1")
        tree = ET.fromstring(resp.text)
        self._calendars.clear()

        for response in tree.findall(f"{{{NS_DAV}}}response"):
            href_el = response.find(f"{{{NS_DAV}}}href")
            if href_el is None or href_el.text is None:
                continue

            if response.find(f".//{{{NS_DAV}}}resourcetype/{{{NS_CALDAV}}}calendar") is None:
                continue

            supported = response.findall(
                f".//{{{NS_CALDAV}}}supported-calendar-component-set/{{{NS_CALDAV}}}comp"
            )
            if supported and not any(c.get("name") == "VEVENT" for c in supported):
                continue

            name_el = response.find(f".//{{{NS_DAV}}}displayname")
            color_el = response.find(f".//{{{NS_APPLE}}}calendar-color")
            ctag_el = response.find(f".//{{{NS_CS}}}getctag")

            url = self._resolve_url(href_el.text)
            cal_id = href_el.text.rstrip("/").split("/")[-1]

            self._calendars[cal_id] = Calendar(
                id=cal_id,
                name=name_el.text if name_el is not None and name_el.text else cal_id,
                url=url,
                color=color_el.text if color_el is not None else None,
                ctag=ctag_el.text if ctag_el is not None else None,
            )

    def get_calendars(self) -> list[Calendar]:
        return list(self._calendars.values())

    def find_calendar(
        self, calendar: str | None = None
    ) -> Calendar:
        if calendar is None:
            if len(self._calendars) == 1:
                return next(iter(self._calendars.values()))
            raise CalDAVError(
                "Multiple calendars available — specify which one. "
                f"Options: {', '.join(c.name for c in self._calendars.values())}"
            )
        if calendar in self._calendars:
            return self._calendars[calendar]
        for cal in self._calendars.values():
            if cal.name.lower() == calendar.lower():
                return cal
        raise NotFoundError(
            f"Calendar '{calendar}' not found. "
            f"Available: {', '.join(c.name for c in self._calendars.values())}"
        )

    # -- Event operations -----------------------------------------------------

    async def get_events(self, calendar: Calendar, start: str, end: str) -> list[Event]:
        body = (
            '<?xml version="1.0" encoding="utf-8"?>'
            f'<C:calendar-query xmlns:D="{NS_DAV}" xmlns:C="{NS_CALDAV}">'
            "<D:prop><D:getetag/><C:calendar-data/></D:prop>"
            "<C:filter>"
            '<C:comp-filter name="VCALENDAR">'
            '<C:comp-filter name="VEVENT">'
            f'<C:time-range start="{_to_ical_datetime(start)}" '
            f'end="{_to_ical_datetime(end)}"/>'
            "</C:comp-filter>"
            "</C:comp-filter>"
            "</C:filter>"
            "</C:calendar-query>"
        )
        resp = await self._report(calendar.url, body)
        tree = ET.fromstring(resp.text)
        events: list[Event] = []

        for response in tree.findall(f"{{{NS_DAV}}}response"):
            href_el = response.find(f"{{{NS_DAV}}}href")
            etag_el = response.find(f".//{{{NS_DAV}}}getetag")
            data_el = response.find(f".//{{{NS_CALDAV}}}calendar-data")
            if data_el is None or data_el.text is None:
                continue

            for event in parse_vcalendar(data_el.text):
                event.calendar_id = calendar.id
                event.etag = (
                    etag_el.text.strip('"')
                    if etag_el is not None and etag_el.text
                    else None
                )
                event.href = (
                    self._resolve_url(href_el.text)
                    if href_el is not None and href_el.text
                    else None
                )
                events.append(event)

        return sorted(events, key=lambda e: e.start)

    async def create_event(
        self,
        calendar: Calendar,
        title: str,
        start: str,
        end: str,
        description: str | None = None,
        location: str | None = None,
        all_day: bool = False,
    ) -> Event:
        uid = str(uuid.uuid4())
        ical_data = generate_vcalendar(
            uid=uid,
            title=title,
            start=start,
            end=end,
            description=description,
            location=location,
            all_day=all_day,
        )
        url = f"{calendar.url.rstrip('/')}/{uid}.ics"
        resp = await self._client.put(
            url,
            content=ical_data,
            headers={
                "Content-Type": "text/calendar; charset=utf-8",
                "If-None-Match": "*",
            },
        )
        self._check_response(resp, [201, 204])
        etag = resp.headers.get("etag", "").strip('"') or None

        return Event(
            uid=uid,
            calendar_id=calendar.id,
            title=title,
            start=start,
            end=end,
            description=description,
            location=location,
            all_day=all_day,
            etag=etag,
            href=url,
        )

    async def update_event(
        self,
        calendar: Calendar,
        uid: str,
        etag: str,
        title: str | None = None,
        start: str | None = None,
        end: str | None = None,
        description: str | None = None,
        location: str | None = None,
        all_day: bool | None = None,
    ) -> Event:
        url = await self._resolve_event_url(calendar, uid)
        resp = await self._client.get(url)
        self._check_response(resp, [200])

        logger.info("BACKUP before update [%s/%s]:\n%s", calendar.name, uid, resp.text)
        existing = parse_vcalendar(resp.text)
        if not existing:
            raise NotFoundError(f"Event {uid} not found in calendar {calendar.name}")
        current = existing[0]

        merged_title = title if title is not None else current.title
        merged_start = start if start is not None else current.start
        merged_end = end if end is not None else current.end
        merged_desc = description if description is not None else current.description
        merged_loc = location if location is not None else current.location
        merged_all_day = all_day if all_day is not None else current.all_day

        ical_data = generate_vcalendar(
            uid=uid,
            title=merged_title,
            start=merged_start,
            end=merged_end,
            description=merged_desc,
            location=merged_loc,
            all_day=merged_all_day,
        )
        resp = await self._client.put(
            url,
            content=ical_data,
            headers={
                "Content-Type": "text/calendar; charset=utf-8",
                "If-Match": f'"{etag}"',
            },
        )
        self._check_response(resp, [200, 201, 204])
        new_etag = resp.headers.get("etag", "").strip('"') or None

        return Event(
            uid=uid,
            calendar_id=calendar.id,
            title=merged_title,
            start=merged_start,
            end=merged_end,
            description=merged_desc,
            location=merged_loc,
            all_day=merged_all_day,
            etag=new_etag,
            href=url,
        )

    async def delete_event(
        self, calendar: Calendar, uid: str, etag: str | None = None
    ) -> None:
        url = await self._resolve_event_url(calendar, uid)

        backup_resp = await self._client.get(url)
        if backup_resp.status_code == 200:
            logger.info("BACKUP before delete [%s/%s]:\n%s", calendar.name, uid, backup_resp.text)

        headers: dict[str, str] = {}
        if etag:
            headers["If-Match"] = f'"{etag}"'
        resp = await self._client.delete(url, headers=headers)
        self._check_response(resp, [200, 204])

    async def _resolve_event_url(self, calendar: Calendar, uid: str) -> str:
        """Resolve the actual CalDAV resource URL for an event UID.

        The naive `{calendar}/{uid}.ics` path holds only when the resource
        filename equals the iCalendar UID. iCloud (and some other servers)
        keep the original filename used at PUT time while rewriting the
        VEVENT's UID on sync, so `get_events` returns a UID that no longer
        matches the href — making `{uid}.ics` 404. Fast-path the direct URL,
        then fall back to a UID-filtered calendar-query to find the real href.
        """
        direct = f"{calendar.url.rstrip('/')}/{uid}.ics"
        resp = await self._client.get(direct)
        if resp.status_code == 200:
            return direct
        if resp.status_code != 404:
            self._check_response(resp, [200])

        body = (
            '<?xml version="1.0" encoding="utf-8"?>'
            f'<C:calendar-query xmlns:D="{NS_DAV}" xmlns:C="{NS_CALDAV}">'
            "<D:prop><D:getetag/></D:prop>"
            "<C:filter>"
            '<C:comp-filter name="VCALENDAR">'
            '<C:comp-filter name="VEVENT">'
            '<C:prop-filter name="UID">'
            f'<C:text-match collation="i;octet">{_xml_escape(uid)}</C:text-match>'
            "</C:prop-filter>"
            "</C:comp-filter>"
            "</C:comp-filter>"
            "</C:filter>"
            "</C:calendar-query>"
        )
        report = await self._report(calendar.url, body)
        tree = ET.fromstring(report.text)
        for response in tree.findall(f"{{{NS_DAV}}}response"):
            href_el = response.find(f"{{{NS_DAV}}}href")
            if href_el is not None and href_el.text:
                return self._resolve_url(href_el.text)

        raise NotFoundError(f"Event {uid} not found in calendar {calendar.name}")

    # -- Discovery helpers ----------------------------------------------------

    async def _find_principal(self) -> str:
        body = (
            '<?xml version="1.0" encoding="utf-8"?>'
            f'<D:propfind xmlns:D="{NS_DAV}">'
            "<D:prop><D:current-user-principal/></D:prop>"
            "</D:propfind>"
        )
        resp = await self._propfind(
            self._base_url + "/.well-known/caldav", body, depth="0"
        )
        tree = ET.fromstring(resp.text)
        href = tree.find(
            f".//{{{NS_DAV}}}current-user-principal/{{{NS_DAV}}}href"
        )
        if href is None or href.text is None:
            raise CalDAVError("Could not discover principal URL")
        return self._resolve_url(href.text)

    async def _find_calendar_home(self, principal_url: str) -> str:
        body = (
            '<?xml version="1.0" encoding="utf-8"?>'
            f'<D:propfind xmlns:D="{NS_DAV}" xmlns:C="{NS_CALDAV}">'
            "<D:prop><C:calendar-home-set/></D:prop>"
            "</D:propfind>"
        )
        resp = await self._propfind(principal_url, body, depth="0")
        tree = ET.fromstring(resp.text)
        href = tree.find(
            f".//{{{NS_CALDAV}}}calendar-home-set/{{{NS_DAV}}}href"
        )
        if href is None or href.text is None:
            raise CalDAVError("Could not discover calendar home")
        return self._resolve_url(href.text)

    # -- HTTP primitives ------------------------------------------------------

    async def _propfind(
        self, url: str, body: str, depth: str = "0"
    ) -> httpx.Response:
        resp = await self._client.request(
            "PROPFIND",
            url,
            content=body,
            headers={
                "Content-Type": "application/xml; charset=utf-8",
                "Depth": depth,
            },
        )
        self._check_response(resp, [207])
        return resp

    async def _report(self, url: str, body: str) -> httpx.Response:
        resp = await self._client.request(
            "REPORT",
            url,
            content=body,
            headers={
                "Content-Type": "application/xml; charset=utf-8",
                "Depth": "1",
            },
        )
        self._check_response(resp, [207])
        return resp

    def _resolve_url(self, href: str) -> str:
        if href.startswith("http"):
            return href
        return urljoin(self._base_url + "/", href)

    def _check_response(self, resp: httpx.Response, expected: list[int]) -> None:
        if resp.status_code in expected:
            return
        if resp.status_code == 401:
            raise AuthError(
                "Authentication failed. If using iCloud, generate an app-specific "
                "password at https://account.apple.com → Sign-In and Security → "
                "App-Specific Passwords."
            )
        if resp.status_code == 403:
            raise AuthError(
                f"Access denied: {resp.url}. Check that your credentials have "
                "calendar access."
            )
        if resp.status_code == 404:
            raise NotFoundError(f"Not found: {resp.url}")
        if resp.status_code == 412:
            raise ConflictError(
                "Event was modified by another client since you last fetched it. "
                "Re-fetch and try again."
            )
        if resp.status_code == 503:
            raise RateLimitError(
                "CalDAV server returned 503 (rate limit or maintenance). "
                "Wait a few seconds and retry."
            )
        raise CalDAVError(
            f"CalDAV request failed: {resp.status_code} {resp.reason_phrase} "
            f"for {resp.request.method} {resp.url}"
        )
