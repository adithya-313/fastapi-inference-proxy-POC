"""
app/core/logging.py

This file sets up logging - a way to track what's happening in our application.
Logging is like putting print statements throughout your code, but better:

1. You can control how much detail you see (INFO, WARNING, ERROR)
2. You can save logs to files
3. You can turn logging off in production if needed

Think of it as an "invisible stopwatch" that records timestamps and events.
"""

# Import Python's built-in logging module
import logging

# Import sys for accessing system-specific parameters
import sys


def setup_logging(level: int = logging.INFO) -> None:
    """
    Set up the logging configuration for our application.

    This function:
    1. Creates a handler that writes to the console (stdout)
    2. Formats each log message to include timestamp, logger name, level, and message
    3. Attaches the handler to the root logger

    Args:
        level: The minimum log level to show (default: INFO)
               Options: DEBUG, INFO, WARNING, ERROR, CRITICAL
    """
    # Create a handler that writes log messages to the console
    # sys.stdout is the standard output (your terminal)
    handler = logging.StreamHandler(sys.stdout)

    # Set the minimum log level for this handler
    # Messages below this level will be ignored
    handler.setLevel(level)

    # Create a format for our log messages
    # %(asctime)s = When the log was created (timestamp)
    # %(name)s = Which part of the code created the log
    # %(levelname)s = What type of message (INFO, WARNING, etc.)
    # %(message)s = The actual message
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",  # Format the timestamp nicely
    )

    # Attach the formatter to the handler
    handler.setFormatter(formatter)

    # Get the root logger - this is the top-level logger
    # All other loggers are children of this one
    root_logger = logging.getLogger()

    # Set the minimum log level for the root logger
    root_logger.setLevel(level)

    # Attach our handler to the root logger
    # Now all loggers will use our handler
    root_logger.addHandler(handler)

    # Reduce noise from HTTP libraries
    # These libraries are very chatty, so we lower their log level
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)