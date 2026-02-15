# RAG System Architecture Diagrams

## 1. High-Level System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          USER LAYER (Frontend)                              │
├──────────────────────┬──────────────────────────┬──────────────────────────┤
│  Streamlit App       │     FastAPI Portal       │     CLI Commands         │
│  (app.py)            │     (portal_api.py)      │     (query_data.py)      │
└──────────────────────┴──────────────────────────┴──────────────────────────┘
                              │
                              ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│                    APPLICATION LAYER (Backend)                              │
│                                                                              │
│  backend/chat.py: run_chat()                                               │
│  ├─ Routes queries to RAG or Eligibility modules                           │
│  ├─ Merges context for hybrid queries                                      │
│  └─ Formats responses for UI/API                                           │
└──────────────────────────────────────────────────────────────────────────────┘
                              │
                              ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│                    ORCHESTRATION LAYER                                       │
├──────────────────────────────────────┬──────────────────────────────────────┤
│  RAG Module (rag/)                   │  Eligibility Module (eligibility/)   │
│  ├─ Query Processing                 │  ├─ Account Extraction              │
│  ├─ Vector Retrieval                 │  ├─ Eligibility Determination       │
│  ├─ Context Building                 │  └─ Evidence Formatting             │
│  └─ Response Generation              │                                      │
└──────────────────────────────────────┴──────────────────────────────────────┘
                    │                              │
        ┌───────────┼──────────────┬───────────────┼────────────┐
        │           │              │               │            │
        ↓           ↓              ↓               ↓            ↓
    ┌────────────────────────────────────────────────────────────────────┐
    │                      PROVIDER LAYER                                │
    ├────────────────────────────────────────────────────────────────────┤
    │                                                                    │
    │  Embedding Providers          Generation Providers               │
    │  ├─ OllamaEmbeddings          ├─ OllamaLLM                       │
    │  └─ GeminiEmbeddings          └─ GeminiGenerationProvider        │
    │                                                                    │
    │  Database Layer                                                   │
    │  ├─ Chroma (Vector Store)                                        │
    │  │  ├─ rag/chroma/ollama/      [Ollama-embedded vectors]        │
    │  │  └─ rag/chroma/gemini/      [Gemini-embedded vectors]        │
    │  └─ PostgreSQL (Conversations & Sessions)                        │
    │                                                                    │
    └────────────────────────────────────────────────────────────────────┘
        │           │                  │           │
        ↓           ↓                  ↓           ↓
    ┌──────────┐ ┌──────────┐  ┌──────────────┐ ┌──────────────┐
    │ Ollama   │ │ Gemini   │  │ Ollama       │ │ Gemini       │
    │ Local    │ │ Cloud    │  │ Local        │ │ Cloud        │
    │ Instance │ │ API      │  │ Instance     │ │ API          │
    └──────────┘ └──────────┘  └──────────────┘ └──────────────┘
```

---

## 2. Document Ingestion Pipeline (Populate Phase)

```
                    ┌─────────────────────┐
                    │   START             │
                    │ populate_database.py│
                    └──────────┬──────────┘
                               │
                    ┌──────────▼──────────┐
                    │ Load Documents      │
                    │ • Load PDFs         │
                    │ • Load DOCX files   │
                    │ from rag/data/      │
                    └──────────┬──────────┘
                               │
                     Result: List[Document]
                               │
                    ┌──────────▼──────────────────┐
                    │ Split into Chunks          │
                    │ RecursiveCharacterSplitter:│
                    │ • chunk_size: 1000         │
                    │ • overlap: 200             │
                    └──────────┬──────────────────┘
                               │
                   Result: List[Chunk] (~500-1000 chunks)
                               │
                    ┌──────────▼──────────────────────────┐
                    │ Get Embedding Provider              │
                    │ ├─ Read: ACTIVE_EMBEDDING_PROVIDER │
                    │ ├─ Route: get_embedding_function() │
                    │ └─ Initialize Provider             │
                    └──────────┬──────────────────────────┘
                               │
                    ┌──────────▼──────────────────────────┐
                    │ Embed All Chunks                    │
                    │ embedding_fn.embed_documents(...)   │
                    │ [BATCH PROCESSING]                  │
                    └──────────┬──────────────────────────┘
                               │
              Result: List[List[float]] (768 or 3072 dims)
                               │
                    ┌──────────▼──────────────────────────┐
                    │ Add Metadata to Chunks              │
                    │ ├─ embedding_space_id (CRITICAL)   │
                    │ ├─ id                               │
                    │ ├─ source                           │
                    │ └─ page                             │
                    └──────────┬──────────────────────────┘
                               │
                    ┌──────────▼──────────────────────────┐
                    │ Determine Collection                │
                    │ ├─ Ollama? → documents_ollama_...   │
                    │ ├─ Gemini? → documents_gemini_...   │
                    │ └─ Path: rag/chroma/{ollama,gemini} │
                    └──────────┬──────────────────────────┘
                               │
                    ┌──────────▼──────────────────────────┐
                    │ Store in Chroma                     │
                    │ ├─ Persist vectors to disk          │
                    │ ├─ Index metadata                   │
                    │ ├─ Create searchable collection     │
                    │ └─ Log completion                   │
                    └──────────┬──────────────────────────┘
                               │
                    ┌──────────▼──────────────────┐
                    │ COMPLETE                    │
                    │ Ready for queries!          │
                    └─────────────────────────────┘
