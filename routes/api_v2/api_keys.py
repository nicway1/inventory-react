"""
API Key Management Endpoints

This module provides RESTful API endpoints for managing API keys:
- List API keys with pagination and filtering
- Create new API keys
- Get API key details
- Update API key properties
- Revoke (delete) API keys
- Get usage statistics

All endpoints require SUPER_ADMIN permissions.
"""

from flask import request
from datetime import datetime, timedelta
from sqlalchemy import or_
from sqlalchemy.orm import joinedload
import logging

from models.api_key import APIKey
from models.api_usage import APIUsage
from models.user import User, UserType
from models.activity import Activity
from utils.db_manager import DatabaseManager
from utils.api_key_manager import APIKeyManager, PERMISSION_GROUPS

from . import api_v2_bp
from .utils import (
    api_response,
    api_error,
    api_created,
    api_no_content,
    paginate_query,
    get_pagination_params,
    validate_required_fields,
    validate_json_body,
    ErrorCodes,
    handle_exceptions,
    dual_auth_required,
    serialize_datetime,
)

logger = logging.getLogger(__name__)
db_manager = DatabaseManager()


# =============================================================================
# SUPER ADMIN PERMISSION DECORATOR
# =============================================================================

def super_admin_required(f):
    """
    Decorator to ensure user has SUPER_ADMIN permissions.
    Must be used after dual_auth_required decorator.
    """
    from functools import wraps

    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = getattr(request, 'current_api_user', None)

        if not user:
            return api_error(
                ErrorCodes.AUTHENTICATION_REQUIRED,
                'Authentication required',
                status_code=401
            )

        # Only SUPER_ADMIN can manage API keys
        if user.user_type != UserType.SUPER_ADMIN:
            logger.warning(f'API key management access denied for user {user.username} (type: {user.user_type})')
            return api_error(
                ErrorCodes.ADMIN_ACCESS_REQUIRED,
                'Super admin access required. Only SUPER_ADMIN users can manage API keys.',
                status_code=403
            )

        return f(*args, **kwargs)

    return decorated_function


def log_api_key_activity(db_session, user_id, activity_type, content, reference_id=None):
    """
    Create an audit log entry for API key management actions
    """
    try:
        activity = Activity(
            user_id=user_id,
            type=activity_type,
            content=content,
            reference_id=reference_id
        )
        db_session.add(activity)
        logger.info(f'API key activity logged: {activity_type} by user {user_id}')
    except Exception as e:
        logger.error(f'Failed to log API key activity: {str(e)}')


def get_key_prefix(api_key):
    """
    Generate a display-safe key prefix.
    Since we only store the hash, we create a prefix from the hash for display.
    Format: tl_<first 8 chars of hash>...
    """
    if api_key.key_hash:
        return f"tl_{api_key.key_hash[:8]}..."
    return "tl_****..."


def get_api_key_status(api_key):
    """
    Determine the status of an API key.
    Returns: 'active', 'revoked', or 'expired'
    """
    if not api_key.is_active:
        return 'revoked'
    if api_key.is_expired():
        return 'expired'
    return 'active'


def format_api_key_response(api_key, include_created_by=True):
    """
    Format an API key for API response.
    Never includes the full key - only the prefix.
    """
    data = {
        'id': api_key.id,
        'name': api_key.name,
        'key_prefix': get_key_prefix(api_key),
        'status': get_api_key_status(api_key),
        'permissions': api_key.get_permissions(),
        'created_at': serialize_datetime(api_key.created_at),
        'expires_at': serialize_datetime(api_key.expires_at),
        'last_used_at': serialize_datetime(api_key.last_used_at),
        'usage_count': api_key.request_count or 0,
        'last_request_ip': api_key.last_request_ip
    }

    if include_created_by and api_key.created_by:
        data['created_by'] = {
            'id': api_key.created_by.id,
            'username': api_key.created_by.username
        }
    else:
        data['created_by'] = None

    return data


# =============================================================================
# LIST API KEYS
# =============================================================================

