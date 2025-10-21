"""
API Routes for Mobile App Integration

This module provides RESTful API endpoints for:
- Ticket management
- User information
- Inventory access
- Mobile-specific sync operations
"""

from flask import Blueprint, request, jsonify, g
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

from utils.api_auth import require_api_key, create_success_response, create_error_response
from models.ticket import Ticket, TicketStatus, TicketPriority, TicketCategory
from models.user import User
from models.asset import Asset
from models.customer_user import CustomerUser
from models.queue import Queue
from flask import current_app

# Create API blueprint
api_bp = Blueprint('main_api', __name__, url_prefix='/api/v1')

# Helper functions
def paginate_query(query, page: int = 1, per_page: int = 50, max_per_page: int = 100):
    """
    Paginate a SQLAlchemy query
    
    Args:
        query: SQLAlchemy query object
        page: Page number (1-based)
        per_page: Items per page
        max_per_page: Maximum items per page
        
    Returns:
        Tuple of (items, pagination_info)
    """
    # Validate and limit per_page
    per_page = min(per_page, max_per_page)
    per_page = max(per_page, 1)
    
    # Validate page
    page = max(page, 1)
    
    # Execute paginated query
    paginated = query.paginate(
        page=page,
        per_page=per_page,
        error_out=False
    )
    
    pagination_info = {
        'page': page,
        'per_page': per_page,
        'total': paginated.total,
        'pages': paginated.pages,
        'has_next': paginated.has_next,
        'has_prev': paginated.has_prev,
        'next_page': paginated.next_num if paginated.has_next else None,
        'prev_page': paginated.prev_num if paginated.has_prev else None
    }
    
    return paginated.items, pagination_info

def parse_datetime(date_string: str) -> Optional[datetime]:
    """Parse datetime string in ISO format"""
    if not date_string:
        return None
    
    try:
        # Try parsing with timezone
        if date_string.endswith('Z'):
            return datetime.fromisoformat(date_string[:-1])
        return datetime.fromisoformat(date_string)
    except ValueError:
        return None

# Ticket Management Endpoints

@api_bp.route('/tickets', methods=['GET'])
@require_api_key(permissions=['tickets:read'])
def list_tickets():
    """
    List tickets with filtering and pagination
    
    Query Parameters:
        - page: Page number (default: 1)
        - per_page: Items per page (default: 50, max: 100)
        - status: Filter by status
        - priority: Filter by priority
        - queue_id: Filter by queue ID
        - customer_id: Filter by customer ID
        - created_after: Filter by creation date (ISO format)
        - updated_after: Filter by last update date (ISO format)
    """
    try:
        # Parse query parameters
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)
        status = request.args.get('status')
        priority = request.args.get('priority')
        queue_id = request.args.get('queue_id', type=int)
        customer_id = request.args.get('customer_id', type=int)
        created_after = parse_datetime(request.args.get('created_after'))
        updated_after = parse_datetime(request.args.get('updated_after'))
        
        # Build query
        session = SessionLocal()
        try:
            query = session.query(Ticket)
        
        # Apply filters
        if status:
            query = query.filter(Ticket.status == status)
        
        if priority:
            query = query.filter(Ticket.priority_id == priority)
        
        if queue_id:
            query = query.filter(Ticket.queue_id == queue_id)
        
        if customer_id:
            query = query.filter(Ticket.customer_user_id == customer_id)
        
        if created_after:
            query = query.filter(Ticket.created_at >= created_after)
        
        if updated_after:
            query = query.filter(Ticket.updated_at >= updated_after)
        
        # Order by most recent first
        query = query.order_by(Ticket.updated_at.desc())
        
        # Paginate
        tickets, pagination = paginate_query(query, page, per_page)
        
        # Convert to dict
        tickets_data = []
        for ticket in tickets:
            ticket_data = {
                'id': ticket.id,
                'subject': ticket.subject,
                'description': ticket.description,
                'status': ticket.status,
                'priority': ticket.priority.name if ticket.priority else None,
                'category': ticket.category.name if ticket.category else None,
                'queue_id': ticket.queue_id,
                'queue_name': ticket.queue.name if ticket.queue else None,
                'customer_id': ticket.customer_user_id,
                'customer_name': ticket.customer_user.name if ticket.customer_user else None,
                'customer_email': ticket.customer_user.email if ticket.customer_user else None,
                'assigned_to_id': ticket.assigned_to_id,
                'assigned_to_name': ticket.assigned_to.name if ticket.assigned_to else None,
                'created_at': ticket.created_at.isoformat() if ticket.created_at else None,
                'updated_at': ticket.updated_at.isoformat() if ticket.updated_at else None,
                'shipping_address': ticket.shipping_address,
                'shipping_tracking': ticket.shipping_tracking,
                'shipping_carrier': ticket.shipping_carrier,
                'shipping_status': ticket.shipping_status
            }
            tickets_data.append(ticket_data)
        
        return jsonify(create_success_response(
            tickets_data,
            f"Retrieved {len(tickets_data)} tickets",
            {"pagination": pagination}
        ))
        
    finally:
            session.close()
        
    except Exception as e:
        response, status_code = create_error_response(
            "INTERNAL_ERROR",
            f"Error retrieving tickets: {str(e)}",
            500
        )
        return jsonify(response), status_code

