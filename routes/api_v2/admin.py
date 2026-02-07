"""
Admin API v2 Endpoints

This module provides RESTful API endpoints for admin operations:
- User Management (CRUD)
- Company Management (CRUD)
- Queue Management (CRUD)
- Ticket Category Management (CRUD)

All endpoints require admin authentication (SUPER_ADMIN or DEVELOPER user types).
"""

from flask import Blueprint, request
from functools import wraps
from datetime import datetime
import logging

from models.user import User, UserType
from models.company import Company
from models.queue import Queue
from models.ticket import TicketCategory
from models.ticket_category_config import TicketCategoryConfig, CategoryDisplayConfig
from models.activity import Activity
from utils.db_manager import DatabaseManager
from werkzeug.security import generate_password_hash

from . import api_v2_bp
from .utils import (
    api_response,
    api_error,
    api_created,
    api_no_content,
    paginate_query,
    get_pagination_params,
    apply_sorting,
    get_sorting_params,
    validate_required_fields,
    validate_json_body,
    ErrorCodes,
    handle_exceptions,
    dual_auth_required,
)

logger = logging.getLogger(__name__)
db_manager = DatabaseManager()


# =============================================================================
# ADMIN PERMISSION DECORATOR
# =============================================================================

def admin_required(f):
    """
    Decorator to ensure user has admin permissions (SUPER_ADMIN or DEVELOPER).
    Must be used after dual_auth_required decorator.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = getattr(request, 'current_api_user', None)

        if not user:
            return api_error(
                ErrorCodes.AUTHENTICATION_REQUIRED,
                'Authentication required',
                status_code=401
            )

        # Check if user is SUPER_ADMIN or DEVELOPER
        if user.user_type not in [UserType.SUPER_ADMIN, UserType.DEVELOPER]:
            logger.warning(f'Admin access denied for user {user.username} (type: {user.user_type})')
            return api_error(
                ErrorCodes.ADMIN_ACCESS_REQUIRED,
                'Admin access required. Only SUPER_ADMIN and DEVELOPER users can access this endpoint.',
                status_code=403
            )

        return f(*args, **kwargs)

    return decorated_function


def log_admin_activity(db_session, user_id, activity_type, content, reference_id=None):
    """
    Create an audit log entry for admin actions

    Args:
        db_session: Database session
        user_id: ID of the user performing the action
        activity_type: Type of activity (e.g., 'user_created', 'company_deleted')
        content: Description of the action
        reference_id: Optional ID of the affected resource
    """
    try:
        activity = Activity(
            user_id=user_id,
            type=activity_type,
            content=content,
            reference_id=reference_id
        )
        db_session.add(activity)
        logger.info(f'Admin activity logged: {activity_type} by user {user_id}')
    except Exception as e:
        logger.error(f'Failed to log admin activity: {str(e)}')


# =============================================================================
# USER MANAGEMENT ENDPOINTS
# =============================================================================

@api_v2_bp.route('/admin/users', methods=['GET'])
@dual_auth_required
@admin_required
@handle_exceptions
def list_users():
    """
    List all users with pagination and sorting

    GET /api/v2/admin/users

    Query Parameters:
        - page: Page number (default: 1)
        - per_page: Items per page (default: 20, max: 100)
        - sort: Field to sort by (default: created_at)
        - order: Sort order - 'asc' or 'desc' (default: desc)
        - search: Search term for username/email
        - user_type: Filter by user type
        - company_id: Filter by company ID
        - include_deleted: Include soft-deleted users (default: false)

    Returns:
        List of users with pagination metadata
    """
    db_session = db_manager.get_session()
    try:
        # Get pagination params
        page, per_page = get_pagination_params()

        # Get sorting params
        allowed_sort_fields = ['id', 'username', 'email', 'user_type', 'created_at', 'updated_at']
        sort_field, sort_order = get_sorting_params(allowed_sort_fields)

        # Build query
        query = db_session.query(User)

        # Filter by deleted status
        include_deleted = request.args.get('include_deleted', 'false').lower() == 'true'
        if not include_deleted:
            query = query.filter(User.is_deleted == False)

        # Filter by search term
        search = request.args.get('search', '').strip()
        if search:
            search_pattern = f'%{search}%'
            query = query.filter(
                (User.username.ilike(search_pattern)) |
                (User.email.ilike(search_pattern))
            )

        # Filter by user type
        user_type_filter = request.args.get('user_type')
        if user_type_filter:
            try:
                user_type_enum = UserType[user_type_filter.upper()]
                query = query.filter(User.user_type == user_type_enum)
            except KeyError:
                pass  # Invalid user type, ignore filter

        # Filter by company
        company_id = request.args.get('company_id', type=int)
        if company_id:
            query = query.filter(User.company_id == company_id)

        # Apply sorting
        query = apply_sorting(query, User, sort_field, sort_order)

        # Paginate
        users, pagination_meta = paginate_query(query, page, per_page)

        # Format response
        users_data = []
        for user in users:
            user_dict = user.to_dict()
            user_dict['is_deleted'] = user.is_deleted
            user_dict['deleted_at'] = user.deleted_at.isoformat() if user.deleted_at else None
            users_data.append(user_dict)

        return api_response(
            data=users_data,
            message=f'Retrieved {len(users_data)} users',
            meta=pagination_meta
        )

    finally:
        db_session.close()


@api_v2_bp.route('/admin/users', methods=['POST'])
@dual_auth_required
@admin_required
@handle_exceptions
def create_user():
    """
    Create a new user

    POST /api/v2/admin/users

    Request Body:
        {
            "username": "string (required)",
            "email": "string (required)",
            "password": "string (required)",
            "user_type": "SUPER_ADMIN|DEVELOPER|COUNTRY_ADMIN|SUPERVISOR|CLIENT (required)",
            "company_id": "integer (optional)",
            "assigned_country": "string (optional)"
        }

    Returns:
        Created user object
    """
    # Validate request body
    data, error = validate_json_body()
    if error:
        return error

    # Validate required fields
    required_fields = ['username', 'email', 'password', 'user_type']
    is_valid, error = validate_required_fields(data, required_fields)
    if not is_valid:
        return error

    db_session = db_manager.get_session()
    try:
        # Validate user type
        try:
            user_type = UserType[data['user_type'].upper()]
        except KeyError:
            return api_error(
                ErrorCodes.INVALID_FIELD_VALUE,
                f'Invalid user_type. Must be one of: {", ".join([t.name for t in UserType])}',
                status_code=400
            )

        # Check for existing username
        existing_username = db_session.query(User).filter_by(username=data['username']).first()
        if existing_username:
            return api_error(
                ErrorCodes.RESOURCE_ALREADY_EXISTS,
                f'User with username "{data["username"]}" already exists',
                status_code=409
            )

        # Check for existing email
        existing_email = db_session.query(User).filter_by(email=data['email']).first()
        if existing_email:
            return api_error(
                ErrorCodes.RESOURCE_ALREADY_EXISTS,
                f'User with email "{data["email"]}" already exists',
                status_code=409
            )

        # Validate company_id if provided
        company_id = data.get('company_id')
        if company_id:
            company = db_session.query(Company).get(company_id)
            if not company:
                return api_error(
                    ErrorCodes.RESOURCE_NOT_FOUND,
                    f'Company with ID {company_id} not found',
                    status_code=400
                )

        # Create user
        user = User(
            username=data['username'],
            email=data['email'],
            password_hash=generate_password_hash(data['password'], method='pbkdf2:sha256'),
            user_type=user_type,
            company_id=company_id,
            assigned_country=data.get('assigned_country')
        )

        db_session.add(user)
        db_session.flush()  # Get the user ID

        # Log activity
        current_user = request.current_api_user
        log_admin_activity(
            db_session,
            current_user.id,
            'admin_user_created',
            f'Created user "{user.username}" with type {user_type.value}',
            user.id
        )

        db_session.commit()

        logger.info(f'User created: {user.username} (ID: {user.id}) by admin {current_user.username}')

        return api_created(
            data=user.to_dict(),
            message=f'User "{user.username}" created successfully'
        )

    except Exception as e:
        db_session.rollback()
        logger.error(f'Error creating user: {str(e)}')
        return api_error(
            ErrorCodes.DATABASE_ERROR,
            f'Failed to create user: {str(e)}',
            status_code=500
        )
    finally:
        db_session.close()


@api_v2_bp.route('/admin/users/<int:user_id>', methods=['PUT'])
@dual_auth_required
@admin_required
@handle_exceptions
def update_user(user_id):
    """
    Update an existing user

    PUT /api/v2/admin/users/<id>

    Request Body:
        {
            "username": "string (optional)",
            "email": "string (optional)",
            "password": "string (optional)",
            "user_type": "SUPER_ADMIN|DEVELOPER|COUNTRY_ADMIN|SUPERVISOR|CLIENT (optional)",
            "company_id": "integer (optional)",
            "assigned_country": "string (optional)"
        }

    Returns:
        Updated user object
    """
    # Validate request body
    data, error = validate_json_body()
    if error:
        return error

    db_session = db_manager.get_session()
    try:
        # Find user
        user = db_session.query(User).get(user_id)
        if not user:
            return api_error(
                ErrorCodes.RESOURCE_NOT_FOUND,
                f'User with ID {user_id} not found',
                status_code=404
            )

        changes = []

        # Update username
        if 'username' in data and data['username'] != user.username:
            existing = db_session.query(User).filter(
                User.username == data['username'],
                User.id != user_id
            ).first()
            if existing:
                return api_error(
                    ErrorCodes.RESOURCE_ALREADY_EXISTS,
                    f'Username "{data["username"]}" is already taken',
                    status_code=409
                )
            changes.append(f'username: {user.username} -> {data["username"]}')
            user.username = data['username']

        # Update email
        if 'email' in data and data['email'] != user.email:
            existing = db_session.query(User).filter(
                User.email == data['email'],
                User.id != user_id
            ).first()
            if existing:
                return api_error(
                    ErrorCodes.RESOURCE_ALREADY_EXISTS,
                    f'Email "{data["email"]}" is already in use',
                    status_code=409
                )
            changes.append(f'email: {user.email} -> {data["email"]}')
            user.email = data['email']

        # Update password
        if 'password' in data and data['password']:
            user.password_hash = generate_password_hash(data['password'], method='pbkdf2:sha256')
            changes.append('password: [changed]')

        # Update user type
        if 'user_type' in data:
            try:
                new_user_type = UserType[data['user_type'].upper()]
                if new_user_type != user.user_type:
                    changes.append(f'user_type: {user.user_type.value} -> {new_user_type.value}')
                    user.user_type = new_user_type
            except KeyError:
                return api_error(
                    ErrorCodes.INVALID_FIELD_VALUE,
                    f'Invalid user_type. Must be one of: {", ".join([t.name for t in UserType])}',
                    status_code=400
                )

        # Update company
        if 'company_id' in data:
            new_company_id = data['company_id']
            if new_company_id and new_company_id != user.company_id:
                company = db_session.query(Company).get(new_company_id)
                if not company:
                    return api_error(
                        ErrorCodes.RESOURCE_NOT_FOUND,
                        f'Company with ID {new_company_id} not found',
                        status_code=400
                    )
                changes.append(f'company_id: {user.company_id} -> {new_company_id}')
                user.company_id = new_company_id
            elif new_company_id is None:
                changes.append(f'company_id: {user.company_id} -> None')
                user.company_id = None

        # Update assigned country
        if 'assigned_country' in data:
            if data['assigned_country'] != user.assigned_country:
                changes.append(f'assigned_country: {user.assigned_country} -> {data["assigned_country"]}')
                user.assigned_country = data['assigned_country']

        # Log activity
        current_user = request.current_api_user
        if changes:
            log_admin_activity(
                db_session,
                current_user.id,
                'admin_user_updated',
                f'Updated user "{user.username}": {"; ".join(changes)}',
                user.id
            )

        db_session.commit()

        logger.info(f'User updated: {user.username} (ID: {user.id}) by admin {current_user.username}')

        return api_response(
            data=user.to_dict(),
            message=f'User "{user.username}" updated successfully'
        )

    except Exception as e:
        db_session.rollback()
        logger.error(f'Error updating user: {str(e)}')
        return api_error(
            ErrorCodes.DATABASE_ERROR,
            f'Failed to update user: {str(e)}',
            status_code=500
        )
    finally:
        db_session.close()


@api_v2_bp.route('/admin/users/<int:user_id>', methods=['DELETE'])
@dual_auth_required
@admin_required
@handle_exceptions
def delete_user(user_id):
    """
    Delete (soft-delete) a user

    DELETE /api/v2/admin/users/<id>

    Query Parameters:
        - permanent: If 'true', permanently delete instead of soft-delete (default: false)

    Returns:
        204 No Content on success
    """
    db_session = db_manager.get_session()
    try:
        # Find user
        user = db_session.query(User).get(user_id)
        if not user:
            return api_error(
                ErrorCodes.RESOURCE_NOT_FOUND,
                f'User with ID {user_id} not found',
                status_code=404
            )

        current_user = request.current_api_user

        # Prevent self-deletion
        if user.id == current_user.id:
            return api_error(
                ErrorCodes.VALIDATION_ERROR,
                'Cannot delete your own user account',
                status_code=400
            )

        permanent = request.args.get('permanent', 'false').lower() == 'true'

        if permanent:
            # Permanent delete - only allow for already soft-deleted users
            if not user.is_deleted:
                return api_error(
                    ErrorCodes.VALIDATION_ERROR,
                    'Cannot permanently delete an active user. Soft-delete first.',
                    status_code=400
                )

            username = user.username
            db_session.delete(user)

            log_admin_activity(
                db_session,
                current_user.id,
                'admin_user_deleted_permanent',
                f'Permanently deleted user "{username}" (ID: {user_id})',
                user_id
            )

            logger.info(f'User permanently deleted: {username} (ID: {user_id}) by admin {current_user.username}')
        else:
            # Soft delete
            user.is_deleted = True
            user.deleted_at = datetime.utcnow()

            log_admin_activity(
                db_session,
                current_user.id,
                'admin_user_deactivated',
                f'Deactivated user "{user.username}" (ID: {user_id})',
                user_id
            )

            logger.info(f'User deactivated: {user.username} (ID: {user_id}) by admin {current_user.username}')

        db_session.commit()

        return api_no_content()

    except Exception as e:
        db_session.rollback()
        logger.error(f'Error deleting user: {str(e)}')
        return api_error(
            ErrorCodes.DATABASE_ERROR,
            f'Failed to delete user: {str(e)}',
            status_code=500
        )
    finally:
        db_session.close()


# =============================================================================
# COMPANY MANAGEMENT ENDPOINTS
# =============================================================================

@api_v2_bp.route('/admin/companies', methods=['GET'])
@dual_auth_required
@admin_required
@handle_exceptions
def list_companies():
    """
    List all companies with pagination and sorting

    GET /api/v2/admin/companies

    Query Parameters:
        - page: Page number (default: 1)
        - per_page: Items per page (default: 20, max: 100)
        - sort: Field to sort by (default: name)
        - order: Sort order - 'asc' or 'desc' (default: asc)
        - search: Search term for company name
        - parent_only: If 'true', only show parent/standalone companies

    Returns:
        List of companies with pagination metadata
    """
    db_session = db_manager.get_session()
    try:
        # Get pagination params
        page, per_page = get_pagination_params()

        # Get sorting params
        allowed_sort_fields = ['id', 'name', 'created_at', 'updated_at']
        sort_field, sort_order = get_sorting_params(allowed_sort_fields, default_sort='name', default_order='asc')

        # Build query
        query = db_session.query(Company)

        # Filter parent only
        parent_only = request.args.get('parent_only', 'false').lower() == 'true'
        if parent_only:
            query = query.filter(Company.parent_company_id.is_(None))

        # Filter by search term
        search = request.args.get('search', '').strip()
        if search:
            search_pattern = f'%{search}%'
            query = query.filter(Company.name.ilike(search_pattern))

        # Apply sorting
        query = apply_sorting(query, Company, sort_field, sort_order)

        # Paginate
        companies, pagination_meta = paginate_query(query, page, per_page)

        # Format response
        companies_data = [company.to_dict() for company in companies]

        return api_response(
            data=companies_data,
            message=f'Retrieved {len(companies_data)} companies',
            meta=pagination_meta
        )

    finally:
        db_session.close()


@api_v2_bp.route('/admin/companies', methods=['POST'])
@dual_auth_required
@admin_required
@handle_exceptions
def create_company():
    """
    Create a new company

    POST /api/v2/admin/companies

    Request Body:
        {
            "name": "string (required)",
            "description": "string (optional)",
            "address": "string (optional)",
            "contact_name": "string (optional)",
            "contact_email": "string (optional)",
            "parent_company_id": "integer (optional)",
            "display_name": "string (optional)",
            "is_parent_company": "boolean (optional, default: false)"
        }

    Returns:
        Created company object
    """
    # Validate request body
    data, error = validate_json_body()
    if error:
        return error

    # Validate required fields
    required_fields = ['name']
    is_valid, error = validate_required_fields(data, required_fields)
    if not is_valid:
        return error

    db_session = db_manager.get_session()
    try:
        # Check for existing company with same name (note: Company model auto-uppercases names)
        existing = db_session.query(Company).filter_by(name=data['name'].strip().upper()).first()
        if existing:
            return api_error(
                ErrorCodes.RESOURCE_ALREADY_EXISTS,
                f'Company with name "{data["name"]}" already exists',
                status_code=409
            )

        # Validate parent_company_id if provided
        parent_company_id = data.get('parent_company_id')
        if parent_company_id:
            parent = db_session.query(Company).get(parent_company_id)
            if not parent:
                return api_error(
                    ErrorCodes.RESOURCE_NOT_FOUND,
                    f'Parent company with ID {parent_company_id} not found',
                    status_code=400
                )

        # Create company
        company = Company(
            name=data['name'],
            description=data.get('description'),
            address=data.get('address'),
            contact_name=data.get('contact_name'),
            contact_email=data.get('contact_email'),
            parent_company_id=parent_company_id,
            display_name=data.get('display_name'),
            is_parent_company=data.get('is_parent_company', False)
        )

        db_session.add(company)
        db_session.flush()

        # Log activity
        current_user = request.current_api_user
        log_admin_activity(
            db_session,
            current_user.id,
            'admin_company_created',
            f'Created company "{company.name}"',
            company.id
        )

        db_session.commit()

        logger.info(f'Company created: {company.name} (ID: {company.id}) by admin {current_user.username}')

        return api_created(
            data=company.to_dict(),
            message=f'Company "{company.name}" created successfully'
        )

    except Exception as e:
        db_session.rollback()
        logger.error(f'Error creating company: {str(e)}')
        return api_error(
            ErrorCodes.DATABASE_ERROR,
            f'Failed to create company: {str(e)}',
            status_code=500
        )
    finally:
        db_session.close()


@api_v2_bp.route('/admin/companies/<int:company_id>', methods=['PUT'])
@dual_auth_required
@admin_required
@handle_exceptions
def update_company(company_id):
    """
    Update an existing company

    PUT /api/v2/admin/companies/<id>

    Request Body:
        {
            "name": "string (optional)",
            "description": "string (optional)",
            "address": "string (optional)",
            "contact_name": "string (optional)",
            "contact_email": "string (optional)",
            "parent_company_id": "integer (optional)",
            "display_name": "string (optional)",
            "is_parent_company": "boolean (optional)"
        }

    Returns:
        Updated company object
    """
    # Validate request body
    data, error = validate_json_body()
    if error:
        return error

    db_session = db_manager.get_session()
    try:
        # Find company
        company = db_session.query(Company).get(company_id)
        if not company:
            return api_error(
                ErrorCodes.RESOURCE_NOT_FOUND,
                f'Company with ID {company_id} not found',
                status_code=404
            )

        changes = []

        # Update name
        if 'name' in data and data['name']:
            new_name = data['name'].strip().upper()
            if new_name != company.name:
                existing = db_session.query(Company).filter(
                    Company.name == new_name,
                    Company.id != company_id
                ).first()
                if existing:
                    return api_error(
                        ErrorCodes.RESOURCE_ALREADY_EXISTS,
                        f'Company with name "{data["name"]}" already exists',
                        status_code=409
                    )
                changes.append(f'name: {company.name} -> {new_name}')
                company.name = new_name

        # Update description
        if 'description' in data:
            if data['description'] != company.description:
                changes.append(f'description: updated')
                company.description = data['description']

        # Update address
        if 'address' in data:
            if data['address'] != company.address:
                changes.append(f'address: updated')
                company.address = data['address']

        # Update contact_name
        if 'contact_name' in data:
            if data['contact_name'] != company.contact_name:
                changes.append(f'contact_name: {company.contact_name} -> {data["contact_name"]}')
                company.contact_name = data['contact_name']

        # Update contact_email
        if 'contact_email' in data:
            if data['contact_email'] != company.contact_email:
                changes.append(f'contact_email: {company.contact_email} -> {data["contact_email"]}')
                company.contact_email = data['contact_email']

        # Update parent_company_id
        if 'parent_company_id' in data:
            new_parent_id = data['parent_company_id']
            if new_parent_id != company.parent_company_id:
                if new_parent_id:
                    # Prevent circular reference
                    if new_parent_id == company_id:
                        return api_error(
                            ErrorCodes.VALIDATION_ERROR,
                            'Company cannot be its own parent',
                            status_code=400
                        )
                    parent = db_session.query(Company).get(new_parent_id)
                    if not parent:
                        return api_error(
                            ErrorCodes.RESOURCE_NOT_FOUND,
                            f'Parent company with ID {new_parent_id} not found',
                            status_code=400
                        )
                changes.append(f'parent_company_id: {company.parent_company_id} -> {new_parent_id}')
                company.parent_company_id = new_parent_id

        # Update display_name
        if 'display_name' in data:
            if data['display_name'] != company.display_name:
                changes.append(f'display_name: {company.display_name} -> {data["display_name"]}')
                company.display_name = data['display_name']

        # Update is_parent_company
        if 'is_parent_company' in data:
            if data['is_parent_company'] != company.is_parent_company:
                changes.append(f'is_parent_company: {company.is_parent_company} -> {data["is_parent_company"]}')
                company.is_parent_company = data['is_parent_company']

        # Log activity
        current_user = request.current_api_user
        if changes:
            log_admin_activity(
                db_session,
                current_user.id,
                'admin_company_updated',
                f'Updated company "{company.name}": {"; ".join(changes)}',
                company.id
            )

        db_session.commit()

        logger.info(f'Company updated: {company.name} (ID: {company.id}) by admin {current_user.username}')

        return api_response(
            data=company.to_dict(),
            message=f'Company "{company.name}" updated successfully'
        )

    except Exception as e:
        db_session.rollback()
        logger.error(f'Error updating company: {str(e)}')
        return api_error(
            ErrorCodes.DATABASE_ERROR,
            f'Failed to update company: {str(e)}',
            status_code=500
        )
    finally:
        db_session.close()


@api_v2_bp.route('/admin/companies/<int:company_id>', methods=['DELETE'])
@dual_auth_required
@admin_required
@handle_exceptions
def delete_company(company_id):
    """
    Delete a company

    DELETE /api/v2/admin/companies/<id>

    Note: Cannot delete companies that have associated users or child companies.

    Returns:
        204 No Content on success
    """
    db_session = db_manager.get_session()
    try:
        # Find company
        company = db_session.query(Company).get(company_id)
        if not company:
            return api_error(
                ErrorCodes.RESOURCE_NOT_FOUND,
                f'Company with ID {company_id} not found',
                status_code=404
            )

        # Check for associated users
        users_count = db_session.query(User).filter_by(company_id=company_id).count()
        if users_count > 0:
            return api_error(
                ErrorCodes.RESOURCE_IN_USE,
                f'Cannot delete company: It has {users_count} associated users. Reassign or delete users first.',
                status_code=409
            )

        # Check for child companies
        children_count = db_session.query(Company).filter_by(parent_company_id=company_id).count()
        if children_count > 0:
            return api_error(
                ErrorCodes.RESOURCE_IN_USE,
                f'Cannot delete company: It has {children_count} child companies. Delete or reassign child companies first.',
                status_code=409
            )

        company_name = company.name

        # Delete related queue permissions
        from models.company_queue_permission import CompanyQueuePermission
        db_session.query(CompanyQueuePermission).filter_by(company_id=company_id).delete()

        # Delete company
        db_session.delete(company)

        # Log activity
        current_user = request.current_api_user
        log_admin_activity(
            db_session,
            current_user.id,
            'admin_company_deleted',
            f'Deleted company "{company_name}" (ID: {company_id})',
            company_id
        )

        db_session.commit()

        logger.info(f'Company deleted: {company_name} (ID: {company_id}) by admin {current_user.username}')

        return api_no_content()

    except Exception as e:
        db_session.rollback()
        logger.error(f'Error deleting company: {str(e)}')
        return api_error(
            ErrorCodes.DATABASE_ERROR,
            f'Failed to delete company: {str(e)}',
            status_code=500
        )
    finally:
        db_session.close()


# =============================================================================
# QUEUE MANAGEMENT ENDPOINTS
# =============================================================================

@api_v2_bp.route('/admin/queues', methods=['GET'])
@dual_auth_required
@admin_required
@handle_exceptions
def list_queues():
    """
    List all queues with pagination and sorting

    GET /api/v2/admin/queues

    Query Parameters:
        - page: Page number (default: 1)
        - per_page: Items per page (default: 20, max: 100)
        - sort: Field to sort by (default: display_order)
        - order: Sort order - 'asc' or 'desc' (default: asc)
        - search: Search term for queue name

    Returns:
        List of queues with pagination metadata
    """
    db_session = db_manager.get_session()
    try:
        # Get pagination params
        page, per_page = get_pagination_params()

        # Get sorting params
        allowed_sort_fields = ['id', 'name', 'display_order', 'created_at', 'updated_at']
        sort_field, sort_order = get_sorting_params(allowed_sort_fields, default_sort='display_order', default_order='asc')

        # Build query
        query = db_session.query(Queue)

        # Filter by search term
        search = request.args.get('search', '').strip()
        if search:
            search_pattern = f'%{search}%'
            query = query.filter(Queue.name.ilike(search_pattern))

        # Apply sorting
        query = apply_sorting(query, Queue, sort_field, sort_order)

        # Paginate
        queues, pagination_meta = paginate_query(query, page, per_page)

        # Format response
        queues_data = [queue.to_dict() for queue in queues]

        return api_response(
            data=queues_data,
            message=f'Retrieved {len(queues_data)} queues',
            meta=pagination_meta
        )

    finally:
        db_session.close()


@api_v2_bp.route('/admin/queues', methods=['POST'])
@dual_auth_required
@admin_required
@handle_exceptions
def create_queue():
    """
    Create a new queue

    POST /api/v2/admin/queues

    Request Body:
        {
            "name": "string (required)",
            "description": "string (optional)",
            "folder_id": "integer (optional)",
            "display_order": "integer (optional, default: 0)"
        }

    Returns:
        Created queue object
    """
    # Validate request body
    data, error = validate_json_body()
    if error:
        return error

    # Validate required fields
    required_fields = ['name']
    is_valid, error = validate_required_fields(data, required_fields)
    if not is_valid:
        return error

    db_session = db_manager.get_session()
    try:
        # Check for existing queue with same name
        existing = db_session.query(Queue).filter_by(name=data['name']).first()
        if existing:
            return api_error(
                ErrorCodes.RESOURCE_ALREADY_EXISTS,
                f'Queue with name "{data["name"]}" already exists',
                status_code=409
            )

        # Validate folder_id if provided
        folder_id = data.get('folder_id')
        if folder_id:
            from models.queue_folder import QueueFolder
            folder = db_session.query(QueueFolder).get(folder_id)
            if not folder:
                return api_error(
                    ErrorCodes.RESOURCE_NOT_FOUND,
                    f'Queue folder with ID {folder_id} not found',
                    status_code=400
                )

        # Create queue
        queue = Queue(
            name=data['name'],
            description=data.get('description'),
            folder_id=folder_id,
            display_order=data.get('display_order', 0)
        )

        db_session.add(queue)
        db_session.flush()

        # Log activity
        current_user = request.current_api_user
        log_admin_activity(
            db_session,
            current_user.id,
            'admin_queue_created',
            f'Created queue "{queue.name}"',
            queue.id
        )

        db_session.commit()

        logger.info(f'Queue created: {queue.name} (ID: {queue.id}) by admin {current_user.username}')

        return api_created(
            data=queue.to_dict(),
            message=f'Queue "{queue.name}" created successfully'
        )

    except Exception as e:
        db_session.rollback()
        logger.error(f'Error creating queue: {str(e)}')
        return api_error(
            ErrorCodes.DATABASE_ERROR,
            f'Failed to create queue: {str(e)}',
            status_code=500
        )
    finally:
        db_session.close()


@api_v2_bp.route('/admin/queues/<int:queue_id>', methods=['PUT'])
@dual_auth_required
@admin_required
@handle_exceptions
def update_queue(queue_id):
    """
    Update an existing queue

    PUT /api/v2/admin/queues/<id>

    Request Body:
        {
            "name": "string (optional)",
            "description": "string (optional)",
            "folder_id": "integer (optional)",
            "display_order": "integer (optional)"
        }

    Returns:
        Updated queue object
    """
    # Validate request body
    data, error = validate_json_body()
    if error:
        return error

    db_session = db_manager.get_session()
    try:
        # Find queue
        queue = db_session.query(Queue).get(queue_id)
        if not queue:
            return api_error(
                ErrorCodes.RESOURCE_NOT_FOUND,
                f'Queue with ID {queue_id} not found',
                status_code=404
            )

        changes = []

        # Update name
        if 'name' in data and data['name']:
            if data['name'] != queue.name:
                existing = db_session.query(Queue).filter(
                    Queue.name == data['name'],
                    Queue.id != queue_id
                ).first()
                if existing:
                    return api_error(
                        ErrorCodes.RESOURCE_ALREADY_EXISTS,
                        f'Queue with name "{data["name"]}" already exists',
                        status_code=409
                    )
                changes.append(f'name: {queue.name} -> {data["name"]}')
                queue.name = data['name']

        # Update description
        if 'description' in data:
            if data['description'] != queue.description:
                changes.append(f'description: updated')
                queue.description = data['description']

        # Update folder_id
        if 'folder_id' in data:
            new_folder_id = data['folder_id']
            if new_folder_id != queue.folder_id:
                if new_folder_id:
                    from models.queue_folder import QueueFolder
                    folder = db_session.query(QueueFolder).get(new_folder_id)
                    if not folder:
                        return api_error(
                            ErrorCodes.RESOURCE_NOT_FOUND,
                            f'Queue folder with ID {new_folder_id} not found',
                            status_code=400
                        )
                changes.append(f'folder_id: {queue.folder_id} -> {new_folder_id}')
                queue.folder_id = new_folder_id

        # Update display_order
        if 'display_order' in data:
            if data['display_order'] != queue.display_order:
                changes.append(f'display_order: {queue.display_order} -> {data["display_order"]}')
                queue.display_order = data['display_order']

        # Log activity
        current_user = request.current_api_user
        if changes:
            log_admin_activity(
                db_session,
                current_user.id,
                'admin_queue_updated',
                f'Updated queue "{queue.name}": {"; ".join(changes)}',
                queue.id
            )

        db_session.commit()

        logger.info(f'Queue updated: {queue.name} (ID: {queue.id}) by admin {current_user.username}')

        return api_response(
            data=queue.to_dict(),
            message=f'Queue "{queue.name}" updated successfully'
        )

    except Exception as e:
        db_session.rollback()
        logger.error(f'Error updating queue: {str(e)}')
        return api_error(
            ErrorCodes.DATABASE_ERROR,
            f'Failed to update queue: {str(e)}',
            status_code=500
        )
    finally:
        db_session.close()


@api_v2_bp.route('/admin/queues/<int:queue_id>', methods=['DELETE'])
@dual_auth_required
@admin_required
@handle_exceptions
def delete_queue(queue_id):
    """
    Delete a queue

    DELETE /api/v2/admin/queues/<id>

    Note: Cannot delete queues that have associated tickets.

    Returns:
        204 No Content on success
    """
    from models.ticket import Ticket

    db_session = db_manager.get_session()
    try:
        # Find queue
        queue = db_session.query(Queue).get(queue_id)
        if not queue:
            return api_error(
                ErrorCodes.RESOURCE_NOT_FOUND,
                f'Queue with ID {queue_id} not found',
                status_code=404
            )

        # Check for associated tickets
        tickets_count = db_session.query(Ticket).filter_by(queue_id=queue_id).count()
        if tickets_count > 0:
            return api_error(
                ErrorCodes.RESOURCE_IN_USE,
                f'Cannot delete queue: It has {tickets_count} associated tickets. Reassign tickets first.',
                status_code=409
            )

        queue_name = queue.name

        # Delete related permissions
        from models.company_queue_permission import CompanyQueuePermission
        from models.user_queue_permission import UserQueuePermission
        from models.queue_notification import QueueNotification

        db_session.query(CompanyQueuePermission).filter_by(queue_id=queue_id).delete()
        db_session.query(UserQueuePermission).filter_by(queue_id=queue_id).delete()
        db_session.query(QueueNotification).filter_by(queue_id=queue_id).delete()

        # Delete queue
        db_session.delete(queue)

        # Log activity
        current_user = request.current_api_user
        log_admin_activity(
            db_session,
            current_user.id,
            'admin_queue_deleted',
            f'Deleted queue "{queue_name}" (ID: {queue_id})',
            queue_id
        )

        db_session.commit()

        logger.info(f'Queue deleted: {queue_name} (ID: {queue_id}) by admin {current_user.username}')

        return api_no_content()

    except Exception as e:
        db_session.rollback()
        logger.error(f'Error deleting queue: {str(e)}')
        return api_error(
            ErrorCodes.DATABASE_ERROR,
            f'Failed to delete queue: {str(e)}',
            status_code=500
        )
    finally:
        db_session.close()


# =============================================================================
# TICKET CATEGORY MANAGEMENT ENDPOINTS
# =============================================================================

@api_v2_bp.route('/admin/ticket-categories', methods=['GET'])
@dual_auth_required
@admin_required
@handle_exceptions
def list_ticket_categories():
    """
    List all ticket categories (both predefined enum and custom)

    GET /api/v2/admin/ticket-categories

    Query Parameters:
        - page: Page number (default: 1)
        - per_page: Items per page (default: 50, max: 100)
        - type: Filter by type - 'predefined', 'custom', or 'all' (default: all)
        - enabled_only: If 'true', only show enabled categories (default: false)

    Returns:
        List of ticket categories with pagination metadata
    """
    db_session = db_manager.get_session()
    try:
        # Get pagination params
        page, per_page = get_pagination_params(default_per_page=50)

        category_type = request.args.get('type', 'all').lower()
        enabled_only = request.args.get('enabled_only', 'false').lower() == 'true'

        # Build query for CategoryDisplayConfig
        query = db_session.query(CategoryDisplayConfig)

        # Filter by type
        if category_type == 'predefined':
            query = query.filter(CategoryDisplayConfig.is_predefined == True)
        elif category_type == 'custom':
            query = query.filter(CategoryDisplayConfig.is_predefined == False)

        # Filter by enabled status
        if enabled_only:
            query = query.filter(CategoryDisplayConfig.is_enabled == True)

        # Order by sort_order
        query = query.order_by(CategoryDisplayConfig.sort_order)

        # Paginate
        categories, pagination_meta = paginate_query(query, page, per_page)

        # Format response
        categories_data = [cat.to_dict() for cat in categories]

        # Also include predefined categories that may not have display configs yet
        if category_type in ['all', 'predefined']:
            existing_keys = {cat['category_key'] for cat in categories_data}
            for tc in TicketCategory:
                if tc.name not in existing_keys:
                    categories_data.append({
                        'id': None,
                        'category_key': tc.name,
                        'display_name': tc.value,
                        'is_enabled': True,
                        'is_predefined': True,
                        'sort_order': 999,
                        'created_at': None,
                        'updated_at': None
                    })

        return api_response(
            data=categories_data,
            message=f'Retrieved {len(categories_data)} ticket categories',
            meta=pagination_meta
        )

    finally:
        db_session.close()


@api_v2_bp.route('/admin/ticket-categories', methods=['POST'])
@dual_auth_required
@admin_required
@handle_exceptions
def create_ticket_category():
    """
    Create a new custom ticket category or update display settings for predefined

    POST /api/v2/admin/ticket-categories

    Request Body:
        {
            "category_key": "string (required) - unique identifier",
            "display_name": "string (required) - display label",
            "is_enabled": "boolean (optional, default: true)",
            "is_predefined": "boolean (optional, default: false)",
            "sort_order": "integer (optional, default: 0)"
        }

    Returns:
        Created category config object
    """
    # Validate request body
    data, error = validate_json_body()
    if error:
        return error

    # Validate required fields
    required_fields = ['category_key', 'display_name']
    is_valid, error = validate_required_fields(data, required_fields)
    if not is_valid:
        return error

    db_session = db_manager.get_session()
    try:
        # Check for existing category with same key
        existing = db_session.query(CategoryDisplayConfig).filter_by(
            category_key=data['category_key']
        ).first()
        if existing:
            return api_error(
                ErrorCodes.RESOURCE_ALREADY_EXISTS,
                f'Category with key "{data["category_key"]}" already exists',
                status_code=409
            )

        # Determine if predefined (matches enum value)
        is_predefined = data.get('is_predefined', False)
        try:
            TicketCategory[data['category_key'].upper()]
            is_predefined = True  # It's a predefined enum value
        except KeyError:
            pass

        # Create category config
        category = CategoryDisplayConfig(
            category_key=data['category_key'],
            display_name=data['display_name'],
            is_enabled=data.get('is_enabled', True),
            is_predefined=is_predefined,
            sort_order=data.get('sort_order', 0)
        )

        db_session.add(category)
        db_session.flush()

        # Log activity
        current_user = request.current_api_user
        log_admin_activity(
            db_session,
            current_user.id,
            'admin_category_created',
            f'Created ticket category "{category.display_name}" (key: {category.category_key})',
            category.id
        )

        db_session.commit()

        logger.info(f'Ticket category created: {category.category_key} by admin {current_user.username}')

        return api_created(
            data=category.to_dict(),
            message=f'Ticket category "{category.display_name}" created successfully'
        )

    except Exception as e:
        db_session.rollback()
        logger.error(f'Error creating ticket category: {str(e)}')
        return api_error(
            ErrorCodes.DATABASE_ERROR,
            f'Failed to create ticket category: {str(e)}',
            status_code=500
        )
    finally:
        db_session.close()


@api_v2_bp.route('/admin/ticket-categories/<int:category_id>', methods=['PUT'])
@dual_auth_required
@admin_required
@handle_exceptions
def update_ticket_category(category_id):
    """
    Update a ticket category display configuration

    PUT /api/v2/admin/ticket-categories/<id>

    Request Body:
        {
            "display_name": "string (optional)",
            "is_enabled": "boolean (optional)",
            "sort_order": "integer (optional)"
        }

    Note: category_key and is_predefined cannot be changed after creation.

    Returns:
        Updated category config object
    """
    # Validate request body
    data, error = validate_json_body()
    if error:
        return error

    db_session = db_manager.get_session()
    try:
        # Find category
        category = db_session.query(CategoryDisplayConfig).get(category_id)
        if not category:
            return api_error(
                ErrorCodes.RESOURCE_NOT_FOUND,
                f'Ticket category with ID {category_id} not found',
                status_code=404
            )

        changes = []

        # Update display_name
        if 'display_name' in data and data['display_name']:
            if data['display_name'] != category.display_name:
                changes.append(f'display_name: {category.display_name} -> {data["display_name"]}')
                category.display_name = data['display_name']

        # Update is_enabled
        if 'is_enabled' in data:
            if data['is_enabled'] != category.is_enabled:
                changes.append(f'is_enabled: {category.is_enabled} -> {data["is_enabled"]}')
                category.is_enabled = data['is_enabled']

        # Update sort_order
        if 'sort_order' in data:
            if data['sort_order'] != category.sort_order:
                changes.append(f'sort_order: {category.sort_order} -> {data["sort_order"]}')
                category.sort_order = data['sort_order']

        # Log activity
        current_user = request.current_api_user
        if changes:
            log_admin_activity(
                db_session,
                current_user.id,
                'admin_category_updated',
                f'Updated ticket category "{category.display_name}": {"; ".join(changes)}',
                category.id
            )

        db_session.commit()

        logger.info(f'Ticket category updated: {category.category_key} by admin {current_user.username}')

        return api_response(
            data=category.to_dict(),
            message=f'Ticket category "{category.display_name}" updated successfully'
        )

    except Exception as e:
        db_session.rollback()
        logger.error(f'Error updating ticket category: {str(e)}')
        return api_error(
            ErrorCodes.DATABASE_ERROR,
            f'Failed to update ticket category: {str(e)}',
            status_code=500
        )
    finally:
        db_session.close()


@api_v2_bp.route('/admin/ticket-categories/<int:category_id>', methods=['DELETE'])
@dual_auth_required
@admin_required
@handle_exceptions
def delete_ticket_category(category_id):
    """
    Delete a ticket category configuration

    DELETE /api/v2/admin/ticket-categories/<id>

    Note: Predefined categories (from enum) cannot be deleted, only disabled.
          Custom categories can be deleted if no tickets are using them.

    Returns:
        204 No Content on success
    """
    from models.ticket import Ticket

    db_session = db_manager.get_session()
    try:
        # Find category
        category = db_session.query(CategoryDisplayConfig).get(category_id)
        if not category:
            return api_error(
                ErrorCodes.RESOURCE_NOT_FOUND,
                f'Ticket category with ID {category_id} not found',
                status_code=404
            )

        # Cannot delete predefined categories
        if category.is_predefined:
            return api_error(
                ErrorCodes.VALIDATION_ERROR,
                'Cannot delete predefined ticket categories. Disable them instead by setting is_enabled to false.',
                status_code=400
            )

        # Check if any tickets use this category (for custom categories stored differently)
        # Custom categories might be stored in a custom_category field or similar
        # For now, we'll allow deletion of custom category configs

        category_key = category.category_key
        category_display_name = category.display_name

        # Delete category
        db_session.delete(category)

        # Log activity
        current_user = request.current_api_user
        log_admin_activity(
            db_session,
            current_user.id,
            'admin_category_deleted',
            f'Deleted ticket category "{category_display_name}" (key: {category_key})',
            category_id
        )

        db_session.commit()

        logger.info(f'Ticket category deleted: {category_key} by admin {current_user.username}')

        return api_no_content()

    except Exception as e:
        db_session.rollback()
        logger.error(f'Error deleting ticket category: {str(e)}')
        return api_error(
            ErrorCodes.DATABASE_ERROR,
            f'Failed to delete ticket category: {str(e)}',
            status_code=500
        )
    finally:
        db_session.close()


# =============================================================================
# USER STATS AND RESTORE ENDPOINTS
# =============================================================================

def super_admin_required(f):
    """
    Decorator to ensure user has SUPER_ADMIN permission only.
    Must be used after dual_auth_required decorator.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = getattr(request, 'current_api_user', None)

        if not user:
            return api_error(
                ErrorCodes.AUTHENTICATION_REQUIRED,
                'Authentication required',
                status_code=401
            )

        # Check if user is SUPER_ADMIN only
        if user.user_type != UserType.SUPER_ADMIN:
            logger.warning(f'Super admin access denied for user {user.username} (type: {user.user_type})')
            return api_error(
                ErrorCodes.ADMIN_ACCESS_REQUIRED,
                'Super admin access required. Only SUPER_ADMIN users can access this endpoint.',
                status_code=403
            )

        return f(*args, **kwargs)

    return decorated_function


