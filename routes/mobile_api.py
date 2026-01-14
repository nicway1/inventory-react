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
from models.accessory import Accessory
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
        from sqlalchemy.orm import joinedload
        secret_key = current_app.config.get('SECRET_KEY', 'fallback-secret-key')

        payload = jwt.decode(token, secret_key, algorithms=['HS256'])
        user_id = payload['user_id']

        db_session = db_manager.get_session()
        try:
            # Eagerly load company relationship
            # Note: permissions is a @property, not a relationship - it queries its own session
            user = db_session.query(User).options(
                joinedload(User.company)
            ).filter(User.id == user_id).first()

            # Force load the company before session closes
            if user:
                _ = user.company

            return user
        finally:
            db_session.close()

    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

# Helper function to get full image URL
def get_full_image_url(relative_url):
    """Convert relative image URL to full URL for mobile clients"""
    if not relative_url:
        return None
    # Get base URL from request
    base_url = request.host_url.rstrip('/')
    return f"{base_url}{relative_url}"


# Helper function to get asset image URL with fallback to default product images
def get_asset_image_url(asset):
    """Get asset image URL, falling back to default product image if none set"""
    # If asset has a custom image, use it
    if asset.image_url:
        return get_full_image_url(asset.image_url)

    # Auto-detect image based on manufacturer/model
    model_lower = (asset.model or '').lower()
    name_lower = (asset.name or '').lower()
    mfg_lower = (asset.manufacturer or '').lower()

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
        return get_full_image_url(default_image)

    return None


