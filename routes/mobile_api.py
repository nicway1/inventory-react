"""
Mobile API Routes for iOS App Integration

This module provides RESTful API endpoints specifically designed for mobile app access:
- Authentication and user management
- Ticket viewing and basic operations  
- Inventory access with mobile-optimized responses
- User profile and role information
"""

from flask import Blueprint, request, jsonify, session
from flask_login import login_user, logout_user, current_user
from werkzeug.security import check_password_hash
from datetime import datetime, timedelta
import jwt
import logging

from models.user import User, UserType
from models.ticket import Ticket, TicketStatus, TicketPriority, TicketCategory
from models.asset import Asset, AssetStatus
from models.queue import Queue
from utils.db_manager import DatabaseManager
from utils.auth_decorators import login_required

# Set up logging
logger = logging.getLogger(__name__)

# Create Mobile API blueprint
mobile_api_bp = Blueprint('mobile_api', __name__, url_prefix='/api/mobile/v1')
db_manager = DatabaseManager()

# Helper function to create JWT token
def create_mobile_token(user):
    """Create JWT token for mobile authentication"""
    payload = {
        'user_id': user.id,
        'username': user.username,
        'user_type': user.user_type.value,
        'exp': datetime.utcnow() + timedelta(days=30),  # 30 day expiry
        'iat': datetime.utcnow()
    }
    
    # Use Flask secret key for JWT encoding
    from flask import current_app
    secret_key = current_app.config.get('SECRET_KEY', 'fallback-secret-key')
    
    return jwt.encode(payload, secret_key, algorithm='HS256')

def verify_mobile_token(token):
    """Verify JWT token and return user"""
    try:
        from flask import current_app
        secret_key = current_app.config.get('SECRET_KEY', 'fallback-secret-key')
        
        payload = jwt.decode(token, secret_key, algorithms=['HS256'])
        user_id = payload['user_id']
        
        db_session = db_manager.get_session()
        try:
            user = db_session.query(User).filter(User.id == user_id).first()
            return user
        finally:
            db_session.close()
            
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

# Authentication decorator for mobile API
def mobile_auth_required(f):
    """Decorator to require mobile authentication"""
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Missing or invalid authorization header'}), 401
        
        token = auth_header.split(' ')[1]
        user = verify_mobile_token(token)
        
        if not user:
            return jsonify({'error': 'Invalid or expired token'}), 401
        
        # Set current user for the request
        request.current_mobile_user = user
        return f(*args, **kwargs)
    
    decorated_function.__name__ = f.__name__
    return decorated_function

@mobile_api_bp.route('/auth/login', methods=['POST'])
def mobile_login():
    """
    Mobile login endpoint
    
    POST /api/mobile/v1/auth/login
    Body: {
        "username": "user@example.com",
        "password": "password123"
    }
    
    Response: {
        "success": true,
        "token": "jwt_token_here",
        "user": {
            "id": 1,
            "username": "user@example.com", 
            "first_name": "John",
            "last_name": "Doe",
            "user_type": "SUPERVISOR",
            "permissions": {...}
        }
    }
    """
    try:
        data = request.get_json()
        
        if not data or not data.get('username') or not data.get('password'):
            return jsonify({
                'success': False,
                'error': 'Username and password are required'
            }), 400
        
        username = data['username'].strip()
        password = data['password']
        
        # Find user by username/email
        db_session = db_manager.get_session()
        try:
            user = db_session.query(User).filter(User.username == username).first()
            
            if not user or not user.check_password(password):
                return jsonify({
                    'success': False,
                    'error': 'Invalid username or password'
                }), 401
            
            # Create mobile token
            token = create_mobile_token(user)
            
            # Get user permissions
            permissions = {}
            if user.permissions:
                permission_fields = [attr for attr in dir(user.permissions) if attr.startswith('can_')]
                permissions = {field: getattr(user.permissions, field) for field in permission_fields}
            
            return jsonify({
                'success': True,
                'token': token,
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'user_type': user.user_type.value,
                    'email': user.email,
                    'is_admin': user.is_admin,
                    'is_supervisor': user.is_supervisor,
                    'permissions': permissions
                }
            })
            
        finally:
            db_session.close()
            
    except Exception as e:
        logger.error(f"Mobile login error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Login failed'
        }), 500

