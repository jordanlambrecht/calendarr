#!/usr/bin/env python3
import pytz
import datetime
import os
from typing import Dict, List
import logging
from constants import COLOR_PALETTE

logger = logging.getLogger("calendar")

def is_event_in_past(event_datetime):
    """Check if an event has already occurred"""
    # Get current time with timezone
    local_tz = pytz.timezone(os.environ.get('TZ', 'UTC'))
    now = datetime.datetime.now(local_tz)
    
    # Convert event time to comparable timezone if needed
    if event_datetime.tzinfo is not None:
        event_time = event_datetime.astimezone(local_tz)
    else:
        event_time = local_tz.localize(event_datetime)
    
    # Return True if event is in the past
    return event_time < now

def get_short_day_name(day_name: str) -> str:
    """Get short name for the day"""
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

def get_days_order(start_week_on_monday: bool = True) -> List[str]:
    """
    Get the days of the week in order based on the first day of the week
    """
    if start_week_on_monday:
        return ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    else:
        return ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]

def calculate_date_range(calendar_range: str = "WEEK", start_week_on_monday: bool = True):
    """
    Calculate date range based on environment settings
    """
    # Get the local timezone
    local_tz = pytz.timezone(os.environ.get('TZ', 'UTC'))
    today = datetime.datetime.now(local_tz).replace(hour=0, minute=0, second=0, microsecond=0)
    
    if calendar_range == "DAY":
        # For daily mode, show just today's events
        start_date = today
        end_date = today.replace(hour=23, minute=59, second=59)
        
        # Update the header to reflect just this day
        custom_header = os.environ.get("CUSTOM_HEADER", "TV Guide")
        if " for " not in custom_header:  # Avoid duplicating the date if run multiple times
            os.environ["CUSTOM_HEADER"] = custom_header + f" for {today.strftime('%A, %b %d')}"
    else:
        # For weekly mode, calculate week dates
        weekday = today.weekday()  # 0 is Monday, 6 is Sunday
        
        if start_week_on_monday:
            days_until_start = (7 - weekday) % 7  # Days until next Monday
        else:
            days_until_start = (8 - weekday) % 7  # Days until next Sunday
            if days_until_start == 7:
                days_until_start = 0  # Today is Sunday
        
        start_date = today + datetime.timedelta(days=days_until_start)
        end_date = start_date + datetime.timedelta(days=6, hours=23, minutes=59, seconds=59)
    
    logger.info(f"📅 Date range: {start_date.strftime('%Y-%m-%d %A')} to {end_date.strftime('%Y-%m-%d %A')}")
    return start_date, end_date


def parse_event_datetime(event_datetime):
    """
    Parse a datetime object and return its components
    """
    # Make sure we're working with the datetime in the correct timezone
    local_tz = pytz.timezone(os.environ.get('TZ', 'UTC'))
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

def format_time(hour: int, minute: int, platform: str = None, use_24_hour: bool = False, 
               add_leading_zero: bool = True) -> str:
    """Format time according to configuration"""
    # Choose separator based on platform
    if platform == "slack":
        separator = "."
    else:  # discord or default
        separator = "."  # Changed to avoid Slack formatting issues
        
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

def format_date_range(start_date: datetime.datetime, end_date: datetime.datetime,               is_daily_mode: bool = False) -> str:
    """Format date range text for headers"""
    if is_daily_mode:
        return f"({start_date.strftime('%A, %b %d')})"
    else:
        return f" ({start_date.strftime('%b %d')} - {end_date.strftime('%b %d')})"


def get_day_colors(platform: str, start_week_on_monday: bool = True) -> Dict:
    """
    Get ROYGBIV color mapping for days of the week based on platform and week start
    """
    # Define the ROYGBIV colors for each platform

    
    # Get days in order based on week start
    days_order = get_days_order(start_week_on_monday)
    
    # ROYGBIV color order
    color_order = ["red", "orange", "yellow", "green", "blue", "indigo", "violet"]
    
    # Map colors to days
    day_colors = {}
    for i, day in enumerate(days_order):
        color_name = color_order[i % len(color_order)]
        day_colors[day] = COLOR_PALETTE[platform.lower()][color_name]
    
    return day_colors
