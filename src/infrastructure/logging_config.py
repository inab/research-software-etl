import logging
import sys

# Define log format
LOG_FORMAT = "%(asctime)s - %(levelname)s - %(name)s - %(message)s"

def setup_logging():
    """Configure logging for the application (console-only)."""
    logger = logging.getLogger("rs-etl-pipeline")
    logger.setLevel(logging.DEBUG)  # Capture everything
    logging.getLogger('bibtexparser').setLevel(logging.WARNING)

    # Remove any existing handlers to avoid duplicate logs
    if logger.hasHandlers():
        logger.handlers.clear()

    # Console Handler (for terminal/GitLab CI/CD or local dev)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)  # Show everything
    console_formatter = logging.Formatter(LOG_FORMAT)
    console_handler.setFormatter(console_formatter)

    # Attach handler to the logger
    logger.addHandler(console_handler)

    return logger