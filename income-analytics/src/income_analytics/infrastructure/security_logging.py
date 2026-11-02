"""Redact credential-bearing diagnostics before any logging handler sees them."""

import logging
import re
import traceback
from typing import Any

_PATTERNS = (
    re.compile(r"(?i)(bearer\s+)[a-z0-9._~+/=-]+"),
    re.compile(r"(?i)((?:token|api[_-]?key|password|secret)[\"']?\s*[=:]\s*[\"']?)[^\s&\"'<>]+"),
    re.compile(r"(?i)(https?://)[^\s/:@]+:[^\s/@]+@"),
    re.compile(r"(?i)()[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}"),
)


def redact(message: str) -> str:
    for pattern in _PATTERNS:
        message = pattern.sub(lambda match: match.group(1) + "[REDACTED]", message)
    return message


def install_log_redaction() -> None:
    previous = logging.getLogRecordFactory()
    if getattr(previous, "_income_redaction", False):
        return

    def factory(*args: Any, **kwargs: Any) -> logging.LogRecord:
        record = previous(*args, **kwargs)
        record.msg = redact(record.getMessage())
        record.args = ()
        if record.exc_info:
            record.exc_text = redact("".join(traceback.format_exception(*record.exc_info)))
            record.exc_info = None
        return record

    setattr(factory, "_income_redaction", True)
    logging.setLogRecordFactory(factory)
