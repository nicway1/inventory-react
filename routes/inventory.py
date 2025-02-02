from flask import Blueprint, render_template, request, jsonify, session, flash, redirect, url_for
from datetime import datetime
from utils.auth_decorators import login_required, admin_required
from utils.store_instances import inventory_store, db_manager
from models.asset import Asset, AssetStatus
from models.accessory import Accessory
import os
from werkzeug.utils import secure_filename
import pandas as pd
from sqlalchemy import func, case, or_
from utils.db_manager import DatabaseManager
from flask_wtf.csrf import generate_csrf

inventory_bp = Blueprint('inventory', __name__, url_prefix='/inventory')
db_manager = DatabaseManager()

# Configure upload settings
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'csv'}

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@inventory_bp.route('/')
@login_required
def view_inventory():
    db_session = db_manager.get_session()
    try:
        # Get counts using a simpler query
        tech_assets_count = db_session.query(Asset).count()
        accessories_count = db_session.query(Accessory).count()

        print(f"Initial Tech Assets Count: {tech_assets_count}")  # Debug print

        # Get unique values for filters from assets only
        companies = db_session.query(Asset.customer).distinct().all()
        companies = sorted(list(set([c[0] for c in companies if c[0]])))

        models = db_session.query(Asset.model).distinct().all()
        models = sorted(list(set([m[0] for m in models if m[0]])))

        countries = db_session.query(Asset.country).distinct().all()
        countries = sorted(list(set([c[0] for c in countries if c[0]])))

        # Get accessories with counts
        accessories = db_session.query(
            Accessory.name,
            Accessory.category,
            func.count(Accessory.id).label('total_count'),
            func.sum(case([(Accessory.status == 'Available', 1)], else_=0)).label('available_count')
        ).group_by(Accessory.name, Accessory.category).all()

        accessories_list = [
            {
                'name': acc.name,
                'category': acc.category,
                'total_count': acc.total_count,
                'available_count': acc.available_count
            }
            for acc in accessories
        ]

        print(f"Tech Assets Count: {tech_assets_count}")  # Debug print
        print(f"Accessories Count: {accessories_count}")  # Debug print

        return render_template(
            'inventory/view.html',
            tech_assets_count=tech_assets_count,
            accessories_count=accessories_count,
            companies=companies,
            models=models,
            countries=countries,
            accessories=accessories_list
        )

    finally:
        db_session.close()

@inventory_bp.route('/tech-assets')
@login_required
def view_tech_assets():
    db_session = db_manager.get_session()
    try:
        assets = db_session.query(Asset).all()
        total_count = len(assets)
        
        # Debug print to check asset data
        for asset in assets:
            print(f"Asset {asset.id}:")
            print(f"  - Hardware Type: '{asset.hardware_type}'")
            print(f"  - Model: '{asset.model}'")
            print(f"  - Status: '{asset.status.value if asset.status else 'Unknown'}'")
            
        return jsonify({
            'total_count': total_count,
            'assets': [
                {
                    'id': asset.id,
                    'product': f"{asset.hardware_type} {asset.model}" if asset.hardware_type else asset.model,
                    'asset_tag': asset.asset_tag,
                    'serial_num': asset.serial_num,
                    'model': asset.model,
                    'inventory': asset.status.value if asset.status else 'Unknown',
                    'customer': asset.customer,
                    'country': asset.country
                }
                for asset in assets
            ]
        })
    finally:
        db_session.close()

@inventory_bp.route('/accessories')
@login_required
def view_accessories():
    db_session = db_manager.get_session()
    try:
        accessories = db_session.query(Accessory).all()
        return render_template('inventory/accessories.html', accessories=accessories)
    finally:
        db_session.close()

@inventory_bp.route('/filter', methods=['POST'])
@login_required
def filter_inventory():
    try:
        data = request.json
        print("Received filter data:", data)  # Debug log
        
        if not data:
            return jsonify({
                'error': 'No filter data received',
                'total_count': 0,
                'assets': []
            }), 400
        
        db_session = db_manager.get_session()
        try:
            # Build query based on filters
            assets_query = db_session.query(Asset)

            if data.get('search'):
                search = f"%{data['search']}%"
                print(f"Applying search filter: {search}")  # Debug log
                assets_query = assets_query.filter(
                    or_(
                        Asset.serial_num.ilike(search),
                        Asset.asset_tag.ilike(search),
                        Asset.model.ilike(search),
                        Asset.country.ilike(search)
                    )
                )

            if data.get('inventory_status'):
                print(f"Applying status filter: {data['inventory_status']}")  # Debug log
                assets_query = assets_query.filter(Asset.status == data['inventory_status'])

            if data.get('company'):
                print(f"Applying company filter: {data['company']}")  # Debug log
                assets_query = assets_query.filter(Asset.customer == data['company'])

            if data.get('model'):
                print(f"Applying model filter: {data['model']}")  # Debug log
                assets_query = assets_query.filter(Asset.model == data['model'])

            if data.get('country'):
                print(f"Applying country filter: {data['country']}")  # Debug log
                assets_query = assets_query.filter(Asset.country == data['country'])

            # Get results
            try:
                assets = assets_query.all()
                tech_assets_count = len(assets)

                print(f"Filtered Tech Assets Count: {tech_assets_count}")

                response_data = {
                    'total_count': tech_assets_count,  # Use consistent key name
                    'assets': [
                        {
                            'id': asset.id,
                            'product': f"{asset.hardware_type} {asset.model}" if asset.hardware_type else asset.model,
                            'asset_tag': asset.asset_tag,
                            'serial_num': asset.serial_num,
                            'model': asset.model,
                            'inventory': asset.status.value if asset.status else 'Unknown',
                            'customer': asset.customer,
                            'country': asset.country
                        }
                        for asset in assets
                    ]
                }
                
                print("Sending response data:", response_data)  # Debug log
                return jsonify(response_data)
            
            except Exception as e:
                print(f"Error processing query results: {str(e)}")
                return jsonify({
                    'error': 'Error processing query results',
                    'message': str(e),
                    'total_count': 0,
                    'assets': []
                }), 500

        finally:
            db_session.close()
            
    except Exception as e:
        print(f"Error in filter_inventory: {str(e)}")
        return jsonify({
            'error': 'Server error',
            'message': str(e),
            'total_count': 0,
            'assets': []
        }), 500

@inventory_bp.route('/checkout/<int:id>', methods=['POST'])
@login_required
def checkout_accessory(id):
    db_session = db_manager.get_session()
    try:
        accessory = db_session.query(Accessory).get(id)
        if not accessory:
            flash('Accessory not found')
            return redirect(url_for('inventory.view_inventory'))

        if accessory.status != 'Available':
            flash('This accessory is not available for checkout')
            return redirect(url_for('inventory.view_inventory'))

        # Update accessory status
        accessory.status = 'Checked Out'
        accessory.customer = session.get('user_id')  # Or however you track the current user
        db_session.commit()

        flash('Accessory checked out successfully')
        return redirect(url_for('inventory.view_inventory'))

    finally:
        db_session.close()

@inventory_bp.route('/item/<int:item_id>')
@login_required
def view_item(item_id):
    item = inventory_store.get_item(item_id)
    if not item:
        flash('Item not found')
        return redirect(url_for('inventory.view_inventory'))
    
    return render_template(
        'inventory/item_details.html',
        item=item
    )

@inventory_bp.route('/item/add', methods=['GET', 'POST'])
@login_required
def add_item():
    if request.method == 'POST':
        try:
            name = request.form.get('name')
            category = request.form.get('category')
            status = request.form.get('status', 'Available')
            
            if not name or not category:
                flash('Name and category are required')
                return redirect(url_for('inventory.add_item'))
            
            item = inventory_store.create_item(name, category, status)
            flash('Item added successfully')
            return redirect(url_for('inventory.view_inventory'))
        except Exception as e:
            flash(f'Error adding item: {str(e)}')
            return redirect(url_for('inventory.add_item'))

    return render_template('inventory/add_item.html')

