from flask import Flask, redirect, url_for, render_template, session, jsonify
from flask_cors import CORS
from flask_login import LoginManager, current_user
from routes.inventory import inventory_bp
from routes.auth import auth_bp
from routes.tickets import tickets_bp
from routes.shipments import shipments_bp
from routes.users import users_bp
from routes.data_loader import data_loader_bp
from routes.admin import admin_bp
from utils.auth_decorators import login_required
from utils.store_instances import (
    user_store,
    activity_store,
    ticket_store,
    inventory_store,
    queue_store,
    snipe_client,
    shipment_store
)
from flask_sqlalchemy import SQLAlchemy
from models.base import Base
from models.company import Company
from utils.db_manager import DatabaseManager
import os
from models.user import UserType
from routes.main import main_bp
from flask_wtf.csrf import CSRFProtect
from database import init_db, engine, SessionLocal
from werkzeug.security import generate_password_hash

# Create data directory if it doesn't exist
os.makedirs('data', exist_ok=True)

app = Flask(__name__)

# Configure Flask app
app.config.update(
    SECRET_KEY=os.urandom(24),
    SESSION_COOKIE_SECURE=False,  # Set to True in production with HTTPS
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    PERMANENT_SESSION_LIFETIME=1800,  # 30 minutes
    SQLALCHEMY_DATABASE_URI='sqlite:///inventory.db',
    SQLALCHEMY_TRACK_MODIFICATIONS=False,
    WTF_CSRF_TIME_LIMIT=None,  # Disable CSRF token expiration
    WTF_CSRF_CHECK_DEFAULT=False,  # Disable CSRF check by default
    WTF_CSRF_SSL_STRICT=False  # Allow CSRF tokens over HTTP
)

# Initialize CORS
CORS(app)

# Initialize CSRF protection
csrf = CSRFProtect(app)

# Exempt certain routes from CSRF protection
csrf.exempt(inventory_bp)

# Initialize database
db = SQLAlchemy(app)
db_manager = DatabaseManager(app.config['SQLALCHEMY_DATABASE_URI'])

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'
login_manager.login_message_category = 'info'

@login_manager.user_loader
def load_user(user_id):
    if user_id is None:
        return None
    try:
        return db_manager.get_user(int(user_id))
    except (ValueError, TypeError):
        return None

# Register blueprints with proper URL prefixes
app.register_blueprint(main_bp, url_prefix='/')
app.register_blueprint(auth_bp, url_prefix='/auth')
app.register_blueprint(inventory_bp, url_prefix='/inventory')
app.register_blueprint(tickets_bp, url_prefix='/tickets')
app.register_blueprint(shipments_bp, url_prefix='/shipments')
app.register_blueprint(users_bp, url_prefix='/users')
app.register_blueprint(data_loader_bp, url_prefix='/data-loader')
app.register_blueprint(admin_bp, url_prefix='/admin')

@app.context_processor
def utility_processor():
    """Make current_user available in all templates"""
    return dict(current_user=current_user)

@app.route('/activity/<int:activity_id>/read', methods=['POST'])
@login_required
def mark_activity_read(activity_id):
    activity_store.mark_as_read(activity_id)
    return redirect(url_for('main.index'))

@app.route('/health')
def health_check():
    return jsonify({"status": "healthy"}), 200

if __name__ == '__main__':
    print("Starting application...")
    
    # Initialize database and create tables
    with app.app_context():
        print("Initializing database...")
        init_db()
        
        # Create default company if it doesn't exist
        db = SessionLocal()
        try:
            default_company = db.query(Company).filter_by(name="LunaComputer").first()
            if not default_company:
                print("\nCreating default company...")
                default_company = Company(
                    name="LunaComputer",
                    address="Default Address"
                )
                db.add(default_company)
                db.commit()
                print("Default company created")
            
            # Create default admin user if it doesn't exist
            print("\nChecking for admin user...")
            admin_user = db_manager.get_user_by_username('admin')
            if not admin_user:
                print("Creating admin user...")
                admin_data = {
                    'username': 'admin',
                    'password_hash': generate_password_hash('admin123'),
                    'email': 'admin@lunacomputer.com',
                    'user_type': UserType.SUPER_ADMIN,
                    'company_id': default_company.id
                }
                try:
                    admin_user = db_manager.create_user(admin_data)
                    print(f"Admin user created successfully: {admin_user.username}")
                except Exception as e:
                    print(f"Error creating admin user: {e}")
            else:
                print(f"Admin user already exists: {admin_user.username}")
        finally:
            db.close()

    app.run(debug=True, host='0.0.0.0', port=5001) 