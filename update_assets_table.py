from sqlalchemy import create_engine, inspect, MetaData, Table, Column, Integer, ForeignKey
from utils.db_manager import DatabaseManager

def update_assets_table():
    """Add the intake_ticket_id column to the assets table if it doesn't exist"""
    try:
        # Get database connection
        db_manager = DatabaseManager()
        engine = db_manager.engine
        
        # Create an inspector and metadata object
        inspector = inspect(engine)
        metadata = MetaData()
        metadata.reflect(bind=engine)
        
        # Check if the 'assets' table exists
        if 'assets' in inspector.get_table_names():
            # Check if the column already exists
            columns = [column['name'] for column in inspector.get_columns('assets')]
            
            if 'intake_ticket_id' not in columns:
                # Get the assets table
                assets_table = Table('assets', metadata, autoload_with=engine)
                
                # Execute ALTER TABLE to add the column
                with engine.begin() as conn:
                    conn.execute(
                        f"ALTER TABLE assets ADD COLUMN intake_ticket_id INTEGER REFERENCES intake_tickets(id)"
                    )
                    print("Added intake_ticket_id column to assets table")
            else:
                print("intake_ticket_id column already exists in assets table")
        else:
            print("assets table does not exist")
        
        return True
    except Exception as e:
        print(f"Error updating assets table: {str(e)}")
        return False

if __name__ == "__main__":
    update_assets_table() 