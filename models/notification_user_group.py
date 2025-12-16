from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Table
from sqlalchemy.orm import relationship
from datetime import datetime
from models import Base

# Association table for many-to-many relationship between groups and users
notification_user_group_members = Table(
    'notification_user_group_members',
    Base.metadata,
    Column('group_id', Integer, ForeignKey('notification_user_groups.id', ondelete='CASCADE'), primary_key=True),
    Column('user_id', Integer, ForeignKey('users.id', ondelete='CASCADE'), primary_key=True)
)

class NotificationUserGroup(Base):
    """Model for preset user groups for queue notifications"""
    __tablename__ = 'notification_user_groups'

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False, unique=True)
    description = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Many-to-many relationship with users
    members = relationship(
        'User',
        secondary=notification_user_group_members,
        backref='notification_groups',
        lazy='dynamic'
    )

    def __repr__(self):
        return f'<NotificationUserGroup {self.name}>'

    @property
    def member_count(self):
        return self.members.count()

    @property
    def member_list(self):
        """Return list of member user IDs"""
        return [u.id for u in self.members.all()]
