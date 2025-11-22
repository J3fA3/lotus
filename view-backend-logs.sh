#!/bin/bash

# View backend logs with filtering for scheduling/AI
echo "📋 Backend Log Viewer - Scheduling & AI Focus"
echo "=============================================="
echo ""
echo "Options:"
echo "  1. View all logs (real-time)"
echo "  2. View only scheduling/AI logs (real-time)"
echo "  3. View last 100 lines"
echo "  4. View last 100 scheduling/AI lines"
echo ""
read -p "Choose option (1-4): " choice

case $choice in
    1)
        echo "📺 Following all backend logs (Ctrl+C to stop)..."
        tail -f /tmp/backend.log
        ;;
    2)
        echo "📺 Following scheduling/AI logs (Ctrl+C to stop)..."
        tail -f /tmp/backend.log | grep --line-buffered -E "SCHEDULING|🤖|AI|Gemini|scheduling|calendar/schedule|scheduling_agent" -i
        ;;
    3)
        echo "📄 Last 100 lines:"
        tail -100 /tmp/backend.log
        ;;
    4)
        echo "📄 Last 100 scheduling/AI lines:"
        tail -1000 /tmp/backend.log | grep -E "SCHEDULING|🤖|AI|Gemini|scheduling|calendar/schedule|scheduling_agent" -i | tail -100
        ;;
    *)
        echo "Invalid option"
        exit 1
        ;;
esac

