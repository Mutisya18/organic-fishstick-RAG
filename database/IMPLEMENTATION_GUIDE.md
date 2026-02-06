# Database Layer Implementation Guide
**Organic Fishstick Chatbot - SQLite/PostgreSQL Memory System**

**Date**: February 6, 2026  
**Purpose**: Design guide for implementing the database layer with logic, architecture, and pseudocode (no actual code yet)  
**Design Decisions**:
- Database: SQLite (initial), PostgreSQL (production)
- ORM + Context managers pattern
- DB layer stays "pure" (no logging, business logic in app.py)
- Lazy initialization, separate from app.py
- Concurrent access support via connection pooling
- Schema validation at DB layer; business logic validation at app.py layer

---

## 1. FOLDER STRUCTURE

```
/root
├── database/
│   ├── __init__.py
│   ├── IMPLEMENTATION_GUIDE.md (this file)
│   ├── SCHEMA.md (ER diagram, SQL DDL)
│   ├── models/
│   │   ├── __init__.py
│   │   ├── base.py (SQLAlchemy declarative base, common columns)
│   │   ├── conversation.py (Conversation model class)
│   │   ├── message.py (Message model class)
│   │   └── schemas.py (Pydantic schemas for validation)
│   ├── core/
│   │   ├── __init__.py
│   │   ├── engine.py (SQLAlchemy engine initialization, connection pooling)
│   │   ├── session.py (Session manager, context managers)
│   │   └── config.py (DB config: connection string, pool settings, etc.)
│   ├── repository/
│   │   ├── __init__.py
│   │   ├── base.py (Base CRUD methods)
│   │   ├── conversation_repository.py (Conversation operations)
│   │   ├── message_repository.py (Message operations)
│   │   └── query_builder.py (Common query patterns)
│   ├── migrations/
│   │   ├── __init__.py
│   │   ├── versions/ (Alembic migration files)
│   │   ├── env.py (Alembic environment setup)
│   │   └── script.py.mako (Alembic template)
│   ├── exceptions.py (Custom exceptions: DBConnectionError, ValidationError, etc.)
│   └── utils.py (Helper functions: generate_id, timestamp_utils, etc.)
```

---

## 2. ARCHITECTURE OVERVIEW & DATA FLOW

### 2.1 High-Level Layer Structure

```
┌─────────────────────────────────────────────────────────┐
│ app.py / orchestrator.py                                │
│ (Business logic, logging, error handling, validation)   │
└────────────┬────────────────────────────────────────────┘
             │ 1. Call: db.create_message(...)
             │ 2. Await result
             │ 3. Log the operation (with request_id)
             │
             ▼
┌─────────────────────────────────────────────────────────┐
│ database/ layer                                          │
│ ┌──────────────────────────────────────────────────────┐│
│ │ Repository Layer (conversation_repo, message_repo)   ││
│ │ - Conversation: create, get, list, update, archive  ││
│ │ - Message: create, get_by_conversation, update_count││
│ │ Returns: raw objects (no side effects)               ││
│ └──────┬───────────────────────────────────────────────┘│
│        │                                                 │
│ ┌──────▼───────────────────────────────────────────────┐│
│ │ Session / Context Manager Layer                      ││
│ │ - Database handles transaction management            ││
│ │ - Automatic rollback on error                        ││
│ │ - Auto-close connections to pool                     ││
│ └──────┬───────────────────────────────────────────────┘│
│        │                                                 │
│ ┌──────▼───────────────────────────────────────────────┐│
│ │ SQLAlchemy ORM Layer                                 ││
│ │ - Models (Conversation, Message)                     ││
│ │ - Validation at model level (CHECK constraints)      ││
│ │ - Relationships defined here                         ││
│ └──────┬───────────────────────────────────────────────┘│
│        │                                                 │
│ ┌──────▼───────────────────────────────────────────────┐│
│ │ SQLAlchemy Engine + Connection Pool                  ││
│ │ - Pooling strategy: QueuePool (PostgreSQL)           ││
│ │ - Max pool size: 10, pool timeout: 30s               ││
│ │ - Lazy initialization on first db operation          ││
│ └──────┬───────────────────────────────────────────────┘│
│        │                                                 │
│ ┌──────▼───────────────────────────────────────────────┐│
│ │ Actual Database (SQLite / PostgreSQL)                ││
│ └──────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────┘
```

### 2.2 Data Flow: User Sends Message

```
User sends message in Streamlit UI
    ↓
app.py receives input + extracts request_id, user_id, conversation_id
    ↓
app.py calls: result = db.save_user_message(
    conversation_id=...,
    user_id=...,
    content=...,
    request_id=...  ← Used by orchestrator for tracing
)
    ↓ [DB Layer (PURE - no logging)]
DB creates Message object with: 
    - id = generate_uuid()
    - conversation_id = ...
    - role = 'user'
    - content = ... (validated by Pydantic schema)
    - source = 'user_input' (set by app.py, passed in metadata)
    - request_id = ... (metadata)
    - created_at = NOW()
    ↓
DB opens transaction (context manager)
    UPDATE conversations SET last_message_at=NOW(), message_count += 1
    INSERT INTO messages (...)
    COMMIT
    ↓
DB returns: Message object with all fields populated
    ↓ [Back in app.py]
app.py logs the operation (via logger.log_message_created(...))
app.py passes Message to orchestrator/RAG/eligibility modules
    ↓
[LLM processing...]
    ↓
orchestrator.py prepares assistant response
    ↓
app.py calls: result = db.save_assistant_message(
    conversation_id=...,
    content=...,
    metadata={
        'source': 'llm_generation',
        'tokens': 150,
        'model_name': 'llama3.2:3b',
        'latency_ms': 2500,
        'request_id': ...
    }
)
    ↓ [DB Layer again]
DB creates Message, updates conversation, COMMIT
    ↓ [Back in app.py]
app.py logs the operation
Streamlit UI displays assistant response
```

### 2.3 Data Flow: Fetch Conversation History

```
User opens conversation X in UI
    ↓
app.py calls: messages = db.get_messages_for_conversation(
    conversation_id='conv_001',
    limit=10,
    offset=0
)
    ↓ [DB Layer]
DB opens READ-ONLY session (or implicit read transaction)
DB queries: SELECT * FROM messages WHERE conversation_id = ... 
    ORDER BY created_at ASC LIMIT 10 OFFSET 0
DB returns: list of Message objects
    ↓
DB also queries: conversation = db.get_conversation(id='conv_001')
DB returns: Conversation object with metadata (title, message_count, etc.)
    ↓ [Back in app.py]
app.py assembles context:
    - Last N messages (history)
    - Conversation summary (if exists)
    - User profile / session info
    ↓
app.py passes assembled context to LLM prompt builder
    ↓
[LLM generation continues as in previous flow]
```

