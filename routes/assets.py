from flask import Blueprint, request, jsonify, redirect, url_for, flash, session, render_template, make_response
from utils.auth_decorators import login_required, admin_required
from utils.store_instances import inventory_store, db_manager, ticket_store
from models.asset import Asset, AssetStatus
from models.activity import Activity
from models.ticket import Ticket
from flask_login import current_user
from utils.db_manager import DatabaseManager
from models.company import Company
from utils.barcode_generator import barcode_generator
from database import SessionLocal
import io
from sqlalchemy import text
from datetime import datetime

# Create Blueprint
assets_bp = Blueprint('assets', __name__, url_prefix='/assets')
db_manager = DatabaseManager()

def _is_asset_checkout_ticket(ticket_category):
    """
    Check if the ticket category is an Asset Checkout type
    
    Args:
        ticket_category: TicketCategory enum value
        
    Returns:
        bool: True if this is an Asset Checkout ticket
    """
    from models.ticket import TicketCategory
    
    checkout_categories = [
        TicketCategory.ASSET_CHECKOUT,
        TicketCategory.ASSET_CHECKOUT_SINGPOST,
        TicketCategory.ASSET_CHECKOUT_DHL,
        TicketCategory.ASSET_CHECKOUT_UPS,
        TicketCategory.ASSET_CHECKOUT_BLUEDART,
        TicketCategory.ASSET_CHECKOUT_DTDC,
        TicketCategory.ASSET_CHECKOUT_AUTO,
        TicketCategory.ASSET_CHECKOUT_CLAW,
    ]
    
    return ticket_category in checkout_categories


