# Bug Report Screenshot Migration Instructions

This document explains how to add the `screenshot_path` column to the `bug_reports` table in your database.

## The Issue

The bug report screenshot feature requires a new `screenshot_path` column in the `bug_reports` table. This migration needs to be run on your production database (PythonAnywhere MySQL).

## Migration Options

### Option 1: Web Interface (Recommended for PythonAnywhere)

1. Log in to your application as a super admin
2. Navigate to: `https://your-domain.com/admin/run-migration/add-screenshot-to-bugs`
3. The migration will run automatically and show a success message
4. Reload your PythonAnywhere web app from the Web tab

### Option 2: PythonAnywhere Bash Console

1. Open a Bash console on PythonAnywhere
2. Navigate to your project directory:
   ```bash
   cd ~/inventory
   ```
3. Run the migration script:
   ```bash
   python3 migrate_screenshot_pythonanywhere.py
   ```
4. Reload your web app from the PythonAnywhere Web tab

### Option 3: Local SQLite (Already Done)

The local SQLite database already has the migration applied via:
```bash
python3 add_screenshot_to_bug_reports.py
```

## Verification

After running the migration, you can verify it worked by:

1. Going to Development > Bug Reports
2. Creating a new bug report
3. You should see a "Screenshot" upload field
4. Upload a screenshot and submit
5. View the bug report - the screenshot should be displayed

## What the Migration Does

The migration adds a single column to the `bug_reports` table:
- Column name: `screenshot_path`
- Type: VARCHAR(500)
- Nullable: YES
- Purpose: Stores the file path to uploaded bug screenshots

## Troubleshooting

If you see an error like "Unknown column 'bug_reports.screenshot_path'":
- The migration hasn't been run on your production database yet
- Use Option 1 or Option 2 above to run the migration
- Make sure to reload your web app after the migration

If the migration says the column already exists:
- The migration has already been run successfully
- No further action needed
- If you're still seeing errors, try reloading your web app

## Files Created

- `add_screenshot_to_bug_reports.py` - SQLite migration (local)
- `add_screenshot_to_bug_reports_mysql.py` - MySQL migration (standalone)
- `migrate_screenshot_universal.py` - Universal migration using existing DB connection
- `migrate_screenshot_pythonanywhere.py` - PythonAnywhere-specific migration script
- Admin route: `/admin/run-migration/add-screenshot-to-bugs` - Web-based migration
