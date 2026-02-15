# RAG System: Optimization & Enhancement Roadmap

**Document:** Strategic guide for improving performance, reliability, and scalability  
**Status:** Ready for prioritization and implementation

---

## 🎯 Optimization Priorities (Quick Reference)

| Priority | Optimization | Effort | Impact | Timeline |
|----------|-------------|--------|--------|----------|
| 🔴 HIGH | Batch query processing | 2h | 5-10x throughput | Week 1 |
| 🔴 HIGH | Vector cache layer | 3h | 40-60% latency ↓ | Week 1 |
| 🔴 HIGH | Query reranking | 4h | 20-30% quality ↑ | Week 2 |
| 🟡 MED | Adaptive retrieval-k | 2h | 15-25% latency ↓ | Week 1 |
| 🟡 MED | Chunk size tuning | 1h | 10-20% quality ↑ | Week 1 |
| 🟡 MED | Hybrid search (BM25) | 6h | 25-35% quality ↑ | Week 3 |
| 🟡 MED | Smart provider routing | 5h | Provider optimization | Week 4 |
| 🟢 LOW | Query expansion | 3h | Context enrichment | Week 2 |
| 🟢 LOW | Response caching | 2h | 80%+ hit rate (static) | Week 2 |
| 🟢 LOW | Parallel retrieval | 3h | Unlocks future scale | Week 3 |

---

## 🚀 Quick Wins (1-2 hours each)

### 1. Adaptive Retrieval K-Value

**Current**: Fixed `k=5` for all queries

**Problem**: 
- Some queries need more context (complex topics)
- Some queries need less (simple questions) 
- Wastes retrieval cost unnecessarily

**Solution**:
```python
def calculate_adaptive_k(query_text: str, context_length: int = None) -> int:
    """
    Determine optimal k based on query characteristics.
    
    Rules:
    - Short query (<20 chars) → k=3 (simple question)
    - Medium query (20-100 chars) → k=5 (typical)
    - Long query (>100 chars) → k=7 (complex, needs more context)
    - If context_length provided: adjust dynamically
    """
    word_count = len(query_text.split())
    
    if word_count < 5:
        return 3  # Simple question
    elif word_count < 20:
        return 5  # Typical
    else:
        return min(7, word_count // 3)  # Complex, scale with query size

# In query_data.py:
k = calculate_adaptive_k(query_text)
results = db.similarity_search_with_score(query_text, k=k)
```

**Expected Impact**: 
- 10-15% faster simple queries
- Maintain quality for complex queries

**Measurement**:
- Track avg latency by query type
- Monitor retrieval size distribution

---

### 2. Chunk Size Optimization

**Current**: Fixed 1000 chars with 200 char overlap

**Analysis via Testing**:
```python
def analyze_chunk_quality(
    documents: List[Document],
    chunk_sizes: [500, 1000, 1500, 2000],
    overlaps: [100, 200, 300]
):
    """
    Test different chunk configurations to find optimal balance.
    
    Metrics to measure:
    - Chunking time
    - Number of chunks generated
    - Chunk quality (semantic coherence)
    - Retrieval effectiveness
    """
    results = {}
    for size in chunk_sizes:
        for overlap in overlaps:
            chunks = split_documents(docs, size, overlap)
            quality = evaluate_chunks(chunks)
            results[f"{size}@{overlap}"] = quality
    return results
```

**Recommended Tests**:
```
Configuration          Chunks   Time    Quality
500 + 100 overlap      2000+    Fast    Good (too granular?)
1000 + 200 overlap     1000     Med     Good (current)
1000 + 300 overlap     900      Med     Better (more context)
1500 + 300 overlap     650      Med     Best? (longer chunks)
```

**Expected Impact**: 
- Right size = better relevance (10-20% improvement)
- Wrong size = worse performance

**Recommendation**: Start with `1000 + 300` for your banking docs

---

### 3. Simple Query Caching

**Current**: Every query hits vector DB

