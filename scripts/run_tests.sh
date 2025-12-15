#!/bin/bash
# Run test suite

set -e

cd "$(dirname "$0")/.."

# Activate virtual environment
source .venv/bin/activate

# Export Python path
export PYTHONPATH="${PYTHONPATH}:$(pwd)/backend:$(pwd)/frontend"

echo "🧪 Running FIBO Omni-Director Tests..."
echo ""

# Run pytest with coverage
pytest tests/ -v --tb=short --cov=backend/app --cov=frontend/app --cov-report=term-missing

echo ""
echo "✅ Tests complete!"
