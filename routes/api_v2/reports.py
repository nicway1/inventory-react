"""
API v2 Report Endpoints

Provides report template listing and report generation endpoints:
- GET /api/v2/reports/templates - List all available report templates
- POST /api/v2/reports/generate - Generate a report from a template
"""

from flask import request
from datetime import datetime, timedelta
from sqlalchemy import func, and_, or_
from sqlalchemy.orm import joinedload
import logging
import uuid
import csv
import io

from . import api_v2_bp
from .utils import (
    api_response,
    api_error,
    ErrorCodes,
    handle_exceptions,
    validate_json_body,
    validate_required_fields,
    dual_auth_required,
    serialize_datetime,
)

from utils.db_manager import DatabaseManager
from models.ticket import Ticket, TicketStatus, TicketPriority, TicketCategory
from models.asset import Asset, AssetStatus
from models.user import User, UserType
from models.customer_user import CustomerUser
from models.company import Company
from models.queue import Queue
from models.accessory import Accessory

logger = logging.getLogger(__name__)
db_manager = DatabaseManager()


# =============================================================================
# REPORT TEMPLATE DEFINITIONS
# =============================================================================

REPORT_TEMPLATES = {
    'ticket_summary': {
        'id': 'ticket_summary',
        'name': 'Ticket Summary Report',
        'description': 'Summary of tickets by status, queue, and priority',
        'category': 'tickets',
        'icon': 'file-text',
        'parameters': [
            {
                'key': 'date_from',
                'type': 'date',
                'label': 'From Date',
                'required': True
            },
            {
                'key': 'date_to',
                'type': 'date',
                'label': 'To Date',
                'required': True
            },
            {
                'key': 'queue_ids',
                'type': 'multi_select',
                'label': 'Queues',
                'required': False,
                'options_endpoint': '/api/v2/queues'
            },
            {
                'key': 'group_by',
                'type': 'select',
                'label': 'Group By',
                'options': ['status', 'queue', 'priority', 'category'],
                'default': 'status'
            }
        ],
        'output_formats': ['json', 'csv', 'pdf'],
        'permissions': ['reports:read']
    },
    'ticket_resolution_time': {
        'id': 'ticket_resolution_time',
        'name': 'Ticket Resolution Time Report',
        'description': 'Average resolution time by category and queue',
        'category': 'tickets',
        'icon': 'clock',
        'parameters': [
            {
                'key': 'date_from',
                'type': 'date',
                'label': 'From Date',
                'required': True
            },
            {
                'key': 'date_to',
                'type': 'date',
                'label': 'To Date',
                'required': True
            },
            {
                'key': 'queue_ids',
                'type': 'multi_select',
                'label': 'Queues',
                'required': False,
                'options_endpoint': '/api/v2/queues'
            }
        ],
        'output_formats': ['json', 'csv'],
        'permissions': ['reports:read']
    },
    'asset_inventory': {
        'id': 'asset_inventory',
        'name': 'Asset Inventory Report',
        'description': 'Complete asset inventory with status and assignments',
        'category': 'inventory',
        'icon': 'laptop',
        'parameters': [
            {
                'key': 'status',
                'type': 'multi_select',
                'label': 'Status',
                'options': ['Available', 'Deployed', 'Maintenance', 'Retired', 'Ready to Deploy']
            },
            {
                'key': 'company_id',
                'type': 'select',
                'label': 'Company',
                'required': False,
                'options_endpoint': '/api/v2/companies'
            },
            {
                'key': 'asset_type',
                'type': 'multi_select',
                'label': 'Asset Type',
                'options': ['Apple', 'Windows (PC)', 'Monitor', 'Phone', 'Tablet', 'Other']
            }
        ],
        'output_formats': ['json', 'csv', 'xlsx'],
        'permissions': ['inventory:read']
    },
    'asset_by_status': {
        'id': 'asset_by_status',
        'name': 'Assets by Status Report',
        'description': 'Asset breakdown by status with counts and percentages',
        'category': 'inventory',
        'icon': 'pie-chart',
        'parameters': [
            {
                'key': 'company_id',
                'type': 'select',
                'label': 'Company',
                'required': False,
                'options_endpoint': '/api/v2/companies'
            },
            {
                'key': 'country',
                'type': 'select',
                'label': 'Country',
                'required': False,
                'options_endpoint': '/api/v2/countries'
            }
        ],
        'output_formats': ['json', 'csv'],
        'permissions': ['inventory:read']
    },
    'asset_age_distribution': {
        'id': 'asset_age_distribution',
        'name': 'Asset Age Distribution Report',
        'description': 'Distribution of asset ages for lifecycle planning',
        'category': 'inventory',
        'icon': 'calendar',
        'parameters': [
            {
                'key': 'company_id',
                'type': 'select',
                'label': 'Company',
                'required': False,
                'options_endpoint': '/api/v2/companies'
            }
        ],
        'output_formats': ['json', 'csv'],
        'permissions': ['inventory:read']
    },
    'user_activity': {
        'id': 'user_activity',
        'name': 'User Activity Report',
        'description': 'User ticket activity and workload analysis',
        'category': 'users',
        'icon': 'users',
        'parameters': [
            {
                'key': 'date_from',
                'type': 'date',
                'label': 'From Date',
                'required': True
            },
            {
                'key': 'date_to',
                'type': 'date',
                'label': 'To Date',
                'required': True
            },
            {
                'key': 'user_ids',
                'type': 'multi_select',
                'label': 'Users',
                'required': False,
                'options_endpoint': '/api/v2/users'
            }
        ],
        'output_formats': ['json', 'csv'],
        'permissions': ['reports:read', 'users:read']
    },
    'customer_tickets': {
        'id': 'customer_tickets',
        'name': 'Customer Ticket Report',
        'description': 'Ticket volume and trends by customer/company',
        'category': 'analytics',
        'icon': 'bar-chart-2',
        'parameters': [
            {
                'key': 'date_from',
                'type': 'date',
                'label': 'From Date',
                'required': True
            },
            {
                'key': 'date_to',
                'type': 'date',
                'label': 'To Date',
                'required': True
            },
            {
                'key': 'company_id',
                'type': 'select',
                'label': 'Company',
                'required': False,
                'options_endpoint': '/api/v2/companies'
            },
            {
                'key': 'top_n',
                'type': 'number',
                'label': 'Top N Customers',
                'default': 10
            }
        ],
        'output_formats': ['json', 'csv'],
        'permissions': ['reports:read']
    }
}

