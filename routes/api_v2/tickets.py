"""
API v2 Ticket Endpoints

Provides comprehensive ticket management endpoints for the React frontend:
- GET /api/v2/tickets - List tickets with pagination, filtering, sorting, search
- POST /api/v2/tickets - Create new ticket
- PUT /api/v2/tickets/<id> - Update ticket
- POST /api/v2/tickets/<id>/assign - Assign ticket to user
- POST /api/v2/tickets/<id>/status - Change ticket status
"""

from flask import request
from datetime import datetime
from sqlalchemy.orm import joinedload, selectinload, load_only
from sqlalchemy import or_, func, and_, cast, String
import logging

from . import api_v2_bp
from .utils import (
    api_response,
    api_error,
    api_created,
    ErrorCodes,
    handle_exceptions,
    validate_json_body,
    validate_required_fields,
    dual_auth_required,
    get_pagination_params,
    paginate_query,
    get_sorting_params,
    apply_sorting,
    get_filter_param,
    get_date_filter,
    get_search_term,
)

from utils.db_manager import DatabaseManager
from utils.timezone_utils import singapore_now_as_utc
from models.ticket import Ticket, TicketStatus, TicketPriority, TicketCategory
from models.user import User, UserType
from models.customer_user import CustomerUser
from models.asset import Asset, AssetStatus
from models.queue import Queue
from models.activity import Activity
from models.notification import Notification
from models.ticket_category_config import TicketCategoryConfig
from models.accessory import Accessory

logger = logging.getLogger(__name__)
db_manager = DatabaseManager()


def format_ticket(ticket):
    """Format a ticket object for API response"""
    return {
        'id': ticket.id,
        'display_id': ticket.display_id,
        'subject': ticket.subject,
        'description': ticket.description,
        'status': ticket.status.value if ticket.status else None,
        'custom_status': ticket.custom_status,
        'priority': ticket.priority.value if ticket.priority else None,
        'category': ticket.category.value if ticket.category else None,
        'queue_id': ticket.queue_id,
        'queue_name': ticket.queue.name if ticket.queue else None,
        'requester_id': ticket.requester_id,
        'requester_name': ticket.requester.username if ticket.requester else None,
        'assigned_to_id': ticket.assigned_to_id,
        'assigned_to_name': ticket.assigned_to.username if ticket.assigned_to else None,
        'customer_id': ticket.customer_id,
        'customer_name': ticket.customer.name if ticket.customer else None,
        'asset_id': ticket.asset_id,
        'country': ticket.country,
        'shipping_address': ticket.shipping_address,
        'shipping_tracking': ticket.shipping_tracking,
        'shipping_carrier': ticket.shipping_carrier,
        'shipping_status': ticket.shipping_status,
        'notes': ticket.notes,
        'created_at': ticket.created_at.isoformat() if ticket.created_at else None,
        'updated_at': ticket.updated_at.isoformat() if ticket.updated_at else None,
    }


def check_queue_permission(user, queue_id, permission_type='view'):
    """Check if user has permission for a queue"""
    from models.user_queue_permission import UserQueuePermission

    # Super admins and developers have full access
    if user.user_type in [UserType.SUPER_ADMIN, UserType.DEVELOPER]:
        return True

    db_session = db_manager.get_session()
    try:
        permission = db_session.query(UserQueuePermission).filter_by(
            user_id=user.id,
            queue_id=queue_id
        ).first()

        if not permission:
            return False

        if permission_type == 'view':
            return permission.can_view
        elif permission_type == 'create':
            return permission.can_create
        elif permission_type == 'edit':
            return permission.can_edit
        else:
            return permission.can_view
    finally:
        db_session.close()


def check_ticket_permission(user, ticket):
    """Check if user has permission to access a ticket"""
    from models.user_queue_permission import UserQueuePermission

    # Super admins and developers have full access
    if user.user_type in [UserType.SUPER_ADMIN, UserType.DEVELOPER]:
        return True, None

    db_session = db_manager.get_session()
    try:
        # COUNTRY_ADMIN and SUPERVISOR: Check queue and country permissions
        if user.user_type in [UserType.COUNTRY_ADMIN, UserType.SUPERVISOR]:
            has_queue_access = False
            if ticket.queue_id:
                queue_permission = db_session.query(UserQueuePermission).filter_by(
                    user_id=user.id,
                    queue_id=ticket.queue_id,
                    can_view=True
                ).first()
                has_queue_access = queue_permission is not None

            has_country_access = True
            if user.assigned_countries and ticket.country:
                has_country_access = ticket.country in user.assigned_countries

            if not has_queue_access:
                return False, "You do not have permission to access tickets in this queue"
            if not has_country_access:
                return False, "You do not have permission to access tickets from this country"
            return True, None

        # CLIENT: Check if ticket belongs to their company or they created it
        if user.user_type == UserType.CLIENT:
            if not user.company_id:
                return False, "Your account is not associated with a company"

            customer_company_id = ticket.customer.company_id if ticket.customer else None
            is_requester = ticket.requester_id == user.id
            is_same_company = customer_company_id == user.company_id

            if is_requester or is_same_company:
                return True, None
            return False, "You do not have permission to view this ticket"

        return False, "Unknown user type"
    finally:
        db_session.close()


def log_activity(db_session, user_id, activity_type, content, ticket_id):
    """Log an activity for a ticket"""
    activity = Activity(
        user_id=user_id,
        type=activity_type,
        content=content,
        reference_id=ticket_id
    )
    db_session.add(activity)


def create_notification(db_session, user_id, notification_type, title, message, ticket_id):
    """Create an in-app notification"""
    notification = Notification(
        user_id=user_id,
        type=notification_type,
        title=title,
        message=message,
        reference_type='ticket',
        reference_id=ticket_id,
        is_read=False,
        created_at=datetime.utcnow()
    )
    db_session.add(notification)


def format_ticket_list_item(ticket):
    """Format a ticket object for list API response (optimized for list view)"""
    return {
        'id': ticket.id,
        'display_id': ticket.display_id,
        'subject': ticket.subject,
        'status': ticket.status.value if ticket.status else None,
        'custom_status': ticket.custom_status,
        'priority': ticket.priority.value if ticket.priority else None,
        'category': ticket.category.value if ticket.category else None,
        'queue': {
            'id': ticket.queue.id,
            'name': ticket.queue.name
        } if ticket.queue else None,
        'assigned_to': {
            'id': ticket.assigned_to.id,
            'username': ticket.assigned_to.username
        } if ticket.assigned_to else None,
        'customer': {
            'id': ticket.customer.id,
            'name': ticket.customer.name
        } if ticket.customer else None,
        'created_at': ticket.created_at.isoformat() + 'Z' if ticket.created_at else None,
        'updated_at': ticket.updated_at.isoformat() + 'Z' if ticket.updated_at else None,
    }


def get_ticket_status_counts(db_session, base_query):
    """Get ticket counts by status category for the meta response"""
    # Total count
    total = base_query.count()

    # Count by status categories
    # "new" / "open" statuses
    new_count = base_query.filter(
        or_(
            Ticket.status == TicketStatus.NEW,
            func.lower(Ticket.custom_status).like('%new%'),
            func.lower(Ticket.custom_status).like('%open%')
        )
    ).count()

    # "in_progress" / "processing" statuses
    in_progress_count = base_query.filter(
        or_(
            Ticket.status == TicketStatus.IN_PROGRESS,
            Ticket.status == TicketStatus.PROCESSING,
            func.lower(Ticket.custom_status).like('%progress%'),
            func.lower(Ticket.custom_status).like('%processing%')
        )
    ).count()

    # "resolved" / "completed" statuses
    resolved_count = base_query.filter(
        or_(
            Ticket.status == TicketStatus.RESOLVED,
            Ticket.status == TicketStatus.RESOLVED_DELIVERED,
            func.lower(Ticket.custom_status).like('%resolved%'),
            func.lower(Ticket.custom_status).like('%complete%'),
            func.lower(Ticket.custom_status).like('%delivered%')
        )
    ).count()

    # "on_hold" statuses
    on_hold_count = base_query.filter(
        or_(
            Ticket.status == TicketStatus.ON_HOLD,
            func.lower(Ticket.custom_status).like('%hold%'),
            func.lower(Ticket.custom_status).like('%pending%')
        )
    ).count()

    return {
        'total': total,
        'new': new_count,
        'in_progress': in_progress_count,
        'resolved': resolved_count,
        'on_hold': on_hold_count
    }


# =============================================================================
# LIST TICKETS
# =============================================================================

