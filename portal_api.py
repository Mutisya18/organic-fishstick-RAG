"""
Portal API – FastAPI server for the new Portal UI.

Serves static portal (HTML/CSS/JS) and REST API. Uses same backend as Streamlit
(database, RAG, eligibility) via backend.chat.run_chat. No changes to app.py
beyond the shared backend facade.
"""

import traceback
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from database import db as database_manager
from backend.chat import run_chat
from rag.config.prompts import DEFAULT_PROMPT_VERSION

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
