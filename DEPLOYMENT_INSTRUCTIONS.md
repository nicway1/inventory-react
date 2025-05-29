# PythonAnywhere Deployment Instructions

## Quick Fix for Current Issues

If you're getting errors on PythonAnywhere after the latest updates, follow these steps:

### 1. Update Your Code

In a PythonAnywhere Bash console:

```bash
# Navigate to your app directory
cd /home/yourusername/your-app-directory

# Pull the latest changes
git pull origin main
```

### 2. Run the Deployment Fix Script

```bash
# Make the script executable
chmod +x deploy_fix.py

# Run the deployment fix script
python3 deploy_fix.py
```

### 3. Restart Your Web App

1. Go to your PythonAnywhere **Web** tab
2. Click **Reload** for your web app
3. Wait for the reload to complete

### 4. Test the Application

Visit your application URL and check that:
- The dashboard loads without errors
- The System Configuration page shows Firecrawl API keys
- The Shipments section displays both outbound and inbound tracking

## What the Script Fixes

The `deploy_fix.py` script automatically:

1. ✅ Adds the missing `return_carrier` column to the tickets table
2. ✅ Creates the `firecrawl_keys` table if it doesn't exist
3. ✅ Adds any missing columns to existing tables
4. ✅ Sets up a default Firecrawl API key if none exists
5. ✅ Validates essential table structures

## Manual Database Fixes (Alternative)

If the script doesn't work, you can manually run these SQL commands:

### Add return_carrier column:
```sql
ALTER TABLE tickets ADD COLUMN return_carrier VARCHAR(50) DEFAULT 'singpost';
```

### Create firecrawl_keys table:
```sql
CREATE TABLE firecrawl_keys (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    api_key VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255),
    is_active BOOLEAN DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP,
    usage_count INTEGER DEFAULT 0,
    limit_count INTEGER DEFAULT 500,
    is_primary BOOLEAN DEFAULT 0,
    last_used TIMESTAMP,
    notes TEXT
);
```

## Environment Variables

Make sure these environment variables are set in your PythonAnywhere environment:

- `FIRECRAWL_API_KEY` - Your Firecrawl API key
- `DATABASE_URL` - Database connection string (optional for SQLite)

## Troubleshooting

### Still Getting Errors?

1. Check the error log in PythonAnywhere:
   - Web tab → Your domain → Log files → Error log

2. Run the deployment script again:
   ```bash
   python3 deploy_fix.py
   ```

3. Restart your web app again

### Common Issues:

- **"Address already in use"**: Normal port conflict, the app will find another port
- **"no such column"**: Run the deployment fix script
- **"no such table"**: Database needs to be initialized - contact support

### Need Help?

If you continue to have issues:
1. Check the error logs for specific error messages
2. Run the deployment script with verbose output
3. Verify all environment variables are set correctly

## Recent Updates (Latest Deployment)

- ✅ Dual outbound/inbound tracking display on homepage
- ✅ Multiple Firecrawl API key management
- ✅ Enhanced shipment status tracking
- ✅ Improved database schema
- ✅ Better error handling for missing database columns 