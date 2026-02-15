# Eligibility Module Design

## Tech Stack & Architecture Decisions

### Language & File Formats
- **Language**: Python (aligned with main RAG system)
- **Data Files Format**: `.xlsx` (Excel) for eligible_customers and reasons_file
- **Config Files Format**: `.json` (checks_catalog, reason_detection_rules, reason_playbook)

### Module Structure

```
eligibility/
├── data/
│   ├── eligible_customers.xlsx       # Eligible accounts lookup
│   ├── reasons_file.xlsx             # Ineligible accounts + evidence
│
├── config/
│   ├── checks_catalog.json           # Column definitions & normalization
│   ├── reason_detection_rules.json   # Maps check values → reason codes
│   └── reason_playbook.json          # Reason codes → user-friendly text + remediation
│
├── __init__.py
├── DESIGN.md
├── instructions.md
├── pseudocode.md
├── runtime_schema.md
└── scope.md
```

### Module Components

#### 1. **Config Loader** (`config_loader.py`)
- **Lifecycle**: Loads all 3 config files at **startup** (application init)
- **Caching**: Configs cached in memory after first load
- **Error Handling**: **Raises exception** if any file is malformed or missing
- **Logging**: Logs config load events with session_id and request_id

#### 2. **Data Loader** (`data_loader.py`)
- **Lifecycle**: Loads eligible_customers.xlsx and reasons_file.xlsx at startup
- **Caching**: Both files cached in memory after load
- **Error Handling**: **Raises exception** if files missing or corrupt
- **Logging**: Logs row count, load time, validation checks

#### 3. **Intent Detector** (`intent_detector.py`)
- Analyzes user message to detect eligibility questions
- Matches against keywords from scope.md
- Returns: `is_eligibility_check: bool`
- **Logging**: Logs intent detection with full message hash (not raw text per PII rules)

#### 4. **Account Extractor** (`account_extractor.py`)
- Scans message for 10-digit account numbers
- Returns: `account_numbers: List[str]`, deduped
- **Logging**: Logs extracted account count, no account number values (PII)

#### 5. **Account Validator** (`account_validator.py`)
- Validates each account number (10 digits, numeric only)
- Returns: `valid_accounts: List[str]`, `invalid_accounts: List[str]`
- **Logging**: Logs validation results without account details

#### 6. **Eligibility Processor** (`eligibility_processor.py`)
- **Core Logic**:
  1. Batch load all accounts
  2. Check eligible_customers first
  3. Check reasons_file for each
  4. Normalize row using checks_catalog rules
  5. Extract reasons using reason_detection_rules
  6. Enrich with reason_playbook
- **Returns**: Single JSON payload with all account results
- **Logging**: Logs each account result, extraction steps, processing time

#### 7. **LLM Payload Builder** (`llm_payload_builder.py`)
- Formats eligibility_processor output into LLM-ready JSON
- Includes all extracted reasons + evidence + next steps
- **Returns**: Ready-to-send payload for LLM
- **Logging**: Logs payload size, structure validation

### Logging Strategy

All logging follows the system's existing patterns:

#### Log Format
- **Structured JSON** (per logging_rules.md)
- **ISO 8601 timestamps** in UTC
- **Severity levels**: DEBUG, INFO, WARNING, ERROR, CRITICAL
- **Session tracking**: Include `session_id`, `request_id` (unique per eligibility check)

#### What to Log (Eligibility-Specific)
- **CONFIG LOAD** (startup): File paths, schema versions, row/rule counts
- **DATA LOAD** (startup): File paths, customer record counts, validation status
- **INTENT DETECTION**: Detected intent flag, message hash (not raw text)
- **ACCOUNT EXTRACTION**: Account count extracted (no account details)
- **ACCOUNT VALIDATION**: Valid/invalid counts, validation errors (no account numbers)
- **ELIGIBILITY PROCESSING**: Per-account results, reason count, processing latency
- **LLM PAYLOAD**: Payload structure validation, total reasons count

#### What NOT to Log (PII Rules)
- Account numbers
- Customer names
- Email addresses
- Phone numbers
- Raw user messages (hash only)
- Raw evidence values from reasons_file

### Integration Points

#### 1. **Where It Lives in the Pipeline**
- New Python module under `eligibility/` folder
- Callable from `query_data.py` (during query processing)
- OR called from `app.py` (as separate flow before RAG query)
- Decision: TBD (depends on when eligibility flow triggers)

#### 2. **Integration with Existing RAG Logger**
- Import `RAGLogger` from `logger.rag_logging`
- Use `SessionManager` for session_id and log file rotation
- Follow existing PII scrubbing patterns from `logger.pii`
- Generate request_id via `RAGLogger.generate_request_id()`

#### 3. **Error Handling Pattern**
- Match system's pattern: `get_user_friendly_error_message(error_type, message)`
- Throw exceptions on config/data load failure (critical)
- Return structured error results for validation/processing failures
- Log all errors with full traceback + context

### Config File Schemas

All 3 JSON config files are fully specified in [instructions.md](./instructions.md):
- **checks_catalog.json**: Column definitions, normalization rules
- **reason_detection_rules.json**: Extraction logic per reason code
- **reason_playbook.json**: User-friendly meanings + next steps + timing

### Data File Schemas

Both Excel files follow JSON schemas specified in [instructions.md](./instructions.md):
- **eligible_customers.xlsx**: Customer table schema (when status="ELIGIBLE")
- **reasons_file.xlsx**: Checks catalog structure (when status="NOT_ELIGIBLE")

---

## Design Summary

| Aspect | Decision |
|--------|----------|
| **Language** | Python |
| **Data Format** | .xlsx (Excel) |
| **Config Format** | .json |
| **Config Loading** | Startup (cached) |
| **Data Loading** | Startup (cached) |
| **Error on Bad Config** | Raise exception |
| **Logging** | JSON structured, follow system rules, use RAGLogger + SessionManager |
| **PII Handling** | Hash messages, no account/customer details, follow logger.pii patterns |
| **Return Format** | Single JSON payload per batch |
| **Multi-Account Handling** | Batch all in one LLM call |

