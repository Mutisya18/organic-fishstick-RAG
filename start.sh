#!/bin/bash

################################################################################
# RAG Chatbot Startup Script
# 
# Loads environment variables from .env and starts the system
# 
# Usage:
#   bash start.sh              # Start Streamlit web UI
#   bash start.sh query        # Start in query mode (CLI)
#   bash start.sh setup        # Run initial setup
################################################################################

set -e

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Load environment variables from .env
if [ -f .env ]; then
    echo "📁 Loading environment from .env..."
    export $(cat .env | grep -v '^#' | xargs)
else
    echo "⚠️  .env file not found. Creating from .env.example..."
    cp .env.example .env
    export $(cat .env | grep -v '^#' | xargs)
    echo "✅ .env created. Please update OLLAMA_BASE_URL if needed."
fi

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    echo "🐍 Activating virtual environment..."
    source venv/bin/activate
fi

# Verify environment variables are set
echo ""
echo "📋 Environment Configuration:"
echo "  OLLAMA_BASE_URL: $OLLAMA_BASE_URL"
echo "  LOG_DIR: $LOG_DIR"
echo "  CHROMA_PATH: $CHROMA_PATH"
echo "  DATA_PATH: $DATA_PATH"
echo "  ELIGIBILITY_DATA_PATH: $ELIGIBILITY_DATA_PATH"
echo "  DATABASE_TYPE: ${DATABASE_TYPE:-sqlite}"
echo "  DATABASE_TIMEOUT: ${DATABASE_TIMEOUT:-30}s"
echo "  ENV: $ENV"
echo ""

# Create necessary directories
mkdir -p "$LOG_DIR"
mkdir -p "$CHROMA_PATH"
mkdir -p "$DATA_PATH"
mkdir -p "$ELIGIBILITY_DATA_PATH"

# Check database availability (with retry logic)
echo "🔍 Checking database availability..."
python -c "
import sys
from database.initialization import check_database_availability, print_database_error_guide
from database.core.config import is_sqlite

db_timeout = ${DATABASE_TIMEOUT:-30}
db_retries = ${DATABASE_INIT_RETRY_COUNT:-3}
db_delay = ${DATABASE_INIT_RETRY_DELAY_MS:-100}

if not check_database_availability(
    timeout_seconds=db_timeout,
    retry_count=db_retries,
    retry_delay_ms=db_delay
):
    print_database_error_guide()
    sys.exit(1)
"

if [ $? -ne 0 ]; then
    echo ""
    echo "❌ Database initialization failed. See error messages above."
    exit 1
fi

echo "✅ Database is ready!"

# Check Ollama connectivity and binding
echo ""
echo "🔍 Checking Ollama availability..."
python -c "
import os
import requests
import sys
from urllib.parse import urlparse

ollama_url = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
parsed = urlparse(ollama_url)
is_remote = 'ngrok' in parsed.netloc or parsed.hostname not in ['localhost', '127.0.0.1']

print(f'  OLLAMA_BASE_URL: {ollama_url}')
print(f'  Remote tunnel: {\"yes\" if is_remote else \"no\"}')

# Try to connect to configured URL
try:
    resp = requests.get(f'{ollama_url}/api/tags', timeout=5)
    if resp.status_code == 200:
        print(f'  ✅ Connected successfully')
    else:
        print(f'  ⚠️  Got HTTP {resp.status_code} - checking localhost fallback...')
        # If remote fails, check localhost
        if is_remote:
            try:
                local_resp = requests.get('http://localhost:11434/api/tags', timeout=3)
                if local_resp.status_code == 200:
                    print(f'')
                    print(f'  🔧 DIAGNOSTIC: Ollama is reachable on localhost:11434 but NOT on {ollama_url}')
                    print(f'')
                    print(f'  LIKELY CAUSE: Ollama is bound to 127.0.0.1 only (localhost binding)')
                    print(f'')
                    print(f'  FIX: On the machine running Ollama, restart with:')
                    print(f'    Windows:  set OLLAMA_HOST=0.0.0.0:11434 && ollama serve')
                    print(f'    Linux:    OLLAMA_HOST=0.0.0.0:11434 ollama serve')
                    print(f'')
                    print(f'  This allows external access via ngrok tunnel.')
                    sys.exit(1)
            except Exception:
                pass  # localhost also failed
