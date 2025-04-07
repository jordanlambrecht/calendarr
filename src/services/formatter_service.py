#!/usr/bin/env python3
# src/services/formatter_service.py

import logging
import re
from typing import Dict, List, Tuple
from datetime import datetime
from collections import defaultdict

from models.day import Day
from models.event import Event
from config.settings import Config
from utils.date_utils import get_days_order, get_short_day_name, parse_event_datetime, format_time
from utils.format_utils import (
    apply_formatting, process_movie_event
)


logger = logging.getLogger("service_formatter")


class FormatterService:
    """Service for formatting calendar events into platform-specific formats"""
    
    def __init__(self, config: Config):
        """
        Initialize with configuration
        
        Args:
            config: Application configuration
        """
        self.config = config
    # This has unused vars but I'm lazy
    def process_events(self, events: List[Event], 
                     start_date: datetime, 
                     end_date: datetime) -> Tuple[List[Day], Dict[str, int]]:
        """
        Process events into Day objects with formatted content
        
        Args:
            events: List of Event objects
            start_date: Start date of the range
            end_date: End date of the range
            
        Returns:
            Tuple of (formatted_days, event_counts)
        """
        if not events:
            return [], {"tv_count": 0, "movie_count": 0, "premiere_count": 0}
        
        # Count events by type
        tv_count = sum(1 for e in events if e.source_type == "tv")
        movie_count = sum(1 for e in events if e.source_type == "movie")
        
        logger.debug(f"🔢 Processing {tv_count} TV episodes and {movie_count} movies for display")
        
        # Group events by day
        days_data = defaultdict(lambda: {"tv": [], "movie": []})
        premiere_count = 0
        
        # Process each event
        for event in events:
            # Skip past events if configured to hide them
            if event.is_past and self.config.passed_event_handling == "HIDE":
                logger.debug(f"⏪ Skipping past event: {event.summary}")
                continue
            
            # Format event based on type
            if event.source_type == "tv":
                formatted_entry = self._process_tv_event(event)
                
                # Count premieres
                if "🎉" in formatted_entry:
                    premiere_count += 1
                
                # Apply strikethrough for past events if configured
                if event.is_past and self.config.passed_event_handling == "STRIKE":
                    formatted_entry = apply_formatting(
                        formatted_entry, 
                        "strikethrough", 
                        "discord"  # This will be platform-specific when I have more time
                    )
                    
                days_data[event.day_key]["tv"].append(formatted_entry)
            else:  # movie
                formatted_entry = process_movie_event(event.summary)
                
                if event.is_past and self.config.passed_event_handling == "STRIKE":
                    formatted_entry = apply_formatting(
                        formatted_entry, 
                        "strikethrough", 
                        "discord"  # This will be platform-specific when I have more time
                    )
                        
                days_data[event.day_key]["movie"].append(formatted_entry)
        
        # Sort days by day of week
        day_order = get_days_order(self.config.start_week_on_monday)
        
        # Convert to Day objects (without colors)
        days = []
        
        for day_key, content in sorted(days_data.items(), 
                                     key=lambda x: day_order.index(x[0].split(',')[0])):
            day = Day(
                name=day_key,
                tv_events=content["tv"],
                movie_events=content["movie"]
            )
            days.append(day)
        
        # Log days processed
        logger.info(f"📊 Total days processed: {len(days)}")
        for day in days:
            logger.info(f"    ├ {get_short_day_name(day.day_name)}: {day.total_events} events")
        
        return days, {
            "tv_count": tv_count,
            "movie_count": movie_count,
            "premiere_count": premiere_count
        }
    
    def _process_tv_event(self, event: Event) -> str:
        """
        Format TV event for display
        
        Args:
            event: TV event to format
            
        Returns:
            Formatted TV event string
        """
        summary = event.summary
        start = event.start_time
        is_premiere = event.is_premiere
        
        # Get time settings from config
        display_time = self.config.time_settings.display_time
        use_24_hour = self.config.time_settings.use_24_hour
        add_leading_zero = self.config.time_settings.add_leading_zero
        
        # Parse datetime components
        dt_parts = parse_event_datetime(start, self.config.timezone)
        
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
                time_str = format_time(
                    dt_parts["hour"], 
                    dt_parts["minute"], 
                    "discord",  # This will be platform-specific when I have more time
                    use_24_hour, 
                    add_leading_zero
                )
                
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
                time_str = format_time(
                    dt_parts["hour"], 
                    dt_parts["minute"], 
                    "discord",  # This will be platform-specific when I have more time
                    use_24_hour, 
                    add_leading_zero
                )
                
                if is_premiere:
                    return f"{time_str}: **{summary}**  🎉"
                else:
                    return f"{time_str}: **{summary}**"
            else:
                if is_premiere:
                    return f" **{summary}**  🎉"
                else:
                    return f"**{summary}**"