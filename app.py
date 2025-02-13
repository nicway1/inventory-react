from flask import Flask, redirect, url_for, render_template, session, jsonify
from flask_cors import CORS
from flask_login import LoginManager, current_user
from routes.inventory import inventory_bp
from routes.auth import auth_bp
from routes.tickets import tickets_bp
from routes.shipments import shipments_bp
from routes.users import users_bp
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
from models.user import User, UserType, Country
from utils.db_manager import DatabaseManager
from utils.email_sender import mail
import os
import logging
from routes.main import main_bp
from flask_wtf.csrf import CSRFProtect
from database import init_db, engine, SessionLocal
from werkzeug.security import generate_password_hash

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Create data directory if it doesn't exist
os.makedirs('data', exist_ok=True)

app = Flask(__name__)

# Configure Flask app
app.config.update(
    SECRET_KEY=os.environ.get('SECRET_KEY', 'dev-key-please-change'),
    SESSION_COOKIE_SECURE=False,  # Set to False for development without HTTPS
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    PERMANENT_SESSION_LIFETIME=1800,  # 30 minutes
    SQLALCHEMY_DATABASE_URI=os.environ.get('DATABASE_URL', 'sqlite:///inventory.db'),
    SQLALCHEMY_TRACK_MODIFICATIONS=False,
    WTF_CSRF_TIME_LIMIT=None,  # Disable CSRF token expiration
    WTF_CSRF_CHECK_DEFAULT=False,  # Disable CSRF check by default
    WTF_CSRF_SSL_STRICT=False,  # Allow CSRF tokens over HTTP
    # Email configuration for Gmail SMTP
    MAIL_SERVER=os.environ.get('MAIL_SERVER', 'smtp.gmail.com'),
    MAIL_PORT=int(os.environ.get('MAIL_PORT', '587')),
    MAIL_USE_TLS=True,
    MAIL_USERNAME=os.environ.get('MAIL_USERNAME', 'trueloginventory@gmail.com'),
    MAIL_PASSWORD=os.environ.get('MAIL_PASSWORD', 'lfve nald ymnl vrzf'),  # Gmail App Password
    MAIL_DEFAULT_SENDER=os.environ.get('MAIL_DEFAULT_SENDER', 'trueloginventory@gmail.com'),
    MAIL_DEBUG=True  # Enable debug mode
)

# Initialize CORS
CORS(app)

# Initialize CSRF protection
csrf = CSRFProtect(app)

# Initialize Flask-Mail
mail.init_app(app)

# Log mail configuration
logging.info("Mail Configuration:")
logging.info(f"MAIL_SERVER: {app.config['MAIL_SERVER']}")
logging.info(f"MAIL_PORT: {app.config['MAIL_PORT']}")
logging.info(f"MAIL_USE_TLS: {app.config['MAIL_USE_TLS']}")
logging.info(f"MAIL_USERNAME: {app.config['MAIL_USERNAME']}")
logging.info(f"MAIL_DEFAULT_SENDER: {app.config['MAIL_DEFAULT_SENDER']}")

# Exempt certain routes from CSRF protection
csrf.exempt(inventory_bp)

# Initialize database
db = SQLAlchemy(app)

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
        db_session = SessionLocal()
        user = db_session.query(User).get(int(user_id))
        db_session.close()
        return user
    except (ValueError, TypeError):
        return None

# Register blueprints with proper URL prefixes
app.register_blueprint(main_bp, url_prefix='/')
app.register_blueprint(auth_bp, url_prefix='/auth')
app.register_blueprint(inventory_bp, url_prefix='/inventory')
app.register_blueprint(tickets_bp, url_prefix='/tickets')
app.register_blueprint(shipments_bp, url_prefix='/shipments')
app.register_blueprint(users_bp, url_prefix='/users')
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

@app.route('/')
def hello():
    return 'Hello, World!'

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
            admin_user = db.query(User).filter_by(username='admin').first()
            if not admin_user:
                print("Creating admin user...")
                admin_user = User(
                    username='admin',
                    password_hash=generate_password_hash('admin123'),
                    email='admin@lunacomputer.com',
                    user_type=UserType.SUPER_ADMIN,
                    company_id=default_company.id
                )
                db.add(admin_user)
                db.commit()
                print(f"Admin user created successfully: {admin_user.username}")
            else:
                print(f"Admin user already exists: {admin_user.username}")
        finally:
            db.close()

    # Try different ports if 5001 is in use
    port = 5001
    while port < 5010:  # Try ports 5001-5009
        try:
            app.run(debug=True, host='0.0.0.0', port=port)
            break
        except OSError:
            print(f"Port {port} is in use, trying {port + 1}")
            port += 1 