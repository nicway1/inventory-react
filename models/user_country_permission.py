from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from models.base import Base

class UserCountryPermission(Base):
    """Junction table for user-country many-to-many relationship"""
    __tablename__ = 'user_country_permissions'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    country = Column(String(100), nullable=False)  # Store country as string to match Asset.country

    # Relationships
    user = relationship("User", back_populates="country_permissions")

    def __repr__(self):
        return f'<UserCountryPermission user_id={self.user_id} country={self.country}>'
