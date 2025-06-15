# 🚨 Fix SQLite Database Corruption on PythonAnywhere

## Problem
Your SQLite database is corrupted with error: `database disk image is malformed`

## 🔧 Solution Steps

### Step 1: Upload Repair Scripts
1. Upload `repair_database.py` to your PythonAnywhere files
2. Upload `recreate_database.py` to your PythonAnywhere files (backup option)

### Step 2: Try Database Repair First
```bash
# In PythonAnywhere console
cd /home/yourusername/inventory
python3 repair_database.py
```

### Step 3: If Repair Fails, Recreate Database
```bash
# Only if repair failed
python3 recreate_database.py
```

### Step 4: Restart Web App
1. Go to PythonAnywhere Web tab
2. Click "Reload" button for your web app
3. Test the application

## 🔍 Manual SQLite Commands (Alternative)

If scripts don't work, try manual repair:

```bash
# Backup corrupted database
cp inventory.db inventory_backup.db

# Try SQLite integrity check
sqlite3 inventory.db "PRAGMA integrity_check;"

# If integrity check fails, try dump and restore
sqlite3 inventory.db ".dump" | sqlite3 inventory_new.db
mv inventory_new.db inventory.db

# Clean up WAL files
rm -f inventory.db-wal inventory.db-shm
```

## 🚨 Prevention Tips

1. **Regular Backups**: Set up automated database backups
2. **Proper Shutdown**: Always close database connections properly
3. **WAL Mode**: Consider using WAL mode for better concurrency
4. **Disk Space**: Ensure sufficient disk space on PythonAnywhere

## 📞 If All Else Fails

1. **Restore from Backup**: If you have a recent backup
2. **Contact Support**: Reach out to PythonAnywhere support
3. **Fresh Start**: Recreate database and re-import data

## 🔄 Database Backup Script (Future Prevention)

```python
#!/usr/bin/env python3
import sqlite3
import shutil
from datetime import datetime

def backup_database():
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = f"inventory_backup_{timestamp}.db"
    shutil.copy2("inventory.db", backup_path)
    print(f"Database backed up to: {backup_path}")

if __name__ == "__main__":
    backup_database()
```

Run this weekly: `python3 backup_database.py` 