@api_v2_bp.route('/tickets', methods=['GET'])
@dual_auth_required
@handle_exceptions
def list_tickets():
    """
    List tickets with pagination, filtering, sorting, and search

    GET /api/v2/tickets

    Query Parameters:
        page (int, default=1): Page number
        per_page (int, default=20, max=100): Items per page
        sort (string): Field to sort by (created_at, updated_at, priority, status, subject)
        order (string): asc or desc (default: desc)
        search (string): Search in subject, id, customer name
        status (string): Filter by status (new, open, in_progress, resolved, etc.)
        queue_id (int): Filter by queue
        priority (string): Filter by priority (Low, Medium, High, Critical)
        assigned_to_id (int): Filter by assignee
        customer_id (int): Filter by customer
        category (string): Filter by category
        date_from (string): Created after date (ISO 8601)
        date_to (string): Created before date (ISO 8601)

    Returns:
        200: List of tickets with pagination metadata
        401: Authentication required
        403: Permission denied
    """
    from models.user_queue_permission import UserQueuePermission

    user = request.current_api_user

    # Get pagination parameters
    page, per_page = get_pagination_params(default_page=1, default_per_page=20, max_per_page=100)

    # Get sorting parameters
    allowed_sort_fields = ['created_at', 'updated_at', 'priority', 'status', 'subject', 'id']
    sort_field, sort_order = get_sorting_params(allowed_sort_fields, default_sort='created_at', default_order='desc')

    # Get filter parameters
    search_term = get_search_term()
    status_filter = get_filter_param('status', str)
    queue_id_filter = get_filter_param('queue_id', int)
    priority_filter = get_filter_param('priority', str)
    assigned_to_id_filter = get_filter_param('assigned_to_id', int)
    customer_id_filter = get_filter_param('customer_id', int)
    category_filter = get_filter_param('category', str)
    date_from = get_date_filter('date_from')
    date_to = get_date_filter('date_to')

    db_session = db_manager.get_session()
    try:
        # Build base query with optimized loading
        query = db_session.query(Ticket).options(
            load_only(
                Ticket.id, Ticket.subject, Ticket.status, Ticket.custom_status,
                Ticket.priority, Ticket.category, Ticket.queue_id,
                Ticket.assigned_to_id, Ticket.requester_id, Ticket.customer_id,
                Ticket.created_at, Ticket.updated_at, Ticket.country
            ),
            selectinload(Ticket.assigned_to).load_only(User.id, User.username),
            selectinload(Ticket.requester).load_only(User.id, User.username),
            selectinload(Ticket.queue).load_only(Queue.id, Queue.name),
            selectinload(Ticket.customer).load_only(CustomerUser.id, CustomerUser.name)
        )

        # Apply permission filtering based on user type
        if user.user_type in [UserType.SUPER_ADMIN, UserType.DEVELOPER]:
            # Super admins and developers can see all tickets
            pass
        elif user.user_type in [UserType.COUNTRY_ADMIN, UserType.SUPERVISOR]:
            # Filter by accessible queues
            accessible_queue_ids = user.get_accessible_queue_ids(db_session)
            if accessible_queue_ids is not None:
                query = query.filter(Ticket.queue_id.in_(accessible_queue_ids))
        elif user.user_type == UserType.CLIENT:
            # Clients can only see tickets for their company or tickets they created
            if user.company_id:
                # Get all customer users belonging to the same company
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
                # Client without company can only see their own tickets
                query = query.filter(
                    or_(
                        Ticket.requester_id == user.id,
                        Ticket.assigned_to_id == user.id
                    )
                )
        else:
            # Regular users can only see their own tickets
            query = query.filter(
                or_(
                    Ticket.requester_id == user.id,
                    Ticket.assigned_to_id == user.id
                )
            )

        # Store base query for counts (before additional filters)
        base_query_for_counts = query

        # Apply search filter
        if search_term:
            search_pattern = f'%{search_term}%'
            # Try to parse as ticket ID (TICK-XXXX format)
            ticket_id = None
            if search_term.upper().startswith('TICK-'):
                try:
                    ticket_id = int(search_term.upper().replace('TICK-', ''))
                except ValueError:
                    pass
            elif search_term.isdigit():
                ticket_id = int(search_term)

            search_conditions = [
                Ticket.subject.ilike(search_pattern),
            ]

            if ticket_id:
                search_conditions.append(Ticket.id == ticket_id)

            # Search in customer name via join
            search_conditions.append(
                Ticket.customer.has(CustomerUser.name.ilike(search_pattern))
            )

            query = query.filter(or_(*search_conditions))

        # Apply status filter
        if status_filter:
            status_lower = status_filter.lower()
            # Check if it's a system status
            status_matched = False
            for ts in TicketStatus:
                if ts.name.lower() == status_lower or ts.value.lower() == status_lower:
                    query = query.filter(
                        or_(
                            Ticket.status == ts,
                            func.lower(Ticket.custom_status) == status_lower
                        )
                    )
                    status_matched = True
                    break

            if not status_matched:
                # It might be a custom status
                query = query.filter(func.lower(Ticket.custom_status) == status_lower)

        # Apply queue filter
        if queue_id_filter:
            # Verify user has access to this queue
            if user.user_type not in [UserType.SUPER_ADMIN, UserType.DEVELOPER]:
                accessible_queue_ids = user.get_accessible_queue_ids(db_session)
                if accessible_queue_ids is not None and queue_id_filter not in accessible_queue_ids:
                    return api_error(
                        ErrorCodes.PERMISSION_DENIED,
                        'You do not have access to this queue',
                        status_code=403
                    )
            query = query.filter(Ticket.queue_id == queue_id_filter)

        # Apply priority filter
        if priority_filter:
            try:
                priority_enum = TicketPriority[priority_filter.upper()]
                query = query.filter(Ticket.priority == priority_enum)
            except KeyError:
                # Try by value
                for tp in TicketPriority:
                    if tp.value.lower() == priority_filter.lower():
                        query = query.filter(Ticket.priority == tp)
                        break

        # Apply assigned_to filter
        if assigned_to_id_filter:
            query = query.filter(Ticket.assigned_to_id == assigned_to_id_filter)

        # Apply customer filter
        if customer_id_filter:
            query = query.filter(Ticket.customer_id == customer_id_filter)

        # Apply category filter
        if category_filter:
            try:
                category_enum = TicketCategory[category_filter.upper().replace(' ', '_')]
                query = query.filter(Ticket.category == category_enum)
            except KeyError:
                # Try by value
                for tc in TicketCategory:
                    if tc.value.lower() == category_filter.lower():
                        query = query.filter(Ticket.category == tc)
                        break

        # Apply date filters
        if date_from:
            query = query.filter(Ticket.created_at >= date_from)

        if date_to:
            # Add one day to include tickets created on the end date
            from datetime import timedelta
            date_to_inclusive = date_to + timedelta(days=1)
            query = query.filter(Ticket.created_at < date_to_inclusive)

        # Get counts for meta (using base query before filters for overall counts)
        counts = get_ticket_status_counts(db_session, base_query_for_counts)

        # Apply sorting
        query = apply_sorting(query, Ticket, sort_field, sort_order)

        # Apply pagination
        items, pagination_meta = paginate_query(query, page, per_page)

        # Format tickets for response
        tickets_data = [format_ticket_list_item(ticket) for ticket in items]

        # Build response meta
        meta = {
            'pagination': pagination_meta['pagination'],
            'counts': counts,
            'request_id': pagination_meta.get('request_id'),
            'timestamp': pagination_meta.get('timestamp')
        }

        return api_response(
            data=tickets_data,
            meta=meta
        )

    except Exception as e:
        logger.exception(f"Error listing tickets: {str(e)}")
        return api_error(
            ErrorCodes.INTERNAL_ERROR,
            f'Failed to list tickets: {str(e)}',
            status_code=500
        )
    finally:
        db_session.close()


# =============================================================================
# CREATE TICKET
# =============================================================================

