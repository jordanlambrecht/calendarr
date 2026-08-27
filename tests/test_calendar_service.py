# tests/test_calendar_service.py
"""Fetch and parse path with mocked HTTP."""

from unittest.mock import MagicMock, patch

import requests

from config.settings import CalendarUrl, Config
from conftest import aware, make_ics, vevent
from services.calendar_service import CalendarService


def service() -> CalendarService:
    cfg = Config(timezone="UTC", calendar_urls=[CalendarUrl(url="http://test/cal.ics", type="tv")])
    return CalendarService(cfg)


def mock_response(ics: bytes) -> MagicMock:
    resp = MagicMock()
    resp.content = ics
    resp.raise_for_status = MagicMock()
    return resp


class TestFetchEvents:
    def test_happy_path(self):
        ics = make_ics(
            vevent("1", "DTSTART:20260826T200000Z", "Show - S01E05 - Title"),
            vevent("2", "DTSTART;VALUE=DATE:20260828", "Movie Day"),
        )
        with patch("services.calendar_service.requests.get", return_value=mock_response(ics)):
            events = service().fetch_events(aware(2026, 8, 24), aware(2026, 8, 31))
        assert len(events) == 2
        assert events[0].start_time <= events[1].start_time

    def test_fetch_error_returns_empty(self):
        # Defect 3 in the register, failures are silently indistinguishable
        # from an empty week. Behavior changes in the restructure wave.
        with patch("services.calendar_service.requests.get", side_effect=requests.RequestException("boom")):
            events = service().fetch_events(aware(2026, 8, 24), aware(2026, 8, 31))
        assert events == []

    def test_garbage_body_returns_empty(self):
        with patch("services.calendar_service.requests.get", return_value=mock_response(b"not an ics")):
            events = service().fetch_events(aware(2026, 8, 24), aware(2026, 8, 31))
        assert events == []

    def test_event_on_eighth_day_excluded(self):
        # Guards fetch boundary inclusivity at the end of the requested span
        ics = make_ics(vevent("1", "DTSTART;VALUE=DATE:20260831", "Next Week Show - S01E01"))
        with patch("services.calendar_service.requests.get", return_value=mock_response(ics)):
            events = service().fetch_events(aware(2026, 8, 24), aware(2026, 8, 31))
        assert events == []
