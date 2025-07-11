# Simple migration script using direct SQL
from models.base import Base
from models.ticket import Ticket
from models.asset import Asset
from utils.db_manager import DatabaseManager
from sqlalchemy import text
import traceback
import logging

# Set up logging for this module
logger = logging.getLogger(__name__)


db_manager = DatabaseManager()
db_session = db_manager.get_session()

try:
    logger.info("Migrating ticket-asset relationships using direct SQL...")
    
    # Get all tickets with asset_id set
    tickets = db_session.query(Ticket).filter(Ticket.asset_id.isnot(None)).all()
    logger.info("Found {len(tickets)} tickets with assets to migrate")
    
    # For each ticket, execute a direct SQL insert
    migration_count = 0
    for ticket in tickets:
        if ticket.asset_id:
            try:
                # Check if relationship already exists to avoid duplicates
                check_sql = text("SELECT COUNT(*) FROM ticket_assets WHERE ticket_id = :ticket_id AND asset_id = :asset_id")
                result = db_session.execute(check_sql, {"ticket_id": ticket.id, "asset_id": ticket.asset_id}).scalar()
                
                if result == 0:
                    # Insert directly using SQL rather than the ORM relationship
                    insert_sql = text("INSERT INTO ticket_assets (ticket_id, asset_id) VALUES (:ticket_id, :asset_id)")
                    db_session.execute(insert_sql, {"ticket_id": ticket.id, "asset_id": ticket.asset_id})
                    logger.info("Created relationship for ticket {ticket.id} and asset {ticket.asset_id}")
                    migration_count += 1
                else:
                    logger.info("Relationship already exists for ticket {ticket.id} and asset {ticket.asset_id}")
            except Exception as e:
                logger.info("Error processing ticket {ticket.id}: {str(e)}")
    
    db_session.commit()
    logger.info("Migration completed successfully. Migrated {migration_count} relationships.")
    
except Exception as e:
    db_session.rollback()
    logger.info("Error migrating relationships: {str(e)}")
    traceback.print_exc()
finally:
    db_session.close() 