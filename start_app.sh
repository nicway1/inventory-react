#!/bin/bash

# Set Microsoft 365 OAuth2 environment variables
export MS_CLIENT_ID="b5d3d9b5-5ec0-4bb3-a127-5bce2c8e632d"
export MS_CLIENT_SECRET="kya8Q~XzoQ_tNWojqhph5woMH1VdOPxcemELvaOW"
export MS_TENANT_ID="fdc52ee0-3b36-4a9b-ad4f-216bd2d20c4e"
export MS_FROM_EMAIL="support@truelog.com.sg"
export USE_OAUTH2_EMAIL="true"

# Kill any existing processes
pkill -f "python.*app.py" || true

# Start the Flask application
echo "Starting Flask application with Microsoft 365 OAuth2..."
python3 app.py 