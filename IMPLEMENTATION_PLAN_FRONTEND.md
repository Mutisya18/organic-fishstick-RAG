# New Frontend Implementation Plan

This document is the implementation plan for the **Portal UI** (new frontend) based on the demo in `ui-screen.html` and the spec in `frontend.md`. The goal is **seamless integration with the current system with minimal alterations** to existing code.

---

## 1. Summary

| Item | Source | Notes |
|------|--------|--------|
| **UI design** | `ui-screen.html` | Top nav (logo, profile + dark mode), sidebar (single conversation, tools), main chat (welcome + quick actions, messages, floating input). |
| **Architecture** | `frontend.md` | New FastAPI server (`portal_api.py`) serves static portal; same backend (RAG, eligibility, database) as Streamlit; no changes to `app.py` or core modules. |
| **Conversation model** | Spec | Single conversation per user: `GET /api/init` returns or creates one conversation; all chat uses that `conversation_id`. |

**Principle:** All new behavior lives in **new files only**. Existing backend is called from `portal_api.py` using the same imports and patterns as `app.py`.

---

## 2. Current System Touchpoints (No Code Changes)

The portal will use these **existing** APIs only. No edits to these files.

| Component | Location | Usage from portal_api.py |
|-----------|----------|---------------------------|
| Database | `database` (singleton `db`) | `initialize()`, `create_conversation()`, `list_conversations()`, `get_conversation()`, `get_messages()` / `get_last_n_messages()`, `save_user_message()`, `save_assistant_message()` |
| RAG context | `utils.context.context_builder.build_rag_context` | Same signature as app.py: `conversation_id`, `user_message`, `db_manager`, `prompt_version` |
| Query processing | `app.py`: `process_query()` | **Reuse by importing** `process_query` from `app` (or copy the minimal flow into portal_api to avoid importing Streamlit). Prefer **extracting** a small backend module (see §5) so portal does not depend on Streamlit. |
| RAG + sources | `rag.query_data`: `query_rag`, `extract_sources_from_query` | Used inside `process_query` (or equivalent in portal). |
| Eligibility / commands | `utils.commands`: `parse_command`, `dispatch_command`, `get_registry` | Used inside `process_query` (or equivalent). |
| Logging | `utils.logger.rag_logging.RAGLogger`, `SessionManager` | Optional: use in portal_api for request_id and logging. |

**Important:** `app.py` uses `process_query()` and `build_rag_context()` with `database_manager`. The cleanest approach with **minimal alteration** is:

- **Option A (recommended):** Add a thin **backend facade** (e.g. `backend/chat.py`) that contains only the call chain: build context → process_query. Both `app.py` and `portal_api.py` call this. Then the only change to the “current system” is one new module and one line in `app.py` to call the facade instead of inlining.
- **Option B:** Have `portal_api.py` import the same modules as `app.py` and replicate the small flow (create/get conversation, build_rag_context, process_query, save messages) without importing `app` (to avoid pulling in Streamlit). No changes to `app.py`, but some logic is duplicated.

The plan below assumes **Option B** (zero changes to `app.py`) for true minimal alteration; you can switch to Option A and add the facade in Phase 1 if you prefer a single place for the “process one user message” logic.

---

## 3. Directory Structure (Target)

```
organic-fishstick-RAG/
├── app.py                    # Unchanged (Streamlit)
├── portal_api.py             # NEW: FastAPI app (routes + WebSocket)
├── portal/
│   ├── index.html            # NEW: from ui-screen.html (structure + markup)
│   ├── static/
│   │   ├── css/
│   │   │   ├── main.css      # NEW: layout, components (from ui-screen.html)
│   │   │   └── themes.css   # NEW: :root and .dark-mode variables only
│   │   ├── js/
│   │   │   ├── app.js        # NEW: UI logic (profile, dark mode, input, send, welcome cards)
│   │   │   ├── api.js        # NEW: fetch /api/init, WebSocket, POST fallback
│   │   │   └── state.js      # NEW: conversationId, user, messages (single conversation)
│   │   └── assets/
│   │       └── (optional) logo.svg
│   └── README.md             # NEW: how to run portal
├── start.sh                  # Unchanged
├── start_portal.sh           # NEW: uvicorn portal_api:app --port 8000
├── start_dev.sh              # NEW: run both Streamlit and portal
├── requirements.txt          # Add: fastapi, uvicorn, websockets, python-multipart
├── rag/                      # Unchanged
├── eligibility/              # Unchanged
├── database/                 # Unchanged
├── utils/                    # Unchanged
└── IMPLEMENTATION_PLAN_FRONTEND.md  # This file
```

