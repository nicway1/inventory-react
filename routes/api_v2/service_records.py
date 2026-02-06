"""
API v2 Service Records Endpoints

Provides service record management endpoints for tickets:
- GET /api/v2/tickets/<id>/service-records - List service records
- POST /api/v2/tickets/<id>/service-records - Create service record
- PUT /api/v2/tickets/<id>/service-records/<record_id> - Update service record
- DELETE /api/v2/tickets/<id>/service-records/<record_id> - Delete service record
"""

from flask import request
from datetime import datetime
from sqlalchemy.orm import joinedload
import logging

from . import api_v2_bp
from .utils import (
    api_response,
    api_error,
    api_created,
    api_no_content,
    ErrorCodes,
    handle_exceptions,
    validate_json_body,
    validate_required_fields,
    dual_auth_required,
    get_pagination_params,
)

from utils.db_manager import DatabaseManager
from utils.timezone_utils import singapore_now_as_utc
from models.ticket import Ticket
from models.service_record import ServiceRecord
from models.user import User, UserType
from models.asset import Asset
from models.activity import Activity
from models.notification import Notification

logger = logging.getLogger(__name__)
db_manager = DatabaseManager()


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


def format_service_record(record):
    """Format a service record for API response"""
    return {
        'id': record.id,
        'request_id': record.request_id,
        'ticket_id': record.ticket_id,
        'asset_id': record.asset_id,
        'asset_tag': record.asset.asset_tag if record.asset else None,
        'service_type': record.service_type,
        'description': record.description,
        'status': record.status,
        'requested_by_id': record.requested_by_id,
        'requested_by_name': record.requested_by.username if record.requested_by else None,
        'assigned_to_id': record.assigned_to_id,
        'assigned_to_name': record.assigned_to.username if record.assigned_to else None,
        'completed_by_id': record.completed_by_id,
        'completed_by_name': record.completed_by.username if record.completed_by else None,
        'completed_at': record.completed_at.isoformat() if record.completed_at else None,
        'created_at': record.created_at.isoformat() if record.created_at else None,
    }


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


# =============================================================================
# LIST SERVICE RECORDS
# =============================================================================

@api_v2_bp.route('/tickets/<int:ticket_id>/service-records', methods=['GET'])
@dual_auth_required
@handle_exceptions
def list_service_records(ticket_id):
    """
    List service records for a ticket

    GET /api/v2/tickets/<id>/service-records

    Query Parameters:
        page: Page number (default 1)
        per_page: Items per page (default 20, max 100)
        status: Filter by status (Requested, In Progress, Completed)

    Returns:
        200: List of service records with pagination
        403: Permission denied
        404: Ticket not found
    """
    user = request.current_api_user

    db_session = db_manager.get_session()
    try:
        # Get ticket
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

        # Build query
        query = db_session.query(ServiceRecord).filter(
            ServiceRecord.ticket_id == ticket_id
        ).options(
            joinedload(ServiceRecord.asset),
            joinedload(ServiceRecord.requested_by),
            joinedload(ServiceRecord.assigned_to),
            joinedload(ServiceRecord.completed_by)
        )

        # Filter by status
        status_filter = request.args.get('status')
        if status_filter:
            query = query.filter(ServiceRecord.status == status_filter)

        # Order by creation date descending
        query = query.order_by(ServiceRecord.created_at.desc())

        # Pagination
        page, per_page = get_pagination_params()
        total = query.count()
        offset = (page - 1) * per_page
        records = query.offset(offset).limit(per_page).all()

        total_pages = (total + per_page - 1) // per_page if total > 0 else 0

        return api_response(
            [format_service_record(r) for r in records],
            meta={
                'pagination': {
                    'page': page,
                    'per_page': per_page,
                    'total_items': total,
                    'total_pages': total_pages,
                    'has_next': page < total_pages,
                    'has_prev': page > 1
                }
            }
        )

    except Exception as e:
        logger.exception(f"Error listing service records: {str(e)}")
        return api_error(
            ErrorCodes.INTERNAL_ERROR,
            f'Failed to list service records: {str(e)}',
            status_code=500
        )
    finally:
        db_session.close()


# =============================================================================
# CREATE SERVICE RECORD
# =============================================================================

