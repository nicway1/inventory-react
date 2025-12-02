from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from models.base import Base


class DevBlogEntry(Base):
    """Dev blog entry - automatically created from git commits"""
    __tablename__ = 'dev_blog_entries'

    id = Column(Integer, primary_key=True)

    # Git info
    commit_hash = Column(String(40), unique=True, nullable=False)
    commit_short = Column(String(7), nullable=False)
    branch = Column(String(100), nullable=True)

    # Parsed commit info
    commit_type = Column(String(50), nullable=True)  # feat, fix, refactor, docs, etc.
    scope = Column(String(100), nullable=True)  # (tickets), (inventory), etc.
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)

    # Author info
    author_name = Column(String(200), nullable=True)
    author_email = Column(String(200), nullable=True)

    # Dates
    commit_date = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Display settings
    is_visible = Column(Boolean, default=True)  # Can hide minor commits
    is_highlighted = Column(Boolean, default=False)  # Feature important commits

    # Link to user if email matches
    user_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    user = relationship('User', backref='dev_blog_entries')

    @property
    def display_type(self):
        """Return formatted type for display"""
        type_labels = {
            'feat': 'Feature',
            'fix': 'Bug Fix',
            'refactor': 'Refactor',
            'docs': 'Documentation',
            'style': 'Style',
            'test': 'Test',
            'chore': 'Chore',
            'perf': 'Performance',
            'ci': 'CI/CD',
            'build': 'Build',
            'revert': 'Revert'
        }
        return type_labels.get(self.commit_type, self.commit_type or 'Update')

    @property
    def type_color(self):
        """Return CSS color for type"""
        colors = {
            'feat': '#2e844a',      # Green
            'fix': '#c62828',       # Red
            'refactor': '#0176d3',  # Blue
            'docs': '#6f42c1',      # Purple
            'style': '#17a2b8',     # Cyan
            'test': '#fd7e14',      # Orange
            'chore': '#6c757d',     # Gray
            'perf': '#e83e8c',      # Pink
            'ci': '#20c997',        # Teal
            'build': '#343a40',     # Dark
            'revert': '#dc3545'     # Red
        }
        return colors.get(self.commit_type, '#6c757d')

    @property
    def type_icon(self):
        """Return Font Awesome icon for type"""
        icons = {
            'feat': 'fa-star',
            'fix': 'fa-bug',
            'refactor': 'fa-sync',
            'docs': 'fa-book',
            'style': 'fa-paint-brush',
            'test': 'fa-flask',
            'chore': 'fa-wrench',
            'perf': 'fa-tachometer-alt',
            'ci': 'fa-cogs',
            'build': 'fa-hammer',
            'revert': 'fa-undo'
        }
        return icons.get(self.commit_type, 'fa-code-commit')

    def to_dict(self):
        return {
            'id': self.id,
            'commit_hash': self.commit_hash,
            'commit_short': self.commit_short,
            'branch': self.branch,
            'commit_type': self.commit_type,
            'display_type': self.display_type,
            'scope': self.scope,
            'title': self.title,
            'description': self.description,
            'author_name': self.author_name,
            'commit_date': self.commit_date.isoformat() if self.commit_date else None,
            'type_color': self.type_color,
            'type_icon': self.type_icon
        }

    def __repr__(self):
        return f'<DevBlogEntry {self.commit_short}: {self.title[:50]}>'
