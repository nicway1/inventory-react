#!/usr/bin/env python3
"""
SQLite Company Grouping Migration Script
Adds the necessary columns for company parent/child relationships in SQLite.

This script is specifically designed for SQLite databases and adds:
- parent_company_id: Integer for parent company reference
- display_name: Custom display name override
- is_parent_company: Boolean flag for parent companies

Usage: python3 add_company_grouping_sqlite.py
"""

import sys
import os

# Add the parent directory to the path to import models
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def run_sqlite_migration():
    """Run the migration for SQLite database"""
    
    print("=" * 70)
    print("SQLITE COMPANY GROUPING MIGRATION")
    print("=" * 70)
    
    try:
        # Import your existing database setup
        from database import engine
        from sqlalchemy import text
        
        print("🔗 Connected to SQLite database...")
        
        with engine.connect() as connection:
            # Start a transaction
            trans = connection.begin()
            
            try:
                # Check if columns already exist using SQLite syntax
                result = connection.execute(text("PRAGMA table_info(companies)"))
                columns_info = result.fetchall()
                existing_columns = [row[1] for row in columns_info]  # Column name is in index 1
                
                print(f"📋 Current columns in companies table: {existing_columns}")
                
                columns_to_add = ['parent_company_id', 'display_name', 'is_parent_company']
                missing_columns = [col for col in columns_to_add if col not in existing_columns]
                existing = [col for col in columns_to_add if col in existing_columns]
                
                if existing:
                    print(f"⚠️  Columns already exist: {existing}")
                
                if not missing_columns:
                    print("✅ All company grouping columns already exist!")
                    print("No migration needed.")
                    return True
                
                print(f"📝 Adding missing columns: {missing_columns}")
                
                # Add missing columns using SQLite syntax
                if 'parent_company_id' in missing_columns:
                    print("  Adding parent_company_id column...")
                    connection.execute(text("""
                        ALTER TABLE companies 
                        ADD COLUMN parent_company_id INTEGER
                    """))
                    print("  ✅ Added parent_company_id column")
                
                if 'display_name' in missing_columns:
                    print("  Adding display_name column...")
                    connection.execute(text("""
                        ALTER TABLE companies 
                        ADD COLUMN display_name TEXT
                    """))
                    print("  ✅ Added display_name column")
                
                if 'is_parent_company' in missing_columns:
                    print("  Adding is_parent_company column...")
                    connection.execute(text("""
                        ALTER TABLE companies 
                        ADD COLUMN is_parent_company BOOLEAN DEFAULT 0
                    """))
                    print("  ✅ Added is_parent_company column")
                
                # Note about foreign keys in SQLite
                print("  ℹ️  Note: SQLite foreign key constraints are enforced by SQLAlchemy")
                print("  The parent_company_id relationship will work through the application layer")
                
                # Commit the transaction
                trans.commit()
                print("✅ Migration completed successfully!")
                
                # Verify the migration
                print("\n🔍 Verifying migration...")
                result = connection.execute(text("PRAGMA table_info(companies)"))
                updated_columns_info = result.fetchall()
                
                print("📋 Updated table structure:")
                for col_info in updated_columns_info:
                    col_id, name, data_type, not_null, default_val, pk = col_info
                    print(f"  {name}: {data_type} {'NOT NULL' if not_null else 'NULL'} {f'DEFAULT {default_val}' if default_val else ''}")
                
                verified_columns = []
                for col_info in updated_columns_info:
                    if col_info[1] in columns_to_add:
                        verified_columns.append(col_info[1])
                
                print(f"\n✅ Verified added columns: {verified_columns}")
                
                if len(verified_columns) == len(columns_to_add):
                    print("\n🎉 SQLite migration completed successfully!")
                    print("\nNext steps:")
                    print("1. Restart your Flask application")
                    print("2. Visit /admin/company-grouping to manage company relationships")
                    print("3. Set up Wise as child of Firstbase for 'Wise (Firstbase)' display")
                    return True
                else:
                    print("❌ Migration verification failed")
                    return False
                    
            except Exception as e:
                trans.rollback()
                print(f"❌ Migration failed: {str(e)}")
                import traceback
                traceback.print_exc()
                return False
                
    except Exception as e:
        print(f"❌ Error connecting to database: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("SQLite Company Grouping Migration")
    print("This will add columns needed for company parent/child relationships")
    print("Designed specifically for SQLite databases")
    
    # Confirm before running
    response = input("\nProceed with SQLite migration? (y/N): ")
    if response.lower() != 'y':
        print("Migration cancelled.")
        sys.exit(0)
    
    success = run_sqlite_migration()
    
    if success:
        print("\n" + "=" * 70)
        print("✅ SQLITE MIGRATION COMPLETED!")
        print("=" * 70)
        print("Company grouping is now ready to use!")
    else:
        print("\n" + "=" * 70)
        print("❌ SQLITE MIGRATION FAILED!")
        print("=" * 70)
        print("Please check the errors above and try again.")
        sys.exit(1)