---

## 3. CORE ABSTRACTIONS & PATTERNS

### 3.1 Session Manager Pattern (Context Manager)

**Purpose**: Manage database session lifecycle safely, auto-cleanup, transaction handling

**Pseudocode**:
```
class DatabaseSessionManager:
    """
    Context manager for database sessions.
    Handles transaction lifecycle, error handling, auto-cleanup.
    """
    
    __init__(engine):
        store engine (SQLAlchemy engine)
        session_factory = create_session_factory_from_engine(engine)
    
    __enter__():
        // Called when entering 'with db_session:' block
        self.session = session_factory.create_session()
        return self.session
    
    __exit__(exc_type, exc_val, exc_tb):
        // Called when exiting 'with db_session:' block
        
        IF exc_type is not None:
            // Exception occurred in block
            self.session.rollback()  // Undo all changes
            log_error("Transaction rolled back due to error", exception=exc_type)
        ELSE:
            // No exception, commit changes
            self.session.commit()  // Persist changes
        
        self.session.close()  // Return connection to pool
        return False  // Propagate exception if any
    
    // Example usage in repository:
    with DatabaseSessionManager(engine) as session:
        message = Message(...)
        session.add(message)
        // Auto-commit on exit, auto-rollback on error
```

**Why This Pattern**:
- ✅ Automatic cleanup (no forgotten connections)
- ✅ Automatic rollback on error (no partial updates)
- ✅ Automatic commit on success
- ✅ Thread-safe (each thread gets own session)
- ✅ Works with connection pooling (returns connections to pool)

### 3.2 Repository Pattern

**Purpose**: Abstract data access logic, provide clean API for app.py to use

**Key Principle**: Repositories are "data access objects" with no business logic

**Pseudocode**:

```
// Base Repository (common CRUD operations)
class BaseRepository[T]:
    """
    Generic repository for CRUD operations on model T.
    Subclassed by ConversationRepository, MessageRepository, etc.
    """
    
    __init__(model_class, session_manager, engine):
        self.model_class = model_class  // Conversation or Message
        self.session_manager = session_manager  // Context manager
        self.engine = engine
    
    create(data_dict) -> T:
        // Insert a new record
        with self.session_manager as session:
            instance = self.model_class(...)  // Create ORM object from data
            instance.validate()  // Call model's built-in validation
            session.add(instance)
            session.flush()  // Get auto-generated ID
            return instance
    
    get_by_id(id) -> T or None:
        // Fetch single record by ID
        with self.session_manager as session:
            instance = session.query(self.model_class).filter_by(id=id).first()
            return instance
    
    list(filters_dict, limit, offset) -> [T]:
        // Fetch multiple records with filters
        with self.session_manager as session:
            query = session.query(self.model_class)
            FOR each filter_key, filter_value in filters_dict:
                query = query.filter(getattr(self.model_class, filter_key) == filter_value)
            
            query = query.limit(limit).offset(offset)
            return query.all()
    
    update(id, data_dict) -> T:
        // Update a record
        with self.session_manager as session:
            instance = session.query(self.model_class).filter_by(id=id).first()
            IF instance is None:
                raise RecordNotFoundError(...)
            
            FOR each key, value in data_dict:
                setattr(instance, key, value)
            
            session.add(instance)
            return instance
    
    delete(id) -> bool:
        // Note: For audit trail, prefer soft-delete
        with self.session_manager as session:
            instance = session.query(self.model_class).filter_by(id=id).first()
            IF instance is None:
                return False
            session.delete(instance)
            return True


// Conversation Repository (domain-specific queries)
class ConversationRepository(BaseRepository):
    """
    Repository for Conversation model.
    Adds conversation-specific queries on top of base CRUD.
    """
    
    __init__(session_manager, engine):
        super().__init__(Conversation, session_manager, engine)
    
    get_by_user_id(user_id, limit=20, offset=0) -> [Conversation]:
        // Get all conversations for a user
        with self.session_manager as session:
            return (session.query(Conversation)
                    .filter(Conversation.user_id == user_id)
                    .order_by(Conversation.last_message_at DESC)  // Newest first
                    .limit(limit)
                    .offset(offset)
                    .all())
    
    archive(conversation_id) -> Conversation:
        // Soft-delete: mark conversation as archived
        with self.session_manager as session:
            conv = session.query(Conversation).filter_by(id=conversation_id).first()
            IF conv is None:
                raise ConversationNotFoundError(...)
            
            conv.status = 'archived'
            conv.archived_at = NOW()
            session.add(conv)
            return conv
    
    count_messages(conversation_id) -> int:
        // Get message count for a conversation
        with self.session_manager as session:
            return session.query(Message).filter(
                Message.conversation_id == conversation_id
            ).count()


// Message Repository (domain-specific queries)
class MessageRepository(BaseRepository):
    """
    Repository for Message model.
    Adds message-specific queries on top of base CRUD.
    """
    
    __init__(session_manager, engine):
        super().__init__(Message, session_manager, engine)
    
    get_by_conversation(conversation_id, limit=10, offset=0) -> [Message]:
        // Get all messages in a conversation, ordered by created_at
        with self.session_manager as session:
            return (session.query(Message)
                    .filter(Message.conversation_id == conversation_id)
                    .order_by(Message.created_at ASC)
                    .limit(limit)
                    .offset(offset)
                    .all())
    
    get_last_n_messages(conversation_id, n=5) -> [Message]:
        // Get last N messages (for context window in LLM prompt)
        with self.session_manager as session:
            return (session.query(Message)
                    .filter(Message.conversation_id == conversation_id)
                    .order_by(Message.created_at DESC)
                    .limit(n)
                    .all()
                    .reverse())  // Reverse to chronological order
    
    count_by_conversation(conversation_id) -> int:
        // Count messages in a conversation
        with self.session_manager as session:
            return session.query(Message).filter(
                Message.conversation_id == conversation_id
            ).count()
    
    get_by_source(conversation_id, source) -> [Message]:
        // Get messages filtered by source (e.g., 'rag_retrieval')
        with self.session_manager as session:
            return (session.query(Message)
                    .filter(Message.conversation_id == conversation_id,
                            Message.metadata['source'] == source)
                    .order_by(Message.created_at ASC)
                    .all())
```

### 3.3 Models with Validation

**Purpose**: Define data structure, storage, and structural validation (role IN ('user', 'assistant', 'system'))

**Pseudocode**:

```
// Base Model (common properties)
class BaseModel:
    """
    Base model for all tables.
    Includes common properties: id, created_at, updated_at
    """
    
    id: str (PrimaryKey, default=generate_uuid())
    created_at: datetime (default=utcnow(), immutable=true)
    updated_at: datetime (default=utcnow(), auto_update_on_change=true)


// Conversation Model
class Conversation(BaseModel):
    """
    Represents a conversation thread.
    User can have multiple conversations (one per topic).
    """
    
    // Columns
    user_id: str (NotNull, ForeignKey constraints if needed)
    title: str (Optional, max_length=255)
    status: Enum(ACTIVE, ARCHIVED, CLOSED, DELETED)
        -> default=ACTIVE
        -> constraint: only allow these values at DB level
    message_count: int (default=0, auto-updated by trigger/cascade)
    last_message_at: datetime (default=utcnow())
    archived_at: datetime (Optional, set when status=ARCHIVED)
    
    // Relationships (ORM only, not stored columns)
    messages: [Message] (One-to-Many, cascade on delete)
    
    // Virtual properties / methods
    is_active(): bool → return self.status == 'ACTIVE'
    
    // Indexes (for query performance)
    INDEX(user_id, last_message_at DESC)  // Fetch user's conversations
    INDEX(status, created_at)  // Query by status
    UNIQUE(id, user_id)  // Ensure conversation belongs to user


// Message Model
class Message(BaseModel):
    """
    Represents a single message in a conversation.
    Immutable (append-only event log).
    """
    
    // Columns
    conversation_id: str (NotNull, ForeignKey(Conversation.id))
    role: Enum(user, assistant, system)
        -> constraint: only allow these values (CHECK constraint)
    content: text (NotNull)
    metadata: JSON (Optional)
        → Contains: request_id, source, tokens, model_name, latency_ms, temperature, etc.
    
    // Relationships
    conversation: Conversation (Many-to-One)
    
    // Virtual properties
    request_id: str → return metadata.get('request_id')
    source: str → return metadata.get('source')
    tokens: int → return metadata.get('tokens')
    
    // Immutability (no update allowed)
    __setattr__(name, value):
        IF name != 'id' and record_already_exists():
            raise ImmutableError("Messages cannot be updated")
    
    // Indexes
    INDEX(conversation_id, created_at ASC)  // Fetch messages in order
    INDEX(role, created_at)  // Query by role type
```

---

## 4. CONNECTION POOLING STRATEGY

### 4.1 SQLAlchemy Engine + Pool Configuration

**Purpose**: Reuse database connections efficiently across concurrent requests

**Pseudocode**:

```
class DatabaseEngine:
    """
    Initializes SQLAlchemy engine with connection pooling.
    Lazy initialization: engine created on first use, not at import.
    """
    
    _engine = None  // Singleton pattern
    _initialized = False
    
    @staticmethod
    initialize_engine(database_url, pool_size=10, echo=False):
        """
        Initialize the database engine once.
        Called from app startup or on first db operation.
        
        Args:
            database_url: PostgreSQL connection string
                Format: postgresql://user:password@localhost/dbname
            pool_size: Max connections to keep open (default 10)
            echo: Log all SQL queries (true in dev, false in prod)
        """
        
        IF DatabaseEngine._initialized:
            return DatabaseEngine._engine
        
        // Create SQLAlchemy engine with QueuePool
        pool_config = {
            'poolclass': QueuePool,  // FIFO queue for connection allocation
            'pool_size': pool_size,  // Pre-create N connections
            'max_overflow': 5,  // Allow 5 more connections if needed
            'pool_timeout': 30,  // Wait 30s for connection, then fail
            'pool_recycle': 3600,  // Recycle connections every 1 hour (prevent stale)
            'pool_pre_ping': True,  // Test connection before use (detect dead connections)
            'echo': echo  // Log SQL in debug mode
        }
        
        DatabaseEngine._engine = create_engine(
            database_url,
            **pool_config
        )
        
        DatabaseEngine._initialized = True
        return DatabaseEngine._engine
    
    @staticmethod
    get_engine():
        """Get the initialized engine. Raises error if not initialized."""
        IF DatabaseEngine._engine is None:
            raise RuntimeError("Database engine not initialized. Call initialize_engine() first.")
        return DatabaseEngine._engine
    
    @staticmethod
    close_engine():
        """Gracefully close all connections (call at app shutdown)."""
        IF DatabaseEngine._engine:
            DatabaseEngine._engine.dispose()  // Close all pooled connections
            DatabaseEngine._initialized = False


// Usage in app.py startup:
IF running_locally:
    db_url = "sqlite:///./chat_history.db"
ELSE:
    db_url = get_from_config('DATABASE_URL')  // PostgreSQL URL from env

DatabaseEngine.initialize_engine(
    db_url,
    pool_size=10 if production else 5,
    echo=debug_mode
)
```

### 4.2 Connection Pooling Behavior with Concurrency

```
Scenario: 3 concurrent users sending messages simultaneously

Timeline:
│
├─ User1 sends message
│  └─ DB Thread 1 acquires connection #1 from pool (9 available)
│     └─ Executes: INSERT message, UPDATE conversation
│     └─ COMMIT
│     └─ Releases connection #1 back to pool (10 available)
│
├─ User2 sends message (while User1 still processing)
│  └─ DB Thread 2 acquires connection #2 from pool (9 available)
│     └─ Executes: INSERT message, UPDATE conversation
│     └─ COMMIT
│     └─ Releases connection #2 back to pool
│
└─ User3 sends message (while User1, User2 still processing)
   └─ DB Thread 3 acquires connection #3 from pool (8 available)
      └─ Executes: INSERT message, UPDATE conversation
      └─ COMMIT
      └─ Releases connection #3 back to pool

SQLite WARNING:
  SQLite is not recommended for concurrent writes.
  Max 1 write at a time (SQLite locks entire file).
  Use PostgreSQL instead for true concurrency.

PostgreSQL handles:
  Row-level locking (not table-wide)
  Multiple concurrent writes to different rows
  All 3 connections running simultaneously
```

---

## 5. ERROR HANDLING & RETRY STRATEGY

### 5.1 Hybrid Approach: Fail Fast on Reads, Retry on Writes

**Pseudocode**:

```
// In app.py orchestrator:

FUNCTION handle_user_message(user_input, conversation_id, request_id):
    
    TRY:
        // 1. READ: Fetch conversation (fail fast if fails)
        conversation = db.get_conversation(conversation_id)
        IF conversation is None:
            raise ConversationNotFoundError(conversation_id)
        
        // 2. WRITE: Save user message (retry on failure)
        message = retry_with_backoff(
            fn=db.save_user_message,
            args={
                'conversation_id': conversation_id,
                'role': 'user',
                'content': user_input,
                'metadata': {
                    'source': 'user_input',
                    'request_id': request_id
                }
            },
            max_retries=3,
            backoff_ms=100  // Start with 100ms, exponential increase
        )
        
        // 3. Log the save (no retry, if logging fails it's non-critical)
        TRY:
            logger.log_message_created(message, request_id)
        CATCH logging_error:
            logger.warn("Failed to log message, but operation succeeded")
        
        // 4. Process message through LLM
        assistant_response = orchestrator.process(message, conversation)
        
        // 5. WRITE: Save assistant message (retry on failure)
        response_message = retry_with_backoff(
            fn=db.save_assistant_message,
            args={
                'conversation_id': conversation_id,
                'content': assistant_response['text'],
                'metadata': {
                    'source': 'llm_generation',
                    'tokens': assistant_response['token_count'],
                    'model_name': assistant_response['model'],
                    'latency_ms': assistant_response['latency'],
                    'request_id': request_id
                }
            },
            max_retries=3,
            backoff_ms=100
        )
        
        return response_message
    
    CATCH DBConnectionError:
        // Database unreachable - return error to user
        logger.error("Database unavailable", request_id=request_id)
        raise SystemUnavailableError("Chat system temporarily unavailable")
    
    CATCH ConversationNotFoundError:
        // Data integrity error - return error immediately
        logger.error("Conversation not found", request_id=request_id)
        raise InvalidConversationError("Conversation not found")


// Utility: Retry logic with exponential backoff
FUNCTION retry_with_backoff(fn, args, max_retries=3, backoff_ms=100):
    """
    Retry a function on failure with exponential backoff.
    Used for write operations that might fail due to locks/timeouts.
    """
    
    attempt = 0
    last_error = None
    
    WHILE attempt < max_retries:
        TRY:
            return fn(**args)  // Call the function
        
        CATCH OperationalError as e:  // SQLAlchemy operational error
            last_error = e
            
            // Check if error is retriable
            IF is_retriable_error(e):
                wait_ms = backoff_ms * (2 ** attempt)  // 100, 200, 400 ms
                sleep(wait_ms / 1000)
                attempt += 1
            ELSE:
                raise e  // Non-retriable error, fail immediately
        
        CATCH Exception as e:
            raise e  // Non-DB error, fail immediately
    
    // Max retries exceeded
    raise DBRetryExhaustedError(..., last_error)


// Function: Determine if error is retriable
FUNCTION is_retriable_error(error):
    """
    Determine if a database error is worth retrying.
    Retriable: Connection timeout, lock timeout, deadlock
    Non-retriable: Foreign key violation, constraint error, auth error
    """
    
    error_message = str(error).lower()
    
    RETRIABLE_KEYWORDS = [
        'timeout',
        'deadlock',
        'lock wait timeout',
        'connection reset',
        'connection refused'
    ]
    
    FOR keyword in RETRIABLE_KEYWORDS:
        IF keyword in error_message:
            return True
    
    RETURN False
```

### 5.2 Error Types & Handling

```
DB-Layer Exceptions (in database/exceptions.py):

├─ DatabaseError (base class)
│  ├─ ConnectionError
│  │  ├─ DBConnectionTimeoutError (can retry)
│  │  └─ DBConnectionRefusedError (can retry)
│  ├─ OperationalError
│  │  ├─ DBLockTimeoutError (can retry)
│  │  └─ DBDeadlockError (can retry)
│  ├─ IntegrityError (cannot retry)
│  │  ├─ ForeignKeyError
│  │  ├─ UniqueConstraintError
│  │  └─ NotNullError
│  ├─ ValidationError (cannot retry)
│  │  ├─ InvalidRoleError ("role must be 'user', 'assistant', 'system'")
│  │  └─ InvalidStatusError
│  └─ NotFoundError (cannot retry)
│     ├─ ConversationNotFoundError
│     └─ MessageNotFoundError

App-Layer Exception Handling (in app.py):

├─ RETRIABLE (use retry_with_backoff):
│  ├─ DatabaseError.ConnectionError
│  ├─ DatabaseError.OperationalError
│  └─ [Retry up to 3 times with exponential backoff]
│
├─ NON-RETRIABLE (fail immediately):
│  ├─ DatabaseError.IntegrityError
│  │  └─ Return HTTP 400 to user (data validation failed)
│  ├─ DatabaseError.ValidationError
│  │  └─ Return HTTP 400 to user (invalid input)
│  ├─ DatabaseError.NotFoundError
│  │  └─ Return HTTP 404 to user (record not found)
│
└─ UNHANDLED:
   └─ Log error, return HTTP 500 to user
```

---

## 6. CORE API: WHAT app.py CALLS

### 6.1 Database Manager Class (Facade Pattern)

**Purpose**: Single entry point for app.py to interact with database

**Pseudocode**:

