"""
Simple API Routes for Mobile App Integration
"""

from flask import Blueprint, request, jsonify, g
from datetime import datetime, timedelta
from utils.api_auth import require_api_key, create_success_response, create_error_response
from utils.store_instances import ticket_store, user_store, inventory_store
from utils.db_manager import DatabaseManager
from models.user import User
from models.ticket import Ticket
from models.asset import Asset
from models.comment import Comment
from werkzeug.security import check_password_hash
import jwt
import os
import logging

logger = logging.getLogger(__name__)

# Create API blueprint
api_bp = Blueprint('api', __name__, url_prefix='/api/v1')

# Initialize database manager (same as web interface)
db_manager = DatabaseManager()

@api_bp.route('/health', methods=['GET'])
def health_check():
    """API health check endpoint (no authentication required)"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    })

@api_bp.route('/auth/login', methods=['POST'])
def login():
    """
    User authentication endpoint
    
    Accepts username/email and password, returns JWT token for API access
    """
    try:
        data = request.get_json()
        
        if not data:
            response, status_code = create_error_response(
                "VALIDATION_ERROR",
                "Request body is required",
                400
            )
            return jsonify(response), status_code
        
        # Get credentials
        username_or_email = data.get('username') or data.get('email')
        password = data.get('password')
        
        if not username_or_email or not password:
            response, status_code = create_error_response(
                "VALIDATION_ERROR",
                "Username/email and password are required",
                400,
                {"required_fields": ["username", "password"]}
            )
            return jsonify(response), status_code
        
        # Use the same database manager as web login
        try:
            with db_manager as db:
                # Try to find user by username first
                user = db.get_user_by_username(username_or_email)
                
                # If not found by username, try by email
                if not user:
                    db_session = db_manager.get_session()
                    try:
                        user = db_session.query(User).filter(User.email == username_or_email).first()
                    finally:
                        db_session.close()
                
                # Check if user exists and password is correct
                if not user or not user.check_password(password):
                    response, status_code = create_error_response(
                        "INVALID_CREDENTIALS",
                        "Invalid username/email or password",
                        401
                    )
                    return jsonify(response), status_code
                
                # Generate JWT token (user authentication successful)
                secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key')
                payload = {
                    'user_id': user.id,
                    'username': user.username,
                    'user_type': user.user_type.value if user.user_type else 'USER',
                    'exp': datetime.utcnow() + timedelta(hours=24),  # Token expires in 24 hours
                    'iat': datetime.utcnow()
                }
                
                token = jwt.encode(payload, secret_key, algorithm='HS256')
                
                # Return success response
                user_data = {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'user_type': user.user_type.value if user.user_type else 'USER',
                    'token': token,
                    'expires_at': (datetime.utcnow() + timedelta(hours=24)).isoformat()
                }
                
                return jsonify(create_success_response(
                    user_data,
                    "Login successful"
                ))
                
        except Exception as e:
            logger.error(f"Database error during login: {str(e)}")
            response, status_code = create_error_response(
                "INTERNAL_ERROR",
                "Database error during authentication",
                500
            )
            return jsonify(response), status_code
        
    except Exception as e:
        response, status_code = create_error_response(
            "INTERNAL_ERROR",
            f"Error during authentication: {str(e)}",
            500
        )
        return jsonify(response), status_code

@api_bp.route('/auth/verify', methods=['GET'])
def verify_token():
    """
    Verify JWT token validity
    
    Requires Authorization header with Bearer token
    """
    try:
        auth_header = request.headers.get('Authorization', '')
        
        if not auth_header.startswith('Bearer '):
            response, status_code = create_error_response(
                "MISSING_TOKEN",
                "Authorization header with Bearer token is required",
                401
            )
            return jsonify(response), status_code
        
        token = auth_header[7:]  # Remove 'Bearer ' prefix
        secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key')
        
        try:
            payload = jwt.decode(token, secret_key, algorithms=['HS256'])
            
            # Token is valid, return user info
            user_data = {
                'user_id': payload.get('user_id'),
                'username': payload.get('username'),
                'user_type': payload.get('user_type'),
                'expires_at': datetime.fromtimestamp(payload.get('exp')).isoformat(),
                'valid': True
            }
            
            return jsonify(create_success_response(
                user_data,
                "Token is valid"
            ))
            
        except jwt.ExpiredSignatureError:
            response, status_code = create_error_response(
                "TOKEN_EXPIRED",
                "Token has expired",
                401
            )
            return jsonify(response), status_code
            
        except jwt.InvalidTokenError:
            response, status_code = create_error_response(
                "INVALID_TOKEN",
                "Invalid token",
                401
            )
            return jsonify(response), status_code
        
    except Exception as e:
        response, status_code = create_error_response(
            "INTERNAL_ERROR",
            f"Error verifying token: {str(e)}",
            500
        )
        return jsonify(response), status_code

@api_bp.route('/auth/refresh', methods=['POST'])
def refresh_token():
    """
    Refresh JWT token
    
    Requires valid JWT token in Authorization header
    """
    try:
        auth_header = request.headers.get('Authorization', '')
        
        if not auth_header.startswith('Bearer '):
            response, status_code = create_error_response(
                "MISSING_TOKEN",
                "Authorization header with Bearer token is required",
                401
            )
            return jsonify(response), status_code
        
        token = auth_header[7:]  # Remove 'Bearer ' prefix
        secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key')
        
        try:
            # Decode token (allow expired for refresh)
            payload = jwt.decode(token, secret_key, algorithms=['HS256'], options={"verify_exp": False})
            
            # Check if token is not too old (allow refresh within 7 days of expiration)
            exp_timestamp = payload.get('exp')
            if exp_timestamp:
                exp_date = datetime.fromtimestamp(exp_timestamp)
                if datetime.utcnow() > exp_date + timedelta(days=7):
                    response, status_code = create_error_response(
                        "TOKEN_TOO_OLD",
                        "Token is too old to refresh",
                        401
                    )
                    return jsonify(response), status_code
            
            # Generate new token
            new_payload = {
                'user_id': payload.get('user_id'),
                'username': payload.get('username'),
                'user_type': payload.get('user_type'),
                'exp': datetime.utcnow() + timedelta(hours=24),
                'iat': datetime.utcnow()
            }
            
            new_token = jwt.encode(new_payload, secret_key, algorithm='HS256')
            
            token_data = {
                'token': new_token,
                'expires_at': (datetime.utcnow() + timedelta(hours=24)).isoformat(),
                'user_id': payload.get('user_id'),
                'username': payload.get('username')
            }
            
            return jsonify(create_success_response(
                token_data,
                "Token refreshed successfully"
            ))
            
        except jwt.InvalidTokenError:
            response, status_code = create_error_response(
                "INVALID_TOKEN",
                "Invalid token",
                401
            )
            return jsonify(response), status_code
        
    except Exception as e:
        response, status_code = create_error_response(
            "INTERNAL_ERROR",
            f"Error refreshing token: {str(e)}",
            500
        )
        return jsonify(response), status_code

@api_bp.route('/tickets', methods=['GET'])
@require_api_key(permissions=['tickets:read'])
def list_tickets():
    """List tickets with basic filtering"""
    try:
        # Get query parameters
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 50, type=int), 100)
        
        # Get tickets from database (same as web interface)
        db_session = db_manager.get_session()
        try:
            # Query tickets from database
            query = db_session.query(Ticket).order_by(Ticket.created_at.desc())
            
            # Get total count
            total = query.count()
            
            # Apply pagination
            tickets = query.offset((page - 1) * per_page).limit(per_page).all()
            
            # Convert to API format
            tickets_data = []
            for ticket in tickets:
                ticket_data = {
                    'id': ticket.id,
                    'subject': ticket.subject,
                    'description': ticket.description,
                    'status': ticket.status.value if hasattr(ticket.status, 'value') else str(ticket.status),
                    'priority': ticket.priority.value if hasattr(ticket.priority, 'value') else str(ticket.priority) if ticket.priority else None,
                    'created_at': ticket.created_at.isoformat() if ticket.created_at else None,
                    'updated_at': ticket.updated_at.isoformat() if ticket.updated_at else None
                }
                tickets_data.append(ticket_data)
            
            pagination = {
                'page': page,
                'per_page': per_page,
                'total': total,
                'has_next': (page * per_page) < total,
                'has_prev': page > 1
            }
        finally:
            db_session.close()
        
        return jsonify(create_success_response(
            tickets_data,
            f"Retrieved {len(tickets_data)} tickets",
            {"pagination": pagination}
        ))
        
    except Exception as e:
        response, status_code = create_error_response(
            "INTERNAL_ERROR",
            f"Error retrieving tickets: {str(e)}",
            500
        )
        return jsonify(response), status_code

@api_bp.route('/tickets/<int:ticket_id>', methods=['GET'])
@require_api_key(permissions=['tickets:read'])
def get_ticket(ticket_id):
    """Get detailed information about a specific ticket"""
    try:
        # Get ticket from database (same as web interface)
        db_session = db_manager.get_session()
        try:
            ticket = db_session.query(Ticket).get(ticket_id)
            
            if not ticket:
                response, status_code = create_error_response(
                    "RESOURCE_NOT_FOUND",
                    f"Ticket with ID {ticket_id} not found",
                    404
                )
                return jsonify(response), status_code
            
            ticket_data = {
                'id': ticket.id,
                'subject': ticket.subject,
                'description': ticket.description,
                'status': ticket.status.value if hasattr(ticket.status, 'value') else str(ticket.status),
                'priority': ticket.priority.value if hasattr(ticket.priority, 'value') else str(ticket.priority) if ticket.priority else None,
                'category': ticket.category.value if hasattr(ticket.category, 'value') else str(ticket.category) if ticket.category else None,
                'created_at': ticket.created_at.isoformat() if ticket.created_at else None,
                'updated_at': ticket.updated_at.isoformat() if ticket.updated_at else None
            }
        finally:
            db_session.close()
        
        return jsonify(create_success_response(
            ticket_data,
            f"Retrieved ticket {ticket_id}"
        ))
        
    except Exception as e:
        response, status_code = create_error_response(
            "INTERNAL_ERROR",
            f"Error retrieving ticket: {str(e)}",
            500
        )
        return jsonify(response), status_code

@api_bp.route('/users', methods=['GET'])
@require_api_key(permissions=['users:read'])
def list_users():
    """List users with pagination"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 50, type=int), 100)
        
        # Get users from database (same as web interface)
        db_session = db_manager.get_session()
        try:
            # Query users from database
            query = db_session.query(User).order_by(User.username)
            
            # Get total count
            total = query.count()
            
            # Apply pagination
            users = query.offset((page - 1) * per_page).limit(per_page).all()
            
            users_data = []
            for user in users:
                user_data = {
                    'id': user.id,
                    'name': user.username,  # Use username as name for consistency
                    'email': user.email,
                    'user_type': user.user_type.value if user.user_type else None,
                    'created_at': user.created_at.isoformat() if user.created_at else None
                }
                users_data.append(user_data)
            
            pagination = {
                'page': page,
                'per_page': per_page,
                'total': total,
                'has_next': (page * per_page) < total,
                'has_prev': page > 1
            }
        finally:
            db_session.close()
        
        return jsonify(create_success_response(
            users_data,
            f"Retrieved {len(users_data)} users",
            {"pagination": pagination}
        ))
        
    except Exception as e:
        response, status_code = create_error_response(
            "INTERNAL_ERROR",
            f"Error retrieving users: {str(e)}",
            500
        )
        return jsonify(response), status_code

