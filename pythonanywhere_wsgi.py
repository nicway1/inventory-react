#!/usr/bin/env python3
"""
PythonAnywhere WSGI Configuration File
This file specifically handles the WSGI setup for PythonAnywhere hosting.
"""

import os
import sys
import logging

# Configure logging for debugging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add the project directory to the Python path
project_root = '/home/nicway2/mysite3'  # Update this path to your actual PythonAnywhere directory
sys.path.insert(0, project_root)

logger.info(f"🚀 PythonAnywhere WSGI starting")
logger.info(f"📁 Project root: {project_root}")
logger.info(f"🐍 Python version: {sys.version}")

# Force SQLite database configuration for PythonAnywhere
# This overrides any Azure PostgreSQL settings
os.environ['DATABASE_URL'] = f'sqlite:///{project_root}/inventory.db'
os.environ['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{project_root}/inventory.db'

# Set production environment
os.environ['FLASK_ENV'] = 'production'
os.environ['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'pythonanywhere-production-key-change-this')

# Email configuration - use environment variables if available
os.environ.setdefault('MAIL_SERVER', 'smtp.gmail.com')
os.environ.setdefault('MAIL_PORT', '587')
os.environ.setdefault('MAIL_USE_TLS', 'True')
os.environ.setdefault('MAIL_USERNAME', os.environ.get('MAIL_USERNAME', 'trueloginventory@gmail.com'))
os.environ.setdefault('MAIL_PASSWORD', os.environ.get('MAIL_PASSWORD', ''))
os.environ.setdefault('MAIL_DEFAULT_SENDER', os.environ.get('MAIL_DEFAULT_SENDER', 'trueloginventory@gmail.com'))

# Microsoft 365 OAuth2 configuration (if available)
os.environ.setdefault('MS_CLIENT_ID', os.environ.get('MS_CLIENT_ID', ''))
os.environ.setdefault('MS_CLIENT_SECRET', os.environ.get('MS_CLIENT_SECRET', ''))
os.environ.setdefault('MS_TENANT_ID', os.environ.get('MS_TENANT_ID', ''))
os.environ.setdefault('MS_FROM_EMAIL', os.environ.get('MS_FROM_EMAIL', ''))

# API Keys
os.environ.setdefault('FIRECRAWL_API_KEY', os.environ.get('FIRECRAWL_API_KEY', 'fc-9e1ffc308a01434582ece2625a2a0da7'))
os.environ.setdefault('TRACKINGMORE_API_KEY', os.environ.get('TRACKINGMORE_API_KEY', ''))

logger.info(f"📊 Database URL set to: {os.environ['DATABASE_URL']}")
logger.info(f"🔑 Secret key configured: {'Yes' if os.environ.get('SECRET_KEY') else 'Using default'}")

# Create necessary directories
uploads_dir = os.path.join(project_root, 'uploads')
os.makedirs(uploads_dir, exist_ok=True)
logger.info(f"📁 Uploads directory: {uploads_dir}")

try:
    logger.info("📦 Importing Flask application...")
    
    # Import and create the Flask application
    from app import create_app
    logger.info("✅ Successfully imported create_app")
    
    application = create_app()
    logger.info("✅ Flask application created successfully")
    
    # Initialize database in application context
    with application.app_context():
        logger.info("📊 Initializing database...")
        from database import init_db
        try:
            init_db()
            logger.info("✅ Database initialized successfully")
        except Exception as db_error:
            logger.error(f"⚠️ Database initialization warning: {db_error}")
            # Don't fail if database initialization has issues
    
    logger.info("✅ PythonAnywhere WSGI application ready")
    
except ImportError as e:
    logger.error(f"❌ Import error: {e}")
    logger.error(f"📋 Current working directory: {os.getcwd()}")
    logger.error(f"📋 Files in project root: {os.listdir(project_root) if os.path.exists(project_root) else 'Directory not found'}")
    
    # Create a minimal error application
    from flask import Flask
    application = Flask(__name__)
    
    @application.route('/')
    def error():
        return f"Import Error: {str(e)}<br>Check the error logs for details.", 500
        
except Exception as e:
    logger.error(f"❌ Failed to initialize application: {e}")
    logger.error(f"📋 Exception type: {type(e).__name__}")
    import traceback
    logger.error(f"📋 Full traceback: {traceback.format_exc()}")
    
    # Create a minimal error application
    from flask import Flask
    application = Flask(__name__)
    
    @application.route('/')
    def error():
        return f"Application Error: {str(e)}<br>Check the error logs for details.", 500

# For development testing
if __name__ == "__main__":
    application.run(debug=True) 