import requests
import icalendar
import recurring_ical_events
import datetime
import sys
import os
import json
import re

def get_events_for_week(ical_urls, start_week_on_monday=True):
    # Use today's date
    base_date = datetime.date.today()
    
    # Calculate start of week based on preference
    if start_week_on_monday:
        # Start on Monday (0 = Monday in our calculation)
        start_offset = (7 - base_date.weekday()) % 7
    else:
        # Start on Sunday (6 = Sunday in our calculation)
        start_offset = (7 - (base_date.weekday() + 1) % 7) % 7
        if start_offset == 0:
            start_offset = 7
    
    start_of_week_date = base_date + datetime.timedelta(days=start_offset)
    end_of_week_date = start_of_week_date + datetime.timedelta(days=6)

    # Convert those dates to full datetimes
    start_of_week = datetime.datetime.combine(start_of_week_date, datetime.time.min)
    end_of_week = datetime.datetime.combine(end_of_week_date, datetime.time.max)

    all_events = []
    
    for url_info in ical_urls:
        url = url_info["url"]
        source_type = url_info["type"]  # "tv" or "movie"
        
        response = requests.get(url)
        if response.status_code != 200:
            print(f"Failed to fetch iCal from {url}: {response.status_code}")
            continue
        
        calendar = icalendar.Calendar.from_ical(response.content)
        
        events = recurring_ical_events.of(calendar).between(
            start_of_week, 
            end_of_week
        )
        
        # Convert date-only events to datetime
        for event in events:
            dtstart = event.get('DTSTART').dt
            # Strip timezone if present
            if isinstance(dtstart, datetime.datetime) and dtstart.tzinfo is not None:
                dtstart = dtstart.replace(tzinfo=None)
            if isinstance(dtstart, datetime.date) and not isinstance(dtstart, datetime.datetime):
                dtstart = datetime.datetime(dtstart.year, dtstart.month, dtstart.day)
            event['DTSTART'].dt = dtstart
        
        # Add source type to each event
        for event in events:
            event["SOURCE_TYPE"] = source_type
        
        all_events.extend(events)
    
    return all_events, start_of_week, end_of_week

def create_show_embeds(events, start_date, end_date):
    if not events:
        return [], 0, 0
    
    # Count TV episodes and movies
    tv_count = sum(1 for e in events if e.get("SOURCE_TYPE") == "tv")
    movie_count = sum(1 for e in events if e.get("SOURCE_TYPE") == "movie")
    
    # Sort events by date
    sorted_events = sorted(events, key=lambda e: e.get('DTSTART').dt)
    
    # Group events by day
    days = {}
    for event in sorted_events:
        start = event.get('DTSTART').dt
        source_type = event.get("SOURCE_TYPE")
        
        # Convert datetime to date for consistency
        day_key = start.strftime('%A, %b %d')
        time_available = True
        
        if day_key not in days:
            days[day_key] = {"tv": [], "movie": []}
        
        summary = event.get('SUMMARY', 'Untitled Event')
        
        # Check if this is a season premiere (contains x01 or s01e01 pattern)
        is_premiere = False
        
        # Process TV show titles - separate show name from episode info
        if source_type == "tv":
            # Check for pattern like "Show Name - 1x01" or "Show Name - S01E01" 
            if re.search(r'[-\s](?:s\d+e01|(?:\d+x01))\b', summary.lower()):
                is_premiere = True
            
            # Split show name from episode details if possible
            parts = re.split(r'\s+-\s+', summary, 1)
            if len(parts) == 2:
                show_name = parts[0]
                episode_info = parts[1]
                
                # Split again by ' - ' to separate episode number from title
                sub_parts = re.split(r'\s+-\s+', episode_info, 1)
                if len(sub_parts) == 2:
                    episode_num, episode_title = sub_parts
                else:
                    episode_num = episode_info
                    episode_title = ""

                if time_available:
                    time_str = start.strftime('%I:%M %p')
                    if is_premiere:
                        days[day_key]["tv"].append(
                            f"{time_str}: **{show_name}** - {episode_num} - *{episode_title}* 🎉"
                        )
                    else:
                        days[day_key]["tv"].append(
                            f"{time_str}: **{show_name}** - {episode_num} - *{episode_title}*"
                        )
                else:
                    if is_premiere:
                        days[day_key]["tv"].append(
                            f"**{show_name}** - {episode_num} - *{episode_title}* 🎉"
                        )
                    else:
                        days[day_key]["tv"].append(
                            f"**{show_name}** - {episode_num} - *{episode_title}*"
                        )
            else:
                # No dash separator found, just display as is
                if time_available:
                    time_str = start.strftime('%I:%M %p')
                    if is_premiere:
                        days[day_key]["tv"].append(f"{time_str}:  **{summary}** 🎉")
                    else:
                        days[day_key]["tv"].append(f"{time_str}: **{summary}**")
                else:
                    if is_premiere:
                        days[day_key]["tv"].append(f" **{summary}** 🎉")
                    else:
                        days[day_key]["tv"].append(f"**{summary}**")
        else:  # movie
            days[day_key]["movie"].append(f"🎬 **{summary}**")
    
    # Create embeds (one per day)
    embeds = []
    day_colors = {
        "Monday": 15158332,     # Red
        "Tuesday": 15844367,    # Orange
        "Wednesday": 16776960,  # Yellow
        "Thursday": 5763719,    # Green
        "Friday": 3447003,      # Blue
        "Saturday": 10181046,   # Purple
        "Sunday": 16777215      # White
    }
    
    for day, content in days.items():
        day_name = day.split(',')[0]
        color = day_colors.get(day_name, 0)
        
        # Combine TV and movie listings
        description = ""
        if content["tv"]:
            description += "\n".join(content["tv"])
            if content["movie"]:
                description += "\n\n"
        
        if content["movie"]:
            description += "**MOVIES**\n" + "\n".join(content["movie"])
        
        embed = {
            "title": day,
            "description": description,
            "color": color
        }
        embeds.append(embed)
    
    # Sort embeds by day of week
    day_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    embeds = sorted(embeds, key=lambda e: day_order.index(e["title"].split(',')[0]))
    
    return embeds, tv_count, movie_count