# Error handlers for the API blueprint
@api_bp.errorhandler(404)
def api_not_found(error):
    response, status_code = create_error_response(
        "ENDPOINT_NOT_FOUND",
        "The requested API endpoint was not found",
        404
    )
    return jsonify(response), status_code

@api_bp.errorhandler(405)
def api_method_not_allowed(error):
    response, status_code = create_error_response(
        "METHOD_NOT_ALLOWED",
        "The HTTP method is not allowed for this endpoint",
        405
    )
    return jsonify(response), status_code

@api_bp.errorhandler(500)
def api_internal_error(error):
    response, status_code = create_error_response(
        "INTERNAL_ERROR",
        "An internal server error occurred",
        500
    )
    return jsonify(response), status_code
@api_bp.route('/auth/permissions', methods=['GET'])
def get_user_permissions():
    """
    Get current user's permissions
    
    Requires JWT token authentication
    Returns the user's permissions and capabilities
    """
    try:
        auth_header = request.headers.get('Authorization', '')
        
        if not auth_header.startswith('Bearer '):
            response, status_code = create_error_response(
                "MISSING_TOKEN",
                "Authorization header with Bearer token is required",
                401
            )
            return jsonify(response), status_code
        
        token = auth_header[7:]  # Remove 'Bearer ' prefix
        secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key')
        
        try:
            payload = jwt.decode(token, secret_key, algorithms=['HS256'])
            user_id = payload.get('user_id')
            user_type = payload.get('user_type', 'USER')
            
            if not user_id:
                response, status_code = create_error_response(
                    "INVALID_TOKEN",
                    "Token does not contain valid user information",
                    401
                )
                return jsonify(response), status_code
            
            # Get user from database to check current permissions
            from database import SessionLocal
            from models.user import User
            from models.permission import Permission
            
            session = SessionLocal()
            try:
                user = session.query(User).get(user_id)
                if not user:
                    response, status_code = create_error_response(
                        "USER_NOT_FOUND",
                        "User not found",
                        404
                    )
                    return jsonify(response), status_code
                
                # Get user permissions based on user type and specific permissions
                permissions = []
                capabilities = {}
                
                # Base permissions by user type
                if user.user_type and hasattr(user.user_type, 'value'):
                    user_type_value = user.user_type.value
                else:
                    user_type_value = str(user.user_type) if user.user_type else 'USER'
                
                # Define permissions based on user type
                if user_type_value in ['SUPER_ADMIN', 'ADMIN']:
                    permissions = [
                        'tickets:read', 'tickets:write', 'tickets:delete',
                        'users:read', 'users:write', 'users:delete',
                        'inventory:read', 'inventory:write', 'inventory:delete',
                        'admin:read', 'admin:write',
                        'reports:read', 'reports:write',
                        'settings:read', 'settings:write'
                    ]
                    capabilities = {
                        'can_create_tickets': True,
                        'can_edit_tickets': True,
                        'can_delete_tickets': True,
                        'can_view_all_tickets': True,
                        'can_manage_users': True,
                        'can_manage_inventory': True,
                        'can_access_admin': True,
                        'can_view_reports': True,
                        'can_manage_settings': True,
                        'can_assign_tickets': True,
                        'can_close_tickets': True
                    }
                elif user_type_value in ['SUPERVISOR', 'MANAGER']:
                    permissions = [
                        'tickets:read', 'tickets:write',
                        'users:read',
                        'inventory:read', 'inventory:write',
                        'reports:read'
                    ]
                    capabilities = {
                        'can_create_tickets': True,
                        'can_edit_tickets': True,
                        'can_delete_tickets': False,
                        'can_view_all_tickets': True,
                        'can_manage_users': False,
                        'can_manage_inventory': True,
                        'can_access_admin': False,
                        'can_view_reports': True,
                        'can_manage_settings': False,
                        'can_assign_tickets': True,
                        'can_close_tickets': True
                    }
                elif user_type_value == 'TECHNICIAN':
                    permissions = [
                        'tickets:read', 'tickets:write',
                        'inventory:read'
                    ]
                    capabilities = {
                        'can_create_tickets': True,
                        'can_edit_tickets': True,
                        'can_delete_tickets': False,
                        'can_view_all_tickets': False,  # Only assigned tickets
                        'can_manage_users': False,
                        'can_manage_inventory': False,
                        'can_access_admin': False,
                        'can_view_reports': False,
                        'can_manage_settings': False,
                        'can_assign_tickets': False,
                        'can_close_tickets': True
                    }
                else:  # Regular USER or unknown type
                    permissions = [
                        'tickets:read'
                    ]
                    capabilities = {
                        'can_create_tickets': True,
                        'can_edit_tickets': False,
                        'can_delete_tickets': False,
                        'can_view_all_tickets': False,
                        'can_manage_users': False,
                        'can_manage_inventory': False,
                        'can_access_admin': False,
                        'can_view_reports': False,
                        'can_manage_settings': False,
                        'can_assign_tickets': False,
                        'can_close_tickets': False
                    }
                
                # Get any specific permissions from the database
                try:
                    user_permissions = session.query(Permission).filter_by(user_id=user_id).all()
                    for perm in user_permissions:
                        if hasattr(perm, 'permission_name') and perm.permission_name:
                            permissions.append(perm.permission_name)
                except Exception as e:
                    # If permission table doesn't exist or has issues, continue with base permissions
                    pass
                
                # Remove duplicates and sort
                permissions = sorted(list(set(permissions)))
                
                # Prepare response data
                permission_data = {
                    'user_id': user_id,
                    'username': user.username if hasattr(user, 'username') else None,
                    'user_type': user_type_value,
                    'permissions': permissions,
                    'capabilities': capabilities,
                    'company_id': user.company_id if hasattr(user, 'company_id') else None,
                    'assigned_country': user.assigned_country.value if hasattr(user, 'assigned_country') and user.assigned_country else None
                }
                
                return jsonify(create_success_response(
                    permission_data,
                    "User permissions retrieved successfully"
                ))
                
            finally:
                session.close()
            
        except jwt.ExpiredSignatureError:
            response, status_code = create_error_response(
                "TOKEN_EXPIRED",
                "Token has expired",
                401
            )
            return jsonify(response), status_code
            
        except jwt.InvalidTokenError:
            response, status_code = create_error_response(
                "INVALID_TOKEN",
                "Invalid token",
                401
            )
            return jsonify(response), status_code
        
    except Exception as e:
        response, status_code = create_error_response(
            "INTERNAL_ERROR",
            f"Error retrieving user permissions: {str(e)}",
            500
        )
        return jsonify(response), status_code

