"""
API v2 Dashboard Widget Endpoints

Provides endpoints for dashboard widget management:
- GET /api/v2/dashboard/widgets - List all available widgets
- GET /api/v2/dashboard/widgets/<widget_id>/data - Get data for a specific widget
"""

from flask import request
from datetime import datetime, timedelta
from sqlalchemy import func, or_
import json
import logging

from . import api_v2_bp
from .utils import (
    api_response,
    api_error,
    ErrorCodes,
    handle_exceptions,
    dual_auth_required,
    serialize_datetime,
)

from utils.db_manager import DatabaseManager
from models.dashboard_widget import (
    WIDGET_REGISTRY,
    WidgetCategory,
    WidgetSize,
    get_available_widgets_for_user,
    get_widget,
    get_all_widgets,
)
from models.user import User, UserType
from models.asset import Asset
from models.accessory import Accessory
from models.customer_user import CustomerUser
from models.ticket import Ticket, TicketStatus
from models.activity import Activity
from database import SessionLocal

logger = logging.getLogger(__name__)
db_manager = DatabaseManager()


# Widget category metadata
WIDGET_CATEGORIES = [
    {
        'id': 'stats',
        'name': 'Statistics',
        'icon': 'chart-bar',
        'description': 'Real-time metrics and KPIs'
    },
    {
        'id': 'charts',
        'name': 'Charts',
        'icon': 'pie-chart',
        'description': 'Visual data representations'
    },
    {
        'id': 'lists',
        'name': 'Lists',
        'icon': 'list',
        'description': 'Activity feeds and tables'
    },
    {
        'id': 'actions',
        'name': 'Actions',
        'icon': 'bolt',
        'description': 'Quick actions and shortcuts'
    },
    {
        'id': 'system',
        'name': 'System',
        'icon': 'gear',
        'description': 'Administrative tools'
    }
]


def _size_to_grid(size: WidgetSize) -> dict:
    """Convert WidgetSize enum to grid dimensions"""
    size_map = {
        WidgetSize.SMALL: {'w': 1, 'h': 1},
        WidgetSize.MEDIUM: {'w': 2, 'h': 1},
        WidgetSize.LARGE: {'w': 3, 'h': 1},
        WidgetSize.FULL: {'w': 4, 'h': 1}
    }
    return size_map.get(size, {'w': 1, 'h': 1})


def _get_max_size_for_widget(widget) -> dict:
    """Determine maximum size for a widget"""
    # Most widgets can go up to full width
    if widget.category in [WidgetCategory.LISTS, WidgetCategory.SYSTEM]:
        return {'w': 4, 'h': 2}
    elif widget.category == WidgetCategory.CHARTS:
        return {'w': 4, 'h': 2}
    else:
        return {'w': 4, 'h': 1}


