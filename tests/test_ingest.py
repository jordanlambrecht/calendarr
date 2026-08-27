# tests/test_ingest.py
"""Feed fetching and parsing with mocked HTTP."""

from unittest.mock import MagicMock, patch

import requests

from calendarr.ingest import fetch_source
from conftest import CHICAGO, aware, make_ics, mk_config, tv_source, vevent


def mock_response(body: bytes) -> MagicMock:
    resp = MagicMock()
    resp.content = body
    resp.raise_for_status = MagicMock()
    return resp


WINDOW = (aware(2026, 8, 24, tz=CHICAGO), aware(2026, 8, 31, tz=CHICAGO))


class TestFetchSource:
    def test_happy_path(self):
        ics = make_ics(
            vevent("1", "DTSTART:20260828T010000Z", "Show - S01E05 - Title"),
            vevent("2", "DTSTART;VALUE=DATE:20260829", "Movie Day"),
        )
        cfg = mk_config(timezone=CHICAGO)
        with patch("calendarr.ingest.requests.get", return_value=mock_response(ics)):
            result = fetch_source(tv_source(), cfg, *WINDOW)
        assert result.ok
        assert len(result.events) == 2
        # UTC datetime lands on the local Chicago day
        assert result.events[0].start_time.date().day == 27

    def test_retry_then_success(self):
        ics = make_ics(vevent("1", "DTSTART:20260828T010000Z", "Show - S01E05"))
        side_effects = [requests.ConnectionError("down"), mock_response(ics)]
        with (
            patch("calendarr.ingest.requests.get", side_effect=side_effects),
            patch("calendarr.ingest.time.sleep"),
        ):
            result = fetch_source(tv_source(), mk_config(timezone=CHICAGO), *WINDOW)
        assert result.ok
        assert len(result.events) == 1

    def test_persistent_failure_returns_error(self):
        with (
            patch("calendarr.ingest.requests.get", side_effect=requests.ConnectionError("down")),
            patch("calendarr.ingest.time.sleep"),
        ):
            result = fetch_source(tv_source(), mk_config(), *WINDOW)
        assert not result.ok
        assert "fetch failed" in result.error
        assert result.events == []

    def test_garbage_body_returns_parse_error(self):
        with patch("calendarr.ingest.requests.get", return_value=mock_response(b"not an ics")):
            result = fetch_source(tv_source(), mk_config(), *WINDOW)
        assert not result.ok
        assert "parse failed" in result.error

    def test_malformed_event_isolated_not_fatal(self):
        ics = make_ics(vevent("1", "DTSTART:20260828T010000Z", "Show - S01E05"))
        with (
            patch("calendarr.ingest.requests.get", return_value=mock_response(ics)),
            patch("calendarr.ingest._to_event", side_effect=TypeError("weird property")),
        ):
            result = fetch_source(tv_source(), mk_config(timezone=CHICAGO), *WINDOW)
        assert result.ok
        assert result.events == []

    def test_end_boundary_exclusive(self):
        # Was register defect 10, the window must stay seven days
        ics = make_ics(vevent("1", "DTSTART;VALUE=DATE:20260831", "Next Week - S01E01"))
        with patch("calendarr.ingest.requests.get", return_value=mock_response(ics)):
            result = fetch_source(tv_source(), mk_config(timezone=CHICAGO), *WINDOW)
        assert result.ok
        assert result.events == []
