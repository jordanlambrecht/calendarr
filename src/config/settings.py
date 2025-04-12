#!/usr/bin/env python3
# src/config/settings.py

import json
import logging
import os
import traceback
from dataclasses import dataclass, field
from typing import List, Dict, Optional
import pytz

from constants import (
    DEFAULT_ADD_LEADING_ZERO, DEFAULT_DEBUG_MODE, DEFAULT_DEDUPLICATE_EVENTS,
    DEFAULT_HTTP_TIMEOUT, DEFAULT_CALENDAR_RANGE, DEFAULT_PASSED_EVENT_HANDLING,
    DEFAULT_RUN_ON_STARTUP, DEFAULT_SHOW_DATE_RANGE, DEFAULT_START_WEEK_ON_MONDAY,
    DEFAULT_DISPLAY_TIME, DEFAULT_USE_24_HOUR, VALID_PASSED_EVENT_HANDLING,
    VALID_CALENDAR_RANGE, DEFAULT_HEADER, DEFAULT_SCHEDULE_TYPE, DEFAULT_RUN_TIME,
    DEFAULT_SCHEDULE_DAY, DEFAULT_LOG_DIR, DEFAULT_LOG_FILE, DEFAULT_LOG_BACKUP_COUNT, DEFAULT_DISCORD_MENTION_ROLE_ID,
    DEFAULT_LOG_MAX_SIZE_MB, DEFAULT_USE_SLACK, DEFAULT_USE_DISCORD,
    EVENT_TYPE_TV, EVENT_TYPE_MOVIE, VALID_EVENT_TYPES,
    DEFAULT_DISCORD_HIDE_MENTION_INSTRUCTIONS
)

logger = logging.getLogger("config")

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
        try:
            logger.debug(f"🔍  Creating CalendarUrl from dict: {data}")
            url = data.get("url", "")
            type_val = data.get("type", "tv")
            logger.debug(f"📋  Extracted url={url}, type={type_val}")
            
            if not url:
                logger.warning("Empty URL provided in calendar URL data")
                
            if type_val not in VALID_EVENT_TYPES:
                logger.warning(f"Unexpected calendar type: {type_val}, expected one of {VALID_EVENT_TYPES}")
                
            return cls(
                url=url,
                type=type_val
            )
        except Exception as e:
            logger.error(f"Error creating CalendarUrl from dict: {e}")
            logger.debug(f"❌  Exception details: {traceback.format_exc()}")
            return cls(url="", type=EVENT_TYPE_TV)
    
    def to_dict(self) -> Dict[str, str]:
        """
        Convert to dictionary
        
        Returns:
            Dictionary representation
        """
        try:
            logger.debug(f"🔄  Converting CalendarUrl to dict: url={self.url}, type={self.type}")
            result = {
                "url": self.url,
                "type": self.type
            }
            logger.debug(f"📋  CalendarUrl dict conversion result: {result}")
            return result
        except Exception as e:
            logger.error(f"Error converting CalendarUrl to dict: {e}")
            logger.debug(f"❌  Exception details: {traceback.format_exc()}")
            return {"url": "", "type": "tv"}


@dataclass
class TimeSettings:
    """Time display settings"""
    
    use_24_hour: bool = DEFAULT_USE_24_HOUR
    add_leading_zero: bool = DEFAULT_ADD_LEADING_ZERO
    display_time: bool = DEFAULT_DISPLAY_TIME
    
    def __post_init__(self):
        try:
            logger.debug(f"🔧  Initialized TimeSettings: use_24_hour={self.use_24_hour}, "
                         f"add_leading_zero={self.add_leading_zero}, display_time={self.display_time}")
        except Exception as e:
            logger.error(f"Error initializing TimeSettings: {e}")
            logger.debug(f"❌  Exception details: {traceback.format_exc()}")


