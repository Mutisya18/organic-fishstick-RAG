# Database & Memory System - Requirements Analysis

**Purpose**: Provide comprehensive analysis and requirements for designing the database and memory system for the chatbot without prescribing implementation.

**Date**: February 6, 2026  
**System**: Organic Fishstick RAG Chatbot  
**Audience**: Internal Staff Support System

---

## 1. SYSTEM OVERVIEW & CONTEXT

### 1.1 System Purpose
- **Primary Use**: Internal staff chatbot to help serve customers better
- **User Base**: Internal banking staff (relation managers, customer service teams)
- **Integration**: Multi-datasource capable (currently: eligibility system, RAG knowledge base)
- **Scope**: Chatbot maintains conversation context, user sessions, and memory between interactions

### 1.2 Current Architecture
```
Frontend → Streamlit Web UI
    ↓
App.py (orchestration)
    ├── RAG System (query_data.py)
    │   ├── Vector DB (Chroma)
    │   ├── Ollama Embeddings (nomic-embed-text)
    │   └── Ollama LLM (llama3.2:3b)
    │
    ├── Eligibility Module (orchestrator.py)
    │   ├── Config Loader
    │   ├── Data Loader
    │   ├── Intent Detector
    │   ├── Account Validator
    │   └── Eligibility Processor
    │
    └── Logging/Session Management
        ├── RAG Logger
        └── Session Manager
```

---

## 2. DATA DOMAINS & ENTITIES

### 2.1 User Domain (Staff)
**Source**: Assumed from SessionManager, passed from authentication layer  
**Properties to Track**:
- User identifier (likely employee ID or email)
- Department/Role
- Permissions/Scope
- Login/Last activity timestamps
- Session tokens/auth info

**Questions for You**:
- How are staff users authenticated? (LDAP, OAuth, Internal SSO?)
- Does staff role determine what data they can see?
- Are there audit requirements (who viewed what customer info)?

### 2.2 Conversation Domain
**Purpose**: Group messages into coherent threads of intent (not 1 user = 1 chat)  
**Properties**:
- Conversation ID (unique identifier)
- User/Staff ID (who initiated)
- Timestamp created
- Timestamp last message
- Conversation title/topic (optional)
- Status (active, archived, closed)
- Conversation metadata (customer_id if applicable, context)

**Why Conversation-Based**:
- Staff member can have multiple conversations: one about customer X's eligibility, another about product questions
- Each conversation has scoped context
- Prevents "context pollution" between different topics
- Enables future features: branching, retries, A/B testing

### 2.3 Message Domain
**Purpose**: Immutable event log of conversation  
**Properties**:
- Message ID (unique)
- Conversation ID (foreign key)
- Role (user, assistant, system)
- Content (raw text)
- Timestamp (ISO 8601 UTC)
- Metadata:
  - Source (chat input, system prompt, eligibility result, RAG retrieval)
  - Token count (for cost tracking)
  - Model name (which LLM generated)
  - Latency (generation time)

**Design Pattern**: Append-only event log (messages never updated, only soft-deleted)

### 2.4 Conversation Summary Domain
**Purpose**: Compressed context for long conversations  
**Properties**:
- Conversation ID (one-to-one with conversations)
- Summary text (2-3 sentences)
- Key entities extracted (customer names, account numbers, products mentioned)
- Timestamp updated
- Version (to track summary evolution)

**Update Frequency**: Every N messages (e.g., every 10 messages) to reduce context window

### 2.5 User Memory Domain (Potential)
**Purpose**: Cross-conversation facts about a staff user  
**Future Use**: "This user always asks about product X" or "Prefers detailed explanations"  
**Properties**:
- User ID
- Memory key (e.g., "prefers_concise_answers")
- Memory value
- Confidence score
- Timestamp last updated

**Note**: This is separate from conversation-specific memory; only add when needed

### 2.6 Eligibility Check Results Domain
**Purpose**: Log eligibility checks performed in conversations  
**Properties**:
- Check ID (unique)
- Conversation ID (which conversation triggered it)
- Request ID (from orchestrator processing)
- Account numbers checked (if any)
- Timestamp
- Results JSON (reasons, evidence, status)
- Processing latency

**Design**: Could be separate table or embedded JSON in messages