**Solution**:
```python
from functools import lru_cache
import hashlib

class QueryCache:
    def __init__(self, max_size=1000, ttl_seconds=3600):
        self.cache = {}
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
    
    def get_key(self, query_text: str, provider: str) -> str:
        """Generate cache key from query + provider"""
        key_str = f"{query_text}#{provider}"
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def get(self, query_text: str, provider: str):
        """Retrieve cached result if exists and not expired"""
        key = self.get_key(query_text, provider)
        if key in self.cache:
            result, timestamp = self.cache[key]
            if time.time() - timestamp < self.ttl_seconds:
                return result  # Hit!
            else:
                del self.cache[key]  # Expired
        return None
    
    def set(self, query_text: str, provider: str, result):
        """Store result in cache"""
        if len(self.cache) > self.max_size:
            self._evict_oldest()
        
        key = self.get_key(query_text, provider)
        self.cache[key] = (result, time.time())

# In query_data.py - modify query_rag():
query_cache = QueryCache(max_size=1000, ttl_seconds=3600)

def query_rag(query_text, enriched_context=None, prompt_version=None):
    # Try cache first
    cached = query_cache.get(query_text, ACTIVE_EMBEDDING_PROVIDER)
    if cached:
        rag_logger.log_info(request_id, "cache_hit", metadata={"query": query_text})
        return cached
    
    # Normal flow
    result = ... # existing logic
    
    # Store in cache
    query_cache.set(query_text, ACTIVE_EMBEDDING_PROVIDER, result)
    return result
```

**Expected Impact**: 
- Frequently asked questions: 90%+ latency reduction
- Overall: 20-40% reduction if queries repeat (depends on uniqueness)

**Measurement**:
- Hit rate % per hour
- Latency with/without cache

**Important**: Cache invalidation:
- Rebuild cache when docs updated (on `--reset`)
- Consider setting TTL (1 hour default)

---

## 📈 Medium-Term Enhancements (4-6 hours)

### 4. Query Embedding Caching (Redis-backed)

**Why**: Embedding queries is expensive (200-500ms for Gemini)

**Implementation**:
```python
import redis
import json

class EmbeddingCache:
    def __init__(self, redis_host="localhost", redis_port=6379, ttl_minutes=60):
        self.redis_client = redis.Redis(host=redis_host, port=redis_port)
        self.ttl_minutes = ttl_minutes
    
    def get_or_embed(self, query_text: str, embedding_fn) -> List[float]:
        """Get cached embedding or generate and cache"""
        cache_key = f"emb:{hashlib.md5(query_text.encode()).hexdigest()}"
        
        # Try cache
        cached = self.redis_client.get(cache_key)
        if cached:
            rag_logger.log_info(None, "embedding_cache_hit")
            return json.loads(cached)
        
        # Generate
        embedding = embedding_fn.embed_query(query_text)
        
        # Store in cache (with TTL)
        self.redis_client.setex(
            cache_key,
            self.ttl_minutes * 60,
            json.dumps(embedding)
        )
        
        return embedding
```

**Expected Impact**: 
- Direct embedding reuse: 400-500ms saved per query
- Typical hit rate: 30-50% (common query patterns)
- Overall: 15-25% latency reduction

**Setup Required**: 
- Docker: `docker run -d -p 6379:6379 redis:latest`
- Python: `pip install redis`

---

### 5. Response Reranking

**Problem**: Retrieved chunks ranked by similarity, but not by "answerability"

**Idea**: Use generation model to rerank retrieved chunks

**Implementation**:
```python
def rerank_chunks_by_relevance(
    chunks: List[Document],
    query: str,
    generator,
    top_k: int = 3
) -> List[Document]:
    """
    Use LLM to score retrieved chunks by how well they answer the query.
    Keep top_k after reranking.
    """
    
    # Score each chunk
    scores = []
    for chunk in chunks:
        prompt = f"""
        Query: {query}
        
        Context: {chunk.page_content[:200]}
        
        How relevant is this context to answering the query?
        Score 0-10 where 10 = perfectly answers, 0 = irrelevant.
        """
        
        response = generator.generate(prompt)
        score = extract_score(response.text)  # Extract "8" from "Relevance: 8/10"
        scores.append((chunk, score))
    
    # Rerank by score
    reranked = sorted(scores, key=lambda x: x[1], reverse=True)
    return [chunk for chunk, score in reranked[:top_k]]

# In query_data.py after similarity_search():
if ENABLE_RERANKING:  # New config flag
    results_before = [doc for doc, _ in results]
    results_after = rerank_chunks_by_relevance(
        results_before,
        query_text,
        generator,
        top_k=3
    )
    # Use results_after for context building
```

