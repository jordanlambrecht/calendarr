FROM python:3.13.3-slim

WORKDIR /app

LABEL org.opencontainers.image.source=https://github.com/jordanlambrecht/calendarr
LABEL org.opencontainers.image.description="Calendar feeds from Sonarr/Radarr to Discord and Slack"
LABEL org.opencontainers.image.licenses=GPL-3.0

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY src/ /app/src/

# Copy the default custom footer templates to a SEPARATE location
COPY ./calendarr/custom_footers /app/default_footers/

# Copy and set up the entrypoint script
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Create logs directory
RUN mkdir -p /app/logs

ENV PYTHONUNBUFFERED=1

EXPOSE 5000

# Set the entrypoint script
ENTRYPOINT ["/app/entrypoint.sh"]

# Set the default command (will be executed by entrypoint's exec "$@")
CMD ["python", "src/app.py"]