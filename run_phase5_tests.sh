#!/bin/bash
# Phase 5 Test Execution Script
# Runs all Phase 5 tests with proper environment setup

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Phase 5 Test Execution${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Change to backend directory
cd "$(dirname "$0")/backend"

# Activate virtual environment
echo -e "${YELLOW}Activating virtual environment...${NC}"
source venv/bin/activate

# Set PYTHONPATH
export PYTHONPATH="$(pwd):$PYTHONPATH"
echo -e "${GREEN}✓ PYTHONPATH set to: $PYTHONPATH${NC}"
echo ""

# Check if pytest is installed
if ! command -v pytest &> /dev/null; then
    echo -e "${RED}✗ pytest not found. Installing...${NC}"
    pip install pytest pytest-asyncio
fi

# Check for optional test dependencies
echo -e "${YELLOW}Checking test dependencies...${NC}"
if ! python -c "import pytest_cov" 2>/dev/null; then
    echo -e "${YELLOW}  Installing pytest-cov for coverage reporting...${NC}"
    pip install pytest-cov
fi

if ! python -c "import pytest_xdist" 2>/dev/null; then
    echo -e "${YELLOW}  Installing pytest-xdist for parallel execution...${NC}"
    pip install pytest-xdist
fi

echo -e "${GREEN}✓ Dependencies ready${NC}"
echo ""

# Function to run tests with proper formatting
run_test_suite() {
    local name=$1
    local path=$2
    local markers=$3
    
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}Running: $name${NC}"
    echo -e "${GREEN}========================================${NC}"
    
    if [ -z "$markers" ]; then
        pytest "$path" -v --tb=short || true
    else
        pytest "$path" -v --tb=short -m "$markers" || true
    fi
    
    echo ""
}

# Parse command line arguments
TEST_CATEGORY="${1:-all}"

case "$TEST_CATEGORY" in
    "classification")
        run_test_suite "Email Classification Tests" "tests/test_email_classification.py" ""
        ;;
    
    "pipeline")
        run_test_suite "Email-to-Task Pipeline Tests" "tests/test_email_to_task_pipeline.py" ""
        ;;
    
    "polling")
        run_test_suite "Email Polling Service Tests" "tests/test_email_polling_service.py" ""
        ;;
    
    "calendar")
        run_test_suite "Email-Calendar Intelligence Tests" "tests/test_email_calendar_intelligence.py" ""
        ;;
    
    "agents")
        run_test_suite "Agent Interaction Tests" "tests/test_agent_interactions.py" ""
        ;;
    
    "evaluation")
        echo -e "${YELLOW}⚠️  Evaluation tests require Gemini API access and will make real API calls${NC}"
        read -p "Continue? (y/N) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            run_test_suite "LLM-as-a-Judge Evaluation Tests" "tests/evaluation/test_classification_eval.py" "evaluation"
        else
            echo -e "${YELLOW}Skipping evaluation tests${NC}"
        fi
        ;;
    
    "e2e")
        run_test_suite "End-to-End Email Ingestion Tests" "tests/e2e/test_email_ingestion_e2e.py" "e2e"
        ;;
    
    "unit")
        echo -e "${GREEN}Running all unit tests...${NC}"
        run_test_suite "Unit Tests" "tests/" "unit"
        ;;
    
    "integration")
        echo -e "${GREEN}Running all integration tests...${NC}"
        run_test_suite "Integration Tests" "tests/" "integration"
        ;;
    
    "coverage")
        echo -e "${GREEN}Running all tests with coverage...${NC}"
        pytest tests/ \
            --cov=agents \
            --cov=services \
            --cov=db \
            --cov-report=html \
            --cov-report=term \
            -v \
            --tb=short \
            -m "not evaluation" || true
        
        echo ""
        echo -e "${GREEN}Coverage report generated in htmlcov/index.html${NC}"
        ;;
    
    "quick")
        echo -e "${GREEN}Running quick test suite (excluding slow tests)...${NC}"
        pytest tests/ -v --tb=short -m "not slow and not evaluation and not e2e" || true
        ;;
    
    "all")
        echo -e "${GREEN}Running complete test suite...${NC}"
        echo ""
        
        # Unit tests
        run_test_suite "Email Classification Tests" "tests/test_email_classification.py" ""
        run_test_suite "Email Parser Tests" "tests/test_email_parser.py" ""
        run_test_suite "Gmail Service Tests" "tests/test_gmail_service.py" ""
        
        # Integration tests
        run_test_suite "Email-to-Task Pipeline Tests" "tests/test_email_to_task_pipeline.py" ""
        run_test_suite "Email Polling Service Tests" "tests/test_email_polling_service.py" ""
        run_test_suite "Email-Calendar Intelligence Tests" "tests/test_email_calendar_intelligence.py" ""
        run_test_suite "Agent Interaction Tests" "tests/test_agent_interactions.py" ""
        
        # E2E tests
        run_test_suite "End-to-End Tests" "tests/e2e/test_email_ingestion_e2e.py" "e2e"
        
        # Skip evaluation tests by default
        echo -e "${YELLOW}⚠️  Skipping evaluation tests (require Gemini API). Run with 'evaluation' to include.${NC}"
        
        echo ""
        echo -e "${GREEN}========================================${NC}"
        echo -e "${GREEN}Test Suite Complete${NC}"
        echo -e "${GREEN}========================================${NC}"
        ;;
    
    *)
        echo -e "${RED}Unknown test category: $TEST_CATEGORY${NC}"
        echo ""
        echo "Usage: $0 [category]"
        echo ""
        echo "Categories:"
        echo "  all            - Run all tests (default)"
        echo "  quick          - Run quick tests (exclude slow/e2e/evaluation)"
        echo "  classification - Email classification tests"
        echo "  pipeline       - Email-to-task pipeline tests"
        echo "  polling        - Email polling service tests"
        echo "  calendar       - Email-calendar intelligence tests"
        echo "  agents         - Agent interaction tests"
        echo "  evaluation     - LLM-as-a-judge evaluation tests (requires API)"
        echo "  e2e            - End-to-end tests"
        echo "  unit           - All unit tests"
        echo "  integration    - All integration tests"
        echo "  coverage       - All tests with coverage report"
        exit 1
        ;;
esac

echo ""
echo -e "${GREEN}✓ Test execution complete${NC}"