### 2.7 RAG Query Results Domain (Optional)
**Purpose**: Track which documents/chunks were retrieved and used  
**Properties**:
- Query ID (unique)
- Conversation ID
- Original query text (hashed for PII?)
- Retrieved chunk IDs (from Chroma)
- Similarity scores
- Chunks used in response (citation mapping)
- Timestamp

**Use Case**: Evaluation, analytics, retraining signal

---

## 3. DATA FLOW ANALYSIS

### 3.1 User Initiates Chat
```
1. Staff logs in → Session created → Gets session_id
2. Clicks "New Chat" 
3. System creates conversation_id
4. UI sends message with (session_id, conversation_id, text)
```

### 3.2 Message Processing Pipeline
```
User Message
    ↓
[Save to messages table] → request_id, timestamp
    ↓
Intent Detection (intent_detector.py)
    ├─ Is this eligibility question? → Log intent flag
    └─ Store intent in messages or separate table
    ↓
Parallel Processing:
    ├─ Account Extraction → Log account_count (not account_numbers)
    ├─ RAG Query → Retrieve chunks → Log retrieval metadata
    └─ [Other enrichment]
    ↓
LLM Generation (using last N messages + summary + eligibility payload)
    └─ [Log generation metrics: tokens, latency, model]
    ↓
[Save assistant message] → role=assistant, content, metadata
    ↓
[Update/Create conversation summary if needed]
    ↓
[Optionally update user-level memory]
```

### 3.3 Recall Flow (Pulling Context)
```
User sends message in conversation X
    ↓
Fetch conversation_id X
    ↓
Retrieve:
    1. Last 5-10 messages (time-ordered)
    2. Current summary (if exists)
    3. Eligibility payload (if relevant to this conversation)
    4. User-level memory (if any)
    ↓
Assemble prompt
    ↓
Generate response
```

### 3.4 Long-Term Memory Archival
```
Periodically (daily/weekly):
    1. Find conversations with 50+ messages
    2. Generate comprehensive summary
    3. Optionally archive old messages (soft-delete or separate table)
    4. Keep metadata for analytics
```

---

## 4. FUNCTIONAL REQUIREMENTS

### 4.1 Must-Have (MVP)
- [x] Store and retrieve chat messages by conversation
- [x] Append-only message history (no mutations)
- [x] Fetch last N messages for context window
- [x] Create/list/archive conversations
- [x] Per-conversation summaries (generated externally)
- [x] Structured logging of all events (request_id, timestamp, severity)

### 4.2 Should-Have (Early Phase)
- [ ] Session tracking (which staff user, when they logged in)
- [ ] Eligibility check results linked to conversations
- [ ] Citation mapping (which RAG chunk was used in which response)
- [ ] Soft-delete with retention policies
- [ ] Search within a conversation's messages

### 4.3 Nice-to-Have (Future)
- [ ] Cross-conversation search ("all conversations about product X")
- [ ] User-level memory (preferences, patterns)
- [ ] Analytics: conversation duration, message count, satisfaction scores
- [ ] Branching conversations (A/B testing LLM variants)
- [ ] Vector embeddings for semantic search

---

## 5. NON-FUNCTIONAL REQUIREMENTS

### 5.1 Performance
**Expected Metrics**:
- Message write latency: < 10ms (append-only)
- Fetch last N messages: < 50ms
- Conversation list: < 100ms (for 1000 conversations)
- Summary update: < 100ms

**Scaling Context**:
- Initial: ~10-50 active staff users
- Growth: Could scale to 100+ staff users
- Message volume: Assume 10-100 messages/user/day initially

### 5.2 Durability & Reliability
- All writes must be persisted immediately (no in-memory caches without sync)
- No message loss tolerance
- Recovery from DB crash within 5 minutes
- Automated backups (daily minimum, consider transaction logs)

### 5.3 Availability
- Database availability: 99%+ (internal tool, not customer-facing)
- Graceful degradation if DB is down (queue messages, retry)

### 5.4 Consistency
- **Strong consistency required** for audit trail purposes
- Conversations and messages must be transactionally linked
- No eventual consistency for historical data

### 5.5 Maintainability
- Schema should be **version-controlled** (stored in repo)
- Migrations should be trackable (version table or migration logs)
- No custom binary formats (JSON, standard types only)

