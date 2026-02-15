
---

# ✅ Eligibility Feature Logic (with Eligible + Reasons Files)

## Files used

You now have **4 files total** at runtime:

1. **Eligible Customers List** *(new)*

   * contains accounts that are outright eligible
   * if account exists here → **Eligible**

2. **Reasons File** *(ineligible only)*

   * if account exists here → **Not eligible** + extract reasons

3. **Checks Catalog** *(File 1)*

4. **Reason Detection Rules** *(File 2)*

5. **Reason Playbook** *(File 3)*

> Note: (3–5) are your “Reason Objects framework”.
> (1–2) are your “data lookup files”.

---

# ✅ Intent Detection + Prompting Logic

### What counts as an “eligibility question” (intent trigger)

If the user asks anything like:

* “is customer eligible?”
* “why no limit?”
* “loan limit issue”
* “not getting limit”
* “check eligibility”
* “limit allocation failed”
* “why excluded”

THEN trigger the **Eligibility Flow**.

---

# ✅ Pseudocode (Simple Human Text)

start
  receive user message

  **STEP 1: DETECT INTENT**
  if message is asking about:
    loan limit eligibility OR why customer has no limit
  then
    set intent = "ELIGIBILITY_CHECK"
  else
    handle as normal RAG chat
    stop

  **STEP 2: EXTRACT ACCOUNT NUMBER(S)**
  scan message for 10-digit numbers

  if no valid 10-digit account numbers found
    ask user:
    “Please share the 10-digit account number(s) so I can confirm eligibility.”
    stop

  else
    store them as `account_numbers[]`
    remove duplicates

  **STEP 3: VALIDATE ACCOUNT NUMBERS**
  for each account_number in account_numbers[]
    if account_number is not exactly 10 digits
      mark it as invalid
    if account_number contains non-numeric characters
      mark it as invalid

  if there are invalid account numbers
    return message listing invalid ones
    ask user to resend valid 10-digit account numbers
    stop

  **STEP 4: LOAD KNOWLEDGE FILES**
  load Eligible Customers List
  load Reasons File
  load Checks Catalog (File 1)
  load Reason Detection Rules (File 2)
  load Reason Playbook (File 3)

  **STEP 5: PROCESS EACH ACCOUNT NUMBER (BATCH MODE)**
  initialize results list `eligibility_results = []`

  for each account_number in account_numbers[]

    **STEP 5A: CHECK ELIGIBLE LIST FIRST**
    if account_number exists in Eligible Customers List
      create result:
      - status = "ELIGIBLE"
      - customer_name = from eligible file
      - reasons = empty
      add to eligibility_results
      continue to next account_number

    **STEP 5B: CHECK REASONS FILE (INELIGIBLE FILE)**
    lookup row in Reasons File where account_number matches

    if row is found
      normalize the row using Checks Catalog rules
      extract all reasons using Reason Detection Rules:
        - include all checks where value = Exclude
        - also include Recency_Check = N
        - always list all reasons

      enrich each extracted reason using Reason Playbook
      create result:
      - status = "NOT_ELIGIBLE"
      - customer_name = from reasons file
      - extracted reasons + evidence + next steps
      add to eligibility_results
      continue to next account_number

    **STEP 5C: NOT FOUND IN EITHER FILE**
    if account_number is not in Eligible List AND not in Reasons File
      create result:
      - status = "CANNOT_CONFIRM"
      - message = "Account not found in eligible or reasons files — cannot confirm eligibility from these files alone."
      add to eligibility_results

  **STEP 6: BUILD FINAL JSON PAYLOAD FOR THE LLM**
  create llm_payload containing:
    - intent = eligibility check
    - list of accounts processed
    - per account: status + customer name + reasons + evidence + next steps
    - response layout guide (Summary, Findings, Meaning, Next Steps)
    - instruction: vary wording, avoid repetitive phrasing
    - instruction: lists or paragraphs allowed (LLM chooses best)
    - when-to-recheck is optional

  **STEP 7: SEND TO LLM AND RETURN FINAL STAFF RESPONSE**
  send llm_payload to LLM
  return the final staff-facing explanation
stop

---

# ✅ What the System Passes to the LLM (High-Level)

For each account number, the LLM will receive:

* account_number
* customer_name
* eligibility_status: **Eligible / Not eligible / Cannot confirm**
* if not eligible:

  * extracted reasons (multi-reason)
  * evidence facts (e.g. “DPD days = 102”, “Arrears days = 143”, “Classification = B10”)
  * next steps + owner + timing constraints

And the LLM is instructed to:

* follow the information layout (Summary → Findings → Meaning → Next steps)
* **vary wording** to reduce repetition
* use bullets/paragraphs freely
* optionally include “when to recheck”

---

