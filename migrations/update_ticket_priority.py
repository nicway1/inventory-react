import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from models.ticket import TicketPriority

def update_ticket_priorities():
    engine = create_engine('sqlite:///inventory.db')
    
    # Map old values to new enum values
    priority_updates = [
        ("UPDATE tickets SET priority = 'LOW' WHERE priority IN ('low', 'Low')"),
        ("UPDATE tickets SET priority = 'MEDIUM' WHERE priority IN ('medium', 'Medium')"),
        ("UPDATE tickets SET priority = 'HIGH' WHERE priority IN ('high', 'High')"),
        ("UPDATE tickets SET priority = 'CRITICAL' WHERE priority IN ('critical', 'Critical', 'urgent', 'Urgent')")
    ]
    
    with engine.begin() as conn:  # This automatically handles the transaction
        for update_sql in priority_updates:
            conn.execute(text(update_sql))
        print("Successfully updated ticket priorities")

if __name__ == "__main__":
    update_ticket_priorities() 