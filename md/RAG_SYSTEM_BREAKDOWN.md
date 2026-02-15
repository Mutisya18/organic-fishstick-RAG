# RAG System Breakdown: Complete Flow Analysis

**Created:** February 15, 2026  
**Purpose:** Comprehensive analysis of current RAG architecture, data flow, and optimization opportunities

---

## 📊 Executive Overview

Your RAG system is a **dual-provider, multi-stage pipeline** with these key characteristics:

- **Provider Flexibility**: Switch between Ollama (local) and Google Gemini independently for embeddings & generation
- **Dual Collections**: Separate Chroma databases per embedding provider (prevents mixed-space errors)
- **Modular Architecture**: Factory pattern for providers, configuration-driven switching
- **Full Integration**: Embedded in Streamlit UI, FastAPI portal, eligibility determination
- **Logging-Centric**: Structured logging at every stage for observability

---

## 🔄 Complete Data Flow: Start-to-Finish

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         USER INTERACTION LAYER                           │
│                   (Streamlit UI / FastAPI Portal)                        │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │
                    ┌────────────┴────────────┐
                    │                         │
            ┌───────▼──────┐         ┌───────▼──────┐
            │   CLI Query  │         │  Chat Query  │
            │  query_rag() │         │  run_chat()  │
            └───────┬──────┘         └───────┬──────┘
                    │                         │
                    └────────────┬────────────┘
                                 │
                         ┌───────▼────────┐
                         │  Query Router  │
                         │  (backend/     │
                         │   chat.py)     │
                         └───────┬────────┘
                                 │
          ┌──────────────────────┴──────────────────────┐
          │                                             │
    ┌─────▼──────────────────┐            ┌────────────▼──────┐
    │  RAG RETRIEVAL PHASE   │            │  ELIGIBILITY PHASE │
    │  (rag/query_data.py)   │            │  (eligibility/)    │
    └─────┬──────────────────┘            └────────────┬───────┘
          │                                           │
    ┌─────▼─────────────────────────────────────────────────────┐
    │  1. GET EMBEDDING PROVIDER FACTORY                         │
    │  ├─ Read: ACTIVE_EMBEDDING_PROVIDER env var               │
    │  ├─ Route: get_embedding_function() → OllamaEmbeddings   │
    │  │         or GeminiEmbeddingProvider                     │
    │  └─ Initialize: OllamaEmbeddings(base_url, model)        │
    │                 or GeminiEmbeddingProvider(api_key)       │
    └──────────────────┬──────────────────────────────────────┘
                       │
    ┌──────────────────▼──────────────────────────────────────┐
    │  2. LOOKUP COLLECTION METADATA                           │
    │  ├─ Provider: ollama → documents_ollama_nomic_768        │
    │  │            gemini → documents_gemini_embedding_3072   │
    │  ├─ Chroma Path: rag/chroma/ollama or rag/chroma/gemini │
    │  └─ Embedding Space ID: Added to metadata for validation │
    └──────────────────┬──────────────────────────────────────┘
                       │
    ┌──────────────────▼──────────────────────────────────────┐
    │  3. EMBED THE QUERY                                      │
    │  ├─ Input: User's question (query_text)                 │
    │  ├─ Process: embedding_function.embed_query(query_text) │
    │  └─ Output: 768-dim or 3072-dim vector                  │
    └──────────────────┬──────────────────────────────────────┘
                       │
    ┌──────────────────▼──────────────────────────────────────┐
    │  4. SIMILARITY SEARCH IN CHROMA                          │
    │  ├─ Query: db.similarity_search_with_score(query, k=5)  │
    │  ├─ Database: Chroma collection for active provider     │
    │  ├─ Safety Check: Validate embedding_space_id matches   │
    │  └─ Output: Top-5 chunks {doc, score}                   │
    └──────────────────┬──────────────────────────────────────┘
                       │
    ┌──────────────────▼──────────────────────────────────────┐
    │  5. BUILD PROMPT                                         │
    │  ├─ Get: System prompt (from rag/config/prompts.py)     │
    │  ├─ Add: Context from retrieved chunks                  │
    │  ├─ Add: User's original query                          │
    │  ├─ Format: ChatPromptTemplate structure                │
    │  └─ Result: Full_prompt = [system + context + query]    │
    └──────────────────┬──────────────────────────────────────┘
                       │
    ┌──────────────────▼──────────────────────────────────────┐
    │  6. GET GENERATION PROVIDER                              │
    │  ├─ Read: ACTIVE_GENERATION_PROVIDER env var            │
    │  ├─ Route: get_generation_function() → OllamaLLM        │
    │  │         or GeminiGenerationProvider                   │
    │  └─ Initialize: With URL/keys from config               │
    └──────────────────┬──────────────────────────────────────┘
                       │
    ┌──────────────────▼──────────────────────────────────────┐
    │  7. GENERATE RESPONSE                                    │
    │  ├─ Input: full_prompt                                  │
    │  ├─ Process: generation_provider.generate(prompt)       │
    │  ├─ Return: {text, usage, latency_ms, metadata}         │
    │  └─ Duration: Measured & logged                          │
    └──────────────────┬──────────────────────────────────────┘
                       │
    ┌──────────────────▼──────────────────────────────────────┐
    │  8. STRUCTURED RESULT ASSEMBLY                           │
    │  ├─ Response text (generated)                            │
    │  ├─ Sources [{source, page, similarity_score, ...}]     │
    │  ├─ Metadata {request_id, latency_ms, providers}        │
    │  ├─ Token usage {prompt_tokens, completion_tokens}      │
    │  └─ Logging: All captured with RAGLogger                │
    └──────────────────┬──────────────────────────────────────┘
                       │
                ┌──────▼────────┐
                │ PRESENTATION  │
                │ (Next section)│
                └───────────────┘
