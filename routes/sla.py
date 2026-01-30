"""
SLA Management Routes
Handles SLA configuration and holiday management per queue
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from utils.auth_decorators import login_required, admin_required
from utils.db_manager import DatabaseManager
from models.user import UserType
from models.sla_config import SLAConfig
from models.queue_holiday import QueueHoliday
from models.queue import Queue
from models.ticket import Ticket, TicketCategory, TicketStatus
from database import SessionLocal
from datetime import datetime, date
import logging

logger = logging.getLogger(__name__)
sla_bp = Blueprint('sla', __name__, url_prefix='/sla')
db_manager = DatabaseManager()


# ============= SLA Management Page =============

@sla_bp.route('/manage')
@login_required
def manage_sla():
    """SLA and Holiday management page"""
    user = db_manager.get_user(session['user_id'])
    if not user:
        flash('Please log in to continue', 'error')
        return redirect(url_for('auth.login'))

    # Check permissions - only super admin, developer, supervisor
    if user.user_type not in [UserType.SUPER_ADMIN, UserType.DEVELOPER, UserType.SUPERVISOR]:
        flash('Permission denied', 'error')
        return redirect(url_for('dashboard.index'))

    db = SessionLocal()
    try:
        queues = db.query(Queue).order_by(Queue.name).all()
        sla_configs = db.query(SLAConfig).order_by(SLAConfig.queue_id).all()
        holidays = db.query(QueueHoliday).order_by(
            QueueHoliday.holiday_date.desc()
        ).all()
        categories = list(TicketCategory)

        return render_template('sla/manage.html',
            user=user,
            queues=queues,
            sla_configs=sla_configs,
            holidays=holidays,
            categories=categories
        )
    finally:
        db.close()


# ============= SLA Configuration CRUD =============

@sla_bp.route('/api/configs')
@login_required
def list_sla_configs():
    """List all SLA configurations"""
    user = db_manager.get_user(session['user_id'])
    if not user or user.user_type not in [UserType.SUPER_ADMIN, UserType.DEVELOPER, UserType.SUPERVISOR]:
        return jsonify({'success': False, 'error': 'Permission denied'}), 403

    db = SessionLocal()
    try:
        configs = db.query(SLAConfig).order_by(SLAConfig.queue_id).all()
        return jsonify({
            'success': True,
            'configs': [c.to_dict() for c in configs]
        })
    finally:
        db.close()


@sla_bp.route('/api/config', methods=['POST'])
@login_required
def create_sla_config():
    """Create or update SLA configuration"""
    user = db_manager.get_user(session['user_id'])
    if not user or user.user_type not in [UserType.SUPER_ADMIN, UserType.DEVELOPER, UserType.SUPERVISOR]:
        return jsonify({'success': False, 'error': 'Permission denied'}), 403

    data = request.get_json()
    queue_id = data.get('queue_id')
    category = data.get('category')
    working_days = data.get('working_days')
    description = data.get('description', '')

    if not all([queue_id, category, working_days]):
        return jsonify({'success': False, 'error': 'Missing required fields'}), 400

    try:
        working_days = int(working_days)
        if working_days < 1:
            return jsonify({'success': False, 'error': 'Working days must be at least 1'}), 400
    except (ValueError, TypeError):
        return jsonify({'success': False, 'error': 'Invalid working days value'}), 400

    db = SessionLocal()
    try:
        # Parse category string to enum
        try:
            ticket_category = TicketCategory[category]
        except KeyError:
            return jsonify({'success': False, 'error': f'Invalid category: {category}'}), 400

        # Check for existing config
        existing = db.query(SLAConfig).filter(
            SLAConfig.queue_id == queue_id,
            SLAConfig.ticket_category == ticket_category
        ).first()

        if existing:
            existing.working_days = working_days
            existing.description = description
            existing.updated_at = datetime.utcnow()
            message = 'SLA configuration updated'
        else:
            config = SLAConfig(
                queue_id=queue_id,
                ticket_category=ticket_category,
                working_days=working_days,
                description=description,
                created_by_id=user.id
            )
            db.add(config)
            message = 'SLA configuration created'

        db.commit()
        return jsonify({'success': True, 'message': message})
    except Exception as e:
        db.rollback()
        logger.error(f"Error saving SLA config: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()


@sla_bp.route('/api/config/<int:config_id>', methods=['DELETE'])
@login_required
def delete_sla_config(config_id):
    """Delete an SLA configuration"""
    user = db_manager.get_user(session['user_id'])
    if not user or user.user_type not in [UserType.SUPER_ADMIN, UserType.DEVELOPER, UserType.SUPERVISOR]:
        return jsonify({'success': False, 'error': 'Permission denied'}), 403

    db = SessionLocal()
    try:
        config = db.query(SLAConfig).filter(SLAConfig.id == config_id).first()
        if not config:
            return jsonify({'success': False, 'error': 'Config not found'}), 404

        db.delete(config)
        db.commit()
        return jsonify({'success': True, 'message': 'SLA configuration deleted'})
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting SLA config: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()


# ============= Holiday CRUD =============

@sla_bp.route('/api/holidays')
@login_required
def list_holidays():
    """List holidays, optionally filtered by queue"""
    user = db_manager.get_user(session['user_id'])
    if not user or user.user_type not in [UserType.SUPER_ADMIN, UserType.DEVELOPER, UserType.SUPERVISOR]:
        return jsonify({'success': False, 'error': 'Permission denied'}), 403

    queue_id = request.args.get('queue_id')

    db = SessionLocal()
    try:
        query = db.query(QueueHoliday).order_by(QueueHoliday.holiday_date.desc())
        if queue_id:
            query = query.filter(QueueHoliday.queue_id == queue_id)

        holidays = query.all()
        return jsonify({
            'success': True,
            'holidays': [h.to_dict() for h in holidays]
        })
    finally:
        db.close()


@sla_bp.route('/api/holiday', methods=['POST'])
@login_required
def create_holiday():
    """Create a queue holiday"""
    user = db_manager.get_user(session['user_id'])
    if not user or user.user_type not in [UserType.SUPER_ADMIN, UserType.DEVELOPER, UserType.SUPERVISOR]:
        return jsonify({'success': False, 'error': 'Permission denied'}), 403

    data = request.get_json()
    queue_id = data.get('queue_id')
    holiday_date_str = data.get('date')  # ISO format string
    name = data.get('name')
    country = data.get('country', '')
    is_recurring = data.get('is_recurring', False)

    if not all([queue_id, holiday_date_str, name]):
        return jsonify({'success': False, 'error': 'Missing required fields'}), 400

    db = SessionLocal()
    try:
        # Parse date
        try:
            holiday_date = datetime.fromisoformat(holiday_date_str.replace('Z', '+00:00')).date()
        except ValueError:
            try:
                holiday_date = datetime.strptime(holiday_date_str, '%Y-%m-%d').date()
            except ValueError:
                return jsonify({'success': False, 'error': 'Invalid date format'}), 400

        # Check for duplicate
        existing = db.query(QueueHoliday).filter(
            QueueHoliday.queue_id == queue_id,
            QueueHoliday.holiday_date == holiday_date
        ).first()

        if existing:
            return jsonify({'success': False, 'error': 'Holiday already exists for this date'}), 400

        holiday = QueueHoliday(
            queue_id=queue_id,
            holiday_date=holiday_date,
            name=name,
            country=country,
            is_recurring=is_recurring,
            created_by_id=user.id
        )
        db.add(holiday)
        db.commit()
        return jsonify({'success': True, 'message': 'Holiday added', 'id': holiday.id})
    except Exception as e:
        db.rollback()
        logger.error(f"Error adding holiday: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()


@sla_bp.route('/api/holiday/<int:holiday_id>', methods=['DELETE'])
@login_required
def delete_holiday(holiday_id):
    """Delete a holiday"""
    user = db_manager.get_user(session['user_id'])
    if not user or user.user_type not in [UserType.SUPER_ADMIN, UserType.DEVELOPER, UserType.SUPERVISOR]:
        return jsonify({'success': False, 'error': 'Permission denied'}), 403

    db = SessionLocal()
    try:
        holiday = db.query(QueueHoliday).filter(QueueHoliday.id == holiday_id).first()
        if not holiday:
            return jsonify({'success': False, 'error': 'Holiday not found'}), 404

        db.delete(holiday)
        db.commit()
        return jsonify({'success': True, 'message': 'Holiday deleted'})
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting holiday: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()


# ============= SLA Dashboard =============

@sla_bp.route('/dashboard')
@login_required
def sla_dashboard():
    """Full SLA dashboard with all ticket SLA statuses"""
    user = db_manager.get_user(session['user_id'])
    if not user:
        flash('Please log in to continue', 'error')
        return redirect(url_for('auth.login'))

    db = SessionLocal()
    try:
        from utils.sla_calculator import get_sla_status

        # Get open tickets
        tickets = db.query(Ticket).filter(
            Ticket.status.notin_([TicketStatus.RESOLVED, TicketStatus.RESOLVED_DELIVERED])
        ).all()

        ticket_sla_data = []
        for ticket in tickets:
            sla_info = get_sla_status(ticket)
            if sla_info['has_sla']:
                ticket_sla_data.append({
                    'ticket': ticket,
                    'sla': sla_info
                })

        # Sort by status (breached first, then at_risk, then on_track)
        status_order = {'breached': 0, 'at_risk': 1, 'on_track': 2}
        ticket_sla_data.sort(key=lambda x: (
            status_order.get(x['sla']['status'], 3),
            x['sla'].get('days_remaining', 999) if x['sla'].get('days_remaining') else 999
        ))

        # Get summary stats
        on_track = sum(1 for t in ticket_sla_data if t['sla']['status'] == 'on_track')
        at_risk = sum(1 for t in ticket_sla_data if t['sla']['status'] == 'at_risk')
        breached = sum(1 for t in ticket_sla_data if t['sla']['status'] == 'breached')

        return render_template('sla/dashboard.html',
            user=user,
            ticket_sla_data=ticket_sla_data,
            on_track=on_track,
            at_risk=at_risk,
            breached=breached
        )
    finally:
        db.close()
