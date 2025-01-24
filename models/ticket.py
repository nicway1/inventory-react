from datetime import datetime

class Ticket:
    STATUS_OPTIONS = ['New', 'In Progress', 'On Hold', 'Resolved']
    PRIORITY_OPTIONS = ['Low', 'Medium', 'High', 'Critical']
    CATEGORIES = [
        'Hardware Issue', 
        'Software Issue', 
        'Access Request', 
        'New Asset Request',
        'RMA Request'
    ]
    NEW_ASSET_TYPES = ['Laptop', 'Desktop', 'Monitor', 'Phone', 'Tablet', 'Other']
    
    RMA_STATUSES = [
        'Pending Approval',
        'Approved',
        'Item Shipped',
        'Item Received',
        'Replacement Shipped',
        'Completed',
        'Denied'
    ]

    def __init__(self, id, subject, description, requester_id, status='New', 
                 priority='Medium', category=None, asset_id=None, created_at=None, updated_at=None):
        self.id = id
        self.subject = subject
        self.description = description
        self.requester_id = requester_id
        self.status = status
        self.priority = priority
        self.category = category
        self.asset_id = asset_id
        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at or datetime.now()
        self.assigned_to_id = None
        self.queue_id = None
        self.accessory_id = None
        self.shipment = None
        self.rma_status = None
        self.return_tracking = None
        self.replacement_tracking = None
        self.warranty_number = None
        self.serial_number = None

    @property
    def display_id(self):
        """Return a formatted ticket ID (e.g., 'TICK-1001')"""
        return f'TICK-{self.id:04d}'

    @property
    def is_rma(self):
        """Check if this is an RMA ticket"""
        return self.category == 'RMA Request'

    @staticmethod
    def create(subject, description, requester_id, asset_id=None, category=None, priority='Medium'):
        """Create a new ticket with a random ID"""
        import random
        ticket_id = random.randint(1000, 9999)
        return Ticket(
            id=ticket_id,
            subject=subject,
            description=description,
            requester_id=requester_id,
            asset_id=asset_id,
            category=category,
            priority=priority
        )

    def add_shipment(self, tracking_number, description=None):
        """Add a shipment to the ticket"""
        from models.shipment import Shipment
        self.shipment = Shipment(
            tracking_number=tracking_number,
            description=description,
            status='Pending'
        )
        self.updated_at = datetime.now()

    def add_rma_shipment(self, tracking_number, is_return=True, description=None):
        """Add an RMA-specific shipment"""
        from models.shipment import Shipment
        if is_return:
            self.return_tracking = Shipment(
                tracking_number=tracking_number,
                description=f"RMA Return: {description}" if description else "RMA Return",
                status='Pending'
            )
        else:
            self.replacement_tracking = Shipment(
                tracking_number=tracking_number,
                description=f"RMA Replacement: {description}" if description else "RMA Replacement",
                status='Pending'
            )
        self.updated_at = datetime.now()

    def update_rma_status(self, new_status):
        """Update RMA status"""
        if new_status in self.RMA_STATUSES:
            self.rma_status = new_status
            self.updated_at = datetime.now()

    def change_status(self, new_status, comment=None):
        if new_status in self.STATUS_OPTIONS:
            self.status = new_status
            self.updated_at = datetime.now()

    def assign_case_owner(self, user_id):
        self.assigned_to_id = user_id
        self.updated_at = datetime.now() 