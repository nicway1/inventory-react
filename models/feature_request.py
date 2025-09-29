from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum as SQLEnum, Text, Date
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from models.base import Base

class FeatureStatus(enum.Enum):
    REQUESTED = "Requested"
    PENDING_APPROVAL = "Pending Approval"
    APPROVED = "Approved"
    REJECTED = "Rejected"
    IN_PLANNING = "In Planning"
    IN_DEVELOPMENT = "In Development"
    IN_TESTING = "In Testing"
    COMPLETED = "Completed"
    CANCELLED = "Cancelled"

class FeaturePriority(enum.Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    CRITICAL = "Critical"

class FeatureRequest(Base):
    __tablename__ = 'feature_requests'

    id = Column(Integer, primary_key=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    status = Column(SQLEnum(FeatureStatus), default=FeatureStatus.REQUESTED)
    priority = Column(SQLEnum(FeaturePriority), default=FeaturePriority.MEDIUM)

    # User relationships
    requester_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    assignee_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    approver_id = Column(Integer, ForeignKey('users.id'), nullable=True)

    # Release relationship
    target_release_id = Column(Integer, ForeignKey('releases.id'), nullable=True)

    # Dates
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)
    target_date = Column(Date, nullable=True)
    completed_date = Column(DateTime, nullable=True)
    approval_requested_at = Column(DateTime, nullable=True)
    approved_at = Column(DateTime, nullable=True)

    # Additional fields
    component = Column(String(100), nullable=True)  # Which part of system (inventory, tickets, etc.)
    estimated_effort = Column(String(50), nullable=True)  # Small, Medium, Large, XL
    business_value = Column(String(50), nullable=True)  # Low, Medium, High, Critical
    acceptance_criteria = Column(Text, nullable=True)

    # Relationships
    requester = relationship('User', foreign_keys=[requester_id], backref='requested_features')
    assignee = relationship('User', foreign_keys=[assignee_id], backref='assigned_features')
    approver = relationship('User', foreign_keys=[approver_id], backref='features_to_approve')
    target_release = relationship('Release', back_populates='features')
    comments = relationship('FeatureComment', back_populates='feature', cascade='all, delete-orphan')
    changelog_entries = relationship('ChangelogEntry', back_populates='feature')

    @property
    def display_id(self):
        """Return a formatted feature ID (e.g., 'FEAT-0001')"""
        return f'FEAT-{self.id:04d}'

    @property
    def is_completed(self):
        """Check if this feature is completed"""
        return self.status == FeatureStatus.COMPLETED

    @property
    def is_active(self):
        """Check if this feature is actively being worked on"""
        return self.status in [FeatureStatus.IN_PLANNING, FeatureStatus.IN_DEVELOPMENT, FeatureStatus.IN_TESTING]

    @property
    def needs_approval(self):
        """Check if this feature needs approval"""
        return self.status == FeatureStatus.PENDING_APPROVAL

    @property
    def is_approved(self):
        """Check if this feature is approved"""
        return self.status == FeatureStatus.APPROVED

    @property
    def is_rejected(self):
        """Check if this feature is rejected"""
        return self.status == FeatureStatus.REJECTED

    def get_status_color(self):
        """Return CSS color class for status"""
        colors = {
            FeatureStatus.REQUESTED: 'text-blue-600 bg-blue-100',
            FeatureStatus.PENDING_APPROVAL: 'text-indigo-600 bg-indigo-100',
            FeatureStatus.APPROVED: 'text-emerald-600 bg-emerald-100',
            FeatureStatus.REJECTED: 'text-red-600 bg-red-100',
            FeatureStatus.IN_PLANNING: 'text-yellow-600 bg-yellow-100',
            FeatureStatus.IN_DEVELOPMENT: 'text-orange-600 bg-orange-100',
            FeatureStatus.IN_TESTING: 'text-purple-600 bg-purple-100',
            FeatureStatus.COMPLETED: 'text-green-600 bg-green-100',
            FeatureStatus.CANCELLED: 'text-red-600 bg-red-100'
        }
        return colors.get(self.status, 'text-gray-600 bg-gray-100')

    def get_priority_color(self):
        """Return CSS color class for priority"""
        colors = {
            FeaturePriority.LOW: 'text-gray-600 bg-gray-100',
            FeaturePriority.MEDIUM: 'text-yellow-600 bg-yellow-100',
            FeaturePriority.HIGH: 'text-orange-600 bg-orange-100',
            FeaturePriority.CRITICAL: 'text-red-600 bg-red-100'
        }
        return colors.get(self.priority, 'text-gray-600 bg-gray-100')

# Feature-specific comment model
class FeatureComment(Base):
    __tablename__ = 'feature_comments'

    id = Column(Integer, primary_key=True)
    content = Column(Text, nullable=False)
    feature_id = Column(Integer, ForeignKey('feature_requests.id'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)

    # Relationships
    feature = relationship('FeatureRequest', back_populates='comments')
    user = relationship('User', backref='feature_comments')

    def __repr__(self):
        return f'<FeatureComment {self.id}: {self.content[:50]}...>'