def can_view_all_tickets(user):
    """
    Check if user can view all tickets (not just their own).
    Staff users (SUPER_ADMIN, DEVELOPER, SUPERVISOR, COUNTRY_ADMIN) can view all tickets.
    CLIENT users are restricted to only their own tickets.
    """
    # Super admins can view all
    if user.user_type == UserType.SUPER_ADMIN:
        return True
    # Staff users (non-CLIENT) can view all tickets
    if user.user_type in [UserType.DEVELOPER, UserType.SUPERVISOR, UserType.COUNTRY_ADMIN]:
        return True
    # Check permission system as fallback
    if user.permissions and hasattr(user.permissions, 'can_view_tickets') and user.permissions.can_view_tickets:
        return True
    return False


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
            "name": "user@example.com",
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
                    'name': user.username,  # Use username as display name
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
            if can_view_all_tickets(user):
                query = db_session.query(Ticket)
            else:
                # CLIENT users can only see tickets they created or are assigned to
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
                        'name': ticket.requester.username,  # Use username as display name
                        'email': ticket.requester.email
                    } if ticket.requester else None,
                    'assigned_to': {
                        'id': ticket.assigned_to.id,
                        'name': ticket.assigned_to.username,  # Use username as display name
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
            # Import joinedload for relationship loading
            from sqlalchemy.orm import joinedload

            # Get ticket with proper permissions check and load all relationships
            base_query = db_session.query(Ticket).options(
                joinedload(Ticket.requester),
                joinedload(Ticket.assigned_to),
                joinedload(Ticket.queue),
                joinedload(Ticket.customer),
                joinedload(Ticket.assets),
                joinedload(Ticket.comments)
            )

            if can_view_all_tickets(user):
                ticket = base_query.filter(Ticket.id == ticket_id).first()
            else:
                # CLIENT users can only see tickets they created or are assigned to
                ticket = base_query.filter(
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
                    'name': ticket.requester.username,  # Use username as display name
                    'email': ticket.requester.email,
                    'username': ticket.requester.username
                } if ticket.requester else None,
                'assigned_to': {
                    'id': ticket.assigned_to.id,
                    'name': ticket.assigned_to.username,  # Use username as display name
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
                    'phone': ticket.customer.contact_number,  # Fixed: use contact_number field
                    'address': ticket.customer.address,
                    'company': {
                        'id': ticket.customer.company.id,
                        'name': ticket.customer.company.name
                    } if ticket.customer.company else None
                } if ticket.customer else None,

                # Tech Assets
                'assets': [{
                    'id': asset.id,
                    'serial_number': asset.serial_num,
                    'asset_tag': asset.asset_tag,
                    'model': asset.model,
                    'manufacturer': asset.manufacturer,
                    'status': asset.status.value if asset.status else None,
                    'image_url': get_asset_image_url(asset)
                } for asset in ticket.assets] if ticket.assets else [],

                # Case Progress - determine based on ticket state
                'case_progress': {
                    'case_created': bool(ticket.created_at),
                    'assets_assigned': bool(ticket.assets and len(ticket.assets) > 0),
                    'tracking_added': bool(ticket.shipping_tracking),
                    'delivered': bool(ticket.shipping_status and 'delivered' in str(ticket.shipping_status).lower()) if ticket.shipping_status else False
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
                        'name': comment.user.username,  # Use username as display name
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
        logger.error(f"Error getting ticket detail for ticket {ticket_id}: {str(e)}")
        logger.error(f"Exception type: {type(e).__name__}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': 'Failed to get ticket detail',
            'debug_info': str(e) if logger.level <= logging.DEBUG else None
        }), 500

@mobile_api_bp.route('/inventory', methods=['GET'])
@mobile_auth_required  
def get_inventory():
    """
    Get inventory assets with optional filters

    GET /api/mobile/v1/inventory?page=1&limit=20&status=DEPLOYED&search=laptop&manufacturer=Apple&country=Singapore
    Headers: Authorization: Bearer <token>

    Query Parameters:
        page (int): Page number (default: 1)
        limit (int): Items per page (default: 20, max: 100)
        status (str): Filter by asset status (e.g., DEPLOYED, IN_STOCK)
        search (str): Text search across name, asset_tag, serial_num, model
        manufacturer (str): Filter by manufacturer (case-insensitive partial match)
        category (str): Filter by category (case-insensitive partial match)
        country (str): Filter by country (exact match)
        asset_type (str): Filter by asset type
        location_id (int): Filter by location ID
        has_assignee (str): Filter by assignment status ('true' or 'false')

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

        # Filter parameters
        status_filter = request.args.get('status', None)
        search = request.args.get('search', None)
        manufacturer_filter = request.args.get('manufacturer', None)
        category_filter = request.args.get('category', None)
        country_filter = request.args.get('country', None)
        asset_type_filter = request.args.get('asset_type', None)
        location_id_filter = request.args.get('location_id', None, type=int)
        has_assignee_filter = request.args.get('has_assignee', None)

        # Log active filters for debugging
        active_filters = []
        if status_filter:
            active_filters.append(f"status={status_filter}")
        if manufacturer_filter:
            active_filters.append(f"manufacturer={manufacturer_filter}")
        if category_filter:
            active_filters.append(f"category={category_filter}")
        if country_filter:
            active_filters.append(f"country={country_filter}")
        if asset_type_filter:
            active_filters.append(f"asset_type={asset_type_filter}")
        if location_id_filter:
            active_filters.append(f"location_id={location_id_filter}")
        if has_assignee_filter:
            active_filters.append(f"has_assignee={has_assignee_filter}")
        if search:
            active_filters.append(f"search={search}")

        if active_filters:
            logger.info(f"Mobile inventory filters: {', '.join(active_filters)}")

        db_session = db_manager.get_session()
        try:
            # Build query based on user permissions
            query = db_session.query(Asset)

            # Apply country restrictions for COUNTRY_ADMIN
            if user.user_type == UserType.COUNTRY_ADMIN and user.assigned_countries:
                query = query.filter(Asset.country.in_(user.assigned_countries))

            # Apply status filter
            if status_filter:
                try:
                    status_enum = AssetStatus[status_filter.upper()]
                    query = query.filter(Asset.status == status_enum)
                except KeyError:
                    logger.warning(f"Invalid status filter: {status_filter}")
                    pass

            # Apply manufacturer filter (case-insensitive partial match)
            if manufacturer_filter:
                query = query.filter(Asset.manufacturer.ilike(f"%{manufacturer_filter}%"))

            # Apply category filter (case-insensitive partial match)
            if category_filter:
                query = query.filter(Asset.category.ilike(f"%{category_filter}%"))

            # Apply country filter (exact match, unless it's from user restriction)
            if country_filter:
                query = query.filter(Asset.country == country_filter)

            # Apply asset_type filter
            if asset_type_filter:
                query = query.filter(Asset.asset_type == asset_type_filter)

            # Apply location filter
            if location_id_filter:
                query = query.filter(Asset.location_id == location_id_filter)

            # Apply assignee filter
            if has_assignee_filter is not None:
                if has_assignee_filter.lower() == 'true':
                    # Show only assigned assets
                    query = query.filter(Asset.assigned_to_id.isnot(None))
                elif has_assignee_filter.lower() == 'false':
                    # Show only unassigned assets
                    query = query.filter(Asset.assigned_to_id.is_(None))

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
                    'image_url': get_asset_image_url(asset),
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
            if can_view_all_tickets(user):
                total_tickets = db_session.query(Ticket).count()
                open_tickets = db_session.query(Ticket).filter(
                    Ticket.status.notin_([TicketStatus.RESOLVED, TicketStatus.RESOLVED_DELIVERED])
                ).count()
            else:
                # CLIENT users see only their tickets
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
                if user.user_type == UserType.COUNTRY_ADMIN and user.assigned_countries:
                    asset_query = asset_query.filter(Asset.country.in_(user.assigned_countries))
                
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

@mobile_api_bp.route('/debug/routes', methods=['GET'])
def debug_routes():
    """
    Debug endpoint to list all registered mobile API routes

    GET /api/mobile/v1/debug/routes
    """
    from flask import current_app

    routes = []
    for rule in current_app.url_map.iter_rules():
        if 'mobile' in rule.rule:
            routes.append({
                'endpoint': rule.endpoint,
                'methods': list(rule.methods),
                'url': rule.rule
            })

    return jsonify({
        'success': True,
        'routes': routes,
        'total': len(routes)
    })


# ============================================================
# TECH ASSET MANAGEMENT ENDPOINTS
# ============================================================

@mobile_api_bp.route('/assets', methods=['POST'])
@mobile_auth_required
def add_tech_asset():
    """
    Add a new tech asset from mobile app

    POST /api/mobile/v1/assets
    Headers: Authorization: Bearer <token>
    Body: {
        "asset_tag": "ASSET-001",
        "serial_num": "SN123456",
        "name": "MacBook Pro 14",
        "model": "MacBook Pro 14-inch 2023",
        "manufacturer": "Apple",
        "category": "Laptop",
        "hardware_type": "Laptop",
        "country": "Singapore",
        "status": "IN_STOCK",
        "notes": "Optional notes",
        "customer": "CUSTOMER_NAME"
    }

    Response: {
        "success": true,
        "asset": {...},
        "message": "Asset created successfully"
    }
    """
    try:
        user = request.current_mobile_user

        # Check permissions
        if not user.permissions or not user.permissions.can_create_assets:
            return jsonify({
                'success': False,
                'error': 'No permission to create assets'
            }), 403

        data = request.get_json()

        if not data:
            return jsonify({
                'success': False,
                'error': 'No data provided'
            }), 400

        # Validate required fields
        required_fields = ['asset_tag', 'serial_num']
        missing_fields = [f for f in required_fields if not data.get(f)]
        if missing_fields:
            return jsonify({
                'success': False,
                'error': f'Missing required fields: {", ".join(missing_fields)}'
            }), 400

        db_session = db_manager.get_session()
        try:
            # Check for duplicate asset_tag
            existing_tag = db_session.query(Asset).filter(Asset.asset_tag == data['asset_tag']).first()
            if existing_tag:
                return jsonify({
                    'success': False,
                    'error': f'Asset with tag {data["asset_tag"]} already exists'
                }), 400

            # Check for duplicate serial_num
            existing_serial = db_session.query(Asset).filter(Asset.serial_num == data['serial_num']).first()
            if existing_serial:
                return jsonify({
                    'success': False,
                    'error': f'Asset with serial number {data["serial_num"]} already exists'
                }), 400

            # Parse status
            status = AssetStatus.IN_STOCK
            if data.get('status'):
                try:
                    status = AssetStatus[data['status'].upper().replace(' ', '_')]
                except KeyError:
                    pass

            # Parse receiving_date if provided
            receiving_date = None
            if data.get('receiving_date'):
                try:
                    from dateutil import parser as date_parser
                    receiving_date = date_parser.parse(data['receiving_date'])
                except Exception:
                    # Try simple format
                    try:
                        receiving_date = datetime.strptime(data['receiving_date'], '%Y-%m-%d')
                    except Exception:
                        pass

            # Map iOS field names to database column names
            # iOS sends: is_erased -> erased, has_keyboard -> keyboard, has_charger -> charger
            # iOS sends: storage -> harddrive, diagnostics_code -> diag
            erased_value = None
            if data.get('is_erased') is not None:
                erased_value = 'Yes' if data.get('is_erased') else 'No'
            elif data.get('erased'):
                erased_value = data.get('erased')

            keyboard_value = None
            if data.get('has_keyboard') is not None:
                keyboard_value = 'Yes' if data.get('has_keyboard') else 'No'
            elif data.get('keyboard'):
                keyboard_value = data.get('keyboard')

            charger_value = None
            if data.get('has_charger') is not None:
                charger_value = 'Yes' if data.get('has_charger') else 'No'
            elif data.get('charger'):
                charger_value = data.get('charger')

            # Create new asset with all fields
            new_asset = Asset(
                asset_tag=data['asset_tag'],
                serial_num=data['serial_num'],
                name=data.get('name') or data.get('product'),  # Fall back to product if name not provided
                model=data.get('model'),
                manufacturer=data.get('manufacturer'),
                category=data.get('category'),
                hardware_type=data.get('hardware_type'),
                country=data.get('country'),
                status=status,
                notes=data.get('notes'),
                customer=data.get('customer'),
                asset_type=data.get('asset_type'),
                condition=data.get('condition'),
                # Additional fields from iOS QR scan
                cpu_type=data.get('cpu_type'),
                cpu_cores=data.get('cpu_cores'),
                gpu_cores=data.get('gpu_cores'),
                memory=data.get('memory'),
                harddrive=data.get('storage') or data.get('harddrive'),  # iOS sends 'storage'
                diag=data.get('diagnostics_code') or data.get('diag'),  # iOS sends 'diagnostics_code'
                erased=erased_value,
                keyboard=keyboard_value,
                charger=charger_value,
                receiving_date=receiving_date,
                po=data.get('po'),
                created_at=datetime.utcnow()
            )

            db_session.add(new_asset)
            db_session.commit()

            # Handle image upload if provided
            image_url = None
            if data.get('image'):
                import os
                import base64
                import uuid
                from flask import current_app

                upload_folder = os.path.join(current_app.root_path, 'static', 'uploads', 'assets')
                os.makedirs(upload_folder, exist_ok=True)

                image_str = data['image']
                filename_ext = 'jpg'

                # Handle data URL format
                if image_str.startswith('data:'):
                    header, image_str = image_str.split(',', 1)
                    if 'png' in header.lower():
                        filename_ext = 'png'

                try:
                    image_data = base64.b64decode(image_str)
                    if len(image_data) <= 10 * 1024 * 1024:  # Max 10MB
                        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
                        unique_id = str(uuid.uuid4())[:8]
                        filename = f"asset_{new_asset.id}_{timestamp}_{unique_id}.{filename_ext}"
                        filepath = os.path.join(upload_folder, filename)

                        with open(filepath, 'wb') as f:
                            f.write(image_data)

                        image_url = f"/static/uploads/assets/{filename}"
                        new_asset.image_url = image_url
                        db_session.commit()
                except Exception as img_err:
                    logger.warning(f"Failed to save asset image: {str(img_err)}")

            # Return created asset with all fields
            return jsonify({
                'success': True,
                'message': 'Asset created successfully',
                'asset': {
                    'id': new_asset.id,
                    'asset_tag': new_asset.asset_tag,
                    'serial_num': new_asset.serial_num,
                    'name': new_asset.name,
                    'model': new_asset.model,
                    'manufacturer': new_asset.manufacturer,
                    'category': new_asset.category,
                    'hardware_type': new_asset.hardware_type,
                    'country': new_asset.country,
                    'status': new_asset.status.value if new_asset.status else None,
                    'notes': new_asset.notes,
                    'customer': new_asset.customer,
                    'asset_type': new_asset.asset_type,
                    'condition': new_asset.condition,
                    'cpu_type': new_asset.cpu_type,
                    'cpu_cores': new_asset.cpu_cores,
                    'gpu_cores': new_asset.gpu_cores,
                    'memory': new_asset.memory,
                    'storage': new_asset.harddrive,
                    'diagnostics_code': new_asset.diag,
                    'is_erased': new_asset.erased,
                    'has_keyboard': new_asset.keyboard,
                    'has_charger': new_asset.charger,
                    'receiving_date': new_asset.receiving_date.isoformat() if new_asset.receiving_date else None,
                    'po': new_asset.po,
                    'image_url': get_full_image_url(new_asset.image_url),
                    'created_at': new_asset.created_at.isoformat() if new_asset.created_at else None
                }
            }), 201

        except Exception as e:
            db_session.rollback()
            raise e
        finally:
            db_session.close()

    except Exception as e:
        logger.error(f"Add asset error: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': 'Failed to create asset'
        }), 500


# ============================================================
# TRACKING MANAGEMENT ENDPOINTS
# ============================================================

@mobile_api_bp.route('/tracking/outbound', methods=['GET'])
@mobile_auth_required
def get_outbound_tracking():
    """
    Get all tickets with outbound/shipping tracking

    GET /api/mobile/v1/tracking/outbound?page=1&limit=20&status=pending
    Headers: Authorization: Bearer <token>

    Query Parameters:
        page (int): Page number (default: 1)
        limit (int): Items per page (default: 20, max: 100)
        status (str): Filter by status - 'pending', 'in_transit', 'delivered', 'all' (default: 'all')

    Response: {
        "success": true,
        "tracking_items": [...],
        "pagination": {...}
    }
    """
    try:
        user = request.current_mobile_user

        page = request.args.get('page', 1, type=int)
        limit = min(request.args.get('limit', 20, type=int), 100)
        status_filter = request.args.get('status', 'all').lower()

        db_session = db_manager.get_session()
        try:
            # Build query - tickets with shipping tracking
            query = db_session.query(Ticket).filter(
                Ticket.shipping_tracking.isnot(None),
                Ticket.shipping_tracking != ''
            )

            # Apply user permissions
            if user.user_type != UserType.SUPER_ADMIN:
                query = query.filter(
                    (Ticket.requester_id == user.id) |
                    (Ticket.assigned_to_id == user.id)
                )

            # Apply status filter
            if status_filter == 'pending':
                query = query.filter(
                    (Ticket.shipping_status.is_(None)) |
                    (Ticket.shipping_status == 'Pending') |
                    (Ticket.shipping_status == '')
                )
            elif status_filter == 'in_transit':
                query = query.filter(
                    Ticket.shipping_status.ilike('%transit%') |
                    Ticket.shipping_status.ilike('%shipped%')
                )
            elif status_filter == 'delivered':
                query = query.filter(
                    Ticket.shipping_status.ilike('%delivered%') |
                    Ticket.shipping_status.ilike('%received%')
                )

            # Get total count
            total = query.count()

            # Apply pagination
            offset = (page - 1) * limit
            tickets = query.order_by(Ticket.updated_at.desc()).offset(offset).limit(limit).all()

            # Format tracking items
            tracking_items = []
            for ticket in tickets:
                # Collect all shipping tracking numbers
                tracking_numbers = []

                if ticket.shipping_tracking:
                    tracking_numbers.append({
                        'slot': 1,
                        'tracking_number': ticket.shipping_tracking,
                        'carrier': ticket.shipping_carrier,
                        'status': ticket.shipping_status or 'Pending',
                        'is_delivered': 'delivered' in (ticket.shipping_status or '').lower() or 'received' in (ticket.shipping_status or '').lower()
                    })

                if ticket.shipping_tracking_2:
                    tracking_numbers.append({
                        'slot': 2,
                        'tracking_number': ticket.shipping_tracking_2,
                        'carrier': ticket.shipping_carrier_2 if hasattr(ticket, 'shipping_carrier_2') else None,
                        'status': ticket.shipping_status_2 or 'Pending',
                        'is_delivered': 'delivered' in (ticket.shipping_status_2 or '').lower() or 'received' in (ticket.shipping_status_2 or '').lower()
                    })

                if ticket.shipping_tracking_3:
                    tracking_numbers.append({
                        'slot': 3,
                        'tracking_number': ticket.shipping_tracking_3,
                        'carrier': ticket.shipping_carrier_3 if hasattr(ticket, 'shipping_carrier_3') else None,
                        'status': ticket.shipping_status_3 or 'Pending',
                        'is_delivered': 'delivered' in (ticket.shipping_status_3 or '').lower() or 'received' in (ticket.shipping_status_3 or '').lower()
                    })

                if ticket.shipping_tracking_4:
                    tracking_numbers.append({
                        'slot': 4,
                        'tracking_number': ticket.shipping_tracking_4,
                        'carrier': ticket.shipping_carrier_4 if hasattr(ticket, 'shipping_carrier_4') else None,
                        'status': ticket.shipping_status_4 or 'Pending',
                        'is_delivered': 'delivered' in (ticket.shipping_status_4 or '').lower() or 'received' in (ticket.shipping_status_4 or '').lower()
                    })

                if ticket.shipping_tracking_5:
                    tracking_numbers.append({
                        'slot': 5,
                        'tracking_number': ticket.shipping_tracking_5,
                        'carrier': ticket.shipping_carrier_5 if hasattr(ticket, 'shipping_carrier_5') else None,
                        'status': ticket.shipping_status_5 or 'Pending',
                        'is_delivered': 'delivered' in (ticket.shipping_status_5 or '').lower() or 'received' in (ticket.shipping_status_5 or '').lower()
                    })

                tracking_items.append({
                    'ticket_id': ticket.id,
                    'display_id': ticket.display_id,
                    'subject': ticket.subject,
                    'category': ticket.category.value if ticket.category else None,
                    'customer_name': ticket.customer.name if ticket.customer else None,
                    'shipping_address': ticket.shipping_address,
                    'tracking_numbers': tracking_numbers,
                    'created_at': ticket.created_at.isoformat() if ticket.created_at else None,
                    'updated_at': ticket.updated_at.isoformat() if ticket.updated_at else None
                })

            pages = (total + limit - 1) // limit

            return jsonify({
                'success': True,
                'tracking_items': tracking_items,
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
        logger.error(f"Get outbound tracking error: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': 'Failed to get outbound tracking'
        }), 500


@mobile_api_bp.route('/tracking/outbound/<int:ticket_id>/mark-received', methods=['POST'])
@mobile_auth_required
def mark_outbound_received(ticket_id):
    """
    Mark outbound/shipping tracking as received/delivered

    POST /api/mobile/v1/tracking/outbound/<ticket_id>/mark-received
    Headers: Authorization: Bearer <token>
    Body: {
        "slot": 1,  # Optional: which tracking slot (1-5), defaults to 1
        "notes": "Received by customer"  # Optional notes
    }

    Response: {
        "success": true,
        "message": "Marked as received",
        "tracking": {...}
    }
    """
    try:
        user = request.current_mobile_user
        data = request.get_json() or {}
        slot = data.get('slot', 1)
        notes = data.get('notes', '')

        db_session = db_manager.get_session()
        try:
            # Get ticket with permission check
            if can_view_all_tickets(user):
                ticket = db_session.query(Ticket).filter(Ticket.id == ticket_id).first()
            else:
                ticket = db_session.query(Ticket).filter(
                    Ticket.id == ticket_id,
                    (Ticket.requester_id == user.id) | (Ticket.assigned_to_id == user.id)
                ).first()

            if not ticket:
                return jsonify({
                    'success': False,
                    'error': 'Ticket not found or access denied'
                }), 404

            # Update the appropriate tracking status based on slot
            received_status = f"Delivered - Received on {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}"
            if notes:
                received_status += f" - {notes}"

            tracking_number = None
            if slot == 1:
                ticket.shipping_status = received_status
                tracking_number = ticket.shipping_tracking
            elif slot == 2:
                ticket.shipping_status_2 = received_status
                tracking_number = ticket.shipping_tracking_2
            elif slot == 3:
                ticket.shipping_status_3 = received_status
                tracking_number = ticket.shipping_tracking_3
            elif slot == 4:
                ticket.shipping_status_4 = received_status
                tracking_number = ticket.shipping_tracking_4
            elif slot == 5:
                ticket.shipping_status_5 = received_status
                tracking_number = ticket.shipping_tracking_5
            else:
                return jsonify({
                    'success': False,
                    'error': 'Invalid slot number (must be 1-5)'
                }), 400

            ticket.updated_at = datetime.utcnow()
            db_session.commit()

            logger.info(f"User {user.username} marked outbound tracking as received for ticket {ticket_id} slot {slot}")

            return jsonify({
                'success': True,
                'message': 'Marked as received',
                'tracking': {
                    'ticket_id': ticket.id,
                    'slot': slot,
                    'tracking_number': tracking_number,
                    'status': received_status
                }
            })

        except Exception as e:
            db_session.rollback()
            raise e
        finally:
            db_session.close()

    except Exception as e:
        logger.error(f"Mark outbound received error: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': 'Failed to mark as received'
        }), 500


@mobile_api_bp.route('/tickets/<int:ticket_id>/tracking', methods=['GET'])
@mobile_auth_required
def get_ticket_tracking(ticket_id):
    """
    Get tracking information for a ticket with optional refresh from SingPost API

    GET /api/mobile/v1/tickets/<ticket_id>/tracking?force_refresh=false
    Headers: Authorization: Bearer <token>

    Query Parameters:
        force_refresh (bool): If true, bypass cache and fetch fresh data (default: false)
        slot (int): Which tracking slot to fetch (1-5, default: 1)

    Response: {
        "success": true,
        "tracking": {
            "tracking_number": "XZB123456",
            "carrier": "SingPost",
            "status": "Information Received",
            "was_pushed": false,
            "origin_country": "Singapore",
            "destination_country": "Malaysia",
            "events": [...],
            "is_cached": false,
            "last_updated": "2025-12-22T10:00:00"
        }
    }
    """
    try:
        user = request.current_mobile_user
        force_refresh = request.args.get('force_refresh', 'false').lower() == 'true'
        slot = request.args.get('slot', 1, type=int)

        db_session = db_manager.get_session()
        try:
            # Get ticket with permission check
            if can_view_all_tickets(user):
                ticket = db_session.query(Ticket).filter(Ticket.id == ticket_id).first()
            else:
                ticket = db_session.query(Ticket).filter(
                    Ticket.id == ticket_id,
                    (Ticket.requester_id == user.id) | (Ticket.assigned_to_id == user.id)
                ).first()

            if not ticket:
                return jsonify({
                    'success': False,
                    'error': 'Ticket not found or access denied'
                }), 404

            # Get the appropriate tracking number based on slot
            if slot == 1:
                tracking_number = ticket.shipping_tracking
                current_status = ticket.shipping_status
            elif slot == 2:
                tracking_number = getattr(ticket, 'shipping_tracking_2', None)
                current_status = getattr(ticket, 'shipping_status_2', None)
            elif slot == 3:
                tracking_number = getattr(ticket, 'shipping_tracking_3', None)
                current_status = getattr(ticket, 'shipping_status_3', None)
            elif slot == 4:
                tracking_number = getattr(ticket, 'shipping_tracking_4', None)
                current_status = getattr(ticket, 'shipping_status_4', None)
            elif slot == 5:
                tracking_number = getattr(ticket, 'shipping_tracking_5', None)
                current_status = getattr(ticket, 'shipping_status_5', None)
            else:
                return jsonify({
                    'success': False,
                    'error': 'Invalid slot number (must be 1-5)'
                }), 400

            if not tracking_number:
                return jsonify({
                    'success': False,
                    'error': f'No tracking number in slot {slot}'
                }), 404

            # Import tracking utilities
            from utils.tracking_cache import TrackingCache
            from utils.singpost_tracking import get_singpost_tracking_client

            # Check if it's a SingPost tracking number
            upper_tn = tracking_number.upper()
            is_singpost = (
                upper_tn.startswith('XZ') or
                upper_tn.startswith('SPNDD') or
                upper_tn.startswith('SPPSD') or
                upper_tn.startswith('SP') or
                upper_tn.startswith('SG')
            )

            # Try to get cached data first (unless force refresh)
            if not force_refresh:
                cached_data = TrackingCache.get_cached_tracking(
                    db_session,
                    tracking_number,
                    ticket_id=ticket_id,
                    tracking_type='primary',
                    max_age_hours=1,  # 1 hour cache for mobile
                    force=False
                )
                if cached_data and cached_data.get('success'):
                    logger.info(f"Mobile returning cached tracking for {tracking_number}")
                    return jsonify({
                        'success': True,
                        'tracking': {
                            'tracking_number': tracking_number,
                            'carrier': 'SingPost' if is_singpost else 'Unknown',
                            'status': cached_data.get('shipping_status', current_status),
                            'was_pushed': cached_data.get('tracking_info', {}).get('was_pushed', False) if isinstance(cached_data.get('tracking_info'), dict) else False,
                            'events': cached_data.get('tracking_info', []) if isinstance(cached_data.get('tracking_info'), list) else cached_data.get('tracking_info', {}).get('events', []),
                            'is_cached': True,
                            'last_updated': cached_data.get('last_updated')
                        }
                    })

            # Fetch fresh data from SingPost API
            if is_singpost:
                singpost_client = get_singpost_tracking_client()

                if not singpost_client.is_configured():
                    return jsonify({
                        'success': False,
                        'error': 'SingPost Tracking API not configured'
                    }), 500

                result = singpost_client.track_single(tracking_number)

                if result and result.get('success'):
                    # Save to cache
                    TrackingCache.save_tracking_data(
                        db_session,
                        tracking_number,
                        result.get('events', []),
                        result.get('status', 'Unknown'),
                        ticket_id=ticket_id,
                        tracking_type='primary',
                        carrier='singpost'
                    )

                    # Update ticket status
                    if slot == 1:
                        ticket.shipping_status = result.get('status')
                        ticket.shipping_carrier = 'SingPost'
                    ticket.updated_at = datetime.utcnow()
                    db_session.commit()

                    return jsonify({
                        'success': True,
                        'tracking': {
                            'tracking_number': tracking_number,
                            'carrier': 'SingPost',
                            'status': result.get('status'),
                            'was_pushed': result.get('was_pushed', False),
                            'origin_country': result.get('origin_country'),
                            'destination_country': result.get('destination_country'),
                            'posting_date': result.get('posting_date'),
                            'events': result.get('events', []),
                            'is_cached': False,
                            'last_updated': result.get('last_updated')
                        }
                    })
                else:
                    return jsonify({
                        'success': False,
                        'error': result.get('error', 'Failed to fetch tracking data'),
                        'tracking_number': tracking_number
                    }), 404

            else:
                # Non-SingPost tracking - return basic info
                return jsonify({
                    'success': True,
                    'tracking': {
                        'tracking_number': tracking_number,
                        'carrier': ticket.shipping_carrier or 'Unknown',
                        'status': current_status or 'Unknown',
                        'was_pushed': None,
                        'events': [],
                        'is_cached': False,
                        'message': 'Non-SingPost tracking - live tracking not available'
                    }
                })

        finally:
            db_session.close()

    except Exception as e:
        logger.error(f"Get ticket tracking error: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': 'Failed to get tracking information'
        }), 500


@mobile_api_bp.route('/tracking/lookup', methods=['POST'])
@mobile_auth_required
def lookup_tracking():
    """
    Look up a tracking number directly without ticket association

    POST /api/mobile/v1/tracking/lookup
    Headers: Authorization: Bearer <token>
    Body: {
        "tracking_number": "XZB123456"
    }

    Response: {
        "success": true,
        "tracking": {
            "tracking_number": "XZB123456",
            "carrier": "SingPost",
            "status": "Information Received",
            "was_pushed": false,
            "events": [...]
        }
    }
    """
    try:
        data = request.get_json() or {}
        tracking_number = data.get('tracking_number', '').strip()

        if not tracking_number:
            return jsonify({
                'success': False,
                'error': 'Tracking number is required'
            }), 400

        # Check if it's a SingPost tracking number
        upper_tn = tracking_number.upper()
        is_singpost = (
            upper_tn.startswith('XZ') or
            upper_tn.startswith('SPNDD') or
            upper_tn.startswith('SPPSD') or
            upper_tn.startswith('SP') or
            upper_tn.startswith('SG')
        )

        if not is_singpost:
            return jsonify({
                'success': False,
                'error': 'Only SingPost tracking numbers (XZ, SP, SG, SPNDD, SPPSD prefixes) are supported'
            }), 400

        from utils.singpost_tracking import get_singpost_tracking_client

        singpost_client = get_singpost_tracking_client()

        if not singpost_client.is_configured():
            return jsonify({
                'success': False,
                'error': 'SingPost Tracking API not configured'
            }), 500

        result = singpost_client.track_single(tracking_number)

        if result and result.get('success'):
            return jsonify({
                'success': True,
                'tracking': {
                    'tracking_number': tracking_number,
                    'carrier': 'SingPost',
                    'status': result.get('status'),
                    'was_pushed': result.get('was_pushed', False),
                    'origin_country': result.get('origin_country'),
                    'destination_country': result.get('destination_country'),
                    'posting_date': result.get('posting_date'),
                    'events': result.get('events', []),
                    'last_updated': result.get('last_updated'),
                    'source': result.get('source')
                }
            })
        else:
            return jsonify({
                'success': False,
                'error': result.get('error', 'Tracking number not found'),
                'tracking_number': tracking_number
            }), 404

    except Exception as e:
        logger.error(f"Tracking lookup error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to look up tracking'
        }), 500


@mobile_api_bp.route('/tracking/return', methods=['GET'])
@mobile_auth_required
def get_return_tracking():
    """
    Get all tickets with return tracking

    GET /api/mobile/v1/tracking/return?page=1&limit=20&status=pending
    Headers: Authorization: Bearer <token>

    Query Parameters:
        page (int): Page number (default: 1)
        limit (int): Items per page (default: 20, max: 100)
        status (str): Filter by status - 'pending', 'in_transit', 'received', 'all' (default: 'all')

    Response: {
        "success": true,
        "tracking_items": [...],
        "pagination": {...}
    }
    """
    try:
        user = request.current_mobile_user

        page = request.args.get('page', 1, type=int)
        limit = min(request.args.get('limit', 20, type=int), 100)
        status_filter = request.args.get('status', 'all').lower()

        db_session = db_manager.get_session()
        try:
            # Build query - tickets with return tracking
            query = db_session.query(Ticket).filter(
                Ticket.return_tracking.isnot(None),
                Ticket.return_tracking != ''
            )

            # Apply user permissions
            if user.user_type != UserType.SUPER_ADMIN:
                query = query.filter(
                    (Ticket.requester_id == user.id) |
                    (Ticket.assigned_to_id == user.id)
                )

            # Apply status filter
            if status_filter == 'pending':
                query = query.filter(
                    (Ticket.return_status.is_(None)) |
                    (Ticket.return_status == 'Pending') |
                    (Ticket.return_status == '')
                )
            elif status_filter == 'in_transit':
                query = query.filter(
                    Ticket.return_status.ilike('%transit%') |
                    Ticket.return_status.ilike('%shipped%')
                )
            elif status_filter == 'received':
                query = query.filter(
                    Ticket.return_status.ilike('%delivered%') |
                    Ticket.return_status.ilike('%received%')
                )

            # Get total count
            total = query.count()

            # Apply pagination
            offset = (page - 1) * limit
            tickets = query.order_by(Ticket.updated_at.desc()).offset(offset).limit(limit).all()

            # Format tracking items
            tracking_items = []
            for ticket in tickets:
                tracking_items.append({
                    'ticket_id': ticket.id,
                    'display_id': ticket.display_id,
                    'subject': ticket.subject,
                    'category': ticket.category.value if ticket.category else None,
                    'customer_name': ticket.customer.name if ticket.customer else None,
                    'return_tracking': ticket.return_tracking,
                    'return_status': ticket.return_status or 'Pending',
                    'is_received': 'delivered' in (ticket.return_status or '').lower() or 'received' in (ticket.return_status or '').lower(),
                    'shipping_address': ticket.shipping_address,
                    'created_at': ticket.created_at.isoformat() if ticket.created_at else None,
                    'updated_at': ticket.updated_at.isoformat() if ticket.updated_at else None
                })

            pages = (total + limit - 1) // limit

            return jsonify({
                'success': True,
                'tracking_items': tracking_items,
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
        logger.error(f"Get return tracking error: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': 'Failed to get return tracking'
        }), 500


@mobile_api_bp.route('/tracking/return/<int:ticket_id>/mark-received', methods=['POST'])
@mobile_auth_required
def mark_return_received(ticket_id):
    """
    Mark return tracking as received

    POST /api/mobile/v1/tracking/return/<ticket_id>/mark-received
    Headers: Authorization: Bearer <token>
    Body: {
        "notes": "Package received in good condition"  # Optional notes
    }

    Response: {
        "success": true,
        "message": "Return marked as received",
        "tracking": {...}
    }
    """
    try:
        user = request.current_mobile_user
        data = request.get_json() or {}
        notes = data.get('notes', '')

        db_session = db_manager.get_session()
        try:
            # Get ticket with permission check
            if can_view_all_tickets(user):
                ticket = db_session.query(Ticket).filter(Ticket.id == ticket_id).first()
            else:
                ticket = db_session.query(Ticket).filter(
                    Ticket.id == ticket_id,
                    (Ticket.requester_id == user.id) | (Ticket.assigned_to_id == user.id)
                ).first()

            if not ticket:
                return jsonify({
                    'success': False,
                    'error': 'Ticket not found or access denied'
                }), 404

            if not ticket.return_tracking:
                return jsonify({
                    'success': False,
                    'error': 'No return tracking found for this ticket'
                }), 400

            # Update return status
            received_status = f"Received on {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}"
            if notes:
                received_status += f" - {notes}"

            ticket.return_status = received_status
            ticket.updated_at = datetime.utcnow()
            db_session.commit()

            logger.info(f"User {user.username} marked return tracking as received for ticket {ticket_id}")

            return jsonify({
                'success': True,
                'message': 'Return marked as received',
                'tracking': {
                    'ticket_id': ticket.id,
                    'return_tracking': ticket.return_tracking,
                    'return_status': received_status
                }
            })

        except Exception as e:
            db_session.rollback()
            raise e
        finally:
            db_session.close()

    except Exception as e:
        logger.error(f"Mark return received error: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': 'Failed to mark return as received'
        }), 500


# ============================================================
# TICKET ASSETS MANAGEMENT ENDPOINTS (for iOS inline display)
# ============================================================

@mobile_api_bp.route('/tickets/<int:ticket_id>/assets', methods=['GET'])
@mobile_auth_required
def get_ticket_assets(ticket_id):
    """
    Get detailed ticket information with assets and tracking for inline display

    GET /api/mobile/v1/tickets/<ticket_id>/assets
    Headers: Authorization: Bearer <token>

    Response: {
        "success": true,
        "ticket": {
            "id": 123,
            "ticket_id": 123,
            "display_id": "#TL-00123",
            "subject": "Asset Return Request",
            "category": "Asset Return (claw)",
            "customer_name": "John Doe",
            "assets": [...],
            "outbound_tracking": {...},
            "return_tracking": {...}
        }
    }
    """
    try:
        user = request.current_mobile_user

        db_session = db_manager.get_session()
        try:
            from sqlalchemy.orm import joinedload

            # Get ticket with permissions check
            base_query = db_session.query(Ticket).options(
                joinedload(Ticket.customer),
                joinedload(Ticket.assets)
            )

            if can_view_all_tickets(user):
                ticket = base_query.filter(Ticket.id == ticket_id).first()
            else:
                ticket = base_query.filter(
                    Ticket.id == ticket_id,
                    (Ticket.requester_id == user.id) | (Ticket.assigned_to_id == user.id)
                ).first()

            if not ticket:
                return jsonify({
                    'success': False,
                    'error': 'Ticket not found'
                }), 404

            # Build assets list
            assets_list = []
            for asset in (ticket.assets or []):
                assets_list.append({
                    'id': asset.id,
                    'asset_tag': asset.asset_tag,
                    'serial_number': asset.serial_num,
                    'name': asset.name,
                    'model': asset.model,
                    'status': asset.status.value if asset.status else 'UNKNOWN',
                    'image_url': get_asset_image_url(asset)
                })

            # Build outbound tracking object with events
            outbound_tracking = None
            if ticket.shipping_tracking:
                is_received = 'delivered' in (ticket.shipping_status or '').lower() or 'received' in (ticket.shipping_status or '').lower()
                outbound_tracking = {
                    'tracking_number': ticket.shipping_tracking,
                    'carrier': ticket.shipping_carrier,
                    'status': 'delivered' if is_received else ('in_transit' if ticket.shipping_status else 'pending'),
                    'is_received': is_received,
                    'events': []  # Events would be populated by tracking refresh
                }

            # Build return tracking object
            return_tracking = None
            if ticket.return_tracking:
                is_received = 'delivered' in (ticket.return_status or '').lower() or 'received' in (ticket.return_status or '').lower()
                return_tracking = {
                    'tracking_number': ticket.return_tracking,
                    'carrier': None,  # Return carrier not stored separately
                    'status': 'received' if is_received else ('in_transit' if ticket.return_status else 'pending'),
                    'is_received': is_received,
                    'events': []
                }

            return jsonify({
                'success': True,
                'ticket': {
                    'id': ticket.id,
                    'ticket_id': ticket.id,
                    'display_id': ticket.display_id or f"#TL-{ticket.id:05d}",
                    'subject': ticket.subject,
                    'category': ticket.category.value if ticket.category else None,
                    'customer_name': ticket.customer.name if ticket.customer else None,
                    'assets': assets_list,
                    'outbound_tracking': outbound_tracking,
                    'return_tracking': return_tracking
                }
            })

        finally:
            db_session.close()

    except Exception as e:
        logger.error(f"Get ticket assets error: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': 'Failed to get ticket assets'
        }), 500


@mobile_api_bp.route('/tickets/<int:ticket_id>/assets', methods=['POST'])
@mobile_auth_required
def add_asset_to_ticket(ticket_id):
    """
    Add an existing asset to a ticket

    POST /api/mobile/v1/tickets/<ticket_id>/assets
    Headers: Authorization: Bearer <token>
    Body: {
        "asset_id": 456
    }

    Response: {
        "success": true,
        "message": "Asset successfully added to ticket"
    }
    """
    try:
        user = request.current_mobile_user
        data = request.get_json()

        if not data or not data.get('asset_id'):
            return jsonify({
                'success': False,
                'error': 'asset_id is required'
            }), 400

        asset_id = data['asset_id']

        db_session = db_manager.get_session()
        try:
            # Get ticket with permissions check
            if can_view_all_tickets(user):
                ticket = db_session.query(Ticket).filter(Ticket.id == ticket_id).first()
            else:
                ticket = db_session.query(Ticket).filter(
                    Ticket.id == ticket_id,
                    (Ticket.requester_id == user.id) | (Ticket.assigned_to_id == user.id)
                ).first()

            if not ticket:
                return jsonify({
                    'success': False,
                    'error': 'Ticket not found'
                }), 404

            # Get the asset
            asset = db_session.query(Asset).filter(Asset.id == asset_id).first()
            if not asset:
                return jsonify({
                    'success': False,
                    'error': 'Asset not found'
                }), 404

            # Check if asset is already in this ticket using direct query
            from models.asset import ticket_assets
            existing = db_session.query(ticket_assets).filter(
                ticket_assets.c.ticket_id == ticket_id,
                ticket_assets.c.asset_id == asset_id
            ).first()

            if existing:
                return jsonify({
                    'success': False,
                    'error': 'Asset is already assigned to this ticket'
                }), 400

            # Add asset to ticket using direct insert to avoid relationship conflicts
            db_session.execute(
                ticket_assets.insert().values(ticket_id=ticket_id, asset_id=asset_id)
            )
            ticket.updated_at = datetime.utcnow()
            db_session.commit()

            logger.info(f"User {user.username} added asset {asset_id} to ticket {ticket_id}")

            return jsonify({
                'success': True,
                'message': 'Asset successfully added to ticket'
            })

        except Exception as e:
            db_session.rollback()
            raise e
        finally:
            db_session.close()

    except Exception as e:
        logger.error(f"Add asset to ticket error: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': 'Failed to add asset to ticket'
        }), 500


@mobile_api_bp.route('/assets/search', methods=['GET'])
@mobile_auth_required
def search_assets():
    """
    Search for assets by asset tag or serial number

    GET /api/mobile/v1/assets/search?q=ASSET-001&limit=20
    Headers: Authorization: Bearer <token>

    Query Parameters:
        q (str): Search query (asset tag or serial number)
        limit (int): Max results (default: 20)

    Response: {
        "success": true,
        "assets": [...]
    }
    """
    try:
        user = request.current_mobile_user
        search_query = request.args.get('q', '').strip()
        limit = min(request.args.get('limit', 20, type=int), 50)

        if not search_query:
            return jsonify({
                'success': False,
                'error': 'Search query (q) is required'
            }), 400

        db_session = db_manager.get_session()
        try:
            # Search by asset_tag or serial_num
            query = db_session.query(Asset).filter(
                (Asset.asset_tag.ilike(f'%{search_query}%')) |
                (Asset.serial_num.ilike(f'%{search_query}%')) |
                (Asset.name.ilike(f'%{search_query}%'))
            )

            # Only show available assets (not already assigned to tickets) by default
            # But include all for search purposes
            assets = query.limit(limit).all()

            assets_list = []
            for asset in assets:
                assets_list.append({
                    'id': asset.id,
                    'asset_tag': asset.asset_tag,
                    'serial_number': asset.serial_num,
                    'name': asset.name,
                    'model': asset.model,
                    'status': asset.status.value if asset.status else 'UNKNOWN',
                    'image_url': get_asset_image_url(asset)
                })

            return jsonify({
                'success': True,
                'assets': assets_list
            })

        finally:
            db_session.close()

    except Exception as e:
        logger.error(f"Search assets error: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': 'Failed to search assets'
        }), 500


@mobile_api_bp.route('/tickets/<int:ticket_id>/tracking/outbound/received', methods=['POST'])
@mobile_auth_required
def mark_ticket_outbound_received(ticket_id):
    """
    Mark outbound tracking as received (alternative URL pattern for iOS)

    POST /api/mobile/v1/tickets/<ticket_id>/tracking/outbound/received
    Headers: Authorization: Bearer <token>
    Body: {
        "slot": 1,
        "notes": "Package received in good condition"
    }

    Response: {
        "success": true,
        "message": "Outbound tracking marked as received",
        "tracking": {...}
    }
    """
    try:
        user = request.current_mobile_user
        data = request.get_json() or {}
        slot = data.get('slot', 1)
        notes = data.get('notes', '')

        db_session = db_manager.get_session()
        try:
            # Get ticket with permission check
            if can_view_all_tickets(user):
                ticket = db_session.query(Ticket).filter(Ticket.id == ticket_id).first()
            else:
                ticket = db_session.query(Ticket).filter(
                    Ticket.id == ticket_id,
                    (Ticket.requester_id == user.id) | (Ticket.assigned_to_id == user.id)
                ).first()

            if not ticket:
                return jsonify({
                    'success': False,
                    'error': 'Ticket not found or access denied'
                }), 404

            # Update the appropriate tracking status based on slot
            received_status = f"Delivered - Received on {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}"
            if notes:
                received_status += f" - {notes}"

            tracking_number = None
            if slot == 1:
                ticket.shipping_status = received_status
                tracking_number = ticket.shipping_tracking
            elif slot == 2:
                ticket.shipping_status_2 = received_status
                tracking_number = ticket.shipping_tracking_2
            elif slot == 3:
                ticket.shipping_status_3 = received_status
                tracking_number = ticket.shipping_tracking_3
            elif slot == 4:
                ticket.shipping_status_4 = received_status
                tracking_number = ticket.shipping_tracking_4
            elif slot == 5:
                ticket.shipping_status_5 = received_status
                tracking_number = ticket.shipping_tracking_5
            else:
                return jsonify({
                    'success': False,
                    'error': 'Invalid slot number (must be 1-5)'
                }), 400

            ticket.updated_at = datetime.utcnow()
            db_session.commit()

            logger.info(f"User {user.username} marked outbound tracking as received for ticket {ticket_id} slot {slot}")

            return jsonify({
                'success': True,
                'message': 'Outbound tracking marked as received',
                'tracking': {
                    'ticket_id': ticket.id,
                    'slot': slot,
                    'tracking_number': tracking_number,
                    'status': 'delivered'
                }
            })

        except Exception as e:
            db_session.rollback()
            raise e
        finally:
            db_session.close()

    except Exception as e:
        logger.error(f"Mark outbound received error: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': 'Failed to mark as received'
        }), 500


@mobile_api_bp.route('/tickets/<int:ticket_id>/tracking/return/received', methods=['POST'])
@mobile_auth_required
def mark_ticket_return_received(ticket_id):
    """
    Mark return tracking as received (alternative URL pattern for iOS)

    POST /api/mobile/v1/tickets/<ticket_id>/tracking/return/received
    Headers: Authorization: Bearer <token>
    Body: {
        "notes": "Return package received"
    }

    Response: {
        "success": true,
        "message": "Return tracking marked as received",
        "tracking": {...}
    }
    """
    try:
        user = request.current_mobile_user
        data = request.get_json() or {}
        notes = data.get('notes', '')

        db_session = db_manager.get_session()
        try:
            # Get ticket with permission check
            if can_view_all_tickets(user):
                ticket = db_session.query(Ticket).filter(Ticket.id == ticket_id).first()
            else:
                ticket = db_session.query(Ticket).filter(
                    Ticket.id == ticket_id,
                    (Ticket.requester_id == user.id) | (Ticket.assigned_to_id == user.id)
                ).first()

            if not ticket:
                return jsonify({
                    'success': False,
                    'error': 'Ticket not found or access denied'
                }), 404

            if not ticket.return_tracking:
                return jsonify({
                    'success': False,
                    'error': 'No return tracking found for this ticket'
                }), 400

            # Update return status
            received_status = f"Received on {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}"
            if notes:
                received_status += f" - {notes}"

            ticket.return_status = received_status
            ticket.updated_at = datetime.utcnow()
            db_session.commit()

            logger.info(f"User {user.username} marked return tracking as received for ticket {ticket_id}")

            return jsonify({
                'success': True,
                'message': 'Return tracking marked as received',
                'tracking': {
                    'ticket_id': ticket.id,
                    'return_tracking': ticket.return_tracking,
                    'return_status': 'received'
                }
            })

        except Exception as e:
            db_session.rollback()
            raise e
        finally:
            db_session.close()

    except Exception as e:
        logger.error(f"Mark return received error: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': 'Failed to mark return as received'
        }), 500


@mobile_api_bp.route('/tickets/<int:ticket_id>/tracking/refresh', methods=['POST'])
@mobile_auth_required
def refresh_ticket_tracking(ticket_id):
    """
    Refresh tracking information from carrier API

    POST /api/mobile/v1/tickets/<ticket_id>/tracking/refresh
    Headers: Authorization: Bearer <token>
    Body: {
        "type": "outbound"  // or "return"
    }

    Response: {
        "success": true,
        "message": "Tracking information refreshed",
        "tracking": {...}
    }
    """
    try:
        user = request.current_mobile_user
        data = request.get_json() or {}
        tracking_type = data.get('type', 'outbound').lower()

        if tracking_type not in ['outbound', 'return']:
            return jsonify({
                'success': False,
                'error': 'Invalid type. Must be "outbound" or "return"'
            }), 400

        db_session = db_manager.get_session()
        try:
            # Get ticket with permission check
            if can_view_all_tickets(user):
                ticket = db_session.query(Ticket).filter(Ticket.id == ticket_id).first()
            else:
                ticket = db_session.query(Ticket).filter(
                    Ticket.id == ticket_id,
                    (Ticket.requester_id == user.id) | (Ticket.assigned_to_id == user.id)
                ).first()

            if not ticket:
                return jsonify({
                    'success': False,
                    'error': 'Ticket not found or access denied'
                }), 404

            # Get the tracking number based on type
            if tracking_type == 'outbound':
                tracking_number = ticket.shipping_tracking
                carrier = ticket.shipping_carrier
            else:
                tracking_number = ticket.return_tracking
                carrier = None

            if not tracking_number:
                return jsonify({
                    'success': False,
                    'error': f'No {tracking_type} tracking found for this ticket'
                }), 400

            # Try to refresh tracking using Ship24Tracker
            tracking_result = None
            events = []
            status = 'pending'
            is_received = False

            try:
                from utils.ship24_tracker import get_tracker
                import asyncio

                tracker = get_tracker()

                # Run async tracking lookup
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    tracking_result = loop.run_until_complete(
                        tracker.track_shipment(tracking_number)
                    )
                finally:
                    loop.close()

                if tracking_result and tracking_result.get('success'):
                    # Extract events from tracking result
                    raw_events = tracking_result.get('events', [])
                    for i, evt in enumerate(raw_events[:10]):  # Limit to 10 most recent
                        events.append({
                            'id': f'evt_{i+1}',
                            'timestamp': evt.get('timestamp') or evt.get('date'),
                            'location': evt.get('location', ''),
                            'description': evt.get('description') or evt.get('status', ''),
                            'status': evt.get('status_code', 'unknown')
                        })

                    # Determine status
                    latest_status = tracking_result.get('status', '').lower()
                    if 'delivered' in latest_status or 'received' in latest_status:
                        status = 'delivered'
                        is_received = True
                    elif 'transit' in latest_status or 'shipped' in latest_status:
                        status = 'in_transit'
                    else:
                        status = 'pending'

                    # Update ticket with latest status
                    if tracking_type == 'outbound':
                        if tracking_result.get('status'):
                            ticket.shipping_status = tracking_result.get('status')
                    else:
                        if tracking_result.get('status'):
                            ticket.return_status = tracking_result.get('status')

                    ticket.updated_at = datetime.utcnow()
                    db_session.commit()

            except Exception as track_err:
                logger.warning(f"Tracking refresh failed: {str(track_err)}")
                # Continue with current data if tracking API fails

            return jsonify({
                'success': True,
                'message': 'Tracking information refreshed',
                'tracking': {
                    'tracking_number': tracking_number,
                    'carrier': carrier,
                    'status': status,
                    'is_received': is_received,
                    'events': events
                }
            })

        finally:
            db_session.close()

    except Exception as e:
        logger.error(f"Refresh tracking error: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': 'Failed to refresh tracking'
        }), 500


# ============= Asset Label Generation =============

@mobile_api_bp.route('/assets/<int:asset_id>/label', methods=['GET'])
@mobile_auth_required
def get_asset_label(asset_id):
    """
    Get asset label as base64 image for printing

    GET /api/mobile/v1/assets/<asset_id>/label

    Returns:
        {
            "success": true,
            "label": "data:image/png;base64,..."
        }
    """
    try:
        db_session = db_manager.get_session()
        try:
            asset = db_session.query(Asset).filter(Asset.id == asset_id).first()

            if not asset:
                return jsonify({
                    'success': False,
                    'error': 'Asset not found'
                }), 404

            if not asset.serial_num:
                return jsonify({
                    'success': False,
                    'error': 'Asset does not have a serial number'
                }), 400

            # Generate label
            from utils.barcode_generator import barcode_generator
            label_base64 = barcode_generator.generate_label_base64(asset)

            if not label_base64:
                return jsonify({
                    'success': False,
                    'error': 'Failed to generate label'
                }), 500

            return jsonify({
                'success': True,
                'label': label_base64,
                'asset': {
                    'id': asset.id,
                    'serial_num': asset.serial_num,
                    'asset_tag': asset.asset_tag,
                    'name': asset.name
                }
            })

        finally:
            db_session.close()

    except Exception as e:
        logger.error(f"Error generating asset label: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to generate label'
        }), 500


# ============= Asset Image Upload =============

@mobile_api_bp.route('/assets/<int:asset_id>/image', methods=['POST'])
@mobile_auth_required
def upload_asset_image(asset_id):
    """
    Upload an image for an asset

    POST /api/mobile/v1/assets/<asset_id>/image
    Headers: Authorization: Bearer <token>
    Body: {
        "image": "base64_encoded_image_data",
        "content_type": "image/jpeg"  // or "image/png"
    }

    OR multipart/form-data with 'image' file field

    Returns:
        {
            "success": true,
            "image_url": "/static/uploads/assets/asset_123_timestamp.jpg",
            "message": "Image uploaded successfully"
        }
    """
    try:
        import os
        import base64
        import uuid

        user = request.current_mobile_user

        db_session = db_manager.get_session()
        try:
            asset = db_session.query(Asset).filter(Asset.id == asset_id).first()

            if not asset:
                return jsonify({
                    'success': False,
                    'error': 'Asset not found'
                }), 404

            # Determine upload directory
            from flask import current_app
            upload_folder = os.path.join(current_app.root_path, 'static', 'uploads', 'assets')
            os.makedirs(upload_folder, exist_ok=True)

            image_data = None
            content_type = 'image/jpeg'
            filename_ext = 'jpg'

            # Check if it's a multipart form upload
            if request.files and 'image' in request.files:
                file = request.files['image']
                if file.filename:
                    image_data = file.read()
                    content_type = file.content_type or 'image/jpeg'
                    if 'png' in content_type.lower():
                        filename_ext = 'png'
                    elif 'gif' in content_type.lower():
                        filename_ext = 'gif'
            else:
                # JSON body with base64 image
                data = request.get_json()
                if data and data.get('image'):
                    # Handle data URL format (data:image/jpeg;base64,...)
                    image_str = data['image']
                    if image_str.startswith('data:'):
                        # Extract content type and base64 data
                        header, image_str = image_str.split(',', 1)
                        if 'png' in header.lower():
                            content_type = 'image/png'
                            filename_ext = 'png'
                        elif 'gif' in header.lower():
                            content_type = 'image/gif'
                            filename_ext = 'gif'

                    try:
                        image_data = base64.b64decode(image_str)
                    except Exception as e:
                        return jsonify({
                            'success': False,
                            'error': 'Invalid base64 image data'
                        }), 400

                    if data.get('content_type'):
                        content_type = data['content_type']
                        if 'png' in content_type.lower():
                            filename_ext = 'png'
                        elif 'gif' in content_type.lower():
                            filename_ext = 'gif'

            if not image_data:
                return jsonify({
                    'success': False,
                    'error': 'No image data provided'
                }), 400

            # Validate image size (max 10MB)
            if len(image_data) > 10 * 1024 * 1024:
                return jsonify({
                    'success': False,
                    'error': 'Image too large (max 10MB)'
                }), 400

            # Generate unique filename
            timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            unique_id = str(uuid.uuid4())[:8]
            filename = f"asset_{asset_id}_{timestamp}_{unique_id}.{filename_ext}"
            filepath = os.path.join(upload_folder, filename)

            # Delete old image if exists
            if asset.image_url:
                old_path = os.path.join(current_app.root_path, asset.image_url.lstrip('/'))
                if os.path.exists(old_path):
                    try:
                        os.remove(old_path)
                    except Exception:
                        pass

            # Save new image
            with open(filepath, 'wb') as f:
                f.write(image_data)

            # Update asset with image URL
            image_url = f"/static/uploads/assets/{filename}"
            asset.image_url = image_url
            asset.updated_at = datetime.utcnow()
            db_session.commit()

            logger.info(f"User {user.username} uploaded image for asset {asset_id}")

            return jsonify({
                'success': True,
                'message': 'Image uploaded successfully',
                'image_url': get_full_image_url(image_url),
                'asset_id': asset_id
            })

        except Exception as e:
            db_session.rollback()
            raise e
        finally:
            db_session.close()

    except Exception as e:
        logger.error(f"Error uploading asset image: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': 'Failed to upload image'
        }), 500


@mobile_api_bp.route('/assets/<int:asset_id>/image', methods=['GET'])
@mobile_auth_required
def get_asset_image(asset_id):
    """
    Get asset image URL

    GET /api/mobile/v1/assets/<asset_id>/image
    Headers: Authorization: Bearer <token>

    Returns:
        {
            "success": true,
            "image_url": "/static/uploads/assets/asset_123.jpg",
            "has_image": true
        }
    """
    try:
        db_session = db_manager.get_session()
        try:
            asset = db_session.query(Asset).filter(Asset.id == asset_id).first()

            if not asset:
                return jsonify({
                    'success': False,
                    'error': 'Asset not found'
                }), 404

            return jsonify({
                'success': True,
                'image_url': get_asset_image_url(asset),
                'has_image': bool(asset.image_url or get_asset_image_url(asset)),
                'asset_id': asset_id
            })

        finally:
            db_session.close()

    except Exception as e:
        logger.error(f"Error getting asset image: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to get image'
        }), 500


@mobile_api_bp.route('/assets/<int:asset_id>/image', methods=['DELETE'])
@mobile_auth_required
def delete_asset_image(asset_id):
    """
    Delete asset image

    DELETE /api/mobile/v1/assets/<asset_id>/image
    Headers: Authorization: Bearer <token>

    Returns:
        {
            "success": true,
            "message": "Image deleted successfully"
        }
    """
    try:
        import os

        user = request.current_mobile_user

        db_session = db_manager.get_session()
        try:
            asset = db_session.query(Asset).filter(Asset.id == asset_id).first()

            if not asset:
                return jsonify({
                    'success': False,
                    'error': 'Asset not found'
                }), 404

            if not asset.image_url:
                return jsonify({
                    'success': False,
                    'error': 'Asset has no image'
                }), 400

            # Delete file from disk
            from flask import current_app
            filepath = os.path.join(current_app.root_path, asset.image_url.lstrip('/'))
            if os.path.exists(filepath):
                try:
                    os.remove(filepath)
                except Exception:
                    pass

            # Clear image URL in database
            asset.image_url = None
            asset.updated_at = datetime.utcnow()
            db_session.commit()

            logger.info(f"User {user.username} deleted image for asset {asset_id}")

            return jsonify({
                'success': True,
                'message': 'Image deleted successfully'
            })

        except Exception as e:
            db_session.rollback()
            raise e
        finally:
            db_session.close()

    except Exception as e:
        logger.error(f"Error deleting asset image: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to delete image'
        }), 500


# ============================================================
# ACCESSORY MANAGEMENT ENDPOINTS
# ============================================================

@mobile_api_bp.route('/accessories', methods=['GET'])
@mobile_auth_required
def get_accessories():
    """
    Get accessories list with optional filters

    GET /api/mobile/v1/accessories?page=1&limit=20&search=cable&category=Cable&country=Singapore
    Headers: Authorization: Bearer <token>

    Query Parameters:
        page (int): Page number (default: 1)
        limit (int): Items per page (default: 20, max: 100)
        search (str): Text search across name, model_no, manufacturer
        category (str): Filter by category
        country (str): Filter by country
        status (str): Filter by status (Available, Checked Out, etc.)

    Response: {
        "success": true,
        "accessories": [...],
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

        # Get parameters
        page = request.args.get('page', 1, type=int)
        limit = min(request.args.get('limit', 20, type=int), 100)
        search = request.args.get('search', None)
        category_filter = request.args.get('category', None)
        country_filter = request.args.get('country', None)
        status_filter = request.args.get('status', None)

        db_session = db_manager.get_session()
        try:
            query = db_session.query(Accessory)

            # Apply search filter
            if search:
                search_term = f"%{search}%"
                query = query.filter(
                    (Accessory.name.ilike(search_term)) |
                    (Accessory.model_no.ilike(search_term)) |
                    (Accessory.manufacturer.ilike(search_term))
                )

            # Apply category filter
            if category_filter:
                query = query.filter(Accessory.category.ilike(f"%{category_filter}%"))

            # Apply country filter
            if country_filter:
                query = query.filter(Accessory.country == country_filter)

            # Apply status filter
            if status_filter:
                query = query.filter(Accessory.status.ilike(f"%{status_filter}%"))

            # Get total count
            total = query.count()

            # Apply pagination
            offset = (page - 1) * limit
            accessories = query.order_by(Accessory.created_at.desc()).offset(offset).limit(limit).all()

            # Format accessories for mobile
            accessory_list = []
            for accessory in accessories:
                accessory_data = {
                    'id': accessory.id,
                    'name': accessory.name,
                    'category': accessory.category,
                    'manufacturer': accessory.manufacturer,
                    'model_no': accessory.model_no,
                    'total_quantity': accessory.total_quantity,
                    'available_quantity': accessory.available_quantity,
                    'country': accessory.country,
                    'status': accessory.status,
                    'notes': accessory.notes,
                    'image_url': get_full_image_url(accessory.image_url),
                    'company': {
                        'id': accessory.company.id,
                        'name': accessory.company.name
                    } if accessory.company else None,
                    'created_at': accessory.created_at.isoformat() if accessory.created_at else None,
                    'updated_at': accessory.updated_at.isoformat() if accessory.updated_at else None
                }
                accessory_list.append(accessory_data)

            pages = (total + limit - 1) // limit

            return jsonify({
                'success': True,
                'accessories': accessory_list,
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
        logger.error(f"Get accessories error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to get accessories'
        }), 500


@mobile_api_bp.route('/accessories/<int:accessory_id>', methods=['GET'])
@mobile_auth_required
def get_accessory_detail(accessory_id):
    """
    Get detailed accessory information

    GET /api/mobile/v1/accessories/<accessory_id>
    Headers: Authorization: Bearer <token>

    Response: {
        "success": true,
        "accessory": {
            "id": 123,
            "name": "USB-C Cable",
            "category": "Cable",
            "manufacturer": "Apple",
            "model_no": "MLL82AM/A",
            "total_quantity": 50,
            "available_quantity": 35,
            "country": "Singapore",
            "status": "Available",
            "notes": "2m length",
            "image_url": "/static/uploads/accessories/acc_123.jpg",
            ...
        }
    }
    """
    try:
        db_session = db_manager.get_session()
        try:
            accessory = db_session.query(Accessory).filter(Accessory.id == accessory_id).first()

            if not accessory:
                return jsonify({
                    'success': False,
                    'error': 'Accessory not found'
                }), 404

            accessory_data = {
                'id': accessory.id,
                'name': accessory.name,
                'category': accessory.category,
                'manufacturer': accessory.manufacturer,
                'model_no': accessory.model_no,
                'total_quantity': accessory.total_quantity,
                'available_quantity': accessory.available_quantity,
                'country': accessory.country,
                'status': accessory.status,
                'notes': accessory.notes,
                'image_url': get_full_image_url(accessory.image_url),
                'customer_id': accessory.customer_id,
                'company': {
                    'id': accessory.company.id,
                    'name': accessory.company.name
                } if accessory.company else None,
                'checkout_date': accessory.checkout_date.isoformat() if accessory.checkout_date else None,
                'return_date': accessory.return_date.isoformat() if accessory.return_date else None,
                'created_at': accessory.created_at.isoformat() if accessory.created_at else None,
                'updated_at': accessory.updated_at.isoformat() if accessory.updated_at else None
            }

            return jsonify({
                'success': True,
                'accessory': accessory_data
            })

        finally:
            db_session.close()

    except Exception as e:
        logger.error(f"Get accessory detail error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to get accessory detail'
        }), 500


@mobile_api_bp.route('/accessories/search', methods=['GET'])
@mobile_auth_required
def search_accessories():
    """
    Search for accessories by name, model number, or manufacturer

    GET /api/mobile/v1/accessories/search?q=USB&limit=20
    Headers: Authorization: Bearer <token>

    Query Parameters:
        q (str): Search query
        limit (int): Max results (default: 20)

    Response: {
        "success": true,
        "accessories": [...]
    }
    """
    try:
        search_query = request.args.get('q', '').strip()
        limit = min(request.args.get('limit', 20, type=int), 50)

        if not search_query:
            return jsonify({
                'success': False,
                'error': 'Search query (q) is required'
            }), 400

        db_session = db_manager.get_session()
        try:
            query = db_session.query(Accessory).filter(
                (Accessory.name.ilike(f'%{search_query}%')) |
                (Accessory.model_no.ilike(f'%{search_query}%')) |
                (Accessory.manufacturer.ilike(f'%{search_query}%'))
            )

            accessories = query.limit(limit).all()

            accessories_list = []
            for accessory in accessories:
                accessories_list.append({
                    'id': accessory.id,
                    'name': accessory.name,
                    'category': accessory.category,
                    'manufacturer': accessory.manufacturer,
                    'model_no': accessory.model_no,
                    'available_quantity': accessory.available_quantity,
                    'status': accessory.status,
                    'image_url': get_full_image_url(accessory.image_url)
                })

            return jsonify({
                'success': True,
                'accessories': accessories_list
            })

        finally:
            db_session.close()

    except Exception as e:
        logger.error(f"Search accessories error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to search accessories'
        }), 500


# ============= Accessory Image Upload =============

@mobile_api_bp.route('/accessories/<int:accessory_id>/image', methods=['POST'])
@mobile_auth_required
def upload_accessory_image(accessory_id):
    """
    Upload an image for an accessory

    POST /api/mobile/v1/accessories/<accessory_id>/image
    Headers: Authorization: Bearer <token>
    Body: {
        "image": "base64_encoded_image_data",
        "content_type": "image/jpeg"  // or "image/png"
    }

    OR multipart/form-data with 'image' file field

    Returns:
        {
            "success": true,
            "image_url": "/static/uploads/accessories/accessory_123_timestamp.jpg",
            "message": "Image uploaded successfully"
        }
    """
    try:
        import os
        import base64
        import uuid

        user = request.current_mobile_user

        db_session = db_manager.get_session()
        try:
            accessory = db_session.query(Accessory).filter(Accessory.id == accessory_id).first()

            if not accessory:
                return jsonify({
                    'success': False,
                    'error': 'Accessory not found'
                }), 404

            # Determine upload directory
            from flask import current_app
            upload_folder = os.path.join(current_app.root_path, 'static', 'uploads', 'accessories')
            os.makedirs(upload_folder, exist_ok=True)

            image_data = None
            content_type = 'image/jpeg'
            filename_ext = 'jpg'

            # Check if it's a multipart form upload
            if request.files and 'image' in request.files:
                file = request.files['image']
                if file.filename:
                    image_data = file.read()
                    content_type = file.content_type or 'image/jpeg'
                    if 'png' in content_type.lower():
                        filename_ext = 'png'
                    elif 'gif' in content_type.lower():
                        filename_ext = 'gif'
            else:
                # JSON body with base64 image
                data = request.get_json()
                if data and data.get('image'):
                    image_str = data['image']
                    if image_str.startswith('data:'):
                        header, image_str = image_str.split(',', 1)
                        if 'png' in header.lower():
                            content_type = 'image/png'
                            filename_ext = 'png'
                        elif 'gif' in header.lower():
                            content_type = 'image/gif'
                            filename_ext = 'gif'

                    try:
                        image_data = base64.b64decode(image_str)
                    except Exception:
                        return jsonify({
                            'success': False,
                            'error': 'Invalid base64 image data'
                        }), 400

                    if data.get('content_type'):
                        content_type = data['content_type']
                        if 'png' in content_type.lower():
                            filename_ext = 'png'
                        elif 'gif' in content_type.lower():
                            filename_ext = 'gif'

            if not image_data:
                return jsonify({
                    'success': False,
                    'error': 'No image data provided'
                }), 400

            # Validate image size (max 10MB)
            if len(image_data) > 10 * 1024 * 1024:
                return jsonify({
                    'success': False,
                    'error': 'Image too large (max 10MB)'
                }), 400

            # Generate unique filename
            timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            unique_id = str(uuid.uuid4())[:8]
            filename = f"accessory_{accessory_id}_{timestamp}_{unique_id}.{filename_ext}"
            filepath = os.path.join(upload_folder, filename)

            # Delete old image if exists
            if accessory.image_url:
                old_path = os.path.join(current_app.root_path, accessory.image_url.lstrip('/'))
                if os.path.exists(old_path):
                    try:
                        os.remove(old_path)
                    except Exception:
                        pass

            # Save new image
            with open(filepath, 'wb') as f:
                f.write(image_data)

            # Update accessory with image URL
            image_url = f"/static/uploads/accessories/{filename}"
            accessory.image_url = image_url
            accessory.updated_at = datetime.utcnow()
            db_session.commit()

            logger.info(f"User {user.username} uploaded image for accessory {accessory_id}")

            return jsonify({
                'success': True,
                'message': 'Image uploaded successfully',
                'image_url': get_full_image_url(image_url),
                'accessory_id': accessory_id
            })

        except Exception as e:
            db_session.rollback()
            raise e
        finally:
            db_session.close()

    except Exception as e:
        logger.error(f"Error uploading accessory image: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': 'Failed to upload image'
        }), 500