@dataclass
class ScheduleSettings:
    """Application scheduling settings"""
    
    schedule_type: str = DEFAULT_SCHEDULE_TYPE
    run_time: str = DEFAULT_RUN_TIME 
    hour: int = field(init=False)
    minute: int = field(init=False)
    schedule_day: str = DEFAULT_SCHEDULE_DAY
    cron_schedule: Optional[str] = None
    run_on_startup: bool = DEFAULT_RUN_ON_STARTUP
    
    def __post_init__(self):
        """Parse hour and minute from run_time"""
        try:
            logger.debug(f"🔧  Initializing ScheduleSettings with run_time={self.run_time}, "
                         f"schedule_type={self.schedule_type}, schedule_day={self.schedule_day}")
            
            if not self.run_time:
                logger.warning("Empty run_time provided, using default")
                self.run_time = DEFAULT_RUN_TIME
                
            # Validate and sanitize schedule_type
            try:
                self.schedule_type = self.schedule_type.upper()
                logger.debug(f"🔄  Normalized schedule_type to {self.schedule_type}")
            except (AttributeError, TypeError):
                logger.warning(f"Invalid schedule_type: {self.schedule_type}, using default")
                self.schedule_type = DEFAULT_SCHEDULE_TYPE
                
            # Parse time components
            try:
                self.hour, self.minute = map(int, self.run_time.split(":"))
                logger.debug(f"📋  Parsed run_time to hour={self.hour}, minute={self.minute}")
                
                # Basic validation of hour and minute
                if not (0 <= self.hour < 24) or not (0 <= self.minute < 60):
                    raise ValueError(f"Invalid time values: hour={self.hour}, minute={self.minute}")
                    
            except (ValueError, TypeError, AttributeError) as e:
                logger.warning(f"Invalid RUN_TIME format: {self.run_time}, using default. Error: {e}")
                self.hour, self.minute = map(int, DEFAULT_RUN_TIME.split(":"))
                logger.debug(f"⚠️  Using default time: hour={self.hour}, minute={self.minute}")
                
            # Validate cron schedule if provided
            if self.cron_schedule:
                logger.debug(f"🧪  Cron schedule provided: {self.cron_schedule}")
                # Simple validation - just check if it has about like 5-6 components
                cron_parts = self.cron_schedule.split()
                if not (5 <= len(cron_parts) <= 6):
                    logger.warning(f"Suspicious cron format: {self.cron_schedule} - should have 5-6 components")
            
        except Exception as e:
            logger.error(f"Unexpected error in ScheduleSettings.__post_init__: {e}")
            logger.debug(f"❌  Exception details: {traceback.format_exc()}")
            self.hour, self.minute = map(int, DEFAULT_RUN_TIME.split(":"))


@dataclass
class LoggingSettings:
    """Application logging settings"""
    
    log_dir: str = DEFAULT_LOG_DIR
    log_file: str = DEFAULT_LOG_FILE
    backup_count: int = DEFAULT_LOG_BACKUP_COUNT
    max_size_mb: int = DEFAULT_LOG_MAX_SIZE_MB
    debug_mode: bool = DEFAULT_DEBUG_MODE
    
    def __post_init__(self):
        try:
            logger.debug(f"🔧  Initialized LoggingSettings: log_dir={self.log_dir}, log_file={self.log_file}, "
                         f"backup_count={self.backup_count}, max_size_mb={self.max_size_mb}, "
                         f"debug_mode={self.debug_mode}")
            
            # Check if log directory exists or is writable
            try:
                if not os.path.exists(self.log_dir):
                    logger.warning(f"Log directory does not exist: {self.log_dir}")
                elif not os.access(self.log_dir, os.W_OK):
                    logger.warning(f"Log directory is not writable: {self.log_dir}")
            except Exception as e:
                logger.warning(f"Error checking log directory: {e}")
                
            # Validate numeric settings
            if self.backup_count <= 0:
                logger.warning(f"Invalid backup_count: {self.backup_count}, should be positive")
            if self.max_size_mb <= 0:
                logger.warning(f"Invalid max_size_mb: {self.max_size_mb}, should be positive")
                
        except Exception as e:
            logger.error(f"Error in LoggingSettings.__post_init__: {e}")
            logger.debug(f"❌  Exception details: {traceback.format_exc()}")


