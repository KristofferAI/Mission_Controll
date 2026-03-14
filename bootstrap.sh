#!/usr/bin/env bash
set -euo pipefail

echo ""
echo "╔══════════════════════════════════════╗"
echo "║   Mission Controll — Bootstrap v0.1  ║"
echo "╚══════════════════════════════════════╝"
echo ""

# Copy .env template if needed
if [ -f ".env.template" ] && [ ! -f ".env" ]; then
    cp .env.template .env
    echo "✅ Created .env from .env.template"
fi

# Create venv if needed
if [ ! -d "venv" ]; then
    echo "🔧 Creating virtual environment..."
    python3 -m venv venv
fi

echo "🔧 Activating venv and installing dependencies..."
source venv/bin/activate
pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet

echo ""
echo "✅ Dependencies installed."
echo "🚀 Starting Mission Controll on http://localhost:8501"
echo ""

streamlit run src/dashboard/app.py \
    --server.port=8501 \
    --server.address=0.0.0.0 \
    --server.headless=true
