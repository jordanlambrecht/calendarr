#!/usr/bin/env python3
"""
Application-wide constants for Calendarr
"""
import pytz
import os

# Calendar parsing
PREMIERE_PATTERN = r'[-\s](?:s\d+e0*1|(?:\d+x0*1))\b'

# API-related
MAX_DISCORD_EMBEDS_PER_REQUEST = 10
DISCORD_SUCCESS_CODES = [200, 204]
SLACK_SUCCESS_CODES = [200, 201, 204]

# User interface
NO_NEW_RELEASES_MSG = "No new releases. Maybe it's a good day to take a walk?"

# Color definitions
COLOR_PALETTE = {
    "discord": {
        "red": 15158332,      # Red
        "orange": 15844367,   # Orange
        "yellow": 16776960,   # Yellow
        "green": 5763719,     # Green
        "blue": 3447003,      # Blue
        "indigo": 10181046,   # Indigo/Purple
        "violet": 9846527     # Violet
    },
    "slack": {
        "red": "#E53935",     # Red
        "orange": "#FB8C00",  # Orange
        "yellow": "#FFD600",  # Yellow
        "green": "#43A047",   # Green
        "blue": "#1E88E5",    # Blue
        "indigo": "#5E35B1",  # Indigo
        "violet": "#8E24AA"   # Violet
    }
}

# Time-related constants
DEFAULT_TIMEZONE = pytz.timezone(os.environ.get('TZ', 'UTC'))

# Logging
BACKUP_COUNT = 15  # Number of backup files to keep
MAX_LOG_SIZE = 1

# Default env variable These need to go away but im so tired!!! im always so tired.
DEFAULT_SCHEDULE_TYPE = "WEEKLY"
DEFAULT_RUN_TIME = "09:00"
DEFAULT_PASSED_EVENT_HANDLING = "DISPLAY"