@api_bp.route('/tickets/<int:ticket_id>', methods=['GET'])
@require_api_key(permissions=['tickets:read'])
def get_ticket(ticket_id):
    """Get detailed information about a specific ticket"""
    try:
        ticket = Ticket.query.get(ticket_id)
        
        if not ticket:
            response, status_code = create_error_response(
                "RESOURCE_NOT_FOUND",
                f"Ticket with ID {ticket_id} not found",
                404
            )
            return jsonify(response), status_code
        
        # Get ticket comments
        comments = []
        for comment in ticket.comments:
            comment_data = {
                'id': comment.id,
                'content': comment.content,
                'user_id': comment.user_id,
                'user_name': comment.user.username if comment.user else None,
                'created_at': comment.created_at.isoformat() if comment.created_at else None,
                'updated_at': comment.updated_at.isoformat() if comment.updated_at else None
            }
            comments.append(comment_data)
        
        # Get ticket attachments
        attachments = []
        for attachment in ticket.attachments:
            attachment_data = {
                'id': attachment.id,
                'filename': attachment.filename,
                'file_size': attachment.file_size,
                'content_type': attachment.content_type,
                'uploaded_at': attachment.uploaded_at.isoformat() if attachment.uploaded_at else None,
                'uploaded_by_id': attachment.uploaded_by_id,
                'uploaded_by_name': attachment.uploaded_by.name if attachment.uploaded_by else None
            }
            attachments.append(attachment_data)
        
        ticket_data = {
            'id': ticket.id,
            'subject': ticket.subject,
            'description': ticket.description,
            'status': ticket.status,
            'priority': ticket.priority.name if ticket.priority else None,
            'category': ticket.category.name if ticket.category else None,
            'queue_id': ticket.queue_id,
            'queue_name': ticket.queue.name if ticket.queue else None,
            'customer_id': ticket.customer_user_id,
            'customer_name': ticket.customer_user.name if ticket.customer_user else None,
            'customer_email': ticket.customer_user.email if ticket.customer_user else None,
            'customer_phone': ticket.customer_user.contact_number if ticket.customer_user else None,
            'assigned_to_id': ticket.assigned_to_id,
            'assigned_to_name': ticket.assigned_to.name if ticket.assigned_to else None,
            'created_at': ticket.created_at.isoformat() if ticket.created_at else None,
            'updated_at': ticket.updated_at.isoformat() if ticket.updated_at else None,
            'shipping_address': ticket.shipping_address,
            'shipping_tracking': ticket.shipping_tracking,
            'shipping_carrier': ticket.shipping_carrier,
            'shipping_status': ticket.shipping_status,
            'return_tracking': ticket.return_tracking,
            'return_status': ticket.return_status,
            'comments': comments,
            'attachments': attachments
        }
        
        return jsonify(create_success_response(
            ticket_data,
            f"Retrieved ticket {ticket_id}"
        ))
        
    except Exception as e:
        response, status_code = create_error_response(
            "INTERNAL_ERROR",
            f"Error retrieving ticket: {str(e)}",
            500
        )
        return jsonify(response), status_code

