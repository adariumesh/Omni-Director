#!/bin/bash
# Run Streamlit frontend server

set -e

cd "$(dirname "$0")/.."

# Activate virtual environment
source .venv/bin/activate

# Export Python path
export PYTHONPATH="${PYTHONPATH}:$(pwd)/frontend"

echo "🎨 Starting FIBO Omni-Director Frontend..."
echo "   URL: http://localhost:8501"
echo ""

streamlit run frontend/app/main.py --server.port 8501 --server.address localhost