def _format_widget_for_api(widget, user_has_access: bool = True) -> dict:
    """Format a WidgetDefinition for API response"""
    # Build config options from default_config
    config_options = []
    if widget.configurable and widget.default_config:
        for key, default_value in widget.default_config.items():
            option = {
                'key': key,
                'default': default_value,
                'label': key.replace('_', ' ').title()
            }

            # Infer type from default value
            if isinstance(default_value, bool):
                option['type'] = 'boolean'
            elif isinstance(default_value, int):
                option['type'] = 'number'
            elif isinstance(default_value, list):
                option['type'] = 'select'
                option['options'] = default_value
            elif key == 'chart_type':
                option['type'] = 'select'
                option['options'] = ['doughnut', 'pie', 'bar']
            elif key == 'style':
                option['type'] = 'select'
                option['options'] = ['photo', 'minimal', 'detailed']
            elif key == 'limit':
                option['type'] = 'number'
                option['min'] = 1
                option['max'] = 50
            else:
                option['type'] = 'string'

            config_options.append(option)

    # Build permissions list
    permissions = []
    if widget.required_permissions:
        # Convert permission attribute names to permission strings
        for perm in widget.required_permissions:
            # Convert can_view_reports -> reports:read
            perm_parts = perm.replace('can_', '').split('_')
            if len(perm_parts) >= 2:
                resource = '_'.join(perm_parts[1:]) if perm_parts[0] in ['view', 'edit', 'access'] else '_'.join(perm_parts)
                action = 'read' if perm_parts[0] == 'view' else 'write' if perm_parts[0] == 'edit' else 'access'
                permissions.append(f"{resource}:{action}")
            else:
                permissions.append(perm)

    return {
        'id': widget.id,
        'name': widget.name,
        'description': widget.description,
        'long_description': widget.long_description,
        'category': widget.category.value,
        'icon': widget.icon.replace('fas fa-', '').replace('fa-', ''),  # Normalize icon name
        'color': widget.color,
        'default_size': _size_to_grid(widget.default_size),
        'min_size': _size_to_grid(widget.min_size),
        'max_size': _get_max_size_for_widget(widget),
        'config_options': config_options,
        'permissions': permissions,
        'refreshable': widget.refreshable,
        'configurable': widget.configurable,
        'screenshot': widget.screenshot,
        'has_access': user_has_access
    }


# =============================================================================
# GET ALL WIDGETS
# =============================================================================

@api_v2_bp.route('/dashboard/widgets', methods=['GET'])
@dual_auth_required
@handle_exceptions
def list_dashboard_widgets():
    """
    List all available dashboard widgets

    GET /api/v2/dashboard/widgets

    Query Parameters:
        category (string): Filter by category (stats, charts, lists, actions, system)
        include_all (boolean): Include widgets user doesn't have access to (default: false)

    Returns:
        200: List of widgets with metadata
        401: Authentication required
    """
    user = request.current_api_user

    # Get query parameters
    category_filter = request.args.get('category')
    include_all = request.args.get('include_all', 'false').lower() == 'true'

    # Get widgets available to this user
    available_widgets = get_available_widgets_for_user(user)
    available_widget_ids = {w.id for w in available_widgets}

    # Determine which widgets to return
    if include_all:
        # Return all widgets, marking which ones user has access to
        all_widgets = get_all_widgets()
        widgets_to_return = all_widgets
    else:
        # Return only accessible widgets
        widgets_to_return = available_widgets

    # Filter by category if specified
    if category_filter:
        try:
            cat_enum = WidgetCategory(category_filter.lower())
            widgets_to_return = [w for w in widgets_to_return if w.category == cat_enum]
        except ValueError:
            # Invalid category - return empty list with warning
            return api_response(
                data=[],
                message=f'Invalid category: {category_filter}. Valid categories: stats, charts, lists, actions, system',
                meta={
                    'categories': WIDGET_CATEGORIES,
                    'total_available': 0
                }
            )

    # Format widgets for response
    widgets_data = []
    for widget in widgets_to_return:
        user_has_access = widget.id in available_widget_ids
        widgets_data.append(_format_widget_for_api(widget, user_has_access))

    # Sort by category and then by name
    category_order = {'stats': 0, 'charts': 1, 'lists': 2, 'actions': 3, 'system': 4}
    widgets_data.sort(key=lambda w: (category_order.get(w['category'], 99), w['name']))

    return api_response(
        data=widgets_data,
        meta={
            'categories': WIDGET_CATEGORIES,
            'total_available': len(available_widget_ids),
            'total_widgets': len(get_all_widgets())
        }
    )


# =============================================================================
# GET WIDGET DATA
# =============================================================================