@mobile_api_bp.route('/auth/me', methods=['GET'])
@mobile_auth_required
def get_current_user():
    """
    Get current user information
    
    GET /api/mobile/v1/auth/me
    Headers: Authorization: Bearer <token>
    
    Response: {
        "success": true,
        "user": {
            "id": 1,
            "username": "user@example.com",
            "first_name": "John", 
            "last_name": "Doe",
            "user_type": "SUPERVISOR",
            "permissions": {...}
        }
    }
    """
    try:
        user = request.current_mobile_user
        
        # Get user permissions
        permissions = {}
        if user.permissions:
            permission_fields = [attr for attr in dir(user.permissions) if attr.startswith('can_')]
            permissions = {field: getattr(user.permissions, field) for field in permission_fields}
        
        return jsonify({
            'success': True,
            'user': {
                'id': user.id,
                'username': user.username,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'user_type': user.user_type.value,
                'email': user.email,
                'is_admin': user.is_admin,
                'is_supervisor': user.is_supervisor,
                'permissions': permissions
            }
        })
        
    except Exception as e:
        logger.error(f"Get current user error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to get user information'
        }), 500

@mobile_api_bp.route('/tickets', methods=['GET'])
@mobile_auth_required
def get_tickets():
    """
    Get tickets for current user
    
    GET /api/mobile/v1/tickets?page=1&limit=20&status=OPEN
    Headers: Authorization: Bearer <token>
    
    Response: {
        "success": true,
        "tickets": [...],
        "pagination": {
            "page": 1,
            "limit": 20,
            "total": 100,
            "pages": 5
        }
    }
    """
    try:
        user = request.current_mobile_user
        
        # Get pagination parameters
        page = request.args.get('page', 1, type=int)
        limit = min(request.args.get('limit', 20, type=int), 100)  # Max 100 per page
        status_filter = request.args.get('status', None)
        
        db_session = db_manager.get_session()
        try:
            # Build base query based on user permissions
            if user.user_type == UserType.SUPER_ADMIN:
                query = db_session.query(Ticket)
            else:
                # Users can see tickets they created or are assigned to
                query = db_session.query(Ticket).filter(
                    (Ticket.requester_id == user.id) | 
                    (Ticket.assigned_to_id == user.id)
                )
            
            # Apply status filter
            if status_filter:
                try:
                    status_enum = TicketStatus[status_filter.upper()]
                    query = query.filter(Ticket.status == status_enum)
                except KeyError:
                    pass  # Invalid status, ignore filter
            
            # Get total count
            total = query.count()
            
            # Apply pagination
            offset = (page - 1) * limit
            tickets = query.order_by(Ticket.created_at.desc()).offset(offset).limit(limit).all()
            
            # Format tickets for mobile
            ticket_list = []
            for ticket in tickets:
                ticket_data = {
                    'id': ticket.id,
                    'display_id': ticket.display_id,
                    'subject': ticket.subject,
                    'description': ticket.description[:200] + '...' if len(ticket.description) > 200 else ticket.description,
                    'status': ticket.status.value if ticket.status else None,
                    'priority': ticket.priority.value if ticket.priority else None,
                    'category': ticket.category.value if ticket.category else None,
                    'created_at': ticket.created_at.isoformat() if ticket.created_at else None,
                    'updated_at': ticket.updated_at.isoformat() if ticket.updated_at else None,
                    'requester': {
                        'id': ticket.requester.id,
                        'name': f"{ticket.requester.first_name} {ticket.requester.last_name}",
                        'email': ticket.requester.email
                    } if ticket.requester else None,
                    'assigned_to': {
                        'id': ticket.assigned_to.id,
                        'name': f"{ticket.assigned_to.first_name} {ticket.assigned_to.last_name}",
                        'email': ticket.assigned_to.email
                    } if ticket.assigned_to else None,
                    'queue': {
                        'id': ticket.queue.id,
                        'name': ticket.queue.name
                    } if ticket.queue else None,
                    # Basic progress info for list view
                    'has_assets': bool(ticket.assets and len(ticket.assets) > 0),
                    'has_tracking': bool(ticket.shipping_tracking),
                    'customer_name': ticket.customer.name if ticket.customer else None
                }
                ticket_list.append(ticket_data)
            
            pages = (total + limit - 1) // limit  # Ceiling division
            
            return jsonify({
                'success': True,
                'tickets': ticket_list,
                'pagination': {
                    'page': page,
                    'limit': limit,
                    'total': total,
                    'pages': pages
                }
            })
            
        finally:
            db_session.close()
            
    except Exception as e:
        logger.error(f"Get tickets error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to get tickets'
        }), 500

