from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum as SQLEnum, Text
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from models.base import Base

class ChangelogEntryType(enum.Enum):
    FEATURE = "Feature"
    BUG_FIX = "Bug Fix"
    IMPROVEMENT = "Improvement"
    BREAKING_CHANGE = "Breaking Change"
    SECURITY = "Security"
    DEPRECATION = "Deprecation"
    DOCUMENTATION = "Documentation"

class ChangelogEntry(Base):
    __tablename__ = 'changelog_entries'

    id = Column(Integer, primary_key=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    entry_type = Column(SQLEnum(ChangelogEntryType), default=ChangelogEntryType.FEATURE)

    # Release relationship
    release_id = Column(Integer, ForeignKey('releases.id'), nullable=False)

    # Link to source (feature or bug)
    feature_id = Column(Integer, ForeignKey('feature_requests.id'), nullable=True)
    bug_id = Column(Integer, ForeignKey('bug_reports.id'), nullable=True)

    # User who created this entry
    created_by_id = Column(Integer, ForeignKey('users.id'), nullable=False)

    # Dates
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)

    # Display order in changelog
    sort_order = Column(Integer, default=0)

    # Additional metadata
    is_breaking_change = Column(String(10), default='No')  # Yes/No
    impact_description = Column(Text, nullable=True)
    migration_notes = Column(Text, nullable=True)

    # Relationships
    release = relationship('Release', back_populates='changelog_entries')
    feature = relationship('FeatureRequest', back_populates='changelog_entries')
    bug = relationship('BugReport', back_populates='changelog_entries')
    created_by = relationship('User', backref='created_changelog_entries')

    @property
    def display_id(self):
        """Return a formatted changelog entry ID (e.g., 'CHANGE-0001')"""
        return f'CHANGE-{self.id:04d}'

    @property
    def source_item(self):
        """Return the linked feature or bug"""
        if self.feature:
            return self.feature
        elif self.bug:
            return self.bug
        return None

    @property
    def source_type(self):
        """Return the type of source item"""
        if self.feature:
            return 'Feature'
        elif self.bug:
            return 'Bug Fix'
        return 'Manual Entry'

    @property
    def markdown_format(self):
        """Return changelog entry in markdown format"""
        source_ref = ""
        if self.feature:
            source_ref = f" ({self.feature.display_id})"
        elif self.bug:
            source_ref = f" ({self.bug.display_id})"

        breaking_indicator = ""
        if self.is_breaking_change == 'Yes':
            breaking_indicator = " **[BREAKING]**"

        return f"- {self.title}{source_ref}{breaking_indicator}"

    def get_type_color(self):
        """Return CSS color class for entry type"""
        colors = {
            ChangelogEntryType.FEATURE: 'text-blue-600 bg-blue-100',
            ChangelogEntryType.BUG_FIX: 'text-green-600 bg-green-100',
            ChangelogEntryType.IMPROVEMENT: 'text-purple-600 bg-purple-100',
            ChangelogEntryType.BREAKING_CHANGE: 'text-red-600 bg-red-100',
            ChangelogEntryType.SECURITY: 'text-orange-600 bg-orange-100',
            ChangelogEntryType.DEPRECATION: 'text-yellow-600 bg-yellow-100',
            ChangelogEntryType.DOCUMENTATION: 'text-gray-600 bg-gray-100'
        }
        return colors.get(self.entry_type, 'text-gray-600 bg-gray-100')

    def __repr__(self):
        return f'<ChangelogEntry {self.title}: {self.entry_type.value}>'