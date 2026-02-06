"""
SLA Calculator Utility
Calculates working days excluding weekends and queue-specific holidays
"""
from datetime import datetime, date, timedelta, time
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)


def get_queue_holidays(queue_id: int, start_date: date, end_date: date, db=None) -> List[date]:
    """
    Get all holidays for a queue between two dates

    Args:
        queue_id: The queue ID to get holidays for
        start_date: Start of the date range
        end_date: End of the date range
        db: Optional database session to reuse

    Returns:
        List of holiday dates
    """
    from database import SessionLocal
    from models.queue_holiday import QueueHoliday

    should_close = db is None
    if db is None:
        db = SessionLocal()
    try:
        holidays = db.query(QueueHoliday).filter(
            QueueHoliday.queue_id == queue_id,
            QueueHoliday.holiday_date >= start_date,
            QueueHoliday.holiday_date <= end_date
        ).all()
        return [h.holiday_date for h in holidays]
    except Exception as e:
        logger.error(f"Error fetching holidays for queue {queue_id}: {str(e)}")
        return []
    finally:
        if should_close:
            db.close()


def is_working_day(check_date: date, holidays: List[date]) -> bool:
    """
    Check if a date is a working day (not weekend, not holiday)

    Args:
        check_date: The date to check
        holidays: List of holiday dates to exclude

    Returns:
        True if the date is a working day
    """
    # Weekend check (Saturday=5, Sunday=6)
    if check_date.weekday() >= 5:
        return False
    # Holiday check
    if check_date in holidays:
        return False
    return True


def calculate_sla_due_date(
    start_date: datetime,
    working_days: int,
    queue_id: int,
    db=None
) -> datetime:
    """
    Calculate the SLA due date from start date + working days,
    excluding weekends and queue-specific holidays.

    Args:
        start_date: The ticket creation date
        working_days: Number of working days for SLA
        queue_id: The queue ID to get holidays for
        db: Optional database session to reuse

    Returns:
        datetime: The calculated due date (end of business day 5 PM)
    """
    if working_days <= 0:
        return start_date

    current_date = start_date.date() if isinstance(start_date, datetime) else start_date

    # Get holidays for a reasonable range (working_days * 3 to account for weekends/holidays)
    end_search = current_date + timedelta(days=working_days * 3)
    holidays = get_queue_holidays(queue_id, current_date, end_search, db=db)

    days_counted = 0
    while days_counted < working_days:
        current_date += timedelta(days=1)
        if is_working_day(current_date, holidays):
            days_counted += 1

    # Return datetime with end of business day (5 PM)
    return datetime.combine(current_date, time(17, 0))


def get_sla_config_for_ticket(ticket, db=None) -> Optional[dict]:
    """
    Get the SLA configuration for a ticket based on its queue and category

    Args:
        ticket: The ticket object
        db: Optional database session to reuse

    Returns:
        dict with SLA config info or None if no SLA configured
    """
    from database import SessionLocal
    from models.sla_config import SLAConfig

    if not ticket.queue_id or not ticket.category:
        return None

    should_close = db is None
    if db is None:
        db = SessionLocal()
    try:
        sla_config = db.query(SLAConfig).filter(
            SLAConfig.queue_id == ticket.queue_id,
            SLAConfig.ticket_category == ticket.category,
            SLAConfig.is_active == True
        ).first()

        if sla_config:
            return {
                'id': sla_config.id,
                'working_days': sla_config.working_days,
                'description': sla_config.description
            }
        return None
    except Exception as e:
        logger.error(f"Error fetching SLA config for ticket {ticket.id}: {str(e)}")
        return None
    finally:
        if should_close:
            db.close()


def get_sla_status(ticket, db=None) -> dict:
    """
    Get the SLA status for a ticket.

    Args:
        ticket: The ticket object
        db: Optional database session to reuse (improves performance for batch processing)

    Returns:
        dict: {
            'has_sla': bool,
            'due_date': datetime or None,
            'working_days': int or None,
            'is_breached': bool,
            'days_remaining': int or None (negative if breached),
            'hours_remaining': int or None,
            'status': 'on_track' | 'at_risk' | 'breached' | 'no_sla' | 'resolved'
        }
    """
    from models.ticket import TicketStatus

    # Skip if ticket is resolved
    if ticket.status in [TicketStatus.RESOLVED, TicketStatus.RESOLVED_DELIVERED]:
        return {
            'has_sla': False,
            'status': 'resolved',
            'due_date': None,
            'working_days': None,
            'is_breached': False,
            'days_remaining': None,
            'hours_remaining': None
        }

    # Get SLA config (reuse session if provided)
    sla_config = get_sla_config_for_ticket(ticket, db=db)

    if not sla_config:
        return {
            'has_sla': False,
            'status': 'no_sla',
            'due_date': None,
            'working_days': None,
            'is_breached': False,
            'days_remaining': None,
            'hours_remaining': None
        }

    # Calculate due date (reuse session if provided)
    due_date = calculate_sla_due_date(
        ticket.created_at,
        sla_config['working_days'],
        ticket.queue_id,
        db=db
    )

    now = datetime.utcnow()
    time_diff = due_date - now
    days_remaining = time_diff.days
    hours_remaining = int(time_diff.total_seconds() / 3600)
    is_breached = now > due_date

    # Determine status
    if is_breached:
        status = 'breached'
    elif days_remaining <= 1:  # Less than or equal to 1 day remaining
        status = 'at_risk'
    else:
        status = 'on_track'

    return {
        'has_sla': True,
        'due_date': due_date,
        'working_days': sla_config['working_days'],
        'is_breached': is_breached,
        'days_remaining': days_remaining,
        'hours_remaining': hours_remaining,
        'status': status
    }


