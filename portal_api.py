"""
Portal API – FastAPI server for the new Portal UI.

Serves static portal (HTML/CSS/JS) and REST API. Uses same backend as Streamlit
(database, RAG, eligibility) via backend.chat.run_chat. No changes to app.py
beyond the shared backend facade.
"""

import traceback
import logging
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from database import db as database_manager
from database.services.conversation_service import (
    get_visible_conversations,
    count_visible_conversations,
    apply_auto_hide_if_needed,
)
from database.repository.conversation_repository import ConversationRepository
from backend.chat import run_chat, validate_message
from rag.config.prompts import DEFAULT_PROMPT_VERSION
from rag.config.conversation_limits import (
    get_config as get_conversation_config,
    ENABLE_LIMIT,
    CONVERSATION_WARNING_THRESHOLD,
    MAX_ACTIVE_CONVERSATIONS,
)

logger = logging.getLogger(__name__)

# Base directory for portal assets (parent of portal_api.py)
BASE_DIR = Path(__file__).resolve().parent
PORTAL_DIR = BASE_DIR / "portal"
PORTAL_STATIC = PORTAL_DIR / "static"

app = FastAPI(title="NCBA Operations Assistant Portal")

# Mount static files at /static (CSS, JS, assets)
if PORTAL_STATIC.exists():
    app.mount("/static", StaticFiles(directory=str(PORTAL_STATIC)), name="static")

# Default user for portal (can be overridden by /api/init later)
DEFAULT_USER = {"name": "Stanley Mutisya", "role": "Relationship Manager"}


@app.on_event("startup")
def startup():
    """Initialize database on startup (same pattern as app.py)."""
    try:
        database_manager.initialize(debug=False)
    except Exception as e:
        # Log but allow portal to run; API will fail on first DB use
        print(f"[portal_api] Database init warning: {e}")
        traceback.print_exc()


def get_or_create_conversation(user_id: str = "default_user"):
    """Get existing conversation or create one. Single conversation per user."""
    convs = database_manager.list_conversations(
        user_id, limit=1, include_archived=False
    )
    if convs:
        return convs[0]
    return database_manager.create_conversation(
        user_id, title="Operations Assistant Chat"
    )


@app.get("/", response_class=FileResponse)
async def root():
    """Serve the portal single-page app."""
    index_path = PORTAL_DIR / "index.html"
    if not index_path.exists():
        raise HTTPException(status_code=500, detail="Portal index.html not found")
    return FileResponse(index_path, media_type="text/html")


@app.get("/api/v2/config/limits")
async def api_config_limits():
    """Get conversation limit configuration."""
    try:
        config = get_conversation_config()
        return config
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Config fetch failed: {str(e)}")


