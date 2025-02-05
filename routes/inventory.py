from flask import Blueprint, render_template, request, jsonify, session, flash, redirect, url_for, send_file
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
import json
import time
import io
import csv

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
                                'Index', 'Asset Type', 'Product', 'ASSET TAG', 'Receiving date', 'Keyboard', 
                                'SERIAL NUMBER', 'PO', 'MODEL', 'ERASED', 'CUSTOMER', 'CONDITION', 'DIAG', 
                                'HARDWARE TYPE', 'CPU TYPE', 'CPU CORES', 'GPU CORES', 'MEMORY', 'HARDDRIVE', 
                                'STATUS', 'CHARGER', 'INCLUDED', 'INVENTORY', 'country'
                            ]
                        else:  # accessories
                            column_names = [
                                'NAME', 'CATEGORY', 'MANUFACTURER', 'MODEL NO', 'QUANTITY', 'STATUS', 'NOTES'
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
                                    df = pd.read_csv(filepath, encoding=encoding)
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
                                    'Product': f"MacBook Pro {clean_value(row.get('MODEL', ''))} Apple {clean_value(row.get('CPU TYPE', ''))}",
                                    'Model': clean_value(row.get('MODEL', '')),
                                    'Hardware Type': clean_value(row.get('HARDWARE TYPE', '')),
                                    'CPU Type': clean_value(row.get('CPU TYPE', '')),
                                    'CPU Cores': clean_value(row.get('CPU CORES', '')),
                                    'GPU Cores': clean_value(row.get('GPU CORES', '')),
                                    'Memory': clean_value(row.get('MEMORY', '')),
                                    'Hard Drive': clean_value(row.get('HARDDRIVE', '')),
                                    'Status': clean_status(row.get('STATUS', '')),
                                    'Customer': clean_value(row.get('CUSTOMER', '')),
                                    'Country': clean_value(row.get('country', '')),
                                    'PO': clean_value(row.get('PO', '')),
                                    'Receiving Date': clean_value(row.get('Receiving date', '')),
                                    'Condition': clean_value(row.get('CONDITION', '')),
                                    'Diagnostic': clean_value(row.get('DIAG', '')),
                                    'Erased': clean_value(row.get('ERASED', '')),
                                    'Keyboard': clean_value(row.get('Keyboard', '')),
                                    'Charger': clean_value(row.get('CHARGER', '')),
                                    'Included': clean_value(row.get('INCLUDED', ''))
                                }
                                preview_data.append(preview_row)
                        else:  # accessories
                            for _, row in df.iterrows():
                                preview_row = {
                                    'Name': clean_value(row.get('NAME', '')),
                                    'Category': clean_value(row.get('CATEGORY', '')),
                                    'Manufacturer': clean_value(row.get('MANUFACTURER', '')),
                                    'Model No': clean_value(row.get('MODEL NO', '')),
                                    'Quantity': clean_value(row.get('QUANTITY', '')),
                                    'Status': clean_status(row.get('STATUS', '')),
                                    'Notes': clean_value(row.get('NOTES', ''))
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
                            receiving_date = datetime.strptime(row['Receiving Date'], '%Y-%m-%d').date()
                        except ValueError:
                            print(f"Invalid date format '{row['Receiving Date']}', skipping")

                    # Convert memory and storage to integers if present
                    memory = None
                    if row['Memory'] and str(row['Memory']).lower() not in ['nan', 'none', '']:
                        try:
                            memory = int(str(row['Memory']).replace('GB', '').strip())
                        except ValueError:
                            print(f"Invalid memory value '{row['Memory']}', skipping")

                    storage = None
                    if row['Hard Drive'] and str(row['Hard Drive']).lower() not in ['nan', 'none', '']:
                        try:
                            storage = int(str(row['Hard Drive']).replace('GB', '').strip())
                        except ValueError:
                            print(f"Invalid storage value '{row['Hard Drive']}', skipping")

                    # Create new asset with proper type conversion and defaults
                    asset = Asset(
                        # Required fields
                        asset_tag=str(row['Asset Tag']).strip() if row['Asset Tag'] else None,
                        serial_num=str(row['Serial Number']).strip() if row['Serial Number'] else None,
                        model=str(row['Model']).strip() if row['Model'] else None,
                        
                        # Hardware specifications
                        hardware_type=str(row['Hardware Type']).strip() if row['Hardware Type'] else None,
                        cpu_type=str(row['CPU Type']).strip() if row['CPU Type'] else None,
                        cpu_cores=str(row['CPU Cores']).strip() if row['CPU Cores'] else None,
                        gpu_cores=str(row['GPU Cores']).strip() if row['GPU Cores'] else None,
                        memory=str(row['Memory']).strip() if row['Memory'] else None,
                        harddrive=str(row['Hard Drive']).strip() if row['Hard Drive'] else None,
                        
                        # Status and location
                        status=status,
                        customer=str(row['Customer']).strip() if row['Customer'] else None,
                        country=str(row['Country']).strip() if row['Country'] else None,
                        
                        # Purchase and receiving info
                        po=str(row['PO']).strip() if row['PO'] else None,
                        receiving_date=receiving_date,
                        
                        # Condition and diagnostics
                        condition=str(row['Condition']).strip() if row['Condition'] else None,
                        diag=str(row['Diagnostic']).strip() if row['Diagnostic'] else None,
                        erased=str(row['Erased']).strip() if row['Erased'] else None,
                        
                        # Accessories
                        keyboard=str(row['Keyboard']).strip() if row['Keyboard'] else None,
                        charger=str(row['Charger']).strip() if row['Charger'] else None,
                        
                        # Set default values for required fields
                        name=f"{str(row['Hardware Type']).strip()} {str(row['Model']).strip()}".strip(),
                        category="Computer",  # Default category
                        inventory=status.value  # Set inventory status same as status
                    )
                    db_session.add(asset)
                    successful += 1
                except Exception as e:
                    error_msg = f"Row {index}: {str(e)}"
                    print(error_msg)
                    errors.append(error_msg)
                    failed += 1
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
    db_session = db_manager.get_session()
    try:
        # Get all unique models and their associated products from the database
        model_products = db_session.query(Asset.model, Asset.name).distinct().filter(Asset.model.isnot(None)).all()
        unique_models = []
        model_product_map = {}
        for model, product in model_products:
            if model and model not in model_product_map:
                unique_models.append(model)
                model_product_map[model] = product if product else f"{model}"
        
        if request.method == 'POST':
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
                return redirect(url_for('inventory.add_asset'))

            # Create new asset from form data
            new_asset = Asset(
                asset_tag=request.form.get('asset_tag', ''),
                name=request.form.get('product', ''),  # Add product as name
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
            flash('Asset added successfully!', 'success')
            return redirect(url_for('inventory.view_inventory'))
    except Exception as e:
        db_session.rollback()
        flash(f'Error adding asset: {str(e)}', 'error')
        return redirect(url_for('inventory.add_asset'))
    finally:
        db_session.close()
        
    return render_template('inventory/add_asset.html', 
                         statuses=AssetStatus, 
                         models=unique_models,
                         model_product_map=model_product_map)

@inventory_bp.route('/download-template/<template_type>')
@login_required
def download_template(template_type):
    try:
        output = io.StringIO()
        writer = csv.writer(output)
        
        if template_type == 'tech_assets':
            # Write headers for tech assets template
            writer.writerow([
                'Asset Tag', 'Serial Number', 'Model', 'Hardware Type', 'CPU Type',
                'CPU Cores', 'GPU Cores', 'Memory', 'Hard Drive', 'Status',
                'Customer', 'Country', 'PO', 'Receiving date', 'Condition',
                'Diagnostic', 'Erased', 'Keyboard', 'Charger', 'Included'
            ])
            # Write example row
            writer.writerow([
                'AST001', 'SN123456', 'MacBook Pro', 'Laptop', 'M1',
                '8', '8', '16', '512', 'IN_STOCK',
                'Company Name', 'USA', 'PO123', '2024-01-01', 'New',
                'Passed', 'YES', 'US', 'YES', 'Box, Manual'
            ])
            filename = 'tech_assets_template.csv'
        else:  # accessories
            # Write headers for accessories template
            writer.writerow([
                'NAME', 'CATEGORY', 'MANUFACTURER', 'MODEL NO', 'QUANTITY',
                'STATUS', 'NOTES'
            ])
            # Write example row
            writer.writerow([
                'USB-C Charger', 'Charger', 'Apple', 'A1234', '10',
                'Available', 'New stock'
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

@inventory_bp.after_request
def add_csrf_token_to_response(response):
    if 'text/html' in response.headers.get('Content-Type', ''):
        response.set_cookie('csrf_token', generate_csrf())
    return response 