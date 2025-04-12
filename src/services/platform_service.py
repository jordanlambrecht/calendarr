#!/usr/bin/env python3
# src/services/platform_service.py

import logging
import traceback
from typing import Dict, List
from datetime import datetime

from models.platform import Platform, DiscordPlatform, SlackPlatform
from models.day import Day
from services.webhook_service import WebhookService
from config.settings import Config
from constants import (
    MAX_DISCORD_EMBEDS_PER_REQUEST, PLATFORM_DISCORD, PLATFORM_SLACK, DISCORD_SUCCESS_CODES, SLACK_SUCCESS_CODES
)

logger = logging.getLogger("service_platform")


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
                DISCORD_SUCCESS_CODES,
                self.config
            )
            
        if self.config.use_slack and self.config.slack_webhook_url:
            platforms[PLATFORM_SLACK] = SlackPlatform(
                self.config.slack_webhook_url,
                self.webhook_service,
                SLACK_SUCCESS_CODES,
                self.config
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
        for platform_name, platform_instance in self.platforms.items():
            results[platform_name] = self._send_to_platform(
                platform_instance,
                days,
                events_summary,
                start_date,
                end_date
            )
        return results
    
    def _send_to_platform(self, platform: Platform, days: List[Day],
                         events_summary: Dict[str, int], start_date: datetime,
                         end_date: datetime) -> bool:
        """
        Send formatted messages to a specific platform
        """
        try:
            logger.info(f"📤 Sending to {platform.__class__.__name__}")

            # Format header using data from events_summary
            header_payload = platform.format_header(
                custom_header=self.config.custom_header,
                start_date=start_date, # Use start_date from arguments
                end_date=end_date,     # Use end_date from arguments
                show_date_range=self.config.show_date_range,
                # Extract counts using correct keys and pass with expected argument names
                tv_count=events_summary.get("total_tv", 0),
                movie_count=events_summary.get("total_movies", 0),
                premiere_count=events_summary.get("total_premieres", 0)
            )

            # Send header
            success = platform.send_message(header_payload)
            if not success:
                logger.error(f"☠️  Failed to send header to {platform.__class__.__name__}")
                # Optionally decide if you want to stop here or try sending days
                # return False # Uncomment to stop if header fails

            # Format and send days (handle platform specifics like Discord batching)
            if isinstance(platform, DiscordPlatform):
                # Batch embeds for Discord
                embeds = [platform.format_day(day) for day in days]
                for i in range(0, len(embeds), MAX_DISCORD_EMBEDS_PER_REQUEST):
                    batch = embeds[i:i + MAX_DISCORD_EMBEDS_PER_REQUEST]
                    day_payload = {"embeds": batch}
                    if not platform.send_message(day_payload):
                        logger.error(f"☠️  Failed to send day batch {i // MAX_DISCORD_EMBEDS_PER_REQUEST + 1} to Discord")
                        success = False # Mark overall success as False if any batch fails
            elif isinstance(platform, SlackPlatform):
                # Send attachments for Slack
                attachments = [platform.format_day(day) for day in days]
                if attachments: # Only send if there are days with events
                    day_payload = {"attachments": attachments}
                    if not platform.send_message(day_payload):
                        logger.error("Failed to send days to Slack")
                        success = False
            else:
                # Handle other potential platforms if added later
                logger.warning(f"⚠️  Sending days not implemented for platform type: {type(platform)}")


            logger.info(f"👍  Successfully sent to {platform.__class__.__name__}: {success}")
            return success

        except Exception as e:
            logger.error(f"☠️  Error sending to {platform.__class__.__name__.lower()}: {e}")
            logger.debug(traceback.format_exc())
            return False