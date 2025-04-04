from sqlalchemy import Column, Integer, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from models.base import Base
# Import related models explicitly
from models.user import User
from models.company import Company

class UserCompanyPermission(Base):
    __tablename__ = 'user_company_permissions'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    company_id = Column(Integer, ForeignKey('companies.id'), nullable=False)
    can_view = Column(Boolean, default=True)
    can_edit = Column(Boolean, default=False)
    can_delete = Column(Boolean, default=False)
    
    # Relationships
    user = relationship(User, back_populates='company_permissions')
    company = relationship(Company, back_populates='user_permissions') 