```

---

## 3. Query & Retrieval Pipeline

```
                  ┌────────────────────────────────┐
                  │ USER SUBMITS QUERY             │
                  │ "What is eligibility?"         │
                  └──────────┬─────────────────────┘
                             │
                  ┌──────────▼─────────────────────┐
                  │ Initialize Request             │
                  │ • Generate request_id          │
                  │ • Start timing (retrieval)     │
                  └──────────┬─────────────────────┘
                             │
       ┌─────────────────────┴────────────────────────┐
       │                                               │
       ↓                                               ↓
┌─────────────────────────────┐        ┌──────────────────────────────┐
│ Get Active Embedding        │        │ Get Provider Config          │
│ Provider                    │        │ • Provider name              │
│                             │        │ • Collection name            │
│ ACTIVE_EMBEDDING_PROVIDER   │        │ • Chroma path                │
│ ├─ ollama               ┐   │        │ • Embedding space ID         │
│ └─ gemini               ┘   │        └──────────────────────────────┘
└────────┬────────────────────┘                       │
         │                                            │
         └────────────────────┬─────────────────────┬─┘
                              │
                    ┌─────────▼──────────┐
                    │ Get Embedding Fn   │
                    │ • Initialize       │
                    │ • Connect to       │
                    │   provider         │
                    └─────────┬──────────┘
                              │
                    ┌─────────▼──────────┐
                    │ Connect to Chroma  │
                    │ using provider     │
                    │ config             │
                    └─────────┬──────────┘
                              │
                    ┌─────────▼──────────────────┐
                    │ Embed Query                │
                    │ embedding_fn.embed_query() │
                    │ Query → Vector             │
                    └─────────┬──────────────────┘
                              │
                    ┌─────────▼──────────────────────┐
                    │ Similarity Search              │
                    │ db.similarity_search_with_score│
                    │ (query_vector, k=5)            │
                    │                                │
                    │ Result: Top-5 chunks with      │
                    │ similarity scores              │
                    └─────────┬──────────────────────┘
                              │
                    ┌─────────▼──────────────────────┐
                    │ CRITICAL VALIDATION            │
                    │                                │
                    │ For each retrieved chunk:      │
                    │ • Get: chunk.metadata[EMSP_ID] │
                    │ • Compare: Expected EMSP_ID    │
                    │ • If mismatch: FAIL!           │
                    │   (prevents mixed embeddings)  │
                    └─────────┬──────────────────────┘
                              │
                    ┌─────────▼──────────────────────┐
                    │ Build Context                  │
                    │                                │
                    │ context = CHUNK1 +             │
                    │           --- +                │
                    │           CHUNK2 +             │
                    │           --- +                │
                    │           ...                  │
                    └─────────┬──────────────────────┘
                              │
                    ┌─────────▼──────────────────────┐
                    │ Log Retrieval                  │
                    │ • retrieval_latency_ms         │
                    │ • results_count                │
                    │ • top_scores                   │
                    └─────────┬──────────────────────┘
                              │
                    ┌─────────▼──────────────────────┐
                    │ RETRIEVAL COMPLETE             │
                    │ Ready for generation           │
                    └────────────────────────────────┘
