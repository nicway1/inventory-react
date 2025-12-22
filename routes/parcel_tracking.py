"""
Parcel Tracking Routes
Provides parcel tracking functionality using SingPost Tracking API
"""

from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from functools import wraps
import logging

from utils.singpost_tracking import get_singpost_tracking_client

logger = logging.getLogger(__name__)

# Initialize SingPost Tracking client
singpost_client = get_singpost_tracking_client()

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
    Track a single parcel using SingPost Tracking API

    Expected JSON:
    {
        "tracking_number": "1234567890"
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

        if not tracking_number:
            return jsonify({
                'success': False,
                'error': 'Tracking number is required'
            }), 400

        # Check if API is configured
        if not singpost_client.is_configured():
            return jsonify({
                'success': False,
                'error': 'SingPost Tracking API not configured'
            }), 500

        # Track parcel using SingPost API
        result = singpost_client.track_single(tracking_number)

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
    Track multiple parcels using SingPost Tracking API

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

        # Filter out empty strings and limit to 20 at a time
        tracking_numbers = [tn.strip() for tn in tracking_numbers if tn.strip()][:20]

        if not tracking_numbers:
            return jsonify({
                'success': False,
                'error': 'No valid tracking numbers provided'
            }), 400

        # Check if API is configured
        if not singpost_client.is_configured():
            return jsonify({
                'success': False,
                'error': 'SingPost Tracking API not configured'
            }), 500

        # Track all parcels using SingPost API
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
                'success': result.found,
                'tracking_number': result.tracking_number,
                'carrier': 'SingPost',
                'status': result.events[0].status_description if result.events else 'Unknown',
                'origin_country': result.origin_country,
                'destination_country': result.destination_country,
                'events': events,
                'was_pushed': result.was_pushed,  # True if physically received by SingPost
                'error': result.error
            })

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
        {'code': 'singpost', 'name': 'Singapore Post'},
    ]

    return jsonify({
        'success': True,
        'carriers': carriers
    })


@parcel_tracking_bp.route('/status')
@developer_required
def get_status():
    """Get SingPost Tracking API status"""
    status = singpost_client.get_credentials_status()
    return jsonify({
        'success': True,
        'configured': status['is_configured'],
        'api_url': status['base_url']
    })
