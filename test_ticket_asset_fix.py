#!/usr/bin/env python3
"""
Test script to verify that the ticket-asset relationship fix is working correctly.
"""

from utils.db_manager import DatabaseManager
from models.ticket import Ticket
from models.asset import Asset

def test_ticket_asset_relationships():
    """Test that ticket-asset relationships are working correctly"""
    logger.info("🧪 Testing ticket-asset relationships...")
    
    db_manager = DatabaseManager()
    db_session = db_manager.get_session()
    
    try:
        # Test 1: Check existing tickets
        logger.info("\n📋 Test 1: Checking existing tickets...")
        tickets_with_asset_id = db_session.query(Ticket).filter(
            Ticket.asset_id != None
        ).all()
        
        for ticket in tickets_with_asset_id[:5]:  # Check first 5 tickets
            asset_count = len(ticket.assets)
            asset_id_set = ticket.asset_id is not None
            
            logger.info("Ticket {ticket.id} ({ticket.subject[:50]}...):")
            logger.info("  - asset_id: {ticket.asset_id}")
            logger.info("  - assets relationship count: {asset_count}")
            
            if asset_id_set and asset_count > 0:
                logger.info("  ✅ PASS - Has both asset_id and assets relationship")
                # Check if the asset_id matches one of the assets in the relationship
                asset_ids_in_relationship = [asset.id for asset in ticket.assets]
                if ticket.asset_id in asset_ids_in_relationship:
                    logger.info("  ✅ PASS - asset_id {ticket.asset_id} is in the assets relationship")
                else:
                    logger.info("  ⚠️  WARNING - asset_id {ticket.asset_id} is NOT in the assets relationship")
            elif asset_id_set and asset_count == 0:
                logger.info("  ❌ FAIL - Has asset_id but no assets in relationship")
            elif not asset_id_set and asset_count > 0:
                logger.info("  ⚠️  INFO - No asset_id but has assets in relationship (this is ok)")
            else:
                logger.info("  ℹ️  INFO - No assets assigned (this is normal for some ticket types)")
        
        # Test 2: Check Asset Checkout tickets specifically
        logger.info("\n🎯 Test 2: Checking Asset Checkout tickets...")
        from models.ticket import TicketCategory
        
        checkout_tickets = db_session.query(Ticket).filter(
            Ticket.category.in_([
                TicketCategory.ASSET_CHECKOUT_CLAW,
                TicketCategory.ASSET_CHECKOUT_MAIN,
                TicketCategory.ASSET_CHECKOUT
            ])
        ).all()
        
        if checkout_tickets:
            logger.info("Found {len(checkout_tickets)} Asset Checkout tickets")
            for ticket in checkout_tickets:
                asset_count = len(ticket.assets)
                logger.info("Ticket {ticket.id} ({ticket.category.name if ticket.category else 'Unknown'}):")
                logger.info("  - Assets assigned: {asset_count}")
                if asset_count > 0:
                    for asset in ticket.assets:
                        logger.info("    * {asset.asset_tag} - {asset.name} ({asset.status.value if asset.status else 'Unknown'})")
                    logger.info("  ✅ PASS - Asset Checkout ticket has assets")
                else:
                    logger.info("  ❌ FAIL - Asset Checkout ticket has no assets")
        else:
            logger.info("No Asset Checkout tickets found")
        
        # Test 3: Check that we can access asset details through the relationship
        logger.info("\n🔗 Test 3: Testing asset details access...")
        test_ticket = db_session.query(Ticket).filter(Ticket.asset_id != None).first()
        if test_ticket and test_ticket.assets:
            logger.info("Testing with ticket {test_ticket.id}:")
            for asset in test_ticket.assets:
                logger.info("  Asset {asset.id}:")
                logger.info("    - Asset Tag: {asset.asset_tag}")
                logger.info("    - Serial: {asset.serial_num}")
                logger.info("    - Name: {asset.name}")
                logger.info("    - Status: {asset.status.value if asset.status else 'Unknown'}")
            logger.info("  ✅ PASS - Can access asset details through relationship")
        else:
            logger.info("  ⚠️  No suitable ticket found for testing asset details")
        
        logger.info("\n🎉 Test completed successfully!")
        
    except Exception as e:
        logger.info("❌ Error during testing: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        db_session.close()

if __name__ == "__main__":
    test_ticket_asset_relationships() 