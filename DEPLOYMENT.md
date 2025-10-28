# Deployment to PythonAnywhere

This guide covers deploying the inventory management system to PythonAnywhere.

## Pre-deployment Checklist

1. ✅ All code changes committed to git
2. ✅ Database migrations ready in `migrations/` folder
3. ✅ Environment variables documented
4. ✅ SQLite database compatible

## Deployment Steps

### 1. Upload Code to PythonAnywhere

```bash
# On PythonAnywhere console
cd ~
git clone <your-repo-url> inventory
cd inventory
```

Or if updating existing deployment:
```bash
cd ~/inventory
git pull origin main
```

### 2. Set Up Virtual Environment

```bash
cd ~/inventory
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Run Database Migrations

```bash
python run_migrations.py
```

This will automatically apply all pending migrations including:
- `add_feature_case_progress.sql` - Adds case progress tracking
- `create_feature_test_cases_table.sql` - Creates feature test cases table

### 4. Configure Environment Variables

Create a `.env` file in the inventory directory:

```bash
nano .env
```

Add your configuration:
```
# Microsoft 365 OAuth2 Configuration
MS_CLIENT_ID=your-client-id
MS_CLIENT_SECRET=your-client-secret
MS_TENANT_ID=your-tenant-id
MS_FROM_EMAIL=support@yourdomain.com
USE_OAUTH2_EMAIL=true
```

### 5. Configure WSGI File

In PythonAnywhere web dashboard:
1. Go to Web tab
2. Edit WSGI configuration file
3. Update path to your application:

```python
import sys
import os

# Add your project directory to the sys.path
project_home = '/home/yourusername/inventory'
if project_home not in sys.path:
    sys.path.insert(0, project_home)

# Activate virtual environment
activate_this = os.path.join(project_home, 'venv/bin/activate_this.py')
with open(activate_this) as f:
    exec(f.read(), {'__file__': activate_this})

# Import Flask app
from app import app as application
```

### 6. Configure Static Files

In PythonAnywhere web dashboard, add static files mappings:
- URL: `/static/`
- Directory: `/home/yourusername/inventory/static/`

### 7. Set Working Directory

In PythonAnywhere web dashboard:
- Set working directory to: `/home/yourusername/inventory/`

### 8. Reload Web App

Click the green "Reload" button in PythonAnywhere web dashboard.

## Post-Deployment

### Verify Deployment

1. Visit your PythonAnywhere URL
2. Test login functionality
3. Verify features page loads without errors
4. Check that Case Progress is visible
5. Test @mentions in comments
6. Verify email notifications work

### Common Issues

#### Database Errors
If you see "Unknown column 'case_progress'" error:
```bash
cd ~/inventory
source venv/bin/activate
python run_migrations.py
```

#### Permission Errors
Make sure database file is writable:
```bash
chmod 664 inventory.db
```

#### Module Not Found Errors
Reinstall dependencies:
```bash
source venv/bin/activate
pip install --upgrade -r requirements.txt
```

## Maintenance

### Running New Migrations

When you add new migrations:
1. Upload new migration file to `migrations/` folder
2. Run: `python run_migrations.py`
3. Reload web app

### Backing Up Database

```bash
cp inventory.db inventory.db.backup.$(date +%Y%m%d)
```

### Viewing Logs

Check PythonAnywhere error log in the Web tab for debugging.

## Features Deployed

All bug tracking features have been replicated for features:
- ✅ Case Progress tracking (0-100%)
- ✅ "Case Owner" terminology (renamed from "Assignee")
- ✅ Messenger-style comments with @mentions
- ✅ Email notifications for mentions
- ✅ Quick Actions (restricted to case owner)
- ✅ Status change modal
- ✅ Delete feature functionality
- ✅ Test case management (routes ready, templates needed)

## Support

For issues during deployment, check:
1. PythonAnywhere error logs
2. `app_output.log` in your directory
3. Browser console for JavaScript errors
