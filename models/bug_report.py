from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum as SQLEnum, Text
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from models.base import Base

class BugSeverity(enum.Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    CRITICAL = "Critical"

class BugStatus(enum.Enum):
    OPEN = "Open"
    IN_PROGRESS = "In Progress"
    TESTING = "Testing"
    RESOLVED = "Resolved"
    CLOSED = "Closed"
    REOPENED = "Reopened"

class BugPriority(enum.Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    URGENT = "Urgent"

class BugReport(Base):
    __tablename__ = 'bug_reports'

    id = Column(Integer, primary_key=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)

    # Bug classification
    severity = Column(SQLEnum(BugSeverity), default=BugSeverity.MEDIUM)
    priority = Column(SQLEnum(BugPriority), default=BugPriority.MEDIUM)
    status = Column(SQLEnum(BugStatus), default=BugStatus.OPEN)

    # Reproduction details
    steps_to_reproduce = Column(Text, nullable=True)
    expected_behavior = Column(Text, nullable=True)
    actual_behavior = Column(Text, nullable=True)

    # Environment and context
    component = Column(String(100), nullable=True)  # inventory, tickets, reports, etc.
    environment = Column(String(50), nullable=True)  # production, staging, development
    browser_version = Column(String(100), nullable=True)
    operating_system = Column(String(100), nullable=True)

    # User relationships
    reporter_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    assignee_id = Column(Integer, ForeignKey('users.id'), nullable=True)

    # Resolution details
    resolution_notes = Column(Text, nullable=True)
    resolution_date = Column(DateTime, nullable=True)

    # Related items
    duplicate_of_id = Column(Integer, ForeignKey('bug_reports.id'), nullable=True)
    related_ticket_id = Column(Integer, ForeignKey('tickets.id'), nullable=True)
    fixed_in_release_id = Column(Integer, ForeignKey('releases.id'), nullable=True)

    # Dates
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)

    # Additional tracking
    estimated_fix_time = Column(String(50), nullable=True)  # 1h, 4h, 1d, 1w, etc.
    regression_test_required = Column(String(10), default='No')  # Yes/No
    customer_impact = Column(String(50), nullable=True)  # None, Low, Medium, High, Critical
    screenshot_path = Column(String(500), nullable=True)  # Path to uploaded screenshot
    case_progress = Column(Integer, default=0)  # Progress percentage 0-100

    # Relationships
    reporter = relationship('User', foreign_keys=[reporter_id], backref='reported_bugs')
    assignee = relationship('User', foreign_keys=[assignee_id], backref='assigned_bugs')
    duplicate_of = relationship('BugReport', remote_side=[id], backref='duplicates')
    related_ticket = relationship('Ticket', backref='related_bugs')
    fixed_in_release = relationship('Release', back_populates='fixed_bugs')
    comments = relationship('BugComment', back_populates='bug', cascade='all, delete-orphan')
    changelog_entries = relationship('ChangelogEntry', back_populates='bug')
    tester_assignments = relationship('BugTesterAssignment', back_populates='bug', cascade='all, delete-orphan')
    test_cases = relationship('TestCase', back_populates='bug', cascade='all, delete-orphan')

    @property
    def display_id(self):
        """Return a formatted bug ID (e.g., 'BUG-0001')"""
        return f'BUG-{self.id:04d}'

    @property
    def is_open(self):
        """Check if this bug is still open"""
        return self.status in [BugStatus.OPEN, BugStatus.IN_PROGRESS, BugStatus.TESTING, BugStatus.REOPENED]

    @property
    def is_resolved(self):
        """Check if this bug is resolved"""
        return self.status in [BugStatus.RESOLVED, BugStatus.CLOSED]

    @property
    def resolution_time_days(self):
        """Calculate resolution time in days"""
        if self.resolution_date and self.created_at:
            return (self.resolution_date - self.created_at).days
        return None

    def get_status_color(self):
        """Return CSS color class for status"""
        colors = {
            BugStatus.OPEN: 'text-red-600 bg-red-100',
            BugStatus.IN_PROGRESS: 'text-yellow-600 bg-yellow-100',
            BugStatus.TESTING: 'text-blue-600 bg-blue-100',
            BugStatus.RESOLVED: 'text-green-600 bg-green-100',
            BugStatus.CLOSED: 'text-gray-600 bg-gray-100',
            BugStatus.REOPENED: 'text-orange-600 bg-orange-100'
        }
        return colors.get(self.status, 'text-gray-600 bg-gray-100')

    def get_severity_color(self):
        """Return CSS color class for severity"""
        colors = {
            BugSeverity.LOW: 'text-green-600 bg-green-100',
            BugSeverity.MEDIUM: 'text-yellow-600 bg-yellow-100',
            BugSeverity.HIGH: 'text-orange-600 bg-orange-100',
            BugSeverity.CRITICAL: 'text-red-600 bg-red-100'
        }
        return colors.get(self.severity, 'text-gray-600 bg-gray-100')

    def get_priority_color(self):
        """Return CSS color class for priority"""
        colors = {
            BugPriority.LOW: 'text-gray-600 bg-gray-100',
            BugPriority.MEDIUM: 'text-blue-600 bg-blue-100',
            BugPriority.HIGH: 'text-orange-600 bg-orange-100',
            BugPriority.URGENT: 'text-red-600 bg-red-100'
        }
        return colors.get(self.priority, 'text-gray-600 bg-gray-100')

# Bug-specific comment model
class BugComment(Base):
    __tablename__ = 'bug_comments'

    id = Column(Integer, primary_key=True)
    content = Column(Text, nullable=False)
    bug_id = Column(Integer, ForeignKey('bug_reports.id'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)

    # Special comment types
    comment_type = Column(String(20), default='comment')  # comment, resolution, workaround, etc.

    # Relationships
    bug = relationship('BugReport', back_populates='comments')
    user = relationship('User', backref='bug_comments')

    def __repr__(self):
        return f'<BugComment {self.id}: {self.content[:50]}...>'


# Tester model - users who test bugs and features
class Tester(Base):
    __tablename__ = 'testers'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, unique=True)
    specialization = Column(String(100), nullable=True)  # Frontend, Backend, Mobile, API, etc.
    is_active = Column(String(10), default='Yes')  # Yes/No
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)

    # Relationships
    user = relationship('User', backref='tester_profile')
    bug_assignments = relationship('BugTesterAssignment', back_populates='tester', cascade='all, delete-orphan')
    feature_assignments = relationship('FeatureTesterAssignment', back_populates='tester', cascade='all, delete-orphan')

    @property
    def name(self):
        """Get tester's name from user"""
        return self.user.username if self.user else 'Unknown'

    def __repr__(self):
        return f'<Tester {self.id}: {self.name}>'


