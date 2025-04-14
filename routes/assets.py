from flask import Blueprint, request, jsonify, redirect, url_for, flash, session
from utils.auth_decorators import login_required, admin_required
from utils.store_instances import inventory_store, db_manager, ticket_store
from models.asset import Asset, AssetStatus
from models.activity import Activity
from models.ticket import Ticket
from flask_login import current_user

# Create Blueprint
assets_bp = Blueprint('assets', __name__, url_prefix='/assets')

@assets_bp.route('/add', methods=['POST'])
@login_required
def add_asset():
    """Add a new asset and optionally associate it with a ticket"""
    db_session = db_manager.get_session()
    try:
        # Get form data
        asset_tag = request.form.get('asset_tag')
        serial_number = request.form.get('serial_number')
        name = request.form.get('name')
        status = request.form.get('status')
        asset_type = request.form.get('asset_type')
        notes = request.form.get('notes', '')
        ticket_id = request.form.get('ticket_id')  # Optional ticket to associate with

        # Basic validation
        if not asset_tag or not serial_number or not name:
            return jsonify({'success': False, 'error': 'Missing required fields'}), 400

        # Check if asset with same tag or serial already exists
        existing_asset = db_session.query(Asset).filter(
            (Asset.asset_tag == asset_tag) | (Asset.serial_num == serial_number)
        ).first()
        
        if existing_asset:
            return jsonify({
                'success': False, 
                'error': f'Asset with tag {asset_tag} or serial {serial_number} already exists'
            }), 400

        # Convert status to AssetStatus enum
        asset_status = AssetStatus.IN_STOCK
        if status == 'Active' or status == 'Deployed':
            asset_status = AssetStatus.DEPLOYED
        elif status == 'In Stock':
            asset_status = AssetStatus.IN_STOCK
        elif status == 'Repair':
            asset_status = AssetStatus.REPAIR
        elif status == 'Inactive':
            asset_status = AssetStatus.ARCHIVED

        # Create new asset
        new_asset = Asset(
            asset_tag=asset_tag,
            serial_num=serial_number,
            name=name,
            status=asset_status,
            asset_type=asset_type,
            notes=notes
        )
        
        db_session.add(new_asset)
        db_session.commit()
        
        # Add activity tracking
        activity = Activity(
            user_id=current_user.id,
            type='asset_created',
            content=f'Created new asset: {new_asset.name} (Asset Tag: {new_asset.asset_tag})',
            reference_id=new_asset.id
        )
        db_session.add(activity)
        db_session.commit()

        # If ticket_id is provided, link this asset to the ticket
        if ticket_id:
            try:
                ticket_id = int(ticket_id)
                ticket = db_session.query(Ticket).get(ticket_id)
                
                if ticket:
                    # Link asset to ticket
                    ticket.assets.append(new_asset)
                    
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