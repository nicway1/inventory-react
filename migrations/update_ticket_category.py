import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from models.ticket import TicketCategory

def update_ticket_categories():
    engine = create_engine('sqlite:///inventory.db')
    
    # Map old values to new enum names
    category_updates = [
        ("UPDATE tickets SET category = 'HARDWARE_ISSUE' WHERE category IN ('Hardware Issue', 'hardware issue', 'Hardware_Issue')"),
        ("UPDATE tickets SET category = 'SOFTWARE_ISSUE' WHERE category IN ('Software Issue', 'software issue', 'Software_Issue')"),
        ("UPDATE tickets SET category = 'ACCESS_REQUEST' WHERE category IN ('Access Request', 'access request', 'Access_Request')"),
        ("UPDATE tickets SET category = 'NEW_ASSET_REQUEST' WHERE category IN ('New Asset Request', 'new asset request', 'New_Asset_Request')"),
        ("UPDATE tickets SET category = 'RMA_REQUEST' WHERE category IN ('RMA Request', 'rma request', 'RMA_Request')")
    ]
    
    with engine.begin() as conn:  # This automatically handles the transaction
        for update_sql in category_updates:
            conn.execute(text(update_sql))
        print("Successfully updated ticket categories")

if __name__ == "__main__":
    update_ticket_categories() 