@dataclass
class Config:
    """Main Application configuration"""
    
    # Webhook settings
    discord_webhook_url: Optional[str] = None
    slack_webhook_url: Optional[str] = None
    use_discord: bool = DEFAULT_USE_DISCORD
    use_slack: bool = DEFAULT_USE_SLACK
    
    # Display settings
    custom_header: str = DEFAULT_HEADER
    show_date_range: bool = DEFAULT_SHOW_DATE_RANGE
    start_week_on_monday: bool = DEFAULT_START_WEEK_ON_MONDAY
    deduplicate_events: bool = DEFAULT_DEDUPLICATE_EVENTS
    
    # Discord-specific settings
    discord_mention_role_id: Optional[str] = DEFAULT_DISCORD_MENTION_ROLE_ID
    discord_hide_mention_instructions: bool = DEFAULT_DISCORD_HIDE_MENTION_INSTRUCTIONS
    
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
    
    def __post_init__(self):
        try:
            logger.debug("🏁  Initializing Config object")
            # Normalize string settings
            try:
                if self.passed_event_handling:
                    self.passed_event_handling = self.passed_event_handling.upper()
                    logger.debug(f"🔄  Normalized passed_event_handling to {self.passed_event_handling}")
                
                if self.calendar_range:
                    self.calendar_range = self.calendar_range.upper()
                    logger.debug(f"🔄  Normalized calendar_range to {self.calendar_range}")
            except (AttributeError, TypeError) as e:
                logger.warning(f"Error normalizing string settings: {e}")
                
            # Log configured calendar URLs
            logger.debug(f"📋  Initialized with {len(self.calendar_urls)} calendar URLs")
            for i, url in enumerate(self.calendar_urls):
                logger.debug(f"📋  Calendar URL {i+1}: {url.url} (type: {url.type})")
                
            logger.debug(f"✅  Config initialization complete")
        except Exception as e:
            logger.error(f"Error in Config.__post_init__: {e}")
            logger.debug(f"❌  Exception details: {traceback.format_exc()}")
    
    @property
    def timezone_obj(self) -> pytz.timezone:
        """
        Get timezone object
        
        Returns:
            Timezone object
        """
        try:
            logger.debug(f"🔍  Getting timezone object for: {self.timezone}")
            tz = pytz.timezone(self.timezone)
            logger.debug(f"✅  Successfully created timezone object: {tz}")
            return tz
        except pytz.exceptions.UnknownTimeZoneError:
            logger.error(f"Unknown timezone: {self.timezone}, falling back to UTC")
            return pytz.UTC
        except Exception as e:
            logger.error(f"Error creating timezone object: {e}")
            logger.debug(f"❌  Exception details: {traceback.format_exc()}")
            return pytz.UTC
    
    @property
    def enabled_platforms(self) -> List[str]:
        """
        Get list of enabled platforms
        
        Returns:
            List of platform names
        """
        try:
            logger.debug("🔍  Getting enabled platforms")
            platforms = []
            if self.use_discord:
                platforms.append("discord")
            if self.use_slack:
                platforms.append("slack")
            logger.debug(f"📋  Enabled platforms: {platforms}")
            return platforms
        except Exception as e:
            logger.error(f"Error determining enabled platforms: {e}")
            logger.debug(f"❌  Exception details: {traceback.format_exc()}")
            # Return empty list as fallback
            return []
    
    def validate(self) -> List[str]:
        """
        Validate configuration
        
        Returns:
            List of error messages, empty if valid
        """
        try:
            logger.debug("🧪  Validating configuration")
            errors = []
            
            # Validate webhook configuration
            try:
                logger.debug(f"🧪  Validating messaging platforms: discord={self.use_discord}, slack={self.use_slack}")
                if not self.use_discord and not self.use_slack:
                    errors.append("At least one messaging platform must be enabled")

                if self.use_discord:
                    if not self.discord_webhook_url:
                        errors.append("DISCORD_WEBHOOK_URL is required when USE_DISCORD is true")
                    else:
                        logger.debug("✅  Discord webhook URL is configured")
                        
                if self.use_slack:
                    if not self.slack_webhook_url:
                        errors.append("SLACK_WEBHOOK_URL is required when USE_SLACK is true")
                    else:
                        logger.debug("✅  Slack webhook URL is configured")
            except Exception as e:
                logger.error(f"Error validating webhook config: {e}")
                errors.append(f"Internal error validating webhook configuration: {str(e)}")
            
            # Validate the passed event handling option
            try:
                logger.debug(f"🧪  Validating passed_event_handling: {self.passed_event_handling}")
                if self.passed_event_handling not in VALID_PASSED_EVENT_HANDLING:
                    errors.append(f"Invalid PASSED_EVENT_HANDLING value: {self.passed_event_handling}, "
                                f"must be one of {VALID_PASSED_EVENT_HANDLING}")
            except Exception as e:
                logger.error(f"Error validating passed event handling: {e}")
                errors.append(f"Internal error validating event handling: {str(e)}")
            
            # Validate calendar range
            try:
                logger.debug(f"🧪  Validating calendar_range: {self.calendar_range}")
                if self.calendar_range not in VALID_CALENDAR_RANGE:
                    errors.append(f"Invalid CALENDAR_RANGE value: {self.calendar_range}, "
                                f"must be one of {VALID_CALENDAR_RANGE}")
            except Exception as e:
                logger.error(f"Error validating calendar range: {e}")
                errors.append(f"Internal error validating calendar range: {str(e)}")
                
            # Validate calendar URLs
            try:
                logger.debug(f"🧪  Validating {len(self.calendar_urls)} calendar URLs")
                if not self.calendar_urls:
                    logger.warning("No calendar URLs configured")
                
                for i, url in enumerate(self.calendar_urls):
                    if not url.url:
                        errors.append(f"Calendar URL at index {i} is empty")
                    if url.type not in VALID_EVENT_TYPES:
                        errors.append(f"Calendar URL at index {i} has invalid type: {url.type}, must be one of {VALID_EVENT_TYPES}")
            except Exception as e:
                logger.error(f"Error validating calendar URLs: {e}")
                errors.append(f"Internal error validating calendar URLs: {str(e)}")
            
            # Validate timezone
            try:
                logger.debug(f"🧪  Validating timezone: {self.timezone}")
                try:
                    pytz.timezone(self.timezone)
                except pytz.exceptions.UnknownTimeZoneError:
                    errors.append(f"Unknown timezone: {self.timezone}")
            except Exception as e:
                logger.error(f"Error validating timezone: {e}")
                errors.append(f"Internal error validating timezone: {str(e)}")
            
            logger.debug(f"🏁  Validation complete. Found {len(errors)} errors")
            return errors
        except Exception as e:
            logger.error(f"Unexpected error in Config.validate: {e}")
            logger.debug(f"❌  Exception details: {traceback.format_exc()}")
            return [f"Internal validation error: {str(e)}"]