REPORT_CATEGORIES = [
    {'id': 'tickets', 'name': 'Ticket Reports'},
    {'id': 'inventory', 'name': 'Inventory Reports'},
    {'id': 'users', 'name': 'User Reports'},
    {'id': 'analytics', 'name': 'Analytics'}
]


# =============================================================================
# PERMISSION CHECKING
# =============================================================================

def check_user_report_permissions(user, required_permissions):
    """
    Check if user has the required permissions to access a report.

    Args:
        user: The authenticated user
        required_permissions: List of permission strings required

    Returns:
        bool: True if user has all required permissions
    """
    # Super admins and developers have full access
    if user.user_type in [UserType.SUPER_ADMIN, UserType.DEVELOPER]:
        return True

    # Country admins and supervisors have reports access
    if user.user_type in [UserType.COUNTRY_ADMIN, UserType.SUPERVISOR]:
        return True

    # Check specific permissions if user has permissions object
    if hasattr(user, 'permissions') and user.permissions:
        permissions = user.permissions

        for perm in required_permissions:
            if perm == 'reports:read':
                if not getattr(permissions, 'can_view_reports', False):
                    return False
            elif perm == 'inventory:read':
                if not getattr(permissions, 'can_view_assets', False):
                    return False
            elif perm == 'users:read':
                if not getattr(permissions, 'can_view_users', False):
                    return False

        return True

    # Default to no access for clients and other users without explicit permissions
    return False


def filter_templates_by_permission(user, templates):
    """
    Filter report templates based on user permissions.

    Args:
        user: The authenticated user
        templates: Dictionary of report templates

    Returns:
        List of templates the user can access
    """
    accessible_templates = []

    for template_id, template in templates.items():
        required_perms = template.get('permissions', [])
        if check_user_report_permissions(user, required_perms):
            accessible_templates.append(template)

    return accessible_templates


# =============================================================================
# REPORT GENERATORS
# =============================================================================

def generate_ticket_summary_report(db_session, user, parameters):
    """Generate ticket summary report data."""
    date_from = datetime.fromisoformat(parameters['date_from'])
    date_to = datetime.fromisoformat(parameters['date_to'])
    # Include the end date
    date_to_inclusive = date_to + timedelta(days=1)

    queue_ids = parameters.get('queue_ids', [])
    group_by = parameters.get('group_by', 'status')

    # Build base query
    query = db_session.query(Ticket).filter(
        Ticket.created_at >= date_from,
        Ticket.created_at < date_to_inclusive
    )

    # Apply permission filters
    query = apply_ticket_permission_filter(query, user, db_session)

    # Apply queue filter if specified
    if queue_ids:
        query = query.filter(Ticket.queue_id.in_(queue_ids))

    tickets = query.all()
    total_tickets = len(tickets)

    # Group tickets
    grouped_data = {}
    for ticket in tickets:
        if group_by == 'status':
            key = ticket.status.value if ticket.status else 'No Status'
        elif group_by == 'queue':
            key = ticket.queue.name if ticket.queue else 'No Queue'
        elif group_by == 'priority':
            key = ticket.priority.value if ticket.priority else 'No Priority'
        elif group_by == 'category':
            key = ticket.category.value if ticket.category else 'No Category'
        else:
            key = 'Unknown'

        grouped_data[key] = grouped_data.get(key, 0) + 1

    # Calculate percentages and format data
    report_data = []
    for key, count in sorted(grouped_data.items(), key=lambda x: x[1], reverse=True):
        percentage = round((count / total_tickets * 100), 1) if total_tickets > 0 else 0
        report_data.append({
            group_by: key,
            'count': count,
            'percentage': percentage
        })

    # Generate chart data
    charts = [
        {
            'type': 'pie',
            'title': f'Tickets by {group_by.title()}',
            'data': {
                'labels': [item[group_by] for item in report_data],
                'values': [item['count'] for item in report_data]
            }
        }
    ]

    return {
        'summary': {
            'total_tickets': total_tickets,
            'date_range': f"{date_from.strftime('%b %d, %Y')} - {date_to.strftime('%b %d, %Y')}",
            'group_by': group_by
        },
        'data': report_data,
        'charts': charts
    }


def generate_ticket_resolution_time_report(db_session, user, parameters):
    """Generate ticket resolution time report data."""
    date_from = datetime.fromisoformat(parameters['date_from'])
    date_to = datetime.fromisoformat(parameters['date_to'])
    date_to_inclusive = date_to + timedelta(days=1)

    queue_ids = parameters.get('queue_ids', [])

    # Query resolved tickets only
    query = db_session.query(Ticket).filter(
        Ticket.created_at >= date_from,
        Ticket.created_at < date_to_inclusive,
        Ticket.status.in_([TicketStatus.RESOLVED, TicketStatus.RESOLVED_DELIVERED])
    )

    # Apply permission filters
    query = apply_ticket_permission_filter(query, user, db_session)

    if queue_ids:
        query = query.filter(Ticket.queue_id.in_(queue_ids))

    tickets = query.all()

    # Calculate resolution times by category
    category_times = {}
    category_counts = {}

    for ticket in tickets:
        category = ticket.category.value if ticket.category else 'No Category'

        # Resolution time in hours
        resolution_time = (ticket.updated_at - ticket.created_at).total_seconds() / 3600

        if category not in category_times:
            category_times[category] = 0
            category_counts[category] = 0

        category_times[category] += resolution_time
        category_counts[category] += 1

    # Calculate averages
    report_data = []
    for category in sorted(category_times.keys()):
        avg_hours = round(category_times[category] / category_counts[category], 2)
        report_data.append({
            'category': category,
            'resolved_count': category_counts[category],
            'avg_resolution_hours': avg_hours,
            'avg_resolution_days': round(avg_hours / 24, 2)
        })

    total_resolved = len(tickets)
    overall_avg = round(sum(category_times.values()) / total_resolved, 2) if total_resolved > 0 else 0

    charts = [
        {
            'type': 'bar',
            'title': 'Average Resolution Time by Category',
            'data': {
                'labels': [item['category'] for item in report_data],
                'values': [item['avg_resolution_hours'] for item in report_data]
            }
        }
    ]

    return {
        'summary': {
            'total_resolved': total_resolved,
            'overall_avg_hours': overall_avg,
            'date_range': f"{date_from.strftime('%b %d, %Y')} - {date_to.strftime('%b %d, %Y')}"
        },
        'data': report_data,
        'charts': charts
    }


