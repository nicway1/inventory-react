from flask import Blueprint, render_template, redirect, url_for, session, request, flash, jsonify
from utils.auth_decorators import login_required, admin_required
from utils.store_instances import (
    user_store, activity_store, ticket_store, 
    inventory_store, queue_store
)
from utils.db_manager import DatabaseManager
from models.company import Company
from models.ticket import Ticket, TicketCategory, TicketStatus
import os
from werkzeug.utils import secure_filename
from models.asset import Asset
from models.accessory import Accessory
from models.customer_user import CustomerUser
from models.user import UserType, User
from sqlalchemy import func, or_
from models.activity import Activity
from models.permission import Permission
from database import SessionLocal
from sqlalchemy.orm import Session
from flask_login import current_user
import logging

main_bp = Blueprint('main', __name__)
db_manager = DatabaseManager()

# Configure upload settings for dashboard
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'xlsx', 'xls'}

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@main_bp.route('/debug-permissions-page')
@login_required
def debug_permissions_page():
    """Debug page to check permissions for the current user"""
    return render_template('debug_permissions.html')

@main_bp.route('/debug-permissions')
@login_required
def debug_permissions():
    """Debug route to check permissions for the current user"""
    user_permissions = {}
    
    if not current_user or not current_user.is_authenticated:
        return jsonify({
            "error": "User not authenticated",
            "user": None,
            "permissions": None
        })
        
    # Get user info
    user_info = {
        "id": current_user.id,
        "username": current_user.username,
        "user_type": current_user.user_type.value if current_user.user_type else None,
        "is_admin": current_user.is_admin,
        "is_supervisor": current_user.is_supervisor,
    }
    
    # Get permissions
    try:
        permissions = current_user.permissions
        if permissions:
            for attr in dir(permissions):
                if attr.startswith('can_') and not callable(getattr(permissions, attr)):
                    user_permissions[attr] = getattr(permissions, attr)
    except Exception as e:
        return jsonify({
            "error": str(e),
            "user": user_info,
            "permissions": None
        })
    
    return jsonify({
        "user": user_info,
        "permissions": user_permissions
    })

