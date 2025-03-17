import os
import sqlite3

def update_assets_table():
    """Add the intake_ticket_id column to the assets table if it doesn't exist"""
    try:
        # Get database path - adjust this to match your actual database path
        db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'inventory.db')
        
        # Connect to the database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if column exists
        cursor.execute("PRAGMA table_info(assets)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'intake_ticket_id' not in columns:
            # Add the column
            cursor.execute("ALTER TABLE assets ADD COLUMN intake_ticket_id INTEGER")
            conn.commit()
            print("Added intake_ticket_id column to assets table")
        else:
            print("intake_ticket_id column already exists in assets table")
            
        conn.close()
        return True
    except Exception as e:
        print(f"Error updating assets table: {str(e)}")
        return False

if __name__ == "__main__":
    update_assets_table() 