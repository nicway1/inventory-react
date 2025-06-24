#!/usr/bin/env python3
import os
import sys
import logging

# Configure basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add the project directory to the Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

logger.info(f"🚀 Minimal WSGI starting")
logger.info(f"📁 Project root: {project_root}")
logger.info(f"🐍 Python version: {sys.version}")
logger.info(f"📋 Current working directory: {os.getcwd()}")

# Set basic environment variables
os.environ.setdefault('FLASK_ENV', 'production')
os.environ.setdefault('SECRET_KEY', 'minimal-test-key')

# Set SQLite database path
database_path = os.path.join(project_root, 'inventory.db')
os.environ.setdefault('DATABASE_URL', f'sqlite:///{database_path}')

logger.info(f"📊 Database path: {database_path}")
logger.info(f"🔍 Database exists: {os.path.exists(database_path)}")

# List files in project root
try:
    files = os.listdir(project_root)
    logger.info(f"📁 Files in project root: {files[:10]}...")  # Show first 10 files
except Exception as e:
    logger.error(f"❌ Could not list project files: {e}")

# Try to import Flask first
try:
    logger.info("📦 Testing Flask import...")
    from flask import Flask
    logger.info("✅ Flask imported successfully")
except ImportError as e:
    logger.error(f"❌ Flask import failed: {e}")
    # Create a minimal WSGI application for testing
    def application(environ, start_response):
        status = '200 OK'
        headers = [('Content-type', 'text/plain')]
        start_response(status, headers)
        return [b'Flask import failed - check dependencies']

# Try to import our app
try:
    logger.info("📦 Testing app import...")
    from app import create_app
    logger.info("✅ App imported successfully")
    
    logger.info("🏗️ Creating Flask application...")
    application = create_app()
    logger.info("✅ Flask application created successfully")
    
except ImportError as e:
    logger.error(f"❌ App import failed: {e}")
    logger.error(f"📋 Import error details: {str(e)}")
    
    # Create a minimal Flask app for testing
    try:
        from flask import Flask
        application = Flask(__name__)
        
        @application.route('/')
        def hello():
            return f"Minimal WSGI working! Project root: {project_root}"
        
        @application.route('/health')
        def health():
            return {"status": "ok", "message": "Basic Flask working"}
            
        logger.info("✅ Created minimal Flask application")
    except Exception as e:
        logger.error(f"❌ Even minimal Flask failed: {e}")
        
except Exception as e:
    logger.error(f"❌ Unexpected error: {e}")
    import traceback
    logger.error(f"📋 Full traceback: {traceback.format_exc()}")

logger.info("🎯 WSGI setup complete")

# For debugging
if __name__ == "__main__":
    try:
        application.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8000)), debug=True)
    except Exception as e:
        logger.error(f"❌ Failed to run application: {e}")
        print(f"Error: {e}") 