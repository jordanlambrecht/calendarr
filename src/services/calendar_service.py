#!/usr/bin/env python3
# src/services/calendar_service.py

import logging
import requests
import icalendar
import recurring_ical_events
from datetime import datetime
from typing import List

from models.event import Event
from config.settings import Config, CalendarUrl

logger = logging.getLogger("service_cal")


class CalendarService:
    """Service for fetching and processing calendar events"""
    
    def __init__(self, config: Config):
        """
        Initialize with configuration
        
        Args:
            config: Application configuration
        """
        self.config = config
    
    def fetch_events(self, start_date: datetime, end_date: datetime) -> List[Event]:
        """
        Fetch events from all configured calendars
        
        Args:
            start_date: Start date for events
            end_date: End date for events
            
        Returns:
            List of Event objects
        """
        all_events = []
        
        for url_info in self.config.calendar_urls:
            try:
                events = self._fetch_from_calendar(url_info, start_date, end_date)
                all_events.extend(events)
            except Exception as e:
                logger.error(f"Error fetching from calendar {url_info.url}: {str(e)}")
        
        # Sort events by start time
        all_events.sort(key=lambda e: e.start_time)
        
        return all_events
    
    def _fetch_from_calendar(self, calendar_url: CalendarUrl, 
                            start_date: datetime, end_date: datetime) -> List[Event]:
        """
        Fetch events from a single calendar URL
        
        Args:
            calendar_url: Calendar URL object with type
            start_date: Start date for events
            end_date: End date for events
            
        Returns:
            List of Event objects
        """
        url = calendar_url.url
        source_type = calendar_url.type
        
        logger.info(f"⏳  Fetching events for {source_type} between "
                   f"{start_date.strftime('%Y-%m-%d')} and {end_date.strftime('%Y-%m-%d')}")
        
        try:
            response = requests.get(url, timeout=self.config.http_timeout)
            response.raise_for_status()
        except requests.RequestException as e:
            logger.error(f"Failed to fetch iCal from {url}: {str(e)}")
            return []
        
        try:
            calendar = icalendar.Calendar.from_ical(response.content)
            
            # Get recurring events
            ical_events = recurring_ical_events.of(calendar).between(start_date, end_date)
            
            logger.debug(f"🔎 Found {len(list(ical_events))} raw events in calendar from {url}")
            
            # Process events
            processed_events = []
            for event in ical_events:
                # Convert to Event object
                try:
                    # Pass source_type to the factory method
                    processed_event = Event.from_ical_event(event, self.config.timezone_obj, source_type)
                    
                    # Double-check it's in our date range
                    event_date = processed_event.start_time.date()
                    start_range = start_date.date()
                    end_range = end_date.date()
                    
                    if event_date < start_range or event_date > end_range:
                        logger.warning(f"Event date {event_date} is outside range "
                                      f"{start_range} to {end_range}, skipping")
                        continue
                        
                    processed_events.append(processed_event)
                except (KeyError, ValueError, TypeError) as e:
                    logger.warning(f"Skipping invalid event: {str(e)}")
                    continue
            
            return processed_events
            
        except Exception as e:
            logger.error(f"Error processing calendar from {url}: {str(e)}")
            return []