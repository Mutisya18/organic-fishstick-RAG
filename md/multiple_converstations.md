# Multi-Conversation System: Implementation Specification
## Version 1.0 | Feature: Conversation Limit Management

---

# Executive Summary

This specification defines the implementation of a multi-conversation system with intelligent activity-based limiting. The system allows users to maintain up to 20 active conversations, with automatic hiding of least-recently-used conversations based on a dual-factor prioritization algorithm (viewing activity + message activity).

**Core Principle**: Users see their 20 most relevant conversations. Relevance is determined by both when they last opened a conversation and when it last had message activity.

---

# 1. Database Schema Modifications

## 1.1 New Columns Required

### Conversations Table
Add the following columns to the existing `conversations` table:

| Column Name | Type | Nullable | Default | Index | Description |
|------------|------|----------|---------|-------|-------------|
| `is_hidden` | BOOLEAN | NO | FALSE | YES | System-imposed hidden state (NOT user archive) |
| `hidden_at` | TIMESTAMP | YES | NULL | NO | When conversation was auto-hidden (audit trail) |
| `auto_hidden` | BOOLEAN | NO | FALSE | YES | Audit flag: 1=system auto-hid, 0=user action (compliance marker) |
| `last_opened_at` | TIMESTAMP | YES | NULL | YES | When user last switched to this conversation in UI |

### Index Strategy
Create composite index for efficient conversation listing:
```sql
INDEX idx_conversations_visibility_priority 
ON conversations(user_id, is_hidden, last_opened_at DESC, last_message_at DESC)
WHERE is_hidden = FALSE
```

**Rationale**: This index supports the query pattern: "Get top 20 non-hidden conversations for user, ordered by relevance."

---

## 1.2 Data Migration Considerations

### For Existing Conversations
- All existing conversations get `is_hidden = FALSE`
- All existing conversations get `auto_hidden = 0`
- All existing conversations get `last_opened_at = created_at` (seed with creation date)

**No conversations are hidden during migration** - this is a forward-only feature.

---

# 2. Configuration Management

## 2.1 Environment Variables

Add to `.env` and `.env.example`:

```bash
# Conversation limit settings
MAX_ACTIVE_CONVERSATIONS=20
CONVERSATION_WARNING_THRESHOLD=15

# Feature flag (for gradual rollout)
ENABLE_CONVERSATION_LIMIT=true
```

## 2.2 Configuration Loading

**Backend (Python)**:
```python
# rag/config/conversation_limits.py (new file)
import os

MAX_ACTIVE_CONVERSATIONS = int(os.getenv("MAX_ACTIVE_CONVERSATIONS", "20"))
WARNING_THRESHOLD = int(os.getenv("CONVERSATION_WARNING_THRESHOLD", "15"))
ENABLE_LIMIT = os.getenv("ENABLE_CONVERSATION_LIMIT", "true").lower() == "true"
```

**Frontend (JavaScript)**:
```javascript
// Fetch from backend on init
GET /api/config/limits
Response: { maxConversations: 20, warningThreshold: 15, enabled: true }
```

**Rationale**: Backend is source of truth. Frontend queries config on app load.

---

# 3. Business Logic Rules

## 3.1 Conversation Visibility Algorithm

### Prioritization Formula: Dual-Factor Relevance Score

Each conversation gets a relevance score based on two factors:

**Factor 1: Last Opened (Weight: 60%)**
- When user last switched to this conversation in the UI
- Represents explicit user interest

**Factor 2: Last Activity (Weight: 40%)**
- When last message was sent/received
- Represents ongoing conversation momentum

**Combined Scoring**:
```
relevance_score = (last_opened_at_unix * 0.6) + (last_message_at_unix * 0.4)
```

**Ranking Logic**:
1. Calculate relevance score for all non-hidden conversations
2. Sort by relevance score DESC
3. Top 20 remain visible
4. 21st and beyond get auto-hidden

### Edge Case Handling

**Scenario 1: Null Values**
- If `last_opened_at` is NULL, use `created_at` as fallback
- If `last_message_at` is NULL (no messages yet), use `created_at` as fallback

**Scenario 2: Simultaneous Creates**
- If 21st conversation created while user has exactly 20 visible
- Trigger hiding algorithm immediately after conversation creation succeeds
- Recalculate all scores, hide lowest-scoring conversation

