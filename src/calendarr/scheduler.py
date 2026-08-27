# src/calendarr/scheduler.py
"""APScheduler setup with explicit timezone, generous misfire grace, and
a last-run marker enabling catch-up after container downtime."""

import json
import logging
import os
from datetime import datetime, timedelta

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from calendarr.config import Config, ScheduleType
from calendarr.report import calculate_range

logger = logging.getLogger("scheduler")

MISFIRE_GRACE_SECONDS = 3600
MARKER_FILE = "last_run.json"

# APScheduler day names to python weekday numbers
DAY_TO_WEEKDAY = {"mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5, "sun": 6}


def build_trigger(config: Config) -> CronTrigger:
    if config.cron_schedule:
        logger.info("Using custom cron schedule %r", config.cron_schedule)
        return CronTrigger.from_crontab(config.cron_schedule, timezone=config.tz)
    if config.schedule_type is ScheduleType.DAILY:
        return CronTrigger(hour=config.run_hour, minute=config.run_minute, timezone=config.tz)
    return CronTrigger(
        day_of_week=config.schedule_day, hour=config.run_hour, minute=config.run_minute, timezone=config.tz
    )


def create_scheduler(config: Config, job) -> BackgroundScheduler:
    scheduler = BackgroundScheduler(
        timezone=config.tz,
        job_defaults={"misfire_grace_time": MISFIRE_GRACE_SECONDS, "coalesce": True, "max_instances": 1},
    )
    scheduler.add_job(job, build_trigger(config), id="main_job")
    return scheduler


def marker_path(config: Config) -> str:
    return os.path.join(config.log_dir, MARKER_FILE)


def read_marker(config: Config) -> datetime | None:
    try:
        with open(marker_path(config), encoding="utf-8") as f:
            return datetime.fromisoformat(json.load(f)["completed_at"])
    except (OSError, ValueError, KeyError):
        return None


def write_marker(config: Config, completed_at: datetime, outcome: str) -> None:
    try:
        with open(marker_path(config), "w", encoding="utf-8") as f:
            json.dump({"completed_at": completed_at.isoformat(), "outcome": outcome}, f)
    except OSError as e:
        logger.warning("Could not write run marker (%s)", e)


def last_scheduled_before(config: Config, now: datetime) -> datetime | None:
    """Most recent scheduled fire time at or before now. None for custom cron."""
    if config.cron_schedule:
        return None
    local_now = now.astimezone(config.tz)
    candidate = local_now.replace(hour=config.run_hour, minute=config.run_minute, second=0, microsecond=0)
    if config.schedule_type is ScheduleType.DAILY:
        if candidate > local_now:
            candidate -= timedelta(days=1)
        return candidate
    target = DAY_TO_WEEKDAY[config.schedule_day]
    candidate -= timedelta(days=(candidate.weekday() - target) % 7)
    if candidate > local_now:
        candidate -= timedelta(days=7)
    return candidate


def needs_catch_up(config: Config, now: datetime) -> bool:
    """True when the last completed run predates the most recent scheduled fire.
    First start with no marker does not catch up."""
    marker = read_marker(config)
    if marker is None:
        return False
    expected = last_scheduled_before(config, now)
    if expected is None or marker >= expected:
        return False
    # Catch up only when the missed slot would post the same window a run
    # right now would post, and the upcoming regular fire will not cover
    # that window anyway. Anything else is stale content or a double post.
    if calculate_range(config, expected) != calculate_range(config, now):
        logger.info("Missed run at %s skipped, its window has passed", expected)
        return False
    step = timedelta(days=1) if config.schedule_type is ScheduleType.DAILY else timedelta(days=7)
    if calculate_range(config, expected + step) == calculate_range(config, now):
        logger.info("Missed run at %s skipped, the next fire covers the same window", expected)
        return False
    logger.info("Missed run detected, last completed %s, expected %s", marker, expected)
    return True
