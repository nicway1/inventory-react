"""
Parcel Tracking Routes
Provides parcel tracking functionality using multiple carriers (Ship24, SingPost, HFD, etc.)
"""

from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from functools import wraps
import logging

from utils.singpost_tracking import get_singpost_tracking_client
from utils.ship24_tracker import get_tracker

logger = logging.getLogger(__name__)

# Initialize tracking clients
singpost_client = get_singpost_tracking_client()
ship24_tracker = get_tracker()

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
    Track a single parcel using multiple tracking services

    Expected JSON:
    {
        "tracking_number": "1234567890",
        "carrier": "auto",  // optional: auto, singpost, hfd, dhl, ups, fedex, etc.
        "method": "auto",   // optional: auto, oxylabs, playwright, links_only
        "provider": "auto"  // optional: auto, ship24, hfd, 17track, trackingmore
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
        carrier = data.get('carrier', 'auto').lower()
        method = data.get('method', 'auto').lower()
        provider = data.get('provider', 'auto').lower()

        if not tracking_number:
            return jsonify({
                'success': False,
                'error': 'Tracking number is required'
            }), 400

        # Use Ship24Tracker for multi-carrier support
        result = ship24_tracker.track_parcel_sync(
            tracking_number,
            carrier if carrier != 'auto' else None,
            method if method != 'auto' else None,
            provider if provider != 'auto' else None
        )

        # Add tracking links for manual checking
        if 'tracking_links' not in result:
            result['tracking_links'] = ship24_tracker._get_all_tracking_links(tracking_number)

        return jsonify(result)

    except Exception as e:
        logger.error(f"Error in track_parcel endpoint: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e),
            'message': 'An error occurred while tracking the parcel',
            'tracking_links': ship24_tracker._get_all_tracking_links(tracking_number) if tracking_number else {}
        }), 500


@parcel_tracking_bp.route('/track/bulk', methods=['POST'])
@developer_required
def track_multiple_parcels():
    """
    Track multiple parcels using multiple tracking services

    Expected JSON:
    {
        "tracking_numbers": ["1234567890", "0987654321", ...],
        "carrier": "auto",  // optional
        "method": "auto",   // optional: auto, oxylabs, playwright, links_only
        "provider": "auto"  // optional: auto, ship24, hfd, 17track, trackingmore
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
        carrier = data.get('carrier', 'auto').lower()
        method = data.get('method', 'auto').lower()
        provider = data.get('provider', 'auto').lower()

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

        # Track all parcels using Ship24Tracker
        results = []
        for tn in tracking_numbers:
            try:
                result = ship24_tracker.track_parcel_sync(
                    tn,
                    carrier if carrier != 'auto' else None,
                    method if method != 'auto' else None,
                    provider if provider != 'auto' else None
                )
                if 'tracking_links' not in result:
                    result['tracking_links'] = ship24_tracker._get_all_tracking_links(tn)
                results.append(result)
            except Exception as e:
                logger.error(f"Error tracking {tn}: {str(e)}")
                results.append({
                    'success': False,
                    'tracking_number': tn,
                    'error': str(e),
                    'tracking_links': ship24_tracker._get_all_tracking_links(tn)
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
        {'code': 'auto', 'name': 'Auto-Detect'},
        {'code': 'hfd', 'name': 'HFD (Israel)'},
        {'code': 'singpost', 'name': 'Singapore Post'},
        {'code': 'dhl', 'name': 'DHL Express'},
        {'code': 'ups', 'name': 'UPS'},
        {'code': 'fedex', 'name': 'FedEx'},
        {'code': 'usps', 'name': 'USPS'},
        {'code': 'china_post', 'name': 'China Post'},
        {'code': 'ems', 'name': 'EMS'},
        {'code': 'royal_mail', 'name': 'Royal Mail'},
        {'code': 'australia_post', 'name': 'Australia Post'},
        {'code': 'japan_post', 'name': 'Japan Post'},
        {'code': 'korea_post', 'name': 'Korea Post'},
        {'code': 'pos_malaysia', 'name': 'Pos Malaysia'},
        {'code': 'thai_post', 'name': 'Thai Post'},
        {'code': 'aramex', 'name': 'Aramex'},
        {'code': 'tnt', 'name': 'TNT'},
    ]

    return jsonify({
        'success': True,
        'carriers': carriers
    })


@parcel_tracking_bp.route('/status')
@developer_required
def get_status():
    """Get tracking API status"""
    singpost_status = singpost_client.get_credentials_status() if singpost_client.is_configured() else {'is_configured': False}

    return jsonify({
        'success': True,
        'singpost_configured': singpost_status.get('is_configured', False),
        'ship24_available': True,
        'supported_carriers': [
            'HFD (Israel)', 'SingPost', 'DHL', 'UPS', 'FedEx', 'USPS',
            'China Post', 'EMS', 'Royal Mail', 'Australia Post', 'Japan Post',
            'Korea Post', 'Pos Malaysia', 'Thai Post', 'Aramex', 'TNT'
        ]
    })


@parcel_tracking_bp.route('/links/<tracking_number>')
@developer_required
def get_tracking_links(tracking_number):
    """Get all tracking links for a tracking number"""
    links = ship24_tracker._get_all_tracking_links(tracking_number)
    detected_carrier = ship24_tracker._detect_carrier(tracking_number)

    return jsonify({
        'success': True,
        'tracking_number': tracking_number,
        'detected_carrier': detected_carrier,
        'links': links
    })
