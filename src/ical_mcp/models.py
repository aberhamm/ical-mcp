from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Calendar:
    id: str
    name: str
    url: str
    color: str | None = None
    ctag: str | None = None

    def to_dict(self) -> dict:
        d = {"id": self.id, "name": self.name}
        if self.color:
            d["color"] = self.color
        return d


@dataclass
class Event:
    uid: str
    calendar_id: str
    title: str
    start: str
    end: str
    description: str | None = None
    location: str | None = None
    all_day: bool = False
    is_recurring: bool = False
    series_id: str | None = None
    status: str = "confirmed"
    etag: str | None = None
    href: str | None = None

    def to_dict(self) -> dict:
        d = {
            "event_id": self.uid,
            "calendar_id": self.calendar_id,
            "title": self.title,
            "start": self.start,
            "end": self.end,
            "all_day": self.all_day,
            "status": self.status,
        }
        if self.description:
            d["description"] = self.description
        if self.location:
            d["location"] = self.location
        if self.is_recurring:
            d["is_recurring"] = True
            if self.series_id:
                d["series_id"] = self.series_id
        if self.etag:
            d["etag"] = self.etag
        return d