@api_bp.route('/tickets', methods=['POST'])
@require_api_key(permissions=['tickets:write'])
def create_ticket():
    """Create a new ticket"""
    try:
        data = request.get_json()
        
        if not data:
            response, status_code = create_error_response(
                "VALIDATION_ERROR",
                "Request body is required",
                400
            )
            return jsonify(response), status_code
        
        # Validate required fields
        required_fields = ['subject', 'description', 'queue_id']
        missing_fields = [field for field in required_fields if not data.get(field)]
        
        if missing_fields:
            response, status_code = create_error_response(
                "VALIDATION_ERROR",
                f"Missing required fields: {', '.join(missing_fields)}",
                400,
                {"missing_fields": missing_fields}
            )
            return jsonify(response), status_code
        
        # Validate queue exists
        queue = Queue.query.get(data['queue_id'])
        if not queue:
            response, status_code = create_error_response(
                "VALIDATION_ERROR",
                f"Queue with ID {data['queue_id']} not found",
                400
            )
            return jsonify(response), status_code
        
        # Create ticket
        ticket = Ticket(
            subject=data['subject'],
            description=data['description'],
            queue_id=data['queue_id'],
            customer_user_id=data.get('customer_id'),
            priority_id=data.get('priority_id'),
            category_id=data.get('category_id'),
            assigned_to_id=data.get('assigned_to_id'),
            shipping_address=data.get('shipping_address'),
            status='NEW'  # Default status
        )
        
        session = SessionLocal()
        try:
            session.add(ticket)
            session.commit()
            session.refresh(ticket)
        finally:
            session.close()
        
        # Return created ticket
        ticket_data = {
            'id': ticket.id,
            'subject': ticket.subject,
            'description': ticket.description,
            'status': ticket.status,
            'queue_id': ticket.queue_id,
            'customer_id': ticket.customer_user_id,
            'created_at': ticket.created_at.isoformat() if ticket.created_at else None
        }
        
        return jsonify(create_success_response(
            ticket_data,
            f"Ticket created successfully"
        )), 201
        
    except Exception as e:
        response, status_code = create_error_response(
            "INTERNAL_ERROR",
            f"Error creating ticket: {str(e)}",
            500
        )
        return jsonify(response), status_code

@api_bp.route('/tickets/<int:ticket_id>', methods=['PUT'])
@require_api_key(permissions=['tickets:write'])
def update_ticket(ticket_id):
    """Update an existing ticket"""
    try:
        ticket = Ticket.query.get(ticket_id)
        
        if not ticket:
            response, status_code = create_error_response(
                "RESOURCE_NOT_FOUND",
                f"Ticket with ID {ticket_id} not found",
                404
            )
            return jsonify(response), status_code
        
        data = request.get_json()
        if not data:
            response, status_code = create_error_response(
                "VALIDATION_ERROR",
                "Request body is required",
                400
            )
            return jsonify(response), status_code
        
        # Update allowed fields
        updatable_fields = [
            'subject', 'description', 'status', 'priority_id', 'category_id',
            'assigned_to_id', 'shipping_address', 'shipping_tracking',
            'shipping_carrier', 'shipping_status', 'return_tracking', 'return_status'
        ]
        
        updated_fields = []
        for field in updatable_fields:
            if field in data:
                setattr(ticket, field, data[field])
                updated_fields.append(field)
        
        if updated_fields:
            ticket.updated_at = datetime.utcnow()
            session = SessionLocal()
            try:
                session.merge(ticket)
                session.commit()
            finally:
                session.close()
        
        ticket_data = {
            'id': ticket.id,
            'subject': ticket.subject,
            'description': ticket.description,
            'status': ticket.status,
            'updated_at': ticket.updated_at.isoformat() if ticket.updated_at else None
        }
        
        return jsonify(create_success_response(
            ticket_data,
            f"Ticket updated successfully. Updated fields: {', '.join(updated_fields)}"
        ))
        
    except Exception as e:
        response, status_code = create_error_response(
            "INTERNAL_ERROR",
            f"Error updating ticket: {str(e)}",
            500
        )
        return jsonify(response), status_code

