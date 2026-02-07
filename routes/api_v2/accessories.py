"""
API v2 Accessory Endpoints

This module provides CRUD operations for accessories via the v2 API.

Endpoints:
- POST /api/v2/accessories - Create new accessory
- PUT /api/v2/accessories/<id> - Update accessory
- DELETE /api/v2/accessories/<id> - Delete accessory
- POST /api/v2/accessories/<id>/return - Return checked-out accessory
- POST /api/v2/accessories/<id>/checkin - Check-in accessory from a specific customer
"""

from flask import request
from datetime import datetime
import logging

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
    ErrorCodes
)

from models.accessory import Accessory
from models.accessory_history import AccessoryHistory
from models.accessory_transaction import AccessoryTransaction
from models.activity import Activity
from models.user import UserType
from utils.db_manager import DatabaseManager

logger = logging.getLogger(__name__)
db_manager = DatabaseManager()


def format_accessory_response(accessory):
    """Format accessory object for API response"""
    return {
        'id': accessory.id,
        'name': accessory.name,
        'category': accessory.category,
        'manufacturer': accessory.manufacturer,
        'model_no': accessory.model_no,
        'total_quantity': accessory.total_quantity,
        'available_quantity': accessory.available_quantity,
        'checked_out_quantity': (accessory.total_quantity or 0) - (accessory.available_quantity or 0),
        'country': accessory.country,
        'status': accessory.status,
        'notes': accessory.notes,
        'image_url': accessory.image_url,
        'customer_id': accessory.customer_id,
        'company_id': accessory.company_id,
        'checkout_date': accessory.checkout_date.isoformat() if accessory.checkout_date else None,
        'return_date': accessory.return_date.isoformat() if accessory.return_date else None,
        'created_at': accessory.created_at.isoformat() if accessory.created_at else None,
        'updated_at': accessory.updated_at.isoformat() if accessory.updated_at else None,
    }


# =============================================================================
# LIST ACCESSORIES
# =============================================================================

@api_v2_bp.route('/accessories', methods=['GET'])
@dual_auth_required
@handle_exceptions
def list_accessories():
    """
    List accessories with pagination and filtering

    GET /api/v2/accessories

    Query Parameters:
        - page: Page number (default: 1)
        - per_page: Items per page (default: 25, max: 100)
        - search: Search by name, category, manufacturer
        - category: Filter by category
        - manufacturer: Filter by manufacturer
        - status: Filter by status
        - sort_by: Sort field (default: created_at)
        - sort_order: asc or desc (default: desc)

    Returns:
        Paginated list of accessories
    """
    from .utils import paginate_query, get_pagination_params

    db_session = db_manager.get_session()
    try:
        # Get pagination params
        page, per_page = get_pagination_params()

        # Get sorting params
        sort_by = request.args.get('sort_by', 'created_at')
        sort_order = request.args.get('sort_order', 'desc')

        # Build query
        query = db_session.query(Accessory)

        # Apply search filter
        search = request.args.get('search', '').strip()
        if search:
            search_term = f'%{search}%'
            query = query.filter(
                (Accessory.name.ilike(search_term)) |
                (Accessory.category.ilike(search_term)) |
                (Accessory.manufacturer.ilike(search_term))
            )

        # Apply category filter
        category = request.args.get('category')
        if category and category != 'all':
            query = query.filter(Accessory.category == category)

        # Apply manufacturer filter
        manufacturer = request.args.get('manufacturer')
        if manufacturer and manufacturer != 'all':
            query = query.filter(Accessory.manufacturer.ilike(f'%{manufacturer}%'))

        # Apply status filter
        status = request.args.get('status')
        if status and status != 'all':
            query = query.filter(Accessory.status == status)

        # Apply sorting
        sort_column = getattr(Accessory, sort_by, Accessory.created_at)
        if sort_order == 'asc':
            query = query.order_by(sort_column.asc())
        else:
            query = query.order_by(sort_column.desc())

        # Paginate
        accessories, pagination_meta = paginate_query(query, page, per_page)

        # Format response
        accessories_data = [format_accessory_response(acc) for acc in accessories]

        return api_response(
            data=accessories_data,
            meta=pagination_meta,
            message=f'Retrieved {len(accessories_data)} accessories'
        )

    except Exception as e:
        logger.error(f'Error listing accessories: {str(e)}')
        return api_error(
            ErrorCodes.DATABASE_ERROR,
            f'Failed to list accessories: {str(e)}',
            status_code=500
        )
    finally:
        db_session.close()


