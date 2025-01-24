from functools import wraps
from flask import session, redirect, url_for, flash

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
        if user_type not in ['admin', 'super_admin', 'ADMIN', 'SUPER_ADMIN']:
            flash('You do not have permission to access this page')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated_function 