# src/calendarr/domain.py
"""Core data types shared by ingest, report, and render."""

import re
from dataclasses import dataclass, field
from datetime import date, datetime

from calendarr.config import CalendarSource, EventType

PREMIERE_PATTERN = re.compile(r"[-\s](?:s\d+e0*1|(?:\d+x0*1))\b", re.IGNORECASE)
EPISODE_PATTERN = re.compile(r"^(S?\d{1,4}[Ex]\d{1,4})$", re.IGNORECASE)
SPLIT_PATTERN = re.compile(r"\s+-\s+")


@dataclass(frozen=True)
class Event:
    """One calendar entry, timezone aware."""

    summary: str
    start_time: datetime
    source_type: EventType

    @property
    def is_premiere(self) -> bool:
        return bool(PREMIERE_PATTERN.search(self.summary))

    @property
    def key(self) -> tuple[str, date]:
        """Dedup identity, same title on the same day is the same event."""
        return (self.summary, self.start_time.date())


@dataclass(frozen=True)
class EventLine:
    """Display ready event with parsed name parts."""

    summary: str
    source_type: EventType
    is_premiere: bool = False
    is_past: bool = False
    time_str: str = ""
    show_name: str = ""
    episode_number: str = ""
    episode_title: str = ""


@dataclass
class DayReport:
    date: date
    tv: list[EventLine] = field(default_factory=list)
    movies: list[EventLine] = field(default_factory=list)

    @property
    def title(self) -> str:
        return self.date.strftime("%A, %b %d")

    @property
    def weekday(self) -> str:
        return self.date.strftime("%A")

    @property
    def total(self) -> int:
        return len(self.tv) + len(self.movies)


@dataclass(frozen=True)
class SourceError:
    source: CalendarSource
    error: str


@dataclass
class Report:
    """Everything one run produces, ready to render."""

    days: list[DayReport]
    start: datetime
    end: datetime
    tv_count: int = 0
    movie_count: int = 0
    premiere_count: int = 0
    deduplicated: int = 0
    skipped_past: int = 0
    source_errors: list[SourceError] = field(default_factory=list)
    all_sources_failed: bool = False

    @property
    def total_events(self) -> int:
        return self.tv_count + self.movie_count

    @property
    def is_daily(self) -> bool:
        return (self.end - self.start).days <= 1
