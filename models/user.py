from sqlalchemy import Column, Integer, String, Enum, ForeignKey, DateTime, func
from sqlalchemy.orm import relationship
from datetime import datetime
from enum import Enum as PyEnum
from models.base import Base
from flask_login import UserMixin
from werkzeug.security import check_password_hash

class UserType(str, PyEnum):
    SUPER_ADMIN = "SUPER_ADMIN"
    SUPERVISOR = "SUPERVISOR"
    COUNTRY_ADMIN = "COUNTRY_ADMIN"

class Country(str, PyEnum):
    USA = "USA"
    JAPAN = "JAPAN"
    PHILIPPINES = "PHILIPPINES"
    AUSTRALIA = "AUSTRALIA"
    ISRAEL = "ISRAEL"
    INDIA = "INDIA"
    SINGAPORE = "SINGAPORE"

class User(UserMixin, Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    password_hash = Column(String(200), nullable=False)
    user_type = Column(Enum(UserType), nullable=False)
    company_id = Column(Integer, ForeignKey('companies.id'))
    assigned_country = Column(Enum(Country), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)
    
    def check_password(self, password):
        """Check if the provided password matches the stored password hash"""
        return check_password_hash(self.password_hash, password)

    @staticmethod
    def create(username, password, user_type='user', company=None, fixed_id=None):
        # Convert string user_type to enum if needed
        if isinstance(user_type, str):
            user_type = UserType[user_type.upper()]
            
        if fixed_id is not None:
            user_id = fixed_id
        else:
            import random
            user_id = random.randint(1000, 9999)
        
        return User(
            id=user_id,
            username=username,
            password_hash=password,  # In production, you should hash this
            user_type=user_type,
            company_id=company.id if company else None
        )

    @property
    def is_super_admin(self):
        return self.user_type == UserType.SUPER_ADMIN

    @property
    def is_admin(self):
        return self.user_type in [UserType.COUNTRY_ADMIN, UserType.SUPER_ADMIN]

    def to_dict(self):
        """Convert user object to dictionary with serializable values"""
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'company_id': self.company_id,
            'user_type': self.user_type.value,  # Convert enum to string
            'assigned_country': self.assigned_country.value if self.assigned_country else None,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }

    def update_last_login(self):
        """Update the last login timestamp"""
        self.last_login = datetime.utcnow()

# Add relationships after all models are defined to avoid circular imports
from models.asset_history import AssetHistory

User.company = relationship("Company", back_populates="users")
User.tickets_requested = relationship("Ticket", foreign_keys="[Ticket.requester_id]", back_populates="requester")
User.tickets_assigned = relationship("Ticket", foreign_keys="[Ticket.assigned_to_id]", back_populates="assigned_to")
User.activities = relationship("Activity", back_populates="user")
User.assigned_assets = relationship("Asset", back_populates="assigned_to")
User.asset_changes = relationship("AssetHistory", back_populates="user")