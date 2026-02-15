# App Integration - Quick Reference

## How Eligibility Module Integrates with app.py

### Phase 1: Startup (app loads)

```
eligibility/
├── __init__.py                          # Module exports
├── config_loader.py                     # Load JSON configs
├── data_loader.py                       # Load Excel data
├── intent_detector.py                   # Detect eligibility questions
├── account_extractor.py                 # Extract 10-digit accounts
├── account_validator.py                 # Validate account format
├── eligibility_processor.py              # Core business logic
├── llm_payload_builder.py               # Format results for LLM
├── orchestrator.py                      # Orchestrate flow
├── config/
│   ├── checks_catalog.json              # Column definitions
│   ├── reason_detection_rules.json      # Extraction rules
│   └── reason_playbook.json             # Remediation steps
├── data/
│   ├── eligible_customers.xlsx          # Eligible accounts
│   └── reasons_file.xlsx                # Ineligible + reasons
├── DESIGN.md                            # Architecture decisions
├── IMPLEMENTATION.md                    # Implementation steps
└── IMPLEMENTATION_SUMMARY.md            # What was built
```

---

## Basic Usage

### Initialize Orchestrator (at app startup)
```python
from eligibility.orchestrator import EligibilityOrchestrator

# Startup - may raise if config/data files are bad
try:
    orchestrator = EligibilityOrchestrator()
except Exception as e:
    print(f"Eligibility service unavailable: {e}")
    # App should handle gracefully (service disabled)
```

### Process User Message
```python
user_message = "Is customer 1234567890 eligible for a loan limit?"
result = orchestrator.process_message(user_message)

if result is None:
    # Not an eligibility question - route to normal RAG
    rag_response = query_rag(user_message)
    
elif result.get("status") == "ERROR":
    # Validation error - show user-friendly message
    print(result.get("error_message"))
    
else:
    # Eligibility payload ready for LLM
    llm_response = call_llm_with_eligibility_prompt(result)
```

---

## Component Reference

### IntentDetector
```python
detector = IntentDetector()
is_eligibility, message_hash = detector.detect(user_message)
# Returns: (bool, str)
```

### AccountExtractor
```python
extractor = AccountExtractor()
accounts = extractor.extract(user_message)
# Returns: ["1234567890", "9876543210"]
```

### AccountValidator
```python
validator = AccountValidator()
valid, invalid = validator.validate(["1234567890", "123"])
# Returns: (["1234567890"], ["123"])
# Also: AccountValidator.is_valid("1234567890") → bool
```

### EligibilityProcessor
```python
processor = EligibilityProcessor()
results = processor.process_accounts(
    ["1234567890"],
    request_id="abc-123"
)
# Returns: [
#   {
#     "account_number_hash": "...",
#     "status": "ELIGIBLE|NOT_ELIGIBLE|CANNOT_CONFIRM",
#     "reasons": [
#       {
#         "code": "JOINT_ACCOUNT_EXCLUSION",
#         "meaning": "...",
#         "facts": ["..."],
#         "next_steps": [...],
#         "review_type": "...",
#         "review_timing": "..."
#       }
#     ]
#   }
# ]
```

### LLMPayloadBuilder
```python
builder = LLMPayloadBuilder()
payload = builder.build(results, request_id="abc-123")
# Returns: dict ready for LLM

# Or serialize to JSON string:
json_str = builder.build_to_json_string(results, request_id="abc-123")
```

---

## Configuration Files

### checks_catalog.json
- **Defines**: Column names, types, roles (identifier/check/evidence/ignore)
- **Used by**: Data loader for validation, processor for normalization
- **Update when**: Adding new checks or evidence fields

### reason_detection_rules.json
- **Defines**: How to extract reasons (which check → which reason code)
- **Used by**: Eligibility processor to determine triggers and build facts
- **Update when**: Adding new reasons or changing extraction logic

### reason_playbook.json
- **Defines**: Staff-facing content (meaning, next steps, timing, constraints)
- **Used by**: Eligibility processor to enrich extracted reasons
- **Update when**: Changing remediation steps or timing rules

