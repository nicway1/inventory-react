"""
JSON API Routes for iOS App Integration

This module provides RESTful JSON API endpoints that match the specifications
in the iOS app development guide. These endpoints use API key authentication
and return JSON responses suitable for mobile app consumption.
"""

from flask import Blueprint, request, jsonify
from functools import wraps
from datetime import datetime, timedelta
import jwt
import logging

from models.user import User, UserType
from models.ticket import Ticket, TicketStatus, TicketPriority, TicketCategory
from models.asset import Asset, AssetStatus
from models.queue import Queue
from utils.db_manager import DatabaseManager
from flask import current_app

# Set up logging
logger = logging.getLogger(__name__)

# Create JSON API blueprint - using different routes to avoid conflicts with existing api_simple.py
json_api_bp = Blueprint('json_api', __name__, url_prefix='/mobile')
db_manager = DatabaseManager()

# API Key for authentication
API_KEY = 'xAQhm3__ZH6MvRIPMIBSDRAsIa1w2Slh5uaCtc4NurM'

# JWT Secret Key
JWT_SECRET = 'your-secret-key-here'  # In production, use app.config['SECRET_KEY']

def require_api_key(f):
    """API Key validation decorator"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        if api_key != API_KEY:
            return jsonify({'error': 'Invalid API key'}), 401
        return f(*args, **kwargs)
    return decorated_function

def generate_access_token(user_id):
    """Generate JWT access token"""
    payload = {
        'user_id': user_id,
        'exp': datetime.utcnow() + timedelta(hours=1),  # 1 hour expiry
        'iat': datetime.utcnow()
    }
    try:
        secret_key = current_app.config.get('SECRET_KEY', JWT_SECRET)
        return jwt.encode(payload, secret_key, algorithm='HS256')
    except Exception as e:
        logger.error(f"Error generating access token: {str(e)}")
        return jwt.encode(payload, JWT_SECRET, algorithm='HS256')

def generate_refresh_token(user_id):
    """Generate JWT refresh token"""
    payload = {
        'user_id': user_id,
        'exp': datetime.utcnow() + timedelta(days=30),  # 30 day expiry
        'iat': datetime.utcnow()
    }
    try:
        secret_key = current_app.config.get('SECRET_KEY', JWT_SECRET)
        return jwt.encode(payload, secret_key, algorithm='HS256')
    except Exception as e:
        logger.error(f"Error generating refresh token: {str(e)}")
        return jwt.encode(payload, JWT_SECRET, algorithm='HS256')

def verify_jwt_token(token):
    """Verify JWT token and return user_id"""
    try:
        secret_key = current_app.config.get('SECRET_KEY', JWT_SECRET)
        payload = jwt.decode(token, secret_key, algorithms=['HS256'])
        return payload['user_id']
    except jwt.ExpiredSignatureError:
        logger.warning("JWT token expired")
        return None
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid JWT token: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Error verifying JWT token: {str(e)}")
        try:
            # Fallback to default secret
            payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
            return payload['user_id']
        except:
            return None

def require_jwt_auth(f):
    """JWT authentication decorator"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check API key first
        api_key = request.headers.get('X-API-Key')
        if api_key != API_KEY:
            return jsonify({'error': 'Invalid API key'}), 401
            
        # Check JWT token
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Missing or invalid token'}), 401
        
        token = auth_header.split(' ')[1]
        user_id = verify_jwt_token(token)
        
        if not user_id:
            return jsonify({'error': 'Invalid or expired token'}), 401
        
        # Get user from database
        db_session = db_manager.get_session()
        try:
            user = db_session.query(User).filter(User.id == user_id).first()
            if not user:
                return jsonify({'error': 'User not found'}), 401
            
            # Make user available in request context
            request.current_user = user
            return f(*args, **kwargs)
        finally:
            db_session.close()
    
    decorated_function.__name__ = f.__name__
    return decorated_function

# MARK: - Authentication Endpoints