# User Management Endpoints

@api_bp.route('/users', methods=['GET'])
@require_api_key(permissions=['users:read'])
def list_users():
    """List users with pagination"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)
        
        query = User.query.order_by(User.name)
        users, pagination = paginate_query(query, page, per_page)
        
        users_data = []
        for user in users:
            user_data = {
                'id': user.id,
                'name': user.name,
                'email': user.email,
                'user_type': user.user_type.value if user.user_type else None,
                'is_active': user.is_active,
                'created_at': user.created_at.isoformat() if user.created_at else None
            }
            users_data.append(user_data)
        
        return jsonify(create_success_response(
            users_data,
            f"Retrieved {len(users_data)} users",
            {"pagination": pagination}
        ))
        
    except Exception as e:
        response, status_code = create_error_response(
            "INTERNAL_ERROR",
            f"Error retrieving users: {str(e)}",
            500
        )
        return jsonify(response), status_code

@api_bp.route('/users/<int:user_id>', methods=['GET'])
@require_api_key(permissions=['users:read'])
def get_user(user_id):
    """Get detailed information about a specific user"""
    try:
        user = User.query.get(user_id)
        
        if not user:
            response, status_code = create_error_response(
                "RESOURCE_NOT_FOUND",
                f"User with ID {user_id} not found",
                404
            )
            return jsonify(response), status_code
        
        user_data = {
            'id': user.id,
            'name': user.name,
            'email': user.email,
            'user_type': user.user_type.value if user.user_type else None,
            'is_active': user.is_active,
            'created_at': user.created_at.isoformat() if user.created_at else None,
            'last_login': user.last_login.isoformat() if user.last_login else None
        }
        
        return jsonify(create_success_response(
            user_data,
            f"Retrieved user {user_id}"
        ))
        
    except Exception as e:
        response, status_code = create_error_response(
            "INTERNAL_ERROR",
            f"Error retrieving user: {str(e)}",
            500
        )
        return jsonify(response), status_code

# Inventory Management Endpoints

@api_bp.route('/inventory', methods=['GET'])
@require_api_key(permissions=['inventory:read'])
def list_inventory():
    """List inventory items with filtering and pagination"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)
        status = request.args.get('status')
        
        query = Asset.query
        
        if status:
            query = query.filter(Asset.status == status)
        
        query = query.order_by(Asset.created_at.desc())
        assets, pagination = paginate_query(query, page, per_page)
        
        assets_data = []
        for asset in assets:
            asset_data = {
                'id': asset.id,
                'name': asset.name,
                'serial_number': asset.serial_number,
                'model': asset.model,
                'status': asset.status.value if asset.status else None,
                'location_id': asset.location_id,
                'location_name': asset.location.name if asset.location else None,
                'created_at': asset.created_at.isoformat() if asset.created_at else None
            }
            assets_data.append(asset_data)
        
        return jsonify(create_success_response(
            assets_data,
            f"Retrieved {len(assets_data)} inventory items",
            {"pagination": pagination}
        ))
        
    except Exception as e:
        response, status_code = create_error_response(
            "INTERNAL_ERROR",
            f"Error retrieving inventory: {str(e)}",
            500
        )
        return jsonify(response), status_code

