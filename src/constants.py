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
        "red": 15158332,      
        "orange": 15844367,   
        "yellow": 16776960,   
        "green": 5763719,
        "blue": 3447003,
        "indigo": 10181046,
        "violet": 9846527
    },
    "slack": {
        "red": "#E53935",
        "orange": "#FB8C00",
        "yellow": "#FFD600",
        "green": "#43A047",
        "blue": "#1E88E5",
        "indigo": "#5E35B1",
        "violet": "#8E24AA"
    }
}

# Platform names
PLATFORM_DISCORD = "discord"
PLATFORM_SLACK = "slack"

## Needs to be removed eventually but that's a tomorrow problem
DEFAULT_PASSED_EVENT_HANDLING = "DISPLAY"
DEFAULT_RUN_TIME = "09:00"
DEFAULT_SCHEDULE_TYPE = "WEEKLY"
DEFAULT_HEADER = "New Releases"
DEFAULT_CALENDAR_RANGE = "AUTO"