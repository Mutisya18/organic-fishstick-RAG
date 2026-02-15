# Updated Implementation Approach - User Management for Portal

## **Architecture Overview**

```
Portal Frontend (HTML/CSS/JS)
    ↓ (HTTP-only cookie)
FastAPI Backend (portal_api.py)
    ↓
Auth Module (auth/)
    ↓
Database (SQLite/PostgreSQL compatible)
    ├── users table
    ├── user_sessions table
    └── conversations (existing, unchanged)
```

---


## **Phase 1: Database Layer** (Week 1, Days 1-2)

### **New Tables**

**`users` table**:
- Primary purpose: Store user credentials and profile
- Columns needed:
  - `user_id` (VARCHAR(255), PRIMARY KEY) - Use email as ID for simplicity
  - `email` (VARCHAR(255), UNIQUE, NOT NULL) - Login identifier
  - `password_hash` (VARCHAR(255), NOT NULL) - bcrypt hash
  - `full_name` (VARCHAR(255), NOT NULL) - Display name
  - `is_active` (BOOLEAN, DEFAULT TRUE) - Soft delete flag
  - `created_at` (TIMESTAMP, DEFAULT NOW())
  - `last_login` (TIMESTAMP, NULL)
  - `metadata` (JSON/JSONB, NULL) - Future extensibility (department, phone, etc.)

**`user_sessions` table**:
- Primary purpose: Track active sessions for validation and cleanup
- Columns needed:
  - `session_id` (UUID, PRIMARY KEY) - Session token
  - `user_id` (VARCHAR(255), FK → users.user_id, ON DELETE CASCADE)
  - `created_at` (TIMESTAMP, DEFAULT NOW())
  - `expires_at` (TIMESTAMP, NOT NULL) - 30 minutes from creation
  - `last_activity` (TIMESTAMP, NOT NULL) - Updated on each request
  - `ip_address` (VARCHAR(45), NULL) - Audit trail
  - `user_agent` (VARCHAR(500), NULL) - Audit trail
  - `is_active` (BOOLEAN, DEFAULT TRUE) - Soft invalidation (logout)

**Indexes needed**:
```sql
CREATE INDEX idx_sessions_user ON user_sessions(user_id, is_active);
CREATE INDEX idx_sessions_expires ON user_sessions(expires_at);
CREATE INDEX idx_sessions_token ON user_sessions(session_id) WHERE is_active = TRUE;
```

**Compatibility strategy**:
- Use standard SQL types (VARCHAR, BOOLEAN, TIMESTAMP)
- For JSON column: Conditional logic in model
  - SQLite: Use TEXT with JSON validation
  - PostgreSQL: Use JSONB
- Migration tool: Alembic (supports both DBs)

---

## **Phase 2: Auth Module** (Week 1, Days 3-5)

### **Directory Structure**

```
auth/
├── __init__.py           # Exports public API
├── password.py           # Password hashing/verification
├── session.py            # Session CRUD operations
├── user_service.py       # User CRUD operations
├── middleware.py         # FastAPI dependency for auth
└── validation.py         # Password strength validation
```

### **Module Responsibilities**

**`password.py`**:
- `hash_password(plain_text: str) -> str`
  - Use bcrypt with cost factor 12
  - Return base64 hash string
- `verify_password(plain_text: str, hash_string: str) -> bool`
  - Compare using bcrypt's safe comparison
  - Return True/False