@mobile_api_bp.route('/tickets/<int:ticket_id>', methods=['GET'])
@mobile_auth_required
def get_ticket_detail(ticket_id):
    """
    Get detailed ticket information including Case Progress, Customer Info, and Tech Assets

    GET /api/mobile/v1/tickets/<ticket_id>
    Headers: Authorization: Bearer <token>

    Response: {
        "success": true,
        "ticket": {
            "id": 123,
            "display_id": "TIC-123",
            "subject": "...",
            "description": "...",
            "status": "OPEN",
            "priority": "MEDIUM",
            "category": "ASSET_CHECKOUT_MAIN",
            "created_at": "2023-10-01T10:00:00",
            "updated_at": "2023-10-01T15:30:00",
            "requester": {...},
            "assigned_to": {...},
            "queue": {...},
            "customer": {...},
            "assets": [...],
            "case_progress": {
                "case_created": true,
                "assets_assigned": false,
                "tracking_added": false,
                "delivered": false
            },
            "tracking": {...},
            "comments": [...]
        }
    }
    """
    try:
        user = request.current_mobile_user

        db_session = db_manager.get_session()
        try:
            # Get ticket with proper permissions check
            if user.user_type == UserType.SUPER_ADMIN:
                ticket = db_session.query(Ticket).filter(Ticket.id == ticket_id).first()
            else:
                # Users can only see tickets they created or are assigned to
                ticket = db_session.query(Ticket).filter(
                    Ticket.id == ticket_id,
                    (Ticket.requester_id == user.id) | (Ticket.assigned_to_id == user.id)
                ).first()

            if not ticket:
                return jsonify({
                    'success': False,
                    'error': 'Ticket not found or access denied'
                }), 404

            # Build comprehensive ticket data
            ticket_data = {
                'id': ticket.id,
                'display_id': ticket.display_id,
                'subject': ticket.subject,
                'description': ticket.description,
                'status': ticket.status.value if ticket.status else None,
                'priority': ticket.priority.value if ticket.priority else None,
                'category': ticket.category.value if ticket.category else None,
                'created_at': ticket.created_at.isoformat() if ticket.created_at else None,
                'updated_at': ticket.updated_at.isoformat() if ticket.updated_at else None,
                'notes': ticket.notes,
                'requester': {
                    'id': ticket.requester.id,
                    'name': f"{ticket.requester.first_name} {ticket.requester.last_name}",
                    'email': ticket.requester.email,
                    'username': ticket.requester.username
                } if ticket.requester else None,
                'assigned_to': {
                    'id': ticket.assigned_to.id,
                    'name': f"{ticket.assigned_to.first_name} {ticket.assigned_to.last_name}",
                    'email': ticket.assigned_to.email,
                    'username': ticket.assigned_to.username
                } if ticket.assigned_to else None,
                'queue': {
                    'id': ticket.queue.id,
                    'name': ticket.queue.name
                } if ticket.queue else None,

                # Customer Information
                'customer': {
                    'id': ticket.customer.id,
                    'name': ticket.customer.name,
                    'email': ticket.customer.email,
                    'phone': ticket.customer.phone,
                    'address': ticket.customer.address,
                    'company': {
                        'id': ticket.customer.company.id,
                        'name': ticket.customer.company.name
                    } if ticket.customer and ticket.customer.company else None
                } if ticket.customer else None,

                # Tech Assets
                'assets': [{
                    'id': asset.id,
                    'serial_number': asset.serial_num,
                    'asset_tag': asset.asset_tag,
                    'model': asset.model,
                    'manufacturer': asset.manufacturer,
                    'status': asset.status.value if asset.status else None
                } for asset in ticket.assets] if ticket.assets else [],

                # Case Progress - determine based on ticket state
                'case_progress': {
                    'case_created': bool(ticket.created_at),
                    'assets_assigned': bool(ticket.assets and len(ticket.assets) > 0),
                    'tracking_added': bool(ticket.shipping_tracking),
                    'delivered': bool(ticket.shipping_status and 'delivered' in ticket.shipping_status.lower())
                },

                # Tracking Information
                'tracking': {
                    'shipping_tracking': ticket.shipping_tracking,
                    'shipping_carrier': ticket.shipping_carrier,
                    'shipping_status': ticket.shipping_status,
                    'shipping_address': ticket.shipping_address,
                    'return_tracking': ticket.return_tracking,
                    'return_status': ticket.return_status
                },

                # Comments
                'comments': [{
                    'id': comment.id,
                    'content': comment.content,
                    'created_at': comment.created_at.isoformat() if comment.created_at else None,
                    'user': {
                        'id': comment.user.id,
                        'name': f"{comment.user.first_name} {comment.user.last_name}",
                        'username': comment.user.username
                    } if comment.user else None
                } for comment in ticket.comments] if hasattr(ticket, 'comments') and ticket.comments else []
            }

            return jsonify({
                'success': True,
                'ticket': ticket_data
            })

        finally:
            db_session.close()

    except Exception as e:
        logger.error(f"Error getting ticket detail: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to get ticket detail'
        }), 500

