from flask import Blueprint, render_template, redirect, url_for, session, request, flash
from utils.auth_decorators import login_required, admin_required
from utils.store_instances import (
    user_store, activity_store, ticket_store, 
    inventory_store, queue_store, shipment_store
)
from utils.db_manager import DatabaseManager
from models.company import Company
import os
from werkzeug.utils import secure_filename
from models.asset import Asset
from models.accessory import Accessory
from models.user import UserType

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
    if request.method == 'POST' and user.user_type in [UserType.SUPER_ADMIN, UserType.COUNTRY_ADMIN]:
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
        else:
            flash('Invalid file type. Please upload an Excel file (.xlsx or .xls)')
            return redirect(request.url)
    elif request.method == 'POST':
        flash('You do not have permission to import data')
        return redirect(url_for('main.index'))

    # Get shipments
    shipments = shipment_store.get_user_shipments(user_id)

    # Get queues
    queues = queue_store.get_all_queues()

    # Get asset counts from database
    db_session = db_manager.get_session()
    try:
        tech_assets_count = db_session.query(Asset).count()
        accessories_count = db_session.query(Accessory).count()
        total_inventory = tech_assets_count + accessories_count
    finally:
        db_session.close()

    # Calculate summary statistics
    stats = {
        'total_inventory': total_inventory,
        'total_shipments': len(shipments),
        'total_queues': len(queues)
    }

    # Get activities
    activities = activity_store.get_user_activities(user_id)

    return render_template('home.html',
        shipments=shipments,
        queues=queues,
        stats=stats,
        activities=activities,
        user=user
    )