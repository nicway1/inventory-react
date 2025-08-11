from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash, current_app, session, send_file
from flask_login import current_user
from flask_wtf.csrf import CSRFProtect
from utils.auth_decorators import admin_required, super_admin_required, login_required
import logging
from utils.snipeit_client import SnipeITClient
from utils.db_manager import DatabaseManager
from models.user import User, UserType, Country
from models.permission import Permission
from datetime import datetime
from models.company import Company
from models.queue import Queue
from models.company_queue_permission import CompanyQueuePermission
from utils.email_sender import send_welcome_email
from sqlalchemy import or_, func, and_
import os
import shutil
import glob
from werkzeug.utils import secure_filename
import uuid
from werkzeug.security import generate_password_hash
from utils.auth import safe_generate_password_hash
from database import SessionLocal
from models.activity import Activity
from models.asset_history import AssetHistory
from models.accessory_history import AccessoryHistory
import traceback
from models.firecrawl_key import FirecrawlKey
from models.ticket_category_config import TicketCategoryConfig, CategoryDisplayConfig
import tempfile
import sqlite3
import subprocess
import pandas as pd
import csv
import io
import json
from models.ticket import Ticket, TicketStatus, TicketPriority, TicketCategory
from models.customer_user import CustomerUser
from models.asset import Asset
from sqlalchemy import text
from models.accessory import Accessory
from models.company_customer_permission import CompanyCustomerPermission

admin_bp = Blueprint('admin', __name__)
snipe_client = SnipeITClient()
db_manager = DatabaseManager()
csrf = CSRFProtect()

# Set up logging for this module
logger = logging.getLogger(__name__)

def cleanup_old_csv_files():
    """Clean up old CSV temporary files (older than 1 hour)"""
    try:
        import glob
        import time
        temp_dir = tempfile.gettempdir()
        pattern = os.path.join(temp_dir, 'csv_import_*.json')
        current_time = time.time()
        
        for filepath in glob.glob(pattern):
            file_age = current_time - os.path.getmtime(filepath)
            if file_age > 3600:  # 1 hour
                try:
                    os.remove(filepath)
                    logger.info(f"DEBUG: Cleaned up old CSV file: {filepath}")
                except Exception as e:
                    logger.info(f"DEBUG: Failed to cleanup {filepath}: {e}")
    except Exception as e:
        logger.info(f"DEBUG: CSV cleanup error: {e}")

def allowed_file(filename):
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_company_logo(file):
    if file and allowed_file(file.filename):
        # Generate a unique filename
        filename = str(uuid.uuid4()) + os.path.splitext(file.filename)[1]
        file.save(os.path.join('static/company_logos', filename))
        return filename
    return None

@admin_bp.route('/permission-management')
@admin_required
def permission_management():
    """Manage user type permissions"""
    if 'user_id' not in session:
        flash('Please log in to continue', 'error')
        return redirect(url_for('auth.login'))

    db_session = db_manager.get_session()
    try:
        # Get current user
        user = db_manager.get_user(session['user_id'])
        if not user:
            session.clear()
            return redirect(url_for('auth.login'))

        # Get all permissions
        permissions = db_session.query(Permission).all()
        
        # Check for duplicate permissions and remove them
        user_types_seen = set()
        duplicates_found = False
        
        for permission in permissions[:]:  # Use a copy of the list to avoid modification issues
            if permission.user_type in user_types_seen:
                # This is a duplicate
                duplicates_found = True
                db_session.delete(permission)
            else:
                user_types_seen.add(permission.user_type)
        
        if duplicates_found:
            db_session.commit()
            permissions = db_session.query(Permission).all()  # Refresh the list
        
        # Initialize default permissions if needed
        existing_types = {p.user_type for p in permissions}
        missing_types = [user_type for user_type in UserType if user_type not in existing_types]
        
        if missing_types:
            for user_type in missing_types:
                default_permissions = Permission.get_default_permissions(user_type)
                permission = Permission(user_type=user_type, **default_permissions)
                db_session.add(permission)
            db_session.commit()
            permissions = db_session.query(Permission).all()

        return render_template('admin/permission_management.html', 
                             permissions=permissions,
                             user=user,
                             UserType=UserType)
    except Exception as e:
        db_session.rollback()
        flash(f'Error loading permissions: {str(e)}', 'error')
        return redirect(url_for('main.index'))
    finally:
        db_session.close()

@admin_bp.route('/companies')
@admin_required
def manage_companies():
    """List all companies"""
    companies = db_manager.get_all_companies()
    return render_template('admin/companies/list.html', companies=companies)

@admin_bp.route('/companies/create', methods=['GET', 'POST'])
@admin_required
def create_company():
    """Create a new company"""
    if request.method == 'POST':
        name = request.form.get('name')
        contact_name = request.form.get('contact_name')
        contact_email = request.form.get('contact_email')
        address = request.form.get('address')
        
        # Handle logo upload
        logo_path = None
        if 'logo' in request.files:
            logo_file = request.files['logo']
            logo_path = save_company_logo(logo_file)

        try:
            company = Company(
                name=name,
                contact_name=contact_name,
                contact_email=contact_email,
                address=address,
                logo_path=logo_path
            )
            db_session = db_manager.get_session()
            db_session.add(company)
            db_session.commit()
            flash('Company created successfully', 'success')
            return redirect(url_for('admin.manage_companies'))
        except Exception as e:
            flash(f'Error creating company: {str(e)}', 'error')
            return redirect(url_for('admin.create_company'))

    return render_template('admin/create_company.html')

