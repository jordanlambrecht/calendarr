# tests/test_report.py
"""Report building, the pure pipeline core."""

from calendarr.config import CalendarRange, EventType, PastEventHandling
from calendarr.ingest import FetchResult
from calendarr.report import build_report, calculate_range, format_time
from conftest import CHICAGO, aware, mk_config, mk_event, tv_source

# Thursday morning in Chicago
NOW = aware(2026, 8, 27, 10, 0, tz=CHICAGO)


class TestCalculateRange:
    def test_week_monday_start(self):
        start, end = calculate_range(mk_config(timezone=CHICAGO), NOW)
        assert start == aware(2026, 8, 24, tz=CHICAGO)
        assert end == aware(2026, 8, 31, tz=CHICAGO)

    def test_week_sunday_start(self):
        cfg = mk_config(timezone=CHICAGO, start_week_on_monday=False)
        start, end = calculate_range(cfg, NOW)
        assert start == aware(2026, 8, 23, tz=CHICAGO)
        assert end == aware(2026, 8, 30, tz=CHICAGO)

    def test_day_mode(self):
        cfg = mk_config(timezone=CHICAGO, calendar_range=CalendarRange.DAY)
        start, end = calculate_range(cfg, NOW)
        assert start == aware(2026, 8, 27, tz=CHICAGO)
        assert end == aware(2026, 8, 28, tz=CHICAGO)


class TestFormatTime:
    def test_24_hour(self):
        assert format_time(9, 5, mk_config()) == "09:05"

    def test_12_hour_midnight(self):
        cfg = mk_config(use_24_hour=False)
        assert format_time(0, 5, cfg) == "12:05 AM"

    def test_12_hour_no_leading_zero(self):
        cfg = mk_config(use_24_hour=False, add_leading_zero=False)
        assert format_time(15, 30, cfg) == "3:30 PM"


def report_for(events, config=None, errors=(), sources_failed=0):
    cfg = config or mk_config()
    results = [FetchResult(source=tv_source(), events=list(events))]
    for i in range(sources_failed):
        results.append(FetchResult(source=tv_source(f"http://dead{i}/cal.ics"), error="fetch failed"))
    start, end = aware(2026, 8, 24), aware(2026, 8, 31)
    return build_report(cfg, results, start, end, NOW)


class TestBuildReport:
    def test_groups_and_sorts_days(self):
        events = [
            mk_event("B Show - S01E02", aware(2026, 8, 29, 20)),
            mk_event("A Movie", aware(2026, 8, 28), EventType.MOVIE),
        ]
        report = report_for(events)
        assert [d.date.day for d in report.days] == [28, 29]
        assert report.tv_count == 1 and report.movie_count == 1

    def test_stats_count_after_dedup(self):
        # Was register defect 15, header counts now match the body
        events = [
            mk_event("Show - S01E01", aware(2026, 8, 29, 20)),
            mk_event("Show - S01E01", aware(2026, 8, 29, 9)),
        ]
        report = report_for(events)
        assert report.tv_count == 1
        assert report.deduplicated == 1
        assert report.days[0].tv[0].time_str.startswith("09")

    def test_dedup_disabled(self):
        events = [
            mk_event("Show - S01E01", aware(2026, 8, 29, 20)),
            mk_event("Show - S01E01", aware(2026, 8, 29, 9)),
        ]
        report = report_for(events, config=mk_config(deduplicate_events=False))
        assert report.tv_count == 2

    def test_hide_past_events(self):
        events = [
            mk_event("Old - S01E01", aware(2026, 8, 25, 9)),
            mk_event("New - S01E02", aware(2026, 8, 29, 9)),
        ]
        cfg = mk_config(passed_event_handling=PastEventHandling.HIDE)
        report = report_for(events, config=cfg)
        assert report.tv_count == 1
        assert report.skipped_past == 1

    def test_premieres_counted_from_shown_lines(self):
        events = [mk_event("Show - S05E01 - Return", aware(2026, 8, 29, 20))]
        assert report_for(events).premiere_count == 1

    def test_episode_split(self):
        events = [mk_event("Show Name - S01E05 - Sub - Title", aware(2026, 8, 29, 20))]
        line = report_for(events).days[0].tv[0]
        assert line.show_name == "Show Name"
        assert line.episode_number == "S01E05"
        assert line.episode_title == "Sub - Title"

    def test_partial_failure_reported(self):
        report = report_for([mk_event("Show - S01E01", aware(2026, 8, 29, 20))], sources_failed=1)
        assert len(report.source_errors) == 1
        assert report.all_sources_failed is False

    def test_all_sources_failed(self):
        cfg = mk_config()
        results = [FetchResult(source=tv_source(), error="fetch failed")]
        report = build_report(cfg, results, aware(2026, 8, 24), aware(2026, 8, 31), NOW)
        assert report.all_sources_failed is True

    def test_timezone_conversion_to_local_day(self):
        # 01.00 UTC Thursday is Wednesday evening in Chicago
        cfg = mk_config(timezone=CHICAGO)
        events = [mk_event("Show - S01E01", aware(2026, 8, 27, 1, 0, tz="UTC"))]
        report = report_for(events, config=cfg)
        assert report.days[0].date.day == 26
