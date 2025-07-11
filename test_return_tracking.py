import os
import logging

# Set up logging for this module
logger = logging.getLogger(__name__)


logger.info("Creating a test script to test the return tracking endpoint...")

# Create a simple shell script to test the endpoint
with open("test_return_tracking.sh", "w") as f:
    f.write("""#!/bin/bash
echo "Testing return tracking endpoint..."

# Get the current timestamp for a unique tracking number
TIMESTAMP=$(date +%s)
TRACKING_NUMBER="TEST_${TIMESTAMP}"

# First try using 'tracking_number' parameter
echo "Testing with tracking_number parameter..."
curl -X POST -H "Content-Type: application/json" \\
    -d "{\\"tracking_number\\":\\"${TRACKING_NUMBER}\\", \\"carrier\\":\\"auto\\"}" \\
    http://localhost:5000/tickets/3/add_return_tracking

echo ""
echo "Test 1 completed"
echo ""

# Now try using 'return_tracking_number' parameter
echo "Testing with return_tracking_number parameter..."
curl -X POST -H "Content-Type: application/json" \\
    -d "{\\"return_tracking_number\\":\\"${TRACKING_NUMBER}_2\\", \\"carrier\\":\\"auto\\"}" \\
    http://localhost:5000/tickets/3/add_return_tracking

echo ""
echo "All tests completed"
""")

# Make the script executable
os.chmod("test_return_tracking.sh", 0o755)

logger.info("Created test script. Run with: ./test_return_tracking.sh")
 