#!/bin/bash

################################################################################
# Portal API Startup Script - Full Initialization
# 
# Performs complete pre-flight checks and initialization before starting the
# Portal UI (FastAPI) on port 8000.
#
# Checks:
#   1. Environment variables and configuration
#   2. Database availability and initialization
#   3. Required directories exist
#   4. RAG vector database is populated
#   5. Seeding dev user if ENV=dev
#
# Usage:
#   bash start_portal.sh       # Full initialization + start Portal
#   bash start_portal.sh --no-populate  # Skip RAG population
#   bash start_portal.sh --help         # Show help
################################################################################

set -e

# Color output for better readability
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Parse command line arguments
SKIP_POPULATE=false
for arg in "$@"; do
    case $arg in
        --no-populate)
            SKIP_POPULATE=true
            shift
            ;;
        --help)
            echo "Usage: bash start_portal.sh [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --no-populate    Skip RAG database population check"
            echo "  --help           Show this help message"
            exit 0
            ;;
    esac
done

# ============================================================================
# STEP 1: Load Environment Variables
# ============================================================================
echo -e "${BLUE}📁 Step 1: Loading environment configuration...${NC}"
if [ -f .env ]; then
    echo "   ✅ Loading .env"
    export $(cat .env | grep -v '^#' | xargs)
else
    echo -e "${YELLOW}   ⚠️  .env file not found. Creating from .env.example...${NC}"
    if [ -f .env.example ]; then
        cp .env.example .env
        export $(cat .env | grep -v '^#' | xargs)
        echo "   ✅ .env created from .env.example"
    else
        echo -e "${RED}   ❌ Neither .env nor .env.example found${NC}"
        exit 1
    fi
fi

# Set defaults for optional environment variables
OLLAMA_BASE_URL="${OLLAMA_BASE_URL:-http://localhost:11434}"
LOG_DIR="${LOG_DIR:-logs}"
DATA_PATH="${DATA_PATH:-rag/data}"
DATABASE_TYPE="${DATABASE_TYPE:-sqlite}"
DATABASE_TIMEOUT="${DATABASE_TIMEOUT:-30}"
ENV="${ENV:-dev}"

echo -e "${GREEN}   Configuration loaded:${NC}"
echo "     - OLLAMA_BASE_URL: $OLLAMA_BASE_URL"
echo "     - LOG_DIR: $LOG_DIR"
echo "     - DATA_PATH: $DATA_PATH"
echo "     - DATABASE_TYPE: $DATABASE_TYPE"
echo "     - ENV: $ENV"

# ============================================================================
# STEP 2: Activate Virtual Environment
# ============================================================================
echo -e "\n${BLUE}🐍 Step 2: Setting up Python environment...${NC}"
if [ -d venv ]; then
    echo "   ✅ Activating virtual environment"
    source venv/bin/activate
elif [ -d vecna ]; then
    echo "   ✅ Activating virtual environment (vecna)"
    source vecna/bin/activate
else
    echo -e "${YELLOW}   ℹ️  Virtual environment not found (venv/ or vecna/)${NC}"
    echo "     Create with: python -m venv venv && source venv/bin/activate && pip install -r requirements.txt"
fi

# ============================================================================
# STEP 3: Create Required Directories
# ============================================================================
echo -e "\n${BLUE}📂 Step 3: Creating required directories...${NC}"
mkdir -p "$LOG_DIR"
mkdir -p "$DATA_PATH"
mkdir -p "rag/chroma/ollama"
mkdir -p "rag/chroma/gemini"
mkdir -p "eligibility/data"
echo "   ✅ Directories ready"

# ============================================================================
# STEP 4: Check Database Availability and Initialize
# ============================================================================
echo -e "\n${BLUE}🗄️  Step 4: Initializing database...${NC}"
python -c "
import sys
from database.initialization import check_database_availability, initialize_database, print_database_error_guide
from database.core.config import is_sqlite

db_timeout = ${DATABASE_TIMEOUT:-30}
db_retries = ${DATABASE_INIT_RETRY_COUNT:-3}
db_delay = ${DATABASE_INIT_RETRY_DELAY_MS:-100}

print('   Checking database availability...')
if not check_database_availability(
    timeout_seconds=db_timeout,
    retry_count=db_retries,
    retry_delay_ms=db_delay
):
    print_database_error_guide()
    sys.exit(1)

