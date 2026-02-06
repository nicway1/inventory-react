"""
API v2 Blueprint - React Migration API Layer

This module provides a standardized v2 API for the React frontend migration.
All endpoints follow consistent patterns for:
- Response formatting
- Error handling
- Pagination
- Sorting
- Authentication

Blueprint Registration:
    from routes.api_v2 import api_v2_bp
    app.register_blueprint(api_v2_bp)

Base URL: /api/v2

Authentication:
    All endpoints (except health check) require authentication via:
    - Bearer token in Authorization header: `Authorization: Bearer <token>`
    - OR API key in X-API-Key header: `X-API-Key: <key>`

Response Format:
    Success: {
        "success": true,
        "data": <payload>,
        "message": "Optional success message",
        "meta": {
            "pagination": {...},  # If paginated
            "request_id": "...",
            "timestamp": "..."
        }
    }

    Error: {
        "success": false,
        "error": {
            "code": "ERROR_CODE",
            "message": "Human readable message",
            "details": {...}  # Optional additional context
        }
    }
"""

from flask import Blueprint

# Create the v2 API blueprint
api_v2_bp = Blueprint('api_v2', __name__, url_prefix='/api/v2')

# Import utilities for use by endpoint modules
from .utils import (
    # Response helpers
    api_response,
    api_error,
    api_created,
    api_no_content,

    # Pagination helpers
    paginate_query,
    get_pagination_params,

    # Sorting helpers
    apply_sorting,
    get_sorting_params,

    # Validation helpers
    validate_required_fields,
    validate_json_body,

    # Filter helpers
    get_filter_param,
    get_date_filter,
    get_list_filter,

    # Serialization helpers
    serialize_datetime,
    safe_int,
    safe_str,
    safe_bool,
    safe_float,

    # Common formatters
    format_user_summary,
    format_company_summary,
    format_location_summary,

    # Search helpers
    get_search_term,
    apply_search_filter,

    # Resource helpers
    get_or_404,

    # Error codes
    ErrorCodes,

    # Decorators
    handle_exceptions,
    dual_auth_required,
    require_permission,
)

# Health check endpoint (no auth required)
@api_v2_bp.route('/health', methods=['GET'])
def health_check():
    """
    API v2 Health Check

    GET /api/v2/health

    Returns: {
        "success": true,
        "data": {
            "status": "healthy",
            "version": "2.0.0",
            "timestamp": "..."
        }
    }
    """
    from datetime import datetime

    return api_response(
        data={
            'status': 'healthy',
            'version': '2.0.0',
            'api_version': 'v2',
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        },
        message='API v2 is operational'
    )


# =============================================================================
# ENDPOINT REGISTRATION
# =============================================================================
# Import and register endpoint modules here as they are created.
# Each module should define its routes using the api_v2_bp blueprint.
#
# Current registered modules:
# - admin: User, Company, Queue, and TicketCategory management endpoints
# - customers: Customer management endpoints (CRUD)
# - attachments: Ticket attachment file upload endpoints
# - assets: Asset CRUD endpoints (create, update, delete, image upload)
# - accessories: Accessory CRUD endpoints (create, update, delete, return)
# - tickets: Ticket operations (create, update, assign, status change)
# - service_records: Service record CRUD for tickets
# - system_settings: System settings and issue type management endpoints
# - user_preferences: User theme and layout preferences endpoints
# - dashboard: Dashboard widget listing and data endpoints
# - reports: Report templates listing and report generation endpoints
# =============================================================================

# Import admin endpoints (registers routes with api_v2_bp)
from . import admin

# Import customer management endpoints
from . import customers

# Import ticket attachment endpoints
from . import attachments

# Import asset CRUD endpoints
from . import assets

# Import accessory CRUD endpoints
from . import accessories

# Import ticket endpoints (create, update, assign, status)
from . import tickets

# Import service record endpoints (CRUD for ticket service records)
from . import service_records

# Import API key management endpoints (CRUD for API keys)
from . import api_keys

# Import system settings endpoints (CRUD for system settings and issue types)
from . import system_settings

# Import user preferences endpoints (theme and layout settings)
from . import user_preferences

# Import dashboard widget endpoints (list widgets, get widget data)
from . import dashboard

# Import report template and generation endpoints
from . import reports


# Error handlers for the v2 API blueprint
@api_v2_bp.errorhandler(404)
def handle_404(error):
    """Handle 404 Not Found errors"""
    return api_error(
        code=ErrorCodes.ENDPOINT_NOT_FOUND,
        message='The requested API endpoint was not found',
        status_code=404
    )


@api_v2_bp.errorhandler(405)
def handle_405(error):
    """Handle 405 Method Not Allowed errors"""
    return api_error(
        code=ErrorCodes.METHOD_NOT_ALLOWED,
        message='The HTTP method is not allowed for this endpoint',
        status_code=405
    )


@api_v2_bp.errorhandler(500)
def handle_500(error):
    """Handle 500 Internal Server errors"""
    return api_error(
        code=ErrorCodes.INTERNAL_ERROR,
        message='An internal server error occurred',
        status_code=500
    )
