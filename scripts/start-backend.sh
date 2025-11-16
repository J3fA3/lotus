#!/bin/bash

# AI Task Inference Backend Startup Script
# Run this in the dev container

set -e

echo "🚀 Starting AI Task Inference Backend"
echo ""

# Navigate to backend directory
cd "$(dirname "$0")/backend"

# Check if venv exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
    echo "✅ Virtual environment created"
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "📥 Installing dependencies..."
pip install -q -r requirements.txt

echo ""
echo "✅ Setup complete!"
echo ""
echo "🤖 AI Model: qwen2.5:7b-instruct"
echo "🔗 Ollama URL: http://host.docker.internal:11434"
echo "📡 Backend URL: http://localhost:8000"
echo "📚 API Docs: http://localhost:8000/docs"
echo ""
echo "⚠️  Make sure Ollama is running on your Mac:"
echo "   Terminal on Mac: ollama serve"
echo ""
echo "🚀 Starting FastAPI server..."
echo ""

# Start the server
python main.py
