import logging
import sys
from logging.handlers import RotatingFileHandler

# Define log format
LOG_FORMAT = "%(asctime)s - %(levelname)s - %(name)s - %(message)s"

def setup_logging():
    """Configure logging for the application."""
    logger = logging.getLogger("rs-etl-pipeline")
    logger.setLevel(logging.DEBUG)  # Set the lowest level to DEBUG
    logging.getLogger('bibtexparser').setLevel(logging.WARNING)


    # Console Handler (for terminal/GitLab CI/CD)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)  # Only show INFO+ in CI/CD
    console_formatter = logging.Formatter(LOG_FORMAT)
    console_handler.setFormatter(console_formatter)

    # File Handler (for full logs)
    file_handler = RotatingFileHandler("rs_etl_pipeline.log", maxBytes=10*1024*1024, backupCount=5)
    file_handler.setLevel(logging.DEBUG)  # Capture everything (DEBUG+)
    file_formatter = logging.Formatter(LOG_FORMAT)
    file_handler.setFormatter(file_formatter)

    # Attach handlers to the logger
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger
