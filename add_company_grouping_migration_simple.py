#!/usr/bin/env python3
"""
Simple Company Grouping Migration Script
Adds the necessary columns for company parent/child relationships.

This script uses your existing database configuration to add:
- parent_company_id: Foreign key to companies.id 
- display_name: Custom display name override
- is_parent_company: Boolean flag for parent companies

Usage: python3 add_company_grouping_migration_simple.py
"""

import sys
import os

# Add the parent directory to the path to import models
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def run_migration():
    """Run the migration using your existing database setup"""
    
    print("=" * 70)
    print("ADDING COMPANY GROUPING COLUMNS")
    print("=" * 70)
    
    try:
        # Import your existing database setup
        from database import engine
        from sqlalchemy import text
        
        print("🔗 Using existing database connection...")
        
        with engine.connect() as connection:
            # Start a transaction
            trans = connection.begin()
            
            try:
                # Check if columns already exist
                result = connection.execute(text("DESCRIBE companies"))
                existing_columns = [row[0] for row in result.fetchall()]
                
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
                
                # Add missing columns
                if 'parent_company_id' in missing_columns:
                    print("  Adding parent_company_id column...")
                    connection.execute(text("""
                        ALTER TABLE companies 
                        ADD COLUMN parent_company_id INT NULL
                    """))
                    print("  ✅ Added parent_company_id column")
                
                if 'display_name' in missing_columns:
                    print("  Adding display_name column...")
                    connection.execute(text("""
                        ALTER TABLE companies 
                        ADD COLUMN display_name VARCHAR(200) NULL
                    """))
                    print("  ✅ Added display_name column")
                
                if 'is_parent_company' in missing_columns:
                    print("  Adding is_parent_company column...")
                    connection.execute(text("""
                        ALTER TABLE companies 
                        ADD COLUMN is_parent_company BOOLEAN DEFAULT FALSE
                    """))
                    print("  ✅ Added is_parent_company column")
                
                # Add foreign key constraint for parent_company_id
                if 'parent_company_id' in missing_columns:
                    print("  Adding foreign key constraint...")
                    try:
                        connection.execute(text("""
                            ALTER TABLE companies 
                            ADD CONSTRAINT fk_companies_parent 
                            FOREIGN KEY (parent_company_id) REFERENCES companies(id) 
                            ON DELETE SET NULL ON UPDATE CASCADE
                        """))
                        print("  ✅ Added foreign key constraint")
                    except Exception as fk_error:
                        print(f"  ⚠️  Foreign key constraint failed (this is OK): {fk_error}")
                        print("  The parent_company_id column is still functional without the constraint")
                
                # Commit the transaction
                trans.commit()
                print("✅ Migration completed successfully!")
                
                # Verify the migration
                print("\n🔍 Verifying migration...")
                result = connection.execute(text("DESCRIBE companies"))
                columns = result.fetchall()
                
                verified_columns = []
                for column in columns:
                    if column[0] in columns_to_add:
                        verified_columns.append(column[0])
                
                print(f"✅ Verified columns: {verified_columns}")
                
                if len(verified_columns) == len(columns_to_add):
                    print("\n🎉 Company grouping migration completed successfully!")
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
    print("Company Grouping Database Migration")
    print("This will add columns needed for company parent/child relationships")
    
    # Confirm before running
    response = input("\nProceed with migration? (y/N): ")
    if response.lower() != 'y':
        print("Migration cancelled.")
        sys.exit(0)
    
    success = run_migration()
    
    if success:
        print("\n" + "=" * 70)
        print("✅ MIGRATION COMPLETED SUCCESSFULLY!")
        print("=" * 70)
        print("Company grouping is now ready to use!")
    else:
        print("\n" + "=" * 70)
        print("❌ MIGRATION FAILED!")
        print("=" * 70)
        print("Please check the errors above and try again.")
        sys.exit(1)