@mobile_api_bp.route('/inventory', methods=['GET'])
@mobile_auth_required  
def get_inventory():
    """
    Get inventory assets
    
    GET /api/mobile/v1/inventory?page=1&limit=20&status=DEPLOYED&search=laptop
    Headers: Authorization: Bearer <token>
    
    Response: {
        "success": true,
        "assets": [...],
        "pagination": {
            "page": 1,
            "limit": 20, 
            "total": 100,
            "pages": 5
        }
    }
    """
    try:
        user = request.current_mobile_user
        
        # Check permissions
        if not user.permissions or not user.permissions.can_view_assets:
            return jsonify({
                'success': False,
                'error': 'No permission to view inventory'
            }), 403
        
        # Get parameters
        page = request.args.get('page', 1, type=int)
        limit = min(request.args.get('limit', 20, type=int), 100)
        status_filter = request.args.get('status', None)
        search = request.args.get('search', None)
        
        db_session = db_manager.get_session()
        try:
            # Build query based on user permissions
            query = db_session.query(Asset)
            
            # Apply country restrictions for COUNTRY_ADMIN
            if user.user_type == UserType.COUNTRY_ADMIN and user.assigned_country:
                query = query.filter(Asset.country == user.assigned_country.value)
            
            # Apply status filter
            if status_filter:
                try:
                    status_enum = AssetStatus[status_filter.upper()]
                    query = query.filter(Asset.status == status_enum)
                except KeyError:
                    pass
            
            # Apply search filter
            if search:
                search_term = f"%{search}%"
                query = query.filter(
                    (Asset.name.ilike(search_term)) |
                    (Asset.asset_tag.ilike(search_term)) |
                    (Asset.serial_num.ilike(search_term)) |
                    (Asset.model.ilike(search_term))
                )
            
            # Get total count
            total = query.count()
            
            # Apply pagination
            offset = (page - 1) * limit
            assets = query.order_by(Asset.created_at.desc()).offset(offset).limit(limit).all()
            
            # Format assets for mobile
            asset_list = []
            for asset in assets:
                asset_data = {
                    'id': asset.id,
                    'asset_tag': asset.asset_tag,
                    'name': asset.name,
                    'model': asset.model,
                    'serial_num': asset.serial_num,
                    'status': asset.status.value if asset.status else None,
                    'asset_type': asset.asset_type,
                    'manufacturer': asset.manufacturer,
                    'location': asset.location,
                    'country': asset.country,
                    'assigned_to': {
                        'id': asset.assigned_to.id,
                        'name': f"{asset.assigned_to.first_name} {asset.assigned_to.last_name}",
                        'email': asset.assigned_to.email
                    } if asset.assigned_to else None,
                    'customer_user': {
                        'id': asset.customer_user.id,
                        'name': asset.customer_user.name,
                        'email': asset.customer_user.email
                    } if asset.customer_user else None
                }
                asset_list.append(asset_data)
            
            pages = (total + limit - 1) // limit
            
            return jsonify({
                'success': True,
                'assets': asset_list,
                'pagination': {
                    'page': page,
                    'limit': limit,
                    'total': total,
                    'pages': pages
                }
            })
            
        finally:
            db_session.close()
            
    except Exception as e:
        logger.error(f"Get inventory error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to get inventory'
        }), 500