@api_bp.route('/auth/profile', methods=['GET'])
def get_user_profile():
    """
    Get current user's profile information
    
    Requires JWT token authentication
    Returns detailed user profile including permissions
    """
    try:
        auth_header = request.headers.get('Authorization', '')
        
        if not auth_header.startswith('Bearer '):
            response, status_code = create_error_response(
                "MISSING_TOKEN",
                "Authorization header with Bearer token is required",
                401
            )
            return jsonify(response), status_code
        
        token = auth_header[7:]  # Remove 'Bearer ' prefix
        secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key')
        
        try:
            payload = jwt.decode(token, secret_key, algorithms=['HS256'])
            user_id = payload.get('user_id')
            
            if not user_id:
                response, status_code = create_error_response(
                    "INVALID_TOKEN",
                    "Token does not contain valid user information",
                    401
                )
                return jsonify(response), status_code
            
            # Get user from database
            from database import SessionLocal
            from models.user import User
            
            session = SessionLocal()
            try:
                user = session.query(User).get(user_id)
                if not user:
                    response, status_code = create_error_response(
                        "USER_NOT_FOUND",
                        "User not found",
                        404
                    )
                    return jsonify(response), status_code
                
                # Prepare profile data
                profile_data = {
                    'id': user.id,
                    'username': user.username if hasattr(user, 'username') else None,
                    'email': user.email if hasattr(user, 'email') else None,
                    'user_type': user.user_type.value if hasattr(user, 'user_type') and user.user_type else 'USER',
                    'company_id': user.company_id if hasattr(user, 'company_id') else None,
                    'company_name': user.company.name if hasattr(user, 'company') and user.company else None,
                    'assigned_country': user.assigned_country.value if hasattr(user, 'assigned_country') and user.assigned_country else None,
                    'role': user.role if hasattr(user, 'role') else None,
                    'theme_preference': user.theme_preference if hasattr(user, 'theme_preference') else 'light',
                    'created_at': user.created_at.isoformat() if hasattr(user, 'created_at') and user.created_at else None,
                    'last_login': user.last_login.isoformat() if hasattr(user, 'last_login') and user.last_login else None
                }
                
                return jsonify(create_success_response(
                    profile_data,
                    "User profile retrieved successfully"
                ))
                
            finally:
                session.close()
            
        except jwt.ExpiredSignatureError:
            response, status_code = create_error_response(
                "TOKEN_EXPIRED",
                "Token has expired",
                401
            )
            return jsonify(response), status_code
            
        except jwt.InvalidTokenError:
            response, status_code = create_error_response(
                "INVALID_TOKEN",
                "Invalid token",
                401
            )
            return jsonify(response), status_code
        
    except Exception as e:
        response, status_code = create_error_response(
            "INTERNAL_ERROR",
            f"Error retrieving user profile: {str(e)}",
            500
        )
        return jsonify(response), status_code

