# PythonAnywhere MySQL Migration Guide

This guide walks you through setting up MySQL on PythonAnywhere and migrating your data.

## Step 1: Create MySQL Database on PythonAnywhere

1. Log in to your PythonAnywhere account
2. Go to the **Databases** tab
3. Under "MySQL", you'll see your MySQL server info:
   - **Host**: `yourusername.mysql.pythonanywhere-services.com`
   - **Username**: `yourusername`
4. Set a MySQL password (click "Set password" if you haven't already)
5. Create a new database:
   - In the "Create a database" field, enter: `inventory`
   - Click "Create"
   - Your database will be named: `yourusername$inventory`

## Step 2: Note Your Connection Details

Your MySQL connection string format:
```
mysql+pymysql://yourusername:yourpassword@yourusername.mysql.pythonanywhere-services.com/yourusername$inventory
```

Example (replace with your actual values):
```
mysql+pymysql://myuser:MyP@ssw0rd@myuser.mysql.pythonanywhere-services.com/myuser$inventory
```

## Step 3: Prepare for Migration

### Option A: Migrate from Local Machine

1. Export your current data locally by running:
   ```bash
   python migrate_to_mysql.py --export-only
   ```
   This creates `data_export.json` as a backup.

2. Set up the MySQL URL in your `.env` file:
   ```
   MYSQL_URL=mysql+pymysql://yourusername:yourpassword@yourusername.mysql.pythonanywhere-services.com/yourusername$inventory
   ```

3. Run the full migration:
   ```bash
   python migrate_to_mysql.py
   ```

### Option B: Migrate on PythonAnywhere (Recommended)

1. Upload your code to PythonAnywhere (via git or file upload)

2. Open a **Bash console** on PythonAnywhere

3. Install dependencies:
   ```bash
   cd ~/inventory
   pip install --user -r requirements.txt
   ```

4. Create a `.env` file with both database URLs:
   ```bash
   nano .env
   ```

   Add these lines:
   ```
   # Source database (your current SQLite or PostgreSQL)
   DATABASE_URL=sqlite:///inventory.db

   # Target MySQL database
   MYSQL_URL=mysql+pymysql://yourusername:yourpassword@yourusername.mysql.pythonanywhere-services.com/yourusername$inventory
   ```

5. If migrating from SQLite, upload your `inventory.db` file to PythonAnywhere

6. Run the migration:
   ```bash
   python migrate_to_mysql.py
   ```

## Step 4: Update Your Application Configuration

After successful migration, update your `.env` file to use MySQL as the primary database:

```
DATABASE_URL=mysql+pymysql://yourusername:yourpassword@yourusername.mysql.pythonanywhere-services.com/yourusername$inventory
```

Remove or comment out the old `DATABASE_URL`.

## Step 5: Configure Your Web App on PythonAnywhere

1. Go to the **Web** tab on PythonAnywhere

2. If you don't have a web app yet, click "Add a new web app":
   - Choose "Flask"
   - Select Python 3.10 (or your preferred version)

3. Set the **Source code** directory:
   ```
   /home/yourusername/inventory
   ```

4. Set the **Working directory**:
   ```
   /home/yourusername/inventory
   ```

5. Edit the **WSGI configuration file** (click the link):
   ```python
   import sys
   import os

   # Add your project directory to the path
   project_home = '/home/yourusername/inventory'
   if project_home not in sys.path:
       sys.path.insert(0, project_home)

   # Load environment variables
   from dotenv import load_dotenv
   load_dotenv(os.path.join(project_home, '.env'))

   # Import your Flask app
   from app import app as application
   ```

6. Set environment variables (optional but recommended):
   - Go to the **Web** tab
   - Find "Environment variables" or add them to your WSGI file

7. Click **Reload** to apply changes

## Step 6: Verify the Migration

1. Open a Bash console on PythonAnywhere
2. Run the verification:
   ```bash
   cd ~/inventory
   python migrate_to_mysql.py --verify
   ```

3. This compares row counts between source and MySQL to ensure all data migrated.

## Troubleshooting

### Connection Timeout Errors
PythonAnywhere has a 5-minute MySQL connection timeout. The code already handles this with `pool_recycle=280`, but if you see timeout errors:
- Ensure you're using the updated `database.py`
- Check that `pool_recycle` is set

### "Access denied" Error
- Double-check your username and password
- Ensure the database name includes your username prefix: `yourusername$inventory`
- Password should not contain special characters that need URL encoding, or encode them

### "Table already exists" Error
If you need to re-run the migration:
```sql
-- In PythonAnywhere MySQL console, drop all tables first:
DROP DATABASE yourusername$inventory;
CREATE DATABASE yourusername$inventory;
```

### Large Data Migration
For very large databases, you may need to increase the batch size or run the migration in chunks. Edit `migrate_to_mysql.py` and adjust `batch_size` in the `migrate_table` function.

### Character Encoding Issues
If you see encoding errors, ensure your MySQL database uses UTF-8:
```sql
ALTER DATABASE yourusername$inventory CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

## MySQL vs SQLite/PostgreSQL Differences

Some things to be aware of:

1. **Case sensitivity**: MySQL table/column names may be case-insensitive on some systems
2. **Text length**: MySQL `TEXT` columns have a 64KB limit; `LONGTEXT` is used for larger content
3. **Boolean**: MySQL uses TINYINT(1) for booleans
4. **Datetime precision**: MySQL < 5.6.4 doesn't support microseconds

The SQLAlchemy ORM handles most of these differences automatically.

## Backup Your Data

Always keep a backup of `data_export.json` generated during migration. You can restore from it if needed.

## Quick Reference Commands

```bash
# Export only (creates backup)
python migrate_to_mysql.py --export-only

# Full migration
python migrate_to_mysql.py

# Verify migration
python migrate_to_mysql.py --verify

# Test MySQL connection
python -c "from database import engine; print(engine.connect())"
```
