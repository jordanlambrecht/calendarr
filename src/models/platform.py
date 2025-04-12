#!/usr/bin/env python3
# src/models/platform.py

from abc import ABC, abstractmethod
from typing import Dict, List, Any
from datetime import datetime
import logging

from models.day import Day
from models.event_item import EventItem
from config.settings import Config
from utils.format_utils import (
    format_header_text, format_subheader_text, get_day_colors, join_content_parts,
    build_content_summary_parts
)
from constants import (
    PLATFORM_DISCORD,
    PLATFORM_SLACK
)
from services.webhook_service import WebhookService

logger = logging.getLogger("platform")


class Platform(ABC):
    """Abstract base class for messaging platforms"""
    
    def __init__(self, webhook_url: str, webhook_service: WebhookService, success_codes: List[int], config: Config  ):
        """
        Initialize platform
        
        Args:
            webhook_url: URL to send messages to
            webhook_service: Service for sending webhook requests
            success_codes: HTTP status codes that indicate success
            config: Application configuration
        """
        self.webhook_url = webhook_url
        self.webhook_service = webhook_service
        self.success_codes = success_codes
        self.config = config
        self.day_colors = self._initialize_day_colors()
    
    @abstractmethod
    def _initialize_day_colors(self) -> Dict[str, Any]:
        """
        Initialize color scheme for days
        
        Returns:
            Dictionary mapping day names to colors
        """
        pass
    
    @abstractmethod
    def format_day(self, day: Day) -> Dict[str, Any]:
        """
        Format a day for this platform
        
        Args:
            day: Day to format
            
        Returns:
            Platform-specific day representation
        """
        pass
    
    @abstractmethod
    def format_header(self, custom_header: str, start_date: datetime, 
                     end_date: datetime, show_date_range: bool,
                     tv_count: int, movie_count: int, premiere_count: int) -> Dict[str, Any]:
        """
        Format header for this platform
        
        Args:
            custom_header: Header text
            start_date: Start date
            end_date: End date
            show_date_range: Whether to show date range
            tv_count: Number of TV episodes
            movie_count: Number of movie releases
            premiere_count: Number of premieres
            
        Returns:
            Platform-specific header representation
        """
        pass
    
    def send_message(self, payload: Dict[str, Any]) -> bool:
        """
        Send message to platform
        
        Args:
            payload: Data to send
            
        Returns:
            Whether message was sent successfully
        """
        return self.webhook_service.send_request(
            self.webhook_url,
            payload,
            self.success_codes
        )
    
    @abstractmethod
    def format_tv_event(self, event_item: EventItem, passed_event_handling: str) -> str:
        """
        Format a TV event for this platform
        
        Args:
            event_item: EventItem to format
            passed_event_handling: How to handle passed events (DISPLAY, HIDE, STRIKE)
            
        Returns:
            Formatted string for this platform
        """
        pass
    
    @abstractmethod
    def format_movie_event(self, event_item: EventItem, passed_event_handling: str) -> str:
        """
        Format a movie event for this platform
        
        Args:
            event_item: EventItem to format
            passed_event_handling: How to handle passed events (DISPLAY, HIDE, STRIKE)
            
        Returns:
            Formatted string for this platform
        """
        pass