@mobile_api_bp.route('/accessories/<int:accessory_id>/image', methods=['GET'])
@mobile_auth_required
def get_accessory_image(accessory_id):
    """
    Get accessory image URL

    GET /api/mobile/v1/accessories/<accessory_id>/image
    Headers: Authorization: Bearer <token>

    Returns:
        {
            "success": true,
            "image_url": "/static/uploads/accessories/accessory_123.jpg",
            "has_image": true
        }
    """
    try:
        db_session = db_manager.get_session()
        try:
            accessory = db_session.query(Accessory).filter(Accessory.id == accessory_id).first()

            if not accessory:
                return jsonify({
                    'success': False,
                    'error': 'Accessory not found'
                }), 404

            return jsonify({
                'success': True,
                'image_url': get_full_image_url(accessory.image_url),
                'has_image': bool(accessory.image_url),
                'accessory_id': accessory_id
            })

        finally:
            db_session.close()

    except Exception as e:
        logger.error(f"Error getting accessory image: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to get image'
        }), 500


@mobile_api_bp.route('/accessories/<int:accessory_id>/image', methods=['DELETE'])
@mobile_auth_required
def delete_accessory_image(accessory_id):
    """
    Delete accessory image

    DELETE /api/mobile/v1/accessories/<accessory_id>/image
    Headers: Authorization: Bearer <token>

    Returns:
        {
            "success": true,
            "message": "Image deleted successfully"
        }
    """
    try:
        import os

        user = request.current_mobile_user

        db_session = db_manager.get_session()
        try:
            accessory = db_session.query(Accessory).filter(Accessory.id == accessory_id).first()

            if not accessory:
                return jsonify({
                    'success': False,
                    'error': 'Accessory not found'
                }), 404

            if not accessory.image_url:
                return jsonify({
                    'success': False,
                    'error': 'Accessory has no image'
                }), 400

            # Delete file from disk
            from flask import current_app
            filepath = os.path.join(current_app.root_path, accessory.image_url.lstrip('/'))
            if os.path.exists(filepath):
                try:
                    os.remove(filepath)
                except Exception:
                    pass

            # Clear image URL in database
            accessory.image_url = None
            accessory.updated_at = datetime.utcnow()
            db_session.commit()

            logger.info(f"User {user.username} deleted image for accessory {accessory_id}")

            return jsonify({
                'success': True,
                'message': 'Image deleted successfully'
            })

        except Exception as e:
            db_session.rollback()
            raise e
        finally:
            db_session.close()

    except Exception as e:
        logger.error(f"Error deleting accessory image: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to delete image'
        }), 500