@api_v2_bp.route('/tickets/<int:ticket_id>/service-records', methods=['POST'])
@dual_auth_required
@handle_exceptions
def create_service_record(ticket_id):
    """
    Create a new service record for a ticket

    POST /api/v2/tickets/<id>/service-records

    Request Body:
    {
        "service_type": "string (required) - e.g., OS Reinstall, Hardware Repair",
        "description": "string",
        "asset_id": "integer (optional - asset to service)",
        "assigned_to_id": "integer (optional - user to assign the work to)"
    }

    Valid service_type values:
        OS Reinstall, Hardware Repair, Screen Replacement, Battery Replacement,
        Keyboard Replacement, Data Backup, Data Wipe, Software Installation,
        Firmware Update, Diagnostic Test, Cleaning, Other

    Returns:
        201: Created service record
        400: Validation error
        403: Permission denied
        404: Ticket or asset not found
    """
    user = request.current_api_user

    # Validate JSON body
    data, error = validate_json_body()
    if error:
        return error

    # Validate required fields
    is_valid, error = validate_required_fields(data, ['service_type'])
    if not is_valid:
        return error

    service_type = data.get('service_type')

    # Validate service type
    valid_service_types = ServiceRecord.SERVICE_TYPES
    if service_type not in valid_service_types:
        return api_error(
            ErrorCodes.INVALID_FIELD_VALUE,
            f'Invalid service_type. Valid values: {", ".join(valid_service_types)}',
            status_code=400
        )

    db_session = db_manager.get_session()
    try:
        # Get ticket
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

        # Validate asset if provided
        asset_id = data.get('asset_id')
        if asset_id:
            asset = db_session.query(Asset).get(asset_id)
            if not asset:
                return api_error(
                    ErrorCodes.RESOURCE_NOT_FOUND,
                    'Asset not found',
                    status_code=404
                )

        # Validate assigned_to if provided
        assigned_to_id = data.get('assigned_to_id')
        assigned_to = None
        if assigned_to_id:
            assigned_to = db_session.query(User).get(assigned_to_id)
            if not assigned_to:
                return api_error(
                    ErrorCodes.RESOURCE_NOT_FOUND,
                    'Assigned user not found',
                    status_code=404
                )

        # Create service record
        record = ServiceRecord(
            ticket_id=ticket_id,
            asset_id=asset_id,
            service_type=service_type,
            description=data.get('description'),
            status='Requested',
            requested_by_id=user.id,
            assigned_to_id=assigned_to_id,
            created_at=singapore_now_as_utc()
        )

        db_session.add(record)
        db_session.flush()  # Get record ID

        # Log activity
        log_activity(
            db_session,
            user.id,
            'service_record_created',
            f'Created service record {record.request_id}: {service_type} for ticket {ticket.display_id}',
            ticket_id
        )

        # Notify assigned user if different from requester
        if assigned_to_id and assigned_to_id != user.id:
            create_notification(
                db_session,
                assigned_to_id,
                'service_request',
                f'Service Request: {service_type}',
                f'{user.username} assigned you a service request on ticket {ticket.display_id}',
                ticket_id
            )

        db_session.commit()

        # Reload with relationships
        record = db_session.query(ServiceRecord).options(
            joinedload(ServiceRecord.asset),
            joinedload(ServiceRecord.requested_by),
            joinedload(ServiceRecord.assigned_to),
            joinedload(ServiceRecord.completed_by)
        ).get(record.id)

        return api_created(
            format_service_record(record),
            f'Service record {record.request_id} created successfully',
            location=f'/api/v2/tickets/{ticket_id}/service-records/{record.id}'
        )

    except Exception as e:
        db_session.rollback()
        logger.exception(f"Error creating service record: {str(e)}")
        return api_error(
            ErrorCodes.INTERNAL_ERROR,
            f'Failed to create service record: {str(e)}',
            status_code=500
        )
    finally:
        db_session.close()


# =============================================================================
# UPDATE SERVICE RECORD
# =============================================================================

