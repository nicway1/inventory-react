import sqlite3

def add_missing_columns():
    """Add missing columns to the tickets table in SQLite database"""
    try:
        # Connect to the database
        conn = sqlite3.connect('instance/app.db')
        cursor = conn.cursor()
        
        # Check if the column already exists
        cursor.execute("PRAGMA table_info(tickets)")
        columns = [column[1] for column in cursor.fetchall()]
        
        # Add shipping_tracking_2 column if it doesn't exist
        if 'shipping_tracking_2' not in columns:
            print("Adding shipping_tracking_2 column...")
            cursor.execute("ALTER TABLE tickets ADD COLUMN shipping_tracking_2 TEXT")
        else:
            print("Column shipping_tracking_2 already exists.")
        
        # Add return_tracking column if it doesn't exist
        if 'return_tracking' not in columns:
            print("Adding return_tracking column...")
            cursor.execute("ALTER TABLE tickets ADD COLUMN return_tracking TEXT")
        else:
            print("Column return_tracking already exists.")
        
        # Add shipping_carrier column if it doesn't exist
        if 'shipping_carrier' not in columns:
            print("Adding shipping_carrier column...")
            cursor.execute("ALTER TABLE tickets ADD COLUMN shipping_carrier TEXT")
        else:
            print("Column shipping_carrier already exists.")
        
        # Add shipping_status column if it doesn't exist
        if 'shipping_status' not in columns:
            print("Adding shipping_status column...")
            cursor.execute("ALTER TABLE tickets ADD COLUMN shipping_status TEXT")
        else:
            print("Column shipping_status already exists.")
        
        # Add secondary_tracking_carrier column if it doesn't exist
        if 'secondary_tracking_carrier' not in columns:
            print("Adding secondary_tracking_carrier column...")
            cursor.execute("ALTER TABLE tickets ADD COLUMN secondary_tracking_carrier TEXT")
        else:
            print("Column secondary_tracking_carrier already exists.")
        
        # Add secondary_tracking_status column if it doesn't exist
        if 'secondary_tracking_status' not in columns:
            print("Adding secondary_tracking_status column...")
            cursor.execute("ALTER TABLE tickets ADD COLUMN secondary_tracking_status TEXT")
        else:
            print("Column secondary_tracking_status already exists.")
        
        # Commit the changes
        conn.commit()
        print("Database updated successfully!")
        
    except Exception as e:
        print(f"Error updating database: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    add_missing_columns() 