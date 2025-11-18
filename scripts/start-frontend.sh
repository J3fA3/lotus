#!/bin/bash

# AI Task Inference Frontend Startup Script
# Run this in the dev container

set -e

echo "🎨 Starting AI Task Inference Frontend"
echo ""

# Navigate to project root
cd "$(dirname "$0")/.."

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "📦 Installing npm dependencies..."
    npm install
    echo "✅ Dependencies installed"
fi

echo ""
echo "✅ Setup complete!"
echo ""
echo "🌐 Frontend URL: http://localhost:5173"
echo "🔗 API URL: http://localhost:8000"
echo ""
echo "🚀 Starting Vite dev server..."
echo ""

# Start the dev server
npm run dev
