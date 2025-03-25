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
from config import TRACKINGMORE_API_KEY
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Define allowed file extensions
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'}

tickets_bp = Blueprint('tickets', __name__, url_prefix='/tickets')
db_manager = DatabaseManager()

# Initialize TrackingMore API key
# Force the new API key
TRACKINGMORE_API_KEY = "7yyp17vj-t0bh-jtg0-xjf0-v9m3335cjbtc"
trackingmore.set_api_key(TRACKINGMORE_API_KEY)

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
            if category == 'ASSET_CHECKOUT' or category == 'ASSET_CHECKOUT_SINGPOST' or category == 'ASSET_CHECKOUT_DHL':
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

            if category == 'ASSET_CHECKOUT' or category == 'ASSET_CHECKOUT_SINGPOST' or category == 'ASSET_CHECKOUT_DHL':
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
                
                # Determine shipping method based on category
                shipping_method = "Standard"
                if category == 'ASSET_CHECKOUT_SINGPOST':
                    shipping_method = "SingPost"
                elif category == 'ASSET_CHECKOUT_DHL':
                    shipping_method = "DHL"
                
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
Shipping Method: {shipping_method}

Additional Notes:
{notes}"""

                print(f"Creating ticket with description: {description}")  # Debug log

                try:
                    # Determine appropriate ticket category enum value based on shipping method
                    ticket_category = None
                    shipping_carrier = 'singpost'  # Default carrier
                    
                    if shipping_method == "SingPost":
                        ticket_category = TicketCategory.ASSET_CHECKOUT_SINGPOST
                        shipping_carrier = 'singpost'
                    elif shipping_method == "DHL":
                        ticket_category = TicketCategory.ASSET_CHECKOUT_DHL
                        shipping_carrier = 'dhl'
                    elif shipping_method == "UPS":
                        ticket_category = TicketCategory.ASSET_CHECKOUT_UPS
                        shipping_carrier = 'ups'
                    else:
                        ticket_category = TicketCategory.ASSET_CHECKOUT
                    
                    # Create the ticket
                    ticket_id = ticket_store.create_ticket(
                        subject=subject,
                        description=description,
                        requester_id=user_id,
                        category=ticket_category,
                        priority=priority,
                        asset_id=asset.id,
                        customer_id=customer_id,
                        shipping_address=shipping_address,
                        shipping_tracking=shipping_tracking if shipping_tracking else None,
                        shipping_carrier=shipping_carrier
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

@tickets_bp.route('/<int:ticket_id>/track_debug', methods=['GET'])
@login_required
def track_debug(ticket_id):
    """Debug endpoint to show detailed tracking information"""
    ticket = ticket_store.get_ticket(ticket_id)
    if not ticket or not ticket.shipping_tracking:
        return jsonify({'error': 'Invalid ticket or no tracking number'}), 404
    
    tracking_number = ticket.shipping_tracking
    debug_info = {
        'ticket_id': ticket_id,
        'tracking_number': tracking_number,
        'ticket_status': ticket.status.value if ticket.status else 'None',
        'shipping_status': ticket.shipping_status or 'None',
        'shipping_history': getattr(ticket, 'shipping_history', []),  # Default to empty list if attribute doesn't exist
        'api_key': TRACKINGMORE_API_KEY[:5] + '****' if TRACKINGMORE_API_KEY else 'Not Set',
        'carrier_codes_to_try': [],
        'tracking_attempts': []
    }
    
    # Determine carrier codes to try
    if tracking_number.startswith('XZD'):
        carrier_codes = ['speedpost', 'singapore-post', 'singpost-speedpost']
        debug_info['detected_format'] = 'XZD (Speedpost)'
    elif tracking_number.startswith('XZB'):
        carrier_codes = ['singapore-post', 'singpost', 'singpost-registered']
        debug_info['detected_format'] = 'XZB (SingPost)'
    elif tracking_number.startswith('JD'):
        carrier_codes = ['dhl', 'dhl-express']
        debug_info['detected_format'] = 'JD (DHL)'
    else:
        carrier_codes = ['singapore-post', 'singpost', 'dhl', 'speedpost']
        debug_info['detected_format'] = 'Unknown Format'
    
    debug_info['carrier_codes_to_try'] = carrier_codes
    
    # Try each carrier code
    for carrier_code in carrier_codes:
        attempt_result = {
            'carrier_code': carrier_code,
            'create_tracking_attempt': None,
            'realtime_tracking_attempt': None,
            'errors': []
        }
        
        try:
            import trackingmore
            trackingmore.set_api_key(TRACKINGMORE_API_KEY)
            
            # Try to create tracking
            try:
                create_params = {'tracking_number': tracking_number, 'carrier_code': carrier_code}
                create_result = trackingmore.create_tracking_item(create_params)
                attempt_result['create_tracking_attempt'] = {
                    'success': True,
                    'result': create_result
                }
            except Exception as e:
                attempt_result['create_tracking_attempt'] = {
                    'success': False,
                    'error': str(e)
                }
                attempt_result['errors'].append(f"Create tracking error: {str(e)}")
            
            # Try realtime tracking
            try:
                params = {'tracking_number': tracking_number, 'carrier_code': carrier_code}
                result = trackingmore.realtime_tracking(params)
                attempt_result['realtime_tracking_attempt'] = {
                    'success': True,
                    'result': result
                }
                
                # Check status
                if result and 'items' in result and result['items']:
                    tracking_data = result['items'][0]
                    attempt_result['status'] = tracking_data.get('status', 'unknown')
                    attempt_result['substatus'] = tracking_data.get('substatus', 'unknown')
                    
                    # Check tracking events
                    tracking_events = tracking_data.get('origin_info', {}).get('trackinfo', [])
                    attempt_result['has_events'] = bool(tracking_events)
                    attempt_result['event_count'] = len(tracking_events) if tracking_events else 0
                    if tracking_events:
                        attempt_result['first_event'] = tracking_events[0]
            except Exception as e:
                attempt_result['realtime_tracking_attempt'] = {
                    'success': False,
                    'error': str(e)
                }
                attempt_result['errors'].append(f"Realtime tracking error: {str(e)}")
        
        except Exception as e:
            attempt_result['errors'].append(f"General error: {str(e)}")
        
        debug_info['tracking_attempts'].append(attempt_result)
    
    return jsonify(debug_info)

@tickets_bp.route('/<int:ticket_id>/track_singpost', methods=['GET'])
@login_required
def track_singpost(ticket_id):
    """Track Singapore Post package and return tracking data"""
    print(f"==== TRACKING SINGPOST - TICKET {ticket_id} ====")
    ticket = ticket_store.get_ticket(ticket_id)
    if not ticket or not ticket.shipping_tracking:
        print("Invalid ticket or no tracking number")
        return jsonify({'error': 'Invalid ticket or no tracking number'}), 404

    try:
        import trackingmore
        
        # Debug: Print TrackingMore module info
        print(f"TrackingMore module: {trackingmore}")
        
        # Use API key from config
        print(f"Using TrackingMore API Key: {TRACKINGMORE_API_KEY}")
        # Force set API key again
        trackingmore.set_api_key(TRACKINGMORE_API_KEY)
        
        tracking_number = ticket.shipping_tracking
        print(f"Tracking SingPost number: {tracking_number}")
        carrier_code = 'singapore-post'
        
        # Create a new tracking request
        create_params = {
            'tracking_number': tracking_number,
            'carrier_code': carrier_code
        }
        try:
            create_result = trackingmore.create_tracking_item(create_params)
            print(f"Create tracking result: {create_result}")
        except Exception as e:
            if "Tracking already exists" in str(e):
                print(f"Tracking already exists: {str(e)}")
            else:
                print(f"Error creating tracking: {str(e)}")
                # Continue anyway to try to get tracking info
        
        # Try to get real-time tracking data
        try:
            print("\nTrying realtime_tracking")
            realtime_params = {
                'tracking_number': tracking_number,
                'carrier_code': carrier_code
            }
            result = trackingmore.realtime_tracking(realtime_params)
            print(f"Realtime tracking result: {result}")
            
            # Check if we have real tracking data
            if result and 'items' in result and result['items']:
                tracking_data = result['items'][0]
                
                # Check if the status is "notfound" - if so, handle specially
                if tracking_data.get('status') == 'notfound':
                    print(f"No tracking data found for {tracking_number}, but tracking number is valid")
                    print(f"Tracking data details: {tracking_data}")
                    
                    # For valid tracking numbers without data yet, show customized status
                    current_date = datetime.datetime.now()
                    tracking_info = []
                    
                    # Check the substatus for more detailed info
                    substatus = tracking_data.get('substatus', '')
                    if substatus == 'notfound001':
                        status_desc = "Pending - Waiting for Carrier Scan"
                        location = "Shipping System"
                    elif substatus == 'notfound002':
                        status_desc = "Pending - Tracking Number Registered"
                        location = "SingPost System"
                    elif substatus == 'notfound003':
                        status_desc = "Pending - Invalid Tracking Number"
                        location = "Verification Required"
                    else:
                        status_desc = "Information Received - Waiting for Update"
                        location = "SingPost Processing Center"
                        
                    print(f"Using custom status: {status_desc} for substatus: {substatus}")
                    
                    tracking_info.append({
                        'date': current_date.strftime('%Y-%m-%d %H:%M:%S'),
                        'status': status_desc,
                        'location': location
                    })
                    
                    # Update ticket
                    ticket.shipping_status = tracking_info[0]['status']
                    ticket.shipping_history = tracking_info
                    ticket.updated_at = datetime.datetime.now()
                    ticket_store.save_tickets()
                    
                    return jsonify({
                        'success': True,
                        'tracking_info': tracking_info,
                        'shipping_status': ticket.shipping_status,
                        'is_real_data': True,  # Mark as real data
                        'debug_info': {
                            'carrier_code': carrier_code,
                            'status': tracking_data.get('status', 'unknown'),
                            'substatus': substatus,
                            'no_events': True
                        }
                    })
                
                # Parse tracking events from the API response
                tracking_info = []
                
                # Get tracking events from the response
                tracking_events = tracking_data.get('origin_info', {}).get('trackinfo', [])
                
                if tracking_events:
                    for event in tracking_events:
                        tracking_info.append({
                            'date': event.get('Date', event.get('date', '')),
                            'status': event.get('StatusDescription', event.get('status_description', event.get('status', ''))),
                            'location': event.get('Details', event.get('details', event.get('location', '')))
                        })
                    
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
                        'is_real_data': True,
                        'debug_info': {
                            'carrier_code': carrier_code,
                            'has_events': True,
                            'event_count': len(tracking_events)
                        }
                    })
            
        except Exception as e:
            print(f"ERROR with realtime tracking: {str(e)}")
            print(f"Error type: {type(e)}")
            
    except Exception as e:
        print(f"Error tracking SingPost package: {str(e)}")
        
    # Fall back to mock data if all real tracking attempts failed
    print("All tracking attempts failed, falling back to mock data")
    return generate_mock_singpost_data(ticket)

def generate_mock_singpost_data(ticket):
    """Generate mock tracking data for SingPost as fallback"""
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
        
        print(f"Mock SingPost tracking info generated for {tracking_number}: {tracking_info}")
        print(f"Updated shipping status to: {ticket.shipping_status}")
        
        return jsonify({
            'success': True,
            'tracking_info': tracking_info,
            'shipping_status': ticket.shipping_status,
            'is_real_data': False  # Indicate this is mock data
        })
        
    except Exception as e:
        print(f"Error generating mock SingPost tracking: {str(e)}")
        return jsonify({'error': f"Internal server error: {str(e)}"}), 500

@tickets_bp.route('/<int:ticket_id>/track_dhl', methods=['GET'])
@login_required
def track_dhl(ticket_id):
    """Track DHL package and return tracking data"""
    print(f"==== TRACKING DHL - TICKET {ticket_id} ====")
    ticket = ticket_store.get_ticket(ticket_id)
    if not ticket or not ticket.shipping_tracking:
        print("Invalid ticket or no tracking number")
        return jsonify({'error': 'Invalid ticket or no tracking number'}), 404

    try:
        import trackingmore
        
        # Debug: Print TrackingMore module info
        print(f"TrackingMore module: {trackingmore}")
        
        # Use API key from config
        print(f"Using TrackingMore API Key: {TRACKINGMORE_API_KEY}")
        # Force set API key again
        trackingmore.set_api_key(TRACKINGMORE_API_KEY)
        
        tracking_number = ticket.shipping_tracking
        print(f"Tracking DHL number: {tracking_number}")
        
        # Try each carrier code for DHL
        potential_carriers = [
            'dhl',
            'dhl-global-mail',
            'dhl-express',
            'dhl-germany',
            'dhl-benelux',
            'dhl-global-mail-asia',
            'dhl-global-mail-americas',
            'dhl-global-mail-europe',
        ]
        
        # Try each carrier code until one works
        for carrier_code in potential_carriers:
            try:
                print(f"\nAttempting with carrier code: {carrier_code}")
                # Create a new tracking request
                create_params = {
                    'tracking_number': tracking_number,
                    'carrier_code': carrier_code
                }
                try:
                    create_result = trackingmore.create_tracking_item(create_params)
                    print(f"SUCCESS with carrier code {carrier_code}: {create_result}")
                    # If we get here, this carrier code worked - use it for getting results
                    break
                except Exception as e:
                    if "Tracking already exists" in str(e):
                        print(f"Tracking already exists with carrier {carrier_code}, continuing")
                        break
                    else:
                        print(f"Failed with carrier code {carrier_code}: {str(e)}")
                        # Try next carrier code
            except Exception as outer_e:
                print(f"Outer exception with carrier {carrier_code}: {str(outer_e)}")
                continue
                
        print(f"Selected carrier code: {carrier_code}")
        
        # Try to get real-time tracking data
        try:
            print("\nTrying realtime_tracking with carrier code:", carrier_code)
            realtime_params = {
                'tracking_number': tracking_number,
                'carrier_code': carrier_code
            }
            result = trackingmore.realtime_tracking(realtime_params)
            print(f"Realtime tracking result: {result}")
            
            # Check if we have real tracking data
            if result and 'items' in result and result['items']:
                tracking_data = result['items'][0]
                
                # Check if the status is "notfound" - if so, handle specially
                if tracking_data.get('status') == 'notfound':
                    print(f"No tracking data found for {tracking_number}, but tracking number is valid")
                    print(f"Tracking data details: {tracking_data}")
                    
                    # For valid tracking numbers without data yet, show customized status based on carrier
                    current_date = datetime.datetime.now()
                    tracking_info = []
                    
                    # Check the substatus for more detailed info
                    substatus = tracking_data.get('substatus', '')
                    if substatus == 'notfound001':
                        status_desc = "Pending - Waiting for Carrier Scan"
                        location = "Shipping System"
                    elif substatus == 'notfound002':
                        status_desc = "Pending - Tracking Number Registered"
                        location = "DHL System"
                    elif substatus == 'notfound003':
                        status_desc = "Pending - Invalid Tracking Number"
                        location = "Verification Required"
                    else:
                        status_desc = "Information Received - Waiting for Update"
                        location = "DHL Processing Center"
                        
                    print(f"Using custom status: {status_desc} for substatus: {substatus}")
                    
                    tracking_info.append({
                        'date': current_date.strftime('%Y-%m-%d %H:%M:%S'),
                        'status': status_desc,
                        'location': location
                    })
                    
                    # Update ticket
                    ticket.shipping_status = tracking_info[0]['status']
                    ticket.shipping_history = tracking_info
                    ticket.updated_at = datetime.datetime.now()
                    ticket_store.save_tickets()
                    
                    return jsonify({
                        'success': True,
                        'tracking_info': tracking_info,
                        'shipping_status': ticket.shipping_status,
                        'is_real_data': True,  # Mark as real data
                        'debug_info': {
                            'carrier_code': carrier_code,
                            'status': tracking_data.get('status', 'unknown'),
                            'substatus': substatus,
                            'no_events': True
                        }
                    })
                
                # Parse tracking events from the API response
                tracking_info = []
                
                # Get tracking events from the response
                tracking_events = tracking_data.get('origin_info', {}).get('trackinfo', [])
                
                if tracking_events:
                    for event in tracking_events:
                        tracking_info.append({
                            'date': event.get('Date', event.get('date', '')),
                            'status': event.get('StatusDescription', event.get('status_description', event.get('status', ''))),
                            'location': event.get('Details', event.get('details', event.get('location', '')))
                        })
                    
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
                        'is_real_data': True,
                        'debug_info': {
                            'carrier_code': carrier_code,
                            'has_events': True,
                            'event_count': len(tracking_events)
                        }
                    })
            
        except Exception as e:
            print(f"ERROR with realtime tracking: {str(e)}")
            print(f"Error type: {type(e)}")
            
            # If all attempts failed, fall back to mock data
            print(f"All carrier code attempts failed, falling back to mock data")
            return generate_mock_dhl_data(ticket)
            
    except Exception as e:
        print(f"Error tracking DHL package: {str(e)}")
        # Fall back to mock data
        return generate_mock_dhl_data(ticket)

def generate_mock_dhl_data(ticket):
    """Generate mock tracking data for DHL as fallback"""
    try:
        base_date = ticket.created_at or datetime.datetime.now()
        tracking_number = ticket.shipping_tracking
        
        print(f"Generating mock DHL tracking data for {tracking_number}")
        
        # Determine how many days since ticket creation
        days_since_creation = (datetime.datetime.now() - base_date).days
        print(f"Days since ticket creation: {days_since_creation}")
        
        # Generate mock tracking events
        tracking_info = []
        
        # Initial status - Package registered
        initial_date = base_date
        tracking_info.append({
            'date': initial_date.strftime('%Y-%m-%d %H:%M:%S'),
            'status': 'Shipment information received',
            'location': 'DHL eCommerce'
        })
        
        # If more than 1 day since creation, add "Picked up" status
        if days_since_creation >= 1:
            pickup_date = base_date + datetime.timedelta(days=1)
            tracking_info.append({
                'date': pickup_date.strftime('%Y-%m-%d %H:%M:%S'),
                'status': 'Shipment picked up',
                'location': 'Origin Facility'
            })
        
        # If more than 3 days since creation, add "In Transit" status
        if days_since_creation >= 3:
            transit_date = base_date + datetime.timedelta(days=3)
            tracking_info.append({
                'date': transit_date.strftime('%Y-%m-%d %H:%M:%S'),
                'status': 'Shipment in transit',
                'location': 'DHL Processing Center'
            })
        
        # If more than 5 days since creation, add "Arriving" status
        if days_since_creation >= 5:
            arriving_date = base_date + datetime.timedelta(days=5)
            tracking_info.append({
                'date': arriving_date.strftime('%Y-%m-%d %H:%M:%S'),
                'status': 'Shipment arriving at destination',
                'location': 'Destination Country'
            })
        
        # If more than 7 days since creation, add "Out for delivery" status
        if days_since_creation >= 7:
            delivery_date = base_date + datetime.timedelta(days=7)
            tracking_info.append({
                'date': delivery_date.strftime('%Y-%m-%d %H:%M:%S'),
                'status': 'Out for delivery',
                'location': 'Local Delivery Facility'
            })
            
        # If more than 8 days since creation, add "Delivered" status
        if days_since_creation >= 8:
            delivered_date = base_date + datetime.timedelta(days=8)
            tracking_info.append({
                'date': delivered_date.strftime('%Y-%m-%d %H:%M:%S'),
                'status': 'Delivered',
                'location': 'Destination Address'
            })
        
        # Reverse the list so most recent event is first
        tracking_info.reverse()
        
        # Update ticket tracking status
        latest = tracking_info[0] if tracking_info else None
        if latest:
            ticket.shipping_status = latest['status']
            ticket.shipping_history = tracking_info
            ticket.updated_at = datetime.datetime.now()  # Update the timestamp
            ticket_store.save_tickets()
        
        print(f"Mock DHL tracking info generated for {tracking_number}: {tracking_info}")
        print(f"Updated shipping status to: {ticket.shipping_status}")
        
        return jsonify({
            'success': True,
            'tracking_info': tracking_info,
            'shipping_status': ticket.shipping_status,
            'is_real_data': False,  # Mark as mock data
            'debug_info': {
                'mock_data': True,
                'days_since_creation': days_since_creation,
                'events_count': len(tracking_info)
            }
        })
        
    except Exception as e:
        print(f"Error generating mock DHL tracking: {str(e)}")
        return jsonify({'error': f"Internal server error: {str(e)}"}), 500

@tickets_bp.route('/<int:ticket_id>/track_ups', methods=['GET'])
@login_required
def track_ups(ticket_id):
    """Track UPS package and return tracking data"""
    print(f"==== TRACKING UPS - TICKET {ticket_id} ====")
    ticket = ticket_store.get_ticket(ticket_id)
    if not ticket or not ticket.shipping_tracking:
        print("Invalid ticket or no tracking number")
        return jsonify({'error': 'Invalid ticket or no tracking number'}), 404

    try:
        import trackingmore
        
        # Debug: Print TrackingMore module info
        print(f"TrackingMore module: {trackingmore}")
        
        # Use API key from config
        print(f"Using TrackingMore API Key: {TRACKINGMORE_API_KEY}")
        # Force set API key again
        trackingmore.set_api_key(TRACKINGMORE_API_KEY)
        
        tracking_number = ticket.shipping_tracking
        print(f"Tracking UPS number: {tracking_number}")
        
        # Try each carrier code for UPS
        potential_carriers = [
            'ups',
            'ups-freight',
            'ups-mail-innovations',
        ]
        
        # Try each carrier code until one works
        for carrier_code in potential_carriers:
            try:
                print(f"\nAttempting with carrier code: {carrier_code}")
                # Create a new tracking request
                create_params = {
                    'tracking_number': tracking_number,
                    'carrier_code': carrier_code
                }
                try:
                    create_result = trackingmore.create_tracking_item(create_params)
                    print(f"SUCCESS with carrier code {carrier_code}: {create_result}")
                    # If we get here, this carrier code worked - use it for getting results
                    break
                except Exception as e:
                    if "Tracking already exists" in str(e):
                        print(f"Tracking already exists with carrier {carrier_code}, continuing")
                        break
                    else:
                        print(f"Failed with carrier code {carrier_code}: {str(e)}")
                        # Try next carrier code
            except Exception as outer_e:
                print(f"Outer exception with carrier {carrier_code}: {str(outer_e)}")
                continue
                
        print(f"Selected carrier code: {carrier_code}")
        
        # Try to get real-time tracking data
        try:
            print("\nTrying realtime_tracking with carrier code:", carrier_code)
            realtime_params = {
                'tracking_number': tracking_number,
                'carrier_code': carrier_code
            }
            result = trackingmore.realtime_tracking(realtime_params)
            print(f"Realtime tracking result: {result}")
            
            # Check if we have real tracking data
            if result and 'items' in result and result['items']:
                tracking_data = result['items'][0]
                
                # Check if the status is "notfound" - if so, handle specially
                if tracking_data.get('status') == 'notfound':
                    print(f"No tracking data found for {tracking_number}, but tracking number is valid")
                    print(f"Tracking data details: {tracking_data}")
                    
                    # For valid tracking numbers without data yet, show customized status based on carrier
                    current_date = datetime.datetime.now()
                    tracking_info = []
                    
                    # Check the substatus for more detailed info
                    substatus = tracking_data.get('substatus', '')
                    if substatus == 'notfound001':
                        status_desc = "Pending - Waiting for Carrier Scan"
                        location = "Shipping System"
                    elif substatus == 'notfound002':
                        status_desc = "Pending - Tracking Number Registered"
                        location = "UPS System"
                    elif substatus == 'notfound003':
                        status_desc = "Pending - Invalid Tracking Number"
                        location = "Verification Required"
                    else:
                        status_desc = "Information Received - Waiting for Update"
                        location = "UPS Processing Center"
                        
                    print(f"Using custom status: {status_desc} for substatus: {substatus}")
                    
                    tracking_info.append({
                        'date': current_date.strftime('%Y-%m-%d %H:%M:%S'),
                        'status': status_desc,
                        'location': location
                    })
                    
                    # Update ticket
                    ticket.shipping_status = tracking_info[0]['status']
                    ticket.shipping_history = tracking_info
                    ticket.updated_at = datetime.datetime.now()
                    ticket_store.save_tickets()
                    
                    return jsonify({
                        'success': True,
                        'tracking_info': tracking_info,
                        'shipping_status': ticket.shipping_status,
                        'is_real_data': True,  # Mark as real data
                        'debug_info': {
                            'carrier_code': carrier_code,
                            'status': tracking_data.get('status', 'unknown'),
                            'substatus': substatus,
                            'no_events': True
                        }
                    })
                
                # Parse tracking events from the API response
                tracking_info = []
                
                # Get tracking events from the response
                tracking_events = tracking_data.get('origin_info', {}).get('trackinfo', [])
                
                if tracking_events:
                    for event in tracking_events:
                        tracking_info.append({
                            'date': event.get('Date', event.get('date', '')),
                            'status': event.get('StatusDescription', event.get('status_description', event.get('status', ''))),
                            'location': event.get('Details', event.get('details', event.get('location', '')))
                        })
                    
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
                        'is_real_data': True,
                        'debug_info': {
                            'carrier_code': carrier_code,
                            'has_events': True,
                            'event_count': len(tracking_events)
                        }
                    })
            
        except Exception as e:
            print(f"ERROR with realtime tracking: {str(e)}")
            print(f"Error type: {type(e)}")
            
            # If all attempts failed, fall back to mock data
            print(f"All carrier code attempts failed, falling back to mock data")
            return generate_mock_ups_data(ticket)
            
    except Exception as e:
        print(f"Error tracking UPS package: {str(e)}")
        # Fall back to mock data
        return generate_mock_ups_data(ticket)

def generate_mock_ups_data(ticket):
    """Generate mock tracking data for UPS as fallback"""
    try:
        base_date = ticket.created_at or datetime.datetime.now()
        tracking_number = ticket.shipping_tracking
        
        print(f"Generating mock UPS tracking data for {tracking_number}")
        
        # Determine how many days since ticket creation
        days_since_creation = (datetime.datetime.now() - base_date).days
        print(f"Days since ticket creation: {days_since_creation}")
        
        # Generate mock tracking events
        tracking_info = []
        
        # Initial status - Package registered
        initial_date = base_date
        tracking_info.append({
            'date': initial_date.strftime('%Y-%m-%d %H:%M:%S'),
            'status': 'Order Processed: Ready for UPS',
            'location': 'Shipper'
        })
        
        # If more than 1 day since creation, add "Picked up" status
        if days_since_creation >= 1:
            pickup_date = base_date + datetime.timedelta(days=1)
            tracking_info.append({
                'date': pickup_date.strftime('%Y-%m-%d %H:%M:%S'),
                'status': 'Pickup Scan',
                'location': 'Origin Facility'
            })
        
        # If more than 3 days since creation, add "In Transit" status
        if days_since_creation >= 3:
            transit_date = base_date + datetime.timedelta(days=3)
            tracking_info.append({
                'date': transit_date.strftime('%Y-%m-%d %H:%M:%S'),
                'status': 'In Transit',
                'location': 'UPS Facility'
            })
        
        # If more than 5 days since creation, add "Arriving" status
        if days_since_creation >= 5:
            arriving_date = base_date + datetime.timedelta(days=5)
            tracking_info.append({
                'date': arriving_date.strftime('%Y-%m-%d %H:%M:%S'),
                'status': 'Arrived at Destination',
                'location': 'Destination Country'
            })
        
        # If more than 7 days since creation, add "Out for delivery" status
        if days_since_creation >= 7:
            delivery_date = base_date + datetime.timedelta(days=7)
            tracking_info.append({
                'date': delivery_date.strftime('%Y-%m-%d %H:%M:%S'),
                'status': 'Out for Delivery',
                'location': 'Local Delivery Facility'
            })
            
        # If more than 8 days since creation, add "Delivered" status
        if days_since_creation >= 8:
            delivered_date = base_date + datetime.timedelta(days=8)
            tracking_info.append({
                'date': delivered_date.strftime('%Y-%m-%d %H:%M:%S'),
                'status': 'Delivered',
                'location': 'Destination Address'
            })
        
        # Reverse the list so most recent event is first
        tracking_info.reverse()
        
        # Update ticket tracking status
        latest = tracking_info[0] if tracking_info else None
        if latest:
            ticket.shipping_status = latest['status']
            ticket.shipping_history = tracking_info
            ticket.updated_at = datetime.datetime.now()  # Update the timestamp
            ticket_store.save_tickets()
        
        print(f"Mock UPS tracking info generated for {tracking_number}: {tracking_info}")
        print(f"Updated shipping status to: {ticket.shipping_status}")
        
        return jsonify({
            'success': True,
            'tracking_info': tracking_info,
            'shipping_status': ticket.shipping_status,
            'is_real_data': False,  # Mark as mock data
            'debug_info': {
                'mock_data': True,
                'days_since_creation': days_since_creation,
                'events_count': len(tracking_info)
            }
        })
        
    except Exception as e:
        print(f"Error generating mock UPS tracking: {str(e)}")
        return jsonify({'error': f"Internal server error: {str(e)}"}), 500

@tickets_bp.route('/<int:ticket_id>/debug_tracking', methods=['GET'])
@login_required
def debug_tracking(ticket_id):
    """Debug endpoint to get detailed tracking information"""
    ticket = ticket_store.get_ticket(ticket_id)
    if not ticket:
        return jsonify({'error': 'Ticket not found'}), 404
        
    # Collect debug info
    tracking_info = {
        'ticket_id': ticket_id,
        'tracking_number': ticket.shipping_tracking,
        'carrier': getattr(ticket, 'shipping_carrier', 'singpost'),  # Default to 'singpost' if attribute doesn't exist
        'status': ticket.shipping_status,
        'history': getattr(ticket, 'shipping_history', []),  # Default to empty list if attribute doesn't exist
        'created_at': str(ticket.created_at),
        'updated_at': str(ticket.updated_at),
    }
    
    # Try to get current info from carrier APIs
    carrier_info = {}
    try:
        # Get carrier (default to singpost if not set)
        carrier = getattr(ticket, 'shipping_carrier', 'singpost')
        
        if carrier == 'singpost':
            # Import here to avoid circular imports
            import trackingmore
            trackingmore.set_api_key(TRACKINGMORE_API_KEY)
            
            tracking_number = ticket.shipping_tracking
            carrier_code = 'singapore-post'
            
            # Create tracking if needed
            create_params = {
                'tracking_number': tracking_number,
                'carrier_code': carrier_code
            }
            try:
                create_result = trackingmore.create_tracking_item(create_params)
                carrier_info['create_result'] = create_result
            except Exception as e:
                carrier_info['create_error'] = str(e)
            
            # Get real-time data
            try:
                realtime_params = {
                    'tracking_number': tracking_number,
                    'carrier_code': carrier_code
                }
                result = trackingmore.realtime_tracking(realtime_params)
                carrier_info['realtime_result'] = result
            except Exception as e:
                carrier_info['realtime_error'] = str(e)
                
        elif carrier == 'dhl':
            # Import here to avoid circular imports
            import trackingmore
            trackingmore.set_api_key(TRACKINGMORE_API_KEY)
            
            tracking_number = ticket.shipping_tracking
            carrier_info['potential_carriers'] = [
                'dhl',
                'dhl-global-mail',
                'dhl-express',
                'dhl-germany',
                'dhl-benelux',
                'dhl-global-mail-asia',
                'dhl-global-mail-americas',
                'dhl-global-mail-europe',
            ]
            
            # Try each carrier code
            carrier_results = {}
            for carrier_code in carrier_info['potential_carriers']:
                carrier_results[carrier_code] = {}
                
                # Try to create
                try:
                    create_params = {
                        'tracking_number': tracking_number,
                        'carrier_code': carrier_code
                    }
                    create_result = trackingmore.create_tracking_item(create_params)
                    carrier_results[carrier_code]['create_result'] = create_result
                    
                    # If successful, try to get real-time data
                    try:
                        realtime_params = {
                            'tracking_number': tracking_number,
                            'carrier_code': carrier_code
                        }
                        result = trackingmore.realtime_tracking(realtime_params)
                        carrier_results[carrier_code]['realtime_result'] = result
                    except Exception as e:
                        carrier_results[carrier_code]['realtime_error'] = str(e)
                        
                except Exception as e:
                    carrier_results[carrier_code]['create_error'] = str(e)
                    
                    # If "already exists" error, try to get real-time data anyway
                    if "Tracking already exists" in str(e):
                        try:
                            realtime_params = {
                                'tracking_number': tracking_number,
                                'carrier_code': carrier_code
                            }
                            result = trackingmore.realtime_tracking(realtime_params)
                            carrier_results[carrier_code]['realtime_result'] = result
                        except Exception as e2:
                            carrier_results[carrier_code]['realtime_error'] = str(e2)
            
            carrier_info['carrier_results'] = carrier_results
    except Exception as e:
        carrier_info['error'] = str(e)
    
    # Add carrier info to response
    tracking_info['carrier_api_info'] = carrier_info
    
    return jsonify({
        'success': True,
        'debug_tracking_info': tracking_info
    })

@tickets_bp.route('/<int:ticket_id>/update_carrier', methods=['POST'])
@login_required
def update_shipping_carrier(ticket_id):
    """Update shipping carrier for a ticket"""
    ticket = ticket_store.get_ticket(ticket_id)
    if not ticket:
        return jsonify({'error': 'Ticket not found'}), 404
    
    carrier = request.form.get('carrier') or request.json.get('carrier')
    if not carrier:
        return jsonify({'error': 'Carrier parameter is required'}), 400
    
    # Update the carrier
    ticket.shipping_carrier = carrier.lower()
    
    # Also update the ticket category if needed
    if carrier.lower() == 'dhl':
        ticket.category = TicketCategory.ASSET_CHECKOUT_DHL
    elif carrier.lower() == 'singpost':
        ticket.category = TicketCategory.ASSET_CHECKOUT_SINGPOST
    elif carrier.lower() == 'ups':
        ticket.category = TicketCategory.ASSET_CHECKOUT_UPS
    
    # Save the ticket
    ticket.updated_at = datetime.datetime.now()
    ticket_store.update_ticket(ticket_id, shipping_carrier=carrier.lower())
    
    return jsonify({
        'success': True,
        'message': f'Shipping carrier updated to {carrier}',
        'ticket_id': ticket_id,
        'shipping_carrier': carrier.lower()
    })

# Simple GET endpoint to update carrier (for easier testing via URL)
@tickets_bp.route('/<int:ticket_id>/set_carrier/<carrier>', methods=['GET'])
@login_required
def set_carrier(ticket_id, carrier):
    """Simple endpoint to update carrier via GET request"""
    ticket = ticket_store.get_ticket(ticket_id)
    if not ticket:
        return jsonify({'error': 'Ticket not found'}), 404
    
    # Update the carrier
    ticket.shipping_carrier = carrier.lower()
    
    # Also update the ticket category if needed
    if carrier.lower() == 'dhl':
        ticket.category = TicketCategory.ASSET_CHECKOUT_DHL
    elif carrier.lower() == 'singpost':
        ticket.category = TicketCategory.ASSET_CHECKOUT_SINGPOST
    elif carrier.lower() == 'ups':
        ticket.category = TicketCategory.ASSET_CHECKOUT_UPS
    
    # Save the ticket
    ticket.updated_at = datetime.datetime.now()
    ticket_store.update_ticket(ticket_id, shipping_carrier=carrier.lower())
    
    return jsonify({
        'success': True,
        'message': f'Shipping carrier updated to {carrier}',
        'ticket_id': ticket_id,
        'shipping_carrier': carrier.lower()
    })

# Remove the create_repair_ticket route since it's now part of create_ticket

# Add other routes back as needed... 