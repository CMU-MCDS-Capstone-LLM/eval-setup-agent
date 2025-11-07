"""Logging configuration and utilities."""

import logging
import sys
from pathlib import Path
from typing import Optional


def setup_logging(
    log_file: Optional[Path] = None, level: int = logging.INFO, name: str = "env_setup_agent"
) -> logging.Logger:
    """
    Setup logging with both file and console handlers.

    Args:
        log_file: Optional path to log file. If provided, logs to both file and stdout.
                 If None, logs only to stdout.
        level: Logging level (default: INFO)
        name: Logger name (default: env_setup_agent)

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Clear any existing handlers
    logger.handlers.clear()

    # Create formatter
    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(filename)s:%(lineno)d: %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Console handler (stdout)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File handler (if log_file provided)
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, mode="w")
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    # Prevent propagation to root logger
    logger.propagate = False

    return logger


def get_logger(name: str = "env_setup_agent") -> logging.Logger:
    """
    Get logger instance.

    Args:
        name: Logger name (default: env_setup_agent)

    Returns:
        Logger instance
    """
    return logging.getLogger(name)
