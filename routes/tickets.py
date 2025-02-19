import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from utils.auth_decorators import login_required, admin_required
from utils.snipeit_api import get_all_assets, get_asset, get_all_accessories
from models.ticket import Ticket, TicketCategory, TicketPriority
from utils.store_instances import (
    ticket_store,
    user_store,
    queue_store,
    inventory_store,
    comment_store,
    activity_store
)
from utils.db_manager import DatabaseManager

tickets_bp = Blueprint('tickets', __name__, url_prefix='/tickets')
db_manager = DatabaseManager()

@tickets_bp.route('/')
@login_required
def list_tickets():
    user_id = session['user_id']
    user_type = session['user_type']
    tickets = ticket_store.get_user_tickets(user_id, user_type)
    return render_template('tickets/list.html', tickets=tickets)

@tickets_bp.route('/new', methods=['GET', 'POST'])
@login_required
def create_ticket():
    if request.method == 'GET':
        return render_template('tickets/create.html', 
                             priorities=list(TicketPriority),
                             categories=list(TicketCategory))
    if request.method == 'POST':
        subject = request.form.get('subject')
        description = request.form.get('description')
        category = request.form.get('category')
        priority = request.form.get('priority')
        
        user_id = session['user_id']
        
        ticket_id = ticket_store.create_ticket(
            subject=subject,
            description=description,
            requester_id=user_id,
            category=category,
            priority=priority
        )
        
        flash('Ticket created successfully')
        return redirect(url_for('tickets.view_ticket', ticket_id=ticket_id))
    
    return render_template('tickets/create.html',
                         categories=list(TicketCategory),
                         priorities=list(TicketPriority))

@tickets_bp.route('/<int:ticket_id>')
@login_required
def view_ticket(ticket_id):
    ticket = ticket_store.get_ticket(ticket_id)
    if not ticket:
        flash('Ticket not found')
        return redirect(url_for('tickets.list_tickets'))
    
    comments = comment_store.get_ticket_comments(ticket_id)
    
    # Add user information to comments
    for comment in comments:
        comment.user = user_store.get_user_by_id(comment.user_id)

    # Convert users to a dictionary format that can be serialized to JSON
    users_dict = {}
    for user in user_store.get_all_users():
        users_dict[str(user.id)] = {
            'id': user.id,
            'username': user.username,
            'user_type': user.user_type,
            'company': user.company,
            'role': user.role
        }

    # Get owner information
    owner = None
    if ticket.assigned_to_id:
        owner = user_store.get_user_by_id(ticket.assigned_to_id)
        if not owner:
            # If owner not found, clear the assigned_to_id
            ticket.assigned_to_id = None
            ticket_store.save_tickets()

    queues = {q.id: q for q in queue_store.get_all_queues()}
    snipeit_assets = get_all_assets()
    snipeit_accessories = get_all_accessories()
    
    asset_details = None
    if ticket.asset_id:
        asset_details = get_asset(ticket.asset_id)
    
    return render_template(
        'tickets/view.html',
        ticket=ticket,
        comments=sorted(comments, key=lambda x: x.created_at),
        queues=queues,
        users=users_dict,
        owner=owner,  # Pass owner separately
        snipeit_assets=snipeit_assets,
        snipeit_accessories=snipeit_accessories,
        asset_details=asset_details
    )

@tickets_bp.route('/<int:ticket_id>/comment', methods=['POST'])
@login_required
def add_comment(ticket_id):
    content = request.form.get('content')
    if not content:
        flash('Comment cannot be empty')
        return redirect(url_for('tickets.view_ticket', ticket_id=ticket_id))

    comment = comment_store.add_comment(
        ticket_id=ticket_id,
        user_id=session['user_id'],
        content=content
    )
    
    flash('Comment added successfully')
    return redirect(url_for('tickets.view_ticket', ticket_id=ticket_id))

@tickets_bp.route('/queues')
@login_required
def list_queues():
    queues = queue_store.get_all_queues()
    return render_template('tickets/queues.html', queues=queues)

@tickets_bp.route('/queues/<int:queue_id>')
@login_required
def view_queue(queue_id):
    queue = queue_store.get_queue(queue_id)
    if not queue:
        flash('Queue not found')
        return redirect(url_for('tickets.list_queues'))
    
    tickets = [ticket_store.get_ticket(ticket_id) for ticket_id in queue.tickets]
    return render_template('tickets/queue_view.html', queue=queue, tickets=tickets)

