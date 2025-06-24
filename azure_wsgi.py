import os
import sys
import logging

# Configure logging for Azure
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add the project directory to the Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# Azure-specific environment configuration
os.environ.setdefault('FLASK_ENV', 'production')
os.environ.setdefault('SECRET_KEY', os.environ.get('SECRET_KEY', 'change-this-in-production'))

# SQLite database configuration for Azure
# Use a relative path that works with Azure's file system
database_path = os.path.join(project_root, 'inventory.db')
os.environ.setdefault('DATABASE_URL', f'sqlite:///{database_path}')

# Email configuration - use environment variables set in Azure
os.environ.setdefault('MAIL_SERVER', os.environ.get('MAIL_SERVER', 'smtp.gmail.com'))
os.environ.setdefault('MAIL_PORT', os.environ.get('MAIL_PORT', '587'))
os.environ.setdefault('MAIL_USE_TLS', os.environ.get('MAIL_USE_TLS', 'True'))
os.environ.setdefault('MAIL_USERNAME', os.environ.get('MAIL_USERNAME', ''))
os.environ.setdefault('MAIL_PASSWORD', os.environ.get('MAIL_PASSWORD', ''))
os.environ.setdefault('MAIL_DEFAULT_SENDER', os.environ.get('MAIL_DEFAULT_SENDER', ''))

# Ensure uploads directory exists
uploads_dir = os.path.join(project_root, 'uploads')
os.makedirs(uploads_dir, exist_ok=True)

try:
    # Import and create the Flask application
    from app import create_app
    application = create_app()
    
    logger.info("✅ Azure WSGI application initialized successfully")
    logger.info(f"📊 Database path: {database_path}")
    logger.info(f"📁 Project root: {project_root}")
    
except Exception as e:
    logger.error(f"❌ Failed to initialize application: {e}")
    raise

# For Azure App Service
if __name__ == "__main__":
    application.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8000))) 