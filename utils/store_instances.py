from utils.db_manager import DatabaseManager
from utils.shipment_store import ShipmentStore
from utils.queue_store import QueueStore
from utils.activity_store import ActivityStore
from utils.user_store import UserStore
from utils.inventory_store import InventoryStore
from utils.ticket_store import TicketStore

# Initialize database manager
db_manager = DatabaseManager()

# Initialize stores
user_store = UserStore()
activity_store = ActivityStore()
ticket_store = TicketStore()
inventory_store = InventoryStore()
queue_store = QueueStore()
shipment_store = ShipmentStore()
snipe_client = None
comment_store = None