**Trade-off**:
- Pro: Better answer quality (+20-30%)
- Con: Extra generation call (~1000ms)
- Recommendation: Use only for important queries or enable selectively

**Optimization**: 
- Batch reranking: Score all 5 chunks in 1 call
- Parallel: Rerank while generating main response

---

### 6. Hybrid Search (Vector + BM25 Keyword)

**Problem**: Vector search misses exact keyword matches

**Solution**: Combine vector + keyword (BM25) search

```python
def hybrid_search(
    query_text: str,
    db_vector,  # Chroma instance
    db_keyword,  # BM25 instance (or SQL fulltext)
    k: int = 5
):
    """
    Get results from both vector and keyword search, merge with weights.
    """
    
    # Vector search (semantic)
    vector_results = db_vector.similarity_search(query_text, k=k)
    vector_scores = {doc.metadata["id"]: score for doc, score in vector_results}
    
    # Keyword search (exact terms)
    keyword_results = db_keyword.search(query_text, k=k)
    keyword_scores = {doc.metadata["id"]: score for doc, score in keyword_results}
    
    # Merge with weights
    merged = {}
    for doc_id, v_score in vector_scores.items():
        merged[doc_id] = 0.7 * v_score  # Vector: 70% weight
    
    for doc_id, k_score in keyword_scores.items():
        if doc_id in merged:
            merged[doc_id] += 0.3 * k_score  # Keyword: 30% weight
        else:
            merged[doc_id] = 0.3 * k_score
    
    # Sort and return top-k
    ranked = sorted(merged.items(), key=lambda x: x[1], reverse=True)[:k]
    return [doc for doc_id, _ in ranked]
```

**Implementation Options**:
1. **Chroma + SQL** (Best): Chroma for vectors, PostgreSQL fulltext for keywords
2. **Elasticsearch**: All-in-one hybrid search
3. **Weaviate**: Vector DB with BM25 built-in

**Expected Impact**: 
- Better recall for factual queries (+15-25%)
- Better for banking terms (account numbers, policy codes)

**Setup**: Moderate (requires BM25 index setup)

---

## 🎭 Advanced Optimizations (Week 3+)

### 7. Query Expansion

**Problem**: Short queries miss relevant context

**Example**:
```
Query: "eligibility"
Expanded: "How do I check eligibility? What makes me eligible for a loan?"
```

**Implementation**:
```python
def expand_query(query_text: str, generator, expansion_count: int = 3) -> str:
    """Use LLM to generate query variations"""
    
    prompt = f"""
    Original query: "{query_text}"
    
    Generate {expansion_count} alternative ways to phrase this question
    that would help find more relevant documents.
    
    Format: 
    1. [first variation]
    2. [second variation]
    3. [third variation]
    """
    
    expanded = generator.generate(prompt).text
    variations = extract_variations(expanded)  # Parse numbered list
    
    # Combine original + variations
    all_queries = [query_text] + variations
    combined = " ".join(all_queries)
    return combined

# In query_data.py:
if ENABLE_QUERY_EXPANSION:
    expanded_query = expand_query(query_text, generator)
    results = db.similarity_search(expanded_query, k=5)
```

**Expected Impact**: 
- Recall: +10-20% for vague queries
- Latency cost: +500-1000ms (extra generation)

**Best For**: General knowledge queries (not specific searches)

---

### 8. Parallel Dual-Collection Search

**Current**: Search in 1 collection (active provider)

**Future**: Search both Ollama + Gemini collections simultaneously, merge results

