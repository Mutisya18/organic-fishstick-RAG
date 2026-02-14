## Directory Structure (Unified Portal)

```
organic-fishstick-RAG/
├── app.py                           # Existing Streamlit UI (unchanged)
├── portal_api.py                    # NEW: FastAPI server (serves UI + API)
├── portal/                          # NEW: Web UI folder
│   ├── index.html                   # Main UI (your design)
│   ├── static/
│   │   ├── css/
│   │   │   ├── main.css             # Extracted from inline styles
│   │   │   └── themes.css           # Dark mode variables
│   │   ├── js/
│   │   │   ├── app.js               # Main application logic
│   │   │   ├── api.js               # WebSocket + API client
│   │   │   └── state.js             # Single conversation state
│   │   └── assets/
│   │       └── logo.svg
│   └── README.md
│
├── rag/                             # Existing (unchanged)
├── eligibility/                     # Existing (unchanged)
├── database/                        # Existing (unchanged)
├── utils/                           # Existing (unchanged)
│
├── start.sh                         # Existing: Streamlit UI
├── start_portal.sh                  # NEW: Portal UI (FastAPI)
├── start_dev.sh                     # NEW: Both UIs (dev mode)
│
├── requirements.txt                 # Add: fastapi, uvicorn, websockets
├── .env
└── README.md
```

---

## Switching Between UIs

### Current Setup (Streamlit)
```bash
bash start.sh
# → Opens http://localhost:8501 (Streamlit)
```

### New Setup (Portal)
```bash
bash start_portal.sh
# → Opens http://localhost:8000 (FastAPI Portal)
```

### Dev Mode (Both Running)
```bash
bash start_dev.sh
# → Streamlit: http://localhost:8501
# → Portal:    http://localhost:8000
```

**Zero changes to existing code** - both UIs call the same backend functions.

---

## Architecture Diagram

```
┌────────────────────────────────────────────────────────────────┐
│                         CLIENT BROWSER                         │
│                                                                │
│  http://localhost:8501  →  app.py (Streamlit UI)             │
│  http://localhost:8000  →  portal_api.py (New Portal UI)     │
│                                                                │
└────────────────────────────────────────────────────────────────┘
                          │
          ┌───────────────┴───────────────┐
          │                               │
          ▼                               ▼
┌─────────────────────┐      ┌─────────────────────────────┐
│   app.py            │      │   portal_api.py             │
│   (Streamlit)       │      │   (FastAPI)                 │
│                     │      │                             │
│   Port: 8501        │      │   Port: 8000                │
│   UI: Streamlit     │      │   UI: Static HTML           │
│                     │      │   API: REST + WebSocket     │
└──────────┬──────────┘      └──────────┬──────────────────┘
           │                            │
           │  Both call same functions  │
           │                            │
           └────────────┬───────────────┘
                        │
                        ▼
        ┌───────────────────────────────────────┐
        │   Shared Backend Logic                │
        │                                       │
        │   rag/query_data.py                  │
        │   eligibility/orchestrator.py        │
        │   database/__init__.py               │
        │   utils/context/context_builder.py   │
        │   utils/logger/                      │
        └───────────────┬───────────────────────┘
                        │
                        ▼
        ┌───────────────────────────────────────┐
        │   Data Layer                          │
        │                                       │
        │   PostgreSQL/SQLite  │  ChromaDB     │
        │   Log Files (JSON)                    │
        └───────────────────────────────────────┘
```

---

## Single Conversation Architecture

Since you want **one conversation only** for now:

### Flow:
1. User opens portal
2. Frontend calls `GET /api/init` → gets or creates conversation
3. All messages go to this conversation ID
4. Sidebar shows only this conversation (static)
5. "New Chat" button does nothing (or hidden)

### Database:
```python
# In portal_api.py
def get_or_create_conversation(user_id: str = "default_user"):
    """Get existing conversation or create new one."""
    conversations = db.list_conversations(user_id, limit=1)
    if conversations:
        return conversations[0]
    else:
        return db.create_conversation(user_id, title="Operations Assistant Chat")
```

---

## API Endpoints (portal_api.py)

```
GET  /                              → Serve index.html
GET  /static/*                      → Serve CSS/JS/assets

POST /api/init                      → Get/create conversation, return conv_id + user info
POST /api/chat/send                 → Send message (HTTP fallback)
WS   /ws/chat/{conversation_id}     → WebSocket for real-time chat

GET  /api/messages                  → Get all messages (single conversation)
POST /api/eligibility/check         → Check eligibility (account number)
```

