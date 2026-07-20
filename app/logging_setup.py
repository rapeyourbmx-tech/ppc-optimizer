"""Application logging configuration."""

import logging
from datetime import date
from pathlib import Path

_LOGGER_NAME = "ppc_optimizer"
_LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"
_DEFAULT_LOGS_DIRECTORY = Path("logs")


def configure_logging(
    *,
    verbose: bool = False,
    logs_directory: Path = _DEFAULT_LOGS_DIRECTORY,
) -> logging.Logger:
    """Configure file logging and return the application logger.

    The logs directory is created automatically and one file per day is
    written as logs/YYYY-MM-DD.log. The logger records DEBUG messages only
    in verbose mode and INFO and above otherwise. Reconfiguring replaces
    the previous handler, so repeated runs never duplicate log lines.

    Raises:
        OSError: If the logs directory or the log file cannot be created.
    """
    logs_directory.mkdir(parents=True, exist_ok=True)
    log_path = logs_directory / f"{date.today().isoformat()}.log"

    logger = get_logger()
    logger.setLevel(logging.DEBUG if verbose else logging.INFO)
    logger.propagate = False
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        handler.close()

    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setFormatter(logging.Formatter(_LOG_FORMAT))
    logger.addHandler(file_handler)
    return logger


def get_logger() -> logging.Logger:
    """Return the application logger."""
    return logging.getLogger(_LOGGER_NAME)