**Scenario 3: Currently Active Conversation is Lowest Scoring**
- User is viewing conversation A
- User creates conversation 21
- Conversation A has lowest relevance score
- **Protection**: Do NOT hide currently active conversation
- Instead, hide the 2nd-lowest scoring conversation

**Implementation Note**: Track `activeConversationId` in session/state to enforce protection.

---

## 3.2 Auto-Hiding Trigger Points

### When to Check for Auto-Hiding

**Trigger Event**: Conversation creation (POST /api/conversations)

**Algorithm**:
```
1. User creates new conversation
2. Count non-hidden conversations for this user
3. If count > MAX_ACTIVE_CONVERSATIONS:
   a. Calculate relevance scores for all non-hidden conversations
   b. Exclude currently active conversation from hiding candidates
   c. Sort by score ASC (lowest first)
   d. Hide lowest-scoring conversation
   e. Set is_hidden=TRUE, hidden_at=NOW(), auto_hidden=1
   f. Return new conversation to frontend
```

**Not Triggered By**:
- Sending messages (updating existing conversation)
- Renaming conversations
- Switching between conversations
- User-initiated archiving

**Rationale**: Only check on creation to minimize database overhead.

---

## 3.3 Warning System

### Warning Conditions

**Trigger**: When creating a conversation that brings total to exactly 15

**Behavior**:
- Backend response includes warning flag
- Frontend displays toast notification (one-time, session-scoped)
- Warning is NOT shown again in the same session

**Warning Message**:
```
"You have 15 active conversations. At 20, older conversations will be automatically archived."
```

**Session Scope Implementation**:
- Store `conversationLimitWarningShown` in frontend session state
- Reset on page refresh
- Do NOT persist to localStorage (fresh warning on each session)

---

# 4. API Specifications

## 4.1 Modified Endpoints

### GET /api/conversations/list

**Request**:
```
GET /api/conversations?user_id={user_id}
```

**Query Behavior**:
```sql
SELECT * FROM conversations 
WHERE user_id = :user_id 
  AND is_hidden = FALSE
  AND status = 'ACTIVE'
ORDER BY 
  (COALESCE(last_opened_at, created_at) * 0.6 + 
   COALESCE(last_message_at, created_at) * 0.4) DESC
LIMIT 20;
```

**Response**:
```json
{
  "conversations": [
    {
      "id": "uuid",
      "title": "Eligibility - Account ***7890",
      "last_message_at": "2026-02-14T10:30:00Z",
      "last_opened_at": "2026-02-14T12:00:00Z",
      "message_count": 15,
      "preview": "The customer is not eligible...",
      "status": "active",
      "is_hidden": false
    }
  ],
  "visible_count": 17,
  "max_allowed": 20,
  "warning": false
}
```

**New Fields**:
- `visible_count`: Number of non-hidden conversations for this user
- `max_allowed`: Configuration value (20)
- `warning`: Boolean flag if count >= WARNING_THRESHOLD

---

### POST /api/conversations/create

**Request**:
```json
{
  "title": "New Conversation",  // Optional
  "user_id": "default_user"
}
```

**Backend Logic**:
```
1. Create new conversation (status=ACTIVE, is_hidden=FALSE)
2. Count non-hidden conversations for user
3. If count > MAX_ACTIVE_CONVERSATIONS:
   a. Calculate relevance scores
   b. Exclude activeConversationId (from session/state)
   c. Hide lowest-scoring conversation
4. If new count == WARNING_THRESHOLD:
   a. Set warning flag in response
5. Return new conversation + metadata
```

**Response**:
```json
{
  "conversation": {
    "id": "uuid",
    "title": "New Conversation",
    "created_at": "2026-02-14T12:00:00Z",
    "last_opened_at": "2026-02-14T12:00:00Z",
    "status": "active"
  },
  "visible_count": 15,
  "max_allowed": 20,
  "warning": true,
  "auto_hidden": {
    "occurred": true,
    "conversation_id": "uuid-of-hidden-conversation",
    "reason": "limit_exceeded"
  }
}
```

**Note**: `auto_hidden` object only present if hiding occurred.

---

### PATCH /api/conversations/{id}/open

**New Endpoint**: Track when user switches to a conversation

**Request**:
```
PATCH /api/conversations/{id}/open
```

**Backend Logic**:
```sql
UPDATE conversations 
SET last_opened_at = NOW() 
WHERE id = :id;
```

