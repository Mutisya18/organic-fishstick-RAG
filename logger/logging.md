# RAG Logging System Documentation

## Overview

This document describes the comprehensive logging system implemented for the RAG (Retrieval-Augmented Generation) pipeline. The system provides structured JSON logging with session management, PII scrubbing, technical tracing, and RAG-specific observability.

## Architecture

### Core Components

#### 1. **SessionManager** (`logger/session_manager.py`)
Singleton logger managing session-based log files with automatic rotation.

**Features:**
- **Timestamp-based filenames**: `session_YYYYMMDD_HHMMSS.log`
- **Automatic rotation triggers**:
  - Idle timeout: 15 minutes (configurable via `IDLE_TIMEOUT_SECONDS`)
  - Age limit: 60 minutes (configurable via `MAX_AGE_SECONDS`)
- **Session headers**: Every new file starts with session metadata (version, environment, timestamp)
- **Immediate flushing**: Line-buffered writes ensure crash-safety
- **Thread-safe**: Uses singleton pattern with locks

**Configuration:**
```python
LOG_DIR = os.getenv("LOG_DIR", "/workspaces/rag-tutorial-v2/logs")
IDLE_TIMEOUT_SECONDS = int(os.getenv("IDLE_TIMEOUT_SECONDS", "900"))  # 15 min
MAX_AGE_SECONDS = int(os.getenv("MAX_AGE_SECONDS", "3600"))  # 60 min
ENV = os.getenv("ENV", "dev")
```

**Usage:**
```python
from logger.session_manager import SessionManager

sm = SessionManager()
sm.log({"event": "test", "data": "value"}, severity="INFO")
```

#### 2. **PII Scrubbing** (`logger/pii.py`)
Detects and redacts Personal Identifiable Information before logging.

**Patterns detected:**
- Email addresses
- Phone numbers (US format and variations)
- Social Security Numbers (SSN)
- Credit card numbers
- Names (optional, configurable)

**Functions:**
- `scrub_text(text: str) -> (scrubbed_text, is_flagged)`: Scrub individual strings
- `scrub_dict(data: dict, keys_to_scrub=None) -> (scrubbed_dict, is_flagged)`: Scrub dictionary values

**Example:**
```python
from logger.pii import scrub_text

text = "Contact john@example.com or call 555-123-4567"
scrubbed, flagged = scrub_text(text)
# scrubbed: "Contact [EMAIL_REDACTED] or call [PHONE_REDACTED]"
# flagged: True
```

#### 3. **Technical Trace Decorator** (`logger/trace.py`)
Wraps functions to log entry, exit, exceptions with full technical context.

**Logged metadata:**
- Caller context: file path, function name, line number
- Execution state: thread ID, process ID, timestamps (millisecond precision)
- Data flow: input arguments, return value/type
- Duration: execution time in milliseconds
- Errors: full traceback on exception

**Usage:**
```python
from logger.trace import technical_trace

@technical_trace
def process_data(x, y):
    return x + y

result = process_data(2, 3)  # Automatically logged
```

#### 4. **RAG Logger** (`logger/rag_logging.py`)
High-level logging utilities for RAG pipeline events.

**Key methods:**
- `generate_request_id()`: Create unique trace IDs
- `hash_prompt(prompt)`: Hash system prompts for IP protection
- `log_retrieval()`: Log vector DB retrieval with chunks, scores, sources
- `log_generation()`: Log LLM generation with tokens, latency, groundedness
- `log_end_to_end_rag()`: Log complete E2E interaction
- `log_api_request()`: Log external API calls (OpenAI, Pinecone, etc.)
- `log_api_response()`: Log API responses
- `log_warning()`: Log warnings (empty retrieval, low confidence)
- `log_error()`: Log errors with traceback

**Example:**
```python
from logger.rag_logging import RAGLogger

logger = RAGLogger()
request_id = logger.generate_request_id()

# Log retrieval
logger.log_retrieval(
    request_id=request_id,
    query="What is AI?",
    top_k=5,
    chunks=[...],
    similarity_scores=[0.95, 0.87, ...],
    source_documents=["doc1.pdf", "doc2.pdf"],
    latency_ms=150.5,
)

# Log generation
logger.log_generation(
    request_id=request_id,
    query="What is AI?",
    response="AI is artificial intelligence...",
    prompt_template_version="1.0.0",
    prompt_tokens=50,
    completion_tokens=25,
    latency_ms=200.3,
    groundedness_score=0.92,
    cited_chunks=["chunk_1", "chunk_2"],
)
```

