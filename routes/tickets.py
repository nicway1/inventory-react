import datetime
import os
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify, send_file
from utils.auth_decorators import login_required, admin_required
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
from models.asset import Asset, AssetStatus
from werkzeug.utils import secure_filename
from models.customer_user import CustomerUser
from models.ticket_attachment import TicketAttachment
import requests
from bs4 import BeautifulSoup
import trackingmore
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Define allowed file extensions
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'}

tickets_bp = Blueprint('tickets', __name__, url_prefix='/tickets')
db_manager = DatabaseManager()

# Initialize TrackingMore API key
trackingmore.api_key = os.environ.get('TRACKINGMORE_API_KEY', 'your_api_key_here')

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
    print("Entering create_ticket route")  # Debug log
    db_session = db_manager.get_session()
    try:
        # Get all available assets for the dropdown
        assets = db_session.query(Asset).filter(
            Asset.status.in_([AssetStatus.IN_STOCK, AssetStatus.READY_TO_DEPLOY]),
            Asset.serial_num != None
        ).all()
        
        assets_data = [{
            'id': asset.id,
            'serial_number': asset.serial_num,
            'model': asset.model,
            'customer': asset.customer_user.company.name if asset.customer_user and asset.customer_user.company else asset.customer,
            'asset_tag': asset.asset_tag
        } for asset in assets]
        
        # Get all customers for the dropdown
        customers = db_session.query(CustomerUser).order_by(CustomerUser.name).all()

        if request.method == 'GET':
            print("Handling GET request")  # Debug log
            return render_template('tickets/create.html', 
                                assets=assets_data,
                                customers=customers,
                                priorities=list(TicketPriority))

        if request.method == 'POST':
            print("Handling POST request")  # Debug log
            
            # Log all form fields to debug
            for key, value in request.form.items():
                print(f"Form field: {key} = {value}")  # Debug log
            
            # Get common form data
            category = request.form.get('category')
            subject = request.form.get('subject')
            description = request.form.get('description')
            priority = request.form.get('priority')
            user_id = session['user_id']

            print(f"Category: {category}")  # Debug log
            print(f"Subject: {subject}")  # Debug log
            print(f"Priority: {priority}")  # Debug log

            # Validate required fields
            if not category:
                flash('Please select a category', 'error')
                return render_template('tickets/create.html',
                                    assets=assets_data,
                                    customers=customers,
                                    priorities=list(TicketPriority),
                                    form=request.form)

            # Get serial number based on category
            serial_number = None
            if category == 'ASSET_CHECKOUT' or category == 'ASSET_CHECKOUT_SINGPOST':
                serial_number = request.form.get('asset_checkout_serial')
                print(f"Asset Checkout Serial Number: {serial_number}")  # Debug log
            else:
                serial_number = request.form.get('serial_number')
                print(f"Standard Serial Number: {serial_number}")  # Debug log

            # Validate asset selection (skip for Asset Intake)
            if category != 'ASSET_INTAKE' and (not serial_number or serial_number == ""):
                flash('Please select an asset', 'error')
                return render_template('tickets/create.html',
                                    assets=assets_data,
                                    customers=customers,
                                    priorities=list(TicketPriority),
                                    form=request.form)

            # Find the asset (skip for Asset Intake)
            asset = None
            if category != 'ASSET_INTAKE':
                asset = db_session.query(Asset).filter(Asset.serial_num == serial_number).first()
                if not asset:
                    flash(f'Asset not found with serial number: {serial_number}', 'error')
                    return render_template('tickets/create.html',
                                        assets=assets_data,
                                        customers=customers,
                                        priorities=list(TicketPriority),
                                        form=request.form)

            if category == 'ASSET_CHECKOUT' or category == 'ASSET_CHECKOUT_SINGPOST':
                customer_id = request.form.get('customer_id')
                shipping_address = request.form.get('shipping_address')
                shipping_tracking = request.form.get('shipping_tracking', '')  # Optional
                notes = request.form.get('notes', '')
                
                print(f"Processing {category} - Customer ID: {customer_id}, Serial Number: {serial_number}")  # Debug log
                
                if not customer_id:
                    flash('Please select a customer', 'error')
                    return render_template('tickets/create.html',
                                        assets=assets_data,
                                        customers=customers,
                                        priorities=list(TicketPriority),
                                        form=request.form)

                if not shipping_address:
                    flash('Please provide a shipping address', 'error')
                    return render_template('tickets/create.html',
                                        assets=assets_data,
                                        customers=customers,
                                        priorities=list(TicketPriority),
                                        form=request.form)
                
                # Get customer details
                customer = db_session.query(CustomerUser).get(customer_id)
                if not customer:
                    flash('Customer not found', 'error')
                    return render_template('tickets/create.html',
                                        assets=assets_data,
                                        customers=customers,
                                        priorities=list(TicketPriority),
                                        form=request.form)
                
                description = f"""Asset Checkout Details:
Serial Number: {serial_number}
Model: {asset.model}
Asset Tag: {asset.asset_tag}

Customer Information:
Name: {customer.name}
Company: {customer.company.name if customer.company else 'N/A'}
Email: {customer.email}
Contact: {customer.contact_number}

Shipping Information:
Address: {shipping_address}
Tracking Number: {shipping_tracking if shipping_tracking else 'Not provided'}
Shipping Method: {'SingPost' if category == 'ASSET_CHECKOUT_SINGPOST' else 'Standard'}

Additional Notes:
{notes}"""

                print(f"Creating ticket with description: {description}")  # Debug log

                try:
                    # Create the ticket
                    ticket_id = ticket_store.create_ticket(
                        subject=subject,
                        description=description,
                        requester_id=user_id,
                        category=TicketCategory.ASSET_CHECKOUT_SINGPOST if category == 'ASSET_CHECKOUT_SINGPOST' else TicketCategory.ASSET_CHECKOUT,
                        priority=priority,
                        asset_id=asset.id,
                        customer_id=customer_id,
                        shipping_address=shipping_address,
                        shipping_tracking=shipping_tracking if shipping_tracking else None
                    )

                    # Update asset status and assign to customer
                    asset.customer_user_id = customer_id
                    asset.status = AssetStatus.DEPLOYED
                    db_session.commit()

                    print(f"Ticket created successfully with ID: {ticket_id}")  # Debug log
                    flash('Asset checkout ticket created successfully')
                    return redirect(url_for('tickets.view_ticket', ticket_id=ticket_id))
                except Exception as e:
                    print(f"Error creating ticket: {str(e)}")  # Debug log
                    db_session.rollback()
                    flash('Error creating ticket: ' + str(e), 'error')
                    return render_template('tickets/create.html',
                                        assets=assets_data,
                                        customers=customers,
                                        priorities=list(TicketPriority),
                                        form=request.form)

            # Handle category-specific logic
            if category == 'PIN_REQUEST':
                lock_type = request.form.get('lock_type')
                if not lock_type:
                    flash('Please select a lock type', 'error')
                    return render_template('tickets/create.html',
                                        assets=assets_data,
                                        customers=customers,
                                        priorities=list(TicketPriority),
                                        form=request.form)

                description = f"""Serial Number: {serial_number}
Model: {asset.model}
Asset Tag: {asset.asset_tag}
Customer: {asset.customer_user.company.name if asset.customer_user and asset.customer_user.company else asset.customer}
Lock Type: {lock_type}

Additional Information:
- Country: {request.form.get('country')}

Notes:
{request.form.get('notes', '')}"""

            elif category == 'ASSET_REPAIR':
                damage_description = request.form.get('damage_description')
                if not damage_description:
                    flash('Please provide a damage description', 'error')
                    return render_template('tickets/create.html',
                                        assets=assets_data,
                                        customers=customers,
                                        priorities=list(TicketPriority),
                                        form=request.form)

                apple_diagnostics = request.form.get('apple_diagnostics')
                quote_type = request.form.get('quote_type', 'assessment')
                
                # Handle image upload
                image_paths = []
                if 'image' in request.files:
                    images = request.files.getlist('image')
                    for image in images:
                        if image and image.filename:
                            # Secure the filename
                            filename = secure_filename(image.filename)
                            # Create unique filename with timestamp
                            timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
                            unique_filename = f"{timestamp}_{filename}"
                            # Save the file
                            image_path = os.path.join('uploads', 'repairs', unique_filename)
                            os.makedirs(os.path.dirname(image_path), exist_ok=True)
                            image.save(image_path)
                            image_paths.append(image_path)

                description = f"""Asset Details:
Serial Number: {serial_number}
Model: {asset.model}
Customer: {asset.customer_user.company.name if asset.customer_user and asset.customer_user.company else asset.customer}
Country: {request.form.get('country')}

Damage Description:
{damage_description}

Apple Diagnostics Code: {apple_diagnostics if apple_diagnostics else 'N/A'}

Additional Notes:
{request.form.get('notes', '')}

Images Attached: {len(image_paths)} image(s)"""

            elif category == 'ASSET_INTAKE':
                title = request.form.get('title')
                description = request.form.get('description')
                notes = request.form.get('notes', '')

                if not title or not description:
                    flash('Please provide both title and description', 'error')
                    return render_template('tickets/create.html',
                                        assets=assets_data,
                                        customers=customers,
                                        priorities=list(TicketPriority),
                                        form=request.form)

                # Handle file uploads
                packing_list_path = None
                if 'packing_list' in request.files:
                    packing_list = request.files['packing_list']
                    if packing_list and packing_list.filename:
                        # Secure the filename
                        filename = secure_filename(packing_list.filename)
                        # Create unique filename with timestamp
                        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
                        unique_filename = f"{timestamp}_{filename}"
                        # Create uploads/intake directory if it doesn't exist
                        os.makedirs('uploads/intake', exist_ok=True)
                        # Save the file
                        packing_list_path = os.path.join('uploads', 'intake', unique_filename)
                        packing_list.save(packing_list_path)

                asset_csv_path = None
                if 'asset_csv' in request.files:
                    asset_csv = request.files['asset_csv']
                    if asset_csv and asset_csv.filename:
                        # Secure the filename
                        filename = secure_filename(asset_csv.filename)
                        # Create unique filename with timestamp
                        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
                        unique_filename = f"{timestamp}_{filename}"
                        # Create uploads/intake directory if it doesn't exist
                        os.makedirs('uploads/intake', exist_ok=True)
                        # Save the file
                        asset_csv_path = os.path.join('uploads', 'intake', unique_filename)
                        asset_csv.save(asset_csv_path)

                description = f"""Asset Intake Details:
Title: {title}

Description:
{description}

Files:
- Packing List: {os.path.basename(packing_list_path) if packing_list_path else 'Not provided'}
- Asset CSV: {os.path.basename(asset_csv_path) if asset_csv_path else 'Not provided'}

Additional Notes:
{notes}"""

                try:
                    # Create the ticket
                    ticket_id = ticket_store.create_ticket(
                        subject=title,
                        description=description,
                        requester_id=user_id,
                        category=TicketCategory.ASSET_INTAKE,
                        priority=priority
                    )

                    flash('Asset intake ticket created successfully')
                    return redirect(url_for('tickets.view_ticket', ticket_id=ticket_id))
                except Exception as e:
                    print(f"Error creating ticket: {str(e)}")  # Debug log
                    db_session.rollback()
                    flash('Error creating ticket: ' + str(e), 'error')
                    return render_template('tickets/create.html',
                                        assets=assets_data,
                                        customers=customers,
                                        priorities=list(TicketPriority),
                                        form=request.form)

            # Create the ticket for other categories
            ticket_id = ticket_store.create_ticket(
                subject=subject,
                description=description,
                requester_id=user_id,
                category=category,
                priority=priority,
                asset_id=asset.id,
                country=request.form.get('country')
            )

            flash('Ticket created successfully')
            return redirect(url_for('tickets.view_ticket', ticket_id=ticket_id))

    finally:
        db_session.close()

    return render_template('tickets/create.html',
                        assets=assets_data,
                        customers=customers,
                        priorities=list(TicketPriority))