---

## 6. SECURITY & COMPLIANCE REQUIREMENTS

### 6.1 Data Classification
**Sensitive Data in System**:
- Customer account numbers (in eligibility checks)
- Customer names (possibly in conversations)
- Internal staff email/ID
- Conversation content (discussions about customer situations)

**Not Stored (Per PII Rules)**:
- Full raw account numbers in logs (hashed instead)
- Full customer names in logs
- Raw conversation text in logs (hashed or message hash instead)

### 6.2 Access Control
**Requirements**:
- Only staff user who created conversation can view it (initially)
- Admins can view all conversations (with audit trail)
- No public access
- Row-level security (staff can't see other staff's conversations)

### 6.3 Encryption
**Recommend**:
- At-rest encryption (database-level or column-level for sensitive fields)
- In-transit encryption (TLS for all API calls)
- Encryption keys managed separately from DB

### 6.4 Audit Trail
**Required**:
- Who accessed which conversation (user_id, timestamp)
- Who deleted/archived conversations
- Admin actions logged
- For compliance/investigation

### 6.5 Data Retention
**Policy**:
- Conversations kept for X months (you decide based on regulations)
- Option to hard-delete on request
- Soft-delete initially, hard-delete after retention period
- Logs kept longer than message content (e.g., 7 years for audit)

---

## 7. DATA VOLUME & GROWTH PROJECTIONS

### 7.1 Baseline Assumptions
```
Active staff users:        10-50 (initial)
Messages/day/user:         20-50 (varies by role)
Avg message length:        200-500 chars
Conversation duration:     5-20 messages
Conversation lifetime:     1-7 days (new conversation per topic)
```

### 7.2 Year-1 Projections
```
Total staff users:         50-200
Daily messages:            10,000-50,000
Total messages (1 year):   3.6M - 18M
Total conversations:       200K - 1M
DB size (text only):       ~2-10 GB
DB size (with indices):    ~5-20 GB
```

### 7.3 Backup & Storage
- Backup daily: ~1-2 GB compressed
- Retention period: 30 days of backups = 30-60 GB
- Long-term archive: Separate S3/cloud storage for compliance

---

## 8. INTEGRATION POINTS

