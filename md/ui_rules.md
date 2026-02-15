✅ **UI v1.1 is now FROZEN**

Below is the **final, authoritative UI v1.1 specification**, explicitly covering **UI handling, multiple reasons, and evidence**.
This is the version you can now safely hand to your coding agent and treat as **non-negotiable** unless you intentionally bump to v1.2.

---

# 🔒 Eligibility Response UI — **v1.1 (FROZEN)**

**Status:** Locked
**Scope:** User-facing eligibility output formatting
**Applies to:** All eligibility responses rendered in the UI (single or batch)

---

## 1. Core Intent

UI v1.1 defines **how eligibility results MUST be presented to users**, focusing on:

* Fast human scan-ability
* Clear reason visibility
* Evidence shown upfront (not hidden)
* Explicit next steps per reason
* Safe scaling to multiple reasons and multiple accounts

---

## 2. High-Level Rules (Non-Negotiable)

* ❌ No tables
* ❌ No raw reason codes
* ❌ No hiding evidence in expanders only
* ❌ No reordering of reasons
* ❌ No invented evidence or thresholds
* ✅ Line-based layout only
* ✅ Numbered reasons
* ✅ Inline evidence next to reason titles
* ✅ One “Next Steps” block per reason

---

## 3. Account Block Structure (Mandatory)

Each account MUST be rendered as a **self-contained block**.

### 3.1 Header (Exact Order)

```
Customer Name: <Name | "Unknown">
Account Number: <Account Number>
Status: <Eligible | Not Eligible | Cannot Confirm>
```

Rules:

* Account Number is mandatory
* No emojis
* No horizontal rules before the header

---

## 4. Reasons Section (Mandatory)

### 4.1 Section Header

```
Reasons
---
```

Rules:

* The word `Reasons` must be literal
* Horizontal rule must be exactly `---`
* No blank line between `Reasons` and `---`

---

## 5. Multiple Reasons Handling (Core of v1.1)

Reasons MUST be rendered in **the exact order received**.

### 5.1 Reason Title Line (With Inline Evidence)

```
<N>. <Friendly Reason Title> (<Inline Evidence>)
```

Rules:

* Numbering starts at `1`
* Friendly titles only (no internal codes)
* Inline evidence is REQUIRED if evidence exists
* Evidence must be concise and scannable

Examples:

* `1. Customer Classification (B9)`
* `2. DPD Arrears (200 days – Loan)`
* `3. Customer Vintage (4 months)`
* `4. Linked Base Classification (Base 300812 – B12)`

If no evidence exists, omit the brackets entirely.

---

### 5.2 Reason Meaning (Mandatory)

Immediately below the title line:

```
<Clear explanation of why this reason blocks eligibility>
```

Rules:

* Declarative and factual
* Explains *why*, not *how to fix*
* May reference minimum policy thresholds if known

Example:

```
The customer has a risk classification below the minimum eligibility requirement of A5.
```

---

## 6. Evidence Rules (Strict)

### 6.1 Inline Evidence (Primary)

* Appears in brackets on the reason title line
* Derived from `evidence_display` or equivalent
* Short and scannable

### 6.2 Extended Evidence (Optional)

If more detail is useful, it may appear **below the meaning**, as plain sentences.

Rules:

* Must not contradict inline evidence
* Must not introduce new thresholds
* Must not be verbose

---

## 7. Next Steps (Mandatory per Reason)

Each reason MUST include its own Next Steps block:

```
Next Steps
- <Action 1>
- <Action 2>
```

Rules:

* Always present
* Order preserved
* Ownership may be embedded naturally
* System-enforced constraints must be stated

---

## 8. Reason Separation (Strict)

After each reason’s Next Steps:

```
---
```

Rules:

* No extra blank lines before or after
* Final reason MAY omit the trailing rule (optional)

---

## 9. Batch / Multiple Accounts Handling

When rendering multiple accounts:

* Repeat the **entire structure** per account
* Separate accounts using a strong divider:

```
==================== NEXT ACCOUNT ====================
```

* Do not merge or interleave reasons across accounts

---

## 10. Golden Test Fixture (Authoritative)

### Scenario

* One account
* One reason: Customer Classification
* Evidence: Classification = B9
* Minimum required = A5

### Expected Output (Must Match Structurally)

```
Customer Name: Stanley Mutisya
Account Number: 4019982736
Status: Not Eligible

Reasons
---
1. Customer Classification (B9)
The customer has a risk classification below the minimum eligibility requirement of A5.

Next Steps
- Relationship Manager to engage Portfolio Management for classification review
- Eligibility will be reassessed once the classification is upgraded
---
```

---

## 11. Acceptance Checklist (For Coding Agent)

A UI renderer is **v1.1 compliant** if:

* [ ] Uses no tables
* [ ] Numbers reasons correctly
* [ ] Displays evidence inline next to reason titles
* [ ] Shows one Next Steps block per reason
* [ ] Preserves reason order
* [ ] Matches the golden fixture layout

---

## 12. Version Governance

* **UI v1.1 is frozen**
* Any changes require:

  * Explicit version bump (v1.2)
  * Updated golden fixture
  * Clear change log

---