## Log Format

All logs are structured JSON with the following common fields:

```json
{
  "timestamp": "2026-01-18T10:00:00.123Z",
  "severity": "INFO",
  "session_id": "uuid-123456...",
  "event": "retrieval_complete",
  "request_id": "uuid-789012...",
  "data": {...event-specific data...}
}
```

### Severity Levels

- **DEBUG**: Fine-grained technical details (function entry/exit, API requests)
- **INFO**: Business-level events (retrieval complete, generation complete, E2E interaction)
- **WARNING**: Unexpected but recoverable conditions (empty retrieval, idle timeout)
- **ERROR**: Errors that require attention (API timeout, model failure)
- **CRITICAL**: System-level failures (not currently used in implementation)

### Event Types

#### Retrieval Complete (`retrieval_complete`)
```json
{
  "event": "retrieval_complete",
  "request_id": "...",
  "retrieval_metadata": {
    "top_k": 5,
    "retrieved_count": 5,
    "chunk_ids": ["chunk_1", "chunk_2", ...],
    "similarity_scores": [0.95, 0.87, ...],
    "source_documents": ["doc1.pdf", "doc2.pdf", ...]
  },
  "query_metadata": {
    "query_summary": "What is AI?",
    "query_pii_flagged": false
  },
  "latency_ms": 150.5
}
```

#### Generation Complete (`generation_complete`)
```json
{
  "event": "generation_complete",
  "request_id": "...",
  "generation_metadata": {
    "prompt_hash": "a1b2c3d4e5f6g7h8",
    "prompt_template_version": "1.0.0",
    "tokens": {
      "prompt_tokens": 50,
      "completion_tokens": 25,
      "total_tokens": 75
    }
  },
  "quality_metrics": {
    "groundedness_score": 0.92,
    "cited_chunks": ["chunk_1", "chunk_2"]
  },
  "query_metadata": {
    "query_summary": "What is AI?",
    "query_pii_flagged": false
  },
  "response_metadata": {
    "response_summary": "AI is artificial intelligence...",
    "response_pii_flagged": false
  },
  "latency_ms": 200.3
}
```

#### RAG Interaction Complete (`rag_interaction_complete`)
End-to-end interaction linking retrieval and generation.

#### Function Call/Return/Exception (`function_call`, `function_return`, `function_exception`)
Technical trace events with full caller context.

#### API Request/Response (`api_request`, `api_response`)
External API interactions with payloads.

## Integration

The logging system is integrated into the main pipeline files:

### `query_data.py`
- `query_rag()`: Decorated with `@technical_trace` and logs:
  - Retrieval metadata (top_k, chunks, similarity scores, sources)
  - Generation metadata (tokens, latency)
  - E2E interaction with request_id linking

### `populate_database.py`
- `load_documents()`: Logs document loading
- `split_documents()`: Logs chunking
- `add_to_chroma()`: Logs document addition to vector DB

## Directory Structure

```
/workspaces/rag-tutorial-v2/
├── logger/
│   ├── __init__.py
│   ├── session_manager.py      # Session-based file rotation
│   ├── pii.py                  # PII scrubbing utilities
│   ├── trace.py                # Technical trace decorator
│   └── rag_logging.py           # RAG-specific logging
├── logs/                        # Log files (created at runtime)
│   ├── session_20260118_100000.log
│   ├── session_20260118_110000.log
│   └── ...
└── tests/
    ├── __init__.py
    └── test_logging.py          # Comprehensive test suite
```

## Usage Examples

### Basic Setup
```python
from logger.rag_logging import RAGLogger
from logger.trace import technical_trace

rag_logger = RAGLogger()

@technical_trace
def my_function():
    request_id = rag_logger.generate_request_id()
    # ... do work ...
    rag_logger.log_warning(request_id, "Something interesting happened")
```