**Response**:
```json
{
  "id": "uuid",
  "last_opened_at": "2026-02-14T12:00:00Z"
}
```

**When to Call**: Every time user clicks a conversation in the sidebar to switch to it.

**Rationale**: This updates the "last viewed" timestamp for prioritization algorithm.

---

### POST /api/chat/send (Modified)

**Current Behavior**: Already updates `last_message_at` via database trigger

**No Changes Required**: Message sending already updates conversation activity timestamp.

---

## 4.2 New Endpoints

### GET /api/config/limits

**Request**:
```
GET /api/config/limits
```

**Response**:
```json
{
  "maxConversations": 20,
  "warningThreshold": 15,
  "enabled": true
}
```

**Purpose**: Frontend queries this on app initialization to get configuration values.

---

# 5. Frontend State Management

## 5.1 State Structure Extensions

### Existing State
```javascript
state = {
  user: { name, role },
  conversationId: "uuid",
  messages: []
}
```

### New State Structure
```javascript
state = {
  user: { name, role },
  
  conversations: {
    items: [],              // Array of conversation objects (max 20)
    activeId: null,         // Currently selected conversation
    visibleCount: 0,        // How many visible conversations user has
    maxAllowed: 20,         // From config
    warningThreshold: 15,   // From config
    warningShown: false     // Session flag for one-time warning
  },
  
  messages: []              // Messages for active conversation
}
```

---

## 5.2 State Update Logic

### On App Load
```
1. GET /api/config/limits → Set maxAllowed, warningThreshold
2. GET /api/conversations → Set items, visibleCount
3. Set activeId to most recent conversation (or null if empty)
4. If activeId exists: GET /api/conversations/{activeId}/messages
```

### On Conversation Create
```
1. POST /api/conversations → Receive new conversation + metadata
2. If response.warning && !state.warningShown:
   a. Show toast: "You have 15 conversations..."
   b. Set state.warningShown = true
3. If response.auto_hidden.occurred:
   a. Remove hidden conversation from state.items
   b. (No notification - silent operation)
4. Add new conversation to state.items (top of list)
5. Set activeId = new conversation ID
6. Clear messages array
7. Update visibleCount
```

### On Conversation Switch
```
1. PATCH /api/conversations/{id}/open → Update last_opened_at
2. Set state.activeId = clicked conversation ID
3. GET /api/conversations/{id}/messages → Load messages
4. Render messages
```

### On Message Send
```
1. POST /api/chat/send → Send message
2. Append message to state.messages
3. Update conversation's last_message_at in state.items
4. (Backend automatically updates last_message_at)
```

---

# 6. UI Implementation Specifications

## 6.1 Conversation List Header

### Visual Design
```
┌─────────────────────────────────────┐
│ Conversations                  (17/20) │  <- Badge shows count
│ [+ New Chat]                          │
└─────────────────────────────────────┘
```

### Badge Behavior
- Shows: `({visible_count}/{max_allowed})`
- Color coding:
  - Green: 0-14 conversations
  - Yellow: 15-19 conversations
  - Red: 20 conversations (at limit)

### Implementation
```html
<div class="sidebar-header">
  <h2>Conversations</h2>
  <span class="conversation-count-badge" data-count="{visibleCount}">
    ({visibleCount}/{maxAllowed})
  </span>
</div>
```

---

## 6.2 Warning Toast

### Trigger
- When creating 15th conversation
- Only once per session

### Visual Design
```
┌─────────────────────────────────────────┐
│ ⚠️  You have 15 active conversations.   │
│    At 20, older conversations will be   │
│    automatically archived.              │
│                               [Dismiss] │
└─────────────────────────────────────────┘
```

### Behavior
- Appears for 8 seconds
- Dismissible via X button
- Yellow/amber color scheme
- Positioned: Top-right corner (toast pattern)

---

## 6.3 Conversation List Rendering

### Always Show Exactly 20 (or fewer)
- No pagination controls
- No "Show More" button
- No "View All" option

### Sorting
- Already sorted by backend (relevance score DESC)
- Frontend displays in received order

### No Hidden Conversation Indicators
- User does NOT see count of hidden conversations
- User does NOT see "X archived" message
- Hidden conversations are completely invisible

---

## 6.4 New Chat Button Behavior

### When at Limit (20 conversations)
- Button remains enabled
- Clicking creates new conversation
- Oldest (by relevance score) conversation silently disappears from list
- No confirmation dialog
- No notification that a conversation was hidden

