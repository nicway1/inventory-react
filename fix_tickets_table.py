import sqlite3
import os

def fix_tickets_table():
    """Add missing shipping_tracking_2 column to tickets table in SQLite database"""
    
    # Try multiple database files that might exist on PythonAnywhere
    possible_paths = [
        'inventory.db',
        '/home/nicway2/inventory/inventory.db',
        'app.db',
        '/home/nicway2/inventory/app.db',
        'instance/app.db',
        '/home/nicway2/inventory/instance/app.db',
    ]
    
    success = False
    
    for db_path in possible_paths:
        if not os.path.exists(db_path):
            print(f"Database not found at: {db_path}")
            continue
            
        print(f"Trying database at: {db_path}")
        conn = None
        try:
            # Connect to database
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Check if table exists
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='tickets'")
            if not cursor.fetchone():
                print(f"No 'tickets' table found in {db_path}")
                continue
                
            # Check if column exists
            cursor.execute("PRAGMA table_info(tickets)")
            columns = [column[1] for column in cursor.fetchall()]
            print(f"Existing columns in tickets table: {columns}")
            
            # Add missing column
            if 'shipping_tracking_2' not in columns:
                print(f"Adding shipping_tracking_2 column to {db_path}...")
                cursor.execute("ALTER TABLE tickets ADD COLUMN shipping_tracking_2 TEXT")
                conn.commit()
                print("Added shipping_tracking_2 column successfully!")
                success = True
            else:
                print(f"Column shipping_tracking_2 already exists in {db_path}")
                success = True
                
            # Add return_tracking column if needed
            if 'return_tracking' not in columns:
                print(f"Adding return_tracking column to {db_path}...")
                cursor.execute("ALTER TABLE tickets ADD COLUMN return_tracking TEXT")
                conn.commit()
                print("Added return_tracking column successfully!")
            
            # Add shipping_carrier column if needed
            if 'shipping_carrier' not in columns:
                print(f"Adding shipping_carrier column to {db_path}...")
                cursor.execute("ALTER TABLE tickets ADD COLUMN shipping_carrier TEXT")
                conn.commit()
                print("Added shipping_carrier column successfully!")
            
            # Add shipping_status column if needed
            if 'shipping_status' not in columns:
                print(f"Adding shipping_status column to {db_path}...")
                cursor.execute("ALTER TABLE tickets ADD COLUMN shipping_status TEXT")
                conn.commit()
                print("Added shipping_status column successfully!")
                
            # Add secondary_tracking_carrier column if needed
            if 'secondary_tracking_carrier' not in columns:
                print(f"Adding secondary_tracking_carrier column to {db_path}...")
                cursor.execute("ALTER TABLE tickets ADD COLUMN secondary_tracking_carrier TEXT")
                conn.commit()
                print("Added secondary_tracking_carrier column successfully!")
                
            # Add secondary_tracking_status column if needed
            if 'secondary_tracking_status' not in columns:
                print(f"Adding secondary_tracking_status column to {db_path}...")
                cursor.execute("ALTER TABLE tickets ADD COLUMN secondary_tracking_status TEXT")
                conn.commit()
                print("Added secondary_tracking_status column successfully!")
            
        except Exception as e:
            print(f"Error with database {db_path}: {str(e)}")
        finally:
            if conn:
                conn.close()
                
    if not success:
        print("\nCould not find and update any database with tickets table.")
        print("Current directory:", os.getcwd())
        print("Files in current directory:", sorted(os.listdir()))
        if os.path.exists('instance'):
            print("Files in instance directory:", sorted(os.listdir('instance')))

if __name__ == "__main__":
    fix_tickets_table() 