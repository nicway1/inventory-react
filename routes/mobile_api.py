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

            if user.user_type == UserType.SUPER_ADMIN:
                ticket = base_query.filter(Ticket.id == ticket_id).first()
            else:
                # Users can only see tickets they created or are assigned to
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
                    'status': asset.status.value if asset.status else None
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

            # Create new asset
            new_asset = Asset(
                asset_tag=data['asset_tag'],
                serial_num=data['serial_num'],
                name=data.get('name'),
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
                created_at=datetime.utcnow()
            )

            db_session.add(new_asset)
            db_session.commit()

            # Return created asset
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
            if user.user_type == UserType.SUPER_ADMIN:
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
            if user.user_type == UserType.SUPER_ADMIN:
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

            if user.user_type == UserType.SUPER_ADMIN:
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
                    'status': asset.status.value if asset.status else 'UNKNOWN'
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
            if user.user_type == UserType.SUPER_ADMIN:
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

            # Check if asset is already assigned to another ticket
            if asset.ticket_id and asset.ticket_id != ticket_id:
                return jsonify({
                    'success': False,
                    'error': 'Asset is already assigned to another ticket'
                }), 400

            # Check if asset is already in this ticket
            if asset in ticket.assets:
                return jsonify({
                    'success': False,
                    'error': 'Asset is already assigned to this ticket'
                }), 400

            # Add asset to ticket
            ticket.assets.append(asset)
            asset.ticket_id = ticket_id
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
                    'status': asset.status.value if asset.status else 'UNKNOWN'
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
            if user.user_type == UserType.SUPER_ADMIN:
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
            if user.user_type == UserType.SUPER_ADMIN:
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
            if user.user_type == UserType.SUPER_ADMIN:
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