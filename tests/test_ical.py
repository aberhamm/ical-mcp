from ical_mcp.ical import generate_vcalendar, parse_vcalendar


class TestParseVCalendar:
    def test_basic_event(self, sample_vcalendar: str) -> None:
        events = parse_vcalendar(sample_vcalendar)
        assert len(events) == 1
        e = events[0]
        assert e.uid == "test-uid-001"
        assert e.title == "Team standup"
        assert e.start == "2026-06-10T14:00:00+00:00"
        assert e.end == "2026-06-10T15:00:00+00:00"
        assert e.description == "Daily sync with the team"
        assert e.location == "Conference Room B"
        assert e.all_day is False
        assert e.is_recurring is False
        assert e.status == "confirmed"

    def test_allday_event(self, sample_allday_vcalendar: str) -> None:
        events = parse_vcalendar(sample_allday_vcalendar)
        assert len(events) == 1
        e = events[0]
        assert e.uid == "test-uid-002"
        assert e.title == "Company holiday"
        assert e.all_day is True
        assert e.start == "2026-06-15"
        assert e.end == "2026-06-16"

    def test_recurring_event(self, sample_recurring_vcalendar: str) -> None:
        events = parse_vcalendar(sample_recurring_vcalendar)
        assert len(events) == 1
        assert events[0].is_recurring is True

    def test_timezone_event(self, sample_timezone_vcalendar: str) -> None:
        events = parse_vcalendar(sample_timezone_vcalendar)
        assert len(events) == 1
        e = events[0]
        assert e.title == "Morning meeting"
        assert "09:00:00" in e.start
        assert e.location == "123 Main St, Suite 400"
        assert "Q3 goals\nand roadmap" in e.description

    def test_empty_input(self) -> None:
        events = parse_vcalendar("")
        assert events == []

    def test_no_vevent(self) -> None:
        text = "BEGIN:VCALENDAR\r\nVERSION:2.0\r\nEND:VCALENDAR\r\n"
        events = parse_vcalendar(text)
        assert events == []


class TestGenerateVCalendar:
    def test_basic_event(self) -> None:
        ical = generate_vcalendar(
            uid="gen-001",
            title="Lunch",
            start="2026-06-10T12:00:00+00:00",
            end="2026-06-10T13:00:00+00:00",
        )
        assert "BEGIN:VCALENDAR" in ical
        assert "UID:gen-001" in ical
        assert "SUMMARY:Lunch" in ical
        assert "DTSTART:20260610T120000Z" in ical
        assert "DTEND:20260610T130000Z" in ical
        assert ical.endswith("\r\n")

    def test_allday_event(self) -> None:
        ical = generate_vcalendar(
            uid="gen-002",
            title="Vacation",
            start="2026-06-15",
            end="2026-06-16",
            all_day=True,
        )
        assert "DTSTART;VALUE=DATE:20260615" in ical
        assert "DTEND;VALUE=DATE:20260616" in ical

    def test_description_and_location(self) -> None:
        ical = generate_vcalendar(
            uid="gen-003",
            title="Dentist",
            start="2026-06-10T09:00:00-04:00",
            end="2026-06-10T10:00:00-04:00",
            description="Annual checkup",
            location="123 Main St",
        )
        assert "DESCRIPTION:Annual checkup" in ical
        assert "LOCATION:123 Main St" in ical

    def test_escaping(self) -> None:
        ical = generate_vcalendar(
            uid="gen-004",
            title="Review; planning, wrap-up",
            start="2026-06-10T14:00:00+00:00",
            end="2026-06-10T15:00:00+00:00",
            description="Line 1\nLine 2",
        )
        assert "SUMMARY:Review\\; planning\\, wrap-up" in ical
        assert "DESCRIPTION:Line 1\\nLine 2" in ical

    def test_roundtrip(self) -> None:
        ical = generate_vcalendar(
            uid="rt-001",
            title="Roundtrip test",
            start="2026-06-10T14:00:00+02:00",
            end="2026-06-10T15:00:00+02:00",
            description="With special chars: commas, semicolons; etc",
            location="Room A, Building 5",
        )
        events = parse_vcalendar(ical)
        assert len(events) == 1
        e = events[0]
        assert e.uid == "rt-001"
        assert e.title == "Roundtrip test"
        assert "With special chars: commas, semicolons; etc" in e.description
        assert e.location == "Room A, Building 5"
