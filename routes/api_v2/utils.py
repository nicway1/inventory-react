"""
API v2 Utility Functions and Classes

This module provides common utilities for API v2 endpoints including:
- Response formatting helpers
- Pagination utilities
- Sorting utilities
- Validation helpers
- Error code constants
- Common decorators
"""

from flask import jsonify, request
from functools import wraps
from datetime import datetime
import logging
import uuid

logger = logging.getLogger(__name__)


# =============================================================================
# ERROR CODES
# =============================================================================

class ErrorCodes:
    """Standard error codes for API v2 responses"""

    # Authentication errors (401)
    AUTHENTICATION_REQUIRED = 'AUTHENTICATION_REQUIRED'
    INVALID_TOKEN = 'INVALID_TOKEN'
    TOKEN_EXPIRED = 'TOKEN_EXPIRED'

    # Authorization errors (403)
    PERMISSION_DENIED = 'PERMISSION_DENIED'
    INSUFFICIENT_PERMISSIONS = 'INSUFFICIENT_PERMISSIONS'
    ADMIN_ACCESS_REQUIRED = 'ADMIN_ACCESS_REQUIRED'

    # Validation errors (400)
    VALIDATION_ERROR = 'VALIDATION_ERROR'
    MISSING_REQUIRED_FIELD = 'MISSING_REQUIRED_FIELD'
    INVALID_FIELD_VALUE = 'INVALID_FIELD_VALUE'
    INVALID_JSON = 'INVALID_JSON'

    # Resource errors (404, 409)
    RESOURCE_NOT_FOUND = 'RESOURCE_NOT_FOUND'
    RESOURCE_ALREADY_EXISTS = 'RESOURCE_ALREADY_EXISTS'
    RESOURCE_IN_USE = 'RESOURCE_IN_USE'

    # Request errors (405, 415)
    METHOD_NOT_ALLOWED = 'METHOD_NOT_ALLOWED'
    UNSUPPORTED_MEDIA_TYPE = 'UNSUPPORTED_MEDIA_TYPE'
    ENDPOINT_NOT_FOUND = 'ENDPOINT_NOT_FOUND'

    # Server errors (500)
    INTERNAL_ERROR = 'INTERNAL_ERROR'
    DATABASE_ERROR = 'DATABASE_ERROR'


# =============================================================================
# RESPONSE HELPERS
# =============================================================================

def api_response(data=None, message=None, meta=None, status_code=200):
    """
    Create a standardized successful API response

    Args:
        data: The response payload (dict, list, or None)
        message: Optional success message
        meta: Optional metadata (pagination, etc.)
        status_code: HTTP status code (default 200)

    Returns:
        Flask response tuple (response_dict, status_code)
    """
    response = {
        'success': True,
        'data': data
    }

    if message:
        response['message'] = message

    if meta:
        response['meta'] = meta
    else:
        response['meta'] = {
            'request_id': str(uuid.uuid4())[:8],
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        }

    return jsonify(response), status_code


def api_error(code, message, status_code=400, details=None):
    """
    Create a standardized error API response

    Args:
        code: Error code from ErrorCodes class
        message: Human-readable error message
        status_code: HTTP status code
        details: Optional additional error details

    Returns:
        Flask response tuple (response_dict, status_code)
    """
    error = {
        'code': code,
        'message': message
    }

    if details:
        error['details'] = details

    response = {
        'success': False,
        'error': error,
        'meta': {
            'request_id': str(uuid.uuid4())[:8],
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        }
    }

    return jsonify(response), status_code


def api_created(data, message=None, location=None):
    """
    Create a 201 Created response

    Args:
        data: The created resource data
        message: Optional success message
        location: Optional URL of the created resource

    Returns:
        Flask response tuple
    """
    response, _ = api_response(data, message or 'Resource created successfully', status_code=201)

    # Add Location header if provided
    if location:
        response.headers['Location'] = location

    return response, 201


def api_no_content():
    """
    Create a 204 No Content response (typically for successful DELETE)

    Returns:
        Empty response with 204 status
    """
    return '', 204


# =============================================================================
# PAGINATION HELPERS
# =============================================================================

def get_pagination_params(default_page=1, default_per_page=20, max_per_page=100):
    """
    Extract pagination parameters from request query string

    Args:
        default_page: Default page number if not specified
        default_per_page: Default items per page if not specified
        max_per_page: Maximum allowed items per page

    Returns:
        Tuple of (page, per_page)
    """
    page = request.args.get('page', default_page, type=int)
    per_page = request.args.get('per_page', default_per_page, type=int)

    # Ensure valid values
    page = max(1, page)
    per_page = max(1, min(per_page, max_per_page))

    return page, per_page


