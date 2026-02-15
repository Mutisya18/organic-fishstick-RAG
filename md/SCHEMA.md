# Database Schema Documentation

**Version**: 1.0  
**Database Types**: SQLite (development), PostgreSQL (production)  
**Last Updated**: February 6, 2026

---

## Overview

The database uses a **two-table model** to store conversation history:
- **conversations** - Tracks chat sessions and metadata
- **messages** - Stores individual messages (append-only event log)

### Design Patterns

- **Immutable Messages**: Messages are append-only, never updated after creation
- **Soft-Delete**: Conversations archived via `status` field, not hard-deleted
- **Request Tracing**: Each message carries `request_id` for end-to-end tracing
- **Flexible Metadata**: JSON column for extensible data storage
- **Optimized Queries**: Strategic indexes on frequently-queried columns

---

## Entity Relationship Diagram

```
┌──────────────────────────┐
│     conversations        │
├──────────────────────────┤
│ id (PK, UUID)            │◄────┐
│ user_id (FK, String)     │     │ ONE-TO-MANY
│ title (String)           │     │
│ status (Enum)            │     │
│ message_count (Integer)  │     │
│ last_message_at (DT)     │     │
│ archived_at (DT)         │     │
│ created_at (DT)          │     │
│ updated_at (DT)          │     │
└──────────────────────────┘     │
                                 │
                         ┌───────┴──────────┐
                         │    messages      │
                         ├──────────────────┤
                         │ id (PK, UUID)    │
                         │ conversation_id (FK)
                         │ role (Enum)      │
                         │ content (Text)   │
                         │ msg_metadata (JSON)
                         │ created_at (DT)  │
                         │ updated_at (DT)  │
                         └──────────────────┘
```

---

## Table: `conversations`

Represents a chat session between a user and the assistant.

### Columns

| Column | Type | Nullable | Default | Index | Description |
|--------|------|----------|---------|-------|-------------|
| `id` | UUID (36 chars) | No | uuid4() | PK | Unique primary key |
| `user_id` | String(255) | No | — | Yes | User identifier for multi-user support |
| `title` | String(255) | Yes | NULL | — | Human-readable conversation title |
| `status` | Enum | No | ACTIVE | Yes | ACTIVE, ARCHIVED, CLOSED, DELETED |
| `message_count` | Integer | No | 0 | — | Total messages in conversation |
| `last_message_at` | DateTime | Yes | NULL | Yes | Timestamp of most recent message |
| `archived_at` | DateTime | Yes | NULL | — | Timestamp when conversation archived |
| `created_at` | DateTime | No | NOW() | Yes | When conversation created (UTC) |
| `updated_at` | DateTime | No | NOW() | — | Last update timestamp (UTC) |

### Indexes

```sql
-- Primary key index
CREATE UNIQUE INDEX pk_conversations ON conversations(id);

-- Foreign key support
CREATE INDEX idx_user_id ON conversations(user_id);

-- Query optimization
CREATE INDEX idx_status ON conversations(status);
CREATE INDEX idx_user_last_message ON conversations(user_id, last_message_at);
CREATE INDEX idx_status_created ON conversations(status, created_at);
CREATE INDEX idx_created_at ON conversations(created_at);
```

### Status Values

| Status | Description |
|--------|-------------|
| `ACTIVE` | Conversation in progress |
| `ARCHIVED` | User cleared/archived the conversation (soft-delete) |
| `CLOSED` | Conversation ended/completed |
| `DELETED` | Permanently deleted (admin only) |

### Relationships

- **One-to-Many**: One conversation has many messages
- **Cascade Delete**: Deleting a conversation deletes all its messages
- **No Foreign Key to users**: User table not modeled yet (future enhancement)

---

## Table: `messages`

Represents a single message in a conversation. Designed as append-only event log.

### Columns

| Column | Type | Nullable | Default | Index | Description |
|--------|------|----------|---------|-------|-------------|
| `id` | UUID (36 chars) | No | uuid4() | PK | Unique message identifier |
| `conversation_id` | String(36) | No | — | Yes | Foreign key to conversations |
| `role` | Enum | No | — | Yes | Message sender: user, assistant, system |
| `content` | Text | No | — | — | Full message text |
| `msg_metadata` | JSON | Yes | NULL | — | Flexible metadata (request_id, tokens, latency) |
| `created_at` | DateTime | No | NOW() | Yes | Message timestamp (UTC) |
| `updated_at` | DateTime | No | NOW() | — | Always equals created_at (immutable) |

### Indexes

