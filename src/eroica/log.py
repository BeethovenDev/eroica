"""Logging helpers.

EROICA logs to ``stderr`` so that machine-readable output on ``stdout``
(``--json``) stays clean and pipeable.
"""

from __future__ import annotations

import json
import logging
import sys
from typing import Any

_LOGGER_NAME = "eroica"
_CONFIGURED = False

_RESET = "\x1b[0m"
_DIM = "\x1b[2m"
_LEVEL_COLOURS = {
    logging.DEBUG: "\x1b[36m",  # cyan
    logging.INFO: "\x1b[32m",  # green
    logging.WARNING: "\x1b[33m",  # yellow
    logging.ERROR: "\x1b[31m",  # red
    logging.CRITICAL: "\x1b[41m",  # red background
}


class _TextFormatter(logging.Formatter):
    """Compact, optionally coloured text formatter."""

    def __init__(self, *, colour: bool) -> None:
        super().__init__("%(levelname)s %(message)s")
        self._colour = colour

    def format(self, record: logging.LogRecord) -> str:
        message = super().format(record)
        if not self._colour:
            return message
        colour = _LEVEL_COLOURS.get(record.levelno, "")
        return f"{colour}{message}{_RESET}" if colour else message


class _JsonFormatter(logging.Formatter):
    """One JSON object per line — friendly to log shippers."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "level": record.levelname.lower(),
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def configure(*, verbosity: int = 0, json_logs: bool = False, stream: Any | None = None) -> None:
    """Configure the ``eroica`` logger.

    Args:
        verbosity: ``0`` → INFO, ``1`` → DEBUG.
        json_logs: Emit structured JSON lines instead of text.
        stream: Destination stream; defaults to ``sys.stderr``.
    """
    global _CONFIGURED

    logger = logging.getLogger(_LOGGER_NAME)
    logger.handlers.clear()
    handler = logging.StreamHandler(stream if stream is not None else sys.stderr)
    if json_logs:
        handler.setFormatter(_JsonFormatter())
    else:
        colour = stream is None and sys.stderr.isatty()
        handler.setFormatter(_TextFormatter(colour=colour))
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG if verbosity > 0 else logging.INFO)
    logger.propagate = False
    _CONFIGURED = True


def get_logger(name: str | None = None) -> logging.Logger:
    """Return a namespaced child of the ``eroica`` logger.

    Auto-configures on first use so library consumers get sane defaults.
    """
    if not _CONFIGURED:
        configure()
    suffix = f".{name}" if name else ""
    return logging.getLogger(f"{_LOGGER_NAME}{suffix}")


__all__ = ["configure", "get_logger"]