**`validation.py`**:
- `validate_password(password: str) -> tuple[bool, str]`
  - Min 12 characters
  - At least 1 number
  - At least 1 special character (!@#$%^&*()_+-=[]{}|;:,.<>?)
  - Return (is_valid, error_message)
- `validate_email(email: str) -> tuple[bool, str]`
  - Basic regex check
  - Return (is_valid, error_message)

**`user_service.py`**:
- `create_user(email, password, full_name) -> dict`
  - Validate email format
  - Validate password strength
  - Hash password
  - Insert into users table
  - Return user dict (without password_hash)
  - Raise exception if email exists

- `get_user_by_email(email) -> dict | None`
  - Query users table
  - Return user dict or None

- `authenticate(email, password) -> str | None`
  - Get user by email
  - Verify password hash
  - If valid: Create session, update last_login, return session_id
  - If invalid: Return None

- `update_last_login(user_id) -> None`
  - Update last_login timestamp

- `deactivate_user(user_id) -> None`
  - Set is_active = False
  - Expire all sessions for that user

**`session.py`**:
- `create_session(user_id, ip_address, user_agent) -> str`
  - Generate UUID session_id
  - Set expires_at = now + 30 minutes
  - Set last_activity = now
  - Insert into user_sessions
  - Return session_id

- `validate_session(session_id) -> dict | None`
  - Query session by session_id
  - Check is_active = TRUE
  - Check expires_at > now
  - Check last_activity < 30 minutes ago
  - If valid: Update last_activity, return user dict
  - If invalid: Return None

- `extend_session(session_id) -> None`
  - Update last_activity = now
  - Update expires_at = now + 30 minutes

- `expire_session(session_id) -> None`
  - Set is_active = FALSE
  - (Soft delete - keeps audit trail)

- `cleanup_expired_sessions() -> int`
  - Delete sessions where expires_at < now - 7 days
  - Return count deleted
  - (Background job, runs daily)

**`middleware.py`**:
- `get_current_user(session_id: str = Cookie(None)) -> dict`
  - FastAPI dependency function
  - Extract session_id from cookie
  - Call validate_session()
  - If valid: Return user dict
  - If invalid: Raise HTTPException(401, "Unauthorized")

---

## **Phase 3: API Endpoints** (Week 2, Days 1-3)

### **New Auth Endpoints in `portal_api.py`**

**POST `/api/auth/login`**:
- Request body: `{"email": str, "password": str}`
- Process:
  1. Call `authenticate(email, password)`
  2. If returns session_id:
     - Set HTTP-only cookie: `session_id=<token>; HttpOnly; Secure; SameSite=Lax; Max-Age=1800`
     - Return `{"success": true, "user": {email, full_name}}`
  3. If returns None:
     - Return `{"success": false, "error": "Invalid email or password"}`
- Status codes: 200 (both success/failure), 400 (validation error)

**POST `/api/auth/logout`**:
- Requires: session_id cookie
- Process:
  1. Call `get_current_user()` (validates session)
  2. Call `expire_session(session_id)`
  3. Clear cookie: `Set-Cookie: session_id=; Max-Age=0`
  4. Return `{"success": true}`
- Status codes: 200 (success), 401 (not authenticated)

**GET `/api/auth/me`**:
- Requires: session_id cookie
- Process:
  1. Call `get_current_user()` (validates + extends session)
  2. Return `{"user": {email, full_name, last_login}}`
- Status codes: 200 (success), 401 (not authenticated)

**POST `/api/admin/users`** (Admin creates new staff):
- Requires: session_id cookie (but no role check for MVP)
- Request body: `{"email": str, "password": str, "full_name": str}`
- Process:
  1. Call `get_current_user()` (must be authenticated)
  2. Validate password strength
  3. Call `create_user(email, password, full_name)`
  4. Return `{"success": true, "user": {email, full_name}}`
- Status codes: 201 (created), 400 (validation error), 409 (email exists)

**GET `/api/admin/users`** (List all users):
- Requires: session_id cookie
- Process:
  1. Call `get_current_user()`
  2. Query all users (exclude password_hash)
  3. Return `{"users": [{email, full_name, created_at, last_login, is_active}, ...]}`
- Status codes: 200 (success), 401 (not authenticated)

### **Modified Existing Endpoints**

**All `/api/v2/conversations*` endpoints**:
- **BEFORE**: `user_id = "default_user"` (hardcoded)
- **AFTER**: 
  - Add dependency: `user = Depends(get_current_user)`
  - Use `user["user_id"]` instead of hardcoded string
  - If cookie missing/invalid: Auto 401 from middleware

**POST `/api/chat/send`**:
- Add: `user = Depends(get_current_user)`
- Use `user["user_id"]` for conversation ownership

**GET `/api/messages`**:
- Add auth check
- Verify user owns the conversation before returning messages

---

## **Phase 4: Frontend - Login Page** (Week 2, Days 4-5)

### **New File: `portal/login.html`**

**Structure**:
```
<body>
  <div class="login-container">
    <div class="login-card">
      <div class="logo">N</div>
      <h1>NCBA Operations Assistant</h1>
      <form id="loginForm">
        <input type="email" id="email" placeholder="Email" required>
        <input type="password" id="password" placeholder="Password" required>
        <div id="errorMessage" class="error-message"></div>
        <button type="submit">Sign In</button>
      </form>
    </div>
  </div>
</body>
```

**Styling**:
- Match existing Portal theme (use themes.css variables)
- Center card vertically/horizontally
- Error message: Red text below form fields (inline, matches decision #12)
- Focus states on inputs
- Loading state on button during submission

**JavaScript Logic** (`portal/static/js/login.js`):
```
1. On form submit:
   - Prevent default
   - Show loading state on button
   - POST to /api/auth/login with email + password
   - If success:
     - Cookie is auto-set by browser
     - Redirect to /
   - If failure:
     - Show error message inline (red text)
     - Clear password field
     - Re-enable button
```

**Error messages**:
- Generic: "Invalid email or password" (don't reveal which is wrong)
- Network error: "Unable to connect. Please try again."
- Validation: "Please enter a valid email address"

---

## **Phase 5: Frontend - Auth State** (Week 3, Days 1-2)

### **Modify `portal/static/js/state.js`**

**Add to state object**:
```javascript
state = {
  auth: {
    user: null,           // {email, full_name, last_login}
    isAuthenticated: false,
    sessionExpiry: null   // Timestamp for tracking
  },
  conversationId: null,
  user: {...},  // DEPRECATED - remove this
  messages: [],
  conversations: {...}
}
```

**New functions**:
- `setAuthUser(user)` - Set auth.user, isAuthenticated = true
- `clearAuthUser()` - Set auth.user = null, isAuthenticated = false
- `isAuthenticated()` - Return state.auth.isAuthenticated
- `getCurrentUser()` - Return state.auth.user

### **Modify `portal/static/js/api.js`**

**Add to api object**:
```javascript
api.login = async (email, password) => {
  const res = await fetch("/api/auth/login", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    credentials: "include",  // CRITICAL: Include cookies
    body: JSON.stringify({email, password})
  });
  const data = await res.json();
  if (data.success) {
    setAuthUser(data.user);
  }
  return data;
};

api.logout = async () => {
  await fetch("/api/auth/logout", {
    method: "POST",
    credentials: "include"
  });
  clearAuthUser();
};

api.checkAuth = async () => {
  const res = await fetch("/api/auth/me", {
    credentials: "include"
  });
  if (res.ok) {
    const data = await res.json();
    setAuthUser(data.user);
    return true;
  }
  clearAuthUser();
  return false;
};
```

**Modify all existing API calls**:
- Add `credentials: "include"` to EVERY fetch() call
- This ensures cookies are sent automatically

### **Modify `portal/static/js/app.js`**

**On page load**:
```javascript
// At the very top of initialization:
async function checkAuthAndInit() {
  const isAuth = await api.checkAuth();
  if (!isAuth) {
    window.location.href = "/login";
    return;
  }
  
  // Continue with existing initialization
  applyUserToUI();
  initializeMultiConversation();
  // ... rest of app.js logic
}

checkAuthAndInit();
```

**Handle session expiry**:
```javascript
// Add global error handler for 401 responses
window.addEventListener('unhandledrejection', (event) => {
  if (event.reason && event.reason.status === 401) {
    showSessionExpiredModal();
  }
});

function showSessionExpiredModal() {
  // Create modal overlay
  // Show message: "Your session has expired. Please log in again."
  // Button: "Log In" → redirects to /login
  // Block all other interactions
}
```

**Update profile dropdown**:
- Replace hardcoded name with `state.auth.user.full_name`
- "Sign Out" button → Call `api.logout()` → Redirect to `/login`

---

## **Phase 6: Backend Route Guard** (Week 3, Day 3)

### **Modify `portal_api.py` Root Route**

**Change `/` endpoint**:
```python
@app.get("/")
async def root(session_id: str = Cookie(None)):
    # Check if session exists
    if not session_id:
        return RedirectResponse("/login")
    
    # Validate session
    user = validate_session(session_id)
    if not user:
        return RedirectResponse("/login")
    
    # Session valid - serve main app
    return FileResponse(PORTAL_DIR / "index.html")
```

**Add `/login` route**:
```python
@app.get("/login")
async def login_page():
    return FileResponse(PORTAL_DIR / "login.html")
```

**Pattern for all protected routes**:
- Every endpoint now uses: `user = Depends(get_current_user)`
- FastAPI automatically raises 401 if cookie missing/invalid
- Frontend catches 401 and redirects to login

---

## **Phase 7: Scripts & Utilities** (Week 3, Days 4-5)

### **Admin User Creation Script**

**File: `scripts/create_admin.py`**

**Purpose**: Create the very first admin user

**Logic**:
```
1. Load environment variables
2. Initialize database (same as app startup)
3. Prompt for email, full_name, password
4. Validate password strength
5. Call create_user()
6. Print success message with credentials
7. Exit
```

**Usage**:
```bash
python scripts/create_admin.py
# Interactive prompts:
#   Email: admin@company.com
#   Full Name: System Administrator
#   Password: ********** (validated)
# Output: ✅ Admin user created successfully
```

**Safety checks**:
- If any users already exist → Exit with error
- Validate email format before attempting creation
- Confirm password twice

### **Migration Script**

**File: `scripts/migrate_default_user.py`**

**Purpose**: Migrate all `user_id="default_user"` conversations to first admin

**Logic**:
```
1. Load database
2. Query first user from users table (ORDER BY created_at LIMIT 1)
3. If no users exist → Exit with error
4. UPDATE conversations SET user_id = <first_user_email> WHERE user_id = 'default_user'
5. Print count of migrated conversations
```

**Usage**:
```bash
python scripts/migrate_default_user.py
# Output: Migrated 15 conversations to admin@company.com
```

### **Session Cleanup Script**

**File: `scripts/cleanup_sessions.py`**

**Purpose**: Delete expired sessions (run as cron job)

**Logic**:
```
1. Load database
2. Call cleanup_expired_sessions()
3. Print count deleted
4. Log to audit trail
```

**Cron setup** (optional for MVP, but document for later):
```cron
# Run daily at 2 AM
0 2 * * * /path/to/venv/bin/python /path/to/scripts/cleanup_sessions.py
```

### **Dev Mode Seed Script**

**File: `scripts/seed_dev_user.py`**

**Purpose**: Auto-create test user in development

**Logic**:
```
1. Check if ENV=dev (from .env)
2. If not dev → Exit silently
3. If test@test.com already exists → Exit silently
4. Create user: test@test.com / password123 / "Test User"
5. Print message: "Dev user created: test@test.com / password123"
```

**Integration**: Call from `start_portal.sh` after database init

---

## **Phase 8: Environment Configuration** (Week 3, Day 5)

### **Add to `.env`**

```bash
# === User Management Configuration ===

# Session expiry (30 minutes = 1800 seconds)
SESSION_EXPIRY_SECONDS=1800

# Password requirements
PASSWORD_MIN_LENGTH=12
PASSWORD_REQUIRE_NUMBER=true
PASSWORD_REQUIRE_SPECIAL=true

# Dev mode auto-seed test user (test@test.com / password123)
DEV_MODE=true

# Admin email for migration (optional, used by migrate script)
ADMIN_EMAIL=admin@company.com
```

---

## **Phase 9: Testing Strategy** (Week 4)

### **Unit Tests** (`tests/test_auth.py`)

**Password module**:
- `test_hash_password_returns_string()`
- `test_hash_password_different_each_time()`
- `test_verify_password_correct()`
- `test_verify_password_incorrect()`
- `test_verify_password_empty_string()`

**Validation module**:
- `test_validate_password_too_short()`
- `test_validate_password_no_number()`
- `test_validate_password_no_special_char()`
- `test_validate_password_valid()`
- `test_validate_email_invalid_format()`
- `test_validate_email_valid()`

**Session module**:
- `test_create_session_returns_uuid()`
- `test_validate_session_valid()`
- `test_validate_session_expired()`
- `test_validate_session_inactive()`
- `test_extend_session_updates_expiry()`
- `test_expire_session_sets_inactive()`

**User service module**:
- `test_create_user_success()`
- `test_create_user_duplicate_email()`
- `test_create_user_invalid_password()`
- `test_authenticate_success()`
- `test_authenticate_wrong_password()`
- `test_authenticate_nonexistent_user()`

### **Integration Tests** (`tests/test_auth_integration.py`)

**Full flow tests**:
- `test_login_flow_end_to_end()`
  - Create user → Login → Get session → Validate → Logout
- `test_session_expiry_behavior()`
  - Create session → Fast-forward time → Validate fails
- `test_conversation_isolation()`
  - Create 2 users → Create conversations → Verify user A can't see user B's
- `test_unauthorized_access_blocked()`
  - Call protected endpoint without cookie → Expect 401
- `test_session_extension_on_activity()`
  - Create session → Call /api/auth/me → Verify expires_at extended

### **API Tests** (`tests/test_auth_api.py`)

**Endpoint tests using FastAPI TestClient**:
- `test_login_endpoint_success()`
- `test_login_endpoint_wrong_password()`
- `test_login_endpoint_missing_fields()`
- `test_logout_endpoint()`
- `test_me_endpoint_authenticated()`
- `test_me_endpoint_unauthenticated()`
- `test_create_user_endpoint()`
- `test_protected_endpoint_requires_auth()`

---

## **Phase 10: Security Hardening** (Week 4)

### **HTTP-only Cookie Configuration**

**Production settings** (in `portal_api.py`):
```python
# When setting cookie:
response.set_cookie(
    key="session_id",
    value=session_id,
    httponly=True,        # Prevents JavaScript access (XSS protection)
    secure=True,          # HTTPS only (disable for local dev)
    samesite="lax",       # CSRF protection
    max_age=1800,         # 30 minutes in seconds
    path="/"              # Cookie valid for entire domain
)
```

**Development settings**:
- `secure=False` (allow HTTP for localhost)
- All other settings same

### **Rate Limiting**

**Login endpoint protection**:
- Track failed attempts per email in memory (or Redis for multi-instance)
- Max 5 attempts per 15 minutes
- Return 429 (Too Many Requests) when exceeded
- Clear counter on successful login

**Implementation approach** (simple in-memory for MVP):
```python
# Global dict (thread-safe with lock)
login_attempts = {}  # {email: [timestamp, timestamp, ...]}

# Before authenticate():
- Check if email has 5+ attempts in last 15 min
- If yes: return 429
- If no: continue
- After failed auth: append timestamp to attempts[email]
- After successful auth: clear attempts[email]
```

### **Audit Logging**

**Events to log** (integrate with existing RAGLogger):
- User login attempts (success/failure)
- User logout
- User creation
- Session expiry
- Failed authentication (with IP address)
- Password validation failures

**Log format**:
```json
{
  "event": "login_attempt",
  "timestamp": "2026-02-15T10:30:00.123Z",
  "user_email": "admin@company.com",
  "success": true,
  "ip_address": "192.168.1.100",
  "user_agent": "Mozilla/5.0..."
}
```

### **Password Security Checklist**

- [ ] Passwords hashed with bcrypt (cost factor 12)
- [ ] Password validation: min 12 chars, number, special char
- [ ] No password hints/recovery (MVP - just manual reset by admin)
- [ ] Hash compared using bcrypt's timing-safe comparison
- [ ] Password never logged (even in debug mode)
- [ ] Password never returned in API responses

### **Session Security Checklist**

- [ ] Session tokens are UUID v4 (cryptographically random)
- [ ] HTTP-only cookies (no JavaScript access)
- [ ] Secure flag enabled in production (HTTPS only)
- [ ] SameSite=Lax (CSRF protection)
- [ ] 30-minute expiry enforced server-side
- [ ] Sessions invalidated on logout
- [ ] Expired sessions cleaned up regularly

### **Input Validation Checklist**

- [ ] Email validated with regex
- [ ] Password validated before hashing
- [ ] SQL injection prevented (use parameterized queries)
- [ ] XSS prevented (FastAPI auto-escapes, but verify in templates)
- [ ] No sensitive data in URLs (everything in POST body or cookies)

---

## **Phase 11: Documentation** (Week 4)

### **API Documentation** (`docs/AUTH_API.md`)

**Document all endpoints**:
- Request format
- Response format
- Status codes
- Example curl commands
- Example responses

**Example**:
```markdown
## POST /api/auth/login

Authenticate a user and create a session.

**Request**:
```json
{
  "email": "admin@company.com",
  "password": "SecurePass123!"
}
```

**Response (Success)**:
```json
{
  "success": true,
  "user": {
    "email": "admin@company.com",
    "full_name": "System Administrator"
  }
}
```

**Response (Failure)**:
```json
{
  "success": false,
  "error": "Invalid email or password"
}
```

**Status Codes**:
- 200: Success (even if auth fails - check `success` field)
- 400: Validation error (missing fields)
- 429: Too many attempts (rate limited)
```

### **Admin Guide** (`docs/ADMIN_GUIDE.md`)

**Topics**:
- Creating the first admin user
- Creating additional staff users (via API)
- Deactivating users
- Viewing user list
- Resetting passwords (manual process for MVP)
- Session management

### **Developer Guide** (`docs/AUTH_DEV.md`)

**Topics**:
- Auth module architecture
- Adding new endpoints
- Testing authentication
- Debugging session issues
- Database schema
- Migration strategy

---

## **Implementation Checklist**

### **Week 1: Database + Auth Module**
- [ ] Create `users` table migration
- [ ] Create `user_sessions` table migration
- [ ] Build `auth/password.py`
- [ ] Build `auth/validation.py`
- [ ] Build `auth/session.py`
- [ ] Build `auth/user_service.py`
- [ ] Build `auth/middleware.py`
- [ ] Write unit tests for all auth modules
- [ ] Verify SQLite + PostgreSQL compatibility

### **Week 2: API + Login Page**
- [ ] Add `/api/auth/login` endpoint
- [ ] Add `/api/auth/logout` endpoint
- [ ] Add `/api/auth/me` endpoint
- [ ] Add `/api/admin/users` (POST, GET) endpoints
- [ ] Modify all existing endpoints to use `get_current_user`
- [ ] Build `portal/login.html`
- [ ] Build `portal/static/js/login.js`
- [ ] Test login flow end-to-end

### **Week 3: Frontend + Integration**
- [ ] Modify `state.js` - add auth state
- [ ] Modify `api.js` - add auth methods, `credentials: "include"` to all
- [ ] Modify `app.js` - add auth check on load
- [ ] Add session expiry modal
- [ ] Update profile dropdown to use real user data
- [ ] Test conversation isolation between users
- [ ] Build `scripts/create_admin.py`
- [ ] Build `scripts/migrate_default_user.py`
- [ ] Build `scripts/seed_dev_user.py`
- [ ] Build `scripts/cleanup_sessions.py`
- [ ] Update `start_portal.sh` to call seed script in dev mode

### **Week 4: Testing + Security**
- [ ] Write integration tests
- [ ] Write API tests
- [ ] Implement rate limiting
- [ ] Add audit logging for auth events
- [ ] Security review (checklist above)
- [ ] Test session expiry behavior
- [ ] Test rate limiting
- [ ] Write documentation (API, Admin, Developer guides)
- [ ] Manual penetration testing
- [ ] Performance testing (100+ concurrent sessions)

---

## **Key Files to Create/Modify**

### **New Files** (17 total)
```
auth/
  __init__.py
  password.py
  validation.py
  session.py
  user_service.py
  middleware.py

portal/
  login.html

portal/static/js/
  login.js

scripts/
  create_admin.py
  migrate_default_user.py
  seed_dev_user.py
  cleanup_sessions.py

database/models/
  user.py              # User model
  user_session.py      # UserSession model

database/migrations/
  001_create_users.py
  002_create_sessions.py

tests/
  test_auth.py
  test_auth_integration.py
  test_auth_api.py

docs/
  AUTH_API.md
  ADMIN_GUIDE.md
  AUTH_DEV.md
```

### **Modified Files** (6 total)
```
portal_api.py           # Add auth endpoints, modify existing
portal/index.html       # Unchanged structure, but auth-gated
portal/static/js/state.js    # Add auth state
portal/static/js/api.js      # Add auth methods, credentials
portal/static/js/app.js      # Add auth check on load
.env                    # Add auth configuration
requirements.txt        # Add bcrypt
start_portal.sh         # Add seed script call
```

---

## **Migration Path**

### **Day 1: Database Setup**
1. Run `alembic upgrade head` (creates users + sessions tables)
2. Verify tables created in SQLite

### **Day 2: Create First Admin**
1. Run `python scripts/create_admin.py`
2. Create admin: `admin@company.com / SecurePass123!`
3. Verify admin appears in users table

### **Day 3: Migrate Existing Data**
1. Run `python scripts/migrate_default_user.py`
2. Verify all conversations now have `user_id = admin@company.com`
3. Verify no `user_id = "default_user"` remains

### **Day 4: Enable Auth**
1. Deploy new portal_api.py with auth endpoints
2. Deploy login.html and modified JS
3. Test login flow: Login as admin → See migrated conversations

### **Day 5: Create Additional Users**
1. Use curl/Postman to POST /api/admin/users
2. Create test staff: `staff@company.com`
3. Test isolation: Login as staff → See empty conversation list
4. Create new conversation → Verify admin can't see it

---

## **Rollback Strategy**

**If migration fails**:
1. Keep backup of database before running migration
2. Restore from backup
3. Run with `user_id = "default_user"` until issues resolved

**If auth breaks production**:
1. Add environment flag: `AUTH_DISABLED=true`
2. Skip auth checks when flag is true
3. Fix issues
4. Re-enable auth

---

## **Success Criteria**

You'll know it's working when:

✅ **Login flow**: Can login at `/login`, redirected to `/`  
✅ **Session persistence**: Refresh page, still logged in  
✅ **Session expiry**: Wait 31 minutes, shows modal "Session expired"  
✅ **Logout**: Click sign out, redirected to `/login`  
✅ **Conversation isolation**: User A can't see User B's conversations  
✅ **Auth required**: Direct access to `/` without cookie → redirected to `/login`  
✅ **API protection**: Calling `/api/v2/conversations` without cookie → 401 error  
✅ **Migration**: All old conversations belong to admin  
✅ **Dev mode**: Test user auto-created on startup  
✅ **Password validation**: Weak passwords rejected with clear error message  

---

## **Post-MVP Enhancements** (Future)

**Not in scope now, but easy to add later**:
- Password reset via email
- "Remember me" option (longer session)
- User profile editing
- Admin UI panel for user management
- Role-based access control (admin vs staff)
- SSO/LDAP integration
- Two-factor authentication
- Login history/audit trail UI
- User search/filtering
- Bulk user import (CSV)

---
