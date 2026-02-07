"""
API v2 Authentication Endpoints

Provides authentication endpoints for the React frontend:
- Login with username/password
- Logout
- Token refresh
- Get current user

All endpoints return standardized JSON responses.
"""

from flask import request
from flask_login import login_user, logout_user, current_user
from datetime import datetime, timedelta
import jwt
import logging

from routes.api_v2 import api_v2_bp
from routes.api_v2.utils import (
    api_response,
    api_error,
    handle_exceptions,
    validate_json_body,
    validate_required_fields,
    ErrorCodes,
)
from models.user import User, UserType
from utils.db_manager import DatabaseManager
from utils.timezone_utils import singapore_now_as_utc

logger = logging.getLogger(__name__)
db_manager = DatabaseManager()


def create_jwt_token(user, remember_me=False):
    """Create JWT token for API authentication"""
    from flask import current_app

    # Token expiry: 30 days if remember_me, otherwise 24 hours
    expiry_days = 30 if remember_me else 1

    payload = {
        'user_id': user.id,
        'username': user.username,
        'user_type': user.user_type.value,
        'exp': datetime.utcnow() + timedelta(days=expiry_days),
        'iat': datetime.utcnow()
    }

    secret_key = current_app.config.get('SECRET_KEY', 'fallback-secret-key')
    return jwt.encode(payload, secret_key, algorithm='HS256')


def format_user_response(user):
    """Format user object for API response"""
    # Get user permissions
    permissions = []
    if user.permissions:
        permission_fields = [attr for attr in dir(user.permissions) if attr.startswith('can_')]
        permissions = [field for field in permission_fields if getattr(user.permissions, field, False)]

    return {
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'first_name': user.first_name or '',
        'last_name': user.last_name or '',
        'user_type': user.user_type.value,
        'company_id': user.company_id,
        'company_name': user.company.name if user.company else None,
        'is_admin': user.is_admin,
        'is_supervisor': user.is_supervisor,
        'permissions': permissions,
        'theme_preference': user.theme_preference or 'light',
    }


@api_v2_bp.route('/auth/login', methods=['POST'])
@handle_exceptions
def api_login():
    """
    Login with username and password

    POST /api/v2/auth/login

    Request Body:
    {
        "username": "string (required)",
        "password": "string (required)",
        "remember_me": "boolean (optional, default: false)"
    }

    Response:
    {
        "success": true,
        "data": {
            "token": "jwt_token",
            "user": {
                "id": 1,
                "username": "admin",
                "email": "admin@example.com",
                "first_name": "Admin",
                "last_name": "User",
                "user_type": "SUPER_ADMIN",
                "company_id": 1,
                "permissions": ["can_view_tickets", "can_edit_tickets", ...]
            },
            "expires_at": "2024-02-07T12:00:00Z"
        }
    }
    """
    data = validate_json_body()
    validate_required_fields(data, ['username', 'password'])

    username = data['username'].strip()
    password = data['password']
    remember_me = data.get('remember_me', False)

    if not username or not password:
        return api_error(
            code=ErrorCodes.VALIDATION_ERROR,
            message='Username and password are required',
            status_code=400
        )

    db_session = db_manager.get_session()
    try:
        # Find user by username (case-insensitive)
        user = db_session.query(User).filter(
            User.username.ilike(username)
        ).first()

        if not user:
            return api_error(
                code=ErrorCodes.UNAUTHORIZED,
                message='Invalid username or password',
                status_code=401
            )

        if not user.check_password(password):
            return api_error(
                code=ErrorCodes.UNAUTHORIZED,
                message='Invalid username or password',
                status_code=401
            )

        # Check if user is active (if such field exists)
        if hasattr(user, 'is_active') and not user.is_active:
            return api_error(
                code=ErrorCodes.FORBIDDEN,
                message='Account is disabled. Please contact administrator.',
                status_code=403
            )

        # Create JWT token
        token = create_jwt_token(user, remember_me)

        # Calculate expiry
        expiry_days = 30 if remember_me else 1
        expires_at = datetime.utcnow() + timedelta(days=expiry_days)

        # Update last login time
        user.last_login = singapore_now_as_utc()
        db_session.commit()

        # Log successful login
        logger.info(f"API login successful for user: {username}")

        return api_response(
            data={
                'token': token,
                'user': format_user_response(user),
                'expires_at': expires_at.isoformat() + 'Z'
            },
            message='Login successful'
        )

    except Exception as e:
        db_session.rollback()
        logger.error(f"Login error: {str(e)}")
        raise
    finally:
        db_session.close()


