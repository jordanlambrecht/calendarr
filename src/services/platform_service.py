#!/usr/bin/env python3
# src/services/platform_service.py

import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

from models.platform import Platform, DiscordPlatform, SlackPlatform
from models.day import Day
from services.webhook_service import WebhookService
from config.settings import Config
from constants import (
    MAX_DISCORD_EMBEDS_PER_REQUEST, PLATFORM_DISCORD, PLATFORM_SLACK, DISCORD_SUCCESS_CODES, SLACK_SUCCESS_CODES
)

logger = logging.getLogger("service - platform")


class PlatformService:
    """Service for sending messages to platforms"""
    
    def __init__(self, config: Config):
        """
        Initialize with configuration
        
        Args:
            config: Application configuration
        """
        self.config = config
        self.webhook_service = WebhookService(http_timeout=config.http_timeout)
        self.platforms = self._initialize_platforms()
    
    def _initialize_platforms(self) -> Dict[str, Platform]:
        """
        Initialize platform instances based on config
        
        Returns:
            Dictionary mapping platform names to Platform instances
        """
        platforms = {}
        
        if self.config.use_discord and self.config.discord_webhook_url:
            platforms[PLATFORM_DISCORD] = DiscordPlatform(
                self.config.discord_webhook_url,
                self.webhook_service,
                DISCORD_SUCCESS_CODES
            )
            
        if self.config.use_slack and self.config.slack_webhook_url:
            platforms[PLATFORM_SLACK] = SlackPlatform(
                self.config.slack_webhook_url,
                self.webhook_service,
                SLACK_SUCCESS_CODES
            )
            
        return platforms
    
    def send_to_platforms(self, days: List[Day], events_summary: Dict[str, int],
                         start_date: datetime, end_date: datetime) -> Dict[str, bool]:
        """
        Send calendar data to all enabled platforms
        
        Args:
            days: List of Day objects to send
            events_summary: Dictionary with event counts
            start_date: Start date of range
            end_date: End date of range
            
        Returns:
            Dictionary mapping platform names to success status
        """
        results = {}
        
        for platform_name, platform in self.platforms.items():
            logger.info(f"📤 Sending to {platform_name.capitalize()}")
            
            try:
                success = self._send_to_platform(
                    platform, 
                    days, 
                    events_summary,
                    start_date, 
                    end_date
                )
                results[platform_name] = success
                logger.info(f"Successfully sent to {platform_name.capitalize()}: {success}")
            except Exception as e:
                logger.error(f"Error sending to {platform_name}: {str(e)}")
                results[platform_name] = False
        
        return results
    
    def _send_to_platform(self, platform: Platform, days: List[Day], 
                         events_summary: Dict[str, int], start_date: datetime, 
                         end_date: datetime) -> bool:
        """
        Send to a specific platform
        
        Args:
            platform: Platform instance
            days: List of Day objects
            events_summary: Dictionary with event counts
            start_date: Start date of range
            end_date: End date of range
            
        Returns:
            Boolean indicating success
        """
        # Format header
        header = platform.format_header(
            self.config.custom_header,
            start_date,
            end_date,
            self.config.show_date_range,
            events_summary["tv_count"],
            events_summary["movie_count"],
            events_summary["premiere_count"]
        )
        
        # Send header
        if not platform.send_message(header):
            return False
        
        # Format and send days
        # For Discord, we need to batch embeds
        if isinstance(platform, DiscordPlatform):
            # Format all embeds
            embeds = [platform.format_day(day) for day in days]
            
            # Group embeds into batches
            embed_batches = [
                embeds[i:i+MAX_DISCORD_EMBEDS_PER_REQUEST] 
                for i in range(0, len(embeds), MAX_DISCORD_EMBEDS_PER_REQUEST)
            ]
            
            # Send each batch
            for batch in embed_batches:
                payload = {"embeds": batch}
                if not platform.send_message(payload):
                    return False
                
            return True
        elif isinstance(platform, SlackPlatform):
            # For Slack, we create attachments
            attachments = [platform.format_day(day) for day in days]
            
            # Send all attachments at once
            payload = {"attachments": attachments}
            return platform.send_message(payload)
        else:
            # Generic implementation for other platforms
            for day in days:
                day_payload = platform.format_day(day)
                if not platform.send_message(day_payload):
                    return False
            
            return True