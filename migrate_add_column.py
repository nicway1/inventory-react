"""
Migration script to add original_accessory_id column to ticket_accessories table.
"""
import os
import sys
from sqlalchemy import create_engine, text, MetaData, Table, Column, Integer, ForeignKey

# Get the database path from the environment or use the default
DATABASE_URL = os.environ.get('DATABASE_URL', 'sqlite:///inventory.db')
if DATABASE_URL.startswith('postgres://'):
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)

def migrate():
    """Add original_accessory_id column to ticket_accessories table"""
    print(f"Starting migration using database: {DATABASE_URL}")
    
    # Create engine
    engine = create_engine(DATABASE_URL)
    conn = engine.connect()
    
    try:
        # Check if column exists
        metadata = MetaData()
        metadata.reflect(bind=engine)
        
        if 'ticket_accessories' not in metadata.tables:
            print("Error: ticket_accessories table does not exist")
            return False
        
        table = metadata.tables['ticket_accessories']
        column_exists = 'original_accessory_id' in table.columns
        
        if column_exists:
            print("Column 'original_accessory_id' already exists in ticket_accessories table")
            return True
        
        # Execute the DDL statement to add the column
        with conn.begin():
            if DATABASE_URL.startswith('sqlite'):
                conn.execute(text("""
                ALTER TABLE ticket_accessories
                ADD COLUMN original_accessory_id INTEGER REFERENCES accessories(id)
                """))
            else:
                # For PostgreSQL or other databases
                conn.execute(text("""
                ALTER TABLE ticket_accessories
                ADD COLUMN original_accessory_id INTEGER
                REFERENCES accessories(id)
                """))
        
        print("Successfully added 'original_accessory_id' column to ticket_accessories table")
        return True
        
    except Exception as e:
        print(f"Error during migration: {str(e)}")
        return False
    finally:
        conn.close()
        engine.dispose()

if __name__ == "__main__":
    success = migrate()
    if success:
        print("Migration completed successfully")
        sys.exit(0)
    else:
        print("Migration failed")
        sys.exit(1) 