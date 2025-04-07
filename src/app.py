#!/usr/bin/env python3
# src/app.py

import sys
import io
from contextlib import redirect_stdout, redirect_stderr
import traceback
import datetime
import os
import logging

from flask import Flask
from flask import cli
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import main


os.makedirs('/app/logs', exist_ok=True)


from config.settings import load_config_from_env
from utils.logging_utils import setup_logging, cleanup_log_files

app = Flask(__name__)

# Disable the annoying Flask "dev server only" banner
cli = sys.modules['flask.cli']
cli.show_server_banner = lambda *_: None  

config = None
logger = None


def init_app():
    """Initialize application configuration and logging"""
    global config, logger
    
    config = load_config_from_env()

    logger = setup_logging(
        log_dir=config.logging_settings.log_dir,
        log_file=config.logging_settings.log_file,
        debug_mode=config.logging_settings.debug_mode,
        max_size_mb=config.logging_settings.max_size_mb,
        backup_count=config.logging_settings.backup_count
    )
    
    if config.logging_settings.debug_mode:
        logger.setLevel("DEBUG")
        logger.info("🪲 Running in DEBUG mode")
        
    logger.info("Application initialized with configuration")
    return config

    


def run_main_job():
    """Run the main calendar-to-discord script"""
    logger.info("⚙️  Running main job")

    try:
        # Capture output from main function
        output = io.StringIO()
        with redirect_stdout(output), redirect_stderr(output):
            success = main.main()
        
        logger.info(f"Job output: {output.getvalue()}")
        logger.info(f"✅  Job completed with success: {success}")
        
    except Exception as e:
        logger.error(f"☠️  Error in main job: {str(e)}")
        logger.error(traceback.format_exc())
    
    logger.info("✅  Job function complete, container should stay running")

def log_ping():
    """Log a ping message every minute when debug is enabled"""
    if os.environ.get("DEBUG", "").lower() == "true":
        logger.debug("🔄  Ping - Application is running")


# Flask routes
@app.route('/')
def index():
    """Root endpoint"""
    return {'status': 'running', 'scheduler': 'active'}

@app.route('/health')
def health():
    """Health check endpoint for Docker"""
    return {"status": "healthy", "timestamp": datetime.datetime.now().isoformat()}


# Initialize/configure the scheduler
def init_scheduler():
    """
    Initialize and configure the scheduler
    
    Args:
        config: Application configuration
        
    Returns:
        Configured scheduler
    """
    global config
    scheduler = BackgroundScheduler()
    
    # Add debug ping job if debug is enabled
    if config.logging_settings.debug_mode:
        scheduler.add_job(log_ping, 'interval', minutes=1, id='debug_ping_job')
        logger.info("🪲 Debug mode enabled - adding ping job")


    # log cleanup job
    scheduler.add_job(
        lambda: cleanup_log_files(
            config.logging_settings.log_dir,
            config.logging_settings.max_size_mb
        ),
        'interval',
        hours=24,
        id='log_cleanup_job'
    )

    
    # Configure main job
    schedule = config.schedule_settings

    if schedule.cron_schedule:
        logger.info(f"Using custom cron schedule: {schedule.cron_schedule}")
        try:
            scheduler.add_job(
                run_main_job,
                CronTrigger.from_crontab(schedule.cron_schedule),
                id='main_job'
            )
        except Exception as e:
            logger.error(f"Invalid cron schedule: {e}")
            # Fall back to default scheduling
            logger.info("Falling back to default schedule")
            schedule.cron_schedule = None
            

    # If no custom cron schedule, use schedule type
    if not schedule.cron_schedule:
        if schedule.schedule_type == "DAILY":
            # Daily job at specified time
            logger.info(f"Scheduling DAILY job at {schedule.hour}:{schedule.minute}")
            scheduler.add_job(
                run_main_job, 
                CronTrigger(hour=schedule.hour, minute=schedule.minute),
                id='main_job'
            )
        else:
            # Weekly job at specified time and day
            logger.info(f"Scheduling WEEKLY job at {schedule.hour}:{schedule.minute} "
                       f"on day {schedule.schedule_day}")
            scheduler.add_job(
                run_main_job, 
                CronTrigger(
                    day_of_week=schedule.schedule_day, 
                    hour=schedule.hour, 
                    minute=schedule.minute
                ),
                id='main_job'
            )
    

    # Run on startup if configured
    if schedule.run_on_startup:
        logger.info("Running job on startup")
        scheduler.add_job(
            run_main_job,
            'date', 
            run_date=datetime.datetime.now() + datetime.timedelta(seconds=5),
            id='startup_job'
        )
    
    # Start the scheduler
    scheduler.start()
    logger.info("Scheduler started")
    return scheduler

if __name__ == "__main__":
    # Initialize the scheduler
    config = init_app()
    scheduler = init_scheduler()
    
    # Disable all Flask logging
    import logging
    log = logging.getLogger('werkzeug')
    log.disabled = True
    
    app.run(
        host='0.0.0.0', 
        port=5000, 
        debug=False,
        use_reloader=False,
        threaded=True
    )