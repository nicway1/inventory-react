from flask import Blueprint, jsonify, request, session
from utils.auth_decorators import login_required
from utils.db_manager import DatabaseManager
from models.asset import Asset
from models.customer_user import CustomerUser
from models.company import Company
from models.user import User, UserType
from models.ticket_tracking import TicketTracking, TrackingItemAssignment
from models.ticket import Ticket, TicketAccessory
from sqlalchemy import or_
from flask import current_app
import datetime

api_bp = Blueprint('api', __name__, url_prefix='/api')
db_manager = DatabaseManager()

@api_bp.route('/assets/details', methods=['GET'])
@login_required
def get_asset_details():
    serial_number = request.args.get('serial_number')
    if not serial_number:
        return jsonify({'error': 'Serial number is required'}), 400

    db_session = db_manager.get_session()
    try:
        asset = db_session.query(Asset).filter(Asset.serial_num == serial_number).first()
        if not asset:
            return jsonify({'error': 'Asset not found'}), 404

        # Get customer company name from either customer_user or legacy customer field
        customer_company = None
        if asset.customer_user and asset.customer_user.company:
            customer_company = asset.customer_user.company.name
        elif asset.customer:
            customer_company = asset.customer

        return jsonify({
            'model': asset.model,
            'customer_company': customer_company,
            'serial_number': asset.serial_num,
            'asset_tag': asset.asset_tag
        })
    finally:
        db_session.close()

@api_bp.route('/customers/search', methods=['GET'])
@login_required
def search_customers():
    """Search customers by name, company, email, or address"""
    try:
        query = request.args.get('q', '').strip()
        
        db_session = db_manager.get_session()
        user = db_manager.get_user(session['user_id'])
        
        # Base query
        customers_query = db_session.query(CustomerUser).join(Company, CustomerUser.company_id == Company.id, isouter=True)
        
        # Apply permission-based filtering for non-SUPER_ADMIN users
        if user.user_type != UserType.SUPER_ADMIN and user.company_id:
            from models.company_customer_permission import CompanyCustomerPermission
            
            # Get companies this user's company has permission to view customers from
            permitted_company_ids = db_session.query(CompanyCustomerPermission.customer_company_id)\
                .filter(
                    CompanyCustomerPermission.company_id == user.company_id,
                    CompanyCustomerPermission.can_view == True
                ).subquery()
            
            # Users can see their own company's customers plus any permitted ones
            customers_query = customers_query.filter(
                or_(
                    CustomerUser.company_id == user.company_id,  # Own company customers
                    CustomerUser.company_id.in_(permitted_company_ids)  # Permitted customers
                )
            )
        
        if query and len(query) >= 2:
            # Search customers by name, email, company name, or address
            customers = customers_query.filter(
                or_(
                    CustomerUser.name.ilike(f'%{query}%'),
                    CustomerUser.email.ilike(f'%{query}%'),
                    CustomerUser.address.ilike(f'%{query}%'),
                    Company.name.ilike(f'%{query}%')
                )
            ).limit(20).all()
        else:
            # No query or query too short - return all customers (limited)
            customers = customers_query.limit(50).all()
        
        results = []
        for customer in customers:
            results.append({
                'id': customer.id,
                'name': customer.name,
                'email': customer.email or '',
                'company': customer.company.name if customer.company else '',
                'address': customer.address or '',
                'text': f"{customer.name} ({customer.company.name if customer.company else 'No Company'})"
            })
        
        return jsonify(results)
        
    except Exception as e:
        current_app.logger.error(f"Error searching customers: {str(e)}")
        return jsonify({'error': 'Search failed'}), 500

