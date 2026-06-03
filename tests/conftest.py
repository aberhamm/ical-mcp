import pytest


@pytest.fixture
def sample_vcalendar() -> str:
    return (
        "BEGIN:VCALENDAR\r\n"
        "VERSION:2.0\r\n"
        "PRODID:-//Test//EN\r\n"
        "BEGIN:VEVENT\r\n"
        "UID:test-uid-001\r\n"
        "DTSTAMP:20260610T120000Z\r\n"
        "DTSTART:20260610T140000Z\r\n"
        "DTEND:20260610T150000Z\r\n"
        "SUMMARY:Team standup\r\n"
        "DESCRIPTION:Daily sync with the team\r\n"
        "LOCATION:Conference Room B\r\n"
        "STATUS:CONFIRMED\r\n"
        "END:VEVENT\r\n"
        "END:VCALENDAR\r\n"
    )


@pytest.fixture
def sample_allday_vcalendar() -> str:
    return (
        "BEGIN:VCALENDAR\r\n"
        "VERSION:2.0\r\n"
        "BEGIN:VEVENT\r\n"
        "UID:test-uid-002\r\n"
        "DTSTAMP:20260610T120000Z\r\n"
        "DTSTART;VALUE=DATE:20260615\r\n"
        "DTEND;VALUE=DATE:20260616\r\n"
        "SUMMARY:Company holiday\r\n"
        "END:VEVENT\r\n"
        "END:VCALENDAR\r\n"
    )


@pytest.fixture
def sample_recurring_vcalendar() -> str:
    return (
        "BEGIN:VCALENDAR\r\n"
        "VERSION:2.0\r\n"
        "BEGIN:VEVENT\r\n"
        "UID:test-uid-003\r\n"
        "DTSTAMP:20260610T120000Z\r\n"
        "DTSTART:20260610T090000Z\r\n"
        "DTEND:20260610T093000Z\r\n"
        "SUMMARY:Weekly review\r\n"
        "RRULE:FREQ=WEEKLY;BYDAY=WE;COUNT=10\r\n"
        "END:VEVENT\r\n"
        "END:VCALENDAR\r\n"
    )


@pytest.fixture
def sample_timezone_vcalendar() -> str:
    return (
        "BEGIN:VCALENDAR\r\n"
        "VERSION:2.0\r\n"
        "BEGIN:VEVENT\r\n"
        "UID:test-uid-004\r\n"
        "DTSTAMP:20260610T120000Z\r\n"
        "DTSTART;TZID=America/New_York:20260610T090000\r\n"
        "DTEND;TZID=America/New_York:20260610T100000\r\n"
        "SUMMARY:Morning meeting\r\n"
        "LOCATION:123 Main St\\, Suite 400\r\n"
        "DESCRIPTION:Discuss Q3 goals\\nand roadmap\r\n"
        "END:VEVENT\r\n"
        "END:VCALENDAR\r\n"
    )