@tickets_bp.route('/<int:ticket_id>/assign', methods=['POST'])
@admin_required
def assign_ticket(ticket_id):
    assigned_to_id = request.form.get('assigned_to_id')
    queue_id = request.form.get('queue_id')
    
    if queue_id:
        queue_id = int(queue_id)
    if assigned_to_id:
        assigned_to_id = int(assigned_to_id)

    ticket = ticket_store.assign_ticket(ticket_id, assigned_to_id, queue_id)
    if ticket:
        flash('Ticket assigned successfully')
    else:
        flash('Error assigning ticket')
    
    return redirect(url_for('tickets.view_ticket', ticket_id=ticket_id))

@tickets_bp.route('/<int:ticket_id>/status', methods=['POST'])
@admin_required
def change_status(ticket_id):
    ticket = ticket_store.get_ticket(ticket_id)
    if not ticket:
        flash('Ticket not found')
        return redirect(url_for('tickets.list_tickets'))
    
    new_status = request.form.get('status')
    comment = request.form.get('status_comment')
    
    if new_status in Ticket.STATUS_OPTIONS:
        ticket.change_status(new_status, comment)
        flash('Status updated successfully')
    else:
        flash('Invalid status')
    
    return redirect(url_for('tickets.view_ticket', ticket_id=ticket.id))

@tickets_bp.route('/<int:ticket_id>/assign-owner', methods=['POST'])
@admin_required
def assign_case_owner(ticket_id):
    ticket = ticket_store.get_ticket(ticket_id)
    if not ticket:
        flash('Ticket not found')
        return redirect(url_for('tickets.list_tickets'))
    
    owner_id = request.form.get('owner_id')
    if owner_id:
        owner_id = int(owner_id)
        # Check if user exists
        owner = user_store.get_user_by_id(owner_id)
        if owner:
            previous_owner_id = ticket.assigned_to_id
            ticket.assign_case_owner(owner_id)
            
            # Create activity for the new owner
            activity_store.add_activity(
                user_id=owner_id,
                type='case_assigned',
                content=f"You were assigned as owner of ticket {ticket.display_id}: {ticket.subject}",
                reference_id=ticket.id
            )
            
            # If there was a previous owner, notify them as well
            if previous_owner_id and previous_owner_id != owner_id:
                activity_store.add_activity(
                    user_id=previous_owner_id,
                    type='case_unassigned',
                    content=f"You were unassigned from ticket {ticket.display_id}: {ticket.subject}",
                    reference_id=ticket.id
                )
                
            flash('Case owner updated successfully')
        else:
            flash('Selected user not found')
    else:
        # If unassigning, notify the previous owner
        if ticket.assigned_to_id:
            activity_store.add_activity(
                user_id=ticket.assigned_to_id,
                type='case_unassigned',
                content=f"You were unassigned from ticket {ticket.display_id}: {ticket.subject}",
                reference_id=ticket.id
            )
        ticket.assign_case_owner(None)  # Unassign
        flash('Case owner removed')
    
    return redirect(url_for('tickets.view_ticket', ticket_id=ticket_id))

@tickets_bp.route('/<int:ticket_id>/update', methods=['POST'])
@login_required
def update_ticket(ticket_id):
    if session['user_type'] != 'admin':
        flash('Only administrators can update tickets')
        return redirect(url_for('tickets.view_ticket', ticket_id=ticket_id))

    ticket = ticket_store.get_ticket(ticket_id)
    if not ticket:
        flash('Ticket not found')
        return redirect(url_for('tickets.list_tickets'))

    # Update ticket fields
    ticket.status = request.form.get('status', ticket.status)
    ticket.priority = request.form.get('priority', ticket.priority)
    assigned_to_id = request.form.get('assigned_to_id')
    if assigned_to_id:
        ticket.assigned_to_id = int(assigned_to_id)

    # Save changes
    ticket_store.save_tickets()
    flash('Ticket updated successfully')
    return redirect(url_for('tickets.view_ticket', ticket_id=ticket_id))

