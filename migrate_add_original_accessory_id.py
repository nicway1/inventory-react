import sqlite3
import os
import sys

def migrate_ticket_accessories_table():
    """Add original_accessory_id column to ticket_accessories table"""
    print("Starting migration to add original_accessory_id column to ticket_accessories table")
    
    try:
        # Connect to the SQLite database
        conn = sqlite3.connect('inventory.db')
        cursor = conn.cursor()
        
        # Check if column already exists
        cursor.execute("PRAGMA table_info(ticket_accessories)")
        columns = cursor.fetchall()
        column_names = [column[1] for column in columns]
        
        if 'original_accessory_id' in column_names:
            print("Column 'original_accessory_id' already exists in ticket_accessories table")
            conn.close()
            return True
        
        # Add the new column
        cursor.execute("""
        ALTER TABLE ticket_accessories
        ADD COLUMN original_accessory_id INTEGER;
        """)
        
        # Commit the changes
        conn.commit()
        print("Successfully added 'original_accessory_id' column to ticket_accessories table")
        
        # Close the connection
        conn.close()
        return True
        
    except Exception as e:
        print(f"Error during migration: {str(e)}")
        return False

if __name__ == "__main__":
    success = migrate_ticket_accessories_table()
    if success:
        print("Migration completed successfully")
        sys.exit(0)
    else:
        print("Migration failed")
        sys.exit(1) 