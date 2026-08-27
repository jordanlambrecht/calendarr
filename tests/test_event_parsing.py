# tests/test_event_parsing.py
"""ICS parsing into Event objects, matching the calendar_service path."""

import icalendar
import pytest
import pytz
import recurring_ical_events

from conftest import aware, make_ics, mk_event, vevent
from models.event import Event

CHI = pytz.timezone("America/Chicago")


def parse_between(ics: bytes, start, end):
    cal = icalendar.Calendar.from_ical(ics)
    return recurring_ical_events.of(cal).between(start, end)


class TestFromIcalEvent:
    def test_utc_datetime_converted_to_local(self):
        ics = make_ics(vevent("1", "DTSTART:20260827T010000Z", "Test Show - S02E05 - Pilot"))
        evs = parse_between(ics, aware(2026, 8, 24, tz="America/Chicago"), aware(2026, 8, 31, tz="America/Chicago"))
        assert len(evs) == 1
        ev = Event.from_ical_event(evs[0], CHI, "tv")
        # 01.00 UTC on the 27th is the evening of the 26th in Chicago
        assert ev.start_time.date().day == 26
        assert str(ev.summary) == "Test Show - S02E05 - Pilot"

    def test_all_day_event_localized_midnight(self):
        ics = make_ics(vevent("2", "DTSTART;VALUE=DATE:20260828", "Test Movie (2026)"))
        evs = parse_between(ics, aware(2026, 8, 24, tz="America/Chicago"), aware(2026, 8, 31, tz="America/Chicago"))
        assert len(evs) == 1
        ev = Event.from_ical_event(evs[0], CHI, "movie")
        assert ev.start_time.hour == 0
        assert ev.start_time.date().day == 28

    def test_missing_dtstart_raises(self):
        bare = icalendar.Event()
        bare.add("SUMMARY", "No start")
        with pytest.raises(ValueError):
            Event.from_ical_event(bare, CHI, "tv")

    def test_invalid_source_type_rejected(self):
        with pytest.raises(ValueError):
            mk_event("Show", aware(2026, 8, 24), source_type="podcast")

    def test_empty_summary_rejected(self):
        with pytest.raises(ValueError):
            mk_event("", aware(2026, 8, 24))


class TestPremiereDetection:
    @pytest.mark.parametrize(
        "summary,expected",
        [
            ("Show - S02E01 - Opener", True),
            ("Show - 3x01", True),
            ("Show - S02E11", False),
            ("Show - S02E010", False),
            ("Movie Title (2026)", False),
        ],
    )
    def test_premiere_pattern(self, summary, expected):
        assert mk_event(summary, aware(2026, 8, 24)).is_premiere is expected


class TestDedupKey:
    def test_same_summary_same_date_equal(self):
        a = mk_event("Show - S01E01", aware(2026, 8, 24, 9))
        b = mk_event("Show - S01E01", aware(2026, 8, 24, 20))
        assert a == b
        assert hash(a) == hash(b)

    def test_different_date_not_equal(self):
        a = mk_event("Show - S01E01", aware(2026, 8, 24))
        b = mk_event("Show - S01E01", aware(2026, 8, 25))
        assert a != b