def get_batch_sla_status(tickets, db=None) -> dict:
    """
    Get SLA status for multiple tickets efficiently using batch queries.
    Instead of N+1 queries, loads all SLA configs and holidays in bulk.

    Args:
        tickets: List of ticket objects
        db: Optional database session to reuse

    Returns:
        dict mapping ticket_id -> SLA status dict (only tickets with SLA)
    """
    from database import SessionLocal
    from models.sla_config import SLAConfig
    from models.queue_holiday import QueueHoliday
    from models.ticket import TicketStatus

    if not tickets:
        return {}

    should_close = db is None
    if db is None:
        db = SessionLocal()

    try:
        result = {}

        # Collect unique queue_id + category pairs from non-resolved tickets
        queue_category_pairs = set()
        queue_ids = set()
        for ticket in tickets:
            if ticket.status in [TicketStatus.RESOLVED, TicketStatus.RESOLVED_DELIVERED]:
                continue
            if ticket.queue_id and ticket.category:
                queue_category_pairs.add((ticket.queue_id, ticket.category))
                queue_ids.add(ticket.queue_id)

        if not queue_category_pairs:
            return {}

        # Batch load all active SLA configs for relevant queues
        all_sla_configs = db.query(SLAConfig).filter(
            SLAConfig.queue_id.in_(queue_ids),
            SLAConfig.is_active == True
        ).all()

        # Index by (queue_id, category)
        sla_config_map = {}
        for cfg in all_sla_configs:
            sla_config_map[(cfg.queue_id, cfg.ticket_category)] = {
                'id': cfg.id,
                'working_days': cfg.working_days,
                'description': cfg.description
            }

        # Batch load holidays for all relevant queues
        now = datetime.utcnow()
        earliest_ticket = min((t.created_at for t in tickets if t.created_at), default=now)
        earliest_date = earliest_ticket.date() if isinstance(earliest_ticket, datetime) else earliest_ticket
        max_working_days = max((c['working_days'] for c in sla_config_map.values()), default=30)
        end_search = now.date() + timedelta(days=max_working_days * 3)

        all_holidays = db.query(QueueHoliday).filter(
            QueueHoliday.queue_id.in_(queue_ids),
            QueueHoliday.holiday_date >= earliest_date,
            QueueHoliday.holiday_date <= end_search
        ).all()

        # Index holidays by queue_id
        holidays_by_queue = {}
        for h in all_holidays:
            holidays_by_queue.setdefault(h.queue_id, []).append(h.holiday_date)

        # Now calculate SLA for each ticket using cached data
        for ticket in tickets:
            if ticket.status in [TicketStatus.RESOLVED, TicketStatus.RESOLVED_DELIVERED]:
                continue

            if not ticket.queue_id or not ticket.category:
                continue

            sla_config = sla_config_map.get((ticket.queue_id, ticket.category))
            if not sla_config:
                continue

            # Calculate due date in-memory
            working_days = sla_config['working_days']
            if working_days <= 0:
                due_date = ticket.created_at
            else:
                current_date = ticket.created_at.date() if isinstance(ticket.created_at, datetime) else ticket.created_at
                queue_holidays = holidays_by_queue.get(ticket.queue_id, [])
                days_counted = 0
                while days_counted < working_days:
                    current_date += timedelta(days=1)
                    if current_date.weekday() < 5 and current_date not in queue_holidays:
                        days_counted += 1
                due_date = datetime.combine(current_date, time(17, 0))

            time_diff = due_date - now
            days_remaining = time_diff.days
            is_breached = now > due_date

            if is_breached:
                status = 'breached'
            elif days_remaining <= 1:
                status = 'at_risk'
            else:
                status = 'on_track'

            result[ticket.id] = {
                'status': status,
                'days_remaining': days_remaining,
                'due_date': due_date.isoformat() if due_date else None
            }

        return result
    except Exception as e:
        logger.error(f"Error in batch SLA calculation: {str(e)}")
        return {}
    finally:
        if should_close:
            db.close()


def get_sla_summary_stats(tickets: list) -> dict:
    """
    Get summary statistics for a list of tickets

    Args:
        tickets: List of ticket objects

    Returns:
        dict with on_track, at_risk, breached counts
    """
    on_track = 0
    at_risk = 0
    breached = 0
    no_sla = 0

    for ticket in tickets:
        sla_info = get_sla_status(ticket)
        if sla_info['status'] == 'on_track':
            on_track += 1
        elif sla_info['status'] == 'at_risk':
            at_risk += 1
        elif sla_info['status'] == 'breached':
            breached += 1
        elif sla_info['status'] == 'no_sla':
            no_sla += 1

    return {
        'on_track': on_track,
        'at_risk': at_risk,
        'breached': breached,
        'no_sla': no_sla,
        'total_with_sla': on_track + at_risk + breached
    }
