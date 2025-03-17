from sqlalchemy import create_engine
from models import Base, AccessoryTransaction
from utils.db_manager import DatabaseManager

def migrate_database():
    try:
        # Get database URL from DatabaseManager
        db_manager = DatabaseManager()
        engine = db_manager.engine
        
        # Create the new table
        AccessoryTransaction.__table__.create(engine)
        
        print("Successfully created accessory_transactions table")
        return True
    except Exception as e:
        print(f"Error during migration: {str(e)}")
        return False

if __name__ == "__main__":
    migrate_database() 