```
class DatabaseManager:
    """
    Facade class providing clean API for app.py.
    Hides complexity of repositories, sessions, and pooling.
    
    This is what app.py imports and uses.
    Lazy initialization: DB not initialized until first call.
    """
    
    _engine = None
    _conversation_repo = None
    _message_repo = None
    _session_manager = None
    
    @staticmethod
    initialize(database_url, debug=False):
        """
        Initialize database (called at app startup).
        """
        DatabaseEngine.initialize_engine(database_url, pool_size=10, echo=debug)
        
        engine = DatabaseEngine.get_engine()
        DatabaseManager._engine = engine
        DatabaseManager._session_manager = DatabaseSessionManager(engine)
        DatabaseManager._conversation_repo = ConversationRepository(
            DatabaseManager._session_manager,
            engine
        )
        DatabaseManager._message_repo = MessageRepository(
            DatabaseManager._session_manager,
            engine
        )
    
    // ==================== CONVERSATION OPERATIONS ====================
    
    @staticmethod
    create_conversation(user_id, title=None):
        """
        Create a new conversation for a user.
        
        Args:
            user_id: Which user owns this conversation
            title: Optional conversation title
        
        Returns:
            Conversation object with id, created_at, etc.
        
        Raises:
            DatabaseError on failure
        """
        conversation_data = {
            'user_id': user_id,
            'title': title,
            'status': 'ACTIVE'
        }
        return DatabaseManager._conversation_repo.create(conversation_data)
    
    @staticmethod
    get_conversation(conversation_id):
        """
        Fetch a single conversation by ID.
        
        Args:
            conversation_id: UUID of conversation
        
        Returns:
            Conversation object or None if not found
        """
        return DatabaseManager._conversation_repo.get_by_id(conversation_id)
    
    @staticmethod
    list_conversations(user_id, limit=20, offset=0):
        """
        List all conversations for a user (paginated).
        
        Args:
            user_id: Whose conversations to fetch
            limit: Max number to return (default 20)
            offset: Pagination offset (for page 2, offset=20)
        
        Returns:
            List of Conversation objects, sorted newest first
        """
        return DatabaseManager._conversation_repo.get_by_user_id(
            user_id, limit=limit, offset=offset
        )
    
    @staticmethod
    archive_conversation(conversation_id):
        """
        Soft-delete a conversation (mark as archived).
        (Does not delete messages, just changes status)
        
        Args:
            conversation_id: UUID to archive
        
        Returns:
            Updated Conversation object
        
        Raises:
            ConversationNotFoundError if not found
        """
        return DatabaseManager._conversation_repo.archive(conversation_id)
    
    // ==================== MESSAGE OPERATIONS ====================
    
    @staticmethod
    save_user_message(conversation_id, content, request_id, metadata=None):
        """
        Save a message from the user.
        Auto-updates conversation's last_message_at and message_count.
        
        Args:
            conversation_id: UUID of conversation
            content: Message text
            request_id: UUID for tracing (from orchestrator)
            metadata: Optional dict with 'source', etc.
        
        Returns:
            Message object with id, created_at, etc.
        
        Raises:
            ConversationNotFoundError if conversation doesn't exist
            ValidationError if content is invalid
            DatabaseError on connection/transaction failure
        """
        message_data = {
            'conversation_id': conversation_id,
            'role': 'user',
            'content': content,
            'metadata': metadata or {
                'request_id': request_id,
                'source': 'user_input'
            }
        }
        return DatabaseManager._message_repo.create(message_data)
    
    @staticmethod
    save_assistant_message(conversation_id, content, request_id, metadata=None):
        """
        Save a message from the assistant (LLM).
        Auto-updates conversation's last_message_at and message_count.
        
        Args:
            conversation_id: UUID of conversation
            content: Assistant response text
            request_id: UUID for tracing
            metadata: Dict with 'tokens', 'model_name', 'latency_ms', etc.
        
        Returns:
            Message object
        
        Raises:
            ConversationNotFoundError if conversation doesn't exist
            DatabaseError on failure
        """
        message_data = {
            'conversation_id': conversation_id,
            'role': 'assistant',
            'content': content,
            'metadata': metadata or {
                'request_id': request_id,
                'source': 'llm_generation'
            }
        }
        return DatabaseManager._message_repo.create(message_data)
    
    @staticmethod
    save_system_message(conversation_id, content, request_id, metadata=None):
        """
        Save a system message (e.g., 'Eligibility check completed').
        
        Args:
            conversation_id: UUID of conversation
            content: System message text
            request_id: UUID for tracing
            metadata: Optional metadata
        
        Returns:
            Message object
        """
        message_data = {
            'conversation_id': conversation_id,
            'role': 'system',
            'content': content,
            'metadata': metadata or {
                'request_id': request_id,
                'source': 'system'
            }
        }
        return DatabaseManager._message_repo.create(message_data)
    
    @staticmethod
    get_messages(conversation_id, limit=10, offset=0):
        """
        Fetch messages from a conversation (paginated, chronological order).
        
        Args:
            conversation_id: UUID of conversation
            limit: Max messages to return (default 10)
            offset: Pagination offset
        
        Returns:
            List of Message objects, oldest first
        """
        return DatabaseManager._message_repo.get_by_conversation(
            conversation_id, limit=limit, offset=offset
        )
    
    @staticmethod
    get_last_n_messages(conversation_id, n=5):
        """
        Fetch the last N messages (for LLM context window).
        
        Args:
            conversation_id: UUID of conversation
            n: Number of messages (default 5)
        
        Returns:
            List of Message objects, oldest first (but last N)
            
        Use Case:
            messages = db.get_last_n_messages('conv_001', n=10)
            → Pass these to LLM prompt builder for context
        """
        return DatabaseManager._message_repo.get_last_n_messages(
            conversation_id, n=n
        )
    
    @staticmethod
    get_message_count(conversation_id):
        """
        Count total messages in a conversation.
        
        Args:
            conversation_id: UUID of conversation
        
        Returns:
            Integer count
        """
        return DatabaseManager._message_repo.count_by_conversation(conversation_id)
    
    // ==================== LIFECYCLE OPERATIONS ====================
    
    @staticmethod
    shutdown():
        """
        Gracefully close all database connections.
        Called at app shutdown (e.g., Streamlit closing).
        """
        DatabaseEngine.close_engine()
```

### 6.2 Usage Pattern in app.py

```
// At app startup:
from database import DatabaseManager

@streamlit.cache_resource  // Singleton (one instance per process)
def initialize_db():
    db_url = get_from_config('DATABASE_URL')
    DatabaseManager.initialize(db_url, debug=False)
    return DatabaseManager

db = initialize_db()


// At any endpoint:
def chat_endpoint():
    user_id = st.session_state['user_id']
    conversation_id = st.session_state['conversation_id']
    user_input = st.text_input("Your message:")
    
    IF user_input:
        request_id = generate_uuid()
        
        // 1. Save user message to DB
        try:
            message = db.save_user_message(
                conversation_id=conversation_id,
                content=user_input,
                request_id=request_id
            )
            logger.log_message_created(message, request_id)  // Log, don't fail
        
        except ConversationNotFoundError:
            st.error("Conversation not found")
            return
        
        except DatabaseError as e:
            st.error("Database error, please try again")
            logger.error("Failed to save user message", error=e, request_id=request_id)
            return
        
        // 2. Process message through LLM
        try:
            assistant_text = orchestrator.process(message, conversation_id)
        
        except Exception as e:
            st.error("Failed to process message")
            logger.error("LLM processing failed", error=e, request_id=request_id)
            return
        
        // 3. Save assistant message to DB
        try:
            response_msg = db.save_assistant_message(
                conversation_id=conversation_id,
                content=assistant_text,
                request_id=request_id,
                metadata={
                    'tokens': 120,
                    'model_name': 'llama3.2:3b',
                    'latency_ms': 2500,
                    'source': 'llm_generation'
                }
            )
            logger.log_message_created(response_msg, request_id)
        
        except DatabaseError as e:
            st.error("Failed to save response")
            logger.error("Failed to save assistant message", error=e, request_id=request_id)
            return
        
        // 4. Display response
        st.write(response_msg.content)


// At app shutdown:
import atexit
atexit.register(lambda: DatabaseManager.shutdown())
```

