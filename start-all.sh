#!/bin/bash

# Complete startup script for AI Task Inference System

echo "╔══════════════════════════════════════════════════════╗"
echo "║   AI Task Inference System - Complete Startup       ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""

# Check Ollama
echo "🔍 Checking Ollama..."
if ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "❌ Ollama is not running!"
    echo ""
    echo "Please start Ollama in a separate terminal:"
    echo "  ollama serve"
    echo ""
    exit 1
else
    echo "✅ Ollama is running"
fi

# Check if backend dependencies are installed
if [ ! -d "backend/venv" ]; then
    echo ""
    echo "⚠️  Backend not set up. Setting up now..."
    cd backend
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    cd ..
fi

# Check if frontend dependencies are installed
if [ ! -d "node_modules" ]; then
    echo ""
    echo "⚠️  Frontend not set up. Installing dependencies..."
    npm install
fi

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║   Starting all services...                          ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""

# Start backend in background
echo "🚀 Starting backend..."
cd backend
source venv/bin/activate
python main.py > ../backend.log 2>&1 &
BACKEND_PID=$!
cd ..

# Wait for backend to start
echo "⏳ Waiting for backend to start..."
sleep 3

if ! curl -s http://localhost:8000/api/health > /dev/null 2>&1; then
    echo "❌ Backend failed to start. Check backend.log"
    kill $BACKEND_PID 2>/dev/null
    exit 1
fi

echo "✅ Backend is running (PID: $BACKEND_PID)"

# Start frontend
echo "🚀 Starting frontend..."
npm run dev &
FRONTEND_PID=$!

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║   🎉 All services started!                          ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""
echo "📱 Frontend:  http://localhost:5173"
echo "🔧 Backend:   http://localhost:8000"
echo "📚 API Docs:  http://localhost:8000/docs"
echo ""
echo "Backend PID: $BACKEND_PID"
echo "Frontend PID: $FRONTEND_PID"
echo ""
echo "To stop all services:"
echo "  kill $BACKEND_PID $FRONTEND_PID"
echo ""
echo "Backend logs: tail -f backend.log"
echo ""
echo "Press Ctrl+C to stop all services..."

# Wait for Ctrl+C
trap "echo ''; echo '🛑 Stopping services...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit 0" INT

# Keep script running
wait