@tickets_bp.route('/<int:ticket_id>')
@login_required
def view_ticket(ticket_id):
    # Get ticket with eagerly loaded relationships
    db_session = db_manager.get_session()
    try:
        ticket = db_session.query(Ticket)\
            .options(db_manager.joinedload(Ticket.asset))\
            .options(db_manager.joinedload(Ticket.accessory))\
            .filter(Ticket.id == ticket_id)\
            .first()
            
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
        
        # Get available assets and accessories from inventory store
        available_assets = inventory_store.get_available_assets()
        available_accessories = inventory_store.get_available_accessories()
        
        return render_template(
            'tickets/view.html',
            ticket=ticket,
            comments=sorted(comments, key=lambda x: x.created_at),
            queues=queues,
            users=users_dict,
            owner=owner,  # Pass owner separately
            available_assets=available_assets,
            available_accessories=available_accessories
        )
    finally:
        db_session.close()

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
        # Check if asset exists in local inventory
        asset = inventory_store.get_asset(asset_id)
        if not asset:
            flash('Asset not found')
            return redirect(url_for('tickets.view_ticket', ticket_id=ticket_id))
        
        # Update the ticket and the asset
        ticket.asset_id = asset_id
        inventory_store.assign_asset_to_ticket(asset_id, ticket_id)
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
    quantity = request.form.get('quantity', 1, type=int)
    
    if accessory_id:
        accessory_id = int(accessory_id)
        # Check if accessory exists and has enough quantity
        accessory = inventory_store.get_accessory(accessory_id)
        if not accessory:
            flash('Accessory not found')
            return redirect(url_for('tickets.view_ticket', ticket_id=ticket_id))
            
        if accessory.available_quantity < quantity:
            flash(f'Not enough quantity available. Only {accessory.available_quantity} units available.')
            return redirect(url_for('tickets.view_ticket', ticket_id=ticket_id))
        
        # Update the ticket and the accessory
        ticket.accessory_id = accessory_id
        inventory_store.assign_accessory_to_ticket(accessory_id, ticket_id, quantity)
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

