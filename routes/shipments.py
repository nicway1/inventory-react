from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from utils.shipment_store import ShipmentStore
from utils.shipment_tracker import ShipmentTracker
from utils.ship24_tracker import Ship24Tracker
from utils.singpost_ezy2ship import get_ezy2ship_client
from utils.auth_decorators import login_required, admin_required
from models.tracking_history import TrackingHistory
from database import SessionLocal
from datetime import datetime, timedelta
import asyncio
import json
import logging

# Set up logging for this module
logger = logging.getLogger(__name__)


shipments_bp = Blueprint('shipments', __name__, url_prefix='/shipments')
shipment_store = ShipmentStore()
shipment_tracker = ShipmentTracker()

# Initialize Ship24Tracker for SingPost API (uses production endpoint)
ship24_tracker = Ship24Tracker(use_singpost_uat=False)

# Initialize Ezy2ship client for fetching account shipments
ezy2ship_client = get_ezy2ship_client()


def run_async(coro):
    """Helper to run async functions in sync context"""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)


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


# ============================================================================
# SingPost Shipment History Routes (using Ship24Tracker with SingPost API)
# ============================================================================

@shipments_bp.route('/history')
@login_required
def shipment_history():
    """Display the shipment history page with all Ezy2ship account shipments"""
    # Get date filter parameters
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')

    # Default: last 30 days if no dates specified
    if not date_to:
        date_to = datetime.now().strftime('%Y-%m-%d')
    if not date_from:
        date_from = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')

    # Check Ezy2ship API configuration status
    credentials_status = ezy2ship_client.get_credentials_status()

    shipments_list = []
    manifests_list = []
    error = None

    if credentials_status['is_configured']:
        try:
            # Get manifests for the date range
            manifests_list = ezy2ship_client.get_manifests(date_from, date_to)

            # Get all shipments from manifests
            shipments_list = ezy2ship_client.get_all_shipments(date_from, date_to, limit=200)

        except Exception as e:
            logger.error(f"Error loading shipment history from Ezy2ship: {str(e)}")
            error = str(e)
    else:
        # Show which credentials are missing
        missing = []
        if not credentials_status['customer_id']:
            missing.append('Customer ID')
        if not credentials_status['username']:
            missing.append('Username')
        if not credentials_status['password']:
            missing.append('Password')
        if not credentials_status['aes_key']:
            missing.append('AES Key')
        if not credentials_status['crypto_available']:
            missing.append('Cryptography library (pip install pycryptodome)')
        if not credentials_status['zeep_available']:
            missing.append('SOAP library (pip install zeep)')

        if missing:
            error = f"Ezy2ship API not configured. Missing: {', '.join(missing)}"

    return render_template(
        'shipments/history.html',
        shipments_list=shipments_list,
        manifests_list=manifests_list,
        credentials_status=credentials_status,
        date_from=date_from,
        date_to=date_to,
        error=error
    )


@shipments_bp.route('/history/search', methods=['GET', 'POST'])
@login_required
def search_shipment_history():
    """Search for shipment tracking history using SingPost API"""
    tracking_number = request.form.get('tracking_number') or request.args.get('tracking_number', '').strip()

    if not tracking_number:
        flash('Please enter a tracking number', 'warning')
        return redirect(url_for('shipments.shipment_history'))

    # Check cache first
    db = SessionLocal()
    try:
        cached = db.query(TrackingHistory).filter_by(
            tracking_number=tracking_number
        ).order_by(TrackingHistory.last_updated.desc()).first()

        # Use cache if fresh (less than 1 hour old)
        if cached and not cached.is_stale(ttl_hours=1):
            tracking_data = {
                'success': True,
                'tracking_number': cached.tracking_number,
                'carrier': cached.carrier,
                'status': cached.status,
                'events': cached.events,
                'last_updated': cached.last_updated.isoformat(),
                'source': 'Cache'
            }
            return render_template(
                'shipments/history.html',
                tracking_data=tracking_data,
                tracking_number=tracking_number
            )

        # Fetch fresh data from SingPost API via Ship24Tracker
        tracking_data = run_async(ship24_tracker.track_parcel(tracking_number))

        if tracking_data and tracking_data.get('success'):
            # Transform events to expected format
            events = []
            for event in tracking_data.get('events', []):
                events.append({
                    'code': '',
                    'description': event.get('description', ''),
                    'date': event.get('timestamp', '').split('T')[0] if 'T' in event.get('timestamp', '') else event.get('timestamp', ''),
                    'time': event.get('timestamp', '').split('T')[1] if 'T' in event.get('timestamp', '') else '',
                    'location': event.get('location', ''),
                    'signatory': None
                })
            tracking_data['events'] = events

            # Update or create cache entry
            if cached:
                cached.update(
                    tracking_data=events,
                    status=tracking_data.get('status'),
                    carrier=tracking_data.get('carrier')
                )
            else:
                cached = TrackingHistory(
                    tracking_number=tracking_number,
                    tracking_data=events,
                    carrier=tracking_data.get('carrier'),
                    status=tracking_data.get('status'),
                    tracking_type='singpost'
                )
                db.add(cached)

            db.commit()

        return render_template(
            'shipments/history.html',
            tracking_data=tracking_data,
            tracking_number=tracking_number
        )

    except Exception as e:
        logger.error(f"Error searching shipment history: {str(e)}")
        db.rollback()
        flash(f'Error searching shipment: {str(e)}', 'error')
        return render_template(
            'shipments/history.html',
            tracking_number=tracking_number,
            error=str(e)
        )
    finally:
        db.close()