print('   Initializing database schema...')
if not initialize_database(debug=False):
    print_database_error_guide()
    sys.exit(1)

print('   ✅ Database ready')
"

if [ $? -ne 0 ]; then
    echo -e "${RED}   ❌ Database initialization failed. See error messages above.${NC}"
    exit 1
fi

# ============================================================================
# STEP 5: Check Data Files Exist
# ============================================================================
echo -e "\n${BLUE}📄 Step 5: Checking data files...${NC}"
DATA_COUNT=$(find "$DATA_PATH" -type f \( -name "*.pdf" -o -name "*.docx" -o -name "*.doc" \) 2>/dev/null | wc -l)
if [ "$DATA_COUNT" -eq 0 ]; then
    echo -e "${YELLOW}   ⚠️  No data files found in $DATA_PATH${NC}"
    echo "     Expected: PDF or DOCX documents"
    echo "     Action: Add documents to $DATA_PATH/ to populate RAG"
    SKIP_POPULATE=true
else
    echo -e "${GREEN}   ✅ Found $DATA_COUNT data files${NC}"
fi

# ============================================================================
# STEP 6: Check RAG Vector Database Population
# ============================================================================
if [ "$SKIP_POPULATE" = false ]; then
    echo -e "\n${BLUE}🔍 Step 6: Checking RAG vector database...${NC}"
    python -c "
import os
from pathlib import Path

# Determine active provider and check its database
try:
    from rag.config.provider_config import ACTIVE_EMBEDDING_PROVIDER
    from rag.config.index_registry import get_chroma_path_for_provider
    
    chroma_path = get_chroma_path_for_provider(ACTIVE_EMBEDDING_PROVIDER)
    provider = ACTIVE_EMBEDDING_PROVIDER
except Exception as e:
    chroma_path = 'rag/chroma/ollama'
    provider = 'ollama'

db_exists = Path(chroma_path).exists()
db_has_content = False

if db_exists:
    metadata_file = Path(chroma_path) / 'chroma.sqlite3'
    db_has_content = metadata_file.exists() and metadata_file.stat().st_size > 1024

if not db_has_content:
    print(f'   ⚠️  RAG database empty (provider: {provider})')
    print(f'      Path: {chroma_path}')
    print('   🔄 Auto-populating database from data files...')
    import subprocess
    result = subprocess.run(['python', 'rag/populate_database.py'], cwd='.')
    
    if result.returncode != 0:
        print('❌ Failed to populate RAG database.')
        exit(1)
    print('✅ RAG database populated!')
else:
    print(f'   ✅ RAG database populated (provider: {provider})')
    print(f'      Size: {Path(chroma_path).stat().st_size} bytes')
"

    if [ $? -ne 0 ]; then
        echo -e "${RED}   ❌ RAG database population failed.${NC}"
        exit 1
    fi
else
    echo -e "\n${YELLOW}⏭️  Step 6: Skipping RAG database check (--no-populate flag)${NC}"
fi

# ============================================================================
# STEP 7: Seed Dev User (if ENV=dev)
# ============================================================================
if [ "$ENV" = "dev" ]; then
    echo -e "\n${BLUE}👤 Step 7: Seeding dev user...${NC}"
    python scripts/seed_dev_user.py 2>/dev/null || {
        echo -e "${YELLOW}   ℹ️  Could not seed dev user (may already exist)${NC}"
    }
else
    echo -e "\n${BLUE}👤 Step 7: Skipping dev user seed (ENV=$ENV)${NC}"
fi

# ============================================================================
# STEP 8: Pre-flight Checks Summary
# ============================================================================
echo -e "\n${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✅ All pre-flight checks passed!${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "🚀 ${BLUE}Starting Portal API${NC}"
echo -e "   📍 http://localhost:8000"
echo -e "   📚 API Docs: http://localhost:8000/docs"
echo ""
echo -e "💡 ${YELLOW}Quick Tips:${NC}"
echo "   - Check logs in: $LOG_DIR/"
echo "   - Add data to: $DATA_PATH/"
echo "   - Update .env for configuration"
echo ""

# ============================================================================
# START PORTAL
# ============================================================================
exec uvicorn portal_api:app --host 0.0.0.0 --port 8000 --reload
