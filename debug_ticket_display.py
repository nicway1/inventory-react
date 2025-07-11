#!/usr/bin/env python3
"""
Debug script to show exactly what should be displayed for each ticket in the shipments table.
This will help identify why some tickets don't show subjects properly.
"""

from utils.db_manager import DatabaseManager
from models.ticket import Ticket

def debug_ticket_display():
    """Debug what should be displayed for each ticket"""
    logger.info("🔍 Debugging ticket display in shipments table...")
    
    db_manager = DatabaseManager()
    db_session = db_manager.get_session()
    
    try:
        # Get tickets that would be shown in shipments (same filter as in templates)
        tickets = db_session.query(Ticket).filter(
            Ticket.category.isnot(None)
        ).order_by(Ticket.created_at.desc()).limit(15).all()
        
        logger.info("Found {len(tickets)} tickets to display")
        logger.info("\n" + "="*80)
        
        for i, ticket in enumerate(tickets, 1):
            logger.info("\n📋 TICKET {i}: {ticket.display_id}")
            logger.info("Subject: '{ticket.subject}'")
            logger.info("Category: {ticket.category.value if ticket.category else 'None'}")
            logger.info("Assets: {len(ticket.assets)} asset(s)")
            
            # Show what would be displayed in Asset/Subject column
            if ticket.assets:
                logger.info("🔧 HAS ASSETS - Will show asset info:")
                for j, asset in enumerate(ticket.assets[:1]):  # Only show first asset like template
                    device_model = asset.model if asset.model else 'Unknown Device'
                    serial_number = asset.serial_num if asset.serial_num else 'No Serial'
                    display_text = f"{device_model} - {serial_number}"
                    logger.info("   Asset {j+1}: '{display_text}'")
                if len(ticket.assets) > 1:
                    logger.info("   Plus {len(ticket.assets) - 1} more assets")
            else:
                logger.info("📝 NO ASSETS - Will show subject:")
                if ticket.subject and ticket.subject.strip() and ticket.subject.strip() != '-':
                    subject_text = ticket.subject
                else:
                    subject_text = 'No Subject'
                logger.info("   Subject display: '{subject_text}'")
            
            # Show customer info
            if ticket.customer:
                logger.info("👤 Customer: {ticket.customer.name} ({ticket.customer.email})")
            else:
                logger.info("👤 Customer: No Customer")
                
            # Show what the final display would be
            logger.info("🎯 FINAL DISPLAY:")
            if ticket.assets:
                asset = ticket.assets[0]
                device_model = asset.model if asset.model else 'Unknown Device'
                serial_number = asset.serial_num if asset.serial_num else 'No Serial'
                final_display = f"{device_model} - {serial_number}"
            else:
                if ticket.subject and ticket.subject.strip() and ticket.subject.strip() != '-':
                    final_display = ticket.subject
                else:
                    final_display = 'No Subject'
            logger.info("   '{final_display}'")
            logger.info("-" * 60)
            
    except Exception as e:
        logger.info("Error during debug: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db_session.close()

if __name__ == "__main__":
    debug_ticket_display() 