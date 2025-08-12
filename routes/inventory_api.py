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
from utils.db_manager import DatabaseManager
from routes.mobile_api import mobile_auth_required

# Set up logging
logger = logging.getLogger(__name__)

# Create Inventory API blueprint
inventory_api_bp = Blueprint('inventory_api', __name__, url_prefix='/api/v1')
db_manager = DatabaseManager()

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
        
        # Hardware specifications
        "cpu_type": safe_str(asset.cpu_type),
        "cpu_cores": safe_int(asset.cpu_cores),
        "gpu_cores": safe_int(asset.gpu_cores),
        "memory": safe_str(asset.memory),
        "storage": safe_str(asset.harddrive),  # Map harddrive to storage
        "hardware_type": safe_str(asset.hardware_type),
        "asset_type": safe_str(asset.asset_type),
        
        # Condition and status details
        "condition": safe_str(asset.condition),
        "is_erased": bool_to_display(asset.erased) if asset.erased not in [None, '', 'None'] else None,
        "has_keyboard": bool_to_display(asset.keyboard) if asset.keyboard not in [None, '', 'None'] else None,
        "has_charger": bool_to_display(asset.charger) if asset.charger not in [None, '', 'None'] else None,
        "diagnostics_code": safe_str(asset.diag),
        
        # Location and assignment details
        "current_customer": safe_str(asset.customer),
        "country": safe_str(asset.country),
        "asset_company": asset.company.name if asset.company else None,
        "receiving_date": asset.receiving_date.isoformat() if asset.receiving_date else None,
        
        # Standard timestamps
        "created_at": asset.created_at.isoformat() if asset.created_at else None,
        "updated_at": asset.updated_at.isoformat() if asset.updated_at else None,
        
        # Additional useful fields
        "description": safe_str(asset.notes),
        "location": asset.location.name if asset.location else None,
        "assigned_to": {
            "id": asset.assigned_to.id,
            "name": f"{asset.assigned_to.first_name or ''} {asset.assigned_to.last_name or ''}".strip(),
            "email": asset.assigned_to.email
        } if asset.assigned_to else None,
        "customer_user": {
            "id": asset.customer_user.id,
            "name": asset.customer_user.name,
            "email": asset.customer_user.email
        } if asset.customer_user else None
    }

@inventory_api_bp.route('/inventory', methods=['GET'])
@mobile_auth_required
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
            if user.user_type == UserType.COUNTRY_ADMIN and user.assigned_country:
                query = query.filter(Asset.country == user.assigned_country.value)
            
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
@mobile_auth_required
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
            if user.user_type == UserType.COUNTRY_ADMIN and user.assigned_country:
                query = query.filter(Asset.country == user.assigned_country.value)
            
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
            '/api/v1/inventory/{id}'
        ]
    }), 200