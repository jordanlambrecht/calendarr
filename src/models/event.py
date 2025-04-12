#!/usr/bin/env python3
# src/models/event.py

from dataclasses import dataclass, field
from datetime import datetime, date
import re
import pytz
from typing import Dict, Any, Tuple
import icalendar

from constants import PREMIERE_PATTERN, VALID_EVENT_TYPES


@dataclass
class Event:
    """Represents a calendar event"""
    
    summary: str
    start_time: datetime
    source_type: str  # "tv" or "movie"
    raw_event: Dict[str, Any] = field(repr=False)  # Incoming raw iCal event
    
    def __post_init__(self):
        """Validate event data after initialization"""
        if not self.summary:
            raise ValueError("Event summary cannot be empty")
        if not isinstance(self.start_time, datetime):
            raise TypeError("Event start_time must be a datetime object")

        # if not isinstance(self.end_time, datetime):
        #     raise TypeError("Event end_time must be a datetime object")
        
        # Use constant for validation
        if self.source_type not in VALID_EVENT_TYPES:
            raise ValueError(f"Invalid source_type: {self.source_type}, must be one of {VALID_EVENT_TYPES}")

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
    
    def get_event_key(self) -> Tuple[str, date]:
        """
        Get a unique key for identifying this event
        
        This is used for deduplication purposes. Events with the same
        summary (title) and date are considered duplicates.
        
        Returns:
            Tuple of (summary, date) that uniquely identifies the event
        """
        return (self.summary, self.start_time.date())
    
    def __eq__(self, other):
        """
        Compare events for equality
        
        Two events are considered equal if they have the same summary and start date.
        This is useful for deduplication.
        
        Args:
            other: Another Event object to compare with
            
        Returns:
            Boolean indicating if events are equal
        """
        if not isinstance(other, Event):
            return False
        return self.get_event_key() == other.get_event_key()
    
    def __hash__(self):
        """
        Generate hash value for Event
        
        Returns:
            Hash based on the event's key components
        """
        return hash(self.get_event_key())
    
    @classmethod
    def from_ical_event(cls, event: icalendar.Event, timezone: pytz.timezone, source_type: str) -> 'Event':
        """
        Create an Event from an icalendar event
        
        Args:
            event: icalendar event object
            timezone: Timezone object
            source_type: "tv" or "movie"
            
        Returns:
            Event instance
        """
        # Get start time
        start_dt = event.get('DTSTART')
        if start_dt is None:
            raise ValueError("Event has no start time")
            
        start = start_dt.dt
        
        # Get event details
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
        
        
        # Create Event object
        return cls(
            summary=summary,
            start_time=start,
            source_type=source_type,
            raw_event=event
        )