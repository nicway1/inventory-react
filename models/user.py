from sqlalchemy import Column, Integer, String, Enum, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from models.database import Base
from flask_login import UserMixin

class UserType(enum.Enum):
    USER = "user"
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"

class User(UserMixin, Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False)
    password_hash = Column(String(200), nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    company_id = Column(Integer, ForeignKey('companies.id'), nullable=True)
    user_type = Column(Enum(UserType), default=UserType.USER)
    created_at = Column(String(100), default=lambda: datetime.now().isoformat())
    last_login = Column(String(100), nullable=True)
    
    # Relationship
    company = relationship("Company", back_populates="users")
    
    def check_password(self, password):
        """Check if the provided password matches the stored password hash"""
        print(f"Checking password:")
        print(f"- Stored hash: {self.password_hash}")
        print(f"- Provided password: {password}")
        result = self.password_hash == password
        print(f"- Match result: {result}")
        return result

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

    def to_dict(self):
        """Convert user object to dictionary with serializable values"""
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'company_id': self.company_id,
            'user_type': self.user_type.value,  # Convert enum to string
            'created_at': self.created_at,
            'last_login': self.last_login
        }