---

## Data Files

### eligible_customers.xlsx
- **Purpose**: Lookup table of eligible account numbers
- **Key column**: ACCOUNTNO (10-digit string)
- **Constraint**: If account exists here, status = ELIGIBLE
- **Note**: Should never overlap with reasons_file.xlsx

### reasons_file.xlsx
- **Purpose**: Lookup table of ineligible accounts with evidence
- **Key column**: account_number (10-digit string)
- **Columns**: Follow checks_catalog exactly (identifiers, checks, evidence)
- **Constraint**: If account exists here, status = NOT_ELIGIBLE
- **Note**: Should never overlap with eligible_customers.xlsx

---

## Return Value Examples

### Eligibility Question Detected
```python
{
  "request_id": "abc-123",
  "batch_timestamp": "2026-01-24T10:00:00Z",
  "accounts": [
    {
      "account_number_hash": "hash1234",
      "status": "NOT_ELIGIBLE",
      "reasons": [
        {
          "code": "DPD_ARREARS_EXCLUSION",
          "meaning": "Customer had DPD/arrears greater than 3 days...",
          "facts": ["Customer had DPD/arrears greater than 3 days.", "Highest arrears days observed: 15 days (Arrears_Days)."],
          "next_steps": [
            {"action": "Customer must clear...", "owner": "Customer"},
            {"action": "After clearance, wait...", "owner": "System"}
          ],
          "review_type": "Automatic",
          "review_timing": "After 2-month cooling period"
        }
      ]
    }
  ],
  "summary": {
    "total_accounts": 1,
    "eligible_count": 0,
    "not_eligible_count": 1,
    "cannot_confirm_count": 0,
    "total_reasons_extracted": 1,
    "processing_latency_ms": 45.2
  }
}
```

### Not an Eligibility Question
```python
None  # Route to normal RAG flow
```

### Validation Error
```python
{
  "request_id": "abc-123",
  "status": "ERROR",
  "error_type": "No account numbers found",
  "error_message": "Please share the 10-digit account number(s) so I can confirm eligibility.",
  "accounts": [],
  "summary": {...}
}
```

---

## Logging

All operations logged to structured JSON logs:

```
event: "eligibility_flow_start"
severity: "INFO"
request_id: "unique-id"
context: {...}

event: "intent_detection"
severity: "DEBUG"
context: {message_hash: "...", is_eligibility_check: true}

event: "account_extraction"
severity: "DEBUG"
context: {account_count: 2}

event: "account_validation"
severity: "DEBUG"
context: {valid_count: 2, invalid_count: 0}

event: "eligibility_processing_complete"
severity: "INFO"
context: {eligible_count: 0, not_eligible_count: 1, cannot_confirm_count: 0}

event: "eligibility_flow_complete"
severity: "INFO"
context: {total_latency_ms: 150.3}
```

---

## Performance

- **Startup**: ~50-100ms (loading configs and indexing data)
- **Per message**:
  - Intent detection: ~1ms
  - Account extraction: <1ms
  - Account validation: <1ms
  - Eligibility processing: ~20-50ms (depends on batch size)
  - Payload building: ~5-10ms
  - **Total**: ~30-100ms per user message

---

## Error Scenarios

| Scenario | Return | Log Level |
|----------|--------|-----------|
| Config files missing/bad | Raise exception (startup) | CRITICAL |
| Data files missing/bad | Raise exception (startup) | CRITICAL |
| No accounts extracted | Error response | WARNING |
| Invalid account format | Error response | WARNING |
| Processing error | Error response | ERROR |
| LLM payload invalid | Error response | ERROR |
| Not eligibility question | None | DEBUG |

---

## Requirements

Add to `requirements.txt`:
```
openpyxl
```

---

## Next: App Integration

To integrate into main app, see [Step 10 in IMPLEMENTATION.md](./IMPLEMENTATION.md#step-10-integrate-with-main-app)

