start
  receive user query
  extract **account_number** from user input

  **STEP 1: LOOKUP ROW IN REASONS FILE**
  search Reasons File for row where `account_number = user.account_number`

  if **no row found**
    return message to user:
    “Account not found in Reasons File — cannot confirm eligibility from this file alone.”
    stop

  else (row found)
    store row as `customer_row`

  **STEP 2: LOAD KNOWLEDGE FILES**
  load File 1: **Checks Catalog** (columns + expected values + normalization rules)
  load File 2: **Reason Detection Rules** (how to extract reasons)
  load File 3: **Reason Playbook** (meaning + next steps + timing + constraints)

  **STEP 3: NORMALIZE DATA (USING FILE 1)**
  for each numeric arrears field in:
    `Arrears_Days, Credit_Card_OD_Days, DPD_Days`
    if value is blank/null
      set value = 0

  for each text field
    if value is blank/null
      set value = ""

  **STEP 4: EXTRACT EXCLUSION REASONS (USING FILE 2)**
  initialize empty list `extracted_reasons = []`

  for each rule in File 2 (Reason Detection Rules)
    check the trigger condition

    if trigger condition is TRUE
      create a `reason_object`
      set `reason_code` from the rule
      capture `triggered_by` (column + value)
      extract all `evidence_columns` required by that rule from the row
      build `facts_for_explanation` using the rule’s facts logic
      add `reason_object` to `extracted_reasons`

  **SPECIAL GLOBAL EXTRACTION RULES (MUST ALWAYS APPLY)**
  if any check column has value = `Exclude`
    it must appear as a reason in `extracted_reasons`

  if `Recency_Check = N`
    add reason `RECENCY_EXCLUSION` even if all other checks are Include

  always keep all reasons (do not deduplicate)

  **STEP 5: ENRICH REASONS WITH PLAYBOOK (USING FILE 3)**
  for each reason in `extracted_reasons`
    find matching playbook entry in File 3 using `reason_code`
    attach:
      meaning
      next steps
      owner
      review timing
      manual override allowed
      constraints

  **STEP 6: BUILD FINAL JSON PAYLOAD FOR THE LLM**
  create `llm_payload` containing:
    request details (account_number, query_text)
    customer details (name + account_number)
    system rules (extract Exclude + Recency=N, ignore Normalized_Mean)
    row snapshot (checks + evidence)
    extracted reasons (with evidence + facts + playbook)
    required response format sections:
      Summary
      Reasons found
      What it means
      Next steps (owner + timing)
      When to recheck

  **STEP 7: CALL THE LLM**
  send `llm_payload` to the LLM

  **STEP 8: RETURN FINAL RESPONSE TO USER**
  return only the LLM-generated staff-facing explanation
  (do not expose JSON, reason codes, or internal system logic)

stop
