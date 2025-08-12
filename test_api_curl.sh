#!/bin/bash

# Production API Test Script using curl
# Tests the production API at https://inventory.truelog.com.sg/

BASE_URL="https://inventory.truelog.com.sg/api/v1"
API_KEY="xAQhm3__ZH6MvRIPMIBSDRAsIa1w2Slh5uaCtc4NurM"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

# Function to make API request and check response
test_endpoint() {
    local method=$1
    local endpoint=$2
    local description=$3
    local data=$4
    
    print_info "Testing: $description"
    
    if [ -n "$data" ]; then
        response=$(curl -s -w "\n%{http_code}" -X "$method" \
            -H "Authorization: Bearer $API_KEY" \
            -H "Content-Type: application/json" \
            -d "$data" \
            "$BASE_URL$endpoint")
    else
        response=$(curl -s -w "\n%{http_code}" -X "$method" \
            -H "Authorization: Bearer $API_KEY" \
            -H "Content-Type: application/json" \
            "$BASE_URL$endpoint")
    fi
    
    # Extract HTTP status code (last line)
    http_code=$(echo "$response" | tail -n1)
    # Extract response body (all but last line)
    body=$(echo "$response" | head -n -1)
    
    if [ "$http_code" -ge 200 ] && [ "$http_code" -lt 400 ]; then
        print_success "$description - HTTP $http_code"
        
        # Pretty print JSON if it's valid JSON
        if echo "$body" | jq . >/dev/null 2>&1; then
            echo "$body" | jq -C '.' | head -20
            if [ $(echo "$body" | jq -r '.data | length // 0') -gt 0 ]; then
                echo -e "${GREEN}  → Found $(echo "$body" | jq -r '.data | length // 0') items${NC}"
            fi
        else
            echo "$body" | head -5
        fi
    else
        print_error "$description - HTTP $http_code"
        echo "$body" | head -5
    fi
    
    echo ""
}

# Main test execution
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}🚀 Production API Test Suite (curl)${NC}"
echo -e "${BLUE}========================================${NC}"
echo "Base URL: $BASE_URL"
echo "API Key: ${API_KEY:0:20}..."
echo "Started: $(date)"
echo ""

print_warning "⚠️  Testing PRODUCTION API - This will make real API calls!"
echo ""

# Test 1: Health Check (no auth required)
print_info "Testing: Health Check (no auth)"
health_response=$(curl -s -w "\n%{http_code}" "$BASE_URL/health")
health_code=$(echo "$health_response" | tail -n1)
health_body=$(echo "$health_response" | head -n -1)

if [ "$health_code" = "200" ]; then
    print_success "Health Check - HTTP $health_code"
    echo "$health_body" | jq -C '.'
else
    print_error "Health Check - HTTP $health_code"
    echo "$health_body"
fi
echo ""

# Test 2: API Key Validation
test_endpoint "GET" "/tickets?per_page=1" "API Key Validation"

# Test 3: List Tickets
test_endpoint "GET" "/tickets" "List All Tickets"

# Test 4: List Tickets with Pagination
test_endpoint "GET" "/tickets?page=1&per_page=5" "List Tickets (Paginated)"

# Test 5: List Tickets with Status Filter
test_endpoint "GET" "/tickets?status=NEW" "List NEW Tickets"

# Test 6: Get Specific Ticket (we'll use ID 1, might not exist)
test_endpoint "GET" "/tickets/1" "Get Ticket Details (ID: 1)"

# Test 7: List Users
test_endpoint "GET" "/users" "List Users"

# Test 8: Get Specific User (we'll use ID 1, might not exist)
test_endpoint "GET" "/users/1" "Get User Details (ID: 1)"

# Test 9: List Inventory
test_endpoint "GET" "/inventory" "List Inventory"

# Test 10: Get Specific Inventory Item (we'll use ID 1, might not exist)
test_endpoint "GET" "/inventory/1" "Get Inventory Details (ID: 1)"

# Test 11: Sync Tickets
test_endpoint "GET" "/sync/tickets?limit=5" "Sync Tickets"

# Test 12: Create Test Ticket
print_info "Testing: Create Test Ticket"
current_time=$(date '+%Y-%m-%d %H:%M:%S')
test_ticket_data='{
    "subject": "API Test Ticket - '"$current_time"'",
    "description": "This is a test ticket created by the curl test script. It can be safely deleted.",
    "queue_id": 1
}'

test_endpoint "POST" "/tickets" "Create Test Ticket" "$test_ticket_data"

# Test 13: Test Invalid Endpoint (should return 404)
print_info "Testing: Invalid Endpoint (should return 404)"
invalid_response=$(curl -s -w "\n%{http_code}" \
    -H "Authorization: Bearer $API_KEY" \
    "$BASE_URL/nonexistent")
invalid_code=$(echo "$invalid_response" | tail -n1)

if [ "$invalid_code" = "404" ]; then
    print_success "Invalid Endpoint - Correctly returned HTTP 404"
else
    print_warning "Invalid Endpoint - Expected 404, got HTTP $invalid_code"
fi
echo ""

# Test 14: Test Invalid API Key (should return 401)
print_info "Testing: Invalid API Key (should return 401)"
invalid_key_response=$(curl -s -w "\n%{http_code}" \
    -H "Authorization: Bearer invalid_key_12345" \
    "$BASE_URL/tickets")
invalid_key_code=$(echo "$invalid_key_response" | tail -n1)

if [ "$invalid_key_code" = "401" ]; then
    print_success "Invalid API Key - Correctly returned HTTP 401"
else
    print_warning "Invalid API Key - Expected 401, got HTTP $invalid_key_code"
fi
echo ""

# Summary
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}📊 Test Summary${NC}"
echo -e "${BLUE}========================================${NC}"
echo "Completed: $(date)"
echo ""
print_success "All curl tests completed!"
print_info "Check the output above for any errors or issues"
print_warning "Remember to clean up any test tickets created"
echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo "1. Run the Python test script for more comprehensive testing:"
echo "   python test_production_api.py"
echo "2. Check the API management dashboard for usage statistics"
echo "3. Review any test tickets created and delete if needed"