@api_v2_bp.route('/tickets', methods=['POST'])
@dual_auth_required
@handle_exceptions
def create_ticket():
    """
    Create a new ticket

    POST /api/v2/tickets

    Request Body:
    {
        "subject": "string (required)",
        "description": "string",
        "category": "string (enum value)",
        "priority": "string (Low/Medium/High/Critical)",
        "queue_id": "integer (required)",
        "customer_id": "integer",
        "asset_id": "integer",
        "shipping_address": "string",
        "shipping_tracking": "string",
        "shipping_carrier": "string",
        "country": "string",
        "notes": "string",
        "assigned_to_id": "integer"
    }

    Returns:
        201: Created ticket data
        400: Validation error
        403: Permission denied
    """
    user = request.current_api_user

    # Validate JSON body
    data, error = validate_json_body()
    if error:
        return error

    # Validate required fields
    is_valid, error = validate_required_fields(data, ['subject', 'queue_id'])
    if not is_valid:
        return error

    queue_id = data.get('queue_id')
    category_value = data.get('category')

    # Check queue permission
    if not user.can_create_in_queue(queue_id):
        return api_error(
            ErrorCodes.PERMISSION_DENIED,
            'You do not have permission to create tickets in this queue',
            status_code=403
        )

    db_session = db_manager.get_session()
    try:
        # Verify queue exists
        queue = db_session.query(Queue).get(queue_id)
        if not queue:
            return api_error(
                ErrorCodes.RESOURCE_NOT_FOUND,
                'Queue not found',
                status_code=404
            )

        # Parse category
        ticket_category = None
        is_custom_category = False
        if category_value:
            # Check if it's a custom category
            custom_category = db_session.query(TicketCategoryConfig).filter_by(name=category_value).first()
            if custom_category:
                is_custom_category = True
            else:
                # Try to parse as predefined category
                try:
                    ticket_category = TicketCategory[category_value]
                except KeyError:
                    try:
                        ticket_category = TicketCategory(category_value)
                    except ValueError:
                        return api_error(
                            ErrorCodes.INVALID_FIELD_VALUE,
                            f'Invalid category: {category_value}',
                            status_code=400
                        )

        # Parse priority
        priority = TicketPriority.MEDIUM
        priority_value = data.get('priority')
        if priority_value:
            try:
                priority = TicketPriority[priority_value.upper()]
            except KeyError:
                try:
                    priority = TicketPriority(priority_value)
                except ValueError:
                    return api_error(
                        ErrorCodes.INVALID_FIELD_VALUE,
                        f'Invalid priority: {priority_value}. Valid values: Low, Medium, High, Critical',
                        status_code=400
                    )

        # Validate customer if provided
        customer_id = data.get('customer_id')
        if customer_id:
            customer = db_session.query(CustomerUser).get(customer_id)
            if not customer:
                return api_error(
                    ErrorCodes.RESOURCE_NOT_FOUND,
                    'Customer not found',
                    status_code=404
                )

        # Validate asset if provided
        asset_id = data.get('asset_id')
        asset = None
        if asset_id:
            asset = db_session.query(Asset).get(asset_id)
            if not asset:
                return api_error(
                    ErrorCodes.RESOURCE_NOT_FOUND,
                    'Asset not found',
                    status_code=404
                )

        # Determine assigned_to_id
        assigned_to_id = data.get('assigned_to_id')
        if not assigned_to_id:
            assigned_to_id = user.id  # Default to requester

        # Build description for custom category
        description = data.get('description', '')
        if is_custom_category:
            description = f'[CUSTOM CATEGORY: {category_value}]\n{description}'

        # Create the ticket
        ticket = Ticket(
            subject=data.get('subject'),
            description=description,
            requester_id=user.id,
            assigned_to_id=assigned_to_id,
            category=ticket_category,
            priority=priority,
            queue_id=queue_id,
            customer_id=customer_id,
            asset_id=asset_id,
            country=data.get('country'),
            shipping_address=data.get('shipping_address'),
            shipping_tracking=data.get('shipping_tracking'),
            shipping_carrier=data.get('shipping_carrier', 'singpost'),
            notes=data.get('notes'),
            status=TicketStatus.NEW,
            created_at=singapore_now_as_utc()
        )

        db_session.add(ticket)
        db_session.flush()  # Get ticket ID

        # Create ticket-asset relationship if asset provided
        if asset:
            from sqlalchemy import text
            existing_check = text("""
                SELECT COUNT(*) FROM ticket_assets
                WHERE ticket_id = :ticket_id AND asset_id = :asset_id
            """)
            existing_count = db_session.execute(existing_check, {"ticket_id": ticket.id, "asset_id": asset.id}).scalar()

            if existing_count == 0:
                insert_stmt = text("""
                    INSERT INTO ticket_assets (ticket_id, asset_id)
                    VALUES (:ticket_id, :asset_id)
                """)
                db_session.execute(insert_stmt, {"ticket_id": ticket.id, "asset_id": asset.id})

        # Log activity
        log_activity(
            db_session,
            user.id,
            'ticket_created',
            f'Created ticket {ticket.display_id}: {ticket.subject}',
            ticket.id
        )

        # Notify assigned user if different from requester
        if assigned_to_id and assigned_to_id != user.id:
            create_notification(
                db_session,
                assigned_to_id,
                'ticket_assigned',
                f'Ticket {ticket.display_id} Assigned',
                f'{user.username} created and assigned ticket "{ticket.subject}" to you',
                ticket.id
            )

            # Send email notification
            try:
                from utils.email_sender import send_ticket_assignment_notification
                assigned_user = db_session.query(User).get(assigned_to_id)
                if assigned_user and assigned_user.email:
                    send_ticket_assignment_notification(
                        assigned_user=assigned_user,
                        assigner=user,
                        ticket=ticket,
                        previous_assignee=None
                    )
            except Exception as e:
                logger.warning(f"Failed to send assignment email: {str(e)}")

        db_session.commit()

        # Reload ticket with relationships
        ticket = db_session.query(Ticket).options(
            joinedload(Ticket.requester),
            joinedload(Ticket.assigned_to),
            joinedload(Ticket.queue),
            joinedload(Ticket.customer)
        ).get(ticket.id)

        return api_created(
            format_ticket(ticket),
            f'Ticket {ticket.display_id} created successfully',
            location=f'/api/v2/tickets/{ticket.id}'
        )

    except Exception as e:
        db_session.rollback()
        logger.exception(f"Error creating ticket: {str(e)}")
        return api_error(
            ErrorCodes.INTERNAL_ERROR,
            f'Failed to create ticket: {str(e)}',
            status_code=500
        )
    finally:
        db_session.close()


# =============================================================================
# UPDATE TICKET
# =============================================================================

@api_v2_bp.route('/tickets/<int:ticket_id>', methods=['PUT'])
@dual_auth_required
@handle_exceptions
def update_ticket(ticket_id):
    """
    Update an existing ticket

    PUT /api/v2/tickets/<id>

    Request Body:
    {
        "subject": "string",
        "description": "string",
        "priority": "string",
        "queue_id": "integer",
        "customer_id": "integer",
        "asset_id": "integer",
        "shipping_address": "string",
        "shipping_tracking": "string",
        "shipping_carrier": "string",
        "country": "string",
        "notes": "string"
    }

    Returns:
        200: Updated ticket data
        400: Validation error
        403: Permission denied
        404: Ticket not found
    """
    user = request.current_api_user

    # Validate JSON body
    data, error = validate_json_body()
    if error:
        return error

    db_session = db_manager.get_session()
    try:
        # Get ticket with relationships
        ticket = db_session.query(Ticket).options(
            joinedload(Ticket.requester),
            joinedload(Ticket.assigned_to),
            joinedload(Ticket.queue),
            joinedload(Ticket.customer)
        ).get(ticket_id)

        if not ticket:
            return api_error(
                ErrorCodes.RESOURCE_NOT_FOUND,
                'Ticket not found',
                status_code=404
            )

        # Check permission
        has_permission, error_msg = check_ticket_permission(user, ticket)
        if not has_permission:
            return api_error(
                ErrorCodes.PERMISSION_DENIED,
                error_msg,
                status_code=403
            )

        # Track changes for activity log
        changes = []

        # Update fields
        if 'subject' in data and data['subject']:
            if ticket.subject != data['subject']:
                changes.append(f"subject changed from '{ticket.subject}' to '{data['subject']}'")
                ticket.subject = data['subject']

        if 'description' in data:
            ticket.description = data['description']

        if 'priority' in data:
            try:
                new_priority = TicketPriority[data['priority'].upper()]
                if ticket.priority != new_priority:
                    changes.append(f"priority changed from '{ticket.priority.value}' to '{new_priority.value}'")
                    ticket.priority = new_priority
            except (KeyError, AttributeError):
                pass

        if 'queue_id' in data:
            new_queue_id = data['queue_id']
            if new_queue_id and new_queue_id != ticket.queue_id:
                # Check permission for new queue
                if not user.can_create_in_queue(new_queue_id):
                    return api_error(
                        ErrorCodes.PERMISSION_DENIED,
                        'You do not have permission to move tickets to this queue',
                        status_code=403
                    )
                queue = db_session.query(Queue).get(new_queue_id)
                if queue:
                    old_queue_name = ticket.queue.name if ticket.queue else 'None'
                    changes.append(f"queue changed from '{old_queue_name}' to '{queue.name}'")
                    ticket.queue_id = new_queue_id

        if 'customer_id' in data:
            ticket.customer_id = data['customer_id']

        if 'asset_id' in data:
            ticket.asset_id = data['asset_id']

        if 'shipping_address' in data:
            ticket.shipping_address = data['shipping_address']

        if 'shipping_tracking' in data:
            ticket.shipping_tracking = data['shipping_tracking']

        if 'shipping_carrier' in data:
            ticket.shipping_carrier = data['shipping_carrier']

        if 'country' in data:
            ticket.country = data['country']

        if 'notes' in data:
            ticket.notes = data['notes']

        ticket.updated_at = singapore_now_as_utc()

        # Log activity if changes were made
        if changes:
            log_activity(
                db_session,
                user.id,
                'ticket_updated',
                f'Updated ticket {ticket.display_id}: {", ".join(changes)}',
                ticket.id
            )

        db_session.commit()

        # Reload with relationships
        ticket = db_session.query(Ticket).options(
            joinedload(Ticket.requester),
            joinedload(Ticket.assigned_to),
            joinedload(Ticket.queue),
            joinedload(Ticket.customer)
        ).get(ticket_id)

        return api_response(
            format_ticket(ticket),
            'Ticket updated successfully'
        )

    except Exception as e:
        db_session.rollback()
        logger.exception(f"Error updating ticket: {str(e)}")
        return api_error(
            ErrorCodes.INTERNAL_ERROR,
            f'Failed to update ticket: {str(e)}',
            status_code=500
        )
    finally:
        db_session.close()


# =============================================================================
# ASSIGN TICKET
# =============================================================================

