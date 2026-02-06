"""
API v2 Endpoint Template

This file serves as a template for creating new API v2 endpoints.
Copy this file and modify it for your specific resource.

Replace:
- 'items' with your resource name (e.g., 'assets', 'tickets', 'users')
- 'Item' with your model class name
- Update the ALLOWED_SORT_FIELDS for your model's fields
- Update the SEARCH_FIELDS for your model's searchable fields
- Modify the format_item() function for your model's fields

IMPORTANT: After creating your endpoint file, register it in __init__.py:
    from . import your_endpoint_name

Author: [Your Name]
Created: [Date]
"""

from flask import request
from . import api_v2_bp
from .utils import (
    # Response helpers
    api_response,
    api_error,
    api_created,
    api_no_content,
    # Pagination & sorting
    paginate_query,
    get_pagination_params,
    apply_sorting,
    get_sorting_params,
    # Validation
    validate_json_body,
    validate_required_fields,
    # Filters
    get_filter_param,
    get_date_filter,
    get_search_term,
    apply_search_filter,
    # Helpers
    get_or_404,
    serialize_datetime,
    safe_str,
    safe_int,
    format_user_summary,
    format_company_summary,
    # Error codes
    ErrorCodes,
    # Decorators
    handle_exceptions,
    dual_auth_required,
    require_permission,
)

# Import your model
# from models.item import Item

import logging
logger = logging.getLogger(__name__)


# =============================================================================
# CONFIGURATION
# =============================================================================

# Fields that can be sorted on
ALLOWED_SORT_FIELDS = [
    'id', 'name', 'created_at', 'updated_at', 'status'
]

# Fields to search in when using ?search= parameter
SEARCH_FIELDS = [
    'name', 'description'
]


# =============================================================================
# FORMATTERS
# =============================================================================

def format_item(item, include_details=False):
    """
    Format an item model to a dictionary for API response.

    Args:
        item: Item model instance
        include_details: If True, include additional nested details

    Returns:
        Dictionary representation of the item
    """
    data = {
        'id': item.id,
        'name': safe_str(item.name),
        'status': safe_str(item.status),
        'created_at': serialize_datetime(item.created_at),
        'updated_at': serialize_datetime(item.updated_at),
    }

    # Include additional details for single-item responses
    if include_details:
        data.update({
            'description': safe_str(item.description),
            # Add relationship data
            'created_by': format_user_summary(item.created_by) if hasattr(item, 'created_by') else None,
            'company': format_company_summary(item.company) if hasattr(item, 'company') else None,
        })

    return data


def format_item_list(items):
    """Format a list of items for API response."""
    return [format_item(item, include_details=False) for item in items]


# =============================================================================
# LIST ENDPOINT
# =============================================================================

