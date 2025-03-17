from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
import random
import uuid
from models.base import Base

class AccessoryTransaction(Base):
    __tablename__ = 'accessory_transactions'
    
    id = Column(Integer, primary_key=True)
    transaction_number = Column(String(50), unique=True, nullable=False)
    accessory_id = Column(Integer, ForeignKey('accessories.id'), nullable=False)
    customer_id = Column(Integer, ForeignKey('customer_users.id'), nullable=True)
    transaction_date = Column(DateTime, nullable=False, default=datetime.utcnow)
    transaction_type = Column(String(50), nullable=False)  # 'checkout', 'checkin', 'add_stock'
    quantity = Column(Integer, nullable=False, default=1)
    notes = Column(Text, nullable=True)
    
    # Relationships
    accessory = relationship("Accessory", back_populates="transactions")
    customer = relationship("CustomerUser", back_populates="accessory_transactions")
    
    def __init__(self, accessory_id, transaction_type, quantity=1, transaction_number=None, 
                 customer_id=None, notes=None, transaction_date=None):
        self.accessory_id = accessory_id
        self.transaction_type = transaction_type
        self.quantity = quantity
        self.customer_id = customer_id
        self.notes = notes
        
        # Generate a transaction number if not provided
        if not transaction_number:
            # Generate a truly unique transaction number with timestamp, microseconds, and uuid
            timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S%f')
            unique_id = str(uuid.uuid4())[:8]  # Use part of a UUID for uniqueness
            self.transaction_number = f"ACC-{timestamp}-{accessory_id}-{unique_id}"
        else:
            self.transaction_number = transaction_number
            
        # Set transaction date if provided, otherwise use current time
        self.transaction_date = transaction_date if transaction_date else datetime.utcnow()
    
    def __repr__(self):
        return f"<AccessoryTransaction {self.transaction_number}: {self.transaction_type}>"
    
    def to_dict(self):
        """Convert transaction to dictionary representation"""
        accessory_name = None
        customer_name = None
        
        # Safely access related objects
        if self.accessory:
            accessory_name = self.accessory.name
        
        if self.customer:
            customer_name = self.customer.name
        
        return {
            'id': self.id,
            'transaction_number': self.transaction_number,
            'accessory_id': self.accessory_id,
            'customer_id': self.customer_id,
            'transaction_date': self.transaction_date.strftime('%Y-%m-%d %H:%M:%S') if self.transaction_date else None,
            'transaction_type': self.transaction_type,
            'quantity': self.quantity,
            'notes': self.notes,
            'customer_name': customer_name,
            'accessory_name': accessory_name
        } 