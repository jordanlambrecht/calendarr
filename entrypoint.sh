#!/bin/sh
CRON_SCHEDULE=${CRON_SCHEDULE:-"0 9 * * 1"}
echo "$CRON_SCHEDULE cd /app && python /app/sonarr-to-discord.py >> /app/cron.log 2>&1" >/etc/cron.d/sonarr-cron
chmod 0644 /etc/cron.d/sonarr-cron
crontab /etc/cron.d/sonarr-cron

if [ "$RUN_ON_STARTUP" = "true" ]; then
  python /app/calendar-to-discord.py
fi

exec cron -f