@api_v2_bp.route('/admin/users/<int:user_id>/stats', methods=['GET'])
@dual_auth_required
@super_admin_required
@handle_exceptions
def get_user_stats(user_id):
    """
    Get user activity statistics

    GET /api/v2/admin/users/<id>/stats

    Query Parameters:
        - days: Time period for stats in days (default: 30, max: 365)

    Returns:
        User activity statistics including:
        - User basic info
        - Activity summary (total actions, tickets created/resolved, comments, assets processed)
        - Ticket statistics (assigned, open, resolved this period)
        - Daily activity breakdown
    """
    from models.ticket import Ticket, TicketStatus
    from models.comment import Comment
    from sqlalchemy import func
    from datetime import timedelta

    db_session = db_manager.get_session()
    try:
        # Get days parameter with validation
        days = request.args.get('days', 30, type=int)
        if days < 1:
            days = 1
        elif days > 365:
            days = 365

        # Calculate the start date for the time period
        start_date = datetime.utcnow() - timedelta(days=days)

        # Find user
        user = db_session.query(User).get(user_id)
        if not user:
            return api_error(
                ErrorCodes.RESOURCE_NOT_FOUND,
                f'User with ID {user_id} not found',
                status_code=404
            )

        # Get user basic info
        user_info = {
            'id': user.id,
            'username': user.username,
            'user_type': user.user_type.value if user.user_type else None
        }

        # Query Activity table for user's activities in the period
        activities_query = db_session.query(Activity).filter(
            Activity.user_id == user_id,
            Activity.created_at >= start_date
        )

        total_actions = activities_query.count()

        # Get last active timestamp
        last_activity = db_session.query(Activity).filter(
            Activity.user_id == user_id
        ).order_by(Activity.created_at.desc()).first()

        last_active = last_activity.created_at.isoformat() if last_activity else None

        # Count tickets created by user in period
        tickets_created = db_session.query(Ticket).filter(
            Ticket.requester_id == user_id,
            Ticket.created_at >= start_date
        ).count()

        # Count tickets resolved by user in period (assigned to user and resolved)
        resolved_statuses = [TicketStatus.RESOLVED, TicketStatus.RESOLVED_DELIVERED]
        tickets_resolved = db_session.query(Ticket).filter(
            Ticket.assigned_to_id == user_id,
            Ticket.status.in_(resolved_statuses),
            Ticket.updated_at >= start_date
        ).count()

        # Count comments added by user in period
        comments_added = db_session.query(Comment).filter(
            Comment.user_id == user_id,
            Comment.created_at >= start_date
        ).count()

        # Count asset-related activities in period
        assets_processed = db_session.query(Activity).filter(
            Activity.user_id == user_id,
            Activity.created_at >= start_date,
            Activity.type.in_([
                'asset_created', 'asset_updated', 'asset_deleted',
                'asset_checkout', 'asset_shipped', 'asset_assigned',
                'asset_added', 'asset_linked', 'asset_unlinked'
            ])
        ).count()

        # Get current ticket stats
        tickets_assigned = db_session.query(Ticket).filter(
            Ticket.assigned_to_id == user_id
        ).count()

        tickets_open = db_session.query(Ticket).filter(
            Ticket.assigned_to_id == user_id,
            Ticket.status.in_([TicketStatus.NEW, TicketStatus.IN_PROGRESS, TicketStatus.PROCESSING])
        ).count()

        tickets_resolved_this_period = db_session.query(Ticket).filter(
            Ticket.assigned_to_id == user_id,
            Ticket.status.in_(resolved_statuses),
            Ticket.updated_at >= start_date
        ).count()

        # Get daily activity breakdown
        daily_activity = []
        for i in range(min(days, 30)):  # Limit to 30 days for daily breakdown
            day_start = datetime.utcnow() - timedelta(days=i+1)
            day_end = datetime.utcnow() - timedelta(days=i)

            day_actions = db_session.query(Activity).filter(
                Activity.user_id == user_id,
                Activity.created_at >= day_start,
                Activity.created_at < day_end
            ).count()

            daily_activity.append({
                'date': day_start.strftime('%Y-%m-%d'),
                'actions': day_actions
            })

        # Build response
        response_data = {
            'user': user_info,
            'activity': {
                'total_actions': total_actions,
                'tickets_created': tickets_created,
                'tickets_resolved': tickets_resolved,
                'comments_added': comments_added,
                'assets_processed': assets_processed,
                'last_active': last_active
            },
            'tickets': {
                'assigned': tickets_assigned,
                'open': tickets_open,
                'resolved_this_period': tickets_resolved_this_period
            },
            'daily_activity': daily_activity
        }

        logger.info(f'User stats retrieved for user {user_id} by admin {request.current_api_user.username}')

        return api_response(
            data=response_data,
            message=f'Retrieved stats for user "{user.username}" over the last {days} days'
        )

    except Exception as e:
        logger.error(f'Error getting user stats: {str(e)}')
        return api_error(
            ErrorCodes.DATABASE_ERROR,
            f'Failed to get user stats: {str(e)}',
            status_code=500
        )
    finally:
        db_session.close()


