# Slash Command Mode Requirements Spec (Newline-Only Commands, JSON Registry)

## 1) Goal

Introduce a **command-driven interaction mode** where a user triggers backend functions (starting with eligibility checking) via **slash commands** that are only recognized when the command starts at the **beginning of a new line**.

This removes ambiguity from keyword-based intent detection (e.g., “eligible” appearing in a normal question), and makes routing deterministic.

---

## 2) Scope

### In scope (Phase 1)

* Command registry stored in **JSON** (editable without code changes).
* Command recognition rules:

  * Recognize as a command **only if it begins at the start of a new line**.
  * If `/` appears mid-line, treat as **normal text** (RAG).
* Command execution behavior:

  * When a command token is typed and the user presses **space**, UI shows argument prompt behavior (autocomplete/suggestions optional; backend logic deterministic regardless).
  * Command runs only on **submit** (Enter / Send), not on keystroke.
* First command: `/check_eligibility <identifier>`

  * `<identifier>` is **phone number or account number**.
  * If missing, system asks for the identifier.

### Out of scope (Phase 1)

* SQLite command tables (explicitly deferred).
* Multi-command workflows beyond eligibility.
* Permissions, RBAC, user roles (can be added later).
* Natural-language intent detection for eligibility.

---

## 3) Definitions

* **New line**: The start position immediately after either:

  * The beginning of the message, OR
  * A line break (`\n`) within the message.
* **Command line**: A line whose **first non-empty character** is `/` and begins at new line position.
* **Command token**: The first whitespace-delimited token on a command line, e.g. `/check_eligibility`.
* **Arguments string**: Everything after the command token on that line, trimmed.

---

## 4) Command Recognition Rules

### 4.1 Recognition

A line is a command line if:

* It begins at a new line position AND
* The first character is `/` (no leading characters).

  * Optional decision: allow leading spaces before `/`?

    * For strictness and clarity: **No**.
    * If you later want: allow leading whitespace and treat it as command start. (Not required now.)

### 4.2 Non-recognition

If `/` appears:

* In the middle of a line (e.g. “Can you /check_eligibility this?”), it is **NOT** a command.
* In a URL or path, it is **NOT** a command unless it’s at new line start.

### 4.3 Multi-line messages

If a message has multiple lines:

* Each line can be evaluated independently.
* In Phase 1, support **at most one command line per message** (recommended for simplicity).

  * If multiple command lines exist, treat as error with a user-facing message: “One command per message, please.”

---

## 5) Command Registry (JSON)

The command system is driven by a JSON file loaded at startup (like your other config JSONs).

### 5.1 Registry requirements

Each command entry must define:

* `command`: string (e.g. `/check_eligibility`)
* `description`: short help text
* `handler`: backend function identifier (string key, mapped in a dispatcher)
* `args_schema`: definition of expected args

  * required/optional
  * type hints (phone/account)
  * validation rules reference (not code)
* `examples`: list of example invocations
* `enabled`: boolean

### 5.2 Registry behavior

* If a command is not found or disabled:

  * Return a “Command not recognized” response + show closest matches (optional).

---

## 6) UI Behavior Requirements (Command UX)

### 6.1 Slash suggestions

* When user types `/` **at the beginning of a new line**, UI shows available commands from JSON registry.
* When user types `/` mid-line, **no command dropdown** appears (optional but recommended to match your rule).

### 6.2 Space-to-argument entry

* When user has a valid command token and types a space:

  * UI should transition into “argument entry” mode:

    * Show hint: “Enter phone number or account number…”
    * Optionally show example formats.

### 6.3 Submit

* Command does not execute on space; it executes when user submits (Enter/Send).
* The space behavior is purely to guide the user into providing arguments.

---

## 7) Backend Routing Logic

### 7.1 High-level pipeline

**User Message**
→ **Command Parser (new step, before intent detection)**
→ If command detected:

* **Command Dispatcher**
* Handler executes (e.g., Eligibility Orchestrator)
  → Else:
* Route to existing **RAG flow** (unchanged)

### 7.2 Command Parser output contract

