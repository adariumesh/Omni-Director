#!/bin/bash
# Run FastAPI backend server

set -e

cd "$(dirname "$0")/.."

# Activate virtual environment
source .venv/bin/activate

# Export Python path
export PYTHONPATH="${PYTHONPATH}:$(pwd)/backend"

echo "🚀 Starting FIBO Omni-Director Backend..."
echo "   URL: http://localhost:8000"
echo "   Docs: http://localhost:8000/docs"
echo ""

cd backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