@api_bp.route('/search', methods=['GET'])
@login_required
def unified_search():
    """Unified search API endpoint for assets, tickets, accessories, and customers"""
    try:
        from models.ticket import Ticket, TicketCategory, TicketStatus, TicketPriority
        from models.asset import Asset
        from models.accessory import Accessory
        from models.customer_user import CustomerUser
        from models.company import Company
        from models.user import User, UserType
        
        query = request.args.get('q', '').strip()
        result_type = request.args.get('type', 'all')  # all, assets, tickets, accessories, customers
        limit = request.args.get('limit', 10, type=int)
        
        if not query:
            return jsonify({'results': []})
        
        db_session = db_manager.get_session()
        user = db_session.query(User).get(session['user_id'])
        
        results = {
            'query': query,
            'assets': [],
            'tickets': [],
            'accessories': [],
            'customers': [],
            'related_tickets': []
        }
        
        # Search assets
        if result_type in ['all', 'assets']:
            asset_query = db_session.query(Asset)
            
            # Apply user-based filters
            if user.user_type == UserType.CLIENT and user.company:
                asset_query = asset_query.filter(
                    or_(
                        Asset.company_id == user.company_id,
                        Asset.customer == user.company.name
                    )
                )
            elif user.user_type == UserType.COUNTRY_ADMIN and user.assigned_country:
                asset_query = asset_query.filter(Asset.country == user.assigned_country.value)
            
            assets = asset_query.filter(
                or_(
                    Asset.name.ilike(f'%{query}%'),
                    Asset.model.ilike(f'%{query}%'),
                    Asset.serial_num.ilike(f'%{query}%'),
                    Asset.asset_tag.ilike(f'%{query}%'),
                    Asset.category.ilike(f'%{query}%'),
                    Asset.customer.ilike(f'%{query}%'),
                    Asset.hardware_type.ilike(f'%{query}%'),
                    Asset.cpu_type.ilike(f'%{query}%')
                )
            ).limit(limit).all()
            
            for asset in assets:
                results['assets'].append({
                    'id': asset.id,
                    'asset_tag': asset.asset_tag or '',
                    'serial_num': asset.serial_num or '',
                    'name': asset.name or '',
                    'model': asset.model or '',
                    'status': asset.status.value if asset.status else '',
                    'customer': asset.customer or '',
                    'url': f"/inventory/asset/{asset.id}"
                })
        
        # Search tickets
        if result_type in ['all', 'tickets']:
            ticket_query = db_session.query(Ticket)
            
            # Apply user-based filters
            if user.user_type == UserType.COUNTRY_ADMIN and user.assigned_country:
                ticket_query = ticket_query.filter(Ticket.country == user.assigned_country.value)
            
            tickets = ticket_query.filter(
                or_(
                    Ticket.subject.ilike(f'%{query}%'),
                    Ticket.description.ilike(f'%{query}%'),
                    Ticket.notes.ilike(f'%{query}%'),
                    Ticket.serial_number.ilike(f'%{query}%'),
                    Ticket.damage_description.ilike(f'%{query}%'),
                    Ticket.return_description.ilike(f'%{query}%'),
                    Ticket.shipping_tracking.ilike(f'%{query}%'),
                    Ticket.return_tracking.ilike(f'%{query}%'),
                    Ticket.shipping_tracking_2.ilike(f'%{query}%'),
                    *([Ticket.id == int(query.replace('TICK-', '').replace('#', ''))] 
                      if query.replace('TICK-', '').replace('#', '').isdigit() else [])
                )
            ).limit(limit).all()
            
            for ticket in tickets:
                results['tickets'].append({
                    'id': ticket.id,
                    'display_id': ticket.display_id,
                    'subject': ticket.subject or '',
                    'category': ticket.category.value if ticket.category else '',
                    'status': ticket.status.value if ticket.status else '',
                    'priority': ticket.priority.value if ticket.priority else '',
                    'created_at': ticket.created_at.strftime('%Y-%m-%d') if ticket.created_at else '',
                    'url': f"/tickets/{ticket.id}"
                })
        
        # Search accessories
        if result_type in ['all', 'accessories']:
            accessory_query = db_session.query(Accessory)
            
            # Apply user-based filters
            if user.user_type == UserType.COUNTRY_ADMIN and user.assigned_country:
                accessory_query = accessory_query.filter(Accessory.country == user.assigned_country.value)
            
            accessories = accessory_query.filter(
                or_(
                    Accessory.name.ilike(f'%{query}%'),
                    Accessory.category.ilike(f'%{query}%'),
                    Accessory.manufacturer.ilike(f'%{query}%'),
                    Accessory.model_no.ilike(f'%{query}%'),
                    Accessory.notes.ilike(f'%{query}%')
                )
            ).limit(limit).all()
            
            for accessory in accessories:
                results['accessories'].append({
                    'id': accessory.id,
                    'name': accessory.name or '',
                    'category': accessory.category or '',
                    'manufacturer': accessory.manufacturer or '',
                    'total_quantity': accessory.total_quantity or 0,
                    'available_quantity': accessory.available_quantity or 0,
                    'status': accessory.status or '',
                    'url': f"/inventory/accessory/{accessory.id}"
                })
        
        # Search customers - apply company filtering for non-SUPER_ADMIN users
        if result_type in ['all', 'customers']:
            customers_query = db_session.query(CustomerUser).join(Company, CustomerUser.company_id == Company.id, isouter=True)
            
            # Apply permission-based filtering for non-SUPER_ADMIN users
            if user.user_type != UserType.SUPER_ADMIN and user.company_id:
                from models.company_customer_permission import CompanyCustomerPermission
                
                # Get companies this user's company has permission to view customers from
                permitted_company_ids = db_session.query(CompanyCustomerPermission.customer_company_id)\
                    .filter(
                        CompanyCustomerPermission.company_id == user.company_id,
                        CompanyCustomerPermission.can_view == True
                    ).subquery()
                
                # Users can see their own company's customers plus any permitted ones
                customers_query = customers_query.filter(
                    or_(
                        CustomerUser.company_id == user.company_id,  # Own company customers
                        CustomerUser.company_id.in_(permitted_company_ids)  # Permitted customers
                    )
                )
            
            customers = customers_query.filter(
                or_(
                    CustomerUser.name.ilike(f'%{query}%'),
                    CustomerUser.email.ilike(f'%{query}%'),
                    CustomerUser.contact_number.ilike(f'%{query}%'),
                    CustomerUser.address.ilike(f'%{query}%'),
                    Company.name.ilike(f'%{query}%')
                )
            ).limit(limit).all()
            
            for customer in customers:
                results['customers'].append({
                    'id': customer.id,
                    'name': customer.name or '',
                    'email': customer.email or '',
                    'contact_number': customer.contact_number or '',
                    'company': customer.company.name if customer.company else '',
                    'address': customer.address or '',
                    'url': f"/inventory/customer-users/{customer.id}"
                })
        
        # Find related tickets for found assets
        if result_type in ['all', 'assets'] and results['assets']:
            asset_serial_numbers = [a['serial_num'] for a in results['assets'] if a['serial_num']]
            asset_tags = [a['asset_tag'] for a in results['assets'] if a['asset_tag']]
            asset_ids = [a['id'] for a in results['assets']]
            
            if asset_serial_numbers or asset_tags or asset_ids:
                related_tickets_query = db_session.query(Ticket).filter(
                    or_(
                        Ticket.serial_number.in_(asset_serial_numbers) if asset_serial_numbers else False,
                        Ticket.asset_id.in_(asset_ids) if asset_ids else False,
                        *[Ticket.description.ilike(f'%{tag}%') for tag in asset_tags if tag],
                        *[Ticket.notes.ilike(f'%{tag}%') for tag in asset_tags if tag],
                        *[Ticket.description.ilike(f'%{serial}%') for serial in asset_serial_numbers if serial],
                        *[Ticket.notes.ilike(f'%{serial}%') for serial in asset_serial_numbers if serial]
                    )
                )
                
                related_tickets = related_tickets_query.limit(limit).all()
                ticket_ids = [t['id'] for t in results['tickets']]
                related_tickets = [t for t in related_tickets if t.id not in ticket_ids]
                
                for ticket in related_tickets:
                    results['related_tickets'].append({
                        'id': ticket.id,
                        'display_id': ticket.display_id,
                        'subject': ticket.subject or '',
                        'category': ticket.category.value if ticket.category else '',
                        'status': ticket.status.value if ticket.status else '',
                        'asset_info': ticket.asset.asset_tag if ticket.asset else ticket.serial_number,
                        'url': f"/tickets/{ticket.id}"
                    })
        
        return jsonify(results)
        
    except Exception as e:
        current_app.logger.error(f"Error in unified search: {str(e)}")
        return jsonify({'error': 'Search failed'}), 500
    finally:
        db_session.close()