For each message, parser returns:

* `is_command`: boolean
* `command_name`: string (e.g. `/check_eligibility`) or null
* `args_raw`: string or null
* `parse_errors`: list or empty

### 7.3 Dispatcher rules

* If `is_command=true` and `parse_errors` not empty:

  * Return a user-facing error response + usage help.
* Else:

  * Load registry entry for command.
  * Validate args against `args_schema`.
  * If args missing/invalid:

    * Return a clarification prompt specifically for that command.
  * If valid:

    * Invoke mapped handler.

---

## 8) `/check_eligibility` Command Requirements

### 8.1 Inputs

* Identifier must be one of:

  * Phone number (formats accepted should mirror your existing extractor rules)
  * Account number (10-digit per your system)

### 8.2 Behavior

If identifier provided and valid:

* Call Eligibility Orchestrator with extracted identifier
* Return structured eligibility outcome (same payload logic you already have)

If identifier missing:

* Return a deterministic prompt:

  * “Please provide the customer’s phone number or 10-digit account number.”
  * Include examples.

If identifier invalid:

* Return deterministic prompt:

  * “That doesn’t look like a valid phone number or 10-digit account number. Please re-check and send again.”

### 8.3 No intent detection involvement

Once a command is detected, **intent detection is bypassed entirely**.

---

## 9) Persistence & Logging Requirements

### 9.1 Message saving

* Save user message as-is (current behavior).
* Save assistant response as-is (current behavior).
* Add metadata tags:

  * `mode: command | rag`
  * `command_name` if command
  * `command_success: true/false`
  * `command_error_type` if applicable (unknown_command, missing_args, invalid_args, handler_error)

### 9.2 Observability events

New log events:

* `command_detected`
* `command_validation_failed`
* `command_dispatched`
* `command_completed`
* `command_failed`

PII safety:

* Log identifier **type** (phone/account) and **masked** value or hash (no raw identifier).

---

## 10) Error Handling Requirements

### 10.1 Unknown command

* Response: “I don’t recognize that command.”
* Provide `help` suggestion (list top commands from registry).

### 10.2 Multiple commands in one message (Phase 1)

* Response: “Please send one command per message.”

### 10.3 Handler errors

* Response: “I couldn’t complete that command due to a system error. Please try again.”
* Log: include request_id and error type.

---

## 11) Acceptance Criteria

1. If user writes:
   `Am I eligible for a loan?`
   → treated as **RAG** (no accidental eligibility routing).

2. If user writes:
   `/check_eligibility 0712345678`
   → treated as command; calls eligibility flow.

3. If user writes:
   `Please /check_eligibility 0712345678`
   → treated as **RAG** (slash in middle of line).

4. If user writes:
   `/check_eligibility`
   → assistant asks for phone/account.

5. Logs include command detection + outcome metadata without leaking raw PII.

---

## 12) Spec Diagram

```
┌───────────────────────────────┐
│ User Interface (Streamlit)     │
│ - multiline input              │
│ - dropdown only if "/" at BOL  │
└───────────────┬───────────────┘
                │ User submits
                ▼
┌───────────────────────────────┐
│ Command Parser (NEW)           │
│ - split into lines             │
│ - detect command only at BOL   │
│ - extract command + args       │
└───────┬───────────────────────┘
        │is_command? (true)
        │
        ▼
┌───────────────────────────────┐
│ Command Dispatcher (NEW)       │
│ - load JSON registry           │
│ - validate args_schema         │
│ - map handler -> function      │
└───────┬───────────────────────┘
        │
        ▼
┌───────────────────────────────┐
│ Eligibility Orchestrator       │
│ - extract/validate identifier  │
│ - look up excel files          │
│ - build evidence payload       │
└───────┬───────────────────────┘
        │
        ▼
┌───────────────────────────────┐
│ Response + Persistence + Logs  │
│ - save messages                │
│ - add command metadata         │
│ - structured events            │
└───────────────────────────────┘

Else (is_command=false):
Command Parser -> Route to RAG Flow (unchanged)
```

---