---

## 7. INITIALIZATION FLOW: LAZY LOADING

**Purpose**: Defer database initialization until actually needed, keep app.py clean

**Pseudocode**:

```
Timeline: Streamlit app startup → First user interaction

1. Streamlit app starts
   └─ Modules imported (database/__init__.py, models, etc.)
      └─ ✓ Classes defined, no connections made yet
   
2. app.py runs
   └─ Calls: db = initialize_db() (via @streamlit.cache_resource)
      └─ Calls: DatabaseManager.initialize(database_url, debug=False)
         └─ Calls: DatabaseEngine.initialize_engine(...)
            └─ Creates SQLAlchemy engine
            └─ Creates connection pool (but doesn't create connections yet)
            └─ Creates session factory
         └─ Creates repository instances
      └─ Sets DatabaseManager._engine, _session_manager, _repos
   
3. Streamlit UI loads
   └─ User enters message, clicks send
   
4. First database operation (save_user_message)
   └─ Calls: DatabaseManager._message_repo.create(message_data)
      └─ Opens context manager: WITH session_manager
         └─ Tries to get connection from pool
            └─ Pool is empty, so creates first connection to DB
            └─ Connection established: connected!
         └─ Executes: INSERT INTO messages (...)
         └─ Executes: UPDATE conversations SET last_message_at=NOW(), message_count += 1
         └─ COMMIT
         └─ Context manager __exit__ returns connection to pool
   
5. Subsequent operations reuse pooled connections
   └─ Connection #1 available in pool
   └─ Next operation takes connection #1
   └─ Executes query
   └─ Returns connection to pool
   
6. Streamlit app closes
   └─ atexit.register() calls DatabaseManager.shutdown()
      └─ Calls: DatabaseEngine.close_engine()
         └─ Calls: engine.dispose()
            └─ Closes all pooled connections
            └─ Clears pool
      └─ Sets _initialized = False

Benefit: No database I/O until actually needed.
```

---

## 8. CONCURRENCY & TRANSACTION HANDLING

### 8.1 Transaction Isolation During Concurrent Message Saves

```
Scenario: Two users sending messages to same conversation simultaneously

Timeline:
│
├─ User1 sends message at T=0ms
│  └─ Acquires connection #1
│     └─ BEGIN TRANSACTION
│     └─ INSERT into messages (id=msg_001, conversation_id=conv_001, role=user, ...)
│     └─ UPDATE conversations SET message_count = message_count + 1 WHERE id=conv_001
│     │  → PostgreSQL increments atomically (no lost updates)
│     └─ COMMIT (T=50ms)
│     └─ Releases connection #1 back to pool
│
├─ User2 sends message at T=10ms (while User1 still in transaction)
│  └─ Acquires connection #2
│     └─ BEGIN TRANSACTION  
│     └─ INSERT into messages (id=msg_002, conversation_id=conv_001, role=user, ...)
│     └─ UPDATE conversations SET message_count = message_count + 1 WHERE id=conv_001
│     │  → PostgreSQL either:
│     │     a) Waits for User1's transaction to commit, then applies to new value
│     │     b) Uses row versioning to avoid lock (PostgreSQL MVCC)
│     └─ COMMIT (T=60ms)
│     └─ Releases connection #2 back to pool
│
Result: Both messages saved, message_count = 2 (no lost updates)
    │
    ▼ (If using SQLite instead)
    
    ├─ User1 sends message at T=0ms
    │  └─ SQLite acquires WRITE lock on entire database file
    │     └─ Only 1 writer allowed at a time
    │     └─ User2 blocked until User1 finishes
    │
    └─ User2 sends message at T=10ms
       └─ Waits for User1's lock to release
          └─ At T=50ms, User1 releases lock
          └─ User2 acquires WRITE lock
          └─ User2 writes
          └─ User2 releases lock
    
    ⚠️  SQLite is NOT suitable for concurrent writes
        → Recommend PostgreSQL for production
```

### 8.2 Handling Concurrent Reads (No Issue)

```
Scenario: Multiple users reading conversation history simultaneously
(No locks needed for reads, everyone can read at same time)

User1: GET messages for conv_001 (T=0ms)
User2: GET messages for conv_001 (T=5ms)
User3: GET messages for conv_001 (T=10ms)

Database:
├─ Connection #1: SELECT * FROM messages WHERE conversation_id=conv_001 (reads concurrently)
├─ Connection #2: SELECT * FROM messages WHERE conversation_id=conv_001 (reads concurrently)
└─ Connection #3: SELECT * FROM messages WHERE conversation_id=conv_001 (reads concurrently)

✓ All three queries execute simultaneously
✓ No blocking
✓ Each gets consistent snapshot (MVCC in PostgreSQL)
```

### 8.3 Deadlock Prevention Strategy

```
Deadlock scenario (what to avoid):

Transaction A:
  Lock on conversation_001
  → Try to lock message_001

Transaction B:
  Lock on message_001
  → Try to lock conversation_001

DEADLOCK! Each waiting for the other.

Prevention Strategy:

In our design:
  1. Always lock in same order
     → In save_user_message:
        - First INSERT message (auto-locks this row)
        - Then UPDATE conversation (locks conversation row)
  
  2. Both transactions do INSERT first, then UPDATE
     → Consistent ordering prevents deadlock
  
  3. Use context manager to ensure COMMIT/ROLLBACK
     → Releases locks immediately

Retry strategy handles rare deadlock events:
  IF deadlock occurs:
    ROLLBACK (automatic)
    Wait 100ms
    Retry (up to 3 times)
```

---

## 9. MIGRATION STRATEGY (Schema Changes)

### 9.1 Alembic for Database Migrations

**Purpose**: Version-control schema changes, deploy safely, enable rollbacks

**Pseudocode**:

