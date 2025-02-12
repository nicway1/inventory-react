from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from models.base import Base

class CustomerUser(Base):
    __tablename__ = 'customer_users'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    contact_number = Column(String(20), nullable=False)
    email = Column(String(100), nullable=False)
    address = Column(String(500), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)
    
    # Relationships
    assigned_assets = relationship("Asset", back_populates="customer_user")
    assigned_accessories = relationship("Accessory", back_populates="customer_user")
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'contact_number': self.contact_number,
            'email': self.email,
            'address': self.address,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        } 