@tickets_bp.route('/clear-all', methods=['POST'])
@admin_required
def clear_all_tickets():
    """Clear all tickets from the system"""
    ticket_store.clear_all_tickets()
    flash('All tickets have been cleared successfully')
    return redirect(url_for('tickets.list_tickets'))

@tickets_bp.route('/<int:ticket_id>/track/update', methods=['POST'])
@login_required
def update_tracking(ticket_id):
    """Update tracking information from 17track widget"""
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    db_session = db_manager.get_session()
    try:
        ticket = db_session.query(Ticket).get(ticket_id)
        if not ticket:
            return jsonify({'error': 'Ticket not found'}), 404

        tracking_info = data.get('track', {}).get('z0', {})
        status = tracking_info.get('status', 'Unknown')
        events = tracking_info.get('track', [])

        status_changed = False
        
        # Update status based on tracking events
        if events:
            latest_event = events[0]  # Most recent event is first
            event_status = latest_event.get('z', '')
            
            # Check if package is delivered
            is_delivered = (
                'delivered' in event_status.lower() or
                status.lower() == 'delivered' or
                event_status.lower().startswith('delivered')
            )

            if is_delivered and ticket.status != TicketStatus.RESOLVED:
                ticket.status = TicketStatus.RESOLVED
                status_changed = True

            # Update ticket tracking information
            if ticket.shipping_tracking:
                ticket.shipping_status = status
            elif ticket.return_tracking:
                ticket.return_status = status
                if is_delivered and ticket.rma_status == RMAStatus.ITEM_SHIPPED:
                    ticket.rma_status = RMAStatus.ITEM_RECEIVED
                    status_changed = True
            elif ticket.replacement_tracking:
                ticket.replacement_status = status
                if is_delivered and ticket.rma_status == RMAStatus.REPLACEMENT_SHIPPED:
                    ticket.rma_status = RMAStatus.COMPLETED
                    ticket.status = TicketStatus.RESOLVED
                    status_changed = True

        db_session.commit()
        return jsonify({
            'success': True,
            'status_changed': status_changed,
            'status': status
        })

    except Exception as e:
        db_session.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        db_session.close()