def send_to_discord(webhook_url, embeds, tv_count, movie_count, start_date, end_date, custom_header="TV Guide", show_date_range=True):
    # Handle pluralization
    shows_text = "episode" if tv_count == 1 else "episodes"
    movies_text = "movie" if movie_count == 1 else "movies"
    
    # Create header message
    header_text = f"# {custom_header}"
    if show_date_range:
        header_text += f" ({start_date.strftime('%b %d')} - {end_date.strftime('%b %d')})"
    
    header_text += f"\n\n{tv_count} all new {shows_text} and {movie_count} {movies_text}"
    
    header = {
        "content": header_text
    }
    
    # Post header
    headers = {'Content-Type': 'application/json'}
    try:
        response = requests.post(webhook_url, json=header, headers=headers)
        print(f"Header status code: {response.status_code}")
    except Exception as e:
        print(f"Error sending header to Discord: {e}")
    
    # Group embeds into batches of 10 (Discord limit)
    embed_batches = [embeds[i:i+10] for i in range(0, len(embeds), 10)]
    
    success_count = 0
    for batch in embed_batches:
        payload = {
            "embeds": batch
        }
        
        try:
            response = requests.post(webhook_url, json=payload, headers=headers)
            print(f"Embed batch status code: {response.status_code}")
            if response.status_code == 204 or response.status_code == 200:
                success_count += 1
        except Exception as e:
            print(f"Error sending to Discord: {e}")
    
    return success_count

def main():
    print("Starting Calendar to Discord script")
    
    # Get webhook URL from environment variables
    webhook_url = os.environ.get("DISCORD_WEBHOOK_URL")
    if not webhook_url:
        print("Error: DISCORD_WEBHOOK_URL environment variable not set")
        sys.exit(1)
    
    # Get calendar URLs from environment variables
    calendar_urls_json = os.environ.get("CALENDAR_URLS")
    if not calendar_urls_json:
        print("Error: CALENDAR_URLS environment variable not set")
        sys.exit(1)
    
    # Get optional environment variables
    custom_header = os.environ.get("CUSTOM_HEADER", "TV Guide")
    show_date_range = os.environ.get("SHOW_DATE_RANGE", "true").lower() == "true"
    start_week_on_monday = os.environ.get("START_WEEK_ON_MONDAY", "true").lower() == "true"
    # cron_schedule = os.environ.get("CRON_SCHEDULE", "0 9 * * 1")  # Default: Monday at 9 AM
    
    try:
        calendar_urls = json.loads(calendar_urls_json)
        if not isinstance(calendar_urls, list):
            raise ValueError("CALENDAR_URLS must be a JSON array")
    except json.JSONDecodeError:
        print("Error: CALENDAR_URLS is not valid JSON")
        sys.exit(1)
    
    try:
        # Get events
        print(f"Fetching events from {len(calendar_urls)} calendars")
        events, start_date, end_date = get_events_for_week(calendar_urls, start_week_on_monday)
        
        events_count = len(events)
        print(f"Found {events_count} events")
        
        # Create embeds for shows
        print("Creating embeds for events")
        embeds, tv_count, movie_count = create_show_embeds(events, start_date, end_date)
        
        # Send to Discord
        print(f"Sending {len(embeds)} day embeds to Discord")
        success_count = send_to_discord(webhook_url, embeds, tv_count, movie_count, 
                                        start_date, end_date, custom_header, show_date_range)
        print(f"Successfully sent {success_count} messages")
        
        # Explicitly exit
        print("Script completed successfully")
        sys.exit(0)
    except Exception as e:
        print(f"Error in main function: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()