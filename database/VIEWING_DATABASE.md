# Database Viewing Guide for Codespaces

**Quick Reference**: View, query, and analyze your chat history database directly in Codespaces.

---

## Quick Start

### Option 1: Using Python (Recommended for Beginners)

```bash
cd /workspaces/organic-fishstick-RAG
source vecna/bin/activate
python -m database.cli
```

### Option 2: Using SQLite CLI

```bash
sqlite3 chat_history.db
```

### Option 3: Using Python REPL

```bash
source vecna/bin/activate
python
>>> from database import db
>>> db.initialize()
>>> convs = db.list_conversations(user_id="default_user")
>>> print(convs)
```

---

## Method 1: SQLite CLI (Most Direct)

### Access SQLite Database

```bash
# Navigate to workspace
cd /workspaces/organic-fishstick-RAG

# Open database
sqlite3 chat_history.db
```

### Basic Commands

```sql
-- Show all tables
.tables

-- Show schema for a table
.schema conversations
.schema messages

-- Show table info with columns
PRAGMA table_info(conversations);
PRAGMA table_info(messages);

-- Exit
.quit
```

### View All Data

```sql
-- Count total conversations
SELECT COUNT(*) as total_conversations FROM conversations;

-- Count total messages
SELECT COUNT(*) as total_messages FROM messages;

-- List all conversations
SELECT id, user_id, title, status, message_count, created_at 
FROM conversations
ORDER BY created_at DESC;

-- Exit
.quit
```

---

## Method 2: Python Helper Script

### Create a Quick Query Script

```python
# File: query_db.py
from database import db
from datetime import datetime

db.initialize()

# Get all conversations
convs = db.list_conversations(user_id="default_user", include_archived=True)

print("\n" + "="*80)
print("CONVERSATIONS")
print("="*80)
for conv in convs:
    print(f"\nID: {conv['id']}")
    print(f"Title: {conv['title']}")
    print(f"Status: {conv['status']}")
    print(f"Messages: {conv['message_count']}")
    print(f"Created: {conv['created_at']}")
    print(f"Last Message: {conv['last_message_at']}")
    
    # Get messages
    messages = db.get_last_n_messages(conv['id'], n=10)
    print(f"\n  --- Messages ({len(messages)}) ---")
    for msg in messages:
        print(f"  [{msg['role'].upper()}] {msg['content'][:60]}...")
        if msg.get('msg_metadata'):
            print(f"    Metadata: {msg['msg_metadata']}")

db.shutdown()
```

Run it:
```bash
source vecna/bin/activate
python query_db.py
```

---

## Method 3: Interactive Python REPL

Run Python interactively:

```bash
source vecna/bin/activate
python
```

Then in Python:

```python
from database import db

# Initialize
db.initialize()
print("✅ Database initialized")

# List conversations
convs = db.list_conversations(user_id="default_user")
print(f"\n📊 Found {len(convs)} conversations:")
for conv in convs:
    print(f"  - {conv['title']} ({conv['id']})")

# Pick a conversation
if convs:
    conv_id = convs[0]['id']
    
    # Get messages
    messages = db.get_last_n_messages(conv_id, n=5)
    print(f"\n💬 Last 5 messages:")
    for msg in messages:
        print(f"  [{msg['role']}] {msg['content']}")
        if msg.get('msg_metadata'):
            print(f"    📝 {msg['msg_metadata']}")

# Exit
db.shutdown()
exit()
```

---

## SQL Queries by Use Case

### 1. View All Conversations (Active Only)

```sql
SELECT 
  id,
  user_id,
  title,
  status,
  message_count,
  last_message_at,
  created_at
FROM conversations
WHERE status = 'ACTIVE'
ORDER BY last_message_at DESC;
```

### 2. View All Conversations (Including Archived)

```sql
SELECT 
  id,
  user_id,
  title,
  status,
  message_count,
  last_message_at,
  archived_at,
  created_at
FROM conversations
ORDER BY created_at DESC;
```

### 3. Get Full Conversation History

```sql
SELECT 
  c.title as conversation,
  m.role,
  m.content,
  m.created_at,
  m.msg_metadata
FROM conversations c
JOIN messages m ON c.id = m.conversation_id
WHERE c.id = 'YOUR_CONVERSATION_ID'
ORDER BY m.created_at ASC;
```

### 4. View Messages with Metadata

```sql
SELECT 
  id,
  conversation_id,
  role,
  substr(content, 1, 50) as preview,
  json_extract(msg_metadata, '$.request_id') as request_id,
  json_extract(msg_metadata, '$.latency_ms') as latency_ms,
  json_extract(msg_metadata, '$.tokens') as tokens,
  created_at
FROM messages
ORDER BY created_at DESC
LIMIT 20;
```

### 5. Find Messages by Request ID

```sql
SELECT 
  m.created_at,
  m.role,
  substr(m.content, 1, 100) as content_preview,
  m.msg_metadata
FROM messages m
WHERE json_extract(m.msg_metadata, '$.request_id') = 'YOUR_REQUEST_ID'
ORDER BY m.created_at ASC;
```