@shipments_bp.route('/history/bulk', methods=['GET', 'POST'])
@login_required
def bulk_shipment_history():
    """Search for multiple shipment tracking numbers at once"""
    if request.method == 'GET':
        return render_template('shipments/history_bulk.html')

    tracking_numbers_raw = request.form.get('tracking_numbers', '')
    # Split by newlines, commas, or spaces
    import re
    tracking_numbers = [t.strip() for t in re.split(r'[,\n\s]+', tracking_numbers_raw) if t.strip()]

    if not tracking_numbers:
        flash('Please enter at least one tracking number', 'warning')
        return redirect(url_for('shipments.bulk_shipment_history'))

    if len(tracking_numbers) > 20:
        flash('Maximum 20 tracking numbers per search (API limit)', 'warning')
        tracking_numbers = tracking_numbers[:20]

    try:
        results = []
        for tracking_num in tracking_numbers:
            tracking_data = run_async(ship24_tracker.track_parcel(tracking_num))

            if tracking_data:
                events = []
                for event in tracking_data.get('events', []):
                    events.append({
                        'code': '',
                        'description': event.get('description', ''),
                        'date': event.get('timestamp', '').split('T')[0] if 'T' in event.get('timestamp', '') else event.get('timestamp', ''),
                        'time': event.get('timestamp', '').split('T')[1] if 'T' in event.get('timestamp', '') else '',
                        'signatory': None
                    })

                results.append({
                    'tracking_number': tracking_data.get('tracking_number', tracking_num),
                    'carrier': tracking_data.get('carrier', 'Unknown'),
                    'status': tracking_data.get('status', 'Unknown'),
                    'events': events,
                    'last_updated': tracking_data.get('last_updated', datetime.utcnow().isoformat()),
                    'tracking_links': tracking_data.get('tracking_links', {})
                })

        return render_template(
            'shipments/history_bulk.html',
            results=results,
            tracking_numbers=tracking_numbers
        )

    except Exception as e:
        logger.error(f"Error in bulk shipment search: {str(e)}")
        flash(f'Error searching shipments: {str(e)}', 'error')
        return render_template('shipments/history_bulk.html', error=str(e))


@shipments_bp.route('/api/history/<tracking_number>')
@login_required
def api_shipment_history(tracking_number):
    """API endpoint for shipment tracking history (returns JSON)"""
    try:
        tracking_data = run_async(ship24_tracker.track_parcel(tracking_number))
        return jsonify(tracking_data)

    except Exception as e:
        logger.error(f"API error getting tracking history: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@shipments_bp.route('/api/history/bulk', methods=['POST'])
@login_required
def api_bulk_shipment_history():
    """API endpoint for bulk shipment tracking (returns JSON)"""
    data = request.get_json()

    if not data or 'tracking_numbers' not in data:
        return jsonify({
            'success': False,
            'error': 'tracking_numbers required in request body'
        }), 400

    tracking_numbers = data['tracking_numbers']
    if not isinstance(tracking_numbers, list):
        return jsonify({
            'success': False,
            'error': 'tracking_numbers must be a list'
        }), 400

    if len(tracking_numbers) > 20:
        return jsonify({
            'success': False,
            'error': 'Maximum 20 tracking numbers per request'
        }), 400

    try:
        results = []
        for tracking_num in tracking_numbers:
            tracking_data = run_async(ship24_tracker.track_parcel(tracking_num))
            if tracking_data:
                results.append(tracking_data)

        return jsonify({
            'success': True,
            'count': len(results),
            'shipments': results
        })

    except Exception as e:
        logger.error(f"API error in bulk tracking: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