# Multiple Tracking API Endpoints for Asset Checkout (claw)

@api_bp.route('/tickets/<int:ticket_id>/available-items', methods=['GET'])
@login_required
def get_ticket_available_items(ticket_id):
    """Get assets and accessories available for assignment to tracking"""
    db_session = db_manager.get_session()
    try:
        # Verify ticket exists
        ticket = db_session.query(Ticket).get(ticket_id)
        if not ticket:
            return jsonify({'error': 'Ticket not found'}), 404
        
        # Get assets associated with the ticket
        ticket_assets = []
        if ticket.assets:
            for asset in ticket.assets:
                ticket_assets.append({
                    'id': asset.id,
                    'asset_tag': asset.asset_tag,
                    'model': asset.model,
                    'serial_num': asset.serial_num
                })
        
        # Get accessories associated with the ticket
        ticket_accessories = []
        if ticket.accessories:
            for accessory in ticket.accessories:
                ticket_accessories.append({
                    'id': accessory.id,
                    'name': accessory.name,
                    'category': accessory.category,
                    'quantity': accessory.quantity
                })
        
        return jsonify({
            'ticket_id': ticket_id,
            'assets': ticket_assets,
            'accessories': ticket_accessories
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting available items: {str(e)}")
        return jsonify({'error': 'Failed to get available items'}), 500
    finally:
        db_session.close()


@api_bp.route('/tickets/<int:ticket_id>/tracking', methods=['GET'])
@login_required
def get_ticket_tracking(ticket_id):
    """Get all tracking numbers for a ticket with their assigned items"""
    db_session = db_manager.get_session()
    try:
        # Verify ticket exists and user has access
        ticket = db_session.query(Ticket).get(ticket_id)
        if not ticket:
            return jsonify({'error': 'Ticket not found'}), 404
            
        # Get all tracking numbers for this ticket
        tracking_numbers = db_session.query(TicketTracking)\
            .filter(TicketTracking.ticket_id == ticket_id)\
            .order_by(TicketTracking.sequence_number).all()
        
        result = {
            'ticket_id': ticket_id,
            'tracking_numbers': []
        }
        
        for tracking in tracking_numbers:
            # Get assigned items
            assigned_assets = []
            assigned_accessories = []
            
            for assignment in tracking.item_assignments:
                if assignment.asset:
                    assigned_assets.append({
                        'id': assignment.asset.id,
                        'asset_tag': assignment.asset.asset_tag,
                        'model': assignment.asset.model,
                        'serial_num': assignment.asset.serial_num
                    })
                elif assignment.accessory:
                    assigned_accessories.append({
                        'id': assignment.accessory.id,
                        'name': assignment.accessory.name,
                        'category': assignment.accessory.category,
                        'quantity': assignment.accessory.quantity
                    })
            
            result['tracking_numbers'].append({
                'id': tracking.id,
                'tracking_number': tracking.tracking_number,
                'carrier': tracking.carrier,
                'status': tracking.status,
                'tracking_type': tracking.tracking_type,
                'sequence_number': tracking.sequence_number,
                'notes': tracking.notes,
                'created_at': tracking.created_at.isoformat() if tracking.created_at else None,
                'assigned_assets': assigned_assets,
                'assigned_accessories': assigned_accessories
            })
        
        return jsonify(result)
        
    except Exception as e:
        current_app.logger.error(f"Error getting tracking: {str(e)}")
        return jsonify({'error': 'Failed to get tracking'}), 500
    finally:
        db_session.close()


@api_bp.route('/tickets/<int:ticket_id>/tracking', methods=['POST'])
@login_required
def add_ticket_tracking(ticket_id):
    """Add a new tracking number to a ticket"""
    db_session = db_manager.get_session()
    try:
        # Verify ticket exists
        ticket = db_session.query(Ticket).get(ticket_id)
        if not ticket:
            return jsonify({'error': 'Ticket not found'}), 404
        
        # Get form data
        tracking_number = request.form.get('tracking_number', '').strip()
        carrier = request.form.get('carrier', 'claw')
        notes = request.form.get('notes', '')
        
        if not tracking_number:
            return jsonify({'error': 'Tracking number is required'}), 400
        
        # Get the next sequence number
        max_sequence = db_session.query(TicketTracking.sequence_number)\
            .filter(TicketTracking.ticket_id == ticket_id)\
            .order_by(TicketTracking.sequence_number.desc()).first()
        
        next_sequence = (max_sequence[0] + 1) if max_sequence else 1
        
        # Create new tracking record
        new_tracking = TicketTracking(
            ticket_id=ticket_id,
            tracking_number=tracking_number,
            carrier=carrier,
            status='Pending',
            tracking_type='outbound',
            sequence_number=next_sequence,
            notes=notes
        )
        
        db_session.add(new_tracking)
        db_session.commit()
        
        return jsonify({
            'success': True,
            'tracking_id': new_tracking.id,
            'message': f'Tracking number {tracking_number} added successfully'
        })
        
    except Exception as e:
        db_session.rollback()
        current_app.logger.error(f"Error adding tracking: {str(e)}")
        return jsonify({'error': 'Failed to add tracking'}), 500
    finally:
        db_session.close()


@api_bp.route('/tracking/<int:tracking_id>', methods=['DELETE'])
@login_required
def delete_tracking(tracking_id):
    """Delete a tracking number"""
    db_session = db_manager.get_session()
    try:
        tracking = db_session.query(TicketTracking).get(tracking_id)
        if not tracking:
            return jsonify({'error': 'Tracking not found'}), 404
        
        # Store ticket_id for resequencing
        ticket_id = tracking.ticket_id
        sequence_to_delete = tracking.sequence_number
        
        # Delete the tracking (cascade will delete assignments)
        db_session.delete(tracking)
        
        # Resequence remaining tracking numbers
        remaining_tracking = db_session.query(TicketTracking)\
            .filter(
                TicketTracking.ticket_id == ticket_id,
                TicketTracking.sequence_number > sequence_to_delete
            ).all()
        
        for track in remaining_tracking:
            track.sequence_number -= 1
        
        db_session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Tracking number deleted successfully'
        })
        
    except Exception as e:
        db_session.rollback()
        current_app.logger.error(f"Error deleting tracking: {str(e)}")
        return jsonify({'error': 'Failed to delete tracking'}), 500
    finally:
        db_session.close()


