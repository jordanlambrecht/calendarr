# src/calendarr/deliver.py
"""Webhook delivery with rate limit handling and a bounded retry budget."""

import logging
import time

import requests

logger = logging.getLogger("deliver")

DISCORD_SUCCESS = (200, 204)
SLACK_SUCCESS = (200, 201, 204)
RETRY_BUDGET_SECONDS = 60
TRANSIENT_RETRY_DELAY = 2


def _retry_after_seconds(response: requests.Response) -> float:
    header = response.headers.get("Retry-After")
    if header:
        try:
            return max(0.0, float(header))
        except ValueError:
            pass
    try:
        return max(0.0, float(response.json().get("retry_after", TRANSIENT_RETRY_DELAY)))
    except Exception:
        return TRANSIENT_RETRY_DELAY


def send_payload(webhook_url: str, payload: dict, success_codes: tuple, timeout: int, deadline: float) -> bool:
    """POST one payload, retrying 429 and transient errors until the deadline."""
    while True:
        try:
            response = requests.post(
                webhook_url, json=payload, headers={"Content-Type": "application/json"}, timeout=timeout
            )
        except requests.RequestException as e:
            if time.monotonic() + TRANSIENT_RETRY_DELAY < deadline:
                logger.warning("Webhook request failed (%s), retrying", e.__class__.__name__)
                time.sleep(TRANSIENT_RETRY_DELAY)
                continue
            logger.error("Webhook request failed with no retry budget left (%s)", e)
            return False

        if response.status_code in success_codes:
            return True

        if response.status_code == 429:
            wait = _retry_after_seconds(response)
            if time.monotonic() + wait < deadline:
                logger.warning("Rate limited, waiting %.1fs before retry", wait)
                time.sleep(wait)
                continue
            logger.error("Rate limited and retry budget exhausted")
            return False

        if 500 <= response.status_code < 600 and time.monotonic() + TRANSIENT_RETRY_DELAY < deadline:
            logger.warning("Webhook returned %s, retrying", response.status_code)
            time.sleep(TRANSIENT_RETRY_DELAY)
            continue

        logger.error("Webhook rejected payload with %s, %s", response.status_code, response.text[:300])
        return False


def send_payloads(webhook_url: str, payloads: list[dict], success_codes: tuple, timeout: int) -> bool:
    """Send payloads in order. Stops at the first hard failure."""
    deadline = time.monotonic() + RETRY_BUDGET_SECONDS
    for i, payload in enumerate(payloads):
        if not send_payload(webhook_url, payload, success_codes, timeout, deadline):
            logger.error("Stopping after payload %s of %s failed", i + 1, len(payloads))
            return False
    logger.info("Delivered %s payloads", len(payloads))
    return True
