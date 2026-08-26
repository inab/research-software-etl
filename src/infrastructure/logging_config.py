import logging
import sys

# Define log format
LOG_FORMAT = "%(asctime)s - %(levelname)s - %(name)s - %(message)s"


def resolve_level(name: str | None, default: int = logging.INFO) -> int:
    """Map a level name (e.g. ``"INFO"``, ``"debug"``) to a ``logging`` constant.

    Pure — the CLI reads ``LOG_LEVEL`` from the environment and passes the string
    here, keeping env access at the adapter layer. Unknown names fall back to
    ``default``.
    """
    if not name:
        return default
    return getattr(logging, name.upper(), default)


def setup_logging(level: int = logging.DEBUG):
    """Configure logging for the application (console-only).

    ``level`` sets the verbosity of both the ``rs-etl-pipeline`` logger and its
    console handler. The CLI derives it from the ``LOG_LEVEL`` env var; because
    ``rsetl run`` executes each stage as a subprocess, that env var applies to the
    whole pipeline.
    """
    logger = logging.getLogger("rs-etl-pipeline")
    logger.setLevel(level)
    logging.getLogger('bibtexparser').setLevel(logging.WARNING)

    # Remove any existing handlers to avoid duplicate logs
    if logger.hasHandlers():
        logger.handlers.clear()

    # Console Handler (for terminal/GitLab CI/CD or local dev)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_formatter = logging.Formatter(LOG_FORMAT)
    console_handler.setFormatter(console_formatter)

    # Attach handler to the logger
    logger.addHandler(console_handler)

    return logger