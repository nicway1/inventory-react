"""
User Preferences API v2 Endpoints

This module provides RESTful API endpoints for user preference management:
- GET /api/v2/user/preferences - Get current user's preferences
- PUT /api/v2/user/preferences - Update current user's preferences
- GET /api/v2/user/preferences/options - Get available preference options

All endpoints require authentication via dual_auth_required decorator.
Users can only access/modify their own preferences.
"""

from flask import request
import logging

from sqlalchemy.orm.attributes import flag_modified

from models.user import User
from utils.db_manager import DatabaseManager

from . import api_v2_bp
from .utils import (
    api_response,
    api_error,
    validate_json_body,
    ErrorCodes,
    handle_exceptions,
    dual_auth_required,
)

logger = logging.getLogger(__name__)
db_manager = DatabaseManager()


# =============================================================================
# DEFAULT PREFERENCE VALUES
# =============================================================================

DEFAULT_THEME_PREFERENCES = {
    'mode': 'light',
    'primary_color': '#1976D2',
    'sidebar_style': 'expanded'
}

DEFAULT_LAYOUT_PREFERENCES = {
    'default_homepage': 'dashboard',
    'default_ticket_view': 'sf',
    'default_inventory_view': 'sf',
    'sidebar_collapsed': False,
    'compact_mode': False
}

DEFAULT_NOTIFICATION_PREFERENCES = {
    'email_enabled': True,
    'in_app_enabled': True,
    'sound_enabled': False
}


# =============================================================================
# AVAILABLE OPTIONS
# =============================================================================

THEME_MODES = ['light', 'dark', 'auto']

PRIMARY_COLORS = [
    {'name': 'Blue', 'value': '#1976D2'},
    {'name': 'Green', 'value': '#4CAF50'},
    {'name': 'Purple', 'value': '#9C27B0'},
    {'name': 'Red', 'value': '#F44336'},
    {'name': 'Orange', 'value': '#FF9800'},
    {'name': 'Teal', 'value': '#009688'},
    {'name': 'Pink', 'value': '#E91E63'},
    {'name': 'Indigo', 'value': '#3F51B5'}
]

SIDEBAR_STYLES = ['expanded', 'compact', 'hidden']

HOMEPAGE_OPTIONS = ['dashboard', 'tickets', 'inventory']

VIEW_OPTIONS = ['classic', 'sf']


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_user_preferences(user):
    """
    Extract and normalize user preferences from the user model.

    Args:
        user: User model instance

    Returns:
        Dictionary with theme, layout, and notification preferences
    """
    # Get the raw preferences JSON from user model
    raw_preferences = user.preferences or {}

    # Handle case where preferences might be stored as string
    if isinstance(raw_preferences, str):
        import json
        try:
            raw_preferences = json.loads(raw_preferences)
        except (json.JSONDecodeError, TypeError):
            raw_preferences = {}

    # Build theme preferences
    theme = {
        'mode': raw_preferences.get('theme_mode', user.theme_preference or DEFAULT_THEME_PREFERENCES['mode']),
        'primary_color': raw_preferences.get('primary_color', DEFAULT_THEME_PREFERENCES['primary_color']),
        'sidebar_style': raw_preferences.get('sidebar_style', DEFAULT_THEME_PREFERENCES['sidebar_style'])
    }

    # Build layout preferences
    layout = {
        'default_homepage': raw_preferences.get('default_homepage', DEFAULT_LAYOUT_PREFERENCES['default_homepage']),
        'default_ticket_view': raw_preferences.get('default_ticket_view', DEFAULT_LAYOUT_PREFERENCES['default_ticket_view']),
        'default_inventory_view': raw_preferences.get('default_inventory_view', DEFAULT_LAYOUT_PREFERENCES['default_inventory_view']),
        'sidebar_collapsed': raw_preferences.get('sidebar_collapsed', DEFAULT_LAYOUT_PREFERENCES['sidebar_collapsed']),
        'compact_mode': raw_preferences.get('compact_mode', DEFAULT_LAYOUT_PREFERENCES['compact_mode'])
    }

    # Build notification preferences
    notifications = {
        'email_enabled': raw_preferences.get('email_enabled', DEFAULT_NOTIFICATION_PREFERENCES['email_enabled']),
        'in_app_enabled': raw_preferences.get('in_app_enabled', DEFAULT_NOTIFICATION_PREFERENCES['in_app_enabled']),
        'sound_enabled': raw_preferences.get('sound_enabled', DEFAULT_NOTIFICATION_PREFERENCES['sound_enabled'])
    }

    return {
        'theme': theme,
        'layout': layout,
        'notifications': notifications
    }


