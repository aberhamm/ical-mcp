"""iCal (RFC 5545) generation and parsing.

Handles the subset of iCalendar needed for basic event CRUD:
VCALENDAR/VEVENT with DTSTART, DTEND, SUMMARY, DESCRIPTION, LOCATION,
UID, DTSTAMP, and RRULE detection. No external dependencies.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone, date, timedelta
from zoneinfo import ZoneInfo

from .models import Event

CRLF = "\r\n"
PRODID = "-//ical-mcp//EN"


def generate_vcalendar(
    uid: str,
    title: str,
    start: str,
    end: str,
    description: str | None = None,
    location: str | None = None,
    all_day: bool = False,
) -> str:
    now = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        f"PRODID:{PRODID}",
        "BEGIN:VEVENT",
        f"UID:{uid}",
        f"DTSTAMP:{now}",
        f"SUMMARY:{_escape(title)}",
    ]

    if all_day:
        lines.append(f"DTSTART;VALUE=DATE:{_to_date(start)}")
        lines.append(f"DTEND;VALUE=DATE:{_to_date(end)}")
    else:
        lines.append(f"DTSTART:{_to_ical_datetime(start)}")
        lines.append(f"DTEND:{_to_ical_datetime(end)}")

    if description:
        lines.append(f"DESCRIPTION:{_escape(description)}")
    if location:
        lines.append(f"LOCATION:{_escape(location)}")

    lines.extend(["END:VEVENT", "END:VCALENDAR"])

    return CRLF.join(lines) + CRLF


def parse_vcalendar(text: str) -> list[Event]:
    unfolded = _unfold(text)
    events: list[Event] = []

    in_vevent = False
    props: dict[str, str] = {}
    params: dict[str, dict[str, str]] = {}

    for line in unfolded.splitlines():
        if line.strip() == "BEGIN:VEVENT":
            in_vevent = True
            props = {}
            params = {}
            continue
        if line.strip() == "END:VEVENT":
            in_vevent = False
            events.append(_props_to_event(props, params))
            continue
        if not in_vevent:
            continue

        name, line_params, value = _parse_property(line)
        props[name] = value
        if line_params:
            params[name] = line_params

    return events


def _props_to_event(props: dict[str, str], params: dict[str, dict[str, str]]) -> Event:
    uid = props.get("UID", "")
    title = _unescape(props.get("SUMMARY", ""))
    description = _unescape(props.get("DESCRIPTION", "")) if "DESCRIPTION" in props else None
    location = _unescape(props.get("LOCATION", "")) if "LOCATION" in props else None

    dtstart_params = params.get("DTSTART", {})
    dtend_params = params.get("DTEND", {})
    all_day = dtstart_params.get("VALUE") == "DATE"

    start = _from_ical_datetime(props.get("DTSTART", ""), dtstart_params)
    end = _from_ical_datetime(props.get("DTEND", ""), dtend_params)
    if not end and all_day and start:
        dt = date.fromisoformat(start) + timedelta(days=1)
        end = dt.isoformat()

    is_recurring = "RRULE" in props
    status_raw = props.get("STATUS", "CONFIRMED").lower()
    status_map = {"confirmed": "confirmed", "tentative": "tentative", "cancelled": "cancelled"}
    status = status_map.get(status_raw, "confirmed")

    return Event(
        uid=uid,
        calendar_id="",
        title=title,
        start=start,
        end=end or start,
        description=description,
        location=location,
        all_day=all_day,
        is_recurring=is_recurring,
        status=status,
    )


def _unfold(text: str) -> str:
    return re.sub(r"\r?\n[ \t]", "", text)


def _parse_property(line: str) -> tuple[str, dict[str, str], str]:
    match = re.match(r"^([A-Z0-9-]+)((?:;[^:]+)*):(.*)$", line, re.DOTALL)
    if not match:
        return ("", {}, line)
    name = match.group(1)
    raw_params = match.group(2)
    value = match.group(3)

    line_params: dict[str, str] = {}
    if raw_params:
        for param in raw_params.split(";"):
            if not param:
                continue
            if "=" in param:
                k, v = param.split("=", 1)
                line_params[k.upper()] = v
    return name, line_params, value


def _escape(text: str) -> str:
    return (
        text.replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\n", "\\n")
        .replace("\r", "")
    )


def _unescape(text: str) -> str:
    return (
        text.replace("\\n", "\n")
        .replace("\\N", "\n")
        .replace("\\,", ",")
        .replace("\\;", ";")
        .replace("\\\\", "\\")
    )


def _to_ical_datetime(iso: str) -> str:
    dt = datetime.fromisoformat(iso)
    utc = dt.astimezone(timezone.utc)
    return utc.strftime("%Y%m%dT%H%M%SZ")


def _to_date(iso: str) -> str:
    if "T" in iso:
        dt = datetime.fromisoformat(iso)
        return dt.strftime("%Y%m%d")
    return iso.replace("-", "")


def _from_ical_datetime(value: str, params: dict[str, str]) -> str:
    if not value:
        return ""

    if params.get("VALUE") == "DATE" or len(value) == 8:
        return f"{value[:4]}-{value[4:6]}-{value[6:8]}"

    if value.endswith("Z"):
        stripped = value[:-1]
        dt = datetime.strptime(stripped, "%Y%m%dT%H%M%S").replace(tzinfo=timezone.utc)
        return dt.isoformat()

    dt_naive = datetime.strptime(value[:15], "%Y%m%dT%H%M%S")
    tzid = params.get("TZID")
    if tzid:
        try:
            tz = ZoneInfo(tzid)
            dt_aware = dt_naive.replace(tzinfo=tz)
            return dt_aware.isoformat()
        except KeyError:
            pass

    return dt_naive.isoformat()
