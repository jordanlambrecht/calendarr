# 📆 Calendarr

A simple Docker container that fetches upcoming airings/releases for TV shows and movies from Sonarr and Radarr calendars and posts them to Discord on a schedule.

![Example Discord post](https://github.com/jordanlambrecht/calendarr/blob/main/public/calendarr_example_output_v2.png)

## ✨ Features

- Combines multiple Sonarr and Radarr calendar feeds
- Groups shows and movies by day of the week
- Highlights season premieres with a party emoji 🎉
- Runs on a customizable schedule (daily or weekly)
- Supports both Discord and Slack notifications
- Highly customizable configuration 

## 🚀 Usage

Images available via either `ghcr.io/jordanlambrecht/calendarr:latest` or `jordyjordyjordy/calendarr:latest`

### With Docker Compose (Recommended)

1. In Discord, right click channel you want to add the script to -> Edit Channel -> Integrations, Webhooks -> New Webhook -> Copy Webhook URL

2. Create a `.env` file with your configuration or remove '.example' from `.env.example`:

```env
DISCORD_WEBHOOK_URL=your_discord_webhook_url
SLACK_WEBHOOK_URL=your_discord_webhook_url
ICS_URL_SONARR_1=your_sonarr_calendar_url
ICS_URL_SONARR_2=your_anime_sonarr_calendar_url
ICS_URL_RADARR_1=your_radarr_calendar_url

...and so on and so on and turtles all the way down
```
### With Docker Run (If you like pain)

```bash
docker run -d \
  --name calendar-discord-notifier \
  -e DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/your_webhook" \
  -e CALENDAR_URLS='[{"url":"https://sonarr.example.com/feed/calendar/api.ics","type":"tv"},{"url":"https://radarr.example.com/feed/calendar/api.ics","type":"movie"}]' \
  -e CUSTOM_HEADER="My Media Guide" \
  -e SHOW_DATE_RANGE="true" \
  -e START_WEEK_ON_MONDAY="true" \
  -e RUN_ON_STARTUP="true" \
  jordyjordyjordy/calendarr:latest
```


### To Run Offschedule 

1. Start the container via the compose file with `docker compose up -d`
2. Use the command `docker exec calendar-discord-notifier python /app/calendar-to-discord.py` as willy nilly as you wish


## 🛠️ Configuration

| Environment Variable | Type | Description |
|---------------------|-------------|-------|
| `TZ` | Timezone for displaying show times | Uses tzdata names - Default: America/Chicago |
| `DISCORD_WEBHOOK_URL` | String | *Required for Discord* Discord webhook URL |
| `SLACK_WEBHOOK_URL` | String | *Required for Slack* Slack incoming webhook URL |
| `USE_SLACK` | Boolean | Enable Slack integration (Default: false) |
| `USE_DISCORD` | Boolean | Enable Discord integration (Default: true) |
| `USE_24_HOUR` | Boolean | Use 24-hour time format (Default: false) |
| `DISPLAY_TIME` | Boolean | Show release times in output (Default: true) |
| `CALENDAR_URLS` | JSON Array | *Required* Array of calendar URLs and their types (tv/movie)|
| `CUSTOM_HEADER` | String | Custom title for the message (default: "TV Guide") |
| `SHOW_DATE_RANGE` | Boolean | Show date range in header (Default: true) |
| `START_WEEK_ON_MONDAY` | Boolean | Whether the week should start on Monday (Default: true) |
| `RUN_ON_STARTUP` | Boolean | Also run immediately once when container starts (Default: true) |
| `RUN_TIME` | String | Time of day to run the script **Must be 24hr format** |
| `DEBUG` | Boolean | Enable debug mode for additional logging (Default: false) |
| `SCHEDULE_TYPE` | STRING | Either "DAILY" or "WEEKLY" |
| `PASSED_EVENT_HANDLING` | String | How to display past events: "DISPLAY", "HIDE", or "STRIKE" (Default: "STRIKE") |
| `CALENDAR_RANGE` | String | "AUTO", "DAY", or "WEEK" - controls how many days of events to show (Default: "AUTO"). *See Below* |

## Schedule Configuration

Set when and how often the calendar runs:

- `RUN_TIME`: When to run each day (format: HH:MM in 24-hour time, e.g., "09:30")
- `SCHEDULE_TYPE`: Either "DAILY" or "WEEKLY"
- `CALENDAR_RANGE`: "AUTO", "DAY", or "WEEK" - controls how many days of events to show
  - "AUTO": Uses a day's worth for daily schedules or a week for weekly schedules
  - "DAY": Shows one day of events
  - "WEEK": Shows an entire week of events

You can also use `CRON_SCHEDULE` for direct cron expressions (overrides all other schedule settings. Don't use this unless you have a good reason and know what you're doing)

## 🤝 Obtaining Calendar URLs

![Sonarr Calendar Options](https://github.com/jordanlambrecht/calendarr/blob/main/public/calendarr_sonarr_feed.png)

### Sonarr

1. Go to Calendar > iCal Link
2. Leave all three checkboxes blank
3. Optionally set tags for shows you want to announce
4. Copy the ical link

Alternatively: 

1. Go to Settings > General
2. Under "Security" section, look for "API Key"
3. Copy the API key
4. Your calendar URL will be: `http://your-sonarr-url/feed/v3/calendar/Sonarr.ics?apikey=YOUR_API_KEY`

### Radarr

1. Go to Calendar > iCal Link
2. Leave all three checkboxes blank
3. Optionally set tags for movies you want to announce
4. Copy the ical link

Alternatively: 

1. Go to Settings > General
2. Under "Security" section, look for "API Key"
3. Copy the API key
4. Your calendar URL will be: `http://your-radarr-url/feed/v3/calendar/Radarr.ics?apikey=YOUR_API_KEY`


## Slack Webhooks Setup

More info [here](https://api.slack.com/messaging/webhooks) on how to obtain a slack webhook URL if you get lost.

You can set up the Slack app using the provided manifest file:

1. Go to [https://api.slack.com/apps](https://api.slack.com/apps)
2. Click "Create New App" and select "From an app manifest"
3. Select your workspace and click "Next"
4. Copy and paste the contents of the `slack-manifest.yaml` file from this repository
5. Click "Next" and then "Create"
6. Once created, navigate to "Incoming Webhooks" in the sidebar
7. Toggle "Activate Incoming Webhooks" to On
8. Click "Add New Webhook to Workspace"
9. Select the channel where you want to receive updates
10. Copy the Webhook URL provided and use it as your `SLACK_WEBHOOK_URL` environment variable

## 🌟 First Timers

If you're new to Docker, it's fairly easy to get this going. I won't post an in-depth guide- there's [Plenty](https://docs.docker.com/compose/) on the internet. The general gist is:

1. Install Docker Desktop for your platform (Windows, Mac, or Linux)
2. Create a new folder for your Calendarr setup via Terminal: `mkdir calendarr && cd calendarr`
3. Create these two files:
  - A .env file with your configuration (see example above)
  - A docker-compose.yml file with, at a minimum:

  ```
  ---
  name: calendarr
  services:
    calendarr:
      image: ghcr.io/jordanlambrecht/calendarr:latest
      restart: "unless-stopped"
      container_name: calendarr
      environment:
        USE_DISCORD: "true"
        DISCORD_WEBHOOK_URL: ${DISCORD_WEBHOOK_URL}
        CALENDAR_URLS: >
          [{
            "url":"${ICS_URL_SONARR_1}",
            "type":"tv"
          },
          {
            "url":"${ICS_URL_RADARR_1}",
            "type":"movie"
          }]
        CUSTOM_HEADER: "TV Guide - What's Up This Week"
        TZ: "America/Chicago"  # Change to your timezone
      volumes:
        - ./logs:/app/logs:rw
  ```
4. Open a terminal in that folder and run: `docker compose up -d`
5. Check if it's working: `docker logs calendarr`

That's it! The container will immediately run once (if RUN_ON_STARTUP is true) and then according to the schedule you've set.

## 🚧 Development

If you want to build the container yourself:

```bash
git clone https://github.com/jordanlambrecht/calendarr.git
cd calendarr
docker build -t calendarr .
```

## 🧑‍⚖️ License

GNU GENERAL PUBLIC LICENSE

