# src/calendarr/log.py
"""Logging setup, console plus rotating file."""

import logging
import os
import time
from logging.handlers import RotatingFileHandler

from calendarr.config import Config


class EmojiFormatter(logging.Formatter):
    """Prefixes log lines with a level emoji."""

    EMOJI_LEVELS = {
        logging.DEBUG: "🐛  | ",
        logging.INFO: "🔵  | ",
        logging.WARNING: "⚠️  | ",
        logging.ERROR: "❌  | ",
        logging.CRITICAL: "🔥  | ",
    }

    def format(self, record: logging.LogRecord) -> str:
        record.emoji = self.EMOJI_LEVELS.get(record.levelno, "")
        return super().format(record)

    def formatTime(self, record, datefmt=None):  # noqa: N802
        return time.strftime(datefmt or "%Y-%m-%d %H:%M:%S", self.converter(record.created))


def setup_logging(config: Config) -> None:
    os.makedirs(config.log_dir, exist_ok=True)
    level = logging.DEBUG if config.debug else logging.INFO
    formatter = EmojiFormatter("%(emoji)s%(asctime)s - %(name)s - %(message)s")

    root = logging.getLogger()
    root.setLevel(level)
    for handler in root.handlers[:]:
        root.removeHandler(handler)

    console = logging.StreamHandler()
    console.setFormatter(formatter)
    root.addHandler(console)

    try:
        file_handler = RotatingFileHandler(
            os.path.join(config.log_dir, config.log_file),
            maxBytes=config.log_max_size_mb * 1024 * 1024,
            backupCount=config.log_backup_count,
            encoding="utf-8",
        )
        file_handler.setFormatter(formatter)
        file_handler.setLevel(logging.INFO)
        root.addHandler(file_handler)
    except OSError as e:
        root.warning("File logging disabled, %s is not writable (%s)", config.log_dir, e)

    if config.debug:
        root.info("Debug logging enabled")