@api_bp.route('/tracking/<int:tracking_id>/items', methods=['POST'])
@login_required
def add_item_to_tracking(tracking_id):
    """Add an asset or accessory to a tracking number"""
    db_session = db_manager.get_session()
    try:
        tracking = db_session.query(TicketTracking).get(tracking_id)
        if not tracking:
            return jsonify({'error': 'Tracking not found'}), 404
        
        data = request.get_json()
        item_type = data.get('item_type')  # 'asset' or 'accessory'
        item_id = data.get('item_id')
        
        if not item_type or not item_id:
            return jsonify({'error': 'Item type and ID are required'}), 400
        
        # Check if item already assigned to any tracking for this ticket
        existing_assignment = db_session.query(TrackingItemAssignment)\
            .join(TicketTracking)\
            .filter(
                TicketTracking.ticket_id == tracking.ticket_id,
                ((TrackingItemAssignment.asset_id == item_id) if item_type == 'asset' 
                 else (TrackingItemAssignment.accessory_id == item_id))
            ).first()
        
        if existing_assignment:
            return jsonify({'error': 'Item is already assigned to a tracking number'}), 400
        
        # Create new assignment
        assignment = TrackingItemAssignment(
            tracking_id=tracking_id,
            assigned_by_id=session.get('user_id')
        )
        
        if item_type == 'asset':
            # Verify asset exists and belongs to ticket
            asset = db_session.query(Asset).get(item_id)
            if not asset:
                return jsonify({'error': 'Asset not found'}), 404
            assignment.asset_id = item_id
        else:
            # Verify accessory exists and belongs to ticket
            accessory = db_session.query(TicketAccessory).get(item_id)
            if not accessory or accessory.ticket_id != tracking.ticket_id:
                return jsonify({'error': 'Accessory not found or does not belong to this ticket'}), 404
            assignment.accessory_id = item_id
        
        db_session.add(assignment)
        db_session.commit()
        
        return jsonify({
            'success': True,
            'message': f'{item_type.capitalize()} assigned to tracking successfully'
        })
        
    except Exception as e:
        db_session.rollback()
        current_app.logger.error(f"Error adding item to tracking: {str(e)}")
        return jsonify({'error': 'Failed to assign item'}), 500
    finally:
        db_session.close()


