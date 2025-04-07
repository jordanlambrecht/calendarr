#!/usr/bin/env python3

# calendar_processor.py
from dataclasses import dataclass
from datetime import datetime, date, time
from typing import Dict, List
import logging
import re
import pytz
import requests
import icalendar
import recurring_ical_events
import os


from general_helpers import build_content_summary_parts, join_content_parts, apply_formatting, process_movie_event, count_events_by_type
from datetime_helpers import is_event_in_past, get_days_order, get_short_day_name, parse_event_datetime, format_time, format_date_range, get_day_colors
from constants import PREMIERE_PATTERN


logger = logging.getLogger("calendar")


@dataclass
class Config:
    """Configuration for display formatting"""
    platform: str
    custom_header: str 
    show_date_range: bool
    is_daily_mode: bool
    display_time: bool = True
    use_24_hour: bool = False
    add_leading_zero: bool = True
    passed_event_handling: str = "DISPLAY"  # Options: DISPLAY, HIDE, STRIKE
    start_week_on_monday: bool = True
    timezone: str = "UTC"

    @property
    def get_day_colors(self):
        """Get color scheme based on platform and settings"""
        return get_day_colors(self.platform, self.start_week_on_monday)
    
    @property
    def local_timezone(self) -> pytz.timezone:
        """Get the configured timezone object"""
        return pytz.timezone(self.timezone)


@dataclass
class CalendarEvent:
    summary: str
    start_time: datetime
    source_type: str
    is_premiere: bool = False
    
    @property
    def is_past(self):
        return is_event_in_past(self.start_time)
        
    @property
    def day_key(self):
        return self.start_time.strftime('%A, %b %d')





def fetch_events_from_calendar(url_info: Dict, start_date: datetime, end_date: datetime) -> List:
    """Fetch events from a single calendar URL with proper timezone handling"""
    url = url_info["url"]
    source_type = url_info["type"]  # "tv" or "movie"
    
    # Get local timezone
    local_tz = pytz.timezone(os.environ.get('TZ', 'UTC'))
    
    logger.info(f"Fetching events for {source_type} between {start_date.strftime('%Y-%m-%d')} and {end_date.strftime('%Y-%m-%d')}")
    
    response = requests.get(url)
    if response.status_code != 200:
        logger.error(f"Failed to fetch iCal from {url}: {response.status_code}")
        return []
    
    calendar = icalendar.Calendar.from_ical(response.content)
    
    events = recurring_ical_events.of(calendar).between(
        start_date, 
        end_date
    )

    events_count = len(list(events))
    logger.debug(f"🔎  Found {events_count} raw events in calendar from {url}")
    
    # Process events with proper timezone handling
    processed_events = []
    for event in events:
        # Get the start time
        dtstart = event.get('DTSTART').dt
        summary = event.get('SUMMARY', 'Untitled Event')
        
        logger.debug(f"🔄  Processing event: {summary} - Original date: {dtstart}")
        
        # Handle date-only events
        if isinstance(dtstart, date) and not isinstance(dtstart, datetime):
            # Convert to datetime at midnight
            dtstart = datetime.combine(dtstart, time.min)
            # Apply local timezone
            dtstart = local_tz.localize(dtstart)
        elif isinstance(dtstart, datetime):

            if dtstart.tzinfo is not None:
                # Convert to local timezone
                dtstart = dtstart.astimezone(local_tz)
            else:
                # If no timezone, assume UTC and convert
                dtstart = pytz.utc.localize(dtstart).astimezone(local_tz)
        
        # Double-check it's in our date range
        event_date = dtstart.date()
        start_range = start_date.date()
        end_range = end_date.date()
        
        if event_date < start_range or event_date > end_range:
            logger.warning(f"WARNING: Event date {event_date} is outside range {start_range} to {end_range}, skipping")
            continue
        
        logger.debug(f"Event after processing: {summary} - {dtstart.strftime('%Y-%m-%d %H:%M %Z')}")
        
        # Update the event with localized time
        event['DTSTART'].dt = dtstart
        
        # Add source type
        event["SOURCE_TYPE"] = source_type
        processed_events.append(event)
    
    return processed_events

def get_events_for_date_range(ical_urls: List[Dict], start_date: datetime, end_date: datetime) -> List:
    """Fetch events for the given date range"""
    # Fetch all events
    all_events = []
    for url_info in ical_urls:
        events = fetch_events_from_calendar(url_info, start_date, end_date)
        all_events.extend(events)
    
    return all_events


