#!/bin/bash
# Setup script for FIBO Omni-Director Pro

set -e

echo "🎬 Setting up FIBO Omni-Director Pro..."

# Check for Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not installed."
    exit 1
fi

# Check for uv (preferred) or pip
if command -v uv &> /dev/null; then
    PKG_MANAGER="uv"
    echo "✓ Using uv package manager"
else
    PKG_MANAGER="pip"
    echo "⚠️ uv not found, using pip (consider installing uv for faster installs)"
fi

# Create virtual environment
echo "📦 Creating virtual environment..."
python3 -m venv .venv
source .venv/bin/activate

# Install backend dependencies
echo "📦 Installing backend dependencies..."
cd backend
if [ "$PKG_MANAGER" = "uv" ]; then
    uv pip install -r requirements.txt
else
    pip install -r requirements.txt
fi
cd ..

# Install frontend dependencies
echo "📦 Installing frontend dependencies..."
cd frontend
if [ "$PKG_MANAGER" = "uv" ]; then
    uv pip install -r requirements.txt
else
    pip install -r requirements.txt
fi
cd ..

# Install test dependencies
echo "📦 Installing test dependencies..."
if [ "$PKG_MANAGER" = "uv" ]; then
    uv pip install pytest pytest-cov pytest-asyncio
else
    pip install pytest pytest-cov pytest-asyncio
fi

# Create data directory
echo "📁 Creating data directories..."
mkdir -p data/images

# Create .env if not exists
if [ ! -f .env ]; then
    echo "📝 Creating .env from template..."
    cp .env.example .env
    echo "⚠️ Please edit .env and add your BRIA_API_KEY"
fi

echo ""
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "  1. Add your Bria API key to .env"
echo "  2. Run tests: ./scripts/run_tests.sh"
echo "  3. Start backend: ./scripts/run_backend.sh"
echo "  4. Start frontend: ./scripts/run_frontend.sh"
