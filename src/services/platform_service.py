#!/usr/bin/env python3
# src/services/platform_service.py

import logging
import traceback
import json
import time
import os
import re
from typing import Dict, List, Optional
from datetime import datetime

from models.platform import Platform, DiscordPlatform, SlackPlatform
from models.day import Day
from services.webhook_service import WebhookService
from config.settings import Config
from constants import (
    MAX_DISCORD_EMBEDS_PER_REQUEST, PLATFORM_DISCORD, PLATFORM_SLACK, DISCORD_SUCCESS_CODES, SLACK_SUCCESS_CODES,DISCORD_EMBED_PAYLOAD_THRESHOLD,
    DISCORD_FOOTER_FILE, SLACK_FOOTER_FILE
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
        logger.debug("🚀  PlatformService initialized")
    
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
        logger.info(f"📤  Sending to {type(platform).__name__}")

        # --- Read Footer Files (if enabled) ---
        discord_footer_content = None
        slack_footer_content = None
        if isinstance(platform, DiscordPlatform) and self.config.enable_custom_discord_footer:
            discord_footer_content = self._read_footer_file(DISCORD_FOOTER_FILE)
        elif isinstance(platform, SlackPlatform) and self.config.enable_custom_slack_footer:
            slack_footer_content = self._read_footer_file(SLACK_FOOTER_FILE)
        # --- End Footer Reading ---

        try:
            # 1. Format Header (Payload generated but not sent immediately)
            header_payload = platform.format_header(
                custom_header=self.config.custom_header,
                start_date=start_date,
                end_date=end_date,
                show_date_range=self.config.show_date_range,
                tv_count=events_summary.get("total_tv", 0),
                movie_count=events_summary.get("total_movies", 0),
                premiere_count=events_summary.get("total_premieres", 0)
            )

            # 2. Send Header (Immediately for Discord if payload exists)
            if isinstance(platform, DiscordPlatform):
                if header_payload:
                    logger.info("🚚 Attempting to send Discord header message...")
                    # Log the payload being sent (optional, can be verbose)
                    # logger.debug(f"Header Payload: {header_payload}")
                    header_sent_successfully = platform.send_message(header_payload)
                    if not header_sent_successfully:
                        overall_success = False
                        logger.error("❌ Failed to send Discord header message. Aborting further sends for Discord.")
                        return False # Stop processing for this platform if header fails
                    else:
                        # Explicitly log success AFTER the send call returns
                        logger.info("✅ Discord header message acknowledged by webhook service.")
                else:
                    logger.warning("⚠️ No header payload generated for Discord.")

            # 3. Format and Send Days (Platform-specific)
            if isinstance(platform, DiscordPlatform):
                # --- Format Days (Embeds) ---
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

                # --- Send Batched Embeds ---
                logger.info(f"🚚 Sending {len(all_embeds)} formatted day embeds to Discord using smart batching...")
                current_batch = []
                current_payload_size = 0
                # Store header content separately to add it to the first batch later
                initial_header_content = header_payload.get("content", "") if header_payload else ""
                header_content_size = len(json.dumps(initial_header_content))
                current_payload_size += header_content_size # Tentatively add header size

                footer_sent_in_batch = False # Flag to track if footer gets included

                for i, embed in enumerate(all_embeds):
                    embed_str = json.dumps(embed)
                    embed_size = len(embed_str)

                    # Check if adding the embed exceeds limits
                    if (len(current_batch) >= MAX_DISCORD_EMBEDS_PER_REQUEST or
                        current_payload_size + embed_size > DISCORD_EMBED_PAYLOAD_THRESHOLD):

                        # Prepare payload for the current batch
                        payload_to_send = {"embeds": current_batch}
                        # Add header content ONLY if this is the first batch being sent
                        if i > 0 and initial_header_content: # Check if it's NOT the first batch potentially being sent
                             payload_to_send["content"] = initial_header_content
                             initial_header_content = "" # Clear header after adding it once

                        # Send the current batch
                        logger.debug(f"Sending Discord batch: {len(current_batch)} embeds, size ~{current_payload_size}")
                        if not platform.send_message(payload_to_send):
                            overall_success = False
                            logger.error("Failed to send a Discord batch.")

                        # Start a new batch
                        current_batch = [embed]
                        current_payload_size = embed_size
                        # Reset header size calculation for new batch if header was already sent
                        if not initial_header_content:
                             current_payload_size += 0 # Header already sent or empty
                        else:
                             # This shouldn't happen if header sent above
                             current_payload_size += header_content_size

                    else:
                        # Add embed to the current batch
                        current_batch.append(embed)
                        current_payload_size += embed_size

                # --- Handle the final batch ---
                if current_batch:
                    # Prepare payload with ONLY embeds
                    final_payload = {"embeds": current_batch}

                    # Send the final batch (embeds only)
                    final_payload_size = len(json.dumps(final_payload))
                    logger.debug(f"Sending final Discord batch: {len(current_batch)} embeds, size ~{final_payload_size}")
                    if not platform.send_message(final_payload):
                        overall_success = False
                        logger.error("Failed to send the final Discord batch.")

                # --- Send Discord Footer Separately (ALWAYS if content exists) ---
                if discord_footer_content:
                    logger.info("🚚  Sending custom Discord footer as separate message...")
                    if not platform.send_message({"content": discord_footer_content}):
                        overall_success = False
                        logger.error("Failed to send Discord footer message.")
                # --- End Discord Footer ---

            elif isinstance(platform, SlackPlatform):
                # --- Format Days (Attachments) ---
                logger.info(f"Formatting {len(days)} days for Slack...")
                attachments = []
                for day in days:
                     try:
                         attachment = platform.format_day(day)
                         if attachment:
                             attachments.append(attachment)
                         else:
                             logger.warning(f"Skipping day {day.name} due to formatting error (no attachment generated).")
                     except Exception as e:
                         logger.error(f"☠️  Error formatting day {day.name} for Slack: {e}")
                         logger.debug(traceback.format_exc())
                         overall_success = False

                # --- Construct Slack Payload (Header Blocks + Day Attachments ONLY) ---
                slack_payload = {}
                # We only need header blocks here now
                header_blocks = []
                if header_payload and "blocks" in header_payload and header_payload["blocks"]:
                    header_blocks.extend(header_payload["blocks"])
                    logger.debug(f"🧱  Using {len(header_blocks)} header blocks.")
                else:
                    logger.warning("⚠️  Header payload missing or 'blocks' key is empty/missing.")

                # Add header blocks to payload if they exist
                if header_blocks:
                    slack_payload["blocks"] = header_blocks

                # Add attachments if they exist
                if attachments:
                    slack_payload["attachments"] = attachments
                    logger.debug(f"Added {len(attachments)} attachments.")
                else:
                    logger.warning("⚠️  No attachments generated for Slack message.")

                # --- Send the Main Slack Message (Header + Attachments) ---
                if slack_payload: # Check if payload has blocks or attachments
                    logger.debug(f"Main Slack Payload (Header + Attachments): {json.dumps(slack_payload, indent=2)}")
                    logger.info(f"🚚 Sending main Slack message with {len(header_blocks)} blocks and {len(attachments)} attachments...")
                    if not platform.send_message(slack_payload):
                        overall_success = False
                        logger.error("Failed to send main Slack message.")
                    else:
                        logger.info("✅  Main Slack message acknowledged.")
                else:
                     logger.error("❌  Main Slack payload was empty (no blocks or attachments), skipping send.")

                # Send the footer as a separate message containing the context block
                if slack_footer_content:
                    logger.info("🚚  Sending custom Slack footer as separate context block...")
                    footer_payload = {
                        "blocks": [
                            {
                                "type": "text",
                                "elements": [
                                    {
                                        "type": "mrkdwn",
                                        "text": slack_footer_content
                                    }
                                ]
                            }
                        ]
                    }
                    logger.debug(f"Slack Footer Payload: {json.dumps(footer_payload, indent=2)}")
                    if not platform.send_message(footer_payload):
                        overall_success = False
                        logger.error("Failed to send Slack footer message.")
                    else:
                        logger.info("✅  Slack footer message acknowledged.")
                # --- END Separate Footer Sending ---

            logger.info(f"✅  Finished sending to {platform.__class__.__name__}. Overall success: {overall_success}")
            return overall_success

        except Exception as e:
            logger.error(f"☠️  Unhandled error during send to {platform.__class__.__name__}: {e}")
            logger.debug(traceback.format_exc())
            return False

    def _read_footer_file(self, file_path: str) -> Optional[str]:
        """Reads content from a footer file if it exists, stripping HTML comments."""
        try:
            logger.debug(f"Attempting to read footer file: {file_path}")
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    raw_content = f.read()
                content_no_comments = re.sub(r'<!--.*?-->', '', raw_content, flags=re.DOTALL)
                content = content_no_comments.strip()
                if content:
                    logger.info(f"📄  Loaded and processed custom footer from {file_path}")
                    # --- ADD LOGGING ---
                    logger.debug(f"✂️  Stripped footer content:\n'''\n{content}\n'''")
                    # --- END LOGGING ---
                    return content
                else:
                    logger.warning(f"⚠️  Custom footer file {file_path} is empty after stripping comments.")
                    return None
            else:
                logger.warning(f"⚠️  Custom footer file not found at configured path: {file_path}")
                return None
        except Exception as e:
            logger.error(f"☠️  Error reading footer file {file_path}: {e}")
            logger.debug(traceback.format_exc())
            return None