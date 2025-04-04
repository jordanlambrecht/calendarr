# 📆 Calendarr

A simple Docker container that fetches upcoming airings/releases for TV shows and movies from Sonarr and Radarr calendars and posts them to Discord on a schedule.

![Example Discord post](https://github.com/jordanlambrecht/arr-calendar-to-discord/blob/main/public/calendarr_example_output_v2.png)

## ✨ Features

- Combines multiple Sonarr and Radarr calendar feeds
- Groups shows and movies by day of the week
- Highlights season premieres with a party emoji 🎉
- Runs on a customizable schedule (default: every Monday at 9 AM)

## 🚀 Usage

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
| `DISCORD_WEBHOOK_URL` | String | *Required* Discord webhook URL |
| `CALENDAR_URLS` | JSON Array | *Required* Array of calendar URLs and their types (tv/movie)|
| `CUSTOM_HEADER` | String | Custom title for the Discord message (default: "TV Guide") |
| `SHOW_DATE_RANGE` | Boolean | Show date range in header (Default: true) |
| `START_WEEK_ON_MONDAY` | Boolean | Whether the week should start on Monday (Default: true) |
| `RUN_ON_STARTUP` | Boolean | Also run immediately once when container starts (Default: true) |
| `CRON_SCHEDULE` | Boolean | Cron schedule expression (default: "0 9 * * 1" - Monday 9am) [Generating Cron Schedule Expressions](https://crontab.guru/) |

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

## 🚧 Development

If you want to build the container yourself:

```bash
git clone https://github.com/jordanlambrecht/calendarr.git
cd calendar-to-discord
docker build -t calendarr .
```

## 🧑‍⚖️ License

MIT License
