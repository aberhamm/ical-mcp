from __future__ import annotations

import os
from dataclasses import dataclass, field
from enum import Enum


class Provider(Enum):
    ICLOUD = "icloud"
    GOOGLE = "google"
    FASTMAIL = "fastmail"
    NEXTCLOUD = "nextcloud"
    GENERIC = "generic"


def detect_provider(url: str) -> Provider:
    url_lower = url.lower()
    if "icloud.com" in url_lower:
        return Provider.ICLOUD
    if "googleapis.com" in url_lower or "google.com" in url_lower:
        return Provider.GOOGLE
    if "fastmail.com" in url_lower:
        return Provider.FASTMAIL
    if "nextcloud" in url_lower:
        return Provider.NEXTCLOUD
    return Provider.GENERIC


@dataclass
class Config:
    url: str
    username: str
    password: str
    timezone: str = "UTC"
    read_only: bool = False
    provider: Provider = field(init=False)

    def __post_init__(self) -> None:
        self.url = self.url.rstrip("/")
        self.provider = detect_provider(self.url)

    @classmethod
    def from_env(cls) -> Config:
        url = os.environ.get("ICAL_MCP_URL", "")
        username = os.environ.get("ICAL_MCP_USERNAME", "")
        password = os.environ.get("ICAL_MCP_PASSWORD", "")
        if not all([url, username, password]):
            missing = [
                name
                for name, val in [
                    ("ICAL_MCP_URL", url),
                    ("ICAL_MCP_USERNAME", username),
                    ("ICAL_MCP_PASSWORD", password),
                ]
                if not val
            ]
            raise ValueError(
                f"Missing required environment variables: {', '.join(missing)}. "
                "See .env.example for configuration."
            )
        return cls(
            url=url,
            username=username,
            password=password,
            timezone=os.environ.get("ICAL_MCP_TIMEZONE", "UTC"),
            read_only=os.environ.get("ICAL_MCP_READ_ONLY", "").lower()
            in ("true", "1", "yes"),
        )