### WebSocket Protocol:
```javascript
// Client → Server
{
  "type": "user_message",
  "content": "What is the loan eligibility?",
  "conversation_id": "abc-123"
}

// Server → Client (streaming response)
{
  "type": "assistant_message_start",
  "message_id": "msg-456"
}
{
  "type": "assistant_message_chunk",
  "content": "Based on the policy..."
}
{
  "type": "assistant_message_complete",
  "message_id": "msg-456",
  "metadata": {...}
}
```

---

## Key Implementation Details

### 1. **portal_api.py** (FastAPI Server)
```python
from fastapi import FastAPI, WebSocket
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse

app = FastAPI()

# Serve static files
app.mount("/static", StaticFiles(directory="portal/static"), name="static")

# Serve index.html
@app.get("/")
async def root():
    with open("portal/index.html") as f:
        return HTMLResponse(content=f.read())

# API endpoints
@app.post("/api/init")
async def initialize():
    # Get or create single conversation
    conv = get_or_create_conversation()
    return {
        "conversation_id": conv["id"],
        "user": {"name": "Stanley Mutisya", "role": "Relationship Manager"}
    }

@app.websocket("/ws/chat/{conversation_id}")
async def websocket_chat(websocket: WebSocket, conversation_id: str):
    await websocket.accept()
    # Handle WebSocket messages
    # Call query_rag() and stream response
```

### 2. **portal/static/js/api.js** (Frontend WebSocket Client)
```javascript
class ChatAPI {
  constructor() {
    this.ws = null;
    this.conversationId = null;
  }

  async init() {
    // Get conversation ID
    const res = await fetch('/api/init', { method: 'POST' });
    const data = await res.json();
    this.conversationId = data.conversation_id;
    return data;
  }

  connect() {
    this.ws = new WebSocket(`ws://localhost:8000/ws/chat/${this.conversationId}`);
    this.ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      this.handleMessage(data);
    };
  }

  sendMessage(content) {
    this.ws.send(JSON.stringify({
      type: 'user_message',
      content: content,
      conversation_id: this.conversationId
    }));
  }

  handleMessage(data) {
    // Handle different message types
    // Update UI accordingly
  }
}
```

### 3. **start_portal.sh** (Launch Script)
```bash
#!/bin/bash
source venv/bin/activate
export $(cat .env | grep -v '^#' | xargs)
uvicorn portal_api:app --host 0.0.0.0 --port 8000 --reload
```

### 4. **start_dev.sh** (Both UIs)
```bash
#!/bin/bash
# Start both Streamlit and Portal in background
bash start.sh &
bash start_portal.sh &
wait
```

---

## Modified Files (Minimal Changes)

### ✅ No changes needed:
- `app.py` (Streamlit)
- `rag/query_data.py`
- `eligibility/orchestrator.py`
- `database/__init__.py`
- All other backend code

### ➕ New files only:
- `portal_api.py` (wraps existing functions)
- `portal/index.html`
- `portal/static/css/main.css`
- `portal/static/js/app.js`
- `portal/static/js/api.js`
- `start_portal.sh`

---

## Single Conversation Sidebar (Simplified)

Your HTML sidebar will show:
```html
<div class="conversations-list">
  <div class="conversation-item active">
    <div class="conversation-header">
      <svg>...</svg>
      <div>
        <div class="conversation-title">Operations Assistant Chat</div>
        <div class="conversation-time">Active Session</div>
      </div>
    </div>
  </div>
</div>
```

No other conversations listed. "New Chat" button hidden or disabled.

---

## Requirements to Add

Update `requirements.txt`:
```txt
# Existing packages...

# Portal dependencies
fastapi==0.109.0
uvicorn[standard]==0.27.0
websockets==12.0
python-multipart==0.0.9
```

---

## Next Steps

Ready to generate:
1. ✅ `portal_api.py` - Complete FastAPI server with WebSocket
2. ✅ `portal/index.html` - Your design with API integration
3. ✅ `portal/static/js/api.js` - WebSocket client
4. ✅ `portal/static/js/app.js` - Main application logic
5. ✅ `portal/static/css/main.css` - Extracted styles
6. ✅ `start_portal.sh` - Launch script
7. ✅ `start_dev.sh` - Both UIs script
