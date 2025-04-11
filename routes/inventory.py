from flask import Blueprint, render_template, request, jsonify, session, flash, redirect, url_for, send_file, abort, Response, current_app
from datetime import datetime
from utils.auth_decorators import login_required, admin_required
from utils.store_instances import inventory_store, db_manager
from models.asset import Asset, AssetStatus
from models.asset_history import AssetHistory
from models.accessory import Accessory
from models.customer_user import CustomerUser
from models.accessory_history import AccessoryHistory
from models.user import User, UserType, Country
from models.asset_transaction import AssetTransaction
from models.location import Location
from models.company import Company
from models.activity import Activity
from models.accessory_transaction import AccessoryTransaction
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
from sqlalchemy.orm import joinedload
from models.company import Company
from io import StringIO, BytesIO
import logging
import random

inventory_bp = Blueprint('inventory', __name__, url_prefix='/inventory')
db_manager = DatabaseManager()

# Configure upload settings
UPLOAD_FOLDER = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'uploads'))
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
        
        # Debug info
        print(f"DEBUG: User accessing inventory: ID={user.id}, Username={user.username}, Type={user.user_type}, Supervisor={user.user_type == UserType.SUPERVISOR}")
        
        # Base query for tech assets
        tech_assets_query = db_session.query(Asset)
        
        # Filter by country if user is Country Admin or Supervisor
        if (user.user_type == UserType.COUNTRY_ADMIN or user.user_type == UserType.SUPERVISOR) and user.assigned_country:
            tech_assets_query = tech_assets_query.filter(Asset.country == user.assigned_country.value)
        
        # Filter by company if user is a client (can only see their company's assets)
        if user.user_type == UserType.CLIENT and user.company:
            # Filter by company_id and also by customer field matching company name
            tech_assets_query = tech_assets_query.filter(
                or_(
                    Asset.company_id == user.company_id,
                    Asset.customer == user.company.name
                )
            )
            print(f"DEBUG: Filtering assets for client user. Company ID: {user.company_id}, Company Name: {user.company.name}")
        
        # Get counts
        tech_assets_count = tech_assets_query.count()
        accessories_count = db_session.query(func.sum(Accessory.total_quantity)).scalar() or 0

        # Get maintenance assets (assets where ERASED is not COMPLETED)
        maintenance_query = tech_assets_query.filter(
            or_(
                Asset.erased.is_(None),
                Asset.erased == '',
                func.lower(Asset.erased) != 'completed'
            )
        )
        maintenance_assets_count = maintenance_query.count()

        # Get unique values for filters from filtered assets only
        companies = tech_assets_query.with_entities(Asset.customer).distinct().all()
        companies = sorted(list(set([c[0] for c in companies if c[0]])))

        models = tech_assets_query.with_entities(Asset.model).distinct().all()
        models = sorted(list(set([m[0] for m in models if m[0]])))

        # For Country Admin or Supervisor, only show their assigned country
        if (user.user_type == UserType.COUNTRY_ADMIN or user.user_type == UserType.SUPERVISOR) and user.assigned_country:
            countries = [user.assigned_country.value]
        # For Client users, only show countries relevant to their company's assets
        elif user.user_type == UserType.CLIENT and user.company:
            countries = tech_assets_query.with_entities(Asset.country).distinct().all()
            countries = sorted(list(set([c[0] for c in countries if c[0]])))
        else:
            countries = tech_assets_query.with_entities(Asset.country).distinct().all()
            countries = sorted(list(set([c[0] for c in countries if c[0]])))

        # Get accessories with counts
        accessories = db_session.query(
            Accessory.id,
            Accessory.name,
            Accessory.category,
            Accessory.total_quantity,
            Accessory.available_quantity
        ).order_by(Accessory.name).all()

        accessories_list = [
            {
                'id': acc.id,
                'name': acc.name,
                'category': acc.category,
                'total_count': acc.total_quantity,
                'available_count': acc.available_quantity
            }
            for acc in accessories
        ]

        # Get all customers for the checkout form
        customers = db_session.query(CustomerUser).order_by(CustomerUser.name).all()

        # Debug template data
        is_supervisor = user.user_type == UserType.SUPERVISOR
        is_client = user.user_type == UserType.CLIENT
        print(f"DEBUG: Template vars - is_admin={user.is_admin}, is_country_admin={user.is_country_admin}, is_supervisor={is_supervisor}, is_client={is_client}")
        
        return render_template(
            'inventory/view.html',
            tech_assets_count=tech_assets_count,
            accessories_count=accessories_count,
            maintenance_assets_count=maintenance_assets_count,
            companies=companies,
            models=models,
            countries=countries,
            accessories=accessories_list,
            customers=customers,
            user=user,
            is_admin=user.is_admin,
            is_country_admin=user.is_country_admin,
            is_supervisor=is_supervisor,
            is_client=is_client
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
        
        # Filter by country if user is Country Admin or Supervisor
        if (user.user_type == UserType.COUNTRY_ADMIN or user.user_type == UserType.SUPERVISOR) and user.assigned_country:
            assets_query = assets_query.filter(Asset.country == user.assigned_country.value)
        
        # Filter by company if user is a client (can only see their company's assets)
        if user.user_type == UserType.CLIENT and user.company:
            # Filter by company_id and also by customer field matching company name
            assets_query = assets_query.filter(
                or_(
                    Asset.company_id == user.company_id,
                    Asset.customer == user.company.name
                )
            )
            # Log more detailed information for debugging client view
            print(f"DEBUG: Filtering assets for client user. User ID: {user.id}, Company ID: {user.company_id}, Company Name: {user.company.name}")
            
            # Get counts for individual filters to help debug
            company_id_count = db_session.query(Asset).filter(Asset.company_id == user.company_id).count()
            customer_name_count = db_session.query(Asset).filter(Asset.customer == user.company.name).count()
            print(f"DEBUG: Assets count by company_id: {company_id_count}, by customer name: {customer_name_count}")
        
        # Execute query
        assets = assets_query.all()
        
        # Get total count
        total_count = len(assets)
        
        # Log for debugging
        print(f"User type: {user.user_type}, Assets returned: {total_count}")
        
        # Format response
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
                    'harddrive': asset.harddrive,
                    'erased': asset.erased
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
        # Get the current user
        user = db_manager.get_user(session['user_id'])
        
        # Base query for accessories
        accessories_query = db_session.query(Accessory)
        
        # Filter by country if user is Country Admin or Supervisor
        if (user.user_type == UserType.COUNTRY_ADMIN or user.user_type == UserType.SUPERVISOR) and user.assigned_country:
            accessories_query = accessories_query.filter(Accessory.country == user.assigned_country.value)
        
        # Execute query and get accessories
        accessories = accessories_query.all()
        
        # Log for debugging
        print(f"User type: {user.user_type}, Accessories returned: {len(accessories)}")
        
        # Get customers for checkout
        customers = db_session.query(CustomerUser).order_by(CustomerUser.name).all()
        
        # Render the template with appropriate context
        return render_template('inventory/accessories.html', 
                             accessories=accessories,
                             customers=customers,
                             is_admin=user.is_admin,
                             is_country_admin=user.is_country_admin,
                             is_supervisor=user.user_type == UserType.SUPERVISOR,
                             user=user)
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
                    'available_quantity': accessory.available_quantity,
                    'status': accessory.status
                }

                # Update quantities
                accessory.total_quantity += additional_quantity
                accessory.available_quantity += additional_quantity

                # Update status based on available quantity
                if accessory.available_quantity > 0 and accessory.status == 'Out of Stock':
                    accessory.status = 'Available'

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

                if old_values['status'] != accessory.status:
                    changes['status'] = {
                        'old': old_values['status'],
                        'new': accessory.status
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
                return redirect(url_for('inventory.view_accessory', id=id))

            except ValueError:
                flash('Invalid quantity value', 'error')
                return redirect(url_for('inventory.view_accessory', id=id))
            except Exception as e:
                db_session.rollback()
                flash(f'Error adding stock: {str(e)}', 'error')
                return redirect(url_for('inventory.view_accessory', id=id))

        return render_template('inventory/add_accessory_stock.html', accessory=accessory)

    finally:
        db_session.close()

@inventory_bp.route('/filter', methods=['POST'])
@login_required
def filter_inventory():
    db_session = db_manager.get_session()
    try:
        # Get JSON data
        data = request.json or request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'})
        
        # Get the current user
        user = db_manager.get_user(session['user_id'])
        
        # Base query
        query = db_session.query(Asset)
        
        # Country filter for Country Admin or Supervisor
        if (user.user_type == UserType.COUNTRY_ADMIN or user.user_type == UserType.SUPERVISOR) and user.assigned_country:
            query = query.filter(Asset.country == user.assigned_country.value)
        
        # Apply filters from request
        if 'country' in data and data['country']:
            query = query.filter(Asset.country == data['country'])
        
        if 'status' in data and data['status'] or 'inventory_status' in data and data['inventory_status']:
            status_value = data.get('status') or data.get('inventory_status')
            query = query.filter(Asset.status == status_value)
        
        if 'customer' in data and data['customer'] or 'company' in data and data['company']:
            company_value = data.get('customer') or data.get('company')
            query = query.filter(Asset.customer == company_value)
        
        if 'model' in data and data['model']:
            query = query.filter(Asset.model == data['model'])
        
        if 'erased' in data and data['erased']:
            # Use case-insensitive comparison for erased field
            query = query.filter(func.lower(Asset.erased) == func.lower(data['erased']))
        
        if 'search' in data and data['search']:
            search = f"%{data['search']}%"
            query = query.filter(
                or_(
                    Asset.asset_tag.ilike(search),
                    Asset.serial_num.ilike(search),
                    Asset.name.ilike(search),
                    Asset.model.ilike(search),
                    Asset.customer.ilike(search)
                )
            )
        
        # Execute query
        assets = query.all()
        
        # Format response
        return jsonify({
            'total_count': len(assets),
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
                    'harddrive': asset.harddrive,
                    'erased': asset.erased
                }
                for asset in assets
            ]
        })
    except Exception as e:
        return jsonify({'error': str(e)})
    finally:
        db_session.close()

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

        # Store old values for history tracking
        old_values = {
            'available_quantity': accessory.available_quantity,
            'status': accessory.status,
            'customer_id': accessory.customer_id
        }

        # Update accessory quantities and assign to customer
        accessory.available_quantity -= quantity
        
        # Update status based on available quantity
        if accessory.available_quantity == 0:
            accessory.status = 'Out of Stock'
        else:
            accessory.status = 'Available'
            
        accessory.checkout_date = datetime.utcnow()
        accessory.customer_id = customer_id
        accessory.customer_user = customer

        # Create transaction record
        transaction = AccessoryTransaction(
            accessory_id=id,
            customer_id=customer_id,
            transaction_date=datetime.utcnow(),
            transaction_type='Checkout',
            quantity=quantity,
            notes=f"Checked out {quantity} item(s) to {customer.name}"
        )
        db_session.add(transaction)
        
        # Create history record with proper changes format
        changes = {
            'available_quantity': {
                'old': old_values['available_quantity'],
                'new': accessory.available_quantity
            },
            'status': {
                'old': old_values['status'],
                'new': accessory.status
            },
            'customer_id': {
                'old': old_values['customer_id'],
                'new': customer_id
            }
        }
        
        history = AccessoryHistory.create_history(
            accessory_id=accessory.id,
            user_id=current_user.id,
            action='Checkout',
            changes=changes,
            notes=f"Checked out {quantity} item(s) to {customer.name}"
        )
        db_session.add(history)
        
        db_session.commit()
        flash(f'Successfully checked out {quantity} item(s) to {customer.name}', 'success')
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
@login_required
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
                                'Asset Tag', 'Serial Number', 'Product', 'Model', 'Asset Type',
                                'Hardware Type', 'CPU Type', 'CPU Cores', 'GPU Cores', 'Memory',
                                'Hard Drive', 'Status', 'Customer', 'Country', 'PO',
                                'Receiving Date', 'Condition', 'Diagnostic', 'Notes', 'Tech Notes',
                                'Erased', 'Keyboard', 'Charger', 'Included'
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
                                # Read CSV file with the current encoding
                                df = pd.read_csv(filepath, encoding=encoding)
                                
                                # Check if the DataFrame has any data
                                if df.empty:
                                    raise Exception("CSV file is empty")
                                
                                # If successful, break the loop
                                break
                            except Exception as e:
                                last_error = str(e)
                                print(f"Failed to read CSV with encoding {encoding}: {last_error}")
                                continue

                        if df is None:
                            raise Exception(f"Failed to read CSV with any encoding. Please check the file format.")

                        # Create preview data based on import type
                        preview_data = []
                        if import_type == 'tech_assets':
                            # Create a case-insensitive column mapping
                            column_mapping = {col.lower(): col for col in df.columns}
                            
                            for _, row in df.iterrows():
                                preview_row = {
                                    'Asset Type': clean_value(row.get(column_mapping.get('asset type', 'Asset Type'), '')),
                                    'Asset Tag': clean_value(row.get(column_mapping.get('asset tag', 'ASSET TAG'), '')),
                                    'Serial Number': clean_value(row.get(column_mapping.get('serial number', 'SERIAL NUMBER'), '')),
                                    'Product': clean_value(row.get(column_mapping.get('product', 'Product'), '')),
                                    'Model': clean_value(row.get(column_mapping.get('model', 'MODEL'), '')),
                                    'Hardware Type': clean_value(row.get(column_mapping.get('hardware type', 'HARDWARE TYPE'), '')),
                                    'CPU Type': clean_value(row.get(column_mapping.get('cpu type', 'CPU TYPE'), '')),
                                    'CPU Cores': clean_value(row.get(column_mapping.get('cpu cores', 'CPU CORES'), '')),
                                    'GPU Cores': clean_value(row.get(column_mapping.get('gpu cores', 'GPU CORES'), '')),
                                    'Memory': clean_value(row.get(column_mapping.get('memory', 'MEMORY'), '')),
                                    'Hard Drive': clean_value(row.get(column_mapping.get('hard drive', 'HARDDRIVE'), '')),
                                    'Status': clean_value(row.get(column_mapping.get('status', 'STATUS'), 'IN STOCK')),
                                    'Customer': clean_value(row.get(column_mapping.get('customer', 'CUSTOMER'), '')),
                                    'Country': clean_value(row.get(column_mapping.get('country', 'COUNTRY'), '')),
                                    'PO': clean_value(row.get(column_mapping.get('po', 'PO'), '')),
                                    'Receiving Date': clean_value(row.get(column_mapping.get('receiving date', 'RECEIVING DATE'), '')),
                                    'Condition': clean_value(row.get(column_mapping.get('condition', 'CONDITION'), '')),
                                    'Diagnostic': clean_value(row.get(column_mapping.get('diagnostic', 'DIAGNOSTIC'), '')),
                                    'Notes': clean_value(row.get(column_mapping.get('notes', 'NOTES'), '')),
                                    'Tech Notes': clean_value(row.get(column_mapping.get('tech notes', 'TECH NOTES'), '')),
                                    'Erased': clean_value(row.get(column_mapping.get('erased', 'ERASED'), '')),
                                    'Keyboard': clean_value(row.get(column_mapping.get('keyboard', 'KEYBOARD'), '')),
                                    'Charger': clean_value(row.get(column_mapping.get('charger', 'CHARGER'), '')),
                                    'Included': clean_value(row.get(column_mapping.get('included', 'INCLUDED'), ''))
                                }
                                preview_data.append(preview_row)
                        else:  # accessories
                            # Create a case-insensitive column mapping for accessories
                            column_mapping = {col.lower(): col for col in df.columns}
                            
                            for _, row in df.iterrows():
                                try:
                                    quantity = str(row.get(column_mapping.get('total quantity', 'TOTAL QUANTITY'), '')).strip()
                                    quantity = int(quantity) if quantity else 0
                                except (ValueError, KeyError):
                                    quantity = 0

                                preview_row = {
                                    'Name': clean_value(row.get(column_mapping.get('name', 'NAME'), '')),
                                    'Category': clean_value(row.get(column_mapping.get('category', 'CATEGORY'), '')),
                                    'Manufacturer': clean_value(row.get(column_mapping.get('manufacturer', 'MANUFACTURER'), '')),
                                    'Model Number': clean_value(row.get(column_mapping.get('model no', 'MODEL NO'), '')),
                                    'Status': clean_value(row.get(column_mapping.get('status', 'Status'), 'Available')),
                                    'Total Quantity': quantity,
                                    'Country': clean_value(row.get(column_mapping.get('country', 'COUNTRY'), '')),
                                    'Notes': clean_value(row.get(column_mapping.get('notes', 'NOTES'), ''))
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
        if val is None:
            return None
        val = str(val).strip()
        return val if val else None

    def validate_erased(val):
        if not val:
            return 'Not completed'
        return str(val).strip()

    def parse_date(date_str):
        if not date_str:
            return None
        try:
            # Try to parse DD/MM/YYYY format
            from datetime import datetime
            return datetime.strptime(str(date_str).strip(), '%d/%m/%Y')
        except ValueError:
            try:
                # Try to parse YYYY-MM-DD format
                return datetime.strptime(str(date_str).strip(), '%Y-%m-%d')
            except ValueError:
                return None

    db_session = db_manager.get_session()
    try:
        # Get file paths from session
        preview_filepath = session.get('preview_filepath')
        
        if not preview_filepath or not os.path.exists(preview_filepath):
            flash('No preview data found. Please upload a file first.', 'error')
            return redirect(url_for('inventory.import_inventory'))

        # Load preview data from file
        with open(preview_filepath, 'r') as f:
            preview_data = json.load(f)

        if not preview_data:
            flash('No preview data found. Please upload a file first.', 'error')
            return redirect(url_for('inventory.import_inventory'))

        successful = 0
        failed = 0
        errors = []

        # Start a transaction
        if not isinstance(preview_data['data'], list):
            flash('Invalid preview data format. Please upload a file again.', 'error')
            return redirect(url_for('inventory.import_inventory'))
            
        for index, row in enumerate(preview_data['data'], start=1):
            try:
                if preview_data['import_type'] == 'tech_assets':
                    # Check for missing required fields in form data
                    asset_type = request.form.get(f'asset_type_{index}')
                    asset_tag = request.form.get(f'asset_tag_{index}')
                    
                    # Update row data with form inputs if they exist
                    if asset_type:
                        row['Asset Type'] = asset_type
                    if asset_tag:
                        row['Asset Tag'] = asset_tag

                    # Validate required fields
                    if not row.get('Asset Type'):
                        raise ValueError(f"Missing required field: Asset Type")
                    if not row.get('Asset Tag'):
                        raise ValueError(f"Missing required field: Asset Tag")

                    # Get and validate serial number and asset tag
                    serial_num = clean_value(row.get('Serial Number', ''))
                    asset_tag = clean_value(row.get('Asset Tag', ''))
                    erased_value = validate_erased(row.get('Erased', ''))
                    receiving_date = parse_date(row.get('Receiving Date', ''))

                    # Create new asset
                    new_asset = Asset(
                        asset_tag=asset_tag,
                        serial_num=serial_num,
                        name=clean_value(row.get('Product', '')),
                        model=clean_value(row.get('Model', '')),
                        manufacturer=clean_value(row.get('Manufacturer', '')),
                        category=clean_value(row.get('Category', '')),
                        status=AssetStatus.IN_STOCK,
                        hardware_type=clean_value(row.get('Hardware Type', '')),
                        inventory=clean_value(row.get('INVENTORY', '')),
                        customer=clean_value(row.get('Customer', '')),
                        country=clean_value(row.get('Country', '')),
                        asset_type=clean_value(row.get('Asset Type', '')),
                        erased=erased_value,
                        condition=clean_value(row.get('Condition', '')),
                        receiving_date=receiving_date,
                        keyboard=clean_value(row.get('Keyboard', '')),
                        charger=clean_value(row.get('Charger', '')),
                        po=clean_value(row.get('PO', '')),
                        notes=clean_value(row.get('Notes', '')),
                        tech_notes=clean_value(row.get('Tech Notes', '')),
                        diag=clean_value(row.get('Diagnostic', '')),
                        cpu_type=clean_value(row.get('CPU Type', '')),
                        cpu_cores=clean_value(row.get('CPU Cores', '')),
                        gpu_cores=clean_value(row.get('GPU Cores', '')),
                        memory=clean_value(row.get('Memory', '')),
                        harddrive=clean_value(row.get('Hard Drive', ''))
                    )
                    db_session.add(new_asset)
                    db_session.commit()
                    successful += 1
                else:  # accessories
                    # Check for missing required fields in form data
                    name = request.form.get(f'name_{index}')
                    category = request.form.get(f'category_{index}')
                    
                    # Update row data with form inputs if they exist
                    if name:
                        row['Name'] = name
                    if category:
                        row['Category'] = category

                    # Validate required fields
                    if not row.get('Name'):
                        raise ValueError(f"Missing required field: Name")
                    if not row.get('Category'):
                        raise ValueError(f"Missing required field: Category")

                    try:
                        quantity = str(row.get('Total Quantity', '')).strip()
                        quantity = int(quantity) if quantity else 0
                    except (ValueError, KeyError):
                        quantity = 0

                    accessory = Accessory(
                        name=clean_value(row.get('Name', '')),
                        category=clean_value(row.get('Category', '')),
                        manufacturer=clean_value(row.get('Manufacturer', '')),
                        model_no=clean_value(row.get('Model Number', '')),
                        total_quantity=quantity,
                        available_quantity=quantity,  # Initially set to total quantity
                        country=clean_value(row.get('Country', '')),
                        status=clean_value(row.get('Status', 'Available')),
                        notes=clean_value(row.get('Notes', ''))
                    )
                    db_session.add(accessory)
                    db_session.commit()
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
            # Add activity tracking for successful import
            activity = Activity(
                user_id=current_user.id,
                type='data_import',
                content=f'Successfully imported {successful} {preview_data["import_type"]} via data loader',
                reference_id=0  # No specific reference for bulk import
            )
            db_session.add(activity)
            db_session.commit()
            flash(f'Successfully imported {successful} items.', 'success')
        else:
            error_summary = f"Failed to import {failed} items. Please check the following rows:"
            error_details = '<br>'.join(errors[:10])
            if len(errors) > 10:
                error_details += f'<br>... and {len(errors) - 10} more errors'
            flash(f'{error_summary}<br><br>{error_details}', 'error')
            return redirect(url_for('inventory.import_inventory'))
        
        # Clean up files after successful import or on error
        if os.path.exists(preview_filepath):
            os.remove(preview_filepath)
        
        # Clear session data
        session.pop('import_filepath', None)
        session.pop('preview_filepath', None)
        session.pop('filename', None)
        session.pop('import_type', None)
        session.pop('total_rows', None)
        session.pop('preview_data', None)
        
        flash('Data imported successfully!', 'success')
        return redirect(url_for('inventory.import_inventory'))
    except Exception as e:
        db_session.rollback()
        flash(f'Error during import: {str(e)}', 'error')
        return redirect(url_for('inventory.import_inventory'))
    finally:
        db_session.close()

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
    """Update asset status and track changes"""
    db_session = db_manager.get_session()
    try:
        asset = db_session.query(Asset).filter(Asset.id == asset_id).first()
        if not asset:
            abort(404)
            
        data = request.get_json()
        
        if not data:
            # Handle form submission (not JSON)
            data = {
                'status': request.form.get('status'),
                'customer_id': request.form.get('customer_id'),
                'notes': request.form.get('notes')
            }
        
        if 'status' not in data or not data['status']:
            return jsonify({"error": "Status is required"}), 400
        
        # Save original state to track changes
        original_status = asset.status
        original_customer_id = asset.customer_id
        
        # Define the mapping from string to enum
        status_map = {
            "IN_STOCK": AssetStatus.IN_STOCK,
            "READY_TO_DEPLOY": AssetStatus.READY_TO_DEPLOY,
            "SHIPPED": AssetStatus.SHIPPED, 
            "DEPLOYED": AssetStatus.DEPLOYED,
            "REPAIR": AssetStatus.REPAIR,
            "ARCHIVED": AssetStatus.ARCHIVED,
            "DISPOSED": AssetStatus.DISPOSED
        }
        
        # Get the new status from the map
        new_status_value = data['status'].upper()
        new_status = status_map.get(new_status_value)
        if not new_status:
            return jsonify({"error": f"Invalid status: {data['status']}"}), 400
        
        # Update the asset
        asset.status = new_status
        
        # Handle customer assignment if the asset is being deployed
        customer_id = data.get('customer_id')
        if new_status == AssetStatus.DEPLOYED:
            if not customer_id:
                return jsonify({"error": "Customer is required for DEPLOYED status"}), 400
                
            # Make sure customer exists
            customer = db_session.query(CustomerUser).get(customer_id)
            if not customer:
                return jsonify({"error": f"Customer with ID {customer_id} not found"}), 404
                
            asset.customer_id = customer_id
            
            # Create transaction record for checkout
            transaction = AssetTransaction(
                asset_id=asset_id,
                customer_id=customer_id,
                transaction_type='checkout',
                notes=data.get('notes', 'Asset checkout')
            )
            db_session.add(transaction)
        
        # If the asset is being returned to stock and had a customer assigned
        if new_status in [AssetStatus.IN_STOCK, AssetStatus.READY_TO_DEPLOY] and original_customer_id:
            asset.customer_id = None
            
            # Create transaction record for return
            transaction = AssetTransaction(
                asset_id=asset_id,
                customer_id=original_customer_id,
                transaction_type='return',
                notes=data.get('notes', 'Asset return')
            )
            db_session.add(transaction)
        
        # Track changes
        changes = {}
        if original_status != new_status:
            changes['status'] = {
                'from': original_status.value if original_status else None,
                'to': new_status.value
            }
        
        if original_customer_id != asset.customer_id:
            changes['customer_id'] = {
                'from': original_customer_id,
                'to': asset.customer_id
            }
        
        # If changes were made, update the asset
        if changes:
            history_entry = asset.track_change(
                user_id=session.get('user_id'),
                action="UPDATE",
                changes=changes,
                notes=data.get('notes')
            )
            db_session.add(history_entry)
        
        db_session.commit()
        
        if request.is_json:
            return jsonify({
                "success": True,
                "message": f"Asset status updated to {new_status.value}"
            })
        else:
            flash('Asset status updated successfully', 'success')
            return redirect(url_for('inventory.view_asset', asset_id=asset_id))
    except Exception as e:
        db_session.rollback()
        if request.is_json:
            return jsonify({"error": str(e)}), 500
        else:
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
                'STATUS', 'CHARGER', 'INCLUDED', 'INVENTORY', 'country', 'NOTES', 'TECH NOTES'
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
def edit_asset(asset_id):
    # Check if current user has permission to edit assets
    if not (current_user.is_admin or (hasattr(current_user, 'permissions') and getattr(current_user.permissions, 'can_edit_assets', False))):
        flash('You do not have permission to edit assets', 'error')
        return redirect(url_for('inventory.view_asset', asset_id=asset_id))

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
                    'erased': asset.erased,
                    'notes': asset.notes,
                    'tech_notes': asset.tech_notes
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
                asset.notes = request.form.get('notes')
                asset.tech_notes = request.form.get('tech_notes')
                asset.erased = request.form.get('erased')
                
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
        # Check if user is CLIENT type - if so, deny access
        user = db_manager.get_user(session['user_id'])
        if user.user_type == UserType.CLIENT:
            flash('You do not have permission to access this page.', 'error')
            return redirect(url_for('main.dashboard'))
            
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
            company_name = request.form.get('company')  # Get company name instead of ID
            country = Country[request.form.get('country')]

            # Create new customer user
            customer = CustomerUser(
                name=name,
                contact_number=contact_number,
                email=email if email else None,
                address=address,
                country=country
            )

            # Look for existing company by name
            company = db_session.query(Company).filter(Company.name == company_name).first()
            if not company:
                # Create new company if it doesn't exist
                company = Company(name=company_name)
                db_session.add(company)
                db_session.flush()

            customer.company = company
            db_session.add(customer)
            db_session.commit()
            
            flash('Customer user added successfully!', 'success')
            return redirect(url_for('inventory.list_customer_users'))
        
        # For GET request, get unique company names from both assets and companies table
        company_names_from_assets = db_session.query(Asset.customer)\
            .filter(Asset.customer.isnot(None))\
            .distinct()\
            .all()
        company_names_from_companies = db_session.query(Company.name)\
            .distinct()\
            .all()
            
        # Combine and deduplicate company names
        all_companies = set()
        for company in company_names_from_assets:
            if company[0]:  # Check if the company name is not None
                all_companies.add(company[0])
        for company in company_names_from_companies:
            if company[0]:  # Check if the company name is not None
                all_companies.add(company[0])
                
        # Sort the company names
        companies = sorted(list(all_companies))
        
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
        
        # Get accessory quantities from transactions
        accessory_quantities = {}
        
        # Find all transactions for this customer's accessories
        transactions = db_session.query(AccessoryTransaction)\
            .filter(AccessoryTransaction.customer_id == customer.id)\
            .order_by(AccessoryTransaction.transaction_date.desc())\
            .all()
            
        # Calculate net quantity per accessory
        for transaction in transactions:
            accessory_id = transaction.accessory_id
            
            # Initialize if not already in the dictionary
            if accessory_id not in accessory_quantities:
                accessory_quantities[accessory_id] = 0
                
            # Add or subtract quantity based on transaction type
            if transaction.transaction_type.lower() == 'checkout':
                accessory_quantities[accessory_id] += transaction.quantity
            elif transaction.transaction_type.lower() == 'checkin':
                accessory_quantities[accessory_id] -= transaction.quantity
        
        return render_template('inventory/view_customer_user.html', 
                              customer=customer,
                              accessory_quantities=accessory_quantities)
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

@inventory_bp.route('/export/<string:item_type>', methods=['GET', 'POST'])
@login_required
def export_inventory(item_type):
    # Ensure user has permission to export data
    if not (current_user.is_admin or current_user.is_supervisor):
        flash('You do not have permission to export data', 'error')
        return redirect(url_for('inventory.view_inventory'))

    db_session = db_manager.get_session()
    try:
        # Create a string buffer to write CSV data
        si = StringIO()
        writer = csv.writer(si)
        
        if item_type == 'assets':
            # Get assets based on user permissions and selection
            query = db_session.query(Asset)
            
            # Handle selected assets if POST request
            if request.method == 'POST' and request.form.get('selected_ids'):
                try:
                    selected_ids = json.loads(request.form.get('selected_ids'))
                    if selected_ids:
                        query = query.filter(Asset.id.in_(selected_ids))
                except json.JSONDecodeError:
                    flash('Invalid selection data', 'error')
                    return redirect(url_for('inventory.view_inventory'))
            
            # Apply user permission filters
            if not current_user.is_super_admin:
                if current_user.is_country_admin and current_user.assigned_country:
                    query = query.filter(Asset.country == current_user.assigned_country.value)
            
            assets = query.all()
            
            if not assets:
                flash('No assets selected for export', 'error')
                return redirect(url_for('inventory.view_inventory'))
            
            # Write header
            writer.writerow([
                'Asset Type', 'Product', 'ASSET TAG', 'Receiving date', 'Keyboard',
                'SERIAL NUMBER', 'PO', 'MODEL', 'ERASED', 'CUSTOMER', 'CONDITION',
                'DIAG', 'HARDWARE TYPE', 'CPU TYPE', 'CPU CORES', 'GPU CORES',
                'MEMORY', 'HARDDRIVE', 'STATUS', 'CHARGER', 'INCLUDED', 'INVENTORY',
                'country'
            ])
            
            # Write data
            for asset in assets:
                writer.writerow([
                    asset.asset_type or '',
                    asset.name or '',
                    asset.asset_tag or '',
                    asset.receiving_date.strftime('%Y-%m-%d') if asset.receiving_date else '',
                    asset.keyboard or '',
                    asset.serial_num or '',
                    asset.po or '',
                    asset.model or '',
                    asset.erased or '',
                    asset.customer or '',
                    asset.condition or '',
                    asset.diag or '',
                    asset.hardware_type or '',
                    asset.cpu_type or '',
                    asset.cpu_cores or '',
                    asset.gpu_cores or '',
                    asset.memory or '',
                    asset.harddrive or '',
                    asset.status.value if asset.status else '',
                    asset.charger or '',
                    '',  # INCLUDED field (empty for now)
                    asset.inventory or '',
                    asset.country or ''
                ])
        
        elif item_type == 'accessories':
            # Get accessories based on user permissions
            query = db_session.query(Accessory)
            if not current_user.is_super_admin:
                if current_user.is_country_admin and current_user.assigned_country:
                    query = query.filter(Accessory.country == current_user.assigned_country.value)
            accessories = query.all()
            
            # Write header
            writer.writerow([
                'Name', 'Category', 'Manufacturer', 'Model No',
                'Total Quantity', 'Available Quantity', 'Country',
                'Status', 'Notes', 'Created At'
            ])
            
            # Write data
            for accessory in accessories:
                writer.writerow([
                    accessory.name,
                    accessory.category,
                    accessory.manufacturer,
                    accessory.model_no,
                    accessory.total_quantity,
                    accessory.available_quantity,
                    accessory.country,
                    accessory.status,
                    accessory.notes,
                    accessory.created_at.strftime('%Y-%m-%d %H:%M:%S') if accessory.created_at else ''
                ])
        
        # Get the string data and convert to bytes
        output = si.getvalue().encode('utf-8')
        si.close()
        
        # Create a BytesIO object
        bio = BytesIO()
        bio.write(output)
        bio.seek(0)
        
        return send_file(
            bio,
            mimetype='text/csv',
            as_attachment=True,
            download_name=f'inventory_{item_type}_{datetime.utcnow().strftime("%Y%m%d_%H%M%S")}.csv'
        )
    
    finally:
        db_session.close()

@inventory_bp.after_request
def add_csrf_token_to_response(response):
    if 'text/html' in response.headers.get('Content-Type', ''):
        response.set_cookie('csrf_token', generate_csrf())
    return response 

@inventory_bp.route('/bulk-checkout', methods=['POST'])
@login_required
def bulk_checkout():
    """Handle bulk checkout of assets and accessories"""
    db_session = db_manager.get_session()
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400

        customer_id = data.get('customer_id')
        if not customer_id:
            return jsonify({'error': 'Customer ID is required'}), 400

        # Get selected items
        selected_assets = data.get('assets', [])
        selected_accessories = data.get('accessories', [])
        
        if not selected_assets and not selected_accessories:
            return jsonify({'error': 'No items selected for checkout'}), 400

        # Get customer
        customer = db_session.query(CustomerUser).get(customer_id)
        if not customer:
            return jsonify({'error': 'Customer not found'}), 404

        # Start transaction
        db_session.begin_nested()
        
        processed_items = []
        errors = []
        processed_assets = 0
        processed_accessories = 0

        # Process assets
        for asset_id in selected_assets:
            try:
                asset = db_session.query(Asset).get(asset_id)
                if not asset:
                    errors.append(f"Asset {asset_id} not found")
                    continue

                # Check if asset is available based on its status
                if asset.status not in [AssetStatus.IN_STOCK, AssetStatus.READY_TO_DEPLOY]:
                    errors.append(f"Asset {asset.name} is not available for checkout (current status: {asset.status.value})")
                    continue

                # Generate unique transaction number with random component
                random_component = ''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=4))
                transaction_number = f"TRX-{datetime.now().strftime('%Y%m%d%H%M%S')}-{random_component}-{asset_id}"

                # Create transaction
                transaction = AssetTransaction(
                    transaction_number=transaction_number,
                    asset_id=asset_id,
                    customer_id=customer_id,
                    transaction_type='checkout',
                    notes=f"Bulk checkout to {customer.name}"
                )
                db_session.add(transaction)

                # Update asset status
                asset.status = AssetStatus.DEPLOYED
                asset.customer_id = customer_id
                asset.last_checkout_date = datetime.now()

                processed_items.append({
                    'type': 'asset',
                    'id': asset_id,
                    'name': asset.name,
                    'transaction_number': transaction_number
                })
                processed_assets += 1

            except Exception as e:
                errors.append(f"Error processing asset {asset_id}: {str(e)}")
                continue

        # Process accessories
        for accessory_data in selected_accessories:
            try:
                accessory_id = accessory_data.get('id')
                quantity = accessory_data.get('quantity', 1)
                
                accessory = db_session.query(Accessory).get(accessory_id)
                if not accessory:
                    errors.append(f"Accessory {accessory_id} not found")
                    continue

                if accessory.available_quantity < quantity:
                    errors.append(f"Accessory {accessory.name} does not have enough quantity available")
                    continue

                # Generate unique transaction number with random component
                random_component = ''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=4))
                transaction_number = f"TRX-{datetime.now().strftime('%Y%m%d%H%M%S')}-{random_component}-{accessory_id}"

                # Create transaction
                transaction = AccessoryTransaction(
                    transaction_number=transaction_number,
                    accessory_id=accessory_id,
                    customer_id=customer_id,
                    transaction_type='checkout',
                    quantity=quantity,
                    notes=f"Bulk checkout to {customer.name}"
                )
                db_session.add(transaction)

                # Update accessory quantity
                accessory.available_quantity -= quantity
                accessory.total_quantity -= quantity
                
                # Update the customer_id field for the accessory to link it to this customer
                accessory.customer_id = customer_id
                accessory.checkout_date = datetime.now()
                accessory.status = 'Checked Out'

                processed_items.append({
                    'type': 'accessory',
                    'id': accessory_id,
                    'name': accessory.name,
                    'quantity': quantity,
                    'transaction_number': transaction_number
                })
                processed_accessories += 1

            except Exception as e:
                errors.append(f"Error processing accessory {accessory_id}: {str(e)}")
                continue

        # Commit the transaction
        db_session.commit()

        # Create a detailed success message
        message_parts = []
        if processed_assets > 0:
            message_parts.append(f"{processed_assets} asset{'s' if processed_assets != 1 else ''}")
        if processed_accessories > 0:
            message_parts.append(f"{processed_accessories} accessor{'ies' if processed_accessories > 1 else 'y'}")
        
        success_message = f"Successfully checked out {' and '.join(message_parts)}"

        return jsonify({
            'success': True,
            'message': success_message,
            'processed_items': processed_items,
            'errors': errors if errors else None
        })

    except Exception as e:
        db_session.rollback()
        current_app.logger.error(f"Error in bulk_checkout: {str(e)}")
        return jsonify({'error': f"Unexpected error during checkout: {str(e)}"}), 500
    finally:
        db_session.close()

