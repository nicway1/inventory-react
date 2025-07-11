import os
import sys
from flask import Flask
import logging

# Set up logging for this module
logger = logging.getLogger(__name__)


def create_app():
    # Ensure the project root is in the Python path
    project_root = os.path.dirname(os.path.abspath(__file__))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    app = Flask(__name__)
    app.secret_key = 'your-secret-key'  # Make sure you have a secret key set
    
    # Import blueprints here to avoid circular imports
    from routes.inventory import inventory_bp
    from routes.tickets import tickets_bp
    from routes.auth import auth_bp
    
    # Register blueprints with URL prefixes
    app.register_bluelogger.info(inventory_bp, url_prefix='/inventory')
    app.register_bluelogger.info(tickets_bp, url_prefix='/tickets')
    app.register_bluelogger.info(auth_bp, url_prefix='/auth')
    
    return app 