# ============================================================================
# MacBook Specs Collector Mobile API Endpoints
# ============================================================================

@mobile_api_bp.route('/specs', methods=['GET'])
@mobile_auth_required
def get_device_specs():
    """
    Get list of pending device specs for mobile app.

    Query params:
    - processed: 'true' or 'false' to filter by processed status (default: false)
    - limit: max number of results (default: 50)
    """
    try:
        user = request.current_mobile_user
        db_session = db_manager.get_session()

        try:
            from models.device_spec import DeviceSpec
            from utils.mac_models import get_mac_model_name

            # Parse query params
            processed = request.args.get('processed', 'false').lower() == 'true'
            limit = min(int(request.args.get('limit', 50)), 100)

            # Query specs
            query = db_session.query(DeviceSpec).filter(
                DeviceSpec.processed == processed
            ).order_by(DeviceSpec.submitted_at.desc()).limit(limit)

            specs = query.all()

            # Format response
            specs_list = []
            for spec in specs:
                model_name_translated = get_mac_model_name(spec.model_id) if spec.model_id else spec.model_name
                specs_list.append({
                    'id': spec.id,
                    'serial_number': spec.serial_number,
                    'model_id': spec.model_id,
                    'model_name': model_name_translated or spec.model_name,
                    'cpu': spec.cpu,
                    'cpu_cores': spec.cpu_cores,
                    'ram_gb': spec.ram_gb,
                    'storage_gb': spec.storage_gb,
                    'storage_type': spec.storage_type,
                    'battery_cycles': spec.battery_cycles,
                    'battery_health': spec.battery_health,
                    'submitted_at': spec.submitted_at.isoformat() if spec.submitted_at else None,
                    'processed': spec.processed
                })

            return jsonify({
                'success': True,
                'count': len(specs_list),
                'specs': specs_list
            })

        finally:
            db_session.close()

    except Exception as e:
        logger.error(f"Error getting device specs: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to get device specs'
        }), 500


