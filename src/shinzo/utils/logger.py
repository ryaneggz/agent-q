"""Logging utility for the application using Loguru"""
import sys
from loguru import logger

# Export the base logger for direct use if needed
__all__ = ["logger", "setup_logging", "get_logger"]

# Define a log format that is readable and user-friendly
LOG_FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
    "<level>{message}</level>"
    "<level>{exception}</level>"  # Add exception/stacktrace to format
)


def setup_logging():
    """Configure logging for the application using Loguru"""
    # Import here to avoid circular imports
    from shinzo.config import settings

    # Remove default handler
    logger.remove()

    # Add a console handler for terminal logging
    logger.add(
        sys.stdout,
        format=LOG_FORMAT,
        level=settings.log_level.upper(),  # Change to DEBUG for verbose output
        colorize=True,
        backtrace=True,  # Show error backtraces for easier debugging
        # diagnose=True,   # Show variable values in tracebacks
        # catch=True,      # Catch exceptions and show full traceback
    )


def get_logger(name: str):
    """
    Get a logger instance bound with the module name

    Args:
        name: The name of the module (typically __name__)

    Returns:
        A loguru logger instance bound with the module name
    """
    return logger.bind(name=name)