```
Initial Setup:
  1. Create migrations directory (database/migrations/)
  2. Initialize Alembic: alembic init database/migrations
  3. Configure alembic.ini: sqlalchemy.url = DATABASE_URL from env
  4. Create base migration: alembic revision --autogenerate -m "Initial schema"

Directory structure:
database/migrations/
├── alembic.ini
├── env.py (Alembic environment setup)
├── script.py.mako (Migration template)
└── versions/
    ├── 001_initial_schema.py
    ├── 002_add_metadata_column.py
    └── 003_add_soft_delete_fields.py

Each migration file contains:

def upgrade():
    """
    Apply schema change (UP).
    Called when migrating forward.
    """
    
    // Example: Add new column to messages
    op.add_column('messages', sa.Column('metadata', sa.JSON, nullable=True))
    
    // Example: Create new table
    op.create_table(
        'conversation_summaries',
        sa.Column('conversation_id', sa.String(36), nullable=False),
        sa.Column('summary_text', sa.Text, nullable=False),
        sa.Column('created_at', sa.DateTime, nullable=False),
        sa.ForeignKeyConstraint(['conversation_id'], ['conversations.id'])
    )

def downgrade():
    """
    Undo schema change (DOWN).
    Called when rolling back.
    """
    
    // Example: Drop column
    op.drop_column('messages', 'metadata')
    
    // Example: Drop table
    op.drop_table('conversation_summaries')

Running migrations:

// At app startup, before any queries:
app.py:
    alembic.command.upgrade(config, "head")  // Upgrade to latest version

// When schema changes needed:
Developer:
    1. Modify models (conversation.py, message.py)
    2. Generate migration: alembic revision --autogenerate -m "Add field X"
    3. Review generated migration (database/migrations/versions/...)
    4. Run: alembic upgrade head (in dev environment)
    5. Commit migration to git
    6. Deploy to production
       → Prod: alembic upgrade head (automatic at startup)
       → Old schema → New schema (zero downtime if possible)

Rollback if needed:
    alembic downgrade -1  // Go back one version
    OR
    alembic downgrade 001  // Go to specific version
```

---

## 10. INTEGRATION WITH EXISTING SYSTEM

### 10.1 How Database Fits Into app.py / orchestrator.py

```
Current Flow (before DB):
    User input (Streamlit) 
    → app.py 
    → orchestrator.process() 
    → RAG + Eligibility modules
    → Response 
    → Display in Streamlit

New Flow (with DB):

    User input (Streamlit)
    ↓
    app.py:
    ├─ Request ID generated: request_id = generate_uuid()
    ├─ Extract: user_id, conversation_id, timestamp
    │
    ├─ SAVE: db.save_user_message(
    │    conversation_id=conv_id,
    │    content=user_input,
    │    request_id=request_id
    │ )
    │
    ├─ LOG: logger.log_message_created(message, request_id)
    │
    ├─ Orchestrator processes:
    │  orchestrator.process(
    │      message=message,
    │      conversation_id=conv_id,
    │      request_id=request_id
    │  )
    │
    ├─ Orchestrator calls RAG, eligibility:
    │  ├─ rag.query_data(user_input) → [docs1, docs2, ...]
    │  └─ eligibility.check(...) → {status: ..., reasons: ...}
    │
    ├─ Orchestrator builds LLM prompt using:
    │  ├─ db.get_last_n_messages(conv_id, n=5)  // Context!
    │  ├─ Message from RAG docs
    │  └─ Eligibility check results
    │
    ├─ LLM generates response
    │
    ├─ SAVE: db.save_assistant_message(
    │    conversation_id=conv_id,
    │    content=response,
    │    request_id=request_id,
    │    metadata={
    │        'tokens': ...,
    │        'model': 'llama3.2:3b',
    │        'latency_ms': ...,
    │        'source': 'llm_generation'
    │    }
    │ )
    │
    ├─ LOG: logger.log_message_created(response_msg, request_id)
    │
    └─ Display: Streamlit shows response

Key Changes to orchestrator:
    • Accept message object from app.py (not just text)
    • Request context (conversation, user, request_id)
    • Have access to db.get_last_n_messages() for building prompt
    • Return response with metadata (tokens, latency)

Key Changes to app.py:
    • Initialize db at startup
    • Add request_id generation
    • Call db functions before/after orchestrator
    • Handle DB errors (retry on writes, fail on reads)
    • Log all message operations
```

### 10.2 Message Lifecycle Diagram

```
Milestone Events:

Message → Request ID → Logger Request ID
    ↓
[1] User creates message in Streamlit UI
    ↓
[2] app.py generates request_id
    ↓
[3] app.py calls: db.save_user_message(request_id=request_id)
    ↓
[4] Database inserts message with created_at timestamp
    ↓
[5] app.py logs: logger.log_message_created(message, request_id)
    │   → This log entry also has request_id for tracing
    ↓
[6] orchestrator.process(message, request_id) processes message
    ├─ RAG queries documents
    ├─ Eligibility system checks accounts
    └─ Generates assistant response
    ↓
[7] app.py calls: db.save_assistant_message(request_id=request_id)
    ↓
[8] Database inserts response message with created_at timestamp
    ↓
[9] app.py logs: logger.log_message_created(response_msg, request_id)
    ↓
[10] Streamlit displays response

Tracing: All events (logs, messages, eligibility checks) linked by request_id
    → Can query logs: WHERE request_id = 'req_123'
    → Can query messages: WHERE metadata->>'request_id' = 'req_123'
    → Creates complete audit trail
```

---

## 11. TESTING STRATEGY (Pseudocode)

### 11.1 Unit Tests for Repository

```
// tests/test_conversation_repository.py

FUNCTION test_create_conversation():
    """Test creating a new conversation"""
    
    repo = ConversationRepository(session_manager, engine)
    conv = repo.create({
        'user_id': 'user_001',
        'title': 'Test conversation'
    })
    
    ASSERT conv.id is not None
    ASSERT conv.user_id == 'user_001'
    ASSERT conv.status == 'ACTIVE'
    ASSERT conv.created_at is not None


FUNCTION test_get_conversation():
    """Test fetching a conversation by ID"""
    
    repo = ConversationRepository(session_manager, engine)
    conv1 = repo.create({'user_id': 'user_001', 'title': 'Conv 1'})
    
    conv2 = repo.get_by_id(conv1.id)
    
    ASSERT conv2.id == conv1.id
    ASSERT conv2.title == 'Conv 1'


FUNCTION test_list_conversations_paginated():
    """Test fetching user's conversations with pagination"""
    
    repo = ConversationRepository(session_manager, engine)
    
    // Create 5 conversations
    FOR i in range(5):
        repo.create({'user_id': 'user_001', 'title': f'Conv {i}'})
    
    // Fetch first page (limit=2)
    page1 = repo.get_by_user_id('user_001', limit=2, offset=0)
    ASSERT len(page1) == 2
    
    // Fetch second page
    page2 = repo.get_by_user_id('user_001', limit=2, offset=2)
    ASSERT len(page2) == 2
    
    // Fetch all
    all_convs = repo.get_by_user_id('user_001', limit=100, offset=0)
    ASSERT len(all_convs) == 5


FUNCTION test_archive_conversation():
    """Test soft-deleting (archiving) a conversation"""
    
    repo = ConversationRepository(session_manager, engine)
    conv = repo.create({'user_id': 'user_001', 'title': 'Conv 1'})
    
    archived = repo.archive(conv.id)
    
    ASSERT archived.status == 'ARCHIVED'
    ASSERT archived.archived_at is not None
    
    // Verify it's still in DB with status=ARCHIVED
    fetched = repo.get_by_id(conv.id)
    ASSERT fetched.status == 'ARCHIVED'
```

