"""
Logging configuration for the application.

Provides centralized logging setup with support for console and file output.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Optional

# Global flag to track if logging has been configured
_configured = False


def configure_logging(
    level: str = "INFO",
    log_to_file: bool = False,
    log_file: Optional[str | Path] = None,
    log_dir: str = "logs",
    format_string: Optional[str] = None,
) -> None:
    """
    Configure application-wide logging.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_to_file: Enable file logging in addition to console
        log_file: Specific log file path (optional)
        log_dir: Directory for log files (used if log_file not specified)
        format_string: Custom log format string (optional)

    Example:
        configure_logging(level="DEBUG", log_to_file=True)
    """
    global _configured

    if _configured:
        return

    # Convert level string to logging constant
    numeric_level = getattr(logging, level.upper(), logging.INFO)

    # Default format
    if format_string is None:
        format_string = "[%(asctime)s] %(levelname)s [%(name)s:%(lineno)d] %(message)s"

    # Date format
    date_format = "%Y-%m-%d %H:%M:%S"

    # Create formatter
    formatter = logging.Formatter(format_string, datefmt=date_format)

    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)

    # Remove existing handlers
    root_logger.handlers.clear()

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # File handler (optional)
    if log_to_file:
        if log_file is None:
            log_file = Path(log_dir) / "app.log"
        else:
            log_file = Path(log_file)

        # Create log directory if it doesn't exist
        log_file.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(numeric_level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

        root_logger.info(f"Logging to file: {log_file}")

    _configured = True
    root_logger.debug(f"Logging configured at {level} level")


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for a module.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Logger instance

    Example:
        logger = get_logger(__name__)
        logger.info("Processing started")
    """
    return logging.getLogger(name)


def reset_logging() -> None:
    """Reset logging configuration (mainly for testing)."""
    global _configured
    _configured = False

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.setLevel(logging.WARNING)
