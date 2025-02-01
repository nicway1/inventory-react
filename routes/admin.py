from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from utils.auth_decorators import admin_required
from utils.snipeit_client import SnipeITClient
from utils.db_manager import DatabaseManager
from models.user import UserType
from datetime import datetime

admin_bp = Blueprint('admin', __name__)
snipe_client = SnipeITClient()
db_manager = DatabaseManager()

@admin_bp.route('/settings')
@admin_required
def settings():
    """Admin settings page"""
    return render_template('admin/settings.html')

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
        company_data = {
            'name': request.form.get('name'),
            'contact_name': request.form.get('contact_name'),
            'contact_email': request.form.get('contact_email')
        }
        try:
            company = db_manager.create_company(company_data)
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
    company = db_manager.get_company(company_id)
    if not company:
        flash('Company not found', 'error')
        return redirect(url_for('admin.manage_companies'))

    if request.method == 'POST':
        company_data = {
            'name': request.form.get('name'),
            'contact_name': request.form.get('contact_name'),
            'contact_email': request.form.get('contact_email')
        }
        try:
            db_manager.update_company(company_id, company_data)
            flash('Company updated successfully', 'success')
            return redirect(url_for('admin.manage_companies'))
        except Exception as e:
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
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        company = request.form.get('company')
        role = request.form.get('role')
        user_type = request.form.get('user_type')

        # Validate input
        if not username or not password:
            flash('Username and password are required', 'error')
            return redirect(url_for('admin.create_user'))

        # Check if username already exists
        if db_manager.get_user_by_username(username):
            flash('Username already exists', 'error')
            return redirect(url_for('admin.create_user'))

        # Create user
        try:
            user_data = {
                'username': username,
                'password_hash': password,  # Will be hashed by db_manager
                'company': company,
                'role': role,
                'user_type': UserType.ADMIN if user_type == 'admin' else UserType.USER,
                'created_at': datetime.utcnow()
            }
            db_manager.create_user(user_data)
            flash('User created successfully', 'success')
            return redirect(url_for('admin.manage_users'))
        except Exception as e:
            flash(f'Error creating user: {str(e)}', 'error')
            return redirect(url_for('admin.create_user'))

    # GET request - show form
    # Get list of companies for the dropdown
    companies = db_manager.get_all_companies()
    return render_template('admin/create_user.html', companies=companies)

@admin_bp.route('/users/<int:user_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_user(user_id):
    user = db_manager.get_user(user_id)
    if not user:
        flash('User not found', 'error')
        return redirect(url_for('admin.manage_users'))

    if request.method == 'POST':
        username = request.form.get('username')
        company = request.form.get('company')
        role = request.form.get('role')
        user_type = request.form.get('user_type')
        new_password = request.form.get('new_password')

        # Update user data
        try:
            update_data = {
                'username': username,
                'company': company,
                'role': role,
                'user_type': UserType.ADMIN if user_type == 'admin' else UserType.USER
            }
            
            # Only update password if a new one is provided
            if new_password:
                update_data['password_hash'] = new_password

            db_manager.update_user(user_id, update_data)
            flash('User updated successfully', 'success')
            return redirect(url_for('admin.manage_users'))
        except Exception as e:
            flash(f'Error updating user: {str(e)}', 'error')

    companies = db_manager.get_all_companies()
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