def load_calendar_urls(urls_str: str) -> List[CalendarUrl]:
    """
    Parse calendar URLs from environment variable
    
    Args:
        urls_str: JSON string of calendar URLs
        
    Returns:
        List of CalendarUrl objects
    """
    try:
        logger.debug(f"🔍  Loading calendar URLs from string: {urls_str}")
        if not urls_str or urls_str.strip() == "":
            logger.warning("Empty calendar URLs string provided")
            return []
            
        try:
            urls_data = json.loads(urls_str)
            logger.debug(f"📋  Parsed calendar URLs JSON: {urls_data}")
            
            if not isinstance(urls_data, list):
                logger.error(f"CALENDAR_URLS is not a list: {urls_data}")
                return []
                
            urls = []
            for i, url_data in enumerate(urls_data):
                try:
                    logger.debug(f"⚙️  Processing calendar URL at index {i}: {url_data}")
                    if not isinstance(url_data, dict):
                        logger.warning(f"Calendar URL at index {i} is not a dictionary: {url_data}")
                        continue
                        
                    url = CalendarUrl.from_dict(url_data)
                    if url.url:  # Only add if URL is not empty
                        urls.append(url)
                    else:
                        logger.warning(f"Skipping empty URL at index {i}")
                except Exception as e:
                    logger.error(f"Error processing calendar URL at index {i}: {e}")
                    logger.debug(f"❌  Exception details: {traceback.format_exc()}")
            
            logger.info(f"✅ Successfully loaded CALENDAR_URLS: {len(urls)} calendars")
            return urls
        except json.JSONDecodeError as e:
            logger.error(f"ERROR: CALENDAR_URLS is not valid JSON: {urls_str}")
            logger.error(f"Error details: {str(e)}")
            return []
    except Exception as e:
        logger.error(f"Unexpected error loading calendar URLs: {e}")
        logger.debug(f"❌  Exception details: {traceback.format_exc()}")
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
    try:
        logger.debug(f"🔍  Getting boolean environment variable {name} with default {default}")
        
        if name not in os.environ:
            logger.debug(f"📋  Environment variable {name} not found, using default: {default}")
            return default
            
        value = os.environ.get(name, str(default)).lower()
        logger.debug(f"📋  Retrieved env variable {name} with raw value '{value}'")
        
        result = value in ('true', 'yes', '1', 'y')
        logger.debug(f"🔄  Converted {name}='{value}' to boolean: {result}")
        return result
    except Exception as e:
        logger.error(f"Error getting boolean env var {name}: {e}")
        logger.debug(f"❌  Exception details: {traceback.format_exc()}")
        return default


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
        logger.debug(f"🔍  Getting integer environment variable {name} with default {default}")
        
        if name not in os.environ:
            logger.debug(f"📋  Environment variable {name} not found, using default: {default}")
            return default
            
        value = os.environ.get(name, str(default))
        logger.debug(f"📋  Retrieved env variable {name} with raw value '{value}'")
        
        try:
            result = int(value)
            logger.debug(f"🔄  Successfully converted {name}='{value}' to int: {result}")
            
            # Basic validation for some known variables
            if name in ["LOG_BACKUP_COUNT", "MAX_LOG_SIZE", "HTTP_TIMEOUT"] and result <= 0:
                logger.warning(f"Invalid {name} value: {result}, should be positive. Using default: {default}")
                return default
                
            return result
        except (ValueError, TypeError) as e:
            logger.warning(f"Cannot convert {name}='{value}' to int: {e}")
            return default
    except Exception as e:
        logger.error(f"Unexpected error getting int env var {name}: {e}")
        logger.debug(f"❌  Exception details: {traceback.format_exc()}")
        return default


