#!/usr/bin/env python3
"""
Migration script to create the missing ticket_assets table.
This table is needed for the many-to-many relationship between tickets and assets.
"""

import sqlite3
import os
from pathlib import Path

def create_ticket_assets_table():
    """Create the ticket_assets table for many-to-many relationship"""
    
    # Database path
    db_path = Path(__file__).parent / 'instance' / 'inventory.db'
    
    if not db_path.exists():
        print(f"Database not found at {db_path}")
        return False
    
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        print("🔍 Checking if ticket_assets table exists...")
        
        # Check if table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='ticket_assets'")
        table_exists = cursor.fetchone() is not None
        
        if table_exists:
            print("✅ ticket_assets table already exists")
            return True
        
        print("🔧 Creating ticket_assets table...")
        
        # Create the ticket_assets table
        cursor.execute("""
            CREATE TABLE ticket_assets (
                ticket_id INTEGER NOT NULL,
                asset_id INTEGER NOT NULL,
                PRIMARY KEY (ticket_id, asset_id),
                FOREIGN KEY (ticket_id) REFERENCES tickets(id) ON DELETE CASCADE,
                FOREIGN KEY (asset_id) REFERENCES assets(id) ON DELETE CASCADE
            )
        """)
        
        # Create indexes for better performance
        cursor.execute("CREATE INDEX ix_ticket_assets_ticket_id ON ticket_assets (ticket_id)")
        cursor.execute("CREATE INDEX ix_ticket_assets_asset_id ON ticket_assets (asset_id)")
        
        conn.commit()
        print("✅ Successfully created ticket_assets table with indexes")
        
        # Verify table creation
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='ticket_assets'")
        if cursor.fetchone():
            print("✅ Table creation verified")
        else:
            print("❌ Table creation failed - table not found after creation")
            return False
            
        return True
        
    except Exception as e:
        print(f"❌ Error creating ticket_assets table: {str(e)}")
        return False
    finally:
        conn.close()

def main():
    """Main function"""
    print("🚀 Creating ticket_assets table migration...")
    print("=" * 50)
    
    success = create_ticket_assets_table()
    
    print("=" * 50)
    if success:
        print("🎉 Migration completed successfully!")
        print("")
        print("Next steps:")
        print("1. Restart your application")
        print("2. Test asset assignment to tickets")
        print("3. Verify assets show up in ticket view")
    else:
        print("💥 Migration failed!")
        print("Please check the error messages above and try again.")
    
    return success

if __name__ == "__main__":
    main() 