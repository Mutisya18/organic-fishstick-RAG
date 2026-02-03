# ✅ FILE 1 — Checks Catalog (Structure / Data Contract)

### Purpose

Defines the **Reasons File schema**:

* which columns exist
* which ones are checks vs evidence
* allowed values per column
* how blanks/nulls should be treated

### Suggested filename

`checks_catalog.json`

```json
{
  "version": "1.0",
  "file_type": "CHECKS_CATALOG",
  "description": "Defines the Reasons File structure, check columns, evidence columns, expected values, and normalization rules.",
  "primary_key": "account_number",
  "dataset_rules": {
    "reasons_file_contains_only_ineligible_accounts": true,
    "eligible_accounts_not_present_in_this_file": true
  },
  "columns": [
    {
      "name": "CUSTOMERNAMES",
      "type": "string",
      "role": "identifier",
      "required": false
    },
    {
      "name": "account_number",
      "type": "string",
      "role": "identifier",
      "required": true,
      "format_hint": "10-digit account number"
    },

    {
      "name": "Joint_Check",
      "type": "string",
      "role": "check",
      "expected_values": ["Include", "Exclude", ""]
    },
    {
      "name": "Average_Bal_check",
      "type": "string",
      "role": "check",
      "expected_values": ["Include", "Exclude", ""]
    },
    {
      "name": "DPD_Arrears_Check",
      "type": "string",
      "role": "check",
      "expected_values": ["Include", "Exclude", ""]
    },
    {
      "name": "Elma_check",
      "type": "string",
      "role": "check",
      "expected_values": ["Include", "Exclude", ""]
    },
    {
      "name": "Mandates_Check",
      "type": "string",
      "role": "check",
      "expected_values": ["Include", "Exclude", ""]
    },
    {
      "name": "Classification_Check",
      "type": "string",
      "role": "check",
      "expected_values": ["Include", "Exclude", ""]
    },
    {
      "name": "Linked_Base_Check",
      "type": "string",
      "role": "check",
      "expected_values": ["Include", "Exclude", ""]
    },
    {
      "name": "customer_vintage_Check",
      "type": "string",
      "role": "check",
      "expected_values": ["Include", "Exclude", ""]
    },
    {
      "name": "Active_Inactive_Check",
      "type": "string",
      "role": "check",
      "expected_values": ["Include", "Exclude", ""]
    },
    {
      "name": "Turnover_Check",
      "type": "string",
      "role": "check",
      "expected_values": ["Include", "Exclude", ""]
    },

    {
      "name": "Recency_Check",
      "type": "string",
      "role": "check_special",
      "expected_values": ["Y", "N", ""],
      "notes": "Recency_Check=N must be treated as an exclusion reason even if other checks are Include."
    },

    {
      "name": "CLASSIFICATION",
      "type": "string",
      "role": "evidence",
      "required": false
    },
    {
      "name": "dormancy_status",
      "type": "string",
      "role": "evidence",
      "expected_values": ["DORMANT", "INACTIVE", "", null]
    },
    {
      "name": "Arrears_Days",
      "type": "number",
      "role": "evidence",
      "null_handling": "treat_null_as_zero"
    },
    {
      "name": "Credit_Card_OD_Days",
      "type": "number",
      "role": "evidence",
      "null_handling": "treat_null_as_zero"
    },
    {
      "name": "DPD_Days",
      "type": "number",
      "role": "evidence",
      "null_handling": "treat_null_as_zero"
    },
    {
      "name": "customer_vintage_Months",
      "type": "number",
      "role": "evidence",
      "required": false
    },
    {
      "name": "JOINT_ACCOUNT",
      "type": "string",
      "role": "evidence",
      "expected_values": ["Y", "N", ""]
    },
    {
      "name": "LINKED_BASE",
      "type": "string",
      "role": "evidence",
      "required": false
    },
    {
      "name": "LINKED_BASE_CLASSIFICATION",
      "type": "string",
      "role": "evidence",
      "required": false
    },
    {
      "name": "Mandate",
      "type": "string",
      "role": "evidence",
      "required": false
    },

    {
      "name": "Normalized_Mean",
      "type": "number",
      "role": "ignore",
      "notes": "Not used for eligibility decisions. Must never be treated as an exclusion reason."
    }
  ],
  "normalization_rules": {
    "blank_string_values": ["", " ", null],
    "convert_blanks_to_empty_string_for_text_fields": true,
    "convert_blanks_to_zero_for_numeric_fields": [
      "Arrears_Days",
      "Credit_Card_OD_Days",
      "DPD_Days"
    ]
  }
}
```

