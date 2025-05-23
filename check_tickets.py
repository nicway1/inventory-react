from app import db_manager
from models.ticket import Ticket

session = db_manager.get_session()
tickets = session.query(Ticket).all()

print("\nTicket Tracking Information:")
print("-" * 80)
for t in tickets:
    print(f'Ticket {t.id}: status={t.status}, shipping_status={t.shipping_status}')
    if t.shipping_tracking:
        print(f'   Tracking: {t.shipping_tracking}')
    if hasattr(t, 'shipping_history') and t.shipping_history:
        print(f'   History: {t.shipping_history}')
    print("-" * 40)

session.close() 