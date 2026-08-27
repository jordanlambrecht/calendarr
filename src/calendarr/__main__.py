# src/calendarr/__main__.py
"""Entry point. Daemon mode by default, `python -m calendarr run` for one shot."""

import logging
import sys
import threading
import traceback
from datetime import datetime

from calendarr import scheduler as sched
from calendarr.config import Config, load_config
from calendarr.deliver import DISCORD_SUCCESS, SLACK_SUCCESS, send_payloads
from calendarr.health import Status, start_health_server
from calendarr.ingest import fetch_all
from calendarr.log import setup_logging
from calendarr.render import (
    DISCORD_FOOTER_FILE,
    SLACK_FOOTER_FILE,
    discord_payloads,
    read_footer,
    slack_payloads,
)
from calendarr.report import build_report, calculate_range

logger = logging.getLogger("main")

OUTCOME_SUCCESS = "success"
OUTCOME_SKIPPED = "skipped_all_sources_failed"
OUTCOME_ERROR = "error"


def run_once(config: Config) -> str:
    now = datetime.now(config.tz)
    start, end = calculate_range(config, now)
    logger.info("Run window %s to %s", start.date(), end.date())

    results = fetch_all(config, start, end)
    report = build_report(config, results, start, end, now)

    if report.all_sources_failed:
        logger.error("Every calendar source failed, skipping the post entirely")
        return OUTCOME_SKIPPED

    ok = True
    if config.use_discord and config.discord_webhook_url:
        footer = read_footer(DISCORD_FOOTER_FILE) if config.enable_custom_discord_footer else ""
        payloads = discord_payloads(report, config, footer)
        logger.info("Sending %s Discord payloads", len(payloads))
        ok = send_payloads(config.discord_webhook_url, payloads, DISCORD_SUCCESS, config.http_timeout) and ok
    if config.use_slack and config.slack_webhook_url:
        footer = read_footer(SLACK_FOOTER_FILE) if config.enable_custom_slack_footer else ""
        payloads = slack_payloads(report, config, footer)
        logger.info("Sending %s Slack payloads", len(payloads))
        ok = send_payloads(config.slack_webhook_url, payloads, SLACK_SUCCESS, config.http_timeout) and ok
    return OUTCOME_SUCCESS if ok else OUTCOME_ERROR


def make_job(config: Config, status: Status):
    def job():
        logger.info("Job starting")
        try:
            outcome = run_once(config)
        except Exception:
            logger.error("Job crashed\n%s", traceback.format_exc())
            outcome = OUTCOME_ERROR
        status.record_run(outcome)
        sched.write_marker(config, datetime.now(config.tz), outcome)
        logger.info("Job finished with outcome %s", outcome)

    return job


def run_daemon() -> int:
    try:
        config = load_config()
    except ValueError as e:
        print(f"Configuration error. {e}", file=sys.stderr)
        return 1
    setup_logging(config)

    status = Status()
    job = make_job(config, status)
    scheduler = sched.create_scheduler(config, job)

    now = datetime.now(config.tz)
    if config.run_on_startup:
        logger.info("RUN_ON_STARTUP enabled, running now")
        scheduler.add_job(job, id="startup_job")
    elif sched.needs_catch_up(config, now):
        logger.info("Running missed job from downtime catch up")
        scheduler.add_job(job, id="catchup_job")

    scheduler.start()
    status.scheduler_running = True
    server = start_health_server(status)
    logger.info("Scheduler started, next run %s", scheduler.get_job("main_job").next_run_time)

    stop = threading.Event()
    try:
        stop.wait()
    except KeyboardInterrupt:
        logger.info("Shutting down")
    finally:
        scheduler.shutdown(wait=False)
        server.shutdown()
    return 0


def run_single() -> int:
    try:
        config = load_config()
    except ValueError as e:
        print(f"Configuration error. {e}", file=sys.stderr)
        return 1
    setup_logging(config)
    outcome = run_once(config)
    return 0 if outcome == OUTCOME_SUCCESS else 1


def main(argv: list[str]) -> int:
    if "run" in argv:
        return run_single()
    return run_daemon()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
