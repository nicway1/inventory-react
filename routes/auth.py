from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from utils.user_store import UserStore
from utils.auth_decorators import admin_required
from utils.snipeit_client import SnipeITClient
from utils.db_manager import DatabaseManager
from flask_login import login_required, current_user, login_user, logout_user
from datetime import datetime
from models.user import User
from models.permission import Permission
import logging

# Set up logging for this module
logger = logging.getLogger(__name__)


auth_bp = Blueprint('auth', __name__)
user_store = UserStore()
snipe_client = SnipeITClient()
db_manager = DatabaseManager()

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if not username or not password:
            flash('Please provide both username and password')
            return render_template('auth/login.html')
        
        try:
            # Use DatabaseManager to get user with permissions
            with db_manager as db:
                user = db.get_user_by_username(username)
                if user and user.check_password(password):
                    # Get permission record for this user's type
                    permission = db.session.query(Permission).filter_by(user_type=user.user_type).first()
                    
                    if not permission:
                        # Create default permissions if none exist
                        default_permissions = Permission.get_default_permissions(user.user_type)
                        permission = Permission(user_type=user.user_type, **default_permissions)
                        db.session.add(permission)
                    
                    login_user(user)
                    session['user_id'] = user.id
                    session['user_type'] = user.user_type.value
                    session['username'] = user.username
                    session['user_theme'] = user.theme_preference or 'light'
                    
                    # Update last login time
                    user.last_login = datetime.utcnow()
                    
                    return redirect(url_for('main.index'))
                
                flash('Invalid username or password')
        except Exception as e:
            flash('An error occurred during login')
            logger.info("Login error: {str(e)}")
            logging.error(f"Login error: {str(e)}", exc_info=True)
    
    return render_template('auth/login.html')

@auth_bp.route('/logout')
def logout():
    logout_user()
    session.clear()
    return redirect(url_for('auth.login'))

@auth_bp.route('/users')
@admin_required
def list_users():
    users = user_store.get_all_users()
    return render_template('auth/users.html', users=users)

@auth_bp.route('/users/new', methods=['GET', 'POST'])
@admin_required
def create_user():
    logger.info("Accessing create_user route")  # Debug print
    
    if request.method == 'POST':
        logger.info("POST request received")  # Debug print
        logger.info("Form data:", request.form)  # Debug print
        
        username = request.form.get('username')
        password = request.form.get('password')
        user_type = request.form.get('user_type')
        company = request.form.get('company')
        role = request.form.get('role')
        
        logger.info("Creating user: {username}, type: {user_type}, company: {company}, role: {role}")  # Debug print
        
        user = user_store.create_user(
            username=username,
            password=password,
            user_type=user_type,
            company=company,
            role=role
        )
        
        if user:
            logger.info("User created successfully: {user.id}")  # Debug print
            flash('User created successfully')
            return redirect(url_for('auth.list_users'))
        else:
            logger.info("User creation failed")  # Debug print
            flash('Failed to create user')
            return redirect(url_for('auth.create_user'))
    
    try:
        companies = snipe_client.get_companies()
        logger.info("Retrieved companies: {companies}")  # Debug print
    except Exception as e:
        logger.info("Error fetching companies: {e}")  # Debug print
        companies = []
    
    return render_template(
        'auth/create_user.html',
        companies=companies,
        user_types=['user', 'admin', 'super_admin']
    )

@auth_bp.route('/register', methods=['POST'])
def register():
    username = request.form.get('username')
    password = request.form.get('password')
    company = request.form.get('company')
    role = request.form.get('role')
    
    user = user_store.create_user(
        username=username,
        password=password,
        company=company,
        role=role
    )
    
    if user:
        flash('Registration successful')
        return redirect(url_for('auth.login'))
    else:
        flash('Username already exists')
        return redirect(url_for('auth.register'))

@auth_bp.route('/profile')
@login_required
def profile():
    # Get a fresh user object from the database with company relationship loaded
    user = db_manager.get_user_by_id(current_user.id)
    return render_template('profile.html', user=user)

@auth_bp.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    """Edit user profile"""
    # Get a fresh user object from the database with company relationship loaded
    user = db_manager.get_user_by_id(current_user.id)
    
    if request.method == 'POST':
        # Get form data
        user_data = {
            'username': request.form.get('username'),
            'email': request.form.get('email')
        }
        
        try:
            db_manager.update_user(current_user.id, user_data)
            # Update session with new username
            session['username'] = user_data['username']
            flash('Profile updated successfully', 'success')
            return redirect(url_for('auth.profile'))
        except Exception as e:
            flash(f'Error updating profile: {str(e)}', 'error')
            
    return render_template('edit_profile.html', user=user)

@auth_bp.route('/profile/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    """Change user password"""
    if request.method == 'POST':
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        if not current_user.check_password(current_password):
            flash('Current password is incorrect', 'error')
            return redirect(url_for('auth.change_password'))
            
        if new_password != confirm_password:
            flash('New passwords do not match', 'error')
            return redirect(url_for('auth.change_password'))
            
        try:
            db_manager.update_user_password(current_user.id, new_password)
            flash('Password changed successfully', 'success')
            return redirect(url_for('auth.profile'))
        except Exception as e:
            flash(f'Error changing password: {str(e)}', 'error')
            
    return render_template('change_password.html') 