def generate_asset_inventory_report(db_session, user, parameters):
    """Generate asset inventory report data."""
    status_filter = parameters.get('status', [])
    company_id = parameters.get('company_id')
    asset_type_filter = parameters.get('asset_type', [])

    query = db_session.query(Asset)

    # Apply permission filters
    query = apply_asset_permission_filter(query, user)

    # Apply status filter
    if status_filter:
        status_enums = []
        for s in status_filter:
            for status_enum in AssetStatus:
                if status_enum.value.lower() == s.lower() or status_enum.name.lower() == s.lower().replace(' ', '_'):
                    status_enums.append(status_enum)
                    break
        if status_enums:
            query = query.filter(Asset.status.in_(status_enums))

    # Apply company filter via customer_user
    if company_id:
        query = query.join(CustomerUser, Asset.customer_id == CustomerUser.id).filter(
            CustomerUser.company_id == company_id
        )

    # Apply asset type filter
    if asset_type_filter:
        type_conditions = []
        for at in asset_type_filter:
            type_conditions.append(func.lower(Asset.asset_type) == at.lower())
        query = query.filter(or_(*type_conditions))

    assets = query.all()

    # Format report data
    report_data = []
    for asset in assets:
        report_data.append({
            'asset_tag': asset.asset_tag,
            'serial_number': asset.serial_num,
            'name': asset.name,
            'model': asset.model,
            'asset_type': asset.asset_type,
            'status': asset.status.value if asset.status else 'Unknown',
            'customer': asset.customer_user.name if asset.customer_user else None,
            'country': asset.country,
            'receiving_date': asset.receiving_date.isoformat() if asset.receiving_date else None
        })

    # Summary stats
    status_counts = {}
    for asset in assets:
        status = asset.status.value if asset.status else 'Unknown'
        status_counts[status] = status_counts.get(status, 0) + 1

    charts = [
        {
            'type': 'pie',
            'title': 'Assets by Status',
            'data': {
                'labels': list(status_counts.keys()),
                'values': list(status_counts.values())
            }
        }
    ]

    return {
        'summary': {
            'total_assets': len(assets),
            'status_breakdown': status_counts
        },
        'data': report_data,
        'charts': charts
    }


def generate_asset_by_status_report(db_session, user, parameters):
    """Generate asset by status report data."""
    company_id = parameters.get('company_id')
    country = parameters.get('country')

    query = db_session.query(Asset)

    # Apply permission filters
    query = apply_asset_permission_filter(query, user)

    if company_id:
        query = query.join(CustomerUser, Asset.customer_id == CustomerUser.id).filter(
            CustomerUser.company_id == company_id
        )

    if country:
        query = query.filter(Asset.country == country)

    assets = query.all()
    total = len(assets)

    # Count by status
    status_counts = {}
    for asset in assets:
        status = asset.status.value if asset.status else 'Unknown'
        status_counts[status] = status_counts.get(status, 0) + 1

    report_data = []
    for status, count in sorted(status_counts.items(), key=lambda x: x[1], reverse=True):
        percentage = round((count / total * 100), 1) if total > 0 else 0
        report_data.append({
            'status': status,
            'count': count,
            'percentage': percentage
        })

    charts = [
        {
            'type': 'donut',
            'title': 'Asset Distribution by Status',
            'data': {
                'labels': [item['status'] for item in report_data],
                'values': [item['count'] for item in report_data]
            }
        }
    ]

    return {
        'summary': {
            'total_assets': total
        },
        'data': report_data,
        'charts': charts
    }


