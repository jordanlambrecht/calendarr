#!/usr/bin/env python3
# src/models/platform.py

import re
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from datetime import datetime
import logging
import traceback
from models.day import Day
from models.event_item import EventItem
from config.settings import Config
from utils.format_utils import (
    format_header_text, format_subheader_text, get_day_colors,
    format_timezone_line
)
from constants import (
    MENTION_ROLE_ID_MSG,
    NO_CONTENT_TODAY_MSG,
    PLATFORM_DISCORD,
    PLATFORM_SLACK,
    EPISODE_PATTERN,
    # Import styling constants
    DISCORD_BOLD_START, DISCORD_BOLD_END, DISCORD_ITALIC_START, DISCORD_ITALIC_END, DISCORD_STRIKE_START, DISCORD_STRIKE_END,
    SLACK_BOLD_START, SLACK_BOLD_END, SLACK_ITALIC_START, SLACK_ITALIC_END, SLACK_STRIKE_START, SLACK_STRIKE_END,
    ITALIC_START, ITALIC_END # Universal italic
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
    
    def format_day(self, day: Day) -> Optional[Dict[str, Any]]:
        """
        Format a day as Discord embed.

        Args:
            day: Day to format

        Returns:
            Discord embed object dictionary, or None if formatting fails.
        """
        try:
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
                    description += "\n\n" # Blank line between TV and Movies

            if movie_formatted:
                description += f"{DISCORD_BOLD_START}MOVIES{DISCORD_BOLD_END}\n" + "\n".join(movie_formatted)

            # Ensure description is not empty before returning
            if not description:
                description = f"{DISCORD_ITALIC_START}{NO_CONTENT_TODAY_MSG}{DISCORD_ITALIC_END}"

            # --- Assemble Embed ---
            embed_dict = {
                "title": day.name,
                "description": description,
                "color": color
            }

            return embed_dict

        except Exception as e:
            logger.error(f"☠️ Error formatting day {day.name} in DiscordPlatform.format_day: {e}")
            logger.debug(traceback.format_exc())
            return None # Return None if formatting fails
    
    def format_header(self, custom_header: str, start_date: datetime,
                     end_date: datetime, show_date_range: bool,
                     tv_count: int, movie_count: int, premiere_count: int) -> Dict[str, Any]:

        logger.debug("Entering DiscordPlatform.format_header")
        final_content = ""

        try:
            # Create header text
            header_text = format_header_text(custom_header, start_date, end_date, show_date_range)
            logger.debug(f"🖌️  format_header - header_text: '{header_text}'")

            # Get subheader text, already bolded for Discord
            subheader = format_subheader_text(tv_count, movie_count, premiere_count, PLATFORM_DISCORD)
            logger.debug(f"🖌️  format_header - subheader: '{subheader.strip()}'") 

            # --- Get Timezone Line if needed ---
            timezone_line = ""
            if self.config.show_timezone_in_subheader:
                timezone_line = format_timezone_line(self.config.timezone_obj, PLATFORM_DISCORD)
            logger.debug(f"🖌️  format_header - timezone_line: '{timezone_line}'")

            # --- Create Mention Text ---
            mention_text = ""
            role_id = self.config.discord_mention_role_id
            hide_instructions = self.config.discord_hide_mention_instructions
            if role_id:
                mention_text = f"<@&{role_id}>"
                if not hide_instructions:
                    mention_text += f"\n{ITALIC_START}{MENTION_ROLE_ID_MSG}{ITALIC_END}"
            logger.debug(f"🖌️  format_header - mention_text: '{mention_text}'")

            # --- Combine parts ---
            logger.debug("🖌️  format_header - Attempting to assemble final_content")
            safe_header = str(header_text) if header_text is not None else ""
            safe_subheader = str(subheader).rstrip() if subheader is not None else "" # Use rstrip here

            final_content = f"{safe_header}\n\n{safe_subheader}" # Initial assignment
            logger.debug("🖌️  format_header - Assembled base final_content")

            if timezone_line:
                final_content += f"\n\n{str(timezone_line)}"
                logger.debug("🖌️  format_header - Added timezone_line to final_content")
            if mention_text:
                final_content += f"\n\n{str(mention_text)}"
                logger.debug("🖌️  format_header - Added mention_text to final_content")

            logger.debug("🖌️  format_header - Successfully assembled final_content")

        except Exception as e:
             logger.error(f"☠️ Error during Discord content assembly in format_header: {e}")
             logger.debug(traceback.format_exc())
             # Fallback: Try returning at least the header text if assembly fails
             try:
                 final_content = str(header_text) if header_text is not None else "Error generating message content."
                 logger.debug("🖌️  format_header - Assigned fallback content after error")
             except Exception as fallback_e:
                 logger.error(f"☠️ Error assigning fallback content in format_header: {fallback_e}")
                 final_content = "Error generating message content." # Absolute fallback

        logger.debug(f"🖌️  format_header - Returning final_content:\n'''\n{final_content}\n'''")
        return {
            "content": final_content
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

        formatted_show = f"{DISCORD_BOLD_START}{show_name_to_format}{DISCORD_BOLD_END}"

        episode_details = ""
        number = event_item.episode_number
        title = event_item.episode_title

        if title:
            is_standard_ep_num = bool(number and EPISODE_PATTERN.match(number))
            if is_standard_ep_num:
                episode_details = f" - {number} - {DISCORD_ITALIC_START}{title}{DISCORD_ITALIC_END}"
            else:
                episode_details = f" - {DISCORD_ITALIC_START}{number} - {title}{DISCORD_ITALIC_END}"
        elif number:
            is_standard_ep_num = bool(EPISODE_PATTERN.match(number))
            if is_standard_ep_num:
                # Standard number only: Show - SxxExx
                episode_details = f" - {number}"
            else:
                # Non-standard number only: Show - *Number*
                episode_details = f" - {DISCORD_ITALIC_START}{number}{DISCORD_ITALIC_END}"

        formatted = f"{time_prefix}{formatted_show}{episode_details}"
        if event_item.is_premiere:
            formatted += " 🎉"
        if event_item.is_past and passed_event_handling == "STRIKE":
            formatted = f"{DISCORD_STRIKE_START}{formatted}{DISCORD_STRIKE_END}"

        return formatted.strip()
    
    def format_movie_event(self, event_item: EventItem, passed_event_handling: str) -> str:
        """Format a movie event for Discord"""
        movie_name_to_format = event_item.show_name if event_item.show_name else event_item.summary

        formatted = f"🎬  {DISCORD_BOLD_START}{movie_name_to_format}{DISCORD_BOLD_END}"

        if event_item.is_past and passed_event_handling == "STRIKE":
            formatted = f"{DISCORD_STRIKE_START}{formatted}{DISCORD_STRIKE_END}"

        return formatted.strip()


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
            # Add blank line only if both TV and Movies exist
            if movie_formatted:
                text += "\n\n"

        if movie_formatted:
            # Use Slack bold constants for the header
            text += f"{SLACK_BOLD_START}MOVIES{SLACK_BOLD_END}\n" + "\n".join(movie_formatted)

        # Ensure text is not empty before returning
        if not text:
            text = "_No releases scheduled for this day._" # Or some placeholder

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
        # Create header text and date range text
        header_text = format_header_text(custom_header, start_date, end_date, show_date_range)

        # Create subheader text (without timezone)
        subheader_text = format_subheader_text(tv_count, movie_count, premiere_count, PLATFORM_SLACK).strip()

        # Get timezone line if needed
        timezone_line = ""
        if self.config.show_timezone_in_subheader:
            timezone_line = format_timezone_line(self.config.timezone_obj, PLATFORM_SLACK)

        # Combine subheader and timezone for the section block's text
        section_block_text = ""
        if subheader_text and timezone_line:
            # Both exist, add newline between them
            section_block_text = f"{subheader_text}\n\n{timezone_line}"
        elif subheader_text:
            # Only subheader exists
            section_block_text = subheader_text
        elif timezone_line:
            # Only timezone exists (not super likely, but handle)
            section_block_text = timezone_line
        # If both are empty, section_block_text remains ""

        # --- Assemble Blocks ---
        blocks = []

        # Add Header Block
        blocks.append({
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": header_text
            }
        })

        # Add Section Block only if it has content
        if section_block_text:
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": section_block_text
                }
            })

        return {
            "blocks": blocks
        }

    def format_tv_event(self, event_item: EventItem, passed_event_handling: str) -> str:
        """
        Format a TV event for Slack, applying italics based on content.
        """
        time_prefix = f"{event_item.time_str}: " if event_item.time_str else ""
        show_name_to_format = event_item.show_name if event_item.show_name else event_item.summary
        formatted_show = f"{SLACK_BOLD_START}{show_name_to_format}{SLACK_BOLD_END}"

        episode_details = ""
        number = event_item.episode_number
        title = event_item.episode_title

        if title:
            is_standard_ep_num = bool(number and EPISODE_PATTERN.match(number))
            if is_standard_ep_num:
                episode_details = f" - {number} - {SLACK_ITALIC_START}{title}{SLACK_ITALIC_END}"
            else:
                episode_details = f" - {SLACK_ITALIC_START}{number} - {title}{SLACK_ITALIC_END}"
        elif number:
            is_standard_ep_num = bool(EPISODE_PATTERN.match(number))
            if is_standard_ep_num:
                episode_details = f" - {number}"
            else:
                episode_details = f" - {SLACK_ITALIC_START}{number}{SLACK_ITALIC_END}"

        formatted = f"{time_prefix}{formatted_show}{episode_details}"
        if event_item.is_premiere:
            formatted += " 🎉"
        if event_item.is_past and passed_event_handling == "STRIKE":
            formatted = f"{SLACK_STRIKE_START}{formatted}{SLACK_STRIKE_END}"

        return formatted.strip()
    
    def format_movie_event(self, event_item: EventItem, passed_event_handling: str) -> str:
        """Format a movie event for Slack"""
        movie_name_to_format = event_item.show_name if event_item.show_name else event_item.summary
        formatted = f"🎬  {SLACK_BOLD_START}{movie_name_to_format}{SLACK_BOLD_END}"

        if event_item.is_past and passed_event_handling == "STRIKE":
            formatted = f"{SLACK_STRIKE_START}{formatted}{SLACK_STRIKE_END}"

        return formatted.strip()