def validate_theme_preferences(theme_data):
    """
    Validate theme preference values.

    Args:
        theme_data: Dictionary with theme preferences

    Returns:
        Tuple of (is_valid, error_message)
    """
    if 'mode' in theme_data:
        if theme_data['mode'] not in THEME_MODES:
            return False, f"Invalid theme mode. Must be one of: {', '.join(THEME_MODES)}"

    if 'primary_color' in theme_data:
        # Validate hex color format
        color = theme_data['primary_color']
        if not isinstance(color, str) or not color.startswith('#') or len(color) != 7:
            return False, "Invalid primary_color format. Must be a hex color (e.g., #1976D2)"

    if 'sidebar_style' in theme_data:
        if theme_data['sidebar_style'] not in SIDEBAR_STYLES:
            return False, f"Invalid sidebar_style. Must be one of: {', '.join(SIDEBAR_STYLES)}"

    return True, None


def validate_layout_preferences(layout_data):
    """
    Validate layout preference values.

    Args:
        layout_data: Dictionary with layout preferences

    Returns:
        Tuple of (is_valid, error_message)
    """
    if 'default_homepage' in layout_data:
        if layout_data['default_homepage'] not in HOMEPAGE_OPTIONS:
            return False, f"Invalid default_homepage. Must be one of: {', '.join(HOMEPAGE_OPTIONS)}"

    if 'default_ticket_view' in layout_data:
        if layout_data['default_ticket_view'] not in VIEW_OPTIONS:
            return False, f"Invalid default_ticket_view. Must be one of: {', '.join(VIEW_OPTIONS)}"

    if 'default_inventory_view' in layout_data:
        if layout_data['default_inventory_view'] not in VIEW_OPTIONS:
            return False, f"Invalid default_inventory_view. Must be one of: {', '.join(VIEW_OPTIONS)}"

    if 'sidebar_collapsed' in layout_data:
        if not isinstance(layout_data['sidebar_collapsed'], bool):
            return False, "sidebar_collapsed must be a boolean"

    if 'compact_mode' in layout_data:
        if not isinstance(layout_data['compact_mode'], bool):
            return False, "compact_mode must be a boolean"

    return True, None


def validate_notification_preferences(notification_data):
    """
    Validate notification preference values.

    Args:
        notification_data: Dictionary with notification preferences

    Returns:
        Tuple of (is_valid, error_message)
    """
    boolean_fields = ['email_enabled', 'in_app_enabled', 'sound_enabled']

    for field in boolean_fields:
        if field in notification_data:
            if not isinstance(notification_data[field], bool):
                return False, f"{field} must be a boolean"

    return True, None


# =============================================================================
# API ENDPOINTS
# =============================================================================

