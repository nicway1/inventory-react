"""
API v2 Notification Endpoints

Provides notification management endpoints for the React frontend:
- GET /api/v2/notifications - List notifications with pagination and filtering
- GET /api/v2/notifications/unread-count - Get unread notification count
- PUT /api/v2/notifications/:id/read - Mark single notification as read
- PUT /api/v2/notifications/read-all - Mark all notifications as read
- DELETE /api/v2/notifications/:id - Delete a notification
- DELETE /api/v2/notifications/bulk - Bulk delete notifications
"""

from flask import request
from datetime import datetime
from sqlalchemy import or_, and_
import logging

from . import api_v2_bp
from .utils import (
    api_response,
    api_error,
    api_no_content,
    ErrorCodes,
    handle_exceptions,
    dual_auth_required,
    get_pagination_params,
    paginate_query,
    get_sorting_params,
    apply_sorting,
    get_filter_param,
    get_search_term,
    serialize_datetime,
    validate_json_body,
)

from utils.db_manager import DatabaseManager
from models.notification import Notification
from models.user import User

logger = logging.getLogger(__name__)
db_manager = DatabaseManager()


def format_notification(notification):
    """Format a notification object for API response"""
    return {
        'id': notification.id,
        'type': notification.type,
        'title': notification.title,
        'message': notification.message,
        'is_read': notification.is_read,
        'reference_type': notification.reference_type,
        'reference_id': notification.reference_id,
        'created_at': serialize_datetime(notification.created_at),
        'read_at': serialize_datetime(notification.read_at),
    }


# =============================================================================
# LIST NOTIFICATIONS
# =============================================================================

@api_v2_bp.route('/notifications', methods=['GET'])
@dual_auth_required
@handle_exceptions
def list_notifications():
    """
    List user notifications with pagination and filtering

    GET /api/v2/notifications

    Query Parameters:
        - page: Page number (default: 1)
        - per_page: Items per page (default: 20, max: 100)
        - sort: Sort field (default: 'created_at')
        - order: Sort order ('asc' or 'desc', default: 'desc')
        - type: Filter by notification type ('mention', 'ticket_update', 'asset', 'system')
        - is_read: Filter by read status (true/false)
        - search: Search in title and message

    Returns:
        List of notifications with pagination metadata
    """
    user = request.current_api_user
    db_session = db_manager.get_session()

    try:
        # Build base query for current user's notifications
        query = db_session.query(Notification).filter(
            Notification.user_id == user.id
        )

        # Apply type filter
        notification_type = get_filter_param('type')
        if notification_type:
            query = query.filter(Notification.type == notification_type)

        # Apply read status filter
        is_read = get_filter_param('is_read')
        if is_read is not None:
            is_read_bool = is_read.lower() in ('true', '1', 'yes')
            query = query.filter(Notification.is_read == is_read_bool)

        # Apply search filter
        search_term = get_search_term()
        if search_term:
            search_pattern = f'%{search_term}%'
            query = query.filter(
                or_(
                    Notification.title.ilike(search_pattern),
                    Notification.message.ilike(search_pattern)
                )
            )

        # Apply sorting
        allowed_sort_fields = ['created_at', 'type', 'is_read', 'title']
        sort_field, sort_order = get_sorting_params(
            allowed_sort_fields,
            default_sort='created_at',
            default_order='desc'
        )
        query = apply_sorting(query, Notification, sort_field, sort_order)

        # Get pagination params and paginate
        page, per_page = get_pagination_params()
        notifications, pagination_meta = paginate_query(query, page, per_page)

        # Format response
        data = [format_notification(n) for n in notifications]

        # Add unread count to meta
        unread_count = db_session.query(Notification).filter(
            Notification.user_id == user.id,
            Notification.is_read == False
        ).count()

        pagination_meta['unread_count'] = unread_count

        return api_response(data=data, meta=pagination_meta)

    finally:
        db_session.close()


# =============================================================================
# GET UNREAD COUNT
# =============================================================================

@api_v2_bp.route('/notifications/unread-count', methods=['GET'])
@dual_auth_required
@handle_exceptions
def get_unread_count():
    """
    Get count of unread notifications for current user

    GET /api/v2/notifications/unread-count

    Returns:
        {
            "success": true,
            "data": {
                "unread_count": 5
            }
        }
    """
    user = request.current_api_user
    db_session = db_manager.get_session()

    try:
        count = db_session.query(Notification).filter(
            Notification.user_id == user.id,
            Notification.is_read == False
        ).count()

        return api_response(data={'unread_count': count})

    finally:
        db_session.close()


# =============================================================================
# MARK NOTIFICATION AS READ
# =============================================================================

@api_v2_bp.route('/notifications/<int:notification_id>/read', methods=['PUT'])
@dual_auth_required
@handle_exceptions
def mark_notification_read(notification_id):
    """
    Mark a single notification as read

    PUT /api/v2/notifications/:id/read

    Returns:
        Updated notification object
    """
    user = request.current_api_user
    db_session = db_manager.get_session()

    try:
        notification = db_session.query(Notification).filter(
            Notification.id == notification_id,
            Notification.user_id == user.id
        ).first()

        if not notification:
            return api_error(
                ErrorCodes.RESOURCE_NOT_FOUND,
                f'Notification with ID {notification_id} not found',
                status_code=404
            )

        notification.is_read = True
        notification.read_at = datetime.utcnow()
        db_session.commit()

        return api_response(
            data=format_notification(notification),
            message='Notification marked as read'
        )

    finally:
        db_session.close()


# =============================================================================
# MARK NOTIFICATION AS UNREAD
# =============================================================================

@api_v2_bp.route('/notifications/<int:notification_id>/unread', methods=['PUT'])
@dual_auth_required
@handle_exceptions
def mark_notification_unread(notification_id):
    """
    Mark a single notification as unread

    PUT /api/v2/notifications/:id/unread

    Returns:
        Updated notification object
    """
    user = request.current_api_user
    db_session = db_manager.get_session()

    try:
        notification = db_session.query(Notification).filter(
            Notification.id == notification_id,
            Notification.user_id == user.id
        ).first()

        if not notification:
            return api_error(
                ErrorCodes.RESOURCE_NOT_FOUND,
                f'Notification with ID {notification_id} not found',
                status_code=404
            )

        notification.is_read = False
        notification.read_at = None
        db_session.commit()

        return api_response(
            data=format_notification(notification),
            message='Notification marked as unread'
        )

    finally:
        db_session.close()


# =============================================================================
# MARK ALL AS READ
# =============================================================================

@api_v2_bp.route('/notifications/read-all', methods=['PUT'])
@dual_auth_required
@handle_exceptions
def mark_all_notifications_read():
    """
    Mark all notifications as read for current user

    PUT /api/v2/notifications/read-all

    Optional body:
        {
            "type": "mention"  // Optional: only mark specific type as read
        }

    Returns:
        {
            "success": true,
            "data": {
                "updated_count": 5
            },
            "message": "All notifications marked as read"
        }
    """
    user = request.current_api_user
    db_session = db_manager.get_session()

    try:
        # Build query for unread notifications
        query = db_session.query(Notification).filter(
            Notification.user_id == user.id,
            Notification.is_read == False
        )

        # Optionally filter by type
        data = request.get_json(silent=True) or {}
        notification_type = data.get('type')
        if notification_type:
            query = query.filter(Notification.type == notification_type)

        # Update all matching notifications
        updated_count = query.update({
            'is_read': True,
            'read_at': datetime.utcnow()
        }, synchronize_session='fetch')

        db_session.commit()

        return api_response(
            data={'updated_count': updated_count},
            message='All notifications marked as read'
        )

    finally:
        db_session.close()


# =============================================================================
# DELETE NOTIFICATION
# =============================================================================

@api_v2_bp.route('/notifications/<int:notification_id>', methods=['DELETE'])
@dual_auth_required
@handle_exceptions
def delete_notification(notification_id):
    """
    Delete a single notification

    DELETE /api/v2/notifications/:id

    Returns:
        204 No Content on success
    """
    user = request.current_api_user
    db_session = db_manager.get_session()

    try:
        notification = db_session.query(Notification).filter(
            Notification.id == notification_id,
            Notification.user_id == user.id
        ).first()

        if not notification:
            return api_error(
                ErrorCodes.RESOURCE_NOT_FOUND,
                f'Notification with ID {notification_id} not found',
                status_code=404
            )

        db_session.delete(notification)
        db_session.commit()

        return api_no_content()

    finally:
        db_session.close()


# =============================================================================
# BULK DELETE NOTIFICATIONS
# =============================================================================

@api_v2_bp.route('/notifications/bulk-delete', methods=['POST'])
@dual_auth_required
@handle_exceptions
def bulk_delete_notifications():
    """
    Bulk delete notifications

    POST /api/v2/notifications/bulk-delete

    Body:
        {
            "notification_ids": [1, 2, 3],
            // OR
            "delete_all_read": true  // Delete all read notifications
        }

    Returns:
        {
            "success": true,
            "data": {
                "deleted_count": 3
            }
        }
    """
    user = request.current_api_user
    db_session = db_manager.get_session()

    try:
        data, error = validate_json_body()
        if error:
            return error

        notification_ids = data.get('notification_ids', [])
        delete_all_read = data.get('delete_all_read', False)

        deleted_count = 0

        if delete_all_read:
            # Delete all read notifications for user
            deleted_count = db_session.query(Notification).filter(
                Notification.user_id == user.id,
                Notification.is_read == True
            ).delete(synchronize_session='fetch')

        elif notification_ids:
            # Delete specific notifications
            deleted_count = db_session.query(Notification).filter(
                Notification.id.in_(notification_ids),
                Notification.user_id == user.id
            ).delete(synchronize_session='fetch')

        db_session.commit()

        return api_response(
            data={'deleted_count': deleted_count},
            message=f'{deleted_count} notification(s) deleted'
        )

    finally:
        db_session.close()


# =============================================================================
# GET SINGLE NOTIFICATION
# =============================================================================

@api_v2_bp.route('/notifications/<int:notification_id>', methods=['GET'])
@dual_auth_required
@handle_exceptions
def get_notification(notification_id):
    """
    Get a single notification by ID

    GET /api/v2/notifications/:id

    Returns:
        Notification object
    """
    user = request.current_api_user
    db_session = db_manager.get_session()

    try:
        notification = db_session.query(Notification).filter(
            Notification.id == notification_id,
            Notification.user_id == user.id
        ).first()

        if not notification:
            return api_error(
                ErrorCodes.RESOURCE_NOT_FOUND,
                f'Notification with ID {notification_id} not found',
                status_code=404
            )

        return api_response(data=format_notification(notification))

    finally:
        db_session.close()
