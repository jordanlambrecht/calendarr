FROM python:3.9-slim

WORKDIR /app

LABEL org.opencontainers.image.source=https://github.com/jordanlambrecht/calendarr
LABEL org.opencontainers.image.description="Calendar feeds from Sonarr/Radarr to Discord and Slack"
LABEL org.opencontainers.image.licenses=GPL-3.0

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
# COPY *.py /app/
COPY src/ /app/

RUN mkdir -p /app/logs

ENV PYTHONUNBUFFERED=1

EXPOSE 5000
# Set the command that runs when the container starts
CMD ["python", "app.py"]