### Query with Full Logging
```python
from logger.rag_logging import RAGLogger
import time

logger = RAGLogger()

def query_with_logging(query_text):
    request_id = logger.generate_request_id()
    start = time.time()
    
    # Retrieval
    chunks = retrieve_chunks(query_text)
    retrieval_latency = (time.time() - start) * 1000
    
    logger.log_retrieval(
        request_id=request_id,
        query=query_text,
        top_k=5,
        chunks=chunks,
        similarity_scores=[c["score"] for c in chunks],
        source_documents=[c["source"] for c in chunks],
        latency_ms=retrieval_latency,
    )
    
    # Generation
    gen_start = time.time()
    response = generate_response(query_text, chunks)
    gen_latency = (time.time() - gen_start) * 1000
    
    logger.log_generation(
        request_id=request_id,
        query=query_text,
        response=response,
        prompt_template_version="1.0.0",
        prompt_tokens=100,
        completion_tokens=50,
        latency_ms=gen_latency,
    )
    
    return response
```

## Testing

Run the test suite:
```bash
cd /workspaces/rag-tutorial-v2
python -m pytest tests/test_logging.py -v
```

Tests cover:
- PII scrubbing (emails, phones, SSNs, credit cards)
- Session management (file creation, rotation, JSON parsing)
- Technical trace decorator (entry, exit, exceptions)
- RAG logger methods (retrieval, generation, E2E)
- Integration with pipeline

All tests pass ✅

## Best Practices

### 1. Always Use Request IDs
Link retrieval and generation logs with the same `request_id`:
```python
request_id = logger.generate_request_id()
logger.log_retrieval(..., request_id=request_id, ...)
logger.log_generation(..., request_id=request_id, ...)
```

### 2. Measure Latency
Capture timing for each stage:
```python
import time
start = time.time()
# ... work ...
latency_ms = (time.time() - start) * 1000
logger.log_retrieval(..., latency_ms=latency_ms)
```

### 3. Include Quality Metrics
Log groundedness, citations, and user feedback:
```python
logger.log_generation(
    ...,
    groundedness_score=0.92,
    cited_chunks=["chunk_1", "chunk_2"],
)
```

### 4. Decorate Major Functions
Use `@technical_trace` on pipeline functions for automatic entry/exit logging:
```python
@technical_trace
def retrieve_chunks(query):
    ...
```

### 5. Handle Errors Gracefully
Always log errors before re-raising:
```python
try:
    # ... work ...
except Exception as e:
    logger.log_error(request_id, type(e).__name__, str(e))
    raise
```

## Viewing Logs

### Real-time Monitoring
```bash
tail -f /workspaces/rag-tutorial-v2/logs/session_*.log
```

### Parse JSON Logs
```bash
cat /workspaces/rag-tutorial-v2/logs/session_*.log | jq '.event'
```

### Filter by Request ID
```bash
cat /workspaces/rag-tutorial-v2/logs/session_*.log | jq 'select(.request_id == "uuid-123")'
```

### Filter by Severity
```bash
cat /workspaces/rag-tutorial-v2/logs/session_*.log | jq 'select(.severity == "ERROR")'
```

## Future Enhancements

1. **Distributed Tracing**: Integrate with OpenTelemetry for cross-service tracing
2. **Log Aggregation**: Automatically ship logs to ELK, Datadog, or CloudWatch
3. **Sampling**: Reduce overhead by sampling non-critical events
4. **Custom Formatters**: Support additional output formats (CSV, Parquet)
5. **Async Logging**: Non-blocking writes for high-throughput scenarios
6. **Log Retention**: Automatic cleanup of old logs based on age/size

## Compliance & Security

✅ **PII Protection**: All personal data (emails, phones, SSNs) redacted before logging
✅ **IP Protection**: System prompts logged as hashes, not full text
✅ **Audit Trail**: Complete trace of all interactions with full caller context
✅ **Privacy**: PII flags indicate when sensitive data was present
✅ **Crash Recovery**: Line-buffered writes ensure data persistence on failure

## Support

For issues or questions:
1. Check the test suite in `tests/test_logging.py`
2. Review log files in `/workspaces/rag-tutorial-v2/logs/`
3. Enable DEBUG logging for detailed traces
