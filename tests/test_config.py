# tests/test_config.py
"""Environment loading and validation."""

import pytest

from config.settings import (
    Config,
    ScheduleSettings,
    get_env_bool,
    get_env_int,
    load_calendar_urls,
    load_config_from_env,
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
    def test_get_env_bool(self, monkeypatch, raw, expected):
        monkeypatch.setenv("SOME_FLAG", raw)
        assert get_env_bool("SOME_FLAG", False) is expected

    def test_get_env_int_fallback(self, monkeypatch):
        monkeypatch.setenv("SOME_INT", "not a number")
        assert get_env_int("SOME_INT", 7) == 7


class TestCalendarUrls:
    def test_valid_json(self):
        urls = load_calendar_urls('[{"url":"http://a/x.ics","type":"tv"},{"url":"http://b/y.ics","type":"movie"}]')
        assert len(urls) == 2
        assert urls[1].type == "movie"

    def test_invalid_json_returns_empty(self):
        assert load_calendar_urls("{oops") == []

    def test_empty_url_skipped(self):
        assert load_calendar_urls('[{"url":"","type":"tv"}]') == []


class TestScheduleSettings:
    def test_run_time_parsed(self):
        s = ScheduleSettings(run_time="14:45")
        assert (s.hour, s.minute) == (14, 45)

    def test_bad_run_time_falls_back(self):
        s = ScheduleSettings(run_time="25:99")
        assert (s.hour, s.minute) == (9, 0)


class TestLoadConfig:
    def test_minimal_valid_config(self, monkeypatch):
        set_required(monkeypatch)
        cfg = load_config_from_env()
        assert len(cfg.calendar_urls) == 1
        assert cfg.timezone == "America/Chicago"
        # AUTO resolves to WEEK under the default WEEKLY schedule
        assert cfg.calendar_range == "WEEK"

    def test_auto_resolves_to_day_for_daily(self, monkeypatch):
        set_required(monkeypatch, SCHEDULE_TYPE="DAILY")
        assert load_config_from_env().calendar_range == "DAY"

    def test_missing_webhook_raises(self, monkeypatch):
        set_required(monkeypatch)
        monkeypatch.delenv("DISCORD_WEBHOOK_URL")
        with pytest.raises(ValueError):
            load_config_from_env()

    def test_validate_rejects_bad_timezone(self):
        cfg = Config(discord_webhook_url="https://example.invalid/h", timezone="Mars/Olympus")
        assert any("timezone" in e.lower() for e in cfg.validate())

    @pytest.mark.xfail(reason="defect 14, code reads MAX_LOG_SIZE not the documented LOG_MAX_SIZE_MB", strict=True)
    def test_documented_log_size_var_honored(self, monkeypatch):
        set_required(monkeypatch, LOG_MAX_SIZE_MB="5")
        monkeypatch.delenv("MAX_LOG_SIZE", raising=False)
        assert load_config_from_env().logging_settings.max_size_mb == 5
