"""
API Routes for Device Specification Collection
"""

from flask import Blueprint, request, jsonify, render_template
from datetime import datetime
from database import SessionLocal
from models.device_spec import DeviceSpec
from utils.auth_decorators import login_required
from utils.mac_models import get_mac_model_name
import logging

logger = logging.getLogger(__name__)

specs_bp = Blueprint('specs', __name__)


@specs_bp.route('/api/specs/submit', methods=['POST'])
def submit_specs():
    """
    Receive device specifications from the mac-specs.sh script.
    No authentication required - specs are submitted from recovery mode.
    """
    try:
        data = request.get_json()

        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400

        # Get client IP
        client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
        if client_ip:
            client_ip = client_ip.split(',')[0].strip()

        # Create new spec record
        db_session = SessionLocal()
        try:
            spec = DeviceSpec(
                serial_number=data.get('serial_number', '').strip(),
                hardware_uuid=data.get('hardware_uuid', '').strip(),
                model_name=data.get('model_name', '').strip(),
                model_id=data.get('model_id', '').strip(),
                cpu=data.get('cpu', '').strip(),
                cpu_cores=data.get('cpu_cores', '').strip(),
                gpu=data.get('gpu', '').strip(),
                gpu_cores=data.get('gpu_cores', '').strip(),
                ram_gb=data.get('ram_gb', '').strip(),
                memory_type=data.get('memory_type', '').strip(),
                storage_gb=data.get('storage_gb', '').strip(),
                storage_type=data.get('storage_type', '').strip(),
                free_space=data.get('free_space', '').strip(),
                os_name=data.get('os_name', '').strip(),
                os_version=data.get('os_version', '').strip(),
                os_build=data.get('os_build', '').strip(),
                battery_cycles=data.get('battery_cycles', '').strip(),
                battery_health=data.get('battery_health', '').strip(),
                wifi_mac=data.get('wifi_mac', '').strip(),
                ethernet_mac=data.get('ethernet_mac', '').strip(),
                ip_address=client_ip,
                submitted_at=datetime.utcnow()
            )

            db_session.add(spec)
            db_session.commit()

            logger.info(f"Device spec submitted: {spec.serial_number} from {client_ip}")

            return jsonify({
                'success': True,
                'id': spec.id,
                'serial_number': spec.serial_number,
                'message': 'Specs submitted successfully'
            })

        except Exception as e:
            db_session.rollback()
            logger.error(f"Error saving device spec: {str(e)}")
            return jsonify({'success': False, 'error': str(e)}), 500
        finally:
            db_session.close()

    except Exception as e:
        logger.error(f"Error processing spec submission: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@specs_bp.route('/api/specs/list', methods=['GET'])
@login_required
def list_specs():
    """Get list of submitted device specs"""
    db_session = SessionLocal()
    try:
        # Get query parameters
        processed = request.args.get('processed')
        limit = request.args.get('limit', 100, type=int)

        query = db_session.query(DeviceSpec).order_by(DeviceSpec.submitted_at.desc())

        if processed is not None:
            query = query.filter(DeviceSpec.processed == (processed.lower() == 'true'))

        specs = query.limit(limit).all()

        return jsonify({
            'success': True,
            'count': len(specs),
            'specs': [spec.to_dict() for spec in specs]
        })

    except Exception as e:
        logger.error(f"Error listing specs: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db_session.close()


@specs_bp.route('/api/specs/<int:spec_id>', methods=['GET'])
@login_required
def get_spec(spec_id):
    """Get a specific device spec"""
    db_session = SessionLocal()
    try:
        spec = db_session.query(DeviceSpec).get(spec_id)

        if not spec:
            return jsonify({'success': False, 'error': 'Spec not found'}), 404

        spec_dict = spec.to_dict()
        # Add translated model name
        spec_dict['model_name_translated'] = get_mac_model_name(spec.model_id) if spec.model_id else spec.model_name

        return jsonify({
            'success': True,
            'spec': spec_dict
        })

    except Exception as e:
        logger.error(f"Error getting spec: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db_session.close()


@specs_bp.route('/api/specs/<int:spec_id>/mark-processed', methods=['POST'])
@login_required
def mark_processed(spec_id):
    """Mark a spec as processed (added to inventory)"""
    db_session = SessionLocal()
    try:
        spec = db_session.query(DeviceSpec).get(spec_id)

        if not spec:
            return jsonify({'success': False, 'error': 'Spec not found'}), 404

        data = request.get_json() or {}
        spec.processed = True
        spec.processed_at = datetime.utcnow()
        spec.asset_id = data.get('asset_id')
        spec.notes = data.get('notes')

        db_session.commit()

        return jsonify({
            'success': True,
            'message': 'Spec marked as processed'
        })

    except Exception as e:
        db_session.rollback()
        logger.error(f"Error marking spec as processed: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db_session.close()


@specs_bp.route('/api/specs/<int:spec_id>', methods=['DELETE'])
@login_required
def delete_spec(spec_id):
    """Delete a device spec"""
    db_session = SessionLocal()
    try:
        spec = db_session.query(DeviceSpec).get(spec_id)

        if not spec:
            return jsonify({'success': False, 'error': 'Spec not found'}), 404

        db_session.delete(spec)
        db_session.commit()

        return jsonify({
            'success': True,
            'message': 'Spec deleted'
        })

    except Exception as e:
        db_session.rollback()
        logger.error(f"Error deleting spec: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db_session.close()


@specs_bp.route('/api/specs/<int:spec_id>/find-tickets', methods=['GET'])
@login_required
def find_related_tickets(spec_id):
    """Find tickets related to a device spec by searching serial number, model, etc."""
    db_session = SessionLocal()
    try:
        from models.ticket import Ticket, TicketStatus
        from sqlalchemy import or_

        spec = db_session.query(DeviceSpec).get(spec_id)
        if not spec:
            return jsonify({'success': False, 'error': 'Spec not found'}), 404

        # Search for tickets that might be related to this spec
        # Search in ticket title, description, and notes
        search_terms = []
        if spec.serial_number:
            search_terms.append(spec.serial_number)
        if spec.model_id:
            search_terms.append(spec.model_id)
        if spec.model_name:
            search_terms.append(spec.model_name)

        if not search_terms:
            return jsonify({
                'success': True,
                'tickets': [],
                'message': 'No search terms available for this spec'
            })

        # Build search filters
        filters = []
        for term in search_terms:
            filters.append(Ticket.title.ilike(f'%{term}%'))
            filters.append(Ticket.description.ilike(f'%{term}%'))
            if hasattr(Ticket, 'notes'):
                filters.append(Ticket.notes.ilike(f'%{term}%'))

        # Query tickets
        tickets = db_session.query(Ticket).filter(
            or_(*filters)
        ).order_by(Ticket.created_at.desc()).limit(20).all()

        # Format response
        tickets_list = []
        for ticket in tickets:
            tickets_list.append({
                'id': ticket.id,
                'display_id': ticket.display_id if hasattr(ticket, 'display_id') else f'#{ticket.id}',
                'title': ticket.title,
                'status': ticket.status.value if ticket.status else 'Unknown',
                'category': ticket.category.value if hasattr(ticket, 'category') and ticket.category else '',
                'created_at': ticket.created_at.strftime('%b %d, %Y') if ticket.created_at else '',
                'customer': ticket.customer.name if hasattr(ticket, 'customer') and ticket.customer else ''
            })

        return jsonify({
            'success': True,
            'count': len(tickets_list),
            'tickets': tickets_list,
            'search_terms': search_terms
        })

    except Exception as e:
        logger.error(f"Error finding related tickets: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db_session.close()


@specs_bp.route('/device-specs')
@login_required
def device_specs_page():
    """Page to view submitted device specs"""
    db_session = SessionLocal()
    try:
        # Get all specs, unprocessed first
        specs = db_session.query(DeviceSpec).order_by(
            DeviceSpec.processed.asc(),
            DeviceSpec.submitted_at.desc()
        ).all()

        unprocessed_count = sum(1 for s in specs if not s.processed)

        return render_template('device_specs.html',
                               specs=specs,
                               unprocessed_count=unprocessed_count,
                               get_mac_model_name=get_mac_model_name)

    except Exception as e:
        logger.error(f"Error loading device specs page: {str(e)}")
        return f"Error: {str(e)}", 500
    finally:
        db_session.close()
