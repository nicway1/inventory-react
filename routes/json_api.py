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


# MARK: - Development Console Endpoints

@json_api_bp.route('/dev/dashboard', methods=['GET'])
@require_jwt_auth
def get_dev_dashboard():
    """
    Get development dashboard data

    GET /mobile/dev/dashboard
    Returns: stats, recent features, bugs, releases, schedules
    """
    from models.feature_request import FeatureRequest, FeatureStatus
    from models.bug_report import BugReport, BugStatus, BugSeverity
    from models.release import Release, ReleaseStatus
    from models.developer_schedule import DeveloperSchedule
    from sqlalchemy.orm import joinedload
    from sqlalchemy import desc, asc
    from datetime import date, timedelta

    try:
        user = request.current_user

        # Check permission
        if not user.permissions or not user.permissions.can_access_development:
            return jsonify({'error': 'Permission denied'}), 403

        db_session = db_manager.get_session()
        try:
            # Get summary statistics
            stats = {
                'features': {
                    'total': db_session.query(FeatureRequest).count(),
                    'active': db_session.query(FeatureRequest).filter(
                        FeatureRequest.status.in_([
                            FeatureStatus.IN_PLANNING,
                            FeatureStatus.IN_DEVELOPMENT,
                            FeatureStatus.IN_TESTING
                        ])
                    ).count(),
                    'completed': db_session.query(FeatureRequest).filter(
                        FeatureRequest.status == FeatureStatus.COMPLETED
                    ).count(),
                    'pending_approval': db_session.query(FeatureRequest).filter(
                        FeatureRequest.status == FeatureStatus.PENDING_APPROVAL
                    ).count()
                },
                'bugs': {
                    'total': db_session.query(BugReport).count(),
                    'open': db_session.query(BugReport).filter(
                        BugReport.status.in_([
                            BugStatus.OPEN,
                            BugStatus.IN_PROGRESS,
                            BugStatus.TESTING,
                            BugStatus.REOPENED
                        ])
                    ).count(),
                    'critical': db_session.query(BugReport).filter(
                        BugReport.severity == BugSeverity.CRITICAL,
                        BugReport.status.in_([BugStatus.OPEN, BugStatus.IN_PROGRESS])
                    ).count()
                },
                'releases': {
                    'total': db_session.query(Release).count(),
                    'active': db_session.query(Release).filter(
                        Release.status.in_([
                            ReleaseStatus.PLANNING,
                            ReleaseStatus.IN_DEVELOPMENT,
                            ReleaseStatus.TESTING
                        ])
                    ).count(),
                    'released': db_session.query(Release).filter(
                        Release.status == ReleaseStatus.RELEASED
                    ).count()
                }
            }

            # Get recent active features
            recent_features = db_session.query(FeatureRequest)\
                .options(joinedload(FeatureRequest.requester))\
                .options(joinedload(FeatureRequest.assignee))\
                .filter(FeatureRequest.status.in_([
                    FeatureStatus.IN_PLANNING,
                    FeatureStatus.IN_DEVELOPMENT,
                    FeatureStatus.IN_TESTING,
                    FeatureStatus.PENDING_APPROVAL
                ]))\
                .order_by(desc(FeatureRequest.updated_at))\
                .limit(10).all()

            features_data = [{
                'id': f.id,
                'display_id': f.display_id,
                'title': f.title,
                'status': f.status.value if f.status else None,
                'priority': f.priority.value if f.priority else None,
                'requester': f.requester.username if f.requester else None,
                'assignee': f.assignee.username if f.assignee else None,
                'updated_at': f.updated_at.isoformat() + 'Z' if f.updated_at else None
            } for f in recent_features]

            # Get recent open bugs
            recent_bugs = db_session.query(BugReport)\
                .options(joinedload(BugReport.reporter))\
                .options(joinedload(BugReport.assignee))\
                .filter(BugReport.status.in_([BugStatus.OPEN, BugStatus.IN_PROGRESS, BugStatus.REOPENED]))\
                .order_by(desc(BugReport.updated_at))\
                .limit(10).all()

            bugs_data = [{
                'id': b.id,
                'display_id': b.display_id,
                'title': b.title,
                'status': b.status.value if b.status else None,
                'severity': b.severity.value if b.severity else None,
                'priority': b.priority.value if b.priority else None,
                'reporter': b.reporter.username if b.reporter else None,
                'assignee': b.assignee.username if b.assignee else None,
                'updated_at': b.updated_at.isoformat() + 'Z' if b.updated_at else None
            } for b in recent_bugs]

            # Get active releases
            active_releases = db_session.query(Release)\
                .filter(Release.status.in_([
                    ReleaseStatus.PLANNING,
                    ReleaseStatus.IN_DEVELOPMENT,
                    ReleaseStatus.TESTING,
                    ReleaseStatus.READY
                ]))\
                .order_by(asc(Release.planned_date))\
                .limit(5).all()

            releases_data = [{
                'id': r.id,
                'version': r.version,
                'name': r.name,
                'status': r.status.value if r.status else None,
                'release_type': r.release_type.value if r.release_type else None,
                'planned_date': r.planned_date.isoformat() if r.planned_date else None,
                'release_date': r.release_date.isoformat() if r.release_date else None
            } for r in active_releases]

            # Get this week's schedule
            today = date.today()
            monday = today - timedelta(days=today.weekday())
            friday = monday + timedelta(days=4)

            week_schedules = db_session.query(DeveloperSchedule)\
                .options(joinedload(DeveloperSchedule.user))\
                .filter(DeveloperSchedule.work_date >= monday)\
                .filter(DeveloperSchedule.work_date <= friday)\
                .order_by(DeveloperSchedule.work_date)\
                .all()

            schedule_data = [{
                'id': s.id,
                'user_id': s.user_id,
                'username': s.user.username if s.user else None,
                'work_date': s.work_date.isoformat() if s.work_date else None,
                'is_working': s.is_working,
                'work_location': s.work_location,
                'note': s.note
            } for s in week_schedules]

            return jsonify({
                'stats': stats,
                'recent_features': features_data,
                'recent_bugs': bugs_data,
                'active_releases': releases_data,
                'week_schedule': schedule_data
            }), 200

        finally:
            db_session.close()

    except Exception as e:
        logger.error(f"Get dev dashboard error: {str(e)}")
        return jsonify({'error': 'Failed to get development dashboard'}), 500