@api_bp.route('/tracking/<int:tracking_id>/items', methods=['DELETE'])
@login_required
def remove_item_from_tracking(tracking_id):
    """Remove an asset or accessory from a tracking number"""
    db_session = db_manager.get_session()
    try:
        data = request.get_json()
        item_type = data.get('item_type')
        item_id = data.get('item_id')
        
        if not item_type or not item_id:
            return jsonify({'error': 'Item type and ID are required'}), 400
        
        # Find and delete the assignment
        query = db_session.query(TrackingItemAssignment)\
            .filter(TrackingItemAssignment.tracking_id == tracking_id)
        
        if item_type == 'asset':
            query = query.filter(TrackingItemAssignment.asset_id == item_id)
        else:
            query = query.filter(TrackingItemAssignment.accessory_id == item_id)
        
        assignment = query.first()
        
        if not assignment:
            return jsonify({'error': 'Assignment not found'}), 404
        
        db_session.delete(assignment)
        db_session.commit()
        
        return jsonify({
            'success': True,
            'message': f'{item_type.capitalize()} removed from tracking successfully'
        })
        
    except Exception as e:
        db_session.rollback()
        current_app.logger.error(f"Error removing item from tracking: {str(e)}")
        return jsonify({'error': 'Failed to remove item'}), 500
    finally:
        db_session.close()


