#!/usr/bin/env python3
# src/utils/date_utils.py

import pytz
import datetime
from typing import Dict, List, Tuple
import logging

logger = logging.getLogger("date-utils")


def calculate_date_range(calendar_range: str, start_week_on_monday: bool, timezone_str: str = "UTC"):
    """
    Calculate start and end dates based on the calendar range setting.
    
    Args:
        calendar_range: "DAY" or "WEEK" or "AUTO"
        start_week_on_monday: Whether weeks start on Monday (True) or Sunday (False)
        timezone_str: Timezone string
        
    Returns:
        Tuple of (start_date, end_date) as datetime objects
    """
    import datetime
    import pytz
    
    logger = logging.getLogger("calendar")
    logger.debug(f"🔍  Calculating date range with: range={calendar_range}, start_on_monday={start_week_on_monday}, tz={timezone_str}")
    
    try:
        timezone = pytz.timezone(timezone_str)
    except pytz.exceptions.UnknownTimeZoneError:
        logger.warning(f"❌  Unknown timezone: {timezone_str}, falling back to UTC")
        timezone = pytz.UTC
    
    # Get current date in the specified timezone
    now = datetime.datetime.now(timezone)
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    logger.debug(f"📅  Current date in {timezone_str}: {today}")
    
    # For "DAY" mode, simply use today
    if calendar_range == "DAY":
        logger.debug(f"📅  Using DAY mode: {today} to {today + datetime.timedelta(days=1)}")
        return today, today + datetime.timedelta(days=1)
    
    # For "WEEK" mode, calculate start and end of the current week
    # Get the current weekday (0=Monday in Python's datetime by default)
    weekday = today.weekday()
    
    # Adjust for Sunday as first day if needed
    if not start_week_on_monday:
        # Convert Python's weekday (0=Monday) to a system where 0=Sunday
        # If today is Sunday (Python weekday 6), then adjusted_weekday = 0
        # Otherwise, adjusted_weekday = Python weekday + 1
        adjusted_weekday = 0 if weekday == 6 else weekday + 1
        logger.debug(f"📅  Adjusted weekday for Sunday-start: Python weekday={weekday}, adjusted={adjusted_weekday}")
    else:
        # No adjustment needed if Monday is first day
        adjusted_weekday = weekday
        logger.debug(f"📅  Using Monday-start weekday: {adjusted_weekday}")
    
    # Calculate start of the week
    # Subtract the adjusted weekday to get to the start of the week
    start_date = today - datetime.timedelta(days=adjusted_weekday)
    
    # End date is 7 days after start date
    end_date = start_date + datetime.timedelta(days=7)
    
    logger.debug(f"📅  Calculated date range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
    return start_date, end_date


def get_days_order(start_week_on_monday: bool = True) -> List[str]:
    """
    Get the days of the week in order based on the first day of the week
    
    Args:
        start_week_on_monday: Whether week starts on Monday
        
    Returns:
        List of day names in order
    """
    if start_week_on_monday:
        return ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    else:
        return ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]


def get_short_day_name(day_name: str) -> str:
    """
    Get short name for the day
    
    Args:
        day_name: Full day name
        
    Returns:
        Short day name (3 letters)
    """
    short_names = {
        "Monday": "Mon",
        "Tuesday": "Tue",
        "Wednesday": "Wed",
        "Thursday": "Thu",
        "Friday": "Fri",
        "Saturday": "Sat",
        "Sunday": "Sun"
    }
    return short_names.get(day_name, day_name)


def parse_event_datetime(event_datetime: datetime.datetime, 
                        timezone: str = "UTC") -> Dict[str, any]:
    """
    Parse a datetime object and return its components
    
    Args:
        event_datetime: Datetime to parse
        timezone: Timezone string
        
    Returns:
        Dictionary with datetime components
    """
    # Make sure we're working with the datetime in the correct timezone
    local_tz = pytz.timezone(timezone)
    if event_datetime.tzinfo is not None:
        dt = event_datetime.astimezone(local_tz)
    else:
        dt = local_tz.localize(event_datetime)
    
    return {
        "hour": dt.hour,
        "minute": dt.minute,
        "day": dt.day,
        "month": dt.month,
        "month_name": dt.strftime("%b"),
        "year": dt.year,
        "weekday": dt.weekday(),
        "weekday_name": dt.strftime("%A"),
        "timestamp": dt.timestamp()
    }


def format_time(hour: int, minute: int, platform: str = None, 
               use_24_hour: bool = False, add_leading_zero: bool = True) -> str:
    """
    Format time according to configuration
    
    Args:
        hour: Hour component
        minute: Minute component
        platform: Platform name for formatting
        use_24_hour: Use 24-hour format
        add_leading_zero: Add leading zero to hour
        
    Returns:
        Formatted time string
    """
    # Choose separator based on platform
    separator = "." if platform == "slack" else ":"
        
    if use_24_hour:
        # 24-hour format
        hour_display = hour
        suffix = ""
    else:
        # 12-hour format
        if hour == 0:
            hour_display = 12
            suffix = " AM"
        elif hour < 12:
            hour_display = hour
            suffix = " AM"
        elif hour == 12:
            hour_display = 12
            suffix = " PM"
        else:
            hour_display = hour - 12
            suffix = " PM"
    
    # Add leading zero if needed
    if add_leading_zero and hour_display < 10:
        hour_str = f"0{hour_display}"
    else:
        hour_str = str(hour_display)
    
    # Always add leading zero to minutes
    minute_str = f"0{minute}" if minute < 10 else str(minute)
    
    return f"{hour_str}{separator}{minute_str}{suffix}"


def format_date_range(start_date: datetime.datetime, end_date: datetime.datetime,
                     is_daily_mode: bool = False) -> str:
    """
    Format date range text for headers
    
    Args:
        start_date: Start date
        end_date: End date
        is_daily_mode: Whether showing a single day
        
    Returns:
        Formatted date range string
    """
    if is_daily_mode:
        return f"({start_date.strftime('%A, %b %d')})"
    else:
        return f"({start_date.strftime('%b %d')} - {end_date.strftime('%b %d')})"