@json_api_bp.route('/dev/features', methods=['GET'])
@require_jwt_auth
def get_features():
    """
    Get all feature requests with optional filtering

    GET /mobile/dev/features
    Query params: status, priority, page, per_page
    """
    from models.feature_request import FeatureRequest, FeatureStatus, FeaturePriority
    from sqlalchemy.orm import joinedload
    from sqlalchemy import desc

    try:
        user = request.current_user

        if not user.permissions or not user.permissions.can_view_features:
            return jsonify({'error': 'Permission denied'}), 403

        # Get query params
        status_filter = request.args.get('status')
        priority_filter = request.args.get('priority')
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)

        db_session = db_manager.get_session()
        try:
            query = db_session.query(FeatureRequest)\
                .options(joinedload(FeatureRequest.requester))\
                .options(joinedload(FeatureRequest.assignee))\
                .options(joinedload(FeatureRequest.approver))

            # Apply filters
            if status_filter:
                try:
                    status_enum = FeatureStatus(status_filter)
                    query = query.filter(FeatureRequest.status == status_enum)
                except ValueError:
                    pass

            if priority_filter:
                try:
                    priority_enum = FeaturePriority(priority_filter)
                    query = query.filter(FeatureRequest.priority == priority_enum)
                except ValueError:
                    pass

            # Get total count
            total = query.count()

            # Apply pagination
            features = query.order_by(desc(FeatureRequest.updated_at))\
                .offset((page - 1) * per_page)\
                .limit(per_page)\
                .all()

            features_data = [{
                'id': f.id,
                'display_id': f.display_id,
                'title': f.title,
                'description': f.description,
                'status': f.status.value if f.status else None,
                'priority': f.priority.value if f.priority else None,
                'component': f.component,
                'requester': {
                    'id': f.requester.id,
                    'username': f.requester.username
                } if f.requester else None,
                'assignee': {
                    'id': f.assignee.id,
                    'username': f.assignee.username
                } if f.assignee else None,
                'approver': {
                    'id': f.approver.id,
                    'username': f.approver.username
                } if f.approver else None,
                'estimated_effort': f.estimated_effort,
                'business_value': f.business_value,
                'created_at': f.created_at.isoformat() + 'Z' if f.created_at else None,
                'updated_at': f.updated_at.isoformat() + 'Z' if f.updated_at else None
            } for f in features]

            return jsonify({
                'features': features_data,
                'total': total,
                'page': page,
                'per_page': per_page,
                'total_pages': (total + per_page - 1) // per_page
            }), 200

        finally:
            db_session.close()

    except Exception as e:
        logger.error(f"Get features error: {str(e)}")
        return jsonify({'error': 'Failed to get features'}), 500


@json_api_bp.route('/dev/features/<int:feature_id>', methods=['GET'])
@require_jwt_auth
def get_feature_detail(feature_id):
    """
    Get single feature request detail

    GET /mobile/dev/features/<id>
    """
    from models.feature_request import FeatureRequest, FeatureComment
    from sqlalchemy.orm import joinedload

    try:
        user = request.current_user

        if not user.permissions or not user.permissions.can_view_features:
            return jsonify({'error': 'Permission denied'}), 403

        db_session = db_manager.get_session()
        try:
            feature = db_session.query(FeatureRequest)\
                .options(joinedload(FeatureRequest.requester))\
                .options(joinedload(FeatureRequest.assignee))\
                .options(joinedload(FeatureRequest.approver))\
                .options(joinedload(FeatureRequest.comments).joinedload(FeatureComment.user))\
                .filter(FeatureRequest.id == feature_id)\
                .first()

            if not feature:
                return jsonify({'error': 'Feature not found'}), 404

            comments_data = [{
                'id': c.id,
                'content': c.content,
                'user': {
                    'id': c.user.id,
                    'username': c.user.username
                } if c.user else None,
                'created_at': c.created_at.isoformat() + 'Z' if c.created_at else None
            } for c in (feature.comments or [])]

            return jsonify({
                'id': feature.id,
                'display_id': feature.display_id,
                'title': feature.title,
                'description': feature.description,
                'status': feature.status.value if feature.status else None,
                'priority': feature.priority.value if feature.priority else None,
                'component': feature.component,
                'requester': {
                    'id': feature.requester.id,
                    'username': feature.requester.username,
                    'email': feature.requester.email
                } if feature.requester else None,
                'assignee': {
                    'id': feature.assignee.id,
                    'username': feature.assignee.username
                } if feature.assignee else None,
                'approver': {
                    'id': feature.approver.id,
                    'username': feature.approver.username
                } if feature.approver else None,
                'estimated_effort': feature.estimated_effort,
                'business_value': feature.business_value,
                'acceptance_criteria': feature.acceptance_criteria,
                'technical_notes': feature.technical_notes,
                'approval_requested_at': feature.approval_requested_at.isoformat() + 'Z' if feature.approval_requested_at else None,
                'approved_at': feature.approved_at.isoformat() + 'Z' if feature.approved_at else None,
                'completed_at': feature.completed_at.isoformat() + 'Z' if feature.completed_at else None,
                'created_at': feature.created_at.isoformat() + 'Z' if feature.created_at else None,
                'updated_at': feature.updated_at.isoformat() + 'Z' if feature.updated_at else None,
                'comments': comments_data
            }), 200

        finally:
            db_session.close()

    except Exception as e:
        logger.error(f"Get feature detail error: {str(e)}")
        return jsonify({'error': 'Failed to get feature'}), 500