@api_v2_bp.route('/admin/api-keys', methods=['GET'])
@dual_auth_required
@super_admin_required
@handle_exceptions
def list_api_keys():
    """
    List all API keys with pagination and filtering

    GET /api/v2/admin/api-keys

    Query Parameters:
        - page: Page number (default: 1)
        - per_page: Items per page (default: 20, max: 100)
        - status: Filter by status - 'active', 'revoked', 'expired' (optional)
        - search: Search by name or key prefix (optional)

    Returns:
        List of API keys with pagination metadata
    """
    db_session = db_manager.get_session()
    try:
        # Get pagination params
        page, per_page = get_pagination_params()

        # Build query with eager loading
        query = db_session.query(APIKey).options(
            joinedload(APIKey.created_by)
        )

        # Filter by status
        status_filter = request.args.get('status', '').lower()
        if status_filter == 'active':
            query = query.filter(
                APIKey.is_active == True,
                or_(
                    APIKey.expires_at.is_(None),
                    APIKey.expires_at > datetime.utcnow()
                )
            )
        elif status_filter == 'revoked':
            query = query.filter(APIKey.is_active == False)
        elif status_filter == 'expired':
            query = query.filter(
                APIKey.expires_at.isnot(None),
                APIKey.expires_at <= datetime.utcnow()
            )

        # Search by name or key prefix
        search = request.args.get('search', '').strip()
        if search:
            search_pattern = f'%{search}%'
            query = query.filter(
                or_(
                    APIKey.name.ilike(search_pattern),
                    APIKey.key_hash.ilike(f'{search}%')  # Match hash prefix
                )
            )

        # Order by created_at desc (newest first)
        query = query.order_by(APIKey.created_at.desc())

        # Paginate
        api_keys, pagination_meta = paginate_query(query, page, per_page)

        # Format response
        keys_data = [format_api_key_response(key) for key in api_keys]

        return api_response(
            data=keys_data,
            message=f'Retrieved {len(keys_data)} API keys',
            meta=pagination_meta
        )

    finally:
        db_session.close()


# =============================================================================
# CREATE API KEY
# =============================================================================

@api_v2_bp.route('/admin/api-keys', methods=['POST'])
@dual_auth_required
@super_admin_required
@handle_exceptions
def create_api_key():
    """
    Create a new API key

    POST /api/v2/admin/api-keys

    Request Body:
        {
            "name": "string (required)",
            "permissions": ["string array (optional, defaults to read_only)"],
            "expires_in_days": "integer (optional, default: 365)"
        }

    Returns:
        Created API key with the FULL key (only shown once)
    """
    # Validate request body
    data, error = validate_json_body()
    if error:
        return error

    # Validate required fields
    required_fields = ['name']
    is_valid, error = validate_required_fields(data, required_fields)
    if not is_valid:
        return error

    db_session = db_manager.get_session()
    try:
        current_user = request.current_api_user

        # Get permissions (default to read_only)
        permissions = data.get('permissions', PERMISSION_GROUPS['read_only'])

        # Validate permissions
        if not APIKeyManager._validate_permissions(permissions):
            return api_error(
                ErrorCodes.VALIDATION_ERROR,
                'Invalid permissions provided. Valid permissions are: tickets:read, tickets:write, tickets:delete, tickets:*, users:read, users:write, users:delete, users:*, inventory:read, inventory:write, inventory:delete, inventory:*, admin:read, admin:write, admin:*, sync:read, sync:write, sync:*, analytics:read, analytics:*, usage:read, usage:*',
                status_code=400
            )

        # Calculate expiration date
        expires_in_days = data.get('expires_in_days', 365)
        if not isinstance(expires_in_days, int) or expires_in_days < 1:
            return api_error(
                ErrorCodes.VALIDATION_ERROR,
                'expires_in_days must be a positive integer',
                status_code=400
            )

        expires_at = datetime.utcnow() + timedelta(days=expires_in_days)

        # Generate the API key using the manager
        success, message, api_key = APIKeyManager.generate_key(
            name=data['name'],
            permissions=permissions,
            expires_at=expires_at,
            created_by_id=current_user.id
        )

        if not success:
            return api_error(
                ErrorCodes.VALIDATION_ERROR,
                message,
                status_code=400
            )

        # Log activity
        log_api_key_activity(
            db_session,
            current_user.id,
            'api_key_created',
            f'Created API key "{api_key.name}" with {len(permissions)} permissions',
            api_key.id
        )
        db_session.commit()

        logger.info(f'API key created: {api_key.name} (ID: {api_key.id}) by admin {current_user.username}')

        # Return with the full key (only time it's shown)
        response_data = {
            'id': api_key.id,
            'name': api_key.name,
            'key': f"tl_{api_key._raw_key}",  # Add prefix for identification
            'key_prefix': get_key_prefix(api_key),
            'permissions': api_key.get_permissions(),
            'expires_at': serialize_datetime(api_key.expires_at)
        }

        return api_created(
            data=response_data,
            message='API key created. Save this key - it won\'t be shown again.'
        )

    except Exception as e:
        db_session.rollback()
        logger.error(f'Error creating API key: {str(e)}')
        return api_error(
            ErrorCodes.DATABASE_ERROR,
            f'Failed to create API key: {str(e)}',
            status_code=500
        )
    finally:
        db_session.close()