---

## 4. Phased Implementation

### Phase 1: Static portal and API shell (no backend wiring)

**Goal:** Serve the new UI and implement init + message loading so the frontend can show a single conversation and send a message (backend can return a placeholder response).

1. **Create directory structure**
   - `portal/`, `portal/static/css/`, `portal/static/js/`, `portal/static/assets/`.

2. **Extract UI from `ui-screen.html`**
   - **portal/index.html:** Use the same structure as `ui-screen.html`: top nav, sidebar, main content (chat header, messages container, welcome block, quick actions, input area). Remove inline CSS/JS; link `static/css/main.css`, `static/css/themes.css`, and `static/js/app.js`, `static/js/api.js`, `static/js/state.js`.
   - **portal/static/css/themes.css:** Copy `:root` and `body.dark-mode` variables from `ui-screen.html`.
   - **portal/static/css/main.css:** Copy all other styles (layout, nav, sidebar, messages, input, animations, responsive).

3. **FastAPI app (portal_api.py)**
   - Mount `StaticFiles` for `/static` → `portal/static`.
   - `GET /` → read `portal/index.html` and return `HTMLResponse`.
   - `POST /api/init`: For now return a fixed payload, e.g. `{ "conversation_id": "default", "user": { "name": "Stanley Mutisya", "role": "Relationship Manager" } }`.
   - Optional: `GET /api/messages?conversation_id=...` returning `[]` so the frontend can call it without errors.

4. **Frontend JS**
   - **state.js:** Export a simple state object: `conversationId`, `user`, `messages` (array). Provide getters/setters or a minimal subscription if needed.
   - **api.js:**  
     - `init()`: `POST /api/init`, store `conversation_id` and `user` in state.  
     - `getMessages(conversationId)`: `GET /api/messages?conversation_id=...`, update state.messages.  
     - No WebSocket yet; add a `sendMessage(text)` that uses `POST /api/chat/send` (see Phase 2).
   - **app.js:**  
     - On load: call `api.init()` then `api.getMessages(state.conversationId)`; render sidebar (single conversation), profile (name, role from state.user), welcome + quick actions.  
     - Profile dropdown: open/close; dark mode toggle (persist in localStorage, apply `body.dark-mode`).  
     - Input: auto-resize textarea, Enter to send, Shift+Enter newline; send button enable/disable.  
     - “Send”: append user message to UI, call `api.sendMessage(text)`; when response arrives, append assistant message (or placeholder “Response will appear here”).  
     - Quick action cards: click fills input or sends a predefined prompt (same as demo).  
     - Optional: “New Chat” hidden or disabled per spec.

5. **Scripts and deps**
   - **start_portal.sh:** Activate venv, load `.env`, run `uvicorn portal_api:app --host 0.0.0.0 --port 8000 --reload`.
   - **start_dev.sh:** Start `start.sh` and `start_portal.sh` in background (or in two terminals).
   - **requirements.txt:** Add `fastapi`, `uvicorn[standard]`, `websockets`, `python-multipart`.

**Deliverables:** Opening `http://localhost:8000` shows the new UI; init and (stub) send work; no changes to `app.py`, `rag/`, `eligibility/`, `database/`.

---

### Phase 2: Backend integration (real conversation and chat)

**Goal:** Portal uses the real database and the same query pipeline as Streamlit (RAG + eligibility/commands), with no changes to existing backend code.

