"""
System Settings API v2 Endpoints

This module provides RESTful API endpoints for system settings management:
- GET /api/v2/admin/system-settings - Get all system settings
- PUT /api/v2/admin/system-settings - Update system settings
- POST /api/v2/admin/system-settings/issue-types - Create issue type
- DELETE /api/v2/admin/system-settings/issue-types/<id> - Delete issue type

All endpoints require admin authentication (SUPER_ADMIN or DEVELOPER user types).
"""

from flask import request, current_app
import logging
import os
import pytz

from models.system_settings import SystemSettings
from models.custom_issue_type import CustomIssueType
from models.user import UserType
from models.activity import Activity
from utils.db_manager import DatabaseManager

from . import api_v2_bp
from .utils import (
    api_response,
    api_error,
    api_created,
    api_no_content,
    validate_required_fields,
    validate_json_body,
    ErrorCodes,
    handle_exceptions,
    dual_auth_required,
)

logger = logging.getLogger(__name__)
db_manager = DatabaseManager()


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def admin_required_for_settings(f):
    """
    Decorator to ensure user has admin permissions (SUPER_ADMIN or DEVELOPER).
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

        # Check if user is SUPER_ADMIN or DEVELOPER
        if user.user_type not in [UserType.SUPER_ADMIN, UserType.DEVELOPER]:
            logger.warning(f'System settings access denied for user {user.username} (type: {user.user_type})')
            return api_error(
                ErrorCodes.ADMIN_ACCESS_REQUIRED,
                'Admin access required. Only SUPER_ADMIN and DEVELOPER users can access system settings.',
                status_code=403
            )

        return f(*args, **kwargs)

    return decorated_function


def log_settings_activity(db_session, user_id, activity_type, content, reference_id=None):
    """
    Create an audit log entry for system settings changes.

    Args:
        db_session: Database session
        user_id: ID of the user performing the action
        activity_type: Type of activity (e.g., 'system_settings_updated')
        content: Description of the action
        reference_id: Optional ID of the affected resource
    """
    try:
        activity = Activity(
            user_id=user_id,
            type=activity_type,
            content=content,
            reference_id=reference_id
        )
        db_session.add(activity)
        logger.info(f'System settings activity logged: {activity_type} by user {user_id}')
    except Exception as e:
        logger.error(f'Failed to log system settings activity: {str(e)}')


def get_setting_value(db_session, setting_key, default_value=None):
    """
    Get a system setting value by key.

    Args:
        db_session: Database session
        setting_key: The setting key to look up
        default_value: Default value if setting not found

    Returns:
        The setting value or default
    """
    try:
        setting = db_session.query(SystemSettings).filter_by(
            setting_key=setting_key
        ).first()
        if setting:
            return setting.get_value()
        return default_value
    except Exception as e:
        logger.warning(f"Could not load setting {setting_key}: {str(e)}")
        return default_value


def set_setting_value(db_session, setting_key, setting_value, setting_type='string', description=None):
    """
    Set a system setting value.

    Args:
        db_session: Database session
        setting_key: The setting key
        setting_value: The value to set
        setting_type: Type of setting ('string', 'boolean', 'integer')
        description: Optional description

    Returns:
        The updated/created SystemSettings object
    """
    setting = db_session.query(SystemSettings).filter_by(
        setting_key=setting_key
    ).first()

    # Convert value to string for storage
    if isinstance(setting_value, bool):
        str_value = 'true' if setting_value else 'false'
    else:
        str_value = str(setting_value)

    if setting:
        setting.setting_value = str_value
        if description:
            setting.description = description
    else:
        setting = SystemSettings(
            setting_key=setting_key,
            setting_value=str_value,
            setting_type=setting_type,
            description=description
        )
        db_session.add(setting)

    return setting


def get_email_config():
    """
    Get email configuration status.

    Returns:
        Dictionary with email configuration details
    """
    # Check SMTP configuration
    mail_server = os.environ.get('MAIL_SERVER', current_app.config.get('MAIL_SERVER', ''))
    smtp_enabled = bool(mail_server and mail_server != 'smtp.example.com')

    # Get from email
    from_email = os.environ.get('MAIL_DEFAULT_SENDER',
                               current_app.config.get('MAIL_DEFAULT_SENDER', ''))

    # Check MS365 OAuth2 configuration
    ms_client_id = os.environ.get('MS_CLIENT_ID', '')
    ms_client_secret = os.environ.get('MS_CLIENT_SECRET', '')
    ms_tenant_id = os.environ.get('MS_TENANT_ID', '')
    ms365_oauth_configured = bool(ms_client_id and ms_client_secret and ms_tenant_id)

    # Check OAuth2 sender
    oauth2_sender = os.environ.get('MS_FROM_EMAIL',
                                   os.environ.get('OAUTH2_DEFAULT_SENDER', ''))
    if oauth2_sender:
        from_email = oauth2_sender

    return {
        'smtp_enabled': smtp_enabled,
        'from_email': from_email or None,
        'ms365_oauth_configured': ms365_oauth_configured
    }


def get_feature_flags(db_session):
    """
    Get feature flag configuration.

    Returns:
        Dictionary with feature flag status
    """
    # Check chatbot enabled (from setting or default)
    chatbot_enabled = get_setting_value(db_session, 'chatbot_enabled', True)
    if isinstance(chatbot_enabled, str):
        chatbot_enabled = chatbot_enabled.lower() in ('true', '1', 'yes')

    # Check SLA enabled
    sla_enabled = get_setting_value(db_session, 'sla_enabled', True)
    if isinstance(sla_enabled, str):
        sla_enabled = sla_enabled.lower() in ('true', '1', 'yes')

    # Check audit enabled
    audit_enabled = get_setting_value(db_session, 'audit_enabled', True)
    if isinstance(audit_enabled, str):
        audit_enabled = audit_enabled.lower() in ('true', '1', 'yes')

    return {
        'chatbot_enabled': chatbot_enabled,
        'sla_enabled': sla_enabled,
        'audit_enabled': audit_enabled
    }


def validate_timezone(timezone_str):
    """
    Validate that a timezone string is valid.

    Args:
        timezone_str: Timezone string to validate

    Returns:
        True if valid, False otherwise
    """
    try:
        pytz.timezone(timezone_str)
        return True
    except pytz.exceptions.UnknownTimeZoneError:
        return False


def validate_homepage(homepage_value):
    """
    Validate homepage value.

    Args:
        homepage_value: Homepage value to validate

    Returns:
        True if valid, False otherwise
    """
    valid_values = ['classic', 'dashboard', 'tickets', 'inventory', 'sf']
    return homepage_value in valid_values


def validate_view(view_value):
    """
    Validate view value (ticket_view or inventory_view).

    Args:
        view_value: View value to validate

    Returns:
        True if valid, False otherwise
    """
    valid_values = ['classic', 'sf']
    return view_value in valid_values


# =============================================================================
# SYSTEM SETTINGS ENDPOINTS
# =============================================================================

@api_v2_bp.route('/admin/system-settings', methods=['GET'])
@dual_auth_required
@admin_required_for_settings
@handle_exceptions
def get_system_settings():
    """
    Get all system settings.

    GET /api/v2/admin/system-settings

    Returns:
        {
            "success": true,
            "data": {
                "general": {
                    "default_homepage": "dashboard",
                    "default_ticket_view": "sf",
                    "default_inventory_view": "sf",
                    "system_timezone": "Asia/Singapore"
                },
                "email": {
                    "smtp_enabled": true,
                    "from_email": "support@example.com",
                    "ms365_oauth_configured": true
                },
                "features": {
                    "chatbot_enabled": true,
                    "sla_enabled": true,
                    "audit_enabled": true
                },
                "issue_types": [
                    {"id": 1, "name": "Hardware Issue", "is_active": true},
                    ...
                ]
            }
        }
    """
    db_session = db_manager.get_session()
    try:
        # Get general settings
        general_settings = {
            'default_homepage': get_setting_value(db_session, 'default_homepage', 'classic'),
            'default_ticket_view': get_setting_value(db_session, 'default_ticket_view', 'classic'),
            'default_inventory_view': get_setting_value(db_session, 'default_inventory_view', 'classic'),
            'system_timezone': get_setting_value(db_session, 'system_timezone', 'Asia/Singapore')
        }

        # Get email configuration
        email_config = get_email_config()

        # Get feature flags
        feature_flags = get_feature_flags(db_session)

        # Get issue types
        issue_types = []
        try:
            custom_issue_types = db_session.query(CustomIssueType).order_by(
                CustomIssueType.name
            ).all()
            issue_types = [
                {
                    'id': it.id,
                    'name': it.name,
                    'is_active': it.is_active,
                    'usage_count': it.usage_count,
                    'created_at': it.created_at.isoformat() + 'Z' if it.created_at else None
                }
                for it in custom_issue_types
            ]
        except Exception as e:
            logger.warning(f"Could not load issue types: {str(e)}")

        response_data = {
            'general': general_settings,
            'email': email_config,
            'features': feature_flags,
            'issue_types': issue_types
        }

        return api_response(
            data=response_data,
            message='System settings retrieved successfully'
        )

    finally:
        db_session.close()


@api_v2_bp.route('/admin/system-settings', methods=['PUT'])
@dual_auth_required
@admin_required_for_settings
@handle_exceptions
def update_system_settings():
    """
    Update system settings.

    PUT /api/v2/admin/system-settings

    Request Body:
        {
            "general": {
                "default_homepage": "tickets",
                "default_ticket_view": "sf",
                "default_inventory_view": "sf",
                "system_timezone": "UTC"
            },
            "features": {
                "chatbot_enabled": true,
                "sla_enabled": false,
                "audit_enabled": true
            }
        }

    Note: Email settings cannot be updated via API (require environment changes).

    Returns:
        Same format as GET with updated values
    """
    # Validate request body
    data, error = validate_json_body()
    if error:
        return error

    db_session = db_manager.get_session()
    try:
        current_user = request.current_api_user
        changes = []

        # Update general settings
        if 'general' in data:
            general = data['general']

            # Update default_homepage
            if 'default_homepage' in general:
                new_value = general['default_homepage']
                if not validate_homepage(new_value):
                    return api_error(
                        ErrorCodes.INVALID_FIELD_VALUE,
                        f'Invalid default_homepage value. Must be one of: classic, dashboard, tickets, inventory, sf',
                        status_code=400
                    )
                old_value = get_setting_value(db_session, 'default_homepage', 'classic')
                if new_value != old_value:
                    set_setting_value(db_session, 'default_homepage', new_value, 'string',
                                     'Default homepage for users')
                    changes.append(f'default_homepage: {old_value} -> {new_value}')

            # Update default_ticket_view
            if 'default_ticket_view' in general:
                new_value = general['default_ticket_view']
                if not validate_view(new_value):
                    return api_error(
                        ErrorCodes.INVALID_FIELD_VALUE,
                        f'Invalid default_ticket_view value. Must be one of: classic, sf',
                        status_code=400
                    )
                old_value = get_setting_value(db_session, 'default_ticket_view', 'classic')
                if new_value != old_value:
                    set_setting_value(db_session, 'default_ticket_view', new_value, 'string',
                                     'Default ticket view style')
                    changes.append(f'default_ticket_view: {old_value} -> {new_value}')

            # Update default_inventory_view
            if 'default_inventory_view' in general:
                new_value = general['default_inventory_view']
                if not validate_view(new_value):
                    return api_error(
                        ErrorCodes.INVALID_FIELD_VALUE,
                        f'Invalid default_inventory_view value. Must be one of: classic, sf',
                        status_code=400
                    )
                old_value = get_setting_value(db_session, 'default_inventory_view', 'classic')
                if new_value != old_value:
                    set_setting_value(db_session, 'default_inventory_view', new_value, 'string',
                                     'Default inventory view style')
                    changes.append(f'default_inventory_view: {old_value} -> {new_value}')

            # Update system_timezone
            if 'system_timezone' in general:
                new_value = general['system_timezone']
                if not validate_timezone(new_value):
                    return api_error(
                        ErrorCodes.INVALID_FIELD_VALUE,
                        f'Invalid timezone: {new_value}. Please provide a valid timezone.',
                        status_code=400
                    )
                old_value = get_setting_value(db_session, 'system_timezone', 'Asia/Singapore')
                if new_value != old_value:
                    set_setting_value(db_session, 'system_timezone', new_value, 'string',
                                     'System timezone')
                    changes.append(f'system_timezone: {old_value} -> {new_value}')

        # Update feature flags
        if 'features' in data:
            features = data['features']

            # Update chatbot_enabled
            if 'chatbot_enabled' in features:
                new_value = bool(features['chatbot_enabled'])
                old_value = get_setting_value(db_session, 'chatbot_enabled', True)
                if isinstance(old_value, str):
                    old_value = old_value.lower() in ('true', '1', 'yes')
                if new_value != old_value:
                    set_setting_value(db_session, 'chatbot_enabled', new_value, 'boolean',
                                     'Enable chatbot feature')
                    changes.append(f'chatbot_enabled: {old_value} -> {new_value}')

            # Update sla_enabled
            if 'sla_enabled' in features:
                new_value = bool(features['sla_enabled'])
                old_value = get_setting_value(db_session, 'sla_enabled', True)
                if isinstance(old_value, str):
                    old_value = old_value.lower() in ('true', '1', 'yes')
                if new_value != old_value:
                    set_setting_value(db_session, 'sla_enabled', new_value, 'boolean',
                                     'Enable SLA tracking feature')
                    changes.append(f'sla_enabled: {old_value} -> {new_value}')

            # Update audit_enabled
            if 'audit_enabled' in features:
                new_value = bool(features['audit_enabled'])
                old_value = get_setting_value(db_session, 'audit_enabled', True)
                if isinstance(old_value, str):
                    old_value = old_value.lower() in ('true', '1', 'yes')
                if new_value != old_value:
                    set_setting_value(db_session, 'audit_enabled', new_value, 'boolean',
                                     'Enable inventory audit feature')
                    changes.append(f'audit_enabled: {old_value} -> {new_value}')

        # Log activity if changes were made
        if changes:
            log_settings_activity(
                db_session,
                current_user.id,
                'system_settings_updated',
                f'Updated system settings: {"; ".join(changes)}'
            )
            logger.info(f'System settings updated by {current_user.username}: {"; ".join(changes)}')

        db_session.commit()

        # Return updated settings (re-read from database)
        general_settings = {
            'default_homepage': get_setting_value(db_session, 'default_homepage', 'classic'),
            'default_ticket_view': get_setting_value(db_session, 'default_ticket_view', 'classic'),
            'default_inventory_view': get_setting_value(db_session, 'default_inventory_view', 'classic'),
            'system_timezone': get_setting_value(db_session, 'system_timezone', 'Asia/Singapore')
        }

        email_config = get_email_config()
        feature_flags = get_feature_flags(db_session)

        # Get issue types
        issue_types = []
        try:
            custom_issue_types = db_session.query(CustomIssueType).order_by(
                CustomIssueType.name
            ).all()
            issue_types = [
                {
                    'id': it.id,
                    'name': it.name,
                    'is_active': it.is_active,
                    'usage_count': it.usage_count,
                    'created_at': it.created_at.isoformat() + 'Z' if it.created_at else None
                }
                for it in custom_issue_types
            ]
        except Exception as e:
            logger.warning(f"Could not load issue types: {str(e)}")

        response_data = {
            'general': general_settings,
            'email': email_config,
            'features': feature_flags,
            'issue_types': issue_types
        }

        return api_response(
            data=response_data,
            message='System settings updated successfully' if changes else 'No changes made'
        )

    except Exception as e:
        db_session.rollback()
        logger.error(f'Error updating system settings: {str(e)}')
        return api_error(
            ErrorCodes.DATABASE_ERROR,
            f'Failed to update system settings: {str(e)}',
            status_code=500
        )
    finally:
        db_session.close()


# =============================================================================
# ISSUE TYPE ENDPOINTS
# =============================================================================

@api_v2_bp.route('/admin/system-settings/issue-types', methods=['POST'])
@dual_auth_required
@admin_required_for_settings
@handle_exceptions
def create_issue_type():
    """
    Create a new custom issue type.

    POST /api/v2/admin/system-settings/issue-types

    Request Body:
        {
            "name": "Hardware Issue",
            "is_active": true  // optional, defaults to true
        }

    Returns:
        Created issue type object
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
        name = data['name'].strip()

        if not name:
            return api_error(
                ErrorCodes.VALIDATION_ERROR,
                'Issue type name cannot be empty',
                status_code=400
            )

        if len(name) > 100:
            return api_error(
                ErrorCodes.VALIDATION_ERROR,
                'Issue type name cannot exceed 100 characters',
                status_code=400
            )

        # Check if issue type already exists
        existing = db_session.query(CustomIssueType).filter_by(name=name).first()
        if existing:
            return api_error(
                ErrorCodes.RESOURCE_ALREADY_EXISTS,
                f'Issue type "{name}" already exists',
                status_code=409
            )

        # Create new issue type
        is_active = data.get('is_active', True)
        issue_type = CustomIssueType(
            name=name,
            is_active=is_active
        )

        db_session.add(issue_type)
        db_session.flush()

        # Log activity
        current_user = request.current_api_user
        log_settings_activity(
            db_session,
            current_user.id,
            'issue_type_created',
            f'Created issue type "{name}"',
            issue_type.id
        )

        db_session.commit()

        logger.info(f'Issue type created: {name} (ID: {issue_type.id}) by {current_user.username}')

        return api_created(
            data=issue_type.to_dict(),
            message=f'Issue type "{name}" created successfully'
        )

    except Exception as e:
        db_session.rollback()
        logger.error(f'Error creating issue type: {str(e)}')
        return api_error(
            ErrorCodes.DATABASE_ERROR,
            f'Failed to create issue type: {str(e)}',
            status_code=500
        )
    finally:
        db_session.close()