@inventory_bp.route('/bulk-delete', methods=['POST'])
@login_required
@admin_required
def bulk_delete():
    """Delete multiple assets and accessories"""
    if not current_user.is_admin:
        flash('You do not have permission to delete items.', 'error')
        return redirect(url_for('inventory.view_inventory'))

    db_session = db_manager.get_session()
    try:
        # Get selected IDs
        try:
            asset_ids = json.loads(request.form.get('selected_asset_ids', '[]'))
            accessory_ids = json.loads(request.form.get('selected_accessory_ids', '[]'))
        except json.JSONDecodeError:
            flash('Invalid selection data', 'error')
            return redirect(url_for('inventory.view_inventory'))

        if not asset_ids and not accessory_ids:
            flash('No items selected for deletion', 'error')
            return redirect(url_for('inventory.view_inventory'))

        deleted_assets = 0
        deleted_accessories = 0
        errors = []

        # Process assets
        for asset_id in asset_ids:
            try:
                asset = db_session.query(Asset).get(asset_id)
                if asset:
                    # Store asset info for activity log
                    asset_info = {
                        'name': asset.name,
                        'asset_tag': asset.asset_tag,
                        'serial_num': asset.serial_num
                    }
                    
                    # Delete asset history first
                    db_session.query(AssetHistory).filter(AssetHistory.asset_id == asset_id).delete()
                    
                    # Delete the asset
                    db_session.delete(asset)
                    deleted_assets += 1

                    # Add activity log
                    activity = Activity(
                        user_id=current_user.id,
                        type='asset_deleted',
                        content=f'Deleted asset: {asset_info["name"]} (Asset Tag: {asset_info["asset_tag"]}, Serial: {asset_info["serial_num"]})',
                        reference_id=0
                    )
                    db_session.add(activity)
            except Exception as e:
                errors.append(f'Error deleting asset {asset_id}: {str(e)}')

        # Process accessories
        for accessory_id in accessory_ids:
            try:
                accessory = db_session.query(Accessory).get(accessory_id)
                if accessory:
                    # Store accessory info for activity log
                    accessory_info = {
                        'name': accessory.name,
                        'total_quantity': accessory.total_quantity
                    }
                    
                    # Delete accessory history first
                    db_session.query(AccessoryHistory).filter(AccessoryHistory.accessory_id == accessory_id).delete()
                    
                    # Delete the accessory
                    db_session.delete(accessory)
                    deleted_accessories += 1

                    # Add activity log
                    activity = Activity(
                        user_id=current_user.id,
                        type='accessory_deleted',
                        content=f'Deleted accessory: {accessory_info["name"]} (Total Quantity: {accessory_info["total_quantity"]})',
                        reference_id=0
                    )
                    db_session.add(activity)
            except Exception as e:
                errors.append(f'Error deleting accessory {accessory_id}: {str(e)}')

        if errors:
            db_session.rollback()
            error_message = '<br>'.join(errors)
            flash(f'Errors occurred during deletion:<br>{error_message}', 'error')
        else:
            db_session.commit()
            flash(f'Successfully deleted {deleted_assets} assets and {deleted_accessories} accessories.', 'success')

        return redirect(url_for('inventory.view_inventory'))

    except Exception as e:
        db_session.rollback()
        flash(f'Error during bulk deletion: {str(e)}', 'error')
        return redirect(url_for('inventory.view_inventory'))
    finally:
        db_session.close()