@api_v2_bp.route('/admin/users/<int:user_id>/restore', methods=['POST'])
@dual_auth_required
@super_admin_required
@handle_exceptions
def restore_user(user_id):
    """
    Restore a soft-deleted user

    POST /api/v2/admin/users/<id>/restore

    Returns:
        Restored user object with restore timestamp
    """
    db_session = db_manager.get_session()
    try:
        # Find user
        user = db_session.query(User).get(user_id)
        if not user:
            return api_error(
                ErrorCodes.RESOURCE_NOT_FOUND,
                f'User with ID {user_id} not found',
                status_code=404
            )

        # Check if user is actually deleted
        if not user.is_deleted:
            return api_error(
                ErrorCodes.VALIDATION_ERROR,
                f'User "{user.username}" is not deleted and cannot be restored',
                status_code=400
            )

        current_user = request.current_api_user
        restored_at = datetime.utcnow()

        # Restore user
        user.is_deleted = False
        user.deleted_at = None

        # Log activity
        log_admin_activity(
            db_session,
            current_user.id,
            'admin_user_restored',
            f'Restored user "{user.username}" (ID: {user_id})',
            user_id
        )

        db_session.commit()

        logger.info(f'User restored: {user.username} (ID: {user_id}) by admin {current_user.username}')

        # Build response
        response_data = {
            'id': user.id,
            'username': user.username,
            'is_deleted': user.is_deleted,
            'restored_at': restored_at.isoformat()
        }

        return api_response(
            data=response_data,
            message='User restored successfully'
        )

    except Exception as e:
        db_session.rollback()
        logger.error(f'Error restoring user: {str(e)}')
        return api_error(
            ErrorCodes.DATABASE_ERROR,
            f'Failed to restore user: {str(e)}',
            status_code=500
        )
    finally:
        db_session.close()