# =============================================================================
# GET SINGLE API KEY
# =============================================================================

@api_v2_bp.route('/admin/api-keys/<int:key_id>', methods=['GET'])
@dual_auth_required
@super_admin_required
@handle_exceptions
def get_api_key(key_id):
    """
    Get a single API key by ID with usage stats

    GET /api/v2/admin/api-keys/<id>

    Returns:
        API key details with usage statistics
    """
    db_session = db_manager.get_session()
    try:
        # Get API key with eager loading
        api_key = db_session.query(APIKey).options(
            joinedload(APIKey.created_by)
        ).filter(APIKey.id == key_id).first()

        if not api_key:
            return api_error(
                ErrorCodes.RESOURCE_NOT_FOUND,
                f'API key with ID {key_id} not found',
                status_code=404
            )

        # Get usage stats
        usage_stats = APIKeyManager.get_usage_stats(key_id, days=30)

        # Format response
        key_data = format_api_key_response(api_key)
        key_data['usage_stats'] = {
            'total_requests_30d': usage_stats.get('total_requests', 0),
            'avg_response_time_ms': round(usage_stats.get('avg_response_time', 0), 2),
            'error_count_30d': usage_stats.get('error_count', 0),
            'error_rate_30d': round(usage_stats.get('error_rate', 0), 2)
        }

        return api_response(
            data=key_data,
            message=f'Retrieved API key "{api_key.name}"'
        )

    finally:
        db_session.close()


# =============================================================================
# UPDATE API KEY
# =============================================================================

@api_v2_bp.route('/admin/api-keys/<int:key_id>', methods=['PUT'])
@dual_auth_required
@super_admin_required
@handle_exceptions
def update_api_key(key_id):
    """
    Update an API key (name, permissions, extend expiry)

    PUT /api/v2/admin/api-keys/<id>

    Request Body:
        {
            "name": "string (optional)",
            "permissions": ["string array (optional)"],
            "extend_days": "integer (optional) - days to extend expiration"
        }

    Returns:
        Updated API key object
    """
    # Validate request body
    data, error = validate_json_body()
    if error:
        return error

    db_session = db_manager.get_session()
    try:
        # Find API key
        api_key = db_session.query(APIKey).options(
            joinedload(APIKey.created_by)
        ).filter(APIKey.id == key_id).first()

        if not api_key:
            return api_error(
                ErrorCodes.RESOURCE_NOT_FOUND,
                f'API key with ID {key_id} not found',
                status_code=404
            )

        current_user = request.current_api_user
        changes = []

        # Update name
        if 'name' in data and data['name']:
            new_name = data['name'].strip()
            if new_name != api_key.name:
                # Check if name already exists
                existing = db_session.query(APIKey).filter(
                    APIKey.name == new_name,
                    APIKey.id != key_id
                ).first()
                if existing:
                    return api_error(
                        ErrorCodes.RESOURCE_ALREADY_EXISTS,
                        f'An API key with name "{new_name}" already exists',
                        status_code=409
                    )
                changes.append(f'name: {api_key.name} -> {new_name}')
                api_key.name = new_name

        # Update permissions
        if 'permissions' in data:
            permissions = data['permissions']
            if not APIKeyManager._validate_permissions(permissions):
                return api_error(
                    ErrorCodes.VALIDATION_ERROR,
                    'Invalid permissions provided',
                    status_code=400
                )
            old_perms = api_key.get_permissions()
            if set(permissions) != set(old_perms):
                changes.append(f'permissions updated: {len(old_perms)} -> {len(permissions)} permissions')
                api_key.set_permissions(permissions)

        # Extend expiration
        if 'extend_days' in data:
            extend_days = data['extend_days']
            if not isinstance(extend_days, int) or extend_days < 1:
                return api_error(
                    ErrorCodes.VALIDATION_ERROR,
                    'extend_days must be a positive integer',
                    status_code=400
                )

            if api_key.expires_at:
                new_expires = api_key.expires_at + timedelta(days=extend_days)
            else:
                new_expires = datetime.utcnow() + timedelta(days=extend_days)

            changes.append(f'expiration extended by {extend_days} days')
            api_key.expires_at = new_expires

        # Log activity
        if changes:
            log_api_key_activity(
                db_session,
                current_user.id,
                'api_key_updated',
                f'Updated API key "{api_key.name}": {"; ".join(changes)}',
                api_key.id
            )
            db_session.commit()
            logger.info(f'API key updated: {api_key.name} (ID: {api_key.id}) by admin {current_user.username}')

        return api_response(
            data=format_api_key_response(api_key),
            message=f'API key "{api_key.name}" updated successfully'
        )

    except Exception as e:
        db_session.rollback()
        logger.error(f'Error updating API key: {str(e)}')
        return api_error(
            ErrorCodes.DATABASE_ERROR,
            f'Failed to update API key: {str(e)}',
            status_code=500
        )
    finally:
        db_session.close()