@tickets_bp.route('/<int:ticket_id>/upload', methods=['POST'])
@login_required
def upload_attachment(ticket_id):
    db_session = db_manager.get_session()
    try:
        # Debug logging
        print("Received upload request for ticket:", ticket_id)
        print("Files in request:", request.files)
        print("Form data:", request.form)
        
        ticket = db_session.query(Ticket).get(ticket_id)
        if not ticket:
            return jsonify({'success': False, 'error': 'Ticket not found'}), 404

        if 'attachments' not in request.files:
            print("No attachments found in request.files")
            return jsonify({'success': False, 'error': 'No files uploaded'}), 400

        files = request.files.getlist('attachments')
        if not files or all(not f.filename for f in files):
            print("No valid files found in request")
            return jsonify({'success': False, 'error': 'No files selected'}), 400

        uploaded_files = []
        base_upload_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'uploads', 'tickets')
        os.makedirs(base_upload_path, exist_ok=True)
        print(f"Upload path: {base_upload_path}")

        for file in files:
            if not file or not file.filename:
                continue

            if not allowed_file(file.filename):
                print(f"Invalid file type: {file.filename}")
                return jsonify({
                    'success': False, 
                    'error': f'File type not allowed for {file.filename}. Allowed types: {", ".join(ALLOWED_EXTENSIONS)}'
                }), 400

            try:
                filename = secure_filename(file.filename)
                timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
                unique_filename = f"{ticket_id}_{timestamp}_{filename}"
                file_path = os.path.join(base_upload_path, unique_filename)
                
                print(f"Saving file to: {file_path}")
                file.save(file_path)
                
                attachment = TicketAttachment(
                    ticket_id=ticket_id,
                    filename=filename,
                    file_path=file_path,
                    file_type=file.content_type if hasattr(file, 'content_type') else None,
                    uploaded_by=session['user_id']
                )
                db_session.add(attachment)
                uploaded_files.append(filename)
                print(f"Successfully saved file: {filename}")
                
            except Exception as e:
                print(f"Error uploading {filename}: {str(e)}")
                continue
        
        if not uploaded_files:
            return jsonify({'success': False, 'error': 'No files were successfully uploaded'}), 400
        
        db_session.commit()
        return jsonify({
            'success': True,
            'message': f'Successfully uploaded {len(uploaded_files)} file(s)',
            'files': uploaded_files
        })

    except Exception as e:
        db_session.rollback()
        print(f"Upload error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db_session.close()

@tickets_bp.route('/<int:ticket_id>/attachment/<int:attachment_id>/delete', methods=['POST'])
@login_required
def delete_attachment(ticket_id, attachment_id):
    db_session = db_manager.get_session()
    try:
        attachment = db_session.query(TicketAttachment).get(attachment_id)
        if not attachment or attachment.ticket_id != ticket_id:
            return jsonify({'success': False, 'error': 'Attachment not found'}), 404

        # Delete the file from disk
        if os.path.exists(attachment.file_path):
            os.remove(attachment.file_path)

        # Delete the attachment record
        db_session.delete(attachment)
        db_session.commit()

        return jsonify({'success': True, 'message': 'Attachment deleted successfully'})

    except Exception as e:
        db_session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db_session.close()

@tickets_bp.route('/<int:ticket_id>/attachment/<int:attachment_id>/download')
@login_required
def download_attachment(ticket_id, attachment_id):
    db_session = db_manager.get_session()
    try:
        attachment = db_session.query(TicketAttachment).get(attachment_id)
        if not attachment or attachment.ticket_id != ticket_id:
            flash('Attachment not found', 'error')
            return redirect(url_for('tickets.view_ticket', ticket_id=ticket_id))

        # Check if the file exists
        if not os.path.exists(attachment.file_path):
            flash('File not found on server', 'error')
            return redirect(url_for('tickets.view_ticket', ticket_id=ticket_id))

        # Determine if this is a PDF and if we should display it inline
        is_pdf = attachment.filename.lower().endswith('.pdf')
        as_attachment = not is_pdf or request.args.get('download') == 'true'

        return send_file(
            attachment.file_path,
            as_attachment=as_attachment,
            download_name=attachment.filename,
            mimetype='application/pdf' if is_pdf else None
        )

    except Exception as e:
        flash(f'Error downloading attachment: {str(e)}', 'error')
        return redirect(url_for('tickets.view_ticket', ticket_id=ticket_id))
    finally:
        db_session.close()

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@tickets_bp.route('/<int:ticket_id>/track_singpost', methods=['GET'])
@login_required
def track_singpost(ticket_id):
    """Track SingPost package and return tracking data"""
    ticket = ticket_store.get_ticket(ticket_id)
    if not ticket or not ticket.shipping_tracking:
        return jsonify({'error': 'Invalid ticket or no tracking number'}), 404

    try:
        import trackingmore

        # Use API key from config
        trackingmore.api_key = TRACKINGMORE_API_KEY
        
        tracking_number = ticket.shipping_tracking
        
        # First try to get existing tracking data
        try:
            params = {
                'tracking_numbers': tracking_number,
                'courier_code': 'singapore-post'
            }
            result = trackingmore.tracking.get_tracking_results(params)
            
            if 'data' in result and 'items' in result['data'] and len(result['data']['items']) > 0:
                tracking_data = result['data']['items'][0]
            else:
                # If no existing tracking, create a new tracking
                create_params = {
                    'tracking_number': tracking_number,
                    'courier_code': 'singapore-post'
                }
                create_result = trackingmore.tracking.create_tracking(create_params)
                
                # Try to get results again
                params = {
                    'tracking_numbers': tracking_number,
                    'courier_code': 'singapore-post'
                }
                result = trackingmore.tracking.get_tracking_results(params)
                if 'data' in result and 'items' in result['data'] and len(result['data']['items']) > 0:
                    tracking_data = result['data']['items'][0]
                else:
                    raise Exception("Failed to retrieve tracking data")
        except Exception as api_error:
            print(f"TrackingMore API Error: {str(api_error)}")
            # Fallback to our mock data in case of API issues
            return generate_mock_tracking_data(ticket)
        
        # Parse tracking events from the API response
        tracking_info = []
        
        # Extract delivery status and events
        delivery_status = tracking_data.get('delivery_status', 'unknown')
        
        # Get tracking events - these are in reverse order (newest first)
        tracking_events = tracking_data.get('origin_info', {}).get('trackinfo', [])
        
        for event in tracking_events:
            tracking_info.append({
                'date': event.get('Date', ''),
                'status': event.get('StatusDescription', ''),
                'location': event.get('Details', '')
            })
        
        # If no events but we have a status, create at least one event
        if not tracking_info and 'tracking_status' in tracking_data:
            tracking_info.append({
                'date': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'status': tracking_data.get('tracking_status', {}).get('description', 'In Transit'),
                'location': 'Singapore'
            })
        
        # If still no events, fall back to mock data
        if not tracking_info:
            return generate_mock_tracking_data(ticket)
        
        # Update ticket tracking status
        latest = tracking_info[0] if tracking_info else None  # Most recent event is first
        if latest:
            ticket.shipping_status = latest['status']
            ticket.shipping_history = tracking_info
            ticket.updated_at = datetime.datetime.now()  # Update the timestamp
            ticket_store.save_tickets()
        
        print(f"Real tracking info retrieved for {tracking_number}: {tracking_info}")
        print(f"Updated shipping status to: {ticket.shipping_status}")
        
        return jsonify({
            'success': True,
            'tracking_info': tracking_info,
            'shipping_status': ticket.shipping_status,
            'is_real_data': True
        })
        
    except Exception as e:
        print(f"Error tracking SingPost package: {str(e)}")
        # Fall back to mock data
        return generate_mock_tracking_data(ticket)

def generate_mock_tracking_data(ticket):
    """Generate mock tracking data as fallback"""
    try:
        base_date = ticket.created_at or datetime.datetime.now()
        tracking_number = ticket.shipping_tracking
        
        # Different tracking pattern for XZB numbers vs XZD numbers
        if tracking_number.startswith('XZB'):
            tracking_info = []
            
            # Current status (most recent)
            current_date = datetime.datetime.now()
            tracking_info.append({
                'date': current_date.strftime('%Y-%m-%d %H:%M:%S'),
                'status': 'Out for Delivery',
                'location': 'Singapore Central'
            })
            
            # Processing started
            processing_date = current_date - datetime.timedelta(hours=12)
            tracking_info.append({
                'date': processing_date.strftime('%Y-%m-%d %H:%M:%S'),
                'status': 'Arrived at SingPost delivery facility',
                'location': 'Singapore Central'
            })
            
            # Sorting center
            sorting_date = current_date - datetime.timedelta(days=1)
            tracking_info.append({
                'date': sorting_date.strftime('%Y-%m-%d %H:%M:%S'),
                'status': 'Processed at SingPost sorting center',
                'location': 'Singapore'
            })
            
            # Collection event
            collection_date = current_date - datetime.timedelta(days=1, hours=12)
            tracking_info.append({
                'date': collection_date.strftime('%Y-%m-%d %H:%M:%S'),
                'status': 'Package collected from sender',
                'location': 'Singapore'
            })
            
            # Information received
            info_date = current_date - datetime.timedelta(days=2)
            tracking_info.append({
                'date': info_date.strftime('%Y-%m-%d %H:%M:%S'),
                'status': 'Shipping information received by SingPost',
                'location': 'Singapore'
            })
        else:
            # XZD or other tracking pattern (original implementation)
            # Generate a unique seed based on the tracking number
            seed = sum(ord(c) for c in tracking_number)
            
            # Generate tracking events with dates relative to the ticket creation
            tracking_info = []
            
            # Initial event (most recent)
            initial_date = base_date + datetime.timedelta(days=2)
            tracking_info.append({
                'date': initial_date.strftime('%Y-%m-%d %H:%M:%S'),
                'status': 'Delivered',
                'location': 'Singapore'
            })
            
            # Out for delivery events
            delivery_date = base_date + datetime.timedelta(days=2, hours=-6)
            tracking_info.append({
                'date': delivery_date.strftime('%Y-%m-%d %H:%M:%S'),
                'status': 'Out for Delivery',
                'location': 'Singapore'
            })
            
            # Processing events
            processing_date = base_date + datetime.timedelta(days=1)
            tracking_info.append({
                'date': processing_date.strftime('%Y-%m-%d %H:%M:%S'),
                'status': 'Item is with SingPost (Singapore) for processing.',
                'location': 'Singapore'
            })
            
            # Collection event
            collection_date = base_date + datetime.timedelta(hours=12)
            tracking_info.append({
                'date': collection_date.strftime('%Y-%m-%d %H:%M:%S'),
                'status': 'Item collected by SingPost courier',
                'location': 'Singapore'
            })
            
            # Initial event
            tracking_info.append({
                'date': base_date.strftime('%Y-%m-%d %H:%M:%S'),
                'status': 'SingPost has received your order information, but not your item yet',
                'location': 'Singapore'
            })
        
        # Update ticket tracking status
        latest = tracking_info[0]  # Most recent event is first
        ticket.shipping_status = latest['status']
        ticket.shipping_history = tracking_info
        ticket.updated_at = datetime.datetime.now()  # Update the timestamp
        ticket_store.save_tickets()
        
        print(f"Mock tracking info generated for {tracking_number}: {tracking_info}")
        print(f"Updated shipping status to: {ticket.shipping_status}")
        
        return jsonify({
            'success': True,
            'tracking_info': tracking_info,
            'shipping_status': ticket.shipping_status,
            'is_real_data': False  # Indicate this is mock data
        })
        
    except Exception as e:
        print(f"Error generating mock tracking: {str(e)}")
        return jsonify({'error': f"Internal server error: {str(e)}"}), 500

# Remove the create_repair_ticket route since it's now part of create_ticket

# Add other routes back as needed... 