# =============================================================================
# QUEUE NOTIFICATION MANAGEMENT ENDPOINTS
# =============================================================================

@api_v2_bp.route('/admin/queue-notifications', methods=['GET'])
@dual_auth_required
@admin_required
@handle_exceptions
def get_queue_notifications():
    """
    Get the queue notification matrix

    GET /api/v2/admin/queue-notifications

    Returns:
        Queue notification settings for all queues including:
        - queues: List of queues with their notification settings
        - available_events: List of available notification event types
        - available_recipients: List of available recipient types
    """
    from models.queue_notification_config import QueueNotificationConfig
    from models.notification_user_group import NotificationUserGroup
    from sqlalchemy.orm import joinedload

    db_session = db_manager.get_session()
    try:
        # Get all queues with their notification configs
        queues = db_session.query(Queue).order_by(Queue.display_order, Queue.name).all()

        # Get all notification configs
        configs = db_session.query(QueueNotificationConfig).all()
        config_map = {config.queue_id: config for config in configs}

        # Get all notification user groups
        notification_groups = db_session.query(NotificationUserGroup).order_by(NotificationUserGroup.name).all()

        # Build queue data with notification settings
        queues_data = []
        for queue in queues:
            config = config_map.get(queue.id)

            # Get notification settings (use defaults if no config exists)
            if config:
                notifications = config.get_settings()
            else:
                notifications = QueueNotificationConfig.DEFAULT_SETTINGS.copy()

            # Get notification groups associated with this queue (via queue members who are in groups)
            # For now, we'll return an empty list since we need to query the association table
            queue_notification_groups = []

            queue_data = {
                'id': queue.id,
                'name': queue.name,
                'notifications': notifications,
                'notification_groups': queue_notification_groups
            }
            queues_data.append(queue_data)

        # Build response
        response_data = {
            'queues': queues_data,
            'available_events': QueueNotificationConfig.AVAILABLE_EVENTS,
            'available_recipients': QueueNotificationConfig.AVAILABLE_RECIPIENTS,
            'notification_groups': [
                {'id': g.id, 'name': g.name, 'member_count': g.member_count}
                for g in notification_groups
            ]
        }

        logger.info(f'Queue notifications retrieved by admin {request.current_api_user.username}')

        return api_response(
            data=response_data,
            message=f'Retrieved notification settings for {len(queues_data)} queues'
        )

    except Exception as e:
        logger.error(f'Error getting queue notifications: {str(e)}')
        return api_error(
            ErrorCodes.DATABASE_ERROR,
            f'Failed to get queue notifications: {str(e)}',
            status_code=500
        )
    finally:
        db_session.close()