### 11.2 Integration Tests (Full Message Flow)

```
FUNCTION test_message_flow_updates_conversation_metadata():
    """
    Test that saving messages auto-updates conversation's
    last_message_at and message_count
    """
    
    db = DatabaseManager
    db.initialize('sqlite:///test.db')
    
    // Create conversation
    conv = db.create_conversation('user_001', title='Test Conv')
    initial_count = conv.message_count  // Should be 0
    
    // Save user message
    msg1 = db.save_user_message(
        conversation_id=conv.id,
        content='Hello',
        request_id='req_001'
    )
    
    // Fetch conversation again
    conv_updated = db.get_conversation(conv.id)
    
    ASSERT conv_updated.message_count == 1
    ASSERT conv_updated.last_message_at == msg1.created_at
    
    // Save assistant message
    msg2 = db.save_assistant_message(
        conversation_id=conv.id,
        content='Hi there!',
        request_id='req_001'
    )
    
    // Fetch again
    conv_final = db.get_conversation(conv.id)
    
    ASSERT conv_final.message_count == 2
    ASSERT conv_final.last_message_at == msg2.created_at


FUNCTION test_get_last_n_messages_returns_correct_order():
    """
    Test that last N messages are returned in chronological order
    """
    
    db = DatabaseManager
    conv = db.create_conversation('user_001')
    
    // Insert 5 messages
    FOR i in range(5):
        db.save_user_message(conv.id, f'Message {i}', f'req_{i}')
    
    // Get last 3
    last_3 = db.get_last_n_messages(conv.id, n=3)
    
    ASSERT len(last_3) == 3
    // Should be messages 2, 3, 4 in that order (oldest to newest)
    ASSERT last_3[0].content == 'Message 2'
    ASSERT last_3[1].content == 'Message 3'
    ASSERT last_3[2].content == 'Message 4'
```

---

## 12. NEXT STEPS TO IMPLEMENT

```
Phase 1: Foundation
  [ ] 1. Create folder structure (database/)
  [ ] 2. Write base models (base.py) with SQLAlchemy declarative base
  [ ] 3. Write Conversation and Message models (conversation.py, message.py)
  [ ] 4. Write exceptions (exceptions.py)
  [ ] 5. Write database engine/pooling setup (core/engine.py)
  [ ] 6. Write session manager / context managers (core/session.py)

Phase 2: Repositories
  [ ] 7. Write BaseRepository (repository/base.py)
  [ ] 8. Write ConversationRepository (repository/conversation_repository.py)
  [ ] 9. Write MessageRepository (repository/message_repository.py)
  [ ] 10. Write DatabaseManager facade (database/__init__.py)

Phase 3: Integration
  [ ] 11. Update app.py: Initialize db at startup, call db functions
  [ ] 12. Update orchestrator.py: Accept message object, use db for context
  [ ] 13. Implement retry logic in app.py for write failures
  [ ] 14. Implement error handling: map DB errors to user-friendly messages

Phase 4: Testing
  [ ] 15. Write unit tests for repositories
  [ ] 16. Write integration tests for full message flow
  [ ] 17. Load test: 10 concurrent users, 100 messages each
  [ ] 18. Test database recovery (kill and restart)

Phase 5: Migrations (if using PostgreSQL)
  [ ] 19. Set up Alembic migration framework
  [ ] 20. Create initial schema migration
  [ ] 21. Document migration process for team

Phase 6: Monitoring
  [ ] 22. Add logging for all DB operations (latency, errors)
  [ ] 23. Add metrics: message insert latency, connection pool usage
  [ ] 24. Create dashboard or alerts for DB health
```

---

## 13. SCHEMA DOCUMENTATION (for reference)

See [SCHEMA.md](SCHEMA.md) for full SQL DDL and ER diagram.

**Quick Reference**:

```
conversations
├── id (UUID, PK)
├── user_id (TEXT)
├── title (TEXT)
├── status (ENUM: ACTIVE, ARCHIVED, CLOSED, DELETED)
├── message_count (INT)
├── created_at (DATETIME)
├── last_message_at (DATETIME)
└── archived_at (DATETIME, nullable)

messages
├── id (UUID, PK)
├── conversation_id (UUID, FK → conversations.id)
├── role (ENUM: user, assistant, system)
├── content (TEXT)
├── metadata (JSON)
├── created_at (DATETIME)
└── [immutable - no updates after insert]
```

---

## 14. KEY DESIGN PRINCIPLES SUMMARY

1. **DB Layer is Pure**: No logging, business logic, or side effects. Just CRUD operations.

2. **app.py Owns Logging**: All logging happens in orchestrator/app.py after DB calls.

3. **Context Managers for Safety**: Automatic transaction management, rollback on error, cleanup.

4. **Retry on Writes, Fail-Fast on Reads**: Writes (INSERT/UPDATE) can be retried; reads fail immediately.

5. **Repository Pattern**: Clean API for app.py; all queries centralized, easy to change.

6. **ORM + Connection Pooling**: SQLAlchemy handles complexity; pooling reuses connections.

7. **Lazy Initialization**: DB doesn't start until first use; keeps startup fast.

8. **Request ID Tracing**: Every message/log carries request_id for end-to-end tracing.

9. **Audit Trail**: Soft-delete, timestamps, immutable messages = full history.

10. **Design for Concurrency**: Even though MVP is single-user, architecture supports multi-user.

---

**End of Implementation Guide**

This document provides all the logic, architecture, and pseudocode needed to implement the database layer. No actual Python code here—just concepts and patterns ready for coding.
