from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from utils.shipment_store import ShipmentStore
from utils.shipment_tracker import ShipmentTracker
from utils.singpost_tracking import get_singpost_tracking_client
from utils.auth_decorators import login_required, admin_required
from models.tracking_history import TrackingHistory
from database import SessionLocal
from datetime import datetime, timedelta
import json
import logging

# Set up logging for this module
logger = logging.getLogger(__name__)


shipments_bp = Blueprint('shipments', __name__, url_prefix='/shipments')
shipment_store = ShipmentStore()
shipment_tracker = ShipmentTracker()

# Initialize SingPost Tracking API client
singpost_client = get_singpost_tracking_client()




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
    """Display the shipment history page - search tracking via SingPost API"""
    # Check SingPost Tracking API configuration status
    credentials_status = singpost_client.get_credentials_status()

    # Get recent tracked shipments from local cache
    db = SessionLocal()
    shipments_list = []
    error = None

    try:
        # Get recently tracked shipments from cache
        recent_shipments = db.query(TrackingHistory).order_by(
            TrackingHistory.last_updated.desc()
        ).limit(50).all()

        for shipment in recent_shipments:
            shipments_list.append({
                'tracking_number': shipment.tracking_number,
                'carrier': shipment.carrier or 'SingPost',
                'status': shipment.status or 'Unknown',
                'last_updated': shipment.last_updated,
                'events_count': len(shipment.events) if shipment.events else 0
            })

    except Exception as e:
        logger.error(f"Error loading shipment history: {str(e)}")
        error = str(e)
    finally:
        db.close()

    if not credentials_status['is_configured']:
        error = "SingPost Tracking API not configured. Missing API Key."

    return render_template(
        'shipments/history.html',
        shipments_list=shipments_list,
        credentials_status=credentials_status,
        error=error
    )


@shipments_bp.route('/history/search', methods=['GET', 'POST'])
@login_required
def search_shipment_history():
    """Search for shipment tracking history using SingPost Tracking API"""
    tracking_number = request.form.get('tracking_number') or request.args.get('tracking_number', '').strip()

    if not tracking_number:
        flash('Please enter a tracking number', 'warning')
        return redirect(url_for('shipments.shipment_history'))

    # Check API configuration
    credentials_status = singpost_client.get_credentials_status()

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
                tracking_number=tracking_number,
                credentials_status=credentials_status
            )

        # Fetch fresh data from SingPost Tracking API
        tracking_data = singpost_client.track_single(tracking_number)

        if tracking_data and tracking_data.get('success'):
            events = tracking_data.get('events', [])

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
            tracking_number=tracking_number,
            credentials_status=credentials_status
        )

    except Exception as e:
        logger.error(f"Error searching shipment history: {str(e)}")
        db.rollback()
        flash(f'Error searching shipment: {str(e)}', 'error')
        return render_template(
            'shipments/history.html',
            tracking_number=tracking_number,
            credentials_status=credentials_status,
            error=str(e)
        )
    finally:
        db.close()


@shipments_bp.route('/history/bulk', methods=['GET', 'POST'])
@login_required
def bulk_shipment_history():
    """Search for multiple shipment tracking numbers at once"""
    credentials_status = singpost_client.get_credentials_status()

    if request.method == 'GET':
        return render_template('shipments/history_bulk.html', credentials_status=credentials_status)

    tracking_numbers_raw = request.form.get('tracking_numbers', '')
    # Split by newlines, commas, or spaces
    import re
    tracking_numbers = [t.strip() for t in re.split(r'[,\n\s]+', tracking_numbers_raw) if t.strip()]

    if not tracking_numbers:
        flash('Please enter at least one tracking number', 'warning')
        return redirect(url_for('shipments.bulk_shipment_history'))

    if len(tracking_numbers) > 20:
        flash('Maximum 20 tracking numbers per search', 'warning')
        tracking_numbers = tracking_numbers[:20]

    try:
        # Track all numbers at once using the SingPost Tracking API
        tracking_results = singpost_client.track(tracking_numbers)

        results = []
        for result in tracking_results:
            events = []
            for event in result.events:
                events.append({
                    'code': event.status_code,
                    'description': event.status_description,
                    'date': event.date,
                    'time': event.time,
                    'reason_code': event.reason_code
                })

            results.append({
                'tracking_number': result.tracking_number,
                'found': result.found,
                'carrier': 'SingPost',
                'status': result.events[0].status_description if result.events else 'Unknown',
                'origin_country': result.origin_country,
                'destination_country': result.destination_country,
                'events': events,
                'last_updated': datetime.utcnow().isoformat(),
                'error': result.error
            })

        return render_template(
            'shipments/history_bulk.html',
            results=results,
            tracking_numbers=tracking_numbers,
            credentials_status=credentials_status
        )

    except Exception as e:
        logger.error(f"Error in bulk shipment search: {str(e)}")
        flash(f'Error searching shipments: {str(e)}', 'error')
        return render_template('shipments/history_bulk.html', error=str(e), credentials_status=credentials_status)


@shipments_bp.route('/api/history/<tracking_number>')
@login_required
def api_shipment_history(tracking_number):
    """API endpoint for shipment tracking history (returns JSON)"""
    try:
        tracking_data = singpost_client.track_single(tracking_number)
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
        tracking_results = singpost_client.track(tracking_numbers)

        results = []
        for result in tracking_results:
            results.append({
                'tracking_number': result.tracking_number,
                'found': result.found,
                'carrier': 'SingPost',
                'status': result.events[0].status_description if result.events else 'Unknown',
                'origin_country': result.origin_country,
                'destination_country': result.destination_country,
                'events': [
                    {
                        'code': e.status_code,
                        'description': e.status_description,
                        'date': e.date,
                        'time': e.time,
                        'reason_code': e.reason_code
                    } for e in result.events
                ],
                'error': result.error
            })

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
