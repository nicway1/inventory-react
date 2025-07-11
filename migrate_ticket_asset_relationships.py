"""
Script to migrate existing ticket-asset relationships to the new many-to-many structure.
"""
from utils.db_manager import DatabaseManager
from models.ticket import Ticket
from models.asset import Asset
from sqlalchemy import text

def migrate_relationships():
    """Migrates existing one-to-many relationships to many-to-many"""
    logger.info("Migrating ticket-asset relationships...")
    
    # Get database connection
    db_manager = DatabaseManager()
    db_session = db_manager.get_session()
    
    try:
        # Find all tickets with asset_id set
        tickets_with_assets = db_session.query(Ticket).filter(Ticket.asset_id != None).all()
        logger.info("Found {len(tickets_with_assets)} tickets with assets to migrate")
        
        # For each ticket, add the asset to the assets relationship
        for ticket in tickets_with_assets:
            if ticket.asset:
                # Check if not already in the relationship
                if ticket.asset not in ticket.assets:
                    logger.info("Migrating ticket {ticket.id} with asset {ticket.asset_id}")
                    ticket.assets.append(ticket.asset)
        
        # Commit the changes
        db_session.commit()
        logger.info("Migration completed successfully")
        
        # Also check for records in intake_ticket_id
        assets_with_intake_tickets = db_session.query(Asset).filter(Asset.intake_ticket_id != None).all()
        logger.info("Found {len(assets_with_intake_tickets)} assets with intake tickets")
        
        for asset in assets_with_intake_tickets:
            # Get the ticket
            ticket = db_session.query(Ticket).get(asset.intake_ticket_id)
            if ticket and asset not in ticket.assets:
                logger.info("Migrating intake ticket {ticket.id} with asset {asset.id}")
                ticket.assets.append(asset)
        
        # Commit the changes
        db_session.commit()
        logger.info("Intake tickets migration completed successfully")
            
    except Exception as e:
        db_session.rollback()
        logger.info("Error migrating relationships: {str(e)}")
    finally:
        db_session.close()

if __name__ == "__main__":
    migrate_relationships() 