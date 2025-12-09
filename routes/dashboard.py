"""
Dashboard Routes

Routes for the customizable Salesforce-style dashboard (home_v2).
"""

from flask import Blueprint, render_template, redirect, url_for, session, request, jsonify
from utils.auth_decorators import login_required
from utils.db_manager import DatabaseManager
from models.user import UserType, User
from models.asset import Asset
from models.accessory import Accessory
from models.customer_user import CustomerUser
from models.ticket import Ticket, TicketCategory, TicketStatus
from models.activity import Activity
from models.audit_session import AuditSession
from models.system_settings import SystemSettings
from models.dashboard_widget import (
    WIDGET_REGISTRY, WidgetCategory, get_available_widgets_for_user,
    get_default_layout_for_user, get_widget
)
from sqlalchemy import func, or_
from datetime import datetime, timedelta
from database import SessionLocal
import json
import logging

logger = logging.getLogger(__name__)
dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/dashboard')
db_manager = DatabaseManager()


def load_widget_data(user, layout):
    """Load data for all widgets in the layout"""
    widget_data = {}
    db = SessionLocal()

    try:
        widget_ids = [item['widget_id'] for item in layout]

        # Load inventory stats
        if 'inventory_stats' in widget_ids:
            if user.user_type in [UserType.COUNTRY_ADMIN, UserType.SUPERVISOR]:
                from models.user_company_permission import UserCompanyPermission
                asset_query = db.query(Asset)

                # Filter by assigned countries
                if user.assigned_countries:
                    asset_query = asset_query.filter(Asset.country.in_(user.assigned_countries))

                # Filter by company permissions
                company_permissions = db.query(UserCompanyPermission).filter_by(
                    user_id=user.id,
                    can_view=True
                ).all()

                if company_permissions:
                    from models.company import Company
                    permitted_company_ids = [perm.company_id for perm in company_permissions]
                    permitted_companies = db.query(Company).filter(Company.id.in_(permitted_company_ids)).all()
                    permitted_company_names = [c.name.strip() for c in permitted_companies]

                    # Include child companies of parent companies
                    all_company_names = list(permitted_company_names)
                    for company in permitted_companies:
                        if company.is_parent_company or company.child_companies.count() > 0:
                            child_names = [c.name.strip() for c in company.child_companies.all()]
                            all_company_names.extend(child_names)

                    # Filter by company_id OR customer name
                    name_conditions = [func.lower(Asset.customer).like(f"%{name.lower()}%") for name in all_company_names]
                    asset_query = asset_query.filter(
                        or_(
                            Asset.company_id.in_(permitted_company_ids),
                            *name_conditions
                        )
                    )
                    tech_assets = asset_query.count()
                else:
                    tech_assets = 0
            else:
                tech_assets = db.query(Asset).count()
            accessories = db.query(func.sum(Accessory.total_quantity)).scalar() or 0
            widget_data['inventory_stats'] = {
                'total': tech_assets + accessories,
                'tech_assets': tech_assets,
                'accessories': accessories
            }

        # Load ticket stats
        if 'ticket_stats' in widget_ids:
            if user.user_type == UserType.COUNTRY_ADMIN:
                base_query = db.query(Ticket)
                if user.assigned_countries:
                    base_query = base_query.filter(Ticket.country.in_(user.assigned_countries))
                total = base_query.count()
                open_tickets = base_query.filter(
                    Ticket.status != TicketStatus.RESOLVED,
                    Ticket.status != TicketStatus.RESOLVED_DELIVERED
                ).count()
                resolved = total - open_tickets
            else:
                total = db.query(Ticket).count()
                open_tickets = db.query(Ticket).filter(
                    Ticket.status != TicketStatus.RESOLVED,
                    Ticket.status != TicketStatus.RESOLVED_DELIVERED
                ).count()
                resolved = db.query(Ticket).filter(
                    Ticket.status.in_([TicketStatus.RESOLVED, TicketStatus.RESOLVED_DELIVERED])
                ).count()
            widget_data['ticket_stats'] = {
                'total': total,
                'open': open_tickets,
                'resolved': resolved
            }

        # Load customer stats
        if 'customer_stats' in widget_ids:
            if user.user_type == UserType.COUNTRY_ADMIN and user.company_id:
                total_customers = db.query(CustomerUser).filter(
                    CustomerUser.company_id == user.company_id
                ).count()
            else:
                total_customers = db.query(CustomerUser).count()
            widget_data['customer_stats'] = {'total': total_customers}

        # Load queue stats
        if 'queue_stats' in widget_ids:
            from models.queue import Queue
            from models.company_queue_permission import CompanyQueuePermission

            if user.user_type in [UserType.SUPER_ADMIN, UserType.DEVELOPER]:
                queues = db.query(Queue).all()
            else:
                queues = []
                all_queues = db.query(Queue).all()
                for queue in all_queues:
                    if user.can_access_queue(queue.id):
                        queues.append(queue)

            queue_data = []
            for queue in queues:
                total_count = db.query(Ticket).filter(Ticket.queue_id == queue.id).count()
                open_count = db.query(Ticket).filter(
                    Ticket.queue_id == queue.id,
                    Ticket.status != TicketStatus.RESOLVED,
                    Ticket.status != TicketStatus.RESOLVED_DELIVERED
                ).count()
                queue_data.append({
                    'id': queue.id,
                    'name': queue.name,
                    'total_count': total_count,
                    'open_count': open_count
                })
            widget_data['queue_stats'] = {'queues': queue_data}

        # Load weekly ticket data
        if 'weekly_tickets_chart' in widget_ids:
            today = datetime.now()
            weekday = today.weekday()
            monday = today - timedelta(days=weekday)

            labels = []
            values = []
            for i in range(5):
                day = monday + timedelta(days=i)
                day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
                day_end = day.replace(hour=23, minute=59, second=59, microsecond=999999)

                day_query = db.query(Ticket).filter(
                    Ticket.created_at >= day_start,
                    Ticket.created_at <= day_end
                )

                if user.user_type == UserType.COUNTRY_ADMIN:
                    if user.assigned_countries:
                        day_query = day_query.filter(Ticket.country.in_(user.assigned_countries))

                labels.append(day.strftime('%a'))
                values.append(day_query.count())

            widget_data['weekly_tickets'] = {'labels': labels, 'values': values}

        # Load asset status data
        if 'asset_status_chart' in widget_ids:
            statuses = ['DEPLOYED', 'IN_STOCK', 'READY_TO_DEPLOY', 'REPAIR', 'DISPOSED']
            labels = []
            values = []
            for status in statuses:
                count = db.query(Asset).filter(Asset.status == status).count()
                if count > 0:
                    labels.append(status.replace('_', ' ').title())
                    values.append(count)
            widget_data['asset_status'] = {'labels': labels, 'values': values}

        # Load recent activities
        if 'recent_activities' in widget_ids:
            activities = db.query(Activity).order_by(
                Activity.created_at.desc()
            ).limit(5).all()
            widget_data['recent_activities'] = {
                'activities': [
                    {
                        'content': a.content,
                        'created_at': a.created_at.strftime('%Y-%m-%d %H:%M')
                    } for a in activities
                ]
            }

        # Load shipments data
        if 'shipments_list' in widget_ids:
            shipment_query = db.query(Ticket).filter(
                Ticket.category.in_([
                    TicketCategory.ASSET_CHECKOUT,
                    TicketCategory.ASSET_CHECKOUT1,
                    TicketCategory.ASSET_CHECKOUT_SINGPOST,
                    TicketCategory.ASSET_CHECKOUT_DHL,
                    TicketCategory.ASSET_CHECKOUT_UPS,
                    TicketCategory.ASSET_CHECKOUT_BLUEDART,
                    TicketCategory.ASSET_CHECKOUT_DTDC,
                    TicketCategory.ASSET_CHECKOUT_AUTO,
                    TicketCategory.ASSET_CHECKOUT_CLAW,
                    TicketCategory.ASSET_RETURN_CLAW
                ])
            )

            # Filter by queue access for non-admin users
            if not user.is_super_admin and not user.is_developer:
                # Get all shipments first, then filter by queue access
                all_shipments = shipment_query.order_by(Ticket.created_at.desc()).all()
                shipments = [t for t in all_shipments if t.queue_id and user.can_access_queue(t.queue_id)][:20]
            else:
                shipments = shipment_query.order_by(Ticket.created_at.desc()).limit(20).all()
            widget_data['shipments'] = {
                'tickets': [
                    {
                        'id': t.id,
                        'display_id': t.display_id,
                        'customer_name': t.customer.name if t.customer else None,
                        'shipping_tracking': t.shipping_tracking,
                        'shipping_status': t.shipping_status
                    } for t in shipments
                ]
            }

        # Load audit data
        if 'inventory_audit' in widget_ids:
            current_audit = db.query(AuditSession).filter(
                AuditSession.is_active == True
            ).first()
            widget_data['audit'] = {
                'current_audit': current_audit is not None
            }

    except Exception as e:
        logger.error(f"Error loading widget data: {str(e)}", exc_info=True)
    finally:
        db.close()

    # Log which widgets have data loaded
    logger.debug(f"Loaded widget data for: {list(widget_data.keys())}")
    return widget_data