### 6. Analyze Latency by Source

```sql
SELECT 
  json_extract(msg_metadata, '$.source') as source,
  COUNT(*) as message_count,
  ROUND(AVG(CAST(json_extract(msg_metadata, '$.latency_ms') AS NUMERIC)), 2) as avg_latency_ms,
  MAX(CAST(json_extract(msg_metadata, '$.latency_ms') AS NUMERIC)) as max_latency_ms,
  MIN(CAST(json_extract(msg_metadata, '$.latency_ms') AS NUMERIC)) as min_latency_ms
FROM messages
WHERE json_extract(msg_metadata, '$.latency_ms') IS NOT NULL
GROUP BY json_extract(msg_metadata, '$.source')
ORDER BY avg_latency_ms DESC;
```

### 7. Token Usage Report

```sql
SELECT 
  c.title as conversation,
  COUNT(m.id) as message_count,
  SUM(CAST(json_extract(m.msg_metadata, '$.tokens') AS NUMERIC)) as total_tokens,
  ROUND(AVG(CAST(json_extract(m.msg_metadata, '$.tokens') AS NUMERIC)), 2) as avg_tokens_per_msg,
  c.created_at
FROM conversations c
LEFT JOIN messages m ON c.id = m.conversation_id
WHERE json_extract(m.msg_metadata, '$.tokens') IS NOT NULL
GROUP BY c.id
ORDER BY total_tokens DESC;
```

### 8. Message Role Breakdown

```sql
SELECT 
  conversation_id,
  role,
  COUNT(*) as count,
  SUM(LENGTH(content)) as total_chars
FROM messages
GROUP BY conversation_id, role
ORDER BY conversation_id, role;
```

### 9. Find Long Conversations

```sql
SELECT 
  id,
  title,
  user_id,
  message_count,
  COUNT(DISTINCT created_at) as unique_dates,
  MIN(created_at) as first_message,
  MAX(created_at) as last_message,
  printf('%02d:%02d', 
    (julianday(MAX(created_at)) - julianday(MIN(created_at))) * 24,
    ((julianday(MAX(created_at)) - julianday(MIN(created_at))) * 24 * 60) % 60
  ) as duration
FROM (
  SELECT c.*, m.created_at
  FROM conversations c
  JOIN messages m ON c.id = m.conversation_id
)
GROUP BY id
HAVING message_count > 5
ORDER BY message_count DESC;
```

### 10. Message Content Statistics

```sql
SELECT 
  role,
  COUNT(*) as message_count,
  ROUND(AVG(LENGTH(content)), 2) as avg_length,
  MAX(LENGTH(content)) as max_length,
  MIN(LENGTH(content)) as min_length
FROM messages
GROUP BY role
ORDER BY message_count DESC;
```

---

## PostgreSQL Specific Queries

> **Note**: These apply only if using PostgreSQL (change DATABASE_TYPE in .env)

### View All Data with JSONB Functions

```sql
-- View metadata fields
SELECT 
  id,
  conversation_id,
  role,
  content,
  msg_metadata->>'request_id' as request_id,
  msg_metadata->>'source' as source,
  msg_metadata->>'latency_ms' as latency_ms,
  (msg_metadata->>'tokens')::int as tokens,
  created_at
FROM messages
ORDER BY created_at DESC
LIMIT 20;
```

### Search in Metadata

```sql
-- Find all messages from RAG source
SELECT 
  id, role, substr(content, 1, 50) as preview,
  msg_metadata
FROM messages
WHERE msg_metadata->>'source' = 'rag'
ORDER BY created_at DESC;
```

### Advanced JSON Filtering

```sql
-- Find high-latency messages
SELECT 
  id,
  role,
  (msg_metadata->>'latency_ms')::float as latency_ms,
  content
FROM messages
WHERE (msg_metadata->>'latency_ms')::float > 1000
ORDER BY latency_ms DESC;
```

---

## Formatting Output in SQLite

### Pretty Print with Headers

```bash
sqlite3 chat_history.db
```

```sql
-- Enable headers and formatting
.headers on
.mode column
.width 36 20 10 50

-- Then run queries
SELECT id, user_id, title, status FROM conversations;
```

### Export to CSV

```sql
.mode csv
.output conversations.csv
SELECT * FROM conversations;
.output stdout
```

### Export to JSON

```sql
-- SQLite has limited JSON export, use Python instead (see below)
```

---

## Export Data (Python)

### Export Conversations as JSON

```python
import json
from database import db

db.initialize()

# Get all conversations
convs = db.list_conversations(user_id="default_user", include_archived=True)

# Get all messages for each
data = {
    'conversations': convs,
    'messages': []
}

for conv in convs:
    messages = db.get_last_n_messages(conv['id'], n=1000)
    data['messages'].extend(messages)

# Save to file
with open('database_export.json', 'w') as f:
    json.dump(data, f, indent=2, default=str)

print(f"✅ Exported {len(convs)} conversations and {len(data['messages'])} messages")
print("   Saved to: database_export.json")

db.shutdown()
```