```

---

## 📥 Phase 1: Database Population (`populate_database.py`)

### Entry Point
```python
python rag/populate_database.py [--reset]
```

### Step-by-Step Flow

#### 1.1 Load Documents
- **What**: Reads PDFs and DOCX files from `rag/data/`
- **How**: 
  - `PyPDFDirectoryLoader` for PDFs
  - `Docx2txtLoader` for DOCX files
- **Output**: List of `Document` objects with page content and metadata
- **Logging**: Captured with request_id, document count, duration

#### 1.2 Split into Chunks
```
Document (e.g., 50 pages)
    ↓
RecursiveCharacterTextSplitter (chunk_size=1000, overlap=200)
    ↓
List of chunks: [Chunk_1, Chunk_2, ..., Chunk_N]
```

- **Splitter Config**: 
  - `chunk_size`: 1000 characters
  - `overlap`: 200 characters (for context continuity)
  - `separators`: `["\n\n", "\n", " ", ""]`
- **Output**: ~500-1000 chunks per document (depends on size)

#### 1.3 Get Active Embedding Provider
```python
embedding_provider = ACTIVE_EMBEDDING_PROVIDER  # "ollama" or "gemini"
embedding_function = get_embedding_function()
```

**Provider Factory Logic** (in `get_embedding_function.py`):
```
ACTIVE_EMBEDDING_PROVIDER="ollama"
    ↓
OllamaEmbeddingProvider(base_url, model)
    ├─ Connects to: http://localhost:11434 (or ngrok tunnel)
    ├─ Model: nomic-embed-text (768 dims)
    └─ Returns: LangChain OllamaEmbeddings wrapper

ACTIVE_EMBEDDING_PROVIDER="gemini"
    ↓
GeminiEmbeddingProvider(api_key, model)
    ├─ Connects to: Google Gemini API
    ├─ Model: gemini-embedding-001 (3072 dims)
    └─ Returns: LangChain GeminiEmbeddings wrapper
```

#### 1.4 Embed Chunks
```python
embeddings = embedding_function.embed_documents(chunk_texts)
# Each chunk → 768-dim (Ollama) or 3072-dim (Gemini) vector
```

- **Performance**: ~100-500ms per chunk depending on provider
- **Batching**: LangChain batches to reduce API calls
- **Output**: List of embedding vectors matching chunks

#### 1.5 Add Metadata to Chunks
```python
for chunk, embedding in zip(chunks, embeddings):
    chunk.metadata["embedding_space_id"] = get_embedding_space_id(provider)
    chunk.metadata["id"] = f"{doc_id}_{chunk_id}"
    chunk.metadata["source"] = original_document_path
    chunk.metadata["page"] = page_number