```

---

## 4. Response Generation Pipeline

```
                ┌─────────────────────────────────┐
                │ INPUT FROM RETRIEVAL:           │
                │ • context (top-5 chunks)        │
                │ • query_text (original)         │
                │ • retrieval_latency_ms          │
                └────────────┬────────────────────┘
                             │
                ┌────────────▼────────────────────┐
                │ Load System Prompt              │
                │                                 │
                │ SYSTEM_PROMPTS[version]        │
                │ e.g., "You are a helpful       │
                │        banking assistant..."   │
                └────────────┬────────────────────┘
                             │
                ┌────────────▼────────────────────────────┐
                │ Build Full Prompt (Template)           │
                │                                         │
                │ template = ChatPromptTemplate(         │
                │   messages=[                            │
                │     ("system", system_prompt),         │
                │     ("user", formatted_query_with_ctx) │
                │   ]                                     │
                │ )                                       │
                │                                         │
                │ STRUCTURE:                              │
                │ [SYSTEM PROMPT]                         │
                │ You are a helpful...                    │
                │                                         │
                │ [CONTEXT]                               │
                │ CHUNK1: ...                             │
                │ ---                                     │
                │ CHUNK2: ...                             │
                │ ---                                     │
                │ CHUNK3: ...                             │
                │                                         │
                │ [USER QUERY]                            │
                │ What is eligibility?                    │
                └────────────┬────────────────────────────┘
                             │
                ┌────────────▼────────────────────────────┐
                │ Get Generation Provider                │
                │                                         │
                │ ACTIVE_GENERATION_PROVIDER             │
                │ ├─ ollama → OllamaLLM                  │
                │ └─ gemini → GeminiGenerationProvider   │
                └────────────┬────────────────────────────┘
                             │
                ┌────────────▼────────────────────────────┐
                │ Generate Response                      │
                │                                         │
                │ Start timer (generation_start)         │
                │ generator.generate(full_prompt)        │
                │                                         │
                │ ┌─ OLLAMA PATH ────────────────────┐   │
                │ │ OllamaLLM.invoke(prompt)          │   │
                │ │ Wait for response                  │   │
                │ │ (potentially 500-3000ms)          │   │
                │ └─────────────────────────────────┘   │
                │                                        │
                │ ┌─ GEMINI PATH ────────────────────┐  │
                │ │ genai.models.generate_content()   │  │
                │ │ (API call, potentially 1-5s)      │  │
                │ └─────────────────────────────────┘  │
                └────────────┬────────────────────────────┘
                             │
                ┌────────────▼────────────────────────────┐
                │ Parse Response                         │
                │                                         │
                │ response_obj = {                        │
                │   "text": "The answer is...",           │
                │   "usage": {                            │
                │     "prompt_tokens": 342,              │
                │     "completion_tokens": 156,          │
                │     "total_tokens": 498                │
                │   },                                    │
                │   "latency_ms": 1234.5,                │
                │   "metadata": {                         │
                │     "model": "llama3.2:3b",            │
                │     "provider": "ollama"               │
                │   }                                     │
                │ }                                       │
                └────────────┬────────────────────────────┘
                             │
                ┌────────────▼────────────────────────────┐
                │ Measure & Calculate Metrics            │
                │                                         │
                │ generation_latency = timer.stop()      │
                │ total_latency = retrieval + generation │
                └────────────┬────────────────────────────┘
                             │
                ┌────────────▼────────────────────────────┐
                │ Log Generation                         │
                │                                         │
                │ rag_logger.log_info(                   │
                │   request_id,                          │
                │   "response_generated",                │
                │   metadata={...}                       │
                │ )                                      │
                └────────────┬────────────────────────────┘
                             │
                ┌────────────▼────────────────────────────┐
                │ GENERATION COMPLETE                    │
                │ Return structured result               │
                └────────────────────────────────────────┘