@mobile_api_bp.route('/dashboard', methods=['GET'])
@mobile_auth_required
def get_dashboard():
    """
    Get dashboard statistics for mobile
    
    GET /api/mobile/v1/dashboard
    Headers: Authorization: Bearer <token>
    
    Response: {
        "success": true,
        "stats": {
            "total_tickets": 50,
            "open_tickets": 25,
            "assigned_tickets": 10,
            "total_assets": 100,
            "available_assets": 75
        }
    }
    """
    try:
        user = request.current_mobile_user
        
        db_session = db_manager.get_session()
        try:
            stats = {}
            
            # Ticket statistics
            if user.user_type == UserType.SUPER_ADMIN:
                total_tickets = db_session.query(Ticket).count()
                open_tickets = db_session.query(Ticket).filter(
                    Ticket.status.notin_([TicketStatus.RESOLVED, TicketStatus.RESOLVED_DELIVERED])
                ).count()
            else:
                # User's tickets only
                user_tickets_query = db_session.query(Ticket).filter(
                    (Ticket.requester_id == user.id) | (Ticket.assigned_to_id == user.id)
                )
                total_tickets = user_tickets_query.count()
                open_tickets = user_tickets_query.filter(
                    Ticket.status.notin_([TicketStatus.RESOLVED, TicketStatus.RESOLVED_DELIVERED])
                ).count()
            
            assigned_tickets = db_session.query(Ticket).filter(Ticket.assigned_to_id == user.id).count()
            
            stats.update({
                'total_tickets': total_tickets,
                'open_tickets': open_tickets,
                'assigned_tickets': assigned_tickets
            })
            
            # Asset statistics (if user has permission)
            if user.permissions and user.permissions.can_view_assets:
                asset_query = db_session.query(Asset)
                
                # Apply country restrictions
                if user.user_type == UserType.COUNTRY_ADMIN and user.assigned_country:
                    asset_query = asset_query.filter(Asset.country == user.assigned_country.value)
                
                total_assets = asset_query.count()
                available_assets = asset_query.filter(Asset.status == AssetStatus.READY_TO_DEPLOY).count()
                
                stats.update({
                    'total_assets': total_assets,
                    'available_assets': available_assets
                })
            
            return jsonify({
                'success': True,
                'stats': stats
            })
            
        finally:
            db_session.close()
            
    except Exception as e:
        logger.error(f"Get dashboard error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to get dashboard data'
        }), 500

@mobile_api_bp.route('/health', methods=['GET'])
def health_check():
    """
    Health check endpoint
    
    GET /api/mobile/v1/health
    
    Response: {
        "success": true,
        "status": "healthy",
        "timestamp": "2025-01-01T12:00:00Z"
    }
    """
    return jsonify({
        'success': True,
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat() + 'Z'
    })