"""
Conversation visibility and auto-hide service.

Uses conversation_limits config and conversation repository to:
- Return visible conversations ordered by relevance
- Apply auto-hide when over limit, excluding the currently active conversation
"""

import logging
from typing import List, Optional, Dict, Any

from database.models import Conversation
from database.repository.conversation_repository import ConversationRepository
from database.services.audit_logger import log_audit_event
from rag.config.conversation_limits import (
    ENABLE_LIMIT,
    MAX_ACTIVE_CONVERSATIONS,
)

logger = logging.getLogger(__name__)

# Max iterations when selecting candidate to hide (safety bound per NASA-style rules)
_MAX_HIDE_CANDIDATES = 1000


def count_visible_conversations(user_id: str) -> int:
    """
    Count non-hidden conversations for a user.

    Args:
        user_id: User ID

    Returns:
        Count of visible (is_hidden=False, status=ACTIVE) conversations
    """
    assert user_id, "user_id required"
    repo = ConversationRepository()
    return repo.count_visible_for_user(user_id)


def get_visible_conversations(
    user_id: str,
    limit: int = 20,
) -> List[Conversation]:
    """
    Get visible (non-hidden) conversations for a user, sorted by relevance.

    Args:
        user_id: User ID
        limit: Max to return (default from config)

    Returns:
        List of Conversation instances, highest relevance first
    """
    assert user_id, "user_id required"
    bound = min(limit, MAX_ACTIVE_CONVERSATIONS) if ENABLE_LIMIT else limit
    if bound < 1:
        bound = 20

    repo = ConversationRepository()
    return repo.get_visible_by_relevance(user_id=user_id, limit=bound)


def apply_auto_hide_if_needed(
    user_id: str,
    active_conversation_id: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """
    If visible count exceeds limit, hide the lowest-scoring conversation.

    Excludes active_conversation_id from hide candidates. On hide failure,
    logs and returns without blocking (conversation creation already succeeded).

    Args:
        user_id: User ID
        active_conversation_id: Conversation to protect (user was viewing it)

    Returns:
        None if no hide occurred; else
        { "occurred": True, "conversation_id": "<uuid>", "reason": "limit_exceeded" }
    """
    assert user_id, "user_id required"

    if not ENABLE_LIMIT:
        return None

    repo = ConversationRepository()
    visible_count = repo.count_visible_for_user(user_id)
    if visible_count <= MAX_ACTIVE_CONVERSATIONS:
        return None

    # Fetch visible, score, exclude active, hide lowest
    all_visible = repo.get_visible_by_relevance(
        user_id=user_id,
        limit=_MAX_HIDE_CANDIDATES,
    )
    if not all_visible:
        return None

    # Build list of hide candidates (exclude active)
    candidates = []
    for conv in all_visible:
        if conv.id == active_conversation_id:
            continue
        candidates.append((conv.get_relevance_score(), conv))

    if not candidates:
        logger.warning(
            "Auto-hide: only conversation is active; cannot hide. user_id=%s",
            user_id,
        )
        return None

    # Sort by score ascending; lowest first
    candidates.sort(key=lambda pair: pair[0])
    _, to_hide = candidates[0]
    hide_id = to_hide.id
    score = to_hide.get_relevance_score()

    try:
        repo.hide(hide_id)
    except Exception as e:
        logger.error(
            "Auto-hide failed for user_id=%s, conversation_id=%s: %s",
            user_id,
            hide_id,
            str(e),
        )
        return None

    # Audit stub
    log_audit_event(
        {
            "event": "conversation_auto_hidden",
            "user_id": user_id,
            "conversation_id": hide_id,
            "reason": "limit_exceeded",
            "relevance_score": score,
            "visible_count_before": visible_count,
            "visible_count_after": visible_count - 1,
            "trigger": "conversation_created",
        }
    )

    return {
        "occurred": True,
        "conversation_id": hide_id,
        "reason": "limit_exceeded",
    }
