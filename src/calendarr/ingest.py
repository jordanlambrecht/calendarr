# src/calendarr/ingest.py
"""Fetch and parse calendar feeds. Failures are reported, never swallowed."""

import logging
import time
from dataclasses import dataclass, field
from datetime import date, datetime
from datetime import time as dtime

import icalendar
import recurring_ical_events
import requests

from calendarr.config import CalendarSource, Config
from calendarr.domain import Event

logger = logging.getLogger("ingest")

RETRY_DELAYS = (1, 3)


@dataclass
class FetchResult:
    source: CalendarSource
    events: list[Event] = field(default_factory=list)
    error: str = ""

    @property
    def ok(self) -> bool:
        return not self.error


def _get_with_retries(url: str, timeout: int) -> bytes:
    last_error: Exception | None = None
    for attempt, delay in enumerate((0,) + RETRY_DELAYS):
        if delay:
            time.sleep(delay)
        try:
            response = requests.get(url, timeout=timeout)
            response.raise_for_status()
            return response.content
        except requests.RequestException as e:
            last_error = e
            # Log the class only, exception text can embed the full URL with apikey
            logger.warning("Fetch attempt %s failed for %s (%s)", attempt + 1, url.split("?")[0], e.__class__.__name__)
    raise last_error  # type: ignore[misc]


def _to_event(ical_event, config: Config, source: CalendarSource) -> Event:
    dtstart = ical_event.get("DTSTART")
    if dtstart is None:
        raise ValueError("event has no DTSTART")
    start = dtstart.dt
    summary = str(ical_event.get("SUMMARY", "Untitled Event"))
    if not summary:
        raise ValueError("event has empty summary")

    if isinstance(start, datetime):
        if start.tzinfo is None:
            start = start.replace(tzinfo=config.tz)
        else:
            start = start.astimezone(config.tz)
    elif isinstance(start, date):
        start = datetime.combine(start, dtime.min, tzinfo=config.tz)
    else:
        raise ValueError(f"unexpected DTSTART type {type(start)!r}")

    return Event(summary=summary, start_time=start, source_type=source.type)


def fetch_source(source: CalendarSource, config: Config, start: datetime, end: datetime) -> FetchResult:
    """Fetch one feed and convert events inside [start, end)."""
    logger.info("Fetching %s feed from %s", source.type.value, source.display_name)
    try:
        body = _get_with_retries(source.url, config.http_timeout)
    except requests.RequestException as e:
        return FetchResult(source=source, error=f"fetch failed ({e.__class__.__name__})")

    try:
        calendar = icalendar.Calendar.from_ical(body)
        raw_events = recurring_ical_events.of(calendar).between(start, end)
    except Exception as e:
        return FetchResult(source=source, error=f"parse failed ({e})")

    events = []
    for raw in raw_events:
        try:
            event = _to_event(raw, config, source)
        except Exception as e:
            # Any malformed event is skipped, never allowed to kill the run
            logger.warning("Skipping invalid event from %s (%s: %s)", source.display_name, e.__class__.__name__, e)
            continue
        if start <= event.start_time < end:
            events.append(event)
        else:
            logger.debug("Dropping out of range event %s at %s", event.summary, event.start_time)
    logger.info("Parsed %s events from %s", len(events), source.display_name)
    return FetchResult(source=source, events=events)


def fetch_all(config: Config, start: datetime, end: datetime) -> list[FetchResult]:
    return [fetch_source(source, config, start, end) for source in config.calendar_urls]
