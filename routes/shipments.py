from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from utils.shipment_store import ShipmentStore
from utils.shipment_tracker import ShipmentTracker
from utils.auth_decorators import login_required, admin_required
import logging

# Set up logging for this module
logger = logging.getLogger(__name__)


shipments_bp = Blueprint('shipments', __name__, url_prefix='/shipments')
shipment_store = ShipmentStore()
shipment_tracker = ShipmentTracker()

@shipments_bp.route('/')
@login_required
def list_shipments():
    user_id = session['user_id']
    user_type = session['user_type']
    if user_type == 'admin':
        shipments = list(shipment_store.shipments.values())
    else:
        shipments = shipment_store.get_user_shipments(user_id)
    return render_template('shipments/list.html', shipments=shipments)

@shipments_bp.route('/new', methods=['GET', 'POST'])
@admin_required
def create_shipment():
    if request.method == 'POST':
        shipment = shipment_store.create_shipment(
            user_id=request.form.get('user_id'),
            tracking_number=request.form.get('tracking_number'),
            description=request.form.get('description')
        )
        flash('Shipment created successfully')
        return redirect(url_for('shipments.view_shipment', shipment_id=shipment.id))
    return render_template('shipments/create.html')

@shipments_bp.route('/<int:shipment_id>')
@login_required
def view_shipment(shipment_id):
    shipment = shipment_store.get_shipment(shipment_id)
    if not shipment:
        flash('Shipment not found')
        return redirect(url_for('shipments.list_shipments'))
    return render_template('shipments/view.html', shipment=shipment)

@shipments_bp.route('/<int:shipment_id>/track')
@login_required
def track_shipment(shipment_id):
    try:
        shipment = shipment_store.get_shipment(shipment_id)
        if not shipment:
            flash('Shipment not found')
            return redirect(url_for('shipments.list_shipments'))

        tracking_info = shipment_tracker.get_tracking_info(shipment.tracking_number)
        if tracking_info:
            shipment = shipment_store.update_tracking(shipment_id, tracking_info)
        
        return render_template(
            'shipments/tracking.html', 
            shipment=shipment, 
            tracking_info=tracking_info
        )
    except Exception as e:
        flash(f'Error tracking shipment: {str(e)}')
        return redirect(url_for('shipments.list_shipments')) 