@main_bp.route('/', methods=['GET', 'POST'])
@login_required
def index():
    user_id = session['user_id']
    try:
        with db_manager as db:
            user = db.get_user(user_id)
            
        if not user:
            session.clear()
            return redirect(url_for('auth.login'))
        
        # Handle file upload if POST request
        if request.method == 'POST' and user.user_type in [UserType.SUPER_ADMIN, UserType.COUNTRY_ADMIN]:
            if 'file' not in request.files:
                flash('No file uploaded')
                return redirect(request.url)
            
            file = request.files['file']
            if file.filename == '':
                flash('No file selected')
                return redirect(request.url)
            
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                filepath = os.path.join(UPLOAD_FOLDER, filename)
                file.save(filepath)
                
                if inventory_store.import_from_excel(filepath):
                    flash('Inventory imported successfully')
                    # Clean up the uploaded file
                    os.remove(filepath)
                else:
                    flash('Error importing inventory')
                    
                return redirect(url_for('main.index'))
            else:
                flash('Invalid file type. Please upload an Excel file (.xlsx or .xls)')
                return redirect(request.url)
        elif request.method == 'POST':
            flash('You do not have permission to import data')
            return redirect(url_for('main.index'))

        # Get queues with filtering based on user permissions
        if user.user_type == UserType.SUPER_ADMIN:
            # Super admins can see all queues
            queues = queue_store.get_all_queues()
        else:
            # For all other user types, filter queues based on company permissions
            queues = []
            all_queues = queue_store.get_all_queues()
            for queue in all_queues:
                if user.can_access_queue(queue.id):
                    queues.append(queue)

        # Get counts from database with proper filtering
        queue_ticket_counts = {}
        for queue in queues:
            # Count ALL tickets for this queue
            total_ticket_query = db.session.query(Ticket).filter(Ticket.queue_id == queue.id)
            
            # Count OPEN tickets for this queue (exclude resolved tickets)
            open_ticket_query = db.session.query(Ticket).filter(
                Ticket.queue_id == queue.id,
                Ticket.status != TicketStatus.RESOLVED,
                Ticket.status != TicketStatus.RESOLVED_DELIVERED
            )
            
            # Apply COUNTRY_ADMIN filtering to both queries
            if user.user_type == UserType.COUNTRY_ADMIN:
                if user.assigned_country:
                    # Filter by assigned country
                    total_ticket_query = total_ticket_query.filter(Ticket.country == user.assigned_country.value)
                    open_ticket_query = open_ticket_query.filter(Ticket.country == user.assigned_country.value)
                if user.company_id:
                    # Filter by company association - tickets assigned to their company's users or assets
                    company_filter = or_(
                            Ticket.requester_id.in_(
                                db.session.query(User.id).filter(User.company_id == user.company_id)
                            ),
                            Ticket.assigned_to_id.in_(
                                db.session.query(User.id).filter(User.company_id == user.company_id)
                            ),
                            # Also include tickets related to assets from their company
                            Ticket.subject.in_(
                                db.session.query(Asset.asset_tag).filter(Asset.company_id == user.company_id)
                            )
                        )
                    total_ticket_query = total_ticket_query.filter(company_filter)
                    open_ticket_query = open_ticket_query.filter(company_filter)
            
            queue_ticket_counts[queue.id] = {
                'total': total_ticket_query.count(),
                'open': open_ticket_query.count()
            }
        
        # Apply filtering to asset counts for COUNTRY_ADMIN
        if user.user_type == UserType.COUNTRY_ADMIN:
            asset_query = db.session.query(Asset)
            if user.assigned_country:
                asset_query = asset_query.filter(Asset.country == user.assigned_country.value)
            if user.company_id:
                asset_query = asset_query.filter(Asset.company_id == user.company_id)
            tech_assets_count = asset_query.count()
        else:
            tech_assets_count = db.session.query(Asset).count()
        
        accessories_count = db.session.query(func.sum(Accessory.total_quantity)).scalar() or 0
        total_inventory = tech_assets_count + accessories_count
        
        # Apply filtering to customer counts for COUNTRY_ADMIN
        if user.user_type == UserType.COUNTRY_ADMIN and user.company_id:
            total_customers = db.session.query(CustomerUser).filter(
                CustomerUser.company_id == user.company_id
            ).count()
        else:
            total_customers = db.session.query(CustomerUser).count()
        
        # Apply filtering to total tickets for COUNTRY_ADMIN
        if user.user_type == UserType.COUNTRY_ADMIN:
            total_ticket_query = db.session.query(Ticket)
            if user.assigned_country:
                total_ticket_query = total_ticket_query.filter(Ticket.country == user.assigned_country.value)
            if user.company_id:
                total_ticket_query = total_ticket_query.filter(
                    or_(
                        Ticket.requester_id.in_(
                            db.session.query(User.id).filter(User.company_id == user.company_id)
                        ),
                        Ticket.assigned_to_id.in_(
                            db.session.query(User.id).filter(User.company_id == user.company_id)
                        ),
                        Ticket.subject.in_(
                            db.session.query(Asset.asset_tag).filter(Asset.company_id == user.company_id)
                        )
                    )
                )
            total_tickets = total_ticket_query.count()
        else:
            total_tickets = db.session.query(Ticket).count()
        
        # Get shipment tickets with filtering for COUNTRY_ADMIN
        shipment_tickets = []
        # Only load shipment tickets for non-CLIENT users
        if user.user_type != UserType.CLIENT:
            shipment_query = db.session.query(Ticket).filter(
                Ticket.category.in_([
                    TicketCategory.ASSET_CHECKOUT,
                    TicketCategory.ASSET_CHECKOUT_SINGPOST,
                    TicketCategory.ASSET_CHECKOUT_DHL,
                    TicketCategory.ASSET_CHECKOUT_UPS,
                    TicketCategory.ASSET_CHECKOUT_BLUEDART,
                    TicketCategory.ASSET_CHECKOUT_DTDC,
                    TicketCategory.ASSET_CHECKOUT_AUTO,
                    TicketCategory.ASSET_CHECKOUT_CLAW,
                    TicketCategory.ASSET_RETURN_CLAW
                ])
            )
            
            # Apply COUNTRY_ADMIN filtering to shipment tickets
            if user.user_type == UserType.COUNTRY_ADMIN:
                if user.assigned_country:
                    shipment_query = shipment_query.filter(Ticket.country == user.assigned_country.value)
                if user.company_id:
                    shipment_query = shipment_query.filter(
                        or_(
                            Ticket.requester_id.in_(
                                db.session.query(User.id).filter(User.company_id == user.company_id)
                            ),
                            Ticket.assigned_to_id.in_(
                                db.session.query(User.id).filter(User.company_id == user.company_id)
                            ),
                            Ticket.subject.in_(
                                db.session.query(Asset.asset_tag).filter(Asset.company_id == user.company_id)
                            )
                        )
                    )
            
            shipment_tickets = shipment_query.order_by(Ticket.created_at.desc()).all()

        # Calculate summary statistics
        stats = {
            'total_inventory': total_inventory,
            'total_shipments': total_tickets,  # Using total_tickets instead of shipments
            'total_queues': len(queues),
            'total_customers': total_customers
        }

        # Get activities
        activities = activity_store.get_user_activities(user_id)

        # Get user activities
        user_activities = []
        if 'user_id' in session:
            user_id = session['user_id']
            user_activities = activity_store.get_user_activities(user_id)
        
        # Get counts for dashboard with filtering for COUNTRY_ADMIN
        if user.user_type == UserType.COUNTRY_ADMIN:
            asset_query = db.session.query(Asset)
            if user.assigned_country:
                asset_query = asset_query.filter(Asset.country == user.assigned_country.value)
            if user.company_id:
                asset_query = asset_query.filter(Asset.company_id == user.company_id)
            
            total_assets = asset_query.count()
            deployed_assets = asset_query.filter(Asset.status == 'DEPLOYED').count()
            in_stock_assets = asset_query.filter(Asset.status == 'IN_STOCK').count()
        else:
            total_assets = db.session.query(Asset).count()
            deployed_assets = db.session.query(Asset).filter(Asset.status == 'DEPLOYED').count()
            in_stock_assets = db.session.query(Asset).filter(Asset.status == 'IN_STOCK').count()
        
        # Accessory counts
        total_accessories = db.session.query(Accessory).count()
        
        # Ticket counts with filtering for COUNTRY_ADMIN
        if user.user_type == UserType.COUNTRY_ADMIN:
            open_ticket_query = db.session.query(Ticket).filter(
                Ticket.status != TicketStatus.RESOLVED,
                Ticket.status != TicketStatus.RESOLVED_DELIVERED
            )
            resolved_ticket_query = db.session.query(Ticket).filter(
                Ticket.status.in_([TicketStatus.RESOLVED, TicketStatus.RESOLVED_DELIVERED])
            )
            
            if user.assigned_country:
                open_ticket_query = open_ticket_query.filter(Ticket.country == user.assigned_country.value)
                resolved_ticket_query = resolved_ticket_query.filter(Ticket.country == user.assigned_country.value)
                
            if user.company_id:
                company_filter = or_(
                    Ticket.requester_id.in_(
                        db.session.query(User.id).filter(User.company_id == user.company_id)
                    ),
                    Ticket.assigned_to_id.in_(
                        db.session.query(User.id).filter(User.company_id == user.company_id)
                    ),
                    Ticket.subject.in_(
                        db.session.query(Asset.asset_tag).filter(Asset.company_id == user.company_id)
                    )
                )
                open_ticket_query = open_ticket_query.filter(company_filter)
                resolved_ticket_query = resolved_ticket_query.filter(company_filter)
            
            open_tickets = open_ticket_query.count()
            resolved_tickets = resolved_ticket_query.count()
        else:
            open_tickets = db.session.query(Ticket).filter(
                Ticket.status != TicketStatus.RESOLVED,
                Ticket.status != TicketStatus.RESOLVED_DELIVERED
            ).count()
            resolved_tickets = db.session.query(Ticket).filter(
                Ticket.status.in_([TicketStatus.RESOLVED, TicketStatus.RESOLVED_DELIVERED])
            ).count()
        
        # Get the 5 most recent activities for all users (no filtering needed here)
        recent_activities = db.session.query(Activity).order_by(
            Activity.created_at.desc()
        ).limit(5).all()
        
        # Get user count (no filtering needed)
        user_count = db.session.query(User).count()
        
        # Get ticket counts
        ticket_counts = {
            'total': total_tickets,
            'open': open_tickets,
            'resolved': resolved_tickets
        }

        return render_template('home.html',
            queues=queues,
            queue_ticket_counts=queue_ticket_counts,
            stats=stats,
            activities=activities,
            user=user,
            singpost_tickets=shipment_tickets,
            user_activities=user_activities,
            total_assets=total_assets,
            deployed_assets=deployed_assets,
            in_stock_assets=in_stock_assets,
            total_accessories=total_accessories,
            open_tickets=open_tickets,
            recent_activities=recent_activities,
            user_count=user_count,
            ticket_counts=ticket_counts
        )
    except Exception as e:
        logging.error(f"Error in index route: {str(e)}", exc_info=True)
        flash('An error occurred while loading the dashboard')
        return redirect(url_for('auth.login'))

