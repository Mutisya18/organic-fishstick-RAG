#!/bin/bash
# Start the Portal UI (FastAPI) on port 8000.
# Usage: bash start_portal.sh

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [ -f .env ]; then
  export $(cat .env | grep -v '^#' | xargs)
fi

if [ -d venv ]; then
  source venv/bin/activate
fi

# Dev: seed test user if ENV=dev (optional; ignore errors)
python scripts/seed_dev_user.py 2>/dev/null || true

echo "Portal UI: http://localhost:8000"
exec uvicorn portal_api:app --host 0.0.0.0 --port 8000 --reload
