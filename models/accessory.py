from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from models.base import Base

class Accessory(Base):
    __tablename__ = 'accessories'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)  # Item Name
    category = Column(String(50), nullable=False)  # Category
    manufacturer = Column(String(100))  # Manufacturer
    model_no = Column(String(100))  # Model No
    total_quantity = Column(Integer, default=0)  # Quantity
    available_quantity = Column(Integer, default=0)  # Available quantity from total
    country = Column(String(100))  # Country
    status = Column(String(50), default='Available')  # Status
    notes = Column(String(1000))  # Notes
    checkout_date = Column(DateTime)
    return_date = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)
    customer_id = Column(Integer, ForeignKey('customer_users.id'), nullable=True)

    # Relationships
    tickets = relationship("Ticket", back_populates="accessory", lazy="dynamic")
    customer_user = relationship("CustomerUser", back_populates="assigned_accessories")
    history = relationship("AccessoryHistory", back_populates="accessory", order_by="desc(AccessoryHistory.created_at)")
    transactions = relationship("AccessoryTransaction", back_populates="accessory", order_by="desc(AccessoryTransaction.transaction_date)")
    aliases = relationship("AccessoryAlias", back_populates="accessory", cascade="all, delete-orphan")
    
    def track_change(self, user_id, action, changes, notes=None):
        """Create a history entry for accessory changes
        
        Args:
            user_id: ID of the user who made the change
            action: Description of the action (e.g., "UPDATE", "STATUS_CHANGE")
            changes: Dictionary of changes in the format {field: {'old': old_value, 'new': new_value}}
            notes: Any additional notes about the change
            
        Returns:
            AccessoryHistory object (not yet added to session)
        """
        from models.accessory_history import AccessoryHistory
        
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
        
        return AccessoryHistory(
            accessory_id=self.id,
            user_id=user_id,
            action=action,
            changes=serialized_changes,
            notes=notes
        )

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'category': self.category,
            'manufacturer': self.manufacturer,
            'model_no': self.model_no,
            'total_quantity': self.total_quantity,
            'available_quantity': self.available_quantity,
            'country': self.country,
            'status': self.status,
            'notes': self.notes,
            'customer_id': self.customer_id,
            'aliases': [alias.alias_name for alias in self.aliases] if self.aliases else [],
            'checkout_date': self.checkout_date.isoformat() if self.checkout_date else None,
            'return_date': self.return_date.isoformat() if self.return_date else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    def checkout(self, assigned_to):
        """Check out this accessory to a user"""
        if self.available_quantity > 0:
            self.available_quantity -= 1
            self.customer_id = assigned_to
            self.checkout_date = datetime.utcnow()
            self.status = 'Checked Out'
            return True
        return False

    def checkin(self):
        """Return this accessory to inventory"""
        if self.total_quantity > self.available_quantity:
            self.available_quantity += 1
            self.customer_id = None
            self.return_date = datetime.utcnow()
            self.status = 'Available'
            return True
        return False 