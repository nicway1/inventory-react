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
from flask_login import current_user

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
                    'country': asset.country,
                    'cpu_type': asset.cpu_type,
                    'cpu_cores': asset.cpu_cores,
                    'gpu_cores': asset.gpu_cores,
                    'memory': asset.memory,
                    'harddrive': asset.harddrive
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
        # Get all accessories with their full details
        accessories = db_session.query(Accessory).order_by(Accessory.name).all()
        
        # Get current user's admin status
        is_admin = current_user.is_admin if current_user.is_authenticated else False
        
        return render_template(
            'inventory/accessories.html',
            accessories=accessories,
            is_admin=is_admin
        )
    except Exception as e:
        flash(f'Error loading accessories: {str(e)}', 'error')
        return redirect(url_for('inventory.view_inventory'))
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
                            'country': asset.country,
                            'cpu_type': asset.cpu_type,
                            'cpu_cores': asset.cpu_cores
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
# @login_required  # Temporarily commented out for testing
# @admin_required  # Temporarily commented out for testing
def import_inventory():
    if request.method == 'POST':
        db_session = db_manager.get_session()
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
                        # Helper function to clean values
                        def clean_value(val):
                            if pd.isna(val) or str(val).lower() == 'nan':
                                return None
                            return str(val).strip()  # Add strip() to remove any whitespace

                        # Helper function to parse date
                        def parse_date(date_str):
                            if pd.isna(date_str) or str(date_str).lower() in ['present', 'nan', '']:
                                return None
                            try:
                                return pd.to_datetime(date_str).date()
                            except:
                                return None

                        # Helper function to parse numeric values
                        def parse_numeric(val):
                            if pd.isna(val) or str(val).lower() == 'nan' or str(val).strip() == '':
                                return None
                            try:
                                # Convert to integer first, then to string
                                num_val = int(float(val))
                                if num_val > 0:  # Only return positive values
                                    return str(num_val)
                                return None
                            except:
                                return None  # Return None if conversion fails

                        # Read CSV file with no headers and assign our own column names
                        column_names = [
                            'Index', 'Asset Type', 'Product', 'ASSET TAG', 'Receiving date', 'Keyboard', 
                            'SERIAL NUMBER', 'PO', 'MODEL', 'ERASED', 'CUSTOMER', 'CONDITION', 'DIAG', 
                            'HARDWARE TYPE', 'CPU TYPE', 'CPU CORES', 'GPU CORES', 'MEMORY', 'HARDDRIVE', 
                            'STATUS', 'CHARGER', 'INCLUDED', 'INVENTORY', 'country'
                        ]

                        # Read the CSV file, skipping the first row (header)
                        df = pd.read_csv(filepath, skiprows=[0], names=column_names)

                        # Drop the index column
                        df = df.drop('Index', axis=1)

                        # Create preview data
                        preview_data = []
                        for _, row in df.iterrows():
                            # Clean and format the data
                            preview_row = {
                                'Asset Tag': str(row.get('ASSET TAG', '')).strip(),
                                'Serial Number': str(row.get('SERIAL NUMBER', '')).strip(),
                                'Product': f"MacBook Pro {row.get('MODEL', '')} Apple {row.get('CPU TYPE', '')}",
                                'Model': str(row.get('MODEL', '')).strip(),
                                'Hardware Type': str(row.get('HARDWARE TYPE', '')).strip(),
                                'CPU Type': str(row.get('CPU TYPE', '')).strip(),
                                'CPU Cores': str(row.get('CPU CORES', '')).strip(),
                                'GPU Cores': str(row.get('GPU CORES', '')).strip(),
                                'Memory': str(row.get('MEMORY', '')).strip(),
                                'Hard Drive': str(row.get('HARDDRIVE', '')).strip(),
                                'Status': str(row.get('STATUS', 'IN STOCK')).strip(),
                                'Customer': str(row.get('CUSTOMER', '')).strip(),
                                'Country': str(row.get('country', '')).strip(),
                                'PO': str(row.get('PO', '')).strip(),
                                'Receiving Date': str(row.get('Receiving date', '')).strip(),
                                'Condition': str(row.get('CONDITION', '')).strip(),
                                'Diagnostic': str(row.get('DIAG', '')).strip(),
                                'Erased': str(row.get('ERASED', '')).strip(),
                                'Keyboard': str(row.get('Keyboard', '')).strip(),
                                'Charger': str(row.get('CHARGER', '')).strip(),
                                'Included': str(row.get('INCLUDED', '')).strip()
                            }
                            preview_data.append(preview_row)

                        # Store preview data in session
                        session['preview_data'] = preview_data
                        session['filename'] = filename
                        session['total_rows'] = len(preview_data)

                        return render_template('inventory/import.html',
                                            preview_data=preview_data,
                                            filename=filename,
                                            total_rows=len(preview_data))

                    except Exception as e:
                        db_session.rollback()
                        raise e
                    finally:
                        if os.path.exists(filepath) and not dry_run:
                            os.remove(filepath)
                else:
                    flash('Invalid file type. Please upload a CSV file.', 'error')
                    return redirect(url_for('inventory.import_inventory'))
        except Exception as e:
            flash(f'Error reading CSV file: {str(e)}', 'error')
            return redirect(url_for('inventory.import_inventory'))
        finally:
            db_session.close()

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