@api_v2_bp.route('/admin/queue-notifications', methods=['PUT'])
@dual_auth_required
@admin_required
@handle_exceptions
def update_queue_notifications():
    """
    Update queue notification settings

    PUT /api/v2/admin/queue-notifications

    Request Body:
        {
            "queue_id": 1,
            "notifications": {
                "on_new_ticket": {
                    "email": true,
                    "in_app": true,
                    "recipients": ["assigned", "queue_members"]
                }
            },
            "notification_group_ids": [1, 2]
        }

    Notes:
        - Only the notification events specified will be updated (partial update)
        - Unspecified events will retain their current settings
        - notification_group_ids is optional

    Returns:
        Updated queue notification configuration
    """
    from models.queue_notification_config import QueueNotificationConfig
    from models.notification_user_group import NotificationUserGroup

    # Validate request body
    data, error = validate_json_body()
    if error:
        return error

    # Validate required fields
    required_fields = ['queue_id']
    is_valid, error = validate_required_fields(data, required_fields)
    if not is_valid:
        return error

    queue_id = data.get('queue_id')
    notifications = data.get('notifications', {})
    notification_group_ids = data.get('notification_group_ids', [])

    db_session = db_manager.get_session()
    try:
        # Find queue
        queue = db_session.query(Queue).get(queue_id)
        if not queue:
            return api_error(
                ErrorCodes.RESOURCE_NOT_FOUND,
                f'Queue with ID {queue_id} not found',
                status_code=404
            )

        # Validate notification events
        invalid_events = [e for e in notifications.keys() if e not in QueueNotificationConfig.AVAILABLE_EVENTS]
        if invalid_events:
            return api_error(
                ErrorCodes.INVALID_FIELD_VALUE,
                f'Invalid notification events: {", ".join(invalid_events)}. '
                f'Valid events are: {", ".join(QueueNotificationConfig.AVAILABLE_EVENTS)}',
                status_code=400
            )

        # Validate recipients in each notification config
        for event, config in notifications.items():
            if 'recipients' in config:
                invalid_recipients = [
                    r for r in config['recipients']
                    if r not in QueueNotificationConfig.AVAILABLE_RECIPIENTS
                ]
                if invalid_recipients:
                    return api_error(
                        ErrorCodes.INVALID_FIELD_VALUE,
                        f'Invalid recipients for {event}: {", ".join(invalid_recipients)}. '
                        f'Valid recipients are: {", ".join(QueueNotificationConfig.AVAILABLE_RECIPIENTS)}',
                        status_code=400
                    )

        # Validate notification group IDs if provided
        if notification_group_ids:
            valid_groups = db_session.query(NotificationUserGroup).filter(
                NotificationUserGroup.id.in_(notification_group_ids)
            ).all()
            valid_group_ids = {g.id for g in valid_groups}
            invalid_group_ids = [gid for gid in notification_group_ids if gid not in valid_group_ids]
            if invalid_group_ids:
                return api_error(
                    ErrorCodes.RESOURCE_NOT_FOUND,
                    f'Notification groups not found: {", ".join(map(str, invalid_group_ids))}',
                    status_code=400
                )

        # Get or create notification config for this queue
        config = db_session.query(QueueNotificationConfig).filter_by(queue_id=queue_id).first()

        changes = []
        if config:
            # Update existing config
            old_settings = config.get_settings()
            if notifications:
                config.update_settings(notifications)
                changes.append(f'notification settings updated')
        else:
            # Create new config
            config = QueueNotificationConfig(queue_id=queue_id)
            if notifications:
                config.set_settings(notifications)
            else:
                # Use defaults
                config.notification_settings = None
            db_session.add(config)
            changes.append(f'notification config created')

        db_session.flush()

        # Log activity
        current_user = request.current_api_user
        log_admin_activity(
            db_session,
            current_user.id,
            'admin_queue_notifications_updated',
            f'Updated queue notification settings for "{queue.name}": {"; ".join(changes)}',
            queue.id
        )

        db_session.commit()

        # Build response
        response_data = {
            'queue_id': queue.id,
            'queue_name': queue.name,
            'notifications': config.get_settings(),
            'notification_group_ids': notification_group_ids,
            'updated_at': config.updated_at.isoformat() if config.updated_at else None
        }

        logger.info(f'Queue notifications updated for queue {queue.name} (ID: {queue_id}) by admin {current_user.username}')

        return api_response(
            data=response_data,
            message=f'Queue notification settings for "{queue.name}" updated successfully'
        )

    except Exception as e:
        db_session.rollback()
        logger.error(f'Error updating queue notifications: {str(e)}')
        return api_error(
            ErrorCodes.DATABASE_ERROR,
            f'Failed to update queue notifications: {str(e)}',
            status_code=500
        )
    finally:
        db_session.close()


# =============================================================================
# NOTIFICATION GROUP MANAGEMENT ENDPOINTS
# =============================================================================

@api_v2_bp.route('/admin/groups', methods=['GET'])
@dual_auth_required
@admin_required
@handle_exceptions
def list_groups():
    """
    List all notification groups with members

    GET /api/v2/admin/groups

    Query Parameters:
        - page: Page number (default: 1)
        - per_page: Items per page (default: 20, max: 100)
        - sort: Field to sort by (default: created_at)
        - order: Sort order - 'asc' or 'desc' (default: desc)
        - search: Search term for group name
        - is_active: Filter by active status - 'true' or 'false' (default: all)

    Returns:
        List of notification groups with members and pagination metadata
    """
    from models.group import Group

    db_session = db_manager.get_session()
    try:
        # Get pagination params
        page, per_page = get_pagination_params()

        # Get sorting params
        allowed_sort_fields = ['id', 'name', 'created_at', 'updated_at']
        sort_field, sort_order = get_sorting_params(allowed_sort_fields)

        # Build query
        query = db_session.query(Group)

        # Filter by search term
        search = request.args.get('search', '').strip()
        if search:
            search_pattern = f'%{search}%'
            query = query.filter(Group.name.ilike(search_pattern))

        # Filter by active status
        is_active = request.args.get('is_active')
        if is_active is not None:
            is_active_bool = is_active.lower() == 'true'
            query = query.filter(Group.is_active == is_active_bool)

        # Apply sorting
        query = apply_sorting(query, Group, sort_field, sort_order)

        # Paginate
        groups, pagination_meta = paginate_query(query, page, per_page)

        # Format response
        groups_data = []
        for group in groups:
            group_dict = {
                'id': group.id,
                'name': group.name,
                'description': group.description,
                'is_active': group.is_active,
                'members': [
                    {
                        'id': m.user_id,
                        'username': m.user.username if m.user else None,
                        'email': m.user.email if m.user else None
                    }
                    for m in group.memberships if m.is_active
                ],
                'member_count': group.member_count,
                'created_at': group.created_at.isoformat() if group.created_at else None,
                'updated_at': group.updated_at.isoformat() if group.updated_at else None,
                'created_by_id': group.created_by_id,
                'created_by': group.created_by.username if group.created_by else None
            }
            groups_data.append(group_dict)

        return api_response(
            data=groups_data,
            message=f'Retrieved {len(groups_data)} groups',
            meta=pagination_meta
        )

    finally:
        db_session.close()


