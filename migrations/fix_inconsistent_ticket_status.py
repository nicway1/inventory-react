"""
Migration: Fix Inconsistent Ticket Status Data

This migration clears the custom_status field for tickets where a system status
(e.g., RESOLVED, IN_PROGRESS, etc.) is set. This fixes the issue where tickets
show different statuses in the list view vs detail view.

The issue occurred when:
1. A ticket was set to a custom status (e.g., "In Progress")
2. Later, the ticket.status was updated to a system status (e.g., RESOLVED)
3. But the custom_status field was not cleared

This results in:
- List view showing custom_status: "In Progress"
- Detail view/logic using ticket.status: "RESOLVED"

Run this script once after deploying the fix to clean up existing data.
"""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import SessionLocal
from models.ticket import Ticket, TicketStatus


def fix_inconsistent_status():
    """Clear custom_status for tickets with system statuses"""
    db_session = SessionLocal()

    try:
        # Find all tickets that have BOTH a system status AND a custom_status
        # This is the inconsistent state we need to fix
        tickets = db_session.query(Ticket).filter(
            Ticket.status != None,  # Has a system status
            Ticket.custom_status != None  # Also has a custom status (inconsistent!)
        ).all()

        print(f"Found {len(tickets)} tickets with inconsistent status data")

        if not tickets:
            print("No tickets to fix. Migration complete!")
            return

        # Group tickets by status for reporting
        status_counts = {}
        for ticket in tickets:
            status_name = ticket.status.name if ticket.status else "None"
            if status_name not in status_counts:
                status_counts[status_name] = []
            status_counts[status_name].append({
                'id': ticket.id,
                'custom_status': ticket.custom_status
            })

        # Show what we found
        print("\nInconsistent tickets by system status:")
        for status, ticket_list in status_counts.items():
            print(f"  {status}: {len(ticket_list)} tickets")
            # Show first 5 examples
            for ticket in ticket_list[:5]:
                print(f"    - Ticket #{ticket['id']}: status={status}, custom_status={ticket['custom_status']}")
            if len(ticket_list) > 5:
                print(f"    ... and {len(ticket_list) - 5} more")

        # Confirm before proceeding (unless --force flag is used)
        import sys
        force = '--force' in sys.argv or '-f' in sys.argv

        if not force:
            print("\nThis migration will clear the custom_status field for all these tickets.")
            print("The system status field will be kept as the source of truth.")
            response = input("\nProceed with fixing? (yes/no): ")

            if response.lower() != 'yes':
                print("Migration cancelled.")
                return
        else:
            print("\nForce mode enabled. Proceeding with migration...")

        # Clear custom_status for all these tickets
        fixed_count = 0
        for ticket in tickets:
            old_custom_status = ticket.custom_status
            ticket.custom_status = None
            fixed_count += 1
            if fixed_count % 100 == 0:
                print(f"  Fixed {fixed_count} tickets...")

        db_session.commit()
        print(f"\nMigration complete! Fixed {fixed_count} tickets")
        print("All tickets now have consistent status data.")

    except Exception as e:
        db_session.rollback()
        print(f"Error during migration: {str(e)}")
        raise
    finally:
        db_session.close()


if __name__ == '__main__':
    print("=" * 70)
    print("Fixing Inconsistent Ticket Status Data")
    print("=" * 70)
    fix_inconsistent_status()
