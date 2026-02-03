# Environment Configuration Reference

## Overview

The system uses a `.env` file for all configuration settings. This keeps the codebase clean and allows different configurations for different environments (local development, staging, production).

---

## Quick Start

### 1. Load Environment Variables

**Option A: Using the startup script (Recommended)**
```bash
bash start.sh              # Loads .env automatically and starts web UI
bash start.sh query "..."  # Run a query with auto-loaded .env
bash start.sh setup       # Initialize data files with auto-loaded .env
```

**Option B: Manual export (Codespaces/Advanced)**
```bash
export $(cat .env | grep -v '^#' | xargs)
streamlit run app.py
```

---

## Environment Variables

### OLLAMA_BASE_URL
**Purpose**: Base URL for Ollama LLM server  
**Default**: `http://localhost:11434`  
**Examples**:
- Local: `http://localhost:11434`
- Remote (ngrok): `https://your-ngrok-url.ngrok-free.dev`

**Update for remote Ollama**:
```bash
# Edit .env
OLLAMA_BASE_URL=https://your-ngrok-url.ngrok-free.dev

# Then restart
bash start.sh
```

### LOG_DIR
**Purpose**: Directory where session logs are written  
**Default**: `/workspaces/organic-fishstick-RAG/logs`  
**Format**: Absolute path  

**Example**:
```bash
LOG_DIR=/home/user/my-rag-logs
```

### IDLE_TIMEOUT_SECONDS
**Purpose**: Log file rotation trigger - idle timeout  
**Default**: `900` (15 minutes)  
**Notes**: When no activity for this duration, a new log file is created

### MAX_AGE_SECONDS
**Purpose**: Log file rotation trigger - maximum age  
**Default**: `3600` (60 minutes)  
**Notes**: Log files are rotated after reaching this age

### ENV
**Purpose**: Environment label for logs  
**Default**: `dev`  
**Options**: `dev`, `staging`, `prod`  

**Example**:
```bash
ENV=prod  # For production deployment
```

### CHROMA_PATH
**Purpose**: Path to Chroma vector database  
**Default**: `rag/chroma` (relative to project root)  
**Relative paths**: Relative to current working directory  
**Absolute paths**: Use full path `/path/to/chroma`

### DATA_PATH
**Purpose**: Path to data directory (PDFs/DOCX files)  
**Default**: `rag/data` (relative to project root)  
**Note**: The `populate_database.py` script reads from here

### ELIGIBILITY_DATA_PATH
**Purpose**: Path to eligibility data (Excel files)  
**Default**: `eligibility/data` (relative to project root)  
**Files**: Should contain:
  - `eligible_customers.xlsx`
  - `reasons_file.xlsx`

### PROMPT_VERSION
**Purpose**: System prompt version for LLM responses  
**Default**: `1.1.0`  
**Versions**: See `config/prompts.py` for available versions

---

## Common Configurations

### Development (Local Ollama)
```env
OLLAMA_BASE_URL=http://localhost:11434
LOG_DIR=/workspaces/organic-fishstick-RAG/logs
ENV=dev
CHROMA_PATH=rag/chroma
DATA_PATH=rag/data
ELIGIBILITY_DATA_PATH=eligibility/data
```

### Development (Remote Ollama via ngrok)
```env
OLLAMA_BASE_URL=https://your-ngrok-url.ngrok-free.dev
LOG_DIR=/workspaces/organic-fishstick-RAG/logs
ENV=dev
CHROMA_PATH=rag/chroma
DATA_PATH=rag/data
ELIGIBILITY_DATA_PATH=eligibility/data
```

### Production (Cloud Paths)
```env
OLLAMA_BASE_URL=https://api.yourcompany.com/ollama
LOG_DIR=/var/log/rag-chatbot
ENV=prod
CHROMA_PATH=/data/vectors/chroma
DATA_PATH=/data/documents
ELIGIBILITY_DATA_PATH=/data/eligibility
```

---

## Updating Configuration

### Change Ollama URL
```bash
# Edit .env
nano .env

# Change this line:
OLLAMA_BASE_URL=https://new-ngrok-url.ngrok-free.dev

# Restart the app
bash start.sh
```

### Change Log Directory
```bash
# Create new directory
mkdir -p /new/log/path

# Edit .env
LOG_DIR=/new/log/path

# Restart
bash start.sh
```

### Change Environment
```bash
# For production
echo "ENV=prod" >> .env

# Or edit manually
nano .env
```

---

## Verification

### Check current configuration
```bash
# View loaded environment
echo $OLLAMA_BASE_URL
echo $LOG_DIR
echo $ENV

# Or view all RAG variables
env | grep -E "OLLAMA|LOG|CHROMA|DATA|ENV"
```

### Test Ollama connection
```bash
curl $OLLAMA_BASE_URL/api/tags
```

### Test log directory
```bash
# Check directory exists and is writable
touch $LOG_DIR/test.log && rm $LOG_DIR/test.log && echo "✅ OK"
```

---

## Files Modified for Environment Support

The following files now read from `.env`:

| File | Variable | Default |
|------|----------|---------|
| `get_embedding_function.py` | `OLLAMA_BASE_URL` | `http://localhost:11434` |
| `query_data.py` | `CHROMA_PATH` | `chroma` |
| `populate_database.py` | `CHROMA_PATH`, `DATA_PATH` | `chroma`, `data` |
| `logger/session_manager.py` | `LOG_DIR`, `IDLE_TIMEOUT_SECONDS`, `MAX_AGE_SECONDS`, `ENV` | See .env |

---

## Troubleshooting

### Logs not appearing
```bash
# Check LOG_DIR is set and writable
echo $LOG_DIR
ls -la $LOG_DIR

# If not, update .env
LOG_DIR=/workspaces/organic-fishstick-RAG/logs
mkdir -p $LOG_DIR
bash start.sh
```

### Ollama connection failing
```bash
# Check OLLAMA_BASE_URL
echo $OLLAMA_BASE_URL

# Test connection
curl $OLLAMA_BASE_URL/api/tags

# If fails, update .env with correct URL
nano .env
bash start.sh
```

### Database not found
```bash
# Check CHROMA_PATH
echo $CHROMA_PATH

# Verify it exists
ls -la $CHROMA_PATH

# If missing, rebuild
python populate_database.py
```

---

## For Docker/Production

Create a `.env` file in your deployment:

```bash
# Create from template
cp .env.example .env

# Update values for your environment
nano .env

# Start container with env file
docker run --env-file .env your-rag-image
```

Or pass environment variables directly:
```bash
docker run \
  -e OLLAMA_BASE_URL=https://ollama.example.com \
  -e LOG_DIR=/app/logs \
  -e ENV=prod \
  your-rag-image
```

---

## Next Steps

1. ✅ `.env` file created with all settings
2. ✅ Code updated to use environment variables
3. ✅ `start.sh` script created for easy startup
4. Next: Run `bash start.sh` to start the system!

---

*Last Updated: Jan 24, 2026*