@api_bp.route('/inventory/<int:asset_id>', methods=['GET'])
@require_api_key(permissions=['inventory:read'])
def get_inventory_item(asset_id):
    """Get detailed information about a specific inventory item"""
    try:
        asset = Asset.query.get(asset_id)
        
        if not asset:
            response, status_code = create_error_response(
                "RESOURCE_NOT_FOUND",
                f"Asset with ID {asset_id} not found",
                404
            )
            return jsonify(response), status_code
        
        # Get customer name
        customer_name = None
        try:
            if asset.customer_user:
                customer_name = asset.customer_user.name
        except:
            pass

        asset_data = {
            # Basic Info
            'id': asset.id,
            'asset_tag': asset.asset_tag,
            'serial_number': asset.serial_num,
            'name': asset.name,
            'model': asset.model,
            'manufacturer': asset.manufacturer,
            'category': asset.category,
            'status': asset.status.value if asset.status else None,

            # Hardware Specs
            'cpu_type': asset.cpu_type,
            'cpu_cores': asset.cpu_cores,
            'gpu_cores': asset.gpu_cores,
            'memory': asset.memory,
            'storage': asset.harddrive,
            'asset_type': asset.asset_type,
            'hardware_type': asset.hardware_type,

            # Condition Fields
            'condition': asset.condition,
            'is_erased': asset.erased,
            'has_keyboard': asset.keyboard,
            'has_charger': asset.charger,
            'diagnostics_code': asset.diag,

            # Location/Assignment Fields
            'current_customer': customer_name,
            'customer': asset.customer,
            'country': asset.country,
            'asset_company': asset.company.name if asset.company else None,
            'company_id': asset.company_id,
            'location_id': asset.location_id,
            'location_name': asset.location.name if asset.location else None,

            # Additional Fields
            'cost_price': asset.cost_price,
            'notes': asset.notes,
            'tech_notes': asset.tech_notes,
            'specifications': asset.specifications,
            'po': asset.po,
            'receiving_date': asset.receiving_date.isoformat() if asset.receiving_date else None,
            'created_at': asset.created_at.isoformat() if asset.created_at else None,
            'updated_at': asset.updated_at.isoformat() if asset.updated_at else None
        }
        
        return jsonify(create_success_response(
            asset_data,
            f"Retrieved asset {asset_id}"
        ))
        
    except Exception as e:
        response, status_code = create_error_response(
            "INTERNAL_ERROR",
            f"Error retrieving asset: {str(e)}",
            500
        )
        return jsonify(response), status_code

# Sync Endpoints for Mobile Apps

@api_bp.route('/sync/tickets', methods=['GET'])
@require_api_key(permissions=['sync:read'])
def sync_tickets():
    """
    Get tickets for incremental sync based on last modified timestamp
    
    Query Parameters:
        - since: ISO timestamp for incremental sync
        - limit: Maximum number of tickets to return (default: 100, max: 500)
    """
    try:
        since_param = request.args.get('since')
        limit = min(request.args.get('limit', 100, type=int), 500)
        
        query = Ticket.query
        
        if since_param:
            since_date = parse_datetime(since_param)
            if since_date:
                query = query.filter(Ticket.updated_at > since_date)
        
        query = query.order_by(Ticket.updated_at.asc()).limit(limit)
        tickets = query.all()
        
        tickets_data = []
        for ticket in tickets:
            ticket_data = {
                'id': ticket.id,
                'subject': ticket.subject,
                'description': ticket.description,
                'status': ticket.status,
                'priority': ticket.priority.name if ticket.priority else None,
                'category': ticket.category.name if ticket.category else None,
                'queue_id': ticket.queue_id,
                'queue_name': ticket.queue.name if ticket.queue else None,
                'customer_id': ticket.customer_user_id,
                'customer_name': ticket.customer_user.name if ticket.customer_user else None,
                'assigned_to_id': ticket.assigned_to_id,
                'assigned_to_name': ticket.assigned_to.name if ticket.assigned_to else None,
                'created_at': ticket.created_at.isoformat() if ticket.created_at else None,
                'updated_at': ticket.updated_at.isoformat() if ticket.updated_at else None,
                'sync_timestamp': datetime.utcnow().isoformat()
            }
            tickets_data.append(ticket_data)
        
        # Get the latest timestamp for next sync
        next_sync_timestamp = datetime.utcnow().isoformat()
        if tickets_data:
            next_sync_timestamp = max(ticket['updated_at'] for ticket in tickets_data)
        
        return jsonify(create_success_response(
            tickets_data,
            f"Retrieved {len(tickets_data)} tickets for sync",
            {
                "next_sync_timestamp": next_sync_timestamp,
                "has_more": len(tickets_data) == limit
            }
        ))
        
    except Exception as e:
        response, status_code = create_error_response(
            "INTERNAL_ERROR",
            f"Error syncing tickets: {str(e)}",
            500
        )
        return jsonify(response), status_code

