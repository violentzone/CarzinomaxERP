"""Logging helpers built on top of loguru.

Provides two factory functions that return a scoped loguru logger:

- ``system_log()``: a system-level logger for startup, shutdown, and other
  events that are not tied to a specific user. Logs are written to
  ``backend/logs/system/system.log``.
- ``user_log(user_id)``: a per-user logger. Each user gets a dedicated
  directory named by their ``user_id`` under ``backend/logs/users/``.

Records are filtered by an ``extra["scope"]`` tag so each file sink only
receives the records that belong to it.
"""
import sys
from pathlib import Path

from loguru import logger

# Base logs directory: backend/logs
LOGS_DIR = Path(__file__).resolve().parent.parent.parent / "logs"
SYSTEM_LOGS_DIR = LOGS_DIR / "system"
USER_LOGS_DIR = LOGS_DIR / "users"

# Shared settings for file sinks
_ROTATION = "10 MB"
_RETENTION = "30 days"
_ENCODING = "utf-8"
_FILE_FORMAT = (
    "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | "
    "{extra[scope]} | {name}:{function}:{line} - {message}"
)

# Remove loguru's default stderr handler so we control all sinks ourselves.
logger.remove()

# Console sink for convenience during development.
logger.add(
    sys.stderr,
    level="INFO",
    format=(
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | "
        "<cyan>{extra[scope]}</cyan> | <level>{message}</level>"
    ),
)

# Scopes that already have a dedicated file sink, so repeated calls don't
# register duplicate handlers.
_registered_scopes: set[str] = set()


def _add_file_sink(scope: str, log_file: Path):
    """Register a file sink for ``scope`` once and return the bound logger.

    Args:
        scope: Unique scope name used to filter records to this sink.
        log_file: Destination file path for this scope's records. Its
            parent directory is created if it does not exist.

    Returns:
        loguru.Logger: A logger bound to ``scope``.
    """
    log_file.parent.mkdir(parents=True, exist_ok=True)

    if scope not in _registered_scopes:
        logger.add(
            log_file,
            level="DEBUG",
            format=_FILE_FORMAT,
            rotation=_ROTATION,
            retention=_RETENTION,
            encoding=_ENCODING,
            enqueue=True,
            filter=lambda record, s=scope: record["extra"].get("scope") == s,
        )
        _registered_scopes.add(scope)

    return logger.bind(scope=scope)


def system_log():
    """Return the system-level logger.

    Records system startup, termination, and any event not related to a
    specific user. Logs are stored in ``backend/logs/system/system.log``.

    Returns:
        loguru.Logger: A logger bound to the ``system`` scope.
    """
    return _add_file_sink("system", SYSTEM_LOGS_DIR / "system.log")


def user_log(user_id: str | int):
    """Return a logger for a specific user.

    Each user gets a dedicated directory named by their ``user_id`` under
    ``backend/logs/users/``. Logs are stored in
    ``backend/logs/users/<user_id>/user.log``.

    Args:
        user_id: The identifier of the user. Used as the directory name
            and as part of the logging scope.

    Returns:
        loguru.Logger: A logger bound to the ``user:<user_id>`` scope.
    """
    user_id = str(user_id)
    return _add_file_sink(f"user:{user_id}", USER_LOGS_DIR / user_id / "user.log")