def generate_asset_age_distribution_report(db_session, user, parameters):
    """Generate asset age distribution report data."""
    company_id = parameters.get('company_id')

    query = db_session.query(Asset)

    # Apply permission filters
    query = apply_asset_permission_filter(query, user)

    if company_id:
        query = query.join(CustomerUser, Asset.customer_id == CustomerUser.id).filter(
            CustomerUser.company_id == company_id
        )

    assets = query.all()
    current_date = datetime.utcnow()

    # Age buckets
    age_distribution = {
        '0-6 months': 0,
        '6-12 months': 0,
        '1-2 years': 0,
        '2-3 years': 0,
        '3-4 years': 0,
        '4+ years': 0
    }

    for asset in assets:
        if asset.receiving_date:
            age_days = (current_date - asset.receiving_date).days
            if age_days <= 180:
                age_distribution['0-6 months'] += 1
            elif age_days <= 365:
                age_distribution['6-12 months'] += 1
            elif age_days <= 730:
                age_distribution['1-2 years'] += 1
            elif age_days <= 1095:
                age_distribution['2-3 years'] += 1
            elif age_days <= 1460:
                age_distribution['3-4 years'] += 1
            else:
                age_distribution['4+ years'] += 1

    total = len(assets)
    report_data = []
    for age_bucket, count in age_distribution.items():
        percentage = round((count / total * 100), 1) if total > 0 else 0
        report_data.append({
            'age_range': age_bucket,
            'count': count,
            'percentage': percentage
        })

    charts = [
        {
            'type': 'bar',
            'title': 'Asset Age Distribution',
            'data': {
                'labels': [item['age_range'] for item in report_data],
                'values': [item['count'] for item in report_data]
            }
        }
    ]

    return {
        'summary': {
            'total_assets': total,
            'assets_with_date': sum(age_distribution.values())
        },
        'data': report_data,
        'charts': charts
    }


def generate_user_activity_report(db_session, user, parameters):
    """Generate user activity report data."""
    date_from = datetime.fromisoformat(parameters['date_from'])
    date_to = datetime.fromisoformat(parameters['date_to'])
    date_to_inclusive = date_to + timedelta(days=1)

    user_ids = parameters.get('user_ids', [])

    # Query tickets for workload
    query = db_session.query(
        Ticket.assigned_to_id,
        func.count(Ticket.id).label('assigned_count')
    ).filter(
        Ticket.created_at >= date_from,
        Ticket.created_at < date_to_inclusive
    )

    if user_ids:
        query = query.filter(Ticket.assigned_to_id.in_(user_ids))

    query = query.group_by(Ticket.assigned_to_id)
    assigned_counts = {row[0]: row[1] for row in query.all()}

    # Query resolved tickets
    resolved_query = db_session.query(
        Ticket.assigned_to_id,
        func.count(Ticket.id).label('resolved_count')
    ).filter(
        Ticket.updated_at >= date_from,
        Ticket.updated_at < date_to_inclusive,
        Ticket.status.in_([TicketStatus.RESOLVED, TicketStatus.RESOLVED_DELIVERED])
    )

    if user_ids:
        resolved_query = resolved_query.filter(Ticket.assigned_to_id.in_(user_ids))

    resolved_query = resolved_query.group_by(Ticket.assigned_to_id)
    resolved_counts = {row[0]: row[1] for row in resolved_query.all()}

    # Get user info
    all_user_ids = set(assigned_counts.keys()) | set(resolved_counts.keys())
    users = db_session.query(User).filter(User.id.in_(all_user_ids)).all()
    user_map = {u.id: u for u in users}

    report_data = []
    for uid in all_user_ids:
        if uid is None:
            continue
        user_obj = user_map.get(uid)
        if not user_obj:
            continue

        assigned = assigned_counts.get(uid, 0)
        resolved = resolved_counts.get(uid, 0)
        resolution_rate = round((resolved / assigned * 100), 1) if assigned > 0 else 0

        report_data.append({
            'user_id': uid,
            'username': user_obj.username,
            'tickets_assigned': assigned,
            'tickets_resolved': resolved,
            'resolution_rate': resolution_rate
        })

    # Sort by assigned tickets
    report_data.sort(key=lambda x: x['tickets_assigned'], reverse=True)

    charts = [
        {
            'type': 'bar',
            'title': 'Tickets by User',
            'data': {
                'labels': [item['username'] for item in report_data[:10]],
                'datasets': [
                    {
                        'label': 'Assigned',
                        'values': [item['tickets_assigned'] for item in report_data[:10]]
                    },
                    {
                        'label': 'Resolved',
                        'values': [item['tickets_resolved'] for item in report_data[:10]]
                    }
                ]
            }
        }
    ]

    return {
        'summary': {
            'total_users': len(report_data),
            'total_assigned': sum(assigned_counts.values()),
            'total_resolved': sum(resolved_counts.values()),
            'date_range': f"{date_from.strftime('%b %d, %Y')} - {date_to.strftime('%b %d, %Y')}"
        },
        'data': report_data,
        'charts': charts
    }


