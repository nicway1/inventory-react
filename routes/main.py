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
from sqlalchemy import func
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
    user = db_manager.get_user(user_id)
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

    # Get queues
    queues = queue_store.get_all_queues()

    # Get counts from database
    db_session = db_manager.get_session()
    try:
        tech_assets_count = db_session.query(Asset).count()
        accessories_count = db_session.query(func.sum(Accessory.total_quantity)).scalar() or 0
        total_inventory = tech_assets_count + accessories_count
        total_customers = db_session.query(CustomerUser).count()
        total_tickets = db_session.query(Ticket).count()
        
        # Get all shipment tickets (all carriers)
        shipment_tickets = db_session.query(Ticket).filter(
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
        ).order_by(Ticket.created_at.desc()).all()
    finally:
        db_session.close()

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
    
    # Get counts for dashboard
    db_session = SessionLocal()
    try:
        # Asset counts
        total_assets = db_session.query(Asset).count()
        deployed_assets = db_session.query(Asset).filter(Asset.status == 'DEPLOYED').count()
        in_stock_assets = db_session.query(Asset).filter(Asset.status == 'IN_STOCK').count()
        
        # Accessory counts
        total_accessories = db_session.query(Accessory).count()
        
        # Ticket counts
        open_tickets = db_session.query(Ticket).filter(
            Ticket.status != TicketStatus.CLOSED,
            Ticket.status != TicketStatus.RESOLVED
        ).count()
        
        # Get the 5 most recent activities for all users
        recent_activities = db_session.query(Activity).order_by(
            Activity.created_at.desc()
        ).limit(5).all()
        
        # Get user count
        user_count = db_session.query(User).count()
        
    except Exception as e:
        logging.error(f"Error fetching dashboard data: {str(e)}")
        total_assets = deployed_assets = in_stock_assets = total_accessories = open_tickets = 0
        recent_activities = []
        user_count = 0
    finally:
        db_session.close()

    return render_template('home.html',
        queues=queues,
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
        user_count=user_count
    )

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
            
            # If no permission record exists, create one with default permissions
            if not supervisor_permission:
                default_permissions = Permission.get_default_permissions(UserType.SUPERVISOR)
                supervisor_permission = Permission(
                    user_type=UserType.SUPERVISOR, 
                    **default_permissions
                )
                supervisor_permission.can_edit_assets = True
                db_session.add(supervisor_permission)
            else:
                # Force set can_edit_assets to True
                supervisor_permission.can_edit_assets = True
            
            # Commit the changes
            db_session.commit()
            
            # Return success
            return "Supervisor permissions updated successfully! Can edit assets is now set to TRUE. Please log out and log back in to see the changes."
            
        finally:
            db_session.close()
            
    except Exception as e:
        return f"Error updating permissions: {str(e)}"