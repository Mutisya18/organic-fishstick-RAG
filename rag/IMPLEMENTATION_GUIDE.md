# Multi-Provider RAG Implementation Guide

## Overview

This guide explains the dual-provider architecture that enables seamless switching between **Ollama** (local/self-hosted) and **Google Gemini** for both embeddings and text generation in the RAG system.

**Key Features:**
- ✅ **Independent Provider Selection**: Choose Ollama or Gemini for embeddings and generation independently
- ✅ **Dual Collections**: Maintain separate Chroma collections per embedding provider (prevents mixed-space errors)
- ✅ **Zero Downtime Switching**: Switch providers via environment variables—no code changes needed
- ✅ **A/B Testing Ready**: Keep both Ollama and Gemini collections simultaneously for comparison
- ✅ **Backwards Compatible**: Existing Ollama-only workflows continue to work unchanged

---

## Architecture Overview

### Folder Structure

```
rag/
├── chroma/
│   ├── ollama/        # Embedded vectors from Ollama → Chroma
│   └── gemini/        # Embedded vectors from Gemini → Chroma
├── config/
│   ├── provider_config.py       # Provider selection & settings
│   ├── index_registry.py        # Collection ↔ Provider mapping
│   └── prompts.py               # System prompts (existing)
├── models/
│   ├── embedding_providers.py   # OllamaEmbeddingProvider, GeminiEmbeddingProvider
│   └── generation_providers.py  # OllamaGenerationProvider, GeminiGenerationProvider
├── get_embedding_function.py    # Factory: routes to correct embedding provider
├── get_generation_function.py   # Factory: routes to correct generation provider
├── populate_database.py         # Loads docs → embeds → stores in correct collection
├── query_data.py                # Queries correct collection → generates answer
├── test_regression_ollama.py            # Regression test (Ollama only)
├── test_integration_*.py                # Integration tests for each provider combo
└── data/
    └── (PDF/DOCX files for ingestion)
```

### Data Flow

#### Ingestion (Populate Database)

```
Documents → Load → Split into Chunks
    ↓
Get Active Embedding Provider (from config)
    ↓
Embed Chunks (with provider)
    ↓
Add embedding_space_id to metadata
    ↓
Store in Provider-Specific Collection
    ├─ rag/chroma/ollama/documents_ollama_nomic_768
    └─ rag/chroma/gemini/documents_gemini_embedding_768
```

#### Query (RAG)

```
User Query
    ↓
Get Active Embedding Provider
    ↓
Embed Query (with same provider used for docs)
    ↓
Search in Correct Collection
    ├─ Safety check: verify documents have matching embedding_space_id
    ├─ Retrieve top-k chunks
    ↓
Build Prompt (system instruction + context + query)
    ↓
Get Active Generation Provider
    ↓
Generate Response
    ↓
Log with Provider Metadata
    ↓
Return Response
```

---

## Configuration

### Environment Variables

Set these in your `.env` file (use `.env.example` as a template):

```bash
# PROVIDER SELECTION (the main controls)
ACTIVE_EMBEDDING_PROVIDER=ollama    # or "gemini"
ACTIVE_GENERATION_PROVIDER=ollama   # or "gemini"

# OLLAMA
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_EMBED_MODEL=nomic-embed-text
OLLAMA_CHAT_MODEL=llama3.2:3b

# GEMINI (only needed if using Gemini provider)
GEMINI_API_KEY=<your-api-key>
GEMINI_EMBED_MODEL=text-embedding-004
GEMINI_CHAT_MODEL=gemini-2.0-flash
GEMINI_THINKING_LEVEL=low            # off, low, medium, high

# PATHS
CHROMA_PERSIST_DIR_OLLAMA=rag/chroma/ollama
CHROMA_PERSIST_DIR_GEMINI=rag/chroma/gemini
DATA_PATH=rag/data

# DEBUG
DEBUG_MODE=false
```

### How Provider Selection Works

When you call `get_embedding_function()` or `get_generation_function()`:

```python
from rag.get_embedding_function import get_embedding_function
from rag.config.provider_config import ACTIVE_EMBEDDING_PROVIDER

# Automatically reads ACTIVE_EMBEDDING_PROVIDER from .env
embedding_provider = get_embedding_function()

if ACTIVE_EMBEDDING_PROVIDER == "ollama":
    return OllamaEmbeddingProvider(...)
elif ACTIVE_EMBEDDING_PROVIDER == "gemini":
    return GeminiEmbeddingProvider(...)
```

---

## Quick Start: Provider Switching

### Scenario 1: Stay with Ollama (Default)

No changes needed. Everything works as before.

```bash
ACTIVE_EMBEDDING_PROVIDER=ollama
ACTIVE_GENERATION_PROVIDER=ollama
```

---

### Scenario 2: Switch Generation to Gemini (Fast Query Upgrade)

Use Ollama for retrieval (already indexed) but Gemini for faster/better generation.

**Setup:**
```bash
# .env
ACTIVE_EMBEDDING_PROVIDER=ollama    # ← Keep this
ACTIVE_GENERATION_PROVIDER=gemini   # ← Change this
GEMINI_API_KEY=<your-key>
```

