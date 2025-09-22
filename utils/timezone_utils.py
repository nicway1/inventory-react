"""
Timezone utilities for Singapore time handling
"""
from datetime import datetime, timezone, timedelta
import pytz

# Singapore timezone
SINGAPORE_TZ = pytz.timezone('Asia/Singapore')

def now_singapore():
    """
    Get current datetime in Singapore timezone
    """
    return datetime.now(SINGAPORE_TZ)

def utc_to_singapore(utc_dt):
    """
    Convert UTC datetime to Singapore timezone
    """
    if utc_dt is None:
        return None

    # If datetime is naive, assume it's UTC
    if utc_dt.tzinfo is None:
        utc_dt = utc_dt.replace(tzinfo=pytz.UTC)

    return utc_dt.astimezone(SINGAPORE_TZ)

def singapore_to_utc(sg_dt):
    """
    Convert Singapore datetime to UTC
    """
    if sg_dt is None:
        return None

    # If datetime is naive, assume it's Singapore time
    if sg_dt.tzinfo is None:
        sg_dt = SINGAPORE_TZ.localize(sg_dt)

    return sg_dt.astimezone(pytz.UTC)

def format_singapore_time(dt, format_str='%Y-%m-%d %H:%M:%S'):
    """
    Format datetime in Singapore timezone
    """
    if dt is None:
        return None

    sg_dt = utc_to_singapore(dt) if dt.tzinfo is None or dt.tzinfo == pytz.UTC else dt
    return sg_dt.strftime(format_str)

def parse_singapore_time(time_str, format_str='%Y-%m-%d %H:%M:%S'):
    """
    Parse time string as Singapore time and return UTC datetime
    """
    if not time_str:
        return None

    naive_dt = datetime.strptime(time_str, format_str)
    sg_dt = SINGAPORE_TZ.localize(naive_dt)
    return sg_dt.astimezone(pytz.UTC)

# Replacement for datetime.utcnow() to use Singapore time
def singapore_now_as_utc():
    """
    Get current Singapore time but store as UTC for database compatibility
    This is a drop-in replacement for datetime.utcnow()
    """
    sg_now = now_singapore()
    return singapore_to_utc(sg_now)