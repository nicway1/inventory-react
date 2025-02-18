from utils.db_manager import DatabaseManager
from utils.shipment_store import ShipmentStore
from utils.queue_store import QueueStore
from utils.activity_store import ActivityStore

# Initialize database manager
db_manager = DatabaseManager()

# Initialize stores
user_store = None
activity_store = ActivityStore()
ticket_store = None
inventory_store = None
queue_store = QueueStore()
shipment_store = ShipmentStore()
snipe_client = None
comment_store = None