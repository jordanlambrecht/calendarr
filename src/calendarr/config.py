# src/calendarr/config.py
"""Environment configuration. Loads once at startup, fails fast on bad input."""

import json
import logging
import os
from dataclasses import dataclass, field
from enum import StrEnum
from urllib.parse import urlparse
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

logger = logging.getLogger("config")

TRUTHY = ("true", "yes", "1", "y")


class ScheduleType(StrEnum):
    DAILY = "DAILY"
    WEEKLY = "WEEKLY"


class CalendarRange(StrEnum):
    DAY = "DAY"
    WEEK = "WEEK"
    AUTO = "AUTO"


class PastEventHandling(StrEnum):
    DISPLAY = "DISPLAY"
    HIDE = "HIDE"
    STRIKE = "STRIKE"


class EventType(StrEnum):
    TV = "tv"
    MOVIE = "movie"


# Documented contract is 0=Sunday. APScheduler wants day names, so numbers
# are remapped here and never passed through raw.
SUNDAY_FIRST_DAYS = ["sun", "mon", "tue", "wed", "thu", "fri", "sat"]
DAY_NAMES = {
    "sun": "sun",
    "sunday": "sun",
    "mon": "mon",
    "monday": "mon",
    "tue": "tue",
    "tuesday": "tue",
    "wed": "wed",
    "wednesday": "wed",
    "thu": "thu",
    "thursday": "thu",
    "fri": "fri",
    "friday": "fri",
    "sat": "sat",
    "saturday": "sat",
}
DAY_LABELS = {
    "sun": "Sunday",
    "mon": "Monday",
    "tue": "Tuesday",
    "wed": "Wednesday",
    "thu": "Thursday",
    "fri": "Friday",
    "sat": "Saturday",
}


def env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in TRUTHY


def env_int(name: str, default: int, minimum: int = 1) -> int:
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        value = int(raw)
    except ValueError:
        logger.warning("%s=%r is not an integer, using default %s", name, raw, default)
        return default
    if value < minimum:
        logger.warning("%s=%s below minimum %s, using default %s", name, value, minimum, default)
        return default
    return value


def parse_schedule_day(raw: str) -> str:
    """Resolve SCHEDULE_DAY to an APScheduler day name. Accepts names and
    legacy numbers under the documented Sunday=0 mapping."""
    cleaned = raw.strip().lower()
    if cleaned in DAY_NAMES:
        return DAY_NAMES[cleaned]
    try:
        num = int(cleaned)
    except ValueError:
        raise ValueError(f"SCHEDULE_DAY {raw!r} is not a day name or number 0-6") from None
    if not 0 <= num <= 6:
        raise ValueError(f"SCHEDULE_DAY {num} out of range 0-6 (0=Sunday)")
    return SUNDAY_FIRST_DAYS[num]


def parse_run_time(raw: str) -> tuple[int, int]:
    try:
        hour, minute = (int(p) for p in raw.strip().split(":"))
    except ValueError:
        raise ValueError(f"RUN_TIME {raw!r} must be HH:MM") from None
    if not (0 <= hour < 24 and 0 <= minute < 60):
        raise ValueError(f"RUN_TIME {raw!r} out of range")
    return hour, minute


@dataclass(frozen=True)
class CalendarSource:
    url: str
    type: EventType

    @property
    def display_name(self) -> str:
        """Hostname only, never leaks apikey query params into messages."""
        return urlparse(self.url).netloc or self.url


def parse_calendar_urls(raw: str) -> list[CalendarSource]:
    if not raw.strip():
        return []
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(f"CALENDAR_URLS is not valid JSON ({e})") from None
    if not isinstance(data, list):
        raise ValueError("CALENDAR_URLS must be a JSON array")
    sources = []
    for i, entry in enumerate(data):
        if not isinstance(entry, dict) or not entry.get("url"):
            logger.warning("Skipping CALENDAR_URLS entry %s, missing url", i)
            continue
        type_raw = str(entry.get("type", "tv")).lower()
        try:
            ev_type = EventType(type_raw)
        except ValueError:
            raise ValueError(f"CALENDAR_URLS entry {i} has invalid type {type_raw!r}, use tv or movie") from None
        sources.append(CalendarSource(url=entry["url"], type=ev_type))
    return sources


@dataclass
class Config:
    # Platforms
    use_discord: bool = True
    use_slack: bool = False
    discord_webhook_url: str = ""
    slack_webhook_url: str = ""
    discord_mention_role_id: str = ""
    discord_hide_mention_instructions: bool = False
    enable_custom_discord_footer: bool = False
    enable_custom_slack_footer: bool = False

    # Calendars and display
    calendar_urls: list[CalendarSource] = field(default_factory=list)
    custom_header: str = "New Releases"
    show_date_range: bool = True
    show_timezone_in_subheader: bool = False
    start_week_on_monday: bool = True
    deduplicate_events: bool = True
    passed_event_handling: PastEventHandling = PastEventHandling.DISPLAY
    calendar_range: CalendarRange = CalendarRange.WEEK

    # Time display
    display_time: bool = True
    use_24_hour: bool = True
    add_leading_zero: bool = True

    # Schedule
    schedule_type: ScheduleType = ScheduleType.WEEKLY
    run_hour: int = 9
    run_minute: int = 0
    schedule_day: str = "mon"
    cron_schedule: str = ""
    run_on_startup: bool = False

    # Runtime
    timezone: str = "UTC"
    http_timeout: int = 30
    log_dir: str = "/app/logs"
    log_file: str = "calendarr.log"
    log_max_size_mb: int = 1
    log_backup_count: int = 15
    debug: bool = False

    @property
    def tz(self) -> ZoneInfo:
        return ZoneInfo(self.timezone)

    @property
    def sources_label(self) -> str:
        return f"{len(self.calendar_urls)} calendars"