### 8.1 Existing System Dependencies
**RAG System**:
- Needs to log which documents were retrieved
- Could benefit from linking messages to retrieved chunks
- Vector DB (Chroma) is separate from this DB (don't merge)

**Eligibility System**:
- Logs eligibility checks performed
- Need to capture: request_id, account_checked, results, processing_latency
- Results stored as JSON blob or normalized schema (design choice)

**Logging System**:
- All DB writes should trigger logs (request_id, event, timestamp)
- Logs directory separate from DB
- JSON format for all logs

**Session Manager**:
- Provides session_id, request_id
- Handles user authentication
- DB needs to trust session_id as user identifier

### 8.2 Future Integration Points
- **Analytics DB**: Mirror relevant data for dashboards (separate system)
- **Embeddings Store**: Vector DB for semantic search (separate: keep Chroma for docs)
- **Message Queue**: If chat becomes async (Kafka/RabbitMQ could feed messages to DB)
- **External Data Sources**: Customer data, product info (read-only joins)

---

## 9. SCHEMA PATTERNS & DESIGN DECISIONS YOU'LL MAKE

### 9.1 Identifier Strategy Decision
**Options**:
1. Auto-incrementing integers (simple but not portable)
2. UUIDs (v4: random, v1: timestamp-based)
3. Composite keys (user_id + sequence)

**Recommendation for Your Context**: UUIDs (likely v4) enable:
- Distributed generation (no DB round-trip)
- Partition-friendly for future sharding
- Standard in modern systems

### 9.2 Timestamp Strategy Decision
**Options**:
1. UTC timestamps (ISO 8601 strings)
2. Unix timestamps (seconds since epoch)
3. Both (for flexibility)

**Requirement in Your System**: ISO 8601 UTC (per logging_rules.md)

### 9.3 Message Content Storage Decision
**Options**:
1. Plain TEXT field (simple, not searchable)
2. VARCHAR with limit (100KB? 1MB?)
3. JSONB (PostgreSQL) with structured fields (role, content, metadata)

**Trade-off**: JSONB allows flexible metadata; plain TEXT is simpler

### 9.4 Conversation State Decision
**Options**:
1. Boolean flags (is_archived bool)
2. Enum status (ACTIVE, ARCHIVED, CLOSED, DELETED)
3. Status + archived_at timestamp

**Your System Likely Needs**: Status enum + timestamp for audit trail

### 9.5 Summary Storage Decision
**Options**:
1. One summary per conversation (simple, one-time)
2. Multiple versions (track summary evolution)
3. Separate table with versioning

**Complexity Trade-off**: One per conversation is simpler; versioning enables analysis

### 9.6 Eligibility Results Storage Decision
**Options**:
1. Separate table (normalized relational approach)
2. JSON in messages (embedded, denormalized)
3. Hybrid (reference in messages, stored in separate table)

**Impact**: Affects how you query "what eligibility checks happened in conversation X?"

### 9.7 Search Capability Decision
**Options**:
1. No search (just chronological lookup)
2. Full-text search on message content (PostgreSQL: tsvector)
3. Elasticsearch for advanced search (separate system)
4. Semantic search on embeddings (future)

**MVP vs. Growth**: MVP doesn't need search; add later if needed

### 9.8 Soft-Delete vs. Hard-Delete Decision
**Options**:
1. Hard-delete (immediate, space-efficient, non-recoverable)
2. Soft-delete (add deleted_at timestamp, recoverable)
3. Hybrid (soft-delete for X days, then hard-delete)

**Your System**: Soft-delete recommended (compliance, audit trail)

---

## 10. TECHNOLOGY STACK CONSIDERATIONS

### 10.1 Database Engine Options
**Your requirements favor**:
- Relational database (structured, ACID, auditability)
- JSON/unstructured support (for message content, metadata)
- Strong consistency
- Text indexing (eventual need)
- Availability in your infrastructure

**Common choices for internal systems**:
1. **PostgreSQL**: Production-ready, JSON support, excellent for this use case
2. **MySQL/MariaDB**: Also solid, simpler JSON, slightly less flexible
3. **SQLite**: Prototyping only, not suitable for multi-user concurrent access
4. **Cloud DBs**: AWS RDS, GCP Cloud SQL, Azure SQL (managed alternatives)

### 10.2 Concurrent Access Considerations
**Your System Has**:
- Multiple staff users accessing simultaneously
- Append-only messages (reduces locking contention)
- Short transactions (no long-running jobs in DB layer)

**Implication**: Need row-level locking, transaction support, connection pooling

### 10.3 Caching Layer Decision
**Options**:
1. No cache (direct DB queries every time)
2. In-memory cache (Redis, Memcached) for recent conversations
3. Application-level caching (Python @lru_cache)

**Your MVP**: Likely no cache needed; ADD if query latency becomes issue

### 10.4 Migration & Versioning
**Must Have**:
- Schema version tracking (version table or migration logs)
- Deployable migrations (Alembic for Python, Flyway, etc.)
- Rollback capability
- Zero-downtime deployments (avoid blocking migrations)

---

## 11. DETAILED DATA PROPERTIES BY ENTITY

### 11.1 Users (Staff)
```
users
├── user_id          VARCHAR(255) PRIMARY KEY [Auth provider ID]
├── email            VARCHAR(255) UNIQUE REQUIRED
├── department       VARCHAR(100)
├── role             VARCHAR(100)
├── created_at       TIMESTAMP
├── last_login       TIMESTAMP
├── is_active        BOOLEAN
└── metadata         JSONB [Custom fields: phone, team, etc.]

Questions for You:
- Is email the unique identifier, or do you have employee IDs?
- Do you track which team/department they belong to?
- Is there a role hierarchy (admin, manager, staff)?
```

### 11.2 Sessions
```
sessions
├── session_id       UUID PRIMARY KEY
├── user_id          VARCHAR(255) FOREIGN KEY → users
├── created_at       TIMESTAMP
├── last_activity    TIMESTAMP
├── expires_at       TIMESTAMP
├── ip_address       VARCHAR(45)
└── user_agent       VARCHAR(500)

Questions for You:
- How long should sessions last?
- Do you need IP tracking for security?
- Should session be tied to specific browser/device?
```

### 11.3 Conversations
```
conversations
├── id               UUID PRIMARY KEY
├── user_id          VARCHAR(255) FOREIGN KEY → users
├── title            VARCHAR(255)
├── status           ENUM(ACTIVE, ARCHIVED, CLOSED, DELETED)
├── created_at       TIMESTAMP
├── last_message_at  TIMESTAMP
├── archived_at      TIMESTAMP (when soft-deleted)
├── message_count    INTEGER [Denormalized for speed]
└── metadata         JSONB
    ├── customer_id  (if this conversation is about a customer)
    ├── account_numbers (array of accounts discussed)
    ├── intent_tags  (eligibility, product_info, etc.)
    └── context_keys (any app-specific context)

Questions for You:
- Should "title" be auto-generated by LLM?
- What metadata is important beyond customer/account?
- Do you need to track "which customer service rep is helping which customer"?
```

### 11.4 Messages
```
messages
├── id               UUID PRIMARY KEY
├── conversation_id  UUID FOREIGN KEY → conversations
├── role             ENUM(USER, ASSISTANT, SYSTEM) 
├── content          TEXT
├── created_at       TIMESTAMP
├── metadata         JSONB
│   ├── tokens       INTEGER [Prompt + completion tokens]
│   ├── latency_ms   INTEGER [Generation latency]
│   ├── model_name   VARCHAR(100) [Which LLM]
│   ├── temperature  FLOAT [LLM parameter]
│   ├── top_p        FLOAT [LLM parameter]
│   ├── prompt_version VARCHAR(50)
│   ├── source       VARCHAR(100) [user_input, rag_retrieval, eligibility_result]
│   ├── request_id   UUID [From orchestrator]
│   └── tags         JSONB [intent, category, etc.]
├── is_deleted       BOOLEAN
└── deleted_at       TIMESTAMP

Questions for You:
- Should message content be encrypted at rest?
- Do you need to track which prompt template was used?
- Should you store the full eligibility payload, or just reference ID?
```

### 11.5 Conversation Summaries
```
conversation_summaries
├── conversation_id  UUID PRIMARY KEY FK → conversations
├── summary_text     TEXT [2-3 sentences]
├── key_entities     JSONB [Array of important entities: names, accounts, products]
├── version          INTEGER [Auto-increment]
├── created_at       TIMESTAMP [When first created]
├── updated_at       TIMESTAMP [Last update]
├── token_count      INTEGER [Tokens used to generate summary]
└── metadata         JSONB [confidence, model_version, etc.]

Questions for You:
- How frequently should summaries be regenerated?
- Should you keep history of all summary versions?
- Who generates summaries? (Async job, on-demand LLM call?)
```

### 11.6 Eligibility Checks (Optional Separate Table)
```
eligibility_checks
├── check_id         UUID PRIMARY KEY
├── conversation_id  UUID FOREIGN KEY → conversations
├── request_id       UUID [From orchestrator]
├── account_numbers  TEXT ARRAY or JSON [Individual numbers as hashes, not plain text]
├── timestamp        TIMESTAMP
├── results          JSONB [Full eligibility result: reasons, evidence, status]
│   ├── status       (ELIGIBLE, INELIGIBLE, NOT_FOUND)
│   ├── reasons      (array of reason codes)
│   ├── evidence     (structured evidence values)
│   └── recommendations (next steps, owner, timing)
├── processing_latency_ms INTEGER
└── created_at       TIMESTAMP
```

### 11.7 RAG Retrievals (Optional)
```
rag_retrievals
├── retrieval_id     UUID PRIMARY KEY
├── conversation_id  UUID FOREIGN KEY → conversations
├── message_id       UUID FOREIGN KEY → messages [Which assistant message used this]
├── query_text       TEXT (original user query, hashed for PII?)
├── chunk_ids        TEXT ARRAY
├── similarity_scores FLOAT ARRAY
├── sources          JSONB
│   ├── file_names   (array of document names)
│   └── page_numbers (if applicable)
├── chunks_used_in_response  TEXT ARRAY (citation mapping)
├── timestamp        TIMESTAMP
└── metadata         JSONB
```

---

## 12. QUERY PATTERNS YOU'LL NEED

### 12.1 Conversation Queries
```
1. Get conversation by ID
2. List all conversations for user_id (paginated, sorted by last_message_at)
3. Get conversation with last N messages
4. Count messages in conversation
5. Archive/delete conversation
6. Search conversations by title
7. Get all conversations with specific metadata (e.g., mentioning account X)
```

### 12.2 Message Queries
```
1. Get last N messages for conversation (time-ordered DESC, then reverse in code)
2. Get messages between timestamps
3. Insert new message (should be fast, append-only)
4. Get message by ID
5. Soft-delete message
6. Count messages by role in conversation
7. Find all messages tagged with intent=eligibility_check
```

### 12.3 Summary Queries
```
1. Get current summary for conversation
2. Update summary (upsert pattern)
3. Get summary version history
```

### 12.4 Eligibility Queries (if normalized)
```
1. Get all eligibility checks in conversation
2. Get eligibility check by check_id
3. Get all checks for specific account number (hashed)
4. Get checks performed in date range
```

### 12.5 Analytics Queries (future)
```
1. Count messages/user/day
2. Average conversation length
3. Most common intents
4. Average message generation latency
5. Eligibility check failure rate
```

---

## 13. INDEXING STRATEGY

**Essential indexes** (fast writes + reads):
```
CREATE INDEX ON conversations (user_id, created_at DESC);
CREATE INDEX ON messages (conversation_id, created_at ASC);
CREATE INDEX ON conversations (status, created_at);
CREATE INDEX ON messages (created_at);  [For global message stream]
```

**Optional indexes** (only add if queries slow):
```
CREATE UNIQUE INDEX ON conversation_summaries (conversation_id);
CREATE INDEX ON eligibility_checks (conversation_id, created_at DESC);
CREATE INDEX ON eligibility_checks (account_numbers) USING GIN;  [If array search needed]
```

**Avoid premature indexing**: Index only after profiling shows slow queries.

---

## 14. TRANSACTIONS & CONCURRENCY

### 14.1 Critical Transactions
```
Transaction 1: Save user message + update last_message_at
    BEGIN
    INSERT INTO messages (...)
    UPDATE conversations SET last_message_at = NOW()
    COMMIT
    
Transaction 2: Save assistant message + update summary
    BEGIN
    INSERT INTO messages (...)
    UPDATE conversations SET last_message_at = NOW()
    [Maybe] UPDATE conversation_summaries SET summary_text = ... WHERE conversation_id = ...
    COMMIT
```

### 14.2 Isolation Level
**Recommend**: READ COMMITTED (default in most DBs)
- Sufficient for your audit requirements
- Good balance between consistency and concurrency
- Prevents dirty reads

**Avoid**: SERIALIZABLE (too slow for chat app)

---

## 15. COMMON ANTI-PATTERNS TO AVOID

### ❌ Anti-Pattern 1: Storing Every Intermediate State
**Wrong**: Save entity state in separate tables (old_messages, deleted_messages)  
**Right**: Use soft-delete with timestamp (is_deleted bool + deleted_at timestamp)

### ❌ Anti-Pattern 2: Denormalizing Every Metric
**Wrong**: Count messages in every conversation manually in code  
**Right**: Maintain message_count in conversations table, update on INSERT/DELETE

### ❌ Anti-Pattern 3: Blob Storage for Structured Data
**Wrong**: Store eligibility result as single TEXT blob without schema  
**Right**: Use JSONB with documented schema or normalized table

### ❌ Anti-Pattern 4: No Request ID Linkage
**Wrong**: Messages and logs unconnected; can't trace one user action  
**Right**: Every message, log, eligibility check carries request_id

### ❌ Anti-Pattern 5: Mixing Message Storage with Indexing
**Wrong**: Storing message for chat history AND full-text search in same table  
**Right**: Normalize: Chat table stores current messages, separate search index for analytics

### ❌ Anti-Pattern 6: No Schema Versioning
**Wrong**: Change table structure without tracking version  
**Right**: Add schema_version table; track migrations

---

## 16. MISSING INFORMATION (QUESTIONS FOR YOU)

### 16.1 Authentication & User Management
- [ ] How are staff authenticated? (LDAP, OAuth, Internal SSO, hardcoded?)
- [ ] Is there a user directory/service we integrate with?
- [ ] Do you need SSO/SAML, or simple username/password?
- [ ] Who manages user credentials?

### 16.2 Compliance & Regulations
- [ ] Which data protection regulations apply? (GDPR, CCPA, local banking rules?)
- [ ] How long must chat records be retained?
- [ ] Must you comply with data residency requirements?
- [ ] Are there audit logging mandates?
- [ ] Is there an approval process for data deletion?

### 16.3 Customer Data Linkage
- [ ] Can a staff user "switch accounts" (view conversation about customer X)?
- [ ] Is there a master customer/account database you read from?
- [ ] Should conversations be tagged with customer_id for cross-staff visibility?

### 16.4 Eligibility System Integration
- [ ] Should eligibility checks be queryable separately (e.g., "get all ineligible accounts")?
- [ ] Do you need to store full eligibility payload or just summary?
- [ ] Should eligibility results trigger alerts/notifications?

### 16.5 Scaling & Growth
- [ ] What's the expected user growth over 2 years? (10 users → ? users)
- [ ] Will chat history be archived/deleted, or kept indefinitely?
- [ ] Is there budget for managed database (RDS, Cloud SQL) vs. self-hosted?
- [ ] Will you have multiple data centers eventually?

### 16.6 Admin & Monitoring
- [ ] Who has admin access to the database?
- [ ] Do you need real-time dashboards (current active users, messages/sec)?
- [ ] Should there be an audit log UI for staff/admins?
- [ ] Who investigates data issues?

### 16.7 Message Content & Privacy
- [ ] Can conversation content be indexed by external search (compliance issue)?
- [ ] Should customer PII in messages be masked before storage?
- [ ] Is there a need to redact/anonymize conversations for training?

### 16.8 Integration with Existing Systems
- [ ] Where will the database run? (Same server as app? Separate?)
- [ ] Do you have existing database infrastructure/standards?
- [ ] Any constraints on database technology (company approved list)?

---

## 17. SUMMARY: DESIGN DECISIONS YOUR TEAM WILL MAKE

**Core Schema Decisions**:
1. **Identifier Strategy**: UUID vs. auto-increment vs. composite key
2. **Message Structure**: Plain TEXT vs. JSONB with metadata
3. **Conversation State**: Boolean flags vs. ENUM status
4. **Summary Versioning**: Single latest vs. multi-version tracking
5. **Eligibility Storage**: Separate table vs. JSON in messages
6. **Soft-Delete Strategy**: Just `is_deleted` flag vs. `deleted_at` timestamp
7. **Search**: No search vs. full-text vs. dedicated search engine

**Infrastructure Decisions**:
1. **Database Engine**: PostgreSQL vs. MySQL vs. Cloud managed
2. **Hosting**: Self-managed vs. RDS/Cloud SQL
3. **Backup Strategy**: Daily snapshots vs. transaction logs vs. both
4. **Caching**: None vs. Redis for hot conversations
5. **Connection Pooling**: How many concurrent connections?

**Operational Decisions**:
1. **Monitoring**: What metrics to track?
2. **Alerting**: When to notify on-call engineer?
3. **Retention Policy**: How long to keep records?
4. **Access Control**: Row-level vs. role-based security?
5. **Disaster Recovery**: RTO/RPO targets?

---

## 18. NEXT STEPS FOR YOU

1. **Review** this analysis against your actual constraints (compliance, infrastructure, team expertise)
2. **Answer** the questions in Section 16 (Missing Information)
3. **Make decisions** on the major design choices in Section 17
4. **Sketch ER diagram**: How entities relate (use draw.io, Lucidchart, etc.)
5. **Write SQL DDL**: CREATE TABLE statements embodying your decisions
6. **Build migrations framework**: Alembic (Python) or similar
7. **Prototype**: Write basic CRUD operations (insert message, fetch conversation)
8. **Test**: Write integration tests for query patterns (Section 12)
9. **Performance**: Run load tests before going to production
10. **Document**: Schema documentation for future developers

---

**End of Analysis**

This document provides all information needed to design a database that:
- Handles your current chatbot requirements
- Scales for future growth
- Maintains compliance/audit trails
- Integrates seamlessly with your RAG and eligibility systems
- Supports the logging and session management already in place

