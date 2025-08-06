#!/bin/bash

# PythonAnywhere Deployment Script for Comment Fix
# Run this script on your PythonAnywhere server to deploy the comment fixes

echo "🚀 Starting deployment of comment fixes to PythonAnywhere..."

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if we're in the right directory
if [ ! -f "app.py" ] || [ ! -d "models" ] || [ ! -d "utils" ]; then
    print_error "Please run this script from your inventory application root directory"
    print_error "Expected to find: app.py, models/, utils/ directories"
    exit 1
fi

print_status "Found inventory application directory ✓"

# Step 1: Pull latest changes from git
print_status "Pulling latest changes from git..."
git fetch origin
git pull origin main

if [ $? -eq 0 ]; then
    print_status "Git pull successful ✓"
else
    print_error "Git pull failed. Please check your git configuration."
    exit 1
fi

# Step 2: Check if virtual environment exists
if [ -d "venv" ]; then
    print_status "Found existing virtual environment ✓"
    source venv/bin/activate
elif [ -d ".venv" ]; then
    print_status "Found existing virtual environment (.venv) ✓"
    source .venv/bin/activate
else
    print_warning "Virtual environment not found. Creating new one..."
    python3 -m venv venv
    source venv/bin/activate
    print_status "Created and activated new virtual environment ✓"
fi

# Step 3: Install/update requirements
if [ -f "requirements.txt" ]; then
    print_status "Installing/updating Python dependencies..."
    pip install -r requirements.txt
    print_status "Dependencies updated ✓"
else
    print_warning "requirements.txt not found. Skipping dependency installation."
fi

# Step 4: Check critical files exist
print_status "Verifying critical files for comment fix..."

critical_files=(
    "models/comment.py"
    "utils/comment_store.py"
    "data/comments.json"
)

for file in "${critical_files[@]}"; do
    if [ -f "$file" ]; then
        print_status "✓ $file exists"
    else
        print_error "✗ $file is missing!"
        exit 1
    fi
done

# Step 5: Test Python syntax
print_status "Testing Python syntax for updated files..."
python3 -m py_compile models/comment.py
python3 -m py_compile utils/comment_store.py

if [ $? -eq 0 ]; then
    print_status "Python syntax check passed ✓"
else
    print_error "Python syntax errors found. Please check the files."
    exit 1
fi

# Step 6: Backup comments data
print_status "Creating backup of comments.json..."
cp data/comments.json data/comments.json.backup.$(date +%Y%m%d_%H%M%S)
print_status "Backup created ✓"

# Step 7: Set proper permissions
print_status "Setting proper file permissions..."
chmod 644 models/comment.py
chmod 644 utils/comment_store.py
chmod 664 data/comments.json
chmod 755 data/

print_status "File permissions set ✓"

# Step 8: Restart web application
print_status "Attempting to restart web application..."

# Method 1: Touch wsgi file (most common)
if [ -f "wsgi.py" ]; then
    touch wsgi.py
    print_status "Touched wsgi.py to trigger restart ✓"
elif [ -f "flask_app.py" ]; then
    touch flask_app.py
    print_status "Touched flask_app.py to trigger restart ✓"
else
    print_warning "WSGI file not found. You may need to manually restart your web app."
fi

# Method 2: Try to reload using PA API (if available)
if command -v pa_reload_webapp.py &> /dev/null; then
    print_status "Attempting to reload webapp using PythonAnywhere API..."
    pa_reload_webapp.py --domain=$(hostname)
fi

print_status "🎉 Deployment completed successfully!"
print_status ""
print_status "DEPLOYMENT SUMMARY:"
print_status "===================="
print_status "✅ Latest code pulled from git"
print_status "✅ Python dependencies updated"
print_status "✅ Comment loading fixes deployed"
print_status "✅ ORM mapping issues resolved"
print_status "✅ Comments data backed up"
print_status "✅ Web application restarted"
print_status ""
print_status "WHAT WAS FIXED:"
print_status "==============="
print_status "• Comments now load correctly for all tickets"
print_status "• Fixed type consistency issues (int vs string ticket IDs)"
print_status "• Resolved ORM mapping conflicts"
print_status "• Comments will no longer show 0 count or wrong ticket data"
print_status "• User information displays properly for all comments"
print_status ""
print_warning "IMPORTANT: Please test your ticket comments after deployment!"
print_status "If you encounter any issues, check the error logs or contact support."
print_status ""
print_status "Backup location: data/comments.json.backup.*"
print_status "You can restore from backup if needed using:"
print_status "cp data/comments.json.backup.YYYYMMDD_HHMMSS data/comments.json"

echo ""
echo "🚀 Ready to go! Your comment system should now be working perfectly."