from sqlalchemy import Column, Integer, String, Enum, ForeignKey, DateTime, func
from sqlalchemy.orm import relationship
from datetime import datetime
from enum import Enum as PyEnum
from models.base import Base
from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

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

class User(Base, UserMixin):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    username = Column(String(80), unique=True, nullable=False)
    email = Column(String(120), unique=True, nullable=False)
    password_hash = Column(String(128))
    user_type = Column(Enum(UserType), default=UserType.SUPERVISOR)
    company_id = Column(Integer, ForeignKey('companies.id'))
    assigned_country = Column(Enum(Country), nullable=True)
    role = Column(String(50), nullable=True, default='user')
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)
    
    # Add permissions relationship
    permissions_id = Column(Integer, ForeignKey('permissions.id'))
    permissions = relationship("Permission", back_populates="users")
    
    # Relationships
    company = relationship("Company", back_populates="users")
    tickets_requested = relationship("Ticket", foreign_keys="[Ticket.requester_id]", back_populates="requester")
    tickets_assigned = relationship("Ticket", foreign_keys="[Ticket.assigned_to_id]", back_populates="assigned_to")

    def set_password(self, password):
        """Set password hash"""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Check password hash"""
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
        """Check if user is a super admin"""
        return self.user_type == UserType.SUPER_ADMIN

    @property
    def is_admin(self):
        """Check if user is an admin"""
        return self.user_type in [UserType.SUPER_ADMIN, UserType.COUNTRY_ADMIN]

    @property
    def is_country_admin(self):
        return self.user_type == UserType.COUNTRY_ADMIN

    @property
    def is_supervisor(self):
        """Check if user is a supervisor"""
        return self.user_type == UserType.SUPERVISOR

    def to_dict(self):
        """Convert user to dictionary"""
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'user_type': self.user_type.value if self.user_type else None,
            'company_id': self.company_id,
            'company': self.company.name if self.company else None,
            'assigned_country': self.assigned_country.value if self.assigned_country else None,
            'role': self.role or 'user',  # Return default role if None
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    def update_last_login(self):
        """Update the last login timestamp"""
        self.last_login = datetime.utcnow()

# Add relationships after all models are defined to avoid circular imports
from models.asset_history import AssetHistory
from models.accessory_history import AccessoryHistory

User.activities = relationship("Activity", back_populates="user")
User.assigned_assets = relationship("Asset", back_populates="assigned_to")
User.asset_changes = relationship("AssetHistory", back_populates="user")
User.accessory_changes = relationship("AccessoryHistory", back_populates="user")