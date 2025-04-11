import sqlite3
import os

def add_missing_columns():
    """Add missing columns to the tickets table in SQLite database"""
    conn = None
    try:
        # Determine the database path
        # For PythonAnywhere, the path is likely in the project root
        database_paths = [
            'instance/app.db',  # Standard Flask path
            'app.db',           # Root directory
            '/home/nicway2/inventory/instance/app.db',  # Full path on PythonAnywhere
            '/home/nicway2/inventory/app.db'            # Alternative full path
        ]
        
        # Try each path until we find the database
        for db_path in database_paths:
            if os.path.exists(db_path):
                print(f"Found database at: {db_path}")
                conn = sqlite3.connect(db_path)
                break
        
        # If we couldn't find the database, let the user provide the path
        if conn is None:
            print("Could not find the database file automatically.")
            print("Current working directory:", os.getcwd())
            print("Available files in current directory:", os.listdir())
            print("Available files in 'instance' directory (if it exists):", 
                  os.listdir('instance') if os.path.exists('instance') else "No instance directory")
            
            user_path = input("Please enter the full path to the database file: ")
            if os.path.exists(user_path):
                conn = sqlite3.connect(user_path)
            else:
                print(f"Error: File {user_path} does not exist.")
                return
        
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