# Portal System - Quick Reference Card

## 🚀 Quick Start (Copy & Paste)

```bash
# 1. Install dependencies (first time only)
pip install -r requirements.txt

# 2. Copy .env template if needed
[ -f .env ] || cp .env.example .env

# 3. Start Portal (all initialization automatic)
bash start_portal.sh

# Portal ready: http://localhost:8000
```

---

## 📋 Pre-Flight Checklist

```bash
# Environment
[ -f .env ] && echo "✅ .env exists" || echo "❌ Missing .env"

# Python
python --version  # Should be 3.8+

# Dependencies
pip list | grep -E "fastapi|sqlalchemy|chroma" 

# Directories
mkdir -p logs rag/{data,chroma/{ollama,gemini}} eligibility/data

# Data Files
find rag/data -type f \( -name "*.pdf" -o -name "*.docx" \) | wc -l

# Database
[ -f organic-fishstick.db ] && echo "✅ DB ready" || echo "ℹ️ Will create on startup"

# Portal
bash start_portal.sh --help
```

---

## ⚡ Common Commands

### **Start Portal**
```bash
bash start_portal.sh              # Full startup with all checks
bash start_portal.sh --no-populate # Skip RAG population (faster)
```

### **Start Alternative UIs**
```bash
bash start.sh                     # Streamlit UI (port 8501)
bash start_dev.sh                 # Both Portal + Streamlit
```

### **Manage Database**
```bash
# Initialize
python -c "from database.initialization import initialize_database; initialize_database()"

# View (SQLite)
sqlite3 organic-fishstick.db ".tables"

# Check size
du -sh rag/chroma/ollama/
```

### **Manage RAG Data**
```bash
# Populate from scratch
python rag/populate_database.py

# Clear and reset (⚠️ destructive)
python rag/populate_database.py --reset

# Add more documents
cp /path/to/docs/*.pdf rag/data/
python rag/populate_database.py  # Re-populate
```

### **Check Logs**
```bash
tail -f logs/*.log                # Watch all logs
tail -f logs/rag_*.log            # RAG operations only
grep ERROR logs/*.log             # Find errors
```

---

## 🔧 Configuration Quick Reference

### **.env Critical Variables**

```bash
# LLM Provider (choose one)
ACTIVE_EMBEDDING_PROVIDER=ollama    # or gemini
ACTIVE_GENERATION_PROVIDER=ollama   # or gemini

# For Ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_EMBED_MODEL=nomic-embed-text
OLLAMA_CHAT_MODEL=llama3.2:3b

# For Gemini
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
ENV=dev  # or prod
```

---

## ✅ Verification Checklist

After `bash start_portal.sh`:

- [ ] No errors during initialization
- [ ] Database initialized successfully
- [ ] Portal starts on http://localhost:8000
- [ ] API docs available at http://localhost:8000/docs
- [ ] Can access http://localhost:8000/health or similar
- [ ] Logs show no critical errors
- [ ] RAG database populated (if data files exist)

---

## 🆘 Quick Troubleshooting

| Issue | Quick Fix |
|-------|-----------|
| `Module not found` | `pip install -r requirements.txt` |
| `Database not available` | `rm organic-fishstick.db` (SQLite) or check PostgreSQL |
| `Cannot connect to Ollama` | `ollama serve` on another terminal |
| `No data files` | `cp *.pdf rag/data/` then restart |
| `.env not found` | `cp .env.example .env` |
| `Port 8000 in use` | `lsof -i :8000` to find process |
| `venv not found` | `python -m venv venv && pip install -r requirements.txt` |

---

## 📂 Key Directory Structure

```
.
├── start_portal.sh              ← Run this
├── .env                         ← Configure this
├── requirements.txt             ← Install from this
│
├── portal_api.py                ← Portal entry point
├── app.py                       ← Streamlit entry point
│
├── database/
│   ├── initialization.py        ← DB setup
│   └── core/
│       └── config.py            ← DB config
│
├── rag/
│   ├── populate_database.py     ← Data population
│   ├── query_data.py            ← RAG queries
│   ├── data/                    ← Your PDF/DOCX files
│   └── chroma/                  ← Vector databases
│       ├── ollama/
│       └── gemini/
│
├── eligibility/
│   └── data/                    ← Eligibility data
│
├── logs/                        ← Application logs
│
└── md/
    ├── STARTUP_GUIDE.md         ← Full guide
    └── other docs...
```

---

## 🔌 Integration Points

### **Frontend (Portal)**
```
http://localhost:8000
→ FastAPI (portal_api.py)
  → Database (SQLite)
  → RAG Query Engine (rag/query_data.py)
  → Vector DB (Chroma)
  → LLM (Ollama/Gemini)
```

### **Initialization Chain**
```
start_portal.sh
  → database/initialization.py
     → Creates schema
  → rag/populate_database.py
     → Loads documents
     → Generates embeddings
     → Stores in Chroma
```

---

## 📚 Documentation Map

| Document | Purpose |
|----------|---------|
| [STARTUP_GUIDE.md](STARTUP_GUIDE.md) | **Start here** - Full setup guide |
| [PORTAL_STARTUP_IMPROVEMENTS.md](PORTAL_STARTUP_IMPROVEMENTS.md) | What changed in start_portal.sh |
| [ARCHITECTURE.md](md/ARCHITECTURE.md) | System design overview |
| [DATABASE_IMPLEMENTATION_GUIDE.md](md/DATABASE_IMPLEMENTATION_GUIDE.md) | DB details |
| [RAG_IMPLEMENTATION_GUIDE.md](md/RAG_IMPLEMENTATION_GUIDE.md) | RAG pipeline details |
| [ENV_REFERENCE.md](md/ENV_REFERENCE.md) | Environment variables |

---

## 🎯 System Initialization Summary

The new `start_portal.sh` script performs:

```
1. ✅ Load .env environment
2. ✅ Activate Python venv
3. ✅ Create directories
4. ✅ Initialize database (schema)
5. ✅ Check data files
6. ✅ Populate RAG (auto-detect if needed)
7. ✅ Seed dev user (if ENV=dev)
8. ✅ Start Portal API
```

**Result:** Production-ready system with all components initialized and verified.

---

## 💡 Pro Tips

```bash
# Skip verbose output but keep errors
bash start_portal.sh 2>&1 | grep -E "ERROR|✅|❌"

# Run in background and check later
nohup bash start_portal.sh > startup.log 2>&1 &

# Fast startup (skip population)
bash start_portal.sh --no-populate

# Monitor startup
tail -f logs/*.log

# Access portal from remote machine
# Change in portal_api startup:
# --host 0.0.0.0 (already set)
# Then: http://your-ip:8000
```

---

## 🔄 Update Procedure (if needed)

```bash
# Update dependencies
pip install -r requirements.txt --upgrade

# Reset everything
rm -rf rag/chroma/* organic-fishstick.db

# Restart
bash start_portal.sh
```

---

**Created:** February 15, 2026  
**For:** organic-fishstick-RAG Project  
**Quick Reference Version**
