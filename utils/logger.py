"""
utils/logger.py - Structured Logging System
Every request is logged for bank audit compliance.

Format:
  [LEVEL]  YYYY-MM-DD HH:MM:SS | session=<id> | score=<n> | result=<PASS/FAIL> | time=<s>s
"""

import logging
import logging.handlers
import os
import sys
from datetime import datetime

import config


# ──────────────────────────────────────────────
# Ensure logs directory exists
# ──────────────────────────────────────────────
os.makedirs(config.LOG_DIR, exist_ok=True)


# ──────────────────────────────────────────────
# Custom formatter  →  one-line audit record
# ──────────────────────────────────────────────
class AuditFormatter(logging.Formatter):
    """Emit a structured, pipe-delimited log line."""

    FMT = "[%(levelname)s] %(asctime)s | %(message)s"
    DATE_FMT = "%Y-%m-%d %H:%M:%S"

    def format(self, record: logging.LogRecord) -> str:  # noqa: D102
        self.datefmt = self.DATE_FMT
        self._style._fmt = self.FMT
        return super().format(record)


def _build_logger(name: str = "liveness") -> logging.Logger:
    """Create and configure the application logger (singleton-safe)."""
    logger = logging.getLogger(name)

    # Prevent duplicate handlers on hot-reload
    if logger.handlers:
        return logger

    level = getattr(logging, config.LOG_LEVEL.upper(), logging.INFO)
    logger.setLevel(level)

    formatter = AuditFormatter()

    # ── Rotating File Handler ──────────────────
    file_handler = logging.handlers.RotatingFileHandler(
        config.LOG_FILE,
        maxBytes=config.LOG_MAX_BYTES,
        backupCount=config.LOG_BACKUP_COUNT,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(level)

    # ── Console (stdout) Handler ───────────────
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(level)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


# ──────────────────────────────────────────────
# Module-level singleton
# ──────────────────────────────────────────────
app_logger = _build_logger()


# ──────────────────────────────────────────────
# Convenience helpers
# ──────────────────────────────────────────────
def log_request(
    session_id: str,
    input_type: str,
    score: float,
    result: str,
    elapsed: float,
    error: str | None = None,
) -> None:
    """Log a completed liveness request (audit record)."""
    parts = [
        f"session={session_id}",
        f"input={input_type}",
        f"score={score:.1f}",
        f"result={result}",
        f"time={elapsed:.3f}s",
    ]
    if error:
        parts.append(f"error={error}")

    msg = " | ".join(parts)
    if result == "PASS":
        app_logger.info(msg)
    else:
        app_logger.warning(msg)


def log_error(session_id: str, error: str, exc: Exception | None = None) -> None:
    """Log a processing error."""
    msg = f"session={session_id} | error={error}"
    if exc:
        app_logger.exception(msg)
    else:
        app_logger.error(msg)


def log_debug(session_id: str, message: str) -> None:
    """Log a debug-level message (only emitted when DEBUG_MODE=true)."""
    if config.DEBUG_MODE:
        app_logger.debug(f"session={session_id} | {message}")