@api_bp.route('/inventory', methods=['GET'])
@require_api_key(permissions=['inventory:read'])
def list_inventory():
    """List inventory items with pagination"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 50, type=int), 100)
        
        # Get inventory from database (same as web interface)
        db_session = db_manager.get_session()
        try:
            # Query assets from database
            query = db_session.query(Asset).order_by(Asset.created_at.desc())
            
            # Get total count
            total = query.count()
            
            # Apply pagination
            assets = query.offset((page - 1) * per_page).limit(per_page).all()
            
            inventory_data = []
            for asset in assets:
                try:
                    item_data = {
                        'id': asset.id,
                        'name': asset.name,
                        'asset_tag': asset.asset_tag,
                        'serial_number': asset.serial_num,
                        'model': asset.model,
                        'status': asset.status.value if hasattr(asset.status, 'value') else str(asset.status) if asset.status else 'Unknown',
                        'location_id': getattr(asset, 'location_id', None),
                        'created_at': asset.created_at.isoformat() if asset.created_at else None
                    }
                    inventory_data.append(item_data)
                except Exception as e:
                    # Skip items that cause errors but log them
                    logger.error(f"Error serializing inventory item {asset.id}: {e}")
                    continue
            
            pagination = {
                'page': page,
                'per_page': per_page,
                'total': total,
                'has_next': (page * per_page) < total,
                'has_prev': page > 1
            }
        finally:
            db_session.close()
        
        return jsonify(create_success_response(
            inventory_data,
            f"Retrieved {len(inventory_data)} inventory items",
            {"pagination": pagination}
        ))
        
    except Exception as e:
        response, status_code = create_error_response(
            "INTERNAL_ERROR",
            f"Error retrieving inventory: {str(e)}",
            500
        )
        return jsonify(response), status_code

@api_bp.route('/inventory/<int:item_id>', methods=['GET'])
@require_api_key(permissions=['inventory:read'])
def get_inventory_item(item_id):
    """Get detailed information about a specific inventory item"""
    try:
        # Get inventory item from database (same as web interface)
        db_session = db_manager.get_session()
        try:
            item = db_session.query(Asset).get(item_id)
            
            if not item:
                response, status_code = create_error_response(
                    "RESOURCE_NOT_FOUND",
                    f"Inventory item with ID {item_id} not found",
                    404
                )
                return jsonify(response), status_code
            
            item_data = {
                'id': item.id,
                'name': item.name,
                'asset_tag': item.asset_tag,
                'serial_number': item.serial_num,
                'model': item.model,
                'status': item.status.value if hasattr(item.status, 'value') else str(item.status) if item.status else 'Unknown',
                'location_id': getattr(item, 'location_id', None),
                'description': getattr(item, 'description', None),
                'cost_price': getattr(item, 'cost_price', None),
                'manufacturer': getattr(item, 'manufacturer', None),
                'created_at': item.created_at.isoformat() if item.created_at else None,
                'updated_at': item.updated_at.isoformat() if item.updated_at else None
            }
        finally:
            db_session.close()
        
        return jsonify(create_success_response(
            item_data,
            f"Retrieved inventory item {item_id}"
        ))
        
    except Exception as e:
        response, status_code = create_error_response(
            "INTERNAL_ERROR",
            f"Error retrieving inventory item: {str(e)}",
            500
        )
        return jsonify(response), status_code

# Comment Endpoints

@api_bp.route('/tickets/<int:ticket_id>/comments', methods=['GET'])
@require_api_key(permissions=['tickets:read'])
def get_ticket_comments(ticket_id):
    """Get all comments for a specific ticket"""
    try:
        # Get pagination parameters (match iOS app expectations)
        page = request.args.get('page', 1, type=int)
        limit = request.args.get('limit', 20, type=int)
        per_page = min(limit, 100)  # Cap at 100 for performance
        
        # Get database session
        from database import SessionLocal
        db_session = SessionLocal()
        
        try:
            # Get the ticket first to ensure it exists
            ticket = db_session.query(Ticket).get(ticket_id)
            if not ticket:
                return jsonify({
                    "success": False,
                    "message": "Ticket not found"
                }), 404
            
            # Get paginated comments ordered by creation date (oldest first)
            comments_query = db_session.query(Comment).filter_by(ticket_id=ticket_id).order_by(Comment.created_at.asc())
            comments_paginated = comments_query.paginate(
                page=page,
                per_page=per_page,
                error_out=False
            )
        
            # Format comments data to match iOS app expectations
            comments_data = []
            for comment in comments_paginated.items:
                comment_data = {
                    'id': comment.id,
                    'ticket_id': ticket_id,
                    'content': comment.content,
                    'author_name': comment.user.username if comment.user else None,
                    'author_id': comment.user_id,
                    'created_at': comment.created_at.isoformat() + 'Z' if comment.created_at else None,
                    'updated_at': comment.updated_at.isoformat() + 'Z' if comment.updated_at else None
                }
                comments_data.append(comment_data)
            
            # Create response matching iOS app expectations
            response = {
                "data": comments_data,
                "meta": {
                    "pagination": {
                        "page": comments_paginated.page,
                        "per_page": comments_paginated.per_page,
                        "total": comments_paginated.total,
                        "has_next": comments_paginated.has_next,
                        "has_prev": comments_paginated.has_prev
                    }
                },
                "success": True,
                "message": "Comments retrieved successfully"
            }
            return jsonify(response), 200
            
        finally:
            db_session.close()
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Error retrieving comments: {str(e)}"
        }), 500

@api_bp.route('/tickets/<int:ticket_id>/comments', methods=['POST'])
@require_api_key(permissions=['tickets:write'])
def create_ticket_comment(ticket_id):
    """Create a new comment on a specific ticket"""
    try:
        # Get request data
        data = request.get_json()
        if not data:
            return jsonify({
                "success": False,
                "message": "No JSON data provided"
            }), 400
        
        # Validate required fields
        content = data.get('content', '').strip()
        user_id = data.get('user_id')
        
        if not content:
            return jsonify({
                "success": False,
                "message": "Comment content is required"
            }), 400
        
        if not user_id:
            return jsonify({
                "success": False,
                "message": "User ID is required"
            }), 400
        
        # Get database session
        from database import SessionLocal
        db_session = SessionLocal()
        
        try:
            # Verify ticket exists
            ticket = db_session.query(Ticket).get(ticket_id)
            if not ticket:
                return jsonify({
                    "success": False,
                    "message": "Ticket not found"
                }), 404
            
            # Verify user exists
            user = db_session.query(User).get(user_id)
            if not user:
                return jsonify({
                    "success": False,
                    "message": "User not found"
                }), 404
        
            # Create new comment
            new_comment = Comment(
                ticket_id=ticket_id,
                user_id=user_id,
                content=content,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            # Add to database
            db_session.add(new_comment)
            db_session.commit()
            
            # Format response to match iOS app expectations
            comment_data = {
                'id': new_comment.id,
                'ticket_id': ticket_id,
                'content': new_comment.content,
                'author_name': user.username,
                'author_id': user_id,
                'created_at': new_comment.created_at.isoformat() + 'Z',
                'updated_at': new_comment.updated_at.isoformat() + 'Z'
            }
            
            response = {
                "data": comment_data,
                "success": True,
                "message": "Comment created successfully"
            }
            return jsonify(response), 201
            
        finally:
            db_session.close()
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Error creating comment: {str(e)}"
        }), 500