def load_config() -> Config:
    """Build Config from environment. Raises ValueError listing every problem."""
    errors: list[str] = []

    def fail(msg: str) -> None:
        errors.append(msg)

    use_discord = env_bool("USE_DISCORD", True)
    use_slack = env_bool("USE_SLACK", False)
    discord_webhook_url = os.environ.get("DISCORD_WEBHOOK_URL", "")
    slack_webhook_url = os.environ.get("SLACK_WEBHOOK_URL", "")

    if not use_discord and not use_slack:
        fail("At least one of USE_DISCORD or USE_SLACK must be true")
    if use_discord and not discord_webhook_url:
        fail("DISCORD_WEBHOOK_URL is required when USE_DISCORD is true")
    if use_slack and not slack_webhook_url:
        fail("SLACK_WEBHOOK_URL is required when USE_SLACK is true")

    # Legacy fallback kept from v1.x
    role_id = os.environ.get("DISCORD_MENTION_ROLE_ID") or os.environ.get("MENTION_ROLE_ID", "")

    try:
        calendar_urls = parse_calendar_urls(os.environ.get("CALENDAR_URLS", "[]"))
    except ValueError as e:
        calendar_urls = []
        fail(str(e))
    if not calendar_urls and not errors:
        logger.warning("No calendar URLs configured, every run will be empty")

    timezone = os.environ.get("TZ", "UTC")
    try:
        ZoneInfo(timezone)
    except (ZoneInfoNotFoundError, ValueError):
        fail(f"Unknown timezone {timezone!r}")

    try:
        schedule_type = ScheduleType(os.environ.get("SCHEDULE_TYPE", "WEEKLY").upper())
    except ValueError:
        schedule_type = ScheduleType.WEEKLY
        fail("SCHEDULE_TYPE must be DAILY or WEEKLY")

    try:
        run_hour, run_minute = parse_run_time(os.environ.get("RUN_TIME", "09:00"))
    except ValueError as e:
        run_hour, run_minute = 9, 0
        fail(str(e))

    try:
        schedule_day = parse_schedule_day(os.environ.get("SCHEDULE_DAY", "1"))
    except ValueError as e:
        schedule_day = "mon"
        fail(str(e))

    try:
        passed = PastEventHandling(os.environ.get("PASSED_EVENT_HANDLING", "DISPLAY").upper())
    except ValueError:
        passed = PastEventHandling.DISPLAY
        fail("PASSED_EVENT_HANDLING must be DISPLAY, HIDE, or STRIKE")

    try:
        cal_range = CalendarRange(os.environ.get("CALENDAR_RANGE", "AUTO").upper())
    except ValueError:
        cal_range = CalendarRange.AUTO
        fail("CALENDAR_RANGE must be AUTO, DAY, or WEEK")
    if cal_range is CalendarRange.AUTO:
        cal_range = CalendarRange.DAY if schedule_type is ScheduleType.DAILY else CalendarRange.WEEK

    if errors:
        raise ValueError("Invalid configuration. " + " | ".join(errors))

    # LOG_MAX_SIZE_MB is the documented name, MAX_LOG_SIZE the legacy one
    log_max = env_int("LOG_MAX_SIZE_MB", env_int("MAX_LOG_SIZE", 1))

    config = Config(
        use_discord=use_discord,
        use_slack=use_slack,
        discord_webhook_url=discord_webhook_url,
        slack_webhook_url=slack_webhook_url,
        discord_mention_role_id=role_id,
        discord_hide_mention_instructions=env_bool("DISCORD_HIDE_MENTION_INSTRUCTIONS", False),
        enable_custom_discord_footer=env_bool("ENABLE_CUSTOM_DISCORD_FOOTER", False),
        enable_custom_slack_footer=env_bool("ENABLE_CUSTOM_SLACK_FOOTER", False),
        calendar_urls=calendar_urls,
        custom_header=os.environ.get("CUSTOM_HEADER", "New Releases"),
        show_date_range=env_bool("SHOW_DATE_RANGE", True),
        show_timezone_in_subheader=env_bool("SHOW_TIMEZONE_IN_SUBHEADER", False),
        start_week_on_monday=env_bool("START_WEEK_ON_MONDAY", True),
        deduplicate_events=env_bool("DEDUPLICATE_EVENTS", True),
        passed_event_handling=passed,
        calendar_range=cal_range,
        display_time=env_bool("DISPLAY_TIME", True),
        use_24_hour=env_bool("USE_24_HOUR", True),
        add_leading_zero=env_bool("ADD_LEADING_ZERO", True),
        schedule_type=schedule_type,
        run_hour=run_hour,
        run_minute=run_minute,
        schedule_day=schedule_day,
        cron_schedule=os.environ.get("CRON_SCHEDULE", "").strip(),
        run_on_startup=env_bool("RUN_ON_STARTUP", False),
        timezone=timezone,
        http_timeout=env_int("HTTP_TIMEOUT", 30),
        log_dir=os.environ.get("LOG_DIR", "/app/logs"),
        log_file=os.environ.get("LOG_FILE", "calendarr.log"),
        log_max_size_mb=log_max,
        log_backup_count=env_int("LOG_BACKUP_COUNT", 15),
        debug=env_bool("DEBUG", False),
    )
    logger.info(
        "Config loaded, %s, schedule %s %s at %02d:%02d (%s)",
        config.sources_label,
        config.schedule_type.value,
        DAY_LABELS[config.schedule_day] if config.schedule_type is ScheduleType.WEEKLY else "",
        config.run_hour,
        config.run_minute,
        config.timezone,
    )
    return config