# Comment Endpoints

@api_bp.route('/tickets/<int:ticket_id>/comments', methods=['GET'])
@require_api_key(permissions=['tickets:read'])
def get_ticket_comments(ticket_id):
    """Get all comments for a specific ticket"""
    try:
        # Get pagination parameters (match iOS app expectations)
        page = request.args.get('page', 1, type=int)
        limit = request.args.get('limit', 20, type=int)
        per_page = min(limit, 100)  # Cap at 100 for performance
        
        # Get the ticket first to ensure it exists
        ticket = Ticket.query.get(ticket_id)
        if not ticket:
            return jsonify({
                "success": False,
                "message": "Ticket not found"
            }), 404
        
        # Get paginated comments ordered by creation date (oldest first)
        from models.comment import Comment
        comments_query = Comment.query.filter_by(ticket_id=ticket_id).order_by(Comment.created_at.asc())
        comments_paginated = comments_query.paginate(
            page=page,
            per_page=per_page,
            error_out=False
        )
        
        # Format comments data to match iOS app expectations
        comments_data = []
        for comment in comments_paginated.items:
            comment_data = {
                'id': comment.id,
                'ticket_id': ticket_id,
                'content': comment.content,
                'author_name': comment.user.username if comment.user else None,
                'author_id': comment.user_id,
                'created_at': comment.created_at.isoformat() + 'Z' if comment.created_at else None,
                'updated_at': comment.updated_at.isoformat() + 'Z' if comment.updated_at else None
            }
            comments_data.append(comment_data)
        
        # Create response matching iOS app expectations
        response = {
            "data": comments_data,
            "meta": {
                "pagination": {
                    "page": comments_paginated.page,
                    "per_page": comments_paginated.per_page,
                    "total": comments_paginated.total,
                    "has_next": comments_paginated.has_next,
                    "has_prev": comments_paginated.has_prev
                }
            },
            "success": True,
            "message": "Comments retrieved successfully"
        }
        return jsonify(response), 200
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Error retrieving comments: {str(e)}"
        }), 500

