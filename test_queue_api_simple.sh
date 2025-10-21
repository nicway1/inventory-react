#!/bin/bash
# Simple API test script for queue endpoints
# Tests basic connectivity and endpoint existence

BASE_URL="https://inventory.truelog.com.sg"

echo "======================================================================"
echo "  Queue API Quick Test"
echo "======================================================================"
echo ""
echo "Base URL: $BASE_URL"
echo ""

# Get API key from user
read -p "Enter your API key: " API_KEY

if [ -z "$API_KEY" ]; then
    echo "❌ ERROR: API key is required"
    exit 1
fi

echo ""
echo "======================================================================"
echo "  Test 1: GET /api/v1/queues"
echo "======================================================================"
curl -s -w "\nHTTP Status: %{http_code}\n" \
     -H "Authorization: Bearer $API_KEY" \
     -H "Content-Type: application/json" \
     "$BASE_URL/api/v1/queues" | jq '.' 2>/dev/null || curl -s -w "\nHTTP Status: %{http_code}\n" \
     -H "Authorization: Bearer $API_KEY" \
     -H "Content-Type: application/json" \
     "$BASE_URL/api/v1/queues"

echo ""
echo ""
echo "======================================================================"
echo "  Test 2: GET /api/v1/tickets (first 5, check for queue fields)"
echo "======================================================================"
curl -s -w "\nHTTP Status: %{http_code}\n" \
     -H "Authorization: Bearer $API_KEY" \
     -H "Content-Type: application/json" \
     "$BASE_URL/api/v1/tickets?per_page=5" | jq '.' 2>/dev/null || curl -s -w "\nHTTP Status: %{http_code}\n" \
     -H "Authorization: Bearer $API_KEY" \
     -H "Content-Type: application/json" \
     "$BASE_URL/api/v1/tickets?per_page=5"

echo ""
echo ""
echo "======================================================================"
echo "  Test 3: GET /api/v1/tickets with queue filter (queue_id=1)"
echo "======================================================================"
curl -s -w "\nHTTP Status: %{http_code}\n" \
     -H "Authorization: Bearer $API_KEY" \
     -H "Content-Type: application/json" \
     "$BASE_URL/api/v1/tickets?queue_id=1&per_page=5" | jq '.' 2>/dev/null || curl -s -w "\nHTTP Status: %{http_code}\n" \
     -H "Authorization: Bearer $API_KEY" \
     -H "Content-Type: application/json" \
     "$BASE_URL/api/v1/tickets?queue_id=1&per_page=5"

echo ""
echo ""
echo "======================================================================"
echo "  Test 4: GET /api/v1/sync/tickets (check new fields)"
echo "======================================================================"
curl -s -w "\nHTTP Status: %{http_code}\n" \
     -H "Authorization: Bearer $API_KEY" \
     -H "Content-Type: application/json" \
     "$BASE_URL/api/v1/sync/tickets?limit=3" | jq '.' 2>/dev/null || curl -s -w "\nHTTP Status: %{http_code}\n" \
     -H "Authorization: Bearer $API_KEY" \
     -H "Content-Type: application/json" \
     "$BASE_URL/api/v1/sync/tickets?limit=3"

echo ""
echo ""
echo "======================================================================"
echo "  Testing Complete"
echo "======================================================================"
echo ""
echo "Expected Results:"
echo "  ✅ All tests should return HTTP Status: 200"
echo "  ✅ /queues should return a list of queues"
echo "  ✅ Tickets should include 'queue_id' and 'queue_name' fields"
echo "  ✅ Sync tickets should include queue_name, category, customer_name, assigned_to_name"
echo ""