---

# ✅ FILE 2 — Interpretation Rules (Detection + Reason Mapping)

### Purpose

This file defines **deterministic extraction logic**:

* which check triggers which `reason_code`
* evidence columns to extract
* special rules like Recency=N
* multi-reason extraction always

### Suggested filename

`reason_detection_rules.json`

```json
{
  "version": "1.0",
  "file_type": "REASON_DETECTION_RULES",
  "description": "Rules for extracting exclusion reasons from a Reasons File row deterministically.",
  "global_extraction_policy": {
    "extract_all_checks_with_value": "Exclude",
    "also_extract_recency_check_when_value": "N",
    "multi_reason_output": true,
    "ignore_fields": ["Normalized_Mean"]
  },
  "reasons": [
    {
      "reason_code": "JOINT_ACCOUNT_EXCLUSION",
      "trigger": {
        "type": "check_equals",
        "check_column": "Joint_Check",
        "trigger_value": "Exclude"
      },
      "evidence_columns": ["Joint_Check", "JOINT_ACCOUNT"],
      "facts_builder": {
        "type": "simple",
        "facts": [
          "Account is a joint account (JOINT_ACCOUNT=Y)."
        ]
      }
    },
    {
      "reason_code": "AVERAGE_BALANCE_EXCLUSION",
      "trigger": {
        "type": "check_equals",
        "check_column": "Average_Bal_check",
        "trigger_value": "Exclude"
      },
      "evidence_columns": ["Average_Bal_check"],
      "facts_builder": {
        "type": "simple",
        "facts": [
          "Customer failed the Average Balance requirement."
        ]
      }
    },
    {
      "reason_code": "DPD_ARREARS_EXCLUSION",
      "trigger": {
        "type": "check_equals",
        "check_column": "DPD_Arrears_Check",
        "trigger_value": "Exclude"
      },
      "evidence_columns": [
        "DPD_Arrears_Check",
        "Arrears_Days",
        "Credit_Card_OD_Days",
        "DPD_Days"
      ],
      "facts_builder": {
        "type": "max_of_numeric_fields",
        "fields": ["Arrears_Days", "Credit_Card_OD_Days", "DPD_Days"],
        "threshold_days": 3,
        "fact_templates": [
          "Customer had DPD/arrears greater than 3 days.",
          "Highest arrears days observed: {max_value} days ({max_field})."
        ]
      }
    },
    {
      "reason_code": "ELMA_EXCLUSION",
      "trigger": {
        "type": "check_equals",
        "check_column": "Elma_check",
        "trigger_value": "Exclude"
      },
      "evidence_columns": ["Elma_check"],
      "facts_builder": {
        "type": "simple",
        "facts": [
          "Customer failed ELMA/mobile banking/one-account eligibility check."
        ]
      }
    },
    {
      "reason_code": "MANDATE_EXCLUSION",
      "trigger": {
        "type": "check_equals",
        "check_column": "Mandates_Check",
        "trigger_value": "Exclude"
      },
      "evidence_columns": ["Mandates_Check", "Mandate"],
      "facts_builder": {
        "type": "simple",
        "facts": [
          "Account mandate/signing authority is not in the allowed sole-signing formats."
        ]
      }
    },
    {
      "reason_code": "CLASSIFICATION_EXCLUSION",
      "trigger": {
        "type": "check_equals",
        "check_column": "Classification_Check",
        "trigger_value": "Exclude"
      },
      "evidence_columns": ["Classification_Check", "CLASSIFICATION"],
      "facts_builder": {
        "type": "simple_with_parameters",
        "parameters": {
          "minimum_required_classification": "A5"
        },
        "fact_templates": [
          "Customer risk classification is below the minimum required level (A5).",
          "Observed classification: {CLASSIFICATION}."
        ]
      }
    },
    {
      "reason_code": "LINKED_BASE_EXCLUSION",
      "trigger": {
        "type": "check_equals",
        "check_column": "Linked_Base_Check",
        "trigger_value": "Exclude"
      },
      "evidence_columns": ["Linked_Base_Check", "LINKED_BASE", "LINKED_BASE_CLASSIFICATION"],
      "facts_builder": {
        "type": "simple",
        "facts": [
          "A linked base has a classification below A5, causing exclusion."
        ]
      }
    },
    {
      "reason_code": "CUSTOMER_VINTAGE_EXCLUSION",
      "trigger": {
        "type": "check_equals",
        "check_column": "customer_vintage_Check",
        "trigger_value": "Exclude"
      },
      "evidence_columns": ["customer_vintage_Check", "customer_vintage_Months"],
      "facts_builder": {
        "type": "simple_with_parameters",
        "parameters": {
          "minimum_months_required": 7
        },
        "fact_templates": [
          "Customer has not banked long enough (minimum required is 7 months).",
          "Observed customer vintage: {customer_vintage_Months} months."
        ]
      }
    },
    {
      "reason_code": "DORMANCY_INACTIVE_EXCLUSION",
      "trigger": {
        "type": "check_equals",
        "check_column": "Active_Inactive_Check",
        "trigger_value": "Exclude"
      },
      "evidence_columns": ["Active_Inactive_Check", "dormancy_status"],
      "facts_builder": {
        "type": "simple",
        "facts": [
          "Account is dormant or inactive due to low activity."
        ]
      }
    },
    {
      "reason_code": "TURNOVER_EXCLUSION",
      "trigger": {
        "type": "check_equals",
        "check_column": "Turnover_Check",
        "trigger_value": "Exclude"
      },
      "evidence_columns": ["Turnover_Check"],
      "facts_builder": {
        "type": "simple",
        "facts": [
          "Customer does not have sufficient banking activity in at least 5 out of 6 months."
        ]
      }
    },
    {
      "reason_code": "RECENCY_EXCLUSION",
      "trigger": {
        "type": "check_special_equals",
        "check_column": "Recency_Check",
        "trigger_value": "N"
      },
      "evidence_columns": ["Recency_Check"],
      "facts_builder": {
        "type": "simple",
        "facts": [
          "Customer has inconsistent recent banking patterns (amounts and/or frequency)."
        ]
      }
    }
  ]
}
```

