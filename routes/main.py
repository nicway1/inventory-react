from flask import Blueprint, render_template, redirect, url_for, session, request, flash
from utils.auth_decorators import login_required, admin_required
from utils.store_instances import (
    user_store, activity_store, ticket_store, 
    inventory_store, queue_store, shipment_store
)
from utils.db_manager import DatabaseManager
import os
from werkzeug.utils import secure_filename

main_bp = Blueprint('main', __name__)
db_manager = DatabaseManager()

# Configure upload settings for dashboard
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'xlsx', 'xls'}

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@main_bp.route('/', methods=['GET', 'POST'])
@login_required
def index():
    user_id = session['user_id']
    user = db_manager.get_user(user_id)
    if not user:
        session.clear()
        return redirect(url_for('auth.login'))

    # Handle file upload if POST request
    if request.method == 'POST' and user.is_admin:
        if 'file' not in request.files:
            flash('No file uploaded')
            return redirect(request.url)
            
        file = request.files['file']
        if file.filename == '':
            flash('No file selected')
            return redirect(request.url)
            
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            file.save(filepath)
            
            if inventory_store.import_from_excel(filepath):
                flash('Inventory imported successfully')
                # Clean up the uploaded file
                os.remove(filepath)
            else:
                flash('Error importing inventory')
                
            return redirect(url_for('main.index'))

    # Get shipments
    shipments = shipment_store.get_user_shipments(user_id)

    # Get inventory items
    inventory_items = inventory_store.get_all_items()

    # Get queues
    queues = queue_store.get_all_queues()

    # Calculate summary statistics
    stats = {
        'total_inventory': len(inventory_items),
        'total_shipments': len(shipments),
        'total_queues': len(queues)
    }

    # Get activities
    activities = activity_store.get_user_activities(user_id)

    print(f"Rendering home template for user: {user.username} (type: {user.user_type})")
    return render_template('home.html',
        shipments=shipments,
        inventory_items=inventory_items,
        queues=queues,
        stats=stats,
        activities=activities,
        user=user
    )