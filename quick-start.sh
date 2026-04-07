#!/bin/bash
# Quick-start script: Sets up environment and runs Release Desk

set -e

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_ROOT"

echo ""
echo "🎯 Release Desk Quick-Start"
echo "============================"
echo ""

# Check if venv exists; create if not
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
    echo "✅ venv created"
    echo ""
fi

# Activate venv
echo "🔌 Activating venv..."
source venv/bin/activate
echo "✅ venv activated"
echo ""

# Install dependencies
echo "📥 Installing dependencies..."
pip install -q -r requirements.txt
echo "✅ Dependencies installed"
echo ""

# Download spaCy model if needed
echo "📚 Checking spaCy model..."
python -c "import spacy; spacy.load('en_core_web_sm')" 2>/dev/null || {
    echo "  Downloading spaCy model..."
    python -m spacy download en_core_web_sm >/dev/null 2>&1
    echo "✅ spaCy model ready"
}
echo ""

# Run CLI
echo "🚀 Starting Release Desk..."
echo ""
python cli.py run