def generate_customer_tickets_report(db_session, user, parameters):
    """Generate customer ticket volume report data."""
    date_from = datetime.fromisoformat(parameters['date_from'])
    date_to = datetime.fromisoformat(parameters['date_to'])
    date_to_inclusive = date_to + timedelta(days=1)

    company_id = parameters.get('company_id')
    top_n = parameters.get('top_n', 10)

    # Build query
    query = db_session.query(Ticket).filter(
        Ticket.created_at >= date_from,
        Ticket.created_at < date_to_inclusive
    )

    # Apply permission filters
    query = apply_ticket_permission_filter(query, user, db_session)

    tickets = query.options(
        joinedload(Ticket.customer).joinedload(CustomerUser.company)
    ).all()

    # Count by customer
    customer_counts = {}
    company_counts = {}

    for ticket in tickets:
        if ticket.customer:
            customer_name = ticket.customer.name
            customer_counts[customer_name] = customer_counts.get(customer_name, 0) + 1

            if ticket.customer.company:
                company_name = ticket.customer.company.name
                if company_id and ticket.customer.company.id != company_id:
                    continue
                company_counts[company_name] = company_counts.get(company_name, 0) + 1

    # Sort and limit
    top_customers = sorted(customer_counts.items(), key=lambda x: x[1], reverse=True)[:top_n]
    top_companies = sorted(company_counts.items(), key=lambda x: x[1], reverse=True)[:top_n]

    report_data = []
    for customer, count in top_customers:
        percentage = round((count / len(tickets) * 100), 1) if tickets else 0
        report_data.append({
            'customer': customer,
            'ticket_count': count,
            'percentage': percentage
        })

    charts = [
        {
            'type': 'bar',
            'title': f'Top {top_n} Customers by Ticket Volume',
            'data': {
                'labels': [item['customer'] for item in report_data],
                'values': [item['ticket_count'] for item in report_data]
            }
        }
    ]

    return {
        'summary': {
            'total_tickets': len(tickets),
            'unique_customers': len(customer_counts),
            'unique_companies': len(company_counts),
            'date_range': f"{date_from.strftime('%b %d, %Y')} - {date_to.strftime('%b %d, %Y')}"
        },
        'data': report_data,
        'charts': charts
    }


# =============================================================================
# PERMISSION FILTERS
# =============================================================================