@inventory_bp.route('/get-checkout-items', methods=['POST'])
@login_required
def get_checkout_items():
    data = request.get_json()
    asset_ids = data.get('asset_ids', [])
    accessory_ids = data.get('accessory_ids', [])
    
    db_session = db_manager.get_session()
    try:
        assets = db_session.query(Asset).filter(Asset.id.in_(asset_ids)).all()
        accessories = db_session.query(Accessory).filter(Accessory.id.in_(accessory_ids)).all()
        
        response = {
            'assets': [{
                'id': a.id,
                'product': a.name,
                'asset_tag': a.asset_tag,
                'serial_num': a.serial_num,
                'model': a.model
            } for a in assets],
            'accessories': [{
                'id': acc.id,
                'name': acc.name,
                'category': acc.category,
                'available_quantity': acc.available_quantity
            } for acc in accessories]
        }
        return jsonify(response)
    finally:
        db_session.close()

@inventory_bp.route('/remove-serial-prefix', methods=['POST'])
@login_required
@admin_required
def remove_serial_prefix():
    """Remove 'S' prefix from serial numbers of selected assets"""
    db_session = db_manager.get_session()
    try:
        data = request.get_json()
        asset_ids = data.get('asset_ids', [])
        
        if not asset_ids:
            return jsonify({'error': 'No assets selected'}), 400
            
        updated_count = 0
        for asset_id in asset_ids:
            asset = db_session.query(Asset).get(asset_id)
            if asset and asset.serial_num and asset.serial_num.startswith('S'):
                # Store old value for history
                old_serial = asset.serial_num
                # Remove 'S' prefix
                asset.serial_num = asset.serial_num[1:]
                
                # Track change
                changes = {
                    'serial_num': {
                        'old': old_serial,
                        'new': asset.serial_num
                    }
                }
                
                # Create history entry
                history_entry = asset.track_change(
                    user_id=current_user.id,
                    action='update',
                    changes=changes,
                    notes='Removed S prefix from serial number'
                )
                db_session.add(history_entry)
                updated_count += 1
        
        if updated_count > 0:
            # Add activity record
            activity = Activity(
                user_id=current_user.id,
                type='asset_updated',
                content=f'Removed S prefix from {updated_count} asset serial numbers',
                reference_id=0
            )
            db_session.add(activity)
            
        db_session.commit()
        return jsonify({
            'message': f'Successfully updated {updated_count} asset serial numbers',
            'updated_count': updated_count
        })
        
    except Exception as e:
        db_session.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        db_session.close()