```python
async def parallel_dual_search(query_text: str, query_embedding_vec: List[float]):
    """Search both collections in parallel for comparison"""
    
    # Search Ollama collection
    ollama_task = asyncio.create_task(
        search_in_collection(
            "documents_ollama_nomic_768",
            query_embedding_vec,
            k=5
        )
    )
    
    # Search Gemini collection
    gemini_task = asyncio.create_task(
        search_in_collection(
            "documents_gemini_embedding_3072",
            query_embedding_vec,
            k=5
        )
    )
    
    # Wait for both
    ollama_results, gemini_results = await asyncio.gather(
        ollama_task, gemini_task
    )
    
    # Merge and rank
    merged = merge_results(ollama_results, gemini_results)
    return merged[:5]
```

**Benefits**:
- A/B compare both embedding providers
- Best-of-both quality
- Foundation for ensemble methods

**Cost**: Extra retrieval latency (but parallelized so minimal impact)

---

### 9. Provider Performance Routing

**Idea**: Track provider performance metrics, route intelligently

```python
class ProviderPerformanceMonitor:
    def __init__(self):
        self.metrics = {
            "ollama": {
                "avg_latency_ms": [],
                "error_rate": 0,
                "success_count": 0
            },
            "gemini": {
                "avg_latency_ms": [],
                "error_rate": 0,
                "success_count": 0
            }
        }
    
    def record_success(self, provider: str, latency_ms: float):
        self.metrics[provider]["avg_latency_ms"].append(latency_ms)
        self.metrics[provider]["success_count"] += 1
    
    def record_error(self, provider: str):
        total = max(self.metrics[provider]["success_count"], 1)
        errors = self.metrics[provider].get("error_count", 0) + 1
        self.metrics[provider]["error_rate"] = errors / total
    
    def recommend_provider(self) -> str:
        """Pick provider with best latency + reliability"""
        return min(
            self.metrics.items(),
            key=lambda x: (
                x[1]["error_rate"] * 0.3 +  # 30% weight on reliability
                np.mean(x[1]["avg_latency_ms"][-10:]) * 0.7  # 70% on speed
            )
        )[0]

# Usage:
monitor = ProviderPerformanceMonitor()

# Per request:
try:
    provider = monitor.recommend_provider()
    result = generate_with_provider(provider)
    monitor.record_success(provider, latency)
except Exception as e:
    monitor.record_error(provider)
    # Fallback to other provider
```

**Expected Impact**: 
- Automatic failover if one provider is slow
- Balanced load across providers
- Better user experience

---

### 10. Dynamic Chunk Summarization

**Problem**: Large documents have repetitive chunks

**Solution**: Summarize chunks hierarchically

```
Document:
├─ Section 1 (Summary: "About eligibility requirements")
│  ├─ Chunk 1 (full text)
│  └─ Chunk 2 (full text)
├─ Section 2 (Summary: "Income thresholds")
│  ├─ Chunk 3 (full text)
│  └─ Chunk 4 (full text)
```

**Implementation**:
```python
def create_hierarchical_chunks(document: Document):
    """
    1. Split by section (heuristic: ## headers)
    2. Summarize each section (one call per section)
    3. Create chunks with both summary + full text
    """
    sections = split_by_headers(document.page_content)
    
    hierarchy = []
    for section in sections:
        # Summarize section
        summary_prompt = f"Summarize this in 1-2 sentences:\n{section[:500]}"
        summary = generator.generate(summary_prompt).text
        
        # Create chunk with summary metadata
        chunk = Document(
            page_content=section,
            metadata={
                "summary": summary,
                "section": extract_header(section),
                **document.metadata
            }
        )
        hierarchy.append(chunk)
    
    return hierarchy
```

**Benefits**:
- Retrieve summary first (fast)
- User sees summary in sources
- Can retrieve full text on demand
- Better ranking of relevant sections

**Trade-off**: Summarization cost (~100-200ms per chunk)

---

## 📊 Measurement Framework

### Key Metrics to Track