```

---

## 5. Response Assembly & Presentation

```
                ┌──────────────────────────────────┐
                │ Generate() Complete              │
                │                                  │
                │ {response, usage, latency,       │
                │  metadata}                       │
                └────────┬─────────────────────────┘
                         │
                ┌────────▼─────────────────────────┐
                │ Assemble Final Result            │
                │                                  │
                │ final_result = {                 │
                │   "response": "...",             │
                │   "sources": [                   │
                │     {                            │
                │       "id": "chunk_123",         │
                │       "source": "file.pdf",      │
                │       "page": 5,                 │
                │       "similarity": 0.087,       │
                │       "preview": "Lorem..."      │
                │     },                           │
                │     ...                          │
                │   ],                             │
                │   "metadata": {                  │
                │     "request_id": "xyz",        │
                │     "embed_provider": "ollama",  │
                │     "gen_provider": "ollama",    │
                │     "total_latency_ms": 1288.7   │
                │   },                             │
                │   "usage": {                     │
                │     "prompt_tokens": 342,        │
                │     "completion_tokens": 156     │
                │   }                              │
                │ }                                │
                └────────┬─────────────────────────┘
                         │
        ┌────────────────┼────────────────┐
        │                │                │
   ┌────▼──────┐   ┌─────▼──────┐  ┌────▼──────┐
   │ Streamlit │   │  FastAPI   │  │ Database  │
   │    UI     │   │   Portal   │  │  Storage  │
   │           │   │    /API    │  │           │
   │ • Render  │   │            │  │ • Store   │
   │   response│   │ • JSON     │  │   session │
   │ • Show    │   │   response │  │ • Link    │
   │   sources │   │ • 200 OK   │  │   to req  │
   │ • Display │   │            │  │   ID      │
   │   latency │   │ Example:   │  │           │
   │           │   │ {          │  │           │
   │ Markup    │   │   "status" │  │ SQL:      │
   │ rendering │   │   : "ok",  │  │ INSERT    │
   │ in        │   │   "data":  │  │ INTO      │
   │ st.chat   │   │   {...}    │  │ convo...  │
   │ _message  │   │ }          │  │           │
   └───────────┘   └────────────┘  └───────────┘
        │                │                │
        └────────────────┴────────────────┘
                         │
                ┌────────▼────────────┐
                │ USER SEES RESPONSE  │
                │ • Full answer       │
                │ • Source info       │
                │ • Performance data  │
                └─────────────────────┘
```

---

## 6. Provider Switching Logic (Factory Pattern)

### Embedding Function Factory
```
ACTIVE_EMBEDDING_PROVIDER env var
        │
        ├─ "ollama" ──────────────────────────┐
        │                                      │
        │    OllamaEmbeddingProvider()         │
        │    ├─ base_url: $OLLAMA_BASE_URL    │
        │    ├─ model: $OLLAMA_EMBED_MODEL    │
        │    ├─ Init: OllamaEmbeddings()      │
        │    └─ embed_query/embed_documents() │
        │                                      │
        │    Result: 768-dim vectors          │
        │    Collection: documents_ollama...   │
        │                                      │
        └─ "gemini" ──────────────────────────┐
                                              │
           GeminiEmbeddingProvider()           │
           ├─ api_key: $GEMINI_API_KEY        │
           ├─ model: $GEMINI_EMBED_MODEL      │
           ├─ Init: google.genai.Client()     │
           └─ embed_query/embed_documents()   │
                                              │
           Result: 3072-dim vectors           │
           Collection: documents_gemini...    │
                                              │
────────────────────────────────────────────┘
```

### Generation Function Factory
```
ACTIVE_GENERATION_PROVIDER env var
        │
        ├─ "ollama" ──────────────────────────┐
        │                                      │
        │    OllamaGenerationProvider()        │
        │    ├─ base_url: $OLLAMA_BASE_URL    │
        │    ├─ model: $OLLAMA_CHAT_MODEL     │
        │    ├─ Init: OllamaLLM()             │
        │    └─ generate(prompt)              │
        │                                      │
        │    Result: Text response            │
        │    Model: llama3.2:3b               │
        │    Token usage: Estimated           │
        │                                      │
        └─ "gemini" ──────────────────────────┐
                                              │
           GeminiGenerationProvider()          │
           ├─ api_key: $GEMINI_API_KEY        │
           ├─ model: $GEMINI_CHAT_MODEL       │
           ├─ thinking_level: $LEVEL          │
           ├─ Init: google.genai.Client()     │
           └─ generate(prompt)                │
                                              │
           Result: Text response              │
           Model: gemini-2.0-flash            │
           Token usage: From API              │
           Thinking: Extended reasoning       │
                                              │
