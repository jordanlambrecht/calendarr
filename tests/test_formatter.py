# tests/test_formatter.py
"""FormatterService grouping, dedup, and stats. Characterizes current behavior."""

from datetime import datetime, timedelta

import pytz

from config.settings import Config
from conftest import aware, mk_event
from services.formatter_service import FormatterService

UTC_NOW = datetime.now(pytz.UTC)


def svc(**overrides) -> FormatterService:
    return FormatterService(Config(timezone="UTC", **overrides))


class TestProcessEvents:
    def test_empty_input(self):
        days, stats = svc().process_events([], aware(2026, 8, 24), aware(2026, 8, 31))
        assert days == []
        # Defect 15 in the register, the zero event path emits different keys
        assert stats == {"tv_count": 0, "movie_count": 0, "premiere_count": 0}

    def test_groups_by_day_sorted(self):
        events = [
            mk_event("B Show - S01E02", aware(2026, 8, 26, 20)),
            mk_event("A Movie", aware(2026, 8, 25), source_type="movie"),
        ]
        days, stats = svc().process_events(events, aware(2026, 8, 24), aware(2026, 8, 31))
        assert len(days) == 2
        assert days[0].date < days[1].date
        assert days[0].movie_events and days[1].tv_events
        assert stats["total_tv"] == 1 and stats["total_movies"] == 1

    def test_dedup_keeps_earliest(self):
        events = [
            mk_event("Show - S01E01", aware(2026, 8, 26, 20)),
            mk_event("Show - S01E01", aware(2026, 8, 26, 9)),
        ]
        days, stats = svc().process_events(events, aware(2026, 8, 24), aware(2026, 8, 31))
        assert days[0].total_events == 1
        assert days[0].tv_events[0].time_str.startswith("09")
        assert stats["total_deduplicated"] == 1
        # Defect 15, header counts are taken before dedup
        assert stats["total_tv"] == 2

    def test_dedup_disabled(self):
        events = [
            mk_event("Show - S01E01", aware(2026, 8, 26, 20)),
            mk_event("Show - S01E01", aware(2026, 8, 26, 9)),
        ]
        days, _ = svc(deduplicate_events=False).process_events(events, aware(2026, 8, 24), aware(2026, 8, 31))
        assert days[0].total_events == 2

    def test_hide_skips_past_events(self):
        past = UTC_NOW - timedelta(days=1)
        future = UTC_NOW + timedelta(days=1)
        events = [
            mk_event("Old Show - S01E01", pytz.UTC.localize(past.replace(tzinfo=None))),
            mk_event("New Show - S01E02", pytz.UTC.localize(future.replace(tzinfo=None))),
        ]
        days, stats = svc(passed_event_handling="HIDE").process_events(
            events,
            pytz.UTC.localize(past.replace(tzinfo=None)),
            pytz.UTC.localize((future + timedelta(days=1)).replace(tzinfo=None)),
        )
        assert sum(d.total_events for d in days) == 1
        assert stats["total_skipped_past"] == 1

    def test_premiere_counted(self):
        events = [mk_event("Show - S05E01 - Return", aware(2026, 8, 26, 20))]
        _, stats = svc().process_events(events, aware(2026, 8, 24), aware(2026, 8, 31))
        assert stats["total_premieres"] == 1


class TestEpisodeSplitting:
    def test_full_split(self):
        item = svc()._create_event_item(mk_event("Show Name - S01E05 - The Title", aware(2026, 8, 26, 20)))
        assert item.show_name == "Show Name"
        assert item.episode_number == "S01E05"
        assert item.episode_title == "The Title"

    def test_no_episode_info(self):
        item = svc()._create_event_item(mk_event("Just A Show", aware(2026, 8, 26, 20)))
        assert item.show_name == "Just A Show"
        assert item.episode_number is None

    def test_title_with_dash(self):
        item = svc()._create_event_item(mk_event("Show - S01E05 - Sub - Title", aware(2026, 8, 26, 20)))
        assert item.episode_number == "S01E05"
        assert item.episode_title == "Sub - Title"

    def test_movie_not_split(self):
        item = svc()._create_event_item(mk_event("Epic Movie - The Sequel", aware(2026, 8, 26), source_type="movie"))
        assert item.show_name == "Epic Movie - The Sequel"
