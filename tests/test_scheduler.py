# tests/test_scheduler.py
"""Trigger construction and downtime catch up logic."""

from datetime import datetime

from calendarr.config import ScheduleType
from calendarr.scheduler import (
    build_trigger,
    last_scheduled_before,
    needs_catch_up,
    read_marker,
    write_marker,
)
from conftest import CHICAGO, aware, mk_config

# Thursday morning in Chicago
NOW = aware(2026, 8, 27, 10, 0, tz=CHICAGO)


class TestBuildTrigger:
    def test_weekly_uses_day_name(self):
        cfg = mk_config(timezone=CHICAGO, schedule_day="sun", run_hour=9, run_minute=30)
        trigger = build_trigger(cfg)
        rendered = str(trigger)
        assert "day_of_week='sun'" in rendered
        assert "hour='9'" in rendered

    def test_daily_has_no_day_field(self):
        cfg = mk_config(timezone=CHICAGO, schedule_type=ScheduleType.DAILY)
        assert "day_of_week" not in str(build_trigger(cfg))

    def test_custom_cron(self):
        cfg = mk_config(timezone=CHICAGO, cron_schedule="0 10 * * 1")
        assert "hour='10'" in str(build_trigger(cfg))


class TestLastScheduledBefore:
    def test_weekly_previous_sunday(self):
        cfg = mk_config(timezone=CHICAGO, schedule_day="sun", run_hour=9, run_minute=0)
        assert last_scheduled_before(cfg, NOW) == aware(2026, 8, 23, 9, 0, tz=CHICAGO)

    def test_weekly_same_day_before_run_time(self):
        cfg = mk_config(timezone=CHICAGO, schedule_day="thu", run_hour=23, run_minute=0)
        assert last_scheduled_before(cfg, NOW) == aware(2026, 8, 20, 23, 0, tz=CHICAGO)

    def test_daily_earlier_today(self):
        cfg = mk_config(timezone=CHICAGO, schedule_type=ScheduleType.DAILY, run_hour=9)
        assert last_scheduled_before(cfg, NOW) == aware(2026, 8, 27, 9, 0, tz=CHICAGO)

    def test_daily_yesterday(self):
        cfg = mk_config(timezone=CHICAGO, schedule_type=ScheduleType.DAILY, run_hour=23)
        assert last_scheduled_before(cfg, NOW) == aware(2026, 8, 26, 23, 0, tz=CHICAGO)

    def test_custom_cron_unsupported(self):
        cfg = mk_config(timezone=CHICAGO, cron_schedule="0 10 * * 1")
        assert last_scheduled_before(cfg, NOW) is None


class TestCatchUp:
    def cfg(self, tmp_path, **kw):
        base = dict(timezone=CHICAGO, schedule_day="mon", run_hour=9, log_dir=str(tmp_path))
        base.update(kw)
        return mk_config(**base)

    def test_no_marker_no_catch_up(self, tmp_path):
        assert needs_catch_up(self.cfg(tmp_path), NOW) is False

    def test_stale_marker_triggers(self, tmp_path):
        # Missed Monday slot, its week window is still the current window
        cfg = self.cfg(tmp_path)
        write_marker(cfg, aware(2026, 8, 16, 9, 5, tz=CHICAGO), "success")
        assert needs_catch_up(cfg, NOW) is True

    def test_fresh_marker_does_not_trigger(self, tmp_path):
        cfg = self.cfg(tmp_path)
        write_marker(cfg, aware(2026, 8, 24, 9, 5, tz=CHICAGO), "success")
        assert needs_catch_up(cfg, NOW) is False

    def test_restart_before_slot_never_double_posts(self, tmp_path):
        # Restart Monday 08:00 with today's 09:00 fire still pending. The
        # missed slot is LAST Monday whose window has passed, so no catch up.
        cfg = self.cfg(tmp_path)
        write_marker(cfg, aware(2026, 8, 10, 9, 5, tz=CHICAGO), "success")
        monday_early = aware(2026, 8, 24, 8, 0, tz=CHICAGO)
        assert needs_catch_up(cfg, monday_early) is False

    def test_daily_schedule_week_range_defers_to_next_fire(self, tmp_path):
        # DAILY cadence posting a WEEK window. Tomorrow's fire covers the
        # same week, so a catch up would duplicate it.
        from calendarr.config import CalendarRange, ScheduleType

        cfg = self.cfg(tmp_path, schedule_type=ScheduleType.DAILY, calendar_range=CalendarRange.WEEK)
        write_marker(cfg, aware(2026, 8, 23, 9, 5, tz=CHICAGO), "success")
        tuesday_early = aware(2026, 8, 25, 8, 0, tz=CHICAGO)
        assert needs_catch_up(cfg, tuesday_early) is False

    def test_stale_window_skipped(self, tmp_path):
        # Sunday slot with Monday start weeks, the missed window already ended
        cfg = self.cfg(tmp_path, schedule_day="sun")
        write_marker(cfg, aware(2026, 8, 1, 9, 5, tz=CHICAGO), "success")
        assert needs_catch_up(cfg, NOW) is False

    def test_marker_round_trip(self, tmp_path):
        cfg = self.cfg(tmp_path)
        stamp = aware(2026, 8, 23, 9, 5, tz=CHICAGO)
        write_marker(cfg, stamp, "success")
        marker = read_marker(cfg)
        assert isinstance(marker, datetime)
        assert marker == stamp
