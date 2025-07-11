"""
Script to create the ticket_assets association table in the database.
"""
from utils.db_manager import DatabaseManager
from sqlalchemy import Table, Column, Integer, ForeignKey, MetaData
from models.base import Base

def create_ticket_assets_table():
    """Create the ticket_assets association table if it doesn't exist"""
    logger.info("Creating ticket_assets association table...")
    
    # Get database connection
    db_manager = DatabaseManager()
    db_session = db_manager.get_session()
    engine = db_session.bind  # Get engine from session
    
    try:
        # Check if table already exists
        metadata = MetaData()
        metadata.reflect(bind=engine)
        
        if 'ticket_assets' not in metadata.tables:
            # Create the association table
            ticket_assets = Table(
                'ticket_assets',
                Base.metadata,
                Column('ticket_id', Integer, ForeignKey('tickets.id'), primary_key=True),
                Column('asset_id', Integer, ForeignKey('assets.id'), primary_key=True)
            )
            
            # Create the table in the database
            Base.metadata.create_all(engine, tables=[ticket_assets])
            logger.info("ticket_assets table created successfully.")
        else:
            logger.info("ticket_assets table already exists.")
            
    except Exception as e:
        logger.info("Error creating ticket_assets table: {str(e)}")
    finally:
        db_session.close()

if __name__ == "__main__":
    create_ticket_assets_table() 