@api_bp.route('/tracking/<int:tracking_id>/refresh', methods=['POST'])
@login_required
def refresh_tracking_status(tracking_id):
    """Refresh tracking status from carrier API"""
    db_session = db_manager.get_session()
    try:
        tracking = db_session.query(TicketTracking).get(tracking_id)
        if not tracking:
            return jsonify({'error': 'Tracking not found'}), 404
        
        # Import the tracking utilities
        from utils.shipment_tracker import ShipmentTracker
        tracker = ShipmentTracker()
        
        # Get tracking status
        try:
            tracking_info = tracker.track_shipment(tracking.tracking_number, tracking.carrier)
            
            if tracking_info and 'status' in tracking_info:
                # Update tracking status
                tracking.status = tracking_info['status']
                tracking.updated_at = datetime.datetime.now()
                
                # If delivered, check if we should auto-close the ticket
                if tracking.status == 'Delivered':
                    # Check if all tracking numbers are delivered
                    all_tracking = db_session.query(TicketTracking)\
                        .filter(TicketTracking.ticket_id == tracking.ticket_id).all()
                    
                    all_delivered = all(t.status == 'Delivered' for t in all_tracking)
                    
                    if all_delivered and tracking.ticket:
                        # Auto-close the ticket
                        from models.ticket import TicketStatus
                        tracking.ticket.status = TicketStatus.RESOLVED_DELIVERED
                        tracking.ticket.updated_at = datetime.datetime.now()
                
                db_session.commit()
                
                return jsonify({
                    'success': True,
                    'status': tracking.status,
                    'message': 'Tracking status updated successfully'
                })
            else:
                return jsonify({
                    'success': True,
                    'message': 'No tracking updates available'
                })
                
        except Exception as tracker_error:
            current_app.logger.error(f"Tracker error: {str(tracker_error)}")
            return jsonify({
                'success': False,
                'error': 'Failed to get tracking information from carrier'
            })
        
    except Exception as e:
        db_session.rollback()
        current_app.logger.error(f"Error refreshing tracking: {str(e)}")
        return jsonify({'error': 'Failed to refresh tracking'}), 500
    finally:
        db_session.close() 