**Run:**
```bash
python rag/query_data.py "Your question"
# → Retrieves from rag/chroma/ollama/
# → Generates with Gemini
```

**Benefits:**
- ✅ Use existing Ollama collection (no re-indexing)
- ✅ Test Gemini generation quality immediately
- ✅ Compare cost/latency vs Ollama generation
- ✅ Revert in 1 line if not satisfied

---

### Scenario 3: Full Switch to Gemini

Use Gemini for both embeddings and generation.

**Setup:**
```bash
# .env
ACTIVE_EMBEDDING_PROVIDER=gemini
ACTIVE_GENERATION_PROVIDER=gemini
GEMINI_API_KEY=<your-key>
```

**Build Gemini Collection:**
```bash
python rag/populate_database.py
# Creates rag/chroma/gemini/ collection
```

**Query:**
```bash
python rag/query_data.py "Your question"
# → Retrieves from rag/chroma/gemini/
# → Generates with Gemini
```

---

### Scenario 4: A/B Testing (Both Collections)

Keep both Ollama and Gemini collections and test in parallel.

**Setup:**
```bash
# Run with Ollama
ACTIVE_EMBEDDING_PROVIDER=ollama
python rag/populate_database.py

# Switch to Gemini and populate
ACTIVE_EMBEDDING_PROVIDER=gemini
GEMINI_API_KEY=<your-key>
python rag/populate_database.py

# Now both rag/chroma/ollama/ and rag/chroma/gemini/ exist
```

**Test both:**
```bash
# Run regression test (should still pass)
ACTIVE_EMBEDDING_PROVIDER=ollama python rag/test_regression_ollama.py

# Test Gemini collection
ACTIVE_EMBEDDING_PROVIDER=gemini python rag/test_integration_gemini_embed_ollama_gen.py
```

---

## Collection Routing Logic

The system uses `index_registry.py` to map providers to collections:

```python
from rag.config.index_registry import get_collection_name_for_provider

# Automatically returns the correct collection
collection = get_collection_name_for_provider("ollama")
# → "documents_ollama_nomic_768"

collection = get_collection_name_for_provider("gemini")
# → "documents_gemini_embedding_768"
```

**Why this matters:**
- Prevents querying Gemini-embedded docs with Ollama query embeddings
- Allows safe simultaneous collection maintenance
- Enables instant provider switching without data migration

---

## Embedding Space Validation

Each chunk stores `embedding_space_id` in metadata:

```python
chunk.metadata["embedding_space_id"] = "ollama:nomic-embed-text:dim=768"
# or
chunk.metadata["embedding_space_id"] = "gemini:text-embedding-004:dim=768"
```

At query time, the system validates:
```python
# Safety check in query_rag()
for doc in retrieved_docs:
    assert doc.metadata["embedding_space_id"] == expected_space_id
    # Raises error if docs from different embedding provider found
```

This prevents silent failures from mixed embedding spaces.

---

## Provider Wrapper Classes

### Embedding Providers

**Common Interface:**
```python
class EmbeddingProvider:
    def embed_query(text: str) -> List[float]
    def embed_documents(texts: List[str]) -> List[List[float]]
    def get_info() -> Dict[str, Any]
```

**OllamaEmbeddingProvider:**
- Uses LangChain's `OllamaEmbeddings`
- Configurable base URL (local or ngrok)
- Model: `nomic-embed-text` (default)

**GeminiEmbeddingProvider:**
- Uses Google Generative AI API
- Task types: `RETRIEVAL_QUERY` and `RETRIEVAL_DOCUMENT` for optimal encoding
- Model: `text-embedding-004`
- Output: Fixed 768 dimensions

---

### Generation Providers

**Common Interface:**
```python
class GenerationProvider:
    def generate(prompt: str, system_instruction: str, config: Dict) -> Dict[str, Any]
    def get_info() -> Dict[str, Any]
```

**OllamaGenerationProvider:**
- Uses LangChain's `OllamaLLM`
- Model: `llama3.2:3b` (default)
- Returns: `{text, usage, latency_ms, metadata}`

**GeminiGenerationProvider:**
- Uses Google Generative AI API
- Supports thinking modes: `off`, `low`, `medium`, `high`
- Model: `gemini-2.0-flash` (default)
- Returns: `{text, usage, latency_ms, metadata}` with token counts

---

## Testing

Four comprehensive test suites validate the implementation:

### 1. Regression Test (Ollama Only)
```bash
python rag/test_regression_ollama.py
```
Ensures existing Ollama-only workflow still works. **Run this first** after any changes.

**Tests:**
- Provider config is Ollama
- Providers initialize successfully
- Collection routing works
- Documents load and chunk
- Metadata includes embedding_space_id
- Full RAG query completes

---

### 2. Gemini Generation Test
```bash
ACTIVE_EMBEDDING_PROVIDER=ollama \
ACTIVE_GENERATION_PROVIDER=gemini \
GEMINI_API_KEY=<key> \
python rag/test_integration_gemini_gen_ollama_embed.py
```

