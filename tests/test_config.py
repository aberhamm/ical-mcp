import os

import pytest

from ical_mcp.config import Config, Provider, detect_provider


class TestDetectProvider:
    def test_icloud(self) -> None:
        assert detect_provider("https://caldav.icloud.com") == Provider.ICLOUD

    def test_google(self) -> None:
        assert detect_provider("https://apidata.googleapis.com/caldav/v2") == Provider.GOOGLE

    def test_fastmail(self) -> None:
        assert detect_provider("https://caldav.fastmail.com") == Provider.FASTMAIL

    def test_nextcloud(self) -> None:
        assert detect_provider("https://cloud.example.com/nextcloud/dav") == Provider.NEXTCLOUD

    def test_generic(self) -> None:
        assert detect_provider("https://my-radicale.local") == Provider.GENERIC


class TestConfig:
    def test_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ICAL_MCP_URL", "https://caldav.icloud.com")
        monkeypatch.setenv("ICAL_MCP_USERNAME", "user@icloud.com")
        monkeypatch.setenv("ICAL_MCP_PASSWORD", "xxxx-xxxx-xxxx-xxxx")
        config = Config.from_env()
        assert config.url == "https://caldav.icloud.com"
        assert config.provider == Provider.ICLOUD
        assert config.read_only is False
        assert config.timezone == "UTC"

    def test_read_only_flag(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ICAL_MCP_URL", "https://caldav.icloud.com")
        monkeypatch.setenv("ICAL_MCP_USERNAME", "user@icloud.com")
        monkeypatch.setenv("ICAL_MCP_PASSWORD", "xxxx")
        monkeypatch.setenv("ICAL_MCP_READ_ONLY", "true")
        config = Config.from_env()
        assert config.read_only is True

    def test_custom_timezone(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ICAL_MCP_URL", "https://caldav.icloud.com")
        monkeypatch.setenv("ICAL_MCP_USERNAME", "user@icloud.com")
        monkeypatch.setenv("ICAL_MCP_PASSWORD", "xxxx")
        monkeypatch.setenv("ICAL_MCP_TIMEZONE", "America/New_York")
        config = Config.from_env()
        assert config.timezone == "America/New_York"

    def test_missing_url_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("ICAL_MCP_URL", raising=False)
        monkeypatch.setenv("ICAL_MCP_USERNAME", "user")
        monkeypatch.setenv("ICAL_MCP_PASSWORD", "pass")
        with pytest.raises(ValueError, match="ICAL_MCP_URL"):
            Config.from_env()

    def test_strips_trailing_slash(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ICAL_MCP_URL", "https://caldav.icloud.com/")
        monkeypatch.setenv("ICAL_MCP_USERNAME", "user")
        monkeypatch.setenv("ICAL_MCP_PASSWORD", "pass")
        config = Config.from_env()
        assert config.url == "https://caldav.icloud.com"