@api_v2_bp.route('/tickets/<int:ticket_id>/assign', methods=['POST'])
@dual_auth_required
@handle_exceptions
def assign_ticket(ticket_id):
    """
    Assign a ticket to a user

    POST /api/v2/tickets/<id>/assign

    Request Body:
    {
        "assigned_to_id": "integer (required)"
    }

    Returns:
        200: Updated ticket data
        400: Validation error
        403: Permission denied
        404: Ticket or user not found
    """
    user = request.current_api_user

    # Validate JSON body
    data, error = validate_json_body()
    if error:
        return error

    # Validate required fields
    is_valid, error = validate_required_fields(data, ['assigned_to_id'])
    if not is_valid:
        return error

    new_assigned_to_id = data.get('assigned_to_id')

    db_session = db_manager.get_session()
    try:
        # Get ticket
        ticket = db_session.query(Ticket).options(
            joinedload(Ticket.requester),
            joinedload(Ticket.assigned_to),
            joinedload(Ticket.queue),
            joinedload(Ticket.customer)
        ).get(ticket_id)

        if not ticket:
            return api_error(
                ErrorCodes.RESOURCE_NOT_FOUND,
                'Ticket not found',
                status_code=404
            )

        # Check permission
        has_permission, error_msg = check_ticket_permission(user, ticket)
        if not has_permission:
            return api_error(
                ErrorCodes.PERMISSION_DENIED,
                error_msg,
                status_code=403
            )

        # Validate new assignee
        new_assignee = db_session.query(User).get(new_assigned_to_id)
        if not new_assignee:
            return api_error(
                ErrorCodes.RESOURCE_NOT_FOUND,
                'User not found',
                status_code=404
            )

        # Get previous assignee for notification
        previous_assignee = ticket.assigned_to
        old_assigned_to_id = ticket.assigned_to_id

        # Update assignment
        ticket.assigned_to_id = new_assigned_to_id
        ticket.updated_at = singapore_now_as_utc()

        # Log activity
        if old_assigned_to_id != new_assigned_to_id:
            old_name = previous_assignee.username if previous_assignee else 'Unassigned'
            log_activity(
                db_session,
                user.id,
                'ticket_assigned',
                f'Assigned ticket {ticket.display_id} from {old_name} to {new_assignee.username}',
                ticket.id
            )

            # Notify new assignee
            if new_assigned_to_id != user.id:
                create_notification(
                    db_session,
                    new_assigned_to_id,
                    'ticket_assigned',
                    f'Ticket {ticket.display_id} Assigned to You',
                    f'{user.username} assigned ticket "{ticket.subject}" to you',
                    ticket.id
                )

            # Send email notification
            try:
                from utils.email_sender import send_ticket_assignment_notification
                if new_assignee.email:
                    send_ticket_assignment_notification(
                        assigned_user=new_assignee,
                        assigner=user,
                        ticket=ticket,
                        previous_assignee=previous_assignee
                    )
            except Exception as e:
                logger.warning(f"Failed to send assignment email: {str(e)}")

        db_session.commit()

        # Reload with relationships
        ticket = db_session.query(Ticket).options(
            joinedload(Ticket.requester),
            joinedload(Ticket.assigned_to),
            joinedload(Ticket.queue),
            joinedload(Ticket.customer)
        ).get(ticket_id)

        return api_response(
            format_ticket(ticket),
            f'Ticket assigned to {new_assignee.username}'
        )

    except Exception as e:
        db_session.rollback()
        logger.exception(f"Error assigning ticket: {str(e)}")
        return api_error(
            ErrorCodes.INTERNAL_ERROR,
            f'Failed to assign ticket: {str(e)}',
            status_code=500
        )
    finally:
        db_session.close()


# =============================================================================
# CHANGE TICKET STATUS
# =============================================================================

@api_v2_bp.route('/tickets/<int:ticket_id>/status', methods=['POST'])
@dual_auth_required
@handle_exceptions
def change_ticket_status(ticket_id):
    """
    Change the status of a ticket

    POST /api/v2/tickets/<id>/status

    Request Body:
    {
        "status": "string (required) - NEW, IN_PROGRESS, PROCESSING, ON_HOLD, RESOLVED, RESOLVED_DELIVERED",
        "custom_status": "string (optional) - for custom status values"
    }

    Returns:
        200: Updated ticket data
        400: Validation error
        403: Permission denied
        404: Ticket not found
    """
    user = request.current_api_user

    # Validate JSON body
    data, error = validate_json_body()
    if error:
        return error

    # At least one of status or custom_status must be provided
    if 'status' not in data and 'custom_status' not in data:
        return api_error(
            ErrorCodes.MISSING_REQUIRED_FIELD,
            'Either status or custom_status is required',
            status_code=400
        )

    db_session = db_manager.get_session()
    try:
        # Get ticket
        ticket = db_session.query(Ticket).options(
            joinedload(Ticket.requester),
            joinedload(Ticket.assigned_to),
            joinedload(Ticket.queue),
            joinedload(Ticket.customer)
        ).get(ticket_id)

        if not ticket:
            return api_error(
                ErrorCodes.RESOURCE_NOT_FOUND,
                'Ticket not found',
                status_code=404
            )

        # Check permission
        has_permission, error_msg = check_ticket_permission(user, ticket)
        if not has_permission:
            return api_error(
                ErrorCodes.PERMISSION_DENIED,
                error_msg,
                status_code=403
            )

        old_status = ticket.status.value if ticket.status else 'None'
        old_custom_status = ticket.custom_status

        # Handle custom status
        if 'custom_status' in data:
            custom_status_value = data.get('custom_status')
            if custom_status_value:
                # Validate custom status exists
                from models.custom_ticket_status import CustomTicketStatus
                custom_status = db_session.query(CustomTicketStatus).filter_by(
                    name=custom_status_value,
                    is_active=True
                ).first()

                if custom_status:
                    ticket.custom_status = custom_status_value
                    # Don't change the system status when setting custom status
                else:
                    return api_error(
                        ErrorCodes.INVALID_FIELD_VALUE,
                        f'Invalid custom status: {custom_status_value}',
                        status_code=400
                    )
            else:
                ticket.custom_status = None

        # Handle system status
        if 'status' in data and data['status']:
            status_value = data['status']
            try:
                new_status = TicketStatus[status_value]
                ticket.status = new_status
                ticket.custom_status = None  # Clear custom status when setting system status
            except KeyError:
                try:
                    new_status = TicketStatus(status_value)
                    ticket.status = new_status
                    ticket.custom_status = None
                except ValueError:
                    return api_error(
                        ErrorCodes.INVALID_FIELD_VALUE,
                        f'Invalid status: {status_value}. Valid values: NEW, IN_PROGRESS, PROCESSING, ON_HOLD, RESOLVED, RESOLVED_DELIVERED',
                        status_code=400
                    )

        ticket.updated_at = singapore_now_as_utc()

        # Determine new status for logging
        new_status_display = ticket.custom_status or (ticket.status.value if ticket.status else 'None')
        old_status_display = old_custom_status or old_status

        # Log activity
        if new_status_display != old_status_display:
            log_activity(
                db_session,
                user.id,
                'status_changed',
                f'Changed ticket {ticket.display_id} status from "{old_status_display}" to "{new_status_display}"',
                ticket.id
            )

            # Notify ticket requester if status changed and they're not the one changing it
            if ticket.requester_id and ticket.requester_id != user.id:
                create_notification(
                    db_session,
                    ticket.requester_id,
                    'status_changed',
                    f'Ticket {ticket.display_id} Status Updated',
                    f'Status changed to "{new_status_display}" by {user.username}',
                    ticket.id
                )

            # Notify assigned user if different from requester and changer
            if ticket.assigned_to_id and ticket.assigned_to_id != user.id and ticket.assigned_to_id != ticket.requester_id:
                create_notification(
                    db_session,
                    ticket.assigned_to_id,
                    'status_changed',
                    f'Ticket {ticket.display_id} Status Updated',
                    f'Status changed to "{new_status_display}" by {user.username}',
                    ticket.id
                )

        db_session.commit()

        # Reload with relationships
        ticket = db_session.query(Ticket).options(
            joinedload(Ticket.requester),
            joinedload(Ticket.assigned_to),
            joinedload(Ticket.queue),
            joinedload(Ticket.customer)
        ).get(ticket_id)

        return api_response(
            format_ticket(ticket),
            f'Ticket status changed to {new_status_display}'
        )

    except Exception as e:
        db_session.rollback()
        logger.exception(f"Error changing ticket status: {str(e)}")
        return api_error(
            ErrorCodes.INTERNAL_ERROR,
            f'Failed to change ticket status: {str(e)}',
            status_code=500
        )
    finally:
        db_session.close()


# =============================================================================
# GET TICKET DETAILS
# =============================================================================