**Tests:**
- Hybrid config (Ollama embeddings + Gemini generation)
- Both providers initialize
- Ollama collection is used
- RAG query works with mixed providers
- Response quality checks

---

### 3. Gemini Embedding Test
```bash
ACTIVE_EMBEDDING_PROVIDER=gemini \
ACTIVE_GENERATION_PROVIDER=ollama \
GEMINI_API_KEY=<key> \
python rag/test_integration_gemini_embed_ollama_gen.py
```

**Tests:**
- Hybrid config (Gemini embeddings + Ollama generation)
- Both providers initialize
- Gemini collection is used
- Embedding space validation
- RAG query works

---

### 4. Full Gemini Test
```bash
ACTIVE_EMBEDDING_PROVIDER=gemini \
ACTIVE_GENERATION_PROVIDER=gemini \
GEMINI_API_KEY=<key> \
python rag/test_integration_full_gemini.py
```

**Tests:**
- Full Gemini setup
- Both providers initialize
- Gemini collection is used
- Thinking mode configuration
- Multi-query response quality
- Response grounding

---

## Troubleshooting

### Error: "Collection does not exist"
**Cause:** Using a provider whose collection hasn't been built yet.

**Fix:**
```bash
python rag/populate_database.py
```

---

### Error: "Mixed embedding spaces in collection"
**Cause:** Documents in collection have wrong embedding_space_id in metadata.

**Fix:**
```bash
# Clear the problematic collection
ACTIVE_EMBEDDING_PROVIDER=<provider> python rag/populate_database.py --reset
```

---

### Error: "GEMINI_API_KEY not set"
**Cause:** Trying to use Gemini without API key.

**Fix:**
```bash
# Get key from: https://aistudio.google.com/app/apikey
GEMINI_API_KEY=<your-key> python ...
```

---

### Error: "google-generativeai package not found"
**Cause:** Dependency not installed.

**Fix:**
```bash
pip install google-generativeai
```

---

## Advanced: Custom Provider Configuration

### Per-Query Provider Override (Future Enhancement)

The architecture supports per-query provider overrides:

```python
# Override providers for specific query
result = query_rag(
    query_text="Who is the leader?",
    enriched_context={
        "embedding_provider": "gemini",  # Override
        "generation_provider": "ollama"   # Keep Ollama
    }
)
```

This could be implemented by reading from enriched_context instead of global config.

---

### Fallback Strategy (Future Enhancement)

If primary provider fails, automatically fall back:

```python
try:
    response = get_generation_function().generate(prompt)
except GenerationError:
    # Fall back to secondary provider
    fallback_config.ACTIVE_GENERATION_PROVIDER = "ollama"
    response = get_generation_function().generate(prompt)
```

---

## Cost & Latency Comparison

### Ollama (Self-Hosted)
- **Cost:** Free (local GPU only)
- **Latency:** 2-10s (depends on GPU)
- **Control:** Full (open-source models)

### Gemini (Cloud)
- **Cost:** ~$0.02-0.10 per 1M tokens
- **Latency:** 1-5s (API)
- **Control:** Limited (Google-managed models)

---

## Logging & Observability

All RAG queries log provider information:

```json
{
  "request_id": "abc-123",
  "event": "rag_query_complete",
  "embedding_provider": "ollama",
  "generation_provider": "gemini",
  "collection_used": "documents_ollama_nomic_768",
  "latency_ms": 3500,
  "tokens": {
    "prompt_tokens": 450,
    "completion_tokens": 150
  }
}
```

This makes it easy to:
- Track which providers are used
- Compare latency/cost
- Debug provider-specific issues

---

## Next Steps

1. **Test Ollama Regression:**
   ```bash
   python rag/test_regression_ollama.py
   ```

2. **Try Gemini Generation (if you have API key):**
   ```bash
   ACTIVE_GENERATION_PROVIDER=gemini python rag/test_integration_gemini_gen_ollama_embed.py
   ```

3. **Build Gemini Embedding Collection:**
   ```bash
   ACTIVE_EMBEDDING_PROVIDER=gemini python rag/populate_database.py
   ```

4. **Run Full Gemini Test:**
   ```bash
   ACTIVE_EMBEDDING_PROVIDER=gemini python rag/test_integration_full_gemini.py
   ```

---

## Summary

| Aspect | Details |
|--------|---------|
| **Switching** | Edit `.env` variables, no code changes |
| **Collections** | Separate per provider, auto-routed |
| **Safety** | Embedding space validation prevents mixed-space errors |
| **Testing** | 4 test suites cover all provider combinations |
| **Backwards Compatible** | Ollama-only workflows unchanged |
| **A/B Testing** | Keep both collections simultaneously |
| **Observability** | All provider info logged |

---

**Questions?** Check the inline comments in:
- `rag/config/provider_config.py` — Configuration options
- `rag/config/index_registry.py` — Collection routing logic
- `rag/models/embedding_providers.py` — Embedding implementations
- `rag/models/generation_providers.py` — Generation implementations
