from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum as SQLEnum, Text, Date, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime, date
import enum
from models.base import Base

class ReleaseType(enum.Enum):
    MAJOR = "Major"
    MINOR = "Minor"
    PATCH = "Patch"
    HOTFIX = "Hotfix"

class ReleaseStatus(enum.Enum):
    PLANNING = "Planning"
    IN_DEVELOPMENT = "In Development"
    TESTING = "Testing"
    READY = "Ready"
    RELEASED = "Released"
    CANCELLED = "Cancelled"

class Release(Base):
    __tablename__ = 'releases'

    id = Column(Integer, primary_key=True)
    version = Column(String(20), unique=True, nullable=False)  # e.g., "1.2.3", "2.0.0-beta"
    name = Column(String(100), nullable=True)  # e.g., "Winter Release", "Bug Fix Release"
    description = Column(Text, nullable=True)
    release_type = Column(SQLEnum(ReleaseType), default=ReleaseType.MINOR)
    status = Column(SQLEnum(ReleaseStatus), default=ReleaseStatus.PLANNING)

    # Dates
    planned_date = Column(Date, nullable=True)
    release_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)

    # Release management
    release_manager_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    is_pre_release = Column(Boolean, default=False)  # alpha, beta, rc versions
    is_hotfix = Column(Boolean, default=False)

    # Release notes and documentation
    release_notes = Column(Text, nullable=True)
    breaking_changes = Column(Text, nullable=True)
    upgrade_instructions = Column(Text, nullable=True)

    # Metrics and tracking
    total_features = Column(Integer, default=0)
    total_bugs_fixed = Column(Integer, default=0)
    deployment_environment = Column(String(50), nullable=True)  # staging, production
    rollback_plan = Column(Text, nullable=True)

    # Git integration (optional)
    git_tag = Column(String(50), nullable=True)
    git_commit_hash = Column(String(40), nullable=True)
    git_branch = Column(String(100), nullable=True)

    # Relationships
    release_manager = relationship('User', backref='managed_releases')
    features = relationship('FeatureRequest', back_populates='target_release')
    fixed_bugs = relationship('BugReport', back_populates='fixed_in_release')
    changelog_entries = relationship('ChangelogEntry', back_populates='release', cascade='all, delete-orphan')

    @property
    def display_version(self):
        """Return formatted version with type indicator"""
        if self.is_pre_release:
            return f"{self.version} (Pre-release)"
        elif self.is_hotfix:
            return f"{self.version} (Hotfix)"
        return self.version

    @property
    def is_released(self):
        """Check if this release has been deployed"""
        return self.status == ReleaseStatus.RELEASED

    @property
    def is_active(self):
        """Check if this release is actively being worked on"""
        return self.status in [ReleaseStatus.PLANNING, ReleaseStatus.IN_DEVELOPMENT, ReleaseStatus.TESTING]

    @property
    def days_until_release(self):
        """Calculate days until planned release"""
        if self.planned_date:
            today = date.today()
            delta = self.planned_date - today
            return delta.days
        return None

    @property
    def completion_percentage(self):
        """Calculate completion percentage based on completed features and bugs"""
        total_items = len(self.features) + len(self.fixed_bugs)
        if total_items == 0:
            return 0

        completed_features = len([f for f in self.features if f.is_completed])
        resolved_bugs = len([b for b in self.fixed_bugs if b.is_resolved])
        completed_items = completed_features + resolved_bugs

        return int((completed_items / total_items) * 100)

    def get_status_color(self):
        """Return CSS color class for status"""
        colors = {
            ReleaseStatus.PLANNING: 'text-blue-600 bg-blue-100',
            ReleaseStatus.IN_DEVELOPMENT: 'text-yellow-600 bg-yellow-100',
            ReleaseStatus.TESTING: 'text-purple-600 bg-purple-100',
            ReleaseStatus.READY: 'text-green-600 bg-green-100',
            ReleaseStatus.RELEASED: 'text-gray-600 bg-gray-100',
            ReleaseStatus.CANCELLED: 'text-red-600 bg-red-100'
        }
        return colors.get(self.status, 'text-gray-600 bg-gray-100')

    def get_type_color(self):
        """Return CSS color class for release type"""
        colors = {
            ReleaseType.MAJOR: 'text-red-600 bg-red-100',
            ReleaseType.MINOR: 'text-blue-600 bg-blue-100',
            ReleaseType.PATCH: 'text-green-600 bg-green-100',
            ReleaseType.HOTFIX: 'text-orange-600 bg-orange-100'
        }
        return colors.get(self.release_type, 'text-gray-600 bg-gray-100')

    def generate_changelog(self):
        """Generate changelog content from associated features and bugs"""
        changelog_parts = []

        if self.features:
            changelog_parts.append("### New Features")
            for feature in sorted(self.features, key=lambda f: f.created_at):
                if feature.is_completed:
                    changelog_parts.append(f"- {feature.title} ({feature.display_id})")

        if self.fixed_bugs:
            changelog_parts.append("\n### Bug Fixes")
            for bug in sorted(self.fixed_bugs, key=lambda b: b.created_at):
                if bug.is_resolved:
                    changelog_parts.append(f"- {bug.title} ({bug.display_id})")

        if self.breaking_changes:
            changelog_parts.append(f"\n### Breaking Changes\n{self.breaking_changes}")

        return "\n".join(changelog_parts)

    def update_metrics(self):
        """Update calculated metrics"""
        self.total_features = len([f for f in self.features if f.is_completed])
        self.total_bugs_fixed = len([b for b in self.fixed_bugs if b.is_resolved])

    @staticmethod
    def get_next_version(current_version, release_type):
        """Calculate next version number based on type"""
        try:
            parts = current_version.split('.')
            major, minor, patch = int(parts[0]), int(parts[1]), int(parts[2])

            if release_type == ReleaseType.MAJOR:
                return f"{major + 1}.0.0"
            elif release_type == ReleaseType.MINOR:
                return f"{major}.{minor + 1}.0"
            elif release_type == ReleaseType.PATCH:
                return f"{major}.{minor}.{patch + 1}"
            elif release_type == ReleaseType.HOTFIX:
                return f"{major}.{minor}.{patch + 1}"
        except (ValueError, IndexError):
            pass
        return "1.0.0"

    def __repr__(self):
        return f'<Release {self.version}: {self.name or "Unnamed"}>'