@api_v2_bp.route('/dashboard/widgets/<widget_id>/data', methods=['GET'])
@dual_auth_required
@handle_exceptions
def get_widget_data(widget_id):
    """
    Get data for a specific dashboard widget

    GET /api/v2/dashboard/widgets/<widget_id>/data

    Query Parameters:
        config (JSON string): Widget configuration options

    Returns:
        200: Widget data with values and chart data
        401: Authentication required
        403: Permission denied
        404: Widget not found
    """
    user = request.current_api_user

    # Get widget definition
    widget = get_widget(widget_id)
    if not widget:
        return api_error(
            ErrorCodes.RESOURCE_NOT_FOUND,
            f'Widget not found: {widget_id}',
            status_code=404
        )

    # Check if user has access to this widget
    available_widgets = get_available_widgets_for_user(user)
    available_widget_ids = {w.id for w in available_widgets}

    if widget_id not in available_widget_ids:
        return api_error(
            ErrorCodes.PERMISSION_DENIED,
            'You do not have permission to access this widget',
            status_code=403
        )

    # Parse config from query parameter
    config = {}
    config_param = request.args.get('config')
    if config_param:
        try:
            config = json.loads(config_param)
        except json.JSONDecodeError:
            return api_error(
                ErrorCodes.INVALID_JSON,
                'Invalid config JSON',
                status_code=400
            )

    # Merge with default config
    if widget.default_config:
        merged_config = dict(widget.default_config)
        merged_config.update(config)
        config = merged_config

    # Load widget data based on widget_id
    db = SessionLocal()
    try:
        data = _load_widget_data(widget_id, user, config, db)

        return api_response(
            data={
                'widget_id': widget_id,
                'generated_at': datetime.utcnow().isoformat() + 'Z',
                **data
            }
        )
    except Exception as e:
        logger.exception(f"Error loading widget data for {widget_id}: {str(e)}")
        return api_error(
            ErrorCodes.INTERNAL_ERROR,
            f'Failed to load widget data: {str(e)}',
            status_code=500
        )
    finally:
        db.close()


def _load_widget_data(widget_id: str, user: User, config: dict, db) -> dict:
    """Load data for a specific widget based on widget_id and user permissions"""

    # Inventory Stats Widget
    if widget_id == 'inventory_stats':
        return _load_inventory_stats(user, db)

    # Ticket Stats Widget
    elif widget_id == 'ticket_stats':
        return _load_ticket_stats(user, config, db)

    # Customer Stats Widget
    elif widget_id == 'customer_stats':
        return _load_customer_stats(user, db)

    # Queue Stats Widget
    elif widget_id == 'queue_stats':
        return _load_queue_stats(user, db)

    # Weekly Tickets Chart
    elif widget_id == 'weekly_tickets_chart':
        return _load_weekly_tickets_chart(user, db)

    # Asset Status Chart
    elif widget_id == 'asset_status_chart':
        return _load_asset_status_chart(user, config, db)

    # Recent Activities
    elif widget_id == 'recent_activities':
        return _load_recent_activities(user, config, db)

    # Shipments List
    elif widget_id == 'shipments_list':
        return _load_shipments_list(user, config, db)

    # SLA Manager
    elif widget_id == 'sla_manager':
        return _load_sla_manager(user, db)

    # Device Specs Collector
    elif widget_id == 'device_specs_collector':
        return _load_device_specs(user, db)

    # Report Issue Widget
    elif widget_id == 'report_issue':
        return _load_bug_report_stats(user, db)

    # Widgets without data loaders return empty values
    else:
        return {
            'values': {},
            'message': 'This widget does not have dynamic data'
        }