def load_config_from_env() -> Config:
    """
    Load configuration from environment variables
    
    Returns:
        Config object
    """
    try:
        logger.debug("🏁  Loading configuration from environment variables")
        
        # Load calendar URLs
        try:
            logger.debug("🔍  Loading calendar URLs")
            calendar_urls_str = os.environ.get("CALENDAR_URLS", "[]")
            logger.debug(f"📋  CALENDAR_URLS env var value: {calendar_urls_str}")
            calendar_urls = load_calendar_urls(calendar_urls_str)
            logger.debug(f"✅  Loaded {len(calendar_urls)} calendar URLs")
        except Exception as e:
            logger.error(f"Error loading calendar URLs: {e}")
            logger.debug(f"❌  Exception details: {traceback.format_exc()}")
            calendar_urls = []
        
        # Load time settings
        try:
            logger.debug("🔍  Loading time settings")
            time_settings = TimeSettings(
                use_24_hour=get_env_bool("USE_24_HOUR", DEFAULT_USE_24_HOUR),
                add_leading_zero=get_env_bool("ADD_LEADING_ZERO", DEFAULT_ADD_LEADING_ZERO),
                display_time=get_env_bool("DISPLAY_TIME", DEFAULT_DISPLAY_TIME)
            )
            logger.debug(f"✅  Loaded time settings: {time_settings}")
        except Exception as e:
            logger.error(f"Error loading time settings: {e}")
            logger.debug(f"❌  Exception details: {traceback.format_exc()}")
            time_settings = TimeSettings()
        
        # Load scheduling settings
        try:
            logger.debug("🔍  Loading scheduling settings")
            schedule_settings = ScheduleSettings(
                schedule_type=os.environ.get("SCHEDULE_TYPE", DEFAULT_SCHEDULE_TYPE).upper(),
                run_time=os.environ.get("RUN_TIME", DEFAULT_RUN_TIME),
                schedule_day=os.environ.get("SCHEDULE_DAY", DEFAULT_SCHEDULE_DAY),
                cron_schedule=os.environ.get("CRON_SCHEDULE"),
                run_on_startup=get_env_bool("RUN_ON_STARTUP", DEFAULT_RUN_ON_STARTUP)
            )
            logger.debug(f"✅  Loaded schedule settings: type={schedule_settings.schedule_type}, "
                         f"time={schedule_settings.run_time}, day={schedule_settings.schedule_day}")
        except Exception as e:
            logger.error(f"Error loading scheduling settings: {e}")
            logger.debug(f"❌  Exception details: {traceback.format_exc()}")
            schedule_settings = ScheduleSettings()
        
        # Load logging settings
        try:
            logger.debug("🔍  Loading logging settings")
            logging_settings = LoggingSettings(
                log_dir=os.environ.get("LOG_DIR", DEFAULT_LOG_DIR),
                log_file=os.environ.get("LOG_FILE", DEFAULT_LOG_FILE),
                backup_count=get_env_int("LOG_BACKUP_COUNT", DEFAULT_LOG_BACKUP_COUNT),
                max_size_mb=get_env_int("MAX_LOG_SIZE", DEFAULT_LOG_MAX_SIZE_MB),
                debug_mode=get_env_bool("DEBUG", DEFAULT_DEBUG_MODE)
            )
            logger.debug(f"✅  Loaded logging settings: dir={logging_settings.log_dir}, "
                         f"file={logging_settings.log_file}, debug={logging_settings.debug_mode}")
        except Exception as e:
            logger.error(f"Error loading logging settings: {e}")
            logger.debug(f"❌  Exception details: {traceback.format_exc()}")
            logging_settings = LoggingSettings()
        
        # Load webhook URLs and platform settings
        try:
            logger.debug("🔍  Loading webhook URLs and platform settings")
            discord_webhook_url = os.environ.get("DISCORD_WEBHOOK_URL")
            slack_webhook_url = os.environ.get("SLACK_WEBHOOK_URL")
            use_discord = get_env_bool("USE_DISCORD", DEFAULT_USE_DISCORD)
            use_slack = get_env_bool("USE_SLACK", DEFAULT_USE_SLACK)

            # --- Add Fallback Logic for Role ID ---
            # THIS WILL EVENTUALLY BE REMOVED IN FUTURE RELEASES. IT'S JUST A TEMPORARY FIX 
            discord_mention_role_id = os.environ.get("DISCORD_MENTION_ROLE_ID")
            role_id_source = "DISCORD_MENTION_ROLE_ID"
            if not discord_mention_role_id:
                # If new variable is not set, try the old one
                discord_mention_role_id = os.environ.get("MENTION_ROLE_ID", DEFAULT_DISCORD_MENTION_ROLE_ID)
                if discord_mention_role_id != DEFAULT_DISCORD_MENTION_ROLE_ID:
                    role_id_source = "MENTION_ROLE_ID (fallback)"
                else:
                    role_id_source = "Default" # If neither new nor old is set
            # --- End Fallback Logic ---

            discord_hide_mention_instructions=get_env_bool("DISCORD_HIDE_MENTION_INSTRUCTIONS", DEFAULT_DISCORD_HIDE_MENTION_INSTRUCTIONS)

            logger.debug(f"📋  Discord enabled: {use_discord}, webhook configured: {'yes' if discord_webhook_url else 'no'}")
            logger.debug(f"📋  Slack enabled: {use_slack}, webhook configured: {'yes' if slack_webhook_url else 'no'}")
            # Update log message to show which variable was used
            logger.debug(f"📋  Discord mention role: {discord_mention_role_id} (Source: {role_id_source})")
            logger.debug(f"📋  Hide Discord mention role message: {discord_hide_mention_instructions}")
        except Exception as e:
            logger.error(f"Error loading webhook settings: {e}")
            logger.debug(f"❌  Exception details: {traceback.format_exc()}")
            discord_webhook_url = None
            slack_webhook_url = None
            discord_mention_role_id = DEFAULT_DISCORD_MENTION_ROLE_ID
            discord_hide_mention_instructions = DEFAULT_DISCORD_HIDE_MENTION_INSTRUCTIONS
            use_discord = DEFAULT_USE_DISCORD
            use_slack = DEFAULT_USE_SLACK

        # Load display settings
        try:
            logger.debug("🔍  Loading display settings")
            custom_header = os.environ.get("CUSTOM_HEADER", DEFAULT_HEADER)
            show_date_range = get_env_bool("SHOW_DATE_RANGE", DEFAULT_SHOW_DATE_RANGE)
            start_week_on_monday = get_env_bool("START_WEEK_ON_MONDAY", DEFAULT_START_WEEK_ON_MONDAY)
            deduplicate_events = get_env_bool("DEDUPLICATE_EVENTS", DEFAULT_DEDUPLICATE_EVENTS)
            logger.debug(f"✅  Loaded display settings: header='{custom_header}', "
                        f"show_date_range={show_date_range}, start_on_monday={start_week_on_monday}")
        except Exception as e:
            logger.error(f"Error loading display settings: {e}")
            logger.debug(f"❌  Exception details: {traceback.format_exc()}")
            custom_header = DEFAULT_HEADER
            show_date_range = DEFAULT_SHOW_DATE_RANGE
            start_week_on_monday = DEFAULT_START_WEEK_ON_MONDAY
            deduplicate_events = DEFAULT_DEDUPLICATE_EVENTS
        
        # Load calendar settings
        try:
            logger.debug("🔍  Loading calendar settings")
            passed_event_handling = os.environ.get("PASSED_EVENT_HANDLING", DEFAULT_PASSED_EVENT_HANDLING).upper()
            calendar_range = os.environ.get("CALENDAR_RANGE", DEFAULT_CALENDAR_RANGE).upper()
            logger.debug(f"✅  Loaded calendar settings: passed_event_handling={passed_event_handling}, "
                        f"calendar_range={calendar_range}")
        except Exception as e:
            logger.error(f"Error loading calendar settings: {e}")
            logger.debug(f"❌  Exception details: {traceback.format_exc()}")
            passed_event_handling = DEFAULT_PASSED_EVENT_HANDLING
            calendar_range = DEFAULT_CALENDAR_RANGE
        
        # Load timezone and HTTP settings
        try:
            logger.debug("🔍  Loading timezone and HTTP settings")
            timezone = os.environ.get("TZ", "UTC")
            http_timeout = get_env_int("HTTP_TIMEOUT", DEFAULT_HTTP_TIMEOUT)
            logger.debug(f"✅  Loaded timezone={timezone}, http_timeout={http_timeout}")
        except Exception as e:
            logger.error(f"Error loading timezone and HTTP settings: {e}")
            logger.debug(f"❌  Exception details: {traceback.format_exc()}")
            timezone = "UTC"
            http_timeout = DEFAULT_HTTP_TIMEOUT
        
        # Create config object
        try:
            logger.debug("⚙️  Creating Config object")
            config = Config(
                discord_webhook_url=discord_webhook_url,
                slack_webhook_url=slack_webhook_url,
                use_discord=use_discord,
                use_slack=use_slack,
                discord_mention_role_id=discord_mention_role_id,
                discord_hide_mention_instructions=discord_hide_mention_instructions,
                custom_header=custom_header,
                show_date_range=show_date_range,
                start_week_on_monday=start_week_on_monday,
                calendar_urls=calendar_urls,
                passed_event_handling=passed_event_handling,
                calendar_range=calendar_range,
                time_settings=time_settings,
                deduplicate_events=deduplicate_events,
                schedule_settings=schedule_settings,
                logging_settings=logging_settings,
                timezone=timezone,
                http_timeout=http_timeout
            )
            logger.debug("✅  Successfully created Config object")
        except Exception as e:
            logger.error(f"Error creating Config object: {e}")
            logger.debug(f"❌  Exception details: {traceback.format_exc()}")
            # Create a default config as fallback
            config = Config()
        
        # Handle AUTO setting - convert to DAY or WEEK based on SCHEDULE_TYPE
        try:
            if config.calendar_range == "AUTO":
                logger.debug("⚙️  Handling AUTO calendar range")
                if config.schedule_settings.schedule_type == "DAILY":
                    logger.debug("🔄  Converting AUTO calendar range to DAY based on DAILY schedule")
                    config.calendar_range = "DAY"
                else:
                    logger.debug("🔄  Converting AUTO calendar range to WEEK based on non-DAILY schedule")
                    config.calendar_range = "WEEK"
        except Exception as e:
            logger.error(f"Error handling AUTO calendar range: {e}")
            logger.debug(f"❌  Exception details: {traceback.format_exc()}")
            config.calendar_range = DEFAULT_CALENDAR_RANGE
        
        # Validate the passed event handling option
        try:
            if config.passed_event_handling not in VALID_PASSED_EVENT_HANDLING:
                logger.warning(f"Invalid PASSED_EVENT_HANDLING value: {config.passed_event_handling}, "
                            f"defaulting to {DEFAULT_PASSED_EVENT_HANDLING}")
                config.passed_event_handling = DEFAULT_PASSED_EVENT_HANDLING
        except Exception as e:
            logger.error(f"Error validating passed event handling: {e}")
            logger.debug(f"❌  Exception details: {traceback.format_exc()}")
            config.passed_event_handling = DEFAULT_PASSED_EVENT_HANDLING
        
        # Validate configuration
        try:
            logger.debug("🧪  Validating final configuration")
            errors = config.validate()
            if errors:
                for error in errors:
                    logger.error(f"Configuration error: {error}")
                raise ValueError(f"Invalid configuration: {', '.join(errors)}")
        except ValueError:
            # Re-raise validation errors
            raise
        except Exception as e:
            logger.error(f"Error during configuration validation: {e}")
            logger.debug(f"❌  Exception details: {traceback.format_exc()}")
            raise ValueError(f"Error validating configuration: {str(e)}")
        
        logger.debug("🏁  Configuration loaded successfully")
        return config
    except ValueError:
        # Re-raise validation errors
        raise
    except Exception as e:
        logger.error(f"Unexpected error loading configuration: {e}")
        logger.debug(f"❌  Exception details: {traceback.format_exc()}")
        raise ValueError(f"Failed to load configuration: {str(e)}")