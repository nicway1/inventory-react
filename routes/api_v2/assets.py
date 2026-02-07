"""
API v2 Asset Endpoints

This module provides CRUD operations for assets via the v2 API.

Endpoints:
- POST /api/v2/assets - Create new asset
- PUT /api/v2/assets/<id> - Update asset
- DELETE /api/v2/assets/<id> - Delete/archive asset
- POST /api/v2/assets/<id>/image - Upload asset image
- POST /api/v2/assets/<id>/transfer - Transfer asset to different customer
"""

from flask import request
from datetime import datetime
import logging
import os
import uuid

from . import api_v2_bp
from .utils import (
    api_response,
    api_error,
    api_created,
    api_no_content,
    validate_json_body,
    validate_required_fields,
    handle_exceptions,
    dual_auth_required,
    require_permission,
    ErrorCodes
)

from models.asset import Asset, AssetStatus
from models.asset_history import AssetHistory
from models.activity import Activity
from models.user import UserType
from utils.db_manager import DatabaseManager

logger = logging.getLogger(__name__)
db_manager = DatabaseManager()

# Image upload configuration
ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5MB
UPLOAD_FOLDER = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'static', 'uploads', 'assets'))


def allowed_image_file(filename):
    """Check if file has an allowed image extension"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS


def format_asset_response(asset):
    """Format asset object for API response"""
    return {
        'id': asset.id,
        'asset_tag': asset.asset_tag,
        'serial_number': asset.serial_num,
        'name': asset.name,
        'model': asset.model,
        'manufacturer': asset.manufacturer,
        'category': asset.category,
        'asset_type': asset.asset_type,
        'status': asset.status.value if asset.status else None,
        'condition': asset.condition,
        'country': asset.country,
        'customer': asset.customer,
        'location_id': asset.location_id,
        'company_id': asset.company_id,
        'cost_price': float(asset.cost_price) if asset.cost_price else None,
        'hardware_type': asset.hardware_type,
        'cpu_type': asset.cpu_type,
        'cpu_cores': asset.cpu_cores,
        'gpu_cores': asset.gpu_cores,
        'memory': asset.memory,
        'harddrive': asset.harddrive,
        'keyboard': asset.keyboard,
        'charger': asset.charger,
        'erased': asset.erased,
        'diag': asset.diag,
        'po': asset.po,
        'notes': asset.notes,
        'tech_notes': asset.tech_notes,
        'image_url': asset.image_url,
        'legal_hold': asset.legal_hold,
        'receiving_date': asset.receiving_date.isoformat() if asset.receiving_date else None,
        'created_at': asset.created_at.isoformat() if asset.created_at else None,
        'updated_at': asset.updated_at.isoformat() if asset.updated_at else None,
    }


# =============================================================================
# LIST ASSETS
# =============================================================================

@api_v2_bp.route('/assets', methods=['GET'])
@dual_auth_required
@handle_exceptions
def list_assets():
    """
    List assets with pagination and filtering

    GET /api/v2/assets

    Query Parameters:
        - page: Page number (default: 1)
        - per_page: Items per page (default: 25, max: 100)
        - search: Search by asset_tag, serial_number, name, model
        - status: Filter by status (IN_STOCK, DEPLOYED, REPAIR, etc.)
        - asset_type: Filter by asset type
        - manufacturer: Filter by manufacturer
        - customer: Filter by customer name
        - condition: Filter by condition
        - sort_by: Sort field (default: created_at)
        - sort_order: asc or desc (default: desc)

    Returns:
        Paginated list of assets
    """
    from .utils import paginate_query, get_pagination_params, apply_sorting, get_sorting_params

    db_session = db_manager.get_session()
    try:
        # Get pagination params
        page, per_page = get_pagination_params()

        # Get sorting params
        sort_by = request.args.get('sort_by', 'created_at')
        sort_order = request.args.get('sort_order', 'desc')

        # Build query
        query = db_session.query(Asset)

        # Apply search filter
        search = request.args.get('search', '').strip()
        if search:
            search_term = f'%{search}%'
            query = query.filter(
                (Asset.asset_tag.ilike(search_term)) |
                (Asset.serial_num.ilike(search_term)) |
                (Asset.name.ilike(search_term)) |
                (Asset.model.ilike(search_term))
            )

        # Apply status filter
        status = request.args.get('status')
        if status and status != 'all':
            try:
                status_enum = AssetStatus(status)
                query = query.filter(Asset.status == status_enum)
            except ValueError:
                pass

        # Apply asset_type filter
        asset_type = request.args.get('asset_type')
        if asset_type and asset_type != 'all':
            query = query.filter(Asset.asset_type == asset_type)

        # Apply manufacturer filter
        manufacturer = request.args.get('manufacturer')
        if manufacturer and manufacturer != 'all':
            query = query.filter(Asset.manufacturer.ilike(f'%{manufacturer}%'))

        # Apply customer filter
        customer = request.args.get('customer')
        if customer and customer != 'all':
            query = query.filter(Asset.customer.ilike(f'%{customer}%'))

        # Apply condition filter
        condition = request.args.get('condition')
        if condition and condition != 'all':
            query = query.filter(Asset.condition == condition)

        # Apply sorting
        sort_column = getattr(Asset, sort_by, Asset.created_at)
        if sort_order == 'asc':
            query = query.order_by(sort_column.asc())
        else:
            query = query.order_by(sort_column.desc())

        # Paginate
        assets, pagination_meta = paginate_query(query, page, per_page)

        # Format response
        assets_data = [format_asset_response(asset) for asset in assets]

        return api_response(
            data=assets_data,
            meta=pagination_meta,
            message=f'Retrieved {len(assets_data)} assets'
        )

    except Exception as e:
        logger.error(f'Error listing assets: {str(e)}')
        return api_error(
            ErrorCodes.DATABASE_ERROR,
            f'Failed to list assets: {str(e)}',
            status_code=500
        )
    finally:
        db_session.close()


# =============================================================================
# GET SINGLE ASSET
# =============================================================================

@api_v2_bp.route('/assets/<int:asset_id>', methods=['GET'])
@dual_auth_required
@handle_exceptions
def get_asset(asset_id):
    """
    Get a single asset by ID

    GET /api/v2/assets/<id>

    Returns:
        Asset details
    """
    db_session = db_manager.get_session()
    try:
        asset = db_session.query(Asset).filter(Asset.id == asset_id).first()

        if not asset:
            return api_error(
                ErrorCodes.RESOURCE_NOT_FOUND,
                f'Asset with ID {asset_id} not found',
                status_code=404
            )

        return api_response(
            data=format_asset_response(asset),
            message='Asset retrieved successfully'
        )

    except Exception as e:
        logger.error(f'Error getting asset: {str(e)}')
        return api_error(
            ErrorCodes.DATABASE_ERROR,
            f'Failed to get asset: {str(e)}',
            status_code=500
        )
    finally:
        db_session.close()


# =============================================================================
# ASSET FILTER OPTIONS
# =============================================================================

@api_v2_bp.route('/assets/filter-options', methods=['GET'])
@dual_auth_required
@handle_exceptions
def get_asset_filter_options():
    """
    Get filter options for assets

    GET /api/v2/assets/filter-options

    Returns:
        Available filter options for status, types, manufacturers, etc.
    """
    from sqlalchemy import func

    db_session = db_manager.get_session()
    try:
        # Get distinct statuses
        statuses = [{'value': s.value, 'label': s.value.replace('_', ' ').title()} for s in AssetStatus]

        # Get distinct asset types
        types_query = db_session.query(Asset.asset_type).filter(
            Asset.asset_type.isnot(None)
        ).distinct().all()
        types = [{'value': t[0], 'label': t[0]} for t in types_query if t[0]]

        # Get distinct manufacturers
        manufacturers_query = db_session.query(Asset.manufacturer).filter(
            Asset.manufacturer.isnot(None)
        ).distinct().all()
        manufacturers = [{'value': m[0], 'label': m[0]} for m in manufacturers_query if m[0]]

        # Get distinct customers
        customers_query = db_session.query(Asset.customer).filter(
            Asset.customer.isnot(None)
        ).distinct().all()
        customers = [{'value': c[0], 'label': c[0]} for c in customers_query if c[0]]

        # Get distinct conditions
        conditions_query = db_session.query(Asset.condition).filter(
            Asset.condition.isnot(None)
        ).distinct().all()
        conditions = [{'value': c[0], 'label': c[0]} for c in conditions_query if c[0]]

        return api_response(
            data={
                'statuses': statuses,
                'types': types,
                'manufacturers': manufacturers,
                'customers': customers,
                'conditions': conditions
            },
            message='Filter options retrieved successfully'
        )

    except Exception as e:
        logger.error(f'Error getting filter options: {str(e)}')
        return api_error(
            ErrorCodes.DATABASE_ERROR,
            f'Failed to get filter options: {str(e)}',
            status_code=500
        )
    finally:
        db_session.close()


# =============================================================================
# CREATE ASSET
# =============================================================================

@api_v2_bp.route('/assets', methods=['POST'])
@dual_auth_required
@handle_exceptions
def create_asset():
    """
    Create a new asset

    POST /api/v2/assets
    Headers: Authorization: Bearer <token>
    Body: {
        "asset_tag": "ASSET001",
        "serial_number": "SN12345",
        "name": "MacBook Pro",
        "model": "A2338",
        "manufacturer": "Apple",
        "asset_type": "Laptop",
        "status": "IN_STOCK",
        "country": "Singapore",
        ...
    }

    Returns: {
        "success": true,
        "data": { asset object },
        "message": "Asset created successfully"
    }
    """
    user = request.current_api_user

    # Check permission to create assets
    if not user.permissions or not user.permissions.can_edit_assets:
        return api_error(
            ErrorCodes.INSUFFICIENT_PERMISSIONS,
            'You do not have permission to create assets',
            status_code=403
        )

    # Validate JSON body
    data, error = validate_json_body()
    if error:
        return error

    # Validate required fields - at least asset_tag or serial_number required
    asset_tag = data.get('asset_tag', '').strip()
    serial_number = data.get('serial_number', '').strip()

    if not asset_tag and not serial_number:
        return api_error(
            ErrorCodes.MISSING_REQUIRED_FIELD,
            'Either asset_tag or serial_number is required',
            status_code=400,
            details={'missing_fields': ['asset_tag or serial_number']}
        )

    db_session = db_manager.get_session()
    try:
        # Check for existing asset with same tag or serial
        existing_query = db_session.query(Asset)
        if asset_tag:
            existing = existing_query.filter(Asset.asset_tag == asset_tag).first()
            if existing:
                return api_error(
                    ErrorCodes.RESOURCE_ALREADY_EXISTS,
                    f'Asset with tag {asset_tag} already exists',
                    status_code=409,
                    details={'existing_id': existing.id, 'field': 'asset_tag'}
                )

        if serial_number:
            existing = existing_query.filter(Asset.serial_num == serial_number).first()
            if existing:
                return api_error(
                    ErrorCodes.RESOURCE_ALREADY_EXISTS,
                    f'Asset with serial number {serial_number} already exists',
                    status_code=409,
                    details={'existing_id': existing.id, 'field': 'serial_number'}
                )

        # Parse status
        status_str = data.get('status', 'IN_STOCK')
        try:
            status = AssetStatus[status_str.upper().replace(' ', '_')]
        except (KeyError, AttributeError):
            status = AssetStatus.IN_STOCK

        # Parse receiving date
        receiving_date = None
        if data.get('receiving_date'):
            try:
                receiving_date = datetime.strptime(data['receiving_date'], '%Y-%m-%d')
            except ValueError:
                pass

        # Create new asset
        new_asset = Asset(
            asset_tag=asset_tag or None,
            serial_num=serial_number or None,
            name=data.get('name', '').strip() or None,
            model=data.get('model', '').strip() or None,
            manufacturer=data.get('manufacturer', '').strip() or None,
            category=data.get('category', '').strip() or None,
            asset_type=data.get('asset_type', '').strip() or None,
            status=status,
            condition=data.get('condition', '').strip() or None,
            country=data.get('country', '').strip() or None,
            customer=data.get('customer', '').strip() or None,
            location_id=data.get('location_id'),
            company_id=data.get('company_id'),
            cost_price=data.get('cost_price'),
            hardware_type=data.get('hardware_type', '').strip() or None,
            cpu_type=data.get('cpu_type', '').strip() or None,
            cpu_cores=data.get('cpu_cores', '').strip() if data.get('cpu_cores') else None,
            gpu_cores=data.get('gpu_cores', '').strip() if data.get('gpu_cores') else None,
            memory=data.get('memory', '').strip() or None,
            harddrive=data.get('harddrive', '').strip() or None,
            keyboard=data.get('keyboard', '').strip() or None,
            charger=data.get('charger', '').strip() or None,
            erased=data.get('erased', '').strip() if data.get('erased') else None,
            diag=data.get('diag', '').strip() or None,
            po=data.get('po', '').strip() or None,
            notes=data.get('notes', '').strip() or None,
            tech_notes=data.get('tech_notes', '').strip() or None,
            image_url=data.get('image_url', '').strip() or None,
            legal_hold=data.get('legal_hold', False),
            receiving_date=receiving_date,
            specifications=data.get('specifications', {})
        )

        db_session.add(new_asset)
        db_session.flush()  # Get the ID

        # Create activity log
        activity = Activity(
            user_id=user.id,
            type='asset_created',
            content=f'Created asset via API: {new_asset.asset_tag or new_asset.serial_num} - {new_asset.name or "Unnamed"}',
            reference_id=new_asset.id
        )
        db_session.add(activity)

        # Create history entry
        history = AssetHistory(
            asset_id=new_asset.id,
            user_id=user.id,
            action='CREATE',
            changes={'created': {'old': None, 'new': 'Asset created via API v2'}},
            notes=f'Asset created by {user.username}'
        )
        db_session.add(history)

        db_session.commit()

        logger.info(f"Asset {new_asset.id} created via API by user {user.username}")

        return api_created(
            data=format_asset_response(new_asset),
            message='Asset created successfully'
        )

    except Exception as e:
        db_session.rollback()
        logger.error(f"Error creating asset: {str(e)}")
        raise
    finally:
        db_session.close()


# =============================================================================
# UPDATE ASSET
# =============================================================================

@api_v2_bp.route('/assets/<int:asset_id>', methods=['PUT'])
@dual_auth_required
@handle_exceptions
def update_asset(asset_id):
    """
    Update an existing asset

    PUT /api/v2/assets/<id>
    Headers: Authorization: Bearer <token>
    Body: {
        "name": "Updated Name",
        "status": "DEPLOYED",
        ...
    }

    Returns: {
        "success": true,
        "data": { updated asset object },
        "message": "Asset updated successfully"
    }
    """
    user = request.current_api_user

    # Check permission to edit assets
    if not user.permissions or not user.permissions.can_edit_assets:
        return api_error(
            ErrorCodes.INSUFFICIENT_PERMISSIONS,
            'You do not have permission to edit assets',
            status_code=403
        )

    # Validate JSON body
    data, error = validate_json_body()
    if error:
        return error

    db_session = db_manager.get_session()
    try:
        # Find the asset
        asset = db_session.query(Asset).filter(Asset.id == asset_id).first()

        if not asset:
            return api_error(
                ErrorCodes.RESOURCE_NOT_FOUND,
                f'Asset with ID {asset_id} not found',
                status_code=404
            )

        # For COUNTRY_ADMIN, check if asset is in their assigned countries
        if user.user_type == UserType.COUNTRY_ADMIN and user.assigned_countries:
            if asset.country and asset.country not in user.assigned_countries:
                return api_error(
                    ErrorCodes.INSUFFICIENT_PERMISSIONS,
                    'You do not have permission to edit assets in this country',
                    status_code=403
                )

        # Track changes
        changes = {}

        # Define updatable fields
        updatable_fields = [
            ('asset_tag', 'asset_tag'),
            ('serial_number', 'serial_num'),
            ('name', 'name'),
            ('model', 'model'),
            ('manufacturer', 'manufacturer'),
            ('category', 'category'),
            ('asset_type', 'asset_type'),
            ('condition', 'condition'),
            ('country', 'country'),
            ('customer', 'customer'),
            ('location_id', 'location_id'),
            ('company_id', 'company_id'),
            ('cost_price', 'cost_price'),
            ('hardware_type', 'hardware_type'),
            ('cpu_type', 'cpu_type'),
            ('cpu_cores', 'cpu_cores'),
            ('gpu_cores', 'gpu_cores'),
            ('memory', 'memory'),
            ('harddrive', 'harddrive'),
            ('keyboard', 'keyboard'),
            ('charger', 'charger'),
            ('erased', 'erased'),
            ('diag', 'diag'),
            ('po', 'po'),
            ('notes', 'notes'),
            ('tech_notes', 'tech_notes'),
            ('image_url', 'image_url'),
            ('legal_hold', 'legal_hold'),
            ('specifications', 'specifications'),
        ]

        for json_field, model_field in updatable_fields:
            if json_field in data:
                old_value = getattr(asset, model_field)
                new_value = data[json_field]

                # Handle string fields
                if isinstance(new_value, str):
                    new_value = new_value.strip() or None

                if old_value != new_value:
                    changes[model_field] = {'old': old_value, 'new': new_value}
                    setattr(asset, model_field, new_value)

        # Handle status separately (enum)
        if 'status' in data:
            try:
                new_status = AssetStatus[data['status'].upper().replace(' ', '_')]
                if asset.status != new_status:
                    changes['status'] = {
                        'old': asset.status.value if asset.status else None,
                        'new': new_status.value
                    }
                    asset.status = new_status
            except (KeyError, AttributeError):
                return api_error(
                    ErrorCodes.INVALID_FIELD_VALUE,
                    f'Invalid status value: {data["status"]}',
                    status_code=400,
                    details={'valid_values': [s.name for s in AssetStatus]}
                )

        # Handle receiving_date
        if 'receiving_date' in data:
            try:
                new_date = datetime.strptime(data['receiving_date'], '%Y-%m-%d') if data['receiving_date'] else None
                if asset.receiving_date != new_date:
                    changes['receiving_date'] = {
                        'old': asset.receiving_date.isoformat() if asset.receiving_date else None,
                        'new': new_date.isoformat() if new_date else None
                    }
                    asset.receiving_date = new_date
            except ValueError:
                return api_error(
                    ErrorCodes.INVALID_FIELD_VALUE,
                    'Invalid date format. Use YYYY-MM-DD',
                    status_code=400
                )

        # Check for duplicate asset_tag or serial_num
        if 'asset_tag' in data and data['asset_tag']:
            existing = db_session.query(Asset).filter(
                Asset.asset_tag == data['asset_tag'],
                Asset.id != asset_id
            ).first()
            if existing:
                return api_error(
                    ErrorCodes.RESOURCE_ALREADY_EXISTS,
                    f'Asset tag {data["asset_tag"]} is already in use',
                    status_code=409
                )

        if 'serial_number' in data and data['serial_number']:
            existing = db_session.query(Asset).filter(
                Asset.serial_num == data['serial_number'],
                Asset.id != asset_id
            ).first()
            if existing:
                return api_error(
                    ErrorCodes.RESOURCE_ALREADY_EXISTS,
                    f'Serial number {data["serial_number"]} is already in use',
                    status_code=409
                )

        # Only save if there are changes
        if changes:
            asset.updated_at = datetime.utcnow()

            # Create history entry
            history = asset.track_change(
                user_id=user.id,
                action='UPDATE',
                changes=changes,
                notes=f'Updated via API v2 by {user.username}'
            )
            db_session.add(history)

            # Create activity log
            activity = Activity(
                user_id=user.id,
                type='asset_updated',
                content=f'Updated asset via API: {asset.asset_tag or asset.serial_num}',
                reference_id=asset.id
            )
            db_session.add(activity)

            db_session.commit()
            logger.info(f"Asset {asset_id} updated via API by user {user.username}")

        return api_response(
            data=format_asset_response(asset),
            message='Asset updated successfully' if changes else 'No changes made'
        )

    except Exception as e:
        db_session.rollback()
        logger.error(f"Error updating asset {asset_id}: {str(e)}")
        raise
    finally:
        db_session.close()


# =============================================================================
# DELETE/ARCHIVE ASSET
# =============================================================================

@api_v2_bp.route('/assets/<int:asset_id>', methods=['DELETE'])
@dual_auth_required
@handle_exceptions
def delete_asset(asset_id):
    """
    Delete or archive an asset

    DELETE /api/v2/assets/<id>?mode=archive|delete
    Headers: Authorization: Bearer <token>

    Query params:
        mode: 'archive' (default) or 'delete'
              - archive: Sets status to ARCHIVED
              - delete: Permanently removes the asset (admin only)

    Returns:
        204 No Content on success
    """
    user = request.current_api_user
    mode = request.args.get('mode', 'archive').lower()

    # Check permission
    if not user.permissions or not user.permissions.can_edit_assets:
        return api_error(
            ErrorCodes.INSUFFICIENT_PERMISSIONS,
            'You do not have permission to delete assets',
            status_code=403
        )

    # Permanent delete requires admin
    if mode == 'delete' and user.user_type not in [UserType.SUPER_ADMIN, UserType.DEVELOPER]:
        return api_error(
            ErrorCodes.INSUFFICIENT_PERMISSIONS,
            'Permanent deletion requires admin privileges. Use mode=archive instead.',
            status_code=403
        )

    db_session = db_manager.get_session()
    try:
        # Find the asset
        asset = db_session.query(Asset).filter(Asset.id == asset_id).first()

        if not asset:
            return api_error(
                ErrorCodes.RESOURCE_NOT_FOUND,
                f'Asset with ID {asset_id} not found',
                status_code=404
            )

        # For COUNTRY_ADMIN, check if asset is in their assigned countries
        if user.user_type == UserType.COUNTRY_ADMIN and user.assigned_countries:
            if asset.country and asset.country not in user.assigned_countries:
                return api_error(
                    ErrorCodes.INSUFFICIENT_PERMISSIONS,
                    'You do not have permission to delete assets in this country',
                    status_code=403
                )

        # Check if asset is on legal hold
        if asset.legal_hold:
            return api_error(
                ErrorCodes.RESOURCE_IN_USE,
                'This asset is on legal hold and cannot be deleted',
                status_code=409
            )

        asset_info = {
            'id': asset.id,
            'asset_tag': asset.asset_tag,
            'serial_num': asset.serial_num,
            'name': asset.name
        }

        if mode == 'delete':
            # Permanent delete - remove history first
            db_session.query(AssetHistory).filter(AssetHistory.asset_id == asset_id).delete()
            db_session.delete(asset)

            activity = Activity(
                user_id=user.id,
                type='asset_deleted',
                content=f'Permanently deleted asset via API: {asset_info["asset_tag"] or asset_info["serial_num"]} - {asset_info["name"]}',
                reference_id=0
            )
        else:
            # Archive - just change status
            old_status = asset.status
            asset.status = AssetStatus.ARCHIVED
            asset.updated_at = datetime.utcnow()

            # Create history entry
            history = asset.track_change(
                user_id=user.id,
                action='ARCHIVE',
                changes={'status': {'old': old_status.value if old_status else None, 'new': 'Archived'}},
                notes=f'Archived via API v2 by {user.username}'
            )
            db_session.add(history)

            activity = Activity(
                user_id=user.id,
                type='asset_archived',
                content=f'Archived asset via API: {asset_info["asset_tag"] or asset_info["serial_num"]} - {asset_info["name"]}',
                reference_id=asset.id
            )

        db_session.add(activity)
        db_session.commit()

        logger.info(f"Asset {asset_id} {'deleted' if mode == 'delete' else 'archived'} via API by user {user.username}")

        return api_no_content()

    except Exception as e:
        db_session.rollback()
        logger.error(f"Error deleting asset {asset_id}: {str(e)}")
        raise
    finally:
        db_session.close()


# =============================================================================
# UPLOAD ASSET IMAGE
# =============================================================================

@api_v2_bp.route('/assets/<int:asset_id>/image', methods=['POST'])
@dual_auth_required
@handle_exceptions
def upload_asset_image(asset_id):
    """
    Upload or update an asset's image

    POST /api/v2/assets/<id>/image
    Headers:
        Authorization: Bearer <token>
        Content-Type: multipart/form-data
    Body: Form data with 'image' file field

    OR provide URL in JSON:
    Body: { "image_url": "https://..." }

    Returns: {
        "success": true,
        "data": {
            "image_url": "/static/uploads/assets/..."
        },
        "message": "Image uploaded successfully"
    }
    """
    user = request.current_api_user

    # Check permission
    if not user.permissions or not user.permissions.can_edit_assets:
        return api_error(
            ErrorCodes.INSUFFICIENT_PERMISSIONS,
            'You do not have permission to edit assets',
            status_code=403
        )

    db_session = db_manager.get_session()
    try:
        # Find the asset
        asset = db_session.query(Asset).filter(Asset.id == asset_id).first()

        if not asset:
            return api_error(
                ErrorCodes.RESOURCE_NOT_FOUND,
                f'Asset with ID {asset_id} not found',
                status_code=404
            )

        # For COUNTRY_ADMIN, check if asset is in their assigned countries
        if user.user_type == UserType.COUNTRY_ADMIN and user.assigned_countries:
            if asset.country and asset.country not in user.assigned_countries:
                return api_error(
                    ErrorCodes.INSUFFICIENT_PERMISSIONS,
                    'You do not have permission to edit assets in this country',
                    status_code=403
                )

        old_image_url = asset.image_url
        new_image_url = None

        # Check if JSON body with image_url
        if request.is_json:
            data = request.get_json()
            image_url = data.get('image_url', '').strip()
            new_image_url = image_url if image_url else None

        # Check if file upload
        elif 'image' in request.files:
            file = request.files['image']

            if file.filename == '':
                return api_error(
                    ErrorCodes.VALIDATION_ERROR,
                    'No file selected',
                    status_code=400
                )

            if not allowed_image_file(file.filename):
                return api_error(
                    ErrorCodes.VALIDATION_ERROR,
                    f'Invalid file type. Allowed: {", ".join(ALLOWED_IMAGE_EXTENSIONS)}',
                    status_code=400
                )

            # Check file size
            file.seek(0, os.SEEK_END)
            size = file.tell()
            file.seek(0)

            if size > MAX_IMAGE_SIZE:
                return api_error(
                    ErrorCodes.VALIDATION_ERROR,
                    f'File too large. Maximum size: {MAX_IMAGE_SIZE // (1024*1024)}MB',
                    status_code=400
                )

            # Ensure upload directory exists
            os.makedirs(UPLOAD_FOLDER, exist_ok=True)

            # Generate unique filename
            from werkzeug.utils import secure_filename
            ext = file.filename.rsplit('.', 1)[1].lower()
            filename = f"asset_{asset_id}_{uuid.uuid4().hex[:8]}.{ext}"
            filepath = os.path.join(UPLOAD_FOLDER, filename)

            # Save file
            file.save(filepath)

            # Set URL path
            new_image_url = f'/static/uploads/assets/{filename}'

        else:
            return api_error(
                ErrorCodes.VALIDATION_ERROR,
                'No image provided. Send either a file (form-data) or JSON with image_url',
                status_code=400
            )

        # Update asset
        asset.image_url = new_image_url
        asset.updated_at = datetime.utcnow()

        # Create history entry
        history = asset.track_change(
            user_id=user.id,
            action='IMAGE_UPDATE',
            changes={'image_url': {'old': old_image_url, 'new': new_image_url}},
            notes=f'Image updated via API v2 by {user.username}'
        )
        db_session.add(history)

        # Create activity log
        activity = Activity(
            user_id=user.id,
            type='asset_image_updated',
            content=f'Updated image for asset: {asset.asset_tag or asset.serial_num}',
            reference_id=asset.id
        )
        db_session.add(activity)

        db_session.commit()

        logger.info(f"Asset {asset_id} image updated via API by user {user.username}")

        return api_response(
            data={'image_url': new_image_url},
            message='Image uploaded successfully'
        )

    except Exception as e:
        db_session.rollback()
        logger.error(f"Error uploading image for asset {asset_id}: {str(e)}")
        raise
    finally:
        db_session.close()


# =============================================================================
# TRANSFER ASSET TO DIFFERENT CUSTOMER
# =============================================================================

@api_v2_bp.route('/assets/<int:asset_id>/transfer', methods=['POST'])
@dual_auth_required
@handle_exceptions
def transfer_asset(asset_id):
    """
    Transfer an asset to a different customer.

    POST /api/v2/assets/<id>/transfer
    Headers: Authorization: Bearer <token>
    Body: {
        "customer_id": 5,
        "reason": "Employee transfer",
        "notes": "Optional notes about the transfer",
        "effective_date": "2024-01-15"
    }

    Returns: {
        "success": true,
        "data": {
            "id": 10,
            "asset_tag": "TL-0001",
            "previous_customer": { "id": 3, "name": "John Doe" },
            "new_customer": { "id": 5, "name": "Jane Smith" },
            "transferred_at": "ISO8601",
            "transferred_by": { "id": 1, "username": "admin" }
        },
        "message": "Asset transferred successfully"
    }
    """
    from models.customer_user import CustomerUser

    user = request.current_api_user

    # Check permission to edit assets
    if not user.permissions or not user.permissions.can_edit_assets:
        return api_error(
            ErrorCodes.INSUFFICIENT_PERMISSIONS,
            'You do not have permission to transfer assets',
            status_code=403
        )

    # Validate JSON body
    data, error = validate_json_body()
    if error:
        return error

    # Validate required field: customer_id
    is_valid, error = validate_required_fields(data, ['customer_id'])
    if not is_valid:
        return error

    new_customer_id = data.get('customer_id')
    reason = data.get('reason', '').strip() or 'Asset transfer via API'
    notes = data.get('notes', '').strip() or None
    effective_date_str = data.get('effective_date')

    # Parse effective date if provided
    effective_date = None
    if effective_date_str:
        try:
            effective_date = datetime.strptime(effective_date_str, '%Y-%m-%d')
        except ValueError:
            return api_error(
                ErrorCodes.INVALID_FIELD_VALUE,
                'Invalid date format for effective_date. Use YYYY-MM-DD',
                status_code=400
            )

    db_session = db_manager.get_session()
    try:
        # Find the asset
        asset = db_session.query(Asset).filter(Asset.id == asset_id).first()

        if not asset:
            return api_error(
                ErrorCodes.RESOURCE_NOT_FOUND,
                f'Asset with ID {asset_id} not found',
                status_code=404
            )

        # For COUNTRY_ADMIN, check if asset is in their assigned countries
        if user.user_type == UserType.COUNTRY_ADMIN and user.assigned_countries:
            if asset.country and asset.country not in user.assigned_countries:
                return api_error(
                    ErrorCodes.INSUFFICIENT_PERMISSIONS,
                    'You do not have permission to transfer assets in this country',
                    status_code=403
                )

        # Find the new customer
        new_customer = db_session.query(CustomerUser).filter(CustomerUser.id == new_customer_id).first()
        if not new_customer:
            return api_error(
                ErrorCodes.RESOURCE_NOT_FOUND,
                f'Customer with ID {new_customer_id} not found',
                status_code=404
            )

        # Get previous customer information
        previous_customer_info = None
        previous_customer_name = asset.customer
        if previous_customer_name:
            # Try to find the customer by name
            prev_customer = db_session.query(CustomerUser).filter(
                CustomerUser.name == previous_customer_name
            ).first()
            if prev_customer:
                previous_customer_info = {
                    'id': prev_customer.id,
                    'name': prev_customer.name
                }
            else:
                previous_customer_info = {
                    'id': None,
                    'name': previous_customer_name
                }

        # Check if asset is on legal hold
        if asset.legal_hold:
            return api_error(
                ErrorCodes.RESOURCE_IN_USE,
                'This asset is on legal hold and cannot be transferred',
                status_code=409
            )

        # Store old values for tracking
        old_customer = asset.customer
        old_status = asset.status

        # Update the asset
        asset.customer = new_customer.name
        asset.status = AssetStatus.DEPLOYED
        asset.updated_at = datetime.utcnow()

        transfer_time = effective_date if effective_date else datetime.utcnow()

        # Track changes
        changes = {
            'customer': {'old': old_customer, 'new': new_customer.name},
            'transfer_reason': {'old': None, 'new': reason}
        }
        if old_status != AssetStatus.DEPLOYED:
            changes['status'] = {
                'old': old_status.value if old_status else None,
                'new': AssetStatus.DEPLOYED.value
            }

        # Create history entry
        history = AssetHistory(
            asset_id=asset.id,
            user_id=user.id,
            action='TRANSFER',
            changes=changes,
            notes=f'Transferred via API v2. Reason: {reason}' + (f'. Notes: {notes}' if notes else '')
        )
        db_session.add(history)

        # Create activity log
        activity = Activity(
            user_id=user.id,
            type='asset_transferred',
            content=f'Transferred asset {asset.asset_tag or asset.serial_num} from "{old_customer or "unassigned"}" to "{new_customer.name}" via API. Reason: {reason}',
            reference_id=asset.id
        )
        db_session.add(activity)

        db_session.commit()

        logger.info(f"Asset {asset_id} transferred from '{old_customer}' to '{new_customer.name}' via API by user {user.username}")

        # Build response
        response_data = {
            'id': asset.id,
            'asset_tag': asset.asset_tag,
            'previous_customer': previous_customer_info,
            'new_customer': {
                'id': new_customer.id,
                'name': new_customer.name
            },
            'transferred_at': transfer_time.isoformat() + 'Z',
            'transferred_by': {
                'id': user.id,
                'username': user.username
            }
        }

        return api_response(
            data=response_data,
            message='Asset transferred successfully'
        )

    except Exception as e:
        db_session.rollback()
        logger.error(f"Error transferring asset {asset_id}: {str(e)}")
        raise
    finally:
        db_session.close()
