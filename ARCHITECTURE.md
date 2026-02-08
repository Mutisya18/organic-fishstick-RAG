# System Architecture & Design Documentation

## Table of Contents
1. [System Overview](#system-overview)
2. [Architecture Diagram](#architecture-diagram)
3. [Technology Stack](#technology-stack)
4. [Component Architecture](#component-architecture)
5. [Data Flow](#data-flow)
6. [Database Schema](#database-schema)
7. [Configuration & Environment](#configuration--environment)
8. [Design Decisions](#design-decisions)
9. [Integration Points](#integration-points)
10. [Deployment Architecture](#deployment-architecture)

---

## System Overview

**Organic Fishstick** is a dual-mode chatbot system combining:
- **RAG (Retrieval-Augmented Generation):** Context-aware LLM responses grounded in document knowledge
- **Eligibility Module:** Rule-based eligibility checking with evidence-based explanations

The system serves as a customer service chatbot for a banking institution, determining product eligibility while answering general product questions.

### Key Capabilities
- Multi-turn conversation with context preservation (last N messages)
- Intelligent routing between RAG and eligibility flows
- Evidence-based eligibility results with playbook-driven explanations
- Real-time logging and tracing for debugging and analytics
- Persistent conversation history and audit trails

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    USER INTERFACE LAYER                      │
│              Streamlit Web Application (app.py)              │
│                    http://localhost:8501                     │
└──────────────┬──────────────────────────────────────────────┘
               │
               ├─────────────────────┬──────────────────────────┐
               │                     │                          │
        ┌──────▼─────────┐   ┌──────▼──────────┐    ┌──────────▼───────┐
        │  QUERY ROUTING  │   │   CONVERSATION │    │   MESSAGE SAVING │
        │   (Intent Check)│   │   MANAGEMENT   │    │   & PERSISTENCE  │
        └──────┬─────────┘   └──────┬──────────┘    └──────────┬───────┘
               │                    │                          │
        ┌──────┴────────────────────┴──────────────────────────┴────────┐
        │                                                               │
   ┌────▼─────────────┐                                    ┌───────────▼──┐
   │  ELIGIBILITY     │                                    │   RAG FLOW   │
   │  ORCHESTRATOR    │                                    │              │
   │  (Eligibility    │                                    │  • Retrieve  │
   │   Module)        │                                    │  • Augment   │
   └────┬─────────────┘                                    │  • Generate  │
        │                                                  └───────┬──────┘
        │ ┌──────────────────────────────────┐                   │
        │ │ Intent Detection                  │                   │
        │ │ Account Extraction & Validation   │                   │
        │ │ • eligible_customers.xlsx        │                   │
        │ │ • reasons_file.xlsx              │                   │
        │ └──────────────────────────────────┘                   │
        │                                                        │
        │ ┌──────────────────────────────────┐                   │
        │ │ Evidence-Based Explanation       │                   │
        │ │ • reason_playbook.json           │                   │
        │ │ • explanation_playbook.json      │                   │
        │ │ • evidence_display_rules.json    │                   │
        │ └──────────────────────────────────┘                   │
        │                                                        │
        └────────────┬─────────────────────────────────────────┘
                     │
        ┌────────────┴──────────────────┐
        │                               │
   ┌────▼──────────────┐        ┌──────▼────────────┐
   │ VECTOR DATABASE   │        │  LANGUAGE MODEL   │
   │ (Chroma)          │        │  (Ollama)         │
   │                   │        │                   │
   │ • Embeddings      │        │ Models:           │
   │   (nomic-embed)   │        │ • llama3.2:3b     │
   │ • PDF Content     │        │ • nomic-embed     │
   │ • Chunk Search    │        │                   │
   └────────────┬──────┘        └───────────────────┘
                │
        ┌───────▼──────────────┐
        │  DATA DIRECTORY      │
        │ (rag/data/)          │
        │ • PDFs               │
        │ • DOCs               │
        └──────────────────────┘
        
        
   ┌────────────────────────────────┐
   │  PERSISTENT STORAGE            │
   │  SQLAlchemy ORM + SQLite       │
   │                                │
   │ ├─ Conversations               │
   │ ├─ Messages (user/assistant)   │
   │ └─ Metadata & Timestamps       │
   └────────────────────────────────┘
   
   ┌────────────────────────────────┐
   │  LOGGING & OBSERVABILITY       │
   │                                │
   │ ├─ RAG Logging Layer           │
   │ ├─ Session Logs (JSON)         │
   │ ├─ Request Tracing             │
   │ ├─ Error Tracking              │
   │ └─ Performance Metrics         │
   └────────────────────────────────┘
```

---

## Technology Stack

### Frontend & UI
- **Streamlit:** Web UI framework for rapid prototyping
- **Python 3.10+:** Primary development language

### Backend & Core Services
- **LangChain:** LLM orchestration and RAG pipeline
- **Ollama:** Local LLM inference server (open-source foundation)
- **Chroma:** Vector database for semantic search and embeddings

### Data & Persistence
- **SQLAlchemy:** ORM for database abstraction
- **SQLite:** Development database (easily swappable to PostgreSQL)
- **Pandas:** Data loading and processing
- **python-docx, pdf2image, pytesseract:** Document parsing

### Configuration & Environment
- **python-dotenv:** Environment variable management
- **JSON:** Config file format (checks, playbooks, rules)
- **Excel (.xlsx):** Data files for eligibility

### Logging & Monitoring
- **Python logging module:** Structured logging
- **JSON:** Log format for easy parsing and analysis
- **Custom RAG Logger:** Domain-specific metrics

### Remote Access (Optional)
- **ngrok:** Tunneling for remote access to local services

---

## Component Architecture

### 1. User Interface Layer (`app.py`)
**Purpose:** Streamlit-based chat interface

**Key Functions:**
- `main()`: Entry point, UI initialization
- `process_query()`: Route queries to eligibility or RAG
- `render_chat_message()`: Display messages with metadata
- Conversation session management (Streamlit state)

**Inputs:** User text, conversation history UI state
**Outputs:** Rendered responses, eligibility results, source documents

---

### 2. RAG Pipeline (`rag/`)

#### `query_data.py` - Core RAG Engine
```
User Query
    ↓
Embed Query (nomic-embed-text)
    ↓
Search Vector DB (Chroma, top 5)
    ↓
Retrieve Documents
    ↓
Build Prompt (System + Context + Retrieval + Query)
    ↓
LLM Generation (llama3.2:3b via Ollama)
    ↓
Response + Sources
```

**Key Functions:**
- `query_rag()`: Main RAG inference function
- `extract_sources_from_query()`: Return cited documents

**Parameters:**
- `query_text`: User question
- `prompt_version`: System prompt variant (1.0.0, etc.)
- `enriched_context`: Previous conversation messages

---

#### `populate_database.py` - Data Ingestion
**Purpose:** Load PDFs/DOCs into vector database

**Process:**
1. Read documents from `rag/data/`
2. Parse text (PDF via pytesseract, DOCX via python-docx)
3. Split into chunks (default 1024 tokens)
4. Embed chunks (nomic-embed-text)
5. Store in Chroma with metadata

**Output:** 90+ indexed documents ready for retrieval

---

#### `get_embedding_function.py` - Embedding Provider
**Purpose:** Wrapper for Ollama embedding model

**Returns:** `OllamaEmbeddings` instance configured with:
- Model: `nomic-embed-text`
- Base URL: From environment (`OLLAMA_BASE_URL`)

---

#### `config/prompts.py` - Prompt Template Management
**Structure:**
```python
SYSTEM_PROMPTS = {
    "1.0.0": "You are a helpful assistant...",
    # Additional versions for AB testing
}
DEFAULT_PROMPT_VERSION = "1.0.0"
```

**Design Decision:** Versioned prompts allow experimentation without code changes.

---

### 3. Eligibility Module (`eligibility/`)

#### `orchestrator.py` - Main Entry Point
```
User Message
    ↓
Intent Detection (Is it eligibility-related?)
    ↓
If YES: Extract → Validate → Check Rules → Explain
If NO: Route to RAG
    ↓
Return Structured Payload
```

**Key Methods:**
- `process_message()`: Main eligibility flow
- Returns eligibility payload or None

---

#### `intent_detector.py` - Intent Classification
**Purpose:** Determine if message is eligibility-related

**Mechanism:** Rule-based keyword matching against `reason_detection_rules.json`

**Examples:**
- "am I eligible" → eligibility question
- "what is DIGITAL LOAN" → general question (RAG)

---

#### `account_extractor.py` - Customer Identification
**Purpose:** Extract account identifiers from message

**Methods:**
- Regex patterns for phone, account numbers
- Fallback to eligibility data lookup

---

#### `account_validator.py` - Account Verification
**Purpose:** Check if account exists in eligible_customers.xlsx

**Inputs:** Extracted account identifier
**Outputs:** Account found/not found + metadata

---

#### `llm_payload_builder.py` - Evidence Compilation
**Purpose:** Build eligibility payload with evidence

**Structure:**
```json
{
    "account_found": true,
    "account_identifier": "...",
    "eligible_products": ["DIGITAL_LOAN", "..."],
    "reasons": {
        "product": {
            "eligible": true,
            "reason": "Meets age requirement",
            "evidence": "...details..."
        }
    }
}
```

**Uses:** Playbooks from `eligibility/config/`

---

### 4. Database Layer (`database/`)

#### `models/` - ORM Models
**Conversation Model:**
- `id` (UUID)
- `title` (generated from first message)
- `message_count` (running total)
- `created_at`, `updated_at` (timestamps)
- `last_message_preview` (for display)

**Message Model:**
- `id` (UUID)
- `conversation_id` (foreign key)
- `role` (user/assistant enum)
- `content` (text)
- `created_at` (timestamp)

---

#### `repository/` - Data Access Patterns
**ConversationRepository:**
- `get_conversation()`: Fetch by ID
- `create_conversation()`: New conversation
- `get_recent_conversations()`: User's history

**MessageRepository:**
- `get_messages_by_conversation()`: Query messages
- `create_message()`: Append message
- `update_message()`: Edit (for corrections)

---

#### `core/` - Database Infrastructure
**config.py:** Connection string building
**engine.py:** SQLAlchemy engine setup
**session.py:** Session factory with connection pooling

---

### 5. Context Builder (`utils/context/context_builder.py`)

**Purpose:** Assemble conversation context for LLM

**Process:**
1. Query last N messages (default 5, from `CONTEXT_MESSAGE_LIMIT`)
2. Order chronologically
3. Format as "role: content\nrole: content"
4. Return with system prompt

**Configuration:** Adjustable via `.env` to prevent token overload

---

### 6. Logging & Observability (`utils/logger/`)

#### `rag_logging.py` - RAG-Specific Metrics
**Logged Events:**
- Retrieval: Query, chunks, similarity scores, latency
- Generation: Tokens, latency, response summary
- Users: PII detection flags

---

#### `session_manager.py` - Session Tracking
**Purpose:** Correlate requests across the session

**Structure:**
- Session ID (per user/conversation)
- Request IDs (per API call)
- Correlation IDs (debugging multi-step flows)

---

#### `trace.py` - Function Call Tracing
**Decorator:** `@technical_trace`

**Captures:**
- Function entry/exit
- Duration
- Arguments and return values
- Exception context

---

#### `pii.py` - Privacy Protection
**Purpose:** Flag and redact PII in logs

**Detects:** Phone numbers, account IDs, names, emails
**Action:** Flag in logs, redact from storage

---

---

## Data Flow

### Query Execution Flow

```
1. USER SUBMITS MESSAGE (Streamlit UI)
   ↓
2. NEW CONVERSATION CREATED (if first message)
   ↓
3. Build Context:
   - Query DB for last 5 messages
   - Format as conversation history
   ↓
4. INTENT DETECTION (eligibility_orchestrator.process_message)
   ├─ If eligibility question:
   │  ├─ Extract account info
   │  ├─ Validate account exists
   │  ├─ Check eligibility rules
   │  └─ Return structured payload
   │
   └─ If general question:
      └─ Route to RAG
      ↓
5. RAG RETRIEVAL (if non-eligibility):
   ├─ Embed user query (nomic-embed-text)
   ├─ Search Chroma (top 5 similar chunks)
   ├─ Rank by similarity
   └─ Extract metadata
   ↓
6. PROMPT CONSTRUCTION:
   System Prompt
   + Previous Messages Context
   + Retrieved Documents
   + Current Query
   ↓
7. LLM GENERATION:
   Ollama (llama3.2:3b)
   - Input: Complete prompt
   - Output: Response text
   - Latency: 75-90 seconds
   ↓
8. RESPONSE FORMATTING:
   ├─ Add response to chat history (session state)
   ├─ Save user message to DB
   ├─ Save assistant message to DB
   └─ Display with sources/metadata
   ↓
9. LOGGING:
   ├─ Retrieval metrics (chunks, scores)
   ├─ Generation metrics (tokens, latency)
   ├─ Session tracking (request ID)
   └─ Error handling (if failures)
```

---

### Message Persistence Flow

```
User Input
   ↓
save_user_message(conversation_id, content, request_id)
   ├─ Create Message record (role='user')
   ├─ Increment conversation message_count
   └─ Update last_message_preview + timestamp
   ↓
LLM Response
   ↓
save_assistant_message(conversation_id, content, request_id, metadata)
   ├─ Create Message record (role='assistant')
   ├─ Attach RAG sources or eligibility payload
   ├─ Increment conversation message_count
   └─ Update last_message_preview + timestamp
   ↓
DATABASE (SQLite)
   ├─ conversation table (1 row per conversation)
   └─ message table (2 rows per turn)
```

---

## Database Schema

### Conversations Table
```sql
CREATE TABLE conversation (
    id VARCHAR(36) PRIMARY KEY,
    title VARCHAR(500) NOT NULL,
    message_count INTEGER DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    last_message_preview VARCHAR(200)
);
```

### Messages Table
```sql
CREATE TABLE message (
    id VARCHAR(36) PRIMARY KEY,
    conversation_id VARCHAR(36) NOT NULL,
    role VARCHAR(20) NOT NULL,  -- 'user' or 'assistant'
    content TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (conversation_id) REFERENCES conversation(id)
);
```

**Indexes:**
- `(conversation_id, created_at)` for efficient historical queries
- `conversation_id` for session lookups

---

## Configuration & Environment

### .env Variables

**LLM/Ollama:**
```
OLLAMA_BASE_URL=http://localhost:11434  # or ngrok URL
CONTEXT_MESSAGE_LIMIT=5                 # Configurable context window
```

**Database:**
```
DATABASE_TYPE=sqlite
DATABASE_URL=sqlite:///chat_history.db
DATABASE_TIMEOUT=30
DATABASE_POOL_SIZE=5
DATABASE_INIT_RETRY_COUNT=3
```

**Paths:**
```
CHROMA_PATH=rag/chroma                  # Vector DB storage
DATA_PATH=rag/data                      # PDF/DOCX source files
ELIGIBILITY_DATA_PATH=eligibility/data  # Excel data files
LOG_DIR=logs                            # Session logs
```

**Logging:**
```
ENV=dev                                 # Environment label
IDLE_TIMEOUT_SECONDS=900                # Log rotation
MAX_AGE_SECONDS=3600
```

---

## Design Decisions

### 1. **Dual-Mode Routing** (Eligibility vs RAG)
**Rationale:** Some queries are rule-based (eligibility), others need knowledge retrieval (products).
**Implementation:** Intent detection routes to appropriate processor.

---

### 2. **Context Window Limit (5 Messages)**
**Rationale:** Prevent LLM token overflow while maintaining conversation flow.
**Trade-off:** Loses earlier context but prevents memory issues.
**Configurable:** Via `CONTEXT_MESSAGE_LIMIT` in `.env`.

---

### 3. **Versioned Prompts**
**Rationale:** Enable A/B testing and prompt engineering without code changes.
**Structure:** `SYSTEM_PROMPTS` dict with version keys.

---

### 4. **Local-First with Remote Option**
**Rationale:** Use local Ollama for speed, add ngrok for remote teams.
**Binding:** Must use `0.0.0.0` for ngrok access (not `127.0.0.1`).

---

### 5. **SQLite for Development**
**Rationale:** Zero setup, file-based, quick iteration.
**Production:** Easily swappable to PostgreSQL via `DATABASE_TYPE`.

---

### 6. **JSON Logging**
**Rationale:** Structured logs are machine-parseable for analytics.
**Content:** Event type, request ID, metrics, errors.

---

### 7. **PII Detection & Flagging**
**Rationale:** Regulatory compliance (banking context).
**Approach:** Flag in logs rather than block (transparency).

---

## Integration Points

### External Services
1. **Ollama Server** (Local or Remote)
   - `/api/embed`: Embeddings
   - `/api/generate`: Text generation
   - Requires `OLLAMA_HOST=0.0.0.0:11434` for ngrok

2. **ngrok** (Optional Remote Access)
   - Tunnel local port 11434 to internet
   - Update `OLLAMA_BASE_URL` in `.env`

### Internal APIs (Python Modules)
- `eligibility.orchestrator.EligibilityOrchestrator.process_message()`
- `rag.query_data.query_rag()`
- `database.db.save_user_message()`, `save_assistant_message()`
- `utils.context.context_builder.build_rag_context()`

---

## Deployment Architecture

### Development (Current)
```
┌─ Developer Machine (Windows/Linux/Mac)
│  ├─ Ollama (local, 0.0.0.0:11434)
│  ├─ Streamlit (8501)
│  ├─ SQLite (chat_history.db)
│  └─ (Optional) ngrok tunnel
└─ Remote team access via ngrok URL
```

### Production (Recommended)
```
┌─ Docker Container
│  ├─ Python app (Streamlit)
│  ├─ SQLAlchemy + PostgreSQL
│  ├─ Ollama (or external LLM API)
│  └─ Environment secrets via .env
└─ Kubernetes/Cloud orchestration
```

### Model Inference
- **Current:** Ollama (local inference, slow but private)
- **Alternative:** OpenAI/Anthropic API (faster, cost-based)
- **Swap Point:** Change `OllamaLLM` class in `query_data.py`

---

## Future Extensibility

### Planned Improvements
1. **PostgreSQL Migration** - Better for multi-user production
2. **Fine-tuned LLM** - Better domain-specific responses
3. **Vector DB Migration** - Pinecone/Weaviate for scale
4. **Multi-language Support** - Translation layer
5. **Advanced Analytics** - Conversation quality metrics
6. **Feedback Loop** - User ratings → model retraining

### Extension Points
- **New Eligibility Checks:** Add rows to `checks_catalog.json`
- **New Playbooks:** Extend `reason_playbook.json`, `explanation_playbook.json`
- **New Documents:** Drop PDFs in `rag/data/`, re-run populate
- **New Prompts:** Add version to `SYSTEM_PROMPTS` dict
- **New Integrations:** Add modules to `eligibility/` or `rag/`

---

## Performance Metrics

| Metric | Value | Notes |
|--------|-------|-------|
| Embedding Latency | 200-300ms | Per chunk |
| Retrieval (Chroma) | 600-900ms | Top 5 docs |
| LLM Generation | 75-90s | llama3.2:3b via Ollama |
| Total Query Time | ~90s | End-to-end |
| DB Query | <10ms | Message retrieval |
| Context Build | <50ms | Format history |
| Max Conversation Size | ~100 messages | Depends on DB size |

---

## Security & Compliance

### PII Protection
- Regex detection in `pii.py`
- Flagged in logs, not stored

### Access Control
- Streamlit session-based (development)
- Production: Add authentication layer

### Data Retention
- Configurable via log rotation settings
- Database records archived/deleted as needed

### API Security
- ngrok authentication (optional)
- Ollama: No auth (local) or firewall protected

---

## Troubleshooting Architecture Issues

### High Latency?
- Check Ollama inference time (expect 75-90s)
- Verify network latency (ngrok adds ~200ms)
- Profile Python code with `trace.py` logs

### Token Overload Errors?
- Reduce `CONTEXT_MESSAGE_LIMIT` in `.env`
- Use shorter documents in RAG
- Increase llama model size (trade: slower inference)

### Database Corruption?
- Backup SQLite file
- Re-initialize: `python rag/populate_database.py --reset`

### Missing Retrieval Results?
- Check `rag/data/` contains documents
- Verify Chroma index: `ls -la rag/chroma/`
- Re-populate: `python rag/populate_database.py --reset`

---

**Last Updated:** February 2026  
**Audience:** Developers, Maintainers, Contributors, Analysts  
**Status:** Active Development (v1.0.0)
