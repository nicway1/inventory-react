from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
from models.base import Base
from models.user import Country

class CustomerUser(Base):
    __tablename__ = 'customer_users'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    contact_number = Column(String(20), nullable=False)
    email = Column(String(100), nullable=True)
    address = Column(String(500), nullable=False)
    company_id = Column(Integer, ForeignKey('companies.id'))
    country = Column(Enum(Country), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)
    
    # Relationships
    company = relationship("Company", back_populates="customer_users")
    assigned_assets = relationship("Asset", back_populates="customer_user")
    assigned_accessories = relationship("Accessory", back_populates="customer_user")
    tickets = relationship("Ticket", back_populates="customer")
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'contact_number': self.contact_number,
            'email': self.email,
            'address': self.address,
            'company_id': self.company_id,
            'company_name': self.company.name if self.company else None,
            'country': self.country.value if self.country else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        } 