@admin_bp.route('/companies/<int:company_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_company(company_id):
    """Edit an existing company"""
    db_session = db_manager.get_session()
    company = db_session.query(Company).get(company_id)
    
    if not company:
        flash('Company not found', 'error')
        return redirect(url_for('admin.manage_companies'))

    if request.method == 'POST':
        company.name = request.form.get('name')
        company.contact_name = request.form.get('contact_name')
        company.contact_email = request.form.get('contact_email')
        company.address = request.form.get('address')
        
        # Handle logo upload
        if 'logo' in request.files:
            logo_file = request.files['logo']
            if logo_file.filename:
                # Delete old logo if it exists
                if company.logo_path:
                    old_logo_path = os.path.join('static/company_logos', company.logo_path)
                    if os.path.exists(old_logo_path):
                        os.remove(old_logo_path)
                
                # Save new logo
                logo_path = save_company_logo(logo_file)
                if logo_path:
                    company.logo_path = logo_path

        try:
            db_session.commit()
            flash('Company updated successfully', 'success')
            return redirect(url_for('admin.manage_companies'))
        except Exception as e:
            db_session.rollback()
            flash(f'Error updating company: {str(e)}', 'error')
    
    return render_template('admin/create_company.html', company=company)

@admin_bp.route('/companies/<int:company_id>/delete', methods=['POST'])
@admin_required
def delete_company(company_id):
    """Delete a company"""
    logger.info("DEBUG: Delete company request received for company_id={company_id}")
    
    db_session = db_manager.get_session()
    try:
        # Check if company exists
        company = db_session.query(Company).get(company_id)
        if not company:
            logger.info("DEBUG: Company with ID {company_id} not found")
            flash('Company not found', 'error')
            return redirect(url_for('admin.manage_companies'))
        
        # Check if company has associated users
        users_count = db_session.query(User).filter_by(company_id=company_id).count()
        if users_count > 0:
            logger.info("DEBUG: Cannot delete company - it has {users_count} associated users")
            flash(f'Cannot delete company: It has {users_count} associated users. Please reassign or delete the users first.', 'error')
            return redirect(url_for('admin.manage_companies'))
        
        # First delete all related company queue permissions
        logger.info("DEBUG: Deleting queue permissions for company_id={company_id}")
        deleted_permissions = db_session.query(CompanyQueuePermission).filter_by(company_id=company_id).delete()
        logger.info("DEBUG: Deleted {deleted_permissions} queue permissions")
        
        # Then delete the company
        logger.info("DEBUG: Deleting company: {company.name} (ID: {company.id})")
        db_session.delete(company)
        db_session.commit()
        flash('Company deleted successfully', 'success')
        return redirect(url_for('admin.manage_companies'))
    
    except Exception as e:
        db_session.rollback()
        logger.info("DEBUG: Error deleting company: {str(e)}")
        logger.info("DEBUG: {traceback.format_exc()}")
        flash(f'Error deleting company: {str(e)}', 'error')
        return redirect(url_for('admin.manage_companies'))
    
    finally:
        db_session.close()

@admin_bp.route('/users')
@admin_required
def manage_users():
    users = db_manager.get_all_users()
    return render_template('admin/users.html', users=users)

@admin_bp.route('/users/create', methods=['GET', 'POST'])
@admin_required
def create_user():
    """Create a new user"""
    from models.user import User, UserType, Country
    
    db_session = db_manager.get_session()
    try:
        companies = db_session.query(Company).all()
        
        if request.method == 'POST':
            username = request.form.get('username')
            email = request.form.get('email')
            password = request.form.get('password')
            company_id = request.form.get('company_id')
            user_type = request.form.get('user_type')
            assigned_country = request.form.get('assigned_country')

            # Check if user with this email already exists
            existing_user = db_session.query(User).filter_by(email=email).first()
            if existing_user:
                flash('A user with this email already exists. Please use a different email address.', 'error')
                companies_data = [{'id': c.id, 'name': c.name} for c in companies]
                return render_template('admin/create_user.html', companies=companies_data)

            try:
                # Create user data dictionary
                user_data = {
                    'username': username,
                    'email': email,
                    'password_hash': safe_generate_password_hash(password),
                    'company_id': company_id if company_id else None,
                    'user_type': UserType[user_type]
                }

                # Add assigned country for Country Admin
                if user_type == 'COUNTRY_ADMIN':
                    if not assigned_country:
                        flash('Country selection is required for Country Admin', 'error')
                        return render_template('admin/create_user.html', companies=companies)
                    user_data['assigned_country'] = Country[assigned_country]
                
                # Company is required for CLIENT users
                if user_type == 'CLIENT' and not company_id:
                    flash('Company selection is required for Client users', 'error')
                    companies_data = [{'id': c.id, 'name': c.name} for c in companies]
                    return render_template('admin/create_user.html', companies=companies_data)

                user = User(**user_data)
                db_session.add(user)
                db_session.commit()

                # Send welcome email
                if send_welcome_email(email, username, password):
                    flash('User created successfully and welcome email sent', 'success')
                else:
                    flash('User created successfully but failed to send welcome email', 'warning')

                return redirect(url_for('admin.manage_users'))
            except Exception as e:
                db_session.rollback()
                flash(f'Error creating user: {str(e)}', 'error')
                companies_data = [{'id': c.id, 'name': c.name} for c in companies]
                return render_template('admin/create_user.html', companies=companies_data)

        # Convert companies to list of dicts to avoid detached instance errors
        companies_data = [{'id': c.id, 'name': c.name} for c in companies]
        return render_template('admin/create_user.html', companies=companies_data)
    finally:
        db_session.close()

@admin_bp.route('/users/<int:user_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_user(user_id):
    """Edit an existing user"""
    logger.info("DEBUG: Entering edit_user route for user_id={user_id}")
    db_session = db_manager.get_session()
    user = db_session.query(User).get(user_id)
    if not user:
        logger.info("DEBUG: User not found")
        flash('User not found', 'error')
        return redirect(url_for('admin.manage_users'))

    logger.info("DEBUG: User found: {user.username}, type={user.user_type}")
    companies = db_session.query(Company).all()
    logger.info("DEBUG: Found {len(companies)} companies")

    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        company_id = request.form.get('company_id')
        user_type = request.form.get('user_type')
        password = request.form.get('password')
        assigned_country = request.form.get('assigned_country')

        logger.info("DEBUG: Form submission - company_id={company_id}, user_type={user_type}")

        try:
            # Update basic user information
            user.username = username
            user.email = email
            user.user_type = UserType[user_type]

            # Handle company assignment
            user.company_id = company_id if company_id else None
            
            # Company is required for CLIENT users
            if user_type == 'CLIENT' and not company_id:
                logger.info("DEBUG: CLIENT type but no company selected")
                flash('Company selection is required for Client users', 'error')
                return render_template('admin/edit_user.html', user=user, companies=companies)

            # Update password if provided
            if password:
                user.password_hash = safe_generate_password_hash(password)

            # Handle country assignment
            if user_type == 'COUNTRY_ADMIN':
                if not assigned_country:
                    flash('Country selection is required for Country Admin', 'error')
                    return render_template('admin/edit_user.html', user=user, companies=companies)
                user.assigned_country = Country[assigned_country]
            else:
                user.assigned_country = None

            db_session.commit()
            flash('User updated successfully', 'success')
            return redirect(url_for('admin.manage_users'))
        except Exception as e:
            db_session.rollback()
            logger.info("DEBUG: Error updating user: {str(e)}")
            flash(f'Error updating user: {str(e)}', 'error')
        finally:
            db_session.close()

    logger.info("DEBUG: Rendering edit_user template")
    return render_template('admin/edit_user.html', user=user, companies=companies)

@admin_bp.route('/users/<int:user_id>/delete', methods=['POST'])
@admin_required
def delete_user(user_id):
    user = db_manager.get_user(user_id)
    if not user:
        flash('User not found', 'error')
        return redirect(url_for('admin.manage_users'))

    if user.is_admin:
        flash('Cannot delete admin user', 'error')
        return redirect(url_for('admin.manage_users'))

    try:
        db_manager.delete_user(user_id)
        flash('User deleted successfully', 'success')
    except Exception as e:
        flash(f'Error deleting user: {str(e)}', 'error')

    return redirect(url_for('admin.manage_users'))

@admin_bp.route('/users/<int:user_id>/manage')
@admin_required
def manage_user(user_id):
    user = db_manager.get_user(user_id)
    if not user:
        flash('User not found', 'error')
        return redirect(url_for('admin.manage_users'))

    # Get user's activities, assigned assets, etc.
    activities = db_manager.get_user_activities(user_id)
    assigned_assets = db_manager.get_user_assets(user_id)

    return render_template('admin/manage_user.html', 
                         user=user, 
                         activities=activities,
                         assigned_assets=assigned_assets)

@admin_bp.route('/permissions/update', methods=['POST'])
@super_admin_required
def update_permissions():
    """Update user type permissions based on form data"""
    if 'user_id' not in session:
        flash('Please log in to continue', 'error')
        return redirect(url_for('auth.login'))

    db_session = db_manager.get_session()
    try:
        # Log the form data
        logger.info("Form data received:", request.form)
        
        user_type = request.form.get('user_type')
        logger.info("User type:", user_type)
        
        if not user_type:
            flash('User type is required', 'error')
            return redirect(url_for('admin.permission_management'))

        try:
            user_type_enum = UserType[user_type]
            logger.info("User type enum:", user_type_enum)
        except KeyError:
            flash('Invalid user type', 'error')
            return redirect(url_for('admin.permission_management'))

        # Get existing permission record
        permission = db_session.query(Permission).filter_by(user_type=user_type_enum).first()
        logger.info("Existing permission:", permission)
        
        if not permission:
            permission = Permission(user_type=user_type_enum)
            db_session.add(permission)
            logger.info("Created new permission record")

        # Get all permission fields
        fields = Permission.permission_fields()
        logger.info("Permission fields:", fields)

        # Update permissions from form data
        for field in fields:
            old_value = getattr(permission, field)
            # Check if the field exists in form and its value is 'true'
            new_value = request.form.get(field) == 'true'
            setattr(permission, field, new_value)
            logger.info("Updating {field}: {old_value} -> {new_value}")

        db_session.commit()
        logger.info("Changes committed successfully")
        
        flash('Permissions updated successfully', 'success')
        return redirect(url_for('admin.permission_management'))
    except Exception as e:
        db_session.rollback()
        logger.error("Error updating permissions:", str(e))
        flash(f'Error updating permissions: {str(e)}', 'error')
        return redirect(url_for('admin.permission_management'))
    finally:
        db_session.close()

@admin_bp.route('/permissions/reset/<user_type>', methods=['POST'])
@super_admin_required
def reset_permissions(user_type):
    """Reset permissions for a user type to default values"""
    if 'user_id' not in session:
        flash('Please log in to continue', 'error')
        return redirect(url_for('auth.login'))

    db_session = db_manager.get_session()
    try:
        # Validate user type
        try:
            user_type_enum = UserType[user_type]
        except KeyError:
            flash('Invalid user type', 'error')
            return redirect(url_for('admin.permission_management'))

        # Delete existing permissions
        db_session.query(Permission).filter_by(user_type=user_type_enum).delete()
        
        # Get default permissions
        default_permissions = Permission.get_default_permissions(user_type_enum)
        
        # Create new permission record with defaults
        permission = Permission(user_type=user_type_enum, **default_permissions)
        db_session.add(permission)
        db_session.commit()
        
        flash('Permissions reset to default values', 'success')
        return redirect(url_for('admin.permission_management'))
    except Exception as e:
        db_session.rollback()
        flash(f'Error resetting permissions: {str(e)}', 'error')
        return redirect(url_for('admin.permission_management'))
    finally:
        db_session.close()

@admin_bp.route('/users/<int:user_id>/resend-welcome', methods=['POST'])
@admin_required
def resend_welcome_email(user_id):
    """Resend welcome email to a user"""
    db_session = db_manager.get_session()
    try:
        user = db_session.query(User).get(user_id)
        if not user:
            flash('User not found', 'error')
            return redirect(url_for('admin.manage_users'))

        # Generate a new password for the user
        new_password = str(uuid.uuid4())[:8]  # Use first 8 characters of a UUID as password
        user.password_hash = safe_generate_password_hash(new_password)
        db_session.commit()

        # Send welcome email with new credentials
        if send_welcome_email(user.email, user.username, new_password):
            flash('Welcome email sent successfully with new credentials', 'success')
        else:
            flash('Failed to send welcome email', 'error')

    except Exception as e:
        db_session.rollback()
        flash(f'Error resending welcome email: {str(e)}', 'error')
    finally:
        db_session.close()
    
    return redirect(url_for('admin.manage_users'))

@admin_bp.route('/history')
@super_admin_required
def view_history():
    """View all system history/activity logs"""
    db_session = db_manager.get_session()
    try:
        # Get all activities with user information, ordered by most recent first
        activities = (db_session.query(Activity)
                     .join(Activity.user)
                     .order_by(Activity.created_at.desc())
                     .all())
        
        # Get all asset history with user information
        asset_history = (db_session.query(AssetHistory)
                        .join(AssetHistory.user)
                        .join(AssetHistory.asset)
                        .order_by(AssetHistory.created_at.desc())
                        .all())
                        
        # Get all accessory history with user information
        accessory_history = (db_session.query(AccessoryHistory)
                           .join(AccessoryHistory.user)
                           .join(AccessoryHistory.accessory)
                           .order_by(AccessoryHistory.created_at.desc())
                           .all())

        return render_template('admin/history.html',
                             activities=activities,
                             asset_history=asset_history,
                             accessory_history=accessory_history)
    finally:
        db_session.close()

@admin_bp.route('/update-user-type-permissions/<user_type>')
@admin_required
def update_user_type_permissions(user_type):
    """Update permissions for all users of a specific type"""
    try:
        # Convert string to UserType enum
        user_type_enum = UserType[user_type.upper()]
        
        # Get the session
        session = db_manager.get_session()
        
        try:
            # Get or create permission for this user type
            permission = session.query(Permission).filter_by(user_type=user_type_enum).first()
            
            if not permission:
                # Create new permission with default values
                default_permissions = Permission.get_default_permissions(user_type_enum)
                permission = Permission(user_type=user_type_enum, **default_permissions)
                session.add(permission)
            else:
                # Update existing permission with default values
                default_permissions = Permission.get_default_permissions(user_type_enum)
                for key, value in default_permissions.items():
                    setattr(permission, key, value)
            
            session.commit()
            flash(f'Successfully updated permissions for {user_type}', 'success')
            
        finally:
            session.close()
            
        return redirect(url_for('admin.manage_permissions'))
        
    except KeyError:
        flash(f'Invalid user type: {user_type}', 'error')
        return redirect(url_for('admin.manage_permissions'))
    except Exception as e:
        flash(f'Error updating permissions: {str(e)}', 'error')
        return redirect(url_for('admin.manage_permissions'))

@admin_bp.route('/queue-permissions')
@super_admin_required
def manage_queue_permissions():
    """Manage which companies can see which queues"""
    db_session = db_manager.get_session()
    try:
        companies = db_session.query(Company).all()
        queues = db_session.query(Queue).all()
        permissions = db_session.query(CompanyQueuePermission).all()
        
        # Create a mapping of company_id -> queue_id -> permission for easier access in template
        permission_map = {}
        for permission in permissions:
            if permission.company_id not in permission_map:
                permission_map[permission.company_id] = {}
            permission_map[permission.company_id][permission.queue_id] = permission
        
        return render_template('admin/queue_permissions_new.html',
                              companies=companies,
                              queues=queues,
                              permission_map=permission_map)
    except Exception as e:
        flash(f'Error loading queue permissions: {str(e)}', 'error')
        return redirect(url_for('admin.index'))
    finally:
        db_session.close()

@admin_bp.route('/queue-permissions/update', methods=['POST'])
@super_admin_required
def update_queue_permissions():
    """Update queue permissions for companies"""
    try:
        # Debug incoming request data
        logger.info(f"Form data received: {request.form}")
        logger.info(f"JSON data received: {request.get_json(silent=True)}")
        
        # Try multiple ways to get the data
        if request.form:
            company_id = request.form.get('company_id')
            queue_id = request.form.get('queue_id')
            has_permission = 'has_permission' in request.form
            can_view = 'can_view' in request.form
            can_create = 'can_create' in request.form
        else:
            data = request.get_json(silent=True) or {}
            company_id = data.get('company_id')
            queue_id = data.get('queue_id')
            has_permission = data.get('has_permission', False)
            can_view = data.get('can_view', False)
            can_create = data.get('can_create', False)
        
        logger.info(f"Raw company_id: {company_id}, type: {type(company_id)}")
        logger.info(f"Raw queue_id: {queue_id}, type: {type(queue_id)}")
        
        # Convert to integers with safer handling
        try:
            if company_id:
                company_id = int(company_id)
            if queue_id:
                queue_id = int(queue_id)
        except (ValueError, TypeError) as e:
            logger.info(f"Error converting IDs to integers: {str(e)}")
            flash(f"Invalid ID format: {str(e)}", 'error')
            return redirect(url_for('admin.manage_queue_permissions'))
        
        logger.info(f"Converted company_id: {company_id}, queue_id: {queue_id}")
        logger.info(f"Permission values - has_permission: {has_permission}, can_view: {can_view}, can_create: {can_create}")
        
        if not company_id or not queue_id:
            logger.info("INVALID: Missing company_id or queue_id")
            flash('Invalid company or queue ID', 'error')
            return redirect(url_for('admin.manage_queue_permissions'))
        
        db_session = db_manager.get_session()
        try:
            # Verify company and queue exist
            company = db_session.query(Company).get(company_id)
            queue = db_session.query(Queue).get(queue_id)
            
            if not company:
                logger.info(f"Company with ID {company_id} not found")
                flash(f"Company with ID {company_id} not found", 'error')
                return redirect(url_for('admin.manage_queue_permissions'))
                
            if not queue:
                logger.info(f"Queue with ID {queue_id} not found")
                flash(f"Queue with ID {queue_id} not found", 'error')
                return redirect(url_for('admin.manage_queue_permissions'))
            
            # Check if permission already exists
            permission = db_session.query(CompanyQueuePermission).filter_by(
                company_id=company_id, queue_id=queue_id).first()
            
            logger.info(f"Existing permission found: {permission is not None}")
            
            if not has_permission:
                # If no permission should be granted, delete existing permission if it exists
                if permission:
                    db_session.delete(permission)
                    db_session.commit()
                    flash('Permission removed successfully', 'success')
                    logger.info("Permission removed")
            else:
                if permission:
                    # Update existing permission
                    permission.can_view = can_view
                    permission.can_create = can_create
                    logger.info(f"Updated permission - can_view: {can_view}, can_create: {can_create}")
                else:
                    # Create new permission
                    permission = CompanyQueuePermission(
                        company_id=company_id,
                        queue_id=queue_id,
                        can_view=can_view,
                        can_create=can_create
                    )
                    db_session.add(permission)
                    logger.info(f"Created new permission - can_view: {can_view}, can_create: {can_create}")
            
                db_session.commit()
                flash('Queue permissions updated successfully', 'success')
                logger.info("Permission saved successfully")
            
            return jsonify({"status": "success", "message": "Permission updated successfully"})
            
        except Exception as e:
            db_session.rollback()
            logger.info(f"ERROR: {str(e)}")
            logger.info(f"Stack trace: {traceback.format_exc()}")
            flash(f'Error updating queue permissions: {str(e)}', 'error')
            return jsonify({"status": "error", "message": str(e)}), 500
        finally:
            db_session.close()
    
    except Exception as e:
        logger.info(f"Unexpected error: {str(e)}")
        logger.info(f"Stack trace: {traceback.format_exc()}")
        return jsonify({"status": "error", "message": f"Unexpected error: {str(e)}"}), 500
        
    return redirect(url_for('admin.manage_queue_permissions'))

@admin_bp.route('/queue-permissions/delete/<int:permission_id>', methods=['GET', 'POST'])
@super_admin_required
def delete_queue_permission(permission_id):
    """Delete queue permission (reset to default)"""
    if not permission_id:
        flash('Invalid permission ID', 'error')
        return redirect(url_for('admin.manage_queue_permissions'))
    
    db_session = db_manager.get_session()
    try:
        permission = db_session.query(CompanyQueuePermission).get(permission_id)
        if permission:
            db_session.delete(permission)
            db_session.commit()
            flash('Permission removed successfully', 'success')
        else:
            flash('Permission not found', 'error')
    except Exception as e:
        db_session.rollback()
        flash(f'Error removing permission: {str(e)}', 'error')
    finally:
        db_session.close()
    
    return redirect(url_for('admin.manage_queue_permissions'))

@admin_bp.route('/queue-notifications')
@admin_required
def manage_queue_notifications():
    """Manage queue notification subscriptions"""
    from models.queue_notification import QueueNotification
    from models.queue import Queue
    from models.user import User
    
    db_session = db_manager.get_session()
    try:
        # Get all users, queues, and existing notifications
        users = db_session.query(User).order_by(User.username).all()
        queues = db_session.query(Queue).order_by(Queue.name).all()
        notifications = db_session.query(QueueNotification).all()
        
        # Create a mapping for easier template access
        notification_map = {}
        for notification in notifications:
            key = f"{notification.user_id}_{notification.queue_id}"
            notification_map[key] = notification
        
        return render_template('admin/queue_notifications.html',
                              users=users,
                              queues=queues,
                              notification_map=notification_map)
    except Exception as e:
        flash(f'Error loading queue notifications: {str(e)}', 'error')
        return redirect(url_for('admin.manage_users'))
    finally:
        db_session.close()


@admin_bp.route('/queue-notifications/update', methods=['POST'])
@admin_required
def update_queue_notification():
    """Update or create a queue notification subscription"""
    from models.queue_notification import QueueNotification
    from datetime import datetime
    
    try:
        user_id = int(request.form.get('user_id'))
        queue_id = int(request.form.get('queue_id'))
        notify_on_create = request.form.get('notify_on_create') == 'on'
        notify_on_move = request.form.get('notify_on_move') == 'on'
        is_active = request.form.get('is_active') == 'on'
        
        db_session = db_manager.get_session()
        try:
            # Check if notification already exists
            notification = db_session.query(QueueNotification).filter_by(
                user_id=user_id, queue_id=queue_id).first()
            
            if notification:
                # Update existing notification
                notification.notify_on_create = notify_on_create
                notification.notify_on_move = notify_on_move
                notification.is_active = is_active
                notification.updated_at = datetime.utcnow()
                action = "updated"
            else:
                # Create new notification
                notification = QueueNotification(
                    user_id=user_id,
                    queue_id=queue_id,
                    notify_on_create=notify_on_create,
                    notify_on_move=notify_on_move,
                    is_active=is_active
                )
                db_session.add(notification)
                action = "created"
            
            db_session.commit()
            flash(f'Queue notification {action} successfully', 'success')
            
        except Exception as e:
            db_session.rollback()
            flash(f'Error updating queue notification: {str(e)}', 'error')
        finally:
            db_session.close()
            
    except Exception as e:
        flash(f'Invalid request data: {str(e)}', 'error')
    
    return redirect(url_for('admin.manage_queue_notifications'))


@admin_bp.route('/queue-notifications/delete/<int:notification_id>', methods=['POST'])
@admin_required
def delete_queue_notification(notification_id):
    """Delete a queue notification subscription"""
    from models.queue_notification import QueueNotification
    
    db_session = db_manager.get_session()
    try:
        notification = db_session.query(QueueNotification).get(notification_id)
        if notification:
            db_session.delete(notification)
            db_session.commit()
            flash('Queue notification deleted successfully', 'success')
        else:
            flash('Queue notification not found', 'error')
    except Exception as e:
        db_session.rollback()
        flash(f'Error deleting queue notification: {str(e)}', 'error')
    finally:
        db_session.close()
    
    return redirect(url_for('admin.manage_queue_notifications'))

@admin_bp.route('/system-config')
@super_admin_required
def system_config():
    """System configuration page"""
    from version import get_full_version_info
    
    db_session = db_manager.get_session()
    try:
        # Get current user
        user = db_manager.get_user(session['user_id'])
        if not user:
            session.clear()
            return redirect(url_for('auth.login'))

        # Try to get Firecrawl API keys, but handle the case when the table doesn't exist
        firecrawl_keys = []
        active_key = None
        try:
            firecrawl_keys = db_session.query(FirecrawlKey).order_by(FirecrawlKey.created_at.desc()).all()
            active_key = db_session.query(FirecrawlKey).filter_by(is_active=True).first()
            if not active_key:
                active_key = db_session.query(FirecrawlKey).filter_by(is_primary=True).first()
        except Exception as e:
            # If there's an error (like table doesn't exist), just ignore it
            # and use the API key from config
            logger.info("Error fetching Firecrawl keys: {str(e)}")
        
        # Add Microsoft 365 OAuth2 configuration to config for template
        import os
        
        # Get the current API key from the environment or config
        current_api_key = os.environ.get('FIRECRAWL_API_KEY') or current_app.config.get('FIRECRAWL_API_KEY', 'Not set')

        # Get version information
        version_info = get_full_version_info()
        config_with_ms = dict(current_app.config)
        config_with_ms.update({
            'MS_CLIENT_ID': os.getenv('MS_CLIENT_ID'),
            'MS_CLIENT_SECRET': os.getenv('MS_CLIENT_SECRET'),
            'MS_TENANT_ID': os.getenv('MS_TENANT_ID'),
            'MS_FROM_EMAIL': os.getenv('MS_FROM_EMAIL'),
        })

        return render_template('admin/system_config.html', 
                             user=user,
                             firecrawl_keys=firecrawl_keys,
                             active_key=active_key,
                             current_api_key=current_api_key,
                             version_info=version_info,
                             config=config_with_ms)
    except Exception as e:
        db_session.rollback()
        flash(f'Error loading system configuration: {str(e)}', 'error')
        return redirect(url_for('main.index'))
    finally:
        db_session.close()

@admin_bp.route('/customer-permissions')
@super_admin_required
def manage_customer_permissions():
    """Manage which companies can see which customers"""
    db_session = db_manager.get_session()
    try:
        # Get current user
        user = db_manager.get_user(session['user_id'])
        if not user:
            session.clear()
            return redirect(url_for('auth.login'))

        # Get all companies
        companies = db_session.query(Company).order_by(Company.name).all()
        
        # Get all existing permissions with company information
        from sqlalchemy.orm import aliased
        CompanyAlias = aliased(Company)
        
        permission_data = db_session.query(CompanyCustomerPermission, Company, CompanyAlias)\
            .join(Company, CompanyCustomerPermission.company_id == Company.id)\
            .join(CompanyAlias, CompanyCustomerPermission.customer_company_id == CompanyAlias.id)\
            .order_by(Company.name).all()
        
        # Structure the data for the template
        permissions = []
        for perm, company, customer_company in permission_data:
            # Add company and customer_company as attributes to the permission object
            perm.company = company
            perm.customer_company = customer_company
            permissions.append(perm)

        return render_template('admin/customer_permissions.html',
                             user=user,
                             companies=companies,
                             permissions=permissions)
    except Exception as e:
        db_session.rollback()
        flash(f'Error loading customer permissions: {str(e)}', 'error')
        return redirect(url_for('admin.system_config'))
    finally:
        db_session.close()

@admin_bp.route('/customer-permissions/update', methods=['POST'])
@super_admin_required
def update_customer_permissions():
    """Update customer viewing permissions (legacy single permission route)"""
    db_session = db_manager.get_session()
    try:
        company_id = request.form.get('company_id')
        customer_company_id = request.form.get('customer_company_id')
        can_view = request.form.get('can_view') == 'true'

        if not company_id or not customer_company_id:
            flash('Company and customer company are required', 'error')
            return redirect(url_for('admin.manage_customer_permissions'))

        # Check if permission already exists
        existing_permission = db_session.query(CompanyCustomerPermission)\
            .filter_by(company_id=company_id, customer_company_id=customer_company_id)\
            .first()

        if existing_permission:
            existing_permission.can_view = can_view
            existing_permission.updated_at = datetime.utcnow()
            action = "updated"
        else:
            # Create new permission
            new_permission = CompanyCustomerPermission(
                company_id=company_id,
                customer_company_id=customer_company_id,
                can_view=can_view
            )
            db_session.add(new_permission)
            action = "created"

        db_session.commit()
        flash(f'Customer permission {action} successfully', 'success')

    except Exception as e:
        db_session.rollback()
        flash(f'Error updating permission: {str(e)}', 'error')
    finally:
        db_session.close()

    return redirect(url_for('admin.manage_customer_permissions'))

@admin_bp.route('/customer-permissions/update-bulk', methods=['POST'])
@super_admin_required
def update_customer_permissions_bulk():
    """Update customer viewing permissions in bulk"""
    db_session = db_manager.get_session()
    try:
        company_id = request.form.get('company_id')
        customer_company_ids = request.form.getlist('customer_company_ids')
        can_view = request.form.get('can_view') == 'true'

        if not company_id:
            flash('Company is required', 'error')
            return redirect(url_for('admin.manage_customer_permissions'))

        if not customer_company_ids:
            flash('At least one customer company must be selected', 'error')
            return redirect(url_for('admin.manage_customer_permissions'))

        # Prevent self-permissions
        customer_company_ids = [cid for cid in customer_company_ids if cid != company_id]

        if not customer_company_ids:
            flash('Cannot grant permissions to view own customers (already have access)', 'error')
            return redirect(url_for('admin.manage_customer_permissions'))

        created_count = 0
        updated_count = 0

        for customer_company_id in customer_company_ids:
            # Check if permission already exists
            existing_permission = db_session.query(CompanyCustomerPermission)\
                .filter_by(company_id=company_id, customer_company_id=customer_company_id)\
                .first()

            if existing_permission:
                if existing_permission.can_view != can_view:
                    existing_permission.can_view = can_view
                    existing_permission.updated_at = datetime.utcnow()
                    updated_count += 1
            else:
                # Create new permission
                new_permission = CompanyCustomerPermission(
                    company_id=company_id,
                    customer_company_id=customer_company_id,
                    can_view=can_view
                )
                db_session.add(new_permission)
                created_count += 1

        db_session.commit()
        
        # Build success message
        messages = []
        if created_count > 0:
            messages.append(f'{created_count} permission(s) created')
        if updated_count > 0:
            messages.append(f'{updated_count} permission(s) updated')
        
        if messages:
            flash(f'Success: {", ".join(messages)}', 'success')
        else:
            flash('No changes were made (permissions already exist with the same settings)', 'info')

    except Exception as e:
        db_session.rollback()
        flash(f'Error updating permissions: {str(e)}', 'error')
    finally:
        db_session.close()

    return redirect(url_for('admin.manage_customer_permissions'))

@admin_bp.route('/customer-permissions/delete/<int:permission_id>', methods=['POST'])
@super_admin_required
def delete_customer_permission(permission_id):
    """Delete a customer permission"""
    db_session = db_manager.get_session()
    try:
        permission = db_session.query(CompanyCustomerPermission).get(permission_id)
        if not permission:
            flash('Permission not found', 'error')
            return redirect(url_for('admin.manage_customer_permissions'))

        db_session.delete(permission)
        db_session.commit()
        flash('Customer permission deleted successfully', 'success')

    except Exception as e:
        db_session.rollback()
        flash(f'Error deleting permission: {str(e)}', 'error')
    finally:
        db_session.close()

    return redirect(url_for('admin.manage_customer_permissions'))

@admin_bp.route('/theme-settings')
@super_admin_required
def theme_settings():
    """Theme configuration page"""
    db_session = db_manager.get_session()
    try:
        # Get current user
        user = db_manager.get_user(session['user_id'])
        if not user:
            session.clear()
            return redirect(url_for('auth.login'))
        
        # Get theme statistics
        theme_stats = db_session.execute(text("""
            SELECT theme_preference, COUNT(*) as count 
            FROM users 
            WHERE theme_preference IS NOT NULL 
            GROUP BY theme_preference
        """)).fetchall()
        
        theme_counts = {
            'light': 0,
            'dark': 0,
            'liquid_glass': 0,
            'ui_2_0': 0
        }
        
        for stat in theme_stats:
            if stat[0] == 'liquid-glass':
                theme_counts['liquid_glass'] = stat[1]
            elif stat[0] == 'ui-2.0':
                theme_counts['ui_2_0'] = stat[1]
            elif stat[0] in theme_counts:
                theme_counts[stat[0]] = stat[1]
        
        total_users = sum(theme_counts.values())
        
        return render_template('admin/theme_settings.html', 
                             user=user,
                             theme_counts=theme_counts,
                             total_users=total_users)
    except Exception as e:
        db_session.rollback()
        flash(f'Error loading theme settings: {str(e)}', 'error')
        return redirect(url_for('admin.system_config'))
    finally:
        db_session.close()


@admin_bp.route('/update-user-theme', methods=['POST'])
@login_required
def update_user_theme():
    """Update current user's theme preference"""
    theme = request.form.get('theme')
    
    if theme not in ['light', 'dark', 'liquid-glass', 'ui-2.0']:
        flash('Invalid theme selection', 'error')
        return redirect(request.referrer or url_for('main.index'))
    
    db_session = db_manager.get_session()
    try:
        # Get current user
        user = db_manager.get_user(session['user_id'])
        if not user:
            session.clear()
            return redirect(url_for('auth.login'))
        
        # Update theme preference
        user.theme_preference = theme
        db_session.commit()
        
        # Update session to reflect theme change immediately
        session['user_theme'] = theme
        
        flash(f'Theme updated to {theme} mode', 'success')
        
        # Return to previous page or theme settings
        return redirect(request.referrer or url_for('admin.theme_settings'))
        
    except Exception as e:
        db_session.rollback()
        flash(f'Error updating theme: {str(e)}', 'error')
        return redirect(request.referrer or url_for('main.index'))
    finally:
        db_session.close()

@admin_bp.route('/changelog')
@login_required
def changelog():
    """Application changelog page"""
    from version import get_full_version_info
    
    version_info = get_full_version_info()
    return render_template('admin/changelog.html', version_info=version_info)

@admin_bp.route('/firecrawl-keys/add', methods=['POST'])
@super_admin_required
def add_firecrawl_key():
    """Add a new Firecrawl API key"""
    db_session = db_manager.get_session()
    try:
        key = request.form.get('key')
        description = request.form.get('description')

        if not key or not description:
            flash('Both API key and description are required', 'error')
            return redirect(url_for('admin.system_config'))

        # Check if key already exists
        existing_key = db_session.query(FirecrawlKey).filter_by(api_key=key).first()
        if existing_key:
            flash('This API key already exists', 'error')
            return redirect(url_for('admin.system_config'))

        # Create new key
        new_key = FirecrawlKey(
            api_key=key,
            name=description,
            is_active=False,
            is_primary=False
        )
        db_session.add(new_key)
        db_session.commit()

        flash('API key added successfully', 'success')
    except Exception as e:
        db_session.rollback()
        flash(f'Error adding API key: {str(e)}', 'error')
    finally:
        db_session.close()
    
    return redirect(url_for('admin.system_config'))

@admin_bp.route('/firecrawl-keys/<int:key_id>/activate', methods=['POST'])
@super_admin_required
def activate_firecrawl_key(key_id):
    """Activate a Firecrawl API key and deactivate others"""
    db_session = db_manager.get_session()
    try:
        # Deactivate all keys
        db_session.query(FirecrawlKey).update({
            FirecrawlKey.is_active: False,
            FirecrawlKey.is_primary: False
        })
        
        # Activate the selected key
        key = db_session.query(FirecrawlKey).get(key_id)
        if key:
            key.is_active = True
            key.is_primary = True
            key.updated_at = datetime.utcnow()
            
            # Update the environment variable and application config
            os.environ['FIRECRAWL_API_KEY'] = key.api_key
            current_app.config['FIRECRAWL_API_KEY'] = key.api_key
            
            db_session.commit()
            flash(f'API key "{key.name}" activated successfully', 'success')
        else:
            flash('API key not found', 'error')
    except Exception as e:
        db_session.rollback()
        flash(f'Error activating API key: {str(e)}', 'error')
    finally:
        db_session.close()
    
    return redirect(url_for('admin.system_config'))

@admin_bp.route('/firecrawl-keys/<int:key_id>/delete', methods=['POST'])
@super_admin_required
def delete_firecrawl_key(key_id):
    """Delete a Firecrawl API key"""
    db_session = db_manager.get_session()
    try:
        key = db_session.query(FirecrawlKey).get(key_id)
        if key:
            if key.is_active or key.is_primary:
                flash('Cannot delete the active API key. Please activate another key first.', 'error')
            else:
                key_description = key.name
                db_session.delete(key)
                db_session.commit()
                flash(f'API key "{key_description}" deleted successfully', 'success')
        else:
            flash('API key not found', 'error')
    except Exception as e:
        db_session.rollback()
        flash(f'Error deleting API key: {str(e)}', 'error')
    finally:
        db_session.close()
    
    return redirect(url_for('admin.system_config'))

@admin_bp.route('/update-firecrawl-key', methods=['POST'])
@super_admin_required
def update_firecrawl_key():
    """Update Firecrawl API key"""
    try:
        new_key = request.form.get('firecrawl_api_key')
        if not new_key:
            flash('API key cannot be empty', 'error')
            return redirect(url_for('admin.system_config'))

        # Update the environment variable
        os.environ['FIRECRAWL_API_KEY'] = new_key
        
        # Update the config
        current_app.config['FIRECRAWL_API_KEY'] = new_key
        
        # Try to update the database if the table exists
        try:
            db_session = db_manager.get_session()
            # Check if we have any keys in the database
            existing_keys = db_session.query(FirecrawlKey).all()
            
            if existing_keys:
                # If we have keys, update the active one or create a new one
                # First deactivate all keys
                db_session.query(FirecrawlKey).update({FirecrawlKey.is_active: False})
                
                # Then either update existing key with same value or create new one
                existing_key = db_session.query(FirecrawlKey).filter_by(api_key=new_key).first()
                if existing_key:
                    existing_key.is_active = True
                    existing_key.is_primary = True
                else:
                    new_key_obj = FirecrawlKey(
                        api_key=new_key,
                        name="Updated via system config",
                        is_active=True,
                        is_primary=True
                    )
                    db_session.add(new_key_obj)
                
                db_session.commit()
        except Exception as e:
            logger.info("Error updating key in database (continuing anyway): {str(e)}")
            # Don't stop execution - we've already updated the config
        
        flash('Firecrawl API key updated successfully', 'success')
    except Exception as e:
        flash(f'Error updating Firecrawl API key: {str(e)}', 'error')
    
    return redirect(url_for('admin.system_config')) 


@admin_bp.route('/ticket-categories')
@super_admin_required
def manage_ticket_categories():
    """Manage all ticket categories (both predefined and custom)"""
    db_session = SessionLocal()
    try:
        # Initialize predefined categories if they don't exist
        CategoryDisplayConfig.initialize_predefined_categories()
        
        # Get all category display configs
        display_configs = db_session.query(CategoryDisplayConfig).order_by(CategoryDisplayConfig.sort_order).all()
        
        # Get custom categories
        custom_categories = db_session.query(TicketCategoryConfig).order_by(TicketCategoryConfig.created_at.desc()).all()
        
        available_sections = TicketCategoryConfig.get_available_sections()
        
        return render_template('admin/ticket_categories/manage_all.html', 
                             display_configs=display_configs,
                             custom_categories=custom_categories,
                             available_sections=available_sections)
    except Exception as e:
        flash(f'Error loading ticket categories: {str(e)}', 'error')
        return redirect(url_for('admin.system_config'))
    finally:
        db_session.close()


@admin_bp.route('/ticket-categories/predefined/<category_key>/edit', methods=['GET', 'POST'])
@super_admin_required
def edit_predefined_category(category_key):
    """Edit display settings for a predefined category"""
    db_session = SessionLocal()
    try:
        # Get or create the display config
        config = db_session.query(CategoryDisplayConfig).filter_by(category_key=category_key).first()
        if not config:
            # Create config for predefined category
            from models.ticket import TicketCategory
            try:
                category_enum = TicketCategory[category_key]
                config = CategoryDisplayConfig(
                    category_key=category_key,
                    display_name=category_enum.value,
                    is_enabled=True,
                    is_predefined=True,
                    sort_order=list(TicketCategory).index(category_enum)
                )
                db_session.add(config)
                db_session.commit()
            except KeyError:
                flash('Invalid category key', 'error')
                return redirect(url_for('admin.manage_ticket_categories'))
        
        if request.method == 'POST':
            display_name = request.form.get('display_name', '').strip()
            is_enabled = request.form.get('is_enabled') == 'on'
            sort_order = request.form.get('sort_order', 0)
            
            if not display_name:
                flash('Display name is required', 'error')
                return redirect(url_for('admin.edit_predefined_category', category_key=category_key))
            
            try:
                sort_order = int(sort_order)
            except (ValueError, TypeError):
                sort_order = 0
            
            # Update config
            config.display_name = display_name
            config.is_enabled = is_enabled
            config.sort_order = sort_order
            config.updated_at = datetime.utcnow()
            
            db_session.commit()
            
            flash(f'Category "{display_name}" updated successfully', 'success')
            return redirect(url_for('admin.manage_ticket_categories'))
        
        # GET request - show form
        return render_template('admin/ticket_categories/edit_predefined.html', config=config)
                             
    except Exception as e:
        db_session.rollback()
        flash(f'Error editing category: {str(e)}', 'error')
        return redirect(url_for('admin.manage_ticket_categories'))
    finally:
        db_session.close()


@admin_bp.route('/ticket-categories/bulk-update', methods=['POST'])
@super_admin_required
def bulk_update_categories():
    """Bulk update category enable/disable status and sort order"""
    db_session = SessionLocal()
    try:
        # Get all predefined categories that have configs
        predefined_configs = db_session.query(CategoryDisplayConfig).filter_by(is_predefined=True).all()
        
        # Process each predefined category
        for config in predefined_configs:
            category_key = config.category_key
            
            # Check if enabled checkbox was submitted (checked = True, not submitted = False)
            enabled_field = f'enabled_{category_key}'
            is_enabled = enabled_field in request.form and request.form[enabled_field] == 'on'
            config.is_enabled = is_enabled
            
            # Update sort order if provided
            sort_order_field = f'sort_order_{category_key}'
            if sort_order_field in request.form:
                try:
                    sort_order = int(request.form[sort_order_field])
                    config.sort_order = sort_order
                except (ValueError, TypeError):
                    pass  # Keep existing sort order if invalid
            
            config.updated_at = datetime.utcnow()
        
        db_session.commit()
        flash('Category settings updated successfully', 'success')
        
    except Exception as e:
        db_session.rollback()
        flash(f'Error updating categories: {str(e)}', 'error')
    finally:
        db_session.close()
    
    return redirect(url_for('admin.manage_ticket_categories'))


@admin_bp.route('/ticket-categories/create', methods=['GET', 'POST'])
@super_admin_required
def create_ticket_category():
    """Create a new custom ticket category"""
    if request.method == 'POST':
        db_session = SessionLocal()
        try:
            name = request.form.get('name', '').strip()
            display_name = request.form.get('display_name', '').strip()
            description = request.form.get('description', '').strip()
            enabled_sections = request.form.getlist('enabled_sections')
            
            if not name or not display_name:
                flash('Name and display name are required', 'error')
                return redirect(url_for('admin.create_ticket_category'))
            
            # Always include required sections
            required_sections = ['case_information', 'comments']
            final_sections = list(set(enabled_sections + required_sections))
            
            # Check if category name already exists
            existing = db_session.query(TicketCategoryConfig).filter_by(name=name).first()
            if existing:
                flash('A category with this name already exists', 'error')
                return redirect(url_for('admin.create_ticket_category'))
            
            # Create new category
            category = TicketCategoryConfig(
                name=name,
                display_name=display_name,
                description=description,
                created_by_id=current_user.id
            )
            category.sections_list = final_sections
            
            db_session.add(category)
            db_session.commit()
            
            flash(f'Ticket category "{display_name}" created successfully', 'success')
            return redirect(url_for('admin.manage_ticket_categories'))
            
        except Exception as e:
            db_session.rollback()
            flash(f'Error creating ticket category: {str(e)}', 'error')
            return redirect(url_for('admin.create_ticket_category'))
        finally:
            db_session.close()
    
    # GET request - show form
    available_sections = TicketCategoryConfig.get_available_sections()
    return render_template('admin/ticket_categories/create.html',
                         available_sections=available_sections)


@admin_bp.route('/ticket-categories/<int:category_id>/edit', methods=['GET', 'POST'])
@super_admin_required
def edit_ticket_category(category_id):
    """Edit an existing ticket category"""
    db_session = SessionLocal()
    try:
        category = db_session.query(TicketCategoryConfig).get(category_id)
        if not category:
            flash('Ticket category not found', 'error')
            return redirect(url_for('admin.manage_ticket_categories'))
        
        if request.method == 'POST':
            display_name = request.form.get('display_name', '').strip()
            description = request.form.get('description', '').strip()
            enabled_sections = request.form.getlist('enabled_sections')
            is_active = request.form.get('is_active') == 'on'
            
            if not display_name:
                flash('Display name is required', 'error')
                return redirect(url_for('admin.edit_ticket_category', category_id=category_id))
            
            # Always include required sections
            required_sections = ['case_information', 'comments']
            final_sections = list(set(enabled_sections + required_sections))
            
            # Update category
            category.display_name = display_name
            category.description = description
            category.is_active = is_active
            category.sections_list = final_sections
            category.updated_at = datetime.utcnow()
            
            db_session.commit()
            
            flash(f'Ticket category "{display_name}" updated successfully', 'success')
            return redirect(url_for('admin.manage_ticket_categories'))
        
        # GET request - show form
        available_sections = TicketCategoryConfig.get_available_sections()
        return render_template('admin/ticket_categories/edit.html',
                             category=category,
                             available_sections=available_sections)
                             
    except Exception as e:
        db_session.rollback()
        flash(f'Error editing ticket category: {str(e)}', 'error')
        return redirect(url_for('admin.manage_ticket_categories'))
    finally:
        db_session.close()


@admin_bp.route('/ticket-categories/<int:category_id>/delete', methods=['POST'])
@super_admin_required
def delete_ticket_category(category_id):
    """Delete a ticket category"""
    db_session = SessionLocal()
    try:
        category = db_session.query(TicketCategoryConfig).get(category_id)
        if not category:
            flash('Ticket category not found', 'error')
            return redirect(url_for('admin.manage_ticket_categories'))
        
        category_name = category.display_name
        db_session.delete(category)
        db_session.commit()
        
        flash(f'Ticket category "{category_name}" deleted successfully', 'success')
        
    except Exception as e:
        db_session.rollback()
        flash(f'Error deleting ticket category: {str(e)}', 'error')
    finally:
        db_session.close()
    
    return redirect(url_for('admin.manage_ticket_categories'))


@admin_bp.route('/ticket-categories/<int:category_id>/preview')
@super_admin_required
def preview_ticket_category(category_id):
    """Preview what a ticket form would look like for this category"""
    db_session = SessionLocal()
    try:
        category = db_session.query(TicketCategoryConfig).get(category_id)
        if not category:
            flash('Ticket category not found', 'error')
            return redirect(url_for('admin.manage_ticket_categories'))
        
        available_sections = TicketCategoryConfig.get_available_sections()
        sections_dict = {section['id']: section for section in available_sections}
        
        return render_template('admin/ticket_categories/preview.html',
                             category=category,
                             sections_dict=sections_dict)
                             
    except Exception as e:
        flash(f'Error previewing ticket category: {str(e)}', 'error')
        return redirect(url_for('admin.manage_ticket_categories'))
    finally:
        db_session.close() 

@admin_bp.route('/database/backup')
@super_admin_required
def create_database_backup():
    """Create a backup of the SQLite database"""
    try:
        # Create backups directory if it doesn't exist
        backup_dir = os.path.join(os.getcwd(), 'backups')
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir)
        
        # Get current database path
        db_path = 'inventory.db'  # Default SQLite database path
        if not os.path.exists(db_path):
            flash('Database file not found', 'error')
            return redirect(url_for('admin.system_config'))
        
        # Create backup filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_filename = f'inventory_backup_{timestamp}.db'
        backup_path = os.path.join(backup_dir, backup_filename)
        
        # Copy the database file
        shutil.copy2(db_path, backup_path)
        
        flash(f'Database backup created successfully: {backup_filename}', 'success')
        return send_file(backup_path, as_attachment=True, download_name=backup_filename)
        
    except Exception as e:
        flash(f'Error creating database backup: {str(e)}', 'error')
        return redirect(url_for('admin.system_config'))

@admin_bp.route('/database/backups')
@super_admin_required
def list_database_backups():
    """List all available database backups"""
    try:
        backup_dir = os.path.join(os.getcwd(), 'backups')
        if not os.path.exists(backup_dir):
            backups = []
        else:
            # Find all backup files
            backup_files = glob.glob(os.path.join(backup_dir, 'inventory_backup_*.db'))
            
            backups = []
            for file_path in backup_files:
                filename = os.path.basename(file_path)
                file_stat = os.stat(file_path)
                file_size = round(file_stat.st_size / (1024 * 1024), 2)  # Size in MB
                created_time = datetime.fromtimestamp(file_stat.st_ctime)
                
                backups.append({
                    'filename': filename,
                    'full_path': file_path,
                    'size_mb': file_size,
                    'created_at': created_time.strftime('%Y-%m-%d %H:%M:%S'),
                    'created_timestamp': created_time
                })
            
            # Sort by creation time (newest first)
            backups.sort(key=lambda x: x['created_timestamp'], reverse=True)
        
        return jsonify({
            'success': True,
            'backups': backups
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@admin_bp.route('/database/restore', methods=['POST'])
@super_admin_required
def restore_database():
    """Restore the database from a backup file"""
    try:
        backup_filename = request.form.get('backup_filename')
        if not backup_filename:
            flash('No backup file specified', 'error')
            return redirect(url_for('admin.system_config'))
        
        backup_dir = os.path.join(os.getcwd(), 'backups')
        backup_path = os.path.join(backup_dir, backup_filename)
        
        if not os.path.exists(backup_path):
            flash('Backup file not found', 'error')
            return redirect(url_for('admin.system_config'))
        
        # Verify it's a valid SQLite database
        try:
            conn = sqlite3.connect(backup_path)
            conn.execute("SELECT name FROM sqlite_master WHERE type='table';")
            conn.close()
        except sqlite3.Error:
            flash('Invalid database backup file', 'error')
            return redirect(url_for('admin.system_config'))
        
        # Create a backup of current database before restore
        current_db_path = 'inventory.db'
        if os.path.exists(current_db_path):
            pre_restore_backup = f'inventory_pre_restore_{datetime.now().strftime("%Y%m%d_%H%M%S")}.db'
            pre_restore_path = os.path.join(backup_dir, pre_restore_backup)
            shutil.copy2(current_db_path, pre_restore_path)
        
        # Restore the database
        shutil.copy2(backup_path, current_db_path)
        
        flash(f'Database restored successfully from {backup_filename}', 'success')
        return redirect(url_for('admin.system_config'))
        
    except Exception as e:
        flash(f'Error restoring database: {str(e)}', 'error')
        return redirect(url_for('admin.system_config'))

@admin_bp.route('/database/backup/download/<filename>')
@super_admin_required
def download_backup(filename):
    """Download a specific backup file"""
    try:
        # Sanitize filename
        safe_filename = secure_filename(filename)
        backup_dir = os.path.join(os.getcwd(), 'backups')
        backup_path = os.path.join(backup_dir, safe_filename)
        
        if not os.path.exists(backup_path):
            flash('Backup file not found', 'error')
            return redirect(url_for('admin.system_config'))
        
        return send_file(backup_path, as_attachment=True, download_name=safe_filename)
        
    except Exception as e:
        flash(f'Error downloading backup: {str(e)}', 'error')
        return redirect(url_for('admin.system_config'))

@admin_bp.route('/database/backup/delete/<filename>', methods=['POST'])
@super_admin_required
def delete_backup(filename):
    """Delete a specific backup file"""
    try:
        # Sanitize filename
        safe_filename = secure_filename(filename)
        backup_dir = os.path.join(os.getcwd(), 'backups')
        backup_path = os.path.join(backup_dir, safe_filename)
        
        if not os.path.exists(backup_path):
            flash('Backup file not found', 'error')
            return redirect(url_for('admin.system_config'))
        
        # Remove the file
        os.remove(backup_path)
        
        flash(f'Backup {safe_filename} deleted successfully', 'success')
        return redirect(url_for('admin.system_config'))
        
    except Exception as e:
        flash(f'Error deleting backup: {str(e)}', 'error')
        return redirect(url_for('admin.system_config'))

@admin_bp.route('/billing-generator')
@admin_required
def billing_generator():
    """Main billing generator page"""
    try:
        from models.ticket import Ticket
        from models.company import Company
        from models.user import Country
        from sqlalchemy import extract, func
        
        db_session = db_manager.get_session()
        
        # Get available months and years from tickets
        date_ranges = db_session.query(
            extract('year', Ticket.created_at).label('year'),
            extract('month', Ticket.created_at).label('month')
        ).distinct().order_by(
            extract('year', Ticket.created_at).desc(),
            extract('month', Ticket.created_at).desc()
        ).all()
        
        # Get all companies
        companies = db_session.query(Company).all()
        
        # Get all countries
        countries = [country.value for country in Country]
        
        return render_template('admin/billing_generator.html',
                             date_ranges=date_ranges,
                             companies=companies,
                             countries=countries)
        
    except Exception as e:
        flash(f'Error loading billing generator: {str(e)}', 'error')
        return redirect(url_for('admin.system_config'))
    finally:
        db_session.close()

@admin_bp.route('/billing-generator/tickets', methods=['POST'])
@admin_required
def get_billing_tickets():
    """Get tickets for billing based on filters"""
    try:
        from models.ticket import Ticket
        from models.user import User
        from models.company import Company
        from sqlalchemy import extract, and_, or_
        
        db_session = db_manager.get_session()
        
        # Get filter parameters
        year = request.json.get('year')
        month = request.json.get('month')
        country = request.json.get('country')
        company_id = request.json.get('company_id')
        category = request.json.get('category')
        
        # Build query
        query = db_session.query(Ticket).join(User, Ticket.requester_id == User.id)
        
        # Date filters
        if year and month:
            query = query.filter(
                and_(
                    extract('year', Ticket.created_at) == year,
                    extract('month', Ticket.created_at) == month
                )
            )
        elif year:
            query = query.filter(extract('year', Ticket.created_at) == year)
        
        # Country filter
        if country:
            query = query.filter(User.assigned_country == country)
        
        # Company filter
        if company_id:
            query = query.filter(User.company_id == company_id)
        
        # Category filter
        if category:
            query = query.filter(Ticket.category_id == category)
        
        # Get tickets
        tickets = query.all()
        
        # Convert to JSON-serializable format
        tickets_data = []
        for ticket in tickets:
            tickets_data.append({
                'id': ticket.id,
                'subject': ticket.subject,
                'status': ticket.status.value if hasattr(ticket.status, 'value') else str(ticket.status),
                'created_at': ticket.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                'requester': ticket.requester.username if ticket.requester else 'Unknown',
                'country': ticket.requester.assigned_country.value if ticket.requester and ticket.requester.assigned_country else 'Unknown',
                'company': ticket.requester.company.name if ticket.requester and ticket.requester.company else 'Unknown',
                'category': ticket.category.name if ticket.category else 'Unknown',
                'priority': ticket.priority.value if hasattr(ticket.priority, 'value') else str(ticket.priority) if ticket.priority else 'Normal'
            })
        
        return jsonify({
            'success': True,
            'tickets': tickets_data,
            'count': len(tickets_data)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })
    finally:
        db_session.close()

@admin_bp.route('/billing-generator/generate', methods=['POST'])
@admin_required
def generate_billing_report():
    """Generate billing report for selected tickets"""
    try:
        from models.ticket import Ticket
        from models.user import User
        from models.company import Company
        import json
        
        db_session = db_manager.get_session()
        
        # Get parameters
        ticket_ids = request.json.get('ticket_ids', [])
        year = request.json.get('year')
        month = request.json.get('month')
        
        if not ticket_ids:
            return jsonify({
                'success': False,
                'error': 'No tickets selected'
            })
        
        # Get tickets
        tickets = db_session.query(Ticket).filter(Ticket.id.in_(ticket_ids)).all()
        
        # Group tickets by country
        billing_data = {}
        
        for ticket in tickets:
            country = ticket.requester.assigned_country.value if ticket.requester and ticket.requester.assigned_country else 'Unknown'
            
            if country not in billing_data:
                billing_data[country] = {
                    'tickets': [],
                    'fees': {
                        'receiving_fee': 0,
                        'warehouse_storage_fee': 0,
                        'order_fee': 0,
                        'return_fee': 0,
                        'intake_fee': 0,
                        'management_fee': 0,
                        'cancelled_returns': 0,
                        'signature_fee': 0
                    },
                    'total_amount': 0,
                    'quantity': 0
                }
            
            billing_data[country]['tickets'].append({
                'id': ticket.id,
                'subject': ticket.subject,
                'status': ticket.status.value if hasattr(ticket.status, 'value') else str(ticket.status),
                'category': ticket.category.name if ticket.category else 'Unknown',
                'created_at': ticket.created_at.strftime('%Y-%m-%d')
            })
            
            billing_data[country]['quantity'] += 1
            
            # Calculate fees based on ticket category and type
            category_name = ticket.category.name if ticket.category else 'Unknown'
            
            if 'CHECKOUT' in category_name.upper():
                billing_data[country]['fees']['order_fee'] += 500  # Example fee
            elif 'RETURN' in category_name.upper():
                billing_data[country]['fees']['return_fee'] += 240
            elif 'INTAKE' in category_name.upper():
                billing_data[country]['fees']['intake_fee'] += 1100
            
            # Add receiving fee for all tickets
            billing_data[country]['fees']['receiving_fee'] += 80
            
            # Calculate warehouse storage fee (monthly)
            billing_data[country]['fees']['warehouse_storage_fee'] += 10
        
        # Calculate totals
        for country_data in billing_data.values():
            country_data['total_amount'] = sum(country_data['fees'].values())
        
        return jsonify({
            'success': True,
            'billing_data': billing_data,
            'year': year,
            'month': month,
            'month_name': datetime(int(year), int(month), 1).strftime('%B') if year and month else None
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })
    finally:
        db_session.close()

@admin_bp.route('/billing-generator/export', methods=['POST'])
@admin_required
def export_billing_report():
    """Export billing report to Excel"""
    try:
        import pandas as pd
        from io import BytesIO
        
        # Get the billing data from the request
        billing_data = request.json.get('billing_data', {})
        year = request.json.get('year')
        month = request.json.get('month')
        
        # Create Excel file in memory
        output = BytesIO()
        
        # Create a workbook and add worksheets
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            
            # Summary sheet
            summary_data = []
            for country, data in billing_data.items():
                row = {
                    'Country': country,
                    'Total Tickets': data['quantity'],
                    'Receiving Fee': data['fees']['receiving_fee'],
                    'Warehouse/Storage Fee': data['fees']['warehouse_storage_fee'],
                    'Order Fee': data['fees']['order_fee'],
                    'Return Fee': data['fees']['return_fee'],
                    'Intake Fee': data['fees']['intake_fee'],
                    'Management Fee': data['fees']['management_fee'],
                    'Total Amount': data['total_amount']
                }
                summary_data.append(row)
            
            summary_df = pd.DataFrame(summary_data)
            summary_df.to_excel(writer, sheet_name='Billing Summary', index=False)
            
            # Detailed sheets for each country
            for country, data in billing_data.items():
                if data['tickets']:
                    tickets_df = pd.DataFrame(data['tickets'])
                    sheet_name = f"{country} Details"[:31]  # Excel sheet name limit
                    tickets_df.to_excel(writer, sheet_name=sheet_name, index=False)
        
        output.seek(0)
        
        # Create filename
        filename = f"billing_report_{year}_{month:02d}.xlsx" if year and month else "billing_report.xlsx"
        
        return send_file(
            BytesIO(output.read()),
            as_attachment=True,
            download_name=filename,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        
    except Exception as e:
        flash(f'Error exporting billing report: {str(e)}', 'error')
        return redirect(url_for('admin.billing_generator'))

@admin_bp.route('/test-email', methods=['GET', 'POST'])
@super_admin_required
def test_email():
    """Test email configuration (Microsoft OAuth2 or SMTP)"""
    if request.method == 'POST':
        try:
            from utils.microsoft_email import get_microsoft_email_client
            from utils.email_sender import _send_email_via_method
            
            test_email = request.form.get('test_email')
            if not test_email:
                flash('Please provide a test email address', 'error')
                return redirect(url_for('admin.test_email'))
            
            # Test Microsoft Graph connection
            microsoft_client = get_microsoft_email_client()
            if microsoft_client:
                success, message = microsoft_client.test_connection()
                if success:
                    flash(f'Microsoft Graph connection successful: {message}', 'success')
                    
                    # Send test email
                    test_subject = 'TrueLog Email Test - Microsoft OAuth2'
                    test_html = f"""
                    <h2>Email Test Successful!</h2>
                    <p>This email was sent using Microsoft Graph API with OAuth2 authentication.</p>
                    <p><strong>Sent to:</strong> {test_email}</p>
                    <p><strong>Time:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                    <p>Your Microsoft 365 email integration is working correctly!</p>
                    """
                    
                    result = _send_email_via_method(
                        to_emails=test_email,
                        subject=test_subject,
                        html_body=test_html,
                        text_body="Email test successful! Microsoft OAuth2 is working."
                    )
                    
                    if result:
                        flash(f'Test email sent successfully to {test_email}', 'success')
                    else:
                        flash('Failed to send test email', 'error')
                        
                else:
                    flash(f'Microsoft Graph connection failed: {message}', 'error')
            else:
                flash('Microsoft email client not configured. Using SMTP fallback.', 'warning')
                
                # Test SMTP fallback
                try:
                    result = _send_email_via_method(
                        to_emails=test_email,
                        subject='TrueLog Email Test - SMTP Fallback',
                        html_body=f"""
                        <h2>SMTP Email Test</h2>
                        <p>This email was sent using SMTP fallback.</p>
                        <p><strong>Sent to:</strong> {test_email}</p>
                        <p><strong>Time:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                        """,
                        text_body="SMTP email test successful!"
                    )
                    
                    if result:
                        flash(f'Test email sent successfully via SMTP to {test_email}', 'success')
                    else:
                        flash('Failed to send test email via SMTP', 'error')
                        
                except Exception as smtp_error:
                    flash(f'SMTP test failed: {str(smtp_error)}', 'error')
            
        except Exception as e:
            flash(f'Error testing email: {str(e)}', 'error')
        
        return redirect(url_for('admin.test_email'))
    
    # GET request - show test form
    import os
    config_with_ms = dict(current_app.config)
    config_with_ms.update({
        'MS_CLIENT_ID': os.getenv('MS_CLIENT_ID'),
        'MS_CLIENT_SECRET': os.getenv('MS_CLIENT_SECRET'),
        'MS_TENANT_ID': os.getenv('MS_TENANT_ID'),
        'MS_FROM_EMAIL': os.getenv('MS_FROM_EMAIL'),
    })
    return render_template('admin/test_email.html', config=config_with_ms)


@admin_bp.route('/csv-import')
@admin_required
def csv_import():
    """CSV Import for Asset Checkout Tickets"""
    return render_template('admin/csv_import.html')


@admin_bp.route('/csv-import/upload', methods=['POST'])
@admin_required 
def csv_import_upload():
    """Upload and parse CSV file for ticket import"""
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'No file provided'})
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'})
        
        if not file.filename.lower().endswith('.csv'):
            return jsonify({'success': False, 'error': 'File must be a CSV'})
        
        # Generate unique file ID
        import uuid
        file_id = str(uuid.uuid4())
        
        # Read and parse CSV
        csv_content = file.read().decode('utf-8')
        csv_reader = csv.DictReader(io.StringIO(csv_content))
        
        # Convert to list and validate
        raw_data = []
        for row in csv_reader:
            # Clean and validate the row
            cleaned_row = clean_csv_row(row)
            if cleaned_row:  # Only add valid rows
                raw_data.append(cleaned_row)
        
        if not raw_data:
            return jsonify({'success': False, 'error': 'No valid data found in CSV'})
        
        # Group orders by order_id
        grouped_data, individual_data = group_orders_by_id(raw_data)
        
        # Combine grouped and individual data for display
        display_data = grouped_data + individual_data
        
        # Store in temporary file with file_id
        temp_file = os.path.join(tempfile.gettempdir(), f'csv_import_{file_id}.json')
        with open(temp_file, 'w') as f:
            json.dump(display_data, f)
        
        # Clean up old files (older than 1 hour)
        cleanup_old_csv_files()
        
        return jsonify({
            'success': True,
            'file_id': file_id,
            'total_rows': len(display_data),
            'grouped_orders': len(grouped_data),
            'individual_rows': len(individual_data),
            'data': display_data,  # Include the actual data for display
            'message': f'Successfully processed {len(raw_data)} rows into {len(display_data)} tickets ({len(grouped_data)} grouped orders, {len(individual_data)} individual items)'
        })
        
    except Exception as e:
        logger.info("Error in CSV upload: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': f'Failed to process CSV: {str(e)}'})

def cleanup_old_csv_files():
    """Clean up CSV files older than 1 hour"""
    try:
        import time
        temp_dir = tempfile.gettempdir()
        current_time = time.time()
        
        for filename in os.listdir(temp_dir):
            if filename.startswith('csv_import_') and filename.endswith('.json'):
                file_path = os.path.join(temp_dir, filename)
                file_time = os.path.getmtime(file_path)
                # Remove files older than 1 hour (3600 seconds)
                if current_time - file_time > 3600:
                    try:
                        os.remove(file_path)
                        logger.info("Cleaned up old CSV file: {filename}")
                    except Exception as e:
                        logger.info("Failed to clean up file {filename}: {e}")
    except Exception as e:
        logger.info("Error in cleanup: {e}")

def clean_csv_row(row):
    """Clean and validate a CSV row"""
    try:
        # Required fields for validation
        required_fields = ['product_title', 'org_name']
        
        # Clean whitespace and handle quoted empty values
        cleaned = {}
        for key, value in row.items():
            if value is None:
                cleaned[key] = ''
            else:
                # Strip whitespace and handle quoted spaces like " "
                cleaned_value = str(value).strip()
                if cleaned_value in ['" "', "'  '", '""', "''"]:
                    cleaned_value = ''
                cleaned[key] = cleaned_value
        
        # Check if required fields are present and non-empty
        for field in required_fields:
            if not cleaned.get(field):
                logger.info("Skipping row due to missing {field}: {cleaned}")
                return None
        
        # Set default values for missing fields
        defaults = {
            'person_name': cleaned.get('person_name') or 'Unknown Customer',
            'primary_email': cleaned.get('primary_email') or '',
            'phone_number': cleaned.get('phone_number') or '',
            'category_code': cleaned.get('category_code') or 'GENERAL',
            'brand': cleaned.get('brand') or '',
            'serial_number': cleaned.get('serial_number') or '',
            'preferred_condition': cleaned.get('preferred_condition') or 'Good',
            'priority': cleaned.get('priority') or '1',
            'order_id': cleaned.get('order_id') or '',
            'order_item_id': cleaned.get('order_item_id') or '',
            'organization_id': cleaned.get('organization_id') or '',
            'status': cleaned.get('status') or 'Pending',
            'start_date': cleaned.get('start_date') or '',
            'shipped_date': cleaned.get('shipped_date') or '',
            'delivery_date': cleaned.get('delivery_date') or '',
            'office_name': cleaned.get('office_name') or '',
            'address_line1': cleaned.get('address_line1') or '',
            'address_line2': cleaned.get('address_line2') or '',
            'city': cleaned.get('city') or '',
            'state': cleaned.get('state') or '',
            'postal_code': cleaned.get('postal_code') or '',
            'country_code': cleaned.get('country_code') or '',
            'carrier': cleaned.get('carrier') or '',
            'tracking_link': cleaned.get('tracking_link') or ''
        }
        
        # Update cleaned row with defaults
        for key, default_value in defaults.items():
            if not cleaned.get(key):
                cleaned[key] = default_value
        
        return cleaned
        
    except Exception as e:
        logger.info("Error cleaning row: {e}")
        return None

def group_orders_by_id(data):
    """Group CSV rows by order_id"""
    try:
        order_groups = {}
        individual_items = []
        
        # Group by order_id
        for row in data:
            order_id = row.get('order_id', '').strip()
            if order_id:
                if order_id not in order_groups:
                    order_groups[order_id] = []
                order_groups[order_id].append(row)
            else:
                # No order_id, treat as individual
                individual_items.append(row)
        
        grouped_orders = []
        
        # Process groups
        for order_id, items in order_groups.items():
            if len(items) > 1:
                # Multiple items - create grouped order
                primary_item = items[0]  # Use first item as primary
                
                # Create item summary
                product_titles = [item['product_title'] for item in items]
                if len(product_titles) <= 3:
                    title_summary = ', '.join(product_titles)
                else:
                    title_summary = f"{', '.join(product_titles[:2])} and {len(product_titles) - 2} more..."
                
                grouped_order = {
                    'is_grouped': True,
                    'order_id': order_id,
                    'item_count': len(items),
                    'title_summary': title_summary,
                    'all_items': items,
                    # Include primary item data for compatibility
                    **primary_item
                }
                grouped_orders.append(grouped_order)
            else:
                # Single item, add to individual
                item = items[0]
                item['is_grouped'] = False
                individual_items.append(item)
        
        # Mark individual items
        for item in individual_items:
            if 'is_grouped' not in item:
                item['is_grouped'] = False
        
        return grouped_orders, individual_items
        
    except Exception as e:
        logger.info("Error grouping orders: {e}")
        return [], data

@admin_bp.route('/csv-import/preview-ticket', methods=['POST'])
@admin_required
def csv_import_preview_ticket():
    """Preview a single ticket from CSV data with enhanced features"""
    try:
        data = request.json
        row_index = data.get('row_index')
        is_grouped = data.get('is_grouped', False)
        file_id = data.get('file_id')
        
        if file_id is None or row_index is None:
            return jsonify({'success': False, 'error': 'Missing file_id or row_index'})
            
        # Load data from file
        temp_file = os.path.join(tempfile.gettempdir(), f'csv_import_{file_id}.json')
        if not os.path.exists(temp_file):
            return jsonify({'success': False, 'error': 'CSV data not found. Please re-upload your file.'})
            
        with open(temp_file, 'r') as f:
            csv_data = json.load(f)
        
        if row_index >= len(csv_data):
            return jsonify({'success': False, 'error': 'Invalid row index'})
            
        row = csv_data[row_index]
        
        if is_grouped:
            all_items = row.get('all_items', [row])
            if not all_items or len(all_items) == 0:
                return jsonify({'success': False, 'error': 'No items found in grouped order'})
            primary_item = all_items[0]
            if not primary_item:
                return jsonify({'success': False, 'error': 'Primary item is null in grouped order'})
        else:
            all_items = [row]
            primary_item = row
            
        # Validate that primary_item has required fields
        if not primary_item or not primary_item.get('product_title'):
            return jsonify({'success': False, 'error': f'Invalid item data: {primary_item}'})
        
        # Enhanced category mapping with queue routing
        def determine_category_and_queue(product_title, category_code):
            """Determine category and queue based on product type"""
            product_lower = product_title.lower()
            category_lower = category_code.lower() if category_code else ""
            
            # Accessory detection patterns
            accessory_keywords = [
                'adapter', 'cable', 'charger', 'mouse', 'keyboard', 'headset', 
                'webcam', 'dock', 'hub', 'dongle', 'stand', 'pad', 'cover',
                'case', 'sleeve', 'bag', 'power supply', 'cord', 'usb'
            ]
            
            # Computer/laptop detection patterns  
            computer_keywords = [
                'macbook', 'laptop', 'computer', 'imac', 'pc', 'desktop', 
                'workstation', 'tower', 'all-in-one', 'surface', 'thinkpad'
            ]
            
            # Check if it's an accessory
            is_accessory = (
                any(keyword in product_lower for keyword in accessory_keywords) or
                any(keyword in category_lower for keyword in ['accessory', 'peripheral', 'cable', 'adapter'])
            )
            
            # Check if it's a computer/laptop
            is_computer = (
                any(keyword in product_lower for keyword in computer_keywords) or
                any(keyword in category_lower for keyword in ['computer', 'laptop', 'desktop'])
            )
            
            if is_accessory:
                return 'ASSET_CHECKOUT_CLAW', 'Checkout Accessories'
            elif is_computer:
                return 'ASSET_CHECKOUT_CLAW', 'Tech Asset'
            else:
                return 'ASSET_CHECKOUT_CLAW', 'General'
        
        # Check inventory for each item
        db_session = db_manager.get_session()
        try:
            inventory_info = []
            for item in all_items:
                product_title = item.get('product_title', '')
                serial_number = item.get('serial_number', '')
                brand = item.get('brand', '')
                category = item.get('category_code', '')
                
                # Initialize matches list
                matches = []
                
                # Search for matching assets in inventory
                asset_query = db_session.query(Asset)
                
                # 1. Search by serial number (highest priority for assets)
                if serial_number:
                    serial_matches = asset_query.filter(
                        Asset.serial_num.ilike(f'%{serial_number}%')
                    ).all()
                    
                    for asset in serial_matches:
                        # Check availability status
                        is_available = asset.status and asset.status.value in ['In Stock', 'Ready to Deploy']
                        status_display = asset.status.value if asset.status else 'Unknown'
                        availability_text = f"Available ({status_display})" if is_available else f"Not Available ({status_display})"
                        
                        matches.append({
                            'match_type': 'Serial Number (Asset)',
                            'item_type': 'asset',
                            'id': asset.id,
                            'name': asset.name or asset.model,
                            'identifier': f"Tag: {asset.asset_tag or 'N/A'} | Serial: {asset.serial_num or 'N/A'}",
                            'availability': availability_text,
                            'is_available': is_available,
                            'confidence': 'High'
                        })
                
                # 2. Search by product name in assets (medium priority) - IMPROVED ALGORITHM
                if product_title and len(matches) < 3:
                    # First try exact phrase matches (highest relevance)
                    exact_phrase_matches = asset_query.filter(
                        or_(
                            Asset.name.ilike(f'%{product_title}%'),
                            Asset.model.ilike(f'%{product_title}%'),
                            Asset.hardware_type.ilike(f'%{product_title}%')
                        )
                    ).limit(3).all()
                    
                    for asset in exact_phrase_matches:
                        if not any(m.get('id') == asset.id and m.get('item_type') == 'asset' for m in matches):
                            is_available = asset.status and asset.status.value in ['In Stock', 'Ready to Deploy']
                            status_display = asset.status.value if asset.status else 'Unknown'
                            availability_text = f"Available ({status_display})" if is_available else f"Not Available ({status_display})"
                            
                            matches.append({
                                'match_type': 'Exact Phrase (Asset)',
                                'item_type': 'asset',
                                'id': asset.id,
                                'name': asset.name or asset.model,
                                'identifier': f"Tag: {asset.asset_tag or 'N/A'} | Serial: {asset.serial_num or 'N/A'}",
                                'availability': availability_text,
                                'is_available': is_available,
                                'confidence': 'High'
                            })
                    
                    # If still need more matches, try smart keyword matching
                    if len(matches) < 3:
                        # Extract meaningful keywords (filter out common words)
                        common_words = {'with', 'and', 'or', 'the', 'a', 'an', 'in', 'on', 'at', 'to', 'for', 'of', 'by', 'from'}
                        search_terms = [term.lower() for term in product_title.split() 
                                      if len(term) > 3 and term.lower() not in common_words]
                        
                        # Only proceed if we have meaningful terms
                        if search_terms:
                            # Create a query that requires multiple term matches for better relevance
                            conditions = []
                            for term in search_terms[:3]:  # Limit to first 3 meaningful terms
                                conditions.append(
                                    or_(
                                        Asset.name.ilike(f'%{term}%'),
                                        Asset.model.ilike(f'%{term}%'),
                                        Asset.hardware_type.ilike(f'%{term}%'),
                                        Asset.manufacturer.ilike(f'%{term}%')
                                    )
                                )
                            
                            # Try to find assets that match multiple terms
                            if len(conditions) >= 2:
                                multi_term_matches = asset_query.filter(
                                    and_(*conditions[:2])  # Require at least 2 terms to match
                                ).limit(2).all()
                                
                                for asset in multi_term_matches:
                                    if not any(m.get('id') == asset.id and m.get('item_type') == 'asset' for m in matches):
                                        is_available = asset.status and asset.status.value in ['In Stock', 'Ready to Deploy']
                                        status_display = asset.status.value if asset.status else 'Unknown'
                                        availability_text = f"Available ({status_display})" if is_available else f"Not Available ({status_display})"
                                        
                                        matches.append({
                                            'match_type': 'Multi-term Match (Asset)',
                                            'item_type': 'asset',
                                            'id': asset.id,
                                            'name': asset.name or asset.model,
                                            'identifier': f"Tag: {asset.asset_tag or 'N/A'} | Serial: {asset.serial_num or 'N/A'}",
                                            'availability': availability_text,
                                            'is_available': is_available,
                                            'confidence': 'Medium'
                                        })
                
                # 3. Search by brand in assets (lower priority)
                if brand and len(matches) < 3:
                    brand_matches = asset_query.filter(
                        Asset.manufacturer.ilike(f'%{brand}%')
                    ).limit(2).all()
                    
                    for asset in brand_matches:
                        if not any(m.get('id') == asset.id and m.get('item_type') == 'asset' for m in matches):
                            is_available = asset.status and asset.status.value in ['In Stock', 'Ready to Deploy']
                            status_display = asset.status.value if asset.status else 'Unknown'
                            availability_text = f"Available ({status_display})" if is_available else f"Not Available ({status_display})"
                            
                            matches.append({
                                'match_type': 'Brand (Asset)',
                                'item_type': 'asset',
                                'id': asset.id,
                                'name': asset.name or asset.model,
                                'identifier': f"Tag: {asset.asset_tag or 'N/A'} | Serial: {asset.serial_num or 'N/A'}",
                                'availability': availability_text,
                                'is_available': is_available,
                                'confidence': 'Low'
                            })
                
                # 4. Search for accessories - IMPROVED ALGORITHM
                accessory_query = db_session.query(Accessory)
                
                # Debug logging for accessory matching
                logger.info(f"CSV_ACCESSORY_DEBUG: Searching for accessories with product_title='{product_title}'")
                
                # Search by exact product name in accessories (highest priority)
                if product_title:
                    # First try exact phrase matches
                    exact_accessory_matches = accessory_query.filter(
                        or_(
                            Accessory.name.ilike(f'%{product_title}%'),
                            Accessory.model_no.ilike(f'%{product_title}%')
                        )
                    ).limit(3).all()
                    
                    logger.info(f"CSV_ACCESSORY_DEBUG: Found {len(exact_accessory_matches)} exact phrase matches")
                    
                    for accessory in exact_accessory_matches:
                        is_available = accessory.available_quantity > 0
                        availability_text = f"Available (Qty: {accessory.available_quantity})" if is_available else "Out of Stock"
                        
                        matches.append({
                            'match_type': 'Exact Phrase (Accessory)',
                            'item_type': 'accessory',
                            'id': accessory.id,
                            'name': accessory.name,
                            'identifier': f"Category: {accessory.category or 'N/A'} | Model: {accessory.model_no or 'N/A'}",
                            'availability': availability_text,
                            'is_available': is_available,
                            'confidence': 'High'
                        })
                
                # 5. Search accessories by intelligent keyword matching
                if len(matches) < 5:
                    # Extract meaningful keywords (filter out common words)
                    common_words = {'with', 'and', 'or', 'the', 'a', 'an', 'in', 'on', 'at', 'to', 'for', 'of', 'by', 'from'}
                    search_terms = [term.lower() for term in product_title.split() 
                                  if len(term) > 3 and term.lower() not in common_words] if product_title else []
                    
                    logger.info(f"CSV_ACCESSORY_DEBUG: Intelligent search terms: {search_terms}")
                    
                    if search_terms:
                        # Try multi-term matching for better relevance
                        conditions = []
                        for term in search_terms[:3]:  # Limit to first 3 meaningful terms
                            conditions.append(
                                or_(
                                    Accessory.name.ilike(f'%{term}%'),
                                    Accessory.category.ilike(f'%{term}%'),
                                    Accessory.manufacturer.ilike(f'%{term}%'),
                                    Accessory.model_no.ilike(f'%{term}%')
                                )
                            )
                        
                        # Try to find accessories that match multiple terms
                        if len(conditions) >= 2:
                            logger.info(f"CSV_ACCESSORY_DEBUG: Searching for multi-term matches")
                            multi_term_accessory_matches = accessory_query.filter(
                                and_(*conditions[:2])  # Require at least 2 terms to match
                            ).limit(2).all()
                            
                            for accessory in multi_term_accessory_matches:
                                if not any(m.get('id') == accessory.id and m.get('item_type') == 'accessory' for m in matches):
                                    is_available = accessory.available_quantity > 0
                                    availability_text = f"Available (Qty: {accessory.available_quantity})" if is_available else "Out of Stock"
                                    
                                    matches.append({
                                        'match_type': 'Multi-term Match (Accessory)',
                                        'item_type': 'accessory',
                                        'id': accessory.id,
                                        'name': accessory.name,
                                        'identifier': f"Category: {accessory.category or 'N/A'} | Model: {accessory.model_no or 'N/A'}",
                                        'availability': availability_text,
                                        'is_available': is_available,
                                        'confidence': 'Medium'
                                    })
                        
                        # If still need matches, try single meaningful term matches (lower priority)
                        elif len(matches) < 5 and search_terms:
                            # Use only the most specific term (usually the product type)
                            primary_term = search_terms[0]  # Usually the most important term
                            logger.info(f"CSV_ACCESSORY_DEBUG: Searching single term matches for: '{primary_term}'")
                            
                            single_term_matches = accessory_query.filter(
                                or_(
                                    Accessory.name.ilike(f'%{primary_term}%'),
                                    Accessory.category.ilike(f'%{primary_term}%'),
                                    Accessory.manufacturer.ilike(f'%{primary_term}%'),
                                    Accessory.model_no.ilike(f'%{primary_term}%')
                                )
                            ).limit(2).all()
                            
                            for accessory in single_term_matches:
                                if not any(m.get('id') == accessory.id and m.get('item_type') == 'accessory' for m in matches):
                                    is_available = accessory.available_quantity > 0
                                    availability_text = f"Available (Qty: {accessory.available_quantity})" if is_available else "Out of Stock"
                                    
                                    matches.append({
                                        'match_type': 'Single Term Match (Accessory)',
                                        'item_type': 'accessory',
                                        'id': accessory.id,
                                        'name': accessory.name,
                                        'identifier': f"Category: {accessory.category or 'N/A'} | Model: {accessory.model_no or 'N/A'}",
                                        'availability': availability_text,
                                        'is_available': is_available,
                                        'confidence': 'Low'
                                    })
                
                # 6. Search accessories by brand
                if brand and len(matches) < 5:
                    brand_accessory_matches = accessory_query.filter(
                        Accessory.manufacturer.ilike(f'%{brand}%')
                    ).limit(2).all()
                    
                    for accessory in brand_accessory_matches:
                        if not any(m.get('id') == accessory.id and m.get('item_type') == 'accessory' for m in matches):
                            is_available = accessory.available_quantity > 0
                            availability_text = f"Available (Qty: {accessory.available_quantity})" if is_available else "Out of Stock"
                            
                            matches.append({
                                'match_type': 'Brand (Accessory)',
                                'item_type': 'accessory',
                                'id': accessory.id,
                                'name': accessory.name,
                                'identifier': f"Category: {accessory.category or 'N/A'} | Model: {accessory.model_no or 'N/A'}",
                                'availability': availability_text,
                                'is_available': is_available,
                                'confidence': 'Low'
                            })
                
                # Determine overall stock status
                if matches:
                    # Check if any match is available
                    available_matches = [m for m in matches if m.get('is_available', False)]
                    if available_matches:
                        stock_status = "In Stock"
                    else:
                        stock_status = "Found but Not Available"
                else:
                    stock_status = "Not Found"
                
                inventory_info.append({
                    'product_title': product_title,
                    'serial_number': serial_number,
                    'brand': brand,
                    'category': category,
                    'matches': matches[:5],  # Limit to top 5 matches
                    'stock_status': stock_status
                })
        finally:
            db_session.close()
        
        # Determine category and suggested queue
        primary_category, suggested_queue = determine_category_and_queue(
            primary_item.get('product_title', ''),
            primary_item.get('category_code', '')
        )
        
        # Get available queues for selection
        available_queues = []
        queue_session = db_manager.get_session()
        try:
            queues = queue_session.query(Queue).all()
            for queue in queues:
                available_queues.append({
                    'id': queue.id,
                    'name': queue.name,
                    'description': queue.description,
                    'suggested': queue.name == suggested_queue
                })
        finally:
            queue_session.close()
        
        # Get all users for case owner selection (admin and super admin only)
        available_users = []
        user_session = db_manager.get_session()
        try:
            from models.user import User
            from models.enums import UserType
            from flask_login import current_user
            
            # Check if user is admin or super admin
            is_admin = current_user.is_admin or current_user.is_super_admin
            
            if is_admin:
                all_users = user_session.query(User).all()
                for user in all_users:
                    available_users.append({
                        'id': user.id,
                        'name': user.username,
                        'email': user.email,
                        'is_current': user.id == current_user.id
                    })
        except Exception as e:
            logger.info("Error getting users for case owner selection: {str(e)}")
            import traceback
            traceback.print_exc()
        finally:
            user_session.close()
        
        # Create enhanced ticket preview
        if is_grouped:
            subject = f"Asset Checkout - Order {row['order_id']} ({row['item_count']} items)"
            description = f"Multi-item asset checkout request for {primary_item['person_name']} from {primary_item['org_name']} - {row['item_count']} items total"
            
            # Create asset list for grouped items
            asset_list = []
            for item in all_items:
                asset_list.append({
                    'product_title': item['product_title'],
                    'brand': item['brand'],
                    'serial_number': item['serial_number'],
                    'category': item['category_code'],
                    'condition': item['preferred_condition'] or 'Good'
                })
        else:
            subject = f"Asset Checkout - {row['product_title']}"
            description = f"Asset checkout request for {row['person_name']} from {row['org_name']}"
            asset_list = [{
                'product_title': row['product_title'],
                'brand': row['brand'],
                'serial_number': row['serial_number'],
                'category': row['category_code'],
                'condition': row['preferred_condition'] or 'Good'
            }]
        
        # Format shipping address
        shipping_address = f"""{primary_item['office_name']}
{primary_item['address_line1']}
{primary_item['address_line2']}
{primary_item['city']}, {primary_item['state']} {primary_item['postal_code']}
{primary_item['country_code']}""".strip()
        
        # Format order details for notes
        order_notes = f"""Order Details:
- Order ID: {primary_item['order_id']}
- Organization ID: {primary_item['organization_id']}
- Status: {primary_item['status']}
- Start Date: {primary_item['start_date'] or 'Not specified'}
- Shipped Date: {primary_item['shipped_date'] or 'Not specified'}
- Delivery Date: {primary_item['delivery_date'] or 'Not specified'}
- Carrier: {primary_item['carrier'] or 'Not specified'}
- Tracking: {primary_item['tracking_link'] or 'Not provided'}"""
        
        ticket_preview = {
            'subject': subject,
            'description': description,
            'category': primary_category,
            'priority': 'MEDIUM' if primary_item['priority'] == '2' else 'LOW',
            'status': 'OPEN',
            'is_grouped': is_grouped,
            'item_count': len(all_items),
            'customer_info': {
                'name': primary_item['person_name'],
                'email': primary_item['primary_email'],
                'phone': primary_item['phone_number'],
                'company': primary_item['org_name']
            },
            'asset_info': asset_list[0],  # Always provide first asset for compatibility
            'all_assets': asset_list,  # All assets for grouped display
            'shipping_address': shipping_address,
            'notes': order_notes,
            'available_queues': available_queues,
            'suggested_queue_id': next((q['id'] for q in available_queues if q['suggested']), None),
            'available_users': available_users,
            'inventory_info': inventory_info,
            'shipping_info': {
                'office_name': primary_item['office_name'],
                'address_line1': primary_item['address_line1'],
                'address_line2': primary_item['address_line2'],
                'city': primary_item['city'],
                'state': primary_item['state'],
                'postal_code': primary_item['postal_code'],
                'country_code': primary_item['country_code'],
                'carrier': primary_item['carrier'],
                'tracking_link': primary_item['tracking_link'],
                'shipped_date': primary_item['shipped_date'],
                'delivery_date': primary_item['delivery_date']
            },
            'order_info': {
                'order_id': primary_item['order_id'],
                'order_item_id': primary_item.get('order_item_id'),
                'organization_id': primary_item['organization_id'],
                'status': primary_item['status'],
                'start_date': primary_item['start_date'],
                'shipped_date': primary_item['shipped_date'],
                'delivery_date': primary_item['delivery_date']
            }
        }
        
        return jsonify({'success': True, 'preview': ticket_preview})
        
    except Exception as e:
        logger.info("Error in preview: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': f'Failed to generate preview: {str(e)}'})

@admin_bp.route('/csv-import/import-ticket', methods=['POST'])
@admin_required
def csv_import_import_ticket():
    """Import a ticket from CSV data with enhanced data flow"""
    try:
        data = request.json
        row_index = data.get('row_index')
        is_grouped = data.get('is_grouped', False)
        file_id = data.get('file_id')
        selected_queue_id = data.get('queue_id')  # Get selected queue
        selected_case_owner_id = data.get('case_owner_id')  # Get selected case owner
        selected_accessories = data.get('selected_accessories', [])  # Get selected accessories
        selected_assets = data.get('selected_assets', [])  # Get selected assets
        
        # Add logging to see what we're receiving
        import logging
        logging.basicConfig(level=logging.INFO)
        logger = logging.getLogger(__name__)
        logger.info(f"[CSV IMPORT] Received {len(selected_accessories)} accessories and {len(selected_assets)} assets")
        logger.info("[CSV IMPORT] Received {len(selected_accessories)} accessories and {len(selected_assets)} assets")
        logger.info("[CSV IMPORT] Selected assets data: {selected_assets}")
        
        if file_id is None or row_index is None:
            return jsonify({'success': False, 'error': 'Missing file_id or row_index'})
        
        # Load data from file
        temp_file = os.path.join(tempfile.gettempdir(), f'csv_import_{file_id}.json')
        if not os.path.exists(temp_file):
            return jsonify({'success': False, 'error': 'CSV data not found. Please re-upload your file.'})
            
        with open(temp_file, 'r') as f:
            csv_data = json.load(f)
        
        if row_index >= len(csv_data):
            return jsonify({'success': False, 'error': 'Invalid row index'})
            
        row = csv_data[row_index]
        
        # Check if the ticket has PROCESSING status and block import
        if row.get('status') == 'PROCESSING':
            return jsonify({
                'success': False, 
                'error': 'Cannot import tickets with PROCESSING status. Please wait for the order to progress to another status before importing.'
            })
        
        if is_grouped:
            all_items = row.get('all_items', [row])
            if not all_items or len(all_items) == 0:
                return jsonify({'success': False, 'error': 'No items found in grouped order'})
            
            # Check if any item in grouped order has PROCESSING status
            for item in all_items:
                if item.get('status') == 'PROCESSING':
                    return jsonify({
                        'success': False, 
                        'error': 'Cannot import tickets with PROCESSING status. One or more items in this order are still processing.'
                    })
        else:
            all_items = [row]
        
        primary_item = all_items[0]
        
        db_session = db_manager.get_session()
        try:
            # Configure SQLite for better concurrency
            from sqlalchemy import text
            db_session.execute(text("PRAGMA journal_mode=WAL;"))
            db_session.execute(text("PRAGMA synchronous=NORMAL;"))
            db_session.execute(text("PRAGMA busy_timeout=30000;"))  # 30 second timeout
            
            # 1. CREATE CUSTOMER FIRST (as requested)
            from models.customer_user import CustomerUser
            from models.company import Company
            
            # Check if customer already exists
            customer = db_session.query(CustomerUser).filter(
                CustomerUser.email == primary_item['primary_email']
            ).first()
            
            customer_created = False
            if not customer:
                # Get or create company
                company = db_session.query(Company).filter(
                    Company.name == primary_item['org_name']
                ).first()
                
                if not company:
                    company = Company(
                        name=primary_item['org_name'],
                        description=f"Auto-created from CSV import",
                        contact_email=primary_item['primary_email']
                    )
                    db_session.add(company)
                    db_session.flush()
                
                # Create customer with address from shipping information
                customer_address = f"{primary_item.get('address_line1', '')}\n{primary_item.get('address_line2', '')}\n{primary_item.get('city', '')}, {primary_item.get('state', '')} {primary_item.get('postal_code', '')}\n{primary_item.get('country_code', '')}".strip()
                if not customer_address or customer_address.replace('\n', '').replace(',', '').strip() == '':
                    customer_address = "Address not provided"
                
                # Map city to country as requested by user, with fallback to country_code
                city_to_country_mapping = {
                    'Singapore': Country.SINGAPORE,
                    'Kuala Lumpur': Country.MALAYSIA,
                    'Bangkok': Country.THAILAND,
                    'Manila': Country.PHILIPPINES,
                    'Jakarta': Country.INDONESIA,
                    'Ho Chi Minh City': Country.VIETNAM,
                    'Hanoi': Country.VIETNAM,
                    'Seoul': Country.SOUTH_KOREA,
                    'Tokyo': Country.JAPAN,
                    'Osaka': Country.JAPAN,
                    'Sydney': Country.AUSTRALIA,
                    'Melbourne': Country.AUSTRALIA,
                    'Mumbai': Country.INDIA,
                    'Delhi': Country.INDIA,
                    'Bangalore': Country.INDIA,
                    'Tel Aviv': Country.ISRAEL,
                    'Jerusalem': Country.ISRAEL,
                    'Toronto': Country.CANADA,
                    'Vancouver': Country.CANADA,
                    'New York': Country.USA,
                    'Los Angeles': Country.USA,
                    'San Francisco': Country.USA,
                    'Hong Kong': Country.HONG_KONG,
                    'Taipei': Country.TAIWAN,
                    'Beijing': Country.CHINA,
                    'Shanghai': Country.CHINA
                }
                
                # First try to map from city, then fallback to country_code
                city = primary_item.get('city', '')
                country_code = primary_item.get('country_code', '')
                
                if city and city in city_to_country_mapping:
                    customer_country = city_to_country_mapping[city]
                else:
                    # Fallback to country code mapping
                    country_code_mapping = {
                        'SG': Country.SINGAPORE,
                        'US': Country.USA,
                        'JP': Country.JAPAN,
                        'IN': Country.INDIA,
                        'AU': Country.AUSTRALIA,
                        'PH': Country.PHILIPPINES,
                        'IL': Country.ISRAEL,
                        'CA': Country.CANADA,
                        'TW': Country.TAIWAN,
                        'CN': Country.CHINA,
                        'HK': Country.HONG_KONG,
                        'MY': Country.MALAYSIA,
                        'TH': Country.THAILAND,
                        'VN': Country.VIETNAM,
                        'KR': Country.SOUTH_KOREA,
                        'ID': Country.INDONESIA
                    }
                    customer_country = country_code_mapping.get(country_code, Country.SINGAPORE)
                
                customer = CustomerUser(
                    name=primary_item['person_name'],
                    email=primary_item['primary_email'],
                    contact_number=primary_item.get('phone_number', ''),
                    address=customer_address,
                    company_id=company.id,
                    country=customer_country
                )
                db_session.add(customer)
                db_session.flush()
                customer_created = True
            
            # 2. DETERMINE CATEGORY AND QUEUE
            def determine_category_and_queue(product_title, category_code):
                """Determine category based on product type"""
                product_lower = product_title.lower()
                category_lower = category_code.lower() if category_code else ""
                
                # Accessory detection patterns
                accessory_keywords = [
                    'adapter', 'cable', 'charger', 'mouse', 'keyboard', 'headset', 
                    'webcam', 'dock', 'hub', 'dongle', 'stand', 'pad', 'cover',
                    'case', 'sleeve', 'bag', 'power supply', 'cord', 'usb'
                ]
                
                # Computer/laptop detection patterns  
                computer_keywords = [
                    'macbook', 'laptop', 'computer', 'imac', 'pc', 'desktop', 
                    'workstation', 'tower', 'all-in-one', 'surface', 'thinkpad'
                ]
                
                # Check if it's an accessory
                is_accessory = (
                    any(keyword in product_lower for keyword in accessory_keywords) or
                    any(keyword in category_lower for keyword in ['accessory', 'peripheral', 'cable', 'adapter'])
                )
                
                if is_accessory:
                    return 'ASSET_CHECKOUT_CLAW'  # Route accessories to checkout queue
                else:
                    return 'ASSET_CHECKOUT_CLAW'  # Route computers to tech asset queue
            
            # Get ticket category enum value
            category_name = determine_category_and_queue(
                primary_item.get('product_title', ''),
                primary_item.get('category_code', '')
            )
            
            # Convert string to TicketCategory enum
            try:
                category = getattr(TicketCategory, category_name)
            except AttributeError:
                # If category name doesn't exist in enum, use default
                category = TicketCategory.ASSET_CHECKOUT_CLAW
            
            # 3. MAP PRIORITY
            priority_mapping = {
                '1': TicketPriority.LOW,
                '2': TicketPriority.MEDIUM,
                '3': TicketPriority.HIGH
            }
            priority = priority_mapping.get(primary_item.get('priority', '1'), TicketPriority.LOW)
            
            # 4. CREATE ENHANCED DESCRIPTION WITH SELECTED ITEMS
            selected_items_text = ""
            if selected_assets:
                selected_items_text += f"""

Selected Assets from Inventory:
"""
                for asset in selected_assets:
                    selected_items_text += f"- {asset.get('assetName', 'Unknown Asset')} (ID: {asset.get('assetId', 'N/A')})\n"
            
            if selected_accessories:
                selected_items_text += f"""

Selected Accessories from Inventory:
"""
                for acc in selected_accessories:
                    selected_items_text += f"- {acc.get('accessoryName', 'Unknown Accessory')} (ID: {acc.get('accessoryId', 'N/A')})\n"
            
            if is_grouped:
                # Create description for multiple items
                csv_status = primary_item['status']
                status_indicator = f"📋 CSV Status: {csv_status}" + (" 🔴" if csv_status == 'PROCESSING' else " ✅")
                
                description = f"""Asset Checkout Request - CSV Import (Multi-Item Order)
{status_indicator}

Customer Information:
- Name: {primary_item['person_name']}
- Company: {primary_item['org_name']}
- Email: {primary_item['primary_email']}
- Phone: {primary_item['phone_number']}

Order Information:
- Order ID: {primary_item['order_id']}
- Total Items: {len(all_items)}
- Organization ID: {primary_item['organization_id']}
- CSV Import Status: {csv_status}
- Start Date: {primary_item['start_date'] or 'Not specified'}

Asset Information ({len(all_items)} items):
"""
                for i, item in enumerate(all_items, 1):
                    description += f"""
Item {i}:
- Product: {item['product_title']}
- Brand: {item['brand']}
- Serial Number: {item['serial_number']}
- Category: {item['category_code']}
- Condition: {item['preferred_condition'] or 'Not specified'}
- Item ID: {item['order_item_id']}
"""
                
                description += selected_items_text
                description += f"""
Imported from CSV on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"""
                
                subject = f"Asset Checkout - Order {primary_item['order_id']} ({len(all_items)} items) [{csv_status}]"
                
            else:
                # Single item description
                csv_status = primary_item['status']
                status_indicator = f"📋 CSV Status: {csv_status}" + (" 🔴" if csv_status == 'PROCESSING' else " ✅")
                
                description = f"""Asset Checkout Request - CSV Import
{status_indicator}

Customer Information:
- Name: {primary_item['person_name']}
- Company: {primary_item['org_name']}
- Email: {primary_item['primary_email']}
- Phone: {primary_item['phone_number']}

Asset Information:
- Product: {primary_item['product_title']}
- Brand: {primary_item['brand']}
- Serial Number: {primary_item['serial_number']}
- Category: {primary_item['category_code']}
- Condition: {primary_item['preferred_condition'] or 'Not specified'}
- CSV Import Status: {csv_status}
{selected_items_text}
Imported from CSV on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"""
                
                subject = f"Asset Checkout - {primary_item['product_title']} [{csv_status}]"
            
            # 5. FORMAT SHIPPING ADDRESS (as requested)
            shipping_address = f"""{primary_item['office_name']}
{primary_item['address_line1']}
{primary_item['address_line2']}
{primary_item['city']}, {primary_item['state']} {primary_item['postal_code']}
{primary_item['country_code']}""".strip()
            
            # 6. FORMAT ORDER DETAILS FOR NOTES (as requested)
            order_notes = f"""Order Details:
- Order ID: {primary_item['order_id']}
- Organization ID: {primary_item['organization_id']}
- Status: {primary_item['status']}
- Start Date: {primary_item['start_date'] or 'Not specified'}
- Shipped Date: {primary_item['shipped_date'] or 'Not specified'}
- Delivery Date: {primary_item['delivery_date'] or 'Not specified'}
- Carrier: {primary_item['carrier'] or 'Not specified'}
- Tracking: {primary_item['tracking_link'] or 'Not provided'}"""
            
            # 7. CREATE THE TICKET WITH PROPER DATA FLOW
            # Determine case owner (assigned_to_id)
            case_owner_id = current_user.id  # Default to current user
            if selected_case_owner_id:
                try:
                    case_owner_id = int(selected_case_owner_id)
                    logger.info("[CSV DEBUG] Using selected case owner: {case_owner_id}")
                except (ValueError, TypeError):
                    logger.info("[CSV DEBUG] Invalid case owner ID, using current user: {current_user.id}")
            
            logger.info("[CSV DEBUG] Creating ticket with subject: {subject}")
            ticket = Ticket(
                subject=subject,
                description=description,
                customer_id=customer.id,
                category=category,
                priority=priority,
                status=TicketStatus.NEW,
                requester_id=current_user.id,
                assigned_to_id=case_owner_id,  # Set case owner
                queue_id=int(selected_queue_id) if selected_queue_id else None,  # Assign to selected queue
                shipping_address=shipping_address,  # Shipping info goes to shipping_address field
                notes=order_notes  # Order details go to Notes field
            )
            
            db_session.add(ticket)
            db_session.flush()  # Ensure ticket gets an ID
            db_session.commit()
            logger.info("[CSV DEBUG] Ticket created successfully with ID: {ticket.id}")
            
            # Send queue notifications for the imported ticket
            try:
                from utils.queue_notification_sender import send_queue_notifications
                send_queue_notifications(ticket, action_type="created")
            except Exception as e:
                logger.error(f"Error sending queue notifications for CSV imported ticket: {str(e)}")
            
            # 8. ASSIGN SELECTED ASSETS AND ACCESSORIES TO TICKET
            assigned_accessories = []
            assigned_assets = []
            
            # Assign selected assets
            logger.info("[CSV DEBUG] About to process assets. selected_assets = {selected_assets}")
            logger.info("[CSV DEBUG] Number of selected assets: {len(selected_assets)}")
            
            # Check for duplicate asset IDs in the selection
            asset_ids = [asset_data.get('assetId') for asset_data in selected_assets if asset_data.get('assetId')]
            unique_asset_ids = list(set(asset_ids))
            logger.info("[CSV DEBUG] Asset IDs: {asset_ids}")
            logger.info("[CSV DEBUG] Unique Asset IDs: {unique_asset_ids}")
            if len(asset_ids) != len(unique_asset_ids):
                logger.info("[CSV DEBUG] WARNING: Duplicate asset IDs detected in selection!")
            
            if selected_assets:
                from models.asset import Asset
                logger.info("[CSV DEBUG] Processing {len(selected_assets)} selected assets")
                
                # Deduplicate assets by ID to prevent constraint violations
                processed_asset_ids = set()
                
                for asset_data in selected_assets:
                    asset_id = asset_data.get('assetId')
                    logger.info("[CSV DEBUG] Processing asset ID: {asset_id}")
                    if asset_id and asset_id not in processed_asset_ids:
                        processed_asset_ids.add(asset_id)
                        # Get the asset from database
                        asset = db_session.query(Asset).filter(Asset.id == asset_id).first()
                        if asset:
                            logger.info("[CSV DEBUG] Found asset: {asset.name}, Status: {asset.status}")
                            if asset.status and asset.status.value in ['In Stock', 'Ready to Deploy']:
                                # Use the existing function to safely assign asset
                                try:
                                    logger.info("[CSV DEBUG] Attempting to assign asset {asset_id} to ticket {ticket.id}")
                                    success = safely_assign_asset_to_ticket(ticket, asset, db_session)
                                    if success:
                                        assigned_assets.append(asset.name)
                                        logger.info("[CSV DEBUG] Successfully assigned asset {asset.name}")
                                        
                                        # Also assign the asset to the customer and update status
                                        if ticket.customer_id:
                                            asset.customer_id = ticket.customer_id
                                            logger.info("[CSV DEBUG] Assigned asset {asset.name} to customer {ticket.customer_id}")
                                        
                                        if ticket.assigned_to_id:
                                            asset.assigned_to_id = ticket.assigned_to_id
                                            logger.info("[CSV DEBUG] Assigned asset {asset.name} to user {ticket.assigned_to_id}")
                                        
                                        # Update asset status to DEPLOYED
                                        from models.asset import AssetStatus
                                        asset.status = AssetStatus.DEPLOYED
                                        logger.info("[CSV DEBUG] Updated asset {asset.name} status to DEPLOYED")
                                        
                                        # Create activity log for asset assignment
                                        from models.activity import Activity
                                        
                                        # Use current_user.id, fallback to admin user
                                        activity_user_id = current_user.id if current_user else 1
                                        
                                        activity = Activity(
                                            user_id=activity_user_id,
                                            type='asset_assigned',
                                            content=f'Assigned asset "{asset.name}" (Serial: {asset.serial_num}) to ticket #{ticket.display_id}',
                                            reference_id=ticket.id
                                        )
                                        db_session.add(activity)
                                    else:
                                        logger.info("[CSV DEBUG] Asset {asset_id} assignment failed or already assigned")
                                except Exception as e:
                                    logger.info("[CSV DEBUG] Error assigning asset {asset_id}: {str(e)}")
                                    import traceback
                                    traceback.print_exc()
                            else:
                                logger.info("[CSV DEBUG] Asset {asset_id} not available for assignment. Status: {asset.status}")
                        else:
                            logger.info("[CSV DEBUG] Asset {asset_id} not found in database")
                    elif asset_id in processed_asset_ids:
                        logger.info("[CSV DEBUG] Asset {asset_id} already processed, skipping duplicate")
            
            # Commit asset assignments
            if assigned_assets:
                logger.info("[CSV DEBUG] Committing {len(assigned_assets)} asset assignments")
                db_session.commit()
            
            # Assign selected accessories
            if selected_accessories:
                from models.ticket import TicketAccessory
                from models.accessory import Accessory
                
                for acc_data in selected_accessories:
                    accessory_id = acc_data.get('accessoryId')
                    if accessory_id:
                        # Get the accessory from database
                        accessory = db_session.query(Accessory).filter(Accessory.id == accessory_id).first()
                        if accessory and accessory.available_quantity > 0:
                            # Create ticket-accessory assignment
                            ticket_accessory = TicketAccessory(
                                ticket_id=ticket.id,
                                name=accessory.name,
                                category=accessory.category,
                                quantity=1,
                                condition='Good',
                                notes=f'Assigned from CSV import',
                                original_accessory_id=accessory.id
                            )
                            db_session.add(ticket_accessory)
                            
                            # Update accessory quantity (decrease available)
                            accessory.available_quantity -= 1
                            if accessory.available_quantity == 0:
                                accessory.status = 'Out of Stock'
                            
                            assigned_accessories.append(accessory.name)
                            
                            # Create activity log for accessory assignment
                            from models.activity import Activity
                            
                            # Use current_user.id, fallback to admin user
                            activity_user_id = current_user.id if current_user else 1
                            
                            activity = Activity(
                                user_id=activity_user_id,
                                type='accessory_assigned',
                                content=f'Assigned accessory "{accessory.name}" to ticket #{ticket.display_id}',
                                reference_id=ticket.id
                            )
                            db_session.add(activity)
                
                # Commit all assignments at once to avoid database locks
                db_session.commit()
            
            return jsonify({
                'success': True, 
                'ticket_id': ticket.id,
                'ticket_display_id': ticket.display_id,
                'customer_created': customer_created,
                'assigned_accessories': assigned_accessories,
                'assigned_assets': assigned_assets,
                'message': f'Ticket {ticket.display_id} created successfully. Customer {"created" if customer_created else "updated"}. {len(assigned_assets)} assets and {len(assigned_accessories)} accessories assigned.'
            })
            
        except Exception as e:
            db_session.rollback()
            raise e
        finally:
            db_session.close()
            
    except Exception as e:
        logger.info("Error importing ticket: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': f'Failed to import ticket: {str(e)}'})


@admin_bp.route('/csv-import/bulk-import', methods=['POST'])
@admin_required
def csv_import_bulk_import():
    """Import multiple tickets from CSV data"""
    try:
        data = request.get_json()
        row_indices = data.get('row_indices', [])
        auto_create_customer = data.get('auto_create_customer', True)
        selected_accessories = data.get('selected_accessories', [])  # Get selected accessories
        selected_assets = data.get('selected_assets', [])  # Get selected assets
        
        if 'csv_import_file' not in session:
            return jsonify({'success': False, 'error': 'No CSV data found. Please upload a file first.'})
        
        # Load CSV data from temporary file
        import json
        import os
        import tempfile
        
        csv_filename = session['csv_import_file']
        csv_filepath = os.path.join(tempfile.gettempdir(), csv_filename)
        
        if not os.path.exists(csv_filepath):
            return jsonify({'success': False, 'error': 'CSV data file not found. Please upload the file again.'})
        
        try:
            with open(csv_filepath, 'r') as f:
                file_data = json.load(f)
                # Handle both old format (list) and new format (dict with grouped data)
                if isinstance(file_data, list):
                    csv_data = file_data  # Old format
                else:
                    csv_data = file_data.get('grouped_orders', file_data.get('individual_rows', []))
        except Exception as e:
            return jsonify({'success': False, 'error': f'Error reading CSV data: {str(e)}'})
        results = []
        
        for row_index in row_indices:
            if row_index >= len(csv_data):
                results.append({'row_index': row_index, 'success': False, 'error': 'Invalid row index'})
                continue
            
            # Check if the ticket has PROCESSING status and block import
            row = csv_data[row_index]
            if row.get('status') == 'PROCESSING':
                results.append({
                    'row_index': row_index, 
                    'success': False, 
                    'error': 'Cannot import tickets with PROCESSING status. Please wait for the order to progress to another status before importing.'
                })
                continue
            
            # Import single ticket (reuse the logic)
            try:
                result = csv_import_import_ticket_internal(csv_data[row_index], auto_create_customer, selected_accessories, selected_assets, current_user.id)
                results.append({'row_index': row_index, **result})
            except Exception as e:
                results.append({'row_index': row_index, 'success': False, 'error': str(e)})
        
        successful_imports = sum(1 for r in results if r.get('success'))
        
        return jsonify({
            'success': True,
            'results': results,
            'total_processed': len(row_indices),
            'successful_imports': successful_imports,
            'failed_imports': len(row_indices) - successful_imports
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': f'Bulk import error: {str(e)}'})


def csv_import_import_ticket_internal(row, auto_create_customer=True, selected_accessories=[], selected_assets=[], user_id=None):
    """Internal function to import a single ticket (used by bulk import)"""
    
    # Check if the ticket has PROCESSING status and block import
    if row.get('status') == 'PROCESSING':
        return {
            'success': False, 
            'error': 'Cannot import tickets with PROCESSING status. Please wait for the order to progress to another status before importing.'
        }
    
    db_session = db_manager.get_session()
    
    try:
        # Configure SQLite for better concurrency
        from sqlalchemy import text
        db_session.execute(text("PRAGMA journal_mode=WAL;"))
        db_session.execute(text("PRAGMA synchronous=NORMAL;"))
        db_session.execute(text("PRAGMA busy_timeout=30000;"))  # 30 second timeout
        
        # Add a small delay to prevent database lock conflicts
        import time
        time.sleep(0.1)
        # Check if customer exists or create new one
        customer = None
        customer_created = False
        
        if row['primary_email']:
            customer = db_session.query(CustomerUser).filter(CustomerUser.email == row['primary_email']).first()
        
        if not customer and auto_create_customer:
            # Create new customer
            from models.user import Country
            from models.company import Company
            
            # Get or create company
            company = db_session.query(Company).filter(
                Company.name == row['org_name']
            ).first()
            
            if not company:
                company = Company(
                    name=row['org_name'],
                    description=f"Auto-created from CSV import",
                    contact_email=row['primary_email']
                )
                db_session.add(company)
                db_session.flush()
            
            # Map city to country as requested by user, with fallback to country_code
            city_to_country_mapping = {
                'Singapore': Country.SINGAPORE,
                'Kuala Lumpur': Country.MALAYSIA,
                'Bangkok': Country.THAILAND,
                'Manila': Country.PHILIPPINES,
                'Jakarta': Country.INDONESIA,
                'Ho Chi Minh City': Country.VIETNAM,
                'Hanoi': Country.VIETNAM,
                'Seoul': Country.SOUTH_KOREA,
                'Tokyo': Country.JAPAN,
                'Osaka': Country.JAPAN,
                'Sydney': Country.AUSTRALIA,
                'Melbourne': Country.AUSTRALIA,
                'Mumbai': Country.INDIA,
                'Delhi': Country.INDIA,
                'Bangalore': Country.INDIA,
                'Tel Aviv': Country.ISRAEL,
                'Jerusalem': Country.ISRAEL,
                'Toronto': Country.CANADA,
                'Vancouver': Country.CANADA,
                'New York': Country.USA,
                'Los Angeles': Country.USA,
                'San Francisco': Country.USA,
                'Hong Kong': Country.HONG_KONG,
                'Taipei': Country.TAIWAN,
                'Beijing': Country.CHINA,
                'Shanghai': Country.CHINA
            }
            
            # First try to map from city, then fallback to country_code
            city = row.get('city', '')
            country_code = row.get('country_code', '')
            
            if city and city in city_to_country_mapping:
                country = city_to_country_mapping[city]
            else:
                # Fallback to country code mapping
                country_code_mapping = {
                    'SG': Country.SINGAPORE,
                    'US': Country.USA,
                    'JP': Country.JAPAN,
                    'IN': Country.INDIA,
                    'AU': Country.AUSTRALIA,
                    'PH': Country.PHILIPPINES,
                    'IL': Country.ISRAEL,
                    'CA': Country.CANADA,
                    'TW': Country.TAIWAN,
                    'CN': Country.CHINA,
                    'HK': Country.HONG_KONG,
                    'MY': Country.MALAYSIA,
                    'TH': Country.THAILAND,
                    'VN': Country.VIETNAM,
                    'KR': Country.SOUTH_KOREA,
                    'ID': Country.INDONESIA
                }
                country = country_code_mapping.get(country_code, Country.SINGAPORE)
            
            # Create address from available fields
            address_parts = [
                row.get('address_line1', ''),
                row.get('address_line2', ''),
                row.get('city', ''),
                f"{row.get('state', '')} {row.get('postal_code', '')}".strip(),
                row.get('country_code', '')
            ]
            customer_address = ', '.join(filter(None, address_parts))
            if not customer_address.strip():
                customer_address = "Address not provided"
            
            customer = CustomerUser(
                name=row['person_name'],
                email=row['primary_email'],
                contact_number=row.get('phone_number', ''),
                address=customer_address,
                company_id=company.id,
                country=country
            )
            db_session.add(customer)
            db_session.flush()  # Get the customer ID
            customer_created = True
        
        if not customer:
            return {'success': False, 'error': 'Customer not found and auto-create is disabled'}
        
        # Get ticket category enum value
        category_mapping = {
            'COMPUTER': 'ASSET_CHECKOUT_CLAW',
            'LAPTOP': 'ASSET_CHECKOUT_CLAW', 
            'MONITOR': 'ASSET_CHECKOUT_CLAW',
            'KEYBOARD': 'ASSET_CHECKOUT_CLAW',
            'MOUSE': 'ASSET_CHECKOUT_CLAW',
            'HEADSET': 'ASSET_CHECKOUT_CLAW',
            'AV_ADAPTER': 'ASSET_CHECKOUT_CLAW',
            'COMPUTER_ACCESSORY': 'ASSET_CHECKOUT_CLAW'
        }
        
        category_name = category_mapping.get(row['category_code'], 'ASSET_CHECKOUT_CLAW')
        
        # Convert string to TicketCategory enum
        try:
            category = getattr(TicketCategory, category_name)
        except AttributeError:
            # If category name doesn't exist in enum, use default
            category = TicketCategory.ASSET_CHECKOUT_CLAW
        
        # Map priority
        priority_mapping = {
            '1': TicketPriority.LOW,
            '2': TicketPriority.MEDIUM,
            '3': TicketPriority.HIGH
        }
        priority = priority_mapping.get(row['priority'], TicketPriority.LOW)
        
        # Create detailed description
        selected_accessories_text = ""
        if selected_accessories:
            selected_accessories_text = f"""

Selected Accessories from Inventory:
"""
            for acc in selected_accessories:
                selected_accessories_text += f"- {acc.get('accessoryName', 'Unknown Accessory')} (ID: {acc.get('accessoryId', 'N/A')})\n"
        
        # Create CSV status indicator
        csv_status = row['status']
        status_indicator = f"📋 CSV Status: {csv_status}" + (" 🔴" if csv_status == 'PROCESSING' else " ✅")
        
        description = f"""Asset Checkout Request - CSV Import
{status_indicator}

Customer Information:
- Name: {row['person_name']}
- Company: {row['org_name']}
- Email: {row['primary_email']}
- Phone: {row['phone_number']}

Asset Information:
- Product: {row['product_title']}
- Brand: {row['brand']}
- Serial Number: {row['serial_number']}
- Category: {row['category_code']}
- Condition: {row['preferred_condition'] or 'Not specified'}
- CSV Import Status: {csv_status}

Shipping Information:
- Office: {row['office_name']}
- Address: {row['address_line1']}, {row['address_line2']}
- City: {row['city']}, {row['state']} {row['postal_code']}
- Country: {row['country_code']}
- Carrier: {row['carrier'] or 'Not specified'}
- Tracking: {row['tracking_link'] or 'Not provided'}

Order Information:
- Order ID: {row['order_id']}
- Order Item ID: {row['order_item_id']}
- Organization ID: {row['organization_id']}
- CSV Status: {csv_status}
- Start Date: {row['start_date'] or 'Not specified'}
- Shipped Date: {row['shipped_date'] or 'Not specified'}
- Delivery Date: {row['delivery_date'] or 'Not specified'}
{selected_accessories_text}
Imported from CSV on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"""
        
        # Create the ticket
        # Use provided user_id or try to get current_user.id, fallback to 1 (admin)
        requester_id = user_id
        if not requester_id:
            try:
                from flask_login import current_user
                requester_id = current_user.id if current_user and current_user.is_authenticated else 1
            except:
                requester_id = 1  # Fallback to admin user
        
        ticket = Ticket(
            subject=f"Asset Checkout - {row['product_title']} [{csv_status}]",
            description=description,
            customer_id=customer.id,
            category=category,
            priority=priority,
            status=TicketStatus.NEW,
            requester_id=requester_id
        )
        
        db_session.add(ticket)
        db_session.flush()  # Ensure ticket gets an ID
        db_session.commit()
        
        # Send queue notifications for the imported ticket
        try:
            from utils.queue_notification_sender import send_queue_notifications
            send_queue_notifications(ticket, action_type="created")
        except Exception as e:
            logger.error(f"Error sending queue notifications for CSV imported ticket: {str(e)}")
        
        # Assign selected assets and accessories to ticket
        assigned_accessories = []
        assigned_assets = []
        
        # Assign selected assets
        if selected_assets:
            from models.asset import Asset
            
            for asset_data in selected_assets:
                asset_id = asset_data.get('assetId')
                if asset_id:
                    # Get the asset from database
                    asset = db_session.query(Asset).filter(Asset.id == asset_id).first()
                    if asset and asset.status and asset.status.value in ['In Stock', 'Ready to Deploy']:
                        # Use the existing function to safely assign asset
                        try:
                            safely_assign_asset_to_ticket(ticket, asset, db_session)
                            assigned_assets.append(asset.name)
                            
                            # Also assign the asset to the customer and update status
                            if ticket.customer_id:
                                asset.customer_id = ticket.customer_id
                                logger.info("[CSV DEBUG] Assigned asset {asset.name} to customer {ticket.customer_id}")
                            
                            if ticket.assigned_to_id:
                                asset.assigned_to_id = ticket.assigned_to_id
                                logger.info("[CSV DEBUG] Assigned asset {asset.name} to user {ticket.assigned_to_id}")
                            
                            # Update asset status to DEPLOYED
                            from models.asset import AssetStatus
                            asset.status = AssetStatus.DEPLOYED
                            logger.info("[CSV DEBUG] Updated asset {asset.name} status to DEPLOYED")
                            
                            # Create activity log for asset assignment
                            from models.activity import Activity
                            activity = Activity(
                                user_id=requester_id,
                                type='asset_assigned',
                                content=f'Assigned asset "{asset.name}" (Serial: {asset.serial_num}) to ticket #{ticket.display_id}',
                                reference_id=ticket.id
                            )
                            db_session.add(activity)
                        except Exception as e:
                            logger.info("Error assigning asset {asset_id}: {str(e)}")
        
        # Assign selected accessories
        if selected_accessories:
            from models.ticket import TicketAccessory
            from models.accessory import Accessory
            
            for acc_data in selected_accessories:
                accessory_id = acc_data.get('accessoryId')
                if accessory_id:
                    # Get the accessory from database
                    accessory = db_session.query(Accessory).filter(Accessory.id == accessory_id).first()
                    if accessory and accessory.available_quantity > 0:
                        # Create ticket-accessory assignment
                        ticket_accessory = TicketAccessory(
                            ticket_id=ticket.id,
                            name=accessory.name,
                            category=accessory.category,
                            quantity=1,
                            condition='Good',
                            notes=f'Assigned from CSV import',
                            original_accessory_id=accessory.id
                        )
                        db_session.add(ticket_accessory)
                        
                        # Update accessory quantity (decrease available)
                        accessory.available_quantity -= 1
                        if accessory.available_quantity == 0:
                            accessory.status = 'Out of Stock'
                        
                        assigned_accessories.append(accessory.name)
                        
                        # Create activity log for accessory assignment
                        from models.activity import Activity
                        activity = Activity(
                            user_id=requester_id,
                            type='accessory_assigned',
                            content=f'Assigned accessory "{accessory.name}" to ticket #{ticket.display_id}',
                            reference_id=ticket.id
                        )
                        db_session.add(activity)
        
        # Commit all assignments at once to avoid database locks
        if assigned_assets or assigned_accessories:
            db_session.commit()
        
        return {
            'success': True, 
            'ticket_id': ticket.id,
            'ticket_display_id': ticket.display_id,
            'customer_created': customer_created,
            'assigned_accessories': assigned_accessories,
            'assigned_assets': assigned_assets
        }
        
    except Exception as e:
        db_session.rollback()
        raise e
    finally:
        db_session.close() 

def safely_assign_asset_to_ticket(ticket, asset, db_session):
    """
    Safely assign an asset to a ticket, checking for existing relationships first
    
    Args:
        ticket: Ticket object
        asset: Asset object or asset ID
        db_session: Database session
        
    Returns:
        bool: True if assignment was successful or already exists, False otherwise
    """
    try:
        logger.info("[ASSET ASSIGN DEBUG] Starting assignment - Ticket: {ticket.id}, Asset: {asset}")
        
        # If asset is an ID, get the asset object
        if isinstance(asset, int):
            asset_id = asset
            asset = db_session.query(Asset).get(asset_id)
            if not asset:
                logger.info("[ASSET ASSIGN DEBUG] Asset with ID {asset_id} not found")
                return False
        
        logger.info("[ASSET ASSIGN DEBUG] Asset object: {asset.name} (ID: {asset.id})")
        
        # Check if the relationship already exists in the database first
        from sqlalchemy import text
        stmt = text("""
            SELECT COUNT(*) FROM ticket_assets 
            WHERE ticket_id = :ticket_id AND asset_id = :asset_id
        """)
        result = db_session.execute(stmt, {"ticket_id": ticket.id, "asset_id": asset.id})
        count = result.scalar()
        
        logger.info("[ASSET ASSIGN DEBUG] Existing relationship count: {count}")
        
        if count > 0:
            logger.info("[ASSET ASSIGN DEBUG] Asset {asset.id} already linked to ticket {ticket.id} in database")
            return True
        
        # Check if asset is already assigned to this ticket in memory
        if asset in ticket.assets:
            logger.info("[ASSET ASSIGN DEBUG] Asset {asset.id} ({asset.asset_tag}) already assigned to ticket {ticket.id} in memory")
            return True
        
        # Safe to assign - insert directly into ticket_assets table
        logger.info("[ASSET ASSIGN DEBUG] Inserting directly into ticket_assets table")
        try:
            from sqlalchemy import text
            insert_stmt = text("""
                INSERT INTO ticket_assets (ticket_id, asset_id) 
                VALUES (:ticket_id, :asset_id)
            """)
            db_session.execute(insert_stmt, {"ticket_id": ticket.id, "asset_id": asset.id})
            db_session.flush()
            logger.info("[ASSET ASSIGN DEBUG] Successfully assigned asset {asset.id} ({asset.asset_tag}) to ticket {ticket.id}")
            return True
        except Exception as insert_error:
            logger.info("[ASSET ASSIGN DEBUG] Error during direct insert: {str(insert_error)}")
            # Check if it's a constraint violation (asset already assigned)
            if "UNIQUE constraint failed" in str(insert_error):
                logger.info("[ASSET ASSIGN DEBUG] Asset {asset.id} already assigned to ticket {ticket.id}")
                return True  # Consider this a success since the asset is already assigned
            else:
                logger.info("[ASSET ASSIGN DEBUG] Unexpected error during insert")
                return False
        
    except Exception as e:
        logger.info("[ASSET ASSIGN DEBUG] Error assigning asset to ticket: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

@admin_bp.route('/permissions/unified')
@login_required
@admin_required
def unified_permissions():
    """Unified permissions management page combining user permissions and queue permissions"""
    db_session = db_manager.get_session()
    try:
        # Get all users for permission management
        users = db_session.query(User).all()
        
        # Get all companies and queues for queue permissions
        companies = db_session.query(Company).all()
        queues = db_session.query(Queue).all()
        
        # Get existing queue permissions
        queue_permissions = db_session.query(CompanyQueuePermission).all()
        
        # Get existing user permissions
        user_permissions = db_session.query(Permission).all()
        
        return render_template('admin/unified_permissions.html', 
                             users=users,
                             companies=companies,
                             queues=queues,
                             queue_permissions=queue_permissions,
                             user_permissions=user_permissions)
    except Exception as e:
        flash(f'Error loading permissions: {str(e)}', 'error')
        return redirect(url_for('main.index'))
    finally:
        db_session.close()


# Group Management Routes

@admin_bp.route('/groups')
@admin_required
def manage_groups():
    """Group management page"""
    if 'user_id' not in session:
        flash('Please log in to continue', 'error')
        return redirect(url_for('auth.login'))

    db_session = db_manager.get_session()
    try:
        # Get current user
        user = db_manager.get_user(session['user_id'])
        if not user:
            session.clear()
            return redirect(url_for('auth.login'))

        # Import the models here to avoid circular imports
        from models.group import Group
        from models.group_membership import GroupMembership
        
        # Get all groups with their memberships
        groups = db_session.query(Group).order_by(Group.created_at.desc()).all()
        
        # Get all users for the add member dropdown
        users = db_session.query(User).order_by(User.username).all()

        return render_template('admin/manage_groups.html', 
                             user=user,
                             groups=groups,
                             users=users)

    except Exception as e:
        logger.error(f"Error loading groups page: {e}")
        flash(f'Error loading groups: {str(e)}', 'error')
        return redirect(url_for('admin.system_config'))
    finally:
        db_session.close()


@admin_bp.route('/groups/create', methods=['POST'])
@admin_required
def create_group():
    """Create a new group"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401

    db_session = db_manager.get_session()
    try:
        # Get current user
        user = db_manager.get_user(session['user_id'])
        if not user:
            return jsonify({'error': 'User not found'}), 404

        # Import the model here to avoid circular imports
        from models.group import Group
        
        # Get form data
        name = request.form.get('name', '').strip().lower()
        description = request.form.get('description', '').strip()
        
        if not name:
            return jsonify({'error': 'Group name is required'}), 400
            
        # Validate group name (alphanumeric and hyphens only)
        import re
        if not re.match(r'^[a-z0-9-]+$', name):
            return jsonify({'error': 'Group name can only contain lowercase letters, numbers, and hyphens'}), 400
        
        # Check if group name already exists
        existing_group = db_session.query(Group).filter(Group.name == name).first()
        if existing_group:
            return jsonify({'error': 'A group with this name already exists'}), 400
        
        # Create new group
        group = Group(
            name=name,
            description=description if description else None,
            created_by_id=user.id
        )
        
        db_session.add(group)
        db_session.commit()
        
        logger.info(f"Group '{name}' created by user {user.username}")
        flash(f"Group '@{name}' created successfully", 'success')
        
        return jsonify({'success': True, 'group_id': group.id})

    except Exception as e:
        logger.error(f"Error creating group: {e}")
        db_session.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        db_session.close()


@admin_bp.route('/groups/update', methods=['POST'])
@admin_required
def update_group():
    """Update an existing group"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401

    db_session = db_manager.get_session()
    try:
        # Get current user
        user = db_manager.get_user(session['user_id'])
        if not user:
            return jsonify({'error': 'User not found'}), 404

        # Import the model here to avoid circular imports
        from models.group import Group
        
        # Get form data
        group_id = request.form.get('group_id')
        name = request.form.get('name', '').strip().lower()
        description = request.form.get('description', '').strip()
        
        if not group_id or not name:
            return jsonify({'error': 'Group ID and name are required'}), 400
        
        # Validate group name
        import re
        if not re.match(r'^[a-z0-9-]+$', name):
            return jsonify({'error': 'Group name can only contain lowercase letters, numbers, and hyphens'}), 400
        
        # Get the group
        group = db_session.query(Group).filter(Group.id == group_id).first()
        if not group:
            return jsonify({'error': 'Group not found'}), 404
        
        # Check if new name conflicts with existing group (excluding current group)
        if group.name != name:
            existing_group = db_session.query(Group).filter(
                Group.name == name,
                Group.id != group_id
            ).first()
            if existing_group:
                return jsonify({'error': 'A group with this name already exists'}), 400
        
        # Update group
        old_name = group.name
        group.name = name
        group.description = description if description else None
        group.updated_at = datetime.utcnow()
        
        db_session.commit()
        
        logger.info(f"Group '{old_name}' updated to '{name}' by user {user.username}")
        flash(f"Group '@{name}' updated successfully", 'success')
        
        return jsonify({'success': True})

    except Exception as e:
        logger.error(f"Error updating group: {e}")
        db_session.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        db_session.close()


@admin_bp.route('/groups/add-member', methods=['POST'])
@admin_required
def add_group_member():
    """Add a member to a group"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401

    db_session = db_manager.get_session()
    try:
        # Get current user
        current_user = db_manager.get_user(session['user_id'])
        if not current_user:
            return jsonify({'error': 'User not found'}), 404

        # Import the models here to avoid circular imports
        from models.group import Group
        
        # Get form data
        group_id = request.form.get('group_id')
        user_id = request.form.get('user_id')
        
        if not group_id or not user_id:
            return jsonify({'error': 'Group ID and User ID are required'}), 400
        
        # Convert to integers
        try:
            group_id = int(group_id)
            user_id = int(user_id)
        except (ValueError, TypeError):
            return jsonify({'error': 'Invalid Group ID or User ID format'}), 400
        
        # Get the group and user
        group = db_session.query(Group).filter(Group.id == group_id).first()
        if not group:
            return jsonify({'error': 'Group not found'}), 404
            
        user = db_session.query(User).filter(User.id == user_id).first()
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Check if user is already a member
        if group.has_member(user_id):
            return jsonify({'error': f'{user.username} is already a member of this group'}), 400
        
        # Add member to group
        membership = group.add_member(user_id, current_user.id)
        
        db_session.commit()
        
        logger.info(f"User {user.username} added to group '{group.name}' by {current_user.username}")
        flash(f"{user.username} added to group '@{group.name}' successfully", 'success')
        
        return jsonify({'success': True})

    except Exception as e:
        logger.error(f"Error adding group member: {e}")
        db_session.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        db_session.close()


@admin_bp.route('/groups/remove-member', methods=['POST'])
@admin_required
def remove_group_member():
    """Remove a member from a group"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401

    db_session = db_manager.get_session()
    try:
        # Get current user
        current_user = db_manager.get_user(session['user_id'])
        if not current_user:
            return jsonify({'error': 'User not found'}), 404

        # Import the models here to avoid circular imports
        from models.group import Group
        
        # Get form data
        group_id = request.form.get('group_id')
        user_id = request.form.get('user_id')
        
        if not group_id or not user_id:
            return jsonify({'error': 'Group ID and User ID are required'}), 400
        
        # Convert to integers
        try:
            group_id = int(group_id)
            user_id = int(user_id)
        except (ValueError, TypeError):
            return jsonify({'error': 'Invalid Group ID or User ID format'}), 400
        
        # Get the group and user
        group = db_session.query(Group).filter(Group.id == group_id).first()
        if not group:
            return jsonify({'error': 'Group not found'}), 404
            
        user = db_session.query(User).filter(User.id == user_id).first()
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Debug: Check current group membership
        logger.info(f"Attempting to remove user {user.id} ({user.username}) from group {group.id} ({group.name})")
        logger.info(f"Group has {group.member_count} members: {[m.username for m in group.members]}")
        
        # Check if user is actually in the group before attempting removal
        if not group.has_member(user_id):
            current_members = [m.username for m in group.members]
            logger.warning(f"User {user.username} is not a member of group {group.name}. Current members: {current_members}")
            return jsonify({'error': f'User {user.username} is not a member of group @{group.name}. Current members: {", ".join(current_members) if current_members else "none"}'}), 400
        
        # Remove member from group
        if group.remove_member(user_id):
            db_session.commit()
            
            logger.info(f"User {user.username} removed from group '{group.name}' by {current_user.username}")
            flash(f"{user.username} removed from group '@{group.name}' successfully", 'success')
            
            return jsonify({'success': True})
        else:
            # This shouldn't happen if we got past the has_member check above
            logger.error(f"Unexpected: remove_member returned False even though user was a member")
            return jsonify({'error': f'Unexpected error removing user {user.username} from group @{group.name}'}), 500

    except Exception as e:
        logger.error(f"Error removing group member: {e}")
        db_session.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        db_session.close()


@admin_bp.route('/groups/toggle-status', methods=['POST'])
@admin_required
def toggle_group_status():
    """Activate or deactivate a group"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401

    db_session = db_manager.get_session()
    try:
        # Get current user
        current_user = db_manager.get_user(session['user_id'])
        if not current_user:
            return jsonify({'error': 'User not found'}), 404

        # Import the model here to avoid circular imports
        from models.group import Group
        
        # Get form data
        group_id = request.form.get('group_id')
        is_active = request.form.get('is_active', '').lower() == 'true'
        
        if not group_id:
            return jsonify({'error': 'Group ID is required'}), 400
        
        # Get the group
        group = db_session.query(Group).filter(Group.id == group_id).first()
        if not group:
            return jsonify({'error': 'Group not found'}), 404
        
        # Update group status
        group.is_active = is_active
        group.updated_at = datetime.utcnow()
        
        db_session.commit()
        
        status_text = "activated" if is_active else "deactivated"
        logger.info(f"Group '{group.name}' {status_text} by user {current_user.username}")
        flash(f"Group '@{group.name}' {status_text} successfully", 'success')
        
        return jsonify({'success': True})

    except Exception as e:
        logger.error(f"Error toggling group status: {e}")
        db_session.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        db_session.close()


@admin_bp.route('/groups/delete', methods=['POST'])
@admin_required
def delete_group():
    """Delete a group permanently"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401

    db_session = db_manager.get_session()
    try:
        # Get current user
        current_user = db_manager.get_user(session['user_id'])
        if not current_user:
            return jsonify({'error': 'User not found'}), 404

        # Import the model here to avoid circular imports
        from models.group import Group
        
        # Get form data
        group_id = request.form.get('group_id')
        
        if not group_id:
            return jsonify({'error': 'Group ID is required'}), 400
        
        # Get the group
        group = db_session.query(Group).filter(Group.id == group_id).first()
        if not group:
            return jsonify({'error': 'Group not found'}), 404
        
        group_name = group.name
        
        # Delete the group (this will cascade delete memberships due to the relationship)
        db_session.delete(group)
        db_session.commit()
        
        logger.info(f"Group '{group_name}' deleted by user {current_user.username}")
        flash(f"Group '@{group_name}' deleted successfully", 'success')
        
        return jsonify({'success': True})

    except Exception as e:
        logger.error(f"Error deleting group: {e}")
        db_session.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        db_session.close()


@admin_bp.route('/api/mention-suggestions')
@login_required
def get_mention_suggestions():
    """Get users and groups for @mention autocomplete"""
    query = request.args.get('q', '').lower().strip()
    
    db_session = db_manager.get_session()
    try:
        from models.group import Group
        
        suggestions = []
        
        # Get users (limit to 10 for performance)
        users = db_session.query(User).filter(
            User.username.ilike(f'%{query}%')
        ).limit(10).all()
        
        for user in users:
            suggestions.append({
                'type': 'user',
                'id': user.id,
                'name': user.username,
                'display_name': user.username,
                'email': user.email,
                'avatar': user.username[0].upper() if user.username else 'U'
            })
        
        # Get active groups (limit to 10 for performance)
        groups = db_session.query(Group).filter(
            Group.name.ilike(f'%{query}%'),
            Group.is_active == True
        ).limit(10).all()
        
        for group in groups:
            suggestions.append({
                'type': 'group',
                'id': group.id,
                'name': group.name,
                'display_name': f"@{group.name}",
                'description': group.description or f"Group with {group.member_count} members",
                'member_count': group.member_count,
                'avatar': 'G'  # Group icon
            })
        
        # Sort by relevance (exact matches first, then partial matches)
        def sort_key(item):
            name = item['name'].lower()
            if name == query:
                return (0, name)  # Exact match
            elif name.startswith(query):
                return (1, name)  # Starts with query
            else:
                return (2, name)  # Contains query
        
        suggestions.sort(key=sort_key)
        
        return jsonify({'suggestions': suggestions[:20]})  # Limit to 20 total suggestions
        
    except Exception as e:
        logger.error(f"Error getting mention suggestions: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        db_session.close()