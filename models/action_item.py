from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum as SQLEnum, Text, Date
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from models.base import Base


class ActionItemStatus(enum.Enum):
    NOT_STARTED = "Not Started"
    IN_PROGRESS = "In Progress"
    PENDING_TESTING = "Pending Testing"
    BLOCKED = "Blocked"
    DONE = "Done"


class ActionItemPriority(enum.Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    URGENT = "Urgent"


class ActionItem(Base):
    __tablename__ = 'action_items'

    id = Column(Integer, primary_key=True)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(SQLEnum(ActionItemStatus), default=ActionItemStatus.NOT_STARTED)
    priority = Column(SQLEnum(ActionItemPriority), default=ActionItemPriority.MEDIUM)

    # Meeting reference (optional - to group by meeting date)
    meeting_id = Column(Integer, ForeignKey('weekly_meetings.id'), nullable=True)
    meeting_date = Column(Date, nullable=True)  # Legacy field, kept for backward compatibility
    meeting_notes = Column(Text, nullable=True)

    # User relationships
    created_by_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    assigned_to_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    tester_id = Column(Integer, ForeignKey('users.id'), nullable=True)

    # Item number for easy reference (e.g., "test item 3")
    item_number = Column(Integer, nullable=True)

    # Dates
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)
    due_date = Column(Date, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    # Position for ordering within status columns
    position = Column(Integer, default=0)

    # Relationships
    created_by = relationship('User', foreign_keys=[created_by_id], backref='created_action_items')
    assigned_to = relationship('User', foreign_keys=[assigned_to_id], backref='assigned_action_items')
    tester = relationship('User', foreign_keys=[tester_id], backref='testing_action_items')
    meeting = relationship('WeeklyMeeting', back_populates='action_items')
    comments = relationship('ActionItemComment', back_populates='action_item', order_by='ActionItemComment.created_at', cascade='all, delete-orphan')

    def get_status_color(self):
        """Return CSS color class for status"""
        colors = {
            ActionItemStatus.NOT_STARTED: 'bg-gray-100 text-gray-800',
            ActionItemStatus.IN_PROGRESS: 'bg-blue-100 text-blue-800',
            ActionItemStatus.PENDING_TESTING: 'bg-purple-100 text-purple-800',
            ActionItemStatus.BLOCKED: 'bg-red-100 text-red-800',
            ActionItemStatus.DONE: 'bg-green-100 text-green-800'
        }
        return colors.get(self.status, 'bg-gray-100 text-gray-800')

    def get_priority_color(self):
        """Return CSS color class for priority"""
        colors = {
            ActionItemPriority.LOW: 'bg-gray-200 text-gray-700',
            ActionItemPriority.MEDIUM: 'bg-yellow-200 text-yellow-800',
            ActionItemPriority.HIGH: 'bg-orange-200 text-orange-800',
            ActionItemPriority.URGENT: 'bg-red-200 text-red-800'
        }
        return colors.get(self.priority, 'bg-gray-200 text-gray-700')

    def get_priority_badge_color(self):
        """Return border color for kanban card based on priority"""
        colors = {
            ActionItemPriority.LOW: 'border-l-gray-400',
            ActionItemPriority.MEDIUM: 'border-l-yellow-400',
            ActionItemPriority.HIGH: 'border-l-orange-400',
            ActionItemPriority.URGENT: 'border-l-red-500'
        }
        return colors.get(self.priority, 'border-l-gray-400')

    def to_dict(self):
        """Convert to dictionary for JSON responses"""
        return {
            'id': self.id,
            'item_number': self.item_number,
            'title': self.title,
            'description': self.description,
            'status': self.status.value if self.status else None,
            'priority': self.priority.value if self.priority else None,
            'meeting_id': self.meeting_id,
            'meeting_name': self.meeting.name if self.meeting else None,
            'meeting_date': self.meeting_date.isoformat() if self.meeting_date else None,
            'due_date': self.due_date.isoformat() if self.due_date else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'assigned_to_id': self.assigned_to_id,
            'assigned_to_name': self.assigned_to.username if self.assigned_to else None,
            'tester_id': self.tester_id,
            'tester_name': self.tester.username if self.tester else None,
            'position': self.position
        }

    def __repr__(self):
        return f'<ActionItem {self.id}: {self.title[:50]}...>'


class ActionItemComment(Base):
    """Comments/discussion for action items"""
    __tablename__ = 'action_item_comments'

    id = Column(Integer, primary_key=True)
    action_item_id = Column(Integer, ForeignKey('action_items.id'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)

    # Relationships
    action_item = relationship('ActionItem', back_populates='comments')
    user = relationship('User', backref='action_item_comments')

    def to_dict(self):
        return {
            'id': self.id,
            'action_item_id': self.action_item_id,
            'user_id': self.user_id,
            'username': self.user.username if self.user else None,
            'content': self.content,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