@json_api_bp.route('/auth/login', methods=['POST'])
@require_api_key
def mobile_login():
    """
    Mobile login endpoint that returns JSON
    
    POST /auth/login
    Headers: X-API-Key: xAQhm3__ZH6MvRIPMIBSDRAsIa1w2Slh5uaCtc4NurM
    Body: {"username": "user@example.com", "password": "password123"}
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'JSON body required'}), 400
            
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            return jsonify({'error': 'Username and password required'}), 400
        
        # Authenticate user
        db_session = db_manager.get_session()
        try:
            user = db_session.query(User).filter(User.username == username).first()
            
            if not user or not user.check_password(password):
                return jsonify({'error': 'Invalid credentials'}), 401
            
            # Update last login
            user.last_login = datetime.utcnow()
            db_session.commit()
            
            # Generate tokens
            access_token = generate_access_token(user.id)
            refresh_token = generate_refresh_token(user.id)
            
            # Return user data and tokens
            return jsonify({
                'access_token': access_token,
                'refresh_token': refresh_token,
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'role': user.user_type.value.lower() if user.user_type else 'user',
                    'first_name': getattr(user, 'first_name', None),
                    'last_name': getattr(user, 'last_name', None),
                    'is_active': True,  # Assuming active if they can log in
                    'created_at': user.created_at.isoformat() + 'Z' if user.created_at else None,
                    'last_login': user.last_login.isoformat() + 'Z' if user.last_login else None
                }
            }), 200
            
        finally:
            db_session.close()
            
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        return jsonify({'error': 'Login failed'}), 500

@json_api_bp.route('/auth/me', methods=['GET'])
@require_jwt_auth
def get_current_user():
    """
    Get current user information
    
    GET /auth/me
    Headers: 
        X-API-Key: xAQhm3__ZH6MvRIPMIBSDRAsIa1w2Slh5uaCtc4NurM
        Authorization: Bearer <token>
    """
    try:
        user = request.current_user
        
        return jsonify({
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'role': user.user_type.value.lower() if user.user_type else 'user',
            'first_name': getattr(user, 'first_name', None),
            'last_name': getattr(user, 'last_name', None),
            'is_active': True,
            'created_at': user.created_at.isoformat() + 'Z' if user.created_at else None,
            'last_login': user.last_login.isoformat() + 'Z' if user.last_login else None
        }), 200
        
    except Exception as e:
        logger.error(f"Get current user error: {str(e)}")
        return jsonify({'error': 'Failed to get user information'}), 500

# MARK: - Tickets Endpoint

@json_api_bp.route('/tickets', methods=['GET'])
@require_jwt_auth
def get_tickets():
    """
    Get tickets with filtering and pagination
    
    GET /tickets?page=1&limit=20&status=open
    """
    try:
        user = request.current_user
        
        # Get query parameters
        page = request.args.get('page', 1, type=int)
        limit = request.args.get('limit', 20, type=int)
        status_filter = request.args.get('status')
        
        # Limit pagination
        limit = min(limit, 100)  # Max 100 per page
        page = max(page, 1)  # Min page 1
        
        db_session = db_manager.get_session()
        try:
            # Build query based on user permissions
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
                # Map common status values
                status_map = {
                    'open': TicketStatus.OPEN,
                    'in_progress': TicketStatus.IN_PROGRESS,
                    'resolved': TicketStatus.RESOLVED,
                    'closed': TicketStatus.RESOLVED_DELIVERED
                }
                
                if status_filter.lower() in status_map:
                    query = query.filter(Ticket.status == status_map[status_filter.lower()])
            
            # Get total count
            total = query.count()
            
            # Apply pagination
            offset = (page - 1) * limit
            tickets = query.order_by(Ticket.created_at.desc()).offset(offset).limit(limit).all()
            
            # Format tickets
            tickets_data = []
            for ticket in tickets:
                ticket_data = {
                    'id': ticket.id,
                    'title': ticket.subject or 'Untitled',
                    'description': ticket.description or '',
                    'status': ticket.status.value.lower() if ticket.status else 'open',
                    'priority': ticket.priority.value.lower() if ticket.priority else 'normal',
                    'category': ticket.category.value.lower() if ticket.category else 'general',
                    'assigned_to': ticket.assigned_to_id,
                    'assigned_to_name': f"{ticket.assigned_to.first_name or ''} {ticket.assigned_to.last_name or ''}".strip() if ticket.assigned_to else None,
                    'created_by': ticket.requester_id,
                    'created_by_name': f"{ticket.requester.first_name or ''} {ticket.requester.last_name or ''}".strip() if ticket.requester else None,
                    'created_at': ticket.created_at.isoformat() + 'Z' if ticket.created_at else None,
                    'updated_at': ticket.updated_at.isoformat() + 'Z' if ticket.updated_at else None,
                    'due_date': ticket.due_date.isoformat() + 'Z' if getattr(ticket, 'due_date', None) else None,
                    'resolved_at': ticket.resolved_at.isoformat() + 'Z' if getattr(ticket, 'resolved_at', None) else None,
                    'tags': getattr(ticket, 'tags', []) or []
                }
                tickets_data.append(ticket_data)
            
            total_pages = (total + limit - 1) // limit  # Ceiling division
            
            return jsonify({
                'tickets': tickets_data,
                'total': total,
                'page': page,
                'per_page': limit,
                'total_pages': total_pages
            }), 200
            
        finally:
            db_session.close()
            
    except Exception as e:
        logger.error(f"Get tickets error: {str(e)}")
        return jsonify({'error': 'Failed to get tickets'}), 500

# MARK: - Inventory Endpoint

@json_api_bp.route('/inventory', methods=['GET'])
@require_jwt_auth
def get_inventory():
    """
    Get inventory assets with filtering and pagination
    
    GET /inventory?page=1&limit=20&category=computers&search=laptop
    """
    try:
        user = request.current_user
        
        # Check permissions
        if not user.permissions or not user.permissions.can_view_assets:
            return jsonify({'error': 'No permission to view inventory'}), 403
        
        # Get query parameters
        page = request.args.get('page', 1, type=int)
        limit = request.args.get('limit', 20, type=int)
        search = request.args.get('search')
        category = request.args.get('category')
        
        # Limit pagination
        limit = min(limit, 100)
        page = max(page, 1)
        
        db_session = db_manager.get_session()
        try:
            query = db_session.query(Asset)
            
            # Apply country restrictions for COUNTRY_ADMIN
            if user.user_type == UserType.COUNTRY_ADMIN and user.assigned_countries:
                query = query.filter(Asset.country.in_(user.assigned_countries))
            
            # Apply search filter
            if search:
                search_term = f"%{search}%"
                query = query.filter(
                    (Asset.name.ilike(search_term)) |
                    (Asset.asset_tag.ilike(search_term)) |
                    (Asset.serial_num.ilike(search_term)) |
                    (Asset.model.ilike(search_term))
                )
            
            # Apply category filter
            if category:
                query = query.filter(Asset.asset_type.ilike(f"%{category}%"))
            
            # Get total count
            total = query.count()
            
            # Apply pagination
            offset = (page - 1) * limit
            assets = query.order_by(Asset.created_at.desc()).offset(offset).limit(limit).all()
            
            # Format assets
            assets_data = []
            for asset in assets:
                asset_data = {
                    'id': asset.id,
                    'name': asset.name or '',
                    'description': getattr(asset, 'description', '') or '',
                    'serial_number': asset.serial_num or '',
                    'model': asset.model or '',
                    'manufacturer': asset.manufacturer or '',
                    'category': asset.asset_type or 'general',
                    'status': asset.status.value.lower() if asset.status else 'available',
                    'location': asset.location or '',
                    'assigned_to': asset.assigned_to.id if asset.assigned_to else None,
                    'assigned_to_name': f"{asset.assigned_to.first_name or ''} {asset.assigned_to.last_name or ''}".strip() if asset.assigned_to else None,
                    'purchase_date': asset.purchase_date.isoformat() if getattr(asset, 'purchase_date', None) else None,
                    'purchase_price': float(asset.purchase_cost) if getattr(asset, 'purchase_cost', None) else None,
                    'warranty_expiry': asset.warranty_expires.isoformat() if getattr(asset, 'warranty_expires', None) else None,
                    'created_at': asset.created_at.isoformat() + 'Z' if asset.created_at else None,
                    'updated_at': asset.updated_at.isoformat() + 'Z' if asset.updated_at else None,
                    'tags': getattr(asset, 'tags', []) or []
                }
                assets_data.append(asset_data)
            
            total_pages = (total + limit - 1) // limit
            
            return jsonify({
                'assets': assets_data,
                'total': total,
                'page': page,
                'per_page': limit,
                'total_pages': total_pages
            }), 200
            
        finally:
            db_session.close()
            
    except Exception as e:
        logger.error(f"Get inventory error: {str(e)}")
        return jsonify({'error': 'Failed to get inventory'}), 500

# MARK: - Dashboard Endpoint

@json_api_bp.route('/dashboard', methods=['GET'])
@require_jwt_auth
def get_dashboard():
    """
    Get dashboard statistics
    
    GET /dashboard
    """
    try:
        user = request.current_user
        
        db_session = db_manager.get_session()
        try:
            # Ticket statistics
            if user.user_type == UserType.SUPER_ADMIN:
                total_tickets = db_session.query(Ticket).count()
                open_tickets = db_session.query(Ticket).filter(
                    Ticket.status == TicketStatus.OPEN
                ).count()
                in_progress_tickets = db_session.query(Ticket).filter(
                    Ticket.status == TicketStatus.IN_PROGRESS
                ).count()
                resolved_tickets = db_session.query(Ticket).filter(
                    Ticket.status.in_([TicketStatus.RESOLVED, TicketStatus.RESOLVED_DELIVERED])
                ).count()
            else:
                # User's tickets only
                user_tickets_query = db_session.query(Ticket).filter(
                    (Ticket.requester_id == user.id) | (Ticket.assigned_to_id == user.id)
                )
                total_tickets = user_tickets_query.count()
                open_tickets = user_tickets_query.filter(Ticket.status == TicketStatus.OPEN).count()
                in_progress_tickets = user_tickets_query.filter(Ticket.status == TicketStatus.IN_PROGRESS).count()
                resolved_tickets = user_tickets_query.filter(
                    Ticket.status.in_([TicketStatus.RESOLVED, TicketStatus.RESOLVED_DELIVERED])
                ).count()
            
            # Asset statistics (if user has permission)
            total_assets = 0
            available_assets = 0
            assigned_assets = 0
            maintenance_assets = 0
            
            if user.permissions and user.permissions.can_view_assets:
                asset_query = db_session.query(Asset)
                
                # Apply country restrictions
                if user.user_type == UserType.COUNTRY_ADMIN and user.assigned_countries:
                    asset_query = asset_query.filter(Asset.country.in_(user.assigned_countries))
                
                total_assets = asset_query.count()
                available_assets = asset_query.filter(Asset.status == AssetStatus.READY_TO_DEPLOY).count()
                assigned_assets = asset_query.filter(Asset.status == AssetStatus.DEPLOYED).count()
                maintenance_assets = asset_query.filter(Asset.status == AssetStatus.BROKEN).count()
            
            # Recent activity - simplified for now
            recent_activity = [
                {
                    'id': 1,
                    'type': 'ticket_created',
                    'title': 'New support request created',
                    'user': 'System',
                    'timestamp': datetime.utcnow().isoformat() + 'Z'
                }
            ]
            
            return jsonify({
                'total_tickets': total_tickets,
                'open_tickets': open_tickets,
                'in_progress_tickets': in_progress_tickets,
                'resolved_tickets': resolved_tickets,
                'total_assets': total_assets,
                'available_assets': available_assets,
                'assigned_assets': assigned_assets,
                'maintenance_assets': maintenance_assets,
                'recent_activity': recent_activity
            }), 200
            
        finally:
            db_session.close()
            
    except Exception as e:
        logger.error(f"Get dashboard error: {str(e)}")
        return jsonify({'error': 'Failed to get dashboard data'}), 500