@api_v2_bp.route('/items', methods=['GET'])
@handle_exceptions
@dual_auth_required
def list_items():
    """
    List all items with pagination, filtering, and sorting.

    GET /api/v2/items

    Query Parameters:
        - page: Page number (default: 1)
        - per_page: Items per page (default: 20, max: 100)
        - sort: Field to sort by (default: created_at)
        - order: Sort order, 'asc' or 'desc' (default: desc)
        - search: Search term to filter results
        - status: Filter by status

    Headers:
        Authorization: Bearer <token>

    Returns:
        {
            "success": true,
            "data": [
                {"id": 1, "name": "Item 1", ...},
                {"id": 2, "name": "Item 2", ...}
            ],
            "meta": {
                "pagination": {
                    "page": 1,
                    "per_page": 20,
                    "total_items": 150,
                    "total_pages": 8,
                    "has_next": true,
                    "has_prev": false
                }
            },
            "message": "Retrieved 20 items"
        }
    """
    # TODO: Replace with actual model import
    # from models.item import Item

    user = request.current_api_user

    # Check permissions (optional - customize as needed)
    # if not user.permissions or not user.permissions.can_view_items:
    #     return api_error(
    #         ErrorCodes.INSUFFICIENT_PERMISSIONS,
    #         'You do not have permission to view items',
    #         status_code=403
    #     )

    # Get pagination params
    page, per_page = get_pagination_params()

    # Get sorting params
    sort_field, sort_order = get_sorting_params(
        allowed_fields=ALLOWED_SORT_FIELDS,
        default_sort='created_at',
        default_order='desc'
    )

    # Build base query
    # query = Item.query

    # Apply filters
    status = get_filter_param('status')
    # if status:
    #     query = query.filter(Item.status == status)

    # Apply search
    search_term = get_search_term()
    # if search_term:
    #     query = apply_search_filter(query, Item, search_term, SEARCH_FIELDS)

    # Apply sorting
    # query = apply_sorting(query, Item, sort_field, sort_order)

    # Paginate
    # items, meta = paginate_query(query, page, per_page)

    # Format response
    # items_data = format_item_list(items)

    # TODO: Remove this placeholder response
    items_data = []
    meta = {'pagination': {'page': 1, 'per_page': 20, 'total_items': 0, 'total_pages': 0}}

    return api_response(
        data=items_data,
        message=f'Retrieved {len(items_data)} items',
        meta=meta
    )


# =============================================================================
# GET SINGLE ENDPOINT
# =============================================================================

@api_v2_bp.route('/items/<int:item_id>', methods=['GET'])
@handle_exceptions
@dual_auth_required
def get_item(item_id):
    """
    Get a single item by ID.

    GET /api/v2/items/{id}

    Path Parameters:
        - id: Item ID (integer)

    Headers:
        Authorization: Bearer <token>

    Returns:
        {
            "success": true,
            "data": {
                "id": 1,
                "name": "Item Name",
                "description": "...",
                ...
            },
            "message": "Item retrieved successfully"
        }

    Errors:
        404: Item not found
    """
    # TODO: Replace with actual model import
    # from models.item import Item

    # Get the item
    # item, error = get_or_404(Item, item_id)
    # if error:
    #     return error

    # TODO: Remove this placeholder
    return api_error(
        ErrorCodes.RESOURCE_NOT_FOUND,
        f'Item with ID {item_id} not found',
        status_code=404
    )

    # Format with details
    # item_data = format_item(item, include_details=True)

    # return api_response(
    #     data=item_data,
    #     message='Item retrieved successfully'
    # )


# =============================================================================
# CREATE ENDPOINT
# =============================================================================

@api_v2_bp.route('/items', methods=['POST'])
@handle_exceptions
@dual_auth_required
# @require_permission('can_create_items')  # Optional permission check
def create_item():
    """
    Create a new item.

    POST /api/v2/items

    Headers:
        Authorization: Bearer <token>
        Content-Type: application/json

    Request Body:
        {
            "name": "Item Name",        # Required
            "description": "...",       # Optional
            "status": "active"          # Optional, default: 'active'
        }

    Returns:
        201 Created: {
            "success": true,
            "data": {"id": 123, "name": "Item Name", ...},
            "message": "Item created successfully"
        }

    Errors:
        400: Validation error (missing required fields)
    """
    # TODO: Replace with actual model import
    # from models.item import Item
    # from database import db

    user = request.current_api_user

    # Validate JSON body
    data, error = validate_json_body()
    if error:
        return error

    # Validate required fields
    is_valid, error = validate_required_fields(data, ['name'])
    if error:
        return error

    # Create the item
    # item = Item(
    #     name=data['name'],
    #     description=data.get('description'),
    #     status=data.get('status', 'active'),
    #     created_by_id=user.id
    # )

    # try:
    #     db.session.add(item)
    #     db.session.commit()
    # except Exception as e:
    #     db.session.rollback()
    #     logger.error(f'Failed to create item: {e}')
    #     return api_error(
    #         ErrorCodes.DATABASE_ERROR,
    #         'Failed to create item',
    #         status_code=500
    #     )

    # Return created item
    # return api_created(
    #     data=format_item(item, include_details=True),
    #     message='Item created successfully'
    # )

    # TODO: Remove this placeholder
    return api_error(
        ErrorCodes.INTERNAL_ERROR,
        'Not implemented',
        status_code=501
    )