@api_bp.route('/tickets/<int:ticket_id>/comments', methods=['POST'])
@require_api_key(permissions=['tickets:write'])
def create_ticket_comment(ticket_id):
    """Create a new comment on a specific ticket"""
    try:
        # Get request data
        data = request.get_json()
        if not data:
            return jsonify({
                "success": False,
                "message": "Request body must contain valid JSON"
            }), 400
        
        # Validate required fields
        content = data.get('content', '').strip()
        if not content:
            return jsonify({
                "success": False,
                "message": "Comment content is required and cannot be empty"
            }), 400
        
        # Validate content length (2000 characters as per iOS app)
        if len(content) > 2000:
            return jsonify({
                "success": False,
                "message": "Comment content cannot exceed 2000 characters"
            }), 400
        
        # Get the ticket to ensure it exists
        ticket = Ticket.query.get(ticket_id)
        if not ticket:
            return jsonify({
                "success": False,
                "message": "Ticket not found"
            }), 404
        
        # Get the user from the API key context
        user_id = g.api_user.id if hasattr(g, 'api_user') else None
        if not user_id:
            return jsonify({
                "success": False,
                "message": "Unable to identify user from API key"
            }), 401
        
        # Create the comment
        from models.comment import Comment
        from database import SessionLocal
        
        db_session = SessionLocal()
        try:
            comment = Comment(
                ticket_id=ticket_id,
                user_id=user_id,
                content=content
            )
            
            db_session.add(comment)
            db_session.commit()
            db_session.refresh(comment)  # Get the updated comment with relationships
            
            # Format comment data for response (match iOS app expectations)
            comment_data = {
                'id': comment.id,
                'ticket_id': ticket_id,
                'content': comment.content,
                'author_name': comment.user.username if comment.user else None,
                'author_id': comment.user_id,
                'created_at': comment.created_at.isoformat() + 'Z' if comment.created_at else None,
                'updated_at': comment.updated_at.isoformat() + 'Z' if comment.updated_at else None
            }
            
            # Create success response matching iOS app expectations
            response = {
                "data": comment_data,
                "success": True,
                "message": "Comment created successfully"
            }
            return jsonify(response), 201
            
        except Exception as db_error:
            db_session.rollback()
            raise db_error
        finally:
            db_session.close()
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Error creating comment: {str(e)}"
        }), 500

# Companies Endpoint

@api_bp.route('/companies', methods=['GET'])
def get_companies():
    """
    Get all companies with parent/child hierarchy
    No authentication required for internal use
    """
    try:
        from database import db_manager
        from models.company import Company

        db_session = db_manager.get_session()

        try:
            # Get all companies ordered by parent relationship
            companies = db_session.query(Company).order_by(
                Company.is_parent_company.desc(),
                Company.parent_company_id.asc(),
                Company.name.asc()
            ).all()

            companies_list = []
            for company in companies:
                company_data = {
                    'id': company.id,
                    'name': company.name,
                    'display_name': company.effective_display_name,
                    'grouped_display_name': company.grouped_display_name,
                    'is_parent_company': company.is_parent_company,
                    'parent_company_id': company.parent_company_id,
                    'parent_company_name': company.parent_company.name if company.parent_company else None
                }
                companies_list.append(company_data)

            return jsonify({
                'success': True,
                'companies': companies_list
            }), 200

        finally:
            db_session.close()

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error fetching companies: {str(e)}'
        }), 500

# Health Check Endpoint

@api_bp.route('/queues', methods=['GET'])
@require_api_key(permissions=['tickets:read'])
def list_queues():
    """
    Get list of all available queues

    Returns:
        List of queues with id and name
    """
    try:
        queues = Queue.query.order_by(Queue.name).all()

        queues_data = []
        for queue in queues:
            queue_data = {
                'id': queue.id,
                'name': queue.name,
                'description': queue.description if hasattr(queue, 'description') else None
            }
            queues_data.append(queue_data)

        return jsonify(create_success_response(
            queues_data,
            f"Retrieved {len(queues_data)} queues"
        ))

    except Exception as e:
        response, status_code = create_error_response(
            "INTERNAL_ERROR",
            f"Error retrieving queues: {str(e)}",
            500
        )
        return jsonify(response), status_code

@api_bp.route('/health', methods=['GET'])
def health_check():
    """API health check endpoint (no authentication required)"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    })

# Error handlers for the API blueprint

@api_bp.errorhandler(404)
def api_not_found(error):
    response, status_code = create_error_response(
        "ENDPOINT_NOT_FOUND",
        "The requested API endpoint was not found",
        404
    )
    return jsonify(response), status_code

@api_bp.errorhandler(405)
def api_method_not_allowed(error):
    response, status_code = create_error_response(
        "METHOD_NOT_ALLOWED",
        "The HTTP method is not allowed for this endpoint",
        405
    )
    return jsonify(response), status_code

@api_bp.errorhandler(500)
def api_internal_error(error):
    response, status_code = create_error_response(
        "INTERNAL_ERROR",
        "An internal server error occurred",
        500
    )
    return jsonify(response), status_code