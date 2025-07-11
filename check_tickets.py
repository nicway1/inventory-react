from app import db_manager
from models.ticket import Ticket
import logging

# Set up logging for this module
logger = logging.getLogger(__name__)


session = db_manager.get_session()
tickets = session.query(Ticket).all()

logger.info("\nTicket Tracking Information:")
logger.info("-" * 80)
for t in tickets:
    logger.info(f\'Ticket {t.id}: status={t.status}, shipping_status={t.shipping_status}\')
    if t.shipping_tracking:
        logger.info(f\'   Tracking: {t.shipping_tracking}\')
    if hasattr(t, 'shipping_history') and t.shipping_history:
        logger.info(f\'   History: {t.shipping_history}\')
    logger.info("-" * 40)

session.close() 