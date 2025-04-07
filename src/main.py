import logging
import os
import requests
import argparse
import traceback
from typing import Dict, List, Tuple, Callable, Any, Optional
import json
from calendar_processor import (
     get_events_for_date_range,
    process_events_for_display, format_for_discord, format_for_slack, 
)
from datetime_helpers import calculate_date_range
from general_helpers import count_events_by_type, count_premieres, format_subheader_text, format_header_text

from constants import (DEFAULT_PASSED_EVENT_HANDLING, MAX_DISCORD_EMBEDS_PER_REQUEST, DISCORD_SUCCESS_CODES, SLACK_SUCCESS_CODES)

logger = logging.getLogger("calendar")

def load_config():
    """Load configuration from environment variables"""
    calendar_urls_str = os.environ.get("CALENDAR_URLS", "[]")
    
    try:
        calendar_urls = json.loads(calendar_urls_str)
        logger.info(f"✅ Successfully loaded CALENDAR_URLS: {len(calendar_urls)} calendars")
    except json.JSONDecodeError as e:
        logger.error(f"ERROR: CALENDAR_URLS is not valid JSON: {calendar_urls_str}")
        logger.error(f"Error details: {str(e)}")
        calendar_urls = []
    
    config = {
        "discord_webhook_url": os.environ.get("DISCORD_WEBHOOK_URL"),
        "slack_webhook_url": os.environ.get("SLACK_WEBHOOK_URL"),
        "use_discord": os.environ.get("USE_DISCORD", "true").lower() == "true",
        "use_slack": os.environ.get("USE_SLACK", "false").lower() == "true",
        "custom_header": os.environ.get("CUSTOM_HEADER", "TV Guide"),
        "show_date_range": os.environ.get("SHOW_DATE_RANGE", "true").lower() == "true",
        "start_week_on_monday": os.environ.get("START_WEEK_ON_MONDAY", "true").lower() == "true",
        "calendar_urls": calendar_urls,
        "passed_event_handling": os.environ.get("PASSED_EVENT_HANDLING", "DISPLAY").upper(),
        "calendar_range": os.environ.get("CALENDAR_RANGE", "WEEK").upper()
    }
    
    # Handle AUTO setting - convert to DAY or WEEK based on SCHEDULE_TYPE
    if config["calendar_range"] == "AUTO":
        schedule_type = os.environ.get("SCHEDULE_TYPE", "WEEKLY").upper()
        if schedule_type == "DAILY":
            config["calendar_range"] = "DAY"
        else:
            config["calendar_range"] = "WEEK"
    
    # Validate the passed event handling option
    valid_options = ["DISPLAY", "HIDE", "STRIKE"]
    if config["passed_event_handling"] not in valid_options:
        logger.warning(f"Invalid PASSED_EVENT_HANDLING value: {config['passed_event_handling']}, defaulting to DISPLAY")
        config["passed_event_handling"] =  DEFAULT_PASSED_EVENT_HANDLING
    
    # Validate webhook configuration
    if not config["use_discord"] and not config["use_slack"]:
        raise ValueError("At least one messaging platform must be enabled")

    if config["use_discord"] and not config["discord_webhook_url"]:
        raise ValueError("DISCORD_WEBHOOK_URL is required when USE_DISCORD is true")
        
    if config["use_slack"] and not config["slack_webhook_url"]:
        raise ValueError("SLACK_WEBHOOK_URL is required when USE_SLACK is true")
    
    return config





def send_webhook_request(webhook_url: str, payload: dict, success_codes: List[int]) -> bool:
    """
    Send data to a webhook and check for success
    """
    headers = {'Content-Type': 'application/json'}
    try:
        response = requests.post(webhook_url, json=payload, headers=headers)
        logger.info(f"Webhook response status code: {response.status_code}")
        if response.status_code in success_codes:
            return True
        else:
            logger.error(f"Failed to send webhook: {response.text}")
            return False
    except Exception as e:
        logger.error(f"Error sending to webhook: {e}")
        return False

def send_to_discord(webhook_url: str, days_data: dict, tv_count: int, movie_count: int, 
                   start_date, end_date, custom_header: str = "TV Guide", 
                   show_date_range: bool = True, start_week_on_monday: bool = True) -> bool:
    """
    Send formatted message to Discord
    """
    is_daily_mode = start_date.date() == end_date.date()
    premiere_count = count_premieres(days_data)
    
    # Format the data for Discord
    embeds = format_for_discord(days_data, start_week_on_monday, is_daily_mode)
    
    # Create header message with formatted subheader
    header_text = format_header_text(custom_header, start_date, end_date, show_date_range)
    subheader = format_subheader_text(tv_count, movie_count, premiere_count)
    header = {"content": f"{header_text}\n\n{subheader}"}
    
    # Post header
    if not send_webhook_request(webhook_url, header, DISCORD_SUCCESS_CODES):
        return False
    
    # Group embeds into batches (Discord limit)
    embed_batches = [embeds[i:i+MAX_DISCORD_EMBEDS_PER_REQUEST] 
                   for i in range(0, len(embeds), MAX_DISCORD_EMBEDS_PER_REQUEST)]
    
    success_count = 0
    for batch in embed_batches:
        payload = {"embeds": batch}
        if send_webhook_request(webhook_url, payload, DISCORD_SUCCESS_CODES):
            success_count += 1
    
    return success_count == len(embed_batches)  # True if all batches succeeded

