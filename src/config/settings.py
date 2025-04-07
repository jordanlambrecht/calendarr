#!/usr/bin/env python3
# src/config/settings.py

import json
import logging
import os
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import pytz

logger = logging.getLogger("calendar")

# Valid options with defaults
DEFAULT_PASSED_EVENT_HANDLING = "DISPLAY"
VALID_PASSED_EVENT_HANDLING = ["DISPLAY", "HIDE", "STRIKE"]

DEFAULT_CALENDAR_RANGE = "WEEK"
VALID_CALENDAR_RANGE = ["DAY", "WEEK", "AUTO"]

DEFAULT_HEADER = "TV Guide"
DEFAULT_SCHEDULE_TYPE = "WEEKLY"
DEFAULT_RUN_TIME = "09:00"
DEFAULT_SCHEDULE_DAY = "1"  # Monday

# Logging settings default
DEFAULT_LOG_DIR = "/app/logs"
DEFAULT_LOG_FILE = "calendar.log"
DEFAULT_LOG_BACKUP_COUNT = 15
DEFAULT_LOG_MAX_SIZE_MB = 1

# HTTP timeouts
DEFAULT_HTTP_TIMEOUT = 30  # seconds


@dataclass
class CalendarUrl:
    """Represents a calendar URL with its type"""
    
    url: str
    type: str  # "tv" or "movie"
    
    @classmethod
    def from_dict(cls, data: Dict[str, str]) -> 'CalendarUrl':
        """
        Create a CalendarUrl from a dictionary
        
        Args:
            data: Dictionary with URL data
            
        Returns:
            CalendarUrl instance
        """
        return cls(
            url=data.get("url", ""),
            type=data.get("type", "tv")
        )
    
    def to_dict(self) -> Dict[str, str]:
        """
        Convert to dictionary
        
        Returns:
            Dictionary representation
        """
        return {
            "url": self.url,
            "type": self.type
        }


@dataclass
class TimeSettings:
    """Time display settings"""
    
    use_24_hour: bool = False
    add_leading_zero: bool = True
    display_time: bool = True


@dataclass
class ScheduleSettings:
    """Application scheduling settings"""
    
    schedule_type: str = DEFAULT_SCHEDULE_TYPE
    run_time: str = DEFAULT_RUN_TIME 
    hour: int = field(init=False)
    minute: int = field(init=False)
    schedule_day: str = DEFAULT_SCHEDULE_DAY
    cron_schedule: Optional[str] = None
    run_on_startup: bool = False
    
    def __post_init__(self):
        """Parse hour and minute from run_time"""
        try:
            self.hour, self.minute = map(int, self.run_time.split(":"))
        except (ValueError, TypeError):
            logger.warning(f"Invalid RUN_TIME format: {self.run_time}, using default")
            self.hour, self.minute = map(int, DEFAULT_RUN_TIME.split(":"))


@dataclass
class LoggingSettings:
    """Application logging settings"""
    
    log_dir: str = DEFAULT_LOG_DIR
    log_file: str = DEFAULT_LOG_FILE
    backup_count: int = DEFAULT_LOG_BACKUP_COUNT
    max_size_mb: int = DEFAULT_LOG_MAX_SIZE_MB
    debug_mode: bool = False


@dataclass
class Config:
    """Application configuration"""
    
    # Webhook settings
    discord_webhook_url: Optional[str] = None
    slack_webhook_url: Optional[str] = None
    use_discord: bool = True
    use_slack: bool = False
    
    # Display settings
    custom_header: str = DEFAULT_HEADER
    show_date_range: bool = True
    start_week_on_monday: bool = True
    
    # Calendar settings
    calendar_urls: List[CalendarUrl] = field(default_factory=list)
    passed_event_handling: str = DEFAULT_PASSED_EVENT_HANDLING
    calendar_range: str = DEFAULT_CALENDAR_RANGE
    
    # Time settings
    time_settings: TimeSettings = field(default_factory=TimeSettings)
    
    # Scheduling settings
    schedule_settings: ScheduleSettings = field(default_factory=ScheduleSettings)
    
    # Logging settings
    logging_settings: LoggingSettings = field(default_factory=LoggingSettings)
    
    # Timezone
    timezone: str = "UTC"
    
    # HTTP settings
    http_timeout: int = DEFAULT_HTTP_TIMEOUT
    
    @property
    def timezone_obj(self) -> pytz.timezone:
        """
        Get timezone object
        
        Returns:
            Timezone object
        """
        return pytz.timezone(self.timezone)
    
    @property
    def enabled_platforms(self) -> List[str]:
        """
        Get list of enabled platforms
        
        Returns:
            List of platform names
        """
        platforms = []
        if self.use_discord:
            platforms.append("discord")
        if self.use_slack:
            platforms.append("slack")
        return platforms
    
    def validate(self) -> List[str]:
        """
        Validate configuration
        
        Returns:
            List of error messages, empty if valid
        """
        errors = []
        
        # Validate webhook configuration
        if not self.use_discord and not self.use_slack:
            errors.append("At least one messaging platform must be enabled")

        if self.use_discord and not self.discord_webhook_url:
            errors.append("DISCORD_WEBHOOK_URL is required when USE_DISCORD is true")
            
        if self.use_slack and not self.slack_webhook_url:
            errors.append("SLACK_WEBHOOK_URL is required when USE_SLACK is true")
        
        # Validate the passed event handling option
        if self.passed_event_handling not in VALID_PASSED_EVENT_HANDLING:
            errors.append(f"Invalid PASSED_EVENT_HANDLING value: {self.passed_event_handling}, "
                         f"must be one of {VALID_PASSED_EVENT_HANDLING}")
        
        # Validate calendar range
        if self.calendar_range not in VALID_CALENDAR_RANGE:
            errors.append(f"Invalid CALENDAR_RANGE value: {self.calendar_range}, "
                         f"must be one of {VALID_CALENDAR_RANGE}")
        
        return errors