@inventory_bp.route('/customer-users/export')
@login_required
def export_customer_users():
    """Export customer users to CSV"""
    db_session = db_manager.get_session()
    try:
        customers = db_session.query(CustomerUser)\
            .options(joinedload(CustomerUser.company))\
            .options(joinedload(CustomerUser.assigned_assets))\
            .options(joinedload(CustomerUser.assigned_accessories))\
            .order_by(CustomerUser.name).all()
        
        # Create a string buffer to write CSV data
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header row
        writer.writerow([
            'Name', 
            'Company', 
            'Country', 
            'Contact Number', 
            'Email', 
            'Address',
            'Number of Assigned Assets',
            'Number of Assigned Accessories',
            'Created At'
        ])
        
        # Write data rows
        for customer in customers:
            writer.writerow([
                customer.name,
                customer.company.name if customer.company else 'N/A',
                customer.country.value if customer.country else 'N/A',
                customer.contact_number,
                customer.email if customer.email else 'N/A',
                customer.address,
                len(customer.assigned_assets),
                len(customer.assigned_accessories),
                customer.created_at.strftime('%Y-%m-%d %H:%M:%S') if customer.created_at else 'N/A'
            ])
        
        # Create the response
        output.seek(0)
        return Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={
                'Content-Disposition': 'attachment; filename=customer_users.csv',
                'Content-Type': 'text/csv'
            }
        )
    finally:
        db_session.close()