@mobile_api_bp.route('/specs/<int:spec_id>', methods=['GET'])
@mobile_auth_required
def get_device_spec_detail(spec_id):
    """
    Get detailed device spec information for mobile app.
    Returns all spec data for auto-filling asset creation form.
    """
    try:
        user = request.current_mobile_user
        db_session = db_manager.get_session()

        try:
            from models.device_spec import DeviceSpec
            from utils.mac_models import get_mac_model_name

            spec = db_session.query(DeviceSpec).get(spec_id)

            if not spec:
                return jsonify({
                    'success': False,
                    'error': 'Spec not found'
                }), 404

            model_name_translated = get_mac_model_name(spec.model_id) if spec.model_id else spec.model_name

            return jsonify({
                'success': True,
                'spec': {
                    'id': spec.id,
                    'serial_number': spec.serial_number,
                    'hardware_uuid': spec.hardware_uuid,
                    'model_id': spec.model_id,
                    'model_name': spec.model_name,
                    'model_name_translated': model_name_translated,
                    'cpu': spec.cpu,
                    'cpu_cores': spec.cpu_cores,
                    'gpu': spec.gpu,
                    'gpu_cores': spec.gpu_cores,
                    'ram_gb': spec.ram_gb,
                    'memory_type': spec.memory_type,
                    'storage_gb': spec.storage_gb,
                    'storage_type': spec.storage_type,
                    'free_space': spec.free_space,
                    'os_name': spec.os_name,
                    'os_version': spec.os_version,
                    'os_build': spec.os_build,
                    'battery_cycles': spec.battery_cycles,
                    'battery_health': spec.battery_health,
                    'wifi_mac': spec.wifi_mac,
                    'ethernet_mac': spec.ethernet_mac,
                    'ip_address': spec.ip_address,
                    'submitted_at': spec.submitted_at.isoformat() if spec.submitted_at else None,
                    'processed': spec.processed,
                    'processed_at': spec.processed_at.isoformat() if spec.processed_at else None,
                    'asset_id': spec.asset_id,
                    # Pre-formatted fields for asset creation
                    'asset_prefill': {
                        'serial_num': spec.serial_number or '',
                        'model': spec.model_id or '',
                        'product': model_name_translated or spec.model_name or '',
                        'asset_type': 'APPLE',
                        'cpu_type': spec.cpu or '',
                        'cpu_cores': spec.cpu_cores or '',
                        'gpu_cores': spec.gpu_cores or '',
                        'memory': f"{spec.ram_gb} GB" if spec.ram_gb else '',
                        'harddrive': f"{spec.storage_gb} GB {spec.storage_type or ''}".strip() if spec.storage_gb else '',
                        'manufacturer': 'Apple'
                    }
                }
            })

        finally:
            db_session.close()

    except Exception as e:
        logger.error(f"Error getting device spec detail: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to get device spec'
        }), 500


@mobile_api_bp.route('/specs/<int:spec_id>/create-asset', methods=['POST'])
@mobile_auth_required
def create_asset_from_spec(spec_id):
    """
    Create an asset from a device spec.
    Accepts additional fields to merge with spec data.

    Request body (all optional, will use spec data if not provided):
    - asset_tag: Asset tag
    - status: Asset status (default: IN_STOCK)
    - condition: Asset condition
    - customer: Customer name
    - country: Country
    - notes: Additional notes
    """
    try:
        user = request.current_mobile_user

        # Check if user has permission to create assets
        if not hasattr(user, 'can_create_assets') or not user.can_create_assets:
            if user.user_type not in [UserType.ADMIN, UserType.COUNTRY_ADMIN]:
                return jsonify({
                    'success': False,
                    'error': 'You do not have permission to create assets'
                }), 403

        db_session = db_manager.get_session()

        try:
            from models.device_spec import DeviceSpec
            from utils.mac_models import get_mac_model_name

            spec = db_session.query(DeviceSpec).get(spec_id)

            if not spec:
                return jsonify({
                    'success': False,
                    'error': 'Spec not found'
                }), 404

            if spec.processed:
                return jsonify({
                    'success': False,
                    'error': 'This spec has already been processed'
                }), 400

            # Get request data
            data = request.get_json() or {}

            # Translate model name
            model_name_translated = get_mac_model_name(spec.model_id) if spec.model_id else spec.model_name

            # Check for duplicate serial number
            existing_asset = db_session.query(Asset).filter(
                Asset.serial_num == spec.serial_number
            ).first()

            if existing_asset:
                return jsonify({
                    'success': False,
                    'error': f'An asset with serial number {spec.serial_number} already exists',
                    'existing_asset_id': existing_asset.id
                }), 409

            # Create new asset
            new_asset = Asset(
                asset_tag=data.get('asset_tag', ''),
                serial_num=spec.serial_number or '',
                model=spec.model_id or '',
                name=model_name_translated or spec.model_name or '',
                asset_type='APPLE',
                manufacturer='Apple',
                cpu_type=spec.cpu or '',
                cpu_cores=spec.cpu_cores or '',
                gpu_cores=spec.gpu_cores or '',
                memory=f"{spec.ram_gb} GB" if spec.ram_gb else '',
                harddrive=f"{spec.storage_gb} GB {spec.storage_type or ''}".strip() if spec.storage_gb else '',
                status=AssetStatus[data.get('status', 'IN_STOCK')],
                condition=data.get('condition', ''),
                customer=data.get('customer', ''),
                country=data.get('country', ''),
                notes=data.get('notes', ''),
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )

            # Auto-assign image for MacBook
            if 'macbook' in (model_name_translated or '').lower():
                new_asset.image_url = '/static/images/products/macbook.png'

            db_session.add(new_asset)
            db_session.flush()

            # Mark spec as processed
            spec.processed = True
            spec.processed_at = datetime.utcnow()
            spec.asset_id = new_asset.id
            spec.notes = f"Asset created via mobile API: {new_asset.asset_tag or new_asset.serial_num}"

            db_session.commit()

            logger.info(f"User {user.username} created asset {new_asset.id} from spec {spec_id} via mobile API")

            return jsonify({
                'success': True,
                'message': 'Asset created successfully',
                'asset': {
                    'id': new_asset.id,
                    'asset_tag': new_asset.asset_tag or '',
                    'serial_num': new_asset.serial_num or '',
                    'name': new_asset.name or '',
                    'model': new_asset.model or '',
                    'status': new_asset.status.value if new_asset.status else 'Unknown'
                }
            })

        except KeyError as e:
            db_session.rollback()
            return jsonify({
                'success': False,
                'error': f'Invalid status value: {str(e)}'
            }), 400
        except Exception as e:
            db_session.rollback()
            raise e
        finally:
            db_session.close()

    except Exception as e:
        logger.error(f"Error creating asset from spec: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to create asset'
        }), 500


@mobile_api_bp.route('/specs/<int:spec_id>/mark-processed', methods=['POST'])
@mobile_auth_required
def mark_spec_processed_mobile(spec_id):
    """
    Mark a spec as processed without creating an asset.
    Useful for skipping or dismissing a spec.

    Request body (optional):
    - notes: Reason for marking as processed
    """
    try:
        user = request.current_mobile_user
        db_session = db_manager.get_session()

        try:
            from models.device_spec import DeviceSpec

            spec = db_session.query(DeviceSpec).get(spec_id)

            if not spec:
                return jsonify({
                    'success': False,
                    'error': 'Spec not found'
                }), 404

            data = request.get_json() or {}

            spec.processed = True
            spec.processed_at = datetime.utcnow()
            spec.notes = data.get('notes', 'Marked as processed via mobile API')

            db_session.commit()

            logger.info(f"User {user.username} marked spec {spec_id} as processed via mobile API")

            return jsonify({
                'success': True,
                'message': 'Spec marked as processed'
            })

        finally:
            db_session.close()

    except Exception as e:
        logger.error(f"Error marking spec as processed: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to mark spec as processed'
        }), 500


