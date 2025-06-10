from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from flask import session, redirect, url_for, flash

def safe_generate_password_hash(password):
    """Generate password hash using pbkdf2:sha256 method for compatibility"""
    return generate_password_hash(password, method='pbkdf2:sha256')

def safe_check_password_hash(password_hash, password):
    """Check password hash - compatible with both pbkdf2 and other methods"""
    return check_password_hash(password_hash, password)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page')
            return redirect(url_for('auth.login'))
        
        user = db_manager.get_user(session['user_id'])
        if user.user_type not in [UserType.ADMIN, UserType.SUPER_ADMIN]:
            flash('You do not have permission to access this page')
            return redirect(url_for('main.index'))
            
        return f(*args, **kwargs)
    return decorated_function 