Run it:
```bash
source vecna/bin/activate
python -c "$(cat <<'EOF'
import json
from database import db

db.initialize()
convs = db.list_conversations(user_id="default_user", include_archived=True)
data = {'conversations': convs, 'messages': []}
for conv in convs:
    messages = db.get_last_n_messages(conv['id'], n=1000)
    data['messages'].extend(messages)

with open('database_export.json', 'w') as f:
    json.dump(data, f, indent=2, default=str)

print(f"✅ Exported to database_export.json")
db.shutdown()
EOF
)"
```

---

## Database File Locations

### SQLite

```bash
# Default location
/workspaces/organic-fishstick-RAG/chat_history.db

# Check file size
ls -lh chat_history.db

# Check recent modifications
stat chat_history.db
```

### PostgreSQL

Connection string defined in `.env`:
```bash
DATABASE_URL=postgresql://user:password@localhost:5432/chatbot_db
```

---

## Backup and Restore

### SQLite Backup

```bash
# Backup entire database
cp chat_history.db chat_history.db.backup

# Verified backup
sqlite3 chat_history.db.backup "SELECT COUNT(*) FROM conversations;"
```

### SQLite Restore

```bash
# Restore from backup
cp chat_history.db.backup chat_history.db
```

### PostgreSQL Backup

```bash
# Note: Requires psql command-line tools
pg_dump -U $DB_USER -h $DB_HOST -d $DB_NAME > backup.sql

# Restore
psql -U $DB_USER -h $DB_HOST -d $DB_NAME < backup.sql
```

---

## Debugging and Monitoring

### Check Database Corruption (SQLite)

```bash
sqlite3 chat_history.db "PRAGMA integrity_check;"
```

### Analyze Database Size

```bash
# Total size
ls -lh chat_history.db

# Size per table (SQLite)
sqlite3 chat_history.db "
SELECT 
  name,
  SUM(pgsize) / 1024 / 1024.0 as size_mb
FROM dbstat
GROUP BY name
ORDER BY size_mb DESC;
"
```

### Enable Query Logging (Development Only)

In `.env`:
```
DATABASE_ECHO=true
```

Then run your app:
```bash
./start.sh
```

All SQL queries will print to console.

---

## Helpful Aliases

Add to your `.bashrc` or `.zshrc`:

```bash
# SQLite quick access
alias db='sqlite3 /workspaces/organic-fishstick-RAG/chat_history.db'

# Query shortcuts
alias db_tables='sqlite3 /workspaces/organic-fishstick-RAG/chat_history.db ".tables"'
alias db_convs='sqlite3 /workspaces/organic-fishstick-RAG/chat_history.db "SELECT id, title, message_count FROM conversations ORDER BY created_at DESC;"'

# Count data
alias db_count='sqlite3 /workspaces/organic-fishstick-RAG/chat_history.db "SELECT (SELECT COUNT(*) FROM conversations) as convs, (SELECT COUNT(*) FROM messages) as msgs;"'
```

Usage:
```bash
db_tables              # List all tables
db_convs               # Show all conversations
db_count               # Show counts
db ".schema"           # Show full schema
```

---

## Example: Full Interactive Session

```bash
$ sqlite3 chat_history.db

sqlite> .headers on
sqlite> .mode column
sqlite> .width 20 20 15 20

sqlite> SELECT 'CONVERSATIONS OVERVIEW' as ' ';
 CONVERSATIONS OVERVIEW

sqlite> SELECT id, title, message_count, status FROM conversations LIMIT 5;
id                         title                       message_count  status
---------------------------  --------------------------  --------  ----------
550e8400-e29b-41d4-a71...   Chat about eligibility     4           ACTIVE
550e8400-e29b-41d4-a72...   Balance inquiry             2           ARCHIVED

sqlite> SELECT 'MESSAGES BREAKDOWN' as ' ';
 MESSAGES BREAKDOWN

sqlite> SELECT role, COUNT(*) FROM messages GROUP BY role;
role         COUNT(*)
-----------  --------
user         12
assistant    12
system       0

sqlite> .quit
```

---

## Troubleshooting

### Database Locked Error

```bash
# SQLite can only have one writer at a time
# Solution: Close other connections or wait

# Check if database is in use
lsof | grep chat_history.db
```

### No Tables Found

```bash
# Database exists but no tables - needs initialization
python -c "from database import db; db.initialize()"
```

### Can't Connect to PostgreSQL

```bash
# Check credentials in .env
# Verify PostgreSQL server is running
# Check firewall rules
```

---

## References

- [SQLite Documentation](https://www.sqlite.org/docs.html)
- [SQLite JSON Functions](https://www.sqlite.org/json1.html)
- [PostgreSQL JSON/JSONB](https://www.postgresql.org/docs/current/datatype-json.html)

