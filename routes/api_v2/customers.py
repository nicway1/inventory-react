"""
API v2 Customer Management Endpoints

This module provides CRUD operations for customer management:
- GET /api/v2/customers - List customers with pagination and search
- POST /api/v2/customers - Create a new customer
- GET /api/v2/customers/<id> - Get a single customer
- PUT /api/v2/customers/<id> - Update a customer
- DELETE /api/v2/customers/<id> - Delete a customer
- GET /api/v2/customers/<id>/tickets - Get all tickets associated with a customer

All endpoints require dual authentication (JWT token or API key).
"""

from flask import request
from sqlalchemy import or_
import logging

from . import api_v2_bp
from .utils import (
    api_response,
    api_error,
    api_created,
    api_no_content,
    get_pagination_params,
    paginate_query,
    get_sorting_params,
    apply_sorting,
    validate_json_body,
    validate_required_fields,
    handle_exceptions,
    ErrorCodes,
    dual_auth_required
)
from models.customer_user import CustomerUser
from models.company import Company
from models.user import UserType
from utils.db_manager import DatabaseManager

logger = logging.getLogger(__name__)
db_manager = DatabaseManager()


def format_customer(customer):
    """
    Format a CustomerUser model instance to a dictionary for API response.

    Args:
        customer: CustomerUser model instance

    Returns:
        Dictionary representation of the customer
    """
    return {
        'id': customer.id,
        'name': customer.name,
        'contact_number': customer.contact_number,
        'email': customer.email,
        'address': customer.address,
        'company_id': customer.company_id,
        'company_name': customer.company.grouped_display_name if customer.company else None,
        'country': customer.country,
        'created_at': customer.created_at.isoformat() + 'Z' if customer.created_at else None,
        'updated_at': customer.updated_at.isoformat() + 'Z' if customer.updated_at else None
    }


def get_permitted_company_ids(db_session, user):
    """
    Get list of company IDs the user has permission to access.

    Args:
        db_session: Database session
        user: Current user object

    Returns:
        List of company IDs or None if user has access to all companies
    """
    from models.user_company_permission import UserCompanyPermission
    from models.company_customer_permission import CompanyCustomerPermission

    # SUPER_ADMIN and DEVELOPER can see all customers
    if user.user_type in [UserType.SUPER_ADMIN, UserType.DEVELOPER]:
        return None  # No filtering needed

    # For COUNTRY_ADMIN and SUPERVISOR, use UserCompanyPermission
    if user.user_type in [UserType.COUNTRY_ADMIN, UserType.SUPERVISOR]:
        user_company_permissions = db_session.query(UserCompanyPermission).filter_by(
            user_id=user.id,
            can_view=True
        ).all()

        if user_company_permissions:
            permitted_company_ids = [perm.company_id for perm in user_company_permissions]

            # Include child companies of any parent company
            permitted_companies = db_session.query(Company).filter(
                Company.id.in_(permitted_company_ids)
            ).all()
            all_permitted_ids = list(permitted_company_ids)

            for company in permitted_companies:
                if company.is_parent_company or company.child_companies.count() > 0:
                    child_ids = [c.id for c in company.child_companies.all()]
                    all_permitted_ids.extend(child_ids)

            # Check for cross-company customer viewing permissions
            cross_company_ids = []
            for company_id in all_permitted_ids:
                additional_company_ids = db_session.query(CompanyCustomerPermission.customer_company_id)\
                    .filter(
                        CompanyCustomerPermission.company_id == company_id,
                        CompanyCustomerPermission.can_view == True
                    ).all()
                cross_company_ids.extend([cid[0] for cid in additional_company_ids])

            return list(set(all_permitted_ids + cross_company_ids))
        else:
            return []  # No permissions = no access

    # For other users (CLIENT), filter by their company
    if user.company_id:
        permitted_company_ids = db_session.query(CompanyCustomerPermission.customer_company_id)\
            .filter(
                CompanyCustomerPermission.company_id == user.company_id,
                CompanyCustomerPermission.can_view == True
            ).all()

        return [user.company_id] + [cid[0] for cid in permitted_company_ids]

    return []  # No company = no access


