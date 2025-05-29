from flask import Flask, redirect, url_for, render_template, session, jsonify
from flask_cors import CORS
from flask_login import LoginManager, current_user
from routes.inventory import inventory_bp
from routes.auth import auth_bp
from routes.tickets import tickets_bp
from routes.shipments import shipments_bp
from routes.users import users_bp
from routes.admin import admin_bp
from routes.api import api_bp
from routes.assets import assets_bp
from routes.debug_routes import debug_bp
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
from models.permission import Permission
from utils.db_manager import DatabaseManager
from utils.email_sender import mail
# from utils.oauth2_email_sender import oauth2_mail
import os
import logging
from routes.main import main_bp
from flask_wtf.csrf import CSRFProtect, CSRFError
from database import init_db, engine, SessionLocal
from werkzeug.security import generate_password_hash
from sqlalchemy.orm import joinedload
from flask_migrate import Migrate
from routes.intake import intake_bp
# Import category blueprints
from routes.ticket_categories.asset_checkout_claw import asset_checkout_claw_bp
from routes.ticket_categories.asset_return_claw import asset_return_claw_bp

# Add permissions property to User model for Flask-Login
# User.permissions = property(lambda self: self.get_permissions)

# Initialize DatabaseManager at module level
db_manager = DatabaseManager()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Create data directory if it doesn't exist
os.makedirs('data', exist_ok=True)

def create_app():
    app = Flask(__name__)

    # Configure Flask app
    app.config.update(
        SECRET_KEY=os.environ.get('SECRET_KEY', 'dev-key-please-change'),
        SESSION_COOKIE_SECURE=False,  # Set to False for development without HTTPS
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE='Lax',
        PERMANENT_SESSION_LIFETIME=1800,  # 30 minutes
        SQLALCHEMY_DATABASE_URI=os.environ.get('DATABASE_URL', 'sqlite:////home/nicway2/inventory/inventory.db'),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        WTF_CSRF_TIME_LIMIT=None,  # Disable CSRF token expiration
        WTF_CSRF_CHECK_DEFAULT=True,  # Enable CSRF check by default
        WTF_CSRF_SSL_STRICT=False,  # Allow CSRF tokens over HTTP
        # Email configuration for Outlook/Office 365 SMTP (Traditional method)
        MAIL_SERVER='smtp.office365.com',
        MAIL_PORT=587,
        MAIL_USE_TLS=True,
        MAIL_USE_SSL=False,
        MAIL_USERNAME='your-company-email@yourcompany.com',  # Replace with your actual company email
        MAIL_PASSWORD='your-app-password-from-outlook',  # Use App Password (not regular password) for 2FA accounts
        MAIL_DEFAULT_SENDER='your-company-email@yourcompany.com',  # Replace with your actual company email
        MAIL_MAX_EMAILS=1,  # Limit for testing
        MAIL_SUPPRESS_SEND=False,
        MAIL_ASCII_ATTACHMENTS=False,
        MAIL_DEBUG=True,  # Enable debug mode
        
        # OAuth2 configuration for Microsoft Graph API (Recommended for corporate accounts)
        OAUTH2_CLIENT_ID=os.environ.get('OAUTH2_CLIENT_ID', 'your-azure-client-id'),
        OAUTH2_CLIENT_SECRET=os.environ.get('OAUTH2_CLIENT_SECRET', 'your-azure-client-secret'),
        OAUTH2_TENANT_ID=os.environ.get('OAUTH2_TENANT_ID', 'your-azure-tenant-id'),
        OAUTH2_DEFAULT_SENDER=os.environ.get('OAUTH2_DEFAULT_SENDER', 'your-company-email@yourcompany.com'),
        USE_OAUTH2_EMAIL=os.environ.get('USE_OAUTH2_EMAIL', 'True').lower() == 'true'  # Set to False to use SMTP
    )

    # Initialize CORS
    CORS(app)

    # Initialize CSRF protection
    csrf = CSRFProtect(app)

    @app.errorhandler(CSRFError)
    def handle_csrf_error(e):
        logging.error(f"CSRF Error: {str(e)}")
        return render_template('error.html', 
                             error="CSRF token validation failed. Please try again.",
                             details=str(e)), 400

    # Initialize Flask-Mail
    mail.init_app(app)
    
    # Initialize OAuth2 Mail (for Microsoft Graph API)
    # oauth2_mail.init_app(app)

    # Log mail configuration
    logging.info("Mail Configuration:")
    logging.info(f"MAIL_SERVER: {app.config['MAIL_SERVER']}")
    logging.info(f"MAIL_PORT: {app.config['MAIL_PORT']}")
    logging.info(f"MAIL_USE_TLS: {app.config['MAIL_USE_TLS']}")
    logging.info(f"MAIL_USERNAME: {app.config['MAIL_USERNAME']}")
    logging.info(f"MAIL_DEFAULT_SENDER: {app.config['MAIL_DEFAULT_SENDER']}")

    # Initialize database
    db = SQLAlchemy(app)
    migrate = Migrate(app, db)

    # Initialize Flask-Login
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message_category = 'info'

    @login_manager.user_loader
    def load_user(user_id):
        """Load user from database by ID"""
        if user_id is None:
            return None
        try:
            # Use db_manager to handle permission retrieval correctly
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
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(api_bp)
    app.register_blueprint(intake_bp)
    app.register_blueprint(assets_bp)
    app.register_blueprint(debug_bp)
    # Register category blueprints
    app.register_blueprint(asset_checkout_claw_bp) # Prefix is defined in the blueprint file
    app.register_blueprint(asset_return_claw_bp)   # Prefix is defined in the blueprint file

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

    @app.route('/where-we-operate')
    def where_we_operate():
        """Renders the map page, accessible without login."""
        return render_template('maps.html')

    return app

app = create_app()

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
            app.run(debug=True, host='127.0.0.1', port=port)
            break
        except OSError:
            print(f"Port {port} is in use, trying {port + 1}")
            port += 1