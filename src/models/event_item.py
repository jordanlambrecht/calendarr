#!/usr/bin/env python3
# src/models/event_item.py

from dataclasses import dataclass
from typing import Optional

# Import constants
from constants import EVENT_TYPE_TV, EVENT_TYPE_MOVIE


@dataclass
class EventItem:
    """
    Represents a formatted event item ready for display
    
    This class provides a structured representation of an event
    with formatting metadata, allowing platform-specific code to
    apply the appropriate formatting.
    """
    
    summary: str
    source_type: str  # "tv" or "movie"
    is_premiere: bool = False
    is_past: bool = False
    time_str: Optional[str] = None
    show_name: Optional[str] = None
    episode_number: Optional[str] = None
    episode_title: Optional[str] = None
    
    @property
    def has_time(self) -> bool:
        """
        Check if event has time information
        
        Returns:
            Boolean indicating if event has time
        """
        return self.time_str is not None
    
    @property
    def is_tv(self) -> bool:
        """
        Check if event is a TV show
        
        Returns:
            Boolean indicating if event is a TV show
        """
        # Use constant
        return self.source_type == EVENT_TYPE_TV
    
    @property
    def is_movie(self) -> bool:
        """
        Check if event is a movie
        
        Returns:
            Boolean indicating if event is a movie
        """
        # Use constant
        return self.source_type == EVENT_TYPE_MOVIE