# =============================================================================
# UPDATE ENDPOINT
# =============================================================================

@api_v2_bp.route('/items/<int:item_id>', methods=['PUT', 'PATCH'])
@handle_exceptions
@dual_auth_required
# @require_permission('can_edit_items')  # Optional permission check
def update_item(item_id):
    """
    Update an existing item.

    PUT/PATCH /api/v2/items/{id}

    Path Parameters:
        - id: Item ID (integer)

    Headers:
        Authorization: Bearer <token>
        Content-Type: application/json

    Request Body (partial update allowed):
        {
            "name": "Updated Name",
            "description": "...",
            "status": "inactive"
        }

    Returns:
        {
            "success": true,
            "data": {"id": 123, "name": "Updated Name", ...},
            "message": "Item updated successfully"
        }

    Errors:
        404: Item not found
        400: Validation error
    """
    # TODO: Replace with actual model import
    # from models.item import Item
    # from database import db

    # Get the item
    # item, error = get_or_404(Item, item_id)
    # if error:
    #     return error

    # Validate JSON body
    data, error = validate_json_body()
    if error:
        return error

    # Update allowed fields
    # UPDATABLE_FIELDS = ['name', 'description', 'status']
    # for field in UPDATABLE_FIELDS:
    #     if field in data:
    #         setattr(item, field, data[field])

    # try:
    #     db.session.commit()
    # except Exception as e:
    #     db.session.rollback()
    #     logger.error(f'Failed to update item: {e}')
    #     return api_error(
    #         ErrorCodes.DATABASE_ERROR,
    #         'Failed to update item',
    #         status_code=500
    #     )

    # return api_response(
    #     data=format_item(item, include_details=True),
    #     message='Item updated successfully'
    # )

    # TODO: Remove this placeholder
    return api_error(
        ErrorCodes.RESOURCE_NOT_FOUND,
        f'Item with ID {item_id} not found',
        status_code=404
    )


# =============================================================================
# DELETE ENDPOINT
# =============================================================================

@api_v2_bp.route('/items/<int:item_id>', methods=['DELETE'])
@handle_exceptions
@dual_auth_required
# @require_permission('can_delete_items')  # Optional permission check
def delete_item(item_id):
    """
    Delete an item.

    DELETE /api/v2/items/{id}

    Path Parameters:
        - id: Item ID (integer)

    Headers:
        Authorization: Bearer <token>

    Returns:
        204 No Content (on success)

    Errors:
        404: Item not found
        409: Item cannot be deleted (has dependencies)
    """
    # TODO: Replace with actual model import
    # from models.item import Item
    # from database import db

    # Get the item
    # item, error = get_or_404(Item, item_id)
    # if error:
    #     return error

    # Check for dependencies before deleting
    # if item.has_dependencies():  # Implement this method in your model
    #     return api_error(
    #         ErrorCodes.RESOURCE_IN_USE,
    #         'Cannot delete item: it is referenced by other records',
    #         status_code=409
    #     )

    # try:
    #     db.session.delete(item)
    #     db.session.commit()
    # except Exception as e:
    #     db.session.rollback()
    #     logger.error(f'Failed to delete item: {e}')
    #     return api_error(
    #         ErrorCodes.DATABASE_ERROR,
    #         'Failed to delete item',
    #         status_code=500
    #     )

    # return api_no_content()

    # TODO: Remove this placeholder
    return api_error(
        ErrorCodes.RESOURCE_NOT_FOUND,
        f'Item with ID {item_id} not found',
        status_code=404
    )