@api_v2_bp.route('/admin/system-settings/issue-types/<int:issue_type_id>', methods=['PUT'])
@dual_auth_required
@admin_required_for_settings
@handle_exceptions
def update_issue_type(issue_type_id):
    """
    Update an existing issue type.

    PUT /api/v2/admin/system-settings/issue-types/<id>

    Request Body:
        {
            "name": "New Name",        // optional
            "is_active": false         // optional
        }

    Returns:
        Updated issue type object
    """
    # Validate request body
    data, error = validate_json_body()
    if error:
        return error

    db_session = db_manager.get_session()
    try:
        # Find issue type
        issue_type = db_session.query(CustomIssueType).get(issue_type_id)
        if not issue_type:
            return api_error(
                ErrorCodes.RESOURCE_NOT_FOUND,
                f'Issue type with ID {issue_type_id} not found',
                status_code=404
            )

        changes = []

        # Update name
        if 'name' in data:
            new_name = data['name'].strip()
            if not new_name:
                return api_error(
                    ErrorCodes.VALIDATION_ERROR,
                    'Issue type name cannot be empty',
                    status_code=400
                )
            if len(new_name) > 100:
                return api_error(
                    ErrorCodes.VALIDATION_ERROR,
                    'Issue type name cannot exceed 100 characters',
                    status_code=400
                )
            if new_name != issue_type.name:
                # Check if new name already exists
                existing = db_session.query(CustomIssueType).filter(
                    CustomIssueType.name == new_name,
                    CustomIssueType.id != issue_type_id
                ).first()
                if existing:
                    return api_error(
                        ErrorCodes.RESOURCE_ALREADY_EXISTS,
                        f'Issue type "{new_name}" already exists',
                        status_code=409
                    )
                changes.append(f'name: {issue_type.name} -> {new_name}')
                issue_type.name = new_name

        # Update is_active
        if 'is_active' in data:
            new_active = bool(data['is_active'])
            if new_active != issue_type.is_active:
                changes.append(f'is_active: {issue_type.is_active} -> {new_active}')
                issue_type.is_active = new_active

        # Log activity if changes were made
        current_user = request.current_api_user
        if changes:
            log_settings_activity(
                db_session,
                current_user.id,
                'issue_type_updated',
                f'Updated issue type "{issue_type.name}": {"; ".join(changes)}',
                issue_type.id
            )

        db_session.commit()

        logger.info(f'Issue type updated: {issue_type.name} (ID: {issue_type.id}) by {current_user.username}')

        return api_response(
            data=issue_type.to_dict(),
            message=f'Issue type "{issue_type.name}" updated successfully' if changes else 'No changes made'
        )

    except Exception as e:
        db_session.rollback()
        logger.error(f'Error updating issue type: {str(e)}')
        return api_error(
            ErrorCodes.DATABASE_ERROR,
            f'Failed to update issue type: {str(e)}',
            status_code=500
        )
    finally:
        db_session.close()