def _load_inventory_stats(user: User, db) -> dict:
    """Load inventory statistics"""
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

            # Include child companies
            all_company_names = list(permitted_company_names)
            all_company_ids = list(permitted_company_ids)
            for company in permitted_companies:
                if company.is_parent_company or company.child_companies.count() > 0:
                    child_companies = company.child_companies.all()
                    child_names = [c.name.strip() for c in child_companies]
                    child_ids = [c.id for c in child_companies]
                    all_company_names.extend(child_names)
                    all_company_ids.extend(child_ids)

            # Filter by company_id OR customer name
            name_conditions = [func.lower(Asset.customer).like(f"%{name.lower()}%") for name in all_company_names]
            asset_query = asset_query.filter(
                or_(
                    Asset.company_id.in_(all_company_ids),
                    *name_conditions
                )
            )
            tech_assets = asset_query.count()
        else:
            tech_assets = 0
    else:
        tech_assets = db.query(Asset).count()

    accessories = db.query(func.sum(Accessory.total_quantity)).scalar() or 0

    return {
        'values': {
            'total': tech_assets + accessories,
            'tech_assets': tech_assets,
            'accessories': int(accessories)
        },
        'chart_data': None
    }


def _load_ticket_stats(user: User, config: dict, db) -> dict:
    """Load ticket statistics"""
    show_resolved = config.get('show_resolved', True)
    time_period = config.get('time_period', '30d')

    # Parse time period
    days = 30
    if time_period == '7d':
        days = 7
    elif time_period == '90d':
        days = 90

    date_filter = datetime.utcnow() - timedelta(days=days)

    if user.user_type == UserType.COUNTRY_ADMIN:
        base_query = db.query(Ticket)
        if user.assigned_countries:
            base_query = base_query.filter(Ticket.country.in_(user.assigned_countries))

        total = base_query.filter(Ticket.created_at >= date_filter).count()
        open_tickets = base_query.filter(
            Ticket.status != TicketStatus.RESOLVED,
            Ticket.status != TicketStatus.RESOLVED_DELIVERED,
            Ticket.created_at >= date_filter
        ).count()
        in_progress = base_query.filter(
            Ticket.status == TicketStatus.IN_PROGRESS,
            Ticket.created_at >= date_filter
        ).count()
        resolved = total - open_tickets
    else:
        total = db.query(Ticket).filter(Ticket.created_at >= date_filter).count()
        open_tickets = db.query(Ticket).filter(
            Ticket.status != TicketStatus.RESOLVED,
            Ticket.status != TicketStatus.RESOLVED_DELIVERED,
            Ticket.created_at >= date_filter
        ).count()
        in_progress = db.query(Ticket).filter(
            Ticket.status == TicketStatus.IN_PROGRESS,
            Ticket.created_at >= date_filter
        ).count()
        resolved = db.query(Ticket).filter(
            Ticket.status.in_([TicketStatus.RESOLVED, TicketStatus.RESOLVED_DELIVERED]),
            Ticket.created_at >= date_filter
        ).count()

    values = {
        'total': total,
        'open': open_tickets,
        'in_progress': in_progress
    }

    if show_resolved:
        values['resolved'] = resolved

    # Chart data for status breakdown
    chart_labels = ['Open', 'In Progress']
    chart_values = [open_tickets, in_progress]
    chart_colors = ['#F44336', '#FF9800']

    if show_resolved:
        chart_labels.append('Resolved')
        chart_values.append(resolved)
        chart_colors.append('#4CAF50')

    return {
        'values': values,
        'chart_data': {
            'labels': chart_labels,
            'values': chart_values,
            'colors': chart_colors
        }
    }


def _load_customer_stats(user: User, db) -> dict:
    """Load customer statistics"""
    if user.user_type == UserType.COUNTRY_ADMIN and user.company_id:
        total_customers = db.query(CustomerUser).filter(
            CustomerUser.company_id == user.company_id
        ).count()
    else:
        total_customers = db.query(CustomerUser).count()

    return {
        'values': {
            'total': total_customers
        },
        'chart_data': None
    }