1. **Database and conversation in portal_api.py**
   - Import `database` as `db` and call `db.initialize()` on startup (same as app.py; reuse existing env and error handling patterns).
   - **get_or_create_conversation(user_id="default_user"):**  
     - `convs = db.list_conversations(user_id, limit=1, include_archived=False)`.  
     - If non-empty, return `convs[0]`; else `db.create_conversation(user_id, title="Operations Assistant Chat")` and return it.
   - **POST /api/init:** Call `get_or_create_conversation()`, return `{ "conversation_id": conv["id"], "user": { "name": "Stanley Mutisya", "role": "Relationship Manager" } }`.

2. **Message loading**
   - **GET /api/messages:** Query param `conversation_id`. Call `db.get_messages(conversation_id, limit=100, offset=0)` (or equivalent). Return JSON array of `{ id, role, content, created_at, metadata }` so the UI can render history on load.

3. **Sending messages (HTTP first)**
   - **POST /api/chat/send:** Body `{ "content": "user text", "conversation_id": "..." }`.  
     - Validate conversation_id (e.g. get conversation; 404 if not found).  
     - Build context: `build_rag_context(conversation_id=..., user_message=content, db_manager=db, prompt_version=DEFAULT_PROMPT_VERSION)`.  
     - Call the same logic as `process_query`: either import `process_query` from a new backend module that does not import Streamlit, or inline in portal_api: `parse_command` → `dispatch_command` for commands; else `query_rag(query_text, prompt_version=..., enriched_context=...)` and build result.  
     - Save user message: `db.save_user_message(conversation_id, content, request_id=result["request_id"])`.  
     - Save assistant message: `db.save_assistant_message(conversation_id, result["response"], request_id=..., metadata=...)` (and on error, save error message).  
     - Return JSON: `{ "request_id", "response", "success", "sources", "is_eligibility_flow", "eligibility_payload" (if any), "error" (if failed) }`.

4. **Frontend**
   - **api.js:** `sendMessage(text)` → `POST /api/chat/send` with `{ content: text, conversation_id: state.conversationId }`. On response, append assistant message (and optionally show sources/eligibility in UI).
   - **app.js:** When loading messages from GET /api/messages, render them in the messages container and hide welcome block if there are messages.

**Deliverables:** Full chat flow: init creates/loads one conversation, messages load on refresh, send goes through RAG/eligibility and persists in DB. Streamlit and portal share the same data.

---

### Phase 3: WebSocket (real-time streaming, optional)

**Goal:** Replace or complement POST /api/chat/send with a WebSocket so the UI can show a typing indicator and stream assistant text.

1. **WebSocket endpoint**
   - **WS /ws/chat/{conversation_id}:** Accept connection; verify conversation exists. On message: parse JSON `{ type: "user_message", content: "..." }`; run the same pipeline as POST /api/chat/send (build context, process_query); instead of returning one blob, send a sequence of JSON frames, e.g. `assistant_message_start` → multiple `assistant_message_chunk` (if you add streaming to the LLM later) or one chunk with full text → `assistant_message_complete`. For a first version, `query_rag` is synchronous: send start, one chunk with full response, then complete.

2. **Frontend**
   - **api.js:** After init, optionally open WebSocket to `/ws/chat/{conversationId}`. On send, if WS connected, send `user_message` over WS and handle chunks to update the last assistant bubble in real time; else fallback to POST /api/chat/send.

**Deliverables:** Real-time feel; typing indicator and incremental display if you add streaming in the RAG layer later.

---

### Phase 4: Polish and parity

**Goal:** Align with demo and spec: sidebar single-conversation label, tools as placeholders, disclaimer, and any small fixes.

1. **Sidebar**
   - Single conversation: title “Operations Assistant Chat” or from API; “New Chat” hidden or disabled.
   - Tools (Notes, Tasks, Raise Ticket): leave as non-functional buttons or link to placeholder routes.

2. **Chat header**
   - Show “New Conversation” or conversation title from init/get_conversation.

3. **Disclaimer**
   - Keep the input disclaimer text from the demo: “AI responses may be inaccurate — please verify with policy documents.”

4. **Error handling**
   - Show user-friendly errors in the message area when init or send fails; optionally retry.

5. **README**
   - **portal/README.md:** How to run portal (`start_portal.sh`), env requirements, and that it uses the same backend as Streamlit.

