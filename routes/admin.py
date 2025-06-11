from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash, current_app, session, send_file
from flask_login import current_user
from flask_wtf.csrf import CSRFProtect
from utils.auth_decorators import admin_required, super_admin_required, login_required
from utils.snipeit_client import SnipeITClient
from utils.db_manager import DatabaseManager
from models.user import User, UserType, Country
from models.permission import Permission
from datetime import datetime
from models.company import Company
from models.queue import Queue
from models.company_queue_permission import CompanyQueuePermission
from utils.email_sender import send_welcome_email
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

admin_bp = Blueprint('admin', __name__)
snipe_client = SnipeITClient()
db_manager = DatabaseManager()
csrf = CSRFProtect()

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
    print(f"DEBUG: Delete company request received for company_id={company_id}")
    
    db_session = db_manager.get_session()
    try:
        # Check if company exists
        company = db_session.query(Company).get(company_id)
        if not company:
            print(f"DEBUG: Company with ID {company_id} not found")
            flash('Company not found', 'error')
            return redirect(url_for('admin.manage_companies'))
        
        # Check if company has associated users
        users_count = db_session.query(User).filter_by(company_id=company_id).count()
        if users_count > 0:
            print(f"DEBUG: Cannot delete company - it has {users_count} associated users")
            flash(f'Cannot delete company: It has {users_count} associated users. Please reassign or delete the users first.', 'error')
            return redirect(url_for('admin.manage_companies'))
        
        # First delete all related company queue permissions
        print(f"DEBUG: Deleting queue permissions for company_id={company_id}")
        deleted_permissions = db_session.query(CompanyQueuePermission).filter_by(company_id=company_id).delete()
        print(f"DEBUG: Deleted {deleted_permissions} queue permissions")
        
        # Then delete the company
        print(f"DEBUG: Deleting company: {company.name} (ID: {company.id})")
        db_session.delete(company)
        db_session.commit()
        flash('Company deleted successfully', 'success')
        return redirect(url_for('admin.manage_companies'))
    
    except Exception as e:
        db_session.rollback()
        print(f"DEBUG: Error deleting company: {str(e)}")
        print(f"DEBUG: {traceback.format_exc()}")
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
    print(f"DEBUG: Entering edit_user route for user_id={user_id}")
    db_session = db_manager.get_session()
    user = db_session.query(User).get(user_id)
    if not user:
        print("DEBUG: User not found")
        flash('User not found', 'error')
        return redirect(url_for('admin.manage_users'))

    print(f"DEBUG: User found: {user.username}, type={user.user_type}")
    companies = db_session.query(Company).all()
    print(f"DEBUG: Found {len(companies)} companies")

    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        company_id = request.form.get('company_id')
        user_type = request.form.get('user_type')
        password = request.form.get('password')
        assigned_country = request.form.get('assigned_country')

        print(f"DEBUG: Form submission - company_id={company_id}, user_type={user_type}")

        try:
            # Update basic user information
            user.username = username
            user.email = email
            user.user_type = UserType[user_type]

            # Handle company assignment
            user.company_id = company_id if company_id else None
            
            # Company is required for CLIENT users
            if user_type == 'CLIENT' and not company_id:
                print("DEBUG: CLIENT type but no company selected")
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
            print(f"DEBUG: Error updating user: {str(e)}")
            flash(f'Error updating user: {str(e)}', 'error')
        finally:
            db_session.close()

    print("DEBUG: Rendering edit_user template")
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
        print("Form data received:", request.form)
        
        user_type = request.form.get('user_type')
        print("User type:", user_type)
        
        if not user_type:
            flash('User type is required', 'error')
            return redirect(url_for('admin.permission_management'))

        try:
            user_type_enum = UserType[user_type]
            print("User type enum:", user_type_enum)
        except KeyError:
            flash('Invalid user type', 'error')
            return redirect(url_for('admin.permission_management'))

        # Get existing permission record
        permission = db_session.query(Permission).filter_by(user_type=user_type_enum).first()
        print("Existing permission:", permission)
        
        if not permission:
            permission = Permission(user_type=user_type_enum)
            db_session.add(permission)
            print("Created new permission record")

        # Get all permission fields
        fields = Permission.permission_fields()
        print("Permission fields:", fields)

        # Update permissions from form data
        for field in fields:
            old_value = getattr(permission, field)
            # Check if the field exists in form and its value is 'true'
            new_value = request.form.get(field) == 'true'
            setattr(permission, field, new_value)
            print(f"Updating {field}: {old_value} -> {new_value}")

        db_session.commit()
        print("Changes committed successfully")
        
        flash('Permissions updated successfully', 'success')
        return redirect(url_for('admin.permission_management'))
    except Exception as e:
        db_session.rollback()
        print("Error updating permissions:", str(e))
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
        print("Form data received:", request.form)
        print("JSON data received:", request.get_json(silent=True))
        
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
        
        print(f"Raw company_id: {company_id}, type: {type(company_id)}")
        print(f"Raw queue_id: {queue_id}, type: {type(queue_id)}")
        
        # Convert to integers with safer handling
        try:
            if company_id:
                company_id = int(company_id)
            if queue_id:
                queue_id = int(queue_id)
        except (ValueError, TypeError) as e:
            print(f"Error converting IDs to integers: {str(e)}")
            flash(f"Invalid ID format: {str(e)}", 'error')
            return redirect(url_for('admin.manage_queue_permissions'))
        
        print(f"Converted company_id: {company_id}, queue_id: {queue_id}")
        print(f"Permission values - has_permission: {has_permission}, can_view: {can_view}, can_create: {can_create}")
        
        if not company_id or not queue_id:
            print("INVALID: Missing company_id or queue_id")
            flash('Invalid company or queue ID', 'error')
            return redirect(url_for('admin.manage_queue_permissions'))
        
        db_session = db_manager.get_session()
        try:
            # Verify company and queue exist
            company = db_session.query(Company).get(company_id)
            queue = db_session.query(Queue).get(queue_id)
            
            if not company:
                print(f"Company with ID {company_id} not found")
                flash(f"Company with ID {company_id} not found", 'error')
                return redirect(url_for('admin.manage_queue_permissions'))
                
            if not queue:
                print(f"Queue with ID {queue_id} not found")
                flash(f"Queue with ID {queue_id} not found", 'error')
                return redirect(url_for('admin.manage_queue_permissions'))
            
            # Check if permission already exists
            permission = db_session.query(CompanyQueuePermission).filter_by(
                company_id=company_id, queue_id=queue_id).first()
            
            print(f"Existing permission found: {permission is not None}")
            
            if not has_permission:
                # If no permission should be granted, delete existing permission if it exists
                if permission:
                    db_session.delete(permission)
                    db_session.commit()
                    flash('Permission removed successfully', 'success')
                    print("Permission removed")
            else:
                if permission:
                    # Update existing permission
                    permission.can_view = can_view
                    permission.can_create = can_create
                    print(f"Updated permission - can_view: {can_view}, can_create: {can_create}")
                else:
                    # Create new permission
                    permission = CompanyQueuePermission(
                        company_id=company_id,
                        queue_id=queue_id,
                        can_view=can_view,
                        can_create=can_create
                    )
                    db_session.add(permission)
                    print(f"Created new permission - can_view: {can_view}, can_create: {can_create}")
            
                db_session.commit()
                flash('Queue permissions updated successfully', 'success')
                print("Permission saved successfully")
            
            return jsonify({"status": "success", "message": "Permission updated successfully"})
            
        except Exception as e:
            db_session.rollback()
            print(f"ERROR: {str(e)}")
            print(f"Stack trace: {traceback.format_exc()}")
            flash(f'Error updating queue permissions: {str(e)}', 'error')
            return jsonify({"status": "error", "message": str(e)}), 500
        finally:
            db_session.close()
    
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        print(f"Stack trace: {traceback.format_exc()}")
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
            print(f"Error fetching Firecrawl keys: {str(e)}")
        
        # Get the current API key from the environment or config
        current_api_key = os.environ.get('FIRECRAWL_API_KEY') or current_app.config.get('FIRECRAWL_API_KEY', 'Not set')

        # Get version information
        version_info = get_full_version_info()

        return render_template('admin/system_config.html', 
                             user=user,
                             firecrawl_keys=firecrawl_keys,
                             active_key=active_key,
                             current_api_key=current_api_key,
                             version_info=version_info,
                             config=current_app.config)
    except Exception as e:
        db_session.rollback()
        flash(f'Error loading system configuration: {str(e)}', 'error')
        return redirect(url_for('main.index'))
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
            print(f"Error updating key in database (continuing anyway): {str(e)}")
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