@api_v2_bp.route('/customers', methods=['GET'])
@dual_auth_required
@handle_exceptions
def list_customers():
    """
    List customers with pagination and search.

    GET /api/v2/customers

    Query Parameters:
        page (int): Page number (default: 1)
        per_page (int): Items per page (default: 20, max: 100)
        search (str): Search term for name, email, contact number
        company_id (int): Filter by company ID
        country (str): Filter by country
        sort (str): Sort field (name, email, created_at, updated_at)
        order (str): Sort order (asc, desc)

    Returns:
        {
            "success": true,
            "data": [
                {
                    "id": 1,
                    "name": "John Doe",
                    "contact_number": "+1234567890",
                    "email": "john@example.com",
                    ...
                }
            ],
            "meta": {
                "pagination": {...}
            }
        }
    """
    user = request.current_api_user
    db_session = db_manager.get_session()

    try:
        # Build base query
        query = db_session.query(CustomerUser)

        # Apply permission-based filtering
        permitted_company_ids = get_permitted_company_ids(db_session, user)
        if permitted_company_ids is not None:
            if len(permitted_company_ids) == 0:
                # User has no access to any companies
                return api_response(data=[], meta={'pagination': {
                    'page': 1,
                    'per_page': 20,
                    'total_items': 0,
                    'total_pages': 0,
                    'has_next': False,
                    'has_prev': False
                }})
            query = query.filter(CustomerUser.company_id.in_(permitted_company_ids))

        # Apply search filter
        search_term = request.args.get('search', '').strip()
        if search_term:
            search_pattern = f'%{search_term}%'
            query = query.filter(or_(
                CustomerUser.name.ilike(search_pattern),
                CustomerUser.email.ilike(search_pattern),
                CustomerUser.contact_number.ilike(search_pattern),
                CustomerUser.address.ilike(search_pattern)
            ))

        # Apply company filter
        company_id = request.args.get('company_id', type=int)
        if company_id:
            query = query.filter(CustomerUser.company_id == company_id)

        # Apply country filter
        country = request.args.get('country', '').strip()
        if country:
            query = query.filter(CustomerUser.country == country)

        # Apply sorting
        allowed_sort_fields = ['name', 'email', 'created_at', 'updated_at', 'country']
        sort_field, sort_order = get_sorting_params(allowed_sort_fields, default_sort='name', default_order='asc')
        query = apply_sorting(query, CustomerUser, sort_field, sort_order)

        # Apply pagination
        page, per_page = get_pagination_params()

        # Get total count for pagination
        total = query.count()
        total_pages = (total + per_page - 1) // per_page if per_page > 0 else 0

        # Get paginated items
        offset = (page - 1) * per_page
        customers = query.offset(offset).limit(per_page).all()

        # Format response
        customers_data = [format_customer(c) for c in customers]

        pagination_meta = {
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total_items': total,
                'total_pages': total_pages,
                'has_next': page < total_pages,
                'has_prev': page > 1
            }
        }

        return api_response(data=customers_data, meta=pagination_meta)

    finally:
        db_session.close()


@api_v2_bp.route('/customers', methods=['POST'])
@dual_auth_required
@handle_exceptions
def create_customer():
    """
    Create a new customer.

    POST /api/v2/customers

    Request Body:
        {
            "name": "John Doe",           // Required
            "contact_number": "+1234567890", // Required
            "address": "123 Main St",     // Required
            "country": "SINGAPORE",       // Required
            "email": "john@example.com",  // Optional
            "company_id": 1               // Optional
        }

    Returns:
        201: Created customer data
        400: Validation error
    """
    user = request.current_api_user
    db_session = db_manager.get_session()

    try:
        # Validate JSON body
        data, error = validate_json_body()
        if error:
            return error

        # Validate required fields
        required_fields = ['name', 'contact_number', 'address', 'country']
        is_valid, error = validate_required_fields(data, required_fields)
        if not is_valid:
            return error

        # Normalize country (uppercase with underscores)
        country = data['country'].upper().replace(' ', '_')

        # Validate company if provided
        company = None
        company_id = data.get('company_id')
        if company_id:
            company = db_session.query(Company).get(company_id)
            if not company:
                return api_error(
                    code=ErrorCodes.RESOURCE_NOT_FOUND,
                    message=f'Company with ID {company_id} not found',
                    status_code=404
                )

            # Check permission to add customer to this company
            permitted_company_ids = get_permitted_company_ids(db_session, user)
            if permitted_company_ids is not None and company_id not in permitted_company_ids:
                return api_error(
                    code=ErrorCodes.PERMISSION_DENIED,
                    message='You do not have permission to add customers to this company',
                    status_code=403
                )

        # Create customer
        from datetime import datetime
        customer = CustomerUser(
            name=data['name'].strip(),
            contact_number=data['contact_number'].strip(),
            email=data.get('email', '').strip() or None,
            address=data['address'].strip(),
            country=country,
            company_id=company_id,
            created_at=datetime.utcnow()
        )

        db_session.add(customer)
        db_session.commit()
        db_session.refresh(customer)

        logger.info(f"Customer created: {customer.name} (ID: {customer.id}) by user {user.username}")

        return api_created(
            data=format_customer(customer),
            message='Customer created successfully'
        )

    except Exception as e:
        db_session.rollback()
        logger.exception(f"Error creating customer: {str(e)}")
        raise

    finally:
        db_session.close()


@api_v2_bp.route('/customers/<int:customer_id>', methods=['GET'])
@dual_auth_required
@handle_exceptions
def get_customer(customer_id):
    """
    Get a single customer by ID.

    GET /api/v2/customers/<id>

    Returns:
        200: Customer data
        404: Customer not found
    """
    user = request.current_api_user
    db_session = db_manager.get_session()

    try:
        customer = db_session.query(CustomerUser).get(customer_id)

        if not customer:
            return api_error(
                code=ErrorCodes.RESOURCE_NOT_FOUND,
                message=f'Customer with ID {customer_id} not found',
                status_code=404
            )

        # Check permission
        permitted_company_ids = get_permitted_company_ids(db_session, user)
        if permitted_company_ids is not None and customer.company_id not in permitted_company_ids:
            return api_error(
                code=ErrorCodes.PERMISSION_DENIED,
                message='You do not have permission to view this customer',
                status_code=403
            )

        return api_response(data=format_customer(customer))

    finally:
        db_session.close()


@api_v2_bp.route('/customers/<int:customer_id>', methods=['PUT'])
@dual_auth_required
@handle_exceptions
def update_customer(customer_id):
    """
    Update an existing customer.

    PUT /api/v2/customers/<id>

    Request Body (all fields optional):
        {
            "name": "John Doe",
            "contact_number": "+1234567890",
            "address": "123 Main St",
            "country": "SINGAPORE",
            "email": "john@example.com",
            "company_id": 1
        }

    Returns:
        200: Updated customer data
        404: Customer not found
        400: Validation error
    """
    user = request.current_api_user
    db_session = db_manager.get_session()

    try:
        customer = db_session.query(CustomerUser).get(customer_id)

        if not customer:
            return api_error(
                code=ErrorCodes.RESOURCE_NOT_FOUND,
                message=f'Customer with ID {customer_id} not found',
                status_code=404
            )

        # Check permission
        permitted_company_ids = get_permitted_company_ids(db_session, user)
        if permitted_company_ids is not None and customer.company_id not in permitted_company_ids:
            return api_error(
                code=ErrorCodes.PERMISSION_DENIED,
                message='You do not have permission to update this customer',
                status_code=403
            )

        # Validate JSON body
        data, error = validate_json_body()
        if error:
            return error

        # Update fields if provided
        if 'name' in data and data['name']:
            customer.name = data['name'].strip()

        if 'contact_number' in data and data['contact_number']:
            customer.contact_number = data['contact_number'].strip()

        if 'email' in data:
            customer.email = data['email'].strip() if data['email'] else None

        if 'address' in data and data['address']:
            customer.address = data['address'].strip()

        if 'country' in data and data['country']:
            customer.country = data['country'].upper().replace(' ', '_')

        if 'company_id' in data:
            new_company_id = data['company_id']
            if new_company_id:
                # Validate company exists
                company = db_session.query(Company).get(new_company_id)
                if not company:
                    return api_error(
                        code=ErrorCodes.RESOURCE_NOT_FOUND,
                        message=f'Company with ID {new_company_id} not found',
                        status_code=404
                    )

                # Check permission for new company
                if permitted_company_ids is not None and new_company_id not in permitted_company_ids:
                    return api_error(
                        code=ErrorCodes.PERMISSION_DENIED,
                        message='You do not have permission to move customer to this company',
                        status_code=403
                    )

            customer.company_id = new_company_id

        db_session.commit()
        db_session.refresh(customer)

        logger.info(f"Customer updated: {customer.name} (ID: {customer.id}) by user {user.username}")

        return api_response(
            data=format_customer(customer),
            message='Customer updated successfully'
        )

    except Exception as e:
        db_session.rollback()
        logger.exception(f"Error updating customer: {str(e)}")
        raise

    finally:
        db_session.close()


