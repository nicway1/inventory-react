from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from models.base import Base
from datetime import datetime

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
    
    # Company grouping fields
    parent_company_id = Column(Integer, ForeignKey('companies.id'), nullable=True)
    display_name = Column(String(200), nullable=True)
    is_parent_company = Column(Boolean, default=False)
    
    # Relationships
    users = relationship("User", back_populates="company", lazy="dynamic", viewonly=True)
    assets = relationship("Asset", back_populates="company", lazy="dynamic", viewonly=True)
    customer_users = relationship("CustomerUser", back_populates="company")
    user_permissions = relationship("UserCompanyPermission", back_populates="company")
    queue_permissions = relationship("CompanyQueuePermission", back_populates="company")
    
    # Parent/Child company relationships
    parent_company = relationship("Company", remote_side=[id], back_populates="child_companies")
    child_companies = relationship("Company", back_populates="parent_company", lazy="dynamic")
    
    # Fixed relationships for CompanyCustomerPermission using proper string references and foreign_keys
    customer_view_permissions = relationship(
        "CompanyCustomerPermission",
        foreign_keys="CompanyCustomerPermission.company_id",
        back_populates="company", 
        lazy="dynamic",
        overlaps="customer_permissions_received"
    )
    customer_permissions_received = relationship(
        "CompanyCustomerPermission",
        foreign_keys="CompanyCustomerPermission.customer_company_id",
        back_populates="customer_company",
        lazy="dynamic",
        overlaps="customer_view_permissions"
    )

    @property
    def logo_url(self):
        """Return the URL for the company logo"""
        if self.logo_path:
            return f'/static/company_logos/{self.logo_path}'
        return '/static/images/default-company.png'  # Default logo path
    
    @property
    def grouped_display_name(self):
        """Return the display name for grouped companies (e.g., 'Wise (Firstbase)')"""
        if self.parent_company_id and self.parent_company:
            # Child company: show as "Child (Parent)"
            return f"{self.name} ({self.parent_company.name})"
        elif self.is_parent_company and self.child_companies.count() > 0:
            # Parent company with children: just return the name or custom display name
            return self.display_name or self.name
        else:
            # Standalone company: return custom display name or regular name
            return self.display_name or self.name
    
    @property
    def effective_display_name(self):
        """Return the effective display name for UI purposes"""
        return self.display_name or self.name 

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
            'parent_company_id': self.parent_company_id,
            'display_name': self.display_name,
            'is_parent_company': self.is_parent_company,
            'grouped_display_name': self.grouped_display_name,
            'effective_display_name': self.effective_display_name,
            'parent_company_name': self.parent_company.name if self.parent_company else None,
            'child_companies_count': self.child_companies.count() if hasattr(self, 'child_companies') else 0,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        } 