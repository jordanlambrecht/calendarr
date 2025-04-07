# app.py
import sys
import io
from contextlib import redirect_stdout, redirect_stderr
import traceback
import datetime
import os
import logging
from logging.handlers import RotatingFileHandler
from flask import Flask
from flask import cli
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import time
import main

from constants import BACKUP_COUNT, DEFAULT_RUN_TIME, MAX_LOG_SIZE, DEFAULT_SCHEDULE_TYPE
os.makedirs('/app/logs', exist_ok=True)

class EmojiFormatter(logging.Formatter):
    """Custom formatter that adds emojis to log messages"""
    EMOJI_LEVELS = {
        logging.DEBUG: "🐛  | ",    
        logging.INFO: "🔵  | ", 
        logging.WARNING: "⚠️  | ",
        logging.ERROR: "❌  | ",
        logging.CRITICAL: "🔥  | "
    }
    
    def format(self, record):
        emoji = self.EMOJI_LEVELS.get(record.levelno, "")
        record.emoji = emoji
        
        # Use the parent class to do the heavy lifting
        return super().format(record)
        
    def formatTime(self, record, datefmt=None):
        """Override to remove milliseconds from timestamp"""
        created = self.converter(record.created)
        if datefmt:
            return time.strftime(datefmt, created)
        return time.strftime("%Y-%m-%d %H:%M:%S", created)


def setup_logging():
    """Configure rotating file handler"""
    log_level = logging.DEBUG if os.environ.get("DEBUG", "").lower() == "true" else logging.INFO
    
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Create console handler for terminal output
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)  # Changed from INFO to log_level
    console_format = EmojiFormatter('%(emoji)s %(asctime)s - %(name)s - %(message)s')
    console_handler.setFormatter(console_format)
    
    # Create rotating file handler for file output
    file_handler = RotatingFileHandler(
        '/app/logs/calendarr.log',
        maxBytes=((1024 * 1024) * MAX_LOG_SIZE),
        backupCount=BACKUP_COUNT,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.INFO)
    file_format = EmojiFormatter('%(emoji)s %(asctime)s - %(name)s - %(message)s')
    file_handler.setFormatter(file_format)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    werkzeug_logger = logging.getLogger('werkzeug')
    werkzeug_logger.disabled = True
    
    logger = logging.getLogger('app')
    
    return logger


logger = setup_logging()

try:
    logger.info("🚀  Application starting up - log file test entry")
    with open('/app/logs/calendarr.log', 'a') as f:
        f.write(f"Direct write test at {datetime.datetime.now()}\n")
except Exception as e:
    print(f"ERROR: Could not write to log file: {e}")
    

app = Flask(__name__)
cli = sys.modules['flask.cli']
cli.show_server_banner = lambda *_: None  # Disable the annoying Flask "dev server only" banner

def run_main_job():
    """Run the main calendar-to-discord script"""
    logger.info("Running main job")

    try:
        output = io.StringIO()
        with redirect_stdout(output), redirect_stderr(output):
            main.main()
        
        logger.info(f"Job output: {output.getvalue()}")
    except Exception as e:
        logger.error(f"Error in main job: {str(e)}")

        logger.error(traceback.format_exc())
    
    logger.info("Job function complete, container should stay running")

def log_ping():
    """Log a ping message every minute when debug is enabled"""
    if os.environ.get("DEBUG", "").lower() == "true":
        logger.debug("🔄 Ping - Application is running")

# def run_test_job():
#     """Run a test job every minute for debugging"""
#     logger.info(f"Test job ran at: {datetime.datetime.now()} in timezone {os.environ.get('TZ', 'undefined')}")

def cleanup_other_logs():
    """Clean up other log files that aren't managed by the RotatingFileHandler"""
    try:
        log_dir = '/app/logs'
        other_logs = [
            'cron.log', 'wrapper.log', 'minute-test.log', 
            'test_output.log', 'env-fixed.sh'
        ]
        
        for log_name in other_logs:
            log_path = os.path.join(log_dir, log_name)
            if os.path.exists(log_path) and os.path.getsize(log_path) > ((1024 * 1024) * MAX_LOG_SIZE):

                with open(log_path, 'w') as f:
                    f.write(f"Log file truncated at {datetime.datetime.now()}\n")
                logger.info(f"Truncated log file: {log_path}")
    except Exception as e:
        logger.error(f"Error cleaning up logs: {e}")

# Add a default route
@app.route('/')
def index():
    """Root endpoint"""
    return {'status': 'running', 'scheduler': 'active'}

@app.route('/health')
def health():
    """Health check endpoint for Docker"""
    return {"status": "healthy", "timestamp": datetime.datetime.now().isoformat()}

# Initialize and configure the scheduler
def init_scheduler():
    scheduler = BackgroundScheduler()
    
    # Add debug ping job if debug is enabled
    if os.environ.get("DEBUG", "").lower() == "true":
        scheduler.add_job(log_ping, 'interval', minutes=1, id='debug_ping_job')
        logger.info("🪲 Debug mode enabled - adding ping job")
    

    
    # Configure the main job based on environment variables
    schedule_type = os.environ.get("SCHEDULE_TYPE", DEFAULT_SCHEDULE_TYPE).upper()
    
    # Use RUN_TIME if specified, otherwise default
    run_time = os.environ.get("RUN_TIME", DEFAULT_RUN_TIME)
    hour, minute = run_time.split(":")
    
    if schedule_type == "DAILY":
        # Daily job at specified time
        logger.info(f"Scheduling DAILY job at {run_time}")
        scheduler.add_job(
            run_main_job, 
            CronTrigger(hour=hour, minute=minute),
            id='main_job'
        )
    else:
        # Weekly job at specified time and day
        schedule_day = os.environ.get("SCHEDULE_DAY", "1")  # Default to Monday
        logger.info(f"Scheduling WEEKLY job at {run_time} on day {schedule_day}")
        scheduler.add_job(
            run_main_job, 
            CronTrigger(day_of_week=schedule_day, hour=hour, minute=minute),
            id='main_job'
        )
    
    # Handle direct CRON_SCHEDULE if specified (advanced usage)
    cron_schedule = os.environ.get("CRON_SCHEDULE")
    if cron_schedule:
        logger.info(f"Using custom cron schedule: {cron_schedule}")
        # Remove any existing main job
        try:
            scheduler.remove_job('main_job')
        except:
            pass
            
        # Add the custom scheduled job
        scheduler.add_job(
            run_main_job,
            CronTrigger.from_crontab(cron_schedule),
            id='main_job'
        )
    
    # Run on startup if configured
    if os.environ.get("RUN_ON_STARTUP", "").lower() == "true":
        logger.info("Running job on startup")
        run_main_job()
    
    # Start the scheduler
    scheduler.start()
    logger.info("Scheduler started")
    return scheduler

if __name__ == "__main__":
    # Initialize the scheduler
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