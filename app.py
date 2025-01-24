from flask import Flask, redirect, url_for, render_template, session
from flask_cors import CORS
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
from models.database import Base
from utils.db_manager import DatabaseManager
import os
from models.user import UserType
from routes.main import main_bp
from database import init_db

# Create data directory if it doesn't exist
os.makedirs('data', exist_ok=True)

app = Flask(__name__)
app.secret_key = os.urandom(24)
CORS(app)

# Configuration
app.config['SECRET_KEY'] = 'your-secret-key-here'  # Change this in production
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///./inventory.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize database
init_db()

# Register blueprints
app.register_blueprint(main_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(inventory_bp, url_prefix='/inventory')
app.register_blueprint(tickets_bp)
app.register_blueprint(shipments_bp)
app.register_blueprint(users_bp)
app.register_blueprint(data_loader_bp)
app.register_blueprint(admin_bp, url_prefix='/admin')

@app.route('/activity/<int:activity_id>/read', methods=['POST'])
@login_required
def mark_activity_read(activity_id):
    activity_store.mark_as_read(activity_id)
    return redirect(url_for('main.index'))

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port) 