@inventory_bp.route('/asset/<int:asset_id>/transactions')
@login_required
def view_asset_transactions(asset_id):
    """View transactions for a specific asset"""
    db_session = db_manager.get_session()
    try:
        asset = db_session.query(Asset).filter(Asset.id == asset_id).first()
        if not asset:
            abort(404)
        # Transactions are already loaded via relationship
        return render_template('inventory/asset_transactions.html', asset=asset)
    finally:
        db_session.close()

@inventory_bp.route('/api/assets/<int:asset_id>/transactions')
@login_required
def get_asset_transactions(asset_id):
    """API endpoint to get transactions for a specific asset"""
    db_session = db_manager.get_session()
    try:
        asset = db_session.query(Asset).filter(Asset.id == asset_id).first()
        if not asset:
            abort(404)
        # Handle case where transactions might be None
        transactions = []
        if asset.transactions:
            transactions = [t.to_dict() for t in asset.transactions]
        return jsonify({"transactions": transactions})
    finally:
        db_session.close()

@inventory_bp.route('/api/transactions')
@login_required
def get_all_transactions():
    """API endpoint to get all asset transactions"""
    db_session = db_manager.get_session()
    try:
        transactions = db_session.query(AssetTransaction).order_by(AssetTransaction.transaction_date.desc()).all()
        # Handle case where transactions might be None
        transaction_data = []
        if transactions:
            transaction_data = [t.to_dict() for t in transactions]
        return jsonify({"transactions": transaction_data})
    finally:
        db_session.close()

