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
            import logging

            if not current_user.is_authenticated:
                return redirect(url_for('auth.login', next=request.url))

            # Super admins and developers bypass all permission checks
            # Use the property methods for reliable checking
            logging.info(f"[PERMISSION] Checking permission '{permission_name}' for user {getattr(current_user, 'username', 'unknown')}")
            logging.info(f"[PERMISSION] User type: {getattr(current_user, 'user_type', 'unknown')}")
            logging.info(f"[PERMISSION] is_super_admin: {getattr(current_user, 'is_super_admin', False)}")
            logging.info(f"[PERMISSION] is_developer: {getattr(current_user, 'is_developer', False)}")

            if hasattr(current_user, 'is_super_admin') and current_user.is_super_admin:
                logging.info(f"[PERMISSION] ALLOWED - User is super admin")
                return f(*args, **kwargs)
            if hasattr(current_user, 'is_developer') and current_user.is_developer:
                logging.info(f"[PERMISSION] ALLOWED - User is developer")
                return f(*args, **kwargs)

            # Check if user has the required permission
            if not hasattr(current_user, 'permissions') or not current_user.permissions:
                logging.warning(f"[PERMISSION] DENIED - User has no permissions object")
                abort(403)

            if not hasattr(current_user.permissions, permission_name):
                logging.warning(f"[PERMISSION] DENIED - Permission '{permission_name}' does not exist")
                abort(403)

            if not getattr(current_user.permissions, permission_name):
                logging.warning(f"[PERMISSION] DENIED - Permission '{permission_name}' is False")
                abort(403)

            logging.info(f"[PERMISSION] ALLOWED - User has permission '{permission_name}'")
            return f(*args, **kwargs)
        return decorated_function
    return decorator 