@json_api_bp.route('/dev/bugs', methods=['GET'])
@require_jwt_auth
def get_bugs():
    """
    Get all bug reports with optional filtering

    GET /mobile/dev/bugs
    Query params: status, severity, priority, page, per_page
    """
    from models.bug_report import BugReport, BugStatus, BugSeverity, BugPriority
    from sqlalchemy.orm import joinedload
    from sqlalchemy import desc

    try:
        user = request.current_user

        if not user.permissions or not user.permissions.can_view_bugs:
            return jsonify({'error': 'Permission denied'}), 403

        # Get query params
        status_filter = request.args.get('status')
        severity_filter = request.args.get('severity')
        priority_filter = request.args.get('priority')
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)

        db_session = db_manager.get_session()
        try:
            query = db_session.query(BugReport)\
                .options(joinedload(BugReport.reporter))\
                .options(joinedload(BugReport.assignee))

            # Apply filters
            if status_filter:
                try:
                    status_enum = BugStatus(status_filter)
                    query = query.filter(BugReport.status == status_enum)
                except ValueError:
                    pass

            if severity_filter:
                try:
                    severity_enum = BugSeverity(severity_filter)
                    query = query.filter(BugReport.severity == severity_enum)
                except ValueError:
                    pass

            if priority_filter:
                try:
                    priority_enum = BugPriority(priority_filter)
                    query = query.filter(BugReport.priority == priority_enum)
                except ValueError:
                    pass

            # Get total count
            total = query.count()

            # Apply pagination
            bugs = query.order_by(desc(BugReport.updated_at))\
                .offset((page - 1) * per_page)\
                .limit(per_page)\
                .all()

            bugs_data = [{
                'id': b.id,
                'display_id': b.display_id,
                'title': b.title,
                'description': b.description,
                'status': b.status.value if b.status else None,
                'severity': b.severity.value if b.severity else None,
                'priority': b.priority.value if b.priority else None,
                'component': b.component,
                'steps_to_reproduce': b.steps_to_reproduce,
                'reporter': {
                    'id': b.reporter.id,
                    'username': b.reporter.username
                } if b.reporter else None,
                'assignee': {
                    'id': b.assignee.id,
                    'username': b.assignee.username
                } if b.assignee else None,
                'created_at': b.created_at.isoformat() + 'Z' if b.created_at else None,
                'updated_at': b.updated_at.isoformat() + 'Z' if b.updated_at else None
            } for b in bugs]

            return jsonify({
                'bugs': bugs_data,
                'total': total,
                'page': page,
                'per_page': per_page,
                'total_pages': (total + per_page - 1) // per_page
            }), 200

        finally:
            db_session.close()

    except Exception as e:
        logger.error(f"Get bugs error: {str(e)}")
        return jsonify({'error': 'Failed to get bugs'}), 500


@json_api_bp.route('/dev/bugs/<int:bug_id>', methods=['GET'])
@require_jwt_auth
def get_bug_detail(bug_id):
    """
    Get single bug report detail

    GET /mobile/dev/bugs/<id>
    """
    from models.bug_report import BugReport, BugComment
    from sqlalchemy.orm import joinedload

    try:
        user = request.current_user

        if not user.permissions or not user.permissions.can_view_bugs:
            return jsonify({'error': 'Permission denied'}), 403

        db_session = db_manager.get_session()
        try:
            bug = db_session.query(BugReport)\
                .options(joinedload(BugReport.reporter))\
                .options(joinedload(BugReport.assignee))\
                .options(joinedload(BugReport.comments).joinedload(BugComment.user))\
                .filter(BugReport.id == bug_id)\
                .first()

            if not bug:
                return jsonify({'error': 'Bug not found'}), 404

            comments_data = [{
                'id': c.id,
                'content': c.content,
                'user': {
                    'id': c.user.id,
                    'username': c.user.username
                } if c.user else None,
                'created_at': c.created_at.isoformat() + 'Z' if c.created_at else None
            } for c in (bug.comments or [])]

            return jsonify({
                'id': bug.id,
                'display_id': bug.display_id,
                'title': bug.title,
                'description': bug.description,
                'status': bug.status.value if bug.status else None,
                'severity': bug.severity.value if bug.severity else None,
                'priority': bug.priority.value if bug.priority else None,
                'component': bug.component,
                'steps_to_reproduce': bug.steps_to_reproduce,
                'expected_behavior': bug.expected_behavior,
                'actual_behavior': bug.actual_behavior,
                'environment': bug.environment,
                'reporter': {
                    'id': bug.reporter.id,
                    'username': bug.reporter.username,
                    'email': bug.reporter.email
                } if bug.reporter else None,
                'assignee': {
                    'id': bug.assignee.id,
                    'username': bug.assignee.username
                } if bug.assignee else None,
                'resolution': bug.resolution,
                'resolved_at': bug.resolved_at.isoformat() + 'Z' if bug.resolved_at else None,
                'created_at': bug.created_at.isoformat() + 'Z' if bug.created_at else None,
                'updated_at': bug.updated_at.isoformat() + 'Z' if bug.updated_at else None,
                'comments': comments_data
            }), 200

        finally:
            db_session.close()

    except Exception as e:
        logger.error(f"Get bug detail error: {str(e)}")
        return jsonify({'error': 'Failed to get bug'}), 500


@json_api_bp.route('/dev/releases', methods=['GET'])
@require_jwt_auth
def get_releases():
    """
    Get all releases with optional filtering

    GET /mobile/dev/releases
    Query params: status, page, per_page
    """
    from models.release import Release, ReleaseStatus
    from sqlalchemy.orm import joinedload
    from sqlalchemy import desc

    try:
        user = request.current_user

        if not user.permissions or not user.permissions.can_view_releases:
            return jsonify({'error': 'Permission denied'}), 403

        # Get query params
        status_filter = request.args.get('status')
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)

        db_session = db_manager.get_session()
        try:
            query = db_session.query(Release)\
                .options(joinedload(Release.release_manager))

            # Apply filters
            if status_filter:
                try:
                    status_enum = ReleaseStatus(status_filter)
                    query = query.filter(Release.status == status_enum)
                except ValueError:
                    pass

            # Get total count
            total = query.count()

            # Apply pagination
            releases = query.order_by(desc(Release.release_date), desc(Release.created_at))\
                .offset((page - 1) * per_page)\
                .limit(per_page)\
                .all()

            releases_data = [{
                'id': r.id,
                'version': r.version,
                'name': r.name,
                'description': r.description,
                'status': r.status.value if r.status else None,
                'release_type': r.release_type.value if r.release_type else None,
                'planned_date': r.planned_date.isoformat() if r.planned_date else None,
                'release_date': r.release_date.isoformat() if r.release_date else None,
                'release_manager': {
                    'id': r.release_manager.id,
                    'username': r.release_manager.username
                } if r.release_manager else None,
                'created_at': r.created_at.isoformat() + 'Z' if r.created_at else None
            } for r in releases]

            return jsonify({
                'releases': releases_data,
                'total': total,
                'page': page,
                'per_page': per_page,
                'total_pages': (total + per_page - 1) // per_page
            }), 200

        finally:
            db_session.close()

    except Exception as e:
        logger.error(f"Get releases error: {str(e)}")
        return jsonify({'error': 'Failed to get releases'}), 500