@api_v2_bp.route('/tickets/<int:ticket_id>', methods=['GET'])
@dual_auth_required
@handle_exceptions
def get_ticket(ticket_id):
    """
    Get comprehensive ticket details

    GET /api/v2/tickets/<id>

    Returns:
        200: Full ticket data with all relationships
        403: Permission denied
        404: Ticket not found
    """
    from models.company import Company
    from models.comment import Comment
    from models.ticket_attachment import TicketAttachment
    from models.package_item import PackageItem
    from utils.sla_calculator import get_sla_status

    user = request.current_api_user

    db_session = db_manager.get_session()
    try:
        # Load ticket with all relationships
        ticket = db_session.query(Ticket).options(
            joinedload(Ticket.requester),
            joinedload(Ticket.assigned_to),
            joinedload(Ticket.customer).joinedload(CustomerUser.company),
            joinedload(Ticket.queue),
            joinedload(Ticket.assets),
            joinedload(Ticket.accessories),
            joinedload(Ticket.attachments),
        ).get(ticket_id)

        if not ticket:
            return api_error(
                ErrorCodes.RESOURCE_NOT_FOUND,
                'Ticket not found',
                status_code=404
            )

        # Check permission
        has_permission, error_msg = check_ticket_permission(user, ticket)
        if not has_permission:
            return api_error(
                ErrorCodes.PERMISSION_DENIED,
                error_msg,
                status_code=403
            )

        # Get comments count
        comments_count = db_session.query(Comment).filter(
            Comment.ticket_id == ticket_id
        ).count()

        # Get attachments count and list
        attachments_count = len(ticket.attachments) if ticket.attachments else 0
        attachments_list = []
        for attachment in (ticket.attachments or []):
            attachments_list.append({
                'id': attachment.id,
                'filename': attachment.filename,
                'file_size': attachment.file_size,
                'file_type': attachment.file_type,
                'uploaded_at': attachment.created_at.isoformat() if attachment.created_at else None
            })

        # Get SLA status
        sla_info = get_sla_status(ticket, db=db_session)
        sla_data = None
        if sla_info.get('has_sla'):
            sla_data = {
                'status': sla_info.get('status'),
                'due_date': sla_info.get('due_date').isoformat() if sla_info.get('due_date') else None,
                'remaining_hours': sla_info.get('hours_remaining'),
                'is_breached': sla_info.get('is_breached', False)
            }

        # Format queue data
        queue_data = None
        if ticket.queue:
            queue_data = {
                'id': ticket.queue.id,
                'name': ticket.queue.name,
                'description': getattr(ticket.queue, 'description', None)
            }

        # Format assigned_to data
        assigned_to_data = None
        if ticket.assigned_to:
            assigned_to_data = {
                'id': ticket.assigned_to.id,
                'username': ticket.assigned_to.username,
                'email': ticket.assigned_to.email
            }

        # Format requester data
        requester_data = None
        if ticket.requester:
            requester_data = {
                'id': ticket.requester.id,
                'username': ticket.requester.username
            }

        # Format customer data
        customer_data = None
        if ticket.customer:
            customer_data = {
                'id': ticket.customer.id,
                'name': ticket.customer.name,
                'email': ticket.customer.email,
                'company': ticket.customer.company.name if ticket.customer.company else None
            }

        # Format company data (from customer)
        company_data = None
        if ticket.customer and ticket.customer.company:
            company_data = {
                'id': ticket.customer.company.id,
                'name': ticket.customer.company.name
            }

        # Format shipping data
        shipping_data = {
            'tracking_number': ticket.shipping_tracking,
            'carrier': ticket.shipping_carrier,
            'address': ticket.shipping_address,
            'status': ticket.shipping_status
        }

        # Format assets data
        assets_list = []
        for asset in (ticket.assets or []):
            assets_list.append({
                'id': asset.id,
                'asset_tag': asset.asset_tag,
                'serial_number': asset.serial_num,
                'model': asset.model,
                'name': asset.name,
                'status': asset.status.value if asset.status else None
            })

        # Format accessories data
        accessories_list = []
        for accessory in (ticket.accessories or []):
            accessories_list.append({
                'id': accessory.id,
                'name': accessory.name,
                'quantity': accessory.quantity,
                'category': accessory.category,
                'condition': accessory.condition
            })

        # Get packages for Asset Checkout (claw) tickets
        packages_list = []
        if ticket.category and ticket.category.name == 'ASSET_CHECKOUT_CLAW':
            packages = ticket.get_all_packages()
            for package in packages:
                package_number = package['package_number']
                package_items = ticket.get_package_items(package_number, db_session=db_session)
                packages_list.append({
                    'id': package_number,
                    'package_number': package_number,
                    'tracking_number': package['tracking_number'],
                    'carrier': package['carrier'],
                    'status': package['status'],
                    'items': package_items
                })

        # Calculate user permissions for this ticket
        permissions = _calculate_ticket_permissions(user, ticket, db_session)

        # Build response data
        ticket_data = {
            'id': ticket.id,
            'display_id': ticket.display_id,
            'subject': ticket.subject,
            'description': ticket.description,
            'status': ticket.status.value if ticket.status else None,
            'custom_status': ticket.custom_status,
            'priority': ticket.priority.value if ticket.priority else None,
            'category': ticket.category.value if ticket.category else None,
            'category_display': ticket.get_category_display_name(),
            'queue': queue_data,
            'assigned_to': assigned_to_data,
            'requester': requester_data,
            'customer': customer_data,
            'company': company_data,
            'country': ticket.country,
            'created_at': ticket.created_at.isoformat() if ticket.created_at else None,
            'updated_at': ticket.updated_at.isoformat() if ticket.updated_at else None,
            'resolved_at': None,  # Ticket model doesn't have resolved_at field

            'shipping': shipping_data,
            'assets': assets_list,
            'accessories': accessories_list,
            'packages': packages_list,
            'attachments': attachments_list,

            'comments_count': comments_count,
            'attachments_count': attachments_count,

            'sla': sla_data,
            'permissions': permissions,

            # Additional fields from ticket model
            'notes': ticket.notes,
            'return_tracking': ticket.return_tracking,
            'return_carrier': ticket.return_carrier,
            'return_tracking_status': ticket.return_tracking_status,
            'replacement_tracking': ticket.replacement_tracking,
            'replacement_status': ticket.replacement_status,
            'firstbaseorderid': ticket.firstbaseorderid
        }

        return api_response(ticket_data)

    except Exception as e:
        logger.exception(f"Error getting ticket {ticket_id}: {str(e)}")
        return api_error(
            ErrorCodes.INTERNAL_ERROR,
            f'Failed to get ticket: {str(e)}',
            status_code=500
        )
    finally:
        db_session.close()


def _calculate_ticket_permissions(user, ticket, db_session):
    """
    Calculate what actions the user can perform on this ticket.

    Args:
        user: The current user
        ticket: The ticket being accessed
        db_session: Database session

    Returns:
        dict with permission flags
    """
    from models.user_queue_permission import UserQueuePermission

    # Super admins and developers have full access
    if user.user_type in [UserType.SUPER_ADMIN, UserType.DEVELOPER]:
        return {
            'can_edit': True,
            'can_delete': True,
            'can_assign': True,
            'can_comment': True,
            'can_change_status': True,
            'can_add_attachments': True
        }

    # Default permissions
    permissions = {
        'can_edit': False,
        'can_delete': False,
        'can_assign': False,
        'can_comment': True,  # Most users can comment
        'can_change_status': False,
        'can_add_attachments': True
    }

    # Check queue permissions
    if ticket.queue_id:
        queue_permission = db_session.query(UserQueuePermission).filter_by(
            user_id=user.id,
            queue_id=ticket.queue_id
        ).first()

        if queue_permission:
            permissions['can_edit'] = queue_permission.can_edit
            permissions['can_assign'] = queue_permission.can_edit
            permissions['can_change_status'] = queue_permission.can_edit

    # COUNTRY_ADMIN and SUPERVISOR can edit tickets in their queues
    if user.user_type in [UserType.COUNTRY_ADMIN, UserType.SUPERVISOR]:
        if ticket.queue_id:
            queue_permission = db_session.query(UserQueuePermission).filter_by(
                user_id=user.id,
                queue_id=ticket.queue_id,
                can_edit=True
            ).first()
            if queue_permission:
                permissions['can_edit'] = True
                permissions['can_assign'] = True
                permissions['can_change_status'] = True

    # Requester can edit their own tickets
    if ticket.requester_id == user.id:
        permissions['can_edit'] = True
        permissions['can_change_status'] = True

    # Assigned user can edit the ticket
    if ticket.assigned_to_id == user.id:
        permissions['can_edit'] = True
        permissions['can_change_status'] = True

    return permissions


# =============================================================================
# LIST TICKET COMMENTS
# =============================================================================