class  DiscordPlatform(Platform):
    """Discord implementation of Platform"""
    
    def __init__(self, webhook_url: str, webhook_service: WebhookService, 
                 success_codes: List[int], config: Config):
        """Initialize with configuration"""
        super().__init__(webhook_url, webhook_service, success_codes, config)

        
    def _initialize_day_colors(self) -> Dict[str, int]:
        """
        Initialize color scheme for days
        
        Returns:
            Dictionary mapping day names to Discord color integers
        """
        return get_day_colors(PLATFORM_DISCORD, self.config.start_week_on_monday)
    
    def format_day(self, day: Day) -> Dict[str, Any]:
        """
        Format a day as Discord embed
        
        Args:
            day: Day to format
            
        Returns:
            Discord embed object
        """
        # Get color for this day
        color = self.day_colors.get(day.day_name, 0)
        
        # Format TV and movie events
        tv_formatted = [
            self.format_tv_event(event, self.config.passed_event_handling) 
            for event in day.tv_events
        ]
        
        movie_formatted = [
            self.format_movie_event(event, self.config.passed_event_handling) 
            for event in day.movie_events
        ]
        
        # Combine tv and movie listings
        description = ""
        if tv_formatted:
            description += "\n".join(tv_formatted)
            if movie_formatted:
                description += "\n\n"
        
        if movie_formatted:
            description += "**MOVIES**\n" + "\n".join(movie_formatted)
        
        return {
            "title": day.name,
            "description": description,
            "color": color
        }
    
    def format_header(self, custom_header: str, start_date: datetime, 
                     end_date: datetime, show_date_range: bool,
                     tv_count: int, movie_count: int, premiere_count: int) -> Dict[str, Any]:
        """
        Format Discord header message
        
        Args:
            custom_header: Header text
            start_date: Start date
            end_date: End date
            show_date_range: Whether to show date range
            tv_count: Number of TV episodes
            movie_count: Number of movie releases
            premiere_count: Number of premieres
            
        Returns:
            Discord message object
        """
        # Create header with formatted date
        header_text = format_header_text(custom_header, start_date, end_date, show_date_range)
        subheader = format_subheader_text(tv_count, movie_count, premiere_count)

        mention_text = ""
        if hasattr(self, 'config') and self.config.discord_mention_role_id:
            role_id = self.config.discord_mention_role_id
            mention_text = f"\n<@&{role_id}> "
    
        return {
            "content": f"{header_text}\n\n{subheader}{mention_text}"
        }
    
    def format_tv_event(self, event_item: EventItem, passed_event_handling: str) -> str:
        """
        Format a TV event for Discord
        
        Args:
            event_item: EventItem to format
            passed_event_handling: How to handle passed events (DISPLAY, HIDE, STRIKE)
            
        Returns:
            Formatted string for Discord
        """
        # Build the formatted string
        if event_item.time_str:
            if event_item.episode_title:
                formatted = f"{event_item.time_str}: **{event_item.show_name}** - {event_item.episode_number} - *{event_item.episode_title}*"
            elif event_item.episode_number:
                formatted = f"{event_item.time_str}: **{event_item.show_name}** - {event_item.episode_number}"
            else:
                formatted = f"{event_item.time_str}: **{event_item.summary}**"
        else:
            if event_item.episode_title:
                formatted = f"**{event_item.show_name}** - {event_item.episode_number} - *{event_item.episode_title}*"
            elif event_item.episode_number:
                formatted = f"**{event_item.show_name}** - {event_item.episode_number}"
            else:
                formatted = f"**{event_item.summary}**"
        
        # Add premiere emoji if applicable
        if event_item.is_premiere:
            formatted += "  🎉"
        
        # Apply strikethrough for past events if configured
        if event_item.is_past and passed_event_handling == "STRIKE":
            formatted = f"~~{formatted}~~"
        
        return formatted
    
    def format_movie_event(self, event_item: EventItem, passed_event_handling: str) -> str:
        """
        Format a movie event for Discord
        
        Args:
            event_item: EventItem to format
            passed_event_handling: How to handle passed events (DISPLAY, HIDE, STRIKE)
            
        Returns:
            Formatted string for Discord
        """
        # Format movie title
        formatted = f"🎬  **{event_item.summary}**"
        
        # Apply strikethrough for past events if configured
        if event_item.is_past and passed_event_handling == "STRIKE":
            formatted = f"~~{formatted}~~"
        
        return formatted