@mobile_api_bp.route('/specs/<int:spec_id>/find-tickets', methods=['GET'])
@mobile_auth_required
def find_related_tickets_mobile(spec_id):
    """
    Find tickets related to a device spec by searching serial number, model, etc.
    Returns tickets that can be linked when creating an asset.
    """
    try:
        user = request.current_mobile_user
        db_session = db_manager.get_session()

        try:
            from models.device_spec import DeviceSpec
            from models.ticket import Ticket
            from sqlalchemy import or_

            spec = db_session.query(DeviceSpec).get(spec_id)
            if not spec:
                return jsonify({'success': False, 'error': 'Spec not found'}), 404

            # Search for tickets that might be related to this spec
            search_terms = []
            if spec.serial_number:
                search_terms.append(spec.serial_number)
            if spec.model_id:
                search_terms.append(spec.model_id)
            if spec.model_name:
                search_terms.append(spec.model_name)

            if not search_terms:
                return jsonify({
                    'success': True,
                    'tickets': [],
                    'search_terms': [],
                    'message': 'No search terms available for this spec'
                })

            # Build search filters - use 'subject' not 'title' for Ticket model
            filters = []
            for term in search_terms:
                filters.append(Ticket.subject.ilike(f'%{term}%'))
                if hasattr(Ticket, 'description') and Ticket.description is not None:
                    filters.append(Ticket.description.ilike(f'%{term}%'))
                if hasattr(Ticket, 'serial_number') and Ticket.serial_number is not None:
                    filters.append(Ticket.serial_number.ilike(f'%{term}%'))
                if hasattr(Ticket, 'return_description') and Ticket.return_description is not None:
                    filters.append(Ticket.return_description.ilike(f'%{term}%'))

            # Query tickets
            tickets = db_session.query(Ticket).filter(
                or_(*filters)
            ).order_by(Ticket.created_at.desc()).limit(20).all()

            # Format response
            tickets_list = []
            for ticket in tickets:
                tickets_list.append({
                    'id': ticket.id,
                    'display_id': ticket.display_id if hasattr(ticket, 'display_id') else f'#{ticket.id}',
                    'title': ticket.subject,  # Use subject as title
                    'status': ticket.status.value if ticket.status else 'Unknown',
                    'category': ticket.category.value if hasattr(ticket, 'category') and ticket.category else '',
                    'created_at': ticket.created_at.isoformat() if ticket.created_at else None,
                    'customer_name': ticket.customer.name if hasattr(ticket, 'customer') and ticket.customer else ''
                })

            return jsonify({
                'success': True,
                'count': len(tickets_list),
                'tickets': tickets_list,
                'search_terms': search_terms
            })

        finally:
            db_session.close()

    except Exception as e:
        logger.error(f"Error finding related tickets: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to find related tickets'
        }), 500


@mobile_api_bp.route('/specs/<int:spec_id>/create-asset-with-ticket', methods=['POST'])
@mobile_auth_required
def create_asset_from_spec_with_ticket(spec_id):
    """
    Create an asset from a device spec and link it to a ticket.

    Request body:
    - ticket_id: (required) ID of the ticket to link the asset to
    - asset_tag: (optional) Asset tag
    - status: (optional) Asset status (default: IN_STOCK)
    - condition: (optional) Asset condition
    - notes: (optional) Additional notes
    """
    try:
        user = request.current_mobile_user

        # Check if user has permission to create assets
        if not hasattr(user, 'can_create_assets') or not user.can_create_assets:
            if user.user_type not in [UserType.ADMIN, UserType.COUNTRY_ADMIN]:
                return jsonify({
                    'success': False,
                    'error': 'You do not have permission to create assets'
                }), 403

        db_session = db_manager.get_session()

        try:
            from models.device_spec import DeviceSpec
            from models.ticket import Ticket
            from utils.mac_models import get_mac_model_name
            from sqlalchemy import text

            spec = db_session.query(DeviceSpec).get(spec_id)
            if not spec:
                return jsonify({'success': False, 'error': 'Spec not found'}), 404

            if spec.processed:
                return jsonify({
                    'success': False,
                    'error': 'This spec has already been processed'
                }), 400

            # Get request data
            data = request.get_json() or {}
            ticket_id = data.get('ticket_id')

            if not ticket_id:
                return jsonify({
                    'success': False,
                    'error': 'ticket_id is required'
                }), 400

            # Verify ticket exists
            ticket = db_session.query(Ticket).get(ticket_id)
            if not ticket:
                return jsonify({
                    'success': False,
                    'error': 'Ticket not found'
                }), 404

            # Translate model name
            model_name_translated = get_mac_model_name(spec.model_id) if spec.model_id else spec.model_name

            # Check for duplicate serial number
            existing_asset = db_session.query(Asset).filter(
                Asset.serial_num == spec.serial_number
            ).first()

            if existing_asset:
                return jsonify({
                    'success': False,
                    'error': f'An asset with serial number {spec.serial_number} already exists',
                    'existing_asset_id': existing_asset.id
                }), 409

            # Create new asset
            new_asset = Asset(
                asset_tag=data.get('asset_tag', ''),
                serial_num=spec.serial_number or '',
                model=spec.model_id or '',
                name=model_name_translated or spec.model_name or '',
                asset_type='APPLE',
                manufacturer='Apple',
                cpu_type=spec.cpu or '',
                cpu_cores=spec.cpu_cores or '',
                gpu_cores=spec.gpu_cores or '',
                memory=f"{spec.ram_gb} GB" if spec.ram_gb else '',
                harddrive=f"{spec.storage_gb} GB {spec.storage_type or ''}".strip() if spec.storage_gb else '',
                status=AssetStatus[data.get('status', 'IN_STOCK')],
                condition=data.get('condition', ''),
                notes=data.get('notes', ''),
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )

            # Auto-assign image for MacBook
            if 'macbook' in (model_name_translated or '').lower():
                new_asset.image_url = '/static/images/products/macbook.png'

            db_session.add(new_asset)
            db_session.flush()

            # Link asset to ticket using direct SQL
            try:
                stmt = text("""
                    INSERT INTO ticket_assets (ticket_id, asset_id)
                    VALUES (:ticket_id, :asset_id)
                """)
                db_session.execute(stmt, {"ticket_id": ticket_id, "asset_id": new_asset.id})
            except Exception as link_error:
                logger.warning(f"Error linking asset to ticket: {link_error}")

            # Mark spec as processed
            spec.processed = True
            spec.processed_at = datetime.utcnow()
            spec.asset_id = new_asset.id
            spec.notes = f"Asset created and linked to ticket {ticket.display_id if hasattr(ticket, 'display_id') else ticket_id} via mobile API"

            db_session.commit()

            logger.info(f"User {user.username} created asset {new_asset.id} from spec {spec_id} and linked to ticket {ticket_id}")

            return jsonify({
                'success': True,
                'message': 'Asset created and linked to ticket successfully',
                'asset': {
                    'id': new_asset.id,
                    'asset_tag': new_asset.asset_tag or '',
                    'serial_num': new_asset.serial_num or '',
                    'name': new_asset.name or '',
                    'model': new_asset.model or '',
                    'status': new_asset.status.value if new_asset.status else 'Unknown'
                },
                'ticket': {
                    'id': ticket.id,
                    'display_id': ticket.display_id if hasattr(ticket, 'display_id') else f'#{ticket.id}'
                }
            })

        except KeyError as e:
            db_session.rollback()
            return jsonify({
                'success': False,
                'error': f'Invalid status value: {str(e)}'
            }), 400
        except Exception as e:
            db_session.rollback()
            raise e
        finally:
            db_session.close()

    except Exception as e:
        logger.error(f"Error creating asset from spec with ticket: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to create asset'
        }), 500


# ============================================================================
# TICKET ATTACHMENTS API
# ============================================================================

ALLOWED_ATTACHMENT_EXTENSIONS = {'jpg', 'jpeg', 'png', 'gif', 'pdf', 'doc', 'docx', 'xls', 'xlsx', 'txt', 'csv'}
MAX_ATTACHMENT_SIZE = 10 * 1024 * 1024  # 10MB


def allowed_attachment_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_ATTACHMENT_EXTENSIONS


def get_attachment_url(attachment):
    """Get full URL for an attachment"""
    from flask import request as flask_request
    if not attachment.file_path:
        return None

    # Extract filename from path
    filename = os.path.basename(attachment.file_path)

    # Build URL
    base_url = flask_request.host_url.rstrip('/')
    return f"{base_url}/tickets/{attachment.ticket_id}/attachments/{attachment.id}/download"


def generate_thumbnail(image_path, thumbnail_path, size=(200, 200)):
    """Generate a thumbnail for an image"""
    try:
        from PIL import Image

        with Image.open(image_path) as img:
            # Convert to RGB if necessary (for PNG with transparency)
            if img.mode in ('RGBA', 'P'):
                img = img.convert('RGB')

            img.thumbnail(size, Image.Resampling.LANCZOS)
            img.save(thumbnail_path, 'JPEG', quality=85)
            return True
    except Exception as e:
        logger.warning(f"Failed to generate thumbnail: {e}")
        return False


def generate_pdf_thumbnail(pdf_path, thumbnail_path, size=(200, 200)):
    """Generate a thumbnail from the first page of a PDF"""
    try:
        from PIL import Image
        import fitz  # PyMuPDF

        # Open PDF and get first page
        doc = fitz.open(pdf_path)
        if len(doc) == 0:
            return False

        page = doc[0]

        # Render page to image (72 dpi is default, use higher for better quality)
        mat = fitz.Matrix(2, 2)  # 2x zoom for better quality
        pix = page.get_pixmap(matrix=mat)

        # Convert to PIL Image
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

        # Create thumbnail
        img.thumbnail(size, Image.Resampling.LANCZOS)
        img.save(thumbnail_path, 'JPEG', quality=85)

        doc.close()
        return True
    except ImportError:
        logger.warning("PyMuPDF (fitz) not installed, skipping PDF thumbnail generation")
        return False
    except Exception as e:
        logger.warning(f"Failed to generate PDF thumbnail: {e}")
        return False


def validate_pdf_magic_bytes(file_data):
    """Validate that file data starts with PDF magic bytes"""
    return file_data[:5] == b'%PDF-'


@mobile_api_bp.route('/tickets/<int:ticket_id>/attachments', methods=['POST'])
@mobile_auth_required
def upload_ticket_attachment(ticket_id):
    """
    Upload an attachment to a ticket

    POST /api/mobile/v1/tickets/<ticket_id>/attachments
    Headers: Authorization: Bearer <token>
    Body: multipart/form-data with 'file' field

    Returns:
        {
            "success": true,
            "message": "Document uploaded successfully",
            "attachment_id": 456,
            "attachment": {
                "id": 456,
                "filename": "scanned_document.jpg",
                "content_type": "image/jpeg",
                "size": 245678,
                "url": "...",
                "thumbnail_url": "...",
                "created_at": "2025-12-23T10:30:00Z"
            }
        }
    """
    try:
        import os
        import uuid
        from werkzeug.utils import secure_filename
        from models.ticket_attachment import TicketAttachment
        from models.ticket import Ticket

        user = request.current_mobile_user

        db_session = db_manager.get_session()
        try:
            # Verify ticket exists
            ticket = db_session.query(Ticket).filter(Ticket.id == ticket_id).first()
            if not ticket:
                return jsonify({
                    'success': False,
                    'error': 'Ticket not found'
                }), 404

            # Check if file was provided
            if 'file' not in request.files:
                return jsonify({
                    'success': False,
                    'error': 'No file provided'
                }), 400

            file = request.files['file']
            if not file or not file.filename:
                return jsonify({
                    'success': False,
                    'error': 'No file provided'
                }), 400

            # Validate file extension
            if not allowed_attachment_file(file.filename):
                return jsonify({
                    'success': False,
                    'error': f'Unsupported file type. Allowed: {", ".join(ALLOWED_ATTACHMENT_EXTENSIONS).upper()}'
                }), 415

            # Read file data and check size
            file_data = file.read()
            if len(file_data) > MAX_ATTACHMENT_SIZE:
                return jsonify({
                    'success': False,
                    'error': 'File too large. Maximum size is 10MB.'
                }), 413

            # Determine file extension and content type
            original_filename = secure_filename(file.filename)
            file_extension = original_filename.rsplit('.', 1)[1].lower() if '.' in original_filename else 'bin'
            content_type = file.content_type or 'application/octet-stream'

            # Validate PDF magic bytes if file claims to be PDF
            if file_extension == 'pdf' or content_type == 'application/pdf':
                if not validate_pdf_magic_bytes(file_data):
                    return jsonify({
                        'success': False,
                        'error': 'Invalid or corrupted PDF file'
                    }), 400
                file_extension = 'pdf'
                content_type = 'application/pdf'

            # Create upload directory
            from flask import current_app
            upload_folder = os.path.join(current_app.root_path, 'uploads', 'tickets', str(ticket_id))
            os.makedirs(upload_folder, exist_ok=True)

            # Generate unique filename
            timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            unique_id = str(uuid.uuid4())[:8]
            filename = f"{ticket_id}_{timestamp}_{unique_id}.{file_extension}"
            file_path = os.path.join(upload_folder, filename)

            # Save file
            with open(file_path, 'wb') as f:
                f.write(file_data)

            # Generate thumbnail for images and PDFs
            thumbnail_path = None
            thumbnail_url = None
            thumb_filename = f"thumb_{filename.rsplit('.', 1)[0]}.jpg"  # Always save as jpg
            thumbnail_path = os.path.join(upload_folder, thumb_filename)

            if file_extension.lower() in ('jpg', 'jpeg', 'png', 'gif'):
                if generate_thumbnail(file_path, thumbnail_path):
                    thumbnail_url = f"/uploads/tickets/{ticket_id}/{thumb_filename}"
            elif file_extension.lower() == 'pdf':
                if generate_pdf_thumbnail(file_path, thumbnail_path):
                    thumbnail_url = f"/uploads/tickets/{ticket_id}/{thumb_filename}"

            # Create attachment record
            attachment = TicketAttachment(
                ticket_id=ticket_id,
                filename=original_filename,
                file_path=file_path,
                file_type=file_extension,
                file_size=len(file_data),
                uploaded_by=user.id
            )
            db_session.add(attachment)
            db_session.commit()

            # Build response
            attachment_url = f"/uploads/tickets/{ticket_id}/{filename}"
            base_url = request.host_url.rstrip('/')

            logger.info(f"User {user.username} uploaded attachment {attachment.id} to ticket {ticket_id}")

            return jsonify({
                'success': True,
                'message': 'Document uploaded successfully',
                'attachment_id': attachment.id,
                'attachment': {
                    'id': attachment.id,
                    'filename': attachment.filename,
                    'content_type': content_type,
                    'size': attachment.file_size,
                    'url': f"{base_url}{attachment_url}",
                    'thumbnail_url': f"{base_url}{thumbnail_url}" if thumbnail_url else None,
                    'created_at': attachment.created_at.isoformat() + 'Z' if attachment.created_at else None
                }
            }), 201

        except Exception as e:
            db_session.rollback()
            raise e
        finally:
            db_session.close()

    except Exception as e:
        logger.error(f"Error uploading ticket attachment: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': 'Failed to upload document'
        }), 500


@mobile_api_bp.route('/tickets/<int:ticket_id>/attachments', methods=['GET'])
@mobile_auth_required
def get_ticket_attachments(ticket_id):
    """
    Get all attachments for a ticket

    GET /api/mobile/v1/tickets/<ticket_id>/attachments
    Headers: Authorization: Bearer <token>

    Returns:
        {
            "success": true,
            "attachments": [...],
            "total": 5
        }
    """
    try:
        from models.ticket_attachment import TicketAttachment
        from models.ticket import Ticket
        from sqlalchemy.orm import joinedload

        user = request.current_mobile_user

        db_session = db_manager.get_session()
        try:
            # Verify ticket exists
            ticket = db_session.query(Ticket).filter(Ticket.id == ticket_id).first()
            if not ticket:
                return jsonify({
                    'success': False,
                    'error': 'Ticket not found'
                }), 404

            # Get attachments with uploader info
            attachments = db_session.query(TicketAttachment).options(
                joinedload(TicketAttachment.uploader)
            ).filter(
                TicketAttachment.ticket_id == ticket_id
            ).order_by(TicketAttachment.created_at.desc()).all()

            base_url = request.host_url.rstrip('/')

            attachments_list = []
            for att in attachments:
                # Build URLs
                filename = os.path.basename(att.file_path) if att.file_path else None
                attachment_url = f"/uploads/tickets/{ticket_id}/{filename}" if filename else None

                # Check for thumbnail (images and PDFs)
                thumbnail_url = None
                if att.file_type and att.file_type.lower() in ('jpg', 'jpeg', 'png', 'gif', 'pdf') and filename:
                    # Thumbnail is always .jpg
                    base_filename = filename.rsplit('.', 1)[0] if '.' in filename else filename
                    thumb_filename = f"thumb_{base_filename}.jpg"
                    thumb_path = os.path.join(os.path.dirname(att.file_path), thumb_filename) if att.file_path else None
                    if thumb_path and os.path.exists(thumb_path):
                        thumbnail_url = f"/uploads/tickets/{ticket_id}/{thumb_filename}"

                # Determine content type
                content_type_map = {
                    'jpg': 'image/jpeg',
                    'jpeg': 'image/jpeg',
                    'png': 'image/png',
                    'gif': 'image/gif',
                    'pdf': 'application/pdf',
                    'doc': 'application/msword',
                    'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                    'xls': 'application/vnd.ms-excel',
                    'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                    'txt': 'text/plain',
                    'csv': 'text/csv'
                }
                content_type = content_type_map.get(att.file_type, 'application/octet-stream') if att.file_type else 'application/octet-stream'

                attachment_data = {
                    'id': att.id,
                    'filename': att.filename,
                    'content_type': content_type,
                    'size': att.file_size,
                    'url': f"{base_url}{attachment_url}" if attachment_url else None,
                    'thumbnail_url': f"{base_url}{thumbnail_url}" if thumbnail_url else None,
                    'created_at': att.created_at.isoformat() + 'Z' if att.created_at else None,
                    'uploaded_by': {
                        'id': att.uploader.id,
                        'name': att.uploader.username
                    } if att.uploader else None
                }
                attachments_list.append(attachment_data)

            return jsonify({
                'success': True,
                'attachments': attachments_list,
                'total': len(attachments_list)
            })

        finally:
            db_session.close()

    except Exception as e:
        logger.error(f"Error getting ticket attachments: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to get attachments'
        }), 500


