"""
Structured logging for auth module.

Follows logging_rules.md: JSON, timestamp (ISO 8601), level, service, trace_id, event, message, context.
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from utils.logger.session_manager import SessionManager

_SERVICE = "auth"
_MAX_CONTEXT_KEYS = 20


def _ensure_trace_id(trace_id: Optional[str]) -> str:
    if trace_id and isinstance(trace_id, str) and len(trace_id) > 0:
        return trace_id
    return str(uuid.uuid4())


def log_auth_event(
    event: str,
    level: str = "INFO",
    message: str = "",
    trace_id: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Emit a structured auth log entry. No PII (passwords, tokens) in message or context.
    """
    assert event, "event required"
    assert level in ("DEBUG", "INFO", "WARN", "WARNING", "ERROR"), "invalid level"
    trace = _ensure_trace_id(trace_id)
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="milliseconds") + "Z",
        "level": level,
        "service": _SERVICE,
        "trace_id": trace,
        "event": event,
        "message": message[:500] if message else "",
    }
    if context and isinstance(context, dict):
        keys = list(context.keys())[:_MAX_CONTEXT_KEYS]
        safe_context = {}
        for k in keys:
            v = context[k]
            if k.lower() in ("password", "password_hash", "token", "session_id"):
                safe_context[k] = "[REDACTED]"
            else:
                safe_context[k] = v
        entry["context"] = safe_context
    sm = SessionManager()
    sm.log(entry, severity=level if level != "WARN" else "WARNING")