@api_v2_bp.route('/customers/<int:customer_id>', methods=['DELETE'])
@dual_auth_required
@handle_exceptions
def delete_customer(customer_id):
    """
    Delete a customer.

    DELETE /api/v2/customers/<id>

    Returns:
        204: Successfully deleted
        404: Customer not found
        409: Customer has related data and cannot be deleted
    """
    user = request.current_api_user
    db_session = db_manager.get_session()

    try:
        customer = db_session.query(CustomerUser).get(customer_id)

        if not customer:
            return api_error(
                code=ErrorCodes.RESOURCE_NOT_FOUND,
                message=f'Customer with ID {customer_id} not found',
                status_code=404
            )

        # Check permission
        permitted_company_ids = get_permitted_company_ids(db_session, user)
        if permitted_company_ids is not None and customer.company_id not in permitted_company_ids:
            return api_error(
                code=ErrorCodes.PERMISSION_DENIED,
                message='You do not have permission to delete this customer',
                status_code=403
            )

        # Check for related assets
        if customer.assigned_assets and len(customer.assigned_assets) > 0:
            return api_error(
                code=ErrorCodes.RESOURCE_IN_USE,
                message='Cannot delete customer with assigned assets',
                status_code=409,
                details={'assigned_assets_count': len(customer.assigned_assets)}
            )

        # Check for related accessories
        if customer.assigned_accessories and len(customer.assigned_accessories) > 0:
            return api_error(
                code=ErrorCodes.RESOURCE_IN_USE,
                message='Cannot delete customer with assigned accessories',
                status_code=409,
                details={'assigned_accessories_count': len(customer.assigned_accessories)}
            )

        # Check for related tickets
        if customer.tickets and len(customer.tickets) > 0:
            return api_error(
                code=ErrorCodes.RESOURCE_IN_USE,
                message='Cannot delete customer with related tickets',
                status_code=409,
                details={'related_tickets_count': len(customer.tickets)}
            )

        customer_name = customer.name
        db_session.delete(customer)
        db_session.commit()

        logger.info(f"Customer deleted: {customer_name} (ID: {customer_id}) by user {user.username}")

        return api_no_content()

    except Exception as e:
        db_session.rollback()
        logger.exception(f"Error deleting customer: {str(e)}")
        raise

    finally:
        db_session.close()


# =============================================================================
# GET CUSTOMER TICKETS
# =============================================================================

