#!/usr/bin/env python3
# src/models/day.py

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime

from models.event_item import EventItem


@dataclass
class Day:
    """Represents a day with TV and movie events"""
    
    name: str  # something like "Monday, Jan 01"
    tv_events: List[EventItem] = field(default_factory=list)
    movie_events: List[EventItem] = field(default_factory=list)
    date: Optional[datetime] = None  # Full datetime object
    
    @property
    def day_name(self) -> str:
        """
        Get the name of the day (Monday, Tuesday, etc.)
        
        Returns:
            Name of the day
        """
        return self.name.split(',')[0] if ',' in self.name else self.name
    
    @property
    def has_events(self) -> bool:
        """
        Check if day has any events
        
        Returns:
            Boolean indicating if day has any events
        """
        return bool(self.tv_events or self.movie_events)
    
    @property
    def total_events(self) -> int:
        """
        Get total number of events
        
        Returns:
            Number of events
        """
        return len(self.tv_events) + len(self.movie_events)
    
    @property
    def premiere_count(self) -> int:
        """
        Count premieres in TV events
        
        Returns:
            Number of premieres
        """
        return sum(1 for event in self.tv_events if event.is_premiere)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary representation
        
        Returns:
            Dictionary with day data
        """
        return {
            "name": self.name,
            "tv": [self._event_item_to_dict(e) for e in self.tv_events],
            "movie": [self._event_item_to_dict(e) for e in self.movie_events],
            "date": self.date.isoformat() if self.date else None,
            "total_events": self.total_events,
            "premiere_count": self.premiere_count
        }
    
    def _event_item_to_dict(self, event_item: EventItem) -> Dict[str, Any]:
        """
        Convert an EventItem to dictionary
        
        Args:
            event_item: EventItem to convert
            
        Returns:
            Dictionary representation
        """
        return {
            "summary": event_item.summary,
            "source_type": event_item.source_type,
            "is_premiere": event_item.is_premiere,
            "is_past": event_item.is_past,
            "time_str": event_item.time_str,
            "show_name": event_item.show_name,
            "episode_number": event_item.episode_number,
            "episode_title": event_item.episode_title
        }