def apply_ticket_permission_filter(query, user, db_session):
    """Apply permission-based filtering to ticket query."""
    from models.user_queue_permission import UserQueuePermission

    if user.user_type in [UserType.SUPER_ADMIN, UserType.DEVELOPER]:
        return query

    if user.user_type in [UserType.COUNTRY_ADMIN, UserType.SUPERVISOR]:
        # Filter by accessible queues
        accessible_queue_ids = user.get_accessible_queue_ids(db_session)
        if accessible_queue_ids is not None:
            query = query.filter(Ticket.queue_id.in_(accessible_queue_ids))

        # Also filter by country if user has country restrictions
        if user.assigned_countries:
            query = query.filter(Ticket.country.in_(user.assigned_countries))

    elif user.user_type == UserType.CLIENT:
        if user.company_id:
            company_customer_ids = db_session.query(CustomerUser.id).filter(
                CustomerUser.company_id == user.company_id
            ).all()
            company_customer_ids = [c[0] for c in company_customer_ids]

            query = query.filter(
                or_(
                    Ticket.requester_id == user.id,
                    Ticket.customer_id.in_(company_customer_ids) if company_customer_ids else False
                )
            )
        else:
            query = query.filter(Ticket.requester_id == user.id)

    return query


def apply_asset_permission_filter(query, user):
    """Apply permission-based filtering to asset query."""
    if user.user_type in [UserType.SUPER_ADMIN, UserType.DEVELOPER]:
        return query

    if user.user_type == UserType.COUNTRY_ADMIN:
        if user.assigned_countries:
            query = query.filter(Asset.country.in_(user.assigned_countries))

    elif user.user_type == UserType.CLIENT:
        if user.company_id:
            query = query.join(CustomerUser, Asset.customer_id == CustomerUser.id).filter(
                CustomerUser.company_id == user.company_id
            )

    return query


# =============================================================================
# PARAMETER VALIDATION
# =============================================================================

def validate_report_parameters(template, parameters):
    """
    Validate parameters against template definition.

    Args:
        template: Report template definition
        parameters: Parameters provided by user

    Returns:
        Tuple of (is_valid, error_message)
    """
    template_params = {p['key']: p for p in template.get('parameters', [])}

    # Check required parameters
    for param_def in template.get('parameters', []):
        if param_def.get('required', False):
            if param_def['key'] not in parameters or parameters[param_def['key']] is None:
                return False, f"Missing required parameter: {param_def['key']}"

    # Validate parameter types
    for key, value in parameters.items():
        if key not in template_params:
            continue

        param_def = template_params[key]
        param_type = param_def.get('type')

        if param_type == 'date':
            try:
                datetime.fromisoformat(str(value))
            except ValueError:
                return False, f"Invalid date format for {key}. Use ISO format (YYYY-MM-DD)"

        elif param_type == 'select':
            options = param_def.get('options', [])
            if options and value not in options:
                return False, f"Invalid value for {key}. Must be one of: {', '.join(options)}"

        elif param_type == 'multi_select':
            if not isinstance(value, list):
                return False, f"Parameter {key} must be a list"
            options = param_def.get('options', [])
            if options:
                for v in value:
                    if v not in options:
                        return False, f"Invalid value '{v}' for {key}. Must be one of: {', '.join(options)}"

        elif param_type == 'number':
            if not isinstance(value, (int, float)):
                return False, f"Parameter {key} must be a number"

    return True, None


# =============================================================================
# ENDPOINTS
# =============================================================================

@api_v2_bp.route('/reports/templates', methods=['GET'])
@dual_auth_required
@handle_exceptions
def list_report_templates():
    """
    List all available report templates.

    GET /api/v2/reports/templates

    Query Parameters:
        category (string, optional): Filter by category (tickets, inventory, users, analytics)

    Returns:
        200: List of report templates with metadata
        401: Authentication required
    """
    user = request.current_api_user
    category_filter = request.args.get('category')

    # Filter templates by user permissions
    accessible_templates = filter_templates_by_permission(user, REPORT_TEMPLATES)

    # Apply category filter if specified
    if category_filter:
        accessible_templates = [t for t in accessible_templates if t.get('category') == category_filter]

    # Build response
    response_data = accessible_templates

    meta = {
        'categories': REPORT_CATEGORIES,
        'total_templates': len(accessible_templates)
    }

    return api_response(
        data=response_data,
        meta=meta,
        message=f'Retrieved {len(accessible_templates)} report templates'
    )


