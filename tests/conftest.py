# tests/conftest.py
"""Shared helpers for the characterization test suite."""

from datetime import datetime

import pytz


def make_ics(*vevents: str) -> bytes:
    """Build a minimal ICS calendar from VEVENT blocks."""
    return (
        "BEGIN:VCALENDAR\r\nVERSION:2.0\r\nPRODID:-//Test//Test//EN\r\n" + "".join(vevents) + "END:VCALENDAR\r\n"
    ).encode()


def vevent(uid: str, dtstart_line: str, summary: str) -> str:
    """Build one VEVENT block. dtstart_line is the full DTSTART property."""
    return f"BEGIN:VEVENT\r\nUID:{uid}\r\n{dtstart_line}\r\nSUMMARY:{summary}\r\nEND:VEVENT\r\n"


def aware(y: int, mo: int, d: int, h: int = 0, mi: int = 0, tz: str = "UTC") -> datetime:
    """Timezone aware datetime via pytz, matching app conventions."""
    return pytz.timezone(tz).localize(datetime(y, mo, d, h, mi))


def mk_event(summary: str, when: datetime, source_type: str = "tv"):
    """Build a domain Event directly, bypassing ICS parsing."""
    from models.event import Event

    return Event(summary=summary, start_time=when, source_type=source_type, raw_event={})