```

**Metadata Fields**:
- `embedding_space_id`: "ollama:nomic-embed-text:dim=768" (safety check)
- `id`: Unique chunk identifier
- `source`: Original file path
- `page`: Page number from document

#### 1.6 Store in Provider-Specific Collection
```python
collection_name = get_collection_name_for_provider(provider)
# "documents_ollama_nomic_768" or "documents_gemini_embedding_3072"

chroma_path = get_chroma_path_for_provider(provider)
# "rag/chroma/ollama" or "rag/chroma/gemini"

db = Chroma(
    persist_directory=chroma_path,
    collection_name=collection_name,
    embedding_function=embedding_function
)

db.add_documents(chunks)
```

**Result**: 
- Vectors stored in Chroma (persisted to disk)
- Metadata indexed
- Searchable collection ready for queries

### 1.7 Clear Database (Optional)
```
--reset flag
    ↓
Delete: rag/chroma/ollama/ and rag/chroma/gemini/
    ↓
Fresh slate for new documents
```

---

## 🔍 Phase 2: Query & Retrieval (`query_data.py`)

### Entry Points
1. **CLI**: `python rag/query_data.py "What is eligibility?"`
2. **Programmatic**: `query_rag(query_text)` or `extract_sources_from_query(query_text)`
3. **Integration**: Called by `app.py` (Streamlit) and `backend/chat.py` (FastAPI)

### 2.1 Query Initialization
```python
def query_rag(query_text: str, enriched_context=None, prompt_version=None):
    request_id = rag_logger.generate_request_id()
    retrieval_start = time.time()
```

- **Request ID**: Unique trace ID for this entire request
- **Timing**: Start clock for latency measurement

### 2.2 Get Provider Configuration
```python
embedding_provider = ACTIVE_EMBEDDING_PROVIDER  # From env
collection_name = get_collection_name_for_provider(embedding_provider)
chroma_path = get_chroma_path_for_provider(embedding_provider)
embedding_space_id = get_embedding_space_id(embedding_provider)
```

**Example Output**:
```
Provider: "ollama"
Collection: "documents_ollama_nomic_768"
Chroma Path: "rag/chroma/ollama"
Embedding Space ID: "ollama:nomic-embed-text:dim=768"
```

### 2.3 Initialize Embedding Function
```python
embedding_function = get_embedding_function()
```

Same factory as population phase - **must match provider used during indexing**

### 2.4 Connect to Chroma Collection
```python
db = Chroma(
    persist_directory=chroma_path,
    collection_name=collection_name,
    embedding_function=embedding_function
)
```

### 2.5 Embed Query
```python
query_vector = embedding_function.embed_query(query_text)
# Results in 768-dim or 3072-dim vector
```

### 2.6 Similarity Search
```python
results = db.similarity_search_with_score(query_text, k=5)
# Returns: [(Document, similarity_score), ...]
```

**Similarity Scoring**:
- **Metric**: Euclidean distance (lower = more similar)
- **Range**: [0, ∞] where 0 = perfect match, >100 = very different
- **Top-k**: Returns 5 most similar chunks

### 2.7 Safety Validation: Embedding Space Check
```python
for doc, score in results:
    doc_space_id = doc.metadata.get("embedding_space_id")
    if doc_space_id != embedding_space_id:
        raise ValueError("Embedding space mismatch!")
```

**Why**: Prevents accidentally mixing Ollama-embedded and Gemini-embedded chunks
- If you switch providers mid-stream, this catches it
- Ensures mathematical consistency (can't mix 768-dim and 3072-dim)

### 2.8 Build Context
```python
context = "\n---\n".join([doc.page_content for doc, _ in results])
```

**Format**:
```
Chunk 1 content
---
Chunk 2 content
---
Chunk 3 content
...
```

### 2.9 Load System Prompt
```python
system_prompt = SYSTEM_PROMPTS.get(
    prompt_version or DEFAULT_PROMPT_VERSION
)
# e.g., "You are a helpful banking assistant..."
```

Located in: `rag/config/prompts.py`

### 2.10 Build Full Prompt
```python
from langchain_core.prompts import ChatPromptTemplate

template = ChatPromptTemplate.from_messages([
    ("system", system_prompt),
    ("user", f"Context:\n{context}\n\nQuestion:\n{query_text}")
])

full_prompt = template.format_messages(...)
```

**Result**:
```
[System Message]
You are a helpful banking assistant...

[User Message]
Context:
[Top 5 chunks separated by ---]

