# tests/test_config.py
"""Environment loading, validation, and legacy aliases."""

import pytest

from calendarr.config import (
    CalendarRange,
    EventType,
    env_bool,
    env_int,
    load_config,
    parse_calendar_urls,
    parse_run_time,
    parse_schedule_day,
)

REQUIRED_ENV = {
    "DISCORD_WEBHOOK_URL": "https://example.invalid/hook",
    "CALENDAR_URLS": '[{"url":"http://test/cal.ics","type":"tv"}]',
    "TZ": "America/Chicago",
}


def set_required(monkeypatch, **extra):
    for k, v in {**REQUIRED_ENV, **extra}.items():
        monkeypatch.setenv(k, v)


class TestEnvHelpers:
    @pytest.mark.parametrize(
        "raw,expected", [("true", True), ("YES", True), ("1", True), ("false", False), ("banana", False)]
    )
    def test_env_bool(self, monkeypatch, raw, expected):
        monkeypatch.setenv("SOME_FLAG", raw)
        assert env_bool("SOME_FLAG", False) is expected

    def test_env_int_fallback(self, monkeypatch):
        monkeypatch.setenv("SOME_INT", "not a number")
        assert env_int("SOME_INT", 7) == 7


class TestScheduleDay:
    @pytest.mark.parametrize(
        "raw,expected",
        [("0", "sun"), ("1", "mon"), ("6", "sat"), ("mon", "mon"), ("Sunday", "sun"), ("FRI", "fri")],
    )
    def test_documented_mapping(self, raw, expected):
        # Contract is Sunday=0 per the README, names pass through
        assert parse_schedule_day(raw) == expected

    @pytest.mark.parametrize("raw", ["7", "-1", "xyz"])
    def test_invalid_rejected(self, raw):
        with pytest.raises(ValueError):
            parse_schedule_day(raw)


class TestRunTime:
    def test_parsed(self):
        assert parse_run_time("14:45") == (14, 45)

    @pytest.mark.parametrize("raw", ["25:00", "09:75", "morning"])
    def test_invalid(self, raw):
        with pytest.raises(ValueError):
            parse_run_time(raw)


class TestCalendarUrls:
    def test_valid(self):
        sources = parse_calendar_urls('[{"url":"http://a/x.ics","type":"tv"},{"url":"http://b/y.ics","type":"movie"}]')
        assert len(sources) == 2
        assert sources[1].type is EventType.MOVIE

    def test_invalid_json(self):
        with pytest.raises(ValueError):
            parse_calendar_urls("{oops")

    def test_display_name_hides_apikey(self):
        source = parse_calendar_urls('[{"url":"http://sonarr.local:8989/feed.ics?apikey=SECRET","type":"tv"}]')[0]
        assert source.display_name == "sonarr.local:8989"
        assert "SECRET" not in source.display_name


class TestLoadConfig:
    def test_minimal_valid(self, monkeypatch):
        set_required(monkeypatch)
        cfg = load_config()
        assert cfg.timezone == "America/Chicago"
        assert cfg.calendar_range is CalendarRange.WEEK
        assert cfg.schedule_day == "mon"

    def test_auto_resolves_day_for_daily(self, monkeypatch):
        set_required(monkeypatch, SCHEDULE_TYPE="DAILY")
        assert load_config().calendar_range is CalendarRange.DAY

    def test_missing_webhook_fails(self, monkeypatch):
        set_required(monkeypatch)
        monkeypatch.delenv("DISCORD_WEBHOOK_URL")
        with pytest.raises(ValueError):
            load_config()

    def test_bad_timezone_fails(self, monkeypatch):
        set_required(monkeypatch, TZ="Mars/Olympus")
        with pytest.raises(ValueError, match="timezone"):
            load_config()

    def test_bad_schedule_day_fails(self, monkeypatch):
        set_required(monkeypatch, SCHEDULE_DAY="9")
        with pytest.raises(ValueError, match="SCHEDULE_DAY"):
            load_config()

    def test_documented_log_size_var_honored(self, monkeypatch):
        # Was register defect 14, LOG_MAX_SIZE_MB is the documented name
        set_required(monkeypatch, LOG_MAX_SIZE_MB="5")
        assert load_config().log_max_size_mb == 5

    def test_legacy_log_size_alias(self, monkeypatch):
        set_required(monkeypatch, MAX_LOG_SIZE="3")
        assert load_config().log_max_size_mb == 3

    def test_legacy_mention_role_alias(self, monkeypatch):
        set_required(monkeypatch, MENTION_ROLE_ID="123")
        assert load_config().discord_mention_role_id == "123"
