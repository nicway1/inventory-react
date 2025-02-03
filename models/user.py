from sqlalchemy import Column, Integer, String, Enum, ForeignKey, DateTime, func
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from models.base import Base
from flask_login import UserMixin
from werkzeug.security import check_password_hash

class UserType(enum.Enum):
    SUPER_ADMIN = "Super Admin"
    ADMIN = "Admin"
    SALES = "Sales"
    USER = "User"

class User(UserMixin, Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    password_hash = Column(String(200), nullable=False)
    user_type = Column(Enum(UserType), default=UserType.USER)
    company_id = Column(Integer, ForeignKey('companies.id'))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)
    
    # Relationships
    company = relationship("Company", back_populates="users")
    sales = relationship("Sale", back_populates="user", lazy="dynamic", viewonly=True)
    tickets_requested = relationship("Ticket", foreign_keys="[Ticket.requester_id]", back_populates="requester")
    tickets_assigned = relationship("Ticket", foreign_keys="[Ticket.assigned_to_id]", back_populates="assigned_to")
    
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
        return self.user_type in [UserType.ADMIN, UserType.SUPER_ADMIN]

    @property
    def total_sales(self):
        """Calculate total sales amount"""
        return sum(sale.selling_price for sale in self.sales)

    @property
    def total_profit(self):
        """Calculate total profit"""
        return sum(sale.profit for sale in self.sales if sale.profit is not None)

    def get_sales_by_period(self, start_date, end_date):
        """Get sales within a specific date range"""
        from models.sale import Sale
        return self.sales.filter(
            Sale.sale_date >= start_date,
            Sale.sale_date <= end_date
        ).all()

    def get_recent_sales(self, limit=5):
        """Get recent sales with a limit"""
        from models.sale import Sale
        return self.sales.order_by(Sale.sale_date.desc()).limit(limit).all()

    def to_dict(self):
        """Convert user object to dictionary with serializable values"""
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'company_id': self.company_id,
            'user_type': self.user_type.value,  # Convert enum to string
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }

    def update_last_login(self):
        """Update the last login timestamp"""
        self.last_login = datetime.utcnow()