@mobile_api_bp.route('/tickets/<int:ticket_id>/attachments/<int:attachment_id>', methods=['DELETE'])
@mobile_auth_required
def delete_ticket_attachment(ticket_id, attachment_id):
    """
    Delete an attachment from a ticket

    DELETE /api/mobile/v1/tickets/<ticket_id>/attachments/<attachment_id>
    Headers: Authorization: Bearer <token>

    Returns:
        {
            "success": true,
            "message": "Attachment deleted successfully"
        }
    """
    try:
        from models.ticket_attachment import TicketAttachment
        from models.ticket import Ticket

        user = request.current_mobile_user

        db_session = db_manager.get_session()
        try:
            # Verify ticket exists
            ticket = db_session.query(Ticket).filter(Ticket.id == ticket_id).first()
            if not ticket:
                return jsonify({
                    'success': False,
                    'error': 'Ticket not found'
                }), 404

            # Get attachment
            attachment = db_session.query(TicketAttachment).filter(
                TicketAttachment.id == attachment_id,
                TicketAttachment.ticket_id == ticket_id
            ).first()

            if not attachment:
                return jsonify({
                    'success': False,
                    'error': 'Attachment not found'
                }), 404

            # Delete files from disk
            if attachment.file_path and os.path.exists(attachment.file_path):
                try:
                    os.remove(attachment.file_path)

                    # Also try to remove thumbnail if exists
                    thumb_path = os.path.join(
                        os.path.dirname(attachment.file_path),
                        f"thumb_{os.path.basename(attachment.file_path)}"
                    )
                    if os.path.exists(thumb_path):
                        os.remove(thumb_path)
                except Exception as e:
                    logger.warning(f"Failed to delete attachment files: {e}")

            # Delete from database
            db_session.delete(attachment)
            db_session.commit()

            logger.info(f"User {user.username} deleted attachment {attachment_id} from ticket {ticket_id}")

            return jsonify({
                'success': True,
                'message': 'Attachment deleted successfully'
            })

        except Exception as e:
            db_session.rollback()
            raise e
        finally:
            db_session.close()

    except Exception as e:
        logger.error(f"Error deleting ticket attachment: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to delete attachment'
        }), 500


# =============================================================================
# Asset Intake Check-in Endpoints
# =============================================================================