@main_bp.route('/refresh-supervisor-permissions')
def refresh_supervisor_permissions():
    """Force refresh permissions for all supervisor users"""
    try:
        # Get a database session
        db_session = SessionLocal()
        
        try:
            # Get the permission record for supervisors
            supervisor_permission = db_session.query(Permission).filter_by(
                user_type=UserType.SUPERVISOR
            ).first()
            
            # If no permission record exists, create one with default permissions
            if not supervisor_permission:
                default_permissions = Permission.get_default_permissions(UserType.SUPERVISOR)
                supervisor_permission = Permission(
                    user_type=UserType.SUPERVISOR, 
                    **default_permissions
                )
                db_session.add(supervisor_permission)
            else:
                # Update the existing permission with new defaults
                default_permissions = Permission.get_default_permissions(UserType.SUPERVISOR)
                for key, value in default_permissions.items():
                    setattr(supervisor_permission, key, value)
            
            # Commit the changes
            db_session.commit()
            
            # Return success
            return "Supervisor permissions updated successfully! Please log out and log back in to see the changes."
            
        finally:
            db_session.close()
            
    except Exception as e:
        return f"Error updating permissions: {str(e)}"

@main_bp.route('/fix-supervisor-permissions')
def fix_supervisor_permissions():
    """Force set can_edit_assets=True for supervisors directly in the database"""
    try:
        # Get a database session
        db_session = SessionLocal()
        
        try:
            # Get the permission record for supervisors
            supervisor_permission = db_session.query(Permission).filter_by(
                user_type=UserType.SUPERVISOR
            ).first()
            
            if not supervisor_permission:
                return "No supervisor permission record found."
            
            # Update the can_edit_assets permission
            supervisor_permission.can_edit_assets = True
            
            # Commit the changes
            db_session.commit()
            
            # Return success
            return "Successfully set can_edit_assets=True for supervisors!"
            
        finally:
            db_session.close()
            
    except Exception as e:
        return f"Error updating permissions: {str(e)}"