```python
class RAGMetricsCollector:
    def __init__(self):
        self.metrics = {
            "retrieval_latency_ms": [],
            "generation_latency_ms": [],
            "total_latency_ms": [],
            "chunk_count": [],
            "similarity_scores": [],
            "provider_errors": {},
            "cache_hit_rate": 0,
            "reranking_score_delta": [],
        }
    
    def record_query(self, 
        retrieval_ms: float,
        generation_ms: float,
        chunks_retrieved: int,
        top_score: float,
        cache_hit: bool = False):
        
        self.metrics["retrieval_latency_ms"].append(retrieval_ms)
        self.metrics["generation_latency_ms"].append(generation_ms)
        self.metrics["total_latency_ms"].append(retrieval_ms + generation_ms)
        self.metrics["chunk_count"].append(chunks_retrieved)
        self.metrics["similarity_scores"].append(top_score)
        
        if cache_hit:
            self.metrics["cache_hit_rate"] += 1
    
    def get_summary(self):
        return {
            "avg_retrieval_latency": np.mean(self.metrics["retrieval_latency_ms"]),
            "avg_generation_latency": np.mean(self.metrics["generation_latency_ms"]),
            "avg_total_latency": np.mean(self.metrics["total_latency_ms"]),
            "p95_latency": np.percentile(self.metrics["total_latency_ms"], 95),
            "p99_latency": np.percentile(self.metrics["total_latency_ms"], 99),
            "avg_chunk_count": np.mean(self.metrics["chunk_count"]),
            "avg_similarity_score": np.mean(self.metrics["similarity_scores"]),
        }
```

**Dashboards to Create**:
1. **Latency Dashboard**: Overall + by provider + by operation
2. **Quality Dashboard**: Similarity scores, cache hit rate, reranking delta
3. **Error Dashboard**: Provider failures, error rates by type
4. **Provider Comparison**: Ollama vs Gemini performance

---

## 🎬 Implementation Roadmap

### Week 1: Foundation
- [ ] Chunk size analysis (1h)
- [ ] Adaptive k-value (1h)
- [ ] Query caching (2h)
- [ ] Metrics collector setup (2h)

### Week 2: Performance
- [ ] Query expansion (2h)
- [ ] Embedding cache (Redis) (3h)
- [ ] Response reranking (2h)

### Week 3: Quality
- [ ] Hybrid search setup (4h)
- [ ] Parallel dual-collection (3h)

### Week 4: Intelligence
- [ ] Provider performance monitoring (2h)
- [ ] Smart routing (2h)
- [ ] Dynamic summarization (5h - optional)

### Ongoing: Measurement
- [ ] Set up monitoring dashboards
- [ ] Track metrics weekly
- [ ] A/B test optimizations

---

## 🎯 Success Criteria

### Performance Goals
- [ ] Avg query latency: <1500ms (down from ~2000ms)
- [ ] Cache hit rate: >30% (if documents stable)
- [ ] P95 latency: <3000ms (consistent)

### Quality Goals
- [ ] Retrieval relevance: +20% (via reranking)
- [ ] Source quality: +15% (via hybrid search)
- [ ] User satisfaction: Track in portal

### Reliability Goals
- [ ] Embedding space mismatch: 0 errors
- [ ] Provider error rate: <1%
- [ ] Automatic failover: Working end-to-end

---

## 💡 Quick Reference: Implementation Checklist

```bash
# Week 1
[ ] Create chunk size test suite
[ ] Implement adaptive k calculation
[ ] Set up QueryCache class
[ ] Initialize metrics collector
[ ] Run baseline measurements

# Week 2
[ ] Implement query expansion
[ ] Set up Redis (Docker)
[ ] Create EmbeddingCache class
[ ] Implement reranking function
[ ] A/B test on sample queries

# Week 3
[ ] Integrate BM25 indexer
[ ] Implement parallel search
[ ] Set up dual-collection queries
[ ] Test merge logic

# Week 4
[ ] Create performance monitor
[ ] Add provider routing logic
[ ] Set up dashboard
[ ] Document all changes

# Ongoing
[ ] Run weekly performance review
[ ] Update documentation
[ ] Plan next phase
```

