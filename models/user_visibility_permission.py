from sqlalchemy import Column, Integer, ForeignKey
from sqlalchemy.orm import relationship
from models.base import Base

class UserVisibilityPermission(Base):
    """Controls which users a SUPERVISOR/COUNTRY_ADMIN can see in dropdowns (e.g., Change Case Owner)"""
    __tablename__ = 'user_visibility_permissions'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)  # The supervisor/country_admin
    visible_user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)  # User they can see

    # Relationships
    user = relationship('User', foreign_keys=[user_id], back_populates='visibility_permissions')
    visible_user = relationship('User', foreign_keys=[visible_user_id])

    def to_dict(self):
        """Convert permission to dictionary"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'visible_user_id': self.visible_user_id
        }
