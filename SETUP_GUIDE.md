# Setup Guide

**RAG Chatbot with Eligibility Module**  
**Version**: 1.0 | **Status**: Production Ready ✅

---

## Table of Contents

1. [Quick Start (5 minutes)](#quick-start-5-minutes)
2. [System Requirements](#system-requirements)
3. [Complete Setup (30 minutes)](#complete-setup-30-minutes)
4. [Verification](#verification)
5. [First Run](#first-run)
6. [Data Population](#data-population)
7. [Testing](#testing)
8. [Troubleshooting](#troubleshooting)

---

## Quick Start (5 minutes)

### Fastest Way to Get Running

```bash
# 1. Navigate to project
cd /workspaces/organic-fishstick-RAG

# 2. Activate Python environment
python -m venv venv
source venv/bin/activate  # macOS/Linux
# OR: venv\Scripts\activate  # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Start Ollama (Terminal 1)
ollama serve

# 5. Start web app (Terminal 2)
streamlit run app.py

# 6. Open browser
# http://localhost:8501
```

**Done!** System ready to use.

---

## System Requirements

### Hardware

- **CPU**: 2+ cores (4+ recommended)
- **RAM**: 4GB minimum (8GB+ recommended)
- **Disk**: 5GB free space
- **Network**: Internet for initial setup

### Software

- **Python**: 3.8+ (tested on 3.12.1)
- **OS**: Linux, macOS, or Windows 10+
- **Ollama**: Latest version
- **Browser**: Chrome, Firefox, Safari, or Edge

### Verify Prerequisites

```bash
# Check Python
python --version  # Should be 3.8+

# Check Ollama installed
which ollama || where ollama  # Should return path

# Check disk space
df -h /  # Need 5GB+ free

# Check network
ping 8.8.8.8  # Should work
```

---

## Complete Setup (30 minutes)

### Step 1: Clone/Navigate to Project

```bash
# If you have the code already
cd /workspaces/organic-fishstick-RAG

# If cloning from GitHub
git clone https://github.com/Mutisya18/organic-fishstick-RAG.git
cd organic-fishstick-RAG
```

### Step 2: Python Virtual Environment

```bash
# Create virtual environment
python -m venv venv

# Activate it
source venv/bin/activate  # macOS/Linux

# On Windows:
venv\Scripts\activate

# Verify (should show venv in prompt)
echo $VIRTUAL_ENV
```

### Step 3: Install Dependencies

```bash
# Upgrade pip
pip install --upgrade pip

# Install all packages
pip install -r requirements.txt

# Verify key packages
pip list | grep -E "streamlit|langchain|chromadb|openpyxl"
```

**Expected output**: streamlit, langchain, chromadb, openpyxl all listed

### Step 4: Set Up Ollama

#### Option A: Local Installation

```bash
# 1. Download from https://ollama.ai

# 2. Start Ollama server (keep running)
ollama serve

# 3. In another terminal, pull models
ollama pull nomic-embed-text  # For embeddings (~274MB)
ollama pull llama3.2:3b       # For LLM (~2GB)

# 4. Verify models
ollama list
```

**Expected output**:
```
NAME                      ID              SIZE
nomic-embed-text:latest   0a109f4a9c1a    274 MB
llama3.2:3b:latest        a80c4f17acd5    2.0 GB
```

#### Option B: Remote Ollama

If using remote Ollama (e.g., ngrok tunnel):

```bash
# Test connectivity
curl http://YOUR_REMOTE_URL/api/tags

# Update get_embedding_function.py
# Change OllamaEmbeddings(model=...) to include base_url
```

### Step 5: Create Data Directories

```bash
# Create directories
mkdir -p data
mkdir -p eligibility/data
mkdir -p logs

# Verify
ls -d data eligibility/data logs
```

### Step 6: Create Eligibility Data Files

```bash
# Create empty Excel files (will populate later)
python -c "
import openpyxl

# Eligible customers
wb = openpyxl.Workbook()
ws = wb.active
ws['A1'] = 'ACCOUNTNO'
ws['B1'] = 'CUSTOMERNAMES'
wb.save('eligibility/data/eligible_customers.xlsx')

# Reasons file
wb = openpyxl.Workbook()
ws = wb.active
ws['A1'] = 'account_number'
ws['B1'] = 'Joint_Check'
ws['C1'] = 'CLASSIFICATION'
wb.save('eligibility/data/reasons_file.xlsx')

print('✅ Excel files created')
"
```

### Step 7: Add PDF Documents (Optional for RAG)

```bash
# Copy your PDFs to data/ directory
cp /path/to/document1.pdf data/
cp /path/to/document2.pdf data/

# Verify
ls -la data/*.pdf

# Index them
python populate_database.py

# Verify database created
ls -la chroma/
```

### Step 8: Final Verification

```bash
# Check all imports work
python -c "
import streamlit
import langchain
import chromadb
import pytest
from eligibility.orchestrator import EligibilityOrchestrator
print('✅ All imports successful!')
"

# Check Ollama running
curl -s http://localhost:11434/api/tags | head -c 50

# Check directories
ls -d data eligibility/data logs chroma 2>/dev/null || echo "chroma will be created on first run"
```

---

## Verification

### Pre-Startup Checklist

- [ ] Python 3.8+: `python --version`
- [ ] Virtual env activated: `echo $VIRTUAL_ENV`
- [ ] Dependencies installed: `pip list | grep streamlit`
- [ ] Ollama running: `curl http://localhost:11434/api/tags`
- [ ] Ollama models: `ollama list` shows 2 models
- [ ] Directories exist: `ls -d data eligibility/data logs`
- [ ] Config files exist: `ls eligibility/config/*.json`
- [ ] Imports work: `python -c "import streamlit; import chromadb"`

All checkmarks? → **Ready to start!**

---

## First Run

### Starting the System

```bash
# Terminal 1: Ensure Ollama is running
ollama serve

# Terminal 2: Start Streamlit app
cd /workspaces/organic-fishstick-RAG
source venv/bin/activate
streamlit run app.py

# Wait for message:
# You can now view your Streamlit app in your browser.
# Local URL: http://localhost:8501
```

### Using the Web UI

1. **Open browser**: http://localhost:8501
2. **Chat interface**: Type a question in the chat box
3. **Session ID**: Shown in sidebar (unique per session)
4. **Settings**: Click settings to change prompt version
5. **Eligibility check**: Ask about account eligibility
6. **RAG query**: Ask about documents

### Example Queries

**Eligibility Checking**:
- "Is account 1234567890 eligible?"
- "Can account 9876543210 get a loan?"

**General Questions** (uses RAG):
- "What is a loan?"
- "What are the eligibility requirements?"

### What Happens Behind the Scenes

```
Your Query
  ↓
App checks: Is this about eligibility?
  ├─ YES → Eligibility Module (instant response)
  └─ NO → RAG Search (1-6 seconds)
  ↓
Response displayed
  ↓
Logged with unique request_id
```

---

## Data Population

### For Eligibility Module

#### File 1: Eligible Customers

**Path**: `eligibility/data/eligible_customers.xlsx`

```python
import openpyxl

wb = openpyxl.load_workbook('eligibility/data/eligible_customers.xlsx')
ws = wb.active

# Add eligible accounts
ws.append(['1234567890', 'JOHN DOE'])
ws.append(['1234567891', 'JANE SMITH'])
ws.append(['1234567892', 'BOB JOHNSON'])

wb.save('eligibility/data/eligible_customers.xlsx')
print('✅ Eligible customers updated')
```

#### File 2: Reasons File (Ineligible)

**Path**: `eligibility/data/reasons_file.xlsx`

```python
import openpyxl

wb = openpyxl.load_workbook('eligibility/data/reasons_file.xlsx')
ws = wb.active

# Add columns if not present
if ws.max_column == 1:
    headers = [
        'account_number', 'Joint_Check', 'Average_Bal_check',
        'DPD_Arrears_Check', 'CLASSIFICATION', 'dormancy_status',
        'Arrears_Days', 'Credit_Card_OD_Days', 'DPD_Days'
    ]
    for col, header in enumerate(headers, 1):
        ws.cell(1, col, header)

# Add ineligible accounts with reasons
ws.append(['1234567893', 'Exclude', '', '', 'HIGH_RISK', 'DORMANT', 0, 0, 45])
ws.append(['1234567894', '', 'Exclude', '', 'STANDARD', '', 5000, 1000, 0])

wb.save('eligibility/data/reasons_file.xlsx')
print('✅ Reasons file updated')
```

**Schema**: See [SYSTEM_ARCHITECTURE.md](SYSTEM_ARCHITECTURE.md) for complete column list

### For RAG System

```bash
# 1. Copy PDFs
cp /path/to/your/documents/*.pdf data/

# 2. Index them
python populate_database.py

# 3. Verify
python query_data.py "What is a loan?"
```

---

## Testing

### Run Unit Tests

```bash
# All tests
pytest tests/ -v

# Specific test file
pytest tests/test_intent_detector_unit.py -v
pytest tests/test_eligibility_integration.py -v

# With coverage
pytest tests/ --cov=eligibility --cov=logger
```

### Expected Results

```
platform linux -- Python 3.12.1, pytest-9.0.2
collected 150+ items

tests/test_account_extractor.py::test_extract_single_account PASSED
tests/test_account_validator.py::test_valid_account PASSED
tests/test_eligibility_integration.py::test_full_flow PASSED
...

========================= 150+ passed in 5.23s ==========================
```

### Manual Testing

1. **Start the app**: `streamlit run app.py`
2. **Test eligibility**: Ask "Is account 1234567890 eligible?"
3. **Test RAG**: Ask "What is a loan?"
4. **Check logs**: `tail -f logs/session_*.log | jq`
5. **Verify results**: See responses in UI

---

## Troubleshooting

### Problem: Ollama Connection Refused

```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# If not running:
ollama serve

# If port already in use:
lsof -i :11434
kill -9 <PID>
ollama serve
```

### Problem: "Module Not Found" Error

```bash
# Verify virtual environment activated
echo $VIRTUAL_ENV  # Should show path to venv

# If not activated:
source venv/bin/activate  # macOS/Linux
venv\Scripts\activate     # Windows

# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

### Problem: Port 8501 Already in Use

```bash
# Find process using port
lsof -i :8501

# Kill it
kill -9 <PID>

# Or use different port
streamlit run app.py --server.port 8502
```

### Problem: No Data in Eligibility Module

```bash
# Check files exist
ls -la eligibility/data/*.xlsx

# If missing, create them:
python -c "
import openpyxl
wb = openpyxl.Workbook()
ws = wb.active
ws['A1'] = 'ACCOUNTNO'
wb.save('eligibility/data/eligible_customers.xlsx')
print('✅ Created')
"

# Check file validity
python -c "
import openpyxl
wb = openpyxl.load_workbook('eligibility/data/eligible_customers.xlsx')
print(f'✅ File valid, {wb.active.max_row} rows')
"
```

### Problem: Eligibility Module Won't Start

```bash
# Check config files valid JSON
python -c "
import json
for file in ['checks_catalog', 'reason_detection_rules', 'reason_playbook']:
    with open(f'eligibility/config/{file}.json') as f:
        json.load(f)
    print(f'✅ {file}.json valid')
"

# Test module in isolation
python -c "
from eligibility.orchestrator import EligibilityOrchestrator
try:
    orch = EligibilityOrchestrator()
    print('✅ Module initialized')
except Exception as e:
    print(f'❌ Error: {e}')
"
```

### Problem: Slow Responses

```bash
# Check latency in logs
tail -100 logs/session_*.log | jq '.latency_ms' | sort -n | tail -5

# Optimize: Reduce k value in query_data.py
# Change: k=5 → k=3

# Optimize: Use smaller model
ollama pull tinyllama  # ~160MB, faster

# Restart app
```

### Problem: High Memory Usage

```bash
# Check memory
free -h  # Linux
Get-Process | Sort-Object WorkingSet | Select-Object -Last 5  # Windows

# Reduce chunk size in populate_database.py
# Change: chunk_size=800 → chunk_size=400

# Rebuild database
python populate_database.py --reset

# Restart
```

### Problem: No Logs Appearing

```bash
# Check logs directory exists
mkdir -p logs

# Check write permissions
touch logs/test.log && rm logs/test.log

# Run a query to generate logs
python query_data.py "Test"

# Check logs
ls -la logs/
tail logs/session_*.log | jq
```

---

## Common Commands

```bash
# Start system
ollama serve &              # Terminal 1
streamlit run app.py        # Terminal 2

# Query via command line
python query_data.py "Your question here"

# Populate/reset database
python populate_database.py
python populate_database.py --reset

# Run tests
pytest tests/ -v
pytest tests/test_eligibility_integration.py -v

# View logs
tail -f logs/session_*.log | jq
grep ERROR logs/session_*.log | jq

# Stop everything
pkill -f "streamlit run app.py"
pkill -f "ollama serve"

# Check health
curl http://localhost:11434/api/tags
curl http://localhost:8501
```

---

## Next Steps

1. **Load your PDFs**: Copy to `data/` directory and run `python populate_database.py`
2. **Populate eligibility data**: Add accounts to Excel files in `eligibility/data/`
3. **Run full tests**: `pytest tests/ -v`
4. **Deploy**: See [MAINTENANCE_AND_OPERATIONS.md](MAINTENANCE_AND_OPERATIONS.md)

---

**Setup Complete!** Your system is ready to use.

For operations guide, see: [MAINTENANCE_AND_OPERATIONS.md](MAINTENANCE_AND_OPERATIONS.md)  
For architecture details, see: [SYSTEM_ARCHITECTURE.md](SYSTEM_ARCHITECTURE.md)