@dashboard_bp.route('/')
@login_required
def index():
    """Render the customizable dashboard"""
    user_id = session['user_id']

    try:
        with db_manager as db:
            user = db.get_user(user_id)

        if not user:
            session.clear()
            return redirect(url_for('auth.login'))

        # Check if user wants to use classic view
        if request.args.get('use_classic'):
            session['use_classic_home'] = True
            return redirect(url_for('main.index'))

        # Get user's dashboard layout from preferences
        layout = None
        if user.preferences and 'dashboard_layout' in user.preferences:
            layout = user.preferences['dashboard_layout']

        # Fall back to default layout
        if not layout:
            layout = get_default_layout_for_user(user)

        # Get available widgets for this user
        available_widgets = get_available_widgets_for_user(user)

        # Create a map of widget definitions for easy lookup in template
        widgets_map = {w.id: w for w in available_widgets}

        # Get active widget IDs in the current layout
        active_widget_ids = [item['widget_id'] for item in layout]

        # Get widget categories
        widget_categories = list(WidgetCategory)

        # Load widget data
        widget_data = load_widget_data(user, layout)

        # Prepare chart data for JavaScript
        weekly_ticket_data = widget_data.get('weekly_tickets', {'labels': [], 'values': []})
        asset_status_data = widget_data.get('asset_status', {'labels': [], 'values': []})

        return render_template('home_v2.html',
            user=user,
            layout=layout,
            layout_json=json.dumps(layout),
            widgets_map=widgets_map,
            available_widgets=available_widgets,
            active_widget_ids=active_widget_ids,
            widget_categories=widget_categories,
            widget_data=widget_data,
            weekly_ticket_data=weekly_ticket_data,
            asset_status_data=asset_status_data
        )

    except Exception as e:
        logger.error(f"Error rendering dashboard: {str(e)}", exc_info=True)
        # Redirect to classic homepage with use_classic flag to prevent redirect loop
        return redirect(url_for('main.index', use_classic=1))