def paginate_query(query, page=1, per_page=20):
    """
    Paginate a SQLAlchemy query and return items with pagination metadata

    Args:
        query: SQLAlchemy query object
        page: Page number (1-indexed)
        per_page: Items per page

    Returns:
        Tuple of (items_list, pagination_meta)
    """
    # Get total count before pagination
    total_items = query.count()

    # Calculate pagination values
    total_pages = (total_items + per_page - 1) // per_page if total_items > 0 else 0
    has_prev = page > 1
    has_next = page < total_pages

    # Calculate offset and get paginated items
    offset = (page - 1) * per_page
    items = query.offset(offset).limit(per_page).all()

    pagination_meta = {
        'pagination': {
            'page': page,
            'per_page': per_page,
            'total_items': total_items,
            'total_pages': total_pages,
            'has_next': has_next,
            'has_prev': has_prev,
            'next_page': page + 1 if has_next else None,
            'prev_page': page - 1 if has_prev else None
        },
        'request_id': str(uuid.uuid4())[:8],
        'timestamp': datetime.utcnow().isoformat() + 'Z'
    }

    return items, pagination_meta


# =============================================================================
# SORTING HELPERS
# =============================================================================

def get_sorting_params(allowed_fields, default_sort='created_at', default_order='desc'):
    """
    Extract sorting parameters from request query string

    Args:
        allowed_fields: List of field names that can be sorted
        default_sort: Default field to sort by
        default_order: Default sort order ('asc' or 'desc')

    Returns:
        Tuple of (sort_field, sort_order)
    """
    sort_field = request.args.get('sort', default_sort)
    sort_order = request.args.get('order', default_order).lower()

    # Validate sort field
    if sort_field not in allowed_fields:
        sort_field = default_sort

    # Validate sort order
    if sort_order not in ['asc', 'desc']:
        sort_order = default_order

    return sort_field, sort_order


def apply_sorting(query, model, sort_field, sort_order):
    """
    Apply sorting to a SQLAlchemy query

    Args:
        query: SQLAlchemy query object
        model: SQLAlchemy model class
        sort_field: Field name to sort by
        sort_order: 'asc' or 'desc'

    Returns:
        Sorted query object
    """
    if hasattr(model, sort_field):
        column = getattr(model, sort_field)
        if sort_order == 'desc':
            query = query.order_by(column.desc())
        else:
            query = query.order_by(column.asc())

    return query


# =============================================================================
# VALIDATION HELPERS
# =============================================================================

def validate_json_body():
    """
    Validate that request has a JSON body

    Returns:
        Tuple of (data_dict, error_response) - error_response is None if valid
    """
    if not request.is_json:
        return None, api_error(
            ErrorCodes.INVALID_JSON,
            'Request body must be JSON',
            status_code=400
        )

    try:
        data = request.get_json()
        if data is None:
            return None, api_error(
                ErrorCodes.INVALID_JSON,
                'Request body is empty or invalid JSON',
                status_code=400
            )
        return data, None
    except Exception as e:
        return None, api_error(
            ErrorCodes.INVALID_JSON,
            f'Failed to parse JSON: {str(e)}',
            status_code=400
        )


def validate_required_fields(data, required_fields):
    """
    Validate that all required fields are present in data

    Args:
        data: Dictionary to validate
        required_fields: List of required field names

    Returns:
        Tuple of (is_valid, error_response) - error_response is None if valid
    """
    missing_fields = []

    for field in required_fields:
        if field not in data or data[field] is None or data[field] == '':
            missing_fields.append(field)

    if missing_fields:
        return False, api_error(
            ErrorCodes.MISSING_REQUIRED_FIELD,
            f'Missing required fields: {", ".join(missing_fields)}',
            status_code=400,
            details={'missing_fields': missing_fields}
        )

    return True, None


# =============================================================================
# DECORATORS
# =============================================================================

