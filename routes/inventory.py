from flask import Blueprint, render_template, request, jsonify, session, flash, redirect, url_for, send_file, abort
from datetime import datetime
from utils.auth_decorators import login_required, admin_required
from utils.store_instances import inventory_store, db_manager
from models.asset import Asset, AssetStatus
from models.accessory import Accessory
from models.customer_user import CustomerUser
from models.asset_history import AssetHistory
from models.accessory_history import AccessoryHistory
from models.user import User, UserType, Country
from models.asset_history import AssetHistory
from models.accessory_history import AccessoryHistory
import os
from werkzeug.utils import secure_filename
import pandas as pd
from sqlalchemy import func, case, or_
from utils.db_manager import DatabaseManager
from flask_wtf.csrf import generate_csrf
from flask_login import current_user
import json
import time
import io
import csv
from models.activity import Activity
from sqlalchemy.orm import joinedload
from models.company import Company

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
        # Get the current user
        user = db_manager.get_user(session['user_id'])
        
        # Base query for tech assets
        tech_assets_query = db_session.query(Asset)
        
        # Filter by country if user is Country Admin
        if user.user_type == UserType.COUNTRY_ADMIN and user.assigned_country:
            tech_assets_query = tech_assets_query.filter(Asset.country == user.assigned_country.value)
        
        # Get counts
        tech_assets_count = tech_assets_query.count()
        accessories_count = db_session.query(func.sum(Accessory.total_quantity)).scalar() or 0

        # Get unique values for filters from filtered assets only
        companies = tech_assets_query.with_entities(Asset.customer).distinct().all()
        companies = sorted(list(set([c[0] for c in companies if c[0]])))

        models = tech_assets_query.with_entities(Asset.model).distinct().all()
        models = sorted(list(set([m[0] for m in models if m[0]])))

        # For Country Admin, only show their assigned country
        if user.user_type == UserType.COUNTRY_ADMIN and user.assigned_country:
            countries = [user.assigned_country.value]
        else:
            countries = tech_assets_query.with_entities(Asset.country).distinct().all()
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

        return render_template(
            'inventory/view.html',
            tech_assets_count=tech_assets_count,
            accessories_count=accessories_count,
            companies=companies,
            models=models,
            countries=countries,
            accessories=accessories_list,
            user=user
        )

    finally:
        db_session.close()

@inventory_bp.route('/tech-assets')
@login_required
def view_tech_assets():
    db_session = db_manager.get_session()
    try:
        # Get the current user
        user = db_manager.get_user(session['user_id'])
        
        # Base query for assets
        assets_query = db_session.query(Asset)
        
        # Filter by country if user is Country Admin
        if user.user_type == UserType.COUNTRY_ADMIN and user.assigned_country:
            assets_query = assets_query.filter(Asset.country == user.assigned_country.value)
        
        assets = assets_query.all()
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
        accessories = db_session.query(Accessory).all()
        return render_template('inventory/accessories.html', 
                             accessories=accessories,
                             is_admin=current_user.is_admin,
                             is_country_admin=current_user.is_country_admin)
    finally:
        db_session.close()

