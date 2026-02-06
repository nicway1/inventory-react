from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, Table
from sqlalchemy.orm import relationship
from datetime import datetime
from models.base import Base
import json

# Association table for queue notification groups
queue_notification_group_association = Table(
    'queue_notification_group_association',
    Base.metadata,
    Column('queue_id', Integer, ForeignKey('queues.id', ondelete='CASCADE'), primary_key=True),
    Column('notification_group_id', Integer, ForeignKey('notification_user_groups.id', ondelete='CASCADE'), primary_key=True)
)


class QueueNotificationConfig(Base):
    """
    Model for advanced queue notification configuration.

    Stores notification settings per queue for different events:
    - on_new_ticket: When a new ticket is created in the queue
    - on_comment: When a comment is added to a ticket in the queue
    - on_status_change: When a ticket's status changes
    - on_assignment: When a ticket is assigned or reassigned
    - on_sla_breach: When a ticket breaches its SLA

    Each event can have:
    - email: Boolean to send email notifications
    - in_app: Boolean to send in-app notifications
    - recipients: List of recipient types (assigned, requester, queue_members, notification_groups)
    """
    __tablename__ = 'queue_notification_configs'

    id = Column(Integer, primary_key=True)
    queue_id = Column(Integer, ForeignKey('queues.id', ondelete='CASCADE'), nullable=False, unique=True)

    # Notification settings stored as JSON
    # Format: {
    #   "on_new_ticket": {"email": true, "in_app": true, "recipients": ["assigned", "queue_members"]},
    #   "on_comment": {"email": false, "in_app": true, "recipients": ["assigned", "requester"]},
    #   ...
    # }
    notification_settings = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    queue = relationship("Queue", backref="notification_config", uselist=False)

    # Available events for queue notifications
    AVAILABLE_EVENTS = [
        'on_new_ticket',
        'on_comment',
        'on_status_change',
        'on_assignment',
        'on_sla_breach'
    ]

    # Available recipient types
    AVAILABLE_RECIPIENTS = [
        'assigned',
        'requester',
        'queue_members',
        'notification_groups',
        'new_assignee'
    ]

    # Default notification settings
    DEFAULT_SETTINGS = {
        'on_new_ticket': {
            'email': True,
            'in_app': True,
            'recipients': ['assigned', 'queue_members']
        },
        'on_comment': {
            'email': False,
            'in_app': True,
            'recipients': ['assigned', 'requester']
        },
        'on_status_change': {
            'email': True,
            'in_app': True,
            'recipients': ['assigned', 'requester']
        },
        'on_assignment': {
            'email': True,
            'in_app': True,
            'recipients': ['new_assignee']
        },
        'on_sla_breach': {
            'email': True,
            'in_app': True,
            'recipients': ['assigned', 'queue_members']
        }
    }

    def __repr__(self):
        queue_name = self.queue.name if self.queue else 'Unknown'
        return f'<QueueNotificationConfig queue={queue_name}>'

    def get_settings(self):
        """Get parsed notification settings, with defaults for missing events."""
        if self.notification_settings:
            try:
                settings = json.loads(self.notification_settings)
            except json.JSONDecodeError:
                settings = {}
        else:
            settings = {}

        # Merge with defaults to ensure all events are present
        result = {}
        for event in self.AVAILABLE_EVENTS:
            if event in settings:
                result[event] = settings[event]
            else:
                result[event] = self.DEFAULT_SETTINGS.get(event, {
                    'email': True,
                    'in_app': True,
                    'recipients': []
                })

        return result

    def set_settings(self, settings):
        """Set notification settings from a dictionary."""
        # Validate and filter to only known events
        filtered = {}
        for event, config in settings.items():
            if event in self.AVAILABLE_EVENTS:
                filtered[event] = {
                    'email': config.get('email', True),
                    'in_app': config.get('in_app', True),
                    'recipients': [r for r in config.get('recipients', []) if r in self.AVAILABLE_RECIPIENTS]
                }

        self.notification_settings = json.dumps(filtered)

    def update_settings(self, partial_settings):
        """Update only specified notification settings, keeping others unchanged."""
        current = self.get_settings()

        for event, config in partial_settings.items():
            if event in self.AVAILABLE_EVENTS:
                if event not in current:
                    current[event] = self.DEFAULT_SETTINGS.get(event, {
                        'email': True,
                        'in_app': True,
                        'recipients': []
                    })

                if 'email' in config:
                    current[event]['email'] = config['email']
                if 'in_app' in config:
                    current[event]['in_app'] = config['in_app']
                if 'recipients' in config:
                    current[event]['recipients'] = [
                        r for r in config['recipients'] if r in self.AVAILABLE_RECIPIENTS
                    ]

        self.notification_settings = json.dumps(current)

    def to_dict(self):
        """Convert to dictionary representation."""
        return {
            'id': self.id,
            'queue_id': self.queue_id,
            'notifications': self.get_settings(),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