@inventory_bp.route('/download-customer-template')
@login_required
def download_customer_template():
    """Download a template CSV file for customer users import"""
    try:
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write headers for customer users template
        writer.writerow([
            'Name', 
            'Company', 
            'Country', 
            'Contact Number', 
            'Email', 
            'Address'
        ])
        
        # Write example row
        writer.writerow([
            'John Doe',
            'Acme Inc.',
            'USA',  # Must match Country enum values
            '+1 555-123-4567',
            'john.doe@example.com',
            '123 Main St, New York, NY 10001'
        ])
        
        # Write a second example row
        writer.writerow([
            'Jane Smith',
            'Tech Solutions',
            'UK',  # Must match Country enum values
            '+44 20 1234 5678',
            'jane.smith@example.com',
            '456 High Street, London, SW1A 1AA'
        ])
        
        # Prepare the output
        output.seek(0)
        return send_file(
            io.BytesIO(output.getvalue().encode('utf-8')),
            mimetype='text/csv',
            as_attachment=True,
            download_name='customer_users_template.csv'
        )
        
    except Exception as e:
        flash(f'Error generating template: {str(e)}', 'error')
        return redirect(url_for('inventory.list_customer_users'))

@inventory_bp.route('/import-customers', methods=['GET', 'POST'])
@login_required
@admin_required
def import_customers():
    """Import customer users from a CSV file"""
    if request.method == 'POST':
        db_session = db_manager.get_session()
        try:
            if 'file' not in request.files:
                flash('No file part', 'error')
                return redirect(request.url)
                
            file = request.files['file']
            
            if file.filename == '':
                flash('No selected file', 'error')
                return redirect(request.url)
                
            if file and allowed_file(file.filename):
                # Create unique filename for the uploaded file
                timestamp = int(time.time())
                filename = f"{timestamp}_{secure_filename(file.filename)}"
                filepath = os.path.join(os.path.abspath(UPLOAD_FOLDER), filename)
                
                file.save(filepath)
                
                # Try different encodings
                encodings = ['utf-8-sig', 'utf-8', 'latin1', 'iso-8859-1', 'cp1252']
                df = None
                last_error = None
                
                for encoding in encodings:
                    try:
                        df = pd.read_csv(filepath, encoding=encoding)
                        break
                    except Exception as e:
                        last_error = str(e)
                
                if df is None:
                    flash(f"Could not read CSV file with any encoding: {last_error}", 'error')
                    return redirect(request.url)
                
                # Validate expected columns
                expected_columns = ['Name', 'Company', 'Country', 'Contact Number', 'Email', 'Address']
                missing_columns = [col for col in expected_columns if col not in df.columns]
                
                if missing_columns:
                    flash(f"Missing required columns: {', '.join(missing_columns)}", 'error')
                    return redirect(request.url)
                
                # Process the data
                success_count = 0
                error_count = 0
                errors = []
                
                for index, row in df.iterrows():
                    try:
                        # Clean and extract values
                        name = str(row['Name']).strip() if not pd.isna(row['Name']) else None
                        company_name = str(row['Company']).strip() if not pd.isna(row['Company']) else None
                        country_str = str(row['Country']).strip() if not pd.isna(row['Country']) else None
                        contact_number = str(row['Contact Number']).strip() if not pd.isna(row['Contact Number']) else None
                        email = str(row['Email']).strip() if not pd.isna(row['Email']) else None
                        address = str(row['Address']).strip() if not pd.isna(row['Address']) else None
                        
                        # Validate required fields
                        if not name or not company_name or not country_str or not contact_number or not address:
                            error_count += 1
                            errors.append(f"Row {index+2}: Missing required fields")
                            continue
                        
                        # Validate country is in enum
                        try:
                            country = Country[country_str]
                        except KeyError:
                            error_count += 1
                            errors.append(f"Row {index+2}: Invalid country '{country_str}'. Must be one of: {', '.join([c.name for c in Country])}")
                            continue
                        
                        # Look for existing company by name
                        company = db_session.query(Company).filter(Company.name == company_name).first()
                        if not company:
                            # Create new company if it doesn't exist
                            company = Company(name=company_name)
                            db_session.add(company)
                            db_session.flush()
                        
                        # Create new customer user
                        customer = CustomerUser(
                            name=name,
                            contact_number=contact_number,
                            email=email if email else None,
                            address=address,
                            country=country
                        )
                        
                        customer.company = company
                        db_session.add(customer)
                        success_count += 1
                        
                    except Exception as e:
                        error_count += 1
                        errors.append(f"Row {index+2}: {str(e)}")
                
                if success_count > 0:
                    db_session.commit()
                    
                # Clean up the file
                try:
                    os.remove(filepath)
                except Exception:
                    pass
                
                # Flash messages
                if success_count > 0:
                    flash(f"Successfully imported {success_count} customer users", 'success')
                if error_count > 0:
                    flash(f"Failed to import {error_count} customer users", 'error')
                    for error in errors[:10]:  # Show only first 10 errors
                        flash(error, 'error')
                    if len(errors) > 10:
                        flash(f"... and {len(errors) - 10} more errors", 'error')
                
                return redirect(url_for('inventory.list_customer_users'))
            else:
                flash('Invalid file type. Please upload a CSV file.', 'error')
                return redirect(request.url)
                
        except Exception as e:
            db_session.rollback()
            flash(f'Error importing customer users: {str(e)}', 'error')
            return redirect(request.url)
        finally:
            db_session.close()
    
    # For GET request, render the import form
    return render_template('inventory/import_customers.html')

