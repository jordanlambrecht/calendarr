FROM python:3.9-slim

WORKDIR /app

LABEL org.opencontainers.image.source=https://github.com/jordanlambrecht/calendarr
LABEL org.opencontainers.image.description="Calendar feeds from Sonarr/Radarr to Discord"
LABEL org.opencontainers.image.licenses=GPL-3.0

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY calendar-to-discord.py .

# Install cron
RUN apt-get update && apt-get install -y cron

# Create log directory
RUN mkdir -p /app/logs && touch /app/cron.log

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]