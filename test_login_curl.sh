#!/bin/bash

# Login System Test Script using curl
# Tests the login system at https://inventory.truelog.com.sg/

BASE_URL="https://inventory.truelog.com.sg"
API_BASE_URL="$BASE_URL/api/v1"

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

# Function to test API endpoint
test_api_endpoint() {
    local method=$1
    local endpoint=$2
    local description=$3
    local data=$4
    local expected_status=$5
    
    print_info "Testing: $description"
    
    if [ -n "$data" ]; then
        response=$(curl -s -w "\n%{http_code}" -X "$method" \
            -H "Content-Type: application/json" \
            -d "$data" \
            "$API_BASE_URL$endpoint")
    else
        response=$(curl -s -w "\n%{http_code}" -X "$method" \
            -H "Content-Type: application/json" \
            "$API_BASE_URL$endpoint")
    fi
    
    # Extract HTTP status code (last line)
    http_code=$(echo "$response" | tail -n1)
    # Extract response body (all but last line)
    body=$(echo "$response" | sed '$d')
    
    # Check if we got expected status code
    if [ "$http_code" = "$expected_status" ]; then
        print_success "$description - HTTP $http_code (Expected)"
        
        # Pretty print JSON if it's valid JSON
        if echo "$body" | jq . >/dev/null 2>&1; then
            echo "$body" | jq -C '.' | head -10
        else
            echo "$body" | head -3
        fi
    else
        print_error "$description - HTTP $http_code (Expected $expected_status)"
        echo "$body" | head -3
    fi
    
    echo ""
    return $http_code
}

# Function to test with authorization header
test_api_with_auth() {
    local method=$1
    local endpoint=$2
    local description=$3
    local token=$4
    local expected_status=$5
    
    print_info "Testing: $description"
    
    response=$(curl -s -w "\n%{http_code}" -X "$method" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer $token" \
        "$API_BASE_URL$endpoint")
    
    # Extract HTTP status code (last line)
    http_code=$(echo "$response" | tail -n1)
    # Extract response body (all but last line)
    body=$(echo "$response" | sed '$d')
    
    if [ "$http_code" = "$expected_status" ]; then
        print_success "$description - HTTP $http_code"
        
        # Pretty print JSON if it's valid JSON
        if echo "$body" | jq . >/dev/null 2>&1; then
            echo "$body" | jq -C '.' | head -10
        else
            echo "$body" | head -3
        fi
    else
        print_error "$description - HTTP $http_code (Expected $expected_status)"
        echo "$body" | head -3
    fi
    
    echo ""
    echo "$body"  # Return body for token extraction
}

# Main test execution
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}🔐 Login System Test Suite (curl)${NC}"
echo -e "${BLUE}========================================${NC}"
echo "Base URL: $BASE_URL"
echo "API URL: $API_BASE_URL"
echo "Started: $(date)"
echo ""

print_warning "⚠️  Testing PRODUCTION login system!"
echo ""

# Test 1: Check if login page is accessible
print_info "Testing: Web Login Page Access"
login_page_response=$(curl -s -w "%{http_code}" "$BASE_URL/login")
login_page_code=${login_page_response: -3}

if [ "$login_page_code" = "200" ]; then
    print_success "Web Login Page - HTTP 200 (Accessible)"
else
    print_error "Web Login Page - HTTP $login_page_code"
fi
echo ""

# Test 2: API Login with Invalid Credentials
invalid_login_data='{
    "username": "invalid_user_12345",
    "password": "invalid_password_12345"
}'

test_api_endpoint "POST" "/auth/login" "API Login (Invalid Credentials)" "$invalid_login_data" "401"

# Test 3: API Login with Missing Data
missing_data='{
    "username": "test"
}'

test_api_endpoint "POST" "/auth/login" "API Login (Missing Password)" "$missing_data" "400"

# Test 4: API Login with Empty Body
test_api_endpoint "POST" "/auth/login" "API Login (Empty Body)" "" "400"