except requests.exceptions.ConnectionError:
    print(f'  ❌ Cannot connect to Ollama')
    if is_remote:
        print(f'')
        print(f'  LIKELY CAUSES:')
        print(f'    1. ngrok tunnel is inactive or URL has expired')
        print(f'    2. Remote Ollama instance is not running')
        print(f'    3. Ollama is bound to 127.0.0.1 (localhost only) instead of 0.0.0.0')
        print(f'')
        print(f'  FIXES:')
        print(f'    Option 1: Bind Ollama to all interfaces')
        print(f'      Windows:  set OLLAMA_HOST=0.0.0.0:11434 && ollama serve')
        print(f'      Linux:    OLLAMA_HOST=0.0.0.0:11434 ollama serve')
        print(f'')
        print(f'    Option 2: Restart ngrok tunnel (URL may have expired)')
        print(f'') 
    sys.exit(1)
except requests.exceptions.Timeout:
    print(f'  ❌ Ollama request timed out')
    sys.exit(1)
except Exception as e:
    print(f'  ❌ Error: {type(e).__name__}: {e}')
    sys.exit(1)
"

if [ $? -ne 0 ]; then
    echo ""
    exit 1
fi

# Check if RAG vector database is populated
echo ""
echo "🔍 Checking RAG vector database..."
python -c "
import os
from pathlib import Path

chroma_path = os.getenv('CHROMA_PATH', 'chroma')
db_exists = Path(chroma_path).exists()
db_has_content = False

if db_exists:
    # Check if database has content (chroma creates metadata.sqlite3 when populated)
    metadata_file = Path(chroma_path) / 'chroma.sqlite3'
    db_has_content = metadata_file.exists() and metadata_file.stat().st_size > 0

if not db_has_content:
    print('⚠️  RAG database empty or not populated.')
    print('🔄 Auto-populating database from data files...')
    import subprocess
    result = subprocess.run([
        'python', 'rag/populate_database.py'
    ], cwd='$SCRIPT_DIR')
    
    if result.returncode != 0:
        print('❌ Failed to populate RAG database.')
        import sys
        sys.exit(1)
    print('✅ RAG database populated!')
else:
    print('✅ RAG database is populated!')
"

if [ $? -ne 0 ]; then
    echo ""
    echo "❌ RAG database population failed. See error messages above."
    exit 1
fi

# Determine what to start
case "${1:-web}" in
    web)
        echo ""
        echo "🚀 Starting Streamlit Web UI..."
        echo "   Open: http://localhost:8501"
        streamlit run app.py
        ;;
    query)
        echo "❓ Starting Query Mode (CLI)..."
        if [ -z "$2" ]; then
            echo "Usage: bash start.sh query \"your question here\""
            exit 1
        fi
        python query_data.py "$2"
        ;;
    setup)
        echo "⚙️  Running Setup..."
        echo "Creating directories..."
        python -c "
import openpyxl
import os

# Create eligible_customers.xlsx
if not os.path.exists('eligibility/data/eligible_customers.xlsx'):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws['A1'] = 'ACCOUNTNO'
    ws['B1'] = 'CUSTOMERNAMES'
    wb.save('eligibility/data/eligible_customers.xlsx')
    print('✅ Created eligible_customers.xlsx')

# Create reasons_file.xlsx
if not os.path.exists('eligibility/data/reasons_file.xlsx'):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws['A1'] = 'account_number'
    ws['B1'] = 'Joint_Check'
    ws['C1'] = 'CLASSIFICATION'
    wb.save('eligibility/data/reasons_file.xlsx')
    print('✅ Created reasons_file.xlsx')
"
        echo "✅ Setup complete!"
        echo ""
        echo "Next steps:"
        echo "  1. Add eligibility data to: eligibility/data/"
        echo "  2. Copy PDFs/DOCX to: rag/data/"
        echo "  3. Run: python rag/populate_database.py"
        echo "  4. Start: bash start.sh"
        ;;
    *)
        echo "Usage: bash start.sh [web|query|setup]"
        echo ""
        echo "Commands:"
        echo "  web <default>  Start Streamlit web UI"
        echo "  query <text>   Query from command line"
        echo "  setup          Initialize data files"
        exit 1
        ;;
esac