@api_v2_bp.route('/tickets/<int:ticket_id>/comments', methods=['GET'])
@dual_auth_required
@handle_exceptions
def list_ticket_comments(ticket_id):
    """
    List all comments for a ticket with pagination

    GET /api/v2/tickets/<id>/comments

    Query Parameters:
        page (int): Page number (default: 1)
        per_page (int): Items per page (default: 50, max: 100)
        order (string): Sort order - "asc" for oldest first, "desc" for newest first (default: "asc")

    Returns:
        200: List of comments with pagination metadata
        403: Permission denied
        404: Ticket not found
    """
    from models.comment import Comment

    user = request.current_api_user

    # Get pagination and ordering parameters
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    order = request.args.get('order', 'asc').lower()

    # Validate parameters
    page = max(1, page)
    per_page = max(1, min(per_page, 100))
    if order not in ['asc', 'desc']:
        order = 'asc'

    db_session = db_manager.get_session()
    try:
        # Get ticket to check access
        ticket = db_session.query(Ticket).get(ticket_id)

        if not ticket:
            return api_error(
                ErrorCodes.RESOURCE_NOT_FOUND,
                'Ticket not found',
                status_code=404
            )

        # Check permission
        has_permission, error_msg = check_ticket_permission(user, ticket)
        if not has_permission:
            return api_error(
                ErrorCodes.PERMISSION_DENIED,
                error_msg,
                status_code=403
            )

        # Build query for comments
        query = db_session.query(Comment).options(
            joinedload(Comment.user)
        ).filter(Comment.ticket_id == ticket_id)

        # Apply ordering
        if order == 'desc':
            query = query.order_by(Comment.created_at.desc())
        else:
            query = query.order_by(Comment.created_at.asc())

        # Get total count for pagination
        total_items = query.count()
        total_pages = (total_items + per_page - 1) // per_page if total_items > 0 else 1

        # Apply pagination
        offset = (page - 1) * per_page
        comments = query.offset(offset).limit(per_page).all()

        # Format comments
        formatted_comments = []
        for comment in comments:
            formatted_comment = _format_comment(comment, user, db_session)
            formatted_comments.append(formatted_comment)

        # Build pagination metadata
        meta = {
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total_items': total_items,
                'total_pages': total_pages
            }
        }

        return api_response(formatted_comments, meta=meta)

    except Exception as e:
        logger.exception(f"Error listing ticket comments: {str(e)}")
        return api_error(
            ErrorCodes.INTERNAL_ERROR,
            f'Failed to list comments: {str(e)}',
            status_code=500
        )
    finally:
        db_session.close()


def _format_comment(comment, current_user, db_session):
    """
    Format a comment object for API response

    Args:
        comment: Comment model object
        current_user: The authenticated user making the request
        db_session: Database session for querying mentioned users

    Returns:
        Dictionary with formatted comment data
    """
    # Determine edit/delete permissions
    # User can edit their own comments
    # User can delete their own comments OR if they are a super admin
    is_author = comment.user_id == current_user.id
    is_super_admin = current_user.user_type in [UserType.SUPER_ADMIN, UserType.DEVELOPER]

    can_edit = is_author
    can_delete = is_author or is_super_admin

    # Check if comment has been edited
    is_edited = comment.updated_at is not None and comment.updated_at != comment.created_at

    # Get author info
    author = None
    if comment.user:
        author = {
            'id': comment.user.id,
            'username': comment.user.username,
            'avatar_url': None  # No avatar_url field in User model
        }

    # Get content and rendered HTML
    content = comment.content or ''
    content_html = comment.formatted_content if hasattr(comment, 'formatted_content') else content

    # Extract and resolve mentions to user objects
    mentions = []
    if hasattr(comment, 'mentions') and comment.mentions:
        for mention_username in comment.mentions:
            # Look up user by username
            mentioned_user = db_session.query(User).filter(
                User.username == mention_username
            ).first()
            if mentioned_user:
                mentions.append({
                    'id': mentioned_user.id,
                    'username': mentioned_user.username
                })

    # Format the comment - no attachments model exists for comments
    formatted = {
        'id': comment.id,
        'content': content,
        'content_html': content_html,
        'author': author,
        'created_at': comment.created_at.isoformat() + 'Z' if comment.created_at else None,
        'updated_at': comment.updated_at.isoformat() + 'Z' if comment.updated_at else None,
        'is_internal': False,  # Comments model doesn't have is_internal field
        'is_edited': is_edited,
        'attachments': [],  # No comment attachment model exists
        'mentions': mentions,
        'can_edit': can_edit,
        'can_delete': can_delete
    }

    return formatted


# =============================================================================
# LIST TICKET CATEGORIES
# =============================================================================

@api_v2_bp.route('/categories', methods=['GET'])
@dual_auth_required
@handle_exceptions
def list_categories():
    """
    List all ticket categories with their dynamic field configurations.

    GET /api/v2/categories

    This endpoint returns all available ticket categories, including both
    predefined categories (from the TicketCategory enum) and custom categories.
    Each category includes its field requirements and guide information.

    Returns:
        200: List of categories with field configurations
        401: Authentication required
    """
    from models.ticket_category_config import TicketCategoryConfig, CategoryDisplayConfig
    from sqlalchemy import func

    user = request.current_api_user

    db_session = db_manager.get_session()
    try:
        # Get enabled categories from display config
        enabled_display_configs = CategoryDisplayConfig.get_enabled_categories()

        # Get ticket counts per category for usage_count
        from models.ticket import Ticket, TicketCategory as TicketCategoryEnum
        category_counts = {}
        for tc in TicketCategoryEnum:
            count = db_session.query(func.count(Ticket.id)).filter(
                Ticket.category == tc
            ).scalar()
            category_counts[tc.name] = count or 0

        # Build categories list
        categories_data = []

        # Define field configurations for predefined categories
        category_field_configs = {
            'PIN_REQUEST': {
                'customer_required': False,
                'asset_required': False,
                'shipping_address_required': False,
                'show_accessories': False,
                'show_packages': False
            },
            'ASSET_REPAIR': {
                'customer_required': True,
                'asset_required': True,
                'shipping_address_required': False,
                'show_accessories': False,
                'show_packages': False,
                'show_damage_description': True,
                'show_apple_diagnostics': True
            },
            'BULK_DELIVERY_QUOTATION': {
                'customer_required': True,
                'asset_required': False,
                'shipping_address_required': True,
                'show_accessories': False,
                'show_packages': False
            },
            'REPAIR_QUOTE': {
                'customer_required': True,
                'asset_required': True,
                'shipping_address_required': False,
                'show_accessories': False,
                'show_packages': False
            },
            'ITAD_QUOTE': {
                'customer_required': True,
                'asset_required': True,
                'shipping_address_required': False,
                'show_accessories': False,
                'show_packages': False
            },
            'ASSET_CHECKOUT': {
                'customer_required': True,
                'asset_required': True,
                'shipping_address_required': True,
                'show_accessories': True,
                'show_packages': False
            },
            'ASSET_CHECKOUT_CLAW': {
                'customer_required': True,
                'asset_required': True,
                'shipping_address_required': True,
                'show_accessories': True,
                'show_packages': True
            },
            'ASSET_RETURN_CLAW': {
                'customer_required': True,
                'asset_required': False,
                'shipping_address_required': False,
                'show_accessories': True,
                'show_packages': False,
                'show_return_tracking': True
            },
            'ASSET_INTAKE': {
                'customer_required': False,
                'asset_required': False,
                'shipping_address_required': False,
                'show_accessories': False,
                'show_packages': False,
                'show_bulk_upload': True
            },
            'INTERNAL_TRANSFER': {
                'customer_required': True,
                'asset_required': True,
                'shipping_address_required': True,
                'show_accessories': False,
                'show_packages': False,
                'show_offboarding_customer': True,
                'show_onboarding_customer': True
            }
        }

        # Define guide information for categories
        category_guides = {
            'PIN_REQUEST': {
                'title': 'PIN Request',
                'description': 'Request a PIN code for device access',
                'steps': ['Submit request', 'Wait for approval', 'Receive PIN via email']
            },
            'ASSET_REPAIR': {
                'title': 'Asset Repair',
                'description': 'Submit a device for repair with damage details',
                'steps': ['Select customer', 'Select asset', 'Describe damage', 'Submit for assessment']
            },
            'BULK_DELIVERY_QUOTATION': {
                'title': 'Bulk Delivery Quotation',
                'description': 'Request a quote for bulk shipments',
                'steps': ['Select customer', 'Enter shipping address', 'Specify requirements', 'Request quote']
            },
            'REPAIR_QUOTE': {
                'title': 'Repair Quote',
                'description': 'Request a repair cost estimate',
                'steps': ['Select customer', 'Select asset', 'Describe issue', 'Request estimate']
            },
            'ITAD_QUOTE': {
                'title': 'ITAD Quote',
                'description': 'Request IT Asset Disposal quotation',
                'steps': ['Select customer', 'Select assets', 'Specify disposal requirements', 'Request quote']
            },
            'ASSET_CHECKOUT': {
                'title': 'Asset Checkout',
                'description': 'Ship a device to a customer with tracking',
                'steps': ['Select customer', 'Select asset', 'Enter shipping address', 'Add accessories if needed', 'Create shipment']
            },
            'ASSET_CHECKOUT_CLAW': {
                'title': 'Asset Checkout',
                'description': 'Ship devices to a customer with multi-package tracking support',
                'steps': ['Select customer', 'Add assets to packages', 'Enter shipping address', 'Add tracking numbers', 'Monitor delivery']
            },
            'ASSET_RETURN_CLAW': {
                'title': 'Asset Return',
                'description': 'Receive devices back from a customer',
                'steps': ['Select customer', 'Add return tracking', 'Receive and inspect items', 'Update inventory']
            },
            'ASSET_INTAKE': {
                'title': 'Asset Intake',
                'description': 'Register new batch of devices into inventory',
                'steps': ['Upload packing list', 'Upload asset CSV', 'Review assets', 'Check in devices']
            },
            'INTERNAL_TRANSFER': {
                'title': 'Internal Transfer',
                'description': 'Transfer a device between customers or locations',
                'steps': ['Select offboarding customer', 'Select onboarding customer', 'Select asset', 'Enter addresses', 'Create transfer']
            }
        }

        # Define icons and colors for categories
        category_icons = {
            'PIN_REQUEST': {'icon': 'key', 'color': '#9C27B0'},
            'ASSET_REPAIR': {'icon': 'tools', 'color': '#FF9800'},
            'BULK_DELIVERY_QUOTATION': {'icon': 'file-text', 'color': '#FFC107'},
            'REPAIR_QUOTE': {'icon': 'calculator', 'color': '#009688'},
            'ITAD_QUOTE': {'icon': 'trash-2', 'color': '#E91E63'},
            'ASSET_CHECKOUT': {'icon': 'box-arrow-up', 'color': '#4CAF50'},
            'ASSET_CHECKOUT_CLAW': {'icon': 'box-arrow-up', 'color': '#4CAF50'},
            'ASSET_RETURN_CLAW': {'icon': 'box-arrow-in-down', 'color': '#2196F3'},
            'ASSET_INTAKE': {'icon': 'upload', 'color': '#3F51B5'},
            'INTERNAL_TRANSFER': {'icon': 'arrow-left-right', 'color': '#673AB7'}
        }

        # Add predefined categories that are enabled
        for config in enabled_display_configs:
            category_key = config['key']

            # Get the enum value if it exists
            try:
                tc_enum = TicketCategoryEnum[category_key]
                category_value = tc_enum.value
            except KeyError:
                # Custom category
                category_value = config['display_name']

            # Get field configs (use defaults for custom/unknown categories)
            fields = category_field_configs.get(category_key, {
                'customer_required': True,
                'asset_required': False,
                'shipping_address_required': False,
                'show_accessories': False,
                'show_packages': False
            })

            # Get guide info
            guide = category_guides.get(category_key)

            # Get icon and color
            icon_info = category_icons.get(category_key, {'icon': 'circle', 'color': '#607D8B'})

            # For custom categories, try to get sections from TicketCategoryConfig
            if not config['is_predefined']:
                custom_config = db_session.query(TicketCategoryConfig).filter_by(
                    name=category_key
                ).first()
                if custom_config:
                    # Convert sections to field config
                    sections = custom_config.sections_list
                    fields = {
                        'customer_required': 'customer_selection' in sections,
                        'asset_required': 'tech_assets' in sections,
                        'shipping_address_required': 'shipping_tracking' in sections,
                        'show_accessories': 'received_accessories' in sections,
                        'show_packages': False,
                        'show_return_tracking': 'return_tracking' in sections,
                        'show_attachments': 'attachments' in sections,
                        'show_diagnostics': 'diagnostics' in sections,
                        'show_repair_status': 'repair_status' in sections,
                        'show_warranty_info': 'warranty_info' in sections,
                        'show_damage_assessment': 'damage_assessment' in sections,
                        'show_rma_status': 'rma_status' in sections
                    }
                    guide = {
                        'title': custom_config.display_name,
                        'description': custom_config.description or f'Custom category: {custom_config.display_name}',
                        'steps': []
                    }

            category_data = {
                'id': hash(category_key) % 10000,  # Generate a stable numeric ID
                'name': config['display_name'],
                'code': category_key,
                'description': guide['description'] if guide else f'{config["display_name"]} ticket category',
                'icon': icon_info['icon'],
                'color': icon_info['color'],
                'is_active': True,
                'is_predefined': config['is_predefined'],
                'fields': fields,
                'usage_count': category_counts.get(category_key, 0)
            }

            # Add guide if available
            if guide:
                category_data['guide'] = guide

            categories_data.append(category_data)

        return api_response(
            data=categories_data,
            message=f'Retrieved {len(categories_data)} ticket categories'
        )

    except Exception as e:
        logger.exception(f"Error listing categories: {str(e)}")
        return api_error(
            ErrorCodes.INTERNAL_ERROR,
            f'Failed to list categories: {str(e)}',
            status_code=500
        )
    finally:
        db_session.close()