@mobile_api_bp.route('/tickets/<int:ticket_id>/checkin', methods=['POST'])
@mobile_auth_required
def mobile_checkin_asset(ticket_id):
    """
    Check in an asset by serial number for Asset Intake tickets

    Request body:
        {
            "serial_number": "SN123456789"
        }

    Response:
        {
            "success": true,
            "message": "Asset SN123 checked in successfully",
            "asset": {"id": 1, "serial_number": "SN123", "asset_tag": "ASSET-001", "model": "MacBook Pro"},
            "progress": {"total": 10, "checked_in": 5, "pending": 5, "progress_percent": 50, "step": 2},
            "ticket_closed": false
        }
    """
    from models.ticket_asset_checkin import TicketAssetCheckin
    from sqlalchemy import func
    from sqlalchemy.orm import joinedload

    try:
        user = request.current_mobile_user

        db_session = db_manager.get_session()
        try:
            ticket = db_session.query(Ticket).options(
                joinedload(Ticket.assets)
            ).filter(Ticket.id == ticket_id).first()

            if not ticket:
                return jsonify({'success': False, 'error': 'Ticket not found'}), 404

            # Validate ticket is Asset Intake category
            if ticket.category != TicketCategory.ASSET_INTAKE:
                return jsonify({'success': False, 'error': 'Check-in is only available for Asset Intake tickets'}), 400

            data = request.get_json() or {}
            serial_number = data.get('serial_number', '').strip().upper()

            if not serial_number:
                return jsonify({'success': False, 'error': 'Serial number is required'}), 400

            # Find asset by serial number - try multiple variations
            # Some PDFs have leading 'S' prefix on serial numbers
            asset = db_session.query(Asset).filter(
                func.upper(Asset.serial_num) == serial_number
            ).first()

            # If not found, try with 'S' prefix (PDF extraction sometimes includes it)
            if not asset and not serial_number.startswith('S'):
                asset = db_session.query(Asset).filter(
                    func.upper(Asset.serial_num) == 'S' + serial_number
                ).first()

            # If not found, try without 'S' prefix (user might scan with S but DB has it without)
            if not asset and serial_number.startswith('S'):
                asset = db_session.query(Asset).filter(
                    func.upper(Asset.serial_num) == serial_number[1:]
                ).first()

            if not asset:
                return jsonify({'success': False, 'error': f'Asset not found with serial number: {serial_number}'}), 404

            # Check if asset is assigned to this ticket
            ticket_asset_ids = [a.id for a in ticket.assets]
            if asset.id not in ticket_asset_ids:
                return jsonify({'success': False, 'error': f'Asset {serial_number} is not assigned to this ticket'}), 400

            # Check if already checked in
            existing_checkin = db_session.query(TicketAssetCheckin).filter_by(
                ticket_id=ticket_id,
                asset_id=asset.id
            ).first()

            if existing_checkin and existing_checkin.checked_in:
                return jsonify({'success': False, 'error': f'Asset {serial_number} is already checked in'}), 400

            # Create or update check-in record
            if existing_checkin:
                existing_checkin.checked_in = True
                existing_checkin.checked_in_at = datetime.utcnow()
                existing_checkin.checked_in_by_id = user.id
            else:
                checkin = TicketAssetCheckin(
                    ticket_id=ticket_id,
                    asset_id=asset.id,
                    checked_in=True,
                    checked_in_at=datetime.utcnow(),
                    checked_in_by_id=user.id
                )
                db_session.add(checkin)

            db_session.commit()

            # Get updated progress
            progress = ticket.get_checkin_progress(db_session)
            ticket_closed = False

            # Auto-close ticket if all assets are checked in
            if progress['pending'] == 0 and progress['total'] > 0:
                ticket.status = TicketStatus.RESOLVED
                db_session.commit()
                ticket_closed = True

            logger.info(f"User {user.username} checked in asset {serial_number} for ticket {ticket_id}")

            return jsonify({
                'success': True,
                'message': f'Asset {serial_number} checked in successfully',
                'asset': {
                    'id': asset.id,
                    'serial_number': asset.serial_num,
                    'asset_tag': asset.asset_tag,
                    'model': asset.model
                },
                'progress': {
                    'total': progress['total'],
                    'checked_in': progress['checked_in'],
                    'pending': progress['pending'],
                    'progress_percent': progress['progress_percent'],
                    'step': ticket.get_intake_step(db_session)
                },
                'ticket_closed': ticket_closed
            })

        except Exception as e:
            db_session.rollback()
            raise e
        finally:
            db_session.close()

    except Exception as e:
        logger.error(f"Error checking in asset via mobile API: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({'success': False, 'error': str(e)}), 500


@mobile_api_bp.route('/tickets/<int:ticket_id>/checkin-status', methods=['GET'])
@mobile_auth_required
def mobile_get_checkin_status(ticket_id):
    """
    Get check-in status for an Asset Intake ticket

    Response:
        {
            "success": true,
            "ticket": {"id": 123, "display_id": "TICK-0123", "subject": "...", "status": "In Progress"},
            "progress": {
                "step": 2,
                "step_label": "Assets Added",
                "total": 10,
                "checked_in": 5,
                "pending": 5,
                "steps": [
                    {"number": 1, "label": "Case Created", "completed": true},
                    {"number": 2, "label": "Assets Added", "completed": true},
                    {"number": 3, "label": "All Checked In", "completed": false}
                ]
            },
            "assets": [
                {"id": 1, "serial_number": "SN001", "checked_in": true, "checked_in_at": "2025-12-23T10:30:00Z"},
                {"id": 2, "serial_number": "SN002", "checked_in": false}
            ]
        }
    """
    from models.ticket_asset_checkin import TicketAssetCheckin
    from sqlalchemy.orm import joinedload

    try:
        db_session = db_manager.get_session()
        try:
            ticket = db_session.query(Ticket).options(
                joinedload(Ticket.assets)
            ).filter(Ticket.id == ticket_id).first()

            if not ticket:
                return jsonify({'success': False, 'error': 'Ticket not found'}), 404

            if ticket.category != TicketCategory.ASSET_INTAKE:
                return jsonify({'success': False, 'error': 'Check-in status is only available for Asset Intake tickets'}), 400

            # Get all check-in records for this ticket
            checkins = db_session.query(TicketAssetCheckin).options(
                joinedload(TicketAssetCheckin.checked_in_by)
            ).filter_by(ticket_id=ticket_id).all()
            checkin_map = {c.asset_id: c for c in checkins}

            # Build asset list with check-in status
            assets_data = []
            for asset in ticket.assets:
                checkin = checkin_map.get(asset.id)
                assets_data.append({
                    'id': asset.id,
                    'serial_number': asset.serial_num,
                    'asset_tag': asset.asset_tag,
                    'model': asset.model,
                    'type': asset.type if hasattr(asset, 'type') else None,
                    'checked_in': checkin.checked_in if checkin else False,
                    'checked_in_at': checkin.checked_in_at.isoformat() if checkin and checkin.checked_in_at else None,
                    'checked_in_by': checkin.checked_in_by.full_name if checkin and checkin.checked_in_by else None
                })

            # Get progress and steps
            intake_detail = ticket.get_intake_steps_detail(db_session)

            # Add step label
            step_labels = {1: 'Case Created', 2: 'Assets Added', 3: 'All Checked In'}
            current_step = intake_detail['current_step']

            return jsonify({
                'success': True,
                'ticket': {
                    'id': ticket.id,
                    'display_id': ticket.display_id,
                    'subject': ticket.subject,
                    'status': ticket.status.value if ticket.status else None
                },
                'progress': {
                    'step': current_step,
                    'step_label': step_labels.get(current_step, 'Unknown'),
                    'total': intake_detail['progress']['total'],
                    'checked_in': intake_detail['progress']['checked_in'],
                    'pending': intake_detail['progress']['pending'],
                    'progress_percent': intake_detail['progress']['progress_percent']
                },
                'steps': intake_detail['steps'],
                'assets': assets_data
            })

        finally:
            db_session.close()

    except Exception as e:
        logger.error(f"Error getting check-in status via mobile API: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({'success': False, 'error': str(e)}), 500


@mobile_api_bp.route('/tickets/<int:ticket_id>/intake-assets', methods=['GET'])
@mobile_auth_required
def mobile_get_intake_assets(ticket_id):
    """
    Get list of assets for an Asset Intake ticket with check-in status
    Optimized endpoint for mobile asset list view

    Response:
        {
            "success": true,
            "assets": [
                {
                    "id": 1,
                    "serial_number": "SN001",
                    "asset_tag": "ASSET-001",
                    "model": "MacBook Pro",
                    "checked_in": true,
                    "checked_in_at": "2025-12-23T10:30:00Z"
                }
            ],
            "summary": {"total": 10, "checked_in": 5, "pending": 5}
        }
    """
    from models.ticket_asset_checkin import TicketAssetCheckin
    from sqlalchemy.orm import joinedload

    try:
        db_session = db_manager.get_session()
        try:
            ticket = db_session.query(Ticket).options(
                joinedload(Ticket.assets)
            ).filter(Ticket.id == ticket_id).first()

            if not ticket:
                return jsonify({'success': False, 'error': 'Ticket not found'}), 404

            if ticket.category != TicketCategory.ASSET_INTAKE:
                return jsonify({'success': False, 'error': 'This endpoint is only for Asset Intake tickets'}), 400

            # Get all check-in records
            checkins = db_session.query(TicketAssetCheckin).filter_by(
                ticket_id=ticket_id
            ).all()
            checkin_map = {c.asset_id: c for c in checkins}

            # Build asset list
            assets_data = []
            checked_in_count = 0
            for asset in ticket.assets:
                checkin = checkin_map.get(asset.id)
                is_checked_in = checkin.checked_in if checkin else False
                if is_checked_in:
                    checked_in_count += 1

                assets_data.append({
                    'id': asset.id,
                    'serial_number': asset.serial_num,
                    'asset_tag': asset.asset_tag,
                    'model': asset.model,
                    'type': asset.type if hasattr(asset, 'type') else None,
                    'image_url': get_asset_image_url(asset),
                    'checked_in': is_checked_in,
                    'checked_in_at': checkin.checked_in_at.isoformat() if checkin and checkin.checked_in_at else None
                })

            total = len(assets_data)

            return jsonify({
                'success': True,
                'assets': assets_data,
                'summary': {
                    'total': total,
                    'checked_in': checked_in_count,
                    'pending': total - checked_in_count
                }
            })

        finally:
            db_session.close()

    except Exception as e:
        logger.error(f"Error getting intake assets via mobile API: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({'success': False, 'error': str(e)}), 500


@mobile_api_bp.route('/tickets/<int:ticket_id>/undo-checkin/<int:asset_id>', methods=['POST'])
@mobile_auth_required
def mobile_undo_checkin(ticket_id, asset_id):
    """
    Undo a check-in for an asset

    Response:
        {
            "success": true,
            "message": "Check-in undone successfully",
            "progress": {"total": 10, "checked_in": 4, "pending": 6, "progress_percent": 40, "step": 2}
        }
    """
    from models.ticket_asset_checkin import TicketAssetCheckin
    from sqlalchemy.orm import joinedload

    try:
        user = request.current_mobile_user

        db_session = db_manager.get_session()
        try:
            ticket = db_session.query(Ticket).options(
                joinedload(Ticket.assets)
            ).filter(Ticket.id == ticket_id).first()

            if not ticket:
                return jsonify({'success': False, 'error': 'Ticket not found'}), 404

            if ticket.category != TicketCategory.ASSET_INTAKE:
                return jsonify({'success': False, 'error': 'Undo check-in is only available for Asset Intake tickets'}), 400

            # Find the check-in record
            checkin = db_session.query(TicketAssetCheckin).filter_by(
                ticket_id=ticket_id,
                asset_id=asset_id
            ).first()

            if not checkin or not checkin.checked_in:
                return jsonify({'success': False, 'error': 'Asset is not checked in'}), 400

            # Undo the check-in
            checkin.checked_in = False
            checkin.checked_in_at = None
            checkin.checked_in_by_id = None

            # If ticket was resolved, reopen it
            if ticket.status == TicketStatus.RESOLVED:
                ticket.status = TicketStatus.IN_PROGRESS

            db_session.commit()

            # Get updated progress
            progress = ticket.get_checkin_progress(db_session)

            logger.info(f"User {user.username} undid check-in for asset {asset_id} on ticket {ticket_id}")

            return jsonify({
                'success': True,
                'message': 'Check-in undone successfully',
                'progress': {
                    'total': progress['total'],
                    'checked_in': progress['checked_in'],
                    'pending': progress['pending'],
                    'progress_percent': progress['progress_percent'],
                    'step': ticket.get_intake_step(db_session)
                }
            })

        except Exception as e:
            db_session.rollback()
            raise e
        finally:
            db_session.close()

    except Exception as e:
        logger.error(f"Error undoing check-in via mobile API: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({'success': False, 'error': str(e)}), 500


@mobile_api_bp.route('/tickets/<int:ticket_id>/update-serial-checkin', methods=['POST'])
@mobile_auth_required
def mobile_update_serial_and_checkin(ticket_id):
    """
    Update an asset's serial number and check it in for Asset Intake tickets.

    This endpoint is used when the mobile app scans a serial number that differs
    from the original (e.g., correcting OCR errors from PDF extraction).

    Request body:
        {
            "asset_id": 123,
            "new_serial": "K59L170P9P"
        }

    Response:
        {
            "success": true,
            "message": "Asset serial updated and checked in successfully",
            "asset": {
                "id": 123,
                "serial_number": "K59L170P9P",
                "asset_tag": "SG-1234",
                "model": "MacBook Pro 14"
            },
            "progress": {
                "total": 10,
                "checked_in": 5,
                "pending": 5,
                "progress_percent": 50,
                "step": 2
            },
            "ticket_closed": false
        }
    """
    from models.ticket_asset_checkin import TicketAssetCheckin
    from sqlalchemy.orm import joinedload

    try:
        user = request.current_mobile_user

        db_session = db_manager.get_session()
        try:
            ticket = db_session.query(Ticket).options(
                joinedload(Ticket.assets)
            ).filter(Ticket.id == ticket_id).first()

            if not ticket:
                return jsonify({'success': False, 'error': 'Ticket not found'}), 404

            # Validate ticket is Asset Intake category
            if ticket.category != TicketCategory.ASSET_INTAKE:
                return jsonify({'success': False, 'error': 'Update serial check-in is only available for Asset Intake tickets'}), 400

            data = request.get_json() or {}
            asset_id = data.get('asset_id')
            new_serial = data.get('new_serial', '').strip()

            if not asset_id:
                return jsonify({'success': False, 'error': 'asset_id is required'}), 400

            if not new_serial:
                return jsonify({'success': False, 'error': 'new_serial is required'}), 400

            # Find the asset by ID
            asset = db_session.query(Asset).filter(Asset.id == asset_id).first()

            if not asset:
                return jsonify({'success': False, 'error': f'Asset not found with ID: {asset_id}'}), 404

            # Check if asset is assigned to this ticket
            ticket_asset_ids = [a.id for a in ticket.assets]
            if asset.id not in ticket_asset_ids:
                return jsonify({'success': False, 'error': f'Asset {asset_id} is not assigned to this ticket'}), 400

            # Check if new serial number already exists on another asset
            existing_asset = db_session.query(Asset).filter(
                Asset.serial_num == new_serial,
                Asset.id != asset_id
            ).first()

            if existing_asset:
                return jsonify({'success': False, 'error': f'Serial number {new_serial} already exists on another asset (ID: {existing_asset.id})'}), 400

            # Store old serial for logging
            old_serial = asset.serial_num

            # Update the serial number
            asset.serial_num = new_serial

            # Check if already checked in
            existing_checkin = db_session.query(TicketAssetCheckin).filter_by(
                ticket_id=ticket_id,
                asset_id=asset.id
            ).first()

            # Create or update check-in record
            if existing_checkin:
                existing_checkin.checked_in = True
                existing_checkin.checked_in_at = datetime.utcnow()
                existing_checkin.checked_in_by_id = user.id
            else:
                checkin = TicketAssetCheckin(
                    ticket_id=ticket_id,
                    asset_id=asset.id,
                    checked_in=True,
                    checked_in_at=datetime.utcnow(),
                    checked_in_by_id=user.id
                )
                db_session.add(checkin)

            db_session.commit()

            # Get updated progress
            progress = ticket.get_checkin_progress(db_session)
            ticket_closed = False

            # Auto-close ticket if all assets are checked in
            if progress['pending'] == 0 and progress['total'] > 0:
                ticket.status = TicketStatus.RESOLVED
                db_session.commit()
                ticket_closed = True

            logger.info(f"User {user.username} updated asset {asset_id} serial from '{old_serial}' to '{new_serial}' and checked in for ticket {ticket_id}")

            return jsonify({
                'success': True,
                'message': f'Asset serial updated and checked in successfully',
                'asset': {
                    'id': asset.id,
                    'serial_number': asset.serial_num,
                    'asset_tag': asset.asset_tag,
                    'model': asset.model
                },
                'progress': {
                    'total': progress['total'],
                    'checked_in': progress['checked_in'],
                    'pending': progress['pending'],
                    'progress_percent': progress['progress_percent'],
                    'step': ticket.get_intake_step(db_session)
                },
                'ticket_closed': ticket_closed
            })

        except Exception as e:
            db_session.rollback()
            raise e
        finally:
            db_session.close()

    except Exception as e:
        logger.error(f"Error updating serial and checking in via mobile API: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({'success': False, 'error': str(e)}), 500


# =============================================================================
# PDF/OCR Text Processing for Mobile
# =============================================================================

@mobile_api_bp.route('/extract-assets-from-text', methods=['POST'])
def mobile_extract_assets_from_text():
    """
    Extract asset information from pre-extracted OCR text.

    This endpoint allows the mobile app to perform OCR locally (using iOS Vision framework)
    and send the extracted text to the server for asset parsing. This is much faster than
    uploading PDF files for server-side OCR processing.

    Request Body:
        {
            "text": "The OCR-extracted text from the packing list PDF",
            "ticket_id": 123  // Optional - if provided, will associate assets with ticket
        }

    Response:
        {
            "success": true,
            "assets": [
                {
                    "serial_num": "ABC123...",
                    "name": "MacBook Air",
                    "model": "A3113",
                    "manufacturer": "Apple",
                    "category": "Laptop",
                    "cpu_type": "M3",
                    "cpu_cores": "8",
                    "gpu_cores": "10",
                    "memory": "16GB",
                    "harddrive": "256GB",
                    "hardware_type": "Laptop",
                    "condition": "New"
                },
                ...
            ],
            "count": 10,
            "message": "Successfully extracted 10 assets"
        }

    iOS Implementation Notes:
        - Use VNRecognizeTextRequest with .accurate recognition level
        - Set recognitionLanguages to ["en-US"]
        - Combine text from all recognized blocks in reading order
        - For multi-page PDFs, process each page and concatenate text
    """
    try:
        # Get auth token from header
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'success': False, 'error': 'Missing or invalid authorization token'}), 401

        token = auth_header.split(' ')[1]
        user = verify_mobile_token(token)

        if not user:
            return jsonify({'success': False, 'error': 'Invalid or expired token'}), 401

        # Get request data
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'Missing request body'}), 400

        text = data.get('text', '')
        if not text or not text.strip():
            return jsonify({'success': False, 'error': 'No text provided for extraction'}), 400

        ticket_id = data.get('ticket_id')

        # Log the extraction request
        logger.info(f"Mobile OCR extraction request from user {user.username}, text length: {len(text)}, ticket_id: {ticket_id}")

        # Use the existing extraction function
        from utils.pdf_extractor import extract_assets_from_text

        assets = extract_assets_from_text(text)

        logger.info(f"Extracted {len(assets)} assets from mobile OCR text")

        return jsonify({
            'success': True,
            'assets': assets,
            'count': len(assets),
            'message': f'Successfully extracted {len(assets)} asset{"s" if len(assets) != 1 else ""}'
        })

    except Exception as e:
        logger.error(f"Error extracting assets from mobile OCR text: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({'success': False, 'error': str(e)}), 500


@mobile_api_bp.route('/tickets/<int:ticket_id>/create-assets-from-text', methods=['POST'])
def mobile_create_assets_from_text(ticket_id):
    """
    Create assets from pre-extracted OCR text and link them to a ticket.

    This is a combined endpoint that:
    1. Extracts asset information from the provided OCR text
    2. Creates the assets in the database
    3. Links them to the specified ticket

    Request Body:
        {
            "text": "The OCR-extracted text from the packing list PDF",
            "asset_tags": ["SG-1180", "SG-1181", ...],  // Optional - auto-generated if not provided
            "company_id": 1  // Optional - defaults to ticket's company
        }

    Response:
        {
            "success": true,
            "created_assets": [...],
            "count": 10,
            "ticket_id": 123,
            "message": "Successfully created 10 assets and linked to ticket TICK-0123"
        }
    """
    try:
        # Get auth token from header
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'success': False, 'error': 'Missing or invalid authorization token'}), 401

        token = auth_header.split(' ')[1]
        user = verify_mobile_token(token)

        if not user:
            return jsonify({'success': False, 'error': 'Invalid or expired token'}), 401

        # Get request data
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'Missing request body'}), 400

        text = data.get('text', '')
        if not text or not text.strip():
            return jsonify({'success': False, 'error': 'No text provided for extraction'}), 400

        provided_tags = data.get('asset_tags', [])
        company_id = data.get('company_id')

        db_session = db_manager.get_session()
        try:
            # Get the ticket
            ticket = db_session.query(Ticket).filter(Ticket.id == ticket_id).first()
            if not ticket:
                return jsonify({'success': False, 'error': 'Ticket not found'}), 404

            # Use ticket's company if not provided
            if not company_id:
                company_id = ticket.company_id

            # Extract assets from text
            from utils.pdf_extractor import extract_assets_from_text
            assets_data = extract_assets_from_text(text)

            if not assets_data:
                return jsonify({
                    'success': False,
                    'error': 'No assets could be extracted from the provided text'
                }), 400

            # Generate asset tags if not provided
            import re
            if not provided_tags or len(provided_tags) < len(assets_data):
                # Find highest existing SG-XXXX tag
                existing_tags = db_session.query(Asset.asset_tag).filter(
                    Asset.asset_tag.like('SG-%')
                ).all()

                max_num = 0
                for (tag,) in existing_tags:
                    if tag:
                        match = re.match(r'SG-(\d+)', tag)
                        if match:
                            num = int(match.group(1))
                            if num > max_num:
                                max_num = num

                # Generate sequential tags starting from max + 1
                generated_tags = []
                current_num = max_num + 1
                for i in range(len(assets_data)):
                    if i < len(provided_tags):
                        generated_tags.append(provided_tags[i])
                    else:
                        generated_tags.append(f"SG-{current_num}")
                        current_num += 1
                provided_tags = generated_tags

            # Create assets
            created_assets = []
            for i, asset_data in enumerate(assets_data):
                asset = Asset(
                    name=asset_data.get('name', 'MacBook'),
                    model=asset_data.get('model', ''),
                    manufacturer=asset_data.get('manufacturer', 'Apple'),
                    serial_num=asset_data.get('serial_num', ''),
                    asset_tag=provided_tags[i] if i < len(provided_tags) else f"SG-{max_num + i + 1}",
                    category=asset_data.get('category', 'Laptop'),
                    cpu_type=asset_data.get('cpu_type', ''),
                    cpu_cores=asset_data.get('cpu_cores', ''),
                    gpu_cores=asset_data.get('gpu_cores', ''),
                    memory=asset_data.get('memory', ''),
                    harddrive=asset_data.get('harddrive', ''),
                    hardware_type=asset_data.get('hardware_type', 'Laptop'),
                    condition=asset_data.get('condition', 'New'),
                    company_id=company_id,
                    status=AssetStatus.AVAILABLE,
                    created_by_id=user.id
                )
                db_session.add(asset)
                db_session.flush()  # Get the asset ID

                # Link asset to ticket
                ticket.assets.append(asset)

                created_assets.append({
                    'id': asset.id,
                    'serial_num': asset.serial_num,
                    'name': asset.name,
                    'model': asset.model,
                    'asset_tag': asset.asset_tag
                })

            db_session.commit()

            logger.info(f"Mobile API: User {user.username} created {len(created_assets)} assets from OCR text for ticket {ticket_id}")

            return jsonify({
                'success': True,
                'created_assets': created_assets,
                'count': len(created_assets),
                'ticket_id': ticket_id,
                'ticket_display_id': ticket.display_id,
                'message': f'Successfully created {len(created_assets)} asset{"s" if len(created_assets) != 1 else ""} and linked to ticket {ticket.display_id}'
            })

        except Exception as e:
            db_session.rollback()
            raise e
        finally:
            db_session.close()

    except Exception as e:
        logger.error(f"Error creating assets from mobile OCR text: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({'success': False, 'error': str(e)}), 500


@mobile_api_bp.route('/companies', methods=['GET'])
def mobile_get_companies():
    """
    Get list of all companies for mobile app dropdown.

    Response:
        {
            "success": true,
            "companies": [
                {"id": 1, "name": "Company A"},
                {"id": 2, "name": "Company B"}
            ]
        }
    """
    try:
        # Verify auth token
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'success': False, 'error': 'Missing or invalid authorization token'}), 401

        token = auth_header.split(' ')[1]
        user = verify_mobile_token(token)

        if not user:
            return jsonify({'success': False, 'error': 'Invalid or expired token'}), 401

        from models.company import Company

        db_session = db_manager.get_session()
        try:
            companies = db_session.query(Company).order_by(Company.name).all()

            return jsonify({
                'success': True,
                'companies': [
                    {
                        'id': c.id,
                        'name': c.name,
                        'grouped_display_name': getattr(c, 'grouped_display_name', c.name)
                    }
                    for c in companies
                ]
            })
        finally:
            db_session.close()

    except Exception as e:
        logger.error(f"Error fetching companies for mobile: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@mobile_api_bp.route('/next-asset-tag', methods=['GET'])
def mobile_get_next_asset_tag():
    """
    Get the next available asset tag number and optionally pre-generate a list of tags.

    Query Parameters:
        prefix: Tag prefix (default: "SG-")
        count: Number of tags to generate (default: 1, max: 200)

    Response:
        {
            "success": true,
            "next_number": 1207,
            "tags": ["SG-1207", "SG-1208", "SG-1209", ...]
        }
    """
    try:
        # Verify auth token
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'success': False, 'error': 'Missing or invalid authorization token'}), 401

        token = auth_header.split(' ')[1]
        user = verify_mobile_token(token)

        if not user:
            return jsonify({'success': False, 'error': 'Invalid or expired token'}), 401

        prefix = request.args.get('prefix', 'SG-')
        count = min(int(request.args.get('count', 1)), 200)  # Max 200 tags

        import re

        db_session = db_manager.get_session()
        try:
            # Find highest existing tag with this prefix
            # Handle both "SG-" and "SG" prefixes
            clean_prefix = prefix.rstrip('-')

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

            next_number = max_num + 1

            # Generate the requested number of tags
            tags = [f"{clean_prefix}-{next_number + i}" for i in range(count)]

            return jsonify({
                'success': True,
                'next_number': next_number,
                'prefix': f"{clean_prefix}-",
                'tags': tags
            })

        finally:
            db_session.close()

    except Exception as e:
        logger.error(f"Error getting next asset tag for mobile: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@mobile_api_bp.route('/create-assets', methods=['POST'])
def mobile_create_assets_bulk():
    """
    Bulk create assets from mobile app with full control over all fields.

    Request Body:
        {
            "ticket_id": 2040,  // Optional - link assets to ticket
            "company_id": 5,    // Optional - assign company to all assets
            "assets": [
                {
                    "serial_num": "C02XG1YHJK77",
                    "asset_tag": "SG-1207",
                    "name": "13\" MacBook Air",
                    "model": "A3240",
                    "cpu_type": "M4",
                    "cpu_cores": "10",
                    "gpu_cores": "8",
                    "memory": "16GB",
                    "harddrive": "256GB",
                    "hardware_type": "13\" MacBook Air M4 10-Core 256GB",
                    "manufacturer": "Apple",
                    "category": "APPLE",
                    "condition": "New",
                    "country": "Singapore"
                },
                ...
            ]
        }

    Response:
        {
            "success": true,
            "created_count": 56,
            "error_count": 0,
            "assets": [...],
            "errors": []
        }
    """
    try:
        # Verify auth token
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'success': False, 'error': 'Missing or invalid authorization token'}), 401

        token = auth_header.split(' ')[1]
        user = verify_mobile_token(token)

        if not user:
            return jsonify({'success': False, 'error': 'Invalid or expired token'}), 401

        data = request.get_json()
        if not data or 'assets' not in data:
            return jsonify({'success': False, 'error': 'Missing assets data'}), 400

        assets_data = data.get('assets', [])
        ticket_id = data.get('ticket_id')
        company_id = data.get('company_id')

        if not assets_data:
            return jsonify({'success': False, 'error': 'No assets provided'}), 400

        db_session = db_manager.get_session()
        try:
            # Get ticket if provided
            ticket = None
            if ticket_id:
                ticket = db_session.query(Ticket).filter(Ticket.id == ticket_id).first()
                if not ticket:
                    return jsonify({'success': False, 'error': f'Ticket {ticket_id} not found'}), 404

            created_assets = []
            errors = []

            for asset_data in assets_data:
                try:
                    serial_num = asset_data.get('serial_num', '').strip()
                    asset_tag = asset_data.get('asset_tag', '').strip()

                    if not serial_num:
                        errors.append({'error': 'Missing serial number', 'data': asset_data})
                        continue

                    # Check for duplicate serial
                    existing_serial = db_session.query(Asset).filter(Asset.serial_num == serial_num).first()
                    if existing_serial:
                        errors.append({
                            'error': f'Serial {serial_num} already exists (Asset #{existing_serial.id})',
                            'serial_num': serial_num
                        })
                        continue

                    # Check for duplicate asset tag
                    if asset_tag:
                        existing_tag = db_session.query(Asset).filter(Asset.asset_tag == asset_tag).first()
                        if existing_tag:
                            errors.append({
                                'error': f'Asset tag {asset_tag} already exists (Asset #{existing_tag.id})',
                                'asset_tag': asset_tag
                            })
                            continue

                    # Create the asset
                    asset = Asset(
                        serial_num=serial_num,
                        asset_tag=asset_tag,
                        name=asset_data.get('name', ''),
                        model=asset_data.get('model', ''),
                        manufacturer=asset_data.get('manufacturer', 'Apple'),
                        category=asset_data.get('category', 'APPLE'),
                        asset_type=asset_data.get('category', 'APPLE'),
                        cpu_type=asset_data.get('cpu_type', ''),
                        cpu_cores=asset_data.get('cpu_cores', ''),
                        gpu_cores=asset_data.get('gpu_cores', ''),
                        memory=asset_data.get('memory', ''),
                        harddrive=asset_data.get('harddrive', ''),
                        hardware_type=asset_data.get('hardware_type', ''),
                        condition=asset_data.get('condition', 'New'),
                        country=asset_data.get('country', 'Singapore'),
                        company_id=company_id,
                        status=AssetStatus.IN_STOCK,
                        receiving_date=datetime.utcnow(),
                        notes=f"Created via mobile app by {user.username}"
                    )

                    db_session.add(asset)
                    db_session.flush()  # Get the asset ID

                    # Link to ticket if provided
                    if ticket:
                        ticket.assets.append(asset)

                    created_assets.append({
                        'id': asset.id,
                        'serial_num': asset.serial_num,
                        'asset_tag': asset.asset_tag,
                        'name': asset.name,
                        'model': asset.model
                    })

                except Exception as e:
                    errors.append({
                        'error': str(e),
                        'serial_num': asset_data.get('serial_num', 'unknown')
                    })

            db_session.commit()

            logger.info(f"Mobile API: User {user.username} created {len(created_assets)} assets" +
                       (f" for ticket {ticket_id}" if ticket_id else ""))

            return jsonify({
                'success': True,
                'created_count': len(created_assets),
                'error_count': len(errors),
                'assets': created_assets,
                'errors': errors,
                'ticket_id': ticket_id,
                'message': f'Successfully created {len(created_assets)} asset(s)' +
                          (f' and linked to ticket #{ticket_id}' if ticket_id else '')
            })

        except Exception as e:
            db_session.rollback()
            raise e
        finally:
            db_session.close()

    except Exception as e:
        logger.error(f"Error creating assets from mobile app: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({'success': False, 'error': str(e)}), 500