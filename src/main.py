#!/usr/bin/env python3
# src/main.py

import logging
import traceback

from config.settings import load_config_from_env
from services.calendar_service import CalendarService
from services.platform_service import PlatformService
from services.formatter_service import FormatterService
from utils.date_utils import calculate_date_range

logger = logging.getLogger("main")

def main():
    """Main function to process calendar events and send to messaging platforms"""
    
    try:
        # Load config
        config = load_config_from_env()
    except Exception as e:
        logger.error(f"Error loading configuration: {e}")
        return False

    try:
        # Calculate date range
        logger.debug(f"🔍  Loading date ranges from config")
        start_date, end_date = calculate_date_range(
            config.calendar_range,
            config.start_week_on_monday,
            config.timezone
        )
    except Exception as e:
        logger.error(f"Error calculating date range: {e}")
        return False

    # Initialize services
    calendar_service = CalendarService(config)
    formatter_service = FormatterService(config)
    platform_service = PlatformService(config)
    
    try:
        # Get events for the calculated date range
        logger.info(f"🔍  Fetching events from {len(config.calendar_urls)} calendars")
        events = calendar_service.fetch_events(start_date, end_date)
        
        events_count = len(events)
        logger.info(f"📦 Found {events_count} events")
        
        # Process events into Day objects with EventItems
        days, events_summary = formatter_service.process_events(
            events, 
            start_date, 
            end_date
        )
        
        # Send to enabled platforms
        results = platform_service.send_to_platforms(
            days, 
            events_summary,
            start_date, 
            end_date
        )
        
        # Check if all platforms succeeded
        all_success = all(results.values()) if results else False
        
        logger.info("✅ Script completed successfully" if all_success else "⚠️ Script completed with errors")
        return all_success
        
    except Exception as e:
        logger.error(f"⛔ Error in main function: {e}")
        logger.error(traceback.format_exc())
        return False
    
if __name__ == "__main__":
    main()