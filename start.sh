#!/bin/bash

# Task Crate - One-Click Startup Script
# This script starts both backend and frontend servers

set -e

echo "🚀 Starting Task Crate..."
echo ""

# Check if Ollama is accessible
echo "🔍 Checking Ollama connection..."
if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "✅ Ollama is running"
else
    echo "⚠️  Warning: Ollama not accessible at localhost:11434"
    echo "   Make sure port forwarding is active"
fi
echo ""

# Start backend in background
echo "🐍 Starting backend server..."
cd "$(dirname "$0")/backend"
python main.py > /tmp/backend.log 2>&1 &
BACKEND_PID=$!
echo "   Backend PID: $BACKEND_PID"

# Wait for backend to be ready
sleep 3

# Start frontend in background
echo "⚛️  Starting frontend server..."
cd "$(dirname "$0")"
npm run dev > /tmp/frontend.log 2>&1 &
FRONTEND_PID=$!
echo "   Frontend PID: $FRONTEND_PID"

# Wait for frontend to be ready
sleep 3

echo ""
echo "✅ Task Crate is running!"
echo ""
echo "📱 Frontend:  http://localhost:8080"
echo "🔧 Backend:   http://localhost:8000"
echo "📚 API Docs:  http://localhost:8000/docs"
echo ""
echo "📝 Process IDs:"
echo "   Backend:  $BACKEND_PID"
echo "   Frontend: $FRONTEND_PID"
echo ""
echo "🛑 To stop servers, run: ./stop.sh"
echo "   Or use: kill $BACKEND_PID $FRONTEND_PID"
echo ""

# Save PIDs for stop script
echo "$BACKEND_PID" > /tmp/task-crate-backend.pid
echo "$FRONTEND_PID" > /tmp/task-crate-frontend.pid

# Open browser if BROWSER env var is set
if [ -n "$BROWSER" ]; then
    echo "🌐 Opening browser..."
    "$BROWSER" http://localhost:8080 &
fi