```sql
-- Primary key index
CREATE UNIQUE INDEX pk_messages ON messages(id);

-- Foreign key support
CREATE INDEX idx_conversation_id ON messages(conversation_id);

-- Query optimization
CREATE INDEX idx_conversation_created ON messages(conversation_id, created_at);
CREATE INDEX idx_role_created ON messages(role, created_at);
CREATE INDEX idx_created_at ON messages(created_at);
```

### Role Values

| Role | Description | Typical Metadata |
|------|-------------|-----------------|
| `user` | User message | `request_id`, `source` |
| `assistant` | LLM/Eligibility response | `request_id`, `latency_ms`, `tokens`, `model_name`, `source` |
| `system` | System message (reserved) | `error_type`, `source` |

### Metadata Structure (msg_metadata JSON)

The `msg_metadata` column is flexible JSON for extensible data:

#### User Message Metadata
```json
{
  "request_id": "req_abc123def456",
  "source": "user_input"
}
```

#### Assistant Message Metadata (RAG)
```json
{
  "request_id": "req_abc123def456",
  "source": "rag",
  "latency_ms": 1245.67,
  "tokens": 156,
  "model_name": "llama2",
  "prompt_version": "v1.0"
}
```

#### Assistant Message Metadata (Eligibility)
```json
{
  "request_id": "req_abc123def456",
  "source": "eligibility",
  "latency_ms": 234.56,
  "tokens": 89
}
```

#### Error Message Metadata
```json
{
  "request_id": "req_abc123def456",
  "error_type": "TimeoutError",
  "source": "error"
}
```

### Relationships

- **Many-to-One**: Many messages belong to one conversation
- **Parent Conversation**: Foreign key to conversations(id)
- **Cascade Behavior**: Deleting a conversation deletes all its messages

### Immutability Guarantee

Messages are designed to be immutable:
- No UPDATE operations allowed after INSERT
- `updated_at` always equals `created_at`
- Provides append-only event log semantics
- Enables audit trail and forensics

---

## SQL Data Definition

### SQLite

```sql
-- Create conversations table
CREATE TABLE conversations (
  id VARCHAR(36) PRIMARY KEY,
  user_id VARCHAR(255) NOT NULL,
  title VARCHAR(255),
  status VARCHAR(20) DEFAULT 'ACTIVE' NOT NULL,
  message_count INTEGER DEFAULT 0 NOT NULL,
  last_message_at DATETIME,
  archived_at DATETIME,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE INDEX idx_user_id ON conversations(user_id);
CREATE INDEX idx_status ON conversations(status);
CREATE INDEX idx_user_last_message ON conversations(user_id, last_message_at);
CREATE INDEX idx_status_created ON conversations(status, created_at);
CREATE INDEX idx_created_at ON conversations(created_at);

-- Create messages table
CREATE TABLE messages (
  id VARCHAR(36) PRIMARY KEY,
  conversation_id VARCHAR(36) NOT NULL,
  role VARCHAR(20) NOT NULL,
  content TEXT NOT NULL,
  msg_metadata JSON,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
  FOREIGN KEY(conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
);

CREATE INDEX idx_conversation_id ON messages(conversation_id);
CREATE INDEX idx_conversation_created ON messages(conversation_id, created_at);
CREATE INDEX idx_role_created ON messages(role, created_at);
CREATE INDEX idx_created_at ON messages(created_at);
```

### PostgreSQL

```sql
-- Create enums
CREATE TYPE conversation_status AS ENUM ('ACTIVE', 'ARCHIVED', 'CLOSED', 'DELETED');
CREATE TYPE message_role AS ENUM ('user', 'assistant', 'system');

-- Create conversations table
CREATE TABLE conversations (
  id VARCHAR(36) PRIMARY KEY,
  user_id VARCHAR(255) NOT NULL,
  title VARCHAR(255),
  status conversation_status DEFAULT 'ACTIVE' NOT NULL,
  message_count INTEGER DEFAULT 0 NOT NULL,
  last_message_at TIMESTAMP,
  archived_at TIMESTAMP,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE INDEX idx_user_id ON conversations(user_id);
CREATE INDEX idx_status ON conversations(status);
CREATE INDEX idx_user_last_message ON conversations(user_id, last_message_at);
CREATE INDEX idx_status_created ON conversations(status, created_at);
CREATE INDEX idx_created_at ON conversations(created_at);

-- Create messages table
CREATE TABLE messages (
  id VARCHAR(36) PRIMARY KEY,
  conversation_id VARCHAR(36) NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
  role message_role NOT NULL,
  content TEXT NOT NULL,
  msg_metadata JSONB,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE INDEX idx_conversation_id ON messages(conversation_id);
CREATE INDEX idx_conversation_created ON messages(conversation_id, created_at);
CREATE INDEX idx_role_created ON messages(role, created_at);
CREATE INDEX idx_created_at ON messages(created_at);

-- GIN index for JSON querying
CREATE INDEX idx_msg_metadata_gin ON messages USING GIN(msg_metadata);
```

