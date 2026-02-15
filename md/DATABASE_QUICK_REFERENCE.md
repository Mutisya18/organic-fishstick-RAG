# Database Quick Reference

Fast access to the most common queries and operations.

---

## One-Liners

### View recent conversations
```bash
sqlite3 organic-fishstick.db "SELECT id, title, message_count, created_at FROM conversations ORDER BY created_at DESC LIMIT 10;"
```

### Count all messages
```bash
sqlite3 organic-fishstick.db "SELECT COUNT(*) as total_messages FROM messages;"
```

### View all active conversations
```bash
sqlite3 organic-fishstick.db "SELECT id, title, message_count FROM conversations WHERE status='ACTIVE';"
```

### Open database interactively
```bash
sqlite3 organic-fishstick.db
```

### Show all tables
```bash
sqlite3 organic-fishstick.db ".tables"
```

---

## Copy-Paste Queries

### Get Full Conversation with Messages

```sql
SELECT 
  c.id,
  c.title,
  c.user_id,
  c.message_count,
  c.status,
  m.id as msg_id,
  m.role,
  m.content,
  m.msg_metadata,
  m.created_at
FROM conversations c
LEFT JOIN messages m ON c.id = m.conversation_id
WHERE c.id = 'YOUR_CONVERSATION_ID_HERE'
ORDER BY m.created_at ASC;
```

### Find by Request ID

```sql
SELECT 
  m.id,
  m.conversation_id,
  m.role,
  m.content,
  substr(m.created_at, 1, 19) as time,
  json_extract(m.msg_metadata, '$.latency_ms') as latency_ms
FROM messages m
WHERE json_extract(m.msg_metadata, '$.request_id') = 'YOUR_REQUEST_ID_HERE';
```

### Performance Stats

```sql
SELECT 
  json_extract(msg_metadata, '$.source') as source,
  COUNT(*) as count,
  ROUND(AVG(CAST(json_extract(msg_metadata, '$.latency_ms') AS NUMERIC)), 2) as avg_latency_ms,
  ROUND(AVG(CAST(json_extract(msg_metadata, '$.tokens') AS NUMERIC)), 0) as avg_tokens
FROM messages
WHERE json_extract(msg_metadata, '$.latency_ms') IS NOT NULL
GROUP BY source
ORDER BY avg_latency_ms DESC;
```

### Latest Messages

```sql
SELECT 
  m.role,
  substr(m.content, 1, 60) as content,
  substr(m.created_at, 12, 8) as time,
  json_extract(m.msg_metadata, '$.source') as source
FROM messages m
ORDER BY m.created_at DESC
LIMIT 20;
```

---

## Python Quick Commands

### In Python REPL

```python
from database import db

# Initialize
db.initialize()

# Get conversations
convs = db.list_conversations(user_id="default_user")
print(f"Conversations: {len(convs)}")

# Get messages from first conversation
if convs:
    msgs = db.get_last_n_messages(convs[0]['id'], n=10)
    for m in msgs:
        print(f"{m['role']}: {m['content'][:50]}")

db.shutdown()
```

### Print Pretty

```python
import json
from database import db

db.initialize()

convs = db.list_conversations(user_id="default_user")
for c in convs[:3]:  # First 3
    msgs = db.get_last_n_messages(c['id'], n=5)
    print(f"\n🔷 {c['title']} ({c['message_count']} msgs)")
    for m in msgs:
        print(f"  {m['role'].upper()}: {m['content'][:40]}...")

db.shutdown()
```

---

## Database Statistics

### Using Python

```python
from database import db
import json

db.initialize()

# Count everything
convs = db.list_conversations(user_id="default_user", include_archived=True)
total_convs = len(convs)
total_msgs = sum(c['message_count'] for c in convs)
active = len([c for c in convs if c['status'] == 'ACTIVE'])

print(f"📊 Database Statistics")
print(f"  Total conversations: {total_convs}")
print(f"  Active: {active}")
print(f"  Archived: {total_convs - active}")
print(f"  Total messages: {total_msgs}")
print(f"  Avg messages/conv: {total_msgs / total_convs if total_convs > 0 else 0:.1f}")

db.shutdown()
```

### Using SQL

