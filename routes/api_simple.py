"""
Simple API Routes for Mobile App Integration
"""

from flask import Blueprint, request, jsonify, g
from datetime import datetime, timedelta
from utils.api_auth import require_api_key, create_success_response, create_error_response
from routes.inventory_api import dual_auth_required
from utils.store_instances import ticket_store, user_store, inventory_store
from utils.db_manager import DatabaseManager
from models.user import User
from models.ticket import Ticket
from models.asset import Asset
from models.accessory import Accessory
from models.comment import Comment
from models.audit_session import AuditSession
from models.user import Country
from models.queue import Queue
from werkzeug.security import check_password_hash
import jwt
import os
import json
import logging

logger = logging.getLogger(__name__)


# Helper function to get full image URL for assets
def get_asset_image_url_simple(asset):
    """Get asset image URL with fallback to default product images"""
    base_url = request.host_url.rstrip('/')

    # If asset has a custom image, use it
    if asset.image_url:
        return f"{base_url}{asset.image_url}"

    # Auto-detect image based on manufacturer/model
    model_lower = (asset.model or '').lower()
    name_lower = (asset.name or '').lower()
    mfg_lower = (getattr(asset, 'manufacturer', '') or '').lower()

    default_image = None

    if 'macbook' in model_lower or 'macbook' in name_lower or mfg_lower == 'apple':
        default_image = '/static/images/products/macbook.png'
    elif 'thinkpad' in model_lower or 'thinkpad' in name_lower or mfg_lower == 'lenovo':
        default_image = '/static/images/products/laptop_lenovo.png'
    elif 'latitude' in model_lower or 'xps' in model_lower or mfg_lower == 'dell':
        default_image = '/static/images/products/laptop_dell.png'
    elif 'elitebook' in model_lower or 'probook' in model_lower or mfg_lower == 'hp':
        default_image = '/static/images/products/laptop_hp.png'
    elif 'surface' in model_lower or mfg_lower == 'microsoft':
        default_image = '/static/images/products/laptop_surface.png'
    elif 'iphone' in model_lower or 'iphone' in name_lower:
        default_image = '/static/images/products/iphone.png'
    elif 'ipad' in model_lower or 'ipad' in name_lower:
        default_image = '/static/images/products/ipad.png'

    if default_image:
        return f"{base_url}{default_image}"

    return None


# Helper function to get full image URL for accessories
def get_accessory_image_url_simple(accessory):
    """Get accessory image URL with fallback to default category images"""
    base_url = request.host_url.rstrip('/')

    # If accessory has a custom image, use it
    if accessory.image_url:
        return f"{base_url}{accessory.image_url}"

    # Auto-detect image based on category
    category_lower = (getattr(accessory, 'category', '') or '').lower()
    name_lower = (accessory.name or '').lower()

    default_image = None

    # Map categories to default images
    if 'keyboard' in category_lower or 'keyboard' in name_lower:
        default_image = '/static/images/products/accessories/keyboard.png'
    elif 'mouse' in category_lower or 'mouse' in name_lower:
        default_image = '/static/images/products/accessories/mouse.png'
    elif 'monitor' in category_lower or 'display' in name_lower:
        default_image = '/static/images/products/accessories/monitor.png'
    elif 'dock' in category_lower or 'docking' in name_lower:
        default_image = '/static/images/products/accessories/docking_station.png'
    elif 'headset' in category_lower or 'headphone' in category_lower or 'headset' in name_lower or 'headphone' in name_lower:
        default_image = '/static/images/products/accessories/headset.png'
    elif 'cable' in category_lower or 'cable' in name_lower:
        default_image = '/static/images/products/accessories/cable.png'
    elif 'charger' in category_lower or 'power' in category_lower or 'adapter' in category_lower or 'charger' in name_lower:
        default_image = '/static/images/products/accessories/charger.png'
    else:
        # Generic accessory image for Other/unknown categories
        default_image = '/static/images/products/accessories/accessory_generic.png'

    if default_image:
        return f"{base_url}{default_image}"

    return None


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

