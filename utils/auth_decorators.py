from functools import wraps
from flask import session, redirect, url_for, flash
from models.user import UserType

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('user_id'):
            return redirect(url_for('auth.login'))
        user_type = session.get('user_type')
        admin_types = [UserType.ADMIN.value, UserType.SUPER_ADMIN.value, 'Admin', 'Super Admin']
        if not user_type or user_type not in admin_types:
            flash('You do not have permission to access this page')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated_function 