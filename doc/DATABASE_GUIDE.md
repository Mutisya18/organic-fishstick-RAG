# Database Guide - Access, Navigation & Operations

## 📚 Table of Contents

1. [Database Overview](#database-overview)
2. [Schema Design](#schema-design)
3. [Accessing the Database](#accessing-the-database)
4. [Viewing & Querying Data](#viewing--querying-data)
5. [Common Operations](#common-operations)
6. [Performance & Optimization](#performance--optimization)
7. [Backup & Recovery](#backup--recovery)
8. [Troubleshooting](#troubleshooting)

---

## 🗄️ Database Overview

### **Database Specifications**

| Property | Value | Notes |
|----------|-------|-------|
| **Type** | SQLite (dev) / PostgreSQL (prod) | Migratable schema |
| **File Location** | `organic-fishstick.db` | In project root |
| **ORM** | SQLAlchemy | Python database abstraction |
| **Migrations** | Alembic (optional) | Version control for schema |
| **Encoding** | UTF-8 | Unicode support for all fields |
| **Free Disk Space Required** | ~50MB (start) | Grows with conversations |

### **Connection String**

```bash
# SQLite (development)
DATABASE_URL=sqlite:///organic-fishstick.db

# PostgreSQL (production)
DATABASE_URL=postgresql://user:password@localhost:5432/organic_fishstick

# Environment Variable
echo $DATABASE_URL
```

### **Database Size**

```bash
# Check SQLite database size
du -h organic-fishstick.db

# Check directory size
du -sh db/  # If separate
```

---

## 📊 Schema Design

### **Entity Relationship Diagram**

```
┌─────────────────────────────────────────────────────────────────┐
│                          users                                   │
│                                                                   │
│ PK: user_id (email)                                             │
│ ├─ email (UNIQUE)                                               │
│ ├─ password_hash                                                │
│ ├─ full_name                                                    │
│ ├─ is_active (Boolean)                                          │
│ ├─ created_at (DateTime)                                        │
│ └─ last_login (DateTime)                                        │
└──────┬──────────────────────────────────────────────────────────┘
       │
       │ 1:N (One user has many sessions)
       │
       ▼
┌─────────────────────────────────────────────────────────────────┐
│                     user_sessions                                │
│                                                                   │
│ PK: id                                                           │
│ FK: user_id → users.user_id                                     │
│ ├─ session_token (UNIQUE)                                       │
│ ├─ created_at (DateTime)                                        │
│ ├─ expires_at (DateTime)                                        │
│ ├─ last_activity_at (DateTime)                                  │
│ └─ is_expired (Boolean)                                         │
└──────┬──────────────────────────────────────────────────────────┘
       │
       │
───────┼──────────────────────────────────┐
       │                                  │
       │ 1:N                              │ 1:N
       │                                  │
       ▼                                  ▼
┌──────────────────────────────────┐   ┌──────────────────────────────────┐
│     conversations                │   │   (other relationships)          │
│                                  │   │                                  │
│ PK: id (UUID)                    │   └──────────────────────────────────┘
│ FK: user_id → users.user_id      │
│ ├─ title (Conversation topic)    │
│ ├─ status (ACTIVE/ARCHIVED/...)  │
│ ├─ message_count (Integer)       │
│ ├─ created_at (DateTime)         │
│ ├─ last_message_at (DateTime)    │
│ ├─ is_hidden (Boolean)           │
│ ├─ auto_hidden (Boolean)         │
│ └─ last_opened_at (DateTime)     │
└────────┬────────────────────────┘
         │
         │ 1:N (One conversation has many messages)
         │ FK: Cascade Delete
         │
         ▼
┌──────────────────────────────────────────────────────────────┐
│                       messages                                │
│                                                               │
│ PK: id (UUID)                                                │
│ FK: conversation_id → conversations.id (CASCADE DELETE)      │
│ ├─ role (Enum: USER, ASSISTANT, SYSTEM)                    │
│ ├─ content (Long text)                                      │
│ ├─ created_at (DateTime)                                    │
│ └─ msg_metadata (JSON)                                      │
│    ├─ request_id                                            │
│    ├─ source                                                │
│    ├─ tokens                                                │
│    ├─ model_name                                            │
│    └─ latency_ms                                            │
└──────────────────────────────────────────────────────────────┘
```

### **Detailed Table Specifications**

#### **users Table**
```sql
CREATE TABLE users (
    user_id VARCHAR(255) PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_login DATETIME,
    metadata TEXT  -- JSON string
);

-- Indexes
CREATE INDEX idx_email ON users(email);
CREATE INDEX idx_is_active ON users(is_active);
```

**Sample Data:**
```
user_id              | email                | full_name | is_active | created_at
admin@example.com    | admin@example.com    | Admin     | 1         | 2026-02-10 10:00:00
user1@example.com    | user1@example.com    | John Doe  | 1         | 2026-02-11 14:30:00
```

#### **user_sessions Table**
```sql
CREATE TABLE user_sessions (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    session_token VARCHAR(255) UNIQUE NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    expires_at DATETIME NOT NULL,
    last_activity_at DATETIME,
    is_expired BOOLEAN DEFAULT FALSE,
    FOREIGN KEY(user_id) REFERENCES users(user_id)
);

-- Indexes
CREATE INDEX idx_session_token ON user_sessions(session_token);
CREATE INDEX idx_user_active_sessions ON user_sessions(user_id, is_expired);
```

#### **conversations Table**
```sql
CREATE TABLE conversations (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    title VARCHAR(255),
    status VARCHAR(20) DEFAULT 'ACTIVE',  -- Enum
    message_count INTEGER DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_message_at DATETIME,
    archived_at DATETIME,
    is_hidden BOOLEAN DEFAULT FALSE,
    hidden_at DATETIME,
    auto_hidden BOOLEAN DEFAULT FALSE,
    last_opened_at DATETIME,
    FOREIGN KEY(user_id) REFERENCES users(user_id)
);

-- Indexes
CREATE INDEX idx_user_id ON conversations(user_id);
CREATE INDEX idx_status ON conversations(status);
CREATE INDEX idx_is_hidden ON conversations(is_hidden);
CREATE INDEX idx_last_message ON conversations(user_id, last_message_at);
CREATE INDEX idx_visibility_priority ON conversations(user_id, is_hidden, last_opened_at, last_message_at);
```

#### **messages Table**
```sql
CREATE TABLE messages (
    id VARCHAR(36) PRIMARY KEY,
    conversation_id VARCHAR(36) NOT NULL,
    role VARCHAR(20) NOT NULL,  -- 'user', 'assistant', 'system'
    content TEXT NOT NULL,
    msg_metadata JSON,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
);

-- Indexes
CREATE INDEX idx_conversation_id ON messages(conversation_id);
CREATE INDEX idx_role ON messages(role);
CREATE INDEX idx_conversation_created ON messages(conversation_id, created_at);
CREATE INDEX idx_role_created ON messages(role, created_at);
```

---

## 🔌 Accessing the Database

### **Option 1: SQLite Command Line**

```bash
# Open database
sqlite3 organic-fishstick.db

# Common commands:
.tables                    # List all tables
.schema users              # Show table structure
.mode column              # Pretty-print output
.headers on               # Show column headers
.exit                     # Exit SQLite shell
```

### **Option 2: Python SQLAlchemy**

```python
from database import db
from database.models import User, Conversation, Message

# Initialize (if not already)
db.initialize()

# Get session
from database.core.session import SessionLocal
session = SessionLocal()

# Query examples (see next section)
users = session.query(User).all()
conversations = session.query(Conversation).filter_by(user_id="user@example.com").all()

# Always close session
session.close()
```

### **Option 3: GUI Tools**

#### **DB Browser for SQLite**
```bash
# Installation (macOS)
brew install sqlitebrowser

# Open database
sqlitebrowser organic-fishstick.db

# Features:
# - Visual schema explorer
# - SQL query editor
# - Data browser with filtering
# - Export to CSV/JSON
```

#### **DBeaver** (Multi-database)
```bash
# Download from https://dbeaver.io/
# Supports SQLite, PostgreSQL, MySQL, etc.
# Features: Query editor, ER diagrams, data sync
```

### **Option 4: Web-based Interface (Python)**

```bash
# Install Flask-based database browser
pip install flask-sqlalchemy-browser

# Run browser
python -c "
from flask import Flask
from flask_sqlalchemy_browser import admin
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///organic-fishstick.db'
admin.init_app(app)
app.run(debug=True, port=5000)
"

# Access: http://localhost:5000
```

---

## 📋 Viewing & Querying Data

### **SQLite CLI Examples**

#### **View All Users**
```sql
sqlite> SELECT user_id, email, full_name, is_active, created_at FROM users;

user_id              email                 full_name    is_active created_at
-------------------  -------------------  -----------  --------- ----------
admin@example.com    admin@example.com    Admin        1         2026-02-10
user1@example.com    user1@example.com    John Doe     1         2026-02-11
```

#### **View Conversations for a User**
```sql
sqlite> SELECT id, title, status, message_count, last_message_at 
        FROM conversations 
        WHERE user_id = 'user1@example.com';

id                                title                  status   message_count last_message_at
----------------------------------  -------------------  ------   ------------- ---
550e8400-e29b-41d4-a716-446655440000  Eligibility Q       ACTIVE   5             2026-02-15 14:20:00
```

#### **View Messages in a Conversation**
```sql
sqlite> SELECT role, content, created_at FROM messages 
        WHERE conversation_id = '550e8400-e29b-41d4-a716-446655440000'
        ORDER BY created_at;

role        content                              created_at
----------  -----------------------------------  ---
user        What is account eligibility?       2026-02-15 14:15:00
assistant   The eligibility is determined by... 2026-02-15 14:15:30
user        What about joint accounts?         2026-02-15 14:18:00
assistant   Joint accounts must...              2026-02-15 14:18:15
```

#### **View Message Metadata**
```sql
sqlite> SELECT id, role, msg_metadata FROM messages 
        WHERE conversation_id = '550e8400-e29b-41d4-a716-446655440000' 
        LIMIT 1;
```

Output:
```json
{
  "request_id": "req-550e8400",
  "source": "llm_generation",
  "tokens": 245,
  "model_name": "llama3.2:3b",
  "latency_ms": 1234,
  "sources": [
    {
      "source": "document.pdf",
      "page": 5,
      "score": 0.87
    }
  ]
}
```

### **Python SQLAlchemy Examples**

#### **Count Users**
```python
from database.models import User
from database.core.session import SessionLocal

session = SessionLocal()
count = session.query(User).count()
print(f"Total users: {count}")
session.close()
```

#### **Get User by Email**
```python
user = session.query(User).filter_by(email="user@example.com").first()
if user:
    print(f"User: {user.full_name}, Last login: {user.last_login}")
else:
    print("User not found")
```

#### **List All Conversations for User**
```python
from database.models import Conversation

user_id = "user@example.com"
conversations = (
    session.query(Conversation)
    .filter_by(user_id=user_id)
    .order_by(Conversation.last_message_at.desc())
    .all()
)

for conv in conversations:
    print(f"{conv.title} ({conv.message_count} messages)")
```

#### **Get All Messages in Conversation**
```python
from database.models import Message
from sqlalchemy import asc

conversation_id = "550e8400-e29b-41d4-a716-446655440000"
messages = (
    session.query(Message)
    .filter_by(conversation_id=conversation_id)
    .order_by(asc(Message.created_at))
    .all()
)

for msg in messages:
    print(f"[{msg.role.upper()}]: {msg.content[:50]}...")
    print(f"  Request ID: {msg.request_id}")
    print(f"  Latency: {msg.latency_ms}ms")
```

#### **Search Messages by Content**
```python
search_term = "eligibility"
messages = (
    session.query(Message)
    .filter(Message.content.ilike(f"%{search_term}%"))
    .all()
)

print(f"Found {len(messages)} messages containing '{search_term}'")
```

#### **Get Active Sessions**
```python
from database.models import UserSession
from datetime import datetime

active_sessions = (
    session.query(UserSession)
    .filter(
        UserSession.is_expired == False,
        UserSession.expires_at > datetime.utcnow()
    )
    .all()
)

print(f"Active sessions: {len(active_sessions)}")
```

---

## 🔧 Common Operations

### **User Management**

#### **Create User** (Python)
```python
from auth.password import hash_password
from database.models import User
from database.core.session import SessionLocal

session = SessionLocal()

user = User(
    user_id="newuser@example.com",
    email="newuser@example.com",
    password_hash=hash_password("secure_password_123"),
    full_name="New User",
    is_active=True
)

session.add(user)
session.commit()
print(f"User created: {user.user_id}")
session.close()
```

#### **Activate/Deactivate User**
```python
user = session.query(User).filter_by(email="user@example.com").first()
user.is_active = False
session.commit()
print(f"User {user.email} deactivated")
```

#### **Delete User** (Cascades to conversations & messages)
```python
user = session.query(User).filter_by(email="user@example.com").first()
session.delete(user)  # Will cascade delete conversations & messages
session.commit()
print(f"User deleted: {user.email}")
```

### **Conversation Management**

#### **Archive Conversation**
```python
from database.models import Conversation, ConversationStatus

conversation = session.query(Conversation).filter_by(
    id="550e8400-e29b-41d4-a716-446655440000"
).first()

conversation.archive()  # Sets status=ARCHIVED, archived_at=now
session.commit()
print(f"Conversation archived: {conversation.title}")
```

#### **List Hidden Conversations**
```python
hidden_conversations = (
    session.query(Conversation)
    .filter_by(is_hidden=True)
    .all()
)

for conv in hidden_conversations:
    print(f"Hidden: {conv.title} (auto_hidden={conv.auto_hidden})")
```

#### **Un-hide Conversation**
```python
conversation.unhide()  # Sets is_hidden=False
session.commit()
```

#### **Delete Conversation** (Cascades to messages)
```python
session.delete(conversation)  # Will delete all messages
session.commit()
```

### **Message Operations**

#### **Count Messages by Role**
```python
from database.models import Message, MessageRole

user_messages = session.query(Message).filter_by(
    role=MessageRole.USER
).count()

assistant_messages = session.query(Message).filter_by(
    role=MessageRole.ASSISTANT
).count()

print(f"User messages: {user_messages}")
print(f"Assistant messages: {assistant_messages}")
```

#### **Get Tokens by Message**
```python
total_tokens = 0
for msg in messages:
    if msg.tokens:
        total_tokens += msg.tokens
        
print(f"Total tokens used: {total_tokens}")
```

#### **Find Slow Responses** (> 2000ms)
```python
from sqlalchemy import and_
import json

slow_messages = (
    session.query(Message)
    .filter(Message.msg_metadata.ilike('%"latency_ms": %'))
    .all()  # Fetch and filter in Python (SQLite limitation)
)

slow_responses = []
for msg in slow_messages:
    if msg.msg_metadata and msg.latency_ms and msg.latency_ms > 2000:
        slow_responses.append(msg)

print(f"Found {len(slow_responses)} slow responses")
```

---

## ⚡ Performance & Optimization

### **Database Indexing**

Current indexes are optimized for:
- User lookups by email or ID
- Conversation queries by user and status
- Message queries by conversation
- Hidden/Active conversation filtering

### **Query Performance Tips**

```python
# ✅ GOOD: Indexed queries
user = session.query(User).filter_by(email="user@example.com").first()

# ❌ SLOW: Full table scan
users = [u for u in session.query(User).all() if u.full_name == "John"]

# ✅ GOOD: Parameterized queries
conversations = session.query(Conversation).filter_by(
    user_id=user_id,
    status=status
).all()

# ❌ SLOW: String concatenation
conversations = session.query(Conversation).filter(
    f"user_id = '{user_id}' AND status = '{status}'"
).all()
```

### **Monitoring Database Size**

```bash
# Check current size
ls -lh organic-fishstick.db

# Monitor growth over time
du -h organic-fishstick.db > ~/db_size_$(date +%s).txt

# Vacuum (compact database)
sqlite3 organic-fishstick.db "VACUUM;"
```

### **Connection Pooling**

For production (PostgreSQL):
```python
from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool

engine = create_engine(
    database_url,
    poolclass=QueuePool,
    pool_size=10,        # Number of connections to keep
    max_overflow=20,     # Extra connections allowed
    pool_recycle=3600    # Recycle connections after 1 hour
)
```

---

## 💾 Backup & Recovery

### **SQLite Backup**

#### **Manual Backup**
```bash
# Simple file copy
cp organic-fishstick.db organic-fishstick.db.backup

# Backup with timestamp
cp organic-fishstick.db "organic-fishstick.db.backup.$(date +%Y%m%d_%H%M%S)"

# Online backup (recommended)
sqlite3 organic-fishstick.db ".backup organic-fishstick.db.backup"
```

#### **Automated Backup (Cron)**
```bash
# Add to crontab:
# Backup daily at 2 AM
0 2 * * * cp /path/to/organic-fishstick.db /backups/db_$(date +\%Y\%m\%d).db

# Rotate old backups (keep last 30 days)
0 3 * * * find /backups -name "db_*.db" -mtime +30 -delete
```

#### **Remote Backup**
```bash
# SCP to remote server
scp organic-fishstick.db user@backup-server:/backups/

# Rsync (efficient)
rsync -avz organic-fishstick.db user@backup-server:/backups/
```

### **Recovery**

#### **Restore from Backup**
```bash
# Restore latest backup
cp organic-fishstick.db.backup organic-fishstick.db

# Restart application
bash start_portal.sh
```

#### **Export Data for Safekeeping**

```bash
# Export all data as SQL
sqlite3 organic-fishstick.db ".dump" > backup.sql

# Export as CSV
sqlite3 organic-fishstick.db << EOF
.mode csv
.output users.csv
SELECT * FROM users;
.output conversations.csv
SELECT * FROM conversations;
.output messages.csv
SELECT * FROM messages;
EOF
```

#### **Restore from SQL Dump**
```bash
# Recreate database from dump
sqlite3 new_database.db < backup.sql
```

---

## 🐛 Troubleshooting

### **Database Is Locked**

**Error:** `database is locked`

**Causes:**
- Multiple processes accessing SQLite simultaneously
- Previous process crashed while holding lock
- File permissions issue

**Solutions:**
```bash
# 1. Check file permissions
ls -la organic-fishstick.db
chmod 644 organic-fishstick.db

# 2. Kill processes using database
lsof +L1 organic-fishstick.db

# 3. Restart application
bash start_portal.sh

# 4. As last resort, recreate
rm organic-fishstick.db
python -c "from database.initialization import initialize_database; initialize_database()"
```

### **Corrupted Database**

**Error:** `database or disk is full` or `file is not a database`

**Recovery:**
```bash
# 1. Check integrity
sqlite3 organic-fishstick.db "PRAGMA integrity_check;"

# 2. Dump and restore
sqlite3 organic-fishstick.db ".dump" > temp.sql

# 3. Remove corrupted database
rm organic-fishstick.db

# 4. Restore from dump or backup
sqlite3 organic-fishstick.db < temp.sql
```

### **Slow Queries**

**Diagnosis:**
```bash
# Enable query profiling
python -c "
import logging
logging.basicConfig()
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)
"

# Run slow query and check logs
```

**Solution: Add Indexes**
```python
# In database/models/message.py, add:
__table_args__ = (
    Index('idx_conversation_created', 'conversation_id', 'created_at'),
    Index('idx_model_latency', 'model_name', 'latency_ms'),  # NEW
)
```

### **Large Database Size**

**Check what's using space:**
```python
from database.models import Message, Conversation
from database.core.session import SessionLocal

session = SessionLocal()

# Message count
msg_count = session.query(Message).count()
print(f"Total messages: {msg_count}")

# Large conversations
large_convs = (
    session.query(Conversation)
    .order_by(Conversation.message_count.desc())
    .limit(10)
    .all()
)

for conv in large_convs:
    print(f"{conv.title}: {conv.message_count} messages")

session.close()
```

**Cleanup:**
```python
# Archive old conversations
cutoff_date = datetime(2026, 1, 1)
old_conversations = session.query(Conversation).filter(
    Conversation.last_message_at < cutoff_date
).all()

for conv in old_conversations:
    conv.archive()

session.commit()

# Delete archived > 90 days
from datetime import timedelta

very_old = datetime.utcnow() - timedelta(days=90)
archived_conversations = session.query(Conversation).filter(
    Conversation.archived_at < very_old
).all()

for conv in archived_conversations:
    session.delete(conv)

session.commit()
```

### **Connection Pool Exhausted**

**Error:** `QueuePool limit exceeded with overflow`

**Solution:**
```python
# Increase pool size in database/core/engine.py
engine = create_engine(
    database_url,
    pool_size=15,      # Increase from 10
    max_overflow=25    # Increase from 20
)
```

---

## 📖 Related Documentation

- [SYSTEM_ARCHITECTURE.md](SYSTEM_ARCHITECTURE.md) - System design
- [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md) - Development guide
- [STARTUP_GUIDE.md](STARTUP_GUIDE.md) - Setup guide

---

**Last Updated:** February 15, 2026  
**Version:** 1.0  
**Database Type:** SQLite (Development)
