"""
RAG Context Builder

Builds conversation context from all messages to enrich LLM queries.
Retrieves ALL messages from current conversation and formats them for injection into prompts.
This ensures the LLM has full conversation context for better coherence and understanding.
"""

from typing import Dict, Any, Optional
from sqlalchemy import desc

from database.models import Message
from database.core.session import get_session
from rag.config.prompts import SYSTEM_PROMPTS, DEFAULT_PROMPT_VERSION


def build_rag_context(
    conversation_id: str,
    user_message: str,
    db_manager: Any,
    prompt_version: str = DEFAULT_PROMPT_VERSION
) -> Dict[str, str]:
    """
    Build enriched context for RAG queries by including conversation history.
    
    Retrieves the last 5 messages from the conversation and formats them
    along with the system prompt for injection into the LLM request.
    
    Args:
        conversation_id: UUID of the current conversation
        user_message: Current user message
        db_manager: DatabaseManager instance (used only for type consistency)
        prompt_version: System prompt version to use
    
    Returns:
        Dictionary containing:
        - 'system_prompt': The system prompt text
        - 'context': Formatted recent conversation history (role:content pairs)
        - 'user_message': The current user message
    
    Example:
        >>> context = build_rag_context(
        ...     conversation_id="abc-123",
        ...     user_message="Tell me more",
        ...     db_manager=db
        ... )
        >>> context['context']
        'user: What is RAG?\nassistant: RAG is...\nuser: More details?\nassistant: Sure, here...'
    """
    
    # Get system prompt
    system_prompt = SYSTEM_PROMPTS.get(
        prompt_version,
        SYSTEM_PROMPTS[DEFAULT_PROMPT_VERSION]
    )
    
    import os
    # Get configurable message limit from .env, default to 5
    try:
        message_limit = int(os.getenv("CONTEXT_MESSAGE_LIMIT", "5"))
    except Exception:
        message_limit = 5

    context_text = ""
    try:
        with get_session() as session:
            messages = (
                session.query(Message)
                .filter(Message.conversation_id == conversation_id)
                .order_by(desc(Message.created_at))
                .limit(message_limit)
                .all()
            )
            messages.reverse()
            context_lines = []
            for msg in messages:
                role = msg.role.value if hasattr(msg.role, 'value') else str(msg.role)
                context_lines.append(f"{role}: {msg.content}")
            context_text = "\n".join(context_lines)
    except Exception as e:
        print(f"[WARNING] Failed to retrieve conversation context: {str(e)}")
        context_text = ""
    return {
        "system_prompt": system_prompt,
        "context": context_text,
        "user_message": user_message,
    }