@inventory_bp.route('/api/accessories/<int:id>/transactions')
@login_required
def get_accessory_transactions(id):
    current_app.logger.debug(f"Fetching transactions for accessory {id}")
    db_session = db_manager.get_session()
    try:
        # First check if the accessory exists
        accessory = db_session.query(Accessory).get(id)
        if not accessory:
            current_app.logger.error(f"Accessory {id} not found")
            return jsonify({'error': 'Accessory not found'}), 404

        current_app.logger.debug(f"Found accessory: {accessory.name}")
        
        # Get transactions
        transactions = db_session.query(AccessoryTransaction).filter(
            AccessoryTransaction.accessory_id == id
        ).order_by(AccessoryTransaction.transaction_date.desc()).all()
        
        current_app.logger.debug(f"Found {len(transactions)} transactions")
        
        transaction_list = []
        for t in transactions:
            try:
                transaction_data = {
                    'id': t.id,
                    'transaction_number': t.transaction_number,
                    'transaction_date': t.transaction_date.strftime('%Y-%m-%d %H:%M:%S') if t.transaction_date else None,
                    'transaction_type': t.transaction_type,
                    'quantity': t.quantity,
                    'notes': t.notes,
                    'customer': t.customer.name if t.customer else None
                }
                transaction_list.append(transaction_data)
                current_app.logger.debug(f"Processed transaction: {t.transaction_number}")
            except Exception as e:
                current_app.logger.error(f"Error processing transaction {t.id}: {str(e)}")
                continue
        
        current_app.logger.debug(f"Successfully processed {len(transaction_list)} transactions")
        return jsonify(transaction_list)
    except Exception as e:
        current_app.logger.error(f"Error fetching transactions: {str(e)}")
        return jsonify({'error': str(e)}), 500
    finally:
        db_session.close()

@inventory_bp.route('/api/customer-users/<int:id>/transactions')
@login_required
def get_customer_transactions(id):
    """API endpoint to get all transactions for a specific customer"""
    db_session = db_manager.get_session()
    try:
        # First check if the customer exists
        customer = db_session.query(CustomerUser).get(id)
        if not customer:
            return jsonify({'error': 'Customer not found'}), 404
        
        # Get asset transactions
        asset_transactions = db_session.query(AssetTransaction).filter(
            AssetTransaction.customer_id == id
        ).order_by(AssetTransaction.transaction_date.desc()).all()
        
        # Get accessory transactions
        accessory_transactions = db_session.query(AccessoryTransaction).filter(
            AccessoryTransaction.customer_id == id
        ).order_by(AccessoryTransaction.transaction_date.desc()).all()
        
        # Prepare response data
        asset_transaction_list = []
        for t in asset_transactions:
            try:
                transaction_data = {
                    'id': t.id,
                    'transaction_number': t.transaction_number,
                    'transaction_date': t.transaction_date.strftime('%Y-%m-%d %H:%M:%S') if t.transaction_date else None,
                    'transaction_type': t.transaction_type,
                    'notes': t.notes,
                    'asset_tag': t.asset.asset_tag if t.asset else None,
                    'asset_name': t.asset.product if t.asset else None,
                    'type': 'asset'
                }
                asset_transaction_list.append(transaction_data)
            except Exception as e:
                continue
        
        accessory_transaction_list = []
        for t in accessory_transactions:
            try:
                transaction_data = {
                    'id': t.id,
                    'transaction_number': t.transaction_number,
                    'transaction_date': t.transaction_date.strftime('%Y-%m-%d %H:%M:%S') if t.transaction_date else None,
                    'transaction_type': t.transaction_type,
                    'quantity': t.quantity,
                    'notes': t.notes,
                    'accessory_name': t.accessory.name if t.accessory else None,
                    'accessory_category': t.accessory.category if t.accessory else None,
                    'type': 'accessory'
                }
                accessory_transaction_list.append(transaction_data)
            except Exception as e:
                continue
        
        # Combine and sort all transactions by date (newest first)
        all_transactions = asset_transaction_list + accessory_transaction_list
        all_transactions.sort(key=lambda x: x['transaction_date'] if x['transaction_date'] else '', reverse=True)
        
        return jsonify(all_transactions)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        db_session.close()