def _auto_checkout_asset_to_customer(ticket, asset, db_session):
    """
    Automatically checkout an asset to the customer associated with the ticket
    
    Args:
        ticket: Ticket object
        asset: Asset object  
        db_session: Database session
        
    Returns:
        bool: True if checkout was successful, False otherwise
    """
    try:
        print(f"[AUTO_CHECKOUT DEBUG] Starting auto-checkout for asset {asset.id} to customer")
        
        # Check if ticket has a customer
        if not ticket.customer_id:
            print(f"[AUTO_CHECKOUT DEBUG] Ticket {ticket.id} has no customer assigned")
            return False
            
        # Get the customer
        from models.customer_user import CustomerUser
        customer = db_session.query(CustomerUser).get(ticket.customer_id)
        if not customer:
            print(f"[AUTO_CHECKOUT DEBUG] Customer {ticket.customer_id} not found")
            return False
            
        print(f"[AUTO_CHECKOUT DEBUG] Found customer: {customer.name} (ID: {customer.id})")
        
        # Update asset status and assign to customer
        from models.asset import AssetStatus
        asset.status = AssetStatus.DEPLOYED
        asset.customer_id = customer.id
        
        print(f"[AUTO_CHECKOUT DEBUG] Updated asset status to DEPLOYED and assigned to customer {customer.id}")
        
        # Create asset transaction record
        from models.asset_transaction import AssetTransaction
        transaction = AssetTransaction(
            asset_id=asset.id,
            transaction_type='checkout',
            customer_id=customer.id,
            notes=f'Auto-checkout via ticket #{ticket.id}',
            transaction_date=datetime.utcnow()
        )
        
        # Set user_id manually since it's not in the constructor
        transaction.user_id = current_user.id
        
        db_session.add(transaction)
        
        # Create activity for checkout
        from models.activity import Activity
        from flask_login import current_user
        checkout_activity = Activity(
            user_id=current_user.id,
            type='asset_checkout',
            content=f'Auto-checked out asset {asset.asset_tag} to {customer.name} via ticket #{ticket.id}',
            reference_id=asset.id
        )
        db_session.add(checkout_activity)
        
        print(f"[AUTO_CHECKOUT DEBUG] Created transaction and activity records")
        return True
        
    except Exception as e:
        print(f"[AUTO_CHECKOUT DEBUG] Error during auto-checkout: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def _safely_assign_asset_to_ticket(ticket, asset, db_session):
    """
    Safely assign an asset to a ticket using direct SQL to avoid relationship issues
    
    Args:
        ticket: Ticket object
        asset: Asset object
        db_session: Database session
        
    Returns:
        bool: True if assignment was successful or already exists, False otherwise
    """
    try:
        print(f"[SAFELY_ASSIGN DEBUG] Checking assignment for asset {asset.id} to ticket {ticket.id}")
        
        # Check if the relationship already exists in the database FIRST
        stmt = text("""
            SELECT COUNT(*) FROM ticket_assets 
            WHERE ticket_id = :ticket_id AND asset_id = :asset_id
        """)
        result = db_session.execute(stmt, {"ticket_id": ticket.id, "asset_id": asset.id})
        count = result.scalar()
        
        if count > 0:
            print(f"[SAFELY_ASSIGN DEBUG] Asset {asset.id} already linked to ticket {ticket.id} in database")
            return True
        
        # Use direct SQL insertion to avoid SQLAlchemy relationship issues
        print(f"[SAFELY_ASSIGN DEBUG] Inserting relationship via direct SQL")
        insert_stmt = text("""
            INSERT INTO ticket_assets (ticket_id, asset_id) 
            VALUES (:ticket_id, :asset_id)
        """)
        
        try:
            db_session.execute(insert_stmt, {"ticket_id": ticket.id, "asset_id": asset.id})
            print(f"[SAFELY_ASSIGN DEBUG] Successfully inserted asset {asset.id} to ticket {ticket.id} via SQL")
            return True
        except Exception as sql_error:
            # Check for duplicate key error (safe to ignore)
            if "UNIQUE constraint failed" in str(sql_error):
                print(f"[SAFELY_ASSIGN DEBUG] Relationship already exists (UNIQUE constraint), this is OK")
                return True
            else:
                print(f"[SAFELY_ASSIGN DEBUG] SQL insertion failed: {str(sql_error)}")
                return False
        
    except Exception as e:
        print(f"[SAFELY_ASSIGN DEBUG] Error assigning asset to ticket: {str(e)}")
        return False

@assets_bp.route('/add', methods=['POST'])
@login_required
def add_asset():
    """Add a new asset to the system"""
    db_session = db_manager.get_session()
    try:
        data = request.get_json()
        print(f"[ASSETS DEBUG] Received data: {data}")
        
        # Get form data
        asset_tag = data.get('asset_tag')
        serial_number = data.get('serial_number')
        name = data.get('name')
        model = data.get('model')
        category = data.get('category')
        location = data.get('location')
        condition = data.get('condition')
        status = data.get('status', 'IN_STOCK')
        notes = data.get('notes', '')
        tech_notes = data.get('tech_notes', '')
        asset_type = data.get('asset_type', 'MISC')
        ticket_id = data.get('ticket_id')  # Optional ticket ID to link to
        
        # Additional fields from the form
        receiving_date = data.get('receiving_date')
        po = data.get('po')
        customer = data.get('customer')
        country = data.get('country')
        erased = data.get('erased')
        hardware_type = data.get('hardware_type')
        cpu_type = data.get('cpu_type')
        cpu_cores = data.get('cpu_cores')
        memory = data.get('memory')
        harddrive = data.get('harddrive')
        gpu_cores = data.get('gpu_cores')
        keyboard = data.get('keyboard')
        charger = data.get('charger')
        diag = data.get('diag')

        print(f"[ASSETS DEBUG] Parsed fields: asset_tag={asset_tag}, serial_number={serial_number}, name={name}, ticket_id={ticket_id}")

        # Input validation
        if not all([asset_tag, serial_number, name]):
            missing = []
            if not asset_tag: missing.append('asset_tag')
            if not serial_number: missing.append('serial_number') 
            if not name: missing.append('name')
            print(f"[ASSETS DEBUG] Missing required fields: {missing}")
            return jsonify({'success': False, 'error': '[ASSETS_ROUTE] Asset tag, serial number, and name are required'}), 400

        # Check if asset tag or serial number already exists
        existing_asset = db_session.query(Asset).filter(
            (Asset.asset_tag == asset_tag) | (Asset.serial_num == serial_number)
        ).first()
        
        if existing_asset:
            if existing_asset.asset_tag == asset_tag:
                return jsonify({'success': False, 'error': '[ASSETS_ROUTE] Asset tag already exists'}), 400
            else:
                return jsonify({'success': False, 'error': '[ASSETS_ROUTE] Serial number already exists'}), 400

        # Parse receiving_date if provided
        receiving_date_obj = None
        if receiving_date:
            try:
                from datetime import datetime
                receiving_date_obj = datetime.strptime(receiving_date, '%Y-%m-%d')
            except ValueError:
                print(f"[ASSETS DEBUG] Invalid receiving_date format: {receiving_date}")

        # Create new asset with all fields
        print(f"[ASSETS DEBUG] Creating new asset with: asset_tag={asset_tag}, serial_num={serial_number}, name={name}, model={model}")
        new_asset = Asset(
            asset_tag=asset_tag,
            serial_num=serial_number,
            name=name,
            model=model,
            location=location,
            condition=condition,
            notes=notes,
            tech_notes=tech_notes,
            asset_type=asset_type,
            status=getattr(AssetStatus, status, AssetStatus.IN_STOCK),
            receiving_date=receiving_date_obj,
            po=po,
            customer=customer,
            country=country,
            erased=erased,
            hardware_type=hardware_type,
            cpu_type=cpu_type,
            cpu_cores=cpu_cores,
            memory=memory,
            harddrive=harddrive,
            gpu_cores=gpu_cores,
            keyboard=keyboard,
            charger=charger,
            diag=diag
        )
        
        db_session.add(new_asset)
        db_session.flush()  # Get the ID without committing
        print(f"[ASSETS DEBUG] Asset created successfully with ID: {new_asset.id}")
        
        # Create activity log for asset creation
        activity = Activity(
            user_id=current_user.id,
            type='asset_added',
            content=f'Added new asset: {asset_tag} - {name}',
            reference_id=new_asset.id
        )
        db_session.add(activity)

        # If ticket_id is provided, try to link the asset to the ticket
        if ticket_id:
            print(f"[ASSETS DEBUG] Attempting to link asset {new_asset.id} to ticket {ticket_id}")
            try:
                ticket = db_session.query(Ticket).get(int(ticket_id))
                if ticket:
                    print(f"[ASSETS DEBUG] Found ticket {ticket.id}")
                    print(f"[ASSETS DEBUG] Current ticket.assets before linking: {[a.id for a in ticket.assets]}")
                    
                    # Safely link asset to ticket
                    if _safely_assign_asset_to_ticket(ticket, new_asset, db_session):
                        print(f"[ASSETS DEBUG] Successfully linked asset to ticket")
                        print(f"[ASSETS DEBUG] Current ticket.assets after linking: {[a.id for a in ticket.assets]}")
                        
                        # Add activity for linking
                        linking_activity = Activity(
                            user_id=current_user.id,
                            type='asset_linked',
                            content=f'Linked asset {new_asset.asset_tag} to ticket #{ticket_id}',
                            reference_id=new_asset.id
                        )
                        db_session.add(linking_activity)
                        print(f"[ASSETS DEBUG] Added linking activity")
                        
                        # Auto-checkout asset for Asset Checkout tickets
                        print(f"[ASSETS DEBUG] Checking if ticket should auto-checkout asset")
                        print(f"[ASSETS DEBUG] Ticket category: {ticket.category}")
                        print(f"[ASSETS DEBUG] Ticket customer_id: {ticket.customer_id}")
                        
                        if ticket.category and _is_asset_checkout_ticket(ticket.category):
                            print(f"[ASSETS DEBUG] This is an Asset Checkout ticket ({ticket.category.value}), auto-checking out asset")
                            if _auto_checkout_asset_to_customer(ticket, new_asset, db_session):
                                print(f"[ASSETS DEBUG] Successfully auto-checked out asset to customer")
                                print(f"[ASSETS DEBUG] Asset status after checkout: {new_asset.status}")
                                print(f"[ASSETS DEBUG] Asset customer_id after checkout: {new_asset.customer_id}")
                            else:
                                print(f"[ASSETS DEBUG] Failed to auto-checkout asset to customer")
                        else:
                            if not ticket.category:
                                print(f"[ASSETS DEBUG] Ticket has no category - skipping auto-checkout")
                            else:
                                print(f"[ASSETS DEBUG] Ticket category {ticket.category.value} is not an Asset Checkout type - skipping auto-checkout")
                    else:
                        print(f"[ASSETS DEBUG] Failed to link asset to ticket")
                else:
                    print(f"[ASSETS DEBUG] Ticket {ticket_id} not found")
            except Exception as e:
                print(f"[ASSETS DEBUG] Exception during linking: {str(e)}")
                import traceback
                traceback.print_exc()
        
        # Single commit for everything
        print(f"[ASSETS DEBUG] About to commit all operations")
        try:
            db_session.commit()
            print(f"[ASSETS DEBUG] All operations committed successfully")
        except Exception as e:
            print(f"[ASSETS DEBUG] Error during commit: {str(e)}")
            import traceback
            traceback.print_exc()
            raise

        # Return success response with asset data
        return jsonify({
            'success': True,
            'asset': {
                'id': new_asset.id,
                'asset_tag': new_asset.asset_tag,
                'serial_number': new_asset.serial_num,
                'name': new_asset.name,
                'model': new_asset.model,
                'status': new_asset.status.value if new_asset.status else status,
                'type': asset_type,
                'condition': new_asset.condition,
                'customer': new_asset.customer,
                'country': new_asset.country,
                'hardware_type': new_asset.hardware_type,
                'cpu_type': new_asset.cpu_type,
                'memory': new_asset.memory,
                'harddrive': new_asset.harddrive
            }
        })
        
    except Exception as e:
        db_session.rollback()
        print(f"[ASSETS DEBUG] Exception in add_asset: {str(e)}")
        return jsonify({'success': False, 'error': f'[ASSETS_ROUTE] {str(e)}'}), 500
    finally:
        db_session.close()


@assets_bp.route('/<int:asset_id>', methods=['GET'])
@login_required
def view_asset(asset_id):
    """Redirect to inventory asset view"""
    return redirect(url_for('inventory.view_asset', asset_id=asset_id))


@assets_bp.route('/<int:asset_id>/unlink/<int:ticket_id>', methods=['POST'])
@login_required
def unlink_asset(asset_id, ticket_id):
    """Unlink an asset from a ticket"""
    db_session = db_manager.get_session()
    try:
        # Get the ticket and asset
        ticket = db_session.query(Ticket).get(ticket_id)
        asset = db_session.query(Asset).get(asset_id)
        
        if not ticket:
            return jsonify({'success': False, 'error': 'Ticket not found'}), 404
        
        if not asset:
            return jsonify({'success': False, 'error': 'Asset not found'}), 404
        
        # Check if the asset is linked to the ticket
        if asset in ticket.assets:
            # Remove the asset from the ticket's assets
            ticket.assets.remove(asset)
            
            # Add activity for unlinking
            activity = Activity(
                user_id=current_user.id,
                type='asset_unlinked',
                content=f'Unlinked asset {asset.asset_tag} from ticket #{ticket_id}',
                reference_id=asset.id
            )
            db_session.add(activity)
            db_session.commit()
            
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'Asset is not linked to this ticket'}), 400
        
    except Exception as e:
        db_session.rollback()
        print(f"Error unlinking asset: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db_session.close()

@assets_bp.route('/generate-label/<int:asset_id>')
@login_required
def generate_asset_label(asset_id):
    """Generate and display asset label for a specific asset"""
    db_session = SessionLocal()
    try:
        asset = db_session.query(Asset).filter_by(id=asset_id).first()
        if not asset:
            flash('Asset not found', 'error')
            return redirect(url_for('inventory.view'))
        
        # Load company relationship if not already loaded
        if not asset.company and asset.company_id:
            asset.company = db_session.query(Company).filter_by(id=asset.company_id).first()
        
        # Generate label as base64
        label_base64 = barcode_generator.generate_label_base64(asset)
        
        if not label_base64:
            flash('Failed to generate label', 'error')
            return redirect(url_for('inventory.view'))
        
        return render_template('assets/label_preview.html', 
                             asset=asset, 
                             label_image=label_base64)
    
    finally:
        db_session.close()

@assets_bp.route('/generate-barcode/<int:asset_id>')
@login_required
def generate_asset_barcode(asset_id):
    """Generate and display just the barcode for a specific asset"""
    db_session = SessionLocal()
    try:
        asset = db_session.query(Asset).filter_by(id=asset_id).first()
        if not asset:
            return jsonify({'error': 'Asset not found'}), 404
        
        # Generate barcode as base64
        barcode_base64 = barcode_generator.generate_barcode_base64(asset.serial_num)
        
        if not barcode_base64:
            return jsonify({'error': 'Failed to generate barcode'}), 500
        
        return jsonify({
            'success': True,
            'barcode': barcode_base64,
            'serial_number': asset.serial_num
        })
    
    finally:
        db_session.close()

@assets_bp.route('/bulk-labels', methods=['GET', 'POST'])
@login_required
def bulk_labels():
    """Generate bulk labels for multiple assets"""
    db_session = SessionLocal()
    try:
        if request.method == 'GET':
            # Show the bulk label selection page
            assets = db_session.query(Asset).filter(Asset.serial_num.isnot(None)).all()
            return render_template('assets/bulk_labels.html', assets=assets)
        
        elif request.method == 'POST':
            # Generate labels for selected assets
            asset_ids = request.form.getlist('asset_ids')
            if not asset_ids:
                flash('Please select at least one asset', 'error')
                return redirect(url_for('assets.bulk_labels'))
            
            # Get selected assets
            assets = db_session.query(Asset).filter(Asset.id.in_(asset_ids)).all()
            labels = []
            
            for asset in assets:
                # Load company relationship if not already loaded
                if not asset.company and asset.company_id:
                    asset.company = db_session.query(Company).filter_by(id=asset.company_id).first()
                
                label_base64 = barcode_generator.generate_label_base64(asset)
                if label_base64:
                    labels.append({
                        'asset': asset,
                        'label': label_base64
                    })
            
            if not labels:
                flash('Failed to generate any labels', 'error')
                return redirect(url_for('assets.bulk_labels'))
            
            return render_template('assets/bulk_labels_preview.html', labels=labels)
    
    finally:
        db_session.close()

@assets_bp.route('/download-label/<int:asset_id>')
@login_required
def download_label(asset_id):
    """Download asset label as PNG file"""
    db_session = SessionLocal()
    try:
        asset = db_session.query(Asset).filter_by(id=asset_id).first()
        if not asset:
            flash('Asset not found', 'error')
            return redirect(url_for('inventory.view'))
        
        # Load company relationship if not already loaded
        if not asset.company and asset.company_id:
            asset.company = db_session.query(Company).filter_by(id=asset.company_id).first()
        
        # Generate label image
        label_image = barcode_generator.generate_asset_label(asset)
        
        if not label_image:
            flash('Failed to generate label', 'error')
            return redirect(url_for('inventory.view'))
        
        # Convert to bytes
        img_buffer = io.BytesIO()
        label_image.save(img_buffer, format='PNG')
        img_buffer.seek(0)
        
        # Create response
        response = make_response(img_buffer.getvalue())
        response.headers['Content-Type'] = 'image/png'
        response.headers['Content-Disposition'] = f'attachment; filename=asset_label_{asset.serial_num}.png'
        
        return response
    
    finally:
        db_session.close()

@assets_bp.route('/labels')
@login_required
def labels_dashboard():
    """Asset labels dashboard"""
    db_session = SessionLocal()
    try:
        # Get assets with serial numbers for labeling
        assets = db_session.query(Asset).filter(Asset.serial_num.isnot(None)).limit(50).all()
        
        return render_template('assets/labels_dashboard.html', assets=assets)
    
    finally:
        db_session.close() 