**Rationale**: Seamless experience. User sees 20, creates 21st, still sees 20 (with new one added).

---

# 7. Edge Cases & Error Handling

## 7.1 Race Conditions

### Scenario: Rapid Conversation Creation
**Problem**: User clicks "New Chat" 5 times rapidly before first request completes

**Solution**:
- Disable "New Chat" button on click
- Re-enable only after response received
- Queue subsequent clicks (don't fire parallel requests)

---

### Scenario: Concurrent Sessions
**Problem**: User opens two browser tabs, creates conversations in both

**Solution**:
- Each session independently queries conversation list
- Server enforces limit at database level (transaction-safe)
- Both tabs see consistent state after refresh
- No special handling needed (database is source of truth)

---

## 7.2 Database Failures

### Scenario: Auto-Hide Update Fails
**Problem**: New conversation created, but hiding old one fails (DB error)

**Handling**:
```
1. Create conversation (succeeds)
2. Attempt auto-hide (fails)
3. Log error: "Auto-hide failed for user {user_id}"
4. Still return new conversation to user
5. Result: User temporarily has 21 visible conversations
6. Next conversation create will hide 2 conversations to compensate
```

**Rationale**: Never block conversation creation due to cleanup failure.

---

## 7.3 Configuration Changes

### Scenario: Admin Changes MAX_ACTIVE_CONVERSATIONS from 20 to 15

**Behavior**:
- No immediate enforcement
- Users with 20 conversations keep them
- Next conversation create triggers hiding to bring down to 15
- Graceful degradation

**Grandfather Policy**: Existing state is preserved until next limit check.

---

# 8. Audit & Compliance

## 8.1 Audit Trail Requirements

### What to Log

**When Conversation is Auto-Hidden**:
```json
{
  "event": "conversation_auto_hidden",
  "timestamp": "2026-02-14T12:00:00Z",
  "user_id": "default_user",
  "conversation_id": "uuid-of-hidden",
  "reason": "limit_exceeded",
  "relevance_score": 1234567890.5,
  "visible_count_before": 21,
  "visible_count_after": 20,
  "trigger": "conversation_created",
  "new_conversation_id": "uuid-of-new-conversation"
}
```

**When User Manually Archives** (future feature):
```json
{
  "event": "conversation_archived",
  "timestamp": "2026-02-14T12:00:00Z",
  "user_id": "default_user",
  "conversation_id": "uuid",
  "reason": "user_action",
  "auto_hidden": 0
}
```

### Database Markers

- `auto_hidden = 1`: System auto-hid this conversation
- `auto_hidden = 0`: User manually archived (or never hidden)

**Purpose**: Compliance audits can distinguish automated system actions from user actions.

---

## 8.2 Data Retention

### Hidden Conversations
- Retained indefinitely in database
- Status remains `ACTIVE` (not archived)
- `is_hidden = TRUE` marks them as hidden
- All messages preserved
- All metadata preserved

### Future Access
- No UI to recover hidden conversations (for now)
- Database admin can query: `WHERE is_hidden = TRUE AND auto_hidden = 1`
- Potential future feature: "Show Hidden Conversations" (separate implementation)

---

# 9. Testing Requirements

## 9.1 Unit Tests (Backend)

### Relevance Score Calculation
```
Test: Calculate relevance score correctly
Given: last_opened_at = 1000000, last_message_at = 500000
Expected: relevance_score = (1000000 * 0.6) + (500000 * 0.4) = 800000
```

### Null Handling
```
Test: Handle null last_opened_at
Given: last_opened_at = NULL, created_at = 1000000, last_message_at = 500000
Expected: Use created_at as fallback for last_opened_at
```

### Active Conversation Protection
```
Test: Don't hide currently active conversation
Given: 21 conversations, conversation #5 is active but has lowest score
Expected: Hide conversation #6 (2nd lowest score)
```

---

## 9.2 Integration Tests (API)

### Auto-Hide on Create
```
Test: Creating 21st conversation hides oldest
Setup: Create 20 conversations
Action: Create 21st conversation
Verify: 
  - 21st conversation exists and is visible
  - Oldest (by score) conversation is hidden
  - Response includes auto_hidden metadata
  - visible_count = 20
```

### Warning at Threshold
```
Test: Warning flag at 15 conversations
Setup: Create 14 conversations
Action: Create 15th conversation
Verify:
  - Response includes warning: true
  - visible_count = 15
```

### Update last_opened_at
```
Test: Opening conversation updates timestamp
Setup: Create conversation, wait 1 second
Action: PATCH /api/conversations/{id}/open
Verify: last_opened_at > created_at
```

---

## 9.3 End-to-End Tests (Frontend)

### Visual Counter Updates
```
Test: Badge shows correct count
Setup: User has 10 conversations
Action: Create new conversation
Verify: Badge shows (11/20)
```

### Warning Toast Appears
```
Test: Toast at 15 conversations
Setup: User has 14 conversations
Action: Create 15th conversation
Verify:
  - Toast appears with correct message
  - Toast dismissible
  - Toast doesn't appear on 16th conversation create (same session)
```

### Silent Auto-Hide
```
Test: No notification when conversation hidden
Setup: User has 20 conversations
Action: Create 21st conversation
Verify:
  - No error message
  - No confirmation dialog
  - Conversation list shows 20 items
  - New conversation is present
```

---

## 9.4 Load Tests

### Relevance Calculation Performance
```
Test: Handle 1000 conversations per user
Setup: Create 1000 conversations in database (980 hidden, 20 visible)
Action: GET /api/conversations
Measure: Query latency
Target: < 200ms
```

### Concurrent Creates
```
Test: Multiple users creating conversations simultaneously
Setup: 10 users, each with 19 conversations
Action: All 10 create 20th conversation at same time
Verify:
  - All 10 conversations created successfully
  - No database locks or deadlocks
  - All users see correct visible_count = 20
```

---

# 10. Implementation Checklist

## Phase 1: Database (Day 1)
- [ ] Add new columns to conversations table
- [ ] Create composite index for visibility query
- [ ] Write migration script
- [ ] Test migration on copy of production DB
- [ ] Verify index usage with EXPLAIN QUERY PLAN

## Phase 2: Configuration (Day 1)
- [ ] Add environment variables to .env
- [ ] Create conversation_limits.py config module
- [ ] Add GET /api/config/limits endpoint
- [ ] Test configuration loading

## Phase 3: Backend Logic (Day 2)
- [ ] Implement relevance score calculation
- [ ] Implement auto-hide algorithm
- [ ] Modify POST /api/conversations/create
- [ ] Add PATCH /api/conversations/{id}/open endpoint
- [ ] Modify GET /api/conversations/list
- [ ] Add audit logging
- [ ] Write unit tests

## Phase 4: API Integration Tests (Day 2)
- [ ] Test auto-hide on 21st conversation
- [ ] Test warning flag at threshold
- [ ] Test active conversation protection
- [ ] Test relevance score ordering
- [ ] Test concurrent creates

## Phase 5: Frontend State (Day 3)
- [ ] Extend state structure
- [ ] Implement state update logic for create
- [ ] Implement state update logic for switch
- [ ] Handle warning flag from backend
- [ ] Update last_opened_at on switch

## Phase 6: Frontend UI (Day 3-4)
- [ ] Add conversation counter badge
- [ ] Implement warning toast
- [ ] Update conversation list rendering
- [ ] Test visual interactions

## Phase 7: Edge Cases (Day 4)
- [ ] Handle rapid conversation creation
- [ ] Handle database failures gracefully
- [ ] Test null value handling
- [ ] Test active conversation protection

## Phase 8: Testing (Day 5)
- [ ] Run all unit tests
- [ ] Run all integration tests
- [ ] Run E2E tests
- [ ] Run load tests
- [ ] Manual QA testing

## Phase 9: Documentation (Day 5)
- [ ] Update API documentation
- [ ] Update user documentation (if exists)
- [ ] Document configuration options
- [ ] Document audit trail format

## Phase 10: Deployment (Day 6)
- [ ] Deploy to staging environment
- [ ] Test with production-like data
- [ ] Monitor performance metrics
- [ ] Deploy to production
- [ ] Monitor for errors

---

# 11. Rollback Plan

## Immediate Rollback (Environment Variable)
```bash
# Disable feature
ENABLE_CONVERSATION_LIMIT=false

# Restart application
# Users see all conversations (no hiding enforced)
```

## Database Rollback
```sql
-- Unhide all auto-hidden conversations
UPDATE conversations 
SET is_hidden = FALSE 
WHERE auto_hidden = 1;

-- Verify
SELECT COUNT(*) FROM conversations WHERE is_hidden = TRUE;
-- Expected: 0
```

## Full Rollback
```sql
-- Drop new columns
ALTER TABLE conversations DROP COLUMN is_hidden;
ALTER TABLE conversations DROP COLUMN hidden_at;
ALTER TABLE conversations DROP COLUMN auto_hidden;
ALTER TABLE conversations DROP COLUMN last_opened_at;

-- Drop index
DROP INDEX idx_conversations_visibility_priority;
```

---

# 12. Success Metrics

## Post-Launch Monitoring (Week 1)

### Performance Metrics
- [ ] p95 latency for GET /api/conversations < 200ms
- [ ] p95 latency for POST /api/conversations/create < 500ms
- [ ] Zero database deadlocks
- [ ] Zero "active conversation was hidden" incidents

### Usage Metrics
- [ ] Track: Average conversations per user
- [ ] Track: How often users hit 15-conversation warning
- [ ] Track: How often users hit 20-conversation limit
- [ ] Track: Average time between conversation switches

### Error Metrics
- [ ] Zero data loss incidents
- [ ] < 0.1% auto-hide failure rate
- [ ] Zero user-reported "disappeared conversation" complaints

---

# 13. Future Enhancements (Out of Scope)

## Phase 2 Features (Not Now)
- Manual archive with unarchive capability
- "View Archived Conversations" section
- Search hidden conversations
- Export conversation history
- Conversation recovery UI

## Phase 3 Features (Later)
- Per-user customizable limits
- Smart auto-archive suggestions
- Conversation merge/split
- Conversation sharing between users

---

# Appendix A: SQL Schema Reference

## Current Schema (Before Changes)
```sql
CREATE TABLE conversations (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    title VARCHAR(255),
    status VARCHAR(20) NOT NULL,
    message_count INTEGER DEFAULT 0,
    last_message_at TIMESTAMP,
    archived_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL
);
```

## New Schema (After Changes)
```sql
CREATE TABLE conversations (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    title VARCHAR(255),
    status VARCHAR(20) NOT NULL,
    message_count INTEGER DEFAULT 0,
    last_message_at TIMESTAMP,
    archived_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL,
    
    -- NEW COLUMNS
    is_hidden BOOLEAN NOT NULL DEFAULT FALSE,
    hidden_at TIMESTAMP,
    auto_hidden BOOLEAN NOT NULL DEFAULT FALSE,
    last_opened_at TIMESTAMP
);

CREATE INDEX idx_conversations_visibility_priority 
ON conversations(user_id, is_hidden, last_opened_at DESC, last_message_at DESC)
WHERE is_hidden = FALSE;
```

---

# Appendix B: Example API Responses

## Example 1: Normal Conversation Create (Under Limit)
```json
POST /api/conversations/create

Response 200:
{
  "conversation": {
    "id": "abc-123",
    "title": "New Conversation",
    "created_at": "2026-02-14T12:00:00Z",
    "last_opened_at": "2026-02-14T12:00:00Z",
    "status": "active",
    "is_hidden": false
  },
  "visible_count": 12,
  "max_allowed": 20,
  "warning": false
}
```

## Example 2: Create with Warning (At Threshold)
```json
POST /api/conversations/create

Response 200:
{
  "conversation": {
    "id": "def-456",
    "title": "New Conversation",
    "created_at": "2026-02-14T12:00:00Z",
    "last_opened_at": "2026-02-14T12:00:00Z",
    "status": "active",
    "is_hidden": false
  },
  "visible_count": 15,
  "max_allowed": 20,
  "warning": true
}
```

## Example 3: Create with Auto-Hide (Over Limit)
```json
POST /api/conversations/create

Response 200:
{
  "conversation": {
    "id": "ghi-789",
    "title": "New Conversation",
    "created_at": "2026-02-14T12:00:00Z",
    "last_opened_at": "2026-02-14T12:00:00Z",
    "status": "active",
    "is_hidden": false
  },
  "visible_count": 20,
  "max_allowed": 20,
  "warning": false,
  "auto_hidden": {
    "occurred": true,
    "conversation_id": "old-conv-uuid",
    "reason": "limit_exceeded"
  }
}
```

---

# Document Version Control

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-02-14 | System | Initial specification based on user requirements |

---

**END OF SPECIFICATION DOCUMENT**