def process_tv_event(summary, start, platform=None, display_time=True, use_24_hour=False, add_leading_zero=True):
    """Format TV event for display"""
    is_premiere = bool(re.search(PREMIERE_PATTERN, summary, re.IGNORECASE))
    

    dt_parts = parse_event_datetime(start)
    
    # Split show name from episode details if possible
    parts = re.split(r'\s+-\s+', summary, 1)
    if len(parts) == 2:
        show_name = parts[0]
        episode_info = parts[1]
        
        # Split again by ' - ' to separate episode number from title
        sub_parts = re.split(r'\s+-\s+', episode_info, 1)
        if len(sub_parts) == 2:
            episode_num, episode_title = sub_parts
        else:
            episode_num = episode_info
            episode_title = ""

        if display_time:
            time_str = format_time(dt_parts["hour"], dt_parts["minute"], platform, use_24_hour, add_leading_zero)
            if is_premiere:
                return f"{time_str}: **{show_name}** - {episode_num} - *{episode_title}*  🎉"
            else:
                return f"{time_str}: **{show_name}** - {episode_num} - *{episode_title}*"
        else:
            if is_premiere:
                return f"**{show_name}** - {episode_num} - *{episode_title}* 🎉"
            else:
                return f"**{show_name}** - {episode_num} - *{episode_title}*"
    else:
        # No dash separator found, just display as is
        if display_time:
            time_str = format_time(dt_parts["hour"], dt_parts["minute"], platform, use_24_hour, add_leading_zero)
            if is_premiere:
                return f"{time_str}: **{summary}**  🎉"
            else:
                return f"{time_str}: **{summary}**"
        else:
            if is_premiere:
                return f" **{summary}**  🎉"
            else:
                return f"**{summary}**"



def process_events_for_display(events, start_date, end_date, platform=None, start_week_on_monday=True, 
                              use_24_hour=False, add_leading_zero=True, display_time=True,
                              passed_event_handling="DISPLAY"):
    """Process events into platform-specific format"""
    if not events:
        return {}, 0, 0
    
    tv_count, movie_count = count_events_by_type(events)
    
    logger.debug(f"🔢  Processing {tv_count} TV episodes and {movie_count} movies for display")

    sorted_events = sorted(events, key=lambda e: e.get('DTSTART').dt)
    
    # Group events by day
    days = {}
    for event in sorted_events:
        start = event.get('DTSTART').dt
        source_type = event.get("SOURCE_TYPE")
        summary = event.get('SUMMARY', 'Untitled Event')
        
        is_past_event = is_event_in_past(start)

        if is_past_event and passed_event_handling == "HIDE":
            logger.debug(f"⏪  Skipping past event: {summary}")
            continue
        
        day_key = start.strftime('%A, %b %d')
        
        if day_key not in days:
            days[day_key] = {"tv": [], "movie": []}
        
        # Process based on type
        if source_type == "tv":
            formatted_entry = process_tv_event(summary, start, platform, display_time, use_24_hour, add_leading_zero)
            
            # Apply strikethrough for past events if configured
            if is_past_event and passed_event_handling == "STRIKE":
                formatted_entry = apply_formatting(formatted_entry, "strikethrough", platform)
                
            days[day_key]["tv"].append(formatted_entry)
        else:  # movie
            formatted_entry = process_movie_event(summary)
            
            if is_past_event and passed_event_handling == "STRIKE":
                formatted_entry = apply_formatting(formatted_entry, "strikethrough", platform)
                    
            days[day_key]["movie"].append(formatted_entry)
    
    day_order = get_days_order(start_week_on_monday)
    
    # Sort days by day of week, not by date
    ordered_days = {}
    for day_key, content in sorted(days.items(), 
                                  key=lambda x: day_order.index(x[0].split(',')[0])):
        ordered_days[day_key] = content
    
    logger.info(f"Start date: {start_date.strftime('%Y-%m-%d %A')}")
    logger.info(f"End date: {end_date.strftime('%Y-%m-%d %A')}")
    logger.info(f"📊  Total days processed: {len(days)}")
    for day_key in sorted(days.keys()):
        event_count = len(days[day_key]["tv"]) + len(days[day_key]["movie"])
        day_name = day_key.split(',')[0]
        logger.info(f"    ├ {get_short_day_name(day_name)}: {event_count} events")
    
    return ordered_days, tv_count, movie_count