class SlackPlatform(Platform):
    """Slack implementation of Platform"""
    
    def __init__(self, webhook_url: str, webhook_service: WebhookService, 
                 success_codes: List[int], config: Config):
        """Initialize with configuration"""
        super().__init__(webhook_url, webhook_service, success_codes, config)
        # self.config = config
    
    def _initialize_day_colors(self) -> Dict[str, str]:
        """
        Initialize color scheme for days
        
        Returns:
            Dictionary mapping day names to Slack color hex strings
        """
        return get_day_colors(PLATFORM_SLACK, self.config.start_week_on_monday)
    
    def format_day(self, day: Day) -> Dict[str, Any]:
        """
        Format a day as Slack attachment
        
        Args:
            day: Day to format
            
        Returns:
            Slack attachment object
        """
        # Get color for this day
        color = self.day_colors.get(day.day_name, "#000000")
        
        # Format TV and movie events
        tv_formatted = [
            self.format_tv_event(event, self.config.passed_event_handling) 
            for event in day.tv_events
        ]
        
        movie_formatted = [
            self.format_movie_event(event, self.config.passed_event_handling) 
            for event in day.movie_events
        ]
        
        # Combine tv and movie listings
        text = ""
        if tv_formatted:
            text += "\n".join(tv_formatted)
            if movie_formatted:
                text += "\n\n"
        
        if movie_formatted:
            text += "*MOVIES*\n" + "\n".join(movie_formatted)
        
        return {
            "color": color,
            "title": day.name,
            "text": text,
            "mrkdwn_in": ["text"]
        }
    
    def format_header(self, custom_header: str, start_date: datetime, 
                     end_date: datetime, show_date_range: bool,
                     tv_count: int, movie_count: int, premiere_count: int) -> Dict[str, Any]:
        """
        Format Slack header message
        
        Args:
            custom_header: Header text
            start_date: Start date
            end_date: End date
            show_date_range: Whether to show date range
            tv_count: Number of TV episodes
            movie_count: Number of movie releases
            premiere_count: Number of premieres
            
        Returns:
            Slack message object with blocks
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
        
        # Get content summary
        content_parts = build_content_summary_parts(
            tv_count, movie_count, premiere_count, PLATFORM_SLACK
        )
        message_text = join_content_parts(content_parts, PLATFORM_SLACK)
        
        return {
            "blocks": [
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
        }
    
    def format_tv_event(self, event_item: EventItem, passed_event_handling: str) -> str:
        """
        Format a TV event for Slack
        
        Args:
            event_item: EventItem to format
            passed_event_handling: How to handle passed events (DISPLAY, HIDE, STRIKE)
            
        Returns:
            Formatted string for Slack
        """
        # Build the formatted string
        if event_item.time_str:
            time_part = f"{event_item.time_str}: "
            
            if event_item.episode_title:
                formatted = f"{time_part}*{event_item.show_name}* - {event_item.episode_number} - _{event_item.episode_title}_"
            elif event_item.episode_number:
                formatted = f"{time_part}*{event_item.show_name}* - {event_item.episode_number}"
            else:
                formatted = f"{time_part}*{event_item.summary}*"
        else:
            if event_item.episode_title:
                formatted = f"*{event_item.show_name}* - {event_item.episode_number} - _{event_item.episode_title}_"
            elif event_item.episode_number:
                formatted = f"*{event_item.show_name}* - {event_item.episode_number}"
            else:
                formatted = f"*{event_item.summary}*"
        
        # Add premiere emoji if applicable
        if event_item.is_premiere:
            formatted += "  🎉"
        
        # Apply strikethrough for past events if configured
        if event_item.is_past and passed_event_handling == "STRIKE":
            formatted = f"~{formatted}~"
        
        return formatted
    
    def format_movie_event(self, event_item: EventItem, passed_event_handling: str) -> str:
        """
        Format a movie event for Slack
        
        Args:
            event_item: EventItem to format
            passed_event_handling: How to handle passed events (DISPLAY, HIDE, STRIKE)
            
        Returns:
            Formatted string for Slack
        """
        # Format movie title
        formatted = f"🎬  *{event_item.summary}*"
        
        # Apply strikethrough for past events if configured
        if event_item.is_past and passed_event_handling == "STRIKE":
            formatted = f"~{formatted}~"
        
        return formatted