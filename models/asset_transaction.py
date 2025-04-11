from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from models.base import Base

class AssetTransaction(Base):
    """Model for asset transactions"""
    __tablename__ = 'asset_transactions'
    
    id = Column(Integer, primary_key=True)
    asset_id = Column(Integer, ForeignKey('assets.id'), nullable=False)
    customer_id = Column(Integer, ForeignKey('customer_users.id'), nullable=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    transaction_type = Column(String(50), nullable=False)  # checkout, checkin, etc.
    notes = Column(String(1000))
    transaction_date = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    asset = relationship("Asset", back_populates="transactions")
    customer = relationship("CustomerUser", back_populates="asset_transactions")
    user = relationship("User")
    
    def __init__(self, asset_id, transaction_type, transaction_number=None, customer_id=None, 
                 notes=None, transaction_date=None):
        self.asset_id = asset_id
        self.transaction_type = transaction_type
        self.customer_id = customer_id
        self.notes = notes
        
        # Generate a transaction number if not provided
        if not transaction_number:
            timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
            self.transaction_number = f"TRX-{timestamp}-{asset_id}"
        else:
            self.transaction_number = transaction_number
            
        # Set transaction date if provided, otherwise use current time
        self.transaction_date = transaction_date if transaction_date else datetime.utcnow()
    
    def __repr__(self):
        return f"<AssetTransaction {self.transaction_number}: {self.transaction_type}>"
    
    def to_dict(self):
        """Convert transaction to dictionary representation"""
        asset_tag = None
        customer_name = None
        
        # Safely access related objects
        if self.asset:
            asset_tag = self.asset.asset_tag
        
        if self.customer:
            # Use name directly if full_name property not available
            if hasattr(self.customer, 'full_name'):
                customer_name = self.customer.full_name
            else:
                customer_name = self.customer.name
        
        return {
            'id': self.id,
            'transaction_number': self.transaction_number,
            'asset_id': self.asset_id,
            'customer_id': self.customer_id,
            'transaction_date': self.transaction_date.strftime('%Y-%m-%d %H:%M:%S') if self.transaction_date else None,
            'transaction_type': self.transaction_type,
            'notes': self.notes,
            'customer_name': customer_name,
            'asset_tag': asset_tag
        } 