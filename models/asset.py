from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum, JSON, Float, Boolean, Table
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from models.base import Base
from models.intake_ticket import IntakeTicket

class AssetStatus(enum.Enum):
    IN_STOCK = "In Stock"
    READY_TO_DEPLOY = "Ready to Deploy"
    SHIPPED = "Shipped"
    DEPLOYED = "Deployed"
    REPAIR = "Repair"
    ARCHIVED = "Archived"
    DISPOSED = "Disposed"

# Association table for many-to-many relationship between tickets and assets
ticket_assets = Table(
    'ticket_assets',
    Base.metadata,
    Column('ticket_id', Integer, ForeignKey('tickets.id'), primary_key=True),
    Column('asset_id', Integer, ForeignKey('assets.id'), primary_key=True)
)

class Asset(Base):
    __tablename__ = 'assets'
    
    id = Column(Integer, primary_key=True)
    asset_tag = Column(String(50), unique=True, nullable=False)
    serial_num = Column(String(50), unique=True)
    name = Column(String(100))
    model = Column(String(100))
    manufacturer = Column(String(100))
    category = Column(String(50))
    status = Column(Enum(AssetStatus), default=AssetStatus.IN_STOCK)
    cost_price = Column(Float)
    location_id = Column(Integer, ForeignKey('locations.id'))
    company_id = Column(Integer, ForeignKey('companies.id'))
    intake_ticket_id = Column(Integer, ForeignKey('intake_tickets.id'), nullable=True)
    specifications = Column(JSON)
    notes = Column(String(1000))
    tech_notes = Column(String(2000))  # Longer length for detailed technical notes
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)
    assigned_to_id = Column(Integer, ForeignKey('users.id'))
    customer_id = Column(Integer, ForeignKey('customer_users.id'), nullable=True)
    
    # Additional fields used in inventory routes
    hardware_type = Column(String(100))
    inventory = Column(String(50))
    customer = Column(String(100))
    country = Column(String(100))
    asset_type = Column(String(100))
    
    # Additional fields from import
    receiving_date = Column(DateTime)
    keyboard = Column(String(100))
    po = Column(String(100))
    erased = Column(String(50))
    condition = Column(String(100))
    diag = Column(String(1000))
    cpu_type = Column(String(100))
    cpu_cores = Column(String(100))
    gpu_cores = Column(String(100))
    memory = Column(String(100))
    harddrive = Column(String(100))
    charger = Column(String(100))
    
    # Relationships
    location = relationship("Location", back_populates="assets")
    company = relationship("Company", back_populates="assets")
    tickets = relationship("Ticket", secondary=ticket_assets, back_populates="assets")
    assigned_to = relationship("User", back_populates="assigned_assets")
    customer_user = relationship("CustomerUser", back_populates="assigned_assets")
    intake_ticket = relationship("IntakeTicket", back_populates="assets")
    history = relationship("AssetHistory", back_populates="asset", order_by="desc(AssetHistory.created_at)")
    transactions = relationship("AssetTransaction", back_populates="asset", order_by="desc(AssetTransaction.transaction_date)")
    
    def track_change(self, user_id, action, changes, notes=None):
        """Create a history entry for asset changes
        
        Args:
            user_id: ID of the user who made the change
            action: Description of the action (e.g., "UPDATE", "STATUS_CHANGE")
            changes: Dictionary of changes in the format {field: {'old': old_value, 'new': new_value}}
            notes: Any additional notes about the change
            
        Returns:
            AssetHistory object (not yet added to session)
        """
        from models.asset_history import AssetHistory
        import json
        
        # Convert datetime objects to strings for JSON serialization
        def serialize_for_json(obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            return obj
        
        # Process the changes dictionary to handle datetime objects
        serialized_changes = {}
        for field, change_data in changes.items():
            serialized_changes[field] = {
                'old': serialize_for_json(change_data['old']),
                'new': serialize_for_json(change_data['new'])
            }
        
        return AssetHistory(
            asset_id=self.id,
            user_id=user_id,
            action=action,
            changes=serialized_changes,
            notes=notes
        ) 