# =============================================================================
# GET SINGLE ACCESSORY
# =============================================================================

@api_v2_bp.route('/accessories/<int:accessory_id>', methods=['GET'])
@dual_auth_required
@handle_exceptions
def get_accessory(accessory_id):
    """
    Get a single accessory by ID

    GET /api/v2/accessories/<id>

    Returns:
        Accessory details
    """
    db_session = db_manager.get_session()
    try:
        accessory = db_session.query(Accessory).filter(Accessory.id == accessory_id).first()

        if not accessory:
            return api_error(
                ErrorCodes.RESOURCE_NOT_FOUND,
                f'Accessory with ID {accessory_id} not found',
                status_code=404
            )

        return api_response(
            data=format_accessory_response(accessory),
            message='Accessory retrieved successfully'
        )

    except Exception as e:
        logger.error(f'Error getting accessory: {str(e)}')
        return api_error(
            ErrorCodes.DATABASE_ERROR,
            f'Failed to get accessory: {str(e)}',
            status_code=500
        )
    finally:
        db_session.close()


# =============================================================================
# ACCESSORY FILTER OPTIONS
# =============================================================================

@api_v2_bp.route('/accessories/filter-options', methods=['GET'])
@dual_auth_required
@handle_exceptions
def get_accessory_filter_options():
    """
    Get filter options for accessories

    GET /api/v2/accessories/filter-options

    Returns:
        Available filter options for categories, manufacturers, etc.
    """
    db_session = db_manager.get_session()
    try:
        # Get distinct categories
        categories_query = db_session.query(Accessory.category).filter(
            Accessory.category.isnot(None)
        ).distinct().all()
        categories = [{'value': c[0], 'label': c[0]} for c in categories_query if c[0]]

        # Get distinct manufacturers
        manufacturers_query = db_session.query(Accessory.manufacturer).filter(
            Accessory.manufacturer.isnot(None)
        ).distinct().all()
        manufacturers = [{'value': m[0], 'label': m[0]} for m in manufacturers_query if m[0]]

        # Get distinct countries
        countries_query = db_session.query(Accessory.country).filter(
            Accessory.country.isnot(None)
        ).distinct().all()
        countries = [{'value': c[0], 'label': c[0]} for c in countries_query if c[0]]

        return api_response(
            data={
                'categories': categories,
                'manufacturers': manufacturers,
                'countries': countries
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
# CREATE ACCESSORY
# =============================================================================

@api_v2_bp.route('/accessories', methods=['POST'])
@dual_auth_required
@handle_exceptions
def create_accessory():
    """
    Create a new accessory

    POST /api/v2/accessories
    Headers: Authorization: Bearer <token>
    Body: {
        "name": "Wireless Mouse",
        "category": "Computer Accessories",
        "manufacturer": "Logitech",
        "model_no": "MX Master 3",
        "total_quantity": 50,
        "country": "Singapore",
        "notes": "Ergonomic wireless mouse",
        "aliases": ["MX Master", "Logitech MX"]
    }

    Returns: {
        "success": true,
        "data": { accessory object },
        "message": "Accessory created successfully"
    }
    """
    user = request.current_api_user

    # Check permission to create accessories (using asset permission)
    if not user.permissions or not user.permissions.can_edit_assets:
        return api_error(
            ErrorCodes.INSUFFICIENT_PERMISSIONS,
            'You do not have permission to create accessories',
            status_code=403
        )

    # Validate JSON body
    data, error = validate_json_body()
    if error:
        return error

    # Validate required fields
    is_valid, error = validate_required_fields(data, ['name', 'category'])
    if not is_valid:
        return error

    db_session = db_manager.get_session()
    try:
        # Parse quantity
        total_quantity = data.get('total_quantity', 0)
        try:
            total_quantity = int(total_quantity)
            if total_quantity < 0:
                total_quantity = 0
        except (ValueError, TypeError):
            total_quantity = 0

        # Create new accessory
        new_accessory = Accessory(
            name=data['name'].strip(),
            category=data['category'].strip(),
            manufacturer=data.get('manufacturer', '').strip() or None,
            model_no=data.get('model_no', '').strip() or None,
            total_quantity=total_quantity,
            available_quantity=total_quantity,  # Initially all available
            country=data.get('country', '').strip() or None,
            status='Available',
            notes=data.get('notes', '').strip() or None,
            image_url=data.get('image_url', '').strip() or None,
            company_id=data.get('company_id')
        )

        db_session.add(new_accessory)
        db_session.flush()  # Get the ID

        # Handle aliases if provided
        aliases = data.get('aliases', [])
        if aliases:
            from models.accessory_alias import AccessoryAlias
            for alias_name in aliases:
                if alias_name and alias_name.strip():
                    alias = AccessoryAlias(
                        accessory_id=new_accessory.id,
                        alias_name=alias_name.strip()
                    )
                    db_session.add(alias)

        # Create activity log
        activity = Activity(
            user_id=user.id,
            type='accessory_created',
            content=f'Created accessory via API: {new_accessory.name} (Quantity: {new_accessory.total_quantity})',
            reference_id=new_accessory.id
        )
        db_session.add(activity)

        # Create history entry
        history = AccessoryHistory(
            accessory_id=new_accessory.id,
            user_id=user.id,
            action='CREATE',
            changes={'created': {'old': None, 'new': 'Accessory created via API v2'}},
            notes=f'Accessory created by {user.username}'
        )
        db_session.add(history)

        db_session.commit()

        logger.info(f"Accessory {new_accessory.id} created via API by user {user.username}")

        return api_created(
            data=format_accessory_response(new_accessory),
            message='Accessory created successfully'
        )

    except Exception as e:
        db_session.rollback()
        logger.error(f"Error creating accessory: {str(e)}")
        raise
    finally:
        db_session.close()


# =============================================================================
# UPDATE ACCESSORY
# =============================================================================

@api_v2_bp.route('/accessories/<int:accessory_id>', methods=['PUT'])
@dual_auth_required
@handle_exceptions
def update_accessory(accessory_id):
    """
    Update an existing accessory

    PUT /api/v2/accessories/<id>
    Headers: Authorization: Bearer <token>
    Body: {
        "name": "Updated Name",
        "total_quantity": 60,
        ...
    }

    Returns: {
        "success": true,
        "data": { updated accessory object },
        "message": "Accessory updated successfully"
    }
    """
    user = request.current_api_user

    # Check permission to edit accessories
    if not user.permissions or not user.permissions.can_edit_assets:
        return api_error(
            ErrorCodes.INSUFFICIENT_PERMISSIONS,
            'You do not have permission to edit accessories',
            status_code=403
        )

    # Validate JSON body
    data, error = validate_json_body()
    if error:
        return error

    db_session = db_manager.get_session()
    try:
        # Find the accessory
        accessory = db_session.query(Accessory).filter(Accessory.id == accessory_id).first()

        if not accessory:
            return api_error(
                ErrorCodes.RESOURCE_NOT_FOUND,
                f'Accessory with ID {accessory_id} not found',
                status_code=404
            )

        # For COUNTRY_ADMIN, check if accessory is in their assigned countries
        if user.user_type == UserType.COUNTRY_ADMIN and user.assigned_countries:
            if accessory.country and accessory.country not in user.assigned_countries:
                return api_error(
                    ErrorCodes.INSUFFICIENT_PERMISSIONS,
                    'You do not have permission to edit accessories in this country',
                    status_code=403
                )

        # Track changes
        changes = {}

        # Define updatable fields
        updatable_fields = [
            'name', 'category', 'manufacturer', 'model_no',
            'country', 'notes', 'image_url', 'company_id'
        ]

        for field in updatable_fields:
            if field in data:
                old_value = getattr(accessory, field)
                new_value = data[field]

                # Handle string fields
                if isinstance(new_value, str):
                    new_value = new_value.strip() or None

                if old_value != new_value:
                    changes[field] = {'old': old_value, 'new': new_value}
                    setattr(accessory, field, new_value)

        # Handle quantity update specially (need to adjust available_quantity)
        if 'total_quantity' in data:
            try:
                new_total = int(data['total_quantity'])
                if new_total < 0:
                    return api_error(
                        ErrorCodes.INVALID_FIELD_VALUE,
                        'total_quantity cannot be negative',
                        status_code=400
                    )

                old_total = accessory.total_quantity or 0
                if new_total != old_total:
                    # Calculate the difference
                    diff = new_total - old_total

                    # Update total quantity
                    changes['total_quantity'] = {'old': old_total, 'new': new_total}
                    accessory.total_quantity = new_total

                    # Adjust available quantity by the same difference
                    old_available = accessory.available_quantity or 0
                    new_available = max(0, old_available + diff)
                    # Ensure available doesn't exceed total
                    new_available = min(new_available, new_total)

                    if old_available != new_available:
                        changes['available_quantity'] = {'old': old_available, 'new': new_available}
                        accessory.available_quantity = new_available

            except (ValueError, TypeError):
                return api_error(
                    ErrorCodes.INVALID_FIELD_VALUE,
                    'Invalid total_quantity value',
                    status_code=400
                )

        # Handle status update
        if 'status' in data:
            new_status = data['status'].strip() if data['status'] else 'Available'
            if accessory.status != new_status:
                changes['status'] = {'old': accessory.status, 'new': new_status}
                accessory.status = new_status

        # Handle aliases update
        if 'aliases' in data:
            from models.accessory_alias import AccessoryAlias

            # Get current aliases
            current_aliases = [a.alias_name for a in accessory.aliases] if accessory.aliases else []
            new_aliases = [a.strip() for a in data['aliases'] if a and a.strip()]

            if set(current_aliases) != set(new_aliases):
                changes['aliases'] = {'old': current_aliases, 'new': new_aliases}

                # Delete existing aliases
                for alias in accessory.aliases:
                    db_session.delete(alias)

                # Add new aliases
                for alias_name in new_aliases:
                    alias = AccessoryAlias(
                        accessory_id=accessory.id,
                        alias_name=alias_name
                    )
                    db_session.add(alias)

        # Only save if there are changes
        if changes:
            accessory.updated_at = datetime.utcnow()

            # Create history entry
            history = accessory.track_change(
                user_id=user.id,
                action='UPDATE',
                changes=changes,
                notes=f'Updated via API v2 by {user.username}'
            )
            db_session.add(history)

            # Create activity log
            activity = Activity(
                user_id=user.id,
                type='accessory_updated',
                content=f'Updated accessory via API: {accessory.name}',
                reference_id=accessory.id
            )
            db_session.add(activity)

            db_session.commit()
            logger.info(f"Accessory {accessory_id} updated via API by user {user.username}")

        return api_response(
            data=format_accessory_response(accessory),
            message='Accessory updated successfully' if changes else 'No changes made'
        )

    except Exception as e:
        db_session.rollback()
        logger.error(f"Error updating accessory {accessory_id}: {str(e)}")
        raise
    finally:
        db_session.close()


# =============================================================================
# DELETE ACCESSORY
# =============================================================================

@api_v2_bp.route('/accessories/<int:accessory_id>', methods=['DELETE'])
@dual_auth_required
@handle_exceptions
def delete_accessory(accessory_id):
    """
    Delete an accessory

    DELETE /api/v2/accessories/<id>
    Headers: Authorization: Bearer <token>

    Note: Will fail if accessory has items checked out (available_quantity < total_quantity)

    Returns:
        204 No Content on success
    """
    user = request.current_api_user

    # Check permission - require admin for deletion
    if user.user_type not in [UserType.SUPER_ADMIN, UserType.DEVELOPER, UserType.COUNTRY_ADMIN]:
        return api_error(
            ErrorCodes.INSUFFICIENT_PERMISSIONS,
            'Admin privileges required to delete accessories',
            status_code=403
        )

    db_session = db_manager.get_session()
    try:
        # Find the accessory
        accessory = db_session.query(Accessory).filter(Accessory.id == accessory_id).first()

        if not accessory:
            return api_error(
                ErrorCodes.RESOURCE_NOT_FOUND,
                f'Accessory with ID {accessory_id} not found',
                status_code=404
            )

        # For COUNTRY_ADMIN, check if accessory is in their assigned countries
        if user.user_type == UserType.COUNTRY_ADMIN and user.assigned_countries:
            if accessory.country and accessory.country not in user.assigned_countries:
                return api_error(
                    ErrorCodes.INSUFFICIENT_PERMISSIONS,
                    'You do not have permission to delete accessories in this country',
                    status_code=403
                )

        # Check if items are checked out
        checked_out = (accessory.total_quantity or 0) - (accessory.available_quantity or 0)
        if checked_out > 0:
            return api_error(
                ErrorCodes.RESOURCE_IN_USE,
                f'Cannot delete accessory: {checked_out} item(s) are currently checked out',
                status_code=409,
                details={'checked_out_quantity': checked_out}
            )

        accessory_info = {
            'id': accessory.id,
            'name': accessory.name,
            'category': accessory.category
        }

        # Delete history first
        db_session.query(AccessoryHistory).filter(AccessoryHistory.accessory_id == accessory_id).delete()

        # Delete transactions
        db_session.query(AccessoryTransaction).filter(AccessoryTransaction.accessory_id == accessory_id).delete()

        # Delete aliases
        from models.accessory_alias import AccessoryAlias
        db_session.query(AccessoryAlias).filter(AccessoryAlias.accessory_id == accessory_id).delete()

        # Delete the accessory
        db_session.delete(accessory)

        # Create activity log
        activity = Activity(
            user_id=user.id,
            type='accessory_deleted',
            content=f'Deleted accessory via API: {accessory_info["name"]} ({accessory_info["category"]})',
            reference_id=0
        )
        db_session.add(activity)

        db_session.commit()

        logger.info(f"Accessory {accessory_id} deleted via API by user {user.username}")

        return api_no_content()

    except Exception as e:
        db_session.rollback()
        logger.error(f"Error deleting accessory {accessory_id}: {str(e)}")
        raise
    finally:
        db_session.close()


# =============================================================================
# RETURN CHECKED-OUT ACCESSORY
# =============================================================================

@api_v2_bp.route('/accessories/<int:accessory_id>/return', methods=['POST'])
@dual_auth_required
@handle_exceptions
def return_accessory(accessory_id):
    """
    Return a checked-out accessory to inventory

    POST /api/v2/accessories/<id>/return
    Headers: Authorization: Bearer <token>
    Body: {
        "quantity": 1,           // Optional, default 1
        "customer_id": 123,      // Optional, specifies which customer is returning
        "notes": "Good condition"  // Optional
    }

    Returns: {
        "success": true,
        "data": { updated accessory object },
        "message": "Accessory returned successfully"
    }
    """
    user = request.current_api_user

    # Check permission
    if not user.permissions or not user.permissions.can_edit_assets:
        return api_error(
            ErrorCodes.INSUFFICIENT_PERMISSIONS,
            'You do not have permission to process returns',
            status_code=403
        )

    # Get JSON body (optional)
    data = {}
    if request.is_json:
        data = request.get_json() or {}

    db_session = db_manager.get_session()
    try:
        # Find the accessory
        accessory = db_session.query(Accessory).filter(Accessory.id == accessory_id).first()

        if not accessory:
            return api_error(
                ErrorCodes.RESOURCE_NOT_FOUND,
                f'Accessory with ID {accessory_id} not found',
                status_code=404
            )

        # For COUNTRY_ADMIN, check if accessory is in their assigned countries
        if user.user_type == UserType.COUNTRY_ADMIN and user.assigned_countries:
            if accessory.country and accessory.country not in user.assigned_countries:
                return api_error(
                    ErrorCodes.INSUFFICIENT_PERMISSIONS,
                    'You do not have permission to process returns for accessories in this country',
                    status_code=403
                )

        # Get return quantity
        quantity = data.get('quantity', 1)
        try:
            quantity = int(quantity)
            if quantity < 1:
                quantity = 1
        except (ValueError, TypeError):
            quantity = 1

        # Check if there are items to return
        checked_out = (accessory.total_quantity or 0) - (accessory.available_quantity or 0)
        if checked_out <= 0:
            return api_error(
                ErrorCodes.VALIDATION_ERROR,
                'No items are checked out for this accessory',
                status_code=400
            )

        if quantity > checked_out:
            return api_error(
                ErrorCodes.VALIDATION_ERROR,
                f'Cannot return {quantity} items. Only {checked_out} are checked out.',
                status_code=400,
                details={'checked_out_quantity': checked_out, 'requested_quantity': quantity}
            )

        # Store old values for tracking
        old_available = accessory.available_quantity
        old_status = accessory.status

        # Process the return
        accessory.available_quantity = (accessory.available_quantity or 0) + quantity
        accessory.return_date = datetime.utcnow()

        # Update status if all items are back
        if accessory.available_quantity >= accessory.total_quantity:
            accessory.status = 'Available'
            accessory.customer_id = None

        accessory.updated_at = datetime.utcnow()

        # Create transaction record
        transaction = AccessoryTransaction(
            accessory_id=accessory.id,
            transaction_type='Return',
            quantity=quantity,
            customer_id=data.get('customer_id') or accessory.customer_id,
            notes=data.get('notes', f'Returned via API by {user.username}'),
            transaction_date=datetime.utcnow()
        )
        transaction.user_id = user.id
        db_session.add(transaction)

        # Create history entry
        changes = {
            'available_quantity': {'old': old_available, 'new': accessory.available_quantity}
        }
        if old_status != accessory.status:
            changes['status'] = {'old': old_status, 'new': accessory.status}

        history = accessory.track_change(
            user_id=user.id,
            action='RETURN',
            changes=changes,
            notes=data.get('notes') or f'Returned {quantity} unit(s) via API v2'
        )
        db_session.add(history)

        # Create activity log
        activity = Activity(
            user_id=user.id,
            type='accessory_returned',
            content=f'Returned {quantity} unit(s) of {accessory.name} via API',
            reference_id=accessory.id
        )
        db_session.add(activity)

        db_session.commit()

        logger.info(f"Accessory {accessory_id}: {quantity} unit(s) returned via API by user {user.username}")

        return api_response(
            data=format_accessory_response(accessory),
            message=f'Successfully returned {quantity} unit(s)'
        )

    except Exception as e:
        db_session.rollback()
        logger.error(f"Error returning accessory {accessory_id}: {str(e)}")
        raise
    finally:
        db_session.close()


# =============================================================================
# CHECK-IN ACCESSORY FROM CUSTOMER
# =============================================================================

@api_v2_bp.route('/accessories/<int:accessory_id>/checkin', methods=['POST'])
@dual_auth_required
@handle_exceptions
def checkin_accessory(accessory_id):
    """
    Check-in (return) an accessory from a specific customer.

    POST /api/v2/accessories/<id>/checkin
    Headers: Authorization: Bearer <token>
    Body: {
        "customer_id": 5,
        "quantity": 1,
        "condition": "Good",
        "notes": "Returned in good condition",
        "ticket_id": 123
    }

    Returns: {
        "success": true,
        "data": {
            "id": 20,
            "accessory": {
                "id": 5,
                "name": "USB-C Charger",
                "available_quantity": 15,
                "total_quantity": 20
            },
            "customer": {
                "id": 5,
                "name": "Jane Smith"
            },
            "quantity_returned": 1,
            "condition": "Good",
            "transaction_id": 150,
            "checked_in_at": "ISO8601"
        },
        "message": "Accessory checked in successfully"
    }
    """
    from models.customer_user import CustomerUser
    from sqlalchemy import func

    user = request.current_api_user

    # Check permission
    if not user.permissions or not user.permissions.can_edit_assets:
        return api_error(
            ErrorCodes.INSUFFICIENT_PERMISSIONS,
            'You do not have permission to check in accessories',
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

    customer_id = data.get('customer_id')
    quantity = data.get('quantity', 1)
    condition = data.get('condition', 'Good').strip() if data.get('condition') else 'Good'
    notes = data.get('notes', '').strip() or None
    ticket_id = data.get('ticket_id')

    # Validate quantity
    try:
        quantity = int(quantity)
        if quantity < 1:
            quantity = 1
    except (ValueError, TypeError):
        quantity = 1

    db_session = db_manager.get_session()
    try:
        # Find the accessory
        accessory = db_session.query(Accessory).filter(Accessory.id == accessory_id).first()

        if not accessory:
            return api_error(
                ErrorCodes.RESOURCE_NOT_FOUND,
                f'Accessory with ID {accessory_id} not found',
                status_code=404
            )

        # For COUNTRY_ADMIN, check if accessory is in their assigned countries
        if user.user_type == UserType.COUNTRY_ADMIN and user.assigned_countries:
            if accessory.country and accessory.country not in user.assigned_countries:
                return api_error(
                    ErrorCodes.INSUFFICIENT_PERMISSIONS,
                    'You do not have permission to check in accessories in this country',
                    status_code=403
                )

        # Find the customer
        customer = db_session.query(CustomerUser).filter(CustomerUser.id == customer_id).first()
        if not customer:
            return api_error(
                ErrorCodes.RESOURCE_NOT_FOUND,
                f'Customer with ID {customer_id} not found',
                status_code=404
            )

        # Calculate how many units this customer has checked out for this accessory
        # by summing checkout transactions and subtracting checkin transactions
        checkout_sum = db_session.query(func.coalesce(func.sum(AccessoryTransaction.quantity), 0)).filter(
            AccessoryTransaction.accessory_id == accessory_id,
            AccessoryTransaction.customer_id == customer_id,
            AccessoryTransaction.transaction_type.ilike('checkout')
        ).scalar() or 0

        checkin_sum = db_session.query(func.coalesce(func.sum(AccessoryTransaction.quantity), 0)).filter(
            AccessoryTransaction.accessory_id == accessory_id,
            AccessoryTransaction.customer_id == customer_id,
            AccessoryTransaction.transaction_type.ilike('%checkin%')
        ).scalar() or 0

        customer_checked_out = checkout_sum - checkin_sum

        if customer_checked_out <= 0:
            return api_error(
                ErrorCodes.VALIDATION_ERROR,
                f'Customer "{customer.name}" does not have any units of this accessory checked out',
                status_code=400,
                details={
                    'customer_id': customer_id,
                    'accessory_id': accessory_id,
                    'checked_out_quantity': 0
                }
            )

        if quantity > customer_checked_out:
            return api_error(
                ErrorCodes.VALIDATION_ERROR,
                f'Cannot check in {quantity} units. Customer only has {customer_checked_out} units checked out.',
                status_code=400,
                details={
                    'requested_quantity': quantity,
                    'customer_checked_out': customer_checked_out
                }
            )

        # Store old values for tracking
        old_available = accessory.available_quantity
        old_status = accessory.status

        # Process the check-in: increase available quantity
        accessory.available_quantity = (accessory.available_quantity or 0) + quantity
        accessory.return_date = datetime.utcnow()
        accessory.updated_at = datetime.utcnow()

        # Update status if all items are back
        if accessory.available_quantity >= accessory.total_quantity:
            accessory.status = 'Available'
            accessory.customer_id = None

        # Create transaction record
        transaction = AccessoryTransaction(
            accessory_id=accessory.id,
            transaction_type='Checkin',
            quantity=quantity,
            customer_id=customer_id,
            notes=notes or f'Checked in via API by {user.username}. Condition: {condition}',
            transaction_date=datetime.utcnow()
        )
        transaction.user_id = user.id
        db_session.add(transaction)
        db_session.flush()  # Get the transaction ID

        # Create history entry
        changes = {
            'available_quantity': {'old': old_available, 'new': accessory.available_quantity},
            'condition': {'old': None, 'new': condition}
        }
        if old_status != accessory.status:
            changes['status'] = {'old': old_status, 'new': accessory.status}

        history = accessory.track_change(
            user_id=user.id,
            action='CHECKIN',
            changes=changes,
            notes=f'Checked in {quantity} unit(s) from {customer.name} via API v2. Condition: {condition}'
        )
        db_session.add(history)

        # Create activity log
        activity_content = f'Checked in {quantity} unit(s) of {accessory.name} from {customer.name} via API. Condition: {condition}'
        if ticket_id:
            activity_content += f' (Ticket: {ticket_id})'
        activity = Activity(
            user_id=user.id,
            type='accessory_checkin',
            content=activity_content,
            reference_id=accessory.id
        )
        db_session.add(activity)

        db_session.commit()

        logger.info(f"Accessory {accessory_id}: {quantity} unit(s) checked in from customer {customer_id} via API by user {user.username}")

        # Build response
        response_data = {
            'id': accessory.id,
            'accessory': {
                'id': accessory.id,
                'name': accessory.name,
                'available_quantity': accessory.available_quantity,
                'total_quantity': accessory.total_quantity
            },
            'customer': {
                'id': customer.id,
                'name': customer.name
            },
            'quantity_returned': quantity,
            'condition': condition,
            'transaction_id': transaction.id,
            'checked_in_at': datetime.utcnow().isoformat() + 'Z'
        }

        return api_response(
            data=response_data,
            message='Accessory checked in successfully'
        )

    except Exception as e:
        db_session.rollback()
        logger.error(f"Error checking in accessory {accessory_id}: {str(e)}")
        raise
    finally:
        db_session.close()