# =============================================================================
# LIST TICKET PACKAGES
# =============================================================================

@api_v2_bp.route('/tickets/<int:ticket_id>/packages', methods=['GET'])
@dual_auth_required
@handle_exceptions
def list_ticket_packages(ticket_id):
    """
    List all packages for a ticket with their items and tracking history.

    GET /api/v2/tickets/<id>/packages

    This endpoint returns all packages associated with an Asset Checkout (claw)
    ticket, including the assets/accessories in each package and tracking history.

    Returns:
        200: List of packages with items and tracking history
        401: Authentication required
        403: Permission denied
        404: Ticket not found
    """
    from models.package_item import PackageItem
    from models.tracking_history import TrackingHistory
    from models.asset import Asset
    from models.accessory import Accessory
    from sqlalchemy.orm import joinedload

    user = request.current_api_user

    db_session = db_manager.get_session()
    try:
        # Get ticket
        ticket = db_session.query(Ticket).options(
            joinedload(Ticket.customer)
        ).get(ticket_id)

        if not ticket:
            return api_error(
                ErrorCodes.RESOURCE_NOT_FOUND,
                'Ticket not found',
                status_code=404
            )

        # Check permission
        has_permission, error_msg = check_ticket_permission(user, ticket)
        if not has_permission:
            return api_error(
                ErrorCodes.PERMISSION_DENIED,
                error_msg,
                status_code=403
            )

        # Check if this is an Asset Checkout (claw) ticket that supports packages
        is_claw_ticket = ticket.category and ticket.category.name in ['ASSET_CHECKOUT_CLAW', 'ASSET_RETURN_CLAW']

        if not is_claw_ticket:
            # Return empty list for non-package tickets
            return api_response(
                data=[],
                message='This ticket type does not support packages',
                meta={'total_packages': 0}
            )

        # Get all packages from the ticket
        packages_raw = ticket.get_all_packages()

        packages_data = []
        for package in packages_raw:
            package_number = package['package_number']
            tracking_number = package['tracking_number']
            carrier = package['carrier']
            status = package['status']

            # Get package items
            package_items = db_session.query(PackageItem).options(
                joinedload(PackageItem.asset),
                joinedload(PackageItem.accessory)
            ).filter_by(
                ticket_id=ticket_id,
                package_number=package_number
            ).order_by(PackageItem.created_at.asc()).all()

            # Format items
            items_data = []
            for item in package_items:
                item_data = {
                    'id': item.id,
                    'type': 'asset' if item.asset_id else 'accessory',
                    'quantity': item.quantity,
                    'notes': item.notes
                }

                if item.asset:
                    item_data['asset'] = {
                        'id': item.asset.id,
                        'asset_tag': item.asset.asset_tag,
                        'serial_number': item.asset.serial_num,
                        'model': item.asset.model,
                        'name': item.asset.name,
                        'status': item.asset.status.value if item.asset.status else None
                    }
                elif item.accessory:
                    item_data['accessory'] = {
                        'id': item.accessory.id,
                        'name': item.accessory.name,
                        'category': item.accessory.category,
                        'quantity': item.quantity
                    }

                items_data.append(item_data)

            # Get tracking history
            tracking_history_data = []
            if tracking_number:
                # Check if tracking history exists in database
                tracking_history = db_session.query(TrackingHistory).filter_by(
                    ticket_id=ticket_id,
                    tracking_number=tracking_number
                ).first()

                if tracking_history and tracking_history.events:
                    for event in tracking_history.events:
                        tracking_history_data.append({
                            'status': event.get('status') or event.get('description', ''),
                            'location': event.get('location', ''),
                            'timestamp': event.get('timestamp') or event.get('date', '')
                        })

            # Determine shipped_at and delivered_at from tracking history or status
            shipped_at = None
            delivered_at = None

            if tracking_history_data:
                # Find shipped event (first event usually)
                for event in tracking_history_data:
                    event_status_lower = event.get('status', '').lower()
                    if 'shipped' in event_status_lower or 'picked up' in event_status_lower or 'dispatched' in event_status_lower:
                        shipped_at = event.get('timestamp')
                        break

                # Find delivered event
                for event in tracking_history_data:
                    event_status_lower = event.get('status', '').lower()
                    if 'delivered' in event_status_lower:
                        delivered_at = event.get('timestamp')
                        break

            package_data = {
                'id': package_number,
                'package_number': package_number,
                'tracking_number': tracking_number,
                'carrier': carrier,
                'status': status,
                'shipped_at': shipped_at,
                'delivered_at': delivered_at,
                'items': items_data,
                'item_count': len(items_data),
                'tracking_history': tracking_history_data
            }

            packages_data.append(package_data)

        return api_response(
            data=packages_data,
            message=f'Retrieved {len(packages_data)} packages for ticket {ticket.display_id}',
            meta={'total_packages': len(packages_data)}
        )

    except Exception as e:
        logger.exception(f"Error listing ticket packages: {str(e)}")
        return api_error(
            ErrorCodes.INTERNAL_ERROR,
            f'Failed to list ticket packages: {str(e)}',
            status_code=500
        )
    finally:
        db_session.close()


