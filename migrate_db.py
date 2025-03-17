from sqlalchemy import create_engine, inspect
from models import Base, AccessoryTransaction
from utils.db_manager import DatabaseManager

def migrate_database():
    try:
        # Get database URL from DatabaseManager
        db_manager = DatabaseManager()
        engine = db_manager.engine
        
        # Create an inspector
        inspector = inspect(engine)
        
        # Check if the table already exists
        if 'accessory_transactions' not in inspector.get_table_names():
            # Create the new table only if it doesn't exist
            AccessoryTransaction.__table__.create(engine)
            print("Successfully created accessory_transactions table")
        else:
            print("Table accessory_transactions already exists, skipping creation")
        
        # Add any other migration steps here if needed
        
        return True
    except Exception as e:
        print(f"Error during migration: {str(e)}")
        return False

if __name__ == "__main__":
    migrate_database() 