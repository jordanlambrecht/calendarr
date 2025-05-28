![Docker Pulls](https://img.shields.io/docker/pulls/jordyjordyjordy/calendarr)
![GitHub Release](https://img.shields.io/github/v/release/jordanlambrecht/calendarr)
![GitHub last commit](https://img.shields.io/github/last-commit/jordanlambrecht/calendarr)

# 📆 Calendarr

A simple Docker container that fetches upcoming airings/releases for TV shows and movies from Sonarr and Radarr calendars and posts them to Discord on a schedule.

![Example Discord post](https://github.com/jordanlambrecht/calendarr/blob/main/public/calendarr_example_output_v2.png)

## ✨ Features

- Combines multiple Sonarr and Radarr calendar feeds
- Groups shows and movies by day of the week
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
  --name calandarr \
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
2. Use the command `docker exec calandarr python /app/main.py` as willy nilly as you wish


## 🛠️ Configuration

| Variable                              | Type    | Default         | Description                                                                                             |
| :------------------------------------ | :------ | :-------------- | :------------------------------------------------------------------------------------------------------ |
| `ADD_LEADING_ZERO`                    | Boolean | `true`          | Add leading zero to single-digit hours (Optional)                                                       |
| `CALENDAR_RANGE`                      | String  | `AUTO`          | Date range to fetch: `DAY`, `WEEK`, `AUTO` (Optional)                                                   |
| `CALENDAR_URLS` *                     | String  | `[]`            | JSON array of calendar URLs and types (e.g., `[{"url":"http://...","type":"tv"}]`)                       |
| `CRON_SCHEDULE`                       | String  | `None`          | Custom CRON expression (Overrides `SCHEDULE_TYPE`, `SCHEDULE_DAY`, `RUN_TIME`) (Optional)               |
| `CUSTOM_HEADER`                       | String  | `New Releases`  | Custom header text (Optional)                                                                           |
| `DEBUG`                               | Boolean | `false`         | Enable debug logging (Optional)                                                                         |
| `DEDUPLICATE_EVENTS`                  | Boolean | `true`          | Remove duplicate events from multiple sources (Optional)                                                |
| `DISCORD_HIDE_MENTION_INSTRUCTIONS` | Boolean | `false`         | *Discord only* Hide the instruction text below the role mention (Optional)                              |
| `DISCORD_MENTION_ROLE_ID`             | String  | `""`            | *Discord only* Role ID to mention (Format: `123456789012345678`. Numbers only.) (Optional)             |
| `DISCORD_WEBHOOK_URL` **              | String  | `""`            | Discord webhook URL                                                                                     |
| `DISPLAY_TIME`                        | Boolean | `true`          | Display the release time next to events (Optional)                                                      |
| `ENABLE_CUSTOM_DISCORD_FOOTER`        | Boolean | `false`         | Enable custom footer for Discord messages (Optional)                                                    |
| `ENABLE_CUSTOM_SLACK_FOOTER`          | Boolean | `false`         | Enable custom footer for Slack messages (Optional)                                                      |
| `HTTP_TIMEOUT`                        | Integer | `30`            | Timeout in seconds for HTTP requests (Optional)                                                         |
| `LOG_BACKUP_COUNT`                    | Integer | `15`            | Number of rotated log files to keep (Optional)                                                          |
| `LOG_DIR`                             | String  | `/app/logs`     | Directory to store log files (Optional)                                                                 |
| `LOG_FILE`                            | String  | `calendarr.log` | Name of the log file (Optional)                                                                         |
| `LOG_MAX_SIZE_MB`                     | Integer | `1`             | Maximum size of a single log file in MB before rotation (Optional)                                      |
| `PASSED_EVENT_HANDLING`               | String  | `DISPLAY`       | How to handle past events: `DISPLAY`, `HIDE`, `STRIKE` (Optional)                                       |
| `RUN_ON_STARTUP`                      | Boolean | `false`         | Run the job immediately when the container starts (Optional)                                            |
| `RUN_TIME`                            | String  | `09:00`         | Time to run job (HH:MM) (Optional)                                                                      |
| `SCHEDULE_DAY`                        | String  | `1`             | Day of week for weekly schedule (`0`-`6`, Sunday-Saturday) (Optional. Default: Monday)                  |
| `SCHEDULE_TYPE`                       | String  | `WEEKLY`        | `DAILY` or `WEEKLY` (Optional)                                                                          |
| `SHOW_DATE_RANGE`                     | Boolean | `true`          | Show the date range in the header (Optional)                                                            |
| `SHOW_TIMEZONE_IN_SUBHEADER`          | Boolean | `false`         | Show the configured timezone (Optional)                                                                 |
| `SLACK_WEBHOOK_URL` ***             | String  | `""`            | Slack webhook URL                                                                                       |
| `START_WEEK_ON_MONDAY`                | Boolean | `true`          | Use Monday as the start of the week for color rotation (Optional)                                       |
| `TZ` *                                | String  | `UTC`           | Timezone (e.g., `America/New_York`)                                                                     |
| `USE_24_HOUR`                         | Boolean | `true`          | Use 24-hour time format (Optional)                                                                      |
| `USE_DISCORD`                         | Boolean | `true`          | Enable Discord notifications (Optional)                                                                 |
| `USE_SLACK`                           | Boolean | `false`         | Enable Slack notifications (Optional)                                                                   |

\* Required.
** Required if `USE_DISCORD` is `true`.
*** Required if `USE_SLACK` is `true`.

## Schedule Configuration

Set when and how often the calendar runs:

- `RUN_TIME`: When to run each day (format: HH:MM in 24-hour time, e.g., "09:30")
- `SCHEDULE_TYPE`: Either "DAILY" or "WEEKLY"
- `CALENDAR_RANGE`: "AUTO", "DAY", or "WEEK" - controls how many days of events to show
  - "AUTO": Uses a day's worth for daily schedules or a week for weekly schedules
  - "DAY": Shows one day of events
  - "WEEK": Shows an entire week of events

You can also use `CRON_SCHEDULE` for direct cron expressions (overrides all other schedule settings. Don't use this unless you have a good reason and know what you're doing)

## ✍️ Custom Footers

You can add custom text to the end of your Discord and Slack announcements using Markdown files.

1.  **Enable the Feature:** Set `ENABLE_CUSTOM_DISCORD_FOOTER: true` and/or `ENABLE_CUSTOM_SLACK_FOOTER: true` in your environment variables.
2.  **Create a Volume Mount:** Add a volume mount in your `docker-compose.yml` to map a local directory (e.g., `./custom_footers`) to `/app/custom_footers` inside the container.

    ```yaml
    # docker-compose.yml example snippet
    services:
      calendarr:
        # ... other stuff ...
        volumes:
          - ./logs:/app/logs:rw
          - ./custom_footers:/app/custom_footers:rw # Add this line
    ```
3.  **Edit Footer Files:**
    *   When you first start the container with the volume mount, Calendarr will automatically copy default template files (`discord_footer.md` and `slack_footer.md`) into your local `./custom_footers` directory (if they don't already exist).
    *   Edit these files using standard Markdown (for Discord) or Slack's `mrkdwn` (for Slack) to customize your footer.

If the footer files are missing or cannot be read, the app will log a warning and omit the footer without failing.

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

  ```yaml
  ---
  name: calendarr
  services:
    calendarr:
      image: ghcr.io/jordanlambrecht/calendarr:latest
      restart: "unless-stopped"
      container_name: calendarr
      environment:
        USE_DISCORD: "true"
        DISCORD_WEBHOOK_URL: ${DISCORD_WEBHOOK_URL} # Reference the .env.example for more info
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
        SCHEDULE_TYPE: "WEEKLY" # Or "DAILY"
        RUN_TIME: "09:00"       # Time to run the job (HH:MM)
      volumes:
        - ./logs:/app/logs:rw
  ```
4. Open a terminal in that folder and run: `docker compose up -d`
5. Check if it's working: `docker logs calendarr -f`

That's it! The container will immediately run once (if `RUN_ON_STARTUP` is `true`) and then according to the schedule you've set.


## 🧑‍💻 Contributing

The two biggest things I need help with right now are:
- Adding friendly timezone names to the `TIMEZONE_NAME_MAP` in the `constants.py` file
- Translations. There is no localization structure implemented yet, but it would be great to get a head start in things like spanish, etc

## 🛒 ToDo
Features I'd like to maybe implement:

- Localization
- More platform integrations
- Potentially a web ui


## 🚧 Development

Roadmap: https://github.com/users/jordanlambrecht/projects/3

If you want to build the container yourself:

```bash
git clone https://github.com/jordanlambrecht/calendarr.git
cd calendarr
docker build -t calendarr .
```

## 🧑‍⚖️ License

GNU GENERAL PUBLIC LICENSE

