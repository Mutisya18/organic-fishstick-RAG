This schema is designed to be:

* **Deterministic** (no assumptions)
* **Multi-reason capable**
* **Evidence-backed** (human-friendly facts included)
* **Strictly aligned** to your Reasons File rules (Exclude + Recency=N)
* **Staff-response ready** (fixed output sections)

---

# ✅ Runtime LLM Input JSON Schema (Implementation-Ready)

### Suggested name

`llm_input_payload.schema.json`

```json
{
  "schema_version": "1.0",
  "payload_type": "LOAN_LIMIT_INELIGIBILITY_EXPLANATION_REQUEST",

  "request": {
    "request_id": "string",
    "timestamp_utc": "string",
    "user_intent": "explain_loan_limit_ineligibility",
    "query_text": "string",
    "account_number": "string"
  },

  "lookup_result": {
    "found_in_reasons_file": "boolean",
    "not_found_message": "string"
  },

  "customer": {
    "customer_name": "string",
    "account_number": "string"
  },

  "system_rules": {
    "reasons_file_context": {
      "contains_only_ineligible_accounts": true,
      "eligible_accounts_not_present": true
    },
    "extraction_rules": [
      "Extract all checks where value = Exclude",
      "Also treat Recency_Check = N as an exclusion reason",
      "Always return multi-reason output",
      "Do not infer or guess missing values"
    ],
    "ignore_fields": ["Normalized_Mean"]
  },

  "row_snapshot": {
    "checks": {
      "Joint_Check": "string",
      "Average_Bal_check": "string",
      "DPD_Arrears_Check": "string",
      "Elma_check": "string",
      "Mandates_Check": "string",
      "Classification_Check": "string",
      "Linked_Base_Check": "string",
      "customer_vintage_Check": "string",
      "Active_Inactive_Check": "string",
      "Turnover_Check": "string",
      "Recency_Check": "string"
    },
    "evidence": {
      "CLASSIFICATION": "string",
      "dormancy_status": "string",
      "Arrears_Days": "number",
      "Credit_Card_OD_Days": "number",
      "DPD_Days": "number",
      "customer_vintage_Months": "number",
      "JOINT_ACCOUNT": "string",
      "LINKED_BASE": "string",
      "LINKED_BASE_CLASSIFICATION": "string",
      "Mandate": "string"
    }
  },

  "extracted_reasons": [
    {
      "reason_code": "string",
      "triggered_by": [
        {
          "column": "string",
          "value": "string"
        }
      ],
      "evidence": {
        "key_values": {
          "field": "value"
        }
      },
      "facts_for_explanation": [
        "string"
      ],
      "remediation_playbook": {
        "meaning": "string",
        "next_steps": [
          {
            "action": "string",
            "owner": "string"
          }
        ],
        "review_type": "string",
        "review_timing": "string",
        "manual_override_allowed": "boolean",
        "constraints": [
          "string"
        ]
      }
    }
  ],

  "response_format_required": {
    "sections": [
      "Summary",
      "Reasons found",
      "What it means",
      "Next steps (owner + timing)",
      "When to recheck"
    ],
    "tone": "staff-facing, clear, non-technical",
    "constraints": [
      "Do not mention internal file names or system architecture",
      "Do not mention JSON or reason_code in the final response",
      "Use evidence values in a human-friendly way (e.g., DPD days = 7)",
      "If multiple reasons exist, list all reasons"
    ]
  }
}
```

---

# ✅ Example of a Real Runtime Payload (Using Your Dataset)

Sample account: **6917970011** (AARON ABERE LUTUNGU)

This is what you’d actually pass into the LLM:

