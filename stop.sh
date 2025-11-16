#!/bin/bash

# Task Crate - Stop Script
# This script stops both backend and frontend servers

echo "🛑 Stopping Task Crate..."
echo ""

# Read PIDs from files
if [ -f /tmp/task-crate-backend.pid ]; then
    BACKEND_PID=$(cat /tmp/task-crate-backend.pid)
    if ps -p $BACKEND_PID > /dev/null 2>&1; then
        echo "🐍 Stopping backend (PID: $BACKEND_PID)..."
        kill $BACKEND_PID 2>/dev/null || true
        rm /tmp/task-crate-backend.pid
    else
        echo "⚠️  Backend already stopped"
        rm /tmp/task-crate-backend.pid 2>/dev/null || true
    fi
else
    echo "⚠️  No backend PID file found"
fi

if [ -f /tmp/task-crate-frontend.pid ]; then
    FRONTEND_PID=$(cat /tmp/task-crate-frontend.pid)
    if ps -p $FRONTEND_PID > /dev/null 2>&1; then
        echo "⚛️  Stopping frontend (PID: $FRONTEND_PID)..."
        kill $FRONTEND_PID 2>/dev/null || true
        rm /tmp/task-crate-frontend.pid
    else
        echo "⚠️  Frontend already stopped"
        rm /tmp/task-crate-frontend.pid 2>/dev/null || true
    fi
else
    echo "⚠️  No frontend PID file found"
fi

# Also kill any lingering processes
pkill -f "python main.py" 2>/dev/null || true
pkill -f "vite" 2>/dev/null || true

echo ""
echo "✅ Task Crate stopped"
