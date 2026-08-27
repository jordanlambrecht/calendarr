# src/calendarr/report.py
"""Turn fetch results into a Report. Owns date math, dedup, filtering, and stats."""

import logging
from datetime import datetime, timedelta

from calendarr.config import CalendarRange, Config, EventType, PastEventHandling
from calendarr.domain import SPLIT_PATTERN, DayReport, Event, EventLine, Report, SourceError
from calendarr.ingest import FetchResult

logger = logging.getLogger("report")


def calculate_range(config: Config, now: datetime) -> tuple[datetime, datetime]:
    """Date window for a run. End is exclusive."""
    local_now = now.astimezone(config.tz)
    today = local_now.replace(hour=0, minute=0, second=0, microsecond=0)
    if config.calendar_range is CalendarRange.DAY:
        return today, today + timedelta(days=1)
    weekday = today.weekday()
    if config.start_week_on_monday:
        offset = weekday
    else:
        offset = 0 if weekday == 6 else weekday + 1
    start = today - timedelta(days=offset)
    return start, start + timedelta(days=7)


def format_time(hour: int, minute: int, config: Config) -> str:
    if config.use_24_hour:
        display, suffix = hour, ""
    elif hour == 0:
        display, suffix = 12, " AM"
    elif hour < 12:
        display, suffix = hour, " AM"
    elif hour == 12:
        display, suffix = 12, " PM"
    else:
        display, suffix = hour - 12, " PM"
    hour_str = f"{display:02d}" if config.add_leading_zero else str(display)
    return f"{hour_str}:{minute:02d}{suffix}"


def _split_tv_summary(summary: str) -> tuple[str, str, str]:
    """Sonarr summaries look like 'Show - S01E05 - Title'."""
    parts = SPLIT_PATTERN.split(summary, maxsplit=1)
    if len(parts) != 2:
        return summary, "", ""
    show, rest = parts
    sub = SPLIT_PATTERN.split(rest, maxsplit=1)
    if len(sub) == 2:
        return show, sub[0], sub[1]
    return show, rest, ""


def _to_line(event: Event, config: Config, now: datetime) -> EventLine:
    local = event.start_time.astimezone(config.tz)
    time_str = format_time(local.hour, local.minute, config) if config.display_time else ""
    show_name, number, title = (event.summary, "", "")
    if event.source_type is EventType.TV:
        show_name, number, title = _split_tv_summary(event.summary)
    return EventLine(
        summary=event.summary,
        source_type=event.source_type,
        is_premiere=event.is_premiere,
        is_past=event.start_time < now,
        time_str=time_str,
        show_name=show_name,
        episode_number=number,
        episode_title=title,
    )


def _deduplicate(events: list[Event]) -> tuple[list[Event], int]:
    unique: dict = {}
    for event in events:
        existing = unique.get(event.key)
        if existing is None or event.start_time < existing.start_time:
            unique[event.key] = event
    kept = list(unique.values())
    return kept, len(events) - len(kept)


def build_report(config: Config, results: list[FetchResult], start: datetime, end: datetime, now: datetime) -> Report:
    """Aggregate fetch results into the final Report. Stats count what is
    actually shown, after dedup and past-event filtering."""
    source_errors = [SourceError(source=r.source, error=r.error) for r in results if not r.ok]
    all_failed = bool(results) and len(source_errors) == len(results)

    events = [e for r in results for e in r.events]
    events.sort(key=lambda e: e.start_time)

    deduplicated = 0
    if config.deduplicate_events:
        events, deduplicated = _deduplicate(events)
        events.sort(key=lambda e: e.start_time)

    skipped_past = 0
    lines_by_day: dict = {}
    for event in events:
        line = _to_line(event, config, now)
        if line.is_past and config.passed_event_handling is PastEventHandling.HIDE:
            skipped_past += 1
            continue
        local_date = event.start_time.astimezone(config.tz).date()
        day = lines_by_day.setdefault(local_date, DayReport(date=local_date))
        (day.tv if event.source_type is EventType.TV else day.movies).append(line)

    days = [lines_by_day[d] for d in sorted(lines_by_day)]
    tv_count = sum(len(d.tv) for d in days)
    movie_count = sum(len(d.movies) for d in days)
    premiere_count = sum(1 for d in days for line in d.tv if line.is_premiere)

    for err in source_errors:
        logger.error("Source %s failed, %s", err.source.display_name, err.error)
    logger.info(
        "Report ready, %s tv, %s movies, %s premieres over %s days", tv_count, movie_count, premiere_count, len(days)
    )
    if deduplicated:
        logger.info("Removed %s duplicate events", deduplicated)
    if skipped_past:
        logger.info("Hid %s past events", skipped_past)

    return Report(
        days=days,
        start=start,
        end=end,
        tv_count=tv_count,
        movie_count=movie_count,
        premiere_count=premiere_count,
        deduplicated=deduplicated,
        skipped_past=skipped_past,
        source_errors=source_errors,
        all_sources_failed=all_failed,
    )
