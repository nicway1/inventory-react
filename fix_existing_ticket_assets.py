#!/usr/bin/env python3
"""
Script to fix existing tickets by migrating assets from asset_id to the assets relationship.
This will ensure that existing tickets show their assets properly.
"""

from utils.db_manager import DatabaseManager
from models.ticket import Ticket
from models.asset import Asset

def fix_existing_ticket_assets():
    """Migrate existing ticket-asset relationships to the many-to-many relationship"""
    logger.info("🔧 Fixing existing ticket-asset relationships...")
    
    db_manager = DatabaseManager()
    db_session = db_manager.get_session()
    
    try:
        # Find all tickets with asset_id set but no assets in the relationship
        tickets_with_asset_id = db_session.query(Ticket).filter(
            Ticket.asset_id != None
        ).all()
        
        logger.info("Found {len(tickets_with_asset_id)} tickets with asset_id set")
        
        fixed_count = 0
        skipped_count = 0
        
        for ticket in tickets_with_asset_id:
            try:
                # Check if the asset is already in the assets relationship
                asset_already_linked = any(asset.id == ticket.asset_id for asset in ticket.assets)
                
                if asset_already_linked:
                    logger.info("Ticket {ticket.id}: Asset {ticket.asset_id} already in assets relationship - skipping")
                    skipped_count += 1
                    continue
                
                # Get the asset
                asset = db_session.query(Asset).get(ticket.asset_id)
                if asset:
                    # Add to the many-to-many relationship
                    ticket.assets.append(asset)
                    logger.info("Ticket {ticket.id}: Added asset {ticket.asset_id} ({asset.name}) to assets relationship")
                    fixed_count += 1
                else:
                    logger.info("Ticket {ticket.id}: Asset {ticket.asset_id} not found in database")
                    
            except Exception as e:
                logger.info("Error processing ticket {ticket.id}: {str(e)}")
                continue
        
        # Commit all changes
        db_session.commit()
        logger.info("\n✅ Migration completed!")
        logger.info("   Fixed: {fixed_count} tickets")
        logger.info("   Skipped: {skipped_count} tickets (already linked)")
        logger.info("   Total processed: {len(tickets_with_asset_id)} tickets")
        
    except Exception as e:
        logger.info("❌ Error during migration: {str(e)}")
        db_session.rollback()
    finally:
        db_session.close()

if __name__ == "__main__":
    fix_existing_ticket_assets() 