# =============================================================================
# REVOKE (DELETE) API KEY
# =============================================================================

@api_v2_bp.route('/admin/api-keys/<int:key_id>', methods=['DELETE'])
@dual_auth_required
@super_admin_required
@handle_exceptions
def revoke_api_key(key_id):
    """
    Revoke an API key (soft delete - marks as inactive)

    DELETE /api/v2/admin/api-keys/<id>

    Returns:
        204 No Content on success
    """
    db_session = db_manager.get_session()
    try:
        # Find API key
        api_key = db_session.query(APIKey).filter(APIKey.id == key_id).first()

        if not api_key:
            return api_error(
                ErrorCodes.RESOURCE_NOT_FOUND,
                f'API key with ID {key_id} not found',
                status_code=404
            )

        if not api_key.is_active:
            return api_error(
                ErrorCodes.VALIDATION_ERROR,
                'API key is already revoked',
                status_code=400
            )

        current_user = request.current_api_user
        key_name = api_key.name

        # Revoke the key (soft delete)
        api_key.is_active = False

        # Log activity
        log_api_key_activity(
            db_session,
            current_user.id,
            'api_key_revoked',
            f'Revoked API key "{key_name}" (ID: {key_id})',
            key_id
        )

        db_session.commit()
        logger.info(f'API key revoked: {key_name} (ID: {key_id}) by admin {current_user.username}')

        return api_no_content()

    except Exception as e:
        db_session.rollback()
        logger.error(f'Error revoking API key: {str(e)}')
        return api_error(
            ErrorCodes.DATABASE_ERROR,
            f'Failed to revoke API key: {str(e)}',
            status_code=500
        )
    finally:
        db_session.close()


# =============================================================================
# GET API KEY USAGE STATISTICS
# =============================================================================

@api_v2_bp.route('/admin/api-keys/<int:key_id>/usage', methods=['GET'])
@dual_auth_required
@super_admin_required
@handle_exceptions
def get_api_key_usage(key_id):
    """
    Get detailed usage statistics for an API key

    GET /api/v2/admin/api-keys/<id>/usage

    Query Parameters:
        - days: Number of days to look back (default: 30, max: 365)

    Returns:
        Usage statistics including daily breakdown
    """
    db_session = db_manager.get_session()
    try:
        # Verify API key exists
        api_key = db_session.query(APIKey).filter(APIKey.id == key_id).first()

        if not api_key:
            return api_error(
                ErrorCodes.RESOURCE_NOT_FOUND,
                f'API key with ID {key_id} not found',
                status_code=404
            )

        # Get days parameter
        days = request.args.get('days', 30, type=int)
        days = max(1, min(days, 365))  # Clamp between 1 and 365

        # Get usage stats
        usage_stats = APIKeyManager.get_usage_stats(key_id, days=days)
        daily_usage = APIKeyManager.get_daily_usage(key_id, days=days)

        # Get most used endpoints
        endpoint_stats = db_session.query(
            APIUsage.endpoint,
            APIUsage.method,
            APIUsage.status_code.label('status'),
        ).filter(
            APIUsage.api_key_id == key_id,
            APIUsage.timestamp >= datetime.utcnow() - timedelta(days=days)
        ).all()

        # Aggregate endpoint usage
        endpoint_counts = {}
        for record in endpoint_stats:
            key = f"{record.method} {record.endpoint}"
            if key not in endpoint_counts:
                endpoint_counts[key] = {'count': 0, 'errors': 0}
            endpoint_counts[key]['count'] += 1
            if record.status >= 400:
                endpoint_counts[key]['errors'] += 1

        # Sort by count and take top 10
        top_endpoints = sorted(
            [{'endpoint': k, **v} for k, v in endpoint_counts.items()],
            key=lambda x: x['count'],
            reverse=True
        )[:10]

        response_data = {
            'api_key_id': key_id,
            'api_key_name': api_key.name,
            'period_days': days,
            'summary': {
                'total_requests': usage_stats.get('total_requests', 0),
                'avg_response_time_ms': round(usage_stats.get('avg_response_time', 0), 2),
                'error_count': usage_stats.get('error_count', 0),
                'error_rate_percent': round(usage_stats.get('error_rate', 0), 2),
                'lifetime_requests': api_key.request_count or 0,
                'last_used_at': serialize_datetime(api_key.last_used_at),
                'last_request_ip': api_key.last_request_ip
            },
            'daily_breakdown': daily_usage,
            'top_endpoints': top_endpoints
        }

        return api_response(
            data=response_data,
            message=f'Retrieved usage statistics for API key "{api_key.name}"'
        )

    finally:
        db_session.close()


