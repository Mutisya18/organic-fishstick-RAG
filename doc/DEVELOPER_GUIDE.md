# Developer Guide - Building on Organic Fishstick

## 📚 Table of Contents

1. [Project Structure](#project-structure)
2. [RAG Module](#rag-module)
3. [Eligibility Module](#eligibility-module)
4. [Backend Chat Facade](#backend-chat-facade)
5. [Database & ORM](#database--orm)
6. [Authentication & Sessions](#authentication--sessions)
7. [User Interfaces](#user-interfaces)
8. [Utilities & Logging](#utilities--logging)
9. [Adding New Features](#adding-new-features)
10. [Testing & Debugging](#testing--debugging)

---

## 📁 Project Structure

```
organic-fishstick-RAG/
├── app.py                      # Streamlit Web UI entry point
├── portal_api.py               # FastAPI Portal entry point
├── requirements.txt            # Python dependencies
├── .env                        # Configuration (git-ignored)
│
├── auth/                       # Authentication & Authorization
│   ├── __init__.py            # Auth endpoints
│   ├── session.py             # Session management
│   ├── password.py            # Password hashing (bcrypt)
│   ├── validation.py          # Email/input validation
│   ├── user_service.py        # User CRUD operations
│   ├── logger.py              # Auth logging
│   └── middleware.py          # Custom middleware
│
├── backend/                    # Unified chat backend
│   ├── chat.py                # Main chat logic (used by UI layers)
│   └── __init__.py
│
├── database/                   # Data persistence layer
│   ├── initialization.py      # DB setup & health checks
│   ├── __init__.py            # Database manager
│   ├── exceptions.py          # Custom exceptions
│   ├── core/                  # Core database setup
│   │   ├── config.py          # DB URL, type selection
│   │   ├── engine.py          # SQLAlchemy engine
│   │   ├── session.py         # Session factory
│   │   └── __init__.py
│   ├── models/                # SQLAlchemy ORM models
│   │   ├── base.py            # Base model class
│   │   ├── user.py            # User model
│   │   ├── user_session.py    # Session model
│   │   ├── conversation.py    # Conversation model
│   │   ├── message.py         # Message model
│   │   └── __init__.py
│   ├── repository/            # Data access layer (DAL)
│   │   └── conversation_repository.py
│   ├── services/              # Business logic layer
│   │   └── conversation_service.py
│   ├── migrations/            # Alembic migrations (optional)
│   └── scripts/               # DB utility scripts
│
├── eligibility/               # Rule-based eligibility engine
│   ├── orchestrator.py        # Main orchestrator (singleton)
│   ├── intent_detector.py     # Detect eligibility questions
│   ├── account_extractor.py   # Extract account numbers
│   ├── account_validator.py   # Validate account format
│   ├── eligibility_processor.py # Check eligibility logic
│   ├── llm_payload_builder.py # Format for LLM
│   ├── config_loader.py       # Load playbooks
│   ├── data_loader.py         # Load eligibility data
│   ├── config/                # Playbooks & rules (JSON)
│   │   ├── reason_playbook.json
│   │   ├── explanation_playbook.json
│   │   └── evidence_display_rules.json
│   ├── data/                  # Excel data files
│   │   ├── eligible_customers.xlsx
│   │   └── reasons_file.xlsx
│   └── __init__.py
│
├── rag/                       # Retrieval-Augmented Generation
│   ├── populate_database.py   # Load docs → embeddings → Chroma
│   ├── query_data.py          # Query Chroma + LLM generation
│   ├── get_embedding_function.py # Embedding provider wrapper
│   ├── get_generation_function.py # Generation provider wrapper
│   ├── config/                # Provider & prompt config
│   │   ├── provider_config.py # Choose Ollama/Gemini
│   │   ├── index_registry.py  # Collections per provider
│   │   └── prompts.py         # System prompts
│   ├── data/                  # Source documents
│   │   ├── document1.pdf
│   │   └── document2.docx
│   ├── chroma/                # Vector databases
│   │   ├── ollama/            # Ollama embeddings
│   │   └── gemini/            # Gemini embeddings
│   └── __init__.py
│
├── utils/                     # Shared utilities
│   ├── logger/                # Structured logging
│   │   ├── rag_logging.py     # Main logger
│   │   ├── session_manager.py # Session tracking
│   │   └── trace.py           # Technical tracing
│   ├── context/               # Request context
│   │   └── context_builder.py # Build LLM context
│   ├── commands/              # CLI command parsing
│   │   └── __init__.py
│   └── tests/                 # Test utilities
│
├── portal/                    # Portal static files
│   ├── index.html
│   ├── login.html
│   └── static/
│       ├── css/
│       └── js/
│
├── scripts/                   # Utility scripts
│   ├── seed_dev_user.py      # Create dev user
│   ├── create_admin.py        # Create admin
│   └── cleanup_sessions.py    # Cleanup tool
│
├── logs/                      # Application logs
│   ├── rag_*.log
│   └── app_*.log
│
└── tests/                     # Test suite
    ├── core/
    ├── eligibility/
    ├── health/
    └── utils/
```

---

## 🧠 RAG Module

### **Purpose**
Retrieval-Augmented Generation - Use document knowledge to ground LLM responses.

### **Key Files**

#### `rag/populate_database.py` - Data Ingestion Pipeline
```python
# Usage:
python rag/populate_database.py              # Load & embed docs
python rag/populate_database.py --reset      # Clear & reload

# What it does:
# 1. Load PDFs/DOCX from rag/data/
# 2. Split into chunks (1000 tokens, 200 overlap)
# 3. Generate embeddings using ACTIVE_EMBEDDING_PROVIDER
# 4. Store in Chroma vector database
# 5. Create metadata for retrieval
```

**Extending populate_database.py:**
```python
# Add new document loader:
from langchain_community.document_loaders import NewDocumentLoader

def load_new_document_type(data_path: Path):
    """Load from new format (e.g., HTML, XML, etc)"""
    loader = NewDocumentLoader(str(data_path))
    return loader.load()

# In load_documents():
new_docs = load_new_document_type(data_path)
docs.extend(new_docs)
```

#### `rag/query_data.py` - Query & Generation
```python
# Main function:
def query_rag(query_text: str, k: int = 5) -> dict:
    """
    Query vector database and generate response.
    
    Args:
        query_text: User's question
        k: Number of chunks to retrieve
    
    Returns:
        {
            "answer": "Generated response",
            "sources": [{"source": "doc.pdf", "page": 2, ...}]
        }
    """

# Key functions:
extract_sources_from_query()  # Get similarity search results
query_rag()                   # Full pipeline (retrieve + generate)

# Customization points:
# 1. Change similarity_search_with_score parameter (k=5)
# 2. Filter sources by score threshold
# 3. Rerank retrieved documents
# 4. Override system prompt
```

#### `rag/config/provider_config.py` - Provider Selection
```bash
# In .env:
ACTIVE_EMBEDDING_PROVIDER=ollama      # or gemini
ACTIVE_GENERATION_PROVIDER=ollama     # or gemini

# Embedding models:
OLLAMA_EMBED_MODEL=nomic-embed-text   # Dimension: 768
GEMINI_EMBED_MODEL=gemini-embedding-001 # Dimension: 3072

# Generation models:
OLLAMA_CHAT_MODEL=llama3.2:3b
GEMINI_CHAT_MODEL=gemini-2.0-flash
```

**Adding a new provider:**
1. Create `get_embedding_function()` case for new provider
2. Create `get_generation_function()` case for new provider
3. Ensure dimension consistency in `index_registry.py`
4. Update `.env` template with new provider variables

### **Embedding & Generation Functions**

```python
# In rag/get_embedding_function.py:
def get_embedding_function():
    provider = ACTIVE_EMBEDDING_PROVIDER
    if provider == "ollama":
        return OllamaEmbeddings(
            base_url=OLLAMA_BASE_URL,
            model=OLLAMA_EMBED_MODEL
        )
    elif provider == "gemini":
        return GoogleGenerativeAIEmbeddings(
            model=GEMINI_EMBED_MODEL,
            google_api_key=GEMINI_API_KEY
        )

# In rag/get_generation_function.py:
def get_generation_function():
    provider = ACTIVE_GENERATION_PROVIDER
    if provider == "ollama":
        return ChatOllama(
            base_url=OLLAMA_BASE_URL,
            model=OLLAMA_CHAT_MODEL,
            temperature=0.7
        )
    elif provider == "gemini":
        return ChatGoogleGenerativeAI(
            model=GEMINI_CHAT_MODEL,
            google_api_key=GEMINI_API_KEY
        )
```

### **System Prompts**

```python
# In rag/config/prompts.py:
SYSTEM_PROMPTS = {
    "v1": {
        "system": """You are a helpful banking assistant...
        Use the provided context to answer questions.
        If information not in context, say so.""",
        "temperature": 0.7,
        "max_tokens": 1000
    }
}

# Add new prompt version:
SYSTEM_PROMPTS["v2"] = {
    "system": "New system message...",
    "temperature": 0.5,
    "max_tokens": 1500
}

# Use in code:
prompt_version = "v2"
system_message = SYSTEM_PROMPTS[prompt_version]["system"]
```

---

## 🏦 Eligibility Module

### **Purpose**
Rule-based eligibility checking with evidence-based explanations.

### **Architecture (Singleton Pattern)**

```python
# Orchestrator is a singleton - one instance per process
orchestrator = EligibilityOrchestrator()  # First call: initializes
orchestrator = EligibilityOrchestrator()  # Second call: returns same instance

# Components initialized:
orchestrator.config_loader           # Load playbooks
orchestrator.data_loader             # Load eligibility data
orchestrator.account_extractor       # Extract account numbers
orchestrator.account_validator       # Validate format
orchestrator.eligibility_processor    # Check rules
orchestrator.payload_builder         # Format for LLM
```

### **Flow Example**

```
User: "Is account 1234567890 eligible?"

1. Intent Detection (intent_detector.py)
   └─ Output: is_eligibility_question = True

2. Account Extraction (account_extractor.py)
   └─ Extract: 1234567890
   └─ Output: accounts = ["1234567890"]

3. Account Validation (account_validator.py)
   ├─ Check: 10 digits? ✓
   ├─ Check: Numeric? ✓
   └─ Output: validated_accounts = ["1234567890"]

4. Eligibility Check (eligibility_processor.py)
   ├─ Look in eligible_customers.xlsx
   │  └─ Found? Status = ELIGIBLE
   ├─ NOT found? Look in reasons_file.xlsx
   │  └─ Get reasons: JOINT_ACCOUNT_EXCLUSION, BALANCE_EXCLUSION
   │  └─ Get evidence: joint account holder: "JOHN DOE"
   └─ Output: {
      "account": "1234567890",
      "status": "INELIGIBLE",
      "reasons": ["JOINT_ACCOUNT_EXCLUSION"],
      "evidence": {
        "account_holder": "JOHN DOE",
        "account_type": "JOINT"
      }
   }

5. LLM Payload Building (llm_payload_builder.py)
   ├─ Get reason playbook: Map code → title
   ├─ Format evidence: Template substitution
   ├─ Build payload: {
   │    "status": "INELIGIBLE",
   │    "reasons": [{
   │      "title": "Joint Account Status",
   │      "message": "Joint accounts are not eligible...",
   │      "evidence": "This is a joint account..."
   │    }]
   └─ Output: LLM-ready payload

6. LLM Generation
   ├─ System: "You are a banking assistant..."
   ├─ Context: Previous conversation + eligibility details
   └─ Generate: User-friendly explanation
```

### **Playbooks (JSON Configuration)**

#### `eligibility/config/reason_playbook.json`
```json
{
  "JOINT_ACCOUNT_EXCLUSION": {
    "title": "Joint Account Status",
    "category": "account_structure",
    "severity": "high",
    "description": "Joint accounts require additional verification"
  },
  "BALANCE_EXCLUSION": {
    "title": "Average Balance",
    "category": "financial",
    "severity": "medium",
    "description": "Minimum balance requirement not met"
  }
}
```

**Adding new reason code:**
1. Add to `reason_playbook.json`
2. Add to `explanation_playbook.json`
3. Update `reasons_file.xlsx` to use new code
4. Restart system

#### `eligibility/config/explanation_playbook.json`
```json
{
  "JOINT_ACCOUNT_EXCLUSION": {
    "explanation": "This account is {status} because {reason}. {detail}",
    "evidence_template": "Joint account holder: {account_holder}"
  }
}
```

#### `eligibility/config/evidence_display_rules.json`
```json
{
  "JOINT_ACCOUNT_EXCLUSION": {
    "fields": ["account_holder", "account_type"],
    "format": "inline",
    "emphasis": true
  }
}
```

### **Data Files**

#### `eligible_customers.xlsx`
```
ACCOUNTNO | CUSTOMERNAMES
1111111111| CUSTOMER A
2222222222| CUSTOMER B
```

**Code to read:**
```python
from data_loader import load_eligible_customers_data()
eligible_accounts = load_eligible_customers_data()
# Result: {"1111111111": "CUSTOMER A", ...}
```

#### `reasons_file.xlsx`
```
account_number | Joint_Check | CLASSIFICATION
1234567890     | Y           | INELIGIBLE
3456789012     | N           | ELIGIBLE
```

**Code to read:**
```python
reasons_data = load_reasons_data()
# Result: {
#   "1234567890": {
#     "reasons": ["JOINT_ACCOUNT_EXCLUSION"],
#     "evidence": {"Joint_Check": "Y"}
#   }
# }
```

### **Extending Eligibility Logic**

**Add new eligibility rule:**
```python
# In eligibility/eligibility_processor.py:

def check_custom_rule(account_number: str) -> dict:
    """Check custom business rule."""
    # Custom logic here
    if condition:
        return {
            "rule": "CUSTOM_RULE_NAME",
            "status": "INELIGIBLE",
            "evidence": {"key": "value"}
        }
    return None

# In check_eligibility():
custom_result = check_custom_rule(account)
if custom_result:
    reasons.append(custom_result["rule"])
    evidence.update(custom_result["evidence"])
```

---

## 🔌 Backend Chat Facade

### **Purpose**
Unified interface for chat operations, routes queries to RAG or Eligibility.

### `backend/chat.py`

```python
def run_chat(
    user_message: str,
    conversation_id: str,
    user_id: str,
    context_window: int = 5
) -> dict:
    """
    Main chat handler - routes to RAG or Eligibility.
    
    Returns:
        {
            "response": "Assistant's message",
            "sources": [...],                # If RAG
            "eligibility_result": {...},     # If eligibility
            "metadata": {
                "tokens": 245,
                "latency_ms": 1234,
                "request_id": "uuid"
            }
        }
    """
```

### **Integration Points**

```python
# Step 1: Load conversation history
context = build_rag_context(conversation_id, context_window)

# Step 2: Route query
eligibility_result = eligibility_orchestrator.process(user_message)
if eligibility_result.is_eligibility_question:
    # Use eligibility flow
    response = eligibility_flow(eligibility_result)
else:
    # Use RAG flow
    sources = extract_sources_from_query(user_message)
    response = query_rag(user_message, context)

# Step 3: Save conversation
save_messages(conversation_id, user_message, response)

# Step 4: Return formatted response
return {
    "response": response,
    "metadata": extract_metadata(response, elapsed_time)
}
```

### **Customization**

**Modify routing logic:**
```python
# In run_chat():
# Add custom routing before eligibility check
if is_command(user_message):
    return handle_command(user_message, context)

if is_eligibility_question(user_message):
    return eligibility_flow(...)

return rag_flow(user_message, context)
```

---

## 💾 Database & ORM

### **Database Models**

#### User Model
```python
from database.models import User

user = User(
    user_id="user@example.com",
    email="user@example.com",
    password_hash=hash_password("password"),
    full_name="John Doe",
    is_active=True
)

# Methods:
user.to_dict()  # Return as JSON-safe dict
str(user)       # String representation
```

#### Conversation Model
```python
from database.models import Conversation, ConversationStatus

conversation = Conversation(
    user_id="user@example.com",
    title="Product Eligibility Question",
    status=ConversationStatus.ACTIVE,
    message_count=0,
    is_hidden=False
)

# Methods:
conversation.archive()   # Soft-delete
conversation.unarchive() # Restore
conversation.hide()      # Auto-hidden by system
conversation.unhide()    # Restore visibility
conversation.is_active   # Property: check status
```

#### Message Model
```python
from database.models import Message, MessageRole

message = Message(
    conversation_id="conv-uuid",
    role=MessageRole.USER,
    content="What is the eligibility requirement?",
    msg_metadata={
        "request_id": "req-123",
        "source": "user_input",
        "tokens": 12,
        "latency_ms": 450
    }
)

# Properties:
message.request_id    # Extract from metadata
message.source       # Extract from metadata
message.tokens       # Extract from metadata
message.model_name   # Extract from metadata
message.latency_ms   # Extract from metadata
```

### **Data Access (Repository Pattern)**

```python
# In database/repository/conversation_repository.py:

class ConversationRepository:
    @staticmethod
    def create(user_id: str, title: str) -> Conversation:
        """Create new conversation."""
    
    @staticmethod
    def get_by_id(conversation_id: str) -> Conversation:
        """Get conversation by ID."""
    
    @staticmethod
    def list_by_user(user_id: str) -> List[Conversation]:
        """List all conversations for user."""
    
    @staticmethod
    def delete(conversation_id: str):
        """Delete conversation and messages."""

# Usage:
from database.repository import ConversationRepository

conversation = ConversationRepository.create(
    user_id="user@example.com",
    title="Product Question"
)

conversations = ConversationRepository.list_by_user("user@example.com")
```

### **Business Logic (Services)**

```python
# In database/services/conversation_service.py:

def get_visible_conversations(user_id: str) -> List[Conversation]:
    """Get non-hidden conversations ordered by recency."""

def count_visible_conversations(user_id: str) -> int:
    """Count visible conversations."""

def apply_auto_hide_if_needed(user_id: str, max_active: int = 10):
    """Auto-hide oldest conversations if limit exceeded."""
```

### **Adding New Models**

```python
# Create models/custom_model.py:
from .base import BaseModel
from sqlalchemy import Column, String, Integer, ForeignKey

class CustomModel(BaseModel):
    __tablename__ = "custom_table"
    
    custom_field = Column(String(255), nullable=False)
    user_id = Column(String(255), ForeignKey("users.user_id"))
    
    def __repr__(self):
        return f"CustomModel(id={self.id}, custom_field={self.custom_field})"

# Export in models/__init__.py:
from .custom_model import CustomModel

# Use in code:
from database.models import CustomModel
custom = CustomModel(custom_field="value", user_id="user@example.com")
```

---

## 🔐 Authentication & Sessions

### **Authentication Flow**

```python
from auth import authenticate, create_user

# Sign up
user = create_user(
    email="user@example.com",
    password="secure_password",
    full_name="John Doe"
)

# Login
user, session_token = authenticate(
    email="user@example.com",
    password="secure_password"
)

# Validate session
is_valid = validate_session(session_token)

# Logout
expire_session(session_token)
```

### **Password Security**

```python
from auth.password import hash_password, verify_password

# Hash on signup/password change:
password_hash = hash_password("user_password")

# Verify on login:
is_correct = verify_password("user_password", stored_hash)
```

### **Session Management**

```python
from auth.session import create_session, get_session, expire_session

# Create session on login:
session = create_session(user_id="user@example.com")
session_token = session.token  # Send to client (cookie/header)

# Validate session on each request:
session = get_session(session_token)
if session and session.is_valid():
    current_user = session.user
else:
    # Redirect to login

# Logout:
expire_session(session_token)
```

### **Middleware Protection**

```python
# In portal_api.py or app.py:
from auth import get_current_user, Depends

@app.get("/api/profile")
async def get_profile(current_user = Depends(get_current_user)):
    """Protected endpoint - requires authentication."""
    return {"user_id": current_user.user_id, "email": current_user.email}
```

---

## 🖥️ User Interfaces

### **Streamlit UI (app.py)**

```python
import streamlit as st
from backend.chat import run_chat
from database import db

# Initialize session state
if 'conversation_id' not in st.session_state:
    st.session_state.conversation_id = None

# UI Layout:
st.title("AI Banking Assistant")

# Sidebar
with st.sidebar:
    user = st.selectbox("User", options=list_users())
    st.session_state.current_user = user

# Chat interface
messages = st.container()
user_input = st.text_input("Your question:")

if user_input:
    # Call backend
    response = run_chat(
        user_message=user_input,
        conversation_id=st.session_state.conversation_id,
        user_id=st.session_state.current_user
    )
    
    # Display response
    messages.write(response["response"])
    if response.get("sources"):
        messages.info(f"Sources: {response['sources']}")
```

**Extending Streamlit UI:**
```python
# Add custom component
if st.checkbox("Show eligibility details"):
    if response.get("eligibility_result"):
        st.json(response["eligibility_result"])

# Add download button
if st.button("Export conversation"):
    export_conversation(st.session_state.conversation_id)
```

### **FastAPI Portal (portal_api.py)**

```python
from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel

app = FastAPI(title="Portal API")

class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None

@app.post("/api/chat")
async def chat(
    request: ChatRequest,
    current_user = Depends(get_current_user)
):
    """Send a message and get response."""
    response = run_chat(
        user_message=request.message,
        conversation_id=request.conversation_id,
        user_id=current_user.user_id
    )
    return response

@app.get("/api/conversations")
async def list_conversations(
    current_user = Depends(get_current_user)
):
    """Get user's conversations."""
    conversations = ConversationRepository.list_by_user(current_user.user_id)
    return [
        {
            "id": conv.id,
            "title": conv.title,
            "message_count": conv.message_count,
            "last_message_at": conv.last_message_at
        }
        for conv in conversations
    ]
```

**Adding new endpoint:**
```python
@app.post("/api/eligibility/check")
async def check_eligibility(
    account_number: str,
    current_user = Depends(get_current_user)
):
    """Direct eligibility check endpoint."""
    from eligibility.orchestrator import EligibilityOrchestrator
    
    orchestrator = EligibilityOrchestrator()
    result = orchestrator.process_eligibility_check(account_number)
    return result
```

---

## 🛠️ Utilities & Logging

### **Structured Logging**

```python
from utils.logger.rag_logging import RAGLogger

logger = RAGLogger()

# Log different severity levels:
request_id = logger.generate_request_id()

logger.log_warning(
    request_id=request_id,
    message="Feature flag enabled",
    event_type="feature_gate",
    metadata={"feature": "new_embedding_model"}
)

logger.log_error(
    request_id=request_id,
    error_type="QueryError",
    error_message="Vector DB not responding",
    traceback_str=traceback.format_exc()
)

logger.log(
    request_id=request_id,
    event="chat_completed",
    severity="INFO",
    message="User message processed successfully"
)
```

**Log file patterns:**
- `logs/rag_YYYY-MM-DD.log` - RAG operations
- `logs/app_YYYY-MM-DD.log` - Application events
- `logs/eligibility_YYYY-MM-DD.log` - Eligibility operations

### **Request Context**

```python
from utils.context.context_builder import build_rag_context

# Build conversation context for LLM:
context = build_rag_context(
    conversation_id="conv-uuid",
    max_messages=5
)
# Returns: Formatted conversation history as string for LLM prompt
```

### **Command Parsing**

```python
from utils.commands import parse_command, dispatch_command

# Parse user input for commands:
parsed = parse_command("/eligibility account:1234567890")

if parsed.is_command:
    result = dispatch_command(
        command_name=parsed.command_name,
        args=parsed.args_dict
    )
```

---

## 🚀 Adding New Features

### **Add New Document Type to RAG**

1. Create loader in `rag/populate_database.py`:
```python
def load_xlsx_documents(data_path: Path):
    """Load Excel documents."""
    loader = ExcelLoader(str(data_path))
    return loader.load()
```

2. Add to main pipeline:
```python
def load_documents():
    docs = []
    docs.extend(load_pdf_documents(data_path))
    docs.extend(load_docx_documents(data_path))
    docs.extend(load_xlsx_documents(data_path))  # NEW
    return docs
```

3. Regenerate embeddings:
```bash
python rag/populate_database.py --reset
```

### **Add Custom Command**

1. Create command handler in `utils/commands/`:
```python
def handle_eligibility_command(args):
    """Handle /eligibility command."""
    account = args.get("account")
    orchestrator = EligibilityOrchestrator()
    result = orchestrator.process_eligibility_check(account)
    return format_result(result)
```

2. Register in command registry:
```python
COMMAND_REGISTRY = {
    "eligibility": {
        "handler": handle_eligibility_command,
        "required_args": ["account"],
        "description": "Check product eligibility"
    }
}
```

3. Add to Portal API:
```python
@app.post("/api/commands/eligibility")
async def command_eligibility(account: str, current_user = Depends(get_current_user)):
    result = handle_eligibility_command({"account": account})
    return result
```

### **Create New Eligibility Rule**

1. Add reason code to playbooks:
```json
# eligibility/config/reason_playbook.json
{
  "CUSTOM_RULE": {
    "title": "Custom Rule",
    "description": "Custom business logic"
  }
}
```

2. Implement check function:
```python
# eligibility/eligibility_processor.py
def check_custom_rule(self, account_data):
    if custom_condition(account_data):
        return {
            "code": "CUSTOM_RULE",
            "evidence": {...}
        }
    return None
```

3. Add to main check flow:
```python
def process_account(self, account):
    result = self.check_custom_rule(account)
    if result:
        return result
```

---

## 🧪 Testing & Debugging

### **Test Structure**

```
tests/
├── health/              # Health check tests
├── core/                # Core functionality
├── eligibility/         # Eligibility module tests
├── portal/              # Portal API tests
└── utils/               # Utility tests
```

### **Run Tests**

```bash
# All tests
pytest

# Specific module
pytest tests/eligibility/

# With coverage
pytest --cov=. tests/

# Watch mode
pytest-watch

# Run phase 5 tests
bash run_phase5_tests.sh
```

### **Debugging Tips**

```python
# Add logging to trace execution:
logger.log_warning(
    request_id="debug",
    message=f"Variable value: {variable}",
    event_type="debug"
)

# Use Python debugger:
import pdb; pdb.set_trace()

# Check logs:
tail -f logs/rag_*.log

# SQL query debugging:
# Set DATABASE_DEBUG=true in .env
# SQLAlchemy will echo all queries
```

### **Common Issues**

| Issue | Cause | Solution |
|-------|-------|----------|
| RAG returns empty results | No embeddings generated | Run `python rag/populate_database.py --reset` |
| Eligibility check fails | Data file format incorrect | Validate Excel files in `eligibility/data/` |
| LLM not responding | Ollama not running or ngrok expired | `ollama serve` or restart ngrok tunnel |
| Database locked | SQLite file permissions | `chmod 644 organic-fishstick.db` |
| Session expired | Session timeout | User needs to login again |

---

## 📖 Related Documentation

- [SYSTEM_ARCHITECTURE.md](SYSTEM_ARCHITECTURE.md) - High-level design
- [DATABASE_GUIDE.md](DATABASE_GUIDE.md) - Database operations
- [STARTUP_GUIDE.md](STARTUP_GUIDE.md) - Setup instructions

---

**Last Updated:** February 15, 2026  
**Version:** 1.0  
**For Developers Building on This System**