@inventory_bp.route('/delete-accessory-transaction', methods=['POST'])
@login_required
@admin_required
def delete_accessory_transaction():
    """Delete an accessory transaction and update inventory counts"""
    db_session = db_manager.get_session()
    try:
        data = request.get_json()
        transaction_id = data.get('transaction_id')
        
        if not transaction_id:
            return jsonify({'success': False, 'error': 'Transaction ID is required'}), 400
        
        # Get the transaction
        transaction = db_session.query(AccessoryTransaction).filter_by(transaction_id=transaction_id).first()
        
        if not transaction:
            return jsonify({'success': False, 'error': 'Transaction not found'}), 404
        
        # Get the accessory
        accessory = db_session.query(Accessory).filter_by(id=transaction.accessory_id).first()
        
        if not accessory:
            return jsonify({'success': False, 'error': 'Associated accessory not found'}), 404
        
        # Update accessory quantity if it was a checkout
        if transaction.transaction_type == 'Checkout':
            # Increase available quantity
            accessory.available_quantity += transaction.quantity
            db_session.add(accessory)
            
            # Create activity log
            activity = Activity(
                user_id=current_user.id,
                type='transaction_deleted',
                content=f'Deleted checkout transaction {transaction_id} for {accessory.name} (Quantity: {transaction.quantity})',
                reference_id=transaction.accessory_id
            )
            db_session.add(activity)
        
        # Delete the transaction
        db_session.delete(transaction)
        db_session.commit()
        
        return jsonify({
            'success': True, 
            'message': f'Transaction {transaction_id} deleted successfully',
            'transaction_type': transaction.transaction_type,
            'accessory_name': accessory.name,
            'quantity': transaction.quantity
        })
        
    except Exception as e:
        db_session.rollback()
        print(f"Error deleting transaction: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db_session.close()

@inventory_bp.route('/delete-asset-transaction', methods=['POST'])
@login_required
@admin_required
def delete_asset_transaction():
    """Delete an asset transaction and update asset status if needed"""
    db_session = db_manager.get_session()
    try:
        data = request.get_json()
        transaction_id = data.get('transaction_id')
        
        if not transaction_id:
            return jsonify({'success': False, 'error': 'Transaction ID is required'}), 400
        
        # Get the transaction
        transaction = db_session.query(AssetTransaction).filter_by(transaction_id=transaction_id).first()
        
        if not transaction:
            return jsonify({'success': False, 'error': 'Transaction not found'}), 404
        
        # Get the asset
        asset = db_session.query(Asset).filter_by(id=transaction.asset_id).first()
        
        if not asset:
            return jsonify({'success': False, 'error': 'Associated asset not found'}), 404
        
        # Update asset status if it was a checkout and it's the latest transaction
        if transaction.transaction_type == 'Checkout':
            # Check if this is the latest transaction
            latest_transaction = db_session.query(AssetTransaction)\
                .filter_by(asset_id=transaction.asset_id)\
                .order_by(AssetTransaction.transaction_date.desc())\
                .first()
            
            if latest_transaction and latest_transaction.transaction_id == transaction_id:
                # This is the latest transaction, reset to IN_STOCK or previous status
                asset.status = AssetStatus.IN_STOCK
                asset.customer_id = None
                db_session.add(asset)
            
            # Create activity log
            activity = Activity(
                user_id=current_user.id,
                type='transaction_deleted',
                content=f'Deleted checkout transaction {transaction_id} for {asset.serial_num} ({asset.name})',
                reference_id=transaction.asset_id
            )
            db_session.add(activity)
        
        # Delete the transaction
        db_session.delete(transaction)
        db_session.commit()
        
        return jsonify({
            'success': True, 
            'message': f'Transaction {transaction_id} deleted successfully',
            'transaction_type': transaction.transaction_type,
            'asset_name': asset.name,
            'serial_num': asset.serial_num
        })
        
    except Exception as e:
        db_session.rollback()
        print(f"Error deleting transaction: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db_session.close()

@inventory_bp.route('/maintenance-assets', methods=['GET'])
@login_required
def get_maintenance_assets():
    """API endpoint to get assets that need maintenance (ERASED not COMPLETED)"""
    db_session = db_manager.get_session()
    try:
        # Get filter params (if any)
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 1000, type=int)
        search_term = request.args.get('search', '')
        
        # Get the current user
        user = db_manager.get_user(session['user_id'])
        
        # Base query
        query = db_session.query(Asset).filter(
            or_(
                Asset.erased.is_(None),
                Asset.erased == '',
                func.lower(Asset.erased) != 'completed'
            )
        )
        
        # Filter by country if user is Country Admin or Supervisor
        if (user.user_type == UserType.COUNTRY_ADMIN or user.user_type == UserType.SUPERVISOR) and user.assigned_country:
            query = query.filter(Asset.country == user.assigned_country.value)
        
        # Apply search if provided
        if search_term:
            search_term = f"%{search_term}%"
            query = query.filter(
                or_(
                    Asset.serial_num.ilike(search_term),
                    Asset.asset_tag.ilike(search_term),
                    Asset.product.ilike(search_term),
                    Asset.model.ilike(search_term),
                    Asset.cpu_type.ilike(search_term)
                )
            )
        
        # Get total count
        total_count = query.count()
        
        # Manual pagination (fix for SQLAlchemy versions without paginate)
        offset = (page - 1) * per_page
        items = query.order_by(Asset.id.desc()).offset(offset).limit(per_page).all()
        total_pages = (total_count + per_page - 1) // per_page if total_count > 0 else 1
        
        # Format response
        assets = []
        for asset in items:
            customer_name = None
            if asset.customer_id:
                customer = db_session.query(Customer).filter_by(id=asset.customer_id).first()
                if customer:
                    customer_name = customer.name
                    
            assets.append({
                'id': asset.id,
                'asset_tag': asset.asset_tag,
                'serial_num': asset.serial_num,
                'product': f"{asset.hardware_type} {asset.model}" if asset.hardware_type else asset.model,
                'model': asset.model,
                'cpu_type': asset.cpu_type,
                'cpu_cores': asset.cpu_cores,
                'gpu_cores': asset.gpu_cores,
                'memory': asset.memory,
                'harddrive': asset.harddrive,
                'inventory': asset.status.value if asset.status else 'Unknown',
                'customer': asset.customer or customer_name,
                'customer_id': asset.customer_id,
                'country': asset.country,
                'erased': asset.erased
            })
        
        return jsonify({
            'assets': assets,
            'total_count': total_count,
            'page': page,
            'per_page': per_page,
            'total_pages': total_pages
        })
    
    except Exception as e:
        current_app.logger.error(f"Error retrieving maintenance assets: {str(e)}")
        return jsonify({'error': f"Error retrieving maintenance assets: {str(e)}"}), 500
    finally:
        db_session.close()

@inventory_bp.route('/bulk-update-erased', methods=['POST'])
@login_required
@admin_required
def bulk_update_erased():
    """API endpoint to bulk update the ERASED status of multiple assets"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
            
        asset_ids = data.get('asset_ids', [])
        erased_status = data.get('erased_status')
        
        if not asset_ids:
            return jsonify({'error': 'No asset IDs provided'}), 400
            
        if not erased_status:
            return jsonify({'error': 'No erased status provided'}), 400
        
        # Update assets
        updated_count = 0
        for asset_id in asset_ids:
            asset = db_session.query(Asset).filter_by(id=asset_id).first()
            if asset:
                asset.erased = erased_status
                updated_count += 1
        
        # Commit changes
        db_session.commit()
        
        return jsonify({
            'message': f'Successfully updated {updated_count} asset(s) to {erased_status}',
            'updated_count': updated_count
        })
        
    except Exception as e:
        db_session.rollback()
        app.logger.error(f"Error updating assets: {str(e)}")
        return jsonify({'error': f"Error updating assets: {str(e)}"}), 500

@inventory_bp.route('/update-erase-status', methods=['POST'])
@login_required
def update_erase_status():
    """API endpoint to update the ERASED status of a single asset"""
    db_session = db_manager.get_session()
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
            
        asset_id = data.get('asset_id')
        erased_status = data.get('erased_status')
        
        if not asset_id:
            return jsonify({'error': 'No asset ID provided'}), 400
            
        if not erased_status:
            return jsonify({'error': 'No erased status provided'}), 400
        
        # Update asset
        asset = db_session.query(Asset).filter_by(id=asset_id).first()
        if not asset:
            return jsonify({'error': f'Asset with ID {asset_id} not found'}), 404
            
        # Update the asset
        asset.erased = erased_status
        
        # Track changes in asset history
        history_entry = asset.track_change(
            user_id=session.get('user_id'),
            action="UPDATE",
            changes={'erased': {'from': asset.erased, 'to': erased_status}},
            notes=f"Erase status updated to {erased_status}"
        )
        db_session.add(history_entry)
        
        # Commit changes
        db_session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Successfully updated erase status to {erased_status}',
            'asset_id': asset_id
        })
        
    except Exception as e:
        db_session.rollback()
        app.logger.error(f"Error updating erase status: {str(e)}")
        return jsonify({'error': f"Error updating erase status: {str(e)}"}), 500
    finally:
        db_session.close()