---

## Data Examples

### Example Conversation

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "user_id": "user_12345",
  "title": "Digital Lending Eligibility",
  "status": "ACTIVE",
  "message_count": 4,
  "last_message_at": "2026-02-06T14:32:45.123456",
  "archived_at": null,
  "created_at": "2026-02-06T10:15:30.000000",
  "updated_at": "2026-02-06T10:15:30.000000"
}
```

### Example Messages in Conversation

#### User Message
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440001",
  "conversation_id": "550e8400-e29b-41d4-a716-446655440000",
  "role": "user",
  "content": "Am I eligible for digital lending?",
  "msg_metadata": {
    "request_id": "req_abc123def456",
    "source": "user_input"
  },
  "created_at": "2026-02-06T10:15:35.000000",
  "updated_at": "2026-02-06T10:15:35.000000"
}
```

#### Assistant Response
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440002",
  "conversation_id": "550e8400-e29b-41d4-a716-446655440000",
  "role": "assistant",
  "content": "Based on your account details, you appear to be eligible...",
  "msg_metadata": {
    "request_id": "req_abc123def456",
    "source": "eligibility",
    "latency_ms": 245.67,
    "tokens": 124
  },
  "created_at": "2026-02-06T10:16:00.000000",
  "updated_at": "2026-02-06T10:16:00.000000"
}
```

---

## Query Patterns

### Most Common Queries

```sql
-- Fetch last N messages for LLM context
SELECT id, role, content, msg_metadata, created_at
FROM messages
WHERE conversation_id = 'conv_id'
ORDER BY created_at DESC
LIMIT 5;

-- Find active conversations for a user
SELECT id, title, message_count, last_message_at
FROM conversations
WHERE user_id = 'user_id' AND status = 'ACTIVE'
ORDER BY last_message_at DESC;

-- Get conversation with all messages
SELECT c.*, m.id as msg_id, m.role, m.content, m.msg_metadata
FROM conversations c
LEFT JOIN messages m ON c.id = m.conversation_id
WHERE c.id = 'conv_id'
ORDER BY m.created_at ASC;

-- Find messages with latency info (PostgreSQL)
SELECT id, conversation_id, content, msg_metadata->>'latency_ms' as latency_ms
FROM messages
WHERE msg_metadata->>'request_id' = 'req_id';

-- Find messages with latency info (SQLite)
SELECT id, conversation_id, content, json_extract(msg_metadata, '$.latency_ms') as latency_ms
FROM messages
WHERE json_extract(msg_metadata, '$.request_id') = 'req_id';
```

---

## Performance Considerations

### Indexes Strategy

| Index | Purpose | Query Type |
|-------|---------|-----------|
| `idx_user_last_message` | Fetch recent conversations for user | Common |
| `idx_conversation_created` | Get messages in order | Very Common |
| `idx_status_created` | Find active conversations | Common |
| `idx_role_created` | Analyze by role (user vs assistant) | Analytical |
| `idx_created_at` | Time-based queries | Sometimes |

### Scalability

- **SQLite**: Suitable up to 1GB database, single user
- **PostgreSQL**: Handles millions of conversations, concurrent access
- **Partitioning**: For very large databases, partition by user_id or date
- **Archival**: Move old conversations to cold storage after 1 year

### Connection Pooling

- **SQLite**: StaticPool (single connection)
- **PostgreSQL**: QueuePool with pool_size=5, max_overflow=5, timeout=30s

---

## Future Enhancements

1. **User Table**: Create explicit users table with user_id as FK
2. **Conversation Tags**: Add tags table for categorization
3. **Message Reactions**: Track user reactions/feedback on responses
4. **Search Index**: Full-text search on message content
5. **Vector Embeddings**: Store embeddings for semantic search
6. **Analytics Views**: Create materialized views for dashboards
7. **Partitioning**: Partition messages by conversation_id or date
8. **Archival Strategy**: Move old conversations to archive database

---

## References

- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [PostgreSQL JSON/JSONB](https://www.postgresql.org/docs/current/datatype-json.html)
- [SQLite JSON Functions](https://www.sqlite.org/json1.html)