**Deliverables:** UI matches demo behavior and spec; docs updated.

---

## 5. Minimal Alteration: Optional Backend Facade

To avoid duplicating the “process one user message” logic between `app.py` and `portal_api.py`, you can add a **single new module** and **one small change** in `app.py`:

- **New file:** e.g. `backend/chat.py` (or `core/chat_runner.py`):
  - `run_chat(user_message: str, conversation_id: str, db_manager, prompt_version: str) -> dict`
  - Inside: `build_rag_context(...)` then call the same command + RAG logic as in `process_query` (either move `process_query` here and re-export, or call `process_query` from here). Return the same result dict as `process_query`.
- **app.py:** Replace the block that calls `build_rag_context` + `process_query` with a single call to `run_chat(...)`.
- **portal_api.py:** Call `run_chat(...)` from POST /api/chat/send and from the WebSocket handler.

Then:
- **Existing code:** Only `app.py` gains one new import and one call; all other modules unchanged.
- **Portal:** No duplication of RAG/eligibility logic; single source of truth.

This is optional; the plan above works with or without it.

---

## 6. API Contract Summary

| Method | Endpoint | Purpose |
|--------|----------|--------|
| GET | / | Serve portal index.html |
| GET | /static/* | Serve CSS, JS, assets |
| POST | /api/init | Get or create single conversation; return conversation_id + user |
| GET | /api/messages | Query param conversation_id; return list of messages |
| POST | /api/chat/send | Body: content, conversation_id; run RAG/eligibility; return response + metadata |
| WS | /ws/chat/{conversation_id} | Optional: real-time send/receive (Phase 3) |
| POST | /api/eligibility/check | Optional: direct eligibility check by account number (spec) |

---

## 7. UI → Backend Mapping (from ui-screen.html)

| UI element | Data / action |
|------------|----------------|
| Logo, title “NCBA OPERATIONS ASSISTANT”, “Retail Banking” | Static or from /api/init user/dept |
| Profile: name, role | From /api/init → user.name, user.role |
| Dark mode | localStorage; body class `dark-mode` |
| Sidebar: single conversation | conversation_id + title from init; “New Chat” hidden/disabled |
| Tools (Notes, Tasks, Raise Ticket) | Placeholder buttons (no backend in plan) |
| Welcome + quick actions | Shown when messages.length === 0; cards send predefined prompts |
| Messages | GET /api/messages on load; new messages from POST /api/chat/send or WS |
| Input pill | Send via POST /api/chat/send (or WS in Phase 3) |
| Disclaimer | Static text under input |

---

## 8. Testing Checklist

- [ ] `bash start_portal.sh` → http://localhost:8000 loads the new UI.
- [ ] `bash start_dev.sh` → Streamlit on 8501, portal on 8000.
- [ ] No changes to `app.py`, `rag/`, `eligibility/`, `database/` (except optional facade).
- [ ] POST /api/init returns conversation_id and user; frontend shows them.
- [ ] GET /api/messages returns messages for the conversation; frontend renders them.
- [ ] Sending a message: POST /api/chat/send; response appears in UI; DB has user + assistant messages.
- [ ] RAG and eligibility flows behave the same as in Streamlit (same process_query path).
- [ ] Dark mode persists after refresh (localStorage).
- [ ] Quick action cards send the right prompts and get real RAG/eligibility responses.

---

## 9. File Checklist (New Only)

| File | Phase |
|------|--------|
| portal_api.py | 1, 2, 3 |
| portal/index.html | 1 |
| portal/static/css/main.css | 1 |
| portal/static/css/themes.css | 1 |
| portal/static/js/app.js | 1, 2, 4 |
| portal/static/js/api.js | 1, 2, 3 |
| portal/static/js/state.js | 1 |
| start_portal.sh | 1 |
| start_dev.sh | 1 |
| portal/README.md | 4 |
| requirements.txt (add deps) | 1 |
| backend/chat.py (optional) | 5 |

---

This plan keeps the new frontend as an additive layer: same backend, same DB, same RAG and eligibility behavior, with minimal or zero edits to the current system.
