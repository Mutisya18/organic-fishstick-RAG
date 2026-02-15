# System Setup & Startup Guide

This guide walks through the complete initialization process for your RAG Chatbot Portal system, ensuring all components are properly configured and ready to run.

---

## 📋 Quick Start (30 seconds)

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Copy environment template if needed
cp .env.example .env

# 3. Start Portal (includes all initialization)
bash start_portal.sh
```

The portal will initialize automatically and start on **http://localhost:8000**

---

## 🔍 Detailed Initialization Steps

### Step 1: Environment Variables
**Location:** `.env` file at project root  
**Purpose:** Configure all system settings

**Required Variables:**
```bash
# LLM Provider (ollama or gemini)
ACTIVE_EMBEDDING_PROVIDER=ollama
ACTIVE_GENERATION_PROVIDER=ollama

# Ollama Configuration (if using Ollama)
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_EMBED_MODEL=nomic-embed-text
OLLAMA_CHAT_MODEL=llama3.2:3b

# OR Gemini Configuration (if using Gemini)
GEMINI_API_KEY=your_key_here

# Database
DATABASE_TYPE=sqlite
DATABASE_URL=sqlite:///organic-fishstick.db

# Paths
LOG_DIR=logs
DATA_PATH=rag/data
CHROMA_PERSIST_DIR_OLLAMA=rag/chroma/ollama
CHROMA_PERSIST_DIR_GEMINI=rag/chroma/gemini

# Environment
ENV=dev
```

**Validation:**
```bash
# Check if .env exists
[ -f .env ] && echo "✅ .env exists" || echo "❌ Missing .env"
```

---

### Step 2: Python Dependencies
**Location:** `requirements.txt`  
**Purpose:** Install all required Python packages

**Installation:**
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

**Verification:**
```bash
# Test critical imports
python -c "from database import db; from rag import populate_database; print('✅ Dependencies OK')"
```

---

### Step 3: Directory Structure
**Purpose:** Ensure all required directories exist

**Required Directories:**
```
.
├── logs/                      # Application logs
├── rag/
│   ├── data/                  # Source documents (PDF, DOCX)
│   └── chroma/
│       ├── ollama/            # Ollama vector database
│       └── gemini/            # Gemini vector database
└── eligibility/
    └── data/                  # Eligibility data files
```

**Auto-created by `start_portal.sh`** ✅

---

### Step 4: Database Initialization
**Location:** `database/initialization.py`  
**Purpose:** Set up database schema and verify connectivity

**What It Does:**
1. ✅ Checks if database is available
2. ✅ Verifies SQLite write permissions (or PostgreSQL connection)
3. ✅ Creates database tables and schema
4. ✅ Initializes session tables, user tables, etc.

**Manual Trigger (rarely needed):**
```bash
python -c "from database.initialization import initialize_database; initialize_database()"
```

**Troubleshooting:**
```bash
# Check database file exists (SQLite)
ls -la organic-fishstick.db

# Check PostgreSQL connection (if using)
psql -U user -d database_name -c "SELECT 1"
```

---

### Step 5: Data Files
**Location:** `rag/data/`  
**Purpose:** Source documents for RAG embeddings

**Supported Formats:**
- `.pdf` - PDF documents
- `.docx` - Word documents  
- `.doc` - Legacy Word documents

**Setup:**
```bash
# Create data directory
mkdir -p rag/data

