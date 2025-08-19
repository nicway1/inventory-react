#!/usr/bin/env python3
"""
Database Migration: Add Company Grouping Columns
Creates the necessary columns for company parent/child relationships and grouping functionality.

Migration adds:
- parent_company_id: Foreign key to companies.id for parent company
- display_name: Custom display name override 
- is_parent_company: Boolean flag for parent companies

Run this script to add the company grouping columns to your database.
"""

import sys
import os
import mysql.connector
from mysql.connector import Error

# Add the parent directory to the path to import models
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def get_database_config():
    """Get database configuration from environment or config"""
    try:
        # Try to import from your existing config
        from config import Config
        
        # Extract database details from DATABASE_URL or individual config
        if hasattr(Config, 'DATABASE_URL') and Config.DATABASE_URL:
            # Parse DATABASE_URL format: mysql://user:password@host:port/database
            import urllib.parse
            parsed = urllib.parse.urlparse(Config.DATABASE_URL)
            
            return {
                'host': parsed.hostname or 'localhost',
                'port': parsed.port or 3306,
                'user': parsed.username,
                'password': parsed.password,
                'database': parsed.path.lstrip('/') if parsed.path else None
            }
        else:
            # Use individual config attributes
            return {
                'host': getattr(Config, 'DB_HOST', 'localhost'),
                'port': getattr(Config, 'DB_PORT', 3306),
                'user': getattr(Config, 'DB_USER', None),
                'password': getattr(Config, 'DB_PASSWORD', None),
                'database': getattr(Config, 'DB_NAME', None)
            }
    except ImportError:
        # Fallback to environment variables
        return {
            'host': os.getenv('DB_HOST', 'localhost'),
            'port': int(os.getenv('DB_PORT', 3306)),
            'user': os.getenv('DB_USER'),
            'password': os.getenv('DB_PASSWORD'),
            'database': os.getenv('DB_NAME')
        }

def check_columns_exist(cursor, table_name, columns):
    """Check if columns already exist in the table"""
    cursor.execute(f"DESCRIBE {table_name}")
    existing_columns = [row[0] for row in cursor.fetchall()]
    
    existing = []
    missing = []
    
    for column in columns:
        if column in existing_columns:
            existing.append(column)
        else:
            missing.append(column)
    
    return existing, missing

def run_migration():
    """Run the company grouping migration"""
    
    print("=" * 70)
    print("COMPANY GROUPING DATABASE MIGRATION")
    print("=" * 70)
    
    # Get database configuration
    db_config = get_database_config()
    
    # Validate required config
    if not all([db_config['user'], db_config['password'], db_config['database']]):
        print("❌ Missing required database configuration:")
        print(f"  Host: {db_config['host']}")
        print(f"  Port: {db_config['port']}")
        print(f"  User: {db_config['user']}")
        print(f"  Password: {'***' if db_config['password'] else 'None'}")
        print(f"  Database: {db_config['database']}")
        print("\nPlease set the required environment variables or update config.py")
        return False
    
    print(f"🔗 Connecting to database: {db_config['database']} at {db_config['host']}:{db_config['port']}")
    
    try:
        # Connect to database
        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor()
        
        print("✅ Connected to database successfully")
        
        # Check if columns already exist
        columns_to_add = ['parent_company_id', 'display_name', 'is_parent_company']
        existing, missing = check_columns_exist(cursor, 'companies', columns_to_add)
        
        if existing:
            print(f"⚠️  Some columns already exist: {existing}")
        
        if not missing:
            print("✅ All company grouping columns already exist!")
            print("Migration is not needed.")
            return True
        
        print(f"📝 Adding missing columns: {missing}")
        
        # Start transaction
        connection.start_transaction()
        
        try:
            # Add parent_company_id column (foreign key to companies.id)
            if 'parent_company_id' in missing:
                print("  Adding parent_company_id column...")
                cursor.execute("""
                    ALTER TABLE companies 
                    ADD COLUMN parent_company_id INT NULL,
                    ADD CONSTRAINT fk_companies_parent 
                    FOREIGN KEY (parent_company_id) REFERENCES companies(id) 
                    ON DELETE SET NULL ON UPDATE CASCADE
                """)
                print("  ✅ Added parent_company_id column with foreign key constraint")
            
            # Add display_name column
            if 'display_name' in missing:
                print("  Adding display_name column...")
                cursor.execute("""
                    ALTER TABLE companies 
                    ADD COLUMN display_name VARCHAR(200) NULL
                """)
                print("  ✅ Added display_name column")
            
            # Add is_parent_company column
            if 'is_parent_company' in missing:
                print("  Adding is_parent_company column...")
                cursor.execute("""
                    ALTER TABLE companies 
                    ADD COLUMN is_parent_company BOOLEAN DEFAULT FALSE
                """)
                print("  ✅ Added is_parent_company column")
            
            # Commit the transaction
            connection.commit()
            print("✅ Migration completed successfully!")
            
            # Verify the columns were added
            print("\n🔍 Verifying migration...")
            cursor.execute("DESCRIBE companies")
            columns = cursor.fetchall()
            
            added_columns = []
            for column in columns:
                if column[0] in columns_to_add:
                    added_columns.append(column[0])
            
            print(f"✅ Verified columns in database: {added_columns}")
            
            if len(added_columns) == len(columns_to_add):
                print("🎉 Company grouping migration completed successfully!")
                print("\nNext steps:")
                print("1. Restart your Flask application")
                print("2. Visit /admin/company-grouping to set up company relationships")
                print("3. Configure parent/child relationships (e.g., Wise → Firstbase)")
                return True
            else:
                print("❌ Migration verification failed - not all columns were added")
                return False
                
        except Error as e:
            connection.rollback()
            print(f"❌ Error during migration: {e}")
            return False
            
    except Error as e:
        print(f"❌ Database connection error: {e}")
        return False
        
    finally:
        if 'connection' in locals() and connection.is_connected():
            cursor.close()
            connection.close()
            print("🔗 Database connection closed")

if __name__ == "__main__":
    print("Company Grouping Database Migration")
    print("This script will add the necessary columns for company grouping functionality")
    
    # Confirm before running
    response = input("\nDo you want to proceed with the migration? (y/N): ")
    if response.lower() != 'y':
        print("Migration cancelled.")
        sys.exit(0)
    
    success = run_migration()
    
    if success:
        print("\n" + "=" * 70)
        print("MIGRATION SUCCESSFUL!")
        print("=" * 70)
        print("Company grouping functionality is now available.")
        sys.exit(0)
    else:
        print("\n" + "=" * 70)
        print("MIGRATION FAILED!")
        print("=" * 70)
        print("Please check the error messages above and try again.")
        sys.exit(1)