@api_v2_bp.route('/admin/system-settings/issue-types/<int:issue_type_id>', methods=['DELETE'])
@dual_auth_required
@admin_required_for_settings
@handle_exceptions
def delete_issue_type(issue_type_id):
    """
    Delete a custom issue type.

    DELETE /api/v2/admin/system-settings/issue-types/<id>

    Note: Issue types with high usage count may be better disabled than deleted.

    Returns:
        204 No Content on success
    """
    db_session = db_manager.get_session()
    try:
        # Find issue type
        issue_type = db_session.query(CustomIssueType).get(issue_type_id)
        if not issue_type:
            return api_error(
                ErrorCodes.RESOURCE_NOT_FOUND,
                f'Issue type with ID {issue_type_id} not found',
                status_code=404
            )

        issue_type_name = issue_type.name
        usage_count = issue_type.usage_count or 0

        # Warn if issue type has high usage
        if usage_count > 10:
            # Still allow deletion but log a warning
            logger.warning(f'Deleting issue type "{issue_type_name}" with {usage_count} uses')

        # Delete the issue type
        db_session.delete(issue_type)

        # Log activity
        current_user = request.current_api_user
        log_settings_activity(
            db_session,
            current_user.id,
            'issue_type_deleted',
            f'Deleted issue type "{issue_type_name}" (ID: {issue_type_id}, usage_count: {usage_count})',
            issue_type_id
        )

        db_session.commit()

        logger.info(f'Issue type deleted: {issue_type_name} (ID: {issue_type_id}) by {current_user.username}')

        return api_no_content()

    except Exception as e:
        db_session.rollback()
        logger.error(f'Error deleting issue type: {str(e)}')
        return api_error(
            ErrorCodes.DATABASE_ERROR,
            f'Failed to delete issue type: {str(e)}',
            status_code=500
        )
    finally:
        db_session.close()


@api_v2_bp.route('/admin/system-settings/issue-types', methods=['GET'])
@dual_auth_required
@admin_required_for_settings
@handle_exceptions
def list_issue_types():
    """
    List all issue types.

    GET /api/v2/admin/system-settings/issue-types

    Query Parameters:
        - active_only: If 'true', only return active issue types (default: false)

    Returns:
        List of issue type objects
    """
    db_session = db_manager.get_session()
    try:
        active_only = request.args.get('active_only', 'false').lower() == 'true'

        query = db_session.query(CustomIssueType).order_by(CustomIssueType.name)

        if active_only:
            query = query.filter(CustomIssueType.is_active == True)

        issue_types = query.all()

        return api_response(
            data=[it.to_dict() for it in issue_types],
            message=f'Retrieved {len(issue_types)} issue types'
        )

    finally:
        db_session.close()