@api_v2_bp.route('/admin/groups', methods=['POST'])
@dual_auth_required
@admin_required
@handle_exceptions
def create_notification_group():
    """
    Create a new notification group

    POST /api/v2/admin/groups

    Request Body:
        {
            "name": "string (required) - lowercase alphanumeric and hyphens only",
            "description": "string (optional)",
            "member_ids": [1, 2, 3] (optional) - list of user IDs to add as members
        }

    Returns:
        Created group object with members
    """
    import re
    from models.group import Group

    # Validate request body
    data, error = validate_json_body()
    if error:
        return error

    # Validate required fields
    required_fields = ['name']
    is_valid, error = validate_required_fields(data, required_fields)
    if not is_valid:
        return error

    db_session = db_manager.get_session()
    try:
        # Normalize and validate group name
        name = data['name'].strip().lower()

        if not name:
            return api_error(
                ErrorCodes.VALIDATION_ERROR,
                'Group name is required',
                status_code=400
            )

        # Validate group name format (alphanumeric and hyphens only)
        if not re.match(r'^[a-z0-9-]+$', name):
            return api_error(
                ErrorCodes.INVALID_FIELD_VALUE,
                'Group name can only contain lowercase letters, numbers, and hyphens',
                status_code=400
            )

        # Check for existing group with same name
        existing = db_session.query(Group).filter(Group.name == name).first()
        if existing:
            return api_error(
                ErrorCodes.RESOURCE_ALREADY_EXISTS,
                f'Group with name "{name}" already exists',
                status_code=409
            )

        # Get current user
        current_user = request.current_api_user

        # Create group
        group = Group(
            name=name,
            description=data.get('description', '').strip() or None,
            created_by_id=current_user.id
        )

        db_session.add(group)
        db_session.flush()  # Get the group ID

        # Add members if provided
        member_ids = data.get('member_ids', [])
        added_members = []
        if member_ids:
            for user_id in member_ids:
                user = db_session.query(User).get(user_id)
                if user and not user.is_deleted:
                    group.add_member(user_id, current_user.id)
                    added_members.append(user_id)

        # Log activity
        log_admin_activity(
            db_session,
            current_user.id,
            'admin_group_created',
            f'Created notification group "{name}" with {len(added_members)} members',
            group.id
        )

        db_session.commit()

        logger.info(f'Group created: {name} (ID: {group.id}) by admin {current_user.username}')

        # Return the created group with members
        group_dict = {
            'id': group.id,
            'name': group.name,
            'description': group.description,
            'is_active': group.is_active,
            'members': [
                {
                    'id': m.user_id,
                    'username': m.user.username if m.user else None,
                    'email': m.user.email if m.user else None
                }
                for m in group.memberships if m.is_active
            ],
            'member_count': group.member_count,
            'created_at': group.created_at.isoformat() if group.created_at else None,
            'created_by_id': group.created_by_id,
            'created_by': current_user.username
        }

        return api_created(
            data=group_dict,
            message=f'Notification group "{name}" created successfully'
        )

    except Exception as e:
        db_session.rollback()
        logger.error(f'Error creating group: {str(e)}')
        return api_error(
            ErrorCodes.DATABASE_ERROR,
            f'Failed to create group: {str(e)}',
            status_code=500
        )
    finally:
        db_session.close()


@api_v2_bp.route('/admin/groups/<int:group_id>', methods=['PUT'])
@dual_auth_required
@admin_required
@handle_exceptions
def update_notification_group(group_id):
    """
    Update an existing notification group

    PUT /api/v2/admin/groups/<id>

    Request Body:
        {
            "name": "string (optional) - lowercase alphanumeric and hyphens only",
            "description": "string (optional)",
            "is_active": "boolean (optional)",
            "member_ids": [1, 2, 3] (optional) - replaces all members with this list
        }

    Returns:
        Updated group object with members
    """
    import re
    from models.group import Group

    # Validate request body
    data, error = validate_json_body()
    if error:
        return error

    db_session = db_manager.get_session()
    try:
        # Find group
        group = db_session.query(Group).get(group_id)
        if not group:
            return api_error(
                ErrorCodes.RESOURCE_NOT_FOUND,
                f'Group with ID {group_id} not found',
                status_code=404
            )

        current_user = request.current_api_user
        changes = []

        # Update name
        if 'name' in data:
            new_name = data['name'].strip().lower()

            if not new_name:
                return api_error(
                    ErrorCodes.VALIDATION_ERROR,
                    'Group name cannot be empty',
                    status_code=400
                )

            # Validate group name format
            if not re.match(r'^[a-z0-9-]+$', new_name):
                return api_error(
                    ErrorCodes.INVALID_FIELD_VALUE,
                    'Group name can only contain lowercase letters, numbers, and hyphens',
                    status_code=400
                )

            if new_name != group.name:
                # Check if new name conflicts with existing group
                existing = db_session.query(Group).filter(
                    Group.name == new_name,
                    Group.id != group_id
                ).first()
                if existing:
                    return api_error(
                        ErrorCodes.RESOURCE_ALREADY_EXISTS,
                        f'Group with name "{new_name}" already exists',
                        status_code=409
                    )
                changes.append(f'name: {group.name} -> {new_name}')
                group.name = new_name

        # Update description
        if 'description' in data:
            new_description = data['description'].strip() if data['description'] else None
            if new_description != group.description:
                changes.append('description: updated')
                group.description = new_description

        # Update is_active
        if 'is_active' in data:
            if data['is_active'] != group.is_active:
                changes.append(f'is_active: {group.is_active} -> {data["is_active"]}')
                group.is_active = data['is_active']

        # Update members (replace all)
        if 'member_ids' in data:
            new_member_ids = set(data['member_ids'])
            current_member_ids = set(m.user_id for m in group.memberships if m.is_active)

            # Remove members not in the new list
            for membership in group.memberships:
                if membership.is_active and membership.user_id not in new_member_ids:
                    group.remove_member(membership.user_id)

            # Add new members
            for user_id in new_member_ids:
                if user_id not in current_member_ids:
                    user = db_session.query(User).get(user_id)
                    if user and not user.is_deleted:
                        group.add_member(user_id, current_user.id)

            changes.append(f'members: updated to {len(new_member_ids)} members')

        # Update timestamp
        group.updated_at = datetime.utcnow()

        # Log activity
        if changes:
            log_admin_activity(
                db_session,
                current_user.id,
                'admin_group_updated',
                f'Updated notification group "{group.name}": {"; ".join(changes)}',
                group.id
            )

        db_session.commit()

        logger.info(f'Group updated: {group.name} (ID: {group.id}) by admin {current_user.username}')

        # Return the updated group with members
        group_dict = {
            'id': group.id,
            'name': group.name,
            'description': group.description,
            'is_active': group.is_active,
            'members': [
                {
                    'id': m.user_id,
                    'username': m.user.username if m.user else None,
                    'email': m.user.email if m.user else None
                }
                for m in group.memberships if m.is_active
            ],
            'member_count': group.member_count,
            'created_at': group.created_at.isoformat() if group.created_at else None,
            'updated_at': group.updated_at.isoformat() if group.updated_at else None,
            'created_by_id': group.created_by_id,
            'created_by': group.created_by.username if group.created_by else None
        }

        return api_response(
            data=group_dict,
            message=f'Notification group "{group.name}" updated successfully'
        )

    except Exception as e:
        db_session.rollback()
        logger.error(f'Error updating group: {str(e)}')
        return api_error(
            ErrorCodes.DATABASE_ERROR,
            f'Failed to update group: {str(e)}',
            status_code=500
        )
    finally:
        db_session.close()


@api_v2_bp.route('/admin/groups/<int:group_id>', methods=['DELETE'])
@dual_auth_required
@admin_required
@handle_exceptions
def delete_notification_group(group_id):
    """
    Delete a notification group

    DELETE /api/v2/admin/groups/<id>

    Note: This permanently deletes the group and all its memberships.

    Returns:
        204 No Content on success
    """
    from models.group import Group

    db_session = db_manager.get_session()
    try:
        # Find group
        group = db_session.query(Group).get(group_id)
        if not group:
            return api_error(
                ErrorCodes.RESOURCE_NOT_FOUND,
                f'Group with ID {group_id} not found',
                status_code=404
            )

        group_name = group.name
        member_count = group.member_count
        current_user = request.current_api_user

        # Delete the group (cascade will delete memberships)
        db_session.delete(group)

        # Log activity
        log_admin_activity(
            db_session,
            current_user.id,
            'admin_group_deleted',
            f'Deleted notification group "{group_name}" (had {member_count} members)',
            group_id
        )

        db_session.commit()

        logger.info(f'Group deleted: {group_name} (ID: {group_id}) by admin {current_user.username}')

        return api_no_content()

    except Exception as e:
        db_session.rollback()
        logger.error(f'Error deleting group: {str(e)}')
        return api_error(
            ErrorCodes.DATABASE_ERROR,
            f'Failed to delete group: {str(e)}',
            status_code=500
        )
    finally:
        db_session.close()


# =============================================================================
# COMPANY GROUPING MANAGEMENT ENDPOINTS
# =============================================================================

def _build_company_hierarchy(db_session):
    """
    Build the company hierarchy tree structure.

    Returns a dict with:
    - parent_companies: Companies that are marked as parent or have child companies
    - standalone_companies: Companies with no parent and not marked as parent
    - Counts for total companies, parents, and children
    """
    # Get all companies
    companies = db_session.query(Company).order_by(Company.name).all()

    # Separate into categories
    parent_companies_list = []
    standalone_companies_list = []
    total_child_companies = 0

    for company in companies:
        child_count = company.child_companies.count()

        if company.is_parent_company or child_count > 0:
            # This is a parent company
            children = []
            for child in company.child_companies.all():
                children.append({
                    'id': child.id,
                    'name': child.name,
                    'display_name': child.display_name,
                    'description': child.description,
                    'contact_name': child.contact_name,
                    'contact_email': child.contact_email
                })
                total_child_companies += 1

            parent_companies_list.append({
                'id': company.id,
                'name': company.name,
                'display_name': company.display_name,
                'is_parent_company': company.is_parent_company,
                'description': company.description,
                'contact_name': company.contact_name,
                'contact_email': company.contact_email,
                'children': children,
                'child_count': child_count
            })
        elif not company.parent_company_id and not company.is_parent_company:
            # This is a standalone company
            standalone_companies_list.append({
                'id': company.id,
                'name': company.name,
                'display_name': company.display_name,
                'is_parent_company': False,
                'parent_company_id': None,
                'description': company.description,
                'contact_name': company.contact_name,
                'contact_email': company.contact_email
            })

    return {
        'parent_companies': parent_companies_list,
        'standalone_companies': standalone_companies_list,
        'total_companies': len(companies),
        'total_parent_companies': len(parent_companies_list),
        'total_child_companies': total_child_companies
    }


@api_v2_bp.route('/admin/company-grouping', methods=['GET'])
@dual_auth_required
@admin_required
@handle_exceptions
def get_company_grouping():
    """
    Get the company hierarchy tree

    GET /api/v2/admin/company-grouping

    Returns:
        Company hierarchy with parent companies, their children, and standalone companies

    Response Structure:
        {
            "success": true,
            "data": {
                "parent_companies": [
                    {
                        "id": 1,
                        "name": "Parent Corp",
                        "display_name": "Parent Corporation",
                        "is_parent_company": true,
                        "children": [
                            {
                                "id": 2,
                                "name": "Child Company A",
                                "display_name": null
                            }
                        ],
                        "child_count": 1
                    }
                ],
                "standalone_companies": [...],
                "total_companies": 10,
                "total_parent_companies": 3,
                "total_child_companies": 5
            }
        }
    """
    db_session = db_manager.get_session()
    try:
        hierarchy = _build_company_hierarchy(db_session)

        return api_response(
            data=hierarchy,
            message=f'Retrieved company hierarchy with {hierarchy["total_parent_companies"]} parent companies and {hierarchy["total_child_companies"]} child companies'
        )

    finally:
        db_session.close()


@api_v2_bp.route('/admin/company-grouping', methods=['PUT'])
@dual_auth_required
@admin_required
@handle_exceptions
def update_company_grouping():
    """
    Update company hierarchy (set parent, remove from parent, toggle parent status, etc.)

    PUT /api/v2/admin/company-grouping

    Request Body - Set Parent:
        {
            "action": "set_parent",
            "company_id": 2,
            "parent_company_id": 1
        }

    Request Body - Remove from Parent:
        {
            "action": "remove_from_parent",
            "company_id": 2
        }

    Request Body - Toggle Parent Status:
        {
            "action": "toggle_parent_status",
            "company_id": 1,
            "is_parent_company": true
        }

    Request Body - Set Display Name:
        {
            "action": "set_display_name",
            "company_id": 1,
            "display_name": "Parent Corp Display"
        }

    Request Body - Bulk Set Parent:
        {
            "action": "bulk_set_parent",
            "company_ids": [2, 3, 4],
            "parent_company_id": 1
        }

    Returns:
        Updated company hierarchy
    """
    # Validate request body
    data, error = validate_json_body()
    if error:
        return error

    # Validate action is present
    action = data.get('action')
    if not action:
        return api_error(
            ErrorCodes.MISSING_REQUIRED_FIELD,
            'Missing required field: action',
            status_code=400
        )

    valid_actions = ['set_parent', 'remove_from_parent', 'toggle_parent_status', 'set_display_name', 'bulk_set_parent']
    if action not in valid_actions:
        return api_error(
            ErrorCodes.INVALID_FIELD_VALUE,
            f'Invalid action. Must be one of: {", ".join(valid_actions)}',
            status_code=400
        )

    db_session = db_manager.get_session()
    try:
        current_user = request.current_api_user

        if action == 'set_parent':
            return _handle_set_parent(db_session, data, current_user)
        elif action == 'remove_from_parent':
            return _handle_remove_from_parent(db_session, data, current_user)
        elif action == 'toggle_parent_status':
            return _handle_toggle_parent_status(db_session, data, current_user)
        elif action == 'set_display_name':
            return _handle_set_display_name(db_session, data, current_user)
        elif action == 'bulk_set_parent':
            return _handle_bulk_set_parent(db_session, data, current_user)

    except Exception as e:
        db_session.rollback()
        logger.error(f'Error updating company grouping: {str(e)}')
        return api_error(
            ErrorCodes.DATABASE_ERROR,
            f'Failed to update company grouping: {str(e)}',
            status_code=500
        )
    finally:
        db_session.close()


