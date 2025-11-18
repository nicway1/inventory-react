"""
Parcel Tracking Routes
Provides parcel tracking functionality using Ship24.com
"""

from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from functools import wraps
import logging

from utils.ship24_tracker import get_tracker

logger = logging.getLogger(__name__)

parcel_tracking_bp = Blueprint('parcel_tracking', __name__, url_prefix='/parcel-tracking')


def developer_required(f):
    """Decorator to restrict access to developer accounts only"""
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if not current_user.is_developer:
            return jsonify({'error': 'Access denied. Developer account required.'}), 403
        return f(*args, **kwargs)
    return decorated_function


@parcel_tracking_bp.route('/')
@developer_required
def index():
    """Parcel tracking main page - Developer only"""
    return render_template('parcel_tracking/index.html')


@parcel_tracking_bp.route('/track', methods=['POST'])
@developer_required
def track_parcel():
    """
    Track a single parcel

    Expected JSON:
    {
        "tracking_number": "1234567890",
        "carrier": "dhl" (optional)
    }
    """
    try:
        data = request.get_json(force=True, silent=True)

        if not data:
            return jsonify({
                'success': False,
                'error': 'Invalid request: JSON body is required'
            }), 400

        tracking_number = data.get('tracking_number', '').strip() if data.get('tracking_number') else ''
        carrier = data.get('carrier', '').strip() if data.get('carrier') else None

        if not tracking_number:
            return jsonify({
                'success': False,
                'error': 'Tracking number is required'
            }), 400

        # Get tracker instance and track parcel
        tracker = get_tracker()
        result = tracker.track_parcel_sync(tracking_number, carrier)

        return jsonify(result)

    except Exception as e:
        logger.error(f"Error in track_parcel endpoint: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e),
            'message': 'An error occurred while tracking the parcel'
        }), 500


@parcel_tracking_bp.route('/track/bulk', methods=['POST'])
@developer_required
def track_multiple_parcels():
    """
    Track multiple parcels

    Expected JSON:
    {
        "tracking_numbers": ["1234567890", "0987654321", ...]
    }
    """
    try:
        data = request.get_json(force=True, silent=True)

        if not data:
            return jsonify({
                'success': False,
                'error': 'Invalid request: JSON body is required'
            }), 400

        tracking_numbers = data.get('tracking_numbers', [])

        if not tracking_numbers or not isinstance(tracking_numbers, list):
            return jsonify({
                'success': False,
                'error': 'tracking_numbers array is required'
            }), 400

        # Filter out empty strings and limit to 10 at a time
        tracking_numbers = [tn.strip() for tn in tracking_numbers if tn.strip()][:10]

        if not tracking_numbers:
            return jsonify({
                'success': False,
                'error': 'No valid tracking numbers provided'
            }), 400

        # Get tracker instance and track parcels
        tracker = get_tracker()

        # Track parcels synchronously (one at a time to avoid browser resource issues)
        results = []
        for tn in tracking_numbers:
            result = tracker.track_parcel_sync(tn)
            results.append(result)

        return jsonify({
            'success': True,
            'results': results,
            'total': len(results)
        })

    except Exception as e:
        logger.error(f"Error in track_multiple_parcels endpoint: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e),
            'message': 'An error occurred while tracking parcels'
        }), 500


@parcel_tracking_bp.route('/carriers')
@developer_required
def get_carriers():
    """Get list of supported carriers"""
    carriers = [
        {'code': 'dhl', 'name': 'DHL Express'},
        {'code': 'fedex', 'name': 'FedEx'},
        {'code': 'ups', 'name': 'UPS'},
        {'code': 'usps', 'name': 'USPS'},
        {'code': 'singpost', 'name': 'Singapore Post'},
        {'code': 'bluedart', 'name': 'BlueDart'},
        {'code': 'dtdc', 'name': 'DTDC'},
        {'code': 'aramex', 'name': 'Aramex'},
        {'code': 'tnt', 'name': 'TNT'},
        {'code': 'dpd', 'name': 'DPD'},
    ]

    return jsonify({
        'success': True,
        'carriers': carriers
    })
