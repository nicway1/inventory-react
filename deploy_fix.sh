#!/bin/bash
# Script to deploy the fix_shipping_tracking_columns.py script to production
# and execute it to fix the missing columns

# Configuration - EDIT THESE VALUES
REMOTE_USER="nicway2"
REMOTE_HOST="your-server-hostname-or-ip"  # Replace with actual hostname or IP
REMOTE_PATH="/home/nicway2/inventory"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}===== Deploying Shipping Tracking Column Fix =====${NC}"

# Check if fix script exists
if [ ! -f "fix_shipping_tracking_columns.py" ]; then
    echo -e "${RED}Error: fix_shipping_tracking_columns.py not found in current directory${NC}"
    exit 1
fi

# Confirm before proceeding
echo -e "${YELLOW}This script will:${NC}"
echo "1. Copy fix_shipping_tracking_columns.py to ${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_PATH}"
echo "2. Connect to the server and run the script to fix the database"
echo 
read -p "Continue? (y/n): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}Deployment canceled.${NC}"
    exit 0
fi

# Copy the script to the server
echo -e "${YELLOW}Copying fix script to server...${NC}"
scp fix_shipping_tracking_columns.py ${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_PATH}/

if [ $? -ne 0 ]; then
    echo -e "${RED}Error: Failed to copy the script to the server.${NC}"
    echo "Please check your SSH connection and server details."
    exit 1
fi

echo -e "${GREEN}Fix script copied successfully to server.${NC}"

# SSH to the server and run the script
echo -e "${YELLOW}Connecting to server and running the fix script...${NC}"
ssh ${REMOTE_USER}@${REMOTE_HOST} "cd ${REMOTE_PATH} && python3 fix_shipping_tracking_columns.py"

if [ $? -ne 0 ]; then
    echo -e "${RED}Error: Failed to run the script on the server.${NC}"
    exit 1
fi

echo -e "${GREEN}Deployment completed successfully!${NC}"
echo "The database should now have the missing columns added."
echo
echo -e "${YELLOW}Next steps:${NC}"
echo "1. Restart your Flask application to apply the changes"
echo "   (ssh ${REMOTE_USER}@${REMOTE_HOST} 'cd ${REMOTE_PATH} && ./restart_app.sh')"
echo "2. Verify the application works correctly"
echo

exit 0 