# Clarification Patterns Implementation Plan

**Status:** Design & Planning Phase  
**Target:** Deterministic, auditable, zero-risk implementation  
**Scope:** Add clarification response system to eligibility module  

---

## Table of Contents
1. [Core Design Principles](#core-design-principles)
2. [System Overview](#system-overview)
3. [Architecture & File Structure](#architecture--file-structure)
4. [Implementation Steps (Logic & Approach)](#implementation-steps-logic--approach)
5. [Risk Mitigation Strategy](#risk-mitigation-strategy)
6. [Testing Strategy](#testing-strategy)
7. [Decision Tree (Pseudocode)](#decision-tree-pseudocode)
8. [Integration Points](#integration-points)

---

## Core Design Principles

### 1. **Zero-Breaking-Change Rule**
- Existing eligibility checks continue unchanged
- Clarifications are a NEW response path, not a replacement
- If old code works, it still works
- New code is isolated in separate modules

### 2. **Deterministic-Only Rule**
- No randomness, no "pick a hint"
- Exactly one pattern fires per missing requirement
- Same input = same output, always
- Selection logic is rule-based, never probabilistic

### 3. **Audit-First Rule**
- Every decision logged with pattern ID (not message text)
- Why clarification was shown must be traceable
- Pattern selection rationale must be clear in logs
- Pattern variant selection (if any) must be deterministic

### 4. **Backward Compatibility Rule**
- All current tests pass unchanged
- Database schema unchanged
- Message format unchanged
- UI routing logic becomes: eligibility OR rag OR clarification (not replacing)

---

## System Overview

### Current Question-Answer Flow (Before)
```
User Message
    ↓
Orchestrator.process_message()
    ├─ Is eligibility intent? YES → Extract account
    │  ├─ Account found? YES → Run eligibility check → Return payload
    │  └─ Account found? NO → ??? (currently error or unclear handling)
    │
    └─ NOT eligibility → Route to RAG
```

### New Question-Answer Flow (After)
```
User Message
    ↓
Orchestrator.process_message()
    ├─ Is eligibility intent? YES → Extract account
    │  ├─ Can evaluate? YES → Run eligibility check → Return payload
    │  │
    │  └─ Cannot evaluate? → Pattern Detector
    │     ├─ What's missing?
    │     ├─ Select clarification pattern
    │     ├─ Format response from playbook
    │     └─ Return clarification + pattern ID
    │
    └─ NOT eligibility → Route to RAG
```

### Key Difference
- **Before:** Eligibility evaluation required = run check or error
- **After:** Eligibility intent ≠ evaluation ready → return specific clarification

---

## Architecture & File Structure

### New Files to Create

```
eligibility/
├── clarification/                          # NEW FOLDER
│   ├── __init__.py
│   ├── patterns.py                         # Pattern ID constants + detection logic
│   ├── playbook_loader.py                  # Load & parse JSON playbook
│   ├── pattern_detector.py                 # Determine which pattern applies
│   ├── response_formatter.py                # Format final response
│   └── clarification_playbook.json          # Response content
└── config/
    └── clarification_playbook.json          # NEW (moved from above)

utils/
└── logger/
    └── clarification_logger.py              # NEW (audit logging for patterns)
```

### Modified Files

```
eligibility/
├── orchestrator.py                          # MODIFY (call pattern detector)
├── intent_detector.py                       # REVIEW (no changes likely)
├── account_extractor.py                     # REVIEW (possible enhancement)
└── account_validator.py                     # REVIEW (no changes)

app.py                                        # MODIFY (route clarifications)
```

### Not Touched (Zero Risk)
```
database/           # ✅ No changes
rag/                # ✅ No changes
utils/context/      # ✅ No changes
utils/logger/       # ✅ Extend only, don't modify existing
```

---

## Implementation Steps (Logic & Approach)

### **STEP 1: Design Clarification Pattern Architecture**

**What:** Define the mental model and data structure for patterns

**Logic:**
- A pattern is identified by a unique `PATTERN_ID` (e.g., `CLARIFY_ACCOUNT_REQUIRED`)
- Each pattern has:
  - **Name:** Human-readable identifier
  - **Trigger Condition:** What missing requirement triggers this
  - **Default Response:** Primary message text
  - **Alternates:** 1-3 approved variations (same meaning, different tone)
  - **Next Steps:** What user should provide
  - **Audit Fields:** When logged, what metadata to include

**Data Structure (Conceptual):**
```
Pattern {
    id: "CLARIFY_ACCOUNT_REQUIRED"
    name: "Account Not Found"
    trigger_condition: "eligibility_intent AND no_account_extracted"
    default_response: "I can check eligibility for a specific account, but I'll need the 10-digit account number to run the check."
    alternates: [
        "Sure — I can help with eligibility. Please share the account number so I can check it for you.",
        "To confirm eligibility, I need the account number. If you prefer, I can also explain the general eligibility criteria."
    ]
    variant_strategy: "deterministic_round_robin"  # or "always_default"
    audit_label: "ACCOUNT_MISSING"
}
```

**Risk Level:** ⚠️ Low — Design-only, no code execution

---

### **STEP 2: Create Clarification Playbook JSON**

**What:** Write `eligibility/config/clarification_playbook.json` with all pattern responses

**Logic:**
- One file, single source of truth for all clarification responses
- Structure mirrors other playbooks (reason_playbook.json)
- Must include all 6 core patterns (min):
  1. `CLARIFY_ACCOUNT_REQUIRED`
  2. `CLARIFY_MULTIPLE_ACCOUNTS`
  3. `CLARIFY_REASON_LOOKUP`
  4. `CLARIFY_LIMIT_CHECK`
  5. `CLARIFY_PRODUCT_RULES_ONLY`
  6. `CLARIFY_CONTEXT_MISSING`

**Content Requirements:**
- Default message (always grammatically correct, professional, short)
- 2-3 approved alternates (pre-approved for tone variation)
- No random text or generated content
- Plain language (no jargon)
- Always actionable (tell user what to do next)

**File Format:**
```json
{
  "CLARIFY_ACCOUNT_REQUIRED": {
    "name": "Account Not Found",
    "category": "missing_account",
    "default": "I can check eligibility for a specific account, but I'll need the 10-digit account number to run the check.",
    "alternates": [
      "Sure — I can help with eligibility. Please share the account number so I can check it for you.",
      "To confirm eligibility, I need the account number. If you prefer, I can also explain the general eligibility criteria."
    ],
    "audit_label": "ACCOUNT_MISSING"
  },
  ...
}
```

**Risk Level:** ⚠️ Low — Compliance & content review only

---

### **STEP 3: Build Pattern Detector Module**

**File:** `eligibility/clarification/pattern_detector.py`

**What:** Logic to determine which pattern applies to a given situation

**Inputs:**
- `message`: Original user message
- `eligibility_intent`: Boolean (is this eligibility-related?)
- `extracted_accounts`: List of account numbers found
- `validation_result`: Account validation result (found/not found)
- `conversation_context`: Previous messages (to check user context)

**Output:**
```
PatternDetectionResult {
    pattern_id: "CLARIFY_ACCOUNT_REQUIRED" | None
    reason: "No account numbers were extracted from the message"
    severity: "REQUIRED_INPUT"
    missing_field: "account_number"
    can_proceed: False
}
```

**Decision Logic (Pseudocode):**
```
def detect_pattern(message, eligibility_intent, extracted_accounts, validation_result, context):
    
    # Rule 1: Not eligibility-related → No pattern (route to RAG)
    if NOT eligibility_intent:
        return None
    
    # Rule 2: Multiple accounts detected → Clarify which one
    if len(extracted_accounts) > 1:
        return PatternDetectionResult(
            pattern_id="CLARIFY_MULTIPLE_ACCOUNTS",
            reason=f"Found {len(extracted_accounts)} account numbers",
            missing_field="account_selection"
        )
    
    # Rule 3: No accounts extracted, none in context → Basic requirement
    if len(extracted_accounts) == 0:
        if has_account_in_context(context):
            return PatternDetectionResult(
                pattern_id="CLARIFY_CONTEXT_MISSING",
                reason="User said 'my account' but no account in conversation history",
                missing_field="explicit_account_number"
            )
        else:
            return PatternDetectionResult(
                pattern_id="CLARIFY_ACCOUNT_REQUIRED",
                reason="No account numbers provided",
                missing_field="account_number"
            )
    
    # Rule 4: Account extracted but not found in data
    if len(extracted_accounts) == 1:
        extracted_account = extracted_accounts[0]
        if NOT validation_result.account_found:
            # Check if user is asking specifically for reason
            if is_reason_question(message):
                return PatternDetectionResult(
                    pattern_id="CLARIFY_REASON_LOOKUP",
                    reason="Asked for reason but account not found",
                    missing_field="valid_account_number"
                )
            elif is_limit_question(message):
                return PatternDetectionResult(
                    pattern_id="CLARIFY_LIMIT_CHECK",
                    reason="Asked for limit but account not found",
                    missing_field="valid_account_number"
                )
        else:
            # Account exists, can proceed → NO pattern
            return None
    
    # If we get here, can evaluate eligibility
    return None
```

**Risk Level:** ⚠️ Medium — Core logic, but isolated and testable

**Risk Mitigation:**
- Each rule is independent (can test in isolation)
- Falls back to `None` (no pattern) if uncertain
- No external dependencies
- All paths have a documented reason

---

### **STEP 4: Build Playbook Loader**

**File:** `eligibility/clarification/playbook_loader.py`

**What:** Load and cache the clarification playbook JSON

**Logic:**
```
PlaybookLoader:
    - Load JSON file from eligibility/config/clarification_playbook.json
    - Validate schema (all required fields present)
    - Cache in memory (singleton pattern)
    - Provide get_pattern(pattern_id) method
    - Provide get_all_patterns() method
    - Error handling: Log warning if JSON invalid, return empty dict

get_pattern(pattern_id: str) → Pattern:
    if pattern_id not in cache:
        log_warning(f"Pattern {pattern_id} not in playbook")
        return None
    return cache[pattern_id]

validate_playbook(json_data) → bool:
    for pattern_id, pattern_content in json_data.items():
        assert "default" in pattern_content
        assert "alternates" in pattern_content (or empty list)
        assert len(pattern_content["default"]) > 0
    return True
```

**Integration:**
- Loaded same way as other playbooks (event at app startup)
- Singleton instance (loaded once, reused)
- Error doesn't break app (defaults to no clarification)

**Risk Level:** ⚠️ Low — Standard loader, similar patterns already exist

---

### **STEP 5: Build Response Formatter**

**File:** `eligibility/clarification/response_formatter.py`

**What:** Convert a detected pattern into a formated response for the user

**Logic:**
```
format_clarification_response(pattern_id: str, conversation_id: str) → Dict:
    
    # Get pattern from playbook
    pattern = playbook_loader.get_pattern(pattern_id)
    if pattern is None:
        return None  # Fail safe
    
    # Determine variant (deterministic, not random)
    variant_index = determine_variant(conversation_id, pattern_id)
    
    # Get response text
    if variant_index == 0:
        response_text = pattern["default"]
    else:
        response_text = pattern["alternates"][variant_index - 1]
    
    # Build response structure (same as RAG response)
    return {
        "type": "clarification",
        "pattern_id": pattern_id,
        "message": response_text,
        "variant": variant_index,
        "next_step": pattern.get("next_steps", "Provide the missing information")
    }

determine_variant(conversation_id: str, pattern_id: str) → int:
    """
    Deterministic variant selection.
    Not random. Always same for same conversation + pattern.
    """
    # Option 1: Always use default
    # return 0
    
    # Option 2: Deterministic rotation based on conversation context
    context_hash = hash(f"{conversation_id}_{pattern_id}")
    num_variants = 1 + len(pattern.get("alternates", []))
    return context_hash % num_variants
```

**Output Structure:**
```
{
    "type": "clarification",
    "pattern_id": "CLARIFY_ACCOUNT_REQUIRED",
    "message": "I can check eligibility for a specific account, but I'll need the 10-digit account number to run the check.",
    "variant": 0,
    "next_step": "Please provide your account number"
}
```

**Risk Level:** ⚠️ Low — Just formatting and selection, state

-free

---

### **STEP 6: Create Clarification Decision Tree (in Orchestrator)**

**File:** `eligibility/orchestrator.py` (MODIFY)

**What:** Integrate pattern detection into the orchestrator's main flow

**Current Logic (Conceptual):**
```
process_message(message, conversation_id):
    if NOT is_eligibility_intent(message):
        return route_to_rag(message)
    
    extracted_accounts = extract_accounts(message)
    
    if len(extracted_accounts) == 0:
        # Currently: unclear handling or error
        # NEW: Detect if clarification is needed
    
    # Check eligibility rules
    result = evaluate_eligibility(extracted_accounts[0])
    return result
```

**New Logic (Conceptual):**
```
process_message(message, conversation_id):
    
    # Step 1: Classify intent
    eligibility_intent = detect_intent(message)
    
    if NOT eligibility_intent:
        # Route to RAG, no clarification
        return {
            "type": "rag",
            "destination": "query_rag"
        }
    
    # Step 2: Extract & validate accounts
    extracted_accounts = extract_accounts(message)
    validation_result = validate_accounts(extracted_accounts)
    
    # Step 3: NEW — Detect if clarification needed
    pattern = pattern_detector.detect_pattern(
        message=message,
        eligibility_intent=True,
        extracted_accounts=extracted_accounts,
        validation_result=validation_result,
        context=get_conversation_context(conversation_id)
    )
    
    if pattern is not None:
        # Step 4: Format and return clarification
        clarification_response = response_formatter.format_clarification_response(
            pattern_id=pattern.pattern_id,
            conversation_id=conversation_id
        )
        
        # Log the decision
        log_clarification_decision(pattern, message, conversation_id)
        
        return {
            "type": "clarification",
            "data": clarification_response
        }
    
    # Step 5: Proceed with eligibility check
    account = extracted_accounts[0]
    eligibility_result = evaluate_eligibility(account)
    
    return {
        "type": "eligibility",
        "data": eligibility_result
    }
```

**Risk Level:** 🔴 Medium-High — Modifies core orchestrator

**Risk Mitigation:**
- Add as new conditional path (don't remove old logic)
- Design tree such that all outcomes have explicit handling
- Every branch returns a clear "type" (rag, eligibility, or clarification)
- Test all branches before merging
- Can be toggled with a feature flag if needed

---

### **STEP 7: Add Audit Logging for Clarifications**

**File:** `utils/logger/clarification_logger.py` (NEW)

**What:** Log every clarification decision for audit trail

**Events to Log:**
1. **Pattern Detection**
   - Pattern ID selected
   - Trigger condition that fired
   - Missing requirement
   - Not the message text itself

2. **Response Formatting**
   - Variant selected (default vs. alternate)
   - Response text length
   - Timestamp

3. **Decision Rationale**
   - Why this pattern was chosen
   - What was missing
   - Severity level

**Log Format (JSON):**
```json
{
  "event": "clarification_pattern_detected",
  "request_id": "abc123",
  "timestamp": "2026-02-09T18:30:00Z",
  "pattern_id": "CLARIFY_ACCOUNT_REQUIRED",
  "pattern_name": "Account Not Found",
  "trigger_condition": "eligibility_intent AND no_account_extracted",
  "missing_field": "account_number",
  "severity": "REQUIRED_INPUT",
  "can_proceed": false,
  "audit_label": "ACCOUNT_MISSING",
  "variant": 0,
  "session_id": "xyz789"
}
```

**Integration Points:**
- Called from orchestrator after pattern detection
- Only logs pattern ID, not actual message (privacy)
- Searchable by request_id for tracing
- Can be analyzed for metrics (e.g., "how often do users clarify after this pattern?")

**Risk Level:** ⚠️ Low — Additive only

---

### **STEP 8: Implement Backward Compatibility**

**What:** Ensure existing flows still work, no breaking changes

**Compatibility CheckList:**
- [ ] All existing eligibility checks still execute
- [ ] RAG routing unchanged for non-eligibility questions
- [ ] Database schema unchanged
- [ ] Message format unchanged
- [ ] Existing tests pass without modification
- [ ] Conversation history still saved
- [ ] Response timestamp still accurate

**How:**
- Clarifications are a NEW response type ("clarification")
- Don't modify existing "eligibility" or "rag" types
- If pattern detector returns `None`, proceed as before
- Feature flag available (if needed): `ENABLE_CLARIFICATION_PATTERNS=true`

**Risk Level:** ⚠️ Low — Additive design, no modifications to core classes

---

## Risk Mitigation Strategy

### Risk 1: Breaking Existing Eligibility Checks
**Mitigation:**
- Pattern detector returns `None` if uncertain
- Orchestrator only calls pattern detector if intent is eligibility
- All existing checks still run (pattern detector is a pre-check)
- Zero changes to eligibility evaluation logic
- Test: Run all existing eligibility tests unchanged

### Risk 2: Unclear Decision Tree Logic
**Mitigation:**
- Every decision path documented with pseudocode
- Each rule has explicit condition and outcome
- Logging captures why pattern was chosen
- Clear "fall-through" behavior (no implicit paths)
- Test: Unit test each rule independently

### Risk 3: Playbook Content Quality
**Mitigation:**
- Responses pre-written by human (user provided samples)
- Compliance review before deployment
- No LLM-generated content
- All alternates approved (not auto-generated)
- Test: Manual review of all 6 patterns before merge

### Risk 4: Database or Schema Issues
**Mitigation:**
- Zero database changes
- Clarifications stored in conversation history (not new table)
- Backward compatible (old messages don't break)
- No migration needed
- Test: Run existing database tests

### Risk 5: Performance Impact
**Mitigation:**
- Playbook loader is O(1) (cached)
- Pattern detector is O(n) where n = extracted accounts (tiny)
- Response formatter is O(1)
- Total latency: ~10-50ms (negligible)
- Test: Benchmark pattern detection

### Risk 6: Logging Privacy Leaks
**Mitigation:**
- Log pattern ID, not message text
- Log missing field, not extracted values
- Use audit_label instead of user intent
- No PII in pattern logs
- Test: Audit log review

---

## Testing Strategy

### **Phase 1: Unit Tests (Pattern Detection)**

**Test Files:**
- `tests/eligibility/clarification/test_pattern_detector.py`
- `tests/eligibility/clarification/test_playbook_loader.py`
- `tests/eligibility/clarification/test_response_formatter.py`

**Test Cases (Per Pattern):**

```
For CLARIFY_ACCOUNT_REQUIRED:
  ✓ Intent=eligibility, no accounts → pattern fires
  ✓ Intent=eligibility, empty string accounts → pattern fires
  ✓ Intent=not_eligibility, no accounts → pattern=None
  ✓ Intent=eligibility, account found → pattern=None

For CLARIFY_MULTIPLE_ACCOUNTS:
  ✓ Intent=eligibility, 2 accounts → pattern fires
  ✓ Intent=eligibility, 3 accounts → pattern fires
  ✓ Intent=eligibility, 1 account → pattern=None

For CLARIFY_REASON_LOOKUP:
  ✓ Message contains "why", no accounts → pattern fires
  ✓ Message contains "why", invalid account → pattern fires
  ✓ Message contains "why", valid account → pattern=None

For CLARIFY_CONTEXT_MISSING:
  ✓ Current message says "my account", context empty → pattern fires
  ✓ Current message says "my account", context has account → pattern=None
```

**Risk Level:** ⚠️ Low — Isolated, deterministic tests

### **Phase 2: Integration Tests (Orchestrator)**

**Test File:**
- `tests/eligibility/test_orchestrator_with_clarification.py`

**Test Scenarios:**

```
Scenario 1: New user, eligibility question, no account
  Input: "Am I eligible?"
  Expected: type="clarification", pattern_id="CLARIFY_ACCOUNT_REQUIRED"

Scenario 2: User asks reason without account
  Input: "Why am I not eligible?"
  Expected: type="clarification", pattern_id="CLARIFY_REASON_LOOKUP"

Scenario 3: User provides account, passes validation
  Input: "Check eligibility for account 1234567890"
  Expected: type="eligibility", data=<eligibility_payload>

Scenario 4: User asks general product question
  Input: "What is a digital loan?"
  Expected: type="rag", destination="query_rag"

Scenario 5: Multiple accounts provided
  Input: "Check if 1234567890 or 9876543210 is eligible"
  Expected: type="clarification", pattern_id="CLARIFY_MULTIPLE_ACCOUNTS"
```

**Risk Level:** ⚠️ Medium — Tests actual orchestrator behavior

### **Phase 3: End-to-End Tests (UI)**

**Test File:**
- `tests/test_clarification_e2e.py`

**Test Scenarios:**

```
E2E 1: User starts conversation, asks eligibility without account
  1. User types "Am I eligible?"
  2. UI receives clarification response
  3. Message saved to DB
  4. Clarification pattern_id logged
  5. User can respond with account
  6. Next query runs eligibility check

E2E 2: User provides multiple accounts
  1. User types "Check accounts 123 and 456"
  2. UI receives clarification asking which one
  3. User responds "456"
  4. System re-processes, now runs check
```

**Risk Level:** 🔴 High — Full system integration

---

## Decision Tree (Pseudocode)

### Master Decision Tree (Orchestrator)

```
INPUT: message, conversation_id

STEP 1: Intent Classification
  eligibility_intent = classify_intent(message)
  
STEP 2: Route by Intent
  IF NOT eligibility_intent:
    RETURN { type: "rag" }
  END IF
  
STEP 3: Account Extraction
  extracted_accounts = extract_accounts(message)
  validation_result = validate_accounts(extracted_accounts)
  conversation_context = get_context(conversation_id)
  
STEP 4: Pattern Detection (NEW)
  pattern = detect_pattern(
    message = message,
    eligibility_intent = True,
    extracted_accounts = extracted_accounts,
    validation_result = validation_result,
    context = conversation_context
  )
  
STEP 5: Handle Pattern
  IF pattern IS NOT NULL:
    formatted_response = format_response(pattern)
    log_clarification(pattern, message, conversation_id)
    RETURN { type: "clarification", data: formatted_response }
  END IF
  
STEP 6: Proceed with Eligibility
  eligible_account = extracted_accounts[0]
  eligibility_payload = evaluate_eligibility(eligible_account)
  RETURN { type: "eligibility", data: eligibility_payload }
```

### Pattern Detection Tree (Detailed)

```
INPUT: message, eligibility_intent, extracted_accounts, validation_result, context

// Rule 1: Multiple accounts detected
IF len(extracted_accounts) > 1:
  RETURN Pattern(
    id: "CLARIFY_MULTIPLE_ACCOUNTS",
    reason: "More than one account found",
    missing_field: "account_selection"
  )
END IF

// Rule 2: No accounts extracted
IF len(extracted_accounts) == 0:
  
  // Sub-rule: Check if mentioned in context
  IF context.has_account_reference():
    RETURN Pattern(
      id: "CLARIFY_CONTEXT_MISSING",
      reason: "User referred to account, but not provided",
      missing_field: "explicit_account_number"
    )
  ELSE:
    RETURN Pattern(
      id: "CLARIFY_ACCOUNT_REQUIRED",
      reason: "No account information provided",
      missing_field: "account_number"
    )
  END IF
END IF

// Rule 3: One account extracted, validate it
IF len(extracted_accounts) == 1:
  account = extracted_accounts[0]
  
  IF validation_result.account_found == FALSE:
    
    // Sub-rule: Determine user intent
    IF message_contains(message, keywords: ["why", "reason", "excluded"]):
      RETURN Pattern(
        id: "CLARIFY_REASON_LOOKUP",
        reason: "Asked for reason, but account not found",
        missing_field: "valid_account_number"
      )
    END IF
    
    IF message_contains(message, keywords: ["limit", "how much"]):
      RETURN Pattern(
        id: "CLARIFY_LIMIT_CHECK",
        reason: "Asked for limit, but account not found",
        missing_field: "valid_account_number"
      )
    END IF
    
    // Default for invalid account
    RETURN Pattern(
      id: "CLARIFY_ACCOUNT_REQUIRED",
      reason: "Account number provided but not found in system",
      missing_field: "valid_account_number"
    )
  ELSE:
    // Account found and valid, can proceed
    RETURN NULL  // No pattern, proceed to evaluation
  END IF
END IF

// Fallback: If we get here, can evaluate
RETURN NULL
```

---

## Integration Points

### 1. **Orchestrator Integration** (High Priority)
- Import: `from eligibility.clarification.pattern_detector import PatternDetector`
- Call: `pattern = detector.detect_pattern(...)`
- Return: Add new response type check

### 2. **App.py Integration** (Medium Priority)
- Check response type: `if response.type == "clarification"`
- Route accordingly: Show clarification message instead of function-specific rendering
- No changes to existing eligibility/RAG routes

### 3. **Database Integration** (Low Priority)
- Clarification messages saved as regular conversation history
- Same schema, just type="clarification" in metadata
- Query message history: Works unchanged

### 4. **Logging Integration** (Medium Priority)
- Import: `from utils.logger.clarification_logger import log_clarification_decision`
- Call: `log_clarification_decision(pattern, message, conversation_id)`
- No changes to existing logs

### 5. **Testing Integration** (Medium Priority)
- New test files don't affect existing tests
- Existing tests pass unchanged
- New tests added in `tests/eligibility/clarification/`

---

## Implementation Sequence (Safe Order)

**PHASE 1: Foundations (Days 1-2)**
1. Create clarification_playbook.json
2. Design pattern constants (PATTERN_IDs)
3. Create playbook_loader.py
4. Create response_formatter.py

**PHASE 2: Logic (Days 3-4)**
1. Create pattern_detector.py with all rules
2. Unit test pattern_detector (isolated)
3. Create clarification_logger.py
4. Unit test response formatting

**PHASE 3: Integration (Days 5-6)**
1. Modify orchestrator.py to call detector
2. Integration test orchestrator
3. Modify app.py for response routing
4. E2E test full flow

**PHASE 4: Validation (Day 7)**
1. Run ALL existing tests (must pass)
2. Manual QA of all patterns
3. Audit log review
4. Compliance check

**PHASE 5: Deployment (Day 8)**
1. Code review
2. Merge to branch
3. Staging validation
4. Production deployment

---

## Success Criteria

- [ ] All existing tests pass unchanged
- [ ] 6 clarification patterns detected correctly (unit tests)
- [ ] Pattern detector logic is deterministic (same input = same output)
- [ ] All clarification logs audit-compliant (pattern ID, not message text)
- [ ] UI shows clarification messages correctly
- [ ] Users can understand what's missing from clarification
- [ ] No database changes required (backward compatible)
- [ ] Logging captures why clarification was shown
- [ ] Zero impact on eligibility or RAG logic

---

**End of Implementation Plan**