@api_v2_bp.route('/auth/logout', methods=['POST'])
@handle_exceptions
def api_logout():
    """
    Logout current user

    POST /api/v2/auth/logout

    Response:
    {
        "success": true,
        "message": "Logged out successfully"
    }

    Note: Client should discard the JWT token after logout.
    """
    # For JWT-based auth, logout is handled client-side by discarding the token
    # We can optionally invalidate the token server-side if we implement a token blacklist

    logout_user()

    return api_response(
        data=None,
        message='Logged out successfully'
    )


@api_v2_bp.route('/auth/refresh', methods=['POST'])
@handle_exceptions
def api_refresh_token():
    """
    Refresh JWT token

    POST /api/v2/auth/refresh

    Headers:
        Authorization: Bearer <current_token>

    Response:
    {
        "success": true,
        "data": {
            "token": "new_jwt_token",
            "expires_at": "2024-02-07T12:00:00Z"
        }
    }
    """
    from flask import current_app

    # Get current token from header
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return api_error(
            code=ErrorCodes.UNAUTHORIZED,
            message='Authorization token required',
            status_code=401
        )

    token = auth_header.split(' ')[1]

    try:
        secret_key = current_app.config.get('SECRET_KEY', 'fallback-secret-key')
        payload = jwt.decode(token, secret_key, algorithms=['HS256'])
        user_id = payload['user_id']

        # Get user from database
        db_session = db_manager.get_session()
        try:
            user = db_session.query(User).filter(User.id == user_id).first()

            if not user:
                return api_error(
                    code=ErrorCodes.UNAUTHORIZED,
                    message='User not found',
                    status_code=401
                )

            # Create new token (default 24 hours)
            new_token = create_jwt_token(user, remember_me=False)
            expires_at = datetime.utcnow() + timedelta(days=1)

            return api_response(
                data={
                    'token': new_token,
                    'expires_at': expires_at.isoformat() + 'Z'
                },
                message='Token refreshed successfully'
            )
        finally:
            db_session.close()

    except jwt.ExpiredSignatureError:
        return api_error(
            code=ErrorCodes.UNAUTHORIZED,
            message='Token has expired. Please login again.',
            status_code=401
        )
    except jwt.InvalidTokenError:
        return api_error(
            code=ErrorCodes.UNAUTHORIZED,
            message='Invalid token',
            status_code=401
        )


@api_v2_bp.route('/auth/me', methods=['GET'])
@handle_exceptions
def api_get_current_user():
    """
    Get current authenticated user

    GET /api/v2/auth/me

    Headers:
        Authorization: Bearer <token>

    Response:
    {
        "success": true,
        "data": {
            "id": 1,
            "username": "admin",
            "email": "admin@example.com",
            "first_name": "Admin",
            "last_name": "User",
            "user_type": "SUPER_ADMIN",
            "company_id": 1,
            "permissions": [...]
        }
    }
    """
    from flask import current_app

    # Get token from header
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return api_error(
            code=ErrorCodes.UNAUTHORIZED,
            message='Authorization token required',
            status_code=401
        )

    token = auth_header.split(' ')[1]

    try:
        secret_key = current_app.config.get('SECRET_KEY', 'fallback-secret-key')
        payload = jwt.decode(token, secret_key, algorithms=['HS256'])
        user_id = payload['user_id']

        # Get user from database
        db_session = db_manager.get_session()
        try:
            from sqlalchemy.orm import joinedload
            user = db_session.query(User).options(
                joinedload(User.company)
            ).filter(User.id == user_id).first()

            if not user:
                return api_error(
                    code=ErrorCodes.UNAUTHORIZED,
                    message='User not found',
                    status_code=401
                )

            return api_response(
                data=format_user_response(user),
                message='User retrieved successfully'
            )
        finally:
            db_session.close()

    except jwt.ExpiredSignatureError:
        return api_error(
            code=ErrorCodes.UNAUTHORIZED,
            message='Token has expired. Please login again.',
            status_code=401
        )
    except jwt.InvalidTokenError:
        return api_error(
            code=ErrorCodes.UNAUTHORIZED,
            message='Invalid token',
            status_code=401
        )
