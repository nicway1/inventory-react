from utils.user_store import UserStore
from utils.activity_store import ActivityStore
from utils.ticket_store import TicketStore
from utils.comment_store import CommentStore
from utils.queue_store import QueueStore
from utils.inventory_store import InventoryStore
from utils.snipeit_client import SnipeITClient
from utils.shipment_store import ShipmentStore
from utils.db_manager import DatabaseManager

# Initialize all stores
user_store = UserStore()
activity_store = ActivityStore()
ticket_store = TicketStore()
queue_store = QueueStore()
inventory_store = InventoryStore()
shipment_store = ShipmentStore()
snipe_client = SnipeITClient()
db_manager = DatabaseManager()

# Initialize CommentStore with dependencies
comment_store = CommentStore(user_store, activity_store, ticket_store) 