```sql
SELECT 
  'Conversations' as metric, COUNT(*) as value FROM conversations
UNION ALL
SELECT 'Messages', COUNT(*) FROM messages
UNION ALL
SELECT 'Active Convs', COUNT(*) FROM conversations WHERE status='ACTIVE'
UNION ALL
SELECT 'Archived Convs', COUNT(*) FROM conversations WHERE status='ARCHIVED';
```

---

## Export/Backup

### Backup (Bash)

```bash
cp organic-fishstick.db organic-fishstick.db.backup.$(date +%Y%m%d_%H%M%S)
```

### Export to JSON (Python)

```python
import json
from database import db

db.initialize()
convs = db.list_conversations(user_id="default_user", include_archived=True)

data = {'conversations': convs, 'messages': []}
for c in convs:
    data['messages'].extend(db.get_last_n_messages(c['id'], n=1000))

with open('export.json', 'w') as f:
    json.dump(data, f, indent=2, default=str)

print(f"✅ Exported to export.json")
db.shutdown()
```

---

## Clear/Reset

### ⚠️ Delete All Data (Careful!)

```bash
# Backup first!
cp organic-fishstick.db organic-fishstick.db.backup

# Delete
rm organic-fishstick.db

# Fresh start
source vecna/bin/activate
python -c "from database import db; db.initialize()"
```

### Archive a Conversation

```python
from database import db

db.initialize()
db.archive_conversation('CONVERSATION_ID_HERE')
db.shutdown()
```

---

## Common Tasks

### Q: How do I view all conversations?
**A:** 
```bash
sqlite3 organic-fishstick.db "SELECT id, title, message_count, status FROM conversations;"
```

### Q: How do I see messages in a specific conversation?
**A:**
```bash
sqlite3 organic-fishstick.db "SELECT role, substr(content, 1, 60) FROM messages WHERE conversation_id='CONV_ID' ORDER BY created_at;"
```

### Q: How do I find slow responses?
**A:**
```bash
sqlite3 organic-fishstick.db "SELECT json_extract(msg_metadata, '$.latency_ms') as latency, substr(created_at, 12, 8) as time FROM messages WHERE json_extract(msg_metadata, '$.latency_ms') > 1000 ORDER BY latency DESC;"
```

### Q: How do I check token usage?
**A:**
```bash
sqlite3 organic-fishstick.db "SELECT role, SUM(CAST(json_extract(msg_metadata, '$.tokens') AS NUMERIC)) as total_tokens FROM messages WHERE json_extract(msg_metadata, '$.tokens') IS NOT NULL GROUP BY role;"
```

### Q: How do I export data?
**A:** See "Export to JSON (Python)" above

### Q: How do I restore from backup?
**A:**
```bash
cp organic-fishstick.db.backup organic-fishstick.db
```

---

## Column Reference

### conversations table
- `id` - Unique identifier (UUID)
- `user_id` - User identifier
- `title` - Conversation title
- `status` - ACTIVE, ARCHIVED, CLOSED, DELETED
- `message_count` - Total messages in conversation
- `last_message_at` - Timestamp of most recent message
- `archived_at` - When archived (if status=ARCHIVED)
- `created_at` - When created
- `updated_at` - Last update

### messages table
- `id` - Unique identifier (UUID)
- `conversation_id` - Parent conversation
- `role` -user, assistant, or system
- `content` - Full message text
- `msg_metadata` - JSON with request_id, tokens, latency_ms, source, etc.
- `created_at` - When sent
- `updated_at` - Always = created_at (immutable)

---

## File Locations

```
/workspaces/organic-fishstick-RAG/
├── organic-fishstick.db              # SQLite database file
├── database/
│   ├── SCHEMA.md               # Complete schema documentation
│   ├── VIEWING_DATABASE.md     # This guide (detailed)
│   ├── QUICK_REFERENCE.md      # This file (quick queries)
│   ├── models/
│   │   ├── conversation.py
│   │   └── message.py
│   ├── core/
│   │   ├── config.py
│   │   ├── engine.py
│   │   └── session.py
│   ├── repository/
│   │   └── conversation_repository.py
│   │   └── message_repository.py
│   └── __init__.py             # DatabaseManager facade
```

---

See [SCHEMA.md](SCHEMA.md) for complete documentation and [VIEWING_DATABASE.md](VIEWING_DATABASE.md) for detailed viewing guide.
