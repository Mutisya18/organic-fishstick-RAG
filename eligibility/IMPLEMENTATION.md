# Eligibility Module Implementation Roadmap

## Phase 1: Foundation & Infrastructure

### Step 1: Create Module Structure
- Create `eligibility/__init__.py` (empty or with module exports)
- Verify `eligibility/data/` folder exists
- Verify `eligibility/config/` folder exists
- Create empty placeholder files for all config JSONs and data files

**Dependencies**: None
**Deliverable**: Empty module structure ready for code

---

## Phase 2: Configuration & Data Layer

### Step 2: Build Config Loader (`eligibility/config_loader.py`)
**Purpose**: Load and validate all 3 config files at startup

**Responsibilities**:
- Read `checks_catalog.json`, `reason_detection_rules.json`, `reason_playbook.json`
- Validate JSON schema for each file
- Cache in memory as class attributes/singleton
- Throw exception if any file missing or malformed
- Log load event with file paths, schema versions, counts

**Error Handling**:
- `FileNotFoundError` → log + raise
- `JSONDecodeError` → log + raise
- Schema validation failure → log + raise

**Logging**:
- INFO: "Config loaded: checks_catalog (X columns), reason_detection_rules (Y reasons), reason_playbook (Z playbook items)"
- ERROR: "Config load failed: [file_name] - [error_message]"

**Dependencies**: None (standard library only)
**Test**: Can load all 3 config files without errors

---

### Step 3: Build Data Loader (`eligibility/data_loader.py`)
**Purpose**: Load and validate both Excel data files at startup

**Responsibilities**:
- Read `eligible_customers.xlsx` (load into DataFrame/dict)
- Read `reasons_file.xlsx` (load into DataFrame/dict)
- Validate against schemas (must have required columns, correct types)
- Cache in memory as class attributes/singleton
- Create indexes on `account_number` for O(1) lookups
- Throw exception if any file missing, corrupt, or schema invalid
- Log load event with row counts and validation results

**Error Handling**:
- `FileNotFoundError` → log + raise
- `openpyxl.load_workbook()` errors → log + raise
- Schema validation failure → log + raise
- Duplicate account numbers → log warning

**Logging**:
- INFO: "Data loaded: eligible_customers (X rows), reasons_file (Y rows)"
- WARNING: "Duplicate account numbers found in reasons_file: [count]"
- ERROR: "Data load failed: [file_name] - [error_message]"

**Dependencies**: openpyxl, pandas (or just openpyxl if preferred)
**Test**: Can load both files, can look up account by number instantly

---

## Phase 3: User Input Processing

### Step 4: Build Intent Detector (`eligibility/intent_detector.py`)
**Purpose**: Determine if user message is asking about eligibility

**Responsibilities**:
- Accept user message (string)
- Match against keyword list from scope.md
- Return boolean: `is_eligibility_check`
- Log intent detection result (with message hash, not raw text)

**Keywords to Match** (from scope.md):
- "is customer eligible?"
- "why no limit?"
- "loan limit issue"
- "not getting limit"
- "check eligibility"
- "limit allocation failed"
- "why excluded"

**Error Handling**:
- If message is None/empty → return False, log DEBUG
- Case-insensitive matching

**Logging**:
- DEBUG: "Intent detection: message_hash=[HASH], is_eligibility_check=[TRUE/FALSE]"

**Dependencies**: None (standard library only)
**Test**: Matches keywords, ignores case, hashes message for logging

---

### Step 5: Build Account Extractor (`eligibility/account_extractor.py`)
**Purpose**: Extract 10-digit account numbers from user message

**Responsibilities**:
- Scan message for all 10-digit numeric sequences
- Deduplicate results
- Return list of extracted account numbers
- Log extraction result (account count only, no account numbers)

**Error Handling**:
- If message is None/empty → return empty list, log DEBUG
- If no accounts found → return empty list, log DEBUG

**Logging**:
- DEBUG: "Account extraction: found [COUNT] account(s)"

**Dependencies**: re (standard library)
**Test**: Finds all 10-digit sequences, deduplicates, ignores non-digit sequences

---

### Step 6: Build Account Validator (`eligibility/account_validator.py`)
**Purpose**: Validate account number format

**Responsibilities**:
- Accept list of account numbers (strings)
- For each: check exactly 10 digits, no non-numeric characters
- Return tuple: (valid_accounts: List[str], invalid_accounts: List[str])
- Log validation results (counts only, no account details)