def handle_exceptions(f):
    """
    Decorator to catch and handle exceptions in API endpoints

    Converts unhandled exceptions to standardized error responses
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            logger.exception(f'Unhandled exception in {f.__name__}: {str(e)}')
            return api_error(
                ErrorCodes.INTERNAL_ERROR,
                'An unexpected error occurred',
                status_code=500,
                details={'error': str(e)} if logger.isEnabledFor(logging.DEBUG) else None
            )
    return decorated_function


def dual_auth_required(f):
    """
    Enhanced authentication decorator that supports both:
    1. Mobile JWT authentication (preferred)
    2. JSON API key + JWT authentication (backward compatibility)
    3. Session-based authentication for web users

    Sets request.current_api_user to the authenticated user
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        from sqlalchemy.orm import joinedload
        from utils.db_manager import DatabaseManager
        from models.user import User

        db_manager = DatabaseManager()
        user = None

        # Support for JSON API key system
        JSON_API_KEY = 'xAQhm3__ZH6MvRIPMIBSDRAsIa1w2Slh5uaCtc4NurM'

        # Method 1: Try JSON API key + JWT authentication first
        api_key = request.headers.get('X-API-Key')
        if api_key == JSON_API_KEY:
            auth_header = request.headers.get('Authorization')
            if auth_header and auth_header.startswith('Bearer '):
                token = auth_header.split(' ')[1]
                from routes.json_api import verify_jwt_token
                user_id = verify_jwt_token(token)

                if user_id:
                    db_session = db_manager.get_session()
                    try:
                        user = db_session.query(User).options(
                            joinedload(User.company)
                        ).filter(User.id == user_id).first()
                        if user:
                            _ = user.company  # Force load company
                            logger.info(f"JSON API authentication successful for user: {user.username}")
                    finally:
                        db_session.close()

        # Method 2: Try mobile JWT authentication (no API key needed)
        if not user:
            auth_header = request.headers.get('Authorization')
            if auth_header and auth_header.startswith('Bearer '):
                token = auth_header.split(' ')[1]
                from routes.mobile_api import verify_mobile_token
                user = verify_mobile_token(token)
                if user:
                    logger.info(f"Mobile JWT authentication successful for user: {user.username}")

        # Method 3: Try session-based authentication (for web users)
        if not user:
            from flask import session as flask_session
            from flask_login import current_user
            if current_user and hasattr(current_user, 'is_authenticated') and current_user.is_authenticated:
                user = current_user
                logger.info(f"Session authentication successful for user: {user.username}")

        # If no valid authentication found
        if not user:
            return api_error(
                ErrorCodes.AUTHENTICATION_REQUIRED,
                'Authentication required. Please provide a valid Bearer token or API key.',
                status_code=401
            )

        # Set current user for the request
        request.current_api_user = user
        return f(*args, **kwargs)

    return decorated_function


