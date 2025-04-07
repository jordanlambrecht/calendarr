#!/usr/bin/env python3
# src/constants.py
"""
Application-wide constants
"""

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

# Platform names
PLATFORM_DISCORD = "discord"
PLATFORM_SLACK = "slack"

## Needs to be removed eventually
DEFAULT_PASSED_EVENT_HANDLING = "DISPLAY"
DEFAULT_RUN_TIME = "09:00"
DEFAULT_SCHEDULE_TYPE = "WEEKLY"
DEFAULT_HEADER = "New Releases"
DEFAULT_CALENDAR_RANGE = "AUTO"