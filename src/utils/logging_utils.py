#!/usr/bin/env python3
# src/utils/logging_utils.py

import logging
import os
import time
from logging.handlers import RotatingFileHandler
from typing import Optional



class EmojiFormatter(logging.Formatter):
    """Custom formatter that adds emojis to log messages"""
    
    EMOJI_LEVELS = {
        logging.DEBUG: "🐛  | ",    
        logging.INFO: "🔵  | ", 
        logging.WARNING: "⚠️  | ",
        logging.ERROR: "❌  | ",
        logging.CRITICAL: "🔥  | "
    }
    
    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record with emoji
        
        Args:
            record: Log record to format
            
        Returns:
            Formatted log string
        """
        emoji = self.EMOJI_LEVELS.get(record.levelno, "")
        record.emoji = emoji
        
        # Use the parent class to do the heavy lifting
        return super().format(record)
        
    def formatTime(self, record: logging.LogRecord, datefmt: Optional[str] = None) -> str:
        """
        Override to format timestamp without milliseconds
        
        Args:
            record: Log record
            datefmt: Date format string
            
        Returns:
            Formatted timestamp
        """
        created = self.converter(record.created)
        if datefmt:
            return time.strftime(datefmt, created)
        return time.strftime("%Y-%m-%d %H:%M:%S", created)
      

def setup_logging(log_dir: str = "/app/logs", log_file: str = "calendarr.log", 
                  debug_mode: bool = False, max_size_mb: int = 1, 
                  backup_count: int = 15) -> logging.Logger:
    """
    Configure logging with file and console handlers
    
    Args:
        log_dir: Directory for log files
        log_file: Log file name
        debug_mode: Whether to enable debug logging
        
    Returns:
        Configured logger
    """
    # Create log directory if needed
    os.makedirs(log_dir, exist_ok=True)
    
    # Set log level based on configuration
    log_level = logging.DEBUG if debug_mode else logging.INFO
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Clear existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Create console handler for terminal output
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_format = EmojiFormatter('%(emoji)s %(asctime)s - %(name)s - %(message)s')
    console_handler.setFormatter(console_format)
    
    # Create rotating file handler for file output
    log_path = os.path.join(log_dir, log_file)
    file_handler = RotatingFileHandler(
        log_path,
        maxBytes=((1024 * 1024) * max_size_mb),  # Convert MB to bytes
        backupCount=backup_count,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.INFO)
    file_format = EmojiFormatter('%(emoji)s %(asctime)s - %(name)s - %(message)s')
    file_handler.setFormatter(file_format)
    
    # Add handlers to root logger
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    
    # Disable Flask's werkzeug logger
    werkzeug_logger = logging.getLogger('werkzeug')
    werkzeug_logger.disabled = True
    
    # Create and return application logger
    logger = logging.getLogger('calendar')
    
    # Test logging
    logger.info("🚀 Logging initialized")
    
    return logger
  
def cleanup_log_files(log_dir: str, max_size: int = 1) -> None:
    """
    Clean up log files that aren't managed by the RotatingFileHandler
    
    Args:
        log_dir: Directory containing log files
        max_size: Maximum log size in MB
    """
    logger = logging.getLogger('calendar')
    
    try:
        # List of files to check
        other_logs = [
            'cron.log', 'wrapper.log', 'minute-test.log', 
            'test_output.log', 'env-fixed.sh', 'calendarr.log'
        ]
        
        for log_name in other_logs:
            log_path = os.path.join(log_dir, log_name)
            if os.path.exists(log_path) and os.path.getsize(log_path) > ((1024 * 1024) * max_size):
                # Truncate the file
                with open(log_path, 'w') as f:
                    f.write(f"Log file truncated at {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                logger.info(f"Truncated log file: {log_path}")
    except Exception as e:
        logger.error(f"Error cleaning up logs: {e}")