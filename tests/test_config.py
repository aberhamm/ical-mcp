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
        monkeypatch.delenv("ICAL_MCP_WRITABLE_CALENDARS", raising=False)
        config = Config.from_env()
        assert config.url == "https://caldav.icloud.com"
        assert config.provider == Provider.ICLOUD
        assert config.writable_calendars == set()
        assert config.timezone == "UTC"

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


class TestWritableCalendars:
    def _config(self, **kwargs) -> Config:
        defaults = dict(url="https://caldav.icloud.com", username="u", password="p")
        defaults.update(kwargs)
        return Config(**defaults)

    def test_default_is_read_only(self) -> None:
        config = self._config()
        assert config.writable_calendars == set()
        assert not config.is_writable("home", "Matthew")
        assert not config.all_writable

    def test_single_writable_by_id(self) -> None:
        config = self._config(writable_calendars={"home"})
        assert config.is_writable("home", "Matthew")
        assert not config.is_writable("other-id", "Other Calendar")

    def test_single_writable_by_name(self) -> None:
        config = self._config(writable_calendars={"Matthew"})
        assert config.is_writable("home", "Matthew")
        assert not config.is_writable("other-id", "Other Calendar")

    def test_multiple_writable(self) -> None:
        config = self._config(writable_calendars={"home", "No Conflicts"})
        assert config.is_writable("home", "Matthew")
        assert config.is_writable("xxx", "No Conflicts")
        assert not config.is_writable("yyy", "Shared Calendar")

    def test_wildcard_all_writable(self) -> None:
        config = self._config(writable_calendars={"*"})
        assert config.all_writable
        assert config.is_writable("anything", "Any Calendar")

    def test_from_env_single(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ICAL_MCP_URL", "https://caldav.icloud.com")
        monkeypatch.setenv("ICAL_MCP_USERNAME", "user")
        monkeypatch.setenv("ICAL_MCP_PASSWORD", "pass")
        monkeypatch.setenv("ICAL_MCP_WRITABLE_CALENDARS", "home")
        config = Config.from_env()
        assert config.writable_calendars == {"home"}

    def test_from_env_multiple(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ICAL_MCP_URL", "https://caldav.icloud.com")
        monkeypatch.setenv("ICAL_MCP_USERNAME", "user")
        monkeypatch.setenv("ICAL_MCP_PASSWORD", "pass")
        monkeypatch.setenv("ICAL_MCP_WRITABLE_CALENDARS", "home, No Conflicts")
        config = Config.from_env()
        assert config.writable_calendars == {"home", "No Conflicts"}

    def test_from_env_wildcard(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ICAL_MCP_URL", "https://caldav.icloud.com")
        monkeypatch.setenv("ICAL_MCP_USERNAME", "user")
        monkeypatch.setenv("ICAL_MCP_PASSWORD", "pass")
        monkeypatch.setenv("ICAL_MCP_WRITABLE_CALENDARS", "*")
        config = Config.from_env()
        assert config.all_writable

    def test_from_env_empty_is_read_only(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ICAL_MCP_URL", "https://caldav.icloud.com")
        monkeypatch.setenv("ICAL_MCP_USERNAME", "user")
        monkeypatch.setenv("ICAL_MCP_PASSWORD", "pass")
        monkeypatch.setenv("ICAL_MCP_WRITABLE_CALENDARS", "")
        config = Config.from_env()
        assert config.writable_calendars == set()
        assert not config.is_writable("home", "Matthew")