# Add documents
cp /path/to/documents/*.pdf rag/data/
cp /path/to/documents/*.docx rag/data/
```

**Check for Data:**
```bash
# Count data files
find rag/data -type f \( -name "*.pdf" -o -name "*.docx" \) | wc -l

# List them
ls -lh rag/data/
```

**⚠️ Important:**
- If no data files found, `start_portal.sh` will **skip** RAG population
- At least one document is recommended for testing
- Use `--no-populate` flag to skip population checks

---

### Step 6: RAG Vector Database Population
**Location:** `rag/populate_database.py`  
**Purpose:** Convert documents to embeddings and store in Chroma vector DB

**What It Does:**
1. ✅ Loads PDF/DOCX files from `rag/data/`
2. ✅ Chunks documents into segments
3. ✅ Generates embeddings using configured provider (Ollama/Gemini)
4. ✅ Stores vector embeddings in Chroma database

**Auto-triggered by `start_portal.sh` if:**
- Data files exist in `rag/data/`
- Chroma database is empty or not populated

**Manual Trigger:**
```bash
# Populate from scratch
python rag/populate_database.py

# Clear and reset (⚠️ destructive)
python rag/populate_database.py --reset

# Repopulate
python rag/populate_database.py --reset && python rag/populate_database.py
```

**Check Status:**
```bash
# Check Ollama database size
du -sh rag/chroma/ollama/

# Check Gemini database size
du -sh rag/chroma/gemini/

# Verify database exists
[ -f rag/chroma/ollama/chroma.sqlite3 ] && echo "✅ DB exists" || echo "❌ DB missing"
```

**Provider Used:**
The script uses whichever provider is set in `ACTIVE_EMBEDDING_PROVIDER`:
```bash
grep ACTIVE_EMBEDDING_PROVIDER .env
# Output: ACTIVE_EMBEDDING_PROVIDER=ollama (or gemini)
```

---

### Step 7: LLM Provider Setup

#### **If Using Ollama:**
```bash
# 1. Install Ollama (download from ollama.ai)
# 2. Download models
ollama pull nomic-embed-text    # For embeddings
ollama pull llama3.2:3b         # For chat

# 3. Start Ollama server
ollama serve

# 4. Verify connectivity
curl http://localhost:11434/api/tags
```

#### **If Using Gemini:**
```bash
# 1. Get Gemini API Key from Google AI Studio
# https://aistudio.google.com

# 2. Set in .env
GEMINI_API_KEY=your_key_here

# 3. No additional setup needed
```

---

### Step 8: Dev User Seeding (Optional)
**Location:** `scripts/seed_dev_user.py`  
**Purpose:** Create test user for development logging in

**Auto-triggered by `start_portal.sh` if:**
- `ENV=dev` in `.env`

**Credentials Created:**
- Username: `admin`
- Password: `default_password` (check script for current value)

**Manual Trigger:**
```bash
python scripts/seed_dev_user.py
```

---

## ✅ Pre-Flight Checklist

Use this before running the portal:

```bash
# 1. Environment
[ -f .env ] && echo "✅ .env exists" || echo "❌ .env missing"
grep ACTIVE_EMBEDDING_PROVIDER .env | head -1

# 2. Virtual Environment
[ -d venv ] && echo "✅ venv exists" || echo "❌ venv missing"

# 3. Dependencies
python -c "import streamlit; import fastapi; print('✅ Core deps OK')" 2>/dev/null || echo "❌ Missing deps"

# 4. Directories
mkdir -p logs rag/data rag/chroma/{ollama,gemini} eligibility/data && echo "✅ Directories ready"

# 5. Data Files
[ "$(find rag/data -type f | wc -l)" -gt 0 ] && echo "✅ Data files found" || echo "⚠️  No data files"

# 6. Database
[ -f organic-fishstick.db ] && echo "✅ Database exists" || echo "ℹ️  Will create on startup"

# 7. LLM Provider
case $(grep ACTIVE_EMBEDDING_PROVIDER .env) in
    *ollama*) curl -s http://localhost:11434/api/tags > /dev/null && echo "✅ Ollama OK" || echo "❌ Ollama not running" ;;
    *gemini*) [ -n "$GEMINI_API_KEY" ] && echo "✅ Gemini key set" || echo "❌ GEMINI_API_KEY not set" ;;
esac
```

---

## 🚀 Running the System

### **Option 1: Portal Only (FastAPI)**
```bash
bash start_portal.sh

# URL: http://localhost:8000
# API Docs: http://localhost:8000/docs
```

### **Option 2: Streamlit Only**
```bash
bash start.sh

# URL: http://localhost:8501
```

### **Option 3: Both (Development)**
```bash
bash start_dev.sh

# Portal: http://localhost:8000
# Streamlit: http://localhost:8501
```

---

## 🔧 Troubleshooting

### Database Issues

**Problem:** `❌ Database not available`

**Solutions:**
```bash
# 1. Check SQLite permissions
ls -la organic-fishstick.db
chmod 644 organic-fishstick.db

# 2. Reset SQLite (⚠️ deletes data)
rm organic-fishstick.db

# 3. For PostgreSQL, check connection
psql -U user -h host -d database_name -c "SELECT 1"
```

---

### Missing Data Files

**Problem:** `⚠️  RAG database empty or not populated`

**Solutions:**
```bash
# 1. Check data directory
find rag/data -type f \( -name "*.pdf" -o -name "*.docx" \)

# 2. Add sample documents
cp ~/Documents/*.pdf rag/data/

# 3. Manually populate
python rag/populate_database.py

# 4. Check for errors
tail -f logs/rag_*.log
```

---

### Ollama Connection Issues

**Problem:** `❌ Cannot connect to Ollama`

**Solutions:**
```bash
# 1. Verify Ollama is running
ollama serve &

# 2. Check models exist
ollama list

# 3. Test connectivity
curl http://localhost:11434/api/tags

# 4. Fix localhost binding (common issue)
# On the Ollama machine:
# Windows: set OLLAMA_HOST=0.0.0.0:11434 && ollama serve
# Linux: OLLAMA_HOST=0.0.0.0:11434 ollama serve
```

---

### Gemini API Key Issues

**Problem:** `GEMINI_API_KEY environment variable must be set`

**Solutions:**
```bash
# 1. Get API key from https://aistudio.google.com
# 2. Add to .env
echo "GEMINI_API_KEY=your_actual_key" >> .env

# 3. Reload environment
source .env
```

---

### Dependencies Not Found

**Problem:** `ModuleNotFoundError: No module named 'X'`

**Solutions:**
```bash
# 1. Activate virtual environment
source venv/bin/activate

# 2. Reinstall dependencies
pip install -r requirements.txt --upgrade

# 3. Check for missing packages
pip list | grep -i [package_name]
```

---

## 📊 Startup Script Flow

### `start_portal.sh` Execution Path:

```
1. Load .env environment variables
   ↓
2. Activate Python virtual environment
   ↓
3. Create required directories (logs, data, chroma)
   ↓
4. Check database availability & initialize schema
   ↓
5. Check for data files in rag/data/
   ↓
6. Auto-populate RAG database if needed
   ├─ Check if Chroma DB is empty
   ├─ If empty: run rag/populate_database.py
   └─ If populated: skip
   ↓
7. Seed dev user (if ENV=dev)
   ↓
8. Display pre-flight summary
   ↓
9. Start FastAPI Portal Server
   ↓
✅ Portal ready on http://localhost:8000
```

---

## 📝 Log Files

**Location:** `logs/` directory

**Key Log Files:**
```bash
# RAG operations
logs/rag_*.log

# Application logs
logs/app_*.log

# Database operations
logs/database_*.log

# View logs
tail -f logs/rag_*.log
```

---

## 🎯 Success Indicators

After running `bash start_portal.sh`, you should see:

```
✅ All pre-flight checks passed!
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🚀 Starting Portal API
   📍 http://localhost:8000
   📚 API Docs: http://localhost:8000/docs
```

**Then:**
1. ✅ Portal loads on http://localhost:8000
2. ✅ API docs available at http://localhost:8000/docs
3. ✅ Database tables created and accessible
4. ✅ RAG embeddings loaded and searchable
5. ✅ Can log in with dev credentials (if ENV=dev)

---

## 📚 Related Documentation

- [ARCHITECTURE.md](md/ARCHITECTURE.md) - System design overview
- [DATABASE_IMPLEMENTATION_GUIDE.md](md/DATABASE_IMPLEMENTATION_GUIDE.md) - DB setup details
- [RAG_IMPLEMENTATION_GUIDE.md](md/RAG_IMPLEMENTATION_GUIDE.md) - RAG pipeline details
- [ENV_REFERENCE.md](md/ENV_REFERENCE.md) - Environment variable reference
- [VIEWING_DATABASE.md](md/VIEWING_DATABASE.md) - Database inspection tools

---

## 🆘 Still Having Issues?

1. **Check logs first:**
   ```bash
   tail -f logs/*.log
   ```

2. **Run full test suite:**
   ```bash
   bash run_phase5_tests.sh
   ```

3. **Manual initialization (step by step):**
   ```bash
   python -c "from database.initialization import initialize_database; initialize_database()"
   python rag/populate_database.py
   ```

4. **Verify all components:**
   ```bash
   # Database
   python -c "from database import db; db.initialize()"
   
   # RAG
   python -c "from rag.query_data import query_rag; print('RAG OK')"
   
   # Portal
   python -c "from portal_api import app; print('Portal OK')"
   ```

---

**Created:** 2024-2026  
**Last Updated:** February 15, 2026  
**Maintained By:** Development Team