Question:
[User's original query]
```

---

## 💭 Phase 3: Response Generation

### 3.1 Get Generation Provider
```python
generation_provider = ACTIVE_GENERATION_PROVIDER  # "ollama" or "gemini"
generator = get_generation_function()
```

**Factory Routes To**:
- **Ollama**: `OllamaGenerationProvider(base_url, model)`
  - Model: `llama3.2:3b` (3 billion parameter)
  - URL: Local or ngrok tunnel
  
- **Gemini**: `GeminiGenerationProvider(api_key, model, thinking_level)`
  - Model: `gemini-2.0-flash`
  - Thinking: "low", "medium", "high"

### 3.2 Generate Response
```python
result = generator.generate(
    prompt=full_prompt,
    system_instruction=system_prompt,
    config={}
)
```

**Provider-Specific Behavior**:

**Ollama**:
```python
def generate(self, prompt, system_instruction=None, config=None):
    full = f"{system_instruction}\n\n{prompt}"
    response = self._model.invoke(full)
    return {
        "text": response,
        "usage": {
            "prompt_tokens": est_prompt_tokens,
            "completion_tokens": est_completion_tokens,
            "total_tokens": est_total,
        },
        "latency_ms": latency,
        "metadata": {"model": "llama3.2:3b", "provider": "ollama"}
    }
```

**Gemini**:
```python
def generate(self, prompt, system_instruction=None, config=None):
    response = self._client.models.generate_content(
        model="gemini-2.0-flash",
        contents=prompt,
        system_instruction=system_instruction,
        generation_config={
            "thinking": {"type": self.thinking_level},
            "max_output_tokens": config.get("max_tokens", 2048)
        }
    )
    return {
        "text": response.text,
        "usage": {
            "prompt_tokens": response.usage_metadata.prompt_tokens,
            "completion_tokens": response.usage_metadata.candidates_token_count,
            ...
        },
        "latency_ms": latency,
        "metadata": {"model": "gemini-2.0-flash", "provider": "gemini"}
    }
```

### 3.3 Measure Latency
- **Retrieval Latency**: Time to search DB and extract chunks
- **Generation Latency**: Time for LLM to generate response
- **Total Latency**: Sum of both

---

## 📊 Phase 4: Result Assembly

### Structure
```python
result = {
    "response": "The answer to your question is...",
    "sources": [
        {
            "id": "chunk_123",
            "source": "document.pdf",
            "page": 5,
            "similarity_score": 0.087,
            "content_preview": "Lorem ipsum..."
        },
        ...
    ],
    "metadata": {
        "request_id": "rag_20260215_xyz",
        "embedding_provider": "ollama",
        "generation_provider": "ollama",
        "retrieval_latency_ms": 54.2,
        "generation_latency_ms": 1234.5,
        "total_latency_ms": 1288.7,
    },
    "usage": {
        "prompt_tokens": 342,
        "completion_tokens": 156,
        "total_tokens": 498,
    }
}
```

### Logging
```python
rag_logger.log_info(
    request_id=request_id,
    message=f"Query processed successfully",
    event_type="rag_response_generated",
    metadata={
        "providers": {
            "embedding": embedding_provider,
            "generation": generation_provider,
        },
        "retrieval_latency_ms": retrieval_latency,
        "generation_latency_ms": generation_latency,
        "token_usage": usage,
    }
)
```

---

## 🎨 Phase 5: Presentation to User

### 5.1 Streamlit UI (`app.py`)
```
User Types Message
    ↓
Sends to: backend/chat.run_chat()
    ↓
Receives: {response, sources, metadata, usage}
    ↓
Renders:
├─ Main Response (markdown)
├─ Sources Panel (expandable)
└─ Details Panel (latency, request_id, providers)
```

**Key UI Components**:
```python
st.chat_message("assistant")
st.markdown(response_text)

with st.expander("📊 Details"):
    st.code(f"Request ID: {request_id}", language="text")
    st.metric("Latency", f"{latency_ms:.2f} ms")
    st.json(sources)
```

### 5.2 FastAPI Portal (`portal_api.py`)
```
POST /api/chat
├─ Body: {"query": "What is eligibility?", "mode": "rag"}
├─ Backend: run_chat(query, mode="rag")
└─ Response: JSON with response, sources, metadata
```

**Response Schema**:
```json
{
    "status": "success",
    "data": {
        "response": "...",
        "sources": [...],
        "metadata": {...},
        "usage": {...}
    },
    "request_id": "...",
    "timestamp": "2026-02-15T10:30:00Z"
}
```

### 5.3 Integration with Eligibility Check
When `mode="eligibility"`:
1. Extract account info from query
2. Run through `eligibility/orchestrator.py`
3. Merge eligibility results with RAG context
4. Return combined response

---

## 🏗️ Architecture Components Breakdown

### File Structure
```
rag/
├── config/
│   ├── provider_config.py        ← Configuration (env vars)
│   ├── index_registry.py         ← Collection/provider mapping
│   ├── prompts.py                ← System prompts
│   └── conversation_limits.py    ← Rate limiting
│
├── models/
│   ├── embedding_providers.py    ← Ollama + Gemini wrappers
│   └── generation_providers.py   ← Ollama + Gemini wrappers
│
├── get_embedding_function.py     ← Factory for embeddings
├── get_generation_function.py    ← Factory for generation
├── populate_database.py          ← Ingestion pipeline
├── query_data.py                 ← Query pipeline
│
├── chroma/
│   ├── ollama/                   ← Ollama-embedded vectors
│   └── gemini/                   ← Gemini-embedded vectors
│
├── data/                         ← Input documents (PDFs, DOCX)
└── test_*.py                     ← Various test suites
```

### Key Classes

#### EmbeddingProvider Interface
```python
class EmbeddingProvider:
    def embed_query(text) → List[float]
    def embed_documents(texts) → List[List[float]]
    def get_info() → Dict
```

**Implementations**:
- `OllamaEmbeddingProvider`: Wraps `langchain_ollama.OllamaEmbeddings`
- `GeminiEmbeddingProvider`: Uses `google.genai` Client

#### GenerationProvider Interface
```python
class GenerationProvider:
    def generate(prompt, system_instruction, config) → Dict
    def get_info() → Dict
```

**Implementations**:
- `OllamaGenerationProvider`: Wraps `langchain_ollama.OllamaLLM`
- `GeminiGenerationProvider`: Uses `google.genai` Client

#### RAGLogger
```python
rag_logger.log_info(request_id, message, event_type, metadata)
rag_logger.log_error(request_id, error_type, error_message, traceback)
rag_logger.log_warning(request_id, message, event_type)
```

---

## 🔗 Integration Points

### 1. With Frontend (`app.py`)
```
Streamlit UI
    ↓
run_chat(query_text, mode="rag")  [backend/chat.py]
    ↓
query_rag(query_text)  [rag/query_data.py]
    ↓
RAG Response → Rendered in UI
```

### 2. With Portal API (`portal_api.py`)
```
FastAPI Endpoint
    ↓
/api/chat?query=...&mode=rag
    ↓
run_chat(query, mode="rag")  [backend/chat.py]
    ↓
JSON Response
```

### 3. With Eligibility Module
```
run_chat(query, mode="eligibility")
    ↓
Parse account info from query
    ↓
EligibilityOrchestrator.determine_eligibility()
    ↓
query_rag(enriched_query)  [hybrid: use eligibility context]
    ↓
Combined Response
```

### 4. With Database Module
```
Session Management
    ↓
Store conversations in database
    ↓
Link to request_id from RAG
    ↓
Retrieve history for context
```

---

## 📈 Configuration & Environment

### Key Environment Variables
```bash
# PROVIDER SELECTION (main controls)
ACTIVE_EMBEDDING_PROVIDER=ollama    # or "gemini"
ACTIVE_GENERATION_PROVIDER=ollama   # or "gemini"

# OLLAMA
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_EMBED_MODEL=nomic-embed-text
OLLAMA_CHAT_MODEL=llama3.2:3b

# GEMINI
GEMINI_API_KEY=<your-key>
GEMINI_EMBED_MODEL=gemini-embedding-001
GEMINI_CHAT_MODEL=gemini-2.0-flash
GEMINI_THINKING_LEVEL=low

# SYSTEM
DATA_PATH=rag/data
CHROMA_PERSIST_DIR_OLLAMA=rag/chroma/ollama
CHROMA_PERSIST_DIR_GEMINI=rag/chroma/gemini
DEBUG_MODE=false
```

### Provider Combinations (A/B Testing)
```
1. Ollama Embed + Ollama Gen   ✓ Fully local
2. Ollama Embed + Gemini Gen   ✓ Hybrid: fast embed, smart gen
3. Gemini Embed + Ollama Gen   ✓ Hybrid: cloud embed, local gen
4. Gemini Embed + Gemini Gen   ✓ Fully cloud
```

All combinations supported via env vars - no code changes needed!

---

## ⚡ Performance Characteristics

### Typical Latencies (Single Queries)
```
Ollama + Ollama:
├─ Retrieval: 50-150ms (DB search + embedding)
├─ Generation: 500-3000ms (LLM inference)
└─ Total: 550-3150ms

Gemini + Gemini:
├─ Retrieval: 200-500ms (API latency + embedding)
├─ Generation: 1000-5000ms (API latency + inference)
└─ Total: 1200-5500ms

Hybrid (Ollama Embed + Gemini Gen):
├─ Retrieval: 50-150ms
├─ Generation: 1000-5000ms
└─ Total: 1050-5150ms
```

### Scalability Limits
- **Max documents**: 1000s in Chroma (limited by vector DB size)
- **Chunk limit**: 5-10k chunks per collection
- **Concurrent queries**: 1-5 (Ollama local), 5-50 (Gemini with rate limits)
- **Storage**: ~100KB per chunk in Chroma (~100MB for 1000 docs)

---

## 🐛 Error Handling & Recovery

### Provider Connection Failures
```python
if ACTIVE_EMBEDDING_PROVIDER == "ollama":
    try:
        OllamaEmbeddings(model=MODEL, base_url=URL)
    except Exception:
        # Log error, fail fast
        # Recommendation: Add fallback to Gemini
```

### Embedding Space Mismatch
```python
for doc, score in results:
    if doc.metadata["embedding_space_id"] != current_space_id:
        raise ValueError("Mixed embedding spaces detected!")
```

**Recovery**: 
- If happens during query: Use `--reset` to clear old collections
- Add migration script to reindex with new provider

### Missing Collections
```python
try:
    db = Chroma(persist_directory=path, collection_name=name)
    results = db.similarity_search(query)
except:
    # Collection doesn't exist - need to run populate_database.py
```

---

## 📋 Current Strengths

1. ✅ **Provider Agnostic**: Easy switching without code changes
2. ✅ **Modular Design**: Factory pattern for extensibility
3. ✅ **Safety Checks**: Embedding space validation prevents errors
4. ✅ **Comprehensive Logging**: Every stage tracked with request IDs
5. ✅ **A/B Testing Ready**: Dual collections enable comparison
6. ✅ **Latency Tracking**: Built-in performance measurement
7. ✅ **Multiple Integration Points**: CLI, Streamlit, FastAPI, eligibility

---

## 🎯 Optimization Opportunities

### Quick Wins
1. **Batch Query Processing**: Handle multiple queries in parallel
2. **Vector Cache**: Cache frequently queried embeddings
3. **Smart Chunk Sizing**: Dynamic chunk size based on document type
4. **Retrieval K Tuning**: Adaptive k (currently fixed at 5)

### Medium-Term
1. **Hierarchical Chunking**: Chunk + summarize at multiple levels
2. **Reranking**: Use generation model to rerank retrieved chunks
3. **Query Expansion**: Expand query before retrieval
4. **Provider Latency Awareness**: Route based on measured performance

### Advanced
1. **Hybrid Search**: Vector + keyword/BM25 search
2. **Dynamic Provider Selection**: ML model to predict best provider
3. **Caching Layer**: Redis for response caching
4. **Multi-Collection Query**: Search across Ollama + Gemini simultaneously

---

## 📝 Testing & Validation

All providers validated via:
- `test_phase5_validation.py` - Component tests
- `test_regression_ollama.py` - Ollama-only regression
- `test_collection_isolation.py` - Collection independence
- `test_provider_switching.py` - Dynamic switching
- `test_integration_*.py` - End-to-end flows

---

## Next Steps for Enhancement

1. **Profile Current System**: Measure real bottlenecks
2. **Add Monitoring**: Track provider performance over time
3. **Implement Quick Wins**: Batch processing, caching
4. **A/B Test Providers**: Compare quality metrics
5. **Optimize Chunking**: Fine-tune chunk size/overlap
6. **Hybrid Search**: Add BM25 to vector search

