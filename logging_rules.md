To implement effective logging for an LLM-based RAG (Retrieval-Augmented Generation) system, you must follow a dual-track strategy: **Traditional System Logging** (for health and errors) and **LLM Observability** (for quality and security).

Below are the rules for the LLM to follow when implementing logs.

### 1. General Formatting Rules

* **JSON Only**: All logs must be output in a structured JSON format to allow for easy parsing by tools like ELK, Datadog, or your RAG evaluation framework.
* **Unique Request IDs**: Every interaction must carry a `request_id` or `trace_id` that links the user input, the retrieval step, and the final LLM generation.
* **ISO 8601 Timestamps**: Use standard UTC timestamps (e.g., `2024-05-15T10:00:00Z`).
* **Standard Severity Levels**: Follow standard levels: `DEBUG` (tokens, raw chunks), `INFO` (user query summary), `WARNING` (empty retrieval), `ERROR` (API timeout), `CRITICAL` (model failure).

### 2. RAG-Specific Logging Rules

For a RAG pipeline, the LLM must log the following metadata for every query:

* **Retrieval Metadata**:
* `top_k`: Number of chunks requested.
* `chunk_ids`: List of specific chunks retrieved from the vector database.
* `similarity_scores`: The distance/relevance score for each chunk.
* `source_documents`: File names or URLs of the retrieved context.


* **Generation Context**:
* `prompt_template_version`: The version of the system prompt used.
* `total_tokens`: Breakdown of `prompt_tokens`, `completion_tokens`, and `total_tokens` for cost tracking.
* `latency`: Measured time for each stage (Retrieval vs. Generation).



### 3. Security & Privacy Rules (Critical)

* **PII Scrubbing**: Before logging raw `input_text` or `output_text`, the system must run a redacting function to remove Personal Identifiable Information (Names, Emails, Phone Numbers).
* **No System Prompts**: Do not log the full system prompt in every entry (to save space and protect IP); instead, log a `prompt_hash` or version ID.
* **Sanitize Inputs**: Log a flag `is_flagged` if the input triggered any content moderation filters (Toxicity, Prompt Injection).

### 4. Quality & Evaluation Rules

To enable "LLM-as-a-Judge" or manual review later, the LLM must facilitate "Evaluation Logs":

* **Groundedness Score**: If possible, log a self-assessment of whether the answer is based strictly on the retrieved chunks.
* **Citation Mapping**: Log which specific chunks were actually cited in the final answer.
* **User Feedback**: Link any user "thumbs up/down" to the specific `request_id` in the log store.

### 5. Implementation Example (Python Logic)

When the LLM writes the logging code, it should look like this:

```python
import logging
import json

class RAGLogger:
    def log_interaction(self, request_id, query, retrieved_chunks, response, usage):
        log_entry = {
            "request_id": request_id,
            "event": "llm_generation_complete",
            "metrics": {
                "latency_ms": usage.get("latency"),
                "tokens": usage.get("tokens")
            },
            "retrieval": {
                "count": len(retrieved_chunks),
                "sources": [c.metadata['source'] for c in retrieved_chunks]
            },
            # Note: In production, scrub 'query' and 'response' for PII first
            "data": {
                "query_summary": query[:100], 
                "grounded": True # Example flag
            }
        }
        logging.info(json.dumps(log_entry))

```

### Summary Checklist for Implementation:

1. **Does the log contain a Trace ID?** (Required for debugging)
2. **Is the cost (tokens) recorded?** (Required for budget)
3. **Are the retrieval sources cited?** (Required for RAG accuracy)
4. **Is sensitive data redacted?** (Required for compliance)


### **Technical Requirements Specification: Session-Based Trace Logging**

This specification outlines the logic for an automated, high-granularity logging system designed to provide a "black-box" recording of every technical event within your RAG application.

---

### **1. Storage Architecture**

* **Directory Structure**: All logs must be stored in a dedicated `/logs` directory at the project root.
* **File Naming**: Files must be named using a sortable timestamp: `session_YYYYMMDD_HHMMSS.log`.
* **Persistence**: Logs must be written in "Append" mode with **immediate flushing** (unbuffered). This ensures that if the process crashes at line 150, line 149 is already physically saved to the disk.

---

### **2. Session Lifecycle Management**

The system must manage log rotation based on two competing triggers:

* **Trigger A: The 15-Minute Idle Rule**
* The system monitors the time elapsed since the *last* log entry.
* If `current_time - last_entry_time > 15 minutes`, the current file handle is closed.
* Upon the next activity, a brand new file is created with a new timestamp.


* **Trigger B: The 1-Hour Hard Limit**
* The system monitors the time elapsed since the *creation* of the current log file.
* If `current_time - file_creation_time > 60 minutes`, the file is rotated immediately, even if the user is currently active.


* **Session Metadata**: The first line of every new file must contain a "Session Header" including the System Version, Environment (Dev/Prod), and Start Time.

---

### **3. Technical Granularity & Traceability**

To meet the requirement of tracing exactly where a process completes or fails, every log entry must capture the following "No-Summarization" data points:

#### **A. Caller Context (The "Where")**

Every log line must automatically extract and prepend:

* **Absolute File Path**: The script where the call originated.
* **Function Name**: The specific function being executed.
* **Line Number**: The exact line of code currently being processed.

#### **B. Data Flow (The "What")**

* **Function Entry**: Log the exact input arguments (`args` and `kwargs`).
* **Function Exit**: Log the raw return value or object.
* **API Interactions**: For external calls (OpenAI, Vector DB, etc.), log the raw Request Body and the raw Response Headers/Body. Do not truncate long strings; keep the full technical payload.

#### **C. Execution State**

* **Timestamps**: High-precision timestamps (including milliseconds).
* **Thread/Process ID**: Essential for tracing if you are using asynchronous calls or multi-threading, to ensure logs from different tasks don't get mixed up.

---

### **4. Error & Termination Handling**

* **Implicit Termination**: If a process stops, the last log entry will be the "Function Entry" or a specific "Step" log. The absence of an "Exit" log for that same function name/line is the technical indicator of the crash point.
* **Explicit Exceptions**: Upon a code crash, the logger must intercept the signal and write the **Full Traceback**. It must capture every frame leading up to the failure to identify the exact state of variables at the moment of termination.

---

### **5. Implementation Logic (Rules for the Code)**

1. **Centralized Logger**: Create a singleton "SessionManager" class that holds the state of the current file handle.
2. **Wrappers/Interceptors**: Use a "Technical Trace" decorator on all major functions. This decorator handles the "Before" (Input/Line #) and "After" (Output/Duration) logic automatically.
3. **Low-Level Hooking**: Use the language's standard `logging` library but override the `emit` method to check the Session Lifecycle rules before every single write operation.

---

### **Summary of Success Criteria**

If correctly implemented, you should be able to open a log file and see:

1. **[10:00:01] [main.py:45] CALL**: `ingest_document(file="data.pdf")`
2. **[10:00:05] [retriever.py:112] API_REQ**: `POST https://api.openai.com/v1/embeddings {input: "..."}`
3. **[10:00:06] [retriever.py:112] API_RES**: `200 OK {data: [...]}`
4. **[10:21:00] [SessionManager]**: `Idle timeout reached. Session Terminated.`