@api_v2_bp.route('/user/preferences', methods=['GET'])
@dual_auth_required
@handle_exceptions
def get_preferences():
    """
    Get current user's theme and layout preferences

    GET /api/v2/user/preferences

    Returns:
        {
            "success": true,
            "data": {
                "theme": {
                    "mode": "light",
                    "primary_color": "#1976D2",
                    "sidebar_style": "expanded"
                },
                "layout": {
                    "default_homepage": "dashboard",
                    "default_ticket_view": "sf",
                    "default_inventory_view": "sf",
                    "sidebar_collapsed": false,
                    "compact_mode": false
                },
                "notifications": {
                    "email_enabled": true,
                    "in_app_enabled": true,
                    "sound_enabled": false
                }
            }
        }
    """
    user = request.current_api_user

    if not user:
        return api_error(
            ErrorCodes.AUTHENTICATION_REQUIRED,
            'Authentication required',
            status_code=401
        )

    db_session = db_manager.get_session()
    try:
        # Refresh user from database to get latest preferences
        db_user = db_session.query(User).get(user.id)

        if not db_user:
            return api_error(
                ErrorCodes.RESOURCE_NOT_FOUND,
                'User not found',
                status_code=404
            )

        preferences = get_user_preferences(db_user)

        logger.info(f'User {user.username} retrieved preferences')

        return api_response(
            data=preferences,
            message='Preferences retrieved successfully'
        )

    finally:
        db_session.close()