@api_bp.route('/queues', methods=['GET'])
@require_api_key(permissions=['tickets:read'])
def list_queues():
    """
    Get list of all available queues for filtering and display

    Returns:
        List of queues with id, name, and description
    """
    try:
        db_session = db_manager.get_session()
        try:
            queues = db_session.query(Queue).order_by(Queue.name).all()

            queues_data = []
            for queue in queues:
                queue_data = {
                    'id': queue.id,
                    'name': queue.name,
                    'description': queue.description if hasattr(queue, 'description') else None
                }
                queues_data.append(queue_data)

            return jsonify(create_success_response(
                queues_data,
                f"Retrieved {len(queues_data)} queues"
            ))
        finally:
            db_session.close()

    except Exception as e:
        response, status_code = create_error_response(
            "INTERNAL_ERROR",
            f"Error retrieving queues: {str(e)}",
            500
        )
        return jsonify(response), status_code

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
        queue_id = request.args.get('queue_id', type=int)
        status = request.args.get('status')

        # Get tickets from database (same as web interface)
        db_session = db_manager.get_session()
        try:
            # Query tickets from database
            query = db_session.query(Ticket)

            # Apply filters
            if queue_id:
                query = query.filter(Ticket.queue_id == queue_id)

            if status:
                query = query.filter(Ticket.status == status)

            # Order by most recent first
            query = query.order_by(Ticket.created_at.desc())

            # Get total count
            total = query.count()
            
            # Apply pagination
            tickets = query.offset((page - 1) * per_page).limit(per_page).all()
            
            # Convert to API format
            tickets_data = []
            for ticket in tickets:
                # Safely get related object names
                try:
                    category_name = ticket.category.name if hasattr(ticket, 'category') and ticket.category else None
                except:
                    category_name = None

                try:
                    queue_name = ticket.queue.name if hasattr(ticket, 'queue') and ticket.queue else None
                except:
                    queue_name = None

                try:
                    customer_name = ticket.customer_user.name if hasattr(ticket, 'customer_user') and ticket.customer_user else None
                    customer_email = ticket.customer_user.email if hasattr(ticket, 'customer_user') and ticket.customer_user else None
                except:
                    customer_name = None
                    customer_email = None

                try:
                    assigned_name = ticket.assigned_to.name if hasattr(ticket, 'assigned_to') and ticket.assigned_to else None
                except:
                    assigned_name = None

                ticket_data = {
                    'id': ticket.id,
                    'subject': ticket.subject,
                    'description': ticket.description,
                    'status': ticket.status.value if hasattr(ticket.status, 'value') else str(ticket.status),
                    'priority': ticket.priority.value if hasattr(ticket.priority, 'value') else str(ticket.priority) if ticket.priority else None,
                    'category': category_name,
                    'queue_id': getattr(ticket, 'queue_id', None),
                    'queue_name': queue_name,
                    'customer_id': getattr(ticket, 'customer_user_id', None),
                    'customer_name': customer_name,
                    'customer_email': customer_email,
                    'assigned_to_id': getattr(ticket, 'assigned_to_id', None),
                    'assigned_to_name': assigned_name,
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
            
            # Safely get related object names
            try:
                category_name = ticket.category.name if hasattr(ticket, 'category') and ticket.category else None
            except:
                category_name = None

            try:
                queue_name = ticket.queue.name if hasattr(ticket, 'queue') and ticket.queue else None
            except:
                queue_name = None

            try:
                customer_name = ticket.customer_user.name if hasattr(ticket, 'customer_user') and ticket.customer_user else None
                customer_email = ticket.customer_user.email if hasattr(ticket, 'customer_user') and ticket.customer_user else None
                customer_phone = ticket.customer_user.contact_number if hasattr(ticket, 'customer_user') and ticket.customer_user else None
            except:
                customer_name = None
                customer_email = None
                customer_phone = None

            try:
                assigned_name = ticket.assigned_to.name if hasattr(ticket, 'assigned_to') and ticket.assigned_to else None
            except:
                assigned_name = None

            ticket_data = {
                'id': ticket.id,
                'subject': ticket.subject,
                'description': ticket.description,
                'status': ticket.status.value if hasattr(ticket.status, 'value') else str(ticket.status),
                'priority': ticket.priority.value if hasattr(ticket.priority, 'value') else str(ticket.priority) if ticket.priority else None,
                'category': category_name,
                'queue_id': getattr(ticket, 'queue_id', None),
                'queue_name': queue_name,
                'customer_id': getattr(ticket, 'customer_user_id', None),
                'customer_name': customer_name,
                'customer_email': customer_email,
                'customer_phone': customer_phone,
                'assigned_to_id': getattr(ticket, 'assigned_to_id', None),
                'assigned_to_name': assigned_name,
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
                    'assigned_country': user.assigned_country if hasattr(user, 'assigned_country') and user.assigned_country else None
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
                    'assigned_country': user.assigned_country if hasattr(user, 'assigned_country') and user.assigned_country else None,
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
                        'image_url': get_asset_image_url_simple(asset),
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
            
            # Get customer name
            customer_name = None
            try:
                if item.customer_user:
                    customer_name = item.customer_user.name
            except:
                pass

            item_data = {
                # Basic Info
                'id': item.id,
                'asset_tag': item.asset_tag,
                'serial_number': item.serial_num,
                'name': item.name,
                'model': item.model,
                'manufacturer': getattr(item, 'manufacturer', None),
                'category': getattr(item, 'category', None),
                'status': item.status.value if hasattr(item.status, 'value') else str(item.status) if item.status else 'Unknown',

                # Hardware Specs
                'cpu_type': getattr(item, 'cpu_type', None),
                'cpu_cores': getattr(item, 'cpu_cores', None),
                'gpu_cores': getattr(item, 'gpu_cores', None),
                'memory': getattr(item, 'memory', None),
                'storage': getattr(item, 'harddrive', None),
                'asset_type': getattr(item, 'asset_type', None),
                'hardware_type': getattr(item, 'hardware_type', None),

                # Condition Fields
                'condition': getattr(item, 'condition', None),
                'is_erased': getattr(item, 'erased', None),
                'has_keyboard': getattr(item, 'keyboard', None),
                'has_charger': getattr(item, 'charger', None),
                'diagnostics_code': getattr(item, 'diag', None),

                # Location/Assignment Fields
                'current_customer': customer_name,
                'customer': getattr(item, 'customer', None),
                'country': getattr(item, 'country', None),
                'asset_company': item.company.name if item.company else None,
                'company_id': getattr(item, 'company_id', None),
                'location_id': getattr(item, 'location_id', None),
                'location_name': item.location.name if item.location else None,

                # Image URL (with fallback to default product image)
                'image_url': get_asset_image_url_simple(item),

                # Additional Fields
                'description': getattr(item, 'description', None),
                'cost_price': getattr(item, 'cost_price', None),
                'notes': getattr(item, 'notes', None),
                'tech_notes': getattr(item, 'tech_notes', None),
                'specifications': getattr(item, 'specifications', None),
                'po': getattr(item, 'po', None),
                'receiving_date': item.receiving_date.isoformat() if hasattr(item, 'receiving_date') and item.receiving_date else None,
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
            
            # Manual pagination
            total_comments = comments_query.count()
            offset = (page - 1) * per_page
            comments_items = comments_query.offset(offset).limit(per_page).all()
            
            # Calculate pagination info
            has_next = offset + per_page < total_comments
            has_prev = page > 1
        
            # Format comments data to match iOS app expectations
            comments_data = []
            for comment in comments_items:
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
                        "page": page,
                        "per_page": per_page,
                        "total": total_comments,
                        "has_next": has_next,
                        "has_prev": has_prev
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


# ============================================================================
# AUDIT API ENDPOINTS
# ============================================================================

@api_bp.route('/audit/status', methods=['GET'])
def audit_status():
    """
    Get current audit session status
    
    Returns:
        - Active audit details if exists
        - null if no active audit
    """
    try:
        # Get JWT token from Authorization header
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return jsonify(create_error_response(
                "MISSING_TOKEN",
                "Authorization header with Bearer token is required",
                401
            )), 401
        
        token = auth_header[7:]  # Remove 'Bearer ' prefix
        secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key')
        
        try:
            payload = jwt.decode(token, secret_key, algorithms=['HS256'])
            user_id = payload.get('user_id')
            
            if not user_id:
                return jsonify(create_error_response(
                    "INVALID_TOKEN",
                    "Token does not contain valid user information",
                    401
                )), 401
                
        except jwt.ExpiredSignatureError:
            return jsonify(create_error_response(
                "TOKEN_EXPIRED",
                "Token has expired",
                401
            )), 401
        except jwt.InvalidTokenError:
            return jsonify(create_error_response(
                "INVALID_TOKEN",
                "Invalid token",
                401
            )), 401
        
        # Get user from database to check permissions
        db_session = db_manager.get_session()
        try:
            user = db_session.query(User).get(user_id)
            if not user:
                return jsonify(create_error_response(
                    "USER_NOT_FOUND",
                    "User not found",
                    404
                )), 404
            
            # Check audit permissions
            if not user.permissions or not user.permissions.can_access_inventory_audit:
                return jsonify(create_error_response(
                    "INSUFFICIENT_PERMISSIONS",
                    "User does not have permission to access inventory audit",
                    403
                )), 403
            
            # Check for active audit session
            current_audit = db_session.query(AuditSession).filter(
                AuditSession.is_active == True
            ).first()
            
            if not current_audit:
                return jsonify(create_success_response(
                    {"current_audit": None},
                    "No active audit session"
                ))
            
            # Parse JSON data
            audit_inventory = json.loads(current_audit.audit_inventory) if current_audit.audit_inventory else []
            scanned_assets = json.loads(current_audit.scanned_assets) if current_audit.scanned_assets else []
            missing_assets = json.loads(current_audit.missing_assets) if current_audit.missing_assets else []
            unexpected_assets = json.loads(current_audit.unexpected_assets) if current_audit.unexpected_assets else []
            
            # Calculate completion percentage
            completion_percentage = 0
            if current_audit.total_assets > 0:
                completion_percentage = round((len(scanned_assets) / current_audit.total_assets * 100), 2)
            
            audit_data = {
                "id": current_audit.id,
                "country": current_audit.country,
                "total_assets": current_audit.total_assets,
                "scanned_count": len(scanned_assets),
                "missing_count": len(missing_assets),
                "unexpected_count": len(unexpected_assets),
                "completion_percentage": completion_percentage,
                "started_at": current_audit.started_at.isoformat() + 'Z',
                "started_by": current_audit.started_by,
                "is_active": current_audit.is_active
            }
            
            return jsonify(create_success_response(
                {"current_audit": audit_data},
                "Active audit session retrieved"
            ))
            
        finally:
            db_session.close()
            
    except Exception as e:
        logger.error(f"Error in audit status API: {str(e)}")
        return jsonify(create_error_response(
            "INTERNAL_ERROR",
            f"Error retrieving audit status: {str(e)}",
            500
        )), 500


@api_bp.route('/audit/countries', methods=['GET'])
def audit_countries():
    """
    Get available countries for audit
    
    Returns list of countries the user can audit
    """
    try:
        # Get JWT token and validate user
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return jsonify(create_error_response(
                "MISSING_TOKEN",
                "Authorization header with Bearer token is required",
                401
            )), 401
        
        token = auth_header[7:]
        secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key')
        
        try:
            payload = jwt.decode(token, secret_key, algorithms=['HS256'])
            user_id = payload.get('user_id')
        except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
            return jsonify(create_error_response(
                "INVALID_TOKEN",
                "Invalid or expired token",
                401
            )), 401
        
        db_session = db_manager.get_session()
        try:
            user = db_session.query(User).get(user_id)
            if not user or not user.permissions or not user.permissions.can_start_inventory_audit:
                return jsonify(create_error_response(
                    "INSUFFICIENT_PERMISSIONS",
                    "User does not have permission to start inventory audit",
                    403
                )), 403
            
            # Get available countries based on user permissions
            from models.user import UserType
            if user.user_type == UserType.SUPER_ADMIN:
                # Super admins can audit any country
                countries = [country.value for country in Country]
            elif user.user_type == UserType.COUNTRY_ADMIN and user.assigned_countries:
                # Country admins can only audit their assigned country
                countries = [user.assigned_country]
            elif user.user_type == UserType.SUPERVISOR:
                # Supervisors can audit all countries
                countries = [country.value for country in Country]
            else:
                countries = []
            
            return jsonify(create_success_response(
                {"countries": countries},
                "Available countries retrieved"
            ))
            
        finally:
            db_session.close()
            
    except Exception as e:
        logger.error(f"Error in audit countries API: {str(e)}")
        return jsonify(create_error_response(
            "INTERNAL_ERROR",
            f"Error retrieving countries: {str(e)}",
            500
        )), 500


@api_bp.route('/audit/start', methods=['POST'])
def start_audit():
    """
    Start a new audit session
    
    Expects JSON: {"country": "SINGAPORE"}
    """
    try:
        # Get JWT token and validate user
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return jsonify(create_error_response(
                "MISSING_TOKEN",
                "Authorization header with Bearer token is required",
                401
            )), 401
        
        token = auth_header[7:]
        secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key')
        
        try:
            payload = jwt.decode(token, secret_key, algorithms=['HS256'])
            user_id = payload.get('user_id')
        except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
            return jsonify(create_error_response(
                "INVALID_TOKEN",
                "Invalid or expired token",
                401
            )), 401
        
        # Get request data
        data = request.get_json()
        if not data or 'country' not in data:
            return jsonify(create_error_response(
                "VALIDATION_ERROR",
                "Country is required",
                400
            )), 400
        
        country = data['country']
        
        db_session = db_manager.get_session()
        try:
            # Validate user permissions
            user = db_session.query(User).get(user_id)
            if not user or not user.permissions or not user.permissions.can_start_inventory_audit:
                return jsonify(create_error_response(
                    "INSUFFICIENT_PERMISSIONS",
                    "User does not have permission to start inventory audit",
                    403
                )), 403
            
            # Check if there's already an active audit
            existing_audit = db_session.query(AuditSession).filter(
                AuditSession.is_active == True
            ).first()
            
            if existing_audit:
                return jsonify(create_error_response(
                    "AUDIT_ALREADY_ACTIVE",
                    "There is already an active audit session",
                    400
                )), 400
            
            # Validate country access
            from models.user import UserType
            if user.user_type == UserType.COUNTRY_ADMIN and user.assigned_countries:
                if country != user.assigned_countries:
                    return jsonify(create_error_response(
                        "INVALID_COUNTRY",
                        "You can only audit your assigned country",
                        403
                    )), 403
            
            # Get assets for the selected country
            assets_query = db_session.query(Asset).filter(Asset.country == country)
            
            # Apply company filtering for COUNTRY_ADMIN users
            if user.user_type == UserType.COUNTRY_ADMIN and user.company_id:
                assets_query = assets_query.filter(Asset.company_id == user.company_id)
            
            assets = assets_query.all()
            
            if not assets:
                return jsonify(create_error_response(
                    "NO_ASSETS",
                    f"No assets found for country: {country}",
                    400
                )), 400
            
            # Prepare inventory data
            inventory_data = []
            for asset in assets:
                inventory_data.append({
                    'id': asset.id,
                    'asset_tag': asset.asset_tag,
                    'serial_num': asset.serial_num,
                    'name': asset.name,
                    'model': asset.model,
                    'status': asset.status.value if hasattr(asset.status, 'value') else str(asset.status),
                    'location': asset.location.name if asset.location else None,
                    'company': asset.company.name if asset.company else None
                })
            
            # Create audit session
            audit_id = f"audit_{int(datetime.utcnow().timestamp())}"
            
            audit_session = AuditSession(
                id=audit_id,
                country=country,
                total_assets=len(assets),
                started_at=datetime.utcnow(),
                started_by=user_id,
                is_active=True,
                scanned_assets=json.dumps([]),
                missing_assets=json.dumps([]),
                unexpected_assets=json.dumps([]),
                audit_inventory=json.dumps(inventory_data)
            )
            
            db_session.add(audit_session)
            db_session.commit()
            
            audit_data = {
                "id": audit_session.id,
                "country": audit_session.country,
                "total_assets": audit_session.total_assets,
                "scanned_count": 0,
                "missing_count": 0,
                "unexpected_count": 0,
                "completion_percentage": 0,
                "started_at": audit_session.started_at.isoformat() + 'Z',
                "started_by": audit_session.started_by,
                "is_active": audit_session.is_active
            }
            
            return jsonify(create_success_response(
                {"audit": audit_data},
                f"Audit started successfully for {country}"
            )), 201
            
        finally:
            db_session.close()
            
    except Exception as e:
        logger.error(f"Error in start audit API: {str(e)}")
        return jsonify(create_error_response(
            "INTERNAL_ERROR",
            f"Error starting audit: {str(e)}",
            500
        )), 500


@api_bp.route('/audit/scan', methods=['POST'])
def scan_asset():
    """
    Scan an asset during audit
    
    Expects JSON: {"identifier": "asset_tag_or_serial"}
    """
    try:
        # Get JWT token and validate user
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return jsonify(create_error_response(
                "MISSING_TOKEN",
                "Authorization header with Bearer token is required",
                401
            )), 401
        
        token = auth_header[7:]
        secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key')
        
        try:
            payload = jwt.decode(token, secret_key, algorithms=['HS256'])
            user_id = payload.get('user_id')
        except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
            return jsonify(create_error_response(
                "INVALID_TOKEN",
                "Invalid or expired token",
                401
            )), 401
        
        # Get request data
        data = request.get_json()
        if not data or 'identifier' not in data:
            return jsonify(create_error_response(
                "VALIDATION_ERROR",
                "Asset identifier is required",
                400
            )), 400
        
        identifier = data['identifier'].strip()
        
        db_session = db_manager.get_session()
        try:
            # Validate user permissions
            user = db_session.query(User).get(user_id)
            if not user or not user.permissions or not user.permissions.can_access_inventory_audit:
                return jsonify(create_error_response(
                    "INSUFFICIENT_PERMISSIONS",
                    "User does not have permission to access inventory audit",
                    403
                )), 403
            
            # Get active audit session
            audit_session = db_session.query(AuditSession).filter(
                AuditSession.is_active == True
            ).first()
            
            if not audit_session:
                return jsonify(create_error_response(
                    "NO_ACTIVE_AUDIT",
                    "No active audit session found",
                    400
                )), 400
            
            # Parse audit data
            audit_inventory = json.loads(audit_session.audit_inventory)
            scanned_assets = json.loads(audit_session.scanned_assets)
            unexpected_assets = json.loads(audit_session.unexpected_assets)
            
            # Check if asset is in expected inventory
            found_asset = None
            for asset in audit_inventory:
                if (asset['asset_tag'] == identifier or asset['serial_num'] == identifier):
                    found_asset = asset
                    break
            
            if found_asset:
                # Asset found in expected inventory
                if found_asset['id'] in scanned_assets:
                    return jsonify(create_error_response(
                        "ALREADY_SCANNED",
                        "This asset has already been scanned",
                        400
                    )), 400
                
                # Add to scanned assets
                scanned_assets.append(found_asset['id'])
                audit_session.scanned_assets = json.dumps(scanned_assets)
                
                scan_result = {
                    "status": "found_expected",
                    "message": f"Asset {identifier} scanned successfully",
                    "asset": found_asset
                }
            else:
                # Asset not in expected inventory - check if it's an unexpected asset
                unexpected_asset_data = {
                    'identifier': identifier,
                    'scanned_at': datetime.utcnow().isoformat(),
                    'type': 'unexpected'
                }
                
                # Check if already in unexpected assets
                already_unexpected = any(
                    asset['identifier'] == identifier for asset in unexpected_assets
                )
                
                if already_unexpected:
                    return jsonify(create_error_response(
                        "ALREADY_SCANNED",
                        "This unexpected asset has already been recorded",
                        400
                    )), 400
                
                unexpected_assets.append(unexpected_asset_data)
                audit_session.unexpected_assets = json.dumps(unexpected_assets)
                
                scan_result = {
                    "status": "unexpected",
                    "message": f"Asset {identifier} not found in expected inventory (recorded as unexpected)",
                    "asset": unexpected_asset_data
                }
            
            # Update audit session
            db_session.commit()
            
            # Calculate updated progress
            completion_percentage = 0
            if audit_session.total_assets > 0:
                completion_percentage = round((len(scanned_assets) / audit_session.total_assets * 100), 2)
            
            # Add progress info to response
            scan_result["progress"] = {
                "total_assets": audit_session.total_assets,
                "scanned_count": len(scanned_assets),
                "unexpected_count": len(unexpected_assets),
                "completion_percentage": completion_percentage
            }
            
            return jsonify(create_success_response(
                scan_result,
                "Asset scan processed"
            ))
            
        finally:
            db_session.close()
            
    except Exception as e:
        logger.error(f"Error in scan asset API: {str(e)}")
        return jsonify(create_error_response(
            "INTERNAL_ERROR",
            f"Error scanning asset: {str(e)}",
            500
        )), 500


@api_bp.route('/audit/end', methods=['POST'])
def end_audit():
    """
    End the current audit session
    """
    try:
        # Get JWT token and validate user
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return jsonify(create_error_response(
                "MISSING_TOKEN",
                "Authorization header with Bearer token is required",
                401
            )), 401
        
        token = auth_header[7:]
        secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key')
        
        try:
            payload = jwt.decode(token, secret_key, algorithms=['HS256'])
            user_id = payload.get('user_id')
        except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
            return jsonify(create_error_response(
                "INVALID_TOKEN",
                "Invalid or expired token",
                401
            )), 401
        
        db_session = db_manager.get_session()
        try:
            # Validate user permissions
            user = db_session.query(User).get(user_id)
            if not user or not user.permissions or not user.permissions.can_access_inventory_audit:
                return jsonify(create_error_response(
                    "INSUFFICIENT_PERMISSIONS",
                    "User does not have permission to access inventory audit",
                    403
                )), 403
            
            # Get active audit session
            audit_session = db_session.query(AuditSession).filter(
                AuditSession.is_active == True
            ).first()
            
            if not audit_session:
                return jsonify(create_error_response(
                    "NO_ACTIVE_AUDIT",
                    "No active audit session found",
                    400
                )), 400
            
            # End the audit session
            audit_session.is_active = False
            audit_session.completed_at = datetime.utcnow()
            
            # Calculate final missing assets
            audit_inventory = json.loads(audit_session.audit_inventory)
            scanned_assets = json.loads(audit_session.scanned_assets)
            
            missing_assets = [asset for asset in audit_inventory if asset['id'] not in scanned_assets]
            audit_session.missing_assets = json.dumps(missing_assets)
            
            db_session.commit()
            
            # Prepare final report data
            final_report = {
                "audit_id": audit_session.id,
                "country": audit_session.country,
                "started_at": audit_session.started_at.isoformat() + 'Z',
                "completed_at": audit_session.completed_at.isoformat() + 'Z',
                "summary": {
                    "total_expected": audit_session.total_assets,
                    "total_scanned": len(scanned_assets),
                    "total_missing": len(missing_assets),
                    "total_unexpected": len(json.loads(audit_session.unexpected_assets)),
                    "completion_percentage": round((len(scanned_assets) / audit_session.total_assets * 100), 2) if audit_session.total_assets > 0 else 0
                }
            }
            
            return jsonify(create_success_response(
                {"final_report": final_report},
                "Audit session ended successfully"
            ))
            
        finally:
            db_session.close()
            
    except Exception as e:
        logger.error(f"Error in end audit API: {str(e)}")
        return jsonify(create_error_response(
            "INTERNAL_ERROR",
            f"Error ending audit: {str(e)}",
            500
        )), 500


@api_bp.route('/audit/details/<detail_type>', methods=['GET'])
def audit_details(detail_type):
    """
    Get detailed asset lists from current audit
    
    detail_type can be: 'total', 'scanned', 'missing', 'unexpected'
    """
    try:
        # Get JWT token and validate user
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return jsonify(create_error_response(
                "MISSING_TOKEN",
                "Authorization header with Bearer token is required",
                401
            )), 401
        
        token = auth_header[7:]
        secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key')
        
        try:
            payload = jwt.decode(token, secret_key, algorithms=['HS256'])
            user_id = payload.get('user_id')
        except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
            return jsonify(create_error_response(
                "INVALID_TOKEN",
                "Invalid or expired token",
                401
            )), 401
        
        # Validate detail type
        valid_types = ['total', 'scanned', 'missing', 'unexpected']
        if detail_type not in valid_types:
            return jsonify(create_error_response(
                "INVALID_PARAMETER",
                f"Invalid detail_type. Must be one of: {', '.join(valid_types)}",
                400
            )), 400
        
        db_session = db_manager.get_session()
        try:
            # Validate user permissions
            user = db_session.query(User).get(user_id)
            if not user or not user.permissions or not user.permissions.can_access_inventory_audit:
                return jsonify(create_error_response(
                    "INSUFFICIENT_PERMISSIONS",
                    "User does not have permission to access inventory audit",
                    403
                )), 403
            
            # Get active audit session
            audit_session = db_session.query(AuditSession).filter(
                AuditSession.is_active == True
            ).first()
            
            if not audit_session:
                return jsonify(create_error_response(
                    "NO_ACTIVE_AUDIT",
                    "No active audit session found",
                    400
                )), 400
            
            # Parse audit data
            audit_inventory = json.loads(audit_session.audit_inventory)
            scanned_assets = json.loads(audit_session.scanned_assets)
            unexpected_assets = json.loads(audit_session.unexpected_assets)
            
            # Get requested asset list
            if detail_type == 'total':
                assets_data = audit_inventory
                title = f"All Expected Assets ({len(audit_inventory)})"
            elif detail_type == 'scanned':
                assets_data = [asset for asset in audit_inventory if asset['id'] in scanned_assets]
                title = f"Scanned Assets ({len(assets_data)})"
            elif detail_type == 'missing':
                assets_data = [asset for asset in audit_inventory if asset['id'] not in scanned_assets]
                title = f"Missing Assets ({len(assets_data)})"
            elif detail_type == 'unexpected':
                assets_data = unexpected_assets
                title = f"Unexpected Assets ({len(unexpected_assets)})"
            
            response_data = {
                "detail_type": detail_type,
                "title": title,
                "count": len(assets_data),
                "assets": assets_data
            }
            
            return jsonify(create_success_response(
                response_data,
                f"Retrieved {detail_type} asset details"
            ))
            
        finally:
            db_session.close()
            
    except Exception as e:
        logger.error(f"Error in audit details API: {str(e)}")
        return jsonify(create_error_response(
            "INTERNAL_ERROR",
            f"Error retrieving audit details: {str(e)}",
            500
        )), 500

@api_bp.route('/companies', methods=['GET'])
def get_companies():
    """
    Get all companies with parent/child hierarchy
    No authentication required for internal use
    """
    try:
        from models.company import Company

        db_session = db_manager.get_session()

        try:
            # Get all companies ordered by parent relationship
            companies = db_session.query(Company).order_by(
                Company.is_parent_company.desc(),
                Company.parent_company_id.asc(),
                Company.name.asc()
            ).all()

            companies_list = []
            for company in companies:
                company_data = {
                    'id': company.id,
                    'name': company.name,
                    'display_name': company.effective_display_name,
                    'grouped_display_name': company.grouped_display_name,
                    'is_parent_company': company.is_parent_company,
                    'parent_company_id': company.parent_company_id,
                    'parent_company_name': company.parent_company.name if company.parent_company else None
                }
                companies_list.append(company_data)

            return jsonify({
                'success': True,
                'companies': companies_list
            }), 200

        finally:
            db_session.close()

    except Exception as e:
        logger.error(f"Error fetching companies: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error fetching companies: {str(e)}'
        }), 500


# ============================================================================
# ACCESSORY API ENDPOINTS
# ============================================================================

@api_bp.route('/accessories', methods=['GET'])
@dual_auth_required
def list_accessories():
    """List accessories with pagination and image_url"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 50, type=int), 100)
        search = request.args.get('search', None)
        category = request.args.get('category', None)

        db_session = db_manager.get_session()
        try:
            query = db_session.query(Accessory).order_by(Accessory.created_at.desc())

            # Apply search filter
            if search:
                search_term = f"%{search}%"
                query = query.filter(
                    (Accessory.name.ilike(search_term)) |
                    (Accessory.model_no.ilike(search_term)) |
                    (Accessory.manufacturer.ilike(search_term))
                )

            # Apply category filter
            if category:
                query = query.filter(Accessory.category.ilike(f"%{category}%"))

            # Get total count
            total = query.count()

            # Apply pagination
            accessories = query.offset((page - 1) * per_page).limit(per_page).all()

            accessories_data = []
            for accessory in accessories:
                try:
                    item_data = {
                        'id': accessory.id,
                        'name': accessory.name,
                        'category': accessory.category,
                        'manufacturer': accessory.manufacturer,
                        'model': accessory.model_no,
                        'total_quantity': accessory.total_quantity,
                        'available_quantity': accessory.available_quantity,
                        'status': accessory.status,
                        'country': accessory.country,
                        'image_url': get_accessory_image_url_simple(accessory),
                        'created_at': accessory.created_at.isoformat() if accessory.created_at else None
                    }
                    accessories_data.append(item_data)
                except Exception as e:
                    logger.error(f"Error serializing accessory {accessory.id}: {e}")
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
            accessories_data,
            f"Retrieved {len(accessories_data)} accessories",
            {"pagination": pagination}
        ))

    except Exception as e:
        response, status_code = create_error_response(
            "INTERNAL_ERROR",
            f"Error retrieving accessories: {str(e)}",
            500
        )
        return jsonify(response), status_code


@api_bp.route('/accessories/<int:accessory_id>', methods=['GET'])
@dual_auth_required
def get_accessory_item(accessory_id):
    """Get detailed information about a specific accessory"""
    try:
        db_session = db_manager.get_session()
        try:
            accessory = db_session.query(Accessory).get(accessory_id)

            if not accessory:
                response, status_code = create_error_response(
                    "RESOURCE_NOT_FOUND",
                    f"Accessory with ID {accessory_id} not found",
                    404
                )
                return jsonify(response), status_code

            # Get customer name if assigned
            customer_name = None
            try:
                if accessory.customer_user:
                    customer_name = accessory.customer_user.name
            except:
                pass

            item_data = {
                'id': accessory.id,
                'name': accessory.name,
                'category': accessory.category,
                'manufacturer': accessory.manufacturer,
                'model': accessory.model_no,
                'total_quantity': accessory.total_quantity,
                'available_quantity': accessory.available_quantity,
                'status': accessory.status,
                'country': accessory.country,
                'notes': accessory.notes,
                'current_customer': customer_name,
                'company': accessory.company.name if accessory.company else None,
                'company_id': accessory.company_id,
                'image_url': get_accessory_image_url_simple(accessory),
                'checkout_date': accessory.checkout_date.isoformat() if accessory.checkout_date else None,
                'return_date': accessory.return_date.isoformat() if accessory.return_date else None,
                'created_at': accessory.created_at.isoformat() if accessory.created_at else None,
                'updated_at': accessory.updated_at.isoformat() if accessory.updated_at else None
            }
        finally:
            db_session.close()

        return jsonify(create_success_response(
            item_data,
            f"Retrieved accessory {accessory_id}"
        ))

    except Exception as e:
        response, status_code = create_error_response(
            "INTERNAL_ERROR",
            f"Error retrieving accessory: {str(e)}",
            500
        )
        return jsonify(response), status_code


# ============================================================
# NEXT ASSET TAG ENDPOINT (for iOS PDF extraction)
# ============================================================

@api_bp.route('/assets/next-tag', methods=['GET'])
def get_next_asset_tag():
    """
    Get next available asset tag for a given prefix

    GET /api/v1/assets/next-tag?prefix=SG-
    """
    try:
        import re

        prefix = request.args.get('prefix', 'SG-')
        clean_prefix = prefix.rstrip('-')

        db_session = db_manager.get_session()
        try:
            # Find highest existing tag with this prefix
            existing_tags = db_session.query(Asset.asset_tag).filter(
                Asset.asset_tag.like(f'{clean_prefix}-%')
            ).all()

            max_num = 0
            for (tag,) in existing_tags:
                if tag:
                    match = re.match(rf'{re.escape(clean_prefix)}-(\d+)', tag)
                    if match:
                        num = int(match.group(1))
                        if num > max_num:
                            max_num = num

            next_num = max_num + 1

            return jsonify(create_success_response(
                {
                    'prefix': f'{clean_prefix}-',
                    'next_number': next_num,
                    'next_tag': f'{clean_prefix}-{next_num}'
                },
                f"Next asset tag: {clean_prefix}-{next_num}"
            ))
        finally:
            db_session.close()

    except Exception as e:
        response, status_code = create_error_response(
            "INTERNAL_ERROR",
            f"Error getting next asset tag: {str(e)}",
            500
        )
        return jsonify(response), status_code


# ============================================================
# BULK CREATE ASSETS ENDPOINT (for iOS PDF extraction)
# ============================================================

@api_bp.route('/assets/bulk', methods=['POST'])
def bulk_create_assets():
    """
    Bulk create assets from PDF extraction

    POST /api/v1/assets/bulk
    """
    try:
        from models.asset import AssetStatus

        data = request.get_json()
        if not data or 'assets' not in data:
            response, status_code = create_error_response(
                "VALIDATION_ERROR",
                "Missing 'assets' in request body",
                400
            )
            return jsonify(response), status_code

        assets_data = data.get('assets', [])
        ticket_id = data.get('ticket_id')

        if not assets_data:
            response, status_code = create_error_response(
                "VALIDATION_ERROR",
                "No assets provided",
                400
            )
            return jsonify(response), status_code

        db_session = db_manager.get_session()
        try:
            # Get ticket if provided
            ticket = None
            if ticket_id:
                ticket = db_session.query(Ticket).filter(Ticket.id == ticket_id).first()

            created_ids = []
            errors = []

            for asset_data in assets_data:
                try:
                    # Check for duplicate serial number
                    serial = asset_data.get('serial_number') or asset_data.get('serial_num')
                    if serial:
                        existing = db_session.query(Asset).filter(Asset.serial_num == serial).first()
                        if existing:
                            errors.append({
                                'serial_number': serial,
                                'error': f'Duplicate serial number (exists as {existing.asset_tag})'
                            })
                            continue

                    # Check for duplicate asset tag
                    asset_tag = asset_data.get('asset_tag')
                    if asset_tag:
                        existing = db_session.query(Asset).filter(Asset.asset_tag == asset_tag).first()
                        if existing:
                            errors.append({
                                'serial_number': serial,
                                'asset_tag': asset_tag,
                                'error': 'Duplicate asset tag'
                            })
                            continue

                    # Create asset
                    asset = Asset(
                        serial_num=serial,
                        asset_tag=asset_tag,
                        name=asset_data.get('name'),
                        model=asset_data.get('model_identifier') or asset_data.get('model'),
                        part_number=asset_data.get('part_number'),
                        hardware_type=asset_data.get('hardware_type'),
                        cpu_type=asset_data.get('cpu_type'),
                        cpu_cores=asset_data.get('cpu_cores'),
                        gpu_cores=asset_data.get('gpu_cores'),
                        memory=asset_data.get('memory'),
                        harddrive=asset_data.get('storage') or asset_data.get('harddrive'),
                        condition=asset_data.get('condition', 'New'),
                        status=AssetStatus.IN_STOCK,
                        manufacturer=asset_data.get('manufacturer', 'Apple'),
                        category=asset_data.get('category', 'APPLE'),
                        company_id=asset_data.get('company_id'),
                        country=asset_data.get('country', 'Singapore')
                    )

                    db_session.add(asset)
                    db_session.flush()  # Get the ID

                    created_ids.append(asset.id)

                    # Link to ticket if provided
                    if ticket:
                        ticket.assets.append(asset)

                except Exception as e:
                    errors.append({
                        'serial_number': asset_data.get('serial_number', 'unknown'),
                        'error': str(e)
                    })

            db_session.commit()

            result_data = {
                'created_count': len(created_ids),
                'created_ids': created_ids,
                'failed_count': len(errors),
                'errors': errors
            }

            if errors:
                message = f"Created {len(created_ids)} of {len(assets_data)} assets"
            else:
                message = f"Successfully created {len(created_ids)} assets"

            return jsonify(create_success_response(result_data, message))

        except Exception as e:
            db_session.rollback()
            raise
        finally:
            db_session.close()

    except Exception as e:
        response, status_code = create_error_response(
            "INTERNAL_ERROR",
            f"Error creating assets: {str(e)}",
            500
        )
        return jsonify(response), status_code


# ============================================================
# MOBILE TICKET CREATION ENDPOINTS (for iOS app)
# ============================================================

# JSON API Key for iOS app authentication
MOBILE_API_KEY = 'xAQhm3__ZH6MvRIPMIBSDRAsIa1w2Slh5uaCtc4NurM'


def get_jwt_user_id():
    """Helper function to get user_id from JWT token"""
    auth_header = request.headers.get('Authorization', '')
    if not auth_header.startswith('Bearer '):
        return None, "Authorization header with Bearer token is required"

    token = auth_header[7:]
    secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key')

    try:
        payload = jwt.decode(token, secret_key, algorithms=['HS256'])
        return payload.get('user_id'), None
    except jwt.ExpiredSignatureError:
        return None, "Token has expired"
    except jwt.InvalidTokenError:
        return None, "Invalid token"


def get_authenticated_user_for_tickets():
    """
    Get authenticated user from either:
    1. X-API-Key + JWT Bearer token (iOS app)
    2. JWT Bearer token only (mobile)
    Returns (user_id, error_message)
    """
    from routes.json_api import verify_jwt_token

    api_key = request.headers.get('X-API-Key')
    auth_header = request.headers.get('Authorization', '')

    # Method 1: API Key + JWT (iOS app pattern)
    if api_key == MOBILE_API_KEY:
        if auth_header.startswith('Bearer '):
            token = auth_header[7:]
            user_id = verify_jwt_token(token)
            if user_id:
                return user_id, None
            return None, "Invalid or expired token"
        return None, "Authorization Bearer token required with API key"

    # Method 2: JWT only
    if auth_header.startswith('Bearer '):
        token = auth_header[7:]
        secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key')
        try:
            payload = jwt.decode(token, secret_key, algorithms=['HS256'])
            return payload.get('user_id'), None
        except jwt.ExpiredSignatureError:
            return None, "Token has expired"
        except jwt.InvalidTokenError:
            return None, "Invalid token"

    return None, "Authentication required. Provide X-API-Key and Authorization Bearer token"


@api_bp.route('/tickets/categories', methods=['GET'])
def get_ticket_categories():
    """
    Get available ticket categories for mobile app

    Returns list of categories the user can create tickets for
    """
    try:
        categories = [
            {
                'id': 'ASSET_REPAIR',
                'name': 'Asset Repair',
                'description': 'Report device damage and request repair',
                'requires_asset': True,
                'required_fields': ['serial_number', 'damage_description', 'queue_id'],
                'optional_fields': ['apple_diagnostics', 'country', 'notes', 'priority']
            },
            {
                'id': 'ASSET_CHECKOUT_CLAW',
                'name': 'Asset Checkout (claw)',
                'description': 'Deploy device to customer',
                'requires_asset': True,
                'required_fields': ['serial_number', 'customer_id', 'shipping_address', 'queue_id'],
                'optional_fields': ['shipping_tracking', 'notes', 'priority']
            },
            {
                'id': 'ASSET_RETURN_CLAW',
                'name': 'Asset Return (claw)',
                'description': 'Process device return from customer',
                'requires_asset': False,
                'required_fields': ['customer_id', 'return_address', 'queue_id'],
                'optional_fields': ['outbound_tracking', 'inbound_tracking', 'damage_description', 'return_description', 'notes', 'priority']
            },
            {
                'id': 'ASSET_INTAKE',
                'name': 'Asset Intake',
                'description': 'Receive new assets into inventory',
                'requires_asset': False,
                'required_fields': ['title', 'description', 'queue_id'],
                'optional_fields': ['notes', 'priority']
            },
            {
                'id': 'INTERNAL_TRANSFER',
                'name': 'Internal Transfer',
                'description': 'Transfer device between customers/locations',
                'requires_asset': False,
                'required_fields': ['offboarding_customer_id', 'offboarding_details', 'offboarding_address', 'onboarding_customer_id', 'onboarding_address', 'queue_id'],
                'optional_fields': ['transfer_tracking', 'notes', 'priority']
            },
            {
                'id': 'BULK_DELIVERY_QUOTATION',
                'name': 'Bulk Delivery Quote',
                'description': 'Request quote for bulk device delivery',
                'requires_asset': False,
                'required_fields': ['subject', 'description', 'queue_id'],
                'optional_fields': ['notes', 'priority']
            },
            {
                'id': 'REPAIR_QUOTE',
                'name': 'Repair Quote',
                'description': 'Request quote for device repair',
                'requires_asset': False,
                'required_fields': ['subject', 'description', 'queue_id'],
                'optional_fields': ['serial_number', 'notes', 'priority']
            },
            {
                'id': 'ITAD_QUOTE',
                'name': 'ITAD Quote',
                'description': 'IT Asset Disposal quotation',
                'requires_asset': False,
                'required_fields': ['subject', 'description', 'queue_id'],
                'optional_fields': ['notes', 'priority']
            }
        ]

        return jsonify(create_success_response(
            categories,
            "Retrieved ticket categories"
        ))

    except Exception as e:
        response, status_code = create_error_response(
            "INTERNAL_ERROR",
            f"Error retrieving categories: {str(e)}",
            500
        )
        return jsonify(response), status_code


@api_bp.route('/tickets/create', methods=['POST'])
def create_ticket_mobile():
    """
    Create a new ticket from mobile app

    Supports all ticket categories with category-specific validation.
    Accepts both X-API-Key + Bearer token (iOS) or Bearer token only.
    """
    try:
        from models.ticket import TicketCategory, TicketPriority, Ticket
        from models.asset import Asset, AssetStatus
        from models.customer_user import CustomerUser
        from utils.store_instances import ticket_store

        # Get user from JWT (supports both iOS API Key + JWT and JWT only)
        user_id, error = get_authenticated_user_for_tickets()
        if error:
            return jsonify({
                'success': False,
                'error': error,
                'message': 'Authentication required'
            }), 401

        data = request.get_json()
        if not data:
            response, status_code = create_error_response(
                "VALIDATION_ERROR",
                "Request body is required",
                400
            )
            return jsonify(response), status_code

        category = data.get('category')
        if not category:
            response, status_code = create_error_response(
                "VALIDATION_ERROR",
                "Category is required",
                400
            )
            return jsonify(response), status_code

        # Get common fields
        queue_id = data.get('queue_id')

        if not queue_id:
            response, status_code = create_error_response(
                "VALIDATION_ERROR",
                "Queue ID is required",
                400
            )
            return jsonify(response), status_code

        db_session = db_manager.get_session()

        try:
            # Validate queue exists
            queue = db_session.query(Queue).get(queue_id)
            if not queue:
                response, status_code = create_error_response(
                    "VALIDATION_ERROR",
                    f"Queue with ID {queue_id} not found",
                    400
                )
                return jsonify(response), status_code

            # Category-specific handling
            if category == 'PIN_REQUEST':
                return _create_pin_request_ticket(data, user_id, db_session)

            elif category == 'ASSET_REPAIR':
                return _create_asset_repair_ticket(data, user_id, db_session)

            elif category == 'ASSET_CHECKOUT_CLAW':
                return _create_asset_checkout_ticket(data, user_id, db_session)

            elif category == 'ASSET_RETURN_CLAW':
                return _create_asset_return_ticket(data, user_id, db_session)

            elif category == 'ASSET_INTAKE':
                return _create_asset_intake_ticket(data, user_id, db_session)

            elif category == 'INTERNAL_TRANSFER':
                return _create_internal_transfer_ticket(data, user_id, db_session)

            elif category in ['BULK_DELIVERY_QUOTATION', 'REPAIR_QUOTE', 'ITAD_QUOTE']:
                return _create_quote_ticket(data, user_id, db_session, category)

            else:
                response, status_code = create_error_response(
                    "VALIDATION_ERROR",
                    f"Unknown category: {category}",
                    400
                )
                return jsonify(response), status_code

        finally:
            db_session.close()

    except Exception as e:
        logger.error(f"Error creating ticket: {str(e)}")
        response, status_code = create_error_response(
            "INTERNAL_ERROR",
            f"Error creating ticket: {str(e)}",
            500
        )
        return jsonify(response), status_code


def _create_pin_request_ticket(data, user_id, db_session):
    """Create PIN Request ticket"""
    from models.ticket import TicketCategory, TicketPriority
    from models.asset import Asset
    from utils.store_instances import ticket_store

    serial_number = data.get('serial_number')
    lock_type = data.get('lock_type')
    priority = data.get('priority', 'Medium')
    queue_id = data.get('queue_id')
    notes = data.get('notes', '')

    # Validate required fields
    if not serial_number:
        response, status_code = create_error_response(
            "VALIDATION_ERROR",
            "Serial number is required for PIN Request",
            400
        )
        return jsonify(response), status_code

    if not lock_type:
        response, status_code = create_error_response(
            "VALIDATION_ERROR",
            "Lock type is required for PIN Request",
            400
        )
        return jsonify(response), status_code

    # Find asset
    asset = db_session.query(Asset).filter(Asset.serial_num == serial_number).first()
    if not asset:
        response, status_code = create_error_response(
            "VALIDATION_ERROR",
            f"Asset not found with serial number: {serial_number}",
            404
        )
        return jsonify(response), status_code

    subject = f"PIN Request for {asset.model} ({serial_number})"
    description = f"""PIN Request Details:
Serial Number: {serial_number}
Model: {asset.model}
Asset Tag: {asset.asset_tag}
Lock Type: {lock_type}

Additional Notes:
{notes}"""

    try:
        ticket_id = ticket_store.create_ticket(
            subject=subject,
            description=description,
            requester_id=user_id,
            category=TicketCategory.PIN_REQUEST,
            priority=priority,
            asset_id=asset.id,
            queue_id=queue_id,
            notes=notes,
            case_owner_id=user_id
        )

        return jsonify({
            'success': True,
            'message': 'Ticket created successfully',
            'data': {
                'ticket_id': ticket_id,
                'display_id': f'TKT-{ticket_id:06d}',
                'subject': subject,
                'status': 'open'
            }
        }), 200

    except Exception as e:
        db_session.rollback()
        raise


def _create_asset_repair_ticket(data, user_id, db_session):
    """Create Asset Repair ticket"""
    from models.ticket import TicketCategory
    from models.asset import Asset
    from utils.store_instances import ticket_store

    serial_number = data.get('serial_number')
    damage_description = data.get('damage_description')
    apple_diagnostics = data.get('apple_diagnostics', '')
    country = data.get('country', '')
    priority = data.get('priority', 'Medium')
    queue_id = data.get('queue_id')
    notes = data.get('notes', '')

    # Validate required fields
    if not serial_number:
        response, status_code = create_error_response(
            "VALIDATION_ERROR",
            "Serial number is required for Asset Repair",
            400
        )
        return jsonify(response), status_code

    if not damage_description:
        response, status_code = create_error_response(
            "VALIDATION_ERROR",
            "Damage description is required for Asset Repair",
            400
        )
        return jsonify(response), status_code

    # Find asset
    asset = db_session.query(Asset).filter(Asset.serial_num == serial_number).first()
    if not asset:
        response, status_code = create_error_response(
            "VALIDATION_ERROR",
            f"Asset not found with serial number: {serial_number}",
            404
        )
        return jsonify(response), status_code

    # Get customer info if available
    customer_info = "N/A"
    if asset.customer_user and asset.customer_user.company:
        customer_info = asset.customer_user.company.name
    elif asset.customer:
        customer_info = asset.customer

    subject = f"Asset Repair - {asset.model} ({serial_number})"
    description = f"""Asset Details:
Serial Number: {serial_number}
Model: {asset.model}
Asset Tag: {asset.asset_tag}
Customer: {customer_info}
Country: {country if country else 'N/A'}

Damage Description:
{damage_description}

Apple Diagnostics Code: {apple_diagnostics if apple_diagnostics else 'N/A'}

Additional Notes:
{notes}"""

    try:
        ticket_id = ticket_store.create_ticket(
            subject=subject,
            description=description,
            requester_id=user_id,
            category=TicketCategory.ASSET_REPAIR,
            priority=priority,
            asset_id=asset.id,
            country=country,
            damage_description=damage_description,
            apple_diagnostics=apple_diagnostics,
            queue_id=queue_id,
            notes=notes,
            case_owner_id=user_id
        )

        return jsonify({
            'success': True,
            'message': 'Ticket created successfully',
            'data': {
                'ticket_id': ticket_id,
                'display_id': f'TKT-{ticket_id:06d}',
                'subject': subject,
                'status': 'open'
            }
        }), 200

    except Exception as e:
        db_session.rollback()
        raise


def _create_asset_checkout_ticket(data, user_id, db_session):
    """Create Asset Checkout (claw) ticket"""
    from models.ticket import TicketCategory, Ticket
    from models.asset import Asset, AssetStatus
    from models.customer_user import CustomerUser
    from models.asset_transaction import AssetTransaction
    from utils.store_instances import ticket_store
    from sqlalchemy import text
    from datetime import datetime

    serial_number = data.get('serial_number')
    customer_id = data.get('customer_id')
    shipping_address = data.get('shipping_address')
    shipping_tracking = data.get('shipping_tracking', '')
    priority = data.get('priority', 'Medium')
    queue_id = data.get('queue_id')
    notes = data.get('notes', '')

    # Validate required fields
    if not serial_number:
        response, status_code = create_error_response(
            "VALIDATION_ERROR",
            "Serial number is required for Asset Checkout",
            400
        )
        return jsonify(response), status_code

    if not customer_id:
        response, status_code = create_error_response(
            "VALIDATION_ERROR",
            "Customer ID is required for Asset Checkout",
            400
        )
        return jsonify(response), status_code

    if not shipping_address:
        response, status_code = create_error_response(
            "VALIDATION_ERROR",
            "Shipping address is required for Asset Checkout",
            400
        )
        return jsonify(response), status_code

    # Find asset
    asset = db_session.query(Asset).filter(Asset.serial_num == serial_number).first()
    if not asset:
        response, status_code = create_error_response(
            "VALIDATION_ERROR",
            f"Asset not found with serial number: {serial_number}",
            404
        )
        return jsonify(response), status_code

    # Find customer
    customer = db_session.query(CustomerUser).get(customer_id)
    if not customer:
        response, status_code = create_error_response(
            "VALIDATION_ERROR",
            f"Customer not found with ID: {customer_id}",
            404
        )
        return jsonify(response), status_code

    company_name = customer.company.name if customer.company else 'N/A'

    subject = f"Asset Checkout - {asset.model} to {customer.name}"
    description = f"""Asset Checkout Details:
Serial Number: {serial_number}
Model: {asset.model}
Asset Tag: {asset.asset_tag}

Customer Information:
Name: {customer.name}
Company: {company_name}
Email: {customer.email}
Contact: {customer.contact_number}

Shipping Information:
Address: {shipping_address}
Tracking Number: {shipping_tracking if shipping_tracking else 'Not provided'}
Shipping Method: claw

Additional Notes:
{notes}"""

    try:
        ticket_id = ticket_store.create_ticket(
            subject=subject,
            description=description,
            requester_id=user_id,
            category=TicketCategory.ASSET_CHECKOUT_CLAW,
            priority=priority,
            asset_id=asset.id,
            customer_id=customer_id,
            shipping_address=shipping_address,
            shipping_tracking=shipping_tracking if shipping_tracking else None,
            shipping_carrier='claw',
            queue_id=queue_id,
            notes=notes,
            case_owner_id=user_id
        )

        # Create ticket-asset relationship
        existing_check = text("""
            SELECT COUNT(*) FROM ticket_assets
            WHERE ticket_id = :ticket_id AND asset_id = :asset_id
        """)
        existing_count = db_session.execute(existing_check, {"ticket_id": ticket_id, "asset_id": asset.id}).scalar()

        if existing_count == 0:
            insert_stmt = text("""
                INSERT INTO ticket_assets (ticket_id, asset_id)
                VALUES (:ticket_id, :asset_id)
            """)
            db_session.execute(insert_stmt, {"ticket_id": ticket_id, "asset_id": asset.id})

        # Update asset status and assign to customer
        asset.customer_id = customer_id
        asset.status = AssetStatus.DEPLOYED

        # Create asset transaction
        transaction = AssetTransaction(
            asset_id=asset.id,
            transaction_type='checkout',
            customer_id=customer_id,
            notes=f'Asset checkout via mobile ticket #{ticket_id}',
            transaction_date=datetime.utcnow()
        )
        transaction.user_id = user_id
        db_session.add(transaction)

        db_session.commit()

        return jsonify({
            'success': True,
            'message': 'Ticket created successfully',
            'data': {
                'ticket_id': ticket_id,
                'display_id': f'TKT-{ticket_id:06d}',
                'subject': subject,
                'status': 'open'
            }
        }), 200

    except Exception as e:
        db_session.rollback()
        raise


def _create_asset_return_ticket(data, user_id, db_session):
    """Create Asset Return (claw) ticket"""
    from models.ticket import TicketCategory
    from models.customer_user import CustomerUser
    from utils.store_instances import ticket_store
    from sqlalchemy.orm import joinedload

    customer_id = data.get('customer_id')
    return_address = data.get('return_address') or data.get('shipping_address')
    outbound_tracking = data.get('outbound_tracking') or data.get('shipping_tracking', '')
    inbound_tracking = data.get('inbound_tracking') or data.get('return_tracking', '')
    damage_description = data.get('damage_description', '')
    return_description = data.get('return_description', '')
    subject = data.get('subject', '')
    priority = data.get('priority', 'Medium')
    queue_id = data.get('queue_id')
    notes = data.get('notes', '')

    # Validate required fields
    if not customer_id:
        response, status_code = create_error_response(
            "VALIDATION_ERROR",
            "Customer ID is required for Asset Return",
            400
        )
        return jsonify(response), status_code

    if not return_address:
        response, status_code = create_error_response(
            "VALIDATION_ERROR",
            "Return address is required for Asset Return",
            400
        )
        return jsonify(response), status_code

    # Find customer with company
    customer = db_session.query(CustomerUser).options(
        joinedload(CustomerUser.company)
    ).filter(CustomerUser.id == customer_id).first()

    if not customer:
        response, status_code = create_error_response(
            "VALIDATION_ERROR",
            f"Customer not found with ID: {customer_id}",
            404
        )
        return jsonify(response), status_code

    company_name = customer.company.name if customer.company else 'N/A'

    if not subject:
        subject = f"Asset Return - {customer.name}"

    description = f"""Asset Return (Claw) Details:
Customer Information:
Name: {customer.name}
Company: {company_name}
Email: {customer.email}
Contact: {customer.contact_number}

Return Information:
Address: {return_address}
Outbound Tracking Number: {outbound_tracking if outbound_tracking else 'Not provided yet'}
Inbound Tracking Number: {inbound_tracking if inbound_tracking else 'Not provided yet'}
Shipping Method: Claw (Ship24)

Reported Issue:
{damage_description if damage_description else 'None reported'}

Device Condition:
{return_description if return_description else 'Not specified'}

Additional Notes:
{notes}"""

    try:
        ticket_id = ticket_store.create_ticket(
            subject=subject,
            description=description,
            requester_id=user_id,
            category=TicketCategory.ASSET_RETURN_CLAW,
            priority=priority,
            asset_id=None,
            customer_id=customer_id,
            shipping_address=return_address,
            shipping_tracking=outbound_tracking if outbound_tracking else None,
            shipping_carrier='claw',
            return_tracking=inbound_tracking if inbound_tracking else None,
            queue_id=queue_id,
            notes=notes,
            return_description=return_description,
            damage_description=damage_description if damage_description else None,
            case_owner_id=user_id
        )

        return jsonify({
            'success': True,
            'message': 'Ticket created successfully',
            'data': {
                'ticket_id': ticket_id,
                'display_id': f'TKT-{ticket_id:06d}',
                'subject': subject,
                'status': 'open'
            }
        }), 200

    except Exception as e:
        db_session.rollback()
        raise


def _create_asset_intake_ticket(data, user_id, db_session):
    """Create Asset Intake ticket"""
    from models.ticket import TicketCategory
    from utils.store_instances import ticket_store

    title = data.get('title') or data.get('subject')
    description = data.get('description', '')
    priority = data.get('priority', 'Medium')
    queue_id = data.get('queue_id')
    notes = data.get('notes', '')

    # Validate required fields
    if not title:
        response, status_code = create_error_response(
            "VALIDATION_ERROR",
            "Title is required for Asset Intake",
            400
        )
        return jsonify(response), status_code

    if not description:
        response, status_code = create_error_response(
            "VALIDATION_ERROR",
            "Description is required for Asset Intake",
            400
        )
        return jsonify(response), status_code

    full_description = f"""Asset Intake Details:
Title: {title}

Description:
{description}

Additional Notes:
{notes}"""

    try:
        ticket_id = ticket_store.create_ticket(
            subject=title,
            description=full_description,
            requester_id=user_id,
            category=TicketCategory.ASSET_INTAKE,
            priority=priority,
            queue_id=queue_id,
            notes=notes,
            case_owner_id=user_id
        )

        return jsonify({
            'success': True,
            'message': 'Ticket created successfully',
            'data': {
                'ticket_id': ticket_id,
                'display_id': f'TKT-{ticket_id:06d}',
                'subject': title,
                'status': 'open'
            }
        }), 200

    except Exception as e:
        db_session.rollback()
        raise


def _create_internal_transfer_ticket(data, user_id, db_session):
    """Create Internal Transfer ticket"""
    from models.ticket import TicketCategory, Ticket
    from models.customer_user import CustomerUser
    from models.asset import Asset
    from utils.store_instances import ticket_store
    from sqlalchemy.orm import joinedload

    offboarding_customer_id = data.get('offboarding_customer_id')
    offboarding_details = data.get('offboarding_details', '')
    offboarding_address = data.get('offboarding_address', '')
    onboarding_customer_id = data.get('onboarding_customer_id')
    onboarding_address = data.get('onboarding_address', '')
    transfer_tracking = data.get('transfer_tracking', '')
    serial_number = data.get('serial_number', '')
    priority = data.get('priority', 'Medium')
    queue_id = data.get('queue_id')
    notes = data.get('notes', '')

    # Validate required fields
    if not offboarding_customer_id:
        response, status_code = create_error_response(
            "VALIDATION_ERROR",
            "Offboarding customer ID is required for Internal Transfer",
            400
        )
        return jsonify(response), status_code

    if not offboarding_details:
        response, status_code = create_error_response(
            "VALIDATION_ERROR",
            "Offboarding device details are required for Internal Transfer",
            400
        )
        return jsonify(response), status_code

    if not offboarding_address:
        response, status_code = create_error_response(
            "VALIDATION_ERROR",
            "Offboarding address is required for Internal Transfer",
            400
        )
        return jsonify(response), status_code

    if not onboarding_customer_id:
        response, status_code = create_error_response(
            "VALIDATION_ERROR",
            "Onboarding customer ID is required for Internal Transfer",
            400
        )
        return jsonify(response), status_code

    if not onboarding_address:
        response, status_code = create_error_response(
            "VALIDATION_ERROR",
            "Onboarding address is required for Internal Transfer",
            400
        )
        return jsonify(response), status_code

    # Get offboarding customer
    offboarding_customer = db_session.query(CustomerUser).options(
        joinedload(CustomerUser.company)
    ).filter(CustomerUser.id == offboarding_customer_id).first()

    if not offboarding_customer:
        response, status_code = create_error_response(
            "VALIDATION_ERROR",
            f"Offboarding customer not found with ID: {offboarding_customer_id}",
            404
        )
        return jsonify(response), status_code

    # Get onboarding customer
    onboarding_customer = db_session.query(CustomerUser).options(
        joinedload(CustomerUser.company)
    ).filter(CustomerUser.id == onboarding_customer_id).first()

    if not onboarding_customer:
        response, status_code = create_error_response(
            "VALIDATION_ERROR",
            f"Onboarding customer not found with ID: {onboarding_customer_id}",
            404
        )
        return jsonify(response), status_code

    offboarding_company = offboarding_customer.company.name if offboarding_customer.company else 'N/A'
    onboarding_company = onboarding_customer.company.name if onboarding_customer.company else 'N/A'

    # Find asset if serial provided
    asset = None
    if serial_number:
        asset = db_session.query(Asset).filter(Asset.serial_num == serial_number).first()

    subject = f"Internal Transfer: {offboarding_customer.name} -> {onboarding_customer.name}"
    description = f"""Internal Transfer Details:

OFFBOARDING
Customer: {offboarding_customer.name}
Company: {offboarding_company}
Device Details: {offboarding_details}
Address: {offboarding_address}

ONBOARDING
Customer: {onboarding_customer.name}
Company: {onboarding_company}
Address: {onboarding_address}

Tracking Link: {transfer_tracking if transfer_tracking else 'Not provided'}

Additional Notes:
{notes if notes else 'None'}"""

    try:
        ticket_id = ticket_store.create_ticket(
            subject=subject,
            description=description,
            requester_id=user_id,
            category=TicketCategory.INTERNAL_TRANSFER,
            priority=priority,
            asset_id=asset.id if asset else None,
            customer_id=offboarding_customer_id,
            shipping_address=onboarding_address,
            shipping_tracking=transfer_tracking if transfer_tracking else None,
            queue_id=queue_id,
            notes=notes,
            case_owner_id=user_id
        )

        # Update ticket with offboarding/onboarding fields
        ticket = db_session.query(Ticket).get(ticket_id)
        if ticket:
            ticket.offboarding_customer_id = int(offboarding_customer_id)
            ticket.onboarding_customer_id = int(onboarding_customer_id)
            ticket.offboarding_details = offboarding_details
            ticket.offboarding_address = offboarding_address
            ticket.onboarding_address = onboarding_address
            db_session.commit()

        return jsonify({
            'success': True,
            'message': 'Ticket created successfully',
            'data': {
                'ticket_id': ticket_id,
                'display_id': f'TKT-{ticket_id:06d}',
                'subject': subject,
                'status': 'open'
            }
        }), 200

    except Exception as e:
        db_session.rollback()
        raise


def _create_quote_ticket(data, user_id, db_session, category):
    """Create quote ticket (Bulk Delivery, Repair Quote, ITAD Quote)"""
    from models.ticket import TicketCategory
    from models.asset import Asset
    from utils.store_instances import ticket_store

    subject = data.get('subject', '')
    description = data.get('description', '')
    serial_number = data.get('serial_number', '')
    priority = data.get('priority', 'Medium')
    queue_id = data.get('queue_id')
    notes = data.get('notes', '')

    # Validate required fields
    if not subject:
        response, status_code = create_error_response(
            "VALIDATION_ERROR",
            "Subject is required for quote tickets",
            400
        )
        return jsonify(response), status_code

    if not description:
        response, status_code = create_error_response(
            "VALIDATION_ERROR",
            "Description is required for quote tickets",
            400
        )
        return jsonify(response), status_code

    # Map category string to enum
    category_map = {
        'BULK_DELIVERY_QUOTATION': TicketCategory.BULK_DELIVERY_QUOTATION,
        'REPAIR_QUOTE': TicketCategory.REPAIR_QUOTE,
        'ITAD_QUOTE': TicketCategory.ITAD_QUOTE
    }

    category_enum = category_map.get(category)
    if not category_enum:
        response, status_code = create_error_response(
            "VALIDATION_ERROR",
            f"Invalid quote category: {category}",
            400
        )
        return jsonify(response), status_code

    # Find asset if serial provided
    asset = None
    if serial_number:
        asset = db_session.query(Asset).filter(Asset.serial_num == serial_number).first()

    full_description = f"""{category.replace('_', ' ').title()} Request:

{description}

Additional Notes:
{notes}"""

    try:
        ticket_id = ticket_store.create_ticket(
            subject=subject,
            description=full_description,
            requester_id=user_id,
            category=category_enum,
            priority=priority,
            asset_id=asset.id if asset else None,
            queue_id=queue_id,
            notes=notes,
            case_owner_id=user_id
        )

        return jsonify({
            'success': True,
            'message': 'Ticket created successfully',
            'data': {
                'ticket_id': ticket_id,
                'display_id': f'TKT-{ticket_id:06d}',
                'subject': subject,
                'status': 'open'
            }
        }), 200

    except Exception as e:
        db_session.rollback()
        raise


@api_bp.route('/customers', methods=['GET'])
def get_customers_list():
    """
    Get list of customers for ticket creation

    Returns customers with company information.
    Accepts both X-API-Key + Bearer token (iOS) or Bearer token only.
    """
    try:
        from models.customer_user import CustomerUser
        from models.company import Company
        from sqlalchemy.orm import joinedload

        # Get user from JWT (supports both iOS API Key + JWT and JWT only)
        user_id, error = get_authenticated_user_for_tickets()
        if error:
            return jsonify({
                'success': False,
                'error': error,
                'message': 'Authentication required'
            }), 401

        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 50, type=int), 100)
        search = request.args.get('search', '')
        company_id = request.args.get('company_id', type=int)

        db_session = db_manager.get_session()
        try:
            query = db_session.query(CustomerUser).options(
                joinedload(CustomerUser.company)
            )

            # Apply search filter
            if search:
                search_term = f"%{search}%"
                query = query.filter(
                    (CustomerUser.name.ilike(search_term)) |
                    (CustomerUser.email.ilike(search_term))
                )

            # Apply company filter
            if company_id:
                query = query.filter(CustomerUser.company_id == company_id)

            # Order by name
            query = query.order_by(CustomerUser.name)

            # Get total
            total = query.count()

            # Apply pagination
            customers = query.offset((page - 1) * per_page).limit(per_page).all()

            customers_data = []
            for customer in customers:
                customers_data.append({
                    'id': customer.id,
                    'name': customer.name,
                    'email': customer.email,
                    'contact_number': customer.contact_number,
                    'address': customer.address,
                    'company_id': customer.company_id,
                    'company_name': customer.company.name if customer.company else None
                })

            pagination = {
                'page': page,
                'per_page': per_page,
                'total': total,
                'has_next': (page * per_page) < total,
                'has_prev': page > 1
            }

            return jsonify(create_success_response(
                customers_data,
                f"Retrieved {len(customers_data)} customers",
                {"pagination": pagination}
            ))

        finally:
            db_session.close()

    except Exception as e:
        response, status_code = create_error_response(
            "INTERNAL_ERROR",
            f"Error retrieving customers: {str(e)}",
            500
        )
        return jsonify(response), status_code


@api_bp.route('/assets/search', methods=['GET'])
def search_assets_mobile():
    """
    Search assets by serial number or asset tag

    Used for ticket creation to find assets.
    Accepts both X-API-Key + Bearer token (iOS) or Bearer token only.
    """
    try:
        from models.asset import Asset

        # Get user from JWT (supports both iOS API Key + JWT and JWT only)
        user_id, error = get_authenticated_user_for_tickets()
        if error:
            return jsonify({
                'success': False,
                'error': error,
                'message': 'Authentication required'
            }), 401

        search = request.args.get('q', '') or request.args.get('search', '')
        limit = min(request.args.get('limit', 20, type=int), 50)

        if not search or len(search) < 2:
            response, status_code = create_error_response(
                "VALIDATION_ERROR",
                "Search query must be at least 2 characters",
                400
            )
            return jsonify(response), status_code

        db_session = db_manager.get_session()
        try:
            search_term = f"%{search}%"
            assets = db_session.query(Asset).filter(
                (Asset.serial_num.ilike(search_term)) |
                (Asset.asset_tag.ilike(search_term)) |
                (Asset.name.ilike(search_term))
            ).limit(limit).all()

            assets_data = []
            for asset in assets:
                assets_data.append({
                    'id': asset.id,
                    'serial_number': asset.serial_num,
                    'asset_tag': asset.asset_tag,
                    'name': asset.name,
                    'model': asset.model,
                    'manufacturer': getattr(asset, 'manufacturer', None),
                    'status': asset.status.value if hasattr(asset.status, 'value') else str(asset.status) if asset.status else None,
                    'image_url': get_asset_image_url_simple(asset)
                })

            return jsonify(create_success_response(
                assets_data,
                f"Found {len(assets_data)} assets"
            ))

        finally:
            db_session.close()

    except Exception as e:
        response, status_code = create_error_response(
            "INTERNAL_ERROR",
            f"Error searching assets: {str(e)}",
            500
        )
        return jsonify(response), status_code


@api_bp.route('/queues', methods=['GET'])
def get_queues_list():
    """
    Get list of queues for ticket creation

    Returns available queues.
    Accepts both X-API-Key + Bearer token (iOS) or Bearer token only.
    """
    try:
        # Get user from JWT (supports both iOS API Key + JWT and JWT only)
        user_id, error = get_authenticated_user_for_tickets()
        if error:
            return jsonify({
                'success': False,
                'error': error,
                'message': 'Authentication required'
            }), 401

        db_session = db_manager.get_session()
        try:
            queues = db_session.query(Queue).order_by(Queue.name).all()

            queues_data = []
            for queue in queues:
                queues_data.append({
                    'id': queue.id,
                    'name': queue.name,
                    'description': getattr(queue, 'description', None)
                })

            return jsonify({
                'success': True,
                'message': f"Retrieved {len(queues_data)} queues",
                'data': queues_data
            })

        finally:
            db_session.close()

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'message': 'Failed to retrieve queues'
        }), 500


# ============================================================
# DEBUG ENDPOINT - Check and fix Asset Return ticket status
# ============================================================

@api_bp.route('/debug/fix-ticket/<int:ticket_id>', methods=['GET'])
def debug_fix_ticket(ticket_id):
    """Debug endpoint to check and fix Asset Return ticket status"""
    from models.ticket import TicketStatus, TicketCategory

    db_manager = DatabaseManager()
    db_session = db_manager.get_session()

    try:
        ticket = db_session.query(Ticket).get(ticket_id)
        if not ticket:
            return jsonify({'error': 'Ticket not found'}), 404

        result = {
            'ticket_id': ticket.id,
            'category': ticket.category.name if ticket.category else None,
            'current_status': ticket.status.name if ticket.status else None,
            'shipping_status': ticket.shipping_status,
            'replacement_status': ticket.replacement_status,
        }

        # Check conditions - match template logic: check for "received" or "delivered" (case-insensitive)
        return_received = ticket.shipping_status and ("received" in ticket.shipping_status.lower() or "delivered" in ticket.shipping_status.lower())
        replacement_received = ticket.replacement_status and ("received" in ticket.replacement_status.lower() or "delivered" in ticket.replacement_status.lower())

        result['return_received'] = return_received
        result['replacement_received'] = replacement_received
        result['should_be_resolved'] = return_received and replacement_received

        # Auto-fix if needed
        if ticket.category == TicketCategory.ASSET_RETURN_CLAW:
            if return_received and replacement_received and ticket.status != TicketStatus.RESOLVED:
                old_status = ticket.status.name if ticket.status else None
                ticket.status = TicketStatus.RESOLVED
                db_session.commit()
                result['fixed'] = True
                result['old_status'] = old_status
                result['new_status'] = 'RESOLVED'
            else:
                result['fixed'] = False
                result['reason'] = 'Already resolved or conditions not met'
        else:
            result['fixed'] = False
            result['reason'] = 'Not an Asset Return (Claw) ticket'

        return jsonify(result)

    except Exception as e:
        db_session.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        db_session.close()