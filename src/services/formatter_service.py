#!/usr/bin/env python3
# src/services/formatter_service.py

import logging
import re
from typing import Dict, List, Tuple
from datetime import datetime
from collections import defaultdict

from models.day import Day
from models.event import Event
from models.event_item import EventItem
from config.settings import Config
from utils.date_utils import get_days_order, get_short_day_name, parse_event_datetime, format_time
from constants import EVENT_TYPE_TV, EVENT_TYPE_MOVIE

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
        tv_count = sum(1 for e in events if e.source_type == EVENT_TYPE_TV)
        movie_count = sum(1 for e in events if e.source_type == EVENT_TYPE_MOVIE)
        
        logger.debug(f"🔢 Processing {tv_count} TV episodes and {movie_count} movies for display")
        
        # Deduplicate events if enabled
        original_event_count = len(events)
        events = self._deduplicate_events(events)
        deduplicated_count = original_event_count - len(events)
        
        # Group events by day and type
        days_data = defaultdict(lambda: {EVENT_TYPE_TV: [], EVENT_TYPE_MOVIE: []})
        premiere_count = 0
        skipped_past_count = 0
        
        for event in events:
            # Skip past events if configured to hide them
            if event.is_past and self.config.passed_event_handling == "HIDE":
                logger.debug(f"⏪  Skipping past event: {event.summary}")
                skipped_past_count += 1
                continue
            
            # Create EventItem from Event
            event_item = self._create_event_item(event)
            
            # Count premieres
            if event_item.is_premiere:
                premiere_count += 1
            
            # Add to the appropriate day and type
            event_date = event.start_time.date()
            days_data[event_date][event_item.source_type].append(event_item)
        
        # Create Day objects
        days = []
        for date_obj, content in sorted(days_data.items()): # Use date_obj to avoid confusion
            day_name_str = date_obj.strftime('%A, %b %d') # Format the name string
            day = Day(
                name=day_name_str, # Pass the formatted name
                date=date_obj, # Pass the original date object
                tv_events=content[EVENT_TYPE_TV],
                movie_events=content[EVENT_TYPE_MOVIE]
            )
            days.append(day)
        
        logger.info(f"📊 Total days processed: {len(days)}")
        for day in days:
            logger.info(f"    ├ {get_short_day_name(day.name)}: {day.total_events} events")
        
        stats = {
            "total_tv": tv_count,
            "total_movies": movie_count,
            "total_premieres": premiere_count,
            "total_deduplicated": deduplicated_count,
            "total_skipped_past": skipped_past_count,
            "start_date": start_date,
            "end_date": end_date
        }

        logger.info("📊 Processed Events Summary:")
        logger.info(f"    ├ TV Episodes: {stats['total_tv']}")
        logger.info(f"    ├ Movies: {stats['total_movies']}")
        logger.info(f"    ├ Premieres: {stats['total_premieres']}")
        if stats['total_deduplicated'] > 0:
             logger.info(f"    ├ Duplicates Removed: {stats['total_deduplicated']}")
        if stats['total_skipped_past'] > 0:
             logger.info(f"    ├ Past Events Skipped: {stats['total_skipped_past']}")

        return days, stats
        
    def _deduplicate_events(self, events: List[Event]) -> List[Event]:
        """
        Deduplicate events with the same summary and day
        
        Args:
            events: List of events to deduplicate
            
        Returns:
            Deduplicated list of events
        """
        # Skip deduplication if disabled in config
        if not self.config.deduplicate_events:
            logger.debug("⚙️ Event deduplication disabled in config")
            return events
            
        unique_events = {}
        
        for event in events:
            key = event.get_event_key()
            
            if key not in unique_events or event.start_time < unique_events[key].start_time:
                unique_events[key] = event
                
        original_count = len(events)
        deduplicated_count = len(unique_events)
        duplicates_removed = original_count - deduplicated_count
        
        if duplicates_removed > 0:
            logger.info(f"🔄 Removed {duplicates_removed} duplicate events")
            
        return list(unique_events.values())
    
    def _create_event_item(self, event: Event) -> EventItem:
        """
        Create an EventItem from an Event
        
        Args:
            event: Event to process
            
        Returns:
            EventItem instance
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
        
        # Format time string if display_time is enabled
        time_str = None
        if display_time:
            time_str = format_time(
                dt_parts["hour"], 
                dt_parts["minute"], 
                use_24_hour=use_24_hour,
                add_leading_zero=add_leading_zero
            )
        
        # Split show name from episode details if possible
        show_name = summary
        episode_number = None
        episode_title = None
        
        # For TV shows, try to parse show, episode number, and title
        if event.source_type == EVENT_TYPE_TV:
            parts = re.split(r'\s+-\s+', summary, 1)
            if len(parts) == 2:
                show_name = parts[0]
                episode_info = parts[1]
                
                # Split again by ' - ' to separate episode number from title
                sub_parts = re.split(r'\s+-\s+', episode_info, 1)
                if len(sub_parts) == 2:
                    episode_number, episode_title = sub_parts
                else:
                    episode_number = episode_info
        
        # Create the EventItem
        return EventItem(
            summary=summary,
            source_type=event.source_type,
            is_premiere=is_premiere,
            is_past=event.is_past,
            time_str=time_str,
            show_name=show_name,
            episode_number=episode_number,
            episode_title=episode_title
        )