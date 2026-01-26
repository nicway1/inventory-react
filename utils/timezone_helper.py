"""
Timezone helper utilities for the inventory system.
Handles conversion from UTC to the configured system timezone.
"""

from datetime import datetime
from typing import Optional
import pytz

# Primary timezones (26 major zones)
PRIMARY_TIMEZONES = [
    ('UTC', 'UTC (Coordinated Universal Time)', 0),
    ('Pacific/Midway', 'Midway Island (UTC-11)', -11),
    ('Pacific/Honolulu', 'Hawaii (UTC-10)', -10),
    ('America/Anchorage', 'Alaska (UTC-9)', -9),
    ('America/Los_Angeles', 'Pacific Time - US & Canada (UTC-8)', -8),
    ('America/Denver', 'Mountain Time - US & Canada (UTC-7)', -7),
    ('America/Chicago', 'Central Time - US & Canada (UTC-6)', -6),
    ('America/New_York', 'Eastern Time - US & Canada (UTC-5)', -5),
    ('America/Caracas', 'Venezuela (UTC-4:30)', -4.5),
    ('America/Sao_Paulo', 'Brasilia (UTC-3)', -3),
    ('Atlantic/South_Georgia', 'Mid-Atlantic (UTC-2)', -2),
    ('Atlantic/Azores', 'Azores (UTC-1)', -1),
    ('Europe/London', 'London, Dublin, Lisbon (UTC+0)', 0),
    ('Europe/Paris', 'Paris, Berlin, Amsterdam (UTC+1)', 1),
    ('Europe/Helsinki', 'Helsinki, Kyiv, Bucharest (UTC+2)', 2),
    ('Asia/Jerusalem', 'Israel (UTC+2)', 2),
    ('Europe/Moscow', 'Moscow, St. Petersburg (UTC+3)', 3),
    ('Asia/Dubai', 'Dubai, Abu Dhabi (UTC+4)', 4),
    ('Asia/Karachi', 'Karachi, Islamabad (UTC+5)', 5),
    ('Asia/Kolkata', 'Mumbai, New Delhi (UTC+5:30)', 5.5),
    ('Asia/Dhaka', 'Dhaka (UTC+6)', 6),
    ('Asia/Bangkok', 'Bangkok, Hanoi, Jakarta (UTC+7)', 7),
    ('Asia/Singapore', 'Singapore, Kuala Lumpur, Perth (UTC+8)', 8),
    ('Asia/Tokyo', 'Tokyo, Seoul (UTC+9)', 9),
    ('Australia/Sydney', 'Sydney, Melbourne (UTC+10)', 10),
    ('Pacific/Auckland', 'Auckland, Wellington (UTC+12)', 12),
]


def get_timezone_choices():
    """Get list of timezone choices for select dropdown."""
    return [(tz[0], tz[1]) for tz in PRIMARY_TIMEZONES]


def get_system_timezone() -> str:
    """
    Get the configured system timezone from database settings.
    Falls back to 'Asia/Singapore' if not configured.
    """
    try:
        from models import db_manager
        from models.system_settings import SystemSettings

        db_session = db_manager.get_session()
        try:
            setting = db_session.query(SystemSettings).filter_by(
                setting_key='system_timezone'
            ).first()
            if setting and setting.setting_value:
                return setting.setting_value
        finally:
            db_session.close()
    except Exception:
        pass

    # Default to Singapore timezone
    return 'Asia/Singapore'


def convert_to_local(dt: Optional[datetime], timezone_str: Optional[str] = None) -> Optional[datetime]:
    """
    Convert a UTC datetime to the specified or system timezone.

    Args:
        dt: datetime object (assumed to be in UTC if naive)
        timezone_str: Optional timezone string. If None, uses system setting.

    Returns:
        datetime object in the local timezone
    """
    if dt is None:
        return None

    if timezone_str is None:
        timezone_str = get_system_timezone()

    try:
        tz = pytz.timezone(timezone_str)

        # If datetime is naive, assume it's UTC
        if dt.tzinfo is None:
            dt = pytz.UTC.localize(dt)

        return dt.astimezone(tz)
    except Exception:
        # Return original datetime if conversion fails
        return dt


def format_datetime(dt: Optional[datetime], fmt: str = '%b %d, %H:%M',
                    timezone_str: Optional[str] = None) -> str:
    """
    Format a datetime in the system timezone.

    Args:
        dt: datetime object
        fmt: strftime format string
        timezone_str: Optional timezone. If None, uses system setting.

    Returns:
        Formatted datetime string
    """
    if dt is None:
        return 'Unknown'

    local_dt = convert_to_local(dt, timezone_str)
    if local_dt is None:
        return 'Unknown'

    return local_dt.strftime(fmt)


def format_datetime_full(dt: Optional[datetime], timezone_str: Optional[str] = None) -> str:
    """Format datetime with full date and time."""
    return format_datetime(dt, '%Y-%m-%d %H:%M:%S', timezone_str)


def format_datetime_short(dt: Optional[datetime], timezone_str: Optional[str] = None) -> str:
    """Format datetime with short format (Jan 15, 14:30)."""
    return format_datetime(dt, '%b %d, %H:%M', timezone_str)


def format_time_only(dt: Optional[datetime], timezone_str: Optional[str] = None) -> str:
    """Format time only (14:30)."""
    return format_datetime(dt, '%H:%M', timezone_str)


def format_date_only(dt: Optional[datetime], timezone_str: Optional[str] = None) -> str:
    """Format date only (2026-01-15)."""
    return format_datetime(dt, '%Y-%m-%d', timezone_str)


def get_current_time(timezone_str: Optional[str] = None) -> datetime:
    """Get current time in the system timezone."""
    if timezone_str is None:
        timezone_str = get_system_timezone()

    try:
        tz = pytz.timezone(timezone_str)
        return datetime.now(tz)
    except Exception:
        return datetime.utcnow()


# Jinja2 template filter functions
def jinja_localtime(dt, fmt='%b %d, %H:%M'):
    """Jinja2 filter to format datetime in system timezone."""
    return format_datetime(dt, fmt)


def jinja_localtime_full(dt):
    """Jinja2 filter for full datetime format."""
    return format_datetime_full(dt)


def jinja_localtime_short(dt):
    """Jinja2 filter for short datetime format."""
    return format_datetime_short(dt)


def register_jinja_filters(app):
    """Register timezone filters with Flask app."""
    app.jinja_env.filters['localtime'] = jinja_localtime
    app.jinja_env.filters['localtime_full'] = jinja_localtime_full
    app.jinja_env.filters['localtime_short'] = jinja_localtime_short

    # Also add a global function to get system timezone
    app.jinja_env.globals['get_system_timezone'] = get_system_timezone