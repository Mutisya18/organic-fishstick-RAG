---

# 🎯 **Specification: Structured Data Layer (MVP)**

**Feature:** Add structured data layer to existing RAG system
**Team:** 2 developers + AI coding assistance
**Scope:** Minimal viable structured knowledge integration

---

## 📌 **Goal**

Enable your RAG system to:

* Store structured knowledge about organizational entities.
* Retrieve structured facts deterministically.
* Combine structured lookup with semantic search for hybrid answers.
* Support follow-up queries using structured context.

**Not in MVP:**

* Dynamic schema creation
* Department-specific custom modules
* UI for structured data entry
* Automated extraction/parsing

---

## 🧠 **Core Concepts**

### 1️⃣ Structured Entities (MVP)

The structured layer will hold **normalized facts** in a database.

MVP will have 5 core entity types:

| Entity           | Purpose                                |
| ---------------- | -------------------------------------- |
| **Departments**  | High-level department info             |
| **Services**     | What the org offers                    |
| **Roles/People** | Who does what                          |
| **Workflows**    | Step-by-step processes                 |
| **Connections**  | How entities relate (cross-department) |

Entities have fixed attributes (see next section).

---

## 📋 **Entity Definitions (Logic Only)**

### 🟡 **Department**

**Definition:** Basic organizational unit.

**Fields (MVP):**

* `id` – unique identifier
* `name` – human name
* `description` – overview
* `contacts` – list of contacts (roles)
* `metadata` – version, last_updated

**Use Cases:**

* Lookup department by name
* Provide department context in answers

---

### 🟡 **Service**

**Definition:** A deliverable or offering (processes or outputs).

**Fields (MVP):**

* `id`
* `name`
* `description`
* `department_id`
* `related_workflows` – list of workflow IDs
* `metadata`

**Use Cases:**

* Answer “Describe this service”
* Link to related workflows

---

### 🟡 **Role / Person**

**Definition:** A role or specific individual.

**Fields (MVP):**

* `id`
* `role_title`
* `name` (optional)
* `department_id`
* `contact_email` (optional)
* `contact_phone` (optional)
* `responsibilities`
* `approval_authority` (string list)
* `metadata`

**Use Cases:**

* “Who approves X?”
* “What does person Y do?”

---

### 🟡 **Workflow**

**Definition:** Step-by-step process.

**Fields (MVP):**

* `id`
* `name`
* `description`
* `department_id`
* `steps` – ordered list of step objects

  * each step: { sequence_no, description, role_ids }
* `metadata`

**Use Cases:**

* “Explain how X happens”

---

### 🟡 **Connection**

**Definition:** Cross-entity relationships.

**Fields (MVP):**

* `id`
* `source_entity_type`
* `source_entity_id`
* `target_entity_type`
* `target_entity_id`
* `relationship_type`
* `metadata`

**Use Cases:**

* “What depends on this service?”
* “Which department handles after X?”

---

## 📦 **Database Requirements (Logic)**

* Store structured entities persistently.
* Support filtering by entity type & attributes.
* Expose entity query interface (SQL or ORM).

**MVP Constraints:**

* No complex schema evolution
* Entities stored in dedicated tables
* No separate module registry

---

## 🔍 **Retrieval Pipeline Logic**

### 🧠 **Query Handling Flow**

For every user query:

#### A) **Intent Classification (MVP rules)**

Basic classification to decide retrieval strategy:

| Pattern                                         | Route                 |
| ----------------------------------------------- | --------------------- |
| Contains “who”, “contact”, “email”, “phone”     | Structured            |
| Contains “how to”, “steps”, “process”           | Structured + Semantic |
| Contains “describe”, “what is”, “tell me about” | Semantic + Structured |
| Contains keyword matching an entity name        | Structured Preference |

Use simple rules/RAG query classifier.

> **Policy:** Always try structured data first; fallback to semantic.

---

### B) **Structured Lookup Logic**

If intent indicates structured lookup:

1. Map query to entity type:

   * e.g., identify “roles” → role table
   * identify “workflow” → workflow table

2. Execute structured query:

   * direct SQL/ORM filter
   * e.g., `SELECT * FROM roles WHERE role_title ILIKE '%approve%'`

3. Package results:

   * Flatten structured data into LLM prompt context

4. Pass structured context to LLM.

---

### C) **Hybrid Retrieval (Structured + Semantic)**

If query needs both:

1. **Structured Step**

   * Retrieve structured facts
   * e.g., service description, related workflows

2. **Semantic Step**

   * Use RAG to fetch narrative blocks from vector store
   * Filter by metadata (e.g., entity_type, department)

3. **Prompt Builder**

   * Structured facts as top context
   * Then semantic text
   * Then user query

4. **LLM Response**

   * LLM uses both to generate answer

---

### D) **Conversation Memory**

Track per session:

* Entities referenced
* Entity IDs and names
* Last answer context

Use memory in next query as additional filter:

* E.g., if prior context was about service X, filter subsequent retrieval by that service.

---

## 🧠 **Prompt Engineering Guidelines (MVP)**

When inserting structured output into prompts:

```
Structured Facts:
- Department: {name}
- Description: {desc}
- Service: {service name}
- Workflow: Step list
- Roles involved
Then:
Relevant narratives from semantic search
Then:
User Question
```

**Purpose:** Improve relevance and reduce hallucinations.

---

## 📌 **Metadata & Tagging (MVP)**

When storing text chunks in vector store, include:

* `entity_type`: department/service/role/workflow
* `entity_id`
* `department_id`
* `source` (structured or narrative)

This enables filtered retrieval.

---

## 🧪 **Testing Requirements (MVP)**

Provide test cases for:

### A) Structured Only

* “Who approves…”
* “What is the contact email for…”
* “Give me the steps to…”

### B) Semantic Only

* “Explain what X is”
* “Tell me about the org’s policy on Y”

### C) Hybrid

* “How do I request service X and who approves?”
* “Tell me about workflow Y and contact person for step 2”

---

## 📈 **Acceptance Criteria**

### ✅ Structured Lookup

Given input that matches an entity:

* System returns structured data
* No hallucinated facts
* Matches expected table fields

---

### ✅ Hybrid Answer

Given structured + narrative context:

* LLM answer must include facts from structured data
* Semantic text augments but doesn’t contradict

---

### ✅ Contextual Follow-ups

If conversation continues:

* System filters by session memory
* Avoids irrelevant entity retrieval

---

## 🧠 **Developer Tasks (Feature Implementation)**

### Task Group 1 — Schema Implementation

* Create 5 entity tables
* Define fields and constraints
* Create indexes for efficient lookup

**Deliverables:**

* Schema DDL
* Validations

---

### Task Group 2 — Structured Data API

Implement service functions to:

* Query entities by ID/name
* Search with filters (department, entity_type)
* Join entities (e.g., service → workflows)

**Deliverables:**

* Search functions
* Entity serializers

---

### Task Group 3 — Retrieval Logic

* Intent classifier (rules only)
* Structured lookup executor
* Hybrid orchestrator

**Deliverables:**

* Query pipeline functions

---

### Task Group 4 — Prompt Integration

* Structured context builder
* Prompt templates
* Hybrid prompt assembly

**Deliverables:**

* Prompt templates
* Context formatter

---

### Task Group 5 — Memory Handling

* Session tracking module
* Entity reference memory
* Context reuse logic

**Deliverables:**

* Memory store
* Session usage integration

---

### Task Group 6 — Testing

Write automated tests:

* Structured retrieval
* Hybrid retrieval
* Follow-up context tests

**Deliverables:**

* Test suites
* Test data fixtures

---

## 🛠 **Non-MVP (Out of Scope)**

❌ Auto schema discovery
❌ Department-defined custom modules
❌ UI or admin tool for data entry
❌ Real-time synchronization with external systems
❌ Schema versioning or migrations
❌ Role-based access control

---

## 📦 **MVP Data Entry Approach**

Since no UI is in MVP:

* Use spreadsheets (5 sheets mapping to tables)
* Provide import script to load CSV to DB
* Validate required fields
* Reject invalid entities with error log

---

## 🗣 **Future Enhancements (Beyond MVP)**

Not in this spec but possible later:

* Custom modules per department
* UI for data entry
* Automated extraction/parsing
* Analytics dashboards
* Auto intent classification feedback loop

---

# 🚀 **Summary**

This spec defines the **logic and pipeline** for adding a structured data layer to your RAG system MVP, covering:

✔ Entity definitions
✔ Retrieval logic
✔ Hybrid orchestration
✔ Prompt integration
✔ Testing criteria
✔ Developer tasks

It’s **department-agnostic** and ready to hand to developers without referring to specific content.

---