# =============================================================================
# GET AVAILABLE PERMISSIONS
# =============================================================================

@api_v2_bp.route('/admin/api-keys/permissions', methods=['GET'])
@dual_auth_required
@super_admin_required
@handle_exceptions
def get_available_permissions():
    """
    Get list of available permissions and permission groups

    GET /api/v2/admin/api-keys/permissions

    Returns:
        Available permissions and predefined permission groups
    """
    # Individual permissions
    individual_permissions = [
        {'value': 'tickets:read', 'label': 'Read Tickets', 'group': 'Tickets'},
        {'value': 'tickets:write', 'label': 'Create/Update Tickets', 'group': 'Tickets'},
        {'value': 'tickets:delete', 'label': 'Delete Tickets', 'group': 'Tickets'},
        {'value': 'tickets:*', 'label': 'Full Ticket Access', 'group': 'Tickets'},
        {'value': 'users:read', 'label': 'Read Users', 'group': 'Users'},
        {'value': 'users:write', 'label': 'Create/Update Users', 'group': 'Users'},
        {'value': 'users:delete', 'label': 'Delete Users', 'group': 'Users'},
        {'value': 'users:*', 'label': 'Full User Access', 'group': 'Users'},
        {'value': 'inventory:read', 'label': 'Read Inventory', 'group': 'Inventory'},
        {'value': 'inventory:write', 'label': 'Create/Update Inventory', 'group': 'Inventory'},
        {'value': 'inventory:delete', 'label': 'Delete Inventory', 'group': 'Inventory'},
        {'value': 'inventory:*', 'label': 'Full Inventory Access', 'group': 'Inventory'},
        {'value': 'admin:read', 'label': 'Read Admin Data', 'group': 'Admin'},
        {'value': 'admin:write', 'label': 'Write Admin Data', 'group': 'Admin'},
        {'value': 'admin:*', 'label': 'Full Admin Access', 'group': 'Admin'},
        {'value': 'sync:read', 'label': 'Read Sync Data', 'group': 'Sync'},
        {'value': 'sync:write', 'label': 'Write Sync Data', 'group': 'Sync'},
        {'value': 'sync:*', 'label': 'Full Sync Access', 'group': 'Sync'},
        {'value': 'analytics:read', 'label': 'Read Analytics', 'group': 'Analytics'},
        {'value': 'analytics:*', 'label': 'Full Analytics Access', 'group': 'Analytics'},
        {'value': 'usage:read', 'label': 'Read Usage Data', 'group': 'Usage'},
        {'value': 'usage:*', 'label': 'Full Usage Access', 'group': 'Usage'},
    ]

    # Permission groups with descriptions
    permission_groups = {
        'read_only': {
            'name': 'Read Only',
            'description': 'Basic read access to tickets, users, and inventory',
            'permissions': PERMISSION_GROUPS['read_only']
        },
        'tickets_full': {
            'name': 'Full Tickets',
            'description': 'Complete access to ticket operations',
            'permissions': PERMISSION_GROUPS['tickets_full']
        },
        'mobile_app': {
            'name': 'Mobile App',
            'description': 'Permissions suitable for mobile app integration',
            'permissions': PERMISSION_GROUPS['mobile_app']
        },
        'analytics_only': {
            'name': 'Analytics Only',
            'description': 'Read-only access to analytics and usage data',
            'permissions': PERMISSION_GROUPS['analytics_only']
        },
        'full_access': {
            'name': 'Full Access',
            'description': 'Complete access to all API features (use with caution)',
            'permissions': PERMISSION_GROUPS['full_access']
        }
    }

    return api_response(
        data={
            'permissions': individual_permissions,
            'groups': permission_groups
        },
        message='Retrieved available permissions'
    )
