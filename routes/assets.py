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

# Create Blueprint
assets_bp = Blueprint('assets', __name__, url_prefix='/assets')
db_manager = DatabaseManager()

def _safely_assign_asset_to_ticket(ticket, asset, db_session):
    """
    Safely assign an asset to a ticket, checking for existing relationships first
    
    Args:
        ticket: Ticket object
        asset: Asset object
        db_session: Database session
        
    Returns:
        bool: True if assignment was successful or already exists, False otherwise
    """
    try:
        # Check if asset is already assigned to this ticket
        if asset in ticket.assets:
            print(f"Asset {asset.id} ({asset.asset_tag}) already assigned to ticket {ticket.id}")
            return True
        
        # Check if the relationship already exists in the database
        stmt = text("""
            SELECT COUNT(*) FROM ticket_assets 
            WHERE ticket_id = :ticket_id AND asset_id = :asset_id
        """)
        result = db_session.execute(stmt, {"ticket_id": ticket.id, "asset_id": asset.id})
        count = result.scalar()
        
        if count > 0:
            print(f"Asset {asset.id} already linked to ticket {ticket.id} in database")
            return True
        
        # Safe to assign - add the asset to the ticket
        ticket.assets.append(asset)
        print(f"Successfully assigned asset {asset.id} ({asset.asset_tag}) to ticket {ticket.id}")
        return True
        
    except Exception as e:
        print(f"Error assigning asset to ticket: {str(e)}")
        return False

@assets_bp.route('/add', methods=['POST'])
@login_required
def add_asset():
    """Add a new asset to the system"""
    db_session = db_manager.get_session()
    try:
        data = request.get_json()
        
        # Get form data
        asset_tag = data.get('asset_tag')
        serial_number = data.get('serial_number')
        name = data.get('name')
        category = data.get('category')
        location = data.get('location')
        condition = data.get('condition')
        status = data.get('status', 'In Stock')
        notes = data.get('notes', '')
        asset_type = data.get('type', 'MISC')
        ticket_id = data.get('ticket_id')  # Optional ticket ID to link to
        
        # Input validation
        if not all([asset_tag, serial_number, name]):
            return jsonify({'success': False, 'error': 'Asset tag, serial number, and name are required'}), 400
        
        # Check if asset tag or serial number already exists
        existing_asset = db_session.query(Asset).filter(
            (Asset.asset_tag == asset_tag) | (Asset.serial_num == serial_number)
        ).first()
        
        if existing_asset:
            if existing_asset.asset_tag == asset_tag:
                return jsonify({'success': False, 'error': 'Asset tag already exists'}), 400
            else:
                return jsonify({'success': False, 'error': 'Serial number already exists'}), 400
        
        # Create new asset
        new_asset = Asset(
            asset_tag=asset_tag,
            serial_num=serial_number,
            name=name,
            location=location,
            condition=condition,
            notes=notes,
            asset_type=asset_type,
            status=AssetStatus.IN_STOCK if status == 'In Stock' else AssetStatus.READY_TO_DEPLOY
        )
        
        db_session.add(new_asset)
        db_session.commit()
        
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
            try:
                ticket = db_session.query(Ticket).get(int(ticket_id))
                if ticket:
                    # Safely link asset to ticket
                    if _safely_assign_asset_to_ticket(ticket, new_asset, db_session):
                        # Add activity for linking
                        activity = Activity(
                            user_id=current_user.id,
                            type='asset_linked',
                            content=f'Linked asset {new_asset.asset_tag} to ticket #{ticket_id}',
                            reference_id=new_asset.id
                        )
                        db_session.add(activity)
                        db_session.commit()
            except (ValueError, AttributeError) as e:
                # Log the error but don't fail - still return success for asset creation
                print(f"Error linking asset to ticket: {str(e)}")

        # Return success response with asset data
        return jsonify({
            'success': True,
            'asset': {
                'id': new_asset.id,
                'asset_tag': new_asset.asset_tag,
                'serial_number': new_asset.serial_num,
                'name': new_asset.name,
                'status': status,
                'type': asset_type
            }
        })
        
    except Exception as e:
        db_session.rollback()
        print(f"Error adding asset: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500
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