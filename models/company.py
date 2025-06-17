from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from models.base import Base
from datetime import datetime
# Import the related model explicitly
from models.user_company_permission import UserCompanyPermission

class Company(Base):
    __tablename__ = 'companies'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False, unique=True)
    description = Column(String(1000))
    address = Column(String, nullable=True)
    contact_name = Column(String(100), nullable=True)
    contact_email = Column(String(100), nullable=True)
    logo_path = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)
    
    # Relationships
    users = relationship("User", back_populates="company", lazy="dynamic", viewonly=True)
    assets = relationship("Asset", back_populates="company", lazy="dynamic", viewonly=True)
    customer_users = relationship("CustomerUser", back_populates="company")
    user_permissions = relationship(UserCompanyPermission, back_populates="company")
    queue_permissions = relationship("CompanyQueuePermission", back_populates="company")
    
    # Fixed relationships for CompanyCustomerPermission
    customer_view_permissions = relationship(
        "CompanyCustomerPermission", 
        foreign_keys="[CompanyCustomerPermission.company_id]", 
        back_populates="company", 
        lazy="dynamic",
        overlaps="customer_permissions_received"
    )
    customer_permissions_received = relationship(
        "CompanyCustomerPermission", 
        foreign_keys="[CompanyCustomerPermission.customer_company_id]", 
        lazy="dynamic",
        overlaps="customer_view_permissions"
    )

    @property
    def logo_url(self):
        """Return the URL for the company logo"""
        if self.logo_path:
            return f'/static/company_logos/{self.logo_path}'
        return '/static/images/default-company.png'  # Default logo path 

    def __repr__(self):
        return f'<Company {self.name}>'

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'address': self.address,
            'contact_name': self.contact_name,
            'contact_email': self.contact_email,
            'logo_path': self.logo_path,
            'logo_url': self.logo_url,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        } 