@tickets_bp.route('/<int:ticket_id>/shipment', methods=['POST'])
@admin_required
def add_shipment(ticket_id):
    ticket = ticket_store.get_ticket(ticket_id)
    if not ticket:
        flash('Ticket not found')
        return redirect(url_for('tickets.list_tickets'))
    
    tracking_number = request.form.get('tracking_number')
    description = request.form.get('description')
    
    if tracking_number:
        ticket.add_shipment(tracking_number, description)
        flash('Shipment added successfully')
    else:
        flash('Tracking number is required')
    
    return redirect(url_for('tickets.view_ticket', ticket_id=ticket_id))

@tickets_bp.route('/<int:ticket_id>/shipment/update', methods=['POST'])
@admin_required
def update_shipment_tracking(ticket_id):
    ticket = ticket_store.get_ticket(ticket_id)
    if not ticket or not ticket.shipment:
        flash('Ticket or shipment not found')
        return redirect(url_for('tickets.view_ticket', ticket_id=ticket_id))
    
    status = request.form.get('status')
    details = request.form.get('details')
    
    if status:
        ticket.shipment.update_tracking(status, [details] if details else None)
        flash('Tracking information updated')
    else:
        flash('Status is required')
    
    return redirect(url_for('tickets.view_ticket', ticket_id=ticket_id))

@tickets_bp.route('/<int:ticket_id>/asset', methods=['POST'])
@admin_required
def assign_asset(ticket_id):
    ticket = ticket_store.get_ticket(ticket_id)
    if not ticket:
        flash('Ticket not found')
        return redirect(url_for('tickets.list_tickets'))
    
    asset_id = request.form.get('asset_id')
    if asset_id:
        asset_id = int(asset_id)
        # Check if asset exists in Snipe-IT
        asset = get_asset(asset_id)
        if not asset:
            flash('Asset not found in Snipe-IT')
            return redirect(url_for('tickets.view_ticket', ticket_id=ticket_id))
        
        ticket.asset_id = asset_id
        flash('Asset assigned successfully')
    
    return redirect(url_for('tickets.view_ticket', ticket_id=ticket_id))

@tickets_bp.route('/<int:ticket_id>/accessory', methods=['POST'])
@admin_required
def assign_accessory(ticket_id):
    ticket = ticket_store.get_ticket(ticket_id)
    if not ticket:
        flash('Ticket not found')
        return redirect(url_for('tickets.list_tickets'))
    
    accessory_id = request.form.get('accessory_id')
    if accessory_id:
        accessory_id = int(accessory_id)
        # Here you would typically check out the accessory in Snipe-IT
        # and store the reference in your ticket
        ticket.accessory_id = accessory_id
        flash('Accessory assigned successfully')
    
    return redirect(url_for('tickets.view_ticket', ticket_id=ticket_id))

@tickets_bp.route('/<int:ticket_id>/rma/pickup', methods=['POST'])
@admin_required
def add_rma_pickup(ticket_id):
    ticket = ticket_store.get_ticket(ticket_id)
    if not ticket or not ticket.is_rma:
        flash('Invalid RMA ticket')
        return redirect(url_for('tickets.list_tickets'))
    
    tracking_number = request.form.get('pickup_tracking')
    description = request.form.get('pickup_description')
    
    if tracking_number:
        ticket.add_rma_shipment(
            tracking_number=tracking_number,
            is_return=True,
            description=description
        )
        ticket.update_rma_status('Item Shipped')
        ticket_store.save_tickets()
        flash('Pickup tracking added successfully')
    else:
        flash('Tracking number is required')
    
    return redirect(url_for('tickets.view_ticket', ticket_id=ticket_id))

@tickets_bp.route('/<int:ticket_id>/rma/replacement', methods=['POST'])
@admin_required
def add_rma_replacement(ticket_id):
    ticket = ticket_store.get_ticket(ticket_id)
    if not ticket or not ticket.is_rma:
        flash('Invalid RMA ticket')
        return redirect(url_for('tickets.list_tickets'))
    
    tracking_number = request.form.get('replacement_tracking')
    description = request.form.get('replacement_description')
    
    if tracking_number:
        ticket.add_rma_shipment(
            tracking_number=tracking_number,
            is_return=False,
            description=description
        )
        ticket.update_rma_status('Replacement Shipped')
        ticket_store.save_tickets()
        flash('Replacement tracking added successfully')
    else:
        flash('Tracking number is required')
    
    return redirect(url_for('tickets.view_ticket', ticket_id=ticket_id))