@api_v2_bp.route('/tickets/<int:ticket_id>/service-records/<int:record_id>', methods=['PUT'])
@dual_auth_required
@handle_exceptions
def update_service_record(ticket_id, record_id):
    """
    Update a service record

    PUT /api/v2/tickets/<id>/service-records/<record_id>

    Request Body:
    {
        "service_type": "string",
        "description": "string",
        "status": "string (Requested, In Progress, Completed)",
        "asset_id": "integer",
        "assigned_to_id": "integer"
    }

    Returns:
        200: Updated service record
        400: Validation error
        403: Permission denied
        404: Ticket, record, or asset not found
    """
    user = request.current_api_user

    # Validate JSON body
    data, error = validate_json_body()
    if error:
        return error

    db_session = db_manager.get_session()
    try:
        # Get ticket
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

        # Get service record
        record = db_session.query(ServiceRecord).filter(
            ServiceRecord.id == record_id,
            ServiceRecord.ticket_id == ticket_id
        ).first()

        if not record:
            return api_error(
                ErrorCodes.RESOURCE_NOT_FOUND,
                'Service record not found',
                status_code=404
            )

        # Track changes
        changes = []
        old_status = record.status

        # Update service type
        if 'service_type' in data:
            service_type = data['service_type']
            if service_type and service_type in ServiceRecord.SERVICE_TYPES:
                if record.service_type != service_type:
                    changes.append(f"service_type changed from '{record.service_type}' to '{service_type}'")
                    record.service_type = service_type
            elif service_type:
                return api_error(
                    ErrorCodes.INVALID_FIELD_VALUE,
                    f'Invalid service_type. Valid values: {", ".join(ServiceRecord.SERVICE_TYPES)}',
                    status_code=400
                )

        # Update description
        if 'description' in data:
            record.description = data['description']

        # Update asset
        if 'asset_id' in data:
            asset_id = data['asset_id']
            if asset_id:
                asset = db_session.query(Asset).get(asset_id)
                if not asset:
                    return api_error(
                        ErrorCodes.RESOURCE_NOT_FOUND,
                        'Asset not found',
                        status_code=404
                    )
            record.asset_id = asset_id

        # Update assigned user
        if 'assigned_to_id' in data:
            assigned_to_id = data['assigned_to_id']
            old_assigned_to_id = record.assigned_to_id

            if assigned_to_id:
                assigned_to = db_session.query(User).get(assigned_to_id)
                if not assigned_to:
                    return api_error(
                        ErrorCodes.RESOURCE_NOT_FOUND,
                        'Assigned user not found',
                        status_code=404
                    )
                record.assigned_to_id = assigned_to_id

                # Notify new assignee if changed
                if assigned_to_id != old_assigned_to_id and assigned_to_id != user.id:
                    create_notification(
                        db_session,
                        assigned_to_id,
                        'service_request',
                        f'Service Request Assigned: {record.service_type}',
                        f'{user.username} assigned you a service request on ticket {ticket.display_id}',
                        ticket_id
                    )
            else:
                record.assigned_to_id = None

        # Update status
        if 'status' in data:
            status = data['status']
            if status in ServiceRecord.STATUS_OPTIONS:
                if record.status != status:
                    changes.append(f"status changed from '{record.status}' to '{status}'")
                    record.status = status

                    # Handle completion
                    if status == 'Completed' and old_status != 'Completed':
                        record.completed_by_id = user.id
                        record.completed_at = singapore_now_as_utc()

                        # Notify requester if different from completer
                        if record.requested_by_id and record.requested_by_id != user.id:
                            create_notification(
                                db_session,
                                record.requested_by_id,
                                'service_completed',
                                f'Service Completed: {record.service_type}',
                                f'{user.username} completed the service request on ticket {ticket.display_id}',
                                ticket_id
                            )
                    elif status != 'Completed':
                        # Clear completion info if status changed from Completed
                        if old_status == 'Completed':
                            record.completed_by_id = None
                            record.completed_at = None
            else:
                return api_error(
                    ErrorCodes.INVALID_FIELD_VALUE,
                    f'Invalid status. Valid values: {", ".join(ServiceRecord.STATUS_OPTIONS)}',
                    status_code=400
                )

        # Log activity if changes were made
        if changes:
            log_activity(
                db_session,
                user.id,
                'service_record_updated',
                f'Updated service record {record.request_id}: {", ".join(changes)}',
                ticket_id
            )

        db_session.commit()

        # Reload with relationships
        record = db_session.query(ServiceRecord).options(
            joinedload(ServiceRecord.asset),
            joinedload(ServiceRecord.requested_by),
            joinedload(ServiceRecord.assigned_to),
            joinedload(ServiceRecord.completed_by)
        ).get(record_id)

        return api_response(
            format_service_record(record),
            'Service record updated successfully'
        )

    except Exception as e:
        db_session.rollback()
        logger.exception(f"Error updating service record: {str(e)}")
        return api_error(
            ErrorCodes.INTERNAL_ERROR,
            f'Failed to update service record: {str(e)}',
            status_code=500
        )
    finally:
        db_session.close()


# =============================================================================
# DELETE SERVICE RECORD
# =============================================================================

@api_v2_bp.route('/tickets/<int:ticket_id>/service-records/<int:record_id>', methods=['DELETE'])
@dual_auth_required
@handle_exceptions
def delete_service_record(ticket_id, record_id):
    """
    Delete a service record

    DELETE /api/v2/tickets/<id>/service-records/<record_id>

    Returns:
        204: No content (success)
        403: Permission denied
        404: Ticket or record not found
    """
    user = request.current_api_user

    db_session = db_manager.get_session()
    try:
        # Get ticket
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

        # Get service record
        record = db_session.query(ServiceRecord).filter(
            ServiceRecord.id == record_id,
            ServiceRecord.ticket_id == ticket_id
        ).first()

        if not record:
            return api_error(
                ErrorCodes.RESOURCE_NOT_FOUND,
                'Service record not found',
                status_code=404
            )

        request_id = record.request_id
        service_type = record.service_type

        # Log activity before deletion
        log_activity(
            db_session,
            user.id,
            'service_record_deleted',
            f'Deleted service record {request_id}: {service_type} from ticket {ticket.display_id}',
            ticket_id
        )

        # Delete the record
        db_session.delete(record)
        db_session.commit()

        return api_no_content()

    except Exception as e:
        db_session.rollback()
        logger.exception(f"Error deleting service record: {str(e)}")
        return api_error(
            ErrorCodes.INTERNAL_ERROR,
            f'Failed to delete service record: {str(e)}',
            status_code=500
        )
    finally:
        db_session.close()
