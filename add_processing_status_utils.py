#!/usr/bin/env python3

import sys
import os

# Add the project directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.db_manager import DatabaseManager
from models.ticket import Ticket, TicketStatus

def count_processing_tickets():
    """Count tickets currently in PROCESSING status"""
    
    db_manager = DatabaseManager()
    db_session = db_manager.get_session()
    
    try:
        # Count PROCESSING tickets
        processing_count = db_session.query(Ticket).filter(
            Ticket.status == TicketStatus.PROCESSING
        ).count()
        
        print(f"📊 Tickets in PROCESSING status: {processing_count}")
        
        # List them if any exist
        if processing_count > 0:
            processing_tickets = db_session.query(Ticket).filter(
                Ticket.status == TicketStatus.PROCESSING
            ).limit(10).all()
            
            print("\n🔄 PROCESSING Tickets:")
            for ticket in processing_tickets:
                print(f"   - Ticket #{ticket.display_id}: {ticket.subject}")
                if ticket.queue:
                    print(f"     Queue: {ticket.queue.name}")
                if ticket.customer:
                    print(f"     Customer: {ticket.customer.name}")
                print()
        
        return processing_count
        
    except Exception as e:
        print(f"❌ Error counting PROCESSING tickets: {e}")
        return 0
    finally:
        db_session.close()

def update_tickets_to_processing(ticket_ids=None):
    """Update specific tickets to PROCESSING status"""
    
    if not ticket_ids:
        print("⚠️  No ticket IDs provided")
        return
    
    db_manager = DatabaseManager()
    db_session = db_manager.get_session()
    
    try:
        updated_count = 0
        
        for ticket_id in ticket_ids:
            ticket = db_session.query(Ticket).get(ticket_id)
            if ticket:
                old_status = ticket.status.value if ticket.status else 'None'
                ticket.status = TicketStatus.PROCESSING
                print(f"✅ Updated Ticket #{ticket.display_id}: {old_status} → PROCESSING")
                updated_count += 1
            else:
                print(f"❌ Ticket ID {ticket_id} not found")
        
        if updated_count > 0:
            db_session.commit()
            print(f"\n🎉 Successfully updated {updated_count} tickets to PROCESSING status")
        
        return updated_count
        
    except Exception as e:
        db_session.rollback()
        print(f"❌ Error updating tickets: {e}")
        return 0
    finally:
        db_session.close()

def list_tickets_by_status():
    """List tickets grouped by status to see distribution"""
    
    db_manager = DatabaseManager()
    db_session = db_manager.get_session()
    
    try:
        print("📋 Ticket Status Distribution:")
        print("-" * 40)
        
        # Get counts for each status
        for status in TicketStatus:
            count = db_session.query(Ticket).filter(
                Ticket.status == status
            ).count()
            
            print(f"{status.value:<25} : {count:>4} tickets")
        
        # Total count
        total = db_session.query(Ticket).count()
        print("-" * 40)
        print(f"{'TOTAL':<25} : {total:>4} tickets")
        
    except Exception as e:
        print(f"❌ Error listing tickets by status: {e}")
    finally:
        db_session.close()

def detect_candidates_for_processing():
    """Detect tickets that might be candidates for PROCESSING status"""
    
    db_manager = DatabaseManager()
    db_session = db_manager.get_session()
    
    try:
        print("🔍 Detecting candidates for PROCESSING status...")
        
        # Find tickets that are IN_PROGRESS and have shipping tracking
        candidates = db_session.query(Ticket).filter(
            Ticket.status == TicketStatus.IN_PROGRESS,
            Ticket.shipping_tracking.isnot(None)
        ).limit(20).all()
        
        if candidates:
            print(f"\n📦 Found {len(candidates)} IN_PROGRESS tickets with tracking (potential PROCESSING candidates):")
            
            for ticket in candidates:
                print(f"   - Ticket #{ticket.display_id}: {ticket.subject}")
                print(f"     Tracking: {ticket.shipping_tracking}")
                if ticket.shipping_status:
                    print(f"     Shipping Status: {ticket.shipping_status}")
                if ticket.queue:
                    print(f"     Queue: {ticket.queue.name}")
                print()
        else:
            print("   No candidates found")
            
        return candidates
        
    except Exception as e:
        print(f"❌ Error detecting candidates: {e}")
        return []
    finally:
        db_session.close()

def main():
    """Main function to demonstrate PROCESSING status functionality"""
    
    print("🔄 PROCESSING Status Detection & Management\n")
    
    # Show current status distribution
    list_tickets_by_status()
    print()
    
    # Count current PROCESSING tickets
    count_processing_tickets()
    print()
    
    # Find potential candidates for PROCESSING status
    candidates = detect_candidates_for_processing()
    
    # Example: Uncomment to update specific tickets to PROCESSING
    # update_tickets_to_processing([1, 2, 3])  # Replace with actual ticket IDs

if __name__ == '__main__':
    main() 