---

# ✅ FILE 3 — Explanation + Remediation Playbook (Staff-Facing)

### Purpose

Maps each `reason_code` to:

* meaning
* next steps
* owner
* timing
* override constraints

### Suggested filename

`reason_playbook.json`

```json
{
  "version": "1.0",
  "file_type": "REASON_PLAYBOOK",
  "description": "Staff-facing explanations, remediation steps, owners, and timing per reason_code.",
  "reason_playbook": {
    "JOINT_ACCOUNT_EXCLUSION": {
      "meaning": "The account is a joint account, and joint accounts are not eligible for loan limits.",
      "next_steps": [
        { "action": "Use an existing sole account instead (if available).", "owner": "Staff/Customer" },
        { "action": "Open a sole account.", "owner": "Customer" },
        { "action": "Convert account arrangement to sole account (if supported).", "owner": "Branch/RM" }
      ],
      "review_type": "System review",
      "review_timing": "Unknown / not explicitly defined",
      "manual_override_allowed": false,
      "constraints": []
    },

    "AVERAGE_BALANCE_EXCLUSION": {
      "meaning": "Customer failed the Average Balance requirement.",
      "next_steps": [
        { "action": "Remediation steps not provided. Do not assume thresholds or fixes.", "owner": "Unknown" }
      ],
      "review_type": "Unknown",
      "review_timing": "Unknown",
      "manual_override_allowed": false,
      "constraints": ["Do not invent thresholds or remediation."]
    },

    "DPD_ARREARS_EXCLUSION": {
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
    },

    "ELMA_EXCLUSION": {
      "meaning": "Customer failed ELMA eligibility (either not set up on mobile banking NCBA NOW, or another account is already being considered).",
      "next_steps": [
        { "action": "Confirm customer is set up on NCBA NOW mobile banking.", "owner": "Staff" },
        { "action": "Confirm which account is currently being considered for loan limit.", "owner": "Staff" },
        { "action": "If needed, assist customer to change the account being considered.", "owner": "Staff/Customer" }
      ],
      "review_type": "System review",
      "review_timing": "No waiting period required",
      "manual_override_allowed": false,
      "constraints": [
        "Only one account per customer can be considered at a time.",
        "Reasons file does not specify which ELMA sub-cause applies."
      ]
    },

    "MANDATE_EXCLUSION": {
      "meaning": "Account mandate/signing authority does not match the allowed sole-signing mandate formats.",
      "next_steps": [
        { "action": "Update mandate to exactly one of: SOLE SIGNATORY / TO SIGN ALONE / SOLELY.", "owner": "Customer/RM" },
        { "action": "RM to update mandate at branch.", "owner": "RM" }
      ],
      "review_type": "Next-day review",
      "review_timing": "Next day (only if mandates are the reason for exclusion)",
      "manual_override_allowed": false,
      "constraints": [
        "Strict text match required (no fuzzy matching)."
      ]
    },

    "CLASSIFICATION_EXCLUSION": {
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
    },

    "LINKED_BASE_EXCLUSION": {
      "meaning": "A linked base has classification below A5, which blocks eligibility.",
      "next_steps": [
        { "action": "Resolve linked base risk/classification issue via Portfolio Management.", "owner": "Portfolio Management" }
      ],
      "review_type": "Portfolio Management review",
      "review_timing": "Unknown / not explicitly defined",
      "manual_override_allowed": false,
      "constraints": [
        "If LINKED_BASE is blank, treat as Include (no linked base)."
      ]
    },

    "CUSTOMER_VINTAGE_EXCLUSION": {
      "meaning": "Customer has not banked long enough (minimum 7 months required).",
      "next_steps": [
        { "action": "Customer should continue banking until they reach at least 7 months.", "owner": "Customer" }
      ],
      "review_type": "Automatic",
      "review_timing": "Automatic review once customer reaches 7 months",
      "manual_override_allowed": false,
      "constraints": []
    },

    "DORMANCY_INACTIVE_EXCLUSION": {
      "meaning": "Account is dormant/inactive due to low activity.",
      "next_steps": [
        { "action": "Customer must transact to reactivate the account.", "owner": "Customer" }
      ],
      "review_type": "Automatic",
      "review_timing": "Automatic reactivation after sufficient transactions",
      "manual_override_allowed": false,
      "constraints": []
    },

    "TURNOVER_EXCLUSION": {
      "meaning": "Customer does not have sufficient activity/turnover history (needs activity in at least 5 out of 6 months).",
      "next_steps": [
        { "action": "Improve and maintain consistent banking activity, especially credits.", "owner": "Customer" }
      ],
      "review_type": "Monthly system review",
      "review_timing": "Reviewed monthly until sufficient",
      "manual_override_allowed": false,
      "constraints": []
    },

    "RECENCY_EXCLUSION": {
      "meaning": "Customer has inconsistent recent banking patterns (irregular amounts/frequency).",
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
}
```

---

# ✅ What gets passed to the LLM at runtime (summary)

At runtime, your pipeline will:

1. read row from Reasons File
2. apply File 1 normalization
3. apply File 2 extraction → produce `extracted_reasons[]`
4. join File 3 playbook → attach `meaning/next_steps/timing`
5. send a single JSON payload to the LLM to generate staff response

---

