from sqlalchemy import Column, Integer, ForeignKey, DateTime, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from models.base import Base

class CompanyCustomerPermission(Base):
    __tablename__ = 'company_customer_permissions'
    
    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey('companies.id'), nullable=False)
    customer_company_id = Column(Integer, ForeignKey('companies.id'), nullable=False)
    can_view = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)
    
    # Relationships with proper overlaps specification
    company = relationship(
        "Company", 
        foreign_keys=[company_id], 
        back_populates="customer_view_permissions",
        overlaps="customer_permissions_received"
    )
    customer_company = relationship(
        "Company", 
        foreign_keys=[customer_company_id], 
        back_populates="customer_permissions_received",
        overlaps="customer_view_permissions"
    )
    
    def __repr__(self):
        return f'<CompanyCustomerPermission company_id={self.company_id} customer_company_id={self.customer_company_id} can_view={self.can_view}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'company_id': self.company_id,
            'customer_company_id': self.customer_company_id,
            'can_view': self.can_view,
            'company_name': self.company.name if self.company else None,
            'customer_company_name': self.customer_company.name if self.customer_company else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        } 