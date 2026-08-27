# tests/conftest.py
"""Shared helpers for the calendarr test suite."""

from datetime import datetime
from zoneinfo import ZoneInfo

from calendarr.config import CalendarSource, Config, EventType
from calendarr.domain import Event

CHICAGO = "America/Chicago"


def make_ics(*vevents: str) -> bytes:
    return (
        "BEGIN:VCALENDAR\r\nVERSION:2.0\r\nPRODID:-//Test//Test//EN\r\n" + "".join(vevents) + "END:VCALENDAR\r\n"
    ).encode()


def vevent(uid: str, dtstart_line: str, summary: str) -> str:
    return f"BEGIN:VEVENT\r\nUID:{uid}\r\n{dtstart_line}\r\nSUMMARY:{summary}\r\nEND:VEVENT\r\n"


def aware(y: int, mo: int, d: int, h: int = 0, mi: int = 0, tz: str = "UTC") -> datetime:
    return datetime(y, mo, d, h, mi, tzinfo=ZoneInfo(tz))


def mk_event(summary: str, when: datetime, source_type: EventType = EventType.TV) -> Event:
    return Event(summary=summary, start_time=when, source_type=source_type)


def mk_config(**overrides) -> Config:
    defaults = dict(
        discord_webhook_url="https://example.invalid/hook",
        calendar_urls=[CalendarSource(url="http://test/cal.ics", type=EventType.TV)],
        timezone="UTC",
    )
    defaults.update(overrides)
    return Config(**defaults)


def tv_source(url: str = "http://test/cal.ics") -> CalendarSource:
    return CalendarSource(url=url, type=EventType.TV)
