"""
Audit logging stub for conversation and compliance events.

Logs structured JSON for later integration with a real audit backend.
Per logging_rules: JSON format, ISO 8601 timestamps, traceability.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict

logger = logging.getLogger(__name__)


def log_audit_event(payload: Dict[str, Any]) -> None:
    """
    Record an audit event (stub: logs as JSON only).

    Call with the full event payload; no PII in payload for auto-hide events.
    Replace this implementation to write to a real audit store.

    Args:
        payload: Event dict (e.g. event, timestamp, user_id, conversation_id, reason)
    """
    assert payload is not None, "payload must not be None"
    assert isinstance(payload, dict), "payload must be a dict"

    if "timestamp" not in payload:
        payload = {
            **payload,
            "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        }

    log_entry = {
        "audit": True,
        "event": payload.get("event", "unknown"),
        "payload": payload,
    }
    logger.info(json.dumps(log_entry))