def send_to_slack(webhook_url: str, days_data: dict, tv_count: int, movie_count: int, 
                 start_date, end_date, custom_header: str, 
                 show_date_range: bool, start_week_on_monday: bool = True) -> bool:
    """
    Send formatted message to Slack
    """
    is_daily_mode = start_date.date() == end_date.date()
    premiere_count = count_premieres(days_data)
    
    # Format content for Slack
    blocks, attachments = format_for_slack(
        days_data, tv_count, movie_count, premiere_count, 
        start_date, end_date, custom_header, 
        show_date_range, start_week_on_monday, is_daily_mode
    )
    
    # Create the payload with blocks and attachments
    payload = {
        "blocks": blocks,
        "attachments": attachments
    }
    
    # Send to Slack
    return send_webhook_request(webhook_url, payload, SLACK_SUCCESS_CODES)

def process_and_send_to_platform(
    platform: str, config: dict, events: list, start_date, end_date, 
    tv_count: int, movie_count: int, time_settings: dict) -> bool:
    """
    Process events for a platform and send the results
    
    Args:
        platform: 'discord' or 'slack'
        config: Configuration dictionary
        events: List of calendar events
        start_date/end_date: Date range
        tv_count/movie_count: Content counts
        time_settings: Dictionary with time display settings
        
    Returns:
        Boolean indicating success
    """
    logger.info(f"📅 Processing events for {platform.capitalize()}")
    
    # Process events specifically for this platform
    platform_data, tv_count, movie_count = process_events_for_display(
        events, 
        start_date, 
        end_date,
        platform,  # Specify platform
        config['start_week_on_monday'],
        time_settings['use_24_hour'],
        time_settings['add_leading_zero'],
        time_settings['display_time'],
        config['passed_event_handling']
    )
    
    logger.info(f"📤 Sending to {platform.capitalize()}")
    
    if platform == 'discord':
        success = send_to_discord(
            config['discord_webhook_url'], 
            platform_data, tv_count, movie_count, 
            start_date, end_date, 
            config['custom_header'], 
            config['show_date_range'],
            config['start_week_on_monday']
        )
    elif platform == 'slack':
        success = send_to_slack(
            config['slack_webhook_url'], 
            platform_data, tv_count, movie_count, 
            start_date, end_date, 
            config['custom_header'], 
            config['show_date_range'],
            config['start_week_on_monday']
        )
    else:
        logger.error(f"Unknown platform: {platform}")
        return False
        
    logger.info(f"Successfully sent to {platform.capitalize()}: {success}")
    return success

def main():
    """Main function to process calendar events and send to messaging platforms"""
    logger.info("Starting Calendar to Discord script")
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Process calendar events and send to Discord/Slack')
    parser.add_argument('--debug', action='store_true', help='Run in debug mode')
    args = parser.parse_args()
    
    # Set debug level if requested
    if args.debug:
        logger.setLevel(logging.DEBUG)
        logger.info("🪲 Running in DEBUG mode")
    
    try:
        # Load configuration
        config = load_config()
        
        # Calculate date range based on mode
        start_date, end_date = calculate_date_range(
            config['calendar_range'],
            config['start_week_on_monday']
        )
        
        # Get events for the calculated date range
        logger.info(f"🔍 Fetching events from {len(config['calendar_urls'])} calendars")
        events = get_events_for_date_range(
            config['calendar_urls'], 
            start_date,
            end_date
        )
        
        events_count = len(events)
        logger.info(f"📦 Found {events_count} events")
        
        # Get time display settings
        time_settings = {
            'use_24_hour': os.environ.get("USE_24_HOUR", "false").lower() == "true",
            'add_leading_zero': os.environ.get("ADD_LEADING_ZERO", "true").lower() == "true",
            'display_time': os.environ.get("DISPLAY_TIME", "true").lower() == "true"
        }
        
        # Count total TV and movie events once - we'll use these counts for both platforms
        tv_count, movie_count = count_events_by_type(events)
        
        # Flag to track if we need to send to any platforms
        platforms_to_process = []
        if config['use_discord']:
            platforms_to_process.append('discord')
        if config['use_slack']:
            platforms_to_process.append('slack')
            
        # Process events for each platform
        platform_data = {}
        for platform in platforms_to_process:
            logger.info(f"📅 Processing events for {platform.capitalize()}")
            platform_data[platform], _, _ = process_events_for_display(
                events, 
                start_date, 
                end_date,
                platform,
                config['start_week_on_monday'],
                time_settings['use_24_hour'],
                time_settings['add_leading_zero'],
                time_settings['display_time'],
                config['passed_event_handling']
            )
        
        # Send to each enabled platform
        results = []
        
        if config['use_discord'] and 'discord' in platform_data:
            logger.info("📤 Sending to Discord")
            discord_success = send_to_discord(
                config['discord_webhook_url'], 
                platform_data['discord'],
                tv_count, 
                movie_count, 
                start_date, 
                end_date, 
                config['custom_header'], 
                config['show_date_range'],
                config['start_week_on_monday']
            )
            logger.info(f"Successfully sent to Discord: {discord_success}")
            results.append(discord_success)

        if config['use_slack'] and 'slack' in platform_data:
            logger.info("📤 Sending to Slack")
            slack_success = send_to_slack(
                config['slack_webhook_url'], 
                platform_data['slack'],
                tv_count, 
                movie_count, 
                start_date, 
                end_date, 
                config['custom_header'], 
                config['show_date_range'],
                config['start_week_on_monday']
            )
            logger.info(f"Successfully sent to Slack: {slack_success}")
            results.append(slack_success)
        
        all_success = all(results) if results else False
        logger.info("✅ Script completed successfully" if all_success else "⚠️ Script completed with errors")
        return all_success
        
    except Exception as e:
        logger.error(f"⛔ Error in main function: {e}")
        logger.error(traceback.format_exc())
        return False
# Run the script if executed directly
if __name__ == "__main__":
    main()