@dashboard_bp.route('/api/save-layout', methods=['POST'])
@login_required
def save_layout():
    """Save user's dashboard layout"""
    user_id = session['user_id']

    try:
        data = request.get_json()
        if not data or 'layout' not in data:
            return jsonify({'success': False, 'error': 'No layout provided'})

        layout = data['layout']

        # Validate layout structure
        if not isinstance(layout, list):
            return jsonify({'success': False, 'error': 'Invalid layout format'})

        for item in layout:
            if not isinstance(item, dict):
                return jsonify({'success': False, 'error': 'Invalid layout item'})
            if 'widget_id' not in item:
                return jsonify({'success': False, 'error': 'Missing widget_id'})

        # Update user preferences
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                return jsonify({'success': False, 'error': 'User not found'})

            # Initialize preferences if None
            if user.preferences is None:
                user.preferences = {}

            # Update dashboard layout
            prefs = dict(user.preferences)  # Create a mutable copy
            prefs['dashboard_layout'] = layout
            user.preferences = prefs

            db.commit()

            return jsonify({'success': True})

        finally:
            db.close()

    except Exception as e:
        logger.error(f"Error saving layout: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})


@dashboard_bp.route('/api/widget/<widget_id>/data')
@login_required
def get_widget_data(widget_id):
    """Get data for a specific widget"""
    user_id = session['user_id']

    try:
        with db_manager as db:
            user = db.get_user(user_id)

        if not user:
            return jsonify({'success': False, 'error': 'User not found'})

        # Create a fake layout with just this widget
        layout = [{'widget_id': widget_id}]
        widget_data = load_widget_data(user, layout)

        # Get widget definition
        widget = get_widget(widget_id)
        if not widget:
            return jsonify({'success': False, 'error': 'Widget not found'})

        # Render widget HTML with proper context
        html = render_template(widget.template, widget_data=widget_data, user=user)

        # Map widget_id to data key (some widgets use different keys)
        data_key_map = {
            'weekly_tickets_chart': 'weekly_tickets',
            'asset_status_chart': 'asset_status',
            'shipments_list': 'shipments',
            'inventory_audit': 'audit'
        }
        data_key = data_key_map.get(widget_id, widget_id)

        return jsonify({
            'success': True,
            'html': html,
            'data': widget_data.get(data_key, {})
        })

    except Exception as e:
        logger.error(f"Error getting widget data: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})


@dashboard_bp.route('/api/reset-layout', methods=['POST'])
@login_required
def reset_layout():
    """Reset user's dashboard to default layout"""
    user_id = session['user_id']

    try:
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                return jsonify({'success': False, 'error': 'User not found'})

            # Get default layout
            default_layout = get_default_layout_for_user(user)

            # Update preferences
            if user.preferences is None:
                user.preferences = {}

            prefs = dict(user.preferences)
            prefs['dashboard_layout'] = default_layout
            user.preferences = prefs

            db.commit()

            return jsonify({'success': True})

        finally:
            db.close()

    except Exception as e:
        logger.error(f"Error resetting layout: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})
