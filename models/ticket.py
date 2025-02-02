from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from models.base import Base

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
    HARDWARE_ISSUE = "Hardware Issue"
    SOFTWARE_ISSUE = "Software Issue"
    ACCESS_REQUEST = "Access Request"
    NEW_ASSET_REQUEST = "New Asset Request"
    RMA_REQUEST = "RMA Request"

class RMAStatus(enum.Enum):
    PENDING_APPROVAL = "Pending Approval"
    APPROVED = "Approved"
    ITEM_SHIPPED = "Item Shipped"
    ITEM_RECEIVED = "Item Received"
    REPLACEMENT_SHIPPED = "Replacement Shipped"
    COMPLETED = "Completed"
    DENIED = "Denied"

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
    return_tracking = Column(String(100))
    replacement_tracking = Column(String(100))
    warranty_number = Column(String(100))
    serial_number = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)

    # Relationships
    requester = relationship("User", foreign_keys=[requester_id], back_populates="tickets_requested", lazy="dynamic")
    assigned_to = relationship("User", foreign_keys=[assigned_to_id], back_populates="tickets_assigned", lazy="dynamic")
    asset = relationship("Asset", back_populates="tickets", lazy="dynamic")
    queue = relationship("Queue", back_populates="tickets", lazy="dynamic")
    accessory = relationship("Accessory", back_populates="tickets", lazy="dynamic")

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