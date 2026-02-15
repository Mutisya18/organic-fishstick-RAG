"""
Conversation limit configuration.

Reads MAX_ACTIVE_CONVERSATIONS, CONVERSATION_WARNING_THRESHOLD, and
ENABLE_CONVERSATION_LIMIT from environment. Used by portal API and
conversation service for visibility and auto-hide behavior.
"""

import os
import logging

logger = logging.getLogger(__name__)

# Defaults per spec
_DEFAULT_MAX = 20
_DEFAULT_WARNING = 15
_DEFAULT_ENABLED = True

MAX_ACTIVE_CONVERSATIONS = int(
    os.getenv("MAX_ACTIVE_CONVERSATIONS", str(_DEFAULT_MAX))
)
CONVERSATION_WARNING_THRESHOLD = int(
    os.getenv("CONVERSATION_WARNING_THRESHOLD", str(_DEFAULT_WARNING))
)
ENABLE_LIMIT = os.getenv("ENABLE_CONVERSATION_LIMIT", "true").lower() == "true"


def get_config():
    """
    Return conversation limit config for API (frontend source of truth).

    Returns:
        dict: maxConversations, warningThreshold, enabled
    """
    assert MAX_ACTIVE_CONVERSATIONS >= 1, "MAX_ACTIVE_CONVERSATIONS must be >= 1"
    assert (
        CONVERSATION_WARNING_THRESHOLD <= MAX_ACTIVE_CONVERSATIONS
    ), "WARNING_THRESHOLD must be <= MAX_ACTIVE_CONVERSATIONS"

    return {
        "maxConversations": MAX_ACTIVE_CONVERSATIONS,
        "warningThreshold": CONVERSATION_WARNING_THRESHOLD,
        "enabled": ENABLE_LIMIT,
    }
