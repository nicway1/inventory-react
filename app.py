from flask import Flask, redirect, url_for, render_template, session, jsonify, request
from flask_cors import CORS
from flask_login import LoginManager, current_user
from flask_wtf.csrf import CSRFProtect, CSRFError
from dotenv import load_dotenv
import logging

# Set up logging for this module
logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()
from routes.inventory import inventory_bp
from routes.auth import auth_bp
from routes.tickets import tickets_bp
from routes.shipments import shipments_bp
from routes.users import users_bp
from routes.admin import admin_bp
from routes.api_simple import api_bp
from routes.mobile_api import mobile_api_bp
# from routes.json_api import json_api_bp  # Temporarily disabled to avoid conflicts
from routes.inventory_api import inventory_api_bp
from routes.search_api import search_api_bp
from routes.assets import assets_bp
from routes.documents import documents_bp
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
from routes.main import main_bp
from routes.development import development_bp
from flask_wtf.csrf import CSRFProtect, CSRFError
from database import init_db, engine, SessionLocal
from werkzeug.security import generate_password_hash
from utils.auth import safe_generate_password_hash
from sqlalchemy.orm import joinedload
from flask_migrate import Migrate
from routes.intake import intake_bp
from routes.reports import reports_bp
# Import category blueprints
from routes.ticket_categories.asset_checkout_claw import asset_checkout_claw_bp
from routes.ticket_categories.asset_return_claw import asset_return_claw_bp
from routes.knowledge import knowledge_bp
from routes.feedback import feedback_bp

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
        PERMANENT_SESSION_LIFETIME=7200,  # 2 hours
        SQLALCHEMY_DATABASE_URI=os.environ.get('DATABASE_URL', 'sqlite:////home/nicway2/inventory/inventory.db'),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        WTF_CSRF_TIME_LIMIT=None,  # Disable CSRF token expiration
        WTF_CSRF_CHECK_DEFAULT=True,  # Enable CSRF check by default
        WTF_CSRF_SSL_STRICT=False,  # Allow CSRF tokens over HTTP
        # Microsoft 365 OAuth2 configuration (Primary)
        MS_CLIENT_ID=os.environ.get('MS_CLIENT_ID'),
        MS_CLIENT_SECRET=os.environ.get('MS_CLIENT_SECRET'),
        MS_TENANT_ID=os.environ.get('MS_TENANT_ID'),
        MS_FROM_EMAIL=os.environ.get('MS_FROM_EMAIL'),
        USE_OAUTH2_EMAIL=os.environ.get('USE_OAUTH2_EMAIL', 'false').lower() == 'true',
        
        # Gmail SMTP configuration (Fallback)
        MAIL_SERVER='smtp.gmail.com',
        MAIL_PORT=587,
        MAIL_USE_TLS=True,
        MAIL_USE_SSL=False,
        MAIL_USERNAME='trueloginventory@gmail.com',  # Your Gmail address
        MAIL_PASSWORD='lfve nald ymnl vrzf',  # Your Gmail app password
        MAIL_DEFAULT_SENDER='trueloginventory@gmail.com',  # Your Gmail address
        MAIL_MAX_EMAILS=None,  # Remove limit for production use
        MAIL_SUPPRESS_SEND=False,
        MAIL_ASCII_ATTACHMENTS=False,
        MAIL_DEBUG=True,  # Enable debug mode
        # Additional SMTP configuration for better compatibility
        MAIL_TIMEOUT=30,  # Increase timeout
    )

    # Initialize CORS
    CORS(app)

    # Initialize CSRF protection
    csrf = CSRFProtect(app)

    @app.errorhandler(CSRFError)
    def handle_csrf_error(e):
        # Check if this is an API request
        if request.path.startswith('/api/'):
            return jsonify({
                'error': {
                    'code': 'CSRF_ERROR',
                    'message': 'CSRF token validation failed',
                    'details': str(e)
                }
            }), 400
        
        logging.error(f"CSRF Error: {str(e)}")
        return render_template('error.html', 
                             error="CSRF token validation failed. Please try again.",
                             details=str(e)), 400

    # Initialize Flask-Mail
    mail.init_app(app)
    
    # Initialize OAuth2 Mail (for Microsoft Graph API)
    # oauth2_mail.init_app(app)

    # Log mail configuration
    if app.config.get('USE_OAUTH2_EMAIL'):
        logging.info("Mail Configuration: Microsoft 365 OAuth2")
        logging.info(f"MS_CLIENT_ID: {app.config.get('MS_CLIENT_ID', 'Not set')}")
        logging.info(f"MS_TENANT_ID: {app.config.get('MS_TENANT_ID', 'Not set')}")
        logging.info(f"MS_FROM_EMAIL: {app.config.get('MS_FROM_EMAIL', 'Not set')}")
        logging.info(f"USE_OAUTH2_EMAIL: {app.config.get('USE_OAUTH2_EMAIL')}")
    else:
        logging.info("Mail Configuration: Gmail SMTP (Fallback)")
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
    app.register_blueprint(mobile_api_bp)
    app.register_blueprint(inventory_api_bp)
    app.register_blueprint(search_api_bp)
    # app.register_blueprint(json_api_bp)  # Temporarily disabled
    
    # Exempt API blueprints from CSRF protection
    csrf.exempt(api_bp)
    csrf.exempt(mobile_api_bp)
    csrf.exempt(search_api_bp)
    csrf.exempt(inventory_api_bp)
    csrf.exempt(reports_bp)  # Exempt reports API endpoints
    # csrf.exempt(json_api_bp)  # Temporarily disabled
    app.register_blueprint(intake_bp)
    app.register_blueprint(assets_bp)
    app.register_blueprint(documents_bp)
    app.register_blueprint(debug_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(development_bp, url_prefix='/development')
    # Register category blueprints
    app.register_blueprint(asset_checkout_claw_bp) # Prefix is defined in the blueprint file
    app.register_blueprint(asset_return_claw_bp)   # Prefix is defined in the blueprint file
    app.register_blueprint(knowledge_bp)
    app.register_blueprint(feedback_bp)

    @app.context_processor
    def utility_processor():
        """Make current_user available in all templates"""
        return dict(current_user=current_user)

    # Add custom template filters
    @app.template_filter('nl2br')
    def nl2br_filter(text):
        """Template filter to convert newlines to <br> tags"""
        if not text:
            return ""
        import re
        return re.sub(r'\r?\n', '<br>', str(text))

    # Add timezone filter for templates
    @app.template_filter('singapore_time')
    def singapore_time_filter(dt):
        """Template filter to convert UTC datetime to Singapore time"""
        from utils.timezone_utils import format_singapore_time
        return format_singapore_time(dt)

    @app.template_filter('from_json')
    def from_json_filter(json_string):
        """Template filter to parse JSON string"""
        import json
        try:
            return json.loads(json_string) if json_string else []
        except:
            return []

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
    logger.info("Starting application...")
    
    # Initialize database and create tables
    with app.app_context():
        logger.info("Initializing database...")
        init_db()
        
        # Create default company if it doesn't exist
        db = SessionLocal()
        try:
            default_company = db.query(Company).filter_by(name="LunaComputer").first()
            if not default_company:
                logger.info("\nCreating default company...")
                default_company = Company(
                    name="LunaComputer",
                    address="Default Address"
                )
                db.add(default_company)
                db.commit()
                logger.info("Default company created")
            
            # Create default admin user if it doesn't exist
            logger.info("\nChecking for admin user...")
            admin_user = db.query(User).filter_by(username='admin').first()
            if not admin_user:
                logger.info("Creating admin user...")
                admin_user = User(
                    username='admin',
                    password_hash=safe_generate_password_hash('admin123'),
                    email='admin@lunacomputer.com',
                    user_type=UserType.SUPER_ADMIN,
                    company_id=default_company.id
                )
                db.add(admin_user)
                db.commit()
                logger.info("Admin user created successfully: {admin_user.username}")
            else:
                logger.info("Admin user already exists: {admin_user.username}")
        finally:
            db.close()

    # Try different ports if 5001 is in use
    port = 5009
    while port < 5010:  # Try ports 5001-5009
        try:
            app.run(debug=True, host='127.0.0.1', port=port)
            break
        except OSError:
            logger.info("Port {port} is in use, trying {port + 1}")
            port += 1