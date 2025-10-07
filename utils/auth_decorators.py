from functools import wraps
from flask import session, redirect, url_for, flash, abort, request
from flask_login import current_user
from models.enums import UserType

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            # Preserve the current URL so user can be redirected back after login
            return redirect(url_for('auth.login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('user_id'):
            return redirect(url_for('auth.login', next=request.url))
        user_type = session.get('user_type')
        admin_types = [UserType.SUPER_ADMIN.value, UserType.DEVELOPER.value, UserType.COUNTRY_ADMIN.value]
        if not user_type or user_type not in admin_types:
            flash('You do not have permission to access this page')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated_function

def super_admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.user_type not in [UserType.SUPER_ADMIN, UserType.DEVELOPER]:
            abort(403)
        return f(*args, **kwargs)
    return decorated_function

def check_country_access(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if current_user.user_type in [UserType.SUPER_ADMIN, UserType.DEVELOPER]:
            return f(*args, **kwargs)
        elif current_user.user_type == UserType.COUNTRY_ADMIN:
            # Add logic to check if the requested data belongs to the admin's country
            country = kwargs.get('country')
            if country and country != current_user.assigned_country:
                abort(403)
        elif current_user.user_type == UserType.SUPERVISOR:
            # Supervisors can only view data
            if request.method not in ['GET']:
                abort(403)
        return f(*args, **kwargs)
    return decorated_function

def permission_required(permission_name):
    """Decorator to check if user has a specific permission"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('auth.login', next=request.url))
            
            # Check if user has the required permission
            if not hasattr(current_user, 'permissions') or not current_user.permissions:
                abort(403)
            
            if not hasattr(current_user.permissions, permission_name):
                abort(403)
            
            if not getattr(current_user.permissions, permission_name):
                abort(403)
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator 