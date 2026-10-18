"""
Structured logging configuration for Shorts Studio.
Outputs to both the console and a rotating log file under LOGS_DIR.
"""

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from app.config import settings

# ── Constants ────────────────────────────────────────────────────────────────

_LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s:%(module)s | %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
_MAX_BYTES = 5 * 1024 * 1024  # 5 MB
_BACKUP_COUNT = 5

_configured = False


def _setup_root_logger() -> None:
    """
    Configure the root logger once.

    * Console handler  – writes to stderr with the configured LOG_LEVEL.
    * File handler     – rotating file at ``LOGS_DIR/shorts_studio.log``
      (5 MB rotation, 5 backups).
    """
    global _configured
    if _configured:
        return

    # Make sure the log directory exists
    log_dir = Path(settings.LOGS_DIR)
    log_dir.mkdir(parents=True, exist_ok=True)

    log_file = log_dir / "shorts_studio.log"
    level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

    formatter = logging.Formatter(_LOG_FORMAT, datefmt=_DATE_FORMAT)

    # Console handler
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)

    # Rotating file handler
    file_handler = RotatingFileHandler(
        filename=str(log_file),
        maxBytes=_MAX_BYTES,
        backupCount=_BACKUP_COUNT,
        encoding="utf-8",
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)

    # Apply to root logger
    root = logging.getLogger()
    root.setLevel(level)
    root.addHandler(console_handler)
    root.addHandler(file_handler)

    _configured = True


def get_logger(name: str) -> logging.Logger:
    """
    Return a named logger, ensuring the root logger is configured first.

    Usage::

        from app.logging_config import get_logger
        logger = get_logger(__name__)
        logger.info("Server started")
    """
    _setup_root_logger()
    return logging.getLogger(name)