def load_calendar_urls(urls_str: str) -> List[CalendarUrl]:
    """
    Parse calendar URLs from environment variable
    
    Args:
        urls_str: JSON string of calendar URLs
        
    Returns:
        List of CalendarUrl objects
    """
    try:
        urls_data = json.loads(urls_str)
        urls = [CalendarUrl.from_dict(url_data) for url_data in urls_data]
        logger.info(f"✅ Successfully loaded CALENDAR_URLS: {len(urls)} calendars")
        return urls
    except json.JSONDecodeError as e:
        logger.error(f"ERROR: CALENDAR_URLS is not valid JSON: {urls_str}")
        logger.error(f"Error details: {str(e)}")
        return []


def get_env_bool(name: str, default: bool = False) -> bool:
    """
    Get boolean value from environment variable
    
    Args:
        name: Environment variable name
        default: Default value if not found
        
    Returns:
        Boolean value
    """
    value = os.environ.get(name, str(default)).lower()
    return value in ('true', 'yes', '1', 'y')


def get_env_int(name: str, default: int) -> int:
    """
    Get integer value from environment variable
    
    Args:
        name: Environment variable name
        default: Default value if not found
        
    Returns:
        Integer value
    """
    try:
        return int(os.environ.get(name, str(default)))
    except (ValueError, TypeError):
        return default


def load_config_from_env() -> Config:
    """
    Load configuration from environment variables
    
    Returns:
        Config object
    """
    # Load calendar URLs
    calendar_urls_str = os.environ.get("CALENDAR_URLS", "[]")
    calendar_urls = load_calendar_urls(calendar_urls_str)
    
    # Load time settings
    time_settings = TimeSettings(
        use_24_hour=get_env_bool("USE_24_HOUR", False),
        add_leading_zero=get_env_bool("ADD_LEADING_ZERO", True),
        display_time=get_env_bool("DISPLAY_TIME", True)
    )
    
    # Load scheduling settings
    schedule_settings = ScheduleSettings(
        schedule_type=os.environ.get("SCHEDULE_TYPE", DEFAULT_SCHEDULE_TYPE).upper(),
        run_time=os.environ.get("RUN_TIME", DEFAULT_RUN_TIME),
        schedule_day=os.environ.get("SCHEDULE_DAY", DEFAULT_SCHEDULE_DAY),
        cron_schedule=os.environ.get("CRON_SCHEDULE"),
        run_on_startup=get_env_bool("RUN_ON_STARTUP", False)
    )
    
    # Load logging settings
    logging_settings = LoggingSettings(
        log_dir=os.environ.get("LOG_DIR", DEFAULT_LOG_DIR),
        log_file=os.environ.get("LOG_FILE", DEFAULT_LOG_FILE),
        backup_count=get_env_int("LOG_BACKUP_COUNT", DEFAULT_LOG_BACKUP_COUNT),
        max_size_mb=get_env_int("MAX_LOG_SIZE", DEFAULT_LOG_MAX_SIZE_MB),
        debug_mode=get_env_bool("DEBUG", False)
    )
    
    # Create config object
    config = Config(
        discord_webhook_url=os.environ.get("DISCORD_WEBHOOK_URL"),
        slack_webhook_url=os.environ.get("SLACK_WEBHOOK_URL"),
        use_discord=get_env_bool("USE_DISCORD", True),
        use_slack=get_env_bool("USE_SLACK", False),
        custom_header=os.environ.get("CUSTOM_HEADER", DEFAULT_HEADER),
        show_date_range=get_env_bool("SHOW_DATE_RANGE", True),
        start_week_on_monday=get_env_bool("START_WEEK_ON_MONDAY", True),
        calendar_urls=calendar_urls,
        passed_event_handling=os.environ.get("PASSED_EVENT_HANDLING", DEFAULT_PASSED_EVENT_HANDLING).upper(),
        calendar_range=os.environ.get("CALENDAR_RANGE", DEFAULT_CALENDAR_RANGE).upper(),
        time_settings=time_settings,
        schedule_settings=schedule_settings,
        logging_settings=logging_settings,
        timezone=os.environ.get("TZ", "UTC"),
        http_timeout=get_env_int("HTTP_TIMEOUT", DEFAULT_HTTP_TIMEOUT)
    )
    
    # Handle AUTO setting - convert to DAY or WEEK based on SCHEDULE_TYPE
    if config.calendar_range == "AUTO":
        if config.schedule_settings.schedule_type == "DAILY":
            config.calendar_range = "DAY"
        else:
            config.calendar_range = "WEEK"
    
    # Validate the passed event handling option
    if config.passed_event_handling not in VALID_PASSED_EVENT_HANDLING:
        logger.warning(f"Invalid PASSED_EVENT_HANDLING value: {config.passed_event_handling}, "
                      f"defaulting to {DEFAULT_PASSED_EVENT_HANDLING}")
        config.passed_event_handling = DEFAULT_PASSED_EVENT_HANDLING
    
    # Validate configuration
    errors = config.validate()
    if errors:
        for error in errors:
            logger.error(f"Configuration error: {error}")
        raise ValueError(f"Invalid configuration: {', '.join(errors)}")
    
    return config