@inventory_bp.route('/item/<int:item_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_item(item_id):
    item = inventory_store.get_item(item_id)
    if not item:
        flash('Item not found')
        return redirect(url_for('inventory.view_inventory'))
    
    if request.method == 'POST':
        try:
            name = request.form.get('name')
            category = request.form.get('category')
            status = request.form.get('status')
            
            if not name or not category:
                flash('Name and category are required')
                return redirect(url_for('inventory.edit_item', item_id=item_id))
            
            inventory_store.update_item(
                item_id,
                name=name,
                category=category,
                status=status
            )
            flash('Item updated successfully')
            return redirect(url_for('inventory.view_inventory'))
                
        except Exception as e:
            flash(f'Error updating item: {str(e)}')
            return redirect(url_for('inventory.edit_item', item_id=item_id))

    return render_template('inventory/edit_item.html', item=item)

@inventory_bp.route('/item/<int:item_id>/delete', methods=['POST'])
@login_required
def delete_item(item_id):
    if inventory_store.delete_item(item_id):
        flash('Item deleted successfully')
    else:
        flash('Error deleting item')
    return redirect(url_for('inventory.view_inventory'))

@inventory_bp.route('/item/<int:item_id>/assign', methods=['POST'])
@login_required
def assign_item(item_id):
    user_id = request.form.get('user_id')
    if not user_id:
        flash('User ID is required')
        return redirect(url_for('inventory.view_item', item_id=item_id))
    
    if inventory_store.assign_item(item_id, int(user_id)):
        flash('Item assigned successfully')
    else:
        flash('Error assigning item')
    return redirect(url_for('inventory.view_item', item_id=item_id))

@inventory_bp.route('/item/<int:item_id>/unassign', methods=['POST'])
@login_required
def unassign_item(item_id):
    if inventory_store.unassign_item(item_id):
        flash('Item unassigned successfully')
    else:
        flash('Error unassigning item')
    return redirect(url_for('inventory.view_item', item_id=item_id))

@inventory_bp.route('/import', methods=['GET', 'POST'])
@login_required
@admin_required
def import_inventory():
    if request.method == 'POST':
        try:
            if 'file' in request.files:
                file = request.files['file']
                import_type = request.form.get('import_type', 'assets')
                dry_run = request.form.get('dry_run') == 'on'
                
                if file and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    filepath = os.path.join(UPLOAD_FOLDER, filename)
                    file.save(filepath)
                    
                    try:
                        df = pd.read_csv(filepath)
                        
                        # Store preview data in session
                        preview_data = {
                            'columns': df.columns.tolist(),
                            'rows': df.head().values.tolist(),
                            'total_rows': len(df)
                        }
                        session['preview_data'] = preview_data
                        session['import_filepath'] = filepath
                        session['import_type'] = import_type
                        
                        if dry_run:
                            flash('Dry run completed successfully. No data was imported.', 'success')
                            os.remove(filepath)
                            return redirect(url_for('inventory.import_inventory'))
                        
                        return render_template('inventory/import.html', 
                                             preview_data=preview_data,
                                             filename=filename,
                                             import_type=import_type)
                    
                    except Exception as e:
                        flash(f'Error reading CSV file: {str(e)}', 'error')
                        if os.path.exists(filepath):
                            os.remove(filepath)
                        return redirect(url_for('inventory.import_inventory'))
                else:
                    flash('Invalid file type. Please upload a CSV file.', 'error')
                    return redirect(url_for('inventory.import_inventory'))
            
            elif 'action' in request.form:
                action = request.form['action']
                filepath = session.get('import_filepath')
                import_type = session.get('import_type', 'assets')
                
                if action == 'confirm' and filepath and os.path.exists(filepath):
                    try:
                        df = pd.read_csv(filepath)
                        db_session = db_manager.get_session()
                        
                        try:
                            if import_type == 'assets':
                                # Import assets
                                for _, row in df.iterrows():
                                    # Convert erased value to boolean
                                    erased_value = str(row.get('ERASED', '')).upper()
                                    erased = erased_value in ['YES', 'TRUE', 'COMPLETED', '1']
                                    
                                    # Map inventory status to AssetStatus enum
                                    inventory_status = str(row.get('INVENTORY', '')).upper()
                                    if inventory_status == 'READY TO DEPLOY':
                                        status = AssetStatus.READY_TO_DEPLOY
                                    elif inventory_status == 'IN STOCK':
                                        status = AssetStatus.IN_STOCK
                                    elif inventory_status == 'SHIPPED':
                                        status = AssetStatus.SHIPPED
                                    elif inventory_status == 'DEPLOYED':
                                        status = AssetStatus.DEPLOYED
                                    elif inventory_status == 'REPAIR':
                                        status = AssetStatus.REPAIR
                                    elif inventory_status == 'ARCHIVED':
                                        status = AssetStatus.ARCHIVED
                                    else:
                                        status = AssetStatus.IN_STOCK  # Default status
                                    
                                    asset = Asset(
                                        asset_tag=str(row.get('ASSET TAG', '')),
                                        receiving_date=pd.to_datetime(row.get('RECEIVING DATE')).date() if pd.notna(row.get('RECEIVING DATE')) else None,
                                        keyboard=str(row.get('KEYBOARD', '')),
                                        serial_num=str(row.get('SERIAL NUMBER', '')),
                                        po=str(row.get('PO', '')) if pd.notna(row.get('PO')) else '',
                                        model=str(row.get('MODEL', '')),
                                        erased=erased,  # Use converted boolean value
                                        customer=str(row.get('CUSTOMER', '')),
                                        condition=str(row.get('CONDITION', '')),
                                        diag=str(row.get('DIAG', '')),
                                        hardware_type=str(row.get('HARDWARE TYPE', '')),
                                        cpu_type=str(row.get('CPU TYPE', '')),
                                        cpu_cores=str(row.get('CPU CORES', '')),
                                        gpu_cores=str(row.get('GPU CORES', '')),
                                        memory=str(row.get('MEMORY', '')),
                                        harddrive=str(row.get('HARDDRIVE', '')),
                                        charger=str(row.get('CHARGER', '')),
                                        country=str(row.get('COUNTRY', '')),
                                        status=status  # Use mapped status
                                    )
                                    db_session.add(asset)
                            
                            else:  # import_type == 'accessories'
                                # Group accessories by name and category
                                grouped = df.groupby(['NAME', 'CATEGORY']).size().reset_index(name='count')
                                
                                for _, row in grouped.iterrows():
                                    # Check if accessory already exists
                                    existing = db_session.query(Accessory).filter(
                                        Accessory.name == row['NAME'],
                                        Accessory.category == row['CATEGORY']
                                    ).first()
                                    
                                    if existing:
                                        # Update quantities
                                        existing.total_quantity += row['count']
                                        existing.available_quantity += row['count']
                                    else:
                                        # Create new accessory
                                        accessory = Accessory(
                                            name=row['NAME'],
                                            category=row['CATEGORY'],
                                            total_quantity=row['count'],
                                            available_quantity=row['count']
                                        )
                                        db_session.add(accessory)
                            
                            db_session.commit()
                            flash('Data imported successfully!', 'success')
                        
                        except Exception as e:
                            db_session.rollback()
                            flash(f'Error importing data: {str(e)}', 'error')
                            return redirect(url_for('inventory.import_inventory'))
                        
                        finally:
                            db_session.close()
                            # Clean up
                            os.remove(filepath)
                            session.pop('preview_data', None)
                            session.pop('import_filepath', None)
                            session.pop('import_type', None)
                            return redirect(url_for('inventory.import_inventory'))
                    
                    except Exception as e:
                        flash(f'Error processing file: {str(e)}', 'error')
                        return redirect(url_for('inventory.import_inventory'))
                
                elif action == 'cancel' and filepath and os.path.exists(filepath):
                    os.remove(filepath)
                    session.pop('preview_data', None)
                    session.pop('import_filepath', None)
                    session.pop('import_type', None)
                    flash('Import cancelled.', 'info')
                    return redirect(url_for('inventory.import_inventory'))
        
        except Exception as e:
            flash(f'Error: {str(e)}', 'error')
            return redirect(url_for('inventory.import_inventory'))
    
    return render_template('inventory/import.html')

@inventory_bp.route('/asset/<int:asset_id>')
@login_required
def view_asset(asset_id):
    db_session = db_manager.get_session()
    try:
        asset = db_session.query(Asset).get(asset_id)
        if not asset:
            flash('Asset not found', 'error')
            return redirect(url_for('inventory.view_inventory'))
        
        return render_template('inventory/asset_details.html', asset=asset)
    finally:
        db_session.close()

@inventory_bp.route('/asset/<int:asset_id>/update-status', methods=['POST'])
@login_required
def update_asset_status(asset_id):
    new_status = request.form.get('status')
    if not new_status:
        flash('No status provided', 'error')
        return redirect(url_for('inventory.view_asset', asset_id=asset_id))
    
    db_session = db_manager.get_session()
    try:
        asset = db_session.query(Asset).get(asset_id)
        if not asset:
            flash('Asset not found', 'error')
            return redirect(url_for('inventory.view_inventory'))
        
        asset.status = new_status
        db_session.commit()
        flash(f'Status updated to {new_status}', 'success')
        return redirect(url_for('inventory.view_asset', asset_id=asset_id))
    finally:
        db_session.close()

@inventory_bp.after_request
def add_csrf_token_to_response(response):
    if 'text/html' in response.headers.get('Content-Type', ''):
        response.set_cookie('csrf_token', generate_csrf())
    return response 