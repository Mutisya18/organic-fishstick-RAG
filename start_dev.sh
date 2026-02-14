#!/bin/bash
# Run both Streamlit (8501) and Portal (8000) for development.
# Usage: bash start_dev.sh

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "Starting Streamlit (port 8501) and Portal (port 8000)..."
bash start.sh &
PID_STREAMLIT=$!
bash start_portal.sh &
PID_PORTAL=$!

echo "Streamlit: http://localhost:8501 (PID $PID_STREAMLIT)"
echo "Portal:    http://localhost:8000 (PID $PID_PORTAL)"
wait
