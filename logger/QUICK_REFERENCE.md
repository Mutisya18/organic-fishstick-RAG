# RAG Logging Quick Reference

## Quick Start

### 1. Initialize logger
```python
from logger.rag_logging import RAGLogger
logger = RAGLogger()
```

### 2. Generate request ID for tracing
```python
request_id = logger.generate_request_id()
```

### 3. Log retrieval
```python
logger.log_retrieval(
    request_id=request_id,
    query="What is AI?",
    top_k=5,
    chunks=[...],
    similarity_scores=[0.95, 0.87, ...],
    source_documents=["doc1.pdf", "doc2.pdf"],
    latency_ms=150.0,
)
```

### 4. Log generation
```python
logger.log_generation(
    request_id=request_id,
    query="What is AI?",
    response="AI is artificial intelligence.",
    prompt_template_version="1.0.0",
    prompt_tokens=50,
    completion_tokens=25,
    latency_ms=200.0,
    groundedness_score=0.92,
    cited_chunks=["chunk_1", "chunk_2"],
)
```

### 5. Decorate functions for automatic tracing
```python
from logger.trace import technical_trace

@technical_trace
def my_function(x, y):
    return x + y
```

## Log File Locations

All logs are stored in: `/workspaces/rag-tutorial-v2/logs/`

Format: `session_YYYYMMDD_HHMMSS.log`

Example: `session_20260118_100000.log`

## Viewing Logs

### Real-time tail
```bash
tail -f /workspaces/rag-tutorial-v2/logs/session_*.log
```

### Pretty-print JSON
```bash
cat /workspaces/rag-tutorial-v2/logs/session_*.log | jq
```

### Filter by event type
```bash
cat /workspaces/rag-tutorial-v2/logs/session_*.log | jq '.event'
```

### Filter by request ID
```bash
cat /workspaces/rag-tutorial-v2/logs/session_*.log | jq 'select(.request_id == "uuid-here")'
```

### Count events
```bash
cat /workspaces/rag-tutorial-v2/logs/session_*.log | jq '.event' | sort | uniq -c
```

## Common Log Events

| Event | Purpose |
|-------|---------|
| `session_start` | New session created |
| `retrieval_complete` | Vector DB query completed |
| `generation_complete` | LLM response generated |
| `rag_interaction_complete` | Full E2E interaction logged |
| `function_call` | Function entry |
| `function_return` | Function exit |
| `function_exception` | Function error |
| `api_request` | External API called |
| `api_response` | External API responded |
| `warning` | Non-critical issue |
| `error` | Error occurred |

## Key Features

✅ **Automatic PII Redaction**: Emails, phones, SSNs redacted
✅ **Unique Request IDs**: Link retrieval → generation → response
✅ **JSON Structured Logs**: Easy parsing by tools (ELK, Datadog, etc.)
✅ **Caller Context**: File, function, line number automatically included
✅ **Performance Metrics**: Latency, token counts, thread/process IDs
✅ **Session Management**: Automatic rotation (15min idle or 60min age)
✅ **Crash-Safe**: Line-buffered immediate flushing
✅ **Technical Tracing**: Full function entry/exit/exception logging

## API Reference

### RAGLogger Methods

```python
# Generate unique request ID
request_id = logger.generate_request_id()

# Hash system prompt (IP protection)
hash_val = logger.hash_prompt("system prompt")

# Log retrieval phase
logger.log_retrieval(request_id, query, top_k, chunks, 
                     similarity_scores, source_documents, latency_ms)

# Log generation phase
logger.log_generation(request_id, query, response, 
                      prompt_template_version, prompt_tokens, 
                      completion_tokens, latency_ms, 
                      groundedness_score, cited_chunks)

# Log complete E2E interaction
logger.log_end_to_end_rag(request_id, query, response,
                          retrieval_metadata, generation_metadata,
                          total_latency_ms, quality_metrics)

# Log external API calls
logger.log_api_request(request_id, api_name, endpoint, method,
                       request_body, latency_ms)

# Log API responses
logger.log_api_response(request_id, api_name, status_code,
                        response_headers, response_body, latency_ms)

# Log warnings (empty retrieval, low confidence)
logger.log_warning(request_id, message, event_type)

# Log errors
logger.log_error(request_id, error_type, error_message, traceback_str)
```

### SessionManager Methods

```python
# Get singleton instance
sm = SessionManager()

# Log JSON entry
sm.log({"event": "test"}, severity="INFO")

# Get session ID
session_id = sm.get_session_id()

# Get log file path
log_path = sm.get_log_file_path()

# Close (cleanup)
sm.close()
```

### PII Scrubbing

```python
from logger.pii import scrub_text, scrub_dict

# Scrub single string
scrubbed, flagged = scrub_text("Email john@example.com")

# Scrub dictionary
scrubbed, flagged = scrub_dict({"query": "Call 555-123-4567"})
```

## Configuration

Set via environment variables:

```bash
# Log directory
export LOG_DIR="/path/to/logs"

# Idle timeout (seconds)
export IDLE_TIMEOUT_SECONDS="900"

# Max age (seconds)
export MAX_AGE_SECONDS="3600"

# Environment
export ENV="dev"  # or "prod"
```

## Testing

Run all tests:
```bash
cd /workspaces/rag-tutorial-v2
python -m pytest tests/test_logging.py -v
```

Run integration test:
```bash
python tests/integration_test.py
```

## Best Practices

1. **Always use request_id** - Link all events for one request
2. **Measure latency** - Include time for each stage
3. **Log quality metrics** - Groundedness, citations matter
4. **Use @technical_trace** - Automatic entry/exit logging
5. **Handle errors** - Log before re-raising
6. **Scrub PII** - Done automatically
7. **Monitor logs** - Check for errors regularly

## Troubleshooting

### Logs not appearing?
1. Check log directory exists: `ls -la /workspaces/rag-tutorial-v2/logs/`
2. Check permissions: `ls -la /workspaces/rag-tutorial-v2/logs/*.log`
3. Check SessionManager is imported: `from logger.session_manager import SessionManager`

### PII not being redacted?
1. Verify pattern matches your data format
2. Check `is_flagged` field in log (should be `true` if PII found)
3. Review patterns in [pii.py](../logger/pii.py)

### Performance issues?
1. Use DEBUG severity for tracing only
2. Consider sampling in high-throughput scenarios
3. Monitor log file size

## Examples

See full examples in:
- [query_data.py](../query_data.py) - RAG query with logging
- [populate_database.py](../populate_database.py) - Document ingestion logging
- [tests/integration_test.py](../tests/integration_test.py) - Full E2E simulation