@app.post("/api/init")
async def api_init():
    """Get or create single conversation; return conversation_id and user."""
    try:
        conv = get_or_create_conversation()
        return {
            "conversation_id": conv["id"],
            "user": DEFAULT_USER,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Init failed: {str(e)}")


class ValidateBody(BaseModel):
    content: str = ""


@app.post("/api/chat/validate")
async def api_chat_validate(body: ValidateBody):
    """Validate message before send (e.g. command args). Returns valid + message for placeholder."""
    text = (body.content or "").strip()
    valid, error_message = validate_message(text)
    return {"valid": valid, "message": error_message if not valid else None}


@app.get("/api/messages")
async def api_messages(conversation_id: str = ""):
    """Get messages for a conversation."""
    if not conversation_id:
        return []
    try:
        if not database_manager.get_conversation(conversation_id):
            raise HTTPException(status_code=404, detail="Conversation not found")
        messages = database_manager.get_messages(
            conversation_id, limit=100, offset=0
        )
        return [
            {
                "id": m.get("id"),
                "role": m.get("role"),
                "content": m.get("content", ""),
                "created_at": m.get("created_at"),
                "metadata": m.get("msg_metadata") or {},
            }
            for m in messages
        ]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class ChatSendBody(BaseModel):
    content: str
    conversation_id: str = "default"


# ============================================================================
# V2 API: Multi-Conversation Management
# ============================================================================

class CreateConversationRequest(BaseModel):
    """Request to create a new conversation."""
    title: Optional[str] = None
    user_id: str = "default_user"
    active_conversation_id: Optional[str] = None


class ConversationDetail(BaseModel):
    """Conversation list item."""
    id: str
    title: Optional[str]
    last_message_at: Optional[str]
    last_opened_at: Optional[str]
    message_count: int
    preview: Optional[str] = None
    status: str
    is_hidden: bool
    created_at: str
    updated_at: str


class ConversationListResponse(BaseModel):
    """Response for conversation list."""
    conversations: list
    visible_count: int
    max_allowed: int
    warning: bool = False


class CreateConversationResponse(BaseModel):
    """Response for conversation creation."""
    conversation: dict
    visible_count: int
    max_allowed: int
    warning: bool = False
    auto_hidden: Optional[dict] = None


@app.get("/api/v2/conversations")
async def api_v2_conversations_list(user_id: str = "default_user"):
    """
    Get visible conversations for a user, sorted by relevance.
    
    Query Parameters:
    - user_id: User ID (default: "default_user")
    
    Response:
    - conversations: List of conversation objects
    - visible_count: Number of visible conversations
    - max_allowed: Maximum allowed conversations
    - warning: If true, user is at warning threshold
    
    Returns 200 with conversation list.
    """
    assert user_id, "user_id required"
    
    try:
        # Get visible conversations
        conversations = get_visible_conversations(user_id, limit=MAX_ACTIVE_CONVERSATIONS)
        
        # Convert to dicts
        conv_dicts = [c.to_dict() for c in conversations]
        
        # Count visible
        visible_count = count_visible_conversations(user_id)

        # Warning only when limit feature is enabled
        warning = (
            ENABLE_LIMIT
            and visible_count >= CONVERSATION_WARNING_THRESHOLD
        )
        
        logger.info(f"Listed {visible_count} conversations for user_id={user_id}")
        
        return {
            "conversations": conv_dicts,
            "visible_count": visible_count,
            "max_allowed": MAX_ACTIVE_CONVERSATIONS,
            "warning": warning
        }
    
    except Exception as e:
        logger.error(f"Error listing conversations: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v2/conversations")
async def api_v2_conversations_create(body: CreateConversationRequest):
    """
    Create a new conversation.
    
    If creating this conversation exceeds the limit, the lowest-scoring 
    conversation is automatically hidden.
    
    Request:
    - title: Optional conversation title
    - user_id: User ID (default: "default_user")
    
    Response:
    - conversation: Created conversation object
    - visible_count: Number of visible conversations after creation
    - max_allowed: Maximum allowed conversations
    - warning: If true, user has reached warning threshold
    - auto_hidden: If hiding occurred, metadata about hidden conversation
    
    Returns 201 if successful.
    """
    user_id = body.user_id or "default_user"
    assert user_id, "user_id required"
    
    try:
        # Create conversation via database manager
        title = body.title or "New Conversation"
        new_conv = database_manager.create_conversation(
            user_id=user_id,
            title=title
        )
        
        # Apply auto-hiding if needed (exclude conversation user was viewing)
        auto_hide_metadata = apply_auto_hide_if_needed(
            user_id=user_id,
            active_conversation_id=body.active_conversation_id,
        )

        visible_count_after = count_visible_conversations(user_id)
        warning = (
            ENABLE_LIMIT
            and visible_count_after >= CONVERSATION_WARNING_THRESHOLD
        )

        logger.info(
            "Created conversation %s for user_id=%s (visible_count=%s)",
            new_conv.get("id"),
            user_id,
            visible_count_after,
        )
        
        response = {
            "conversation": new_conv,
            "visible_count": visible_count_after,
            "max_allowed": MAX_ACTIVE_CONVERSATIONS,
            "warning": warning
        }
        
        if auto_hide_metadata:
            response["auto_hidden"] = auto_hide_metadata
        
        return response
    
    except Exception as e:
        logger.error(f"Error creating conversation: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.patch("/api/v2/conversations/{conversation_id}/open")
async def api_v2_conversations_open(conversation_id: str):
    """
    Mark a conversation as opened (update last_opened_at).
    
    Called when user switches to a conversation in the UI.
    Updates the viewing activity timestamp for relevance calculation.
    
    Path Parameters:
    - conversation_id: Conversation ID
    
    Response:
    - id: Conversation ID
    - last_opened_at: Updated timestamp
    
    Returns 200 if successful, 404 if conversation not found.
    """
    assert conversation_id, "conversation_id required"
    
    try:
        repo = ConversationRepository()
        updated_conv = repo.mark_opened(conversation_id)
        
        logger.debug(f"Marked conversation {conversation_id} as opened")
        
        return {
            "id": updated_conv.get("id"),
            "last_opened_at": updated_conv.get("last_opened_at")
        }
    
    except Exception as e:
        logger.error(f"Error marking conversation as opened: {str(e)}")
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail="Conversation not found")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/chat/send")
async def api_chat_send(body: ChatSendBody):
    """Send a message; run RAG/eligibility via run_chat; save messages; return response."""
    content = (body.content or "").strip()
    if not content:
        raise HTTPException(status_code=400, detail="content is required")
    conversation_id = body.conversation_id or "default"

    try:
        conv = database_manager.get_conversation(conversation_id)
        if not conv:
            raise HTTPException(status_code=404, detail="Conversation not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    result = run_chat(
        content,
        conversation_id,
        database_manager,
        prompt_version=DEFAULT_PROMPT_VERSION,
    )

    request_id = result.get("request_id") or "unknown"
    response_text = result.get("response") or ""
    if not result.get("success") and result.get("error"):
        response_text = result.get("error") or "An error occurred."

    try:
        database_manager.save_user_message(
            conversation_id=conversation_id,
            content=content,
            request_id=request_id,
        )
        database_manager.save_assistant_message(
            conversation_id=conversation_id,
            content=response_text,
            request_id=request_id,
            metadata={
                "latency_ms": result.get("latency_ms"),
                "source": "eligibility" if result.get("is_eligibility_flow") else "rag",
            },
        )
    except Exception as e:
        # Log but still return result to user
        print(f"[portal_api] Save message error: {e}")
        traceback.print_exc()

    return {
        "request_id": request_id,
        "success": result.get("success", False),
        "response": response_text,
        "sources": result.get("sources") or [],
        "is_eligibility_flow": result.get("is_eligibility_flow", False),
        "eligibility_payload": result.get("eligibility_payload"),
        "error": result.get("error"),
    }
