from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash, current_app
from flask_login import current_user
from utils.auth_decorators import admin_required, super_admin_required
from utils.snipeit_client import SnipeITClient
from utils.db_manager import DatabaseManager
from models.user import User, UserType, Country
from models.permission import Permission
from datetime import datetime
from models.company import Company
import os
from werkzeug.utils import secure_filename
import uuid
from werkzeug.security import generate_password_hash
from database import SessionLocal

admin_bp = Blueprint('admin', __name__)
snipe_client = SnipeITClient()
db_manager = DatabaseManager()

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
    """Render the permissions management page"""
    db = SessionLocal()
    try:
        # Get all permissions
        permissions = db.query(Permission).all()
        
        # If no permissions exist, initialize them for each user type
        if not permissions:
            for user_type in UserType:
                default_permissions = Permission.get_default_permissions(user_type)
                permission = Permission(user_type=user_type, **default_permissions)
                db.add(permission)
            db.commit()
            permissions = db.query(Permission).all()
            
        return render_template('admin/permission_management.html', permissions=permissions)
    finally:
        db.close()

@admin_bp.route('/companies')
@admin_required
def manage_companies():
    """List all companies"""
    companies = db_manager.get_all_companies()
    return render_template('admin/companies.html', companies=companies)

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
    company = db_manager.get_company(company_id)
    if not company:
        flash('Company not found', 'error')
        return redirect(url_for('admin.manage_companies'))

    try:
        db_manager.delete_company(company_id)
        flash('Company deleted successfully', 'success')
    except Exception as e:
        flash(f'Error deleting company: {str(e)}', 'error')

    return redirect(url_for('admin.manage_companies'))

@admin_bp.route('/users')
@admin_required
def manage_users():
    users = db_manager.get_all_users()
    return render_template('admin/users.html', users=users)

@admin_bp.route('/users/create', methods=['GET', 'POST'])
@admin_required
def create_user():
    """Create a new user"""
    db_session = db_manager.get_session()
    companies = db_session.query(Company).all()

    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        company_id = request.form.get('company_id')
        user_type = request.form.get('user_type')
        assigned_country = request.form.get('assigned_country')

        try:
            from models.user import User, UserType, Country

            # Create user data dictionary
            user_data = {
                'username': username,
                'email': email,
                'password_hash': generate_password_hash(password),
                'company_id': company_id if company_id else None,
                'user_type': UserType[user_type]
            }

            # Add assigned country for Country Admin
            if user_type == 'COUNTRY_ADMIN':
                if not assigned_country:
                    flash('Country selection is required for Country Admin', 'error')
                    return render_template('admin/create_user.html', companies=companies)
                user_data['assigned_country'] = Country[assigned_country]

            user = User(**user_data)
            db_session.add(user)
            db_session.commit()
            flash('User created successfully', 'success')
            return redirect(url_for('admin.manage_users'))
        except Exception as e:
            db_session.rollback()
            flash(f'Error creating user: {str(e)}', 'error')
        finally:
            db_session.close()

    return render_template('admin/create_user.html', companies=companies)

@admin_bp.route('/users/<int:user_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_user(user_id):
    """Edit an existing user"""
    db_session = db_manager.get_session()
    user = db_session.query(User).get(user_id)
    if not user:
        flash('User not found', 'error')
        return redirect(url_for('admin.manage_users'))

    companies = db_session.query(Company).all()

    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        company_id = request.form.get('company_id')
        user_type = request.form.get('user_type')
        password = request.form.get('password')
        assigned_country = request.form.get('assigned_country')

        try:
            # Update basic user information
            user.username = username
            user.email = email
            user.company_id = company_id if company_id else None
            user.user_type = UserType[user_type]

            # Update password if provided
            if password:
                user.password_hash = generate_password_hash(password)

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
            flash(f'Error updating user: {str(e)}', 'error')
        finally:
            db_session.close()

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
    """Update user type permissions"""
    db = SessionLocal()
    try:
        # Get form data
        user_type = request.form.get('user_type')
        permissions_data = {}
        
        # Extract permission values from form
        for key in request.form:
            if key.startswith('can_'):
                permissions_data[key] = request.form.get(key) == 'on'
        
        # Update or create permission record
        permission = db.query(Permission).filter_by(user_type=user_type).first()
        if not permission:
            permission = Permission(user_type=user_type)
            db.add(permission)
        
        # Update permission attributes
        for key, value in permissions_data.items():
            setattr(permission, key, value)
        
        db.commit()
        flash('Permissions updated successfully', 'success')
        return redirect(url_for('admin.permission_management'))
    except Exception as e:
        db.rollback()
        flash(f'Error updating permissions: {str(e)}', 'error')
        return redirect(url_for('admin.permission_management'))
    finally:
        db.close()

@admin_bp.route('/permissions/reset/<user_type>')
@super_admin_required
def reset_permissions(user_type):
    """Reset permissions for a user type to default values"""
    db = SessionLocal()
    try:
        # Delete existing permissions
        db.query(Permission).filter_by(user_type=user_type).delete()
        
        # Get default permissions
        default_permissions = Permission.get_default_permissions(user_type)
        
        # Create new permission record with defaults
        permission = Permission(user_type=user_type, **default_permissions)
        db.add(permission)
        db.commit()
        
        flash('Permissions reset to default values', 'success')
        return redirect(url_for('admin.permission_management'))
    except Exception as e:
        db.rollback()
        flash(f'Error resetting permissions: {str(e)}', 'error')
        return redirect(url_for('admin.permission_management'))
    finally:
        db.close() 