@api_v2_bp.route('/user/preferences', methods=['PUT'])
@dual_auth_required
@handle_exceptions
def update_preferences():
    """
    Update current user's preferences (partial update supported)

    PUT /api/v2/user/preferences

    Request Body:
        {
            "theme": {
                "mode": "dark"
            },
            "layout": {
                "sidebar_collapsed": true
            },
            "notifications": {
                "sound_enabled": true
            }
        }

    Returns:
        Updated preferences object
    """
    user = request.current_api_user

    if not user:
        return api_error(
            ErrorCodes.AUTHENTICATION_REQUIRED,
            'Authentication required',
            status_code=401
        )

    # Validate request body
    data, error = validate_json_body()
    if error:
        return error

    # Validate that at least one preference category is provided
    if not any(key in data for key in ['theme', 'layout', 'notifications']):
        return api_error(
            ErrorCodes.VALIDATION_ERROR,
            'Request must include at least one of: theme, layout, notifications',
            status_code=400
        )

    # Validate theme preferences if provided
    if 'theme' in data:
        is_valid, error_msg = validate_theme_preferences(data['theme'])
        if not is_valid:
            return api_error(
                ErrorCodes.INVALID_FIELD_VALUE,
                error_msg,
                status_code=400
            )

    # Validate layout preferences if provided
    if 'layout' in data:
        is_valid, error_msg = validate_layout_preferences(data['layout'])
        if not is_valid:
            return api_error(
                ErrorCodes.INVALID_FIELD_VALUE,
                error_msg,
                status_code=400
            )

    # Validate notification preferences if provided
    if 'notifications' in data:
        is_valid, error_msg = validate_notification_preferences(data['notifications'])
        if not is_valid:
            return api_error(
                ErrorCodes.INVALID_FIELD_VALUE,
                error_msg,
                status_code=400
            )

    db_session = db_manager.get_session()
    try:
        # Get user from database
        db_user = db_session.query(User).get(user.id)

        if not db_user:
            return api_error(
                ErrorCodes.RESOURCE_NOT_FOUND,
                'User not found',
                status_code=404
            )

        # Initialize preferences if None
        if db_user.preferences is None:
            db_user.preferences = {}

        # Create a mutable copy of preferences
        prefs = dict(db_user.preferences)

        # Handle case where preferences might be stored as string
        if isinstance(prefs, str):
            import json
            try:
                prefs = json.loads(prefs)
            except (json.JSONDecodeError, TypeError):
                prefs = {}

        changes = []

        # Update theme preferences
        if 'theme' in data:
            theme_data = data['theme']

            if 'mode' in theme_data:
                prefs['theme_mode'] = theme_data['mode']
                # Also update the legacy theme_preference field for compatibility
                db_user.theme_preference = theme_data['mode']
                changes.append(f"theme.mode -> {theme_data['mode']}")

            if 'primary_color' in theme_data:
                prefs['primary_color'] = theme_data['primary_color']
                changes.append(f"theme.primary_color -> {theme_data['primary_color']}")

            if 'sidebar_style' in theme_data:
                prefs['sidebar_style'] = theme_data['sidebar_style']
                changes.append(f"theme.sidebar_style -> {theme_data['sidebar_style']}")

        # Update layout preferences
        if 'layout' in data:
            layout_data = data['layout']

            if 'default_homepage' in layout_data:
                prefs['default_homepage'] = layout_data['default_homepage']
                changes.append(f"layout.default_homepage -> {layout_data['default_homepage']}")

            if 'default_ticket_view' in layout_data:
                prefs['default_ticket_view'] = layout_data['default_ticket_view']
                changes.append(f"layout.default_ticket_view -> {layout_data['default_ticket_view']}")

            if 'default_inventory_view' in layout_data:
                prefs['default_inventory_view'] = layout_data['default_inventory_view']
                changes.append(f"layout.default_inventory_view -> {layout_data['default_inventory_view']}")

            if 'sidebar_collapsed' in layout_data:
                prefs['sidebar_collapsed'] = layout_data['sidebar_collapsed']
                changes.append(f"layout.sidebar_collapsed -> {layout_data['sidebar_collapsed']}")

            if 'compact_mode' in layout_data:
                prefs['compact_mode'] = layout_data['compact_mode']
                changes.append(f"layout.compact_mode -> {layout_data['compact_mode']}")

        # Update notification preferences
        if 'notifications' in data:
            notification_data = data['notifications']

            if 'email_enabled' in notification_data:
                prefs['email_enabled'] = notification_data['email_enabled']
                changes.append(f"notifications.email_enabled -> {notification_data['email_enabled']}")

            if 'in_app_enabled' in notification_data:
                prefs['in_app_enabled'] = notification_data['in_app_enabled']
                changes.append(f"notifications.in_app_enabled -> {notification_data['in_app_enabled']}")

            if 'sound_enabled' in notification_data:
                prefs['sound_enabled'] = notification_data['sound_enabled']
                changes.append(f"notifications.sound_enabled -> {notification_data['sound_enabled']}")

        # Assign updated preferences back to user
        db_user.preferences = prefs

        # Flag the preferences field as modified to ensure SQLAlchemy detects the change
        flag_modified(db_user, 'preferences')

        db_session.commit()

        # Get updated preferences
        updated_preferences = get_user_preferences(db_user)

        logger.info(f'User {user.username} updated preferences: {"; ".join(changes)}')

        return api_response(
            data=updated_preferences,
            message='Preferences updated successfully'
        )

    except Exception as e:
        db_session.rollback()
        logger.error(f'Error updating preferences for user {user.username}: {str(e)}')
        return api_error(
            ErrorCodes.DATABASE_ERROR,
            f'Failed to update preferences: {str(e)}',
            status_code=500
        )

    finally:
        db_session.close()


@api_v2_bp.route('/user/preferences/options', methods=['GET'])
@dual_auth_required
@handle_exceptions
def get_preference_options():
    """
    Get available theme and layout options

    GET /api/v2/user/preferences/options

    Returns:
        {
            "success": true,
            "data": {
                "theme_modes": ["light", "dark", "auto"],
                "primary_colors": [
                    {"name": "Blue", "value": "#1976D2"},
                    ...
                ],
                "sidebar_styles": ["expanded", "compact", "hidden"],
                "homepage_options": ["dashboard", "tickets", "inventory"],
                "view_options": ["classic", "sf"]
            }
        }
    """
    user = request.current_api_user

    if not user:
        return api_error(
            ErrorCodes.AUTHENTICATION_REQUIRED,
            'Authentication required',
            status_code=401
        )

    options = {
        'theme_modes': THEME_MODES,
        'primary_colors': PRIMARY_COLORS,
        'sidebar_styles': SIDEBAR_STYLES,
        'homepage_options': HOMEPAGE_OPTIONS,
        'view_options': VIEW_OPTIONS
    }

    logger.info(f'User {user.username} retrieved preference options')

    return api_response(
        data=options,
        message='Preference options retrieved successfully'
    )
