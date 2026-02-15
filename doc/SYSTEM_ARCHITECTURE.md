# System Architecture & Pipeline Documentation

## 📊 Table of Contents
1. [System Overview](#system-overview)
2. [High-Level Architecture Diagram](#high-level-architecture-diagram)
3. [Component Architecture](#component-architecture)
4. [Request/Response Pipeline](#requestresponse-pipeline)
5. [Data Flow Diagrams](#data-flow-diagrams)
6. [Module Interactions](#module-interactions)
7. [Technology Stack](#technology-stack)

---

## 🎯 System Overview

**Organic Fishstick** is a dual-mode AI chatbot system that combines:

1. **RAG (Retrieval-Augmented Generation)** - Context-aware LLM responses from document knowledge
2. **Eligibility Engine** - Rule-based product eligibility checking
3. **Multi-channel UI** - Both Streamlit web UI and FastAPI Portal
4. **Persistent Storage** - SQLite conversation history and audit trails

The system serves banking customers by:
- ✅ Answering product questions with document context
- ✅ Determining product eligibility with evidence-based explanations
- ✅ Maintaining conversation history across sessions
- ✅ Providing audit trails for compliance

---

## 🏗️ High-Level Architecture Diagram

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                           USER INTERFACE LAYER                               │
├──────────────────┬──────────────────────────────────┬───────────────────────┤
│  Streamlit UI    │      FastAPI Portal              │  Raw API Endpoints    │
│  (app.py)        │      (portal_api.py)             │  (REST)               │
│                  │                                  │                       │
│ http://localhost │ http://localhost:8000            │ /api/chat             │
│ :8501            │ /api/conversations              │ /api/eligibility      │
│                  │ /api/messages                   │                       │
└────────┬─────────┴──────────────┬───────────────────┴───────┬───────────────┘
         │                        │                           │
         └────────────────────────┼───────────────────────────┘
                                  │
                    ┌─────────────▼──────────────┐
                    │  BACKEND CHAT FACADE       │
                    │  (backend/chat.py)         │
                    │                            │
                    │ • Context Building         │
                    │ • Query Routing            │
                    │ • Response Formatting      │
                    │ • Message Persistence      │
                    └──┬──────────────┬──────────┘
                       │              │
           ┌───────────┘              └──────────────┐
           │                                        │
    ┌──────▼──────────┐            ┌────────────────▼─────────┐
    │   RAG ENGINE    │            │ ELIGIBILITY ENGINE       │
    │                 │            │                          │
    │ • Query         │            │ • Intent Detection       │
    │ • Retrieve      │            │ • Account Extraction     │
    │ • Augment       │            │ • Account Validation     │
    │ • Generate      │            │ • Eligibility Check      │
    │                 │            │ • Evidence Building      │
    └──┬──────────┬───┘            └────────┬────────────────┘
       │          │                         │
    ┌──▼──┐  ┌────▼──────────┐     ┌──────▼──────────┐
    │ LLM │  │ VECTOR DB     │     │ DATA LOADER     │
    │     │  │ (Chroma)      │     │ Rules & Config  │
    │Ollama/│ ├─ Ollama DB  │     ├─ Playbooks     │
    │Gemini│ ├─ Gemini DB  │     ├─ Eligibility    │
    │     │  │              │     │   Data            │
    └─────┘  └────┬─────────┘     └────────────────┘
                  │
             ┌────▼──────────┐
             │ SOURCE DOCS   │
             │ (rag/data/)   │
             │ • PDFs        │
             │ • DOCX        │
             └───────────────┘


    ┌────────────────────────────────────────────────────────────┐
    │              PERSISTENT STORAGE LAYER                      │
    │                                                            │
    │  SQLite Database (organic-fishstick.db)                   │
    │  SQLAlchemy ORM + Alembic Migrations                      │
    │                                                            │
    │  Tables:                                                  │
    │  ├─ users              [Authentication & Authorization]  │
    │  ├─ user_sessions      [Active Sessions]                │
    │  ├─ conversations      [Conversation Threads]           │
    │  └─ messages           [Message History]                │
    │                                                            │
    │  Features:                                                │
    │  ├─ Multi-conversation Management                         │
    │  ├─ Message Metadata (tokens, latency, sources)          │
    │  ├─ Indexing for Fast Queries                            │
    │  └─ Cascade Deletes (conversation → messages)            │
    └────────────────────────────────────────────────────────────┘

    ┌────────────────────────────────────────────────────────────┐
    │            AUTHENTICATION & SECURITY LAYER                │
    │                                                            │
    │  ├─ Session Management (auth.session)                    │
    │  ├─ Password Hashing (auth.password)                     │
    │  ├─ User Validation (auth.validation)                    │
    │  ├─ CORS & Middleware                                    │
    │  └─ Request/Response Logging                             │
    └────────────────────────────────────────────────────────────┘

    ┌────────────────────────────────────────────────────────────┐
    │               LOGGING & OBSERVABILITY LAYER               │
    │                                                            │
    │  ├─ Structured Logging (utils/logger/)                   │
    │  ├─ Request ID Tracing                                   │
    │  ├─ Performance Metrics (latency, tokens)                │
    │  ├─ Error Tracking with Tracebacks                       │
    │  └─ Log Files (logs/*.log)                               │
    └────────────────────────────────────────────────────────────┘
```

---

## 🔄 Component Architecture

### **Module Breakdown**

```
┌─ RAG Module (rag/)
│  ├─ populate_database.py      # Load PDFs/DOCX, generate embeddings
│  ├─ query_data.py             # Retrieve relevant documents
│  ├─ get_embedding_function.py # Embedding model (Ollama/Gemini)
│  ├─ get_generation_function.py# Generation model (Ollama/Gemini)
│  ├─ config/
│  │  ├─ provider_config.py     # Provider selection & settings
│  │  ├─ index_registry.py      # DB collections per provider
│  │  └─ prompts.py             # System prompts for LLM
│  └─ chroma/                   # Vector database storage
│     ├─ ollama/                # Ollama embeddings
│     └─ gemini/                # Gemini embeddings
│
├─ Eligibility Module (eligibility/)
│  ├─ orchestrator.py           # Main orchestrator (singleton)
│  ├─ intent_detector.py        # Detect eligibility questions
│  ├─ account_extractor.py      # Extract account numbers
│  ├─ account_validator.py      # Validate account format
│  ├─ eligibility_processor.py  # Check eligibility rules
│  ├─ llm_payload_builder.py    # Format evidence for LLM
│  ├─ config/                   # Playbooks & rules
│  │  ├─ reason_playbook.json   # Reason codes & titles
│  │  ├─ explanation_playbook.json # Evidence display templates
│  │  └─ evidence_display_rules.json # Formatting rules
│  └─ data/                     # Eligibility data
│     ├─ eligible_customers.xlsx # Eligible account list
│     └─ reasons_file.xlsx       # Reasons per account
│
├─ Database Module (database/)
│  ├─ initialization.py         # DB setup & initialization
│  ├─ core/
│  │  ├─ config.py              # Database URL & type
│  │  ├─ engine.py              # SQLAlchemy engine
│  │  └─ session.py             # Session management
│  ├─ models/                   # SQLAlchemy ORM models
│  │  ├─ base.py                # Base model class
│  │  ├─ user.py                # User authentication
│  │  ├─ user_session.py        # Active sessions
│  │  ├─ conversation.py        # Conversation threads
│  │  └─ message.py             # Message history
│  ├─ repository/               # Data access layer
│  ├─ services/                 # Business logic
│  └─ migrations/               # Alembic migrations (if used)
│
├─ Backend Facade (backend/)
│  ├─ chat.py                   # Unified chat interface
│  │  ├─ run_chat() - Main entry point
│  │  ├─ validate_message()
│  │  └─ Message formatting & persistence
│  └─ Used by: app.py, portal_api.py
│
├─ Authentication & Security (auth/)
│  ├─ __init__.py               # Auth endpoints
│  ├─ session.py                # Session management
│  ├─ password.py               # Hashing & validation
│  ├─ validation.py             # Email & input validation
│  ├─ user_service.py           # User CRUD operations
│  ├─ logger.py                 # Auth logging
│  └─ middleware.py             # Custom middleware
│
├─ Utilities (utils/)
│  ├─ logger/                   # Structured logging
│  │  ├─ rag_logging.py         # RAG logger with request IDs
│  │  ├─ session_manager.py     # Session tracking
│  │  └─ trace.py               # Technical tracing
│  ├─ context/                  # Request context
│  │  └─ context_builder.py     # Build conversation context
│  ├─ commands/                 # Command parsing
│  │  └─ parse_command.py       # CLI-style commands
│  └─ tests/                    # Testing utilities
│
├─ User Interfaces
│  ├─ app.py                    # Streamlit WebUI (port 8501)
│  ├─ portal_api.py             # FastAPI Portal (port 8000)
│  └─ portal/                   # Portal static files
│     ├─ index.html
│     ├─ login.html
│     └─ static/
│
└─ Scripts & Tools
   ├─ start_portal.sh           # Start Portal with full init
   ├─ start.sh                  # Start Streamlit
   ├─ start_dev.sh              # Start both
   └─ scripts/
      ├─ seed_dev_user.py       # Create dev user
      ├─ create_admin.py        # Create admin user
      └─ cleanup_sessions.py    # Expired session cleanup
```

---

## 📤📥 Request/Response Pipeline

### **User Query to Response (Complete Flow)**

```
STEP 1: USER INPUT
  ↓
  User sends message via Streamlit/Portal UI
  └─ Message: "What products are available for my account 12345?"
  └─ Session: User authenticated, session valid
  └─ Conversation: Loaded from database

STEP 2: VALIDATION
  ↓
  backend/chat.py: validate_message()
  ├─ Check non-empty
  ├─ Check length limits
  ├─ Parse for commands
  └─ Validate command arguments (if command)
  
  ✓ Invalid → Return error message
  ✓ Valid → Continue

STEP 3: CONTEXT BUILDING
  ↓
  utils/context/context_builder.py: build_rag_context()
  ├─ Load conversation history (last N messages)
  ├─ Format as LLM context
  └─ Create system prompt with guidelines
  └─ Output: Conversation context string

STEP 4: INTENT DETECTION & ROUTING
  ↓
  eligibility/orchestrator.py: process_user_message()
  ├─ Call intent_detector: Is this an eligibility question?
  │
  ├─ IF eligibility question (YES):
  │  │  ↓
  │  │  CONTINUE ELIGIBILITY FLOW (see STEP 5A)
  │  │
  ├─ ELIF command (YES):
  │  │  ↓
  │  │  DISPATCH COMMAND (see STEP 5B)
  │  │
  └─ ELSE (RAG question):
     └─> CONTINUE RAG FLOW (see STEP 5C)

STEP 5A: ELIGIBILITY FLOW (If eligibility question detected)
  ↓
  eligibility/orchestrator.py:
  ├─ extract_account_numbers() → ["12345678"]
  ├─ validate_accounts() → ✓ Valid 10-digit account
  ├─ check_eligibility() → Check against eligible_customers.xlsx
  │  ├─ Account found? → Status (ELIGIBLE/INELIGIBLE)
  │  └─ If INELIGIBLE: Load reasons_file.xlsx
  ├─ build_evidence() → Extract reason codes & evidence
  ├─ format_for_llm() → Create LLM payload with evidence
  └─ Output: Eligibility result with evidence
     └─> REDIRECT TO LLM WITH EVIDENCE (STEP 6A)

STEP 5B: COMMAND DISPATCH (If command detected)
  ↓
  utils/commands:
  ├─ parse_command() → Parse CLI-style syntax
  ├─ validate_command_args() → Validate parameters
  ├─ dispatch_command() → Execute command handler
  └─ Output: Command result (e.g., conversation list)
     └─> SAVE & RETURN RESULT

STEP 5C: RAG FLOW (If RAG question)
  ↓
  rag/query_data.py: query_rag()
  ├─ Get embedding function (Ollama/Gemini)
  ├─ Query Chroma vector database
  │  ├─ Similarity search with top-k results
  │  └─ Retrieve: ["Document A (page 2)", "Document B (page 5)"]
  ├─ Extract source metadata
  ├─ Build context: Source documents + conversation history
  └─ Output: Retrieved documents + sources
     └─> REDIRECT TO LLM WITH CONTEXT (STEP 6C)

STEP 6A: LLM GENERATION (Eligibility with Evidence)
  ↓
  rag/get_generation_function.py:
  ├─ Provider: ACTIVE_GENERATION_PROVIDER (Ollama/Gemini)
  ├─ Model: llama3.2:3b (or gemini-2.0-flash)
  ├─ Prompt: System + context + eligibility evidence
  ├─ Call LLM: Generate user-friendly response
  ├─ Streaming: Yield chunks as they arrive
  └─ Output: Full response text
     └─> FORMAT & RETURN (STEP 7)

STEP 6B: LLM GENERATION (Command Result)
  ↓
  Command result already formatted
  └─> FORMAT & RETURN (STEP 7)

STEP 6C: LLM GENERATION (RAG with Sources)
  ↓
  rag/get_generation_function.py:
  ├─ Provider: ACTIVE_GENERATION_PROVIDER
  ├─ Model: llama3.2:3b (or gemini-2.0-flash)
  ├─ Prompt: System + conversation + retrieved docs
  ├─ Call LLM: Generate grounded response
  ├─ Streaming: Yield chunks as they arrive
  └─ Output: Full response text
     └─> FORMAT & RETURN (STEP 7)

STEP 7: RESPONSE FORMATTING & PERSISTENCE
  ↓
  backend/chat.py:
  ├─ Get final response from LLM
  ├─ Extract metadata:
  │  ├─ Tokens used
  │  ├─ Latency (ms)
  │  ├─ Model name
  │  ├─ Source documents (if RAG)
  │  └─ Request ID for tracing
  ├─ Create Message object (ASSISTANT role)
  └─ Output: Formatted message with metadata

STEP 8: PERSISTENCE
  ↓
  database/repository/message_repository.py:
  ├─ Save USER message to database
  ├─ Save ASSISTANT message to database
  ├─ Update conversation.message_count
  ├─ Update conversation.last_message_at
  └─ Commit transaction

STEP 9: LOGGING
  ↓
  utils/logger/rag_logging.py:
  ├─ Create structured log entry
  ├─ Include: request_id, event, severity, metadata
  ├─ Write to: logs/rag_*.log
  └─ Output: {timestamp} [request_id] User→Assistant flow complete

STEP 10: RESPONSE TO USER
  ↓
  ├─ Streamlit: Display in chat widget
  ├─ Portal: Send JSON response with metadata
  └─ User sees: Response + sources (if RAG) + response time

END
```

---

## 🔗 Module Interactions

### **Eligibility + RAG Hybrid Flow**

```
User: "What's the eligibility for account 12345?"

1. Intent Detection finds: account number + eligibility question
   ↓
2. Extract: 12345 → account_number
   ↓
3. Validate: Is "12345" a valid 10-digit account? (Could be 1234500000)
   ↓
4. Check Eligibility:
   ├─ Look in eligible_customers.xlsx → Found? ELIGIBLE
   └─ Look in reasons_file.xlsx → Get reasons → INELIGIBLE
   ↓
5. Build Evidence:
   ├─ Reason: "JOINT_ACCOUNT_EXCLUSION"
   ├─ Detail: "Joint accounts are not eligible"
   └─ Template: "This account is {status} because {reason}. {detail}"
   ↓
6. Call LLM with Evidence:
   ├─ System: "You are a banking assistant..."
   ├─ Context: Previous conversation
   ├─ Evidence: Full eligibility details
   └─ User Query: "What's the eligibility for account 12345?"
   ↓
7. LLM Response:
   "Your account (12345) is currently ineligible for this product 
    because it is a joint account. Joint accounts require additional 
    verification. Please contact customer service at..."
   ↓
8. Save conversation + return response
```

---

## 💾 Data Flow Diagrams

### **Data Ingestion (populate_database.py)**

```
SOURCE DOCUMENTS (rag/data/)
  ├─ document1.pdf
  ├─ document2.pdf
  └─ document3.docx
       ↓
DOCUMENT LOADER (PyPDFDirectoryLoader, Docx2txtLoader)
       ↓
RAW TEXT EXTRACTION
       ↓
TEXT SPLITTER (RecursiveCharacterTextSplitter)
  └─ Split on: ["\n\n", "\n", " ", ""]
  └─ Chunk size: 1000 tokens
  └─ Overlap: 200 tokens
       ↓
CHUNKS + METADATA
  {
    "content": "chunk text...",
    "metadata": {
      "source": "document1.pdf",
      "page": 5,
      "id": "doc1_chunk_5"
    }
  }
       ↓
EMBEDDING FUNCTION (get_embedding_function)
  ├─ Provider: ACTIVE_EMBEDDING_PROVIDER
  ├─ Model: nomic-embed-text (Ollama) OR gemini-embedding-001 (Gemini)
  └─ Dimension: 768
       ↓
EMBEDDINGS (Vector representation)
  [0.234, -0.102, 0.456, ... 768 dimensions]
       ↓
CHROMA VECTOR DATABASE
  ├─ Collection Name: Based on provider
  ├─ Path: rag/chroma/ollama/ OR rag/chroma/gemini/
  └─ Storage:
     ├─ chroma.sqlite3 (metadata)
     └─ data/ (vector data)
```

### **Query Execution (query_data.py)**

```
USER QUERY
  "What are the eligibility requirements?"
       ↓
QUERY EMBEDDING
  ├─ Provider: ACTIVE_EMBEDDING_PROVIDER
  ├─ Model: Same as training embeddings
  └─ Output: Query vector [0.210, -0.095, 0.478...]
       ↓
SIMILARITY SEARCH (Chroma)
  ├─ Distance Metric: Cosine Similarity
  ├─ Top-K: 5 results
  └─ Results ranked by relevance
       ↓
RETRIEVED DOCUMENTS
  [
    {
      "content": "Eligibility requirements...",
      "score": 0.87,
      "metadata": {"source": "doc1.pdf", "page": 2}
    },
    {
      "content": "Additional requirements...",
      "score": 0.82,
      "metadata": {"source": "doc2.pdf", "page": 1}
    },
    ...
  ]
       ↓
CONTEXT BUILDING
  ├─ Conversation history (last 5 messages)
  ├─ Retrieved documents
  └─ System prompt
       ↓
LLM PROMPT
  System: "You are a helpful banking assistant..."
  Context: Previous conversation + retrieved docs
  Query: User's original question
       ↓
LLM GENERATION (Streaming)
  Model generates response token by token
       ↓
RESPONSE TO USER
  + Sources cited from retrieved documents
```

---

## 🛠️ Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Frontend** | Streamlit, FastAPI + HTML/CSS/JS | Web UI & API |
| **Backend** | Python 3.8+, FastAPI, Flask-like patterns | Business logic |
| **ORM** | SQLAlchemy | Database abstraction |
| **Database** | SQLite (dev), PostgreSQL (prod) | Persistent storage |
| **Vector DB** | Chroma | Semantic search |
| **Embeddings** | Ollama (nomic-embed-text) or Gemini | Vector generation |
| **LLM** | Ollama (llama3.2:3b) or Gemini (gemini-2.0-flash) | Text generation |
| **Auth** | bcrypt, JWT-style tokens | Security |
| **Logging** | Python logging, custom JSON formatters | Observability |
| **Configuration** | `.env` files, environment variables | Settings management |
| **Testing** | pytest | Quality assurance |

---

## 🔌 Integration Points

### **External Services**

```
System ←→ Ollama Service
  ├─ Embeddings: http://localhost:11434/api/embed
  ├─ Chat: http://localhost:11434/api/chat
  └─ Tags: http://localhost:11434/api/tags (health check)

System ←→ Google Gemini API
  ├─ Endpoint: https://generativelanguage.googleapis.com/v1
  ├─ Auth: GEMINI_API_KEY header
  └─ Models: gemini-embedding-001, gemini-2.0-flash

System ←→ File System
  ├─ Read: rag/data/*.pdf, *.docx
  ├─ Write: rag/chroma/, logs/
  └─ Access: eligibility/data/*.xlsx
```

---

## 📈 Scalability Considerations

### **Current Architecture Limits**

- **Single File Database**: SQLite suitable for development, ~10k conversations
- **In-Memory Embeddings**: Vector DB queries sequential (Chroma)
- **Synchronous Processing**: LLM calls block until response received

### **Production Scaling Path**

```
Phase 1: Current
  ├─ SQLite local database
  ├─ Chroma file-based vector DB
  └─ Single-threaded request handling

Phase 2: Distributed (Recommended)
  ├─ PostgreSQL Remote Database
  ├─ Redis for session caching
  ├─ Chroma in server mode (separate process)
  └─ FastAPI + Uvicorn workers

Phase 3: Cloud-Native
  ├─ PostgreSQL on RDS/Cloud SQL
  ├─ Vector DB service (Pinecone/Weaviate)
  ├─ Kubernetes orchestration
  └─ CDN for static assets
```

---

## 📚 Related Documentation

- [STARTUP_GUIDE.md](STARTUP_GUIDE.md) - Setup & initialization
- [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md) - Detailed module documentation
- [DATABASE_GUIDE.md](DATABASE_GUIDE.md) - Database schema & queries
- [QUICK_REFERENCE.md](QUICK_REFERENCE.md) - Quick commands

---

**Last Updated:** February 15, 2026  
**Version:** 1.0  
**Maintained By:** Development Team


