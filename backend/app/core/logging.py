import contextvars
import json
import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, Optional

# Context variable for tracing request IDs across async calls
request_id_ctx: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("request_id", default=None)
job_id_ctx: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("job_id", default=None)

# Sensitive patterns to redact from logs
TOKEN_REGEX = re.compile(r"(token=)[^&\s]+", re.IGNORECASE)
RAW_IP_REGEX = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")


def mask_sensitive_info(message: str) -> str:
    """Masks authentication tokens and raw IP addresses from log messages."""
    if not isinstance(message, str):
        return message
    msg = TOKEN_REGEX.sub(r"\1[REDACTED_TOKEN]", message)
    # Mask raw IPs that are not loopback
    def _mask_ip(m):
        ip = m.group(0)
        if ip.startswith("127.") or ip == "0.0.0.0":
            return ip
        parts = ip.split(".")
        return f"{parts[0]}.{parts[1]}.***.***"
    msg = RAW_IP_REGEX.sub(_mask_ip, msg)
    return msg


class StructuredJSONFormatter(logging.Formatter):
    """Formats log records as structured JSON lines."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": mask_sensitive_info(record.getMessage()),
        }

        # Add trace context if available
        req_id = request_id_ctx.get()
        if req_id:
            log_entry["request_id"] = req_id

        j_id = job_id_ctx.get()
        if j_id:
            log_entry["job_id"] = j_id

        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_entry)


def setup_structured_logging(debug: bool = False) -> None:
    """Initializes root logger with structured JSON formatting."""
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG if debug else logging.INFO)

    # Remove existing handlers to prevent duplicates
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)

    handler = logging.StreamHandler()
    handler.setFormatter(StructuredJSONFormatter())
    root_logger.addHandler(handler)