@api_v2_bp.route('/customers/<int:customer_id>/tickets', methods=['GET'])
@dual_auth_required
@handle_exceptions
def get_customer_tickets(customer_id):
    """
    Get all tickets associated with a customer.

    GET /api/v2/customers/<id>/tickets

    Query Parameters:
        page (int): Page number (default: 1)
        per_page (int): Items per page (default: 20, max: 100)
        status (str): Filter by status (e.g., "New", "In Progress", "Resolved")
        sort (str): Sort field (created_at, updated_at, status, subject)
        order (str): Sort order (asc, desc)

    Returns:
        {
            "success": true,
            "data": [
                {
                    "id": 123,
                    "display_id": "TICK-0123",
                    "subject": "Asset Checkout Request",
                    "status": "Resolved",
                    "category": "Asset Checkout",
                    "created_at": "ISO8601",
                    "resolved_at": "ISO8601",
                    "assets_count": 2,
                    "assigned_to": {
                        "id": 1,
                        "username": "support.agent"
                    }
                }
            ],
            "meta": {
                "pagination": {...},
                "counts": {
                    "total": 25,
                    "open": 3,
                    "resolved": 22
                }
            }
        }
    """
    from models.ticket import Ticket, TicketStatus
    from sqlalchemy import func

    user = request.current_api_user
    db_session = db_manager.get_session()

    try:
        # Find the customer
        customer = db_session.query(CustomerUser).get(customer_id)

        if not customer:
            return api_error(
                code=ErrorCodes.RESOURCE_NOT_FOUND,
                message=f'Customer with ID {customer_id} not found',
                status_code=404
            )

        # Check permission
        permitted_company_ids = get_permitted_company_ids(db_session, user)
        if permitted_company_ids is not None and customer.company_id not in permitted_company_ids:
            return api_error(
                code=ErrorCodes.PERMISSION_DENIED,
                message='You do not have permission to view this customer\'s tickets',
                status_code=403
            )

        # Build base query for tickets
        query = db_session.query(Ticket).filter(Ticket.customer_id == customer_id)

        # Apply status filter
        status_filter = request.args.get('status', '').strip()
        if status_filter:
            # Try to match against TicketStatus enum
            try:
                # Handle various status formats
                status_normalized = status_filter.upper().replace(' ', '_')
                status_enum = TicketStatus[status_normalized]
                query = query.filter(Ticket.status == status_enum)
            except KeyError:
                # If not a valid enum, filter by custom_status or return empty
                query = query.filter(
                    or_(
                        Ticket.status.has_name(status_filter),
                        Ticket.custom_status.ilike(f'%{status_filter}%')
                    )
                )

        # Get counts before pagination (for all statuses)
        total_count = db_session.query(Ticket).filter(Ticket.customer_id == customer_id).count()

        # Count resolved tickets
        resolved_count = db_session.query(Ticket).filter(
            Ticket.customer_id == customer_id,
            Ticket.status.in_([TicketStatus.RESOLVED, TicketStatus.RESOLVED_DELIVERED])
        ).count()

        # Count open tickets (not resolved)
        open_count = total_count - resolved_count

        # Apply sorting
        allowed_sort_fields = ['created_at', 'updated_at', 'status', 'subject', 'id']
        sort_field, sort_order = get_sorting_params(allowed_sort_fields, default_sort='created_at', default_order='desc')
        query = apply_sorting(query, Ticket, sort_field, sort_order)

        # Apply pagination
        page, per_page = get_pagination_params()

        # Get total filtered count for pagination
        filtered_total = query.count()
        total_pages = (filtered_total + per_page - 1) // per_page if per_page > 0 else 0

        # Get paginated items
        offset = (page - 1) * per_page
        tickets = query.offset(offset).limit(per_page).all()

        # Format tickets for response
        tickets_data = []
        for ticket in tickets:
            # Count assets associated with this ticket
            assets_count = len(ticket.assets) if ticket.assets else 0

            # Determine resolved_at (use updated_at if status is resolved)
            resolved_at = None
            if ticket.status in [TicketStatus.RESOLVED, TicketStatus.RESOLVED_DELIVERED]:
                resolved_at = ticket.updated_at.isoformat() + 'Z' if ticket.updated_at else None

            # Get assigned_to info
            assigned_to = None
            if ticket.assigned_to:
                assigned_to = {
                    'id': ticket.assigned_to.id,
                    'username': ticket.assigned_to.username
                }

            # Get category display name
            category_name = None
            if ticket.category:
                category_name = ticket.category.value

            ticket_data = {
                'id': ticket.id,
                'display_id': ticket.display_id,
                'subject': ticket.subject,
                'status': ticket.status.value if ticket.status else ticket.custom_status,
                'category': category_name,
                'created_at': ticket.created_at.isoformat() + 'Z' if ticket.created_at else None,
                'updated_at': ticket.updated_at.isoformat() + 'Z' if ticket.updated_at else None,
                'resolved_at': resolved_at,
                'assets_count': assets_count,
                'assigned_to': assigned_to
            }
            tickets_data.append(ticket_data)

        # Build pagination meta
        pagination_meta = {
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total_items': filtered_total,
                'total_pages': total_pages,
                'has_next': page < total_pages,
                'has_prev': page > 1
            },
            'counts': {
                'total': total_count,
                'open': open_count,
                'resolved': resolved_count
            }
        }

        return api_response(data=tickets_data, meta=pagination_meta)

    finally:
        db_session.close()