@inventory_bp.route('/accessories/<int:id>/add-stock', methods=['GET', 'POST'])
@login_required
def add_accessory_stock(id):
    if not (current_user.is_admin or current_user.is_country_admin):
        flash('You do not have permission to add stock.', 'error')
        return redirect(url_for('inventory.view_accessories'))

    db_session = db_manager.get_session()
    try:
        accessory = db_session.query(Accessory).get(id)
        if not accessory:
            flash('Accessory not found', 'error')
            return redirect(url_for('inventory.view_accessories'))

        if request.method == 'POST':
            try:
                additional_quantity = int(request.form['additional_quantity'])
                if additional_quantity < 1:
                    flash('Additional quantity must be at least 1', 'error')
                    return redirect(url_for('inventory.add_accessory_stock', id=id))

                # Store old values for history tracking
                old_values = {
                    'total_quantity': accessory.total_quantity,
                    'available_quantity': accessory.available_quantity
                }

                # Update quantities
                accessory.total_quantity += additional_quantity
                accessory.available_quantity += additional_quantity

                # Track changes
                changes = {
                    'total_quantity': {
                        'old': old_values['total_quantity'],
                        'new': accessory.total_quantity
                    },
                    'available_quantity': {
                        'old': old_values['available_quantity'],
                        'new': accessory.available_quantity
                    }
                }

                # Create history entry
                history_entry = accessory.track_change(
                    user_id=current_user.id,
                    action='add_stock',
                    changes=changes,
                    notes=request.form.get('notes')
                )
                db_session.add(history_entry)

                # Add activity record
                activity = Activity(
                    user_id=current_user.id,
                    type='accessory_stock_added',
                    content=f'Added {additional_quantity} units to accessory: {accessory.name}',
                    reference_id=accessory.id
                )
                db_session.add(activity)

                db_session.commit()
                flash(f'Successfully added {additional_quantity} units to stock!', 'success')
                return redirect(url_for('inventory.view_accessories'))

            except ValueError:
                flash('Invalid quantity value', 'error')
                return redirect(url_for('inventory.add_accessory_stock', id=id))
            except Exception as e:
                db_session.rollback()
                flash(f'Error adding stock: {str(e)}', 'error')
                return redirect(url_for('inventory.add_accessory_stock', id=id))

        return render_template('inventory/add_accessory_stock.html', accessory=accessory)

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
            # Get the current user
            user = db_manager.get_user(session['user_id'])
            
            # Build query based on filters
            assets_query = db_session.query(Asset)
            
            # Always apply country filter for Country Admin
            if user.user_type == UserType.COUNTRY_ADMIN and user.assigned_country:
                assets_query = assets_query.filter(Asset.country == user.assigned_country.value)

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

            # Only apply country filter if user is not Country Admin
            if data.get('country') and user.user_type != UserType.COUNTRY_ADMIN:
                print(f"Applying country filter: {data['country']}")  # Debug log
                assets_query = assets_query.filter(Asset.country == data['country'])

            # Get results
            try:
                assets = assets_query.all()
                tech_assets_count = len(assets)

                print(f"Filtered Tech Assets Count: {tech_assets_count}")

                response_data = {
                    'total_count': tech_assets_count,
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
        # Get the requested quantity and customer from the form
        try:
            quantity = int(request.form.get('quantity', 1))
            customer_id = int(request.form.get('customer_id'))
            if quantity < 1:
                flash('Quantity must be at least 1', 'error')
                return redirect(url_for('inventory.view_accessory', id=id))
        except ValueError:
            flash('Invalid quantity or customer', 'error')
            return redirect(url_for('inventory.view_accessory', id=id))

        # Get the accessory and customer
        accessory = db_session.query(Accessory).filter(Accessory.id == id).first()
        customer = db_session.query(CustomerUser).filter(CustomerUser.id == customer_id).first()
        
        if not accessory:
            flash('Accessory not found', 'error')
            return redirect(url_for('inventory.view_accessories'))
            
        if not customer:
            flash('Customer not found', 'error')
            return redirect(url_for('inventory.view_accessory', id=id))

        # Check if enough quantity is available
        if accessory.available_quantity < quantity:
            flash(f'Only {accessory.available_quantity} items available', 'error')
            return redirect(url_for('inventory.view_accessory', id=id))

        # Update accessory quantities and assign to customer
        accessory.available_quantity -= quantity
        accessory.checkout_date = datetime.utcnow()
        accessory.customer_id = customer_id
        accessory.customer_user = customer  # Set the relationship
        accessory.status = 'Checked Out'

        db_session.commit()
        flash(f'Successfully checked out {quantity} {accessory.name}(s) to {customer.name}', 'success')
        return redirect(url_for('inventory.view_accessory', id=id))

    except Exception as e:
        db_session.rollback()
        flash(f'Error checking out accessory: {str(e)}', 'error')
        return redirect(url_for('inventory.view_accessory', id=id))
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
def import_inventory():
    if request.method == 'POST':
        db_session = db_manager.get_session()
        try:
            if 'file' in request.files:
                file = request.files['file']
                import_type = request.form.get('import_type', 'tech_assets')
                
                if file and allowed_file(file.filename):
                    # Create unique filename for both the uploaded file and preview data
                    timestamp = int(time.time())
                    filename = f"{timestamp}_{secure_filename(file.filename)}"
                    filepath = os.path.join(os.path.abspath(UPLOAD_FOLDER), filename)
                    preview_filepath = os.path.join(os.path.abspath(UPLOAD_FOLDER), f"{timestamp}_preview.json")
                    
                    file.save(filepath)
                    
                    try:
                        # Helper function to clean values
                        def clean_value(val):
                            if pd.isna(val) or str(val).lower() == 'nan':
                                return None
                            return str(val).strip()

                        # Helper function to clean status
                        def clean_status(val):
                            if pd.isna(val) or str(val).lower() in ['nan', '', 'none']:
                                return 'IN STOCK'  # Default status
                            return str(val).strip()

                        # Define column names based on import type
                        if import_type == 'tech_assets':
                            column_names = [
                                'Index', 'ASSET TYPE', 'Product', 'ASSET TAG', 'Receiving date', 'Keyboard', 
                                'SERIAL NUMBER', 'PO', 'MODEL', 'ERASED', 'CUSTOMER', 'CONDITION', 'DIAG', 
                                'HARDWARE TYPE', 'CPU TYPE', 'CPU CORES', 'GPU CORES', 'MEMORY', 'HARDDRIVE', 
                                'STATUS', 'CHARGER', 'INCLUDED', 'INVENTORY', 'country'
                            ]
                        else:  # accessories
                            column_names = [
                                'NAME', 'CATEGORY', 'MANUFACTURER', 'MODEL NO', 'STATUS',
                                'QUANTITY', 'COUNTRY', 'NOTES'
                            ]

                        # Try different encodings
                        encodings = ['utf-8-sig', 'utf-8', 'latin1', 'iso-8859-1', 'cp1252']
                        df = None
                        last_error = None

                        for encoding in encodings:
                            try:
                                if import_type == 'tech_assets':
                                    df = pd.read_csv(filepath, skiprows=[0], names=column_names, encoding=encoding)
                                    df = df.drop('Index', axis=1)
                                else:
                                    df = pd.read_csv(filepath, skiprows=[0], names=column_names, encoding=encoding)
                                break
                            except Exception as e:
                                last_error = e
                                continue

                        if df is None:
                            raise Exception(f"Failed to read CSV with any encoding. Last error: {str(last_error)}")

                        # Create preview data based on import type
                        preview_data = []
                        if import_type == 'tech_assets':
                            for _, row in df.iterrows():
                                preview_row = {
                                    'Asset Tag': clean_value(row.get('ASSET TAG', '')),
                                    'Serial Number': clean_value(row.get('SERIAL NUMBER', '')),
                                    'Product': clean_value(row.get('Product', '')),
                                    'Model': clean_value(row.get('MODEL', '')),
                                    'Asset Type': clean_value(row.get('ASSET TYPE', '')),
                                    'Hardware Type': clean_value(row.get('HARDWARE TYPE', '')),
                                    'CPU Type': clean_value(row.get('CPU TYPE', '')),
                                    'CPU Cores': clean_value(row.get('CPU CORES', '')),
                                    'GPU Cores': clean_value(row.get('GPU CORES', '')),
                                    'Memory': clean_value(row.get('MEMORY', '')),
                                    'Hard Drive': clean_value(row.get('HARDDRIVE', '')),
                                    'Status': clean_value(row.get('STATUS', '')),
                                    'Customer': clean_value(row.get('CUSTOMER', '')),
                                    'Country': clean_value(row.get('country', '')),
                                    'PO': clean_value(row.get('PO', '')),
                                    'Receiving Date': clean_value(row.get('Receiving date', '')),
                                    'Condition': clean_value(row.get('CONDITION', '')),
                                    'Diagnostic': clean_value(row.get('DIAG', '')),
                                    'Erased': clean_value(row.get('ERASED', row.get('Erased', ''))).strip().upper() in ['YES', 'TRUE'] if row.get('ERASED') or row.get('Erased') else False,
                                    'Keyboard': clean_value(row.get('Keyboard', '')),
                                    'Charger': clean_value(row.get('CHARGER', '')),
                                    'Included': clean_value(row.get('INCLUDED', ''))
                                }
                                preview_data.append(preview_row)
                        else:  # accessories
                            # Read CSV file with headers
                            df = pd.read_csv(filepath, encoding=encoding)
                            
                            # Generate preview data
                            for _, row in df.iterrows():
                                try:
                                    quantity = str(row['TOTAL QUANTITY']).strip()
                                    quantity = int(quantity) if quantity else 0
                                except (ValueError, KeyError):
                                    quantity = 0

                                preview_row = {
                                    'Name': str(row['NAME']).strip(),
                                    'Category': str(row['CATEGORY']).strip(),
                                    'Manufacturer': str(row['MANUFACTURER']).strip(),
                                    'Model Number': str(row['MODEL_NO']).strip(),
                                    'Status': str(row['Status']).strip() if pd.notna(row['Status']) else 'Available',
                                    'Total Quantity': quantity,
                                    'Country': str(row['COUNTRY']).strip(),
                                    'Notes': str(row['NOTES']).strip()
                                }
                                preview_data.append(preview_row)

                        # Store preview data in a temporary file
                        with open(preview_filepath, 'w') as f:
                            json.dump({
                                'import_type': import_type,
                                'data': preview_data
                            }, f)

                        # Store file paths in session
                        session['import_filepath'] = filepath
                        session['preview_filepath'] = preview_filepath
                        session['filename'] = filename
                        session['import_type'] = import_type
                        session['total_rows'] = len(preview_data)

                        return render_template('inventory/import.html',
                                            preview_data=preview_data,
                                            filename=filename,
                                            filepath=filepath,
                                            import_type=import_type,
                                            total_rows=len(preview_data))

                    except Exception as e:
                        db_session.rollback()
                        print(f"Error processing file: {str(e)}")
                        if os.path.exists(filepath):
                            os.remove(filepath)
                        if os.path.exists(preview_filepath):
                            os.remove(preview_filepath)
                        raise e
                else:
                    flash('Invalid file type. Please upload a CSV file.', 'error')
                    return redirect(url_for('inventory.import_inventory'))
        except Exception as e:
            flash(f'Error reading CSV file: {str(e)}', 'error')
            return redirect(url_for('inventory.import_inventory'))
        finally:
            db_session.close()

    return render_template('inventory/import.html')

@inventory_bp.route('/confirm-import', methods=['POST'])
@admin_required
def confirm_import():
    # Helper function to clean values
    def clean_value(val):
        if pd.isna(val) or str(val).lower() == 'nan':
            return None
        return str(val).strip()

    try:
        filepath = request.form.get('filepath') or session.get('import_filepath')
        preview_filepath = session.get('preview_filepath')

        if not filepath or not preview_filepath:
            flash('No file path provided for import', 'error')
            return redirect(url_for('inventory.import_inventory'))

        if not os.path.exists(filepath) or not os.path.exists(preview_filepath):
            flash('Import file not found. Please upload again.', 'error')
            return redirect(url_for('inventory.import_inventory'))

        # Read preview data from file
        try:
            with open(preview_filepath, 'r') as f:
                preview_data = json.load(f)
                import_type = preview_data.get('import_type')  # Get import_type from preview data
                
                if not import_type:
                    flash('Invalid preview data: missing import type', 'error')
                    return redirect(url_for('inventory.import_inventory'))
        except Exception as e:
            flash('Error reading preview data. Please upload again.', 'error')
            return redirect(url_for('inventory.import_inventory'))

        db_session = db_manager.get_session()
        try:
            successful = 0
            failed = 0
            errors = []
            
            for index, row in enumerate(preview_data['data'], 1):
                try:
                    if preview_data['import_type'] == 'tech_assets':
                        # Get and validate serial number
                        serial_num = clean_value(row.get('Serial Number', ''))
                        if not serial_num:
                            error_msg = f"Row {index}: Serial Number is required but was empty"
                            print(error_msg)
                            errors.append(error_msg)
                            failed += 1
                            continue

                        # Check for duplicate serial number
                        serial_num = str(row['Serial Number']).strip() if row['Serial Number'] else None
                        if serial_num:
                            existing_asset = db_session.query(Asset).filter(Asset.serial_num == serial_num).first()
                            if existing_asset:
                                error_msg = f"Row {index}: Serial Number '{serial_num}' already exists in the database (Asset Tag: {existing_asset.asset_tag})"
                                print(error_msg)
                                errors.append(error_msg)
                                failed += 1
                                continue

                        # Default to IN_STOCK if status is empty, nan, or invalid
                        status = AssetStatus.IN_STOCK
                        if row['Status'] and str(row['Status']).lower() not in ['nan', 'none', '']:
                            try:
                                status = AssetStatus[row['Status'].upper().replace(' ', '_')]
                            except KeyError:
                                print(f"Invalid status '{row['Status']}', defaulting to IN_STOCK")

                        # Parse date
                        receiving_date = None
                        if row['Receiving Date'] and str(row['Receiving Date']).lower() not in ['nan', 'none', '']:
                            try:
                                # Try different date formats
                                date_formats = ['%Y-%m-%d', '%m/%d/%Y', '%d-%b-%y']
                                date_str = str(row['Receiving Date']).strip()
                                for date_format in date_formats:
                                    try:
                                        receiving_date = datetime.strptime(date_str, date_format)
                                        break
                                    except ValueError:
                                        continue
                                if not receiving_date:
                                    print(f"Could not parse date '{date_str}' with any known format")
                            except Exception as e:
                                print(f"Error parsing date '{date_str}': {str(e)}")

                        # Process memory and storage as strings
                        memory = None
                        if row['Memory'] and str(row['Memory']).lower() not in ['nan', 'none', '']:
                            memory_str = str(row['Memory']).strip()
                            if not memory_str.endswith('GB'):
                                memory_str += 'GB'
                            memory = memory_str

                        storage = None
                        if row['Hard Drive'] and str(row['Hard Drive']).lower() not in ['nan', 'none', '']:
                            storage_str = str(row['Hard Drive']).strip()
                            if not storage_str.endswith('GB'):
                                storage_str += 'GB'
                            storage = storage_str

                        # Create new asset with proper type conversion and defaults
                        asset = Asset(
                            # Required fields
                            asset_tag=str(row['Asset Tag']).strip() if row['Asset Tag'] else None,
                            serial_num=str(row['Serial Number']).strip() if row['Serial Number'] else None,
                            model=str(row['Model']).strip() if row['Model'] else None,
                            
                            # Asset and hardware type
                            asset_type=str(row['Asset Type']).strip() if row['Asset Type'] else None,
                            hardware_type=str(row['Hardware Type']).strip() if row['Hardware Type'] else None,
                            
                            # Hardware specifications
                            cpu_type=str(row['CPU Type']).strip() if row['CPU Type'] else None,
                            cpu_cores=str(row['CPU Cores']).strip() if row['CPU Cores'] else None,
                            gpu_cores=str(row['GPU Cores']).strip() if row['GPU Cores'] else None,
                            memory=memory,
                            harddrive=storage,
                            
                            # Status and location
                            status=status,
                            customer=str(row['Customer']).strip() if row['Customer'] else None,
                            country=str(row['Country']).strip() if row['Country'] else None,
                            
                            # Purchase and receiving info
                            po=str(row['PO']).strip() if row['PO'] else None,
                            receiving_date=receiving_date,  # Use the parsed datetime object directly
                            
                            # Condition and diagnostics
                            condition=str(row['Condition']).strip() if row['Condition'] else None,
                            diag=str(row['Diagnostic']).strip() if row['Diagnostic'] else None,
                            erased=str(row.get('ERASED', row.get('Erased', ''))).strip().upper() in ['YES', 'TRUE'] if row.get('ERASED') or row.get('Erased') else False,
                            
                            # Accessories
                            keyboard=str(row['Keyboard']).strip() if row['Keyboard'] else None,
                            charger=str(row['Charger']).strip() if row['Charger'] else None,
                            
                            # Set name to just the Product field from CSV
                            name=str(row['Product']).strip() if row['Product'] else None,
                            category="Computer",  # Default category
                            inventory=status.value  # Set inventory status same as status
                        )
                        db_session.add(asset)
                        db_session.flush()  # Flush each row to catch any database errors early
                        successful += 1
                    else:  # accessories
                        try:
                            quantity = int(row.get('Total Quantity', 0))
                        except (ValueError, TypeError):
                            error_msg = f"Row {index}: Invalid quantity value '{row.get('Total Quantity', '')}'"
                            print(error_msg)
                            errors.append(error_msg)
                            failed += 1
                            continue

                        accessory = Accessory(
                            name=str(row['Name']).strip() if row['Name'] else None,
                            category=str(row['Category']).strip() if row['Category'] else None,
                            manufacturer=str(row['Manufacturer']).strip() if row['Manufacturer'] else None,
                            model_no=str(row['Model Number']).strip() if row['Model Number'] else None,
                            total_quantity=quantity,
                            available_quantity=quantity,  # Initially set to total quantity
                            country=str(row['Country']).strip() if row['Country'] else None,
                            status=str(row['Status']).strip() if row['Status'] else 'Available',
                            notes=str(row['Notes']).strip() if row['Notes'] else None
                        )
                        db_session.add(accessory)
                        db_session.flush()  # Flush each row to catch any database errors early
                        successful += 1

                        # Add activity tracking
                        activity = Activity(
                            user_id=current_user.id,
                            type='accessory_created',
                            content=f'Created new accessory: {accessory.name} (Quantity: {accessory.total_quantity})',
                            reference_id=accessory.id
                        )
                        db_session.add(activity)
                        db_session.commit()
                except Exception as e:
                    error_msg = f"Row {index}: {str(e)}"
                    print(error_msg)
                    errors.append(error_msg)
                    failed += 1
                    db_session.rollback()  # Rollback on error for this row
                    continue

            if failed == 0:
                db_session.commit()
                flash(f'Successfully imported {successful} items.', 'success')
            else:
                db_session.rollback()
                error_details = '<br>'.join(errors[:10])
                if len(errors) > 10:
                    error_details += f'<br>... and {len(errors) - 10} more errors'
                flash(f'Failed to import {failed} items. Errors:<br>{error_details}', 'error')
                return redirect(url_for('inventory.import_inventory'))
            
            # Clean up files after successful import or on error
            if os.path.exists(filepath):
                os.remove(filepath)
            if os.path.exists(preview_filepath):
                os.remove(preview_filepath)
            
            # Clear session data
            session.pop('import_filepath', None)
            session.pop('preview_filepath', None)
            session.pop('filename', None)
            session.pop('import_type', None)
            session.pop('total_rows', None)
            
            # Add activity tracking for successful import
            activity = Activity(
                user_id=current_user.id,
                type='data_import',
                content=f'Successfully imported {len(preview_data)} {import_type} via data loader',
                reference_id=0  # No specific reference for bulk import
            )
            db_session.add(activity)
            db_session.commit()
            
            flash('Data imported successfully!', 'success')
            return redirect(url_for('inventory.view_inventory'))

        except Exception as e:
            db_session.rollback()
            flash(f'Error during import: {str(e)}', 'error')
            return redirect(url_for('inventory.import_inventory'))
        finally:
            db_session.close()

    except Exception as e:
        flash(f'Error processing import: {str(e)}', 'error')
        return redirect(url_for('inventory.import_inventory'))

@inventory_bp.route('/asset/<int:asset_id>')
@login_required
def view_asset(asset_id):
    db_session = db_manager.get_session()
    try:
        # Get the current user
        user = db_manager.get_user(session['user_id'])
        
        # Get the asset
        asset = db_session.query(Asset).get(asset_id)
        if not asset:
            flash('Asset not found', 'error')
            return redirect(url_for('inventory.view_inventory'))
        
        # Check if Country Admin has access to this asset
        if user.user_type == UserType.COUNTRY_ADMIN and user.assigned_country:
            if asset.country != user.assigned_country.value:
                flash('You do not have permission to view this asset', 'error')
                return redirect(url_for('inventory.view_inventory'))
        
        # Get all customers for the deployment dropdown
        customers = db_session.query(CustomerUser).order_by(CustomerUser.name).all()
        
        return render_template('inventory/asset_details.html', 
                             asset=asset, 
                             customers=customers,
                             user=user)
    finally:
        db_session.close()

@inventory_bp.route('/assets/<int:asset_id>/update-status', methods=['POST'])
@login_required
def update_asset_status(asset_id):
    db_session = db_manager.get_session()
    try:
        asset = db_session.query(Asset).filter(Asset.id == asset_id).first()
        if not asset:
            abort(404)
            
        new_status = request.form.get('status')
        notes = request.form.get('notes', '')
        
        if not new_status:
            flash('Status is required', 'error')
            return redirect(url_for('inventory.view_asset', asset_id=asset_id))
        
        try:
            # Convert status to the correct format for the enum
            status_map = {
                'IN_STOCK': AssetStatus.IN_STOCK,
                'READY_TO_DEPLOY': AssetStatus.READY_TO_DEPLOY,
                'SHIPPED': AssetStatus.SHIPPED,
                'DEPLOYED': AssetStatus.DEPLOYED,
                'REPAIR': AssetStatus.REPAIR,
                'ARCHIVED': AssetStatus.ARCHIVED
            }
            
            new_status_value = new_status.upper()
            if new_status_value not in status_map:
                flash(f'Invalid status value: {new_status}', 'error')
                return redirect(url_for('inventory.view_asset', asset_id=asset_id))
                
            new_status_enum = status_map[new_status_value]
            
            # Track the change
            changes = {
                'status': {
                    'old': asset.status.value if asset.status else None,
                    'new': new_status_enum.value
                }
            }

            # Handle customer assignment when deploying
            if new_status_enum == AssetStatus.DEPLOYED:
                customer_id = request.form.get('customer_id')
                if customer_id:
                    customer = db_session.query(CustomerUser).get(customer_id)
                    if customer:
                        asset.customer_id = customer.id
                        asset.customer = customer.name
                        asset.customer_user = customer
                        changes['customer'] = {
                            'old': None if not asset.customer else asset.customer,
                            'new': customer.name
                        }
                    else:
                        flash('Selected customer not found', 'error')
                        return redirect(url_for('inventory.view_asset', asset_id=asset_id))
                else:
                    flash('Customer ID is required for deployment', 'error')
                    return redirect(url_for('inventory.view_asset', asset_id=asset_id))
            elif new_status_enum == AssetStatus.IN_STOCK:
                # Clear customer when returning to stock
                if asset.customer_id:
                    changes['customer'] = {
                        'old': asset.customer,
                        'new': None
                    }
                    asset.customer_id = None
                    asset.customer = None
                    asset.customer_user = None
            
            # Create history entry
            history_entry = asset.track_change(
                user_id=session['user_id'],
                action='status_change',
                changes=changes,
                notes=notes
            )
            
            # Update the asset
            asset.status = new_status_enum
            if notes:
                asset.notes = notes
                
            db_session.add(history_entry)
            db_session.commit()
            
            flash('Asset status updated successfully', 'success')
            return redirect(url_for('inventory.view_asset', asset_id=asset_id))
            
        except Exception as e:
            db_session.rollback()
            flash(f'Error updating asset status: {str(e)}', 'error')
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
                country=request.form['country'],  # Add country field
                status='Available',
                notes=request.form.get('notes', '')
            )
            
            db_session.add(new_accessory)
            db_session.commit()
            
            # Add activity tracking
            activity = Activity(
                user_id=current_user.id,
                type='accessory_created',
                content=f'Created new accessory: {new_accessory.name} (Quantity: {new_accessory.total_quantity})',
                reference_id=new_accessory.id
            )
            db_session.add(activity)
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
                # Store old values for history tracking
                old_values = {
                    'name': accessory.name,
                    'category': accessory.category,
                    'manufacturer': accessory.manufacturer,
                    'model_no': accessory.model_no,
                    'total_quantity': accessory.total_quantity,
                    'country': accessory.country,
                    'notes': accessory.notes
                }

                # Update accessory with form data
                accessory.name = request.form['name']
                accessory.category = request.form['category']
                accessory.manufacturer = request.form['manufacturer']
                accessory.model_no = request.form['model_no']
                new_total = int(request.form['total_quantity'])
                accessory.country = request.form['country']
                
                # Update available quantity proportionally
                if accessory.total_quantity > 0:
                    ratio = accessory.available_quantity / accessory.total_quantity
                    accessory.available_quantity = int(new_total * ratio)
                else:
                    accessory.available_quantity = new_total
                
                accessory.total_quantity = new_total
                accessory.notes = request.form.get('notes', '')

                # Track changes
                changes = {}
                new_values = {
                    'name': accessory.name,
                    'category': accessory.category,
                    'manufacturer': accessory.manufacturer,
                    'model_no': accessory.model_no,
                    'total_quantity': accessory.total_quantity,
                    'country': accessory.country,
                    'notes': accessory.notes
                }
                
                for key, old_value in old_values.items():
                    new_value = new_values[key]
                    if old_value != new_value:
                        changes[key] = {'old': old_value, 'new': new_value}

                if changes:  # Only create history entry if there were changes
                    history_entry = accessory.track_change(
                        user_id=current_user.id,
                        action='update',
                        changes=changes
                    )
                    db_session.add(history_entry)
                
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
            # Store accessory info for history
            accessory_info = {
                'name': accessory.name,
                'category': accessory.category,
                'manufacturer': accessory.manufacturer,
                'model_no': accessory.model_no,
                'total_quantity': accessory.total_quantity,
                'country': accessory.country
            }

            # Create activity record
            activity = Activity(
                user_id=current_user.id,
                type='accessory_deleted',
                content=f'Deleted accessory: {accessory.name} (Total Quantity: {accessory.total_quantity})',
                reference_id=0  # Since the accessory will be deleted
            )
            db_session.add(activity)

            # Delete associated history records first
            db_session.query(AccessoryHistory).filter_by(accessory_id=id).delete()

            # Delete the accessory
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
    db_session = db_manager.get_session()
    try:
        # Get the current user
        user = db_manager.get_user(session['user_id'])
        
        # Get all unique models and their exact product names from the database
        model_info = db_session.query(
            Asset.model, 
            Asset.name,
            Asset.asset_type
        ).distinct().filter(
            Asset.model.isnot(None),
            Asset.name.isnot(None)  # Only get models that have a product name
        ).all()
        
        # Get unique values for dropdown fields
        unique_chargers = db_session.query(Asset.charger).distinct().filter(Asset.charger.isnot(None)).all()
        unique_customers = db_session.query(Asset.customer).distinct().filter(Asset.customer.isnot(None)).all()
        unique_conditions = db_session.query(Asset.condition).distinct().filter(Asset.condition.isnot(None)).all()
        unique_diags = db_session.query(Asset.diag).distinct().filter(Asset.diag.isnot(None)).all()
        unique_asset_types = db_session.query(Asset.asset_type).distinct().filter(Asset.asset_type.isnot(None)).all()
        
        # For Country Admin, only show their assigned country
        if user.user_type == UserType.COUNTRY_ADMIN and user.assigned_country:
            unique_countries = [user.assigned_country.value]
        else:
            unique_countries = db_session.query(Asset.country).distinct().filter(Asset.country.isnot(None)).all()
            unique_countries = sorted([c[0] for c in unique_countries if c[0]])
        
        # Process the lists to remove tuples and None values
        unique_models = []
        model_product_map = {}
        model_type_map = {}
        for model, product_name, asset_type in model_info:
            if model and model not in model_product_map:
                unique_models.append(model)
                model_product_map[model] = product_name
                model_type_map[model] = asset_type if asset_type else ''

        # Clean up the unique values
        unique_chargers = sorted([c[0] for c in unique_chargers if c[0]])
        unique_customers = sorted([c[0] for c in unique_customers if c[0]])
        unique_conditions = sorted([c[0] for c in unique_conditions if c[0]])
        unique_diags = sorted([d[0] for d in unique_diags if d[0]])
        unique_asset_types = sorted([t[0] for t in unique_asset_types if t[0]])
        
        if request.method == 'POST':
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

                # Get model directly from the form
                model = request.form.get('model')
                if not model:
                    flash('Model is required', 'error')
                    return render_template('inventory/add_asset.html',
                                        statuses=AssetStatus,
                                        models=unique_models,
                                        model_product_map=model_product_map,
                                        model_type_map=model_type_map,
                                        chargers=unique_chargers,
                                        customers=unique_customers,
                                        countries=unique_countries,
                                        conditions=unique_conditions,
                                        diags=unique_diags,
                                        asset_types=unique_asset_types,
                                        user=user)

                # Create new asset from form data
                new_asset = Asset(
                    asset_tag=request.form.get('asset_tag', ''),
                    name=request.form.get('product', ''),  # Add product as name
                    asset_type=request.form.get('asset_type', ''),  # Add asset type
                    receiving_date=datetime.strptime(request.form.get('receiving_date', ''), '%Y-%m-%d').date() if request.form.get('receiving_date') else None,
                    keyboard=request.form.get('keyboard', ''),
                    serial_num=request.form.get('serial_num', ''),
                    po=request.form.get('po', ''),
                    model=model,
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
                    status=status
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
                
                flash('Asset added successfully!', 'success')
                return redirect(url_for('inventory.view_inventory'))
                
            except Exception as e:
                db_session.rollback()
                flash(f'Error adding asset: {str(e)}', 'error')
                return render_template('inventory/add_asset.html',
                                    statuses=AssetStatus,
                                    models=unique_models,
                                    model_product_map=model_product_map,
                                    model_type_map=model_type_map,
                                    chargers=unique_chargers,
                                    customers=unique_customers,
                                    countries=unique_countries,
                                    conditions=unique_conditions,
                                    diags=unique_diags,
                                    asset_types=unique_asset_types,
                                    user=user)
        
        # GET request - render the form
        return render_template('inventory/add_asset.html',
                            statuses=AssetStatus,
                            models=unique_models,
                            model_product_map=model_product_map,
                            model_type_map=model_type_map,
                            chargers=unique_chargers,
                            customers=unique_customers,
                            countries=unique_countries,
                            conditions=unique_conditions,
                            diags=unique_diags,
                            asset_types=unique_asset_types,
                            user=user)
                            
    except Exception as e:
        flash(f'Error loading form: {str(e)}', 'error')
        return redirect(url_for('inventory.view_inventory'))
    finally:
        db_session.close()

@inventory_bp.route('/download-template/<template_type>')
@login_required
def download_template(template_type):
    try:
        output = io.StringIO()
        writer = csv.writer(output)
        
        if template_type == 'tech_assets':
            # Write headers for tech assets template
            writer.writerow([
                '#', 'Asset Type', 'Product', 'ASSET TAG', 'Receiving date', 'Keyboard',
                'SERIAL NUMBER', 'PO', 'MODEL', 'ERASED', 'CUSTOMER', 'CONDITION', 'DIAG',
                'HARDWARE TYPE', 'CPU TYPE', 'CPU CORES', 'GPU CORES', 'MEMORY', 'HARDDRIVE',
                'STATUS', 'CHARGER', 'INCLUDED', 'INVENTORY', 'country'
            ])
            # Write example row
            writer.writerow([
                '4', 'APPLE', 'MacBook Pro 14 Apple', '4', '25/07/2024', '',
                'SC4QHX9P6PM', '', 'A2442', 'COMPLETED', 'Wise', 'NEW', 'ADP000',
                'MacBook Pro 14 Apple M3 Pro 11-Core CPU 14-Core GPU 36GB RAM 512GB SSD', 'M3 Pro', '11', '14', '36', '512',
                '', 'INCLUDED', '', 'SHIPPED', 'Singapore'
            ])
            filename = 'tech_assets_template.csv'
        else:  # accessories
            # Write headers for accessories template
            writer.writerow([
                'NAME', 'CATEGORY', 'MANUFACTURER', 'MODEL_NO', 'Status',
                'TOTAL QUANTITY', 'COUNTRY', 'NOTES'
            ])
            # Write example row
            writer.writerow([
                'USB-C Charger', 'Power Adapter', 'Apple', 'A1234', 'Available',
                '10', 'USA', 'New stock from Q1 2024'
            ])
            filename = 'accessories_template.csv'
        
        # Prepare the output
        output.seek(0)
        return send_file(
            io.BytesIO(output.getvalue().encode('utf-8')),
            mimetype='text/csv',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        flash(f'Error generating template: {str(e)}', 'error')
        return redirect(url_for('inventory.import_inventory'))

@inventory_bp.route('/asset/<int:asset_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_asset(asset_id):
    db_session = db_manager.get_session()
    try:
        asset = db_session.query(Asset).filter(Asset.id == asset_id).first()
        if not asset:
            flash('Asset not found', 'error')
            return redirect(url_for('inventory.view_inventory'))
        
        # Get all unique values for dropdowns
        models = db_session.query(Asset.model).distinct().filter(Asset.model.isnot(None)).all()
        models = sorted([m[0] for m in models if m[0]])
        
        chargers = db_session.query(Asset.charger).distinct().filter(Asset.charger.isnot(None)).all()
        chargers = sorted([c[0] for c in chargers if c[0]])
        
        customers = db_session.query(Asset.customer).distinct().filter(Asset.customer.isnot(None)).all()
        customers = sorted([c[0] for c in customers if c[0]])
        
        countries = db_session.query(Asset.country).distinct().filter(Asset.country.isnot(None)).all()
        countries = sorted([c[0] for c in countries if c[0]])
        
        asset_types = db_session.query(Asset.asset_type).distinct().filter(Asset.asset_type.isnot(None)).all()
        asset_types = sorted([t[0] for t in asset_types if t[0]])
        
        if request.method == 'POST':
            try:
                print("Received POST request for asset edit")  # Debug log
                
                # Validate required fields
                required_fields = ['asset_tag', 'serial_num', 'model', 'asset_type']
                for field in required_fields:
                    value = request.form.get(field)
                    print(f"Checking required field {field}: {value}")  # Debug log
                    if not value:
                        flash(f'{field.replace("_", " ").title()} is required', 'error')
                        raise ValueError(f'Missing required field: {field}')

                # Store old values for change tracking
                old_values = {
                    'asset_tag': asset.asset_tag,
                    'serial_num': asset.serial_num,
                    'name': asset.name,
                    'model': asset.model,
                    'asset_type': asset.asset_type,
                    'receiving_date': asset.receiving_date,
                    'status': asset.status.value if asset.status else None,
                    'customer': asset.customer,
                    'country': asset.country,
                    'hardware_type': asset.hardware_type,
                    'cpu_type': asset.cpu_type,
                    'cpu_cores': asset.cpu_cores,
                    'gpu_cores': asset.gpu_cores,
                    'memory': asset.memory,
                    'harddrive': asset.harddrive,
                    'po': asset.po,
                    'charger': asset.charger,
                    'erased': asset.erased
                }
                
                print("Old values stored")  # Debug log
                
                # Update asset with new values
                asset.asset_tag = request.form.get('asset_tag')
                asset.serial_num = request.form.get('serial_num')
                asset.name = request.form.get('product')  # form field is 'product'
                asset.model = request.form.get('model')
                asset.asset_type = request.form.get('asset_type')
                
                print("Basic fields updated")  # Debug log
                
                # Handle receiving date
                receiving_date = request.form.get('receiving_date')
                if receiving_date:
                    try:
                        asset.receiving_date = datetime.strptime(receiving_date, '%Y-%m-%d')
                        print(f"Receiving date set to: {asset.receiving_date}")  # Debug log
                    except ValueError as e:
                        print(f"Error parsing receiving date: {str(e)}")  # Debug log
                        flash('Invalid receiving date format. Please use YYYY-MM-DD', 'error')
                        raise
                else:
                    asset.receiving_date = None
                
                # Handle status
                status = request.form.get('status')
                print(f"Status from form: {status}")  # Debug log
                if status:
                    try:
                        status_value = status.upper().replace(' ', '_')
                        print(f"Converted status value: {status_value}")  # Debug log
                        if not hasattr(AssetStatus, status_value):
                            print(f"Invalid status value: {status_value}")  # Debug log
                            flash(f'Invalid status value: {status}', 'error')
                            raise ValueError(f'Invalid status value: {status}')
                        asset.status = AssetStatus[status_value]
                        print(f"Status set to: {asset.status}")  # Debug log
                    except (KeyError, ValueError) as e:
                        print(f"Error setting status: {str(e)}")  # Debug log
                        flash(f'Error setting status: {str(e)}', 'error')
                        raise
                
                # Update remaining fields
                asset.customer = request.form.get('customer')
                asset.country = request.form.get('country')
                asset.hardware_type = request.form.get('hardware_type')
                asset.cpu_type = request.form.get('cpu_type')
                asset.cpu_cores = request.form.get('cpu_cores')
                asset.gpu_cores = request.form.get('gpu_cores')
                asset.memory = request.form.get('memory')
                asset.harddrive = request.form.get('harddrive')
                asset.po = request.form.get('po')
                asset.charger = request.form.get('charger')
                
                # Handle erased field
                erased_value = request.form.get('erased')
                print(f"Received erased value from form: {erased_value}")  # Debug log
                asset.erased = erased_value == 'true'
                print(f"Set asset.erased to: {asset.erased}")  # Debug log
                
                # Track changes
                changes = {}
                for field in old_values:
                    new_value = getattr(asset, field)
                    if isinstance(new_value, AssetStatus):
                        new_value = new_value.value
                    if old_values[field] != new_value:
                        changes[field] = {
                            'old': old_values[field],
                            'new': new_value
                        }
                
                print(f"Changes detected: {changes}")  # Debug log
                
                if changes:
                    history_entry = asset.track_change(
                        user_id=current_user.id,
                        action='update',
                        changes=changes,
                        notes=f"Asset updated by {current_user.username}"
                    )
                    db_session.add(history_entry)
                    print("History entry added")  # Debug log
                
                db_session.commit()
                print("Changes committed to database")  # Debug log
                flash('Asset updated successfully', 'success')
                return redirect(url_for('inventory.view_asset', asset_id=asset.id))
                
            except Exception as e:
                db_session.rollback()
                print(f"Error in edit_asset: {str(e)}")  # Debug log
                flash(f'Error updating asset: {str(e)}', 'error')
                return render_template('inventory/edit_asset.html',
                                     asset=asset,
                                     models=models,
                                     chargers=chargers,
                                     customers=customers,
                                     countries=countries,
                                     asset_types=asset_types,
                                     statuses=AssetStatus)
        
        return render_template('inventory/edit_asset.html',
                             asset=asset,
                             models=models,
                             chargers=chargers,
                             customers=customers,
                             countries=countries,
                             asset_types=asset_types,
                             statuses=AssetStatus)
                             
    except Exception as e:
        db_session.rollback()
        print(f"Error in edit_asset outer block: {str(e)}")  # Debug log
        flash(f'Error updating asset: {str(e)}', 'error')
        return redirect(url_for('inventory.view_asset', asset_id=asset_id))
    finally:
        db_session.close()

@inventory_bp.route('/asset/<int:asset_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_asset(asset_id):
    db_session = db_manager.get_session()
    try:
        asset = db_session.query(Asset).get(asset_id)
        if not asset:
            flash('Asset not found', 'error')
            return redirect(url_for('inventory.view_inventory'))

        try:
            # Store asset info before deletion for activity tracking
            asset_info = {
                'name': asset.name,
                'asset_tag': asset.asset_tag,
                'serial_num': asset.serial_num
            }
            
            # First delete all history records for this asset
            db_session.query(AssetHistory).filter(AssetHistory.asset_id == asset_id).delete()
            
            # Then delete the asset
            db_session.delete(asset)
            
            # Add activity tracking
            activity = Activity(
                user_id=current_user.id,
                type='asset_deleted',
                content=f'Deleted asset: {asset_info["name"]} (Asset Tag: {asset_info["asset_tag"]}, Serial: {asset_info["serial_num"]})',
                reference_id=0  # Since the asset is deleted, we use 0 as reference
            )
            db_session.add(activity)
            
            db_session.commit()
            flash('Asset deleted successfully!', 'success')
        except Exception as e:
            db_session.rollback()
            flash(f'Error deleting asset: {str(e)}', 'error')
            
        return redirect(url_for('inventory.view_inventory'))
        
    finally:
        db_session.close()

@inventory_bp.route('/accessory/<int:id>')
@login_required
def view_accessory(id):
    """View accessory details"""
    db_session = db_manager.get_session()
    try:
        # Get the accessory
        accessory = db_session.query(Accessory).filter(Accessory.id == id).first()
        if not accessory:
            flash('Accessory not found', 'error')
            return redirect(url_for('inventory.view_accessories'))
        
        # Get all customers for the checkout form
        customers = db_session.query(CustomerUser).order_by(CustomerUser.name).all()
        
        # Get current user
        user = db_manager.get_user(session['user_id'])
        if not user:
            flash('User session expired', 'error')
            return redirect(url_for('auth.login'))
            
        # Check if user is admin (either SUPER_ADMIN or COUNTRY_ADMIN)
        is_admin = user.user_type in [UserType.SUPER_ADMIN, UserType.COUNTRY_ADMIN]
        
        return render_template('inventory/accessory_details.html', 
                             accessory=accessory,
                             customers=customers,
                             is_admin=is_admin)
    finally:
        db_session.close()

@inventory_bp.route('/customer-users')
@login_required
def list_customer_users():
    """List all customer users"""
    db_session = db_manager.get_session()
    try:
        customers = db_session.query(CustomerUser)\
            .options(joinedload(CustomerUser.company))\
            .options(joinedload(CustomerUser.assigned_assets))\
            .options(joinedload(CustomerUser.assigned_accessories))\
            .order_by(CustomerUser.name).all()
        
        # Debug print
        for customer in customers:
            print(f"Customer {customer.name}:")
            print(f"Company: {customer.company.name if customer.company else 'N/A'}")
            print(f"Country: {customer.country.value if customer.country else 'N/A'}")
            print(f"Assets: {len(customer.assigned_assets)}")
            print(f"Accessories: {len(customer.assigned_accessories)}")
            
        return render_template('inventory/customer_users.html', 
                             customers=customers, 
                             len=len,
                             Country=Country)  # Pass Country enum to template
    finally:
        db_session.close()

@inventory_bp.route('/customer-users/add', methods=['GET', 'POST'])
@login_required
def add_customer_user():
    """Add a new customer user"""
    db_session = db_manager.get_session()
    try:
        if request.method == 'POST':
            # Get form data
            name = request.form.get('name')
            contact_number = request.form.get('contact_number')
            email = request.form.get('email')
            address = request.form.get('address')
            company_name = request.form.get('company')
            country = Country[request.form.get('country')]

            # Get or create the company
            company = db_session.query(Company).filter_by(name=company_name).first()
            if not company:
                # Create new company if it doesn't exist
                company = Company(name=company_name)
                db_session.add(company)
                db_session.flush()  # Get the company ID

            # Create new customer user
            customer = CustomerUser(
                name=name,
                contact_number=contact_number,
                email=email,
                address=address,
                company=company,  # Assign the Company object
                country=country
            )
            
            db_session.add(customer)
            db_session.commit()
            
            flash('Customer user added successfully!', 'success')
            return redirect(url_for('inventory.list_customer_users'))
        
        # For GET request, get unique company names from assets
        companies = db_session.query(Asset.customer)\
            .filter(Asset.customer.isnot(None))\
            .distinct()\
            .order_by(Asset.customer)\
            .all()
        
        # Convert list of tuples to list of company names
        companies = [company[0] for company in companies if company[0]]  # Filter out None/empty values
        
        return render_template('inventory/add_customer_user.html', 
                             companies=companies,
                             Country=Country)
    finally:
        db_session.close()

@inventory_bp.route('/customer-users/<int:id>')
@login_required
def view_customer_user(id):
    """View customer user details"""
    db_session = db_manager.get_session()
    try:
        customer = db_session.query(CustomerUser).get(id)
        if not customer:
            flash('Customer not found', 'error')
            return redirect(url_for('inventory.list_customer_users'))
        
        return render_template('inventory/view_customer_user.html', customer=customer)
    finally:
        db_session.close()

@inventory_bp.route('/customer-users/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_customer_user(id):
    """Edit a customer user"""
    db_session = db_manager.get_session()
    try:
        customer = db_session.query(CustomerUser).get(id)
        companies = db_session.query(Company).all()
        countries = list(Country)
        
        if not customer:
            flash('Customer user not found', 'error')
            return redirect(url_for('inventory.list_customer_users'))
            
        if request.method == 'POST':
            customer.name = request.form['name']
            customer.contact_number = request.form['contact_number']
            customer.email = request.form['email']
            customer.address = request.form['address']
            customer.company_id = request.form['company_id']
            customer.country = Country(request.form['country'])
            
            db_session.commit()
            flash('Customer user updated successfully', 'success')
            return redirect(url_for('inventory.list_customer_users'))
            
        return render_template('inventory/edit_customer_user.html', 
                             customer=customer,
                             companies=companies,
                             countries=countries)
    finally:
        db_session.close()

@inventory_bp.route('/customer-users/<int:id>/delete', methods=['POST'])
@login_required
def delete_customer_user(id):
    """Delete a customer user"""
    db_session = db_manager.get_session()
    try:
        customer = db_session.query(CustomerUser).get(id)
        if not customer:
            flash('Customer not found', 'error')
            return redirect(url_for('inventory.list_customer_users'))

        try:
            db_session.delete(customer)
            db_session.commit()
            flash('Customer deleted successfully!', 'success')
        except Exception as e:
            db_session.rollback()
            flash(f'Error deleting customer: {str(e)}', 'error')
        
        return redirect(url_for('inventory.list_customer_users'))
    finally:
        db_session.close()

@inventory_bp.route('/asset/<int:asset_id>/history')
@login_required
def view_asset_history(asset_id):
    db_session = db_manager.get_session()
    try:
        # Get the current user
        user = db_manager.get_user(session['user_id'])
        
        # Get the asset with its history
        asset = db_session.query(Asset).get(asset_id)
        if not asset:
            flash('Asset not found', 'error')
            return redirect(url_for('inventory.view_asset', asset_id=asset_id))
        
        # Check if user is super admin
        if not user.is_super_admin:
            flash('You do not have permission to view asset history', 'error')
            return redirect(url_for('inventory.view_asset', asset_id=asset_id))
        
        return render_template('inventory/asset_history.html', 
                             asset=asset,
                             user=user)
    finally:
        db_session.close()

@inventory_bp.route('/search')
@login_required
def search():
    """Search for assets, accessories, and customers"""
    search_term = request.args.get('q', '').strip()
    if not search_term:
        return redirect(url_for('inventory.view_inventory'))

    db_session = db_manager.get_session()
    try:
        user = db_session.query(User).get(session['user_id'])
        
        # Base queries
        asset_query = db_session.query(Asset)
        accessory_query = db_session.query(Accessory)
        customer_query = db_session.query(CustomerUser)

        # Filter by country for country admins
        if user.user_type == UserType.COUNTRY_ADMIN and user.assigned_country:
            asset_query = asset_query.filter(Asset.country == user.assigned_country.value)
            accessory_query = accessory_query.filter(Accessory.country == user.assigned_country.value)
            # Note: Customers don't have a country field, so no filtering needed

        # Search assets
        assets = asset_query.filter(
            or_(
                Asset.name.ilike(f'%{search_term}%'),
                Asset.model.ilike(f'%{search_term}%'),
                Asset.serial_num.ilike(f'%{search_term}%'),
                Asset.asset_tag.ilike(f'%{search_term}%'),
                Asset.category.ilike(f'%{search_term}%'),
                Asset.customer.ilike(f'%{search_term}%'),
                Asset.country.ilike(f'%{search_term}%'),
                Asset.hardware_type.ilike(f'%{search_term}%'),
                Asset.cpu_type.ilike(f'%{search_term}%')
            )
        ).all()

        # Search accessories
        accessories = accessory_query.filter(
            or_(
                Accessory.name.ilike(f'%{search_term}%'),
                Accessory.category.ilike(f'%{search_term}%'),
                Accessory.manufacturer.ilike(f'%{search_term}%'),
                Accessory.model_no.ilike(f'%{search_term}%'),
                Accessory.country.ilike(f'%{search_term}%'),
                Accessory.notes.ilike(f'%{search_term}%')
            )
        ).all()

        # Search customers (only for super admins)
        customers = []
        if user.is_super_admin:
            customers = customer_query.filter(
                or_(
                    CustomerUser.name.ilike(f'%{search_term}%'),
                    CustomerUser.email.ilike(f'%{search_term}%'),
                    CustomerUser.contact_number.ilike(f'%{search_term}%'),
                    CustomerUser.address.ilike(f'%{search_term}%')
                )
            ).all()

        return render_template('inventory/search_results.html',
                             query=search_term,
                             assets=assets,
                             accessories=accessories,
                             customers=customers,
                             user=user)
    finally:
        db_session.close()

@inventory_bp.after_request
def add_csrf_token_to_response(response):
    if 'text/html' in response.headers.get('Content-Type', ''):
        response.set_cookie('csrf_token', generate_csrf())
    return response 