def _load_queue_stats(user: User, db) -> dict:
    """Load queue statistics"""
    from models.queue import Queue

    if user.user_type in [UserType.SUPER_ADMIN, UserType.DEVELOPER]:
        queues = db.query(Queue).all()
    else:
        accessible_queue_ids = user.get_accessible_queue_ids(db)
        all_queues = db.query(Queue).all()
        queues = [queue for queue in all_queues if queue.id in accessible_queue_ids]

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

    return {
        'values': {
            'queues': queue_data,
            'total_queues': len(queue_data)
        },
        'chart_data': {
            'labels': [q['name'] for q in queue_data],
            'values': [q['open_count'] for q in queue_data],
            'colors': ['#2196F3', '#4CAF50', '#FF9800', '#9C27B0', '#00BCD4', '#E91E63'][:len(queue_data)]
        }
    }


def _load_weekly_tickets_chart(user: User, db) -> dict:
    """Load weekly ticket creation data"""
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

    return {
        'values': {
            'week_start': monday.strftime('%Y-%m-%d'),
            'week_total': sum(values)
        },
        'chart_data': {
            'labels': labels,
            'values': values,
            'colors': ['#3F51B5']
        }
    }


def _load_asset_status_chart(user: User, config: dict, db) -> dict:
    """Load asset status distribution data"""
    chart_type = config.get('chart_type', 'doughnut')

    statuses = ['DEPLOYED', 'IN_STOCK', 'READY_TO_DEPLOY', 'REPAIR', 'DISPOSED']
    labels = []
    values = []
    colors = ['#4CAF50', '#2196F3', '#FF9800', '#F44336', '#9E9E9E']

    for i, status in enumerate(statuses):
        count = db.query(Asset).filter(Asset.status == status).count()
        if count > 0:
            labels.append(status.replace('_', ' ').title())
            values.append(count)

    return {
        'values': {
            'total_assets': sum(values)
        },
        'chart_data': {
            'type': chart_type,
            'labels': labels,
            'values': values,
            'colors': colors[:len(labels)]
        }
    }


def _load_recent_activities(user: User, config: dict, db) -> dict:
    """Load recent activities"""
    limit = config.get('limit', 5)

    activities = db.query(Activity).order_by(
        Activity.created_at.desc()
    ).limit(limit).all()

    activities_list = []
    for a in activities:
        activities_list.append({
            'id': a.id,
            'content': a.content,
            'type': a.type,
            'created_at': a.created_at.isoformat() + 'Z' if a.created_at else None,
            'user_id': a.user_id,
            'reference_id': a.reference_id
        })

    return {
        'values': {
            'activities': activities_list,
            'total_count': len(activities_list)
        },
        'chart_data': None
    }


def _load_shipments_list(user: User, config: dict, db) -> dict:
    """Load active shipments data"""
    from models.ticket import TicketCategory

    limit = config.get('limit', 10)

    shipment_categories = [
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
    ]

    shipment_query = db.query(Ticket).filter(
        Ticket.category.in_(shipment_categories)
    )

    # Filter by queue access for non-admin users
    if not user.is_super_admin and not user.is_developer:
        accessible_queue_ids = user.get_accessible_queue_ids(db)
        all_shipments = shipment_query.order_by(Ticket.created_at.desc()).all()
        shipments = [t for t in all_shipments if t.queue_id and t.queue_id in accessible_queue_ids][:limit]
    else:
        shipments = shipment_query.order_by(Ticket.created_at.desc()).limit(limit).all()

    shipments_list = []
    for t in shipments:
        shipments_list.append({
            'id': t.id,
            'display_id': t.display_id,
            'customer_name': t.customer.name if t.customer else None,
            'shipping_tracking': t.shipping_tracking,
            'shipping_status': t.shipping_status,
            'shipping_carrier': t.shipping_carrier,
            'return_tracking': t.return_tracking,
            'return_tracking_status': t.return_tracking_status,
            'created_at': t.created_at.isoformat() + 'Z' if t.created_at else None
        })

    return {
        'values': {
            'shipments': shipments_list,
            'total_count': len(shipments_list)
        },
        'chart_data': None
    }


