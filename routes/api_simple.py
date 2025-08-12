"""
Simple API Routes for Mobile App Integration
"""

from flask import Blueprint, request, jsonify, g
from datetime import datetime, timedelta
from utils.api_auth import require_api_key, create_success_response, create_error_response
from utils.store_instances import ticket_store, user_store, inventory_store
from werkzeug.security import check_password_hash
import jwt
import os

# Create API blueprint
api_bp = Blueprint('api', __name__, url_prefix='/api/v1')

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
        
        # Find user by username or email
        user = None
        all_users = user_store.get_all_users()
        
        for u in all_users:
            if (hasattr(u, 'username') and u.username == username_or_email) or \
               (hasattr(u, 'email') and u.email == username_or_email):
                user = u
                break
        
        if not user:
            response, status_code = create_error_response(
                "INVALID_CREDENTIALS",
                "Invalid username/email or password",
                401
            )
            return jsonify(response), status_code
        
        # Check password
        if not hasattr(user, 'password_hash') or not user.password_hash:
            response, status_code = create_error_response(
                "INVALID_CREDENTIALS",
                "Invalid username/email or password",
                401
            )
            return jsonify(response), status_code
        
        if not check_password_hash(user.password_hash, password):
            response, status_code = create_error_response(
                "INVALID_CREDENTIALS",
                "Invalid username/email or password",
                401
            )
            return jsonify(response), status_code
        
        # Generate JWT token
        secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key')
        payload = {
            'user_id': user.id,
            'username': user.username if hasattr(user, 'username') else user.email,
            'user_type': user.user_type.value if hasattr(user, 'user_type') and user.user_type else 'USER',
            'exp': datetime.utcnow() + timedelta(hours=24),  # Token expires in 24 hours
            'iat': datetime.utcnow()
        }
        
        token = jwt.encode(payload, secret_key, algorithm='HS256')
        
        # Return success response
        user_data = {
            'id': user.id,
            'username': user.username if hasattr(user, 'username') else None,
            'email': user.email if hasattr(user, 'email') else None,
            'user_type': user.user_type.value if hasattr(user, 'user_type') and user.user_type else 'USER',
            'token': token,
            'expires_at': (datetime.utcnow() + timedelta(hours=24)).isoformat()
        }
        
        return jsonify(create_success_response(
            user_data,
            "Login successful"
        ))
        
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
        
        # Get tickets from store
        all_tickets = ticket_store.get_all_tickets()
        
        # Simple pagination
        start = (page - 1) * per_page
        end = start + per_page
        tickets = all_tickets[start:end]
        
        # Convert to API format
        tickets_data = []
        for ticket in tickets:
            ticket_data = {
                'id': ticket.id,
                'subject': ticket.subject,
                'description': ticket.description,
                'status': ticket.status.value if hasattr(ticket.status, 'value') else str(ticket.status),
                'priority': ticket.priority.name if ticket.priority else None,
                'created_at': ticket.created_at.isoformat() if ticket.created_at else None,
                'updated_at': ticket.updated_at.isoformat() if ticket.updated_at else None
            }
            tickets_data.append(ticket_data)
        
        pagination = {
            'page': page,
            'per_page': per_page,
            'total': len(all_tickets),
            'has_next': end < len(all_tickets),
            'has_prev': page > 1
        }
        
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
        ticket = ticket_store.get_ticket_by_id(ticket_id)
        
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
            'priority': ticket.priority.name if ticket.priority else None,
            'category': ticket.category.name if ticket.category else None,
            'created_at': ticket.created_at.isoformat() if ticket.created_at else None,
            'updated_at': ticket.updated_at.isoformat() if ticket.updated_at else None
        }
        
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
        
        # Get users from store
        all_users = user_store.get_all_users()
        
        # Simple pagination
        start = (page - 1) * per_page
        end = start + per_page
        users = all_users[start:end]
        
        users_data = []
        for user in users:
            user_data = {
                'id': user.id,
                'name': user.name if hasattr(user, 'name') else user.username,
                'email': user.email,
                'user_type': user.user_type.value if user.user_type else None,
                'created_at': user.created_at.isoformat() if user.created_at else None
            }
            users_data.append(user_data)
        
        pagination = {
            'page': page,
            'per_page': per_page,
            'total': len(all_users),
            'has_next': end < len(all_users),
            'has_prev': page > 1
        }
        
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
        
        # Get inventory from store
        all_inventory = inventory_store.get_all_assets()
        
        # Simple pagination
        start = (page - 1) * per_page
        end = start + per_page
        inventory = all_inventory[start:end]
        
        inventory_data = []
        for item in inventory:
            item_data = {
                'id': item.id,
                'name': item.name if hasattr(item, 'name') else None,
                'asset_tag': item.asset_tag if hasattr(item, 'asset_tag') else None,
                'serial_number': item.serial_number if hasattr(item, 'serial_number') else None,
                'model': item.model if hasattr(item, 'model') else None,
                'status': item.status.value if hasattr(item, 'status') and hasattr(item.status, 'value') else str(item.status) if hasattr(item, 'status') else None,
                'location': item.location if hasattr(item, 'location') else None,
                'created_at': item.created_at.isoformat() if hasattr(item, 'created_at') and item.created_at else None
            }
            inventory_data.append(item_data)
        
        pagination = {
            'page': page,
            'per_page': per_page,
            'total': len(all_inventory),
            'has_next': end < len(all_inventory),
            'has_prev': page > 1
        }
        
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
        item = inventory_store.get_asset_by_id(item_id)
        
        if not item:
            response, status_code = create_error_response(
                "RESOURCE_NOT_FOUND",
                f"Inventory item with ID {item_id} not found",
                404
            )
            return jsonify(response), status_code
        
        item_data = {
            'id': item.id,
            'name': item.name if hasattr(item, 'name') else None,
            'asset_tag': item.asset_tag if hasattr(item, 'asset_tag') else None,
            'serial_number': item.serial_number if hasattr(item, 'serial_number') else None,
            'model': item.model if hasattr(item, 'model') else None,
            'status': item.status.value if hasattr(item, 'status') and hasattr(item.status, 'value') else str(item.status) if hasattr(item, 'status') else None,
            'location': item.location if hasattr(item, 'location') else None,
            'description': item.description if hasattr(item, 'description') else None,
            'purchase_date': item.purchase_date.isoformat() if hasattr(item, 'purchase_date') and item.purchase_date else None,
            'warranty_expiry': item.warranty_expiry.isoformat() if hasattr(item, 'warranty_expiry') and item.warranty_expiry else None,
            'created_at': item.created_at.isoformat() if hasattr(item, 'created_at') and item.created_at else None,
            'updated_at': item.updated_at.isoformat() if hasattr(item, 'updated_at') and item.updated_at else None
        }
        
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