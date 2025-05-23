#!/bin/bash
echo "Testing return tracking endpoint..."

# Get the current timestamp for a unique tracking number
TIMESTAMP=$(date +%s)
TRACKING_NUMBER="TEST_${TIMESTAMP}"

# First try using 'tracking_number' parameter
echo "Testing with tracking_number parameter..."
curl -X POST -H "Content-Type: application/json" \
    -d "{\"tracking_number\":\"${TRACKING_NUMBER}\", \"carrier\":\"auto\"}" \
    http://localhost:5000/tickets/3/add_return_tracking

echo ""
echo "Test 1 completed"
echo ""

# Now try using 'return_tracking_number' parameter
echo "Testing with return_tracking_number parameter..."
curl -X POST -H "Content-Type: application/json" \
    -d "{\"return_tracking_number\":\"${TRACKING_NUMBER}_2\", \"carrier\":\"auto\"}" \
    http://localhost:5000/tickets/3/add_return_tracking

echo ""
echo "All tests completed"
