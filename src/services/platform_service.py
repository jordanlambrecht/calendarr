#!/usr/bin/env python3
# src/services/platform_service.py

import logging
import traceback
import json
import time
from typing import Dict, List
from datetime import datetime

from models.platform import Platform, DiscordPlatform, SlackPlatform
from models.day import Day
from services.webhook_service import WebhookService
from config.settings import Config
from constants import (
    MAX_DISCORD_EMBEDS_PER_REQUEST, PLATFORM_DISCORD, PLATFORM_SLACK, DISCORD_SUCCESS_CODES, SLACK_SUCCESS_CODES,DISCORD_EMBED_PAYLOAD_THRESHOLD
)

logger = logging.getLogger("platform_service")


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
        Send formatted messages to a specific platform.
        For Discord, batches embeds intelligently based on payload size.
        For Slack, sends header then all days as attachments.
        """
        overall_success = True

        try:
            logger.info(f"📤 Sending to {platform.__class__.__name__}")

            # 1. Format and Send Header (Common)
            header_payload = platform.format_header(
                custom_header=self.config.custom_header,
                start_date=start_date,
                end_date=end_date,
                show_date_range=self.config.show_date_range,
                tv_count=events_summary.get("total_tv", 0),
                movie_count=events_summary.get("total_movies", 0),
                premiere_count=events_summary.get("total_premieres", 0)
            )
            if not platform.send_message(header_payload):
                logger.error(f"Failed to send header to {platform.__class__.__name__}")
                return False # Stop if header fails

            # 2. Format and Send Days (Platform-specific)
            if isinstance(platform, DiscordPlatform):
                # --- Smart Batching for Discord ---
                logger.info(f"Formatting {len(days)} days for Discord...")
                all_embeds = []
                for day in days:
                    try:
                        embed = platform.format_day(day)
                        if embed: # Only add if embed was successfully created
                            all_embeds.append(embed)
                        else:
                            logger.warning(f"Skipping day {day.name} due to formatting error (no embed generated).")
                    except Exception as e:
                         logger.error(f"☠️  Error formatting day {day.name} for Discord: {e}")
                         logger.debug(traceback.format_exc())
                         overall_success = False # Mark failure but continue formatting

                logger.info(f"🚚  Sending {len(all_embeds)} formatted day embeds to Discord using smart batching...")
                current_batch = []
                current_size = 0 

                for index, embed in enumerate(all_embeds):
                    # Estimate size if this embed is added
                    potential_batch = current_batch + [embed]
                    potential_payload = {"embeds": potential_batch}
                    try:
                        # Calculate length of the JSON string representation
                        potential_size = len(json.dumps(potential_payload))
                    except TypeError as e:
                         logger.error(f"☠️  Error calculating JSON size for embed {index + 1}: {e}. Skipping embed.")
                         overall_success = False
                         continue # Skip this problematic embed

                    # Check if adding this embed exceeds the threshold OR max embed count
                    if current_batch and (potential_size > DISCORD_EMBED_PAYLOAD_THRESHOLD or len(potential_batch) > MAX_DISCORD_EMBEDS_PER_REQUEST):
                        # Send the current batch before it gets too big
                        logger.debug(f"🚛  Batch size threshold reached. Sending batch of {len(current_batch)} embeds.")
                        payload_to_send = {"embeds": current_batch}
                        if not platform.send_message(payload_to_send):
                            logger.error(f"☠️  Failed to send Discord embed batch (size: {current_size}, count: {len(current_batch)})")
                            overall_success = False
                        else:
                            logger.debug(f"👍  Successfully sent Discord embed batch.")

                        # Start new batch with the current embed
                        current_batch = [embed]
                        # Recalculate size for the new batch
                        try:
                            current_size = len(json.dumps({"embeds": current_batch}))
                        except TypeError: # Should not happen if previous check passed, but safety first
                             current_size = 0 # Reset size if error
                             current_batch = [] # Clear batch if error
                             overall_success = False
                             logger.error(f"☠️  Error calculating JSON size for new batch starting with embed {index + 1}. Clearing batch.")

                        time.sleep(0.5) # Pause between sends
                    else:
                        # Add embed to current batch
                        current_batch.append(embed)
                        current_size = potential_size # Update size

                # Send any remaining embeds in the last batch
                if current_batch:
                    logger.debug(f"🚚  Sending final batch of {len(current_batch)} embeds.")
                    payload_to_send = {"embeds": current_batch}
                    if not platform.send_message(payload_to_send):
                        logger.error(f"☠️  Failed to send final Discord embed batch (size: {current_size}, count: {len(current_batch)})")
                        overall_success = False
                    else:
                         logger.debug(f"👍  Successfully sent final Discord embed batch.")
                # --- End Smart Batching ---

            elif isinstance(platform, SlackPlatform):

                attachments = [platform.format_day(day) for day in days if platform.format_day(day)] # Filter out potential None values
                if attachments:
                    day_payload = {"attachments": attachments}
                    if not platform.send_message(day_payload):
                        logger.error("☠️  Failed to send days to Slack")
                        overall_success = False
                # --- End Slack Logic ---
            else:
                logger.warning(f"🚫  Sending days not implemented for platform type: {type(platform)}")

            logger.info(f"✅  Finished sending to {platform.__class__.__name__}. Overall success: {overall_success}")
            return overall_success

        except Exception as e:
            logger.error(f"☠️  Unhandled error during send to {platform.__class__.__name__}: {e}")
            logger.debug(traceback.format_exc())
            return False