#!/usr/bin/env python3
# src/models/platform.py

from abc import ABC, abstractmethod
from typing import Dict, List, Any
from datetime import datetime
import logging

from models.day import Day
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
    
    def __init__(self, webhook_url: str, webhook_service: WebhookService, success_codes: List[int]):
        """
        Initialize platform
        
        Args:
            webhook_url: URL to send messages to
            webhook_service: Service for sending webhook requests
            success_codes: HTTP status codes that indicate success
        """
        self.webhook_url = webhook_url
        self.webhook_service = webhook_service
        self.success_codes = success_codes
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


class DiscordPlatform(Platform):
    """Discord implementation of Platform"""
    
    def __init__(self, webhook_url: str, webhook_service: WebhookService, 
                 success_codes: List[int], config: Config):
        """Initialize with configuration"""
        super().__init__(webhook_url, webhook_service, success_codes)
        self.config = config
        
    def _initialize_day_colors(self) -> Dict[str, int]:
        """
        Initialize color scheme for days
        
        Returns:
            Dictionary mapping day names to Discord color integers
        """
        return get_day_colors(PLATFORM_DISCORD, True)
    
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
        
        # Combine tv and movie listings
        description = ""
        if day.tv_events:
            description += "\n".join(day.tv_events)
            if day.movie_events:
                description += "\n\n"
        
        if day.movie_events:
            description += "**MOVIES**\n" + "\n".join(day.movie_events)
        
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
            mention_text = f"\n\n<@&{role_id}> "
    
        
        return {
            "content": f"{header_text}\n\n{subheader}{mention_text}"
        }


class SlackPlatform(Platform):
    """Slack implementation of Platform"""
    
    def _initialize_day_colors(self) -> Dict[str, str]:
        """
        Initialize color scheme for days
        
        Returns:
            Dictionary mapping day names to Slack color hex strings
        """
        return get_day_colors(PLATFORM_SLACK, True)
    
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
        
        # Format day content for Slack
        day_content = self._format_slack_day_content(day)
        
        return {
            "color": color,
            "title": day.name,
            "text": day_content,
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
    
    def _format_slack_day_content(self, day: Day) -> str:
        """
        Format day content for Slack
        
        Args:
            day: Day to format
            
        Returns:
            Formatted day content string
        """
        # First combine tv and movie events
        day_content = ""
        if day.tv_events:
            day_content += "\n".join(day.tv_events)
            if day.movie_events:
                day_content += "\n\n"
        
        if day.movie_events:
            day_content += "**MOVIES**\n" + "\n".join(day.movie_events)
        
        # Now format for Slack
        formatted_lines = []
        for line in day_content.split('\n'):
            if line.startswith("**MOVIES"):
                formatted_lines.append(line.replace("**", "*"))
                continue
                
            # For TV shows with time
            if ":" in line and "**" in line:
                parts = line.split(":", 1)
                time_part = parts[0] + ":"
                content_part = parts[1].strip()
                
                # Extract the show name while preserving bold
                if " - " in content_part:
                    show_and_episode = content_part.split(" - ", 1)
                    show_name = show_and_episode[0]
                    episode_info = " - " + show_and_episode[1]
                    # Make sure only show name is bold in Slack
                    if "**" in show_name:
                        show_name = show_name.replace("**", "*")
                    formatted_line = f"{time_part} {show_name}{episode_info}"
                else:
                    # If no dash separator, just convert all bold markers
                    formatted_line = line.replace("**", "*")
                
                formatted_lines.append(formatted_line)
            else:
                # For lines without time or special format
                formatted_lines.append(line.replace("**", "*"))
        
        return "\n".join(formatted_lines)