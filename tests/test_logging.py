"""
Tests for logging configuration.

Tests logging setup and configuration.
"""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path

import pytest

from src.logging import configure_logging, get_logger, reset_logging


def test_configure_logging_basic() -> None:
    """Test basic logging configuration."""
    reset_logging()
    configure_logging(level="DEBUG")

    logger = get_logger(__name__)
    assert logger.level == logging.NOTSET  # Uses root logger level

    root_logger = logging.getLogger()
    assert root_logger.level == logging.DEBUG


def test_configure_logging_with_file() -> None:
    """Test logging configuration with file output."""
    reset_logging()

    with tempfile.TemporaryDirectory() as tmpdir:
        log_file = Path(tmpdir) / "test.log"

        configure_logging(level="INFO", log_to_file=True, log_file=str(log_file))

        logger = get_logger(__name__)
        logger.info("Test message")

        # File should be created
        assert log_file.exists()

        # Should contain the message
        content = log_file.read_text()
        assert "Test message" in content


def test_configure_logging_levels() -> None:
    """Test different logging levels."""
    for level in ["DEBUG", "INFO", "WARNING", "ERROR"]:
        reset_logging()
        configure_logging(level=level)

        root_logger = logging.getLogger()
        expected_level = getattr(logging, level)
        assert root_logger.level == expected_level


def test_get_logger_returns_logger() -> None:
    """Test get_logger returns Logger instance."""
    logger = get_logger("test_module")

    assert isinstance(logger, logging.Logger)
    assert logger.name == "test_module"


def test_configure_logging_only_once() -> None:
    """Test that configure_logging only runs once."""
    reset_logging()

    configure_logging(level="DEBUG")
    root_logger = logging.getLogger()
    handler_count = len(root_logger.handlers)

    # Call again - should not add more handlers
    configure_logging(level="INFO")
    assert len(root_logger.handlers) == handler_count


def test_configure_logging_custom_format() -> None:
    """Test logging with custom format string."""
    reset_logging()

    custom_format = "%(levelname)s - %(message)s"
    configure_logging(level="INFO", format_string=custom_format)

    # Should not raise an error
    logger = get_logger(__name__)
    logger.info("Test")


def test_logging_to_directory_creation() -> None:
    """Test that log directory is created if it doesn't exist."""
    reset_logging()

    with tempfile.TemporaryDirectory() as tmpdir:
        log_dir = Path(tmpdir) / "logs" / "nested"
        log_file = log_dir / "test.log"

        configure_logging(level="INFO", log_to_file=True, log_file=str(log_file))

        logger = get_logger(__name__)
        logger.info("Test")

        assert log_dir.exists()
        assert log_file.exists()


def test_reset_logging() -> None:
    """Test reset_logging clears handlers."""
    reset_logging()
    configure_logging(level="INFO")

    root_logger = logging.getLogger()
    assert len(root_logger.handlers) > 0

    reset_logging()
    assert len(root_logger.handlers) == 0
