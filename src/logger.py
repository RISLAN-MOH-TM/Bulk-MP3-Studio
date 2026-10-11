"""
Logger module for Bulk MP3 Studio.
Provides both file logging and an in-memory queue/ring-buffer for real-time UI display.
"""

import collections
import logging
import os
import sys
from pathlib import Path
from typing import List, Callable, Optional


LOG_MAX_ENTRIES = 1000
_log_history: collections.deque = collections.deque(maxlen=LOG_MAX_ENTRIES)
_log_listeners: List[Callable[[str], None]] = []


class UILogHandler(logging.Handler):
    """Logging handler that retains recent messages and notifies UI listeners."""

    def __init__(self):
        super().__init__()
        self.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s", "%H:%M:%S"))

    def emit(self, record: logging.LogRecord):
        try:
            msg = self.format(record)
            _log_history.append(msg)
            for listener in list(_log_listeners):
                try:
                    listener(msg)
                except Exception:
                    pass
        except Exception:
            self.handleError(record)


def get_log_dir() -> Path:
    """Return the directory where logs should be stored."""
    app_data = os.getenv("APPDATA")
    if app_data:
        log_dir = Path(app_data) / "BulkMP3Studio" / "logs"
    else:
        log_dir = Path.home() / ".bulk_mp3_studio" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir


def get_log_file_path() -> Path:
    return get_log_dir() / "bulk_mp3_studio.log"


_initialized = False


def setup_logging(level=logging.INFO) -> None:
    """Initialize application root logger with console, file, and UI handlers."""
    global _initialized
    if _initialized:
        return
    _initialized = True

    root_logger = logging.getLogger("BulkMP3Studio")
    root_logger.setLevel(level)

    # UI in-memory handler
    ui_handler = UILogHandler()
    ui_handler.setLevel(level)
    root_logger.addHandler(ui_handler)

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(
        logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s", "%Y-%m-%d %H:%M:%S")
    )
    root_logger.addHandler(console_handler)

    # File handler
    try:
        log_file = get_log_file_path()
        file_handler = logging.FileHandler(str(log_file), encoding="utf-8", mode="a")
        file_handler.setLevel(level)
        file_handler.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s", "%Y-%m-%d %H:%M:%S")
        )
        root_logger.addHandler(file_handler)
    except Exception as e:
        print(f"Failed to initialize file logger: {e}", file=sys.stderr)


def get_logger(name: str) -> logging.Logger:
    """Get a child logger under BulkMP3Studio."""
    setup_logging()
    return logging.getLogger(f"BulkMP3Studio.{name}")


def add_log_listener(callback: Callable[[str], None]) -> None:
    """Register a callback that receives every formatted log message."""
    if callback not in _log_listeners:
        _log_listeners.append(callback)


def remove_log_listener(callback: Callable[[str], None]) -> None:
    """Unregister a log listener callback."""
    if callback in _log_listeners:
        _log_listeners.remove(callback)


def get_recent_logs() -> List[str]:
    """Retrieve recent in-memory log lines."""
    return list(_log_history)


def clear_recent_logs() -> None:
    """Clear the in-memory log buffer."""
    _log_history.clear()
