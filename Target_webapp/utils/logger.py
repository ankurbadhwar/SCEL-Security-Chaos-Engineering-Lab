"""
Target WebApp structured logger.

Replaces the original print() wrapper with the standard `logging` module.
Output format: [LEVEL] YYYY-MM-DD HH:MM:SS — message

Usage:
    from utils.logger import log_event
    log_event("User logged in")          # INFO
    log_event("Token mismatch", "warn")  # WARNING
    log_event("Upload failed", "error")  # ERROR
"""

import logging

logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)s] %(asctime)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

_logger = logging.getLogger("scel.webapp")


def log_event(message: str, level: str = "info") -> None:
    """Log a message at the given level (info/warn/error)."""
    level = level.lower()
    if level == "warn" or level == "warning":
        _logger.warning(message)
    elif level == "error":
        _logger.error(message)
    else:
        _logger.info(message)