@json_api_bp.route('/dev/releases/<int:release_id>', methods=['GET'])
@require_jwt_auth
def get_release_detail(release_id):
    """
    Get single release detail with features and bugs

    GET /mobile/dev/releases/<id>
    """
    from models.release import Release
    from sqlalchemy.orm import joinedload

    try:
        user = request.current_user

        if not user.permissions or not user.permissions.can_view_releases:
            return jsonify({'error': 'Permission denied'}), 403

        db_session = db_manager.get_session()
        try:
            release = db_session.query(Release)\
                .options(joinedload(Release.release_manager))\
                .options(joinedload(Release.features))\
                .options(joinedload(Release.fixed_bugs))\
                .options(joinedload(Release.changelog_entries))\
                .filter(Release.id == release_id)\
                .first()

            if not release:
                return jsonify({'error': 'Release not found'}), 404

            features_data = [{
                'id': f.id,
                'display_id': f.display_id,
                'title': f.title,
                'status': f.status.value if f.status else None
            } for f in (release.features or [])]

            bugs_data = [{
                'id': b.id,
                'display_id': b.display_id,
                'title': b.title,
                'severity': b.severity.value if b.severity else None
            } for b in (release.fixed_bugs or [])]

            changelog_data = [{
                'id': c.id,
                'title': c.title,
                'description': c.description,
                'entry_type': c.entry_type.value if c.entry_type else None
            } for c in (release.changelog_entries or [])]

            return jsonify({
                'id': release.id,
                'version': release.version,
                'name': release.name,
                'description': release.description,
                'status': release.status.value if release.status else None,
                'release_type': release.release_type.value if release.release_type else None,
                'planned_date': release.planned_date.isoformat() if release.planned_date else None,
                'release_date': release.release_date.isoformat() if release.release_date else None,
                'release_notes': release.release_notes,
                'release_manager': {
                    'id': release.release_manager.id,
                    'username': release.release_manager.username
                } if release.release_manager else None,
                'features': features_data,
                'fixed_bugs': bugs_data,
                'changelog_entries': changelog_data,
                'created_at': release.created_at.isoformat() + 'Z' if release.created_at else None,
                'updated_at': release.updated_at.isoformat() + 'Z' if release.updated_at else None
            }), 200

        finally:
            db_session.close()

    except Exception as e:
        logger.error(f"Get release detail error: {str(e)}")
        return jsonify({'error': 'Failed to get release'}), 500


@json_api_bp.route('/dev/changelog', methods=['GET'])
@require_jwt_auth
def get_dev_changelog():
    """
    Get development changelog / git commits

    GET /mobile/dev/changelog
    Query params: page, per_page, type
    """
    from models.dev_blog_entry import DevBlogEntry
    from sqlalchemy import desc

    try:
        user = request.current_user

        if not user.permissions or not user.permissions.can_access_development:
            return jsonify({'error': 'Permission denied'}), 403

        # Get query params
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)
        commit_type = request.args.get('type')

        db_session = db_manager.get_session()
        try:
            query = db_session.query(DevBlogEntry)\
                .filter(DevBlogEntry.is_visible == True)

            # Apply type filter
            if commit_type:
                query = query.filter(DevBlogEntry.commit_type == commit_type)

            # Get total count
            total = query.count()

            # Apply pagination
            entries = query.order_by(desc(DevBlogEntry.commit_date))\
                .offset((page - 1) * per_page)\
                .limit(per_page)\
                .all()

            entries_data = [{
                'id': e.id,
                'commit_hash': e.commit_hash,
                'commit_type': e.commit_type,
                'title': e.title,
                'description': e.description,
                'author': e.author,
                'commit_date': e.commit_date.isoformat() + 'Z' if e.commit_date else None,
                'files_changed': e.files_changed
            } for e in entries]

            return jsonify({
                'entries': entries_data,
                'total': total,
                'page': page,
                'per_page': per_page,
                'total_pages': (total + per_page - 1) // per_page
            }), 200

        finally:
            db_session.close()

    except Exception as e:
        logger.error(f"Get dev changelog error: {str(e)}")
        return jsonify({'error': 'Failed to get changelog'}), 500


@json_api_bp.route('/dev/schedule', methods=['GET'])
@require_jwt_auth
def get_dev_schedule():
    """
    Get developer schedule for a date range

    GET /mobile/dev/schedule
    Query params: start_date, end_date (YYYY-MM-DD format)
    """
    from models.developer_schedule import DeveloperSchedule
    from sqlalchemy.orm import joinedload
    from datetime import date, timedelta

    try:
        user = request.current_user

        if not user.permissions or not user.permissions.can_access_development:
            return jsonify({'error': 'Permission denied'}), 403

        # Get query params
        start_date_str = request.args.get('start_date')
        end_date_str = request.args.get('end_date')

        # Default to current week if not specified
        today = date.today()
        monday = today - timedelta(days=today.weekday())
        friday = monday + timedelta(days=4)

        if start_date_str:
            try:
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            except ValueError:
                start_date = monday
        else:
            start_date = monday

        if end_date_str:
            try:
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            except ValueError:
                end_date = friday
        else:
            end_date = friday

        db_session = db_manager.get_session()
        try:
            schedules = db_session.query(DeveloperSchedule)\
                .options(joinedload(DeveloperSchedule.user))\
                .filter(DeveloperSchedule.work_date >= start_date)\
                .filter(DeveloperSchedule.work_date <= end_date)\
                .order_by(DeveloperSchedule.work_date, DeveloperSchedule.user_id)\
                .all()

            # Organize by user
            schedule_by_user = {}
            for s in schedules:
                user_id = str(s.user_id)
                if user_id not in schedule_by_user:
                    schedule_by_user[user_id] = {
                        'user_id': s.user_id,
                        'username': s.user.username if s.user else None,
                        'days': []
                    }
                schedule_by_user[user_id]['days'].append({
                    'date': s.work_date.isoformat() if s.work_date else None,
                    'is_working': s.is_working,
                    'work_location': s.work_location,
                    'note': s.note
                })

            return jsonify({
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
                'schedules': list(schedule_by_user.values())
            }), 200

        finally:
            db_session.close()

    except Exception as e:
        logger.error(f"Get dev schedule error: {str(e)}")
        return jsonify({'error': 'Failed to get schedule'}), 500


