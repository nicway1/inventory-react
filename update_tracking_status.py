from app import db_manager
from models.ticket import Ticket

# Get the database session
session = db_manager.get_session()

# Get the ticket
ticket_id = 3
ticket = session.query(Ticket).get(ticket_id)

if ticket:
    # Update status
    print(f"Current status: {ticket.shipping_status}")
    ticket.shipping_status = "Delivered"
    
    # Update any other related fields
    from datetime import datetime
    ticket.updated_at = datetime.now()
    
    # Commit changes
    session.commit()
    print(f"Updated status to: {ticket.shipping_status}")
else:
    print(f"Ticket {ticket_id} not found")

# Close the session
session.close() 