def require_permission(permission_name):
    """
    Decorator to check for specific permission

    Args:
        permission_name: Name of the permission to check (e.g., 'can_edit_assets')
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user = getattr(request, 'current_api_user', None)
            if not user:
                return api_error(
                    ErrorCodes.AUTHENTICATION_REQUIRED,
                    'Authentication required',
                    status_code=401
                )

            # Check if user has the required permission
            permissions = user.permissions
            if not permissions or not getattr(permissions, permission_name, False):
                return api_error(
                    ErrorCodes.INSUFFICIENT_PERMISSIONS,
                    f'Permission required: {permission_name}',
                    status_code=403
                )

            return f(*args, **kwargs)
        return decorated_function
    return decorator


# =============================================================================
# FILTER HELPERS
# =============================================================================

def get_filter_param(param_name, param_type=str, default=None):
    """
    Get a filter parameter from request args with type conversion.

    Args:
        param_name: Name of the query parameter
        param_type: Expected type (str, int, bool, float)
        default: Default value if parameter not provided

    Returns:
        The parameter value converted to the specified type, or default
    """
    value = request.args.get(param_name)

    if value is None:
        return default

    try:
        if param_type == bool:
            return value.lower() in ('true', '1', 'yes', 'on')
        return param_type(value)
    except (ValueError, TypeError):
        return default


def get_date_filter(param_name, default=None):
    """
    Get a date/datetime filter parameter from request args.
    Supports ISO 8601 format: YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS

    Args:
        param_name: Name of the query parameter
        default: Default value if parameter not provided or invalid

    Returns:
        datetime object or default
    """
    value = request.args.get(param_name)

    if not value:
        return default

    try:
        # Handle 'Z' suffix
        if value.endswith('Z'):
            value = value[:-1]
        return datetime.fromisoformat(value)
    except ValueError:
        return default


def get_list_filter(param_name, separator=','):
    """
    Get a list filter parameter from request args.
    Example: ?status=active,pending -> ['active', 'pending']

    Args:
        param_name: Name of the query parameter
        separator: Character to split on (default: ',')

    Returns:
        List of string values (empty list if parameter not provided)
    """
    value = request.args.get(param_name)

    if not value:
        return []

    return [v.strip() for v in value.split(separator) if v.strip()]


# =============================================================================
# SERIALIZATION HELPERS
# =============================================================================

def serialize_datetime(dt):
    """
    Serialize a datetime to ISO 8601 format with Z suffix.

    Args:
        dt: datetime object

    Returns:
        ISO format string with Z suffix, or None if dt is None
    """
    if dt is None:
        return None
    return dt.isoformat() + 'Z'


def safe_int(value, default=None):
    """
    Safely convert a value to int.

    Args:
        value: Value to convert
        default: Default value if conversion fails

    Returns:
        Integer value or default
    """
    if value is None:
        return default
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def safe_str(value, default=None):
    """
    Safely convert a value to string, stripping whitespace.

    Args:
        value: Value to convert
        default: Default value if conversion fails or result is empty

    Returns:
        String value or default
    """
    if value is None:
        return default
    result = str(value).strip()
    return result if result else default


def safe_bool(value, default=None):
    """
    Safely convert a value to boolean.

    Args:
        value: Value to convert
        default: Default value if conversion fails

    Returns:
        Boolean value or default
    """
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in ('true', '1', 'yes', 'on')
    try:
        return bool(value)
    except (ValueError, TypeError):
        return default


def safe_float(value, default=None):
    """
    Safely convert a value to float.

    Args:
        value: Value to convert
        default: Default value if conversion fails

    Returns:
        Float value or default
    """
    if value is None:
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


# =============================================================================
# COMMON OBJECT FORMATTERS
# =============================================================================

def format_user_summary(user):
    """
    Format a user object to a summary dict for inclusion in responses.

    Args:
        user: User model object

    Returns:
        Dictionary with user summary or None if user is None
    """
    if not user:
        return None

    return {
        'id': user.id,
        'username': user.username,
        'name': getattr(user, 'name', user.username),
        'email': getattr(user, 'email', None)
    }


def format_company_summary(company):
    """
    Format a company object to a summary dict for inclusion in responses.

    Args:
        company: Company model object

    Returns:
        Dictionary with company summary or None if company is None
    """
    if not company:
        return None

    return {
        'id': company.id,
        'name': company.name,
        'display_name': getattr(company, 'effective_display_name', company.name)
    }


def format_location_summary(location):
    """
    Format a location object to a summary dict for inclusion in responses.

    Args:
        location: Location model object

    Returns:
        Dictionary with location summary or None if location is None
    """
    if not location:
        return None

    return {
        'id': location.id,
        'name': location.name,
        'address': getattr(location, 'address', None),
        'city': getattr(location, 'city', None),
        'country': getattr(location, 'country', None)
    }


# =============================================================================
# SEARCH HELPERS
# =============================================================================

def get_search_term():
    """
    Get search term from request args (supports 'q', 'search', 'query' params).

    Returns:
        Search term string or None
    """
    for param in ['q', 'search', 'query']:
        term = request.args.get(param)
        if term:
            return term.strip()
    return None


def apply_search_filter(query, model, search_term, search_fields):
    """
    Apply a search filter to a query across multiple fields.

    Args:
        query: SQLAlchemy query object
        model: SQLAlchemy model class
        search_term: The search term
        search_fields: List of field names to search in

    Returns:
        Query with search filter applied
    """
    from sqlalchemy import or_

    if not search_term or not search_fields:
        return query

    search_pattern = f'%{search_term}%'
    conditions = []

    for field_name in search_fields:
        if hasattr(model, field_name):
            column = getattr(model, field_name)
            conditions.append(column.ilike(search_pattern))

    if conditions:
        query = query.filter(or_(*conditions))

    return query


# =============================================================================
# RESOURCE HELPERS
# =============================================================================

def get_or_404(model, id, error_message=None):
    """
    Get a resource by ID or return 404 error response.

    Args:
        model: SQLAlchemy model class
        id: Resource ID
        error_message: Optional custom error message

    Returns:
        Tuple of (resource, None) if found, or (None, error_response) if not found
    """
    resource = model.query.get(id)

    if not resource:
        model_name = model.__name__
        return None, api_error(
            ErrorCodes.RESOURCE_NOT_FOUND,
            error_message or f'{model_name} with ID {id} not found',
            status_code=404,
            details={'model': model_name, 'id': id}
        )

    return resource, None