@json_api_bp.route('/dev/schedule', methods=['POST'])
@require_jwt_auth
def update_dev_schedule():
    """
    Update developer schedule entry

    POST /mobile/dev/schedule
    Body: {
        "work_date": "2024-01-15",
        "is_working": true,
        "work_location": "Office",
        "note": "Working on feature X"
    }
    """
    from models.developer_schedule import DeveloperSchedule
    from datetime import date

    try:
        user = request.current_user

        if not user.permissions or not user.permissions.can_access_development:
            return jsonify({'error': 'Permission denied'}), 403

        data = request.get_json()
        if not data:
            return jsonify({'error': 'JSON body required'}), 400

        work_date_str = data.get('work_date')
        if not work_date_str:
            return jsonify({'error': 'work_date is required'}), 400

        try:
            work_date = datetime.strptime(work_date_str, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400

        db_session = db_manager.get_session()
        try:
            # Find existing schedule or create new
            schedule = db_session.query(DeveloperSchedule)\
                .filter(DeveloperSchedule.user_id == user.id)\
                .filter(DeveloperSchedule.work_date == work_date)\
                .first()

            if not schedule:
                schedule = DeveloperSchedule(
                    user_id=user.id,
                    work_date=work_date
                )
                db_session.add(schedule)

            # Update fields
            if 'is_working' in data:
                schedule.is_working = data['is_working']
            if 'work_location' in data:
                schedule.work_location = data['work_location']
            if 'note' in data:
                schedule.note = data['note']

            db_session.commit()

            return jsonify({
                'success': True,
                'schedule': {
                    'id': schedule.id,
                    'user_id': schedule.user_id,
                    'work_date': schedule.work_date.isoformat() if schedule.work_date else None,
                    'is_working': schedule.is_working,
                    'work_location': schedule.work_location,
                    'note': schedule.note
                }
            }), 200

        finally:
            db_session.close()

    except Exception as e:
        logger.error(f"Update dev schedule error: {str(e)}")
        return jsonify({'error': 'Failed to update schedule'}), 500


@json_api_bp.route('/dev/schedule/me', methods=['GET'])
@require_jwt_auth
def get_my_schedule():
    """
    Get only current user's schedule for a date range

    GET /mobile/dev/schedule/me
    Query params:
        - start_date: YYYY-MM-DD (optional, defaults to Monday of current week)
        - end_date: YYYY-MM-DD (optional, defaults to Friday of current week)

    Returns: Current user's schedule entries
    """
    from models.developer_schedule import DeveloperSchedule
    from datetime import date, timedelta

    try:
        user = request.current_user

        if not user.permissions or not user.permissions.can_access_development:
            return jsonify({'error': 'Permission denied'}), 403

        # Get query params
        start_date_str = request.args.get('start_date')
        end_date_str = request.args.get('end_date')

        # Default to current week if not specified
        today = date.today()
        monday = today - timedelta(days=today.weekday())
        friday = monday + timedelta(days=4)

        if start_date_str:
            try:
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            except ValueError:
                return jsonify({'error': 'Invalid start_date format. Use YYYY-MM-DD'}), 400
        else:
            start_date = monday

        if end_date_str:
            try:
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            except ValueError:
                return jsonify({'error': 'Invalid end_date format. Use YYYY-MM-DD'}), 400
        else:
            end_date = friday

        db_session = db_manager.get_session()
        try:
            schedules = db_session.query(DeveloperSchedule)\
                .filter(DeveloperSchedule.user_id == user.id)\
                .filter(DeveloperSchedule.work_date >= start_date)\
                .filter(DeveloperSchedule.work_date <= end_date)\
                .order_by(DeveloperSchedule.work_date)\
                .all()

            schedule_data = [{
                'id': s.id,
                'work_date': s.work_date.isoformat() if s.work_date else None,
                'is_working': s.is_working,
                'work_location': s.work_location,
                'note': s.note
            } for s in schedules]

            return jsonify({
                'user_id': user.id,
                'username': user.username,
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
                'schedules': schedule_data
            }), 200

        finally:
            db_session.close()

    except Exception as e:
        logger.error(f"Get my schedule error: {str(e)}")
        return jsonify({'error': 'Failed to get schedule'}), 500


@json_api_bp.route('/dev/schedule/bulk', methods=['POST'])
@require_jwt_auth
def bulk_update_schedule():
    """
    Bulk update schedule - mark multiple days at once

    POST /mobile/dev/schedule/bulk
    Body: {
        "dates": ["2024-01-15", "2024-01-16", "2024-01-17"],
        "is_working": true,
        "work_location": "WFO",
        "note": "Optional note"
    }

    Returns: Number of created/updated entries
    """
    from models.developer_schedule import DeveloperSchedule

    try:
        user = request.current_user

        if not user.permissions or not user.permissions.can_access_development:
            return jsonify({'error': 'Permission denied'}), 403

        data = request.get_json()
        if not data:
            return jsonify({'error': 'JSON body required'}), 400

        dates = data.get('dates', [])
        if not dates:
            return jsonify({'error': 'No dates provided'}), 400

        is_working = data.get('is_working', True)
        work_location = data.get('work_location', 'WFO')
        note = data.get('note', '')

        db_session = db_manager.get_session()
        try:
            created = 0
            updated = 0

            for date_str in dates:
                try:
                    work_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                except ValueError:
                    continue  # Skip invalid dates

                existing = db_session.query(DeveloperSchedule)\
                    .filter(DeveloperSchedule.user_id == user.id)\
                    .filter(DeveloperSchedule.work_date == work_date)\
                    .first()

                if existing:
                    existing.is_working = is_working
                    existing.work_location = work_location
                    existing.note = note
                    existing.updated_at = datetime.utcnow()
                    updated += 1
                else:
                    new_schedule = DeveloperSchedule(
                        user_id=user.id,
                        work_date=work_date,
                        is_working=is_working,
                        work_location=work_location,
                        note=note
                    )
                    db_session.add(new_schedule)
                    created += 1

            db_session.commit()

            return jsonify({
                'success': True,
                'created': created,
                'updated': updated,
                'total': created + updated
            }), 200

        finally:
            db_session.close()

    except Exception as e:
        logger.error(f"Bulk update schedule error: {str(e)}")
        return jsonify({'error': 'Failed to update schedule'}), 500


@json_api_bp.route('/dev/schedule/week', methods=['POST'])
@require_jwt_auth
def mark_week_schedule():
    """
    Quick action: Mark entire week (Mon-Fri) with same status

    POST /mobile/dev/schedule/week
    Body: {
        "week_start": "2024-01-15",  // Monday of the week (optional, defaults to current week)
        "is_working": true,
        "work_location": "WFO",  // "WFO", "WFH", or any string
        "note": "Optional note"
    }

    Returns: Updated schedule for the week
    """
    from models.developer_schedule import DeveloperSchedule
    from datetime import date, timedelta

    try:
        user = request.current_user

        if not user.permissions or not user.permissions.can_access_development:
            return jsonify({'error': 'Permission denied'}), 403

        data = request.get_json()
        if not data:
            return jsonify({'error': 'JSON body required'}), 400

        # Get week start or default to current week's Monday
        week_start_str = data.get('week_start')
        if week_start_str:
            try:
                monday = datetime.strptime(week_start_str, '%Y-%m-%d').date()
            except ValueError:
                return jsonify({'error': 'Invalid week_start format. Use YYYY-MM-DD'}), 400
        else:
            today = date.today()
            monday = today - timedelta(days=today.weekday())

        is_working = data.get('is_working', True)
        work_location = data.get('work_location', 'WFO')
        note = data.get('note', '')

        # Generate weekday dates (Mon-Fri)
        weekdays = [monday + timedelta(days=i) for i in range(5)]

        db_session = db_manager.get_session()
        try:
            created = 0
            updated = 0
            schedules = []

            for work_date in weekdays:
                existing = db_session.query(DeveloperSchedule)\
                    .filter(DeveloperSchedule.user_id == user.id)\
                    .filter(DeveloperSchedule.work_date == work_date)\
                    .first()

                if existing:
                    existing.is_working = is_working
                    existing.work_location = work_location
                    existing.note = note
                    existing.updated_at = datetime.utcnow()
                    updated += 1
                    schedules.append(existing)
                else:
                    new_schedule = DeveloperSchedule(
                        user_id=user.id,
                        work_date=work_date,
                        is_working=is_working,
                        work_location=work_location,
                        note=note
                    )
                    db_session.add(new_schedule)
                    created += 1
                    schedules.append(new_schedule)

            db_session.commit()

            schedule_data = [{
                'id': s.id,
                'work_date': s.work_date.isoformat() if s.work_date else None,
                'is_working': s.is_working,
                'work_location': s.work_location,
                'note': s.note
            } for s in schedules]

            return jsonify({
                'success': True,
                'created': created,
                'updated': updated,
                'week_start': monday.isoformat(),
                'schedules': schedule_data
            }), 200

        finally:
            db_session.close()

    except Exception as e:
        logger.error(f"Mark week schedule error: {str(e)}")
        return jsonify({'error': 'Failed to update schedule'}), 500


@json_api_bp.route('/dev/schedule/<int:user_id>', methods=['GET'])
@require_jwt_auth
def get_user_schedule(user_id):
    """
    Get specific user's schedule (super admin or own schedule)

    GET /mobile/dev/schedule/<user_id>
    Query params:
        - start_date: YYYY-MM-DD (optional)
        - end_date: YYYY-MM-DD (optional)

    Returns: User's schedule entries
    """
    from models.developer_schedule import DeveloperSchedule
    from models.user import UserType
    from datetime import date, timedelta

    try:
        user = request.current_user

        if not user.permissions or not user.permissions.can_access_development:
            return jsonify({'error': 'Permission denied'}), 403

        # Only super admin can view other users' schedules
        if user.id != user_id and user.user_type != UserType.SUPER_ADMIN:
            return jsonify({'error': 'Permission denied'}), 403

        # Get query params
        start_date_str = request.args.get('start_date')
        end_date_str = request.args.get('end_date')

        # Default to current week
        today = date.today()
        monday = today - timedelta(days=today.weekday())
        friday = monday + timedelta(days=4)

        if start_date_str:
            try:
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            except ValueError:
                return jsonify({'error': 'Invalid start_date format'}), 400
        else:
            start_date = monday

        if end_date_str:
            try:
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            except ValueError:
                return jsonify({'error': 'Invalid end_date format'}), 400
        else:
            end_date = friday

        db_session = db_manager.get_session()
        try:
            # Get target user info
            target_user = db_session.query(User).get(user_id)
            if not target_user:
                return jsonify({'error': 'User not found'}), 404

            schedules = db_session.query(DeveloperSchedule)\
                .filter(DeveloperSchedule.user_id == user_id)\
                .filter(DeveloperSchedule.work_date >= start_date)\
                .filter(DeveloperSchedule.work_date <= end_date)\
                .order_by(DeveloperSchedule.work_date)\
                .all()

            schedule_data = [{
                'id': s.id,
                'work_date': s.work_date.isoformat() if s.work_date else None,
                'is_working': s.is_working,
                'work_location': s.work_location,
                'note': s.note
            } for s in schedules]

            return jsonify({
                'user_id': user_id,
                'username': target_user.username,
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
                'schedules': schedule_data
            }), 200

        finally:
            db_session.close()

    except Exception as e:
        logger.error(f"Get user schedule error: {str(e)}")
        return jsonify({'error': 'Failed to get schedule'}), 500


@json_api_bp.route('/dev/schedule/delete', methods=['POST'])
@require_jwt_auth
def delete_schedule_entry():
    """
    Delete a schedule entry

    POST /mobile/dev/schedule/delete
    Body: {
        "work_date": "2024-01-15"
    }

    Returns: Success status
    """
    from models.developer_schedule import DeveloperSchedule

    try:
        user = request.current_user

        if not user.permissions or not user.permissions.can_access_development:
            return jsonify({'error': 'Permission denied'}), 403

        data = request.get_json()
        if not data:
            return jsonify({'error': 'JSON body required'}), 400

        work_date_str = data.get('work_date')
        if not work_date_str:
            return jsonify({'error': 'work_date is required'}), 400

        try:
            work_date = datetime.strptime(work_date_str, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400

        db_session = db_manager.get_session()
        try:
            schedule = db_session.query(DeveloperSchedule)\
                .filter(DeveloperSchedule.user_id == user.id)\
                .filter(DeveloperSchedule.work_date == work_date)\
                .first()

            if not schedule:
                return jsonify({'error': 'Schedule entry not found'}), 404

            db_session.delete(schedule)
            db_session.commit()

            return jsonify({
                'success': True,
                'message': f'Schedule entry for {work_date_str} deleted'
            }), 200

        finally:
            db_session.close()

    except Exception as e:
        logger.error(f"Delete schedule entry error: {str(e)}")
        return jsonify({'error': 'Failed to delete schedule entry'}), 500


# MARK: - Developer Work Plan Endpoints

@json_api_bp.route('/dev/work-plans', methods=['GET'])
@require_jwt_auth
def get_work_plans():
    """
    Get work plans - own plans or all developers' plans (super admin)

    GET /mobile/dev/work-plans?week_start=2024-01-15
    Query params:
        - week_start: Start of week (Monday) in YYYY-MM-DD format (optional, defaults to current week)
        - all: Set to 'true' to get all developers' plans (super admin only)

    Returns: List of work plans
    """
    from models.developer_work_plan import DeveloperWorkPlan
    from models.user import UserType
    from sqlalchemy.orm import joinedload
    from datetime import date, timedelta

    try:
        user = request.current_user

        if not user.permissions or not user.permissions.can_access_development:
            return jsonify({'error': 'Permission denied'}), 403

        db_session = db_manager.get_session()
        try:
            # Get week start from query param or default to current week
            week_start_str = request.args.get('week_start')
            if week_start_str:
                try:
                    week_start = datetime.strptime(week_start_str, '%Y-%m-%d').date()
                except ValueError:
                    return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400
            else:
                # Default to current week's Monday
                today = date.today()
                week_start = today - timedelta(days=today.weekday())

            # Check if requesting all plans (super admin only)
            get_all = request.args.get('all', '').lower() == 'true'

            if get_all:
                # Only super admin can view all plans
                if user.user_type != UserType.SUPER_ADMIN:
                    return jsonify({'error': 'Permission denied - Super Admin only'}), 403

                # Get all developers' work plans for the week
                plans = db_session.query(DeveloperWorkPlan)\
                    .options(joinedload(DeveloperWorkPlan.user))\
                    .filter(DeveloperWorkPlan.week_start == week_start)\
                    .all()

                plans_data = [{
                    'id': p.id,
                    'user_id': p.user_id,
                    'username': p.user.username if p.user else None,
                    'week_start': p.week_start.isoformat() if p.week_start else None,
                    'plan_summary': p.plan_summary,
                    'monday_plan': p.monday_plan,
                    'tuesday_plan': p.tuesday_plan,
                    'wednesday_plan': p.wednesday_plan,
                    'thursday_plan': p.thursday_plan,
                    'friday_plan': p.friday_plan,
                    'blockers': p.blockers,
                    'notes': p.notes,
                    'status': p.status,
                    'created_at': p.created_at.isoformat() + 'Z' if p.created_at else None,
                    'updated_at': p.updated_at.isoformat() + 'Z' if p.updated_at else None,
                    'submitted_at': p.submitted_at.isoformat() + 'Z' if p.submitted_at else None
                } for p in plans]

                # Get all developers to show who hasn't submitted
                developers = db_session.query(User)\
                    .filter(User.user_type == UserType.DEVELOPER)\
                    .all()

                developers_data = [{
                    'id': d.id,
                    'username': d.username,
                    'has_plan': any(p['user_id'] == d.id for p in plans_data)
                } for d in developers]

                return jsonify({
                    'week_start': week_start.isoformat(),
                    'plans': plans_data,
                    'developers': developers_data
                }), 200
            else:
                # Get current user's work plan
                plan = db_session.query(DeveloperWorkPlan)\
                    .filter(DeveloperWorkPlan.user_id == user.id)\
                    .filter(DeveloperWorkPlan.week_start == week_start)\
                    .first()

                if plan:
                    plan_data = {
                        'id': plan.id,
                        'user_id': plan.user_id,
                        'week_start': plan.week_start.isoformat() if plan.week_start else None,
                        'plan_summary': plan.plan_summary,
                        'monday_plan': plan.monday_plan,
                        'tuesday_plan': plan.tuesday_plan,
                        'wednesday_plan': plan.wednesday_plan,
                        'thursday_plan': plan.thursday_plan,
                        'friday_plan': plan.friday_plan,
                        'blockers': plan.blockers,
                        'notes': plan.notes,
                        'status': plan.status,
                        'created_at': plan.created_at.isoformat() + 'Z' if plan.created_at else None,
                        'updated_at': plan.updated_at.isoformat() + 'Z' if plan.updated_at else None,
                        'submitted_at': plan.submitted_at.isoformat() + 'Z' if plan.submitted_at else None
                    }
                else:
                    plan_data = None

                return jsonify({
                    'week_start': week_start.isoformat(),
                    'plan': plan_data
                }), 200

        finally:
            db_session.close()

    except Exception as e:
        logger.error(f"Get work plans error: {str(e)}")
        return jsonify({'error': 'Failed to get work plans'}), 500


@json_api_bp.route('/dev/work-plans/<int:user_id>', methods=['GET'])
@require_jwt_auth
def get_user_work_plan(user_id):
    """
    Get specific user's work plan (super admin or own plan)

    GET /mobile/dev/work-plans/<user_id>?week_start=2024-01-15
    Query params:
        - week_start: Start of week (Monday) in YYYY-MM-DD format (optional)

    Returns: User's work plan for the specified week
    """
    from models.developer_work_plan import DeveloperWorkPlan
    from models.user import UserType
    from sqlalchemy.orm import joinedload
    from datetime import date, timedelta

    try:
        user = request.current_user

        if not user.permissions or not user.permissions.can_access_development:
            return jsonify({'error': 'Permission denied'}), 403

        # Only super admin can view other users' plans
        if user.id != user_id and user.user_type != UserType.SUPER_ADMIN:
            return jsonify({'error': 'Permission denied'}), 403

        db_session = db_manager.get_session()
        try:
            # Get week start from query param or default to current week
            week_start_str = request.args.get('week_start')
            if week_start_str:
                try:
                    week_start = datetime.strptime(week_start_str, '%Y-%m-%d').date()
                except ValueError:
                    return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400
            else:
                # Default to current week's Monday
                today = date.today()
                week_start = today - timedelta(days=today.weekday())

            # Get the target user
            target_user = db_session.query(User).get(user_id)
            if not target_user:
                return jsonify({'error': 'User not found'}), 404

            # Get work plan
            plan = db_session.query(DeveloperWorkPlan)\
                .filter(DeveloperWorkPlan.user_id == user_id)\
                .filter(DeveloperWorkPlan.week_start == week_start)\
                .first()

            if plan:
                plan_data = {
                    'id': plan.id,
                    'user_id': plan.user_id,
                    'username': target_user.username,
                    'week_start': plan.week_start.isoformat() if plan.week_start else None,
                    'plan_summary': plan.plan_summary,
                    'monday_plan': plan.monday_plan,
                    'tuesday_plan': plan.tuesday_plan,
                    'wednesday_plan': plan.wednesday_plan,
                    'thursday_plan': plan.thursday_plan,
                    'friday_plan': plan.friday_plan,
                    'blockers': plan.blockers,
                    'notes': plan.notes,
                    'status': plan.status,
                    'created_at': plan.created_at.isoformat() + 'Z' if plan.created_at else None,
                    'updated_at': plan.updated_at.isoformat() + 'Z' if plan.updated_at else None,
                    'submitted_at': plan.submitted_at.isoformat() + 'Z' if plan.submitted_at else None
                }
            else:
                plan_data = None

            return jsonify({
                'user_id': user_id,
                'username': target_user.username,
                'week_start': week_start.isoformat(),
                'plan': plan_data
            }), 200

        finally:
            db_session.close()

    except Exception as e:
        logger.error(f"Get user work plan error: {str(e)}")
        return jsonify({'error': 'Failed to get work plan'}), 500


@json_api_bp.route('/dev/work-plans', methods=['POST'])
@require_jwt_auth
def save_work_plan():
    """
    Create or update work plan

    POST /mobile/dev/work-plans
    Body: {
        "week_start": "2024-01-15",
        "plan_summary": "This week I will focus on...",
        "monday_plan": "Feature development",
        "tuesday_plan": "Code review",
        "wednesday_plan": "Bug fixes",
        "thursday_plan": "Testing",
        "friday_plan": "Documentation",
        "blockers": "Waiting on API spec",
        "notes": "May need help from backend team",
        "submit": false
    }

    Returns: Saved work plan
    """
    from models.developer_work_plan import DeveloperWorkPlan
    from datetime import date, timedelta

    try:
        user = request.current_user

        if not user.permissions or not user.permissions.can_access_development:
            return jsonify({'error': 'Permission denied'}), 403

        data = request.get_json()
        if not data:
            return jsonify({'error': 'JSON body required'}), 400

        # Get week start from body or default to current week
        week_start_str = data.get('week_start')
        if week_start_str:
            try:
                week_start = datetime.strptime(week_start_str, '%Y-%m-%d').date()
            except ValueError:
                return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400
        else:
            # Default to current week's Monday
            today = date.today()
            week_start = today - timedelta(days=today.weekday())

        db_session = db_manager.get_session()
        try:
            # Find existing plan or create new one
            plan = db_session.query(DeveloperWorkPlan)\
                .filter(DeveloperWorkPlan.user_id == user.id)\
                .filter(DeveloperWorkPlan.week_start == week_start)\
                .first()

            if not plan:
                plan = DeveloperWorkPlan(
                    user_id=user.id,
                    week_start=week_start
                )
                db_session.add(plan)

            # Update fields
            if 'plan_summary' in data:
                plan.plan_summary = data['plan_summary']
            if 'monday_plan' in data:
                plan.monday_plan = data['monday_plan']
            if 'tuesday_plan' in data:
                plan.tuesday_plan = data['tuesday_plan']
            if 'wednesday_plan' in data:
                plan.wednesday_plan = data['wednesday_plan']
            if 'thursday_plan' in data:
                plan.thursday_plan = data['thursday_plan']
            if 'friday_plan' in data:
                plan.friday_plan = data['friday_plan']
            if 'blockers' in data:
                plan.blockers = data['blockers']
            if 'notes' in data:
                plan.notes = data['notes']

            plan.updated_at = datetime.utcnow()

            # Handle submission
            if data.get('submit'):
                plan.status = 'submitted'
                plan.submitted_at = datetime.utcnow()

            db_session.commit()

            return jsonify({
                'success': True,
                'plan': {
                    'id': plan.id,
                    'user_id': plan.user_id,
                    'week_start': plan.week_start.isoformat() if plan.week_start else None,
                    'plan_summary': plan.plan_summary,
                    'monday_plan': plan.monday_plan,
                    'tuesday_plan': plan.tuesday_plan,
                    'wednesday_plan': plan.wednesday_plan,
                    'thursday_plan': plan.thursday_plan,
                    'friday_plan': plan.friday_plan,
                    'blockers': plan.blockers,
                    'notes': plan.notes,
                    'status': plan.status,
                    'created_at': plan.created_at.isoformat() + 'Z' if plan.created_at else None,
                    'updated_at': plan.updated_at.isoformat() + 'Z' if plan.updated_at else None,
                    'submitted_at': plan.submitted_at.isoformat() + 'Z' if plan.submitted_at else None
                }
            }), 200

        finally:
            db_session.close()

    except Exception as e:
        logger.error(f"Save work plan error: {str(e)}")
        return jsonify({'error': 'Failed to save work plan'}), 500