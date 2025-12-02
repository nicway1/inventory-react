from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Date, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from models.base import Base


class WeeklyMeeting(Base):
    """Weekly meeting to group action items"""
    __tablename__ = 'weekly_meetings'

    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)  # e.g., "Week of Dec 1, 2025" or custom name
    meeting_date = Column(Date, nullable=False)
    notes = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)  # Currently selected meeting

    created_by_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)

    # Relationships
    created_by = relationship('User', backref='created_meetings')
    action_items = relationship('ActionItem', back_populates='meeting', order_by='ActionItem.item_number')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'meeting_date': self.meeting_date.isoformat() if self.meeting_date else None,
            'notes': self.notes,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'item_count': len(self.action_items) if self.action_items else 0
        }

    def __repr__(self):
        return f'<WeeklyMeeting {self.id}: {self.name}>'