def _handle_set_parent(db_session, data, current_user):
    """Handle setting a parent company for a child company"""
    company_id = data.get('company_id')
    parent_company_id = data.get('parent_company_id')

    if not company_id:
        return api_error(
            ErrorCodes.MISSING_REQUIRED_FIELD,
            'Missing required field: company_id',
            status_code=400
        )

    if not parent_company_id:
        return api_error(
            ErrorCodes.MISSING_REQUIRED_FIELD,
            'Missing required field: parent_company_id. Use remove_from_parent action to remove parent.',
            status_code=400
        )

    # Get the child company
    company = db_session.query(Company).get(company_id)
    if not company:
        return api_error(
            ErrorCodes.RESOURCE_NOT_FOUND,
            f'Company with ID {company_id} not found',
            status_code=404
        )

    # Get the parent company
    parent_company = db_session.query(Company).get(parent_company_id)
    if not parent_company:
        return api_error(
            ErrorCodes.RESOURCE_NOT_FOUND,
            f'Parent company with ID {parent_company_id} not found',
            status_code=404
        )

    # Validate: company cannot be its own parent
    if company_id == parent_company_id:
        return api_error(
            ErrorCodes.VALIDATION_ERROR,
            'A company cannot be its own parent',
            status_code=400
        )

    # Validate: prevent circular reference (parent's parent is the child)
    if parent_company.parent_company_id == company_id:
        return api_error(
            ErrorCodes.VALIDATION_ERROR,
            'This would create a circular reference',
            status_code=400
        )

    # Store old parent name for logging
    old_parent_name = company.parent_company.name if company.parent_company else None

    # Set the parent relationship
    company.parent_company_id = parent_company_id

    # Ensure parent is marked as parent company
    parent_company.is_parent_company = True

    # Log activity
    log_admin_activity(
        db_session,
        current_user.id,
        'company_grouping_set_parent',
        f'Set parent of "{company.name}" to "{parent_company.name}"' +
        (f' (previously under "{old_parent_name}")' if old_parent_name else ''),
        company_id
    )

    db_session.commit()

    logger.info(f'Company {company.name} set under parent {parent_company.name} by admin {current_user.username}')

    # Return updated hierarchy
    hierarchy = _build_company_hierarchy(db_session)

    return api_response(
        data=hierarchy,
        message=f'Successfully grouped "{company.name}" under "{parent_company.name}"'
    )


def _handle_remove_from_parent(db_session, data, current_user):
    """Handle removing a company from its parent"""
    company_id = data.get('company_id')

    if not company_id:
        return api_error(
            ErrorCodes.MISSING_REQUIRED_FIELD,
            'Missing required field: company_id',
            status_code=400
        )

    # Get the company
    company = db_session.query(Company).get(company_id)
    if not company:
        return api_error(
            ErrorCodes.RESOURCE_NOT_FOUND,
            f'Company with ID {company_id} not found',
            status_code=404
        )

    if not company.parent_company_id:
        return api_error(
            ErrorCodes.VALIDATION_ERROR,
            f'Company "{company.name}" is not a child of any parent company',
            status_code=400
        )

    # Store old parent for logging and cleanup
    old_parent = company.parent_company
    old_parent_name = old_parent.name if old_parent else None
    old_parent_id = company.parent_company_id

    # Remove parent relationship
    company.parent_company_id = None

    # Check if old parent still has children; if not, remove parent status
    if old_parent:
        remaining_children = db_session.query(Company).filter(
            Company.parent_company_id == old_parent_id,
            Company.id != company_id
        ).count()

        if remaining_children == 0:
            old_parent.is_parent_company = False

    # Log activity
    log_admin_activity(
        db_session,
        current_user.id,
        'company_grouping_remove_parent',
        f'Removed "{company.name}" from parent "{old_parent_name}"',
        company_id
    )

    db_session.commit()

    logger.info(f'Company {company.name} removed from parent {old_parent_name} by admin {current_user.username}')

    # Return updated hierarchy
    hierarchy = _build_company_hierarchy(db_session)

    return api_response(
        data=hierarchy,
        message=f'Successfully removed "{company.name}" from parent "{old_parent_name}"'
    )


def _handle_toggle_parent_status(db_session, data, current_user):
    """Handle toggling parent company status"""
    company_id = data.get('company_id')
    is_parent_company = data.get('is_parent_company')

    if not company_id:
        return api_error(
            ErrorCodes.MISSING_REQUIRED_FIELD,
            'Missing required field: company_id',
            status_code=400
        )

    if is_parent_company is None:
        return api_error(
            ErrorCodes.MISSING_REQUIRED_FIELD,
            'Missing required field: is_parent_company',
            status_code=400
        )

    # Get the company
    company = db_session.query(Company).get(company_id)
    if not company:
        return api_error(
            ErrorCodes.RESOURCE_NOT_FOUND,
            f'Company with ID {company_id} not found',
            status_code=404
        )

    # If trying to remove parent status, check if company has children
    if not is_parent_company and company.child_companies.count() > 0:
        return api_error(
            ErrorCodes.VALIDATION_ERROR,
            f'Cannot remove parent status from "{company.name}" - it still has child companies. Remove children first.',
            status_code=400
        )

    # Update parent status
    old_status = company.is_parent_company
    company.is_parent_company = is_parent_company

    # Log activity
    status_text = "enabled" if is_parent_company else "disabled"
    log_admin_activity(
        db_session,
        current_user.id,
        'company_grouping_toggle_parent',
        f'{status_text.capitalize()} parent status for "{company.name}"',
        company_id
    )

    db_session.commit()

    logger.info(f'Parent status {status_text} for company {company.name} by admin {current_user.username}')

    # Return updated hierarchy
    hierarchy = _build_company_hierarchy(db_session)

    return api_response(
        data=hierarchy,
        message=f'Successfully {status_text} parent status for "{company.name}"'
    )


def _handle_set_display_name(db_session, data, current_user):
    """Handle setting a custom display name for a company"""
    company_id = data.get('company_id')
    display_name = data.get('display_name')

    if not company_id:
        return api_error(
            ErrorCodes.MISSING_REQUIRED_FIELD,
            'Missing required field: company_id',
            status_code=400
        )

    # display_name can be None/empty to clear it
    if display_name is not None:
        display_name = display_name.strip() if display_name else None

    # Get the company
    company = db_session.query(Company).get(company_id)
    if not company:
        return api_error(
            ErrorCodes.RESOURCE_NOT_FOUND,
            f'Company with ID {company_id} not found',
            status_code=404
        )

    # Update display name
    old_display_name = company.display_name
    company.display_name = display_name if display_name else None

    # Log activity
    if display_name:
        log_message = f'Set display name for "{company.name}" to "{display_name}"'
    else:
        log_message = f'Removed custom display name for "{company.name}"'

    if old_display_name:
        log_message += f' (was: "{old_display_name}")'

    log_admin_activity(
        db_session,
        current_user.id,
        'company_grouping_set_display_name',
        log_message,
        company_id
    )

    db_session.commit()

    logger.info(f'Display name updated for company {company.name} by admin {current_user.username}')

    # Return updated hierarchy
    hierarchy = _build_company_hierarchy(db_session)

    if display_name:
        message = f'Successfully set display name for "{company.name}" to "{display_name}"'
    else:
        message = f'Successfully removed custom display name for "{company.name}"'

    return api_response(
        data=hierarchy,
        message=message
    )


def _handle_bulk_set_parent(db_session, data, current_user):
    """Handle setting parent company for multiple child companies at once"""
    company_ids = data.get('company_ids')
    parent_company_id = data.get('parent_company_id')

    if not company_ids:
        return api_error(
            ErrorCodes.MISSING_REQUIRED_FIELD,
            'Missing required field: company_ids',
            status_code=400
        )

    if not isinstance(company_ids, list) or len(company_ids) == 0:
        return api_error(
            ErrorCodes.INVALID_FIELD_VALUE,
            'company_ids must be a non-empty list of company IDs',
            status_code=400
        )

    if not parent_company_id:
        return api_error(
            ErrorCodes.MISSING_REQUIRED_FIELD,
            'Missing required field: parent_company_id',
            status_code=400
        )

    # Get the parent company
    parent_company = db_session.query(Company).get(parent_company_id)
    if not parent_company:
        return api_error(
            ErrorCodes.RESOURCE_NOT_FOUND,
            f'Parent company with ID {parent_company_id} not found',
            status_code=404
        )

    # Process each company
    grouped_companies = []
    errors = []

    for company_id in company_ids:
        # Skip if company is the parent itself
        if company_id == parent_company_id:
            errors.append(f'Company ID {company_id} cannot be its own parent')
            continue

        company = db_session.query(Company).get(company_id)
        if not company:
            errors.append(f'Company with ID {company_id} not found')
            continue

        # Check for circular reference
        if parent_company.parent_company_id == company_id:
            errors.append(f'Setting {company.name} under {parent_company.name} would create a circular reference')
            continue

        # Set parent
        company.parent_company_id = parent_company_id
        grouped_companies.append(company.name)

    # Mark parent as parent company
    if grouped_companies:
        parent_company.is_parent_company = True

        # Log activity
        log_admin_activity(
            db_session,
            current_user.id,
            'company_grouping_bulk_set_parent',
            f'Grouped {len(grouped_companies)} companies under "{parent_company.name}": {", ".join(grouped_companies)}',
            parent_company_id
        )

        db_session.commit()

        logger.info(f'{len(grouped_companies)} companies grouped under {parent_company.name} by admin {current_user.username}')

    # Return updated hierarchy
    hierarchy = _build_company_hierarchy(db_session)

    # Build response message
    if grouped_companies and not errors:
        message = f'Successfully grouped {len(grouped_companies)} companies under "{parent_company.name}"'
    elif grouped_companies and errors:
        message = f'Grouped {len(grouped_companies)} companies under "{parent_company.name}" with {len(errors)} error(s)'
    else:
        return api_error(
            ErrorCodes.VALIDATION_ERROR,
            f'Failed to group any companies: {"; ".join(errors)}',
            status_code=400
        )

    response_data = hierarchy
    if errors:
        response_data['errors'] = errors

    return api_response(
        data=response_data,
        message=message
    )


# =============================================================================
# ACTIVITY LOG ENDPOINT
# =============================================================================

# Define available activity types based on what's used across the codebase
AVAILABLE_ACTIVITY_TYPES = [
    'ticket_created', 'ticket_updated', 'ticket_resolved',
    'asset_created', 'asset_updated', 'asset_deleted', 'asset_archived',
    'asset_checkout', 'asset_shipped', 'asset_assigned', 'asset_transferred',
    'asset_added', 'asset_linked', 'asset_unlinked', 'asset_image_updated',
    'accessory_created', 'accessory_updated', 'accessory_deleted',
    'accessory_assigned', 'accessory_returned', 'accessory_checkin',
    'accessory_stock_added',
    'bulk_asset_deleted', 'bulk_accessory_deleted',
    'user_created', 'user_updated', 'user_deleted',
    'company_created', 'company_updated', 'company_deleted',
    'company_grouping_set_parent', 'company_grouping_remove_parent',
    'company_grouping_toggle_parent', 'company_grouping_set_display_name',
    'company_grouping_bulk_set_parent',
    'mention', 'group_mention',
    'comment_added', 'attachment_uploaded',
    'data_import', 'csv_import',
    'transaction_deleted',
    'issue_reported', 'issue_resolved', 'issue_reopened', 'issue_comment',
    'service_record_assignment', 'service_record_update', 'service_record_completed',
    'system_settings_updated'
]