def _load_sla_manager(user: User, db) -> dict:
    """Load SLA manager data"""
    from utils.sla_calculator import get_sla_status

    # Get open tickets
    open_tickets = db.query(Ticket).filter(
        Ticket.status.notin_([TicketStatus.RESOLVED, TicketStatus.RESOLVED_DELIVERED])
    ).all()

    # Calculate SLA stats
    on_track = 0
    at_risk = 0
    breached = 0
    total_open = len(open_tickets)

    users_cases = {}

    for ticket in open_tickets:
        sla_info = get_sla_status(ticket, db=db)

        # Track by requester
        if ticket.requester:
            req_id = ticket.requester.id
            if req_id not in users_cases:
                users_cases[req_id] = {
                    'name': ticket.requester.username or ticket.requester.email,
                    'open_count': 0,
                    'breached_count': 0,
                    'at_risk_count': 0
                }
            users_cases[req_id]['open_count'] += 1

        if sla_info['has_sla']:
            if sla_info['status'] == 'on_track':
                on_track += 1
            elif sla_info['status'] == 'at_risk':
                at_risk += 1
                if ticket.requester and ticket.requester.id in users_cases:
                    users_cases[ticket.requester.id]['at_risk_count'] += 1
            elif sla_info['status'] == 'breached':
                breached += 1
                if ticket.requester and ticket.requester.id in users_cases:
                    users_cases[ticket.requester.id]['breached_count'] += 1

    # Sort users by open cases
    sorted_users = sorted(
        users_cases.values(),
        key=lambda x: (x['breached_count'], x['at_risk_count'], x['open_count']),
        reverse=True
    )

    return {
        'values': {
            'total_open': total_open,
            'on_track': on_track,
            'at_risk': at_risk,
            'breached': breached,
            'users_with_cases': sorted_users[:5]
        },
        'chart_data': {
            'labels': ['On Track', 'At Risk', 'Breached'],
            'values': [on_track, at_risk, breached],
            'colors': ['#4CAF50', '#FF9800', '#F44336']
        }
    }


def _load_device_specs(user: User, db) -> dict:
    """Load device specs collector data"""
    from models.device_spec import DeviceSpec

    total_specs = db.query(DeviceSpec).count()
    pending_specs = db.query(DeviceSpec).filter(DeviceSpec.processed == False).count()
    processed_specs = total_specs - pending_specs

    # Get latest unprocessed spec
    latest_spec = db.query(DeviceSpec).filter(
        DeviceSpec.processed == False
    ).order_by(DeviceSpec.submitted_at.desc()).first()

    latest_data = None
    if latest_spec:
        latest_data = {
            'serial': latest_spec.serial_number or 'Unknown',
            'model': latest_spec.model_name or latest_spec.model_id or '',
            'time': latest_spec.submitted_at.strftime('%b %d, %H:%M') if latest_spec.submitted_at else ''
        }

    return {
        'values': {
            'total': total_specs,
            'pending': pending_specs,
            'processed': processed_specs,
            'latest': latest_data
        },
        'chart_data': {
            'labels': ['Processed', 'Pending'],
            'values': [processed_specs, pending_specs],
            'colors': ['#4CAF50', '#FF9800']
        }
    }


def _load_bug_report_stats(user: User, db) -> dict:
    """Load bug report statistics for the current user"""
    from models.bug_report import BugReport, BugStatus

    # Get user's own bug reports
    user_reports = db.query(BugReport).filter(
        BugReport.reporter_id == user.id
    )
    total_count = user_reports.count()
    open_count = user_reports.filter(
        BugReport.status.in_([BugStatus.OPEN, BugStatus.IN_PROGRESS, BugStatus.UNDER_REVIEW])
    ).count()

    return {
        'values': {
            'total_count': total_count,
            'open_count': open_count,
            'resolved_count': total_count - open_count
        },
        'chart_data': {
            'labels': ['Open', 'Resolved'],
            'values': [open_count, total_count - open_count],
            'colors': ['#FF9800', '#4CAF50']
        }
    }
