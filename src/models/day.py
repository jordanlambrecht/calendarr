#!/usr/bin/env python3
# src/models/day.py

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime


@dataclass
class Day:
    """Represents a day with TV and movie events"""
    
    name: str  # e.g., "Monday, Jan 01"
    tv_events: List[str] = field(default_factory=list)
    movie_events: List[str] = field(default_factory=list)
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
        return sum(1 for event in self.tv_events if "🎉" in event)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary representation
        
        Returns:
            Dictionary with day data
        """
        return {
            "name": self.name,
            "tv": self.tv_events,
            "movie": self.movie_events,
            "date": self.date.isoformat() if self.date else None,
            "total_events": self.total_events,
            "premiere_count": self.premiere_count
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Day':
        """
        Create Day from dictionary
        
        Args:
            data: Dictionary with day data
            
        Returns:
            Day instance
        """
        date = None
        if data.get("date"):
            try:
                date = datetime.fromisoformat(data["date"])
            except (ValueError, TypeError):
                pass
                
        return cls(
            name=data.get("name", ""),
            tv_events=data.get("tv", []),
            movie_events=data.get("movie", []),
            date=date
        )