────────────────────────────────────────────┘
```

---

## 7. A/B Testing Configuration

```
Scenario 1: All Local (Fastest)
    ACTIVE_EMBEDDING_PROVIDER=ollama
    ACTIVE_GENERATION_PROVIDER=ollama
    Result: Fast embeddings + fast generation
    Latency: ~0.5-3s total

Scenario 2: Hybrid - Powerful Gen (Best Quality)
    ACTIVE_EMBEDDING_PROVIDER=ollama
    ACTIVE_GENERATION_PROVIDER=gemini
    Result: Fast embeddings + smart generation
    Latency: ~1-5s total

Scenario 3: Hybrid - Cloud Embed (Testing)
    ACTIVE_EMBEDDING_PROVIDER=gemini
    ACTIVE_GENERATION_PROVIDER=ollama
    Result: Cloud embeddings + local generation
    Latency: ~0.5-3.5s total

Scenario 4: All Cloud (Best Quality)
    ACTIVE_EMBEDDING_PROVIDER=gemini
    ACTIVE_GENERATION_PROVIDER=gemini
    Result: Best embeddings + best generation
    Latency: ~1-5.5s total

KEY: All scenarios use separate collections!
Each combination maintains distinct Chroma DBs
-> Prevents embedding space conflicts
-> Enables safe switching at any time
-> Allows parallel testing
```

---

## 8. Data Flow State Diagram

```
                    [IDLE]
                      │
                      │ User Query
                      ↓
        ┌─────────────────────────┐
        │  Validating Input       │
        │  ├─ Check non-empty     │
        │  ├─ Parse command (if)  │
        │  └─ Validate args       │
        └──────────┬──────────────┘
                   │
                   ├─ Invalid → Error Response → [IDLE]
                   │
                   ├─ Valid → Continue
                   ↓
        ┌─────────────────────────┐
        │  Initializing RAG       │
        │  ├─ Load config         │
        │  ├─ Init providers      │
        │  └─ Connect to DB       │
        └──────────┬──────────────┘
                   │
                   ├─ Provider Fail → Error → [IDLE]
                   │
                   ├─ DB Missing → Error → [IDLE]
                   │
                   ├─ Success → Continue
                   ↓
        ┌─────────────────────────┐
        │  Retrieving Context     │
        │  ├─ Embed query         │
        │  ├─ Search DB           │
        │  ├─ Validate chunks     │
        │  └─ Build context       │
        └──────────┬──────────────┘
                   │
                   ├─ No Results → Return "Not found" → [IDLE]
                   │
                   ├─ Space Mismatch → Fatal error → [IDLE]
                   │
                   ├─ Success → Continue
                   ↓
        ┌─────────────────────────┐
        │  Generating Response    │
        │  ├─ Build prompt        │
        │  ├─ Call LLM            │
        │  ├─ Parse response      │
        │  └─ Measure metrics     │
        └──────────┬──────────────┘
                   │
                   ├─ Generation Fail → Error → [IDLE]
                   │
                   ├─ Success → Continue
                   ↓
        ┌─────────────────────────┐
        │  Assembling Result      │
        │  ├─ Combine response    │
        │  ├─ Extract sources     │
        │  ├─ Add metadata        │
        │  └─ Log everything      │
        └──────────┬──────────────┘
                   │
                   ├─ Assembly Fail → Error → [IDLE]
                   │
                   ├─ Success → Continue
                   ↓
        ┌─────────────────────────┐
        │  Presenting to User     │
        │  ├─ Render response     │
        │  ├─ Show sources        │
        │  ├─ Display metrics     │
        │  └─ Store in DB         │
        └──────────┬──────────────┘
                   │
                   ↓
                  [IDLE]
```

