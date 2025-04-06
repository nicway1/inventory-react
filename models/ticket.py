from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from models.base import Base

# Import models after class definition to avoid circular imports
from models.comment import Comment
from models.ticket_attachment import TicketAttachment

class TicketStatus(enum.Enum):
    NEW = "New"
    IN_PROGRESS = "In Progress"
    ON_HOLD = "On Hold"
    RESOLVED = "Resolved"

class TicketPriority(enum.Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    CRITICAL = "Critical"

class TicketCategory(enum.Enum):
    PIN_REQUEST = "PIN Request"
    ASSET_REPAIR = "Asset Repair"
    BULK_DELIVERY_QUOTATION = "Bulk Delivery Quotation"
    REPAIR_QUOTE = "Repair Quote"
    ITAD_QUOTE = "ITAD Quote"
    ASSET_CHECKOUT = "Asset Checkout"
    ASSET_CHECKOUT_SINGPOST = "Asset Checkout (SingPost)"
    ASSET_CHECKOUT_DHL = "Asset Checkout (DHL)"
    ASSET_CHECKOUT_UPS = "Asset Checkout (UPS)"
    ASSET_CHECKOUT_BLUEDART = "Asset Checkout (BlueDart)"
    ASSET_CHECKOUT_DTDC = "Asset Checkout (DTDC)"
    ASSET_CHECKOUT_AUTO = "Asset Checkout (Auto)"
    ASSET_CHECKOUT_CLAW = "Asset Checkout (claw)"
    ASSET_RETURN_CLAW = "Asset Return (claw)"
    ASSET_INTAKE = "Asset Intake"

class RMAStatus(enum.Enum):
    PENDING_APPROVAL = "Pending Approval"
    APPROVED = "Approved"
    ITEM_SHIPPED = "Item Shipped"
    ITEM_RECEIVED = "Item Received"
    REPLACEMENT_SHIPPED = "Replacement Shipped"
    COMPLETED = "Completed"
    DENIED = "Denied"

class RepairStatus(enum.Enum):
    PENDING_ASSESSMENT = "Pending Assessment"
    PENDING_QUOTE = "Pending Quote"
    QUOTE_PROVIDED = "Quote Provided"
    REPAIR_APPROVED = "Repair Approved"
    REPAIR_IN_PROGRESS = "Repair in Progress"
    REPAIR_COMPLETED = "Repair Completed"
    PENDING_DISPOSAL = "Pending Disposal"
    DISPOSAL_APPROVED = "Disposal Approved"
    DISPOSAL_COMPLETED = "Disposal Completed"

class Ticket(Base):
    __tablename__ = 'tickets'

    id = Column(Integer, primary_key=True)
    subject = Column(String(200), nullable=False)
    description = Column(String(2000))
    requester_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    status = Column(SQLEnum(TicketStatus), default=TicketStatus.NEW)
    priority = Column(SQLEnum(TicketPriority), default=TicketPriority.MEDIUM)
    category = Column(SQLEnum(TicketCategory))
    asset_id = Column(Integer, ForeignKey('assets.id'))
    assigned_to_id = Column(Integer, ForeignKey('users.id'))
    queue_id = Column(Integer, ForeignKey('queues.id'))
    accessory_id = Column(Integer, ForeignKey('accessories.id'))
    rma_status = Column(SQLEnum(RMAStatus))
    repair_status = Column(SQLEnum(RepairStatus))
    country = Column(String(100))
    damage_description = Column(String(1000))
    apple_diagnostics = Column(String(100))
    image_path = Column(String(500))
    return_tracking = Column(String(100))
    replacement_tracking = Column(String(100))
    warranty_number = Column(String(100))
    serial_number = Column(String(100))
    shipping_address = Column(String(500))
    shipping_tracking = Column(String(100))
    shipping_carrier = Column(String(50), default='singpost')  # Default to SingPost carrier
    customer_id = Column(Integer, ForeignKey('customer_users.id'))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)
    
    # Add tracking status fields
    shipping_status = Column(String(100), default='Pending')
    return_status = Column(String(100), default='Pending')
    replacement_status = Column(String(100), default='Pending')
    
    # Asset Intake specific fields
    packing_list_path = Column(String(500))
    asset_csv_path = Column(String(500))
    notes = Column(String(2000))
    
    # Non-DB fields for tracking history
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.shipping_history = []  # Initialize shipping history as empty list
        
    def __getattr__(self, name):
        """Handle attributes that might not be initialized"""
        if name == 'shipping_history':
            return []
        raise AttributeError(f"'Ticket' object has no attribute '{name}'")

    # Relationships
    requester = relationship('User', foreign_keys=[requester_id], back_populates='tickets_requested')
    assigned_to = relationship('User', foreign_keys=[assigned_to_id], back_populates='tickets_assigned')
    comments = relationship('Comment', back_populates='ticket', cascade='all, delete-orphan')
    asset = relationship('Asset', back_populates='tickets')
    queue = relationship("Queue", back_populates="tickets")
    accessory = relationship("Accessory", back_populates="tickets")
    customer = relationship('CustomerUser', back_populates='tickets')
    attachments = relationship('TicketAttachment', back_populates='ticket', cascade='all, delete-orphan')

    @property
    def display_id(self):
        """Return a formatted ticket ID (e.g., 'TICK-1001')"""
        return f'TICK-{self.id:04d}'

    @property
    def is_rma(self):
        """Check if this is an RMA ticket"""
        return self.category == TicketCategory.RMA_REQUEST

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

    def update_rma_status(self, new_status):
        """Update RMA status"""
        if isinstance(new_status, RMAStatus):
            self.rma_status = new_status
            self.updated_at = datetime.utcnow()

    def change_status(self, new_status):
        """Change ticket status"""
        if isinstance(new_status, TicketStatus):
            self.status = new_status
            self.updated_at = datetime.utcnow()

    def assign_case_owner(self, user_id):
        """Assign ticket to a user"""
        self.assigned_to_id = user_id
        self.updated_at = datetime.utcnow() 