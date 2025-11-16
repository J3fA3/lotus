#!/bin/bash

# Health check script for AI Task Inference setup
# Run this to verify your environment is ready

echo "🔍 AI Task Inference - Health Check"
echo "===================================="
echo ""

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check counter
ISSUES=0

# 1. Check if Ollama is accessible from dev container
echo "1️⃣  Checking Ollama connection..."
if curl -s --max-time 5 http://host.docker.internal:11434/api/tags > /dev/null 2>&1; then
    echo -e "   ${GREEN}✅ Ollama is accessible at host.docker.internal:11434${NC}"
    
    # Check if qwen model is available
    if curl -s http://host.docker.internal:11434/api/tags | grep -q "qwen2.5:7b-instruct"; then
        echo -e "   ${GREEN}✅ Qwen 2.5 7B model is installed${NC}"
    else
        echo -e "   ${YELLOW}⚠️  Qwen 2.5 7B model not found${NC}"
        echo "      Run on your Mac: ollama pull qwen2.5:7b-instruct"
        ISSUES=$((ISSUES+1))
    fi
else
    echo -e "   ${RED}❌ Cannot reach Ollama${NC}"
    echo "      Make sure 'ollama serve' is running on your Mac"
    echo "      Check if host.docker.internal is accessible from dev container"
    ISSUES=$((ISSUES+1))
fi
echo ""

# 2. Check Python environment
echo "2️⃣  Checking Python environment..."
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version)
    echo -e "   ${GREEN}✅ Python installed: $PYTHON_VERSION${NC}"
else
    echo -e "   ${RED}❌ Python3 not found${NC}"
    ISSUES=$((ISSUES+1))
fi

if [ -d "backend/venv" ]; then
    echo -e "   ${GREEN}✅ Backend virtual environment exists${NC}"
else
    echo -e "   ${YELLOW}⚠️  Backend virtual environment not found${NC}"
    echo "      Run: cd backend && python3 -m venv venv"
    ISSUES=$((ISSUES+1))
fi
echo ""

# 3. Check Node.js environment
echo "3️⃣  Checking Node.js environment..."
if command -v node &> /dev/null; then
    NODE_VERSION=$(node --version)
    echo -e "   ${GREEN}✅ Node.js installed: $NODE_VERSION${NC}"
else
    echo -e "   ${RED}❌ Node.js not found${NC}"
    ISSUES=$((ISSUES+1))
fi

if [ -d "node_modules" ]; then
    echo -e "   ${GREEN}✅ Frontend dependencies installed${NC}"
else
    echo -e "   ${YELLOW}⚠️  Frontend dependencies not installed${NC}"
    echo "      Run: npm install"
    ISSUES=$((ISSUES+1))
fi
echo ""

# 4. Check if backend is running
echo "4️⃣  Checking backend status..."
if curl -s --max-time 5 http://localhost:8000/api/health > /dev/null 2>&1; then
    echo -e "   ${GREEN}✅ Backend is running on port 8000${NC}"
else
    echo -e "   ${YELLOW}⚠️  Backend is not running${NC}"
    echo "      Start with: ./start-backend.sh"
fi
echo ""

# 5. Check if frontend is running
echo "5️⃣  Checking frontend status..."
if curl -s --max-time 5 http://localhost:5173 > /dev/null 2>&1; then
    echo -e "   ${GREEN}✅ Frontend is running on port 5173${NC}"
else
    echo -e "   ${YELLOW}⚠️  Frontend is not running${NC}"
    echo "      Start with: ./start-frontend.sh"
fi
echo ""

# 6. Check configuration files
echo "6️⃣  Checking configuration files..."
if [ -f "backend/.env" ]; then
    echo -e "   ${GREEN}✅ Backend .env exists${NC}"
    
    # Check if using correct Ollama URL for dev container
    if grep -q "host.docker.internal" backend/.env; then
        echo -e "   ${GREEN}✅ Backend configured for dev container${NC}"
    else
        echo -e "   ${YELLOW}⚠️  Backend .env may need update for dev container${NC}"
        echo "      Should use: OLLAMA_BASE_URL=http://host.docker.internal:11434"
    fi
else
    echo -e "   ${RED}❌ Backend .env not found${NC}"
    ISSUES=$((ISSUES+1))
fi
echo ""

# Summary
echo "===================================="
if [ $ISSUES -eq 0 ]; then
    echo -e "${GREEN}🎉 All checks passed! You're ready to go!${NC}"
    echo ""
    echo "Next steps:"
    echo "  1. Make sure 'ollama serve' is running on your Mac"
    echo "  2. Start backend: ./start-backend.sh"
    echo "  3. Start frontend: ./start-frontend.sh"
    echo "  4. Open http://localhost:5173 in your browser"
else
    echo -e "${YELLOW}⚠️  Found $ISSUES issue(s) - please fix them above${NC}"
fi
echo ""
