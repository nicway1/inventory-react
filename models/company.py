from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from models.base import Base

class Company(Base):
    __tablename__ = 'companies'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    address = Column(String, nullable=True)
    contact_name = Column(String(100), nullable=True)
    contact_email = Column(String(100), nullable=True)
    logo_path = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships - use string to avoid circular import
    users = relationship("User", back_populates="company", lazy="dynamic")
    assets = relationship("Asset", back_populates="company", lazy="dynamic")

    @property
    def logo_url(self):
        """Return the URL for the company logo"""
        if self.logo_path:
            return f'/static/company_logos/{self.logo_path}'
        return '/static/images/default-company.png'  # Default logo path 