# =============================================================================
# LIST TICKET PRIORITIES
# =============================================================================

@api_v2_bp.route('/priorities', methods=['GET'])
@dual_auth_required
@handle_exceptions
def list_priorities():
    """
    List all ticket priority options.

    GET /api/v2/priorities

    Returns all available priority levels with their metadata including
    color coding, icons, SLA hours, and descriptions.

    Returns:
        200: List of priorities with metadata
        401: Authentication required
    """
    # Define priority metadata
    # Maps TicketPriority enum values to extended metadata
    priority_metadata = {
        'LOW': {
            'id': 1,
            'name': 'Low',
            'code': 'LOW',
            'color': '#4CAF50',
            'icon': 'arrow-down',
            'sla_hours': 72,
            'description': 'Non-urgent issues',
            'sort_order': 1
        },
        'MEDIUM': {
            'id': 2,
            'name': 'Medium',
            'code': 'MEDIUM',
            'color': '#FF9800',
            'icon': 'dash',
            'sla_hours': 48,
            'description': 'Standard priority',
            'sort_order': 2
        },
        'HIGH': {
            'id': 3,
            'name': 'High',
            'code': 'HIGH',
            'color': '#F44336',
            'icon': 'arrow-up',
            'sla_hours': 24,
            'description': 'Urgent issues',
            'sort_order': 3
        },
        'CRITICAL': {
            'id': 4,
            'name': 'Critical',
            'code': 'CRITICAL',
            'color': '#9C27B0',
            'icon': 'exclamation-triangle',
            'sla_hours': 4,
            'description': 'Emergency issues requiring immediate attention',
            'sort_order': 4
        }
    }

    # Build priorities list from enum, ensuring we only include valid priorities
    priorities_data = []
    for priority in TicketPriority:
        if priority.name in priority_metadata:
            priorities_data.append(priority_metadata[priority.name])

    # Sort by sort_order
    priorities_data.sort(key=lambda x: x['sort_order'])

    return api_response(
        data=priorities_data,
        message=f'Retrieved {len(priorities_data)} priority options'
    )


# =============================================================================
# BULK SEARCH TICKETS
# =============================================================================

@api_v2_bp.route('/tickets/bulk-search', methods=['POST'])
@dual_auth_required
@handle_exceptions
def bulk_search_tickets():
    """
    Search for multiple values at once across tickets.

    POST /api/v2/tickets/bulk-search

    Searches for serial numbers, tracking numbers, and asset tags across
    tickets and their associated assets. Respects user's ticket access permissions.

    Request Body:
    {
        "values": ["ABC123", "XYZ789", "1Z999AA1"],
        "search_fields": ["serial_number", "tracking_number", "asset_tag"]
    }

    search_fields options:
        - serial_number: Search in asset serial numbers
        - tracking_number: Search in shipping/return/replacement tracking numbers
        - asset_tag: Search in asset tags

    Returns:
        200: Search results with found matches and not found values
        400: Validation error (missing values, too many values)
        401: Authentication required
    """
    from models.user_queue_permission import UserQueuePermission

    user = request.current_api_user

    # Validate JSON body
    data, error = validate_json_body()
    if error:
        return error

    # Validate required fields
    is_valid, error = validate_required_fields(data, ['values'])
    if not is_valid:
        return error

    values = data.get('values', [])
    search_fields = data.get('search_fields', ['serial_number', 'tracking_number', 'asset_tag'])

    # Validate values is a list
    if not isinstance(values, list):
        return api_error(
            ErrorCodes.INVALID_FIELD_VALUE,
            'values must be an array of strings',
            status_code=400
        )

    # Validate values count (max 100)
    if len(values) > 100:
        return api_error(
            ErrorCodes.INVALID_FIELD_VALUE,
            'Maximum 100 values allowed per request',
            status_code=400
        )

    # Validate values are non-empty strings
    values = [str(v).strip() for v in values if v and str(v).strip()]
    if not values:
        return api_error(
            ErrorCodes.INVALID_FIELD_VALUE,
            'At least one non-empty value is required',
            status_code=400
        )

    # Validate search_fields
    valid_search_fields = ['serial_number', 'tracking_number', 'asset_tag']
    if not isinstance(search_fields, list):
        search_fields = valid_search_fields
    else:
        search_fields = [f for f in search_fields if f in valid_search_fields]
        if not search_fields:
            search_fields = valid_search_fields

    db_session = db_manager.get_session()
    try:
        found_results = []
        found_values = set()

        # Build base query with permission filtering
        def get_permitted_ticket_query():
            """Get base query filtered by user permissions"""
            query = db_session.query(Ticket).options(
                selectinload(Ticket.assets),
                selectinload(Ticket.queue)
            )

            # Apply permission filtering based on user type
            if user.user_type in [UserType.SUPER_ADMIN, UserType.DEVELOPER]:
                # Super admins and developers can see all tickets
                pass
            elif user.user_type in [UserType.COUNTRY_ADMIN, UserType.SUPERVISOR]:
                # Filter by accessible queues
                accessible_queue_ids = user.get_accessible_queue_ids(db_session)
                if accessible_queue_ids is not None:
                    query = query.filter(Ticket.queue_id.in_(accessible_queue_ids))
            elif user.user_type == UserType.CLIENT:
                # Clients can only see tickets for their company or tickets they created
                if user.company_id:
                    from models.customer_user import CustomerUser
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
                    query = query.filter(
                        or_(
                            Ticket.requester_id == user.id,
                            Ticket.assigned_to_id == user.id
                        )
                    )
            else:
                # Regular users can only see their own tickets
                query = query.filter(
                    or_(
                        Ticket.requester_id == user.id,
                        Ticket.assigned_to_id == user.id
                    )
                )

            return query

        # Search for each value
        for search_value in values:
            search_value_lower = search_value.lower()

            # Search in tracking numbers
            if 'tracking_number' in search_fields:
                tracking_query = get_permitted_ticket_query().filter(
                    or_(
                        func.lower(Ticket.shipping_tracking) == search_value_lower,
                        func.lower(Ticket.return_tracking) == search_value_lower,
                        func.lower(Ticket.replacement_tracking) == search_value_lower,
                        func.lower(Ticket.shipping_tracking_2) == search_value_lower,
                        func.lower(Ticket.shipping_tracking_3) == search_value_lower,
                        func.lower(Ticket.shipping_tracking_4) == search_value_lower,
                        func.lower(Ticket.shipping_tracking_5) == search_value_lower
                    )
                )

                for ticket in tracking_query.all():
                    if search_value not in found_values:
                        found_results.append({
                            'search_value': search_value,
                            'match_type': 'tracking_number',
                            'ticket': {
                                'id': ticket.id,
                                'display_id': ticket.display_id,
                                'subject': ticket.subject,
                                'status': ticket.status.value if ticket.status else None
                            }
                        })
                        found_values.add(search_value)

            # Search in asset serial numbers and asset tags
            if 'serial_number' in search_fields or 'asset_tag' in search_fields:
                # First find assets matching the search value
                asset_conditions = []
                if 'serial_number' in search_fields:
                    asset_conditions.append(func.lower(Asset.serial_num) == search_value_lower)
                if 'asset_tag' in search_fields:
                    asset_conditions.append(func.lower(Asset.asset_tag) == search_value_lower)

                if asset_conditions:
                    matching_assets = db_session.query(Asset).filter(
                        or_(*asset_conditions)
                    ).all()

                    for asset in matching_assets:
                        # Find tickets associated with this asset
                        ticket_query = get_permitted_ticket_query().filter(
                            Ticket.assets.contains(asset)
                        )

                        for ticket in ticket_query.all():
                            if search_value not in found_values:
                                # Determine match type
                                match_type = 'serial_number'
                                if asset.asset_tag and asset.asset_tag.lower() == search_value_lower:
                                    match_type = 'asset_tag'
                                elif asset.serial_num and asset.serial_num.lower() == search_value_lower:
                                    match_type = 'serial_number'

                                found_results.append({
                                    'search_value': search_value,
                                    'match_type': match_type,
                                    'ticket': {
                                        'id': ticket.id,
                                        'display_id': ticket.display_id,
                                        'subject': ticket.subject,
                                        'status': ticket.status.value if ticket.status else None
                                    }
                                })
                                found_values.add(search_value)

        # Determine not found values
        not_found = [v for v in values if v not in found_values]

        # Build response
        response_data = {
            'found': found_results,
            'not_found': not_found
        }

        meta = {
            'total_searched': len(values),
            'total_found': len(found_results),
            'total_not_found': len(not_found)
        }

        return api_response(
            data=response_data,
            meta=meta
        )

    except Exception as e:
        logger.exception(f"Error in bulk search: {str(e)}")
        return api_error(
            ErrorCodes.INTERNAL_ERROR,
            f'Failed to perform bulk search: {str(e)}',
            status_code=500
        )
    finally:
        db_session.close()
