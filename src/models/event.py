#!/usr/bin/env python3
# src/models/event.py

from dataclasses import dataclass, field
from datetime import datetime, date
import re
import pytz
from typing import Dict, Any

from constants import PREMIERE_PATTERN


@dataclass
class Event:
    """Represents a calendar event"""
    
    summary: str
    start_time: datetime
    source_type: str  # "tv" or "movie"
    raw_event: Dict[str, Any] = field(repr=False)  # Original iCal event
    
    @property
    def is_premiere(self) -> bool:
        """
        Check if event is a season premiere
        
        Returns:
            Boolean indicating if event is a premiere
        """
        return bool(re.search(PREMIERE_PATTERN, self.summary, re.IGNORECASE))
    
    @property
    def is_past(self) -> bool:
        """
        Check if event has already occurred
        
        Returns:
            Boolean indicating if event is in the past
        """
        # Get current time with timezone
        local_tz = self.start_time.tzinfo or pytz.UTC
        now = datetime.now(local_tz)
        
        # Return True if event is in the past
        return self.start_time < now
    
    @property
    def day_key(self) -> str:
        """
        Get day key for grouping events
        
        Returns:
            String key in format "Day, Mon DD"
        """
        return self.start_time.strftime('%A, %b %d')
    
    @classmethod
    def from_ical_event(cls, event: Dict[str, Any], timezone: pytz.timezone) -> 'Event':
        """
        Create Event from an iCal event
        
        Args:
            event: iCal event dictionary
            timezone: Timezone to localize datetime
            
        Returns:
            Event instance
            
        Raises:
            ValueError: If event doesn't have required fields
            TypeError: If event datetime is invalid
        """
        # Get start time
        start_dt = event.get('DTSTART')
        if start_dt is None:
            raise ValueError("Event has no start time")
            
        start = start_dt.dt
        
        # Get event details
        source_type = event.get("SOURCE_TYPE", "tv")
        summary = event.get('SUMMARY', 'Untitled Event')
        
        # Handle date-only events
        if isinstance(start, date) and not isinstance(start, datetime):
            # Convert to datetime at midnight
            from datetime import time
            start = datetime.combine(start, time.min)
            # Apply timezone
            start = timezone.localize(start)
        elif isinstance(start, datetime):
            # Ensure datetime is timezone-aware
            if start.tzinfo is None:
                start = timezone.localize(start)
            else:
                start = start.astimezone(timezone)
        else:
            raise TypeError(f"Unexpected datetime type: {type(start)}")
        
        return cls(
            summary=summary,
            start_time=start,
            source_type=source_type,
            raw_event=event
        )