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
echo "  ENV: $ENV"
echo ""

# Create necessary directories
mkdir -p "$LOG_DIR"
mkdir -p "$CHROMA_PATH"
mkdir -p "$DATA_PATH"
mkdir -p "$ELIGIBILITY_DATA_PATH"

# Determine what to start
case "${1:-web}" in
    web)
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