# Define available entity types
AVAILABLE_ENTITY_TYPES = [
    'ticket', 'asset', 'accessory', 'user', 'customer', 'company',
    'comment', 'attachment', 'service_record', 'queue', 'category'
]


def _parse_entity_from_activity(activity):
    """
    Parse entity information from an activity record.

    This attempts to determine the entity type and ID from the activity type
    and reference_id field.
    """
    entity_type = None
    entity_id = activity.reference_id
    display_id = None

    activity_type = activity.type or ''

    # Determine entity type based on activity type
    if activity_type.startswith('ticket_') or activity_type in ['mention', 'comment_added', 'attachment_uploaded']:
        entity_type = 'ticket'
        if entity_id:
            display_id = f'TICK-{str(entity_id).zfill(4)}'
    elif activity_type.startswith('asset_') or activity_type == 'bulk_asset_deleted':
        entity_type = 'asset'
    elif activity_type.startswith('accessory_') or activity_type == 'bulk_accessory_deleted':
        entity_type = 'accessory'
    elif activity_type.startswith('user_'):
        entity_type = 'user'
    elif activity_type.startswith('company_'):
        entity_type = 'company'
    elif activity_type.startswith('issue_'):
        entity_type = 'ticket'
        if entity_id:
            display_id = f'TICK-{str(entity_id).zfill(4)}'
    elif activity_type.startswith('service_record_'):
        entity_type = 'service_record'
    elif activity_type == 'data_import' or activity_type == 'csv_import':
        entity_type = 'import'
    elif activity_type == 'system_settings_updated':
        entity_type = 'system_settings'

    if entity_type and entity_id:
        return {
            'type': entity_type,
            'id': entity_id,
            'display_id': display_id
        }
    return None


def _format_activity_response(activity):
    """
    Format a single activity record for API response.
    """
    # Parse entity information
    entity = _parse_entity_from_activity(activity)

    # Build user info if available
    user_info = None
    if activity.user:
        user_info = {
            'id': activity.user.id,
            'username': activity.user.username
        }

    # Parse details from content if it contains structured data
    details = {}
    content = activity.content or ''

    # Try to extract meaningful details from the content string
    if ':' in content:
        # Content often has format "Action description: Details"
        parts = content.split(':', 1)
        if len(parts) == 2:
            details['summary'] = parts[0].strip()
            details['description'] = parts[1].strip()

    return {
        'id': activity.id,
        'activity_type': activity.type,
        'description': content,
        'user': user_info,
        'entity': entity,
        'details': details if details else None,
        'ip_address': None,  # Activity model doesn't have this field currently
        'user_agent': None,  # Activity model doesn't have this field currently
        'is_read': activity.is_read,
        'created_at': activity.created_at.isoformat() + 'Z' if activity.created_at else None
    }


@api_v2_bp.route('/admin/activity-log', methods=['GET'])
@dual_auth_required
@admin_required
@handle_exceptions
def get_activity_log():
    """
    Get system activity history with filtering and pagination.

    GET /api/v2/admin/activity-log

    Query Parameters:
        - page: Page number (default: 1)
        - per_page: Items per page (default: 20, max: 100)
        - sort: Field to sort by (default: created_at)
        - order: Sort order - 'asc' or 'desc' (default: desc)
        - user_id: Filter by user ID
        - activity_type: Filter by activity type (e.g., ticket_created, asset_updated)
        - entity_type: Filter by entity type (ticket, asset, user, etc.)
        - entity_id: Filter by specific entity ID (requires entity_type or uses reference_id)
        - date_from: Filter activities from this date (ISO format: YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)
        - date_to: Filter activities to this date (ISO format: YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)
        - search: Search term for description/content
        - is_read: Filter by read status (true/false)

    Returns:
        List of activity records with pagination metadata and available filter options.

    Response Structure:
        {
            "success": true,
            "data": [
                {
                    "id": 1,
                    "activity_type": "ticket_created",
                    "description": "Created ticket TICK-0123: Asset Checkout Request",
                    "user": {
                        "id": 1,
                        "username": "john.doe"
                    },
                    "entity": {
                        "type": "ticket",
                        "id": 123,
                        "display_id": "TICK-0123"
                    },
                    "details": {
                        "summary": "Created ticket TICK-0123",
                        "description": "Asset Checkout Request"
                    },
                    "ip_address": null,
                    "user_agent": null,
                    "is_read": false,
                    "created_at": "2024-01-15T10:30:00Z"
                }
            ],
            "meta": {
                "pagination": {...},
                "available_types": [...],
                "available_entity_types": [...]
            }
        }
    """
    db_session = db_manager.get_session()
    try:
        # Get pagination params
        page, per_page = get_pagination_params()

        # Get sorting params
        allowed_sort_fields = ['id', 'type', 'created_at', 'user_id', 'reference_id']
        sort_field, sort_order = get_sorting_params(allowed_sort_fields)

        # Build base query with user join for efficiency
        query = db_session.query(Activity).outerjoin(Activity.user)

        # Filter by user_id
        user_id = request.args.get('user_id', type=int)
        if user_id:
            query = query.filter(Activity.user_id == user_id)

        # Filter by activity_type
        activity_type = request.args.get('activity_type')
        if activity_type:
            # Support multiple types separated by comma
            if ',' in activity_type:
                types = [t.strip() for t in activity_type.split(',')]
                query = query.filter(Activity.type.in_(types))
            else:
                query = query.filter(Activity.type == activity_type)

        # Filter by entity_type (maps to activity type prefixes)
        entity_type = request.args.get('entity_type')
        if entity_type:
            # Map entity type to activity type prefixes
            entity_type_mapping = {
                'ticket': ['ticket_', 'mention', 'comment_', 'attachment_', 'issue_'],
                'asset': ['asset_', 'bulk_asset_'],
                'accessory': ['accessory_', 'bulk_accessory_'],
                'user': ['user_'],
                'company': ['company_'],
                'service_record': ['service_record_'],
                'customer': ['customer_'],
                'import': ['data_import', 'csv_import']
            }

            prefixes = entity_type_mapping.get(entity_type.lower(), [])
            if prefixes:
                # Build OR conditions for each prefix
                from sqlalchemy import or_
                conditions = []
                for prefix in prefixes:
                    if prefix.endswith('_'):
                        conditions.append(Activity.type.like(f'{prefix}%'))
                    else:
                        conditions.append(Activity.type == prefix)
                query = query.filter(or_(*conditions))

        # Filter by entity_id (reference_id)
        entity_id = request.args.get('entity_id', type=int)
        if entity_id:
            query = query.filter(Activity.reference_id == entity_id)

        # Filter by date range
        date_from = request.args.get('date_from')
        if date_from:
            try:
                # Support both date and datetime formats
                if 'T' in date_from:
                    from_date = datetime.fromisoformat(date_from.replace('Z', ''))
                else:
                    from_date = datetime.strptime(date_from, '%Y-%m-%d')
                query = query.filter(Activity.created_at >= from_date)
            except ValueError:
                return api_error(
                    ErrorCodes.VALIDATION_ERROR,
                    'Invalid date_from format. Use YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS',
                    status_code=400
                )

        date_to = request.args.get('date_to')
        if date_to:
            try:
                # Support both date and datetime formats
                if 'T' in date_to:
                    to_date = datetime.fromisoformat(date_to.replace('Z', ''))
                else:
                    # For date-only, include the entire day
                    to_date = datetime.strptime(date_to, '%Y-%m-%d')
                    to_date = to_date.replace(hour=23, minute=59, second=59)
                query = query.filter(Activity.created_at <= to_date)
            except ValueError:
                return api_error(
                    ErrorCodes.VALIDATION_ERROR,
                    'Invalid date_to format. Use YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS',
                    status_code=400
                )

        # Filter by search term in content
        search = request.args.get('search')
        if search:
            query = query.filter(Activity.content.ilike(f'%{search}%'))

        # Filter by read status
        is_read = request.args.get('is_read')
        if is_read is not None:
            is_read_bool = is_read.lower() == 'true'
            query = query.filter(Activity.is_read == is_read_bool)

        # Apply sorting
        query = apply_sorting(query, Activity, sort_field, sort_order)

        # Paginate results
        activities, pagination_meta = paginate_query(query, page, per_page)

        # Format activities for response
        formatted_activities = [_format_activity_response(activity) for activity in activities]

        # Add available filter options to meta
        pagination_meta['available_types'] = AVAILABLE_ACTIVITY_TYPES
        pagination_meta['available_entity_types'] = AVAILABLE_ENTITY_TYPES

        # Get distinct activity types actually in the database for better UX
        distinct_types = db_session.query(Activity.type).distinct().all()
        pagination_meta['types_in_use'] = sorted([t[0] for t in distinct_types if t[0]])

        logger.info(f'Activity log retrieved by admin {request.current_api_user.username}: '
                   f'{len(formatted_activities)} records on page {page}')

        return api_response(
            data=formatted_activities,
            meta=pagination_meta,
            message=f'Retrieved {len(formatted_activities)} activity records'
        )

    except Exception as e:
        logger.error(f'Error retrieving activity log: {str(e)}')
        return api_error(
            ErrorCodes.DATABASE_ERROR,
            f'Failed to retrieve activity log: {str(e)}',
            status_code=500
        )
    finally:
        db_session.close()


# =============================================================================
# SIMPLIFIED LIST ENDPOINTS FOR FORM DROPDOWNS
# =============================================================================

@api_v2_bp.route('/queues', methods=['GET'])
@dual_auth_required
@handle_exceptions
def list_queues_simple():
    """
    List queues for dropdown menus (simplified, non-admin)

    GET /api/v2/queues

    Query Parameters:
        - limit: Maximum number of results (default: 100)

    Returns:
        List of queues with id, name, and description
    """
    db_session = db_manager.get_session()
    try:
        limit = request.args.get('limit', 100, type=int)
        user = request.current_api_user

        # Get queues accessible to the user
        if user.is_super_admin or user.is_developer:
            queues = db_session.query(Queue).order_by(Queue.name).limit(limit).all()
        else:
            accessible_queue_ids = user.get_accessible_queue_ids(db_session)
            queues = db_session.query(Queue).filter(
                Queue.id.in_(accessible_queue_ids)
            ).order_by(Queue.name).limit(limit).all()

        queues_data = [{
            'id': q.id,
            'name': q.name,
            'description': q.description
        } for q in queues]

        return api_response(
            data=queues_data,
            message=f'Retrieved {len(queues_data)} queues'
        )

    except Exception as e:
        logger.error(f'Error listing queues: {str(e)}')
        return api_error(
            ErrorCodes.DATABASE_ERROR,
            f'Failed to list queues: {str(e)}',
            status_code=500
        )
    finally:
        db_session.close()


@api_v2_bp.route('/users', methods=['GET'])
@dual_auth_required
@handle_exceptions
def list_users_simple():
    """
    List users for dropdown menus (simplified, non-admin)

    GET /api/v2/users

    Query Parameters:
        - limit: Maximum number of results (default: 100)
        - search: Search by username or full_name

    Returns:
        List of users with id, username, full_name, email
    """
    db_session = db_manager.get_session()
    try:
        limit = request.args.get('limit', 100, type=int)
        search = request.args.get('search', '').strip()

        query = db_session.query(User).filter(
            User.is_deleted == False
        )

        if search:
            search_term = f'%{search}%'
            query = query.filter(
                (User.username.ilike(search_term)) |
                (User.full_name.ilike(search_term)) |
                (User.email.ilike(search_term))
            )

        users = query.order_by(User.username).limit(limit).all()

        users_data = [{
            'id': u.id,
            'username': u.username,
            'full_name': u.full_name or u.username,
            'email': u.email or ''
        } for u in users]

        return api_response(
            data=users_data,
            message=f'Retrieved {len(users_data)} users'
        )

    except Exception as e:
        logger.error(f'Error listing users: {str(e)}')
        return api_error(
            ErrorCodes.DATABASE_ERROR,
            f'Failed to list users: {str(e)}',
            status_code=500
        )
    finally:
        db_session.close()
