"""
Enhanced Inventory API Routes for Complete Asset Information

This module provides comprehensive JSON API endpoints that return complete 
asset information including hardware specifications, condition details, 
and location/assignment information as requested.

Endpoints:
- GET /api/v1/inventory - List all inventory items with complete info
- GET /api/v1/inventory/{id} - Get single inventory item with complete info
"""

from flask import Blueprint, request, jsonify
from datetime import datetime
import logging

from models.user import User, UserType
from models.asset import Asset, AssetStatus
from models.accessory import Accessory
from utils.db_manager import DatabaseManager
from routes.mobile_api import mobile_auth_required, verify_mobile_token, get_asset_image_url, get_full_image_url
from functools import wraps

# Set up logging
logger = logging.getLogger(__name__)

# Create Inventory API blueprint
inventory_api_bp = Blueprint('inventory_api', __name__, url_prefix='/api/v1')
db_manager = DatabaseManager()

# Support for JSON API key system for backward compatibility
JSON_API_KEY = 'xAQhm3__ZH6MvRIPMIBSDRAsIa1w2Slh5uaCtc4NurM'

def dual_auth_required(f):
    """
    Enhanced authentication decorator that supports both:
    1. Mobile JWT authentication (preferred)
    2. JSON API key + JWT authentication (backward compatibility)
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = None
        
        # Method 1: Try JSON API key + JWT authentication first
        api_key = request.headers.get('X-API-Key')
        if api_key == JSON_API_KEY:
            # JSON API key authentication - also needs JWT token
            auth_header = request.headers.get('Authorization')
            if auth_header and auth_header.startswith('Bearer '):
                token = auth_header.split(' ')[1]
                from routes.json_api import verify_jwt_token
                user_id = verify_jwt_token(token)
                
                if user_id:
                    # Get user from database
                    db_session = db_manager.get_session()
                    try:
                        user = db_session.query(User).filter(User.id == user_id).first()
                        if user:
                            logger.info(f"JSON API authentication successful for user: {user.username}")
                    finally:
                        db_session.close()
        
        # Method 2: Try mobile JWT authentication (no API key needed)
        if not user:
            auth_header = request.headers.get('Authorization')
            if auth_header and auth_header.startswith('Bearer '):
                token = auth_header.split(' ')[1]
                user = verify_mobile_token(token)
                if user:
                    logger.info(f"Mobile JWT authentication successful for user: {user.username}")
        
        # If no valid authentication found
        if not user:
            return jsonify({
                'error': 'Authentication required',
                'message': 'Please provide either: (1) Mobile JWT token in Authorization header, or (2) JSON API key in X-API-Key header plus JWT token in Authorization header'
            }), 401
        
        # Check permissions
        if not user.permissions or not user.permissions.can_view_assets:
            return jsonify({
                'error': 'Insufficient permissions',
                'message': 'User does not have permission to view assets and accessories'
            }), 403
        
        # Set current user for the request
        request.current_mobile_user = user
        return f(*args, **kwargs)
    
    return decorated_function

def format_accessory_complete(accessory):
    """Format accessory with complete information"""
    # Handle string fields
    def safe_str(value):
        if value is None:
            return None
        return str(value).strip() if str(value).strip() else None
    
    # Handle numeric fields
    def safe_int(value):
        if value is None or value == '':
            return None
        try:
            return int(value)
        except (ValueError, TypeError):
            return None
    
    return {
        # Basic identification
        "id": accessory.id,
        "name": safe_str(accessory.name),
        "category": safe_str(accessory.category),
        "manufacturer": safe_str(accessory.manufacturer),
        "model": safe_str(accessory.model_no),
        "status": safe_str(accessory.status) or "available",
        
        # Inventory details
        "total_quantity": safe_int(accessory.total_quantity) or 0,
        "available_quantity": safe_int(accessory.available_quantity) or 0,
        "checked_out_quantity": (safe_int(accessory.total_quantity) or 0) - (safe_int(accessory.available_quantity) or 0),
        
        # Location and assignment details
        "country": safe_str(accessory.country),
        "current_customer": accessory.customer_user.name if accessory.customer_user else None,
        "customer_email": accessory.customer_user.email if accessory.customer_user else None,
        
        # Status details
        "is_available": (accessory.available_quantity or 0) > 0,
        "checkout_date": accessory.checkout_date.isoformat() if accessory.checkout_date else None,
        "return_date": accessory.return_date.isoformat() if accessory.return_date else None,
        
        # Additional information
        "description": safe_str(accessory.notes),
        "notes": safe_str(accessory.notes),

        # Image URL
        "image_url": get_full_image_url(accessory.image_url),

        # Standard timestamps
        "created_at": accessory.created_at.isoformat() if accessory.created_at else None,
        "updated_at": accessory.updated_at.isoformat() if accessory.updated_at else None,

        # Type identifier
        "item_type": "accessory"
    }

def format_asset_complete(asset):
    """Format asset with complete information as specified"""
    # Handle boolean fields properly
    def bool_to_display(value):
        if value is None:
            return None
        if isinstance(value, bool):
            return value
        # Handle string representations
        if isinstance(value, str):
            return value.lower() in ('true', 'yes', '1', 'y')
        return bool(value)
    
    # Handle numeric fields
    def safe_int(value):
        if value is None or value == '':
            return None
        try:
            return int(value)
        except (ValueError, TypeError):
            return None
    
    # Handle string fields
    def safe_str(value):
        if value is None:
            return None
        return str(value).strip() if str(value).strip() else None
    
    return {
        # Basic identification
        "id": asset.id,
        "name": safe_str(asset.name) or "Unknown Asset",
        "serial_number": safe_str(asset.serial_num),
        "model": safe_str(asset.model),
        "asset_tag": safe_str(asset.asset_tag),
        "manufacturer": safe_str(asset.manufacturer),
        "status": asset.status.value.lower() if asset.status else "available",
        
        # Hardware specifications - COMPLETE SET
        "cpu_type": safe_str(asset.cpu_type),
        "cpu_cores": safe_int(asset.cpu_cores),
        "gpu_cores": safe_int(asset.gpu_cores),
        "memory": safe_str(asset.memory),
        "storage": safe_str(asset.harddrive),  # Map harddrive to storage
        "hardware_type": safe_str(asset.hardware_type),
        "asset_type": safe_str(asset.asset_type),
        
        # Additional hardware specifications from JSON
        "specifications": asset.specifications if asset.specifications else {},
        
        # Condition and status details - COMPLETE SET
        "condition": safe_str(asset.condition),
        "is_erased": bool_to_display(asset.erased) if asset.erased not in [None, '', 'None'] else None,
        "data_erasure_status": safe_str(asset.erased),  # Raw erasure status
        "has_keyboard": bool_to_display(asset.keyboard) if asset.keyboard not in [None, '', 'None'] else None,
        "has_charger": bool_to_display(asset.charger) if asset.charger not in [None, '', 'None'] else None,
        "diagnostics_code": safe_str(asset.diag),
        "functional_condition": safe_str(asset.condition),  # Functional condition status
        
        # Purchase and cost information
        "cost_price": float(asset.cost_price) if asset.cost_price else None,
        "purchase_cost": float(asset.cost_price) if asset.cost_price else None,  # Alias
        "purchase_order": safe_str(asset.po),
        
        # Location and assignment details - COMPLETE SET
        "current_customer": safe_str(asset.customer),
        "country": safe_str(asset.country),
        "asset_company": asset.company.grouped_display_name if asset.company else None,
        "company_id": asset.company_id,
        "receiving_date": asset.receiving_date.isoformat() if asset.receiving_date else None,
        
        # Physical location details
        "location": asset.location.name if asset.location else None,
        "location_id": asset.location_id,
        "location_details": {
            "id": asset.location.id,
            "name": asset.location.name,
            "address": getattr(asset.location, 'address', None),
            "city": getattr(asset.location, 'city', None),
            "country": getattr(asset.location, 'country', None)
        } if asset.location else None,
        
        # Assignment and deployment information - COMPLETE SET
        "assigned_to": {
            "id": asset.assigned_to.id,
            "name": f"{asset.assigned_to.first_name or ''} {asset.assigned_to.last_name or ''}".strip(),
            "email": asset.assigned_to.email,
            "username": asset.assigned_to.username,
            "user_type": asset.assigned_to.user_type.value if asset.assigned_to.user_type else None
        } if asset.assigned_to else None,
        "assigned_to_id": asset.assigned_to_id,
        
        # Customer user assignment (if different from assigned_to)
        "customer_user": {
            "id": asset.customer_user.id,
            "name": asset.customer_user.name,
            "email": asset.customer_user.email,
            "company": getattr(asset.customer_user, 'company', None)
        } if asset.customer_user else None,
        "customer_id": asset.customer_id,
        
        # Additional deployment details
        "inventory_status": safe_str(asset.inventory),
        "intake_ticket_id": asset.intake_ticket_id,
        "intake_ticket": {
            "id": asset.intake_ticket.id,
            "ticket_number": getattr(asset.intake_ticket, 'ticket_number', None),
            "status": getattr(asset.intake_ticket, 'status', None)
        } if asset.intake_ticket else None,
        
        # Technical notes and documentation
        "description": safe_str(asset.notes),
        "notes": safe_str(asset.notes),
        "tech_notes": safe_str(asset.tech_notes),
        "technical_notes": safe_str(asset.tech_notes),  # Alias
        
        # Category information
        "category": safe_str(asset.category),

        # Image URL (with fallback to default product image)
        "image_url": get_asset_image_url(asset),

        # Standard timestamps
        "created_at": asset.created_at.isoformat() if asset.created_at else None,
        "updated_at": asset.updated_at.isoformat() if asset.updated_at else None,

        # Type identifier for API consumers
        "item_type": "asset"
    }

@inventory_api_bp.route('/inventory', methods=['GET'])
@dual_auth_required
def get_complete_inventory():
    """
    Get comprehensive inventory listing with all asset details
    
    GET /api/v1/inventory?page=1&limit=20&search=laptop&status=available
    Headers: Authorization: Bearer <token>
    
    Returns complete asset information including:
    - Hardware specifications (CPU, memory, storage, etc.)
    - Condition details (condition, erased status, accessories)
    - Location and assignment information
    
    Response: {
        "data": [
            {
                "id": 123,
                "name": "MacBook Pro",
                "serial_number": "GFXWF6W4HW",
                "model": "A3401",
                "asset_tag": "ASSET001",
                "manufacturer": "Apple",
                "status": "available",
                "cpu_type": "M3 Pro",
                "cpu_cores": 11,
                "gpu_cores": 14,
                "memory": "36.0 GB",
                "storage": "512.0 GB",
                "hardware_type": "MacBook Pro 14\" Apple",
                "asset_type": "Laptop",
                "condition": "NEW",
                "is_erased": true,
                "has_keyboard": true,
                "has_charger": true,
                "diagnostics_code": "ADP000",
                "current_customer": null,
                "country": "Singapore",
                "asset_company": "Wise",
                "receiving_date": "2025-08-11T09:04:27.257649",
                "created_at": "2025-08-11T09:04:27.257649",
                "updated_at": "2025-08-11T09:04:27.257649"
            }
        ],
        "pagination": {
            "page": 1,
            "limit": 20,
            "total": 150,
            "pages": 8
        }
    }
    """
    try:
        user = request.current_mobile_user
        
        # Check permissions
        if not user.permissions or not user.permissions.can_view_assets:
            return jsonify({
                'error': 'No permission to view inventory'
            }), 403
        
        # Get parameters
        page = request.args.get('page', 1, type=int)
        limit = min(request.args.get('limit', 20, type=int), 100)
        search = request.args.get('search', None)
        status_filter = request.args.get('status', None)
        category_filter = request.args.get('category', None)
        
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
                    # Map common status values to enum
                    status_map = {
                        'available': AssetStatus.READY_TO_DEPLOY,
                        'in_stock': AssetStatus.IN_STOCK,
                        'deployed': AssetStatus.DEPLOYED,
                        'shipped': AssetStatus.SHIPPED,
                        'repair': AssetStatus.REPAIR,
                        'archived': AssetStatus.ARCHIVED,
                        'disposed': AssetStatus.DISPOSED
                    }
                    
                    if status_filter.lower() in status_map:
                        query = query.filter(Asset.status == status_map[status_filter.lower()])
                    else:
                        # Try direct enum matching
                        status_enum = AssetStatus[status_filter.upper()]
                        query = query.filter(Asset.status == status_enum)
                except (KeyError, ValueError):
                    pass  # Invalid status, ignore filter
            
            # Apply category filter
            if category_filter:
                query = query.filter(Asset.asset_type.ilike(f"%{category_filter}%"))
            
            # Apply search filter
            if search:
                search_term = f"%{search}%"
                query = query.filter(
                    (Asset.name.ilike(search_term)) |
                    (Asset.asset_tag.ilike(search_term)) |
                    (Asset.serial_num.ilike(search_term)) |
                    (Asset.model.ilike(search_term)) |
                    (Asset.manufacturer.ilike(search_term)) |
                    (Asset.hardware_type.ilike(search_term))
                )
            
            # Get total count
            total = query.count()
            
            # Apply pagination
            offset = (page - 1) * limit
            assets = query.order_by(Asset.created_at.desc()).offset(offset).limit(limit).all()
            
            # Format assets with complete information
            assets_data = [format_asset_complete(asset) for asset in assets]
            
            pages = (total + limit - 1) // limit
            
            return jsonify({
                'data': assets_data,
                'pagination': {
                    'page': page,
                    'limit': limit,
                    'total': total,
                    'pages': pages
                }
            }), 200
            
        finally:
            db_session.close()
            
    except Exception as e:
        logger.error(f"Get complete inventory error: {str(e)}")
        return jsonify({
            'error': 'Failed to get inventory'
        }), 500

@inventory_api_bp.route('/inventory/<int:asset_id>', methods=['GET'])
@dual_auth_required
def get_complete_asset(asset_id):
    """
    Get single asset with complete information
    
    GET /api/v1/inventory/123
    Headers: Authorization: Bearer <token>
    
    Returns complete asset information including all specifications
    
    Response: {
        "data": {
            "id": 123,
            "name": "MacBook Pro",
            ...all the same fields as the list endpoint...
        }
    }
    """
    try:
        user = request.current_mobile_user
        
        # Check permissions
        if not user.permissions or not user.permissions.can_view_assets:
            return jsonify({
                'error': 'No permission to view inventory'
            }), 403
        
        db_session = db_manager.get_session()
        try:
            # Build query based on user permissions
            query = db_session.query(Asset).filter(Asset.id == asset_id)
            
            # Apply country restrictions for COUNTRY_ADMIN
            if user.user_type == UserType.COUNTRY_ADMIN and user.assigned_countries:
                query = query.filter(Asset.country.in_(user.assigned_countries))
            
            asset = query.first()
            
            if not asset:
                return jsonify({
                    'error': 'Asset not found or access denied'
                }), 404
            
            # Format asset with complete information
            asset_data = format_asset_complete(asset)
            
            return jsonify({
                'data': asset_data
            }), 200
            
        finally:
            db_session.close()
            
    except Exception as e:
        logger.error(f"Get complete asset error: {str(e)}")
        return jsonify({
            'error': 'Failed to get asset'
        }), 500

@inventory_api_bp.route('/accessories', methods=['GET'])
@dual_auth_required
def get_complete_accessories():
    """
    Get comprehensive accessories listing with all details
    
    GET /api/v1/accessories?page=1&limit=20&search=mouse&status=available
    Headers: Authorization: Bearer <token>
    
    Returns complete accessory information including:
    - Basic identification (name, category, manufacturer, model)
    - Inventory details (quantities, availability)
    - Assignment information (current customer, checkout dates)
    - Location details (country)
    
    Response: {
        "data": [
            {
                "id": 45,
                "name": "Wireless Mouse",
                "category": "Computer Accessories",
                "manufacturer": "Logitech",
                "model": "MX Master 3",
                "status": "available",
                "total_quantity": 50,
                "available_quantity": 35,
                "checked_out_quantity": 15,
                "country": "Singapore",
                "current_customer": null,
                "is_available": true,
                "checkout_date": null,
                "return_date": null,
                "description": "Wireless ergonomic mouse",
                "created_at": "2025-08-11T09:04:27.257649",
                "updated_at": "2025-08-11T09:04:27.257649",
                "item_type": "accessory"
            }
        ],
        "pagination": {
            "page": 1,
            "limit": 20,
            "total": 85,
            "pages": 5
        }
    }
    """
    try:
        user = request.current_mobile_user
        
        # Check permissions - using same permission check as assets
        if not user.permissions or not user.permissions.can_view_assets:
            return jsonify({
                'error': 'No permission to view accessories'
            }), 403
        
        # Get parameters
        page = request.args.get('page', 1, type=int)
        limit = min(request.args.get('limit', 20, type=int), 100)
        search = request.args.get('search', None)
        status_filter = request.args.get('status', None)
        category_filter = request.args.get('category', None)
        
        db_session = db_manager.get_session()
        try:
            # Build query based on user permissions
            query = db_session.query(Accessory)
            
            # Apply country restrictions for COUNTRY_ADMIN
            if user.user_type == UserType.COUNTRY_ADMIN and user.assigned_countries:
                query = query.filter(Accessory.country.in_(user.assigned_countries))
            
            # Apply status filter
            if status_filter:
                # Map common status values
                status_map = {
                    'available': 'Available',
                    'checked_out': 'Checked Out',
                    'unavailable': 'Unavailable',
                    'maintenance': 'Maintenance',
                    'retired': 'Retired'
                }
                
                if status_filter.lower() in status_map:
                    query = query.filter(Accessory.status == status_map[status_filter.lower()])
                else:
                    # Direct status matching
                    query = query.filter(Accessory.status.ilike(f"%{status_filter}%"))
            
            # Apply category filter
            if category_filter:
                query = query.filter(Accessory.category.ilike(f"%{category_filter}%"))
            
            # Apply search filter
            if search:
                search_term = f"%{search}%"
                query = query.filter(
                    (Accessory.name.ilike(search_term)) |
                    (Accessory.category.ilike(search_term)) |
                    (Accessory.manufacturer.ilike(search_term)) |
                    (Accessory.model_no.ilike(search_term))
                )
            
            # Get total count
            total = query.count()
            
            # Apply pagination
            offset = (page - 1) * limit
            accessories = query.order_by(Accessory.created_at.desc()).offset(offset).limit(limit).all()
            
            # Format accessories with complete information
            accessories_data = [format_accessory_complete(accessory) for accessory in accessories]
            
            pages = (total + limit - 1) // limit
            
            return jsonify({
                'data': accessories_data,
                'pagination': {
                    'page': page,
                    'limit': limit,
                    'total': total,
                    'pages': pages
                }
            }), 200
            
        finally:
            db_session.close()
            
    except Exception as e:
        logger.error(f"Get complete accessories error: {str(e)}")
        return jsonify({
            'error': 'Failed to get accessories'
        }), 500

@inventory_api_bp.route('/accessories/<int:accessory_id>', methods=['GET'])
@dual_auth_required
def get_complete_accessory(accessory_id):
    """
    Get single accessory with complete information
    
    GET /api/v1/accessories/45
    Headers: Authorization: Bearer <token>
    
    Returns complete accessory information including all details
    
    Response: {
        "data": {
            "id": 45,
            "name": "Wireless Mouse",
            "category": "Computer Accessories",
            "manufacturer": "Logitech",
            "model": "MX Master 3",
            "status": "available",
            "total_quantity": 50,
            "available_quantity": 35,
            "checked_out_quantity": 15,
            "country": "Singapore",
            "current_customer": null,
            "is_available": true,
            "checkout_date": null,
            "return_date": null,
            "description": "Wireless ergonomic mouse",
            "created_at": "2025-08-11T09:04:27.257649",
            "updated_at": "2025-08-11T09:04:27.257649",
            "item_type": "accessory"
        }
    }
    """
    try:
        user = request.current_mobile_user
        
        # Check permissions
        if not user.permissions or not user.permissions.can_view_assets:
            return jsonify({
                'error': 'No permission to view accessories'
            }), 403
        
        db_session = db_manager.get_session()
        try:
            # Build query based on user permissions
            query = db_session.query(Accessory).filter(Accessory.id == accessory_id)
            
            # Apply country restrictions for COUNTRY_ADMIN
            if user.user_type == UserType.COUNTRY_ADMIN and user.assigned_countries:
                query = query.filter(Accessory.country.in_(user.assigned_countries))
            
            accessory = query.first()
            
            if not accessory:
                return jsonify({
                    'error': 'Accessory not found or access denied'
                }), 404
            
            # Format accessory with complete information
            accessory_data = format_accessory_complete(accessory)
            
            return jsonify({
                'data': accessory_data
            }), 200
            
        finally:
            db_session.close()
            
    except Exception as e:
        logger.error(f"Get complete accessory error: {str(e)}")
        return jsonify({
            'error': 'Failed to get accessory'
        }), 500

@inventory_api_bp.route('/inventory/health', methods=['GET'])
def inventory_health_check():
    """
    Health check for inventory API
    
    GET /api/v1/inventory/health
    
    Response: {
        "status": "healthy",
        "timestamp": "2025-08-12T...",
        "version": "v1"
    }
    """
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat() + 'Z',
        'version': 'v1',
        'endpoints': [
            '/api/v1/inventory',
            '/api/v1/inventory/{id}',
            '/api/v1/accessories',
            '/api/v1/accessories/{id}'
        ]
    }), 200