# Test 5: Get credentials for valid login test
echo -e "${YELLOW}To test valid login, please provide credentials:${NC}"
echo -n "Username: "
read -r username
if [ -n "$username" ]; then
    echo -n "Password: "
    read -rs password
    echo ""
    
    # Test valid login
    valid_login_data="{
        \"username\": \"$username\",
        \"password\": \"$password\"
    }"
    
    print_info "Testing: API Login (Valid Credentials)"
    login_response=$(curl -s -w "\n%{http_code}" -X "POST" \
        -H "Content-Type: application/json" \
        -d "$valid_login_data" \
        "$API_BASE_URL/auth/login")
    
    login_code=$(echo "$login_response" | tail -n1)
    login_body=$(echo "$login_response" | sed '$d')
    
    if [ "$login_code" = "200" ]; then
        print_success "API Login (Valid Credentials) - HTTP 200"
        
        # Extract JWT token
        if echo "$login_body" | jq . >/dev/null 2>&1; then
            jwt_token=$(echo "$login_body" | jq -r '.data.token // empty')
            user_info=$(echo "$login_body" | jq -r '.data.username // .data.email // "Unknown"')
            
            if [ -n "$jwt_token" ] && [ "$jwt_token" != "null" ]; then
                print_success "JWT Token extracted for user: $user_info"
                echo "Token: ${jwt_token:0:50}..."
                echo ""
                
                # Test token verification
                test_api_with_auth "GET" "/auth/verify" "Token Verification" "$jwt_token" "200"
                
                # Test user permissions
                test_api_with_auth "GET" "/auth/permissions" "User Permissions" "$jwt_token" "200"
                
                # Test user profile
                test_api_with_auth "GET" "/auth/profile" "User Profile" "$jwt_token" "200"
                
                # Test token refresh
                test_api_with_auth "POST" "/auth/refresh" "Token Refresh" "$jwt_token" "200"
                
                # Test protected endpoint access
                print_info "Testing: Protected API Access (with token)"
                protected_response=$(curl -s -w "\n%{http_code}" -X "GET" \
                    -H "Authorization: Bearer $jwt_token" \
                    "$API_BASE_URL/tickets?per_page=1")
                
                protected_code=$(echo "$protected_response" | tail -n1)
                protected_body=$(echo "$protected_response" | sed '$d')
                
                if [ "$protected_code" = "200" ]; then
                    print_success "Protected API Access - HTTP 200"
                    echo "$protected_body" | jq -C '.' | head -5
                else
                    print_error "Protected API Access - HTTP $protected_code"
                    echo "$protected_body" | head -3
                fi
                echo ""
                
                # Test protected endpoint without token
                print_info "Testing: Protected API Access (without token)"
                no_token_response=$(curl -s -w "\n%{http_code}" -X "GET" \
                    "$API_BASE_URL/tickets")
                
                no_token_code=$(echo "$no_token_response" | tail -n1)
                
                if [ "$no_token_code" = "401" ]; then
                    print_success "Protected API Access (no token) - HTTP 401 (Correctly rejected)"
                else
                    print_warning "Protected API Access (no token) - HTTP $no_token_code (Expected 401)"
                fi
                echo ""
                
            else
                print_error "No JWT token found in login response"
                echo "$login_body" | jq -C '.'
            fi
        else
            print_error "Invalid JSON response from login"
            echo "$login_body"
        fi
    else
        print_error "API Login (Valid Credentials) - HTTP $login_code"
        echo "$login_body" | head -3
    fi
    echo ""
else
    print_warning "No credentials provided - skipping valid login tests"
    echo ""
fi

# Test 6: Test invalid token
print_info "Testing: Invalid Token"
invalid_token_response=$(curl -s -w "\n%{http_code}" -X "GET" \
    -H "Authorization: Bearer invalid_token_12345" \
    "$API_BASE_URL/auth/verify")

invalid_token_code=$(echo "$invalid_token_response" | tail -n1)

if [ "$invalid_token_code" = "401" ]; then
    print_success "Invalid Token - HTTP 401 (Correctly rejected)"
else
    print_warning "Invalid Token - HTTP $invalid_token_code (Expected 401)"
fi
echo ""

# Test 7: Test malformed authorization header
print_info "Testing: Malformed Authorization Header"
malformed_auth_response=$(curl -s -w "\n%{http_code}" -X "GET" \
    -H "Authorization: InvalidFormat token123" \
    "$API_BASE_URL/auth/verify")

malformed_auth_code=$(echo "$malformed_auth_response" | tail -n1)

if [ "$malformed_auth_code" = "401" ]; then
    print_success "Malformed Auth Header - HTTP 401 (Correctly rejected)"
else
    print_warning "Malformed Auth Header - HTTP $malformed_auth_code (Expected 401)"
fi
echo ""

# Summary
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}📊 Login Test Summary${NC}"
echo -e "${BLUE}========================================${NC}"
echo "Completed: $(date)"
echo ""
print_success "All login system tests completed!"
print_info "Check the output above for any errors or issues"
echo ""
echo -e "${YELLOW}Key Points:${NC}"
echo "• Web login page should be accessible (HTTP 200)"
echo "• Invalid credentials should be rejected (HTTP 401)"
echo "• Valid credentials should return JWT token (HTTP 200)"
echo "• JWT token should work for protected endpoints"
echo "• Invalid/missing tokens should be rejected (HTTP 401)"
echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo "1. Run the Python test script for more comprehensive testing:"
echo "   python test_login_system.py"
echo "2. Test the web login form manually in a browser"
echo "3. Check server logs for any authentication errors"