**Error Handling**:
- If input is None/empty → return ([], []), log DEBUG
- Invalid formats → move to invalid_accounts list (don't raise)

**Logging**:
- DEBUG: "Account validation: [X] valid, [Y] invalid"
- ERROR: (if all invalid) "No valid account numbers provided"

**Dependencies**: None (standard library only)
**Test**: Accepts 10-digit, rejects <10, >10, non-numeric

---

## Phase 4: Business Logic

### Step 7: Build Eligibility Processor (`eligibility/eligibility_processor.py`)
**Purpose**: Core logic - check eligibility for each account and extract reasons

**Responsibilities**:
- Accept: list of valid account numbers, config_loader instance, data_loader instance
- For each account:
  - **Step 5A**: Check if account in `eligible_customers` → status="ELIGIBLE", reasons=[]
  - **Step 5B**: Check if account in `reasons_file`:
    - Normalize row using `checks_catalog` rules
    - Extract all "Exclude" checks + special handling for Recency_Check="N"
    - For each reason, extract evidence columns
    - Build facts using `reason_detection_rules` facts_builder logic
    - Enrich with playbook (meaning, next_steps, timing)
    - Return status="NOT_ELIGIBLE", reasons=[enriched_reasons]
  - **Step 5C**: If account in neither → status="CANNOT_CONFIRM", reasons=[]
- Return: List[Dict] with all account results
- Log processing steps, latency per account, reason extraction details

**Error Handling**:
- If the reasons file or eligible data set is not avaialble, don't throw an error, simply response that the data is not avaialbe and they should contact the admin. This is for when no data is entirely unavaiable, not when the customer is not found in the dataset.
- If the dataset is empty, it should trigger a reload from the datasource
- If account_numbers list is empty → return empty list, log WARNING
- If config_loader or data_loader not initialized → raise exception
- If reason code not found in playbook → log ERROR, skip enrichment

**Logging**:
- INFO: "Processing [N] account(s)"
- DEBUG: "Account [HASH]: status=[STATUS], [M] reasons extracted"
- DEBUG: "Reason [CODE]: evidence_fields=[FIELD_COUNT], facts=[FACT_COUNT]"
- ERROR: "Account [HASH]: Reason code [CODE] not found in playbook"
- INFO: "Eligibility processing completed: [N] eligible, [M] not_eligible, [K] cannot_confirm"

**Dependencies**: config_loader, data_loader
**Test**: Correctly classifies eligible accounts, extracts all Exclude checks, handles Recency special case, enriches with playbook

---

### Step 8: Build LLM Payload Builder (`eligibility/llm_payload_builder.py`)
**Purpose**: Format eligibility processor output into LLM-ready JSON

**Responsibilities**:
- Accept: list of eligibility results from processor
- Build JSON payload:
  ```json
  {
    "request_id": "unique-id",
    "batch_timestamp": "ISO 8601",
    "accounts": [
      {
        "account_number_hash": "hashed",
        "customer_name_hash": "hashed (if available)",
        "status": "ELIGIBLE|NOT_ELIGIBLE|CANNOT_CONFIRM",
        "reasons": [
          {
            "code": "REASON_CODE",
            "meaning": "from playbook",
            "facts": ["fact1", "fact2"],
            "next_steps": [{action, owner, timing}],
            "review_type": "from playbook",
            "review_timing": "from playbook"
          }
        ]
      }
    ],
    "summary": {
      "total_accounts": N,
      "eligible_count": X,
      "not_eligible_count": Y,
      "cannot_confirm_count": Z,
      "processing_latency_ms": T
    }
  }
  ```
- Validate structure
- Return ready-to-send JSON
- Log payload validation results

**Error Handling**:
- If results list is empty → return minimal valid payload, log WARNING
- If reason missing fields → log ERROR, skip that reason
- Invalid payload structure → raise exception

**Logging**:
- DEBUG: "Building LLM payload for [N] accounts"
- INFO: "Payload complete: [N] reasons total, structure valid"
- ERROR: "Payload validation failed: [reason]"

**Dependencies**: Standard library (json, uuid)
**Test**: Produces valid JSON, all account results included, summary counts accurate

---

## Phase 5: Integration & Orchestration

### Step 9: Build Eligibility Orchestrator (`eligibility/orchestrator.py`)
**Purpose**: Tie all components together in correct sequence

**Responsibilities**:
- **On app startup**:
  - Initialize config_loader (may raise if config files bad)
  - Initialize data_loader (may raise if data files bad)
- **On user message**:
  1. Call intent_detector → is_eligibility_check?
  2. If no → return None (pass to normal RAG flow)
  3. If yes → call account_extractor
  4. If no accounts → ask user for accounts, return None
  5. Call account_validator
  6. If no valid accounts → return error message with invalid list
  7. Call eligibility_processor
  8. Call llm_payload_builder
  9. Return payload ready for LLM
- Log orchestration flow with request_id at each step
- Handle all exceptions, log with traceback

**Error Handling**:
- Config/data load failures → log CRITICAL, halt startup
- Intent detection errors → log ERROR, return None
- Validation failures → log WARNING, return user-friendly message
- Processing errors → log ERROR, return error response

**Logging**:
- INFO: "Eligibility orchestrator initialized"
- INFO: "Eligibility flow triggered: request_id=[ID]"
- DEBUG: "Step [N]: [description]"
- ERROR: "[step] failed: [error_message]"

**Dependencies**: All 7 previous components
**Test**: Correct sequence, all errors handled, returns proper response format

---

### Step 10: Integrate with Main App (`app.py` or `query_data.py`)
**Purpose**: Call eligibility orchestrator from RAG chat flow

**Responsibilities**:
- Import orchestrator
- Before/after user message → call orchestrator.process_message()
- If eligibility payload returned → send to LLM with special prompting
- If None returned → continue with normal RAG flow
- Log integration points with session_id

**Decision Point**: 
- Option A: Call in `app.py` (before query_data) → separate eligibility flow
- Option B: Call in `query_data.py` (within RAG query) → integrated flow
- For now: Document both options, implement Option A (cleaner separation)

**Dependencies**: orchestrator
**Test**: Integrates cleanly, eligibility questions routed correctly, normal questions unaffected

---

## Phase 6: Testing & Validation

### Step 11: Unit Tests
- `tests/test_intent_detector.py` → keyword matching
- `tests/test_account_extractor.py` → 10-digit extraction
- `tests/test_account_validator.py` → format validation
- `tests/test_eligibility_processor.py` → logic, normalization, reason extraction
- `tests/test_llm_payload_builder.py` → JSON structure
- `tests/test_orchestrator.py` → integration, error handling

**Dependencies**: pytest, mock fixtures for config/data files
**Test**: All components work independently and in integration

---

### Step 12: Integration Tests
- `tests/integration_test_eligibility.py`
- Full end-to-end flow: user message → LLM payload
- Test with sample data files and config files
- Test error scenarios: missing files, malformed data, invalid accounts

**Dependencies**: Sample data files, sample config files
**Test**: Full pipeline works correctly, error handling works

---

## Implementation Order Summary

```
1. Module Structure Setup
2. Config Loader ← (foundation for step 3)
3. Data Loader ← (foundation for step 7)
4. Intent Detector ← (independent)
5. Account Extractor ← (independent)
6. Account Validator ← (independent)
7. Eligibility Processor ← (depends on 2, 3)
8. LLM Payload Builder ← (depends on 7)
9. Orchestrator ← (depends on 2-8)
10. App Integration ← (depends on 9)
11. Unit Tests ← (depends on 1-9)
12. Integration Tests ← (depends on 1-12)
```

**Critical Path** (blocking):
- Step 1 (setup) → Step 2 (config) → Step 3 (data) → Step 7 (processor)

**Parallel Tracks** (can work simultaneously):
- Steps 4, 5, 6 can be done in parallel (independent components)

---

## Key Implementation Notes

### Logging at Each Step
- Always include `request_id` (generate once per eligibility check)
- Hash account numbers in logs (no raw account values)
- Use `RAGLogger` from system logger
- Use `SessionManager` for session_id consistency
- Follow JSON structured format per logging_rules.md

### Error Handling Pattern
```
Try startup loads (config + data)
  → on failure: CRITICAL log + raise exception (app doesn't start)

Try user message processing
  → on failure: log + return user-friendly error
  → never break the app, always return structured response
```

### Caching Strategy
- Config files: load once at startup, never reload
- Data files: load once at startup, never reload
- If data needs refresh, that's a separate feature (not in Phase 1)

### PII Protection in Logs
- Never log raw account numbers
- Never log raw customer names
- Hash user messages before logging
- Extract count only, no details

---

Ready to start implementation?