@inventory_bp.route('/accessories/add', methods=['GET', 'POST'])
@login_required
def add_accessory():
    if request.method == 'POST':
        db_session = db_manager.get_session()
        try:
            # Create new accessory from form data
            new_accessory = Accessory(
                name=request.form['name'],
                category=request.form['category'],
                manufacturer=request.form['manufacturer'],
                model_no=request.form['model_no'],
                total_quantity=int(request.form['total_quantity']),
                available_quantity=int(request.form['total_quantity']),  # Initially all are available
                status='Available',
                notes=request.form.get('notes', '')
            )
            
            db_session.add(new_accessory)
            db_session.commit()
            flash('Accessory added successfully!', 'success')
            return redirect(url_for('inventory.view_accessories'))
            
        except Exception as e:
            db_session.rollback()
            flash(f'Error adding accessory: {str(e)}', 'error')
            return redirect(url_for('inventory.add_accessory'))
        finally:
            db_session.close()
            
    return render_template('inventory/add_accessory.html')

@inventory_bp.route('/accessories/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_accessory(id):
    db_session = db_manager.get_session()
    try:
        accessory = db_session.query(Accessory).get(id)
        if not accessory:
            flash('Accessory not found', 'error')
            return redirect(url_for('inventory.view_accessories'))

        if request.method == 'POST':
            try:
                # Update accessory with form data
                accessory.name = request.form['name']
                accessory.category = request.form['category']
                accessory.manufacturer = request.form['manufacturer']
                accessory.model_no = request.form['model_no']
                new_total = int(request.form['total_quantity'])
                
                # Update available quantity proportionally
                if accessory.total_quantity > 0:
                    ratio = accessory.available_quantity / accessory.total_quantity
                    accessory.available_quantity = int(new_total * ratio)
                else:
                    accessory.available_quantity = new_total
                
                accessory.total_quantity = new_total
                accessory.notes = request.form.get('notes', '')
                
                db_session.commit()
                flash('Accessory updated successfully!', 'success')
                return redirect(url_for('inventory.view_accessories'))
                
            except Exception as e:
                db_session.rollback()
                flash(f'Error updating accessory: {str(e)}', 'error')
                return redirect(url_for('inventory.edit_accessory', id=id))
            
        return render_template('inventory/edit_accessory.html', accessory=accessory)
        
    finally:
        db_session.close()

@inventory_bp.route('/accessories/<int:id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_accessory(id):
    db_session = db_manager.get_session()
    try:
        accessory = db_session.query(Accessory).get(id)
        if not accessory:
            flash('Accessory not found', 'error')
            return redirect(url_for('inventory.view_accessories'))

        try:
            db_session.delete(accessory)
            db_session.commit()
            flash('Accessory deleted successfully!', 'success')
        except Exception as e:
            db_session.rollback()
            flash(f'Error deleting accessory: {str(e)}', 'error')
            
        return redirect(url_for('inventory.view_accessories'))
        
    finally:
        db_session.close()

@inventory_bp.route('/assets/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_asset():
    if request.method == 'POST':
        db_session = db_manager.get_session()
        try:
            # Map inventory status to AssetStatus enum
            inventory_status = request.form.get('status', '').upper()
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

            # Get cost price if provided
            cost_price = None
            if request.form.get('cost_price'):
                try:
                    cost_price = float(request.form.get('cost_price'))
                except ValueError:
                    flash('Invalid cost price value', 'error')
                    return redirect(url_for('inventory.add_asset'))

            # Create new asset from form data
            new_asset = Asset(
                asset_tag=request.form.get('asset_tag', ''),
                receiving_date=datetime.strptime(request.form.get('receiving_date', ''), '%Y-%m-%d').date() if request.form.get('receiving_date') else None,
                keyboard=request.form.get('keyboard', ''),
                serial_num=request.form.get('serial_num', ''),
                po=request.form.get('po', ''),
                model=request.form.get('model', ''),
                erased=request.form.get('erased') == 'true',
                customer=request.form.get('customer', ''),
                condition=request.form.get('condition', ''),
                diag=request.form.get('diag', ''),
                hardware_type=request.form.get('hardware_type', ''),
                cpu_type=request.form.get('cpu_type', ''),
                cpu_cores=request.form.get('cpu_cores', ''),
                gpu_cores=request.form.get('gpu_cores', ''),
                memory=request.form.get('memory', ''),
                harddrive=request.form.get('harddrive', ''),
                charger=request.form.get('charger', ''),
                country=request.form.get('country', ''),
                status=status,
                cost_price=cost_price
            )
            
            db_session.add(new_asset)
            db_session.commit()
            flash('Asset added successfully!', 'success')
            return redirect(url_for('inventory.view_inventory'))
            
        except Exception as e:
            db_session.rollback()
            flash(f'Error adding asset: {str(e)}', 'error')
            return redirect(url_for('inventory.add_asset'))
        finally:
            db_session.close()
            
    return render_template('inventory/add_asset.html', statuses=AssetStatus)

@inventory_bp.after_request
def add_csrf_token_to_response(response):
    if 'text/html' in response.headers.get('Content-Type', ''):
        response.set_cookie('csrf_token', generate_csrf())
    return response 