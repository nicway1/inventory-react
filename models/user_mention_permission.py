from sqlalchemy import Column, Integer, ForeignKey, Boolean, String
from sqlalchemy.orm import relationship
from models.base import Base


class UserMentionPermission(Base):
    """
    Stores which users and groups a user can see in @mention suggestions.

    If mention_filter_enabled is False for a user, they see all users/groups.
    If mention_filter_enabled is True, they only see users/groups explicitly allowed.
    """
    __tablename__ = 'user_mention_permissions'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    # Type: 'user' or 'group'
    target_type = Column(String(20), nullable=False)
    # ID of the target user or group
    target_id = Column(Integer, nullable=False)

    # Relationships
    user = relationship('User', back_populates='mention_permissions')

    def __repr__(self):
        return f'<UserMentionPermission user={self.user_id} {self.target_type}={self.target_id}>'