# Bug-Tester assignment (many-to-many relationship)
class BugTesterAssignment(Base):
    __tablename__ = 'bug_tester_assignments'

    id = Column(Integer, primary_key=True)
    bug_id = Column(Integer, ForeignKey('bug_reports.id'), nullable=False)
    tester_id = Column(Integer, ForeignKey('testers.id'), nullable=False)
    assigned_at = Column(DateTime, default=datetime.utcnow)
    notified = Column(String(10), default='No')  # Yes/No - whether tester was notified
    notified_at = Column(DateTime, nullable=True)
    test_status = Column(String(20), default='Pending')  # Pending, In Progress, Passed, Failed
    test_notes = Column(Text, nullable=True)
    tested_at = Column(DateTime, nullable=True)

    # Relationships
    bug = relationship('BugReport', back_populates='tester_assignments')
    tester = relationship('Tester', back_populates='bug_assignments')

    def __repr__(self):
        return f'<BugTesterAssignment Bug:{self.bug_id} Tester:{self.tester_id}>'


# Test Case model - detailed test cases for bugs and features
class TestCase(Base):
    __tablename__ = 'test_cases'

    id = Column(Integer, primary_key=True)
    bug_id = Column(Integer, ForeignKey('bug_reports.id'), nullable=False)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    preconditions = Column(Text, nullable=True)  # What needs to be set up before testing
    test_steps = Column(Text, nullable=False)  # Step-by-step instructions
    expected_result = Column(Text, nullable=False)  # What should happen
    actual_result = Column(Text, nullable=True)  # What actually happened (filled by tester)
    status = Column(String(20), default='Pending')  # Pending, Passed, Failed, Blocked, Skipped
    priority = Column(String(20), default='Medium')  # Low, Medium, High
    test_data = Column(Text, nullable=True)  # Any specific data needed for testing

    # Testing info
    created_by_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    tested_by_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)
    tested_at = Column(DateTime, nullable=True)

    # Relationships
    bug = relationship('BugReport', back_populates='test_cases')
    created_by = relationship('User', foreign_keys=[created_by_id], backref='created_test_cases')
    tested_by = relationship('User', foreign_keys=[tested_by_id], backref='tested_test_cases')

    @property
    def display_id(self):
        """Return a formatted test case ID (e.g., 'TC-0001')"""
        return f'TC-{self.id:04d}'

    def get_status_color(self):
        """Return CSS color class for status"""
        colors = {
            'Pending': 'text-gray-600 bg-gray-100',
            'Passed': 'text-green-600 bg-green-100',
            'Failed': 'text-red-600 bg-red-100',
            'Blocked': 'text-orange-600 bg-orange-100',
            'Skipped': 'text-yellow-600 bg-yellow-100'
        }
        return colors.get(self.status, 'text-gray-600 bg-gray-100')

    def __repr__(self):
        return f'<TestCase {self.id}: {self.title}>'