```json
{
  "schema_version": "1.0",
  "payload_type": "LOAN_LIMIT_INELIGIBILITY_EXPLANATION_REQUEST",

  "request": {
    "request_id": "req-0001",
    "timestamp_utc": "2026-01-23T10:00:00Z",
    "user_intent": "explain_loan_limit_ineligibility",
    "query_text": "Why does this customer not have a loan limit?",
    "account_number": "6917970011"
  },

  "lookup_result": {
    "found_in_reasons_file": true,
    "not_found_message": "Account not found in Reasons File — cannot confirm eligibility from this file alone."
  },

  "customer": {
    "customer_name": "AARON ABERE LUTUNGU",
    "account_number": "6917970011"
  },

  "system_rules": {
    "reasons_file_context": {
      "contains_only_ineligible_accounts": true,
      "eligible_accounts_not_present": true
    },
    "extraction_rules": [
      "Extract all checks where value = Exclude",
      "Also treat Recency_Check = N as an exclusion reason",
      "Always return multi-reason output",
      "Do not infer or guess missing values"
    ],
    "ignore_fields": ["Normalized_Mean"]
  },

  "row_snapshot": {
    "checks": {
      "Joint_Check": "Include",
      "Average_Bal_check": "Include",
      "DPD_Arrears_Check": "Exclude",
      "Elma_check": "Include",
      "Mandates_Check": "Include",
      "Classification_Check": "Exclude",
      "Linked_Base_Check": "Include",
      "customer_vintage_Check": "Include",
      "Active_Inactive_Check": "Include",
      "Turnover_Check": "",
      "Recency_Check": "N"
    },
    "evidence": {
      "CLASSIFICATION": "B10",
      "dormancy_status": "",
      "Arrears_Days": 143,
      "Credit_Card_OD_Days": 0,
      "DPD_Days": 102,
      "customer_vintage_Months": 28,
      "JOINT_ACCOUNT": "N",
      "LINKED_BASE": "",
      "LINKED_BASE_CLASSIFICATION": "",
      "Mandate": ""
    }
  },

  "extracted_reasons": [
    {
      "reason_code": "DPD_ARREARS_EXCLUSION",
      "triggered_by": [
        { "column": "DPD_Arrears_Check", "value": "Exclude" }
      ],
      "evidence": {
        "key_values": {
          "Arrears_Days": 143,
          "Credit_Card_OD_Days": 0,
          "DPD_Days": 102
        }
      },
      "facts_for_explanation": [
        "Customer had DPD/arrears greater than 3 days.",
        "Highest arrears days observed: 143 days (Arrears_Days)."
      ],
      "remediation_playbook": {
        "meaning": "Customer had DPD/arrears greater than 3 days within the past 60 days.",
        "next_steps": [
          { "action": "Customer must clear the arrears position (pay overdue amounts).", "owner": "Customer" },
          { "action": "After clearance, wait a 2-month cooling period starting the next day.", "owner": "System" }
        ],
        "review_type": "Automatic",
        "review_timing": "After 2-month cooling period",
        "manual_override_allowed": false,
        "constraints": [
          "Cooling resets if arrears >3 days occur again."
        ]
      }
    },
    {
      "reason_code": "CLASSIFICATION_EXCLUSION",
      "triggered_by": [
        { "column": "Classification_Check", "value": "Exclude" }
      ],
      "evidence": {
        "key_values": {
          "CLASSIFICATION": "B10"
        }
      },
      "facts_for_explanation": [
        "Customer risk classification is below the minimum required level (A5).",
        "Observed classification: B10."
      ],
      "remediation_playbook": {
        "meaning": "Customer risk classification is below the minimum required level (A5).",
        "next_steps": [
          { "action": "RM to liaise with Portfolio Management for classification review/upgrade.", "owner": "RM/Portfolio Management" },
          { "action": "Customer may request a classification review.", "owner": "Customer" }
        ],
        "review_type": "Portfolio Management review",
        "review_timing": "Unknown / not explicitly defined",
        "manual_override_allowed": false,
        "constraints": [
          "Must be upgraded to A5 or higher."
        ]
      }
    },
    {
      "reason_code": "RECENCY_EXCLUSION",
      "triggered_by": [
        { "column": "Recency_Check", "value": "N" }
      ],
      "evidence": {
        "key_values": {
          "Recency_Check": "N"
        }
      },
      "facts_for_explanation": [
        "Customer has inconsistent recent banking patterns (amounts and/or frequency)."
      ],
      "remediation_playbook": {
        "meaning": "Recent banking behaviour is irregular, which fails the consistency requirement.",
        "next_steps": [
          { "action": "Maintain more consistent transaction frequency and amounts.", "owner": "Customer" }
        ],
        "review_type": "System review",
        "review_timing": "Unknown / not explicitly defined",
        "manual_override_allowed": false,
        "constraints": [
          "Recency_Check=N is a standalone exclusion reason and must always be listed."
        ]
      }
    }
  ],

  "response_format_required": {
    "sections": [
      "Summary",
      "Reasons found",
      "What it means",
      "Next steps (owner + timing)",
      "When to recheck"
    ],
    "tone": "staff-facing, clear, non-technical",
    "constraints": [
      "Do not mention internal file names or system architecture",
      "Do not mention JSON or reason_code in the final response",
      "Use evidence values in a human-friendly way (e.g., DPD days = 7)",
      "If multiple reasons exist, list all reasons"
    ]
  }
}
```

---

# ✅ What this guarantees

With this payload, the LLM can generate staff-facing output that is:

* consistent every time
* evidence-backed
* never invents thresholds
* never misses Recency=N
* always lists all reasons
* includes owners + timing constraints

---