@api_v2_bp.route('/reports/generate', methods=['POST'])
@dual_auth_required
@handle_exceptions
def generate_report():
    """
    Generate a report based on template and parameters.

    POST /api/v2/reports/generate

    Request Body:
    {
        "template_id": "string (required)",
        "parameters": {
            "date_from": "YYYY-MM-DD",
            "date_to": "YYYY-MM-DD",
            ...other template-specific parameters
        },
        "format": "json|csv|pdf (default: json)"
    }

    Returns:
        200: Generated report data
        400: Validation error
        403: Permission denied
        404: Template not found
    """
    user = request.current_api_user

    # Validate JSON body
    data, error = validate_json_body()
    if error:
        return error

    # Validate required fields
    is_valid, error = validate_required_fields(data, ['template_id'])
    if not is_valid:
        return error

    template_id = data.get('template_id')
    parameters = data.get('parameters', {})
    output_format = data.get('format', 'json')

    # Check if template exists
    if template_id not in REPORT_TEMPLATES:
        return api_error(
            ErrorCodes.RESOURCE_NOT_FOUND,
            f'Report template not found: {template_id}',
            status_code=404
        )

    template = REPORT_TEMPLATES[template_id]

    # Check permissions
    required_perms = template.get('permissions', [])
    if not check_user_report_permissions(user, required_perms):
        return api_error(
            ErrorCodes.PERMISSION_DENIED,
            'You do not have permission to generate this report',
            status_code=403
        )

    # Validate output format
    supported_formats = template.get('output_formats', ['json'])
    if output_format not in supported_formats:
        return api_error(
            ErrorCodes.INVALID_FIELD_VALUE,
            f'Unsupported output format: {output_format}. Supported: {", ".join(supported_formats)}',
            status_code=400
        )

    # Validate parameters
    is_valid, error_msg = validate_report_parameters(template, parameters)
    if not is_valid:
        return api_error(
            ErrorCodes.VALIDATION_ERROR,
            error_msg,
            status_code=400
        )

    db_session = db_manager.get_session()
    try:
        # Generate report based on template
        report_generators = {
            'ticket_summary': generate_ticket_summary_report,
            'ticket_resolution_time': generate_ticket_resolution_time_report,
            'asset_inventory': generate_asset_inventory_report,
            'asset_by_status': generate_asset_by_status_report,
            'asset_age_distribution': generate_asset_age_distribution_report,
            'user_activity': generate_user_activity_report,
            'customer_tickets': generate_customer_tickets_report
        }

        generator = report_generators.get(template_id)
        if not generator:
            return api_error(
                ErrorCodes.INTERNAL_ERROR,
                f'Report generator not implemented for: {template_id}',
                status_code=500
            )

        # Generate report data
        report_result = generator(db_session, user, parameters)

        # Generate unique report ID
        report_id = f"rpt_{uuid.uuid4().hex[:12]}"

        # Build response
        response_data = {
            'report_id': report_id,
            'template': template_id,
            'template_name': template['name'],
            'generated_at': datetime.utcnow().isoformat() + 'Z',
            'parameters': parameters,
            'format': output_format,
            'summary': report_result.get('summary', {}),
            'data': report_result.get('data', []),
            'charts': report_result.get('charts', [])
        }

        # Handle CSV format
        if output_format == 'csv':
            # Convert data to CSV string
            if report_result.get('data'):
                csv_output = io.StringIO()
                if isinstance(report_result['data'], list) and len(report_result['data']) > 0:
                    fieldnames = report_result['data'][0].keys()
                    writer = csv.DictWriter(csv_output, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(report_result['data'])
                response_data['csv_data'] = csv_output.getvalue()

        return api_response(
            data=response_data,
            message=f'Report generated successfully: {template["name"]}'
        )

    except Exception as e:
        logger.exception(f"Error generating report {template_id}: {str(e)}")
        return api_error(
            ErrorCodes.INTERNAL_ERROR,
            f'Failed to generate report: {str(e)}',
            status_code=500
        )
    finally:
        db_session.close()
