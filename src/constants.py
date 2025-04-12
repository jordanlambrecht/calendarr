#!/usr/bin/env python3
# src/constants.py
"""
Application-wide constants
"""

# ==============================================
# Calendar & Event Parsing
# ==============================================
PREMIERE_PATTERN = r'[-\s](?:s\d+e0*1|(?:\d+x0*1))\b'
EPISODE_PATTERN = r'^(S?\d{1,4}[Ex]\d{1,4})$'

# ==============================================
# API & HTTP Settings
# ==============================================
MAX_DISCORD_EMBEDS_PER_REQUEST = 10
DISCORD_SUCCESS_CODES = [200, 204]
SLACK_SUCCESS_CODES = [200, 201, 204]
DEFAULT_HTTP_TIMEOUT = 30  # seconds

# ==============================================
# Common Names
# ==============================================
PLATFORM_DISCORD = "discord"
PLATFORM_SLACK = "slack"
EVENT_TYPE_TV = "tv"
EVENT_TYPE_ANIME = "anime" # Coming soon (Maybe)
EVENT_TYPE_ALBUM = "album" # Coming soon (Maybe)
EVENT_TYPE_MOVIE = "movie"
VALID_EVENT_TYPES = [EVENT_TYPE_TV, EVENT_TYPE_MOVIE]

# ==============================================
# User Interface & Formatting
# ==============================================
NO_NEW_RELEASES_MSG = "No new releases. Maybe it's a good day to take a walk?"

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

# ==============================================
# Default Config Values
# ==============================================

# --- General ---
DEFAULT_DEBUG_MODE = False
DEFAULT_HEADER = "New Releases"

# --- Platforms ---
DEFAULT_USE_DISCORD = True
DEFAULT_USE_SLACK = False
DEFAULT_DISCORD_MENTION_ROLE_ID = ""
DEFAULT_DISCORD_HIDE_MENTION_INSTRUCTIONS = False

# --- Calendar & Events ---
DEFAULT_CALENDAR_RANGE = "AUTO"
DEFAULT_PASSED_EVENT_HANDLING = "DISPLAY"
DEFAULT_START_WEEK_ON_MONDAY = True
DEFAULT_DEDUPLICATE_EVENTS = True

# --- Scheduling ---
DEFAULT_RUN_TIME = "09:00"
DEFAULT_SCHEDULE_TYPE = "WEEKLY"
DEFAULT_SCHEDULE_DAY = "1"  # Monday
DEFAULT_RUN_ON_STARTUP = False

# --- Time Formatting ---
DEFAULT_USE_24_HOUR = True
DEFAULT_ADD_LEADING_ZERO = True
DEFAULT_DISPLAY_TIME = True
DEFAULT_SHOW_DATE_RANGE = True

# --- Logging ---
DEFAULT_LOG_DIR = "/app/logs"
DEFAULT_LOG_FILE = "calendarr.log"
DEFAULT_LOG_BACKUP_COUNT = 15
DEFAULT_LOG_MAX_SIZE_MB = 1

# ==============================================
# Valid Config Options
# ==============================================
VALID_PASSED_EVENT_HANDLING = ["DISPLAY", "HIDE", "STRIKE"]
VALID_CALENDAR_RANGE = ["DAY", "WEEK", "AUTO"]

# ==============================================
# Scheduler Job IDs
# ==============================================
JOB_ID_DEBUG_PING = 'debug_ping_job'
JOB_ID_LOG_CLEANUP = 'log_cleanup_job'
JOB_ID_MAIN = 'main_job'