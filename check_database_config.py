#!/usr/bin/env python
"""
Script to check database configuration
"""
import os
import sys
import inspect
from datetime import datetime

def check_database_config():
    print("Starting database configuration check...")
    
    # List all possible config files and database locations
    possible_config_files = [
        '/home/nicway2/inventory/config.py',
        '/home/nicway2/inventory/app/config.py',
        '/home/nicway2/inventory/.env',
        '/home/nicway2/inventory/settings.py',
        '/home/nicway2/inventory/app/settings.py'
    ]
    
    possible_db_files = [
        '/home/nicway2/inventory.db',
        '/home/nicway2/inventory/inventory.db',
        '/home/nicway2/inventory/app/inventory.db',
        '/home/nicway2/inventory/data/inventory.db',
        '/home/nicway2/inventory/db/inventory.db'
    ]
    
    # Check config files
    print("\nChecking configuration files:")
    for config_file in possible_config_files:
        if os.path.exists(config_file):
            print(f"✓ Found: {config_file}")
            try:
                with open(config_file, 'r') as f:
                    content = f.read()
                    if 'SQLALCHEMY_DATABASE_URI' in content or 'DATABASE_URL' in content:
                        print(f"  - Contains database connection string")
                    if 'sqlite' in content:
                        print(f"  - References SQLite database")
                        # Try to extract the database path
                        for line in content.split('\n'):
                            if 'sqlite:///' in line:
                                db_path = line.split('sqlite:///')[1].split("'")[0]
                                print(f"  - Database path: {db_path}")
            except Exception as e:
                print(f"  - Error reading file: {str(e)}")
        else:
            print(f"✗ Not found: {config_file}")
    
    # Check database files
    print("\nChecking database files:")
    for db_file in possible_db_files:
        if os.path.exists(db_file):
            size = os.path.getsize(db_file) / (1024 * 1024)  # Convert to MB
            mod_time = datetime.fromtimestamp(os.path.getmtime(db_file))
            print(f"✓ Found: {db_file} (Size: {size:.2f} MB, Last modified: {mod_time})")
        else:
            print(f"✗ Not found: {db_file}")
    
    # Try to import the database manager
    print("\nTrying to import database configuration from app:")
    sys.path.append('/home/nicway2/inventory')
    
    try:
        from utils.db_manager import DatabaseManager
        db_manager = DatabaseManager()
        db_url = str(db_manager.engine.url)
        print(f"✓ Successfully imported DatabaseManager")
        print(f"  - Database URL: {db_url}")
        
        # Check if the engine uses the same database file
        if 'sqlite:///' in db_url:
            app_db_path = db_url.split('sqlite:///')[1]
            print(f"  - Application database path: {app_db_path}")
            if os.path.exists(app_db_path):
                print(f"  - Database file exists at this path")
            else:
                print(f"  - WARNING: Database file does not exist at this path!")
    except Exception as e:
        print(f"✗ Error importing database configuration: {str(e)}")
    
    print("\nCheck completed.")

if __name__ == "__main__":
    check_database_config() 