@tickets_bp.route('/composer', methods=['GET', 'POST'])
@admin_required
def ticket_composer():
    if request.method == 'POST':
        template_name = request.form.get('template_name')
        subject = request.form.get('subject')
        description = request.form.get('description')
        category = request.form.get('category')
        priority = request.form.get('priority')
        required_fields = request.form.getlist('required_fields')
        
        # Save the template
        template = {
            'name': template_name,
            'subject': subject,
            'description': description,
            'category': category,
            'priority': priority,
            'required_fields': required_fields
        }
        
        # Add to templates store
        ticket_store.save_template(template)
        flash('Ticket template saved successfully')
        return redirect(url_for('tickets.ticket_composer'))
    
    # Get existing templates
    templates = ticket_store.get_templates()
    
    return render_template(
        'tickets/composer.html',
        categories=[category.value for category in TicketCategory],
        priorities=[priority.value for priority in TicketPriority],
        templates=templates,
        field_options=[
            {'id': 'serial_number', 'label': 'Serial Number'},
            {'id': 'warranty_number', 'label': 'Warranty Number'},
            {'id': 'asset_tag', 'label': 'Asset Tag'},
            {'id': 'location', 'label': 'Location'},
            {'id': 'department', 'label': 'Department'},
            {'id': 'contact_info', 'label': 'Contact Information'},
            {'id': 'due_date', 'label': 'Due Date'}
        ]
    )

@tickets_bp.route('/template/<template_id>', methods=['GET'])
@admin_required
def get_template(template_id):
    """Get template by ID"""
    templates = ticket_store.get_templates()
    template = next((t for t in templates if t['id'] == template_id), None)
    if template:
        return jsonify(template)
    return jsonify({'error': 'Template not found'}), 404

@tickets_bp.route('/template/<template_id>/delete', methods=['POST'])
@admin_required
def delete_template(template_id):
    """Delete a template"""
    ticket_store.delete_template(template_id)
    flash('Template deleted successfully')
    return redirect(url_for('tickets.ticket_composer'))

@tickets_bp.route('/<int:ticket_id>/track/<tracking_type>', methods=['POST'])
@admin_required
def update_tracking_status(ticket_id, tracking_type):
    """Update tracking status from 17track"""
    ticket = ticket_store.get_ticket(ticket_id)
    if not ticket:
        return jsonify({'error': 'Ticket not found'}), 404
    
    data = request.get_json()
    
    try:
        tracking_info = data.get('data', {}).get('track', {}).get('z0', {})
        status = tracking_info.get('status', 'Unknown')
        
        # Get the latest event
        events = tracking_info.get('track', [])
        if events:
            latest_event = events[0]  # Most recent event is first
            details = {
                'message': latest_event.get('z', ''),
                'location': latest_event.get('c', ''),
                'time': latest_event.get('a', datetime.now().isoformat())
            }
            
            # Check if package is delivered
            is_delivered = (
                'delivered' in latest_event.get('z', '').lower() or
                status.lower() == 'delivered' or
                latest_event.get('z', '').lower().startswith('delivered')
            )
            
            # Update shipment tracking
            if tracking_type == 'regular' and ticket.shipment:
                ticket.shipment.update_tracking(status, details)
                if is_delivered:
                    ticket.status = 'Resolved'
                    ticket.updated_at = datetime.now()
            elif tracking_type == 'rma_return' and ticket.return_tracking:
                ticket.return_tracking.update_tracking(status, details)
                if is_delivered:
                    ticket.update_rma_status('Item Received')
            elif tracking_type == 'rma_replacement' and ticket.replacement_tracking:
                ticket.replacement_tracking.update_tracking(status, details)
                if is_delivered:
                    ticket.update_rma_status('Completed')
                    ticket.status = 'Resolved'
            
            ticket_store.save_tickets()
            return jsonify({
                'success': True,
                'status': status,
                'ticket_status': ticket.status,
                'rma_status': ticket.rma_status if ticket.is_rma else None
            })
            
        return jsonify({'success': True})
        
    except Exception as e:
        print(f"Error updating tracking: {str(e)}")
        return jsonify({'error': str(e)}), 500

# Add other routes back as needed... 