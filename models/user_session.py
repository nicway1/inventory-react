"""
UserSession model for tracking user login sessions and activity
Used for developer analytics and usage monitoring
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, Text
from sqlalchemy.orm import relationship, backref
from models.base import Base


class UserSession(Base):
    __tablename__ = 'user_sessions'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)

    # Session tracking
    session_token = Column(String(100), nullable=True)  # Flask session ID

    # Timestamps
    login_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    logout_at = Column(DateTime, nullable=True)
    last_activity_at = Column(DateTime, default=datetime.utcnow)

    # Session metadata
    ip_address = Column(String(50), nullable=True)
    user_agent = Column(String(500), nullable=True)
    device_type = Column(String(50), nullable=True)  # desktop, mobile, tablet
    browser = Column(String(100), nullable=True)
    os = Column(String(100), nullable=True)

    # Session status
    is_active = Column(Boolean, default=True)
    logout_reason = Column(String(50), nullable=True)  # manual, timeout, forced

    # Page tracking
    pages_visited = Column(Integer, default=0)
    last_page = Column(String(200), nullable=True)

    # Relationships
    user = relationship("User", backref=backref("sessions", cascade="all, delete-orphan"))

    @property
    def duration_seconds(self):
        """Calculate session duration in seconds"""
        end_time = self.logout_at or datetime.utcnow()
        return int((end_time - self.login_at).total_seconds())

    @property
    def duration_formatted(self):
        """Return formatted duration string"""
        seconds = self.duration_seconds
        if seconds < 60:
            return f"{seconds}s"
        elif seconds < 3600:
            minutes = seconds // 60
            return f"{minutes}m"
        else:
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            return f"{hours}h {minutes}m"

    @property
    def is_currently_active(self):
        """Check if session is currently active (activity in last 15 minutes)"""
        if not self.is_active:
            return False
        if self.logout_at:
            return False
        # Consider active if last activity was within 15 minutes
        from datetime import timedelta
        return (datetime.utcnow() - self.last_activity_at) < timedelta(minutes=15)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'user_name': self.user.username if self.user else None,
            'login_at': self.login_at.isoformat() if self.login_at else None,
            'logout_at': self.logout_at.isoformat() if self.logout_at else None,
            'last_activity_at': self.last_activity_at.isoformat() if self.last_activity_at else None,
            'duration': self.duration_formatted,
            'duration_seconds': self.duration_seconds,
            'ip_address': self.ip_address,
            'device_type': self.device_type,
            'browser': self.browser,
            'os': self.os,
            'is_active': self.is_active,
            'is_currently_active': self.is_currently_active,
            'pages_visited': self.pages_visited,
            'last_page': self.last_page
        }

    def __repr__(self):
        return f'<UserSession {self.id}: User {self.user_id} at {self.login_at}>'


def parse_user_agent(user_agent_string):
    """Parse user agent string to extract device, browser, and OS info"""
    if not user_agent_string:
        return {'device_type': 'unknown', 'browser': 'unknown', 'os': 'unknown'}

    ua = user_agent_string.lower()

    # Detect device type
    if 'mobile' in ua or 'android' in ua or 'iphone' in ua:
        device_type = 'mobile'
    elif 'tablet' in ua or 'ipad' in ua:
        device_type = 'tablet'
    else:
        device_type = 'desktop'

    # Detect browser
    if 'edg' in ua:
        browser = 'Edge'
    elif 'chrome' in ua:
        browser = 'Chrome'
    elif 'firefox' in ua:
        browser = 'Firefox'
    elif 'safari' in ua:
        browser = 'Safari'
    elif 'opera' in ua or 'opr' in ua:
        browser = 'Opera'
    else:
        browser = 'Other'

    # Detect OS
    if 'windows' in ua:
        os_name = 'Windows'
    elif 'mac os' in ua or 'macos' in ua:
        os_name = 'macOS'
    elif 'linux' in ua:
        os_name = 'Linux'
    elif 'android' in ua:
        os_name = 'Android'
    elif 'iphone' in ua or 'ipad' in ua:
        os_name = 'iOS'
    else:
        os_name = 'Other'

    return {
        'device_type': device_type,
        'browser': browser,
        'os': os_name
    }
