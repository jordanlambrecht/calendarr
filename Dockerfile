FROM python:3.13.3-slim

WORKDIR /app

LABEL org.opencontainers.image.source=https://github.com/jordanlambrecht/calendarr
LABEL org.opencontainers.image.description="Calendar feeds from Sonarr/Radarr to Discord and Slack"
LABEL org.opencontainers.image.licenses=GPL-3.0

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ /app/src/

# Default custom footer templates live in a separate location so the
# entrypoint can seed a mounted volume on first run
COPY ./calendarr/custom_footers /app/default_footers/

COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

RUN mkdir -p /app/logs

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/src

EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
  CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:5000/health')"]

ENTRYPOINT ["/app/entrypoint.sh"]

CMD ["python", "-m", "calendarr"]
