#!/bin/bash

# Playwright Ticket Creation Tests Runner
# =======================================

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Ticket Creation Automated Tests${NC}"
echo -e "${GREEN}========================================${NC}"

# Check if Playwright is installed
if ! python -c "import playwright" 2>/dev/null; then
    echo -e "${RED}Error: Playwright not installed${NC}"
    echo "Install with: pip install playwright"
    exit 1
fi

# Default settings
BASE_URL=${TEST_BASE_URL:-"http://localhost:5009"}
USERNAME=${TEST_USERNAME:-"admin1"}
PASSWORD=${TEST_PASSWORD:-"123456"}
HEADED=""
TEST_FILE="tests/test_ticket_creation.py"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --headed)
            HEADED="--headed"
            shift
            ;;
        --url)
            BASE_URL="$2"
            shift 2
            ;;
        --username)
            USERNAME="$2"
            shift 2
            ;;
        --password)
            PASSWORD="$2"
            shift 2
            ;;
        --test)
            TEST_FILE="tests/test_ticket_creation.py::$2"
            shift 2
            ;;
        --all)
            TEST_FILE="tests/test_ticket_creation.py::test_all_ticket_categories"
            shift
            ;;
        --sidebar)
            TEST_FILE="tests/test_ticket_creation.py::test_sidebar_cards"
            shift
            ;;
        --help)
            echo ""
            echo "Usage: ./run_tests.sh [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --headed              Run with browser visible"
            echo "  --url URL            Set base URL (default: http://localhost:5009)"
            echo "  --username USER      Set login username (default: admin1)"
            echo "  --password PASS      Set login password (default: 123456)"
            echo "  --test TEST_NAME     Run specific test (e.g., test_pin_request_ticket)"
            echo "  --all                Run comprehensive test of all categories"
            echo "  --sidebar            Test sidebar category card clicks"
            echo "  --help               Show this help message"
            echo ""
            echo "Examples:"
            echo "  ./run_tests.sh --headed                    # Run all tests with browser visible"
            echo "  ./run_tests.sh --test test_pin_request     # Run only PIN Request test"
            echo "  ./run_tests.sh --all --headed              # Run all categories test with browser"
            echo "  ./run_tests.sh --sidebar --headed          # Test sidebar cards with browser"
            echo ""
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

# Export environment variables
export TEST_BASE_URL="$BASE_URL"
export TEST_USERNAME="$USERNAME"
export TEST_PASSWORD="$PASSWORD"

echo ""
echo -e "${YELLOW}Configuration:${NC}"
echo "  Base URL: $BASE_URL"
echo "  Username: $USERNAME"
echo "  Headed: ${HEADED:-No}"
echo "  Test: $TEST_FILE"
echo ""

# Run tests
echo -e "${GREEN}Running tests...${NC}"
echo ""

cd "$(dirname "$0")/.." || exit 1

# Build pytest arguments
PYTEST_ARGS="$TEST_FILE -v --base-url=$BASE_URL --test-username=$USERNAME --test-password=$PASSWORD"

if [ -n "$HEADED" ]; then
    PYTEST_ARGS="$PYTEST_ARGS --headed"
    export TEST_HEADLESS="false"
fi

pytest $PYTEST_ARGS

EXIT_CODE=$?

echo ""
if [ $EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}  All tests passed!${NC}"
    echo -e "${GREEN}========================================${NC}"
else
    echo -e "${RED}========================================${NC}"
    echo -e "${RED}  Some tests failed!${NC}"
    echo -e "${RED}========================================${NC}"
fi

echo ""
echo "Screenshots saved in: tests/screenshots/"

exit $EXIT_CODE
