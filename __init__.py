from flask import Flask
from routes.inventory import inventory_bp
from routes.tickets import tickets_bp
from routes.auth import auth_bp

def create_app():
    app = Flask(__name__)
    app.secret_key = 'your-secret-key'  # Make sure you have a secret key set
    
    # Register blueprints with URL prefixes
    app.register_blueprint(inventory_bp, url_prefix='/inventory')
    app.register_blueprint(tickets_bp, url_prefix='/tickets')
    app.register_blueprint(auth_bp, url_prefix='/auth')
    
    return app 