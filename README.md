# 📆 Calendarr

A simple Docker container that fetches upcoming airings/releases for TV shows and movies from Sonarr and Radarr calendars and posts them to Discord on a schedule.

![Example Discord post](https://github.com/jordanlambrecht/calendarr/blob/main/public/calendarr_example_output_v2.png)

## ✨ Features

- Combines multiple Sonarr and Radarr calendar feeds
- Groups shows and movies by day of the week
- Highlights season premieres with a party emoji 🎉
- Runs on a customizable schedule (default: every Monday at 9 AM)

## 🚀 Usage

Images available via either `ghcr.io/jordanlambrecht/calendarr:latest` or `jordyjordyjordy/calendarr:latest`

### With Docker Compose (Recommended)

1. In Discord, right click channel you want to add the script to -> Edit Channel -> Integrations, Webhooks -> New Webhook -> Copy Webhook URL

2. Create a `.env` file with your configuration or remove '.example' from `.env.example`:

```env
DISCORD_WEBHOOK_URL=your_discord_webhook_url
ICS_URL_SONARR_1=your_sonarr_calendar_url
ICS_URL_SONARR_2=your_anime_sonarr_calendar_url
ICS_URL_RADARR_1=your_radarr_calendar_url
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
  -e CRON_SCHEDULE="0 9 * * 1" \
  jordyjordyjordy/calendarr:latest
```


### To Run Offschedule 

1. Start the container via the compose file with `docker compose up -d`
2. Use the command `docker exec calendar-discord-notifier python /app/calendar-to-discord.py` as willy nilly as you wish


## 🛠️ Configuration

| Environment Variable | Type | Description |
|---------------------|-------------|-------|
| `TZ` | Timezone for displaying show times | Uses tzdata names (e.g., "America/New_York", "Europe/London", "America/Los_Angeles") - Default: America/Chicago |
| `DISCORD_WEBHOOK_URL` | String | *Required* Discord webhook URL |
| `SLACK_WEBHOOK_URL` | Slack incoming webhook URL | Required for Slack integration |
| `USE_SLACK` | Enable Slack integration | Default: false |
| `USE_DISCORD` | Enable Discord integration | Default: true |
| `CALENDAR_URLS` | JSON Array | *Required* Array of calendar URLs and their types (tv/movie)|
| `CUSTOM_HEADER` | String | Custom title for the Discord message (default: "TV Guide") |
| `SHOW_DATE_RANGE` | Boolean | Show date range in header (Default: true) |
| `START_WEEK_ON_MONDAY` | Boolean | Whether the week should start on Monday (Default: true) |
| `RUN_ON_STARTUP` | Boolean | Also run immediately once when container starts (Default: true) |
| `CRON_SCHEDULE` | Boolean | Cron schedule expression (default: "0 9 * * 1" - Monday 9am) [Generating Cron Schedule Expressions](https://crontab.guru/) |

## Schedule Configuration

Set when and how often the calendar runs:

- `RUN_TIME`: When to run each day (format: HH:MM in 24-hour time, e.g., "09:30")
- `SCHEDULE_TYPE`: Either "DAILY" or "WEEKLY"
- `SCHEDULE_DAY`: Day of week (0=Sunday, 1=Monday, etc.) - only used for weekly schedules
- `CALENDAR_RANGE`: "AUTO", "DAY", or "WEEK" - controls how many days of events to show

For backward compatibility, you can also use:
- `SCHEDULE_TIME`: Same as RUN_TIME
- `CRON_SCHEDULE`: For direct cron expressions (overrides all other schedule settings)

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

## Slack Webhooks



## Slack App Setup

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


## 🚧 Development

If you want to build the container yourself:

```bash
git clone https://github.com/jordanlambrecht/calendarr.git
cd calendarr
docker build -t calendarr .
```

## 🧑‍⚖️ License

GNU GENERAL PUBLIC LICENSE
