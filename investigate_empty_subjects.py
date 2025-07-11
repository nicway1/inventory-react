#!/usr/bin/env python3
"""
Script to investigate tickets with empty or missing subjects and asset information.
This will help identify why some tickets show up as just "-" in the UI.
"""

from utils.db_manager import DatabaseManager
from models.ticket import Ticket
from models.asset import Asset

def investigate_empty_subjects():
    """Investigate tickets with empty subjects or asset info"""
    logger.info("🔍 Investigating tickets with empty subjects and asset information...")
    
    db_manager = DatabaseManager()
    db_session = db_manager.get_session()
    
    try:
        # Get all tickets
        all_tickets = db_session.query(Ticket).all()
        logger.info("Found {len(all_tickets)} total tickets")
        
        empty_subjects = []
        empty_assets = []
        problematic_tickets = []
        
        for ticket in all_tickets:
            # Check for empty or problematic subjects
            if not ticket.subject or ticket.subject.strip() == '' or ticket.subject.strip() == '-':
                empty_subjects.append(ticket)
                
            # Check assets
            if ticket.assets:
                for asset in ticket.assets:
                    if not asset.model or not asset.serial_num:
                        empty_assets.append((ticket, asset))
                        if ticket not in problematic_tickets:
                            problematic_tickets.append(ticket)
            else:
                # Ticket has no assets and potentially no subject
                if not ticket.subject or ticket.subject.strip() == '' or ticket.subject.strip() == '-':
                    problematic_tickets.append(ticket)
        
        logger.info("\n📋 RESULTS:")
        logger.info("Tickets with empty/missing subjects: {len(empty_subjects)}")
        logger.info("Assets with missing device_model or serial_number: {len(empty_assets)}")
        logger.info("Total problematic tickets: {len(problematic_tickets)}")
        
        logger.info("\n📝 EMPTY SUBJECTS:")
        for ticket in empty_subjects[:10]:  # Show first 10
            logger.info("  - Ticket {ticket.display_id}: '{ticket.subject}' (Category: {ticket.category.value if ticket.category else 'None'})")
            
        logger.info("\n🔧 ASSETS WITH MISSING INFO:")
        for ticket, asset in empty_assets[:10]:  # Show first 10
            model = asset.model or 'MISSING'
            serial = asset.serial_num or 'MISSING'
            logger.info("  - Ticket {ticket.display_id}, Asset ID {asset.id}: '{model}' - '{serial}'")
            
        logger.info("\n🚨 MOST PROBLEMATIC TICKETS (showing as '-'):")
        for ticket in problematic_tickets[:5]:
            logger.info("  - Ticket {ticket.display_id}")
            logger.info("    Subject: '{ticket.subject}'")
            logger.info("    Category: {ticket.category.value if ticket.category else 'None'}")
            logger.info("    Assets: {len(ticket.assets)} asset(s)")
            if ticket.assets:
                for asset in ticket.assets:
                    model = asset.model or 'MISSING'
                    serial = asset.serial_num or 'MISSING'
                    logger.info("      - Asset: '{model}' - '{serial}'")
            print()
            
    except Exception as e:
        logger.info("Error during investigation: {e}")
    finally:
        db_session.close()

if __name__ == "__main__":
    investigate_empty_subjects() 