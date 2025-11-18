#!/bin/bash
# Quick test runner script for Art Kiosk tests

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}Art Kiosk Test Runner${NC}"
echo "======================================"

# Check if venv exists
if [ ! -d "venv" ]; then
    echo -e "${RED}Error: Virtual environment not found${NC}"
    echo "Please run: python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt"
    exit 1
fi

# Activate virtual environment
source venv/bin/activate

# Check if server is running
echo -e "${YELLOW}Checking if kiosk server is running...${NC}"
if ! curl -s http://localhost/api/settings > /dev/null 2>&1; then
    echo -e "${RED}Error: Kiosk server is not running on http://localhost${NC}"
    echo "Please start the server first:"
    echo "  cd .."
    echo "  sudo ./venv/bin/python app.py"
    exit 1
fi
echo -e "${GREEN}✓ Server is running${NC}"

# Parse command line arguments
TEST_TYPE="${1:-all}"

case "$TEST_TYPE" in
    "unit")
        echo -e "${YELLOW}Running unit tests only...${NC}"
        pytest -m unit -v
        ;;
    "integration")
        echo -e "${YELLOW}Running integration tests...${NC}"
        pytest -m integration -v
        ;;
    "e2e")
        echo -e "${YELLOW}Running end-to-end tests...${NC}"
        pytest -m e2e -v
        ;;
    "fast")
        echo -e "${YELLOW}Running fast tests (unit + integration)...${NC}"
        pytest -m "not slow and not e2e" -v
        ;;
    "day")
        echo -e "${YELLOW}Running day scheduling tests...${NC}"
        pytest -m day_scheduling -v
        ;;
    "screenshot")
        echo -e "${YELLOW}Running screenshot tests...${NC}"
        pytest -m screenshot -v
        ;;
    "all")
        echo -e "${YELLOW}Running all tests...${NC}"
        pytest -v
        ;;
    "headed")
        echo -e "${YELLOW}Running e2e tests with visible browser...${NC}"
        pytest -m e2e --headed --slowmo 500 -v
        ;;
    *)
        echo -e "${RED}Unknown test type: $TEST_TYPE${NC}"
        echo "Usage: ./run_tests.sh [unit|integration|e2e|fast|day|screenshot|all|headed]"
        exit 1
        ;;
esac

echo -e "${GREEN}======================================"
echo -e "Tests completed!${NC}"
