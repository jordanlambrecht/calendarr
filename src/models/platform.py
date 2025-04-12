#!/usr/bin/env python3
# src/models/platform.py

import re
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
    PLATFORM_SLACK,
    EPISODE_PATTERN
)
from services.webhook_service import WebhookService

# Regex to identify common SxxExx or NNNxNNN patterns (case-insensitive)
# Allows S prefix, 1-4 digits for season, E or x separator, 1-4 digits for episode
EPISODE_PATTERN = re.compile(EPISODE_PATTERN, re.IGNORECASE)

logger = logging.getLogger("service_platform")


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
        role_id = self.config.discord_mention_role_id
        hide_instructions = self.config.discord_hide_mention_instructions


        logger.debug(f"Discord mention check: Role ID='{role_id}', Hide Instructions='{hide_instructions}' (Type: {type(hide_instructions)})")

        if role_id: # Check if role_id is not None and not empty
            mention_text = f"\n<@&{role_id}>"
            # Simple boolean check now works
            if not hide_instructions:
                mention_text += "\n_If you'd like to be notified when new content is available, join this role!_"

        return {
            "content": f"{header_text}\n\n{subheader}{mention_text}"
        }
    
    def format_tv_event(self, event_item: EventItem, passed_event_handling: str) -> str:
        """
        Format a TV event

        Args:
            event_item: EventItem to format
            passed_event_handling: How to handle passed events (DISPLAY, HIDE, STRIKE)
        """
        time_prefix = f"{event_item.time_str}: " if event_item.time_str else ""
        show_name_to_format = event_item.show_name if event_item.show_name else event_item.summary
        formatted_show = f"**{show_name_to_format}**" # Discord uses **bold**

        episode_details = ""
        number = event_item.episode_number
        title = event_item.episode_title

        if title:
            is_standard_ep_num = bool(number and EPISODE_PATTERN.match(number))
            if is_standard_ep_num:
                # Standard format: Show - SxxExx - *Title*
                episode_details = f" - {number} - *{title}*"
            else:
                # Non-standard number: Show - *Number - Title*
                episode_details = f" - *{number} - {title}*"
        elif number:
            is_standard_ep_num = bool(EPISODE_PATTERN.match(number))
            if is_standard_ep_num:
                # Standard number only: Show - SxxExx
                episode_details = f" - {number}"
            else:
                # Non-standard number only: Show - *Number*
                episode_details = f" - *{number}*"

        formatted = f"{time_prefix}{formatted_show}{episode_details}"
        if event_item.is_premiere:
            formatted += " 🎉"
        if event_item.is_past and passed_event_handling == "STRIKE":
            formatted = f"~~{formatted}~~" # Discord uses ~~strike~~

        return formatted.strip()
    
    def format_movie_event(self, event_item: EventItem, passed_event_handling: str) -> str:
        """Format a movie event for Discord"""
        formatted = f"🎬  **{event_item.summary}**" # Discord uses **bold**
        if event_item.is_past and passed_event_handling == "STRIKE":
            formatted = f"~~{formatted}~~" # Discord uses ~~strike~~
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
        Format a TV event for Slack, applying italics based on content.
        """
        time_prefix = f"{event_item.time_str}: " if event_item.time_str else ""
        show_name_to_format = event_item.show_name if event_item.show_name else event_item.summary
        formatted_show = f"*{show_name_to_format}*" # Slack uses *bold*

        episode_details = ""
        number = event_item.episode_number
        title = event_item.episode_title

        if title:
            is_standard_ep_num = bool(number and EPISODE_PATTERN.match(number))
            if is_standard_ep_num:
                # Standard format: Show - SxxExx - _Title_
                episode_details = f" - {number} - _{title}_"
            else:
                # Non-standard number: Show - _Number - Title_
                episode_details = f" - _{number} - {title}_"
        elif number:
            is_standard_ep_num = bool(EPISODE_PATTERN.match(number))
            if is_standard_ep_num:
                # Standard number only: Show - SxxExx
                episode_details = f" - {number}"
            else:
                # Non-standard number only: Show - _Number_
                episode_details = f" - _{number}_"

        formatted = f"{time_prefix}{formatted_show}{episode_details}"
        if event_item.is_premiere:
            formatted += " 🎉"
        if event_item.is_past and passed_event_handling == "STRIKE":
            formatted = f"~{formatted}~" # Slack uses ~strike~

        return formatted.strip()
    
    def format_movie_event(self, event_item: EventItem, passed_event_handling: str) -> str:
        """Format a movie event for Slack"""
        formatted = f"🎬  *{event_item.summary}*" # Slack uses *bold*
        if event_item.is_past and passed_event_handling == "STRIKE":
            formatted = f"~{formatted}~" # Slack uses ~strike~
        return formatted