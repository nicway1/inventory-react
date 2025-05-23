from app import db_manager
from utils.tracking_cache import TrackingCache

tracking_number = "XZD0002657586"
ticket_id = 3

session = db_manager.get_session()

cached_data = TrackingCache.get_cached_tracking(
    session, 
    tracking_number, 
    ticket_id=ticket_id, 
    tracking_type='primary',
    max_age_hours=24
)

if cached_data:
    print(f"Found cached tracking data for {tracking_number}:")
    print(cached_data)
else:
    print(f"No cached tracking data found for {tracking_number}")

session.close() 