def format_for_discord(days_data, start_week_on_monday=True, is_daily_mode=False):
    """Format the day data into Discord embeds"""
    embeds = []
    day_colors = get_day_colors("discord", start_week_on_monday)
    
    for day, content in days_data.items():
        day_name = day.split(',')[0]  # Extract day name (e.g., "Sunday")
        color = day_colors.get(day_name, 0)
        
        # In daily mode, use an empty title since date is in the header
        if is_daily_mode:
            title = ""  # Empty title - no need to repeat the date
        else:
            title = day  # Use full "Sunday, Apr 06" format for weekly view
            
        # Combine TV and movie listings
        description = ""
        if content["tv"]:
            description += "\n".join(content["tv"])
            if content["movie"]:
                description += "\n\n"
        
        if content["movie"]:
            description += "**MOVIES**\n" + "\n".join(content["movie"])
        
        embed = {
            "title": title,
            "description": description,
            "color": color
        }
        embeds.append(embed)
    
    return embeds

def create_discord_header(tv_count, movie_count, premiere_count, start_date, end_date, 
                         custom_header, show_date_range, is_daily_mode):
    """Create Discord header content with proper formatting"""
    # Create header message with formatted date
    header_text = f"# {custom_header}"
    header_text += format_date_range(start_date, end_date, is_daily_mode)
    
    # Get content summary
    content_parts = build_content_summary_parts(tv_count, movie_count, premiere_count, "discord")
    subheader = join_content_parts(content_parts, "discord")
    
    header_text += f"\n\n{subheader}"
    return header_text




def create_slack_header_blocks(tv_count, movie_count, premiere_count, header_text):
    """Create header blocks for Slack message"""
    # Get content summary
    content_parts = build_content_summary_parts(tv_count, movie_count, premiere_count, "slack")
    message_text = join_content_parts(content_parts, "slack")
    
    return [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": header_text
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": message_text
            }
        }
    ]

def format_slack_day_content(content):
    """Format day content for Slack"""
    formatted_lines = []
    for line in content.split('\n'):
        if line.startswith("**MOVIES"):
            formatted_lines.append(line.replace("**", "*"))
            continue
            
        # For TV shows with time
        if ":" in line and "**" in line:
            parts = line.split(":", 1)
            time_part = parts[0] + ":"
            content_part = parts[1].strip()
            
            # Extract the show name while preserving bold
            if " - " in content_part:
                show_and_episode = content_part.split(" - ", 1)
                show_name = show_and_episode[0]
                episode_info = " - " + show_and_episode[1]
                # Make sure only show name is bold in Slack
                if "**" in show_name:
                    show_name = show_name.replace("**", "*")
                formatted_line = f"{time_part} {show_name}{episode_info}"
            else:
                # If no dash separator, just convert all bold markers
                formatted_line = line.replace("**", "*")
            
            formatted_lines.append(formatted_line)
        else:
            # For lines without time or special format
            formatted_lines.append(line.replace("**", "*"))
    
    return "\n".join(formatted_lines)

def format_for_slack(days_data, tv_count, movie_count, premiere_count, start_date, end_date, 
                    custom_header, show_date_range, start_week_on_monday=True, is_daily_mode=False):
    """
    Format show data for Slack, separate from the sending mechanism
    """
    # Create header text
    header_text = custom_header
    
    # Handle date display in header
    if show_date_range:
        # Check if we're in daily mode (start and end date are the same day)
        if start_date.date() == end_date.date():
            # For daily mode, show just the day name and date
            header_text += f" ({start_date.strftime('%A, %b %d')})"
        else:
            # For weekly mode, show the range as before
            header_text += f" ({start_date.strftime('%b %d')} - {end_date.strftime('%b %d')})"
    
    # Get day colors for Slack
    day_colors = get_day_colors("slack", start_week_on_monday)
    
    # Format the header message
    blocks = create_slack_header_blocks(tv_count, movie_count, premiere_count, header_text)
    
    # Create attachments for each day
    attachments = []
    
    for day, content in days_data.items():
        day_name = day.split(',')[0]
        color = day_colors.get(day_name, "#000000")
        
        # Combine TV and movie listings
        day_content = ""
        if content["tv"]:
            day_content += "\n".join(content["tv"])
            if content["movie"]:
                day_content += "\n\n"
        
        if content["movie"]:
            day_content += "**MOVIES**\n" + "\n".join(content["movie"])
        
        # Fix episode title formatting - only show names should be bold
        formatted_content = format_slack_day_content(day_content)
        
        # Create the attachment with empty title in daily mode
        attachment = {
            "color": color,
            "title": "" if is_daily_mode else day,
            "text": formatted_content,
            "mrkdwn_in": ["text"]
        }
        
        attachments.append(attachment)
    
    return blocks, attachments


