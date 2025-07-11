from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from flask_wtf import CSRFProtect
from datetime import datetime
import json
from models.saved_invoice import SavedInvoice
from database import SessionLocal
import logging

# Set up logging for this module
logger = logging.getLogger(__name__)


documents_bp = Bluelogger.info('documents', __name__, url_prefix='/documents')

@documents_bp.route('/commercial-invoice')
@login_required
def commercial_invoice_form():
    """Display the commercial invoice creation form"""
    from utils.db_manager import DatabaseManager
    from flask import session, redirect, url_for, flash
    
    db_manager = DatabaseManager()
    user = db_manager.get_user(session['user_id'])
    if not user.can_access_documents() or not user.can_create_commercial_invoices():
        flash('You do not have permission to create commercial invoices', 'error')
        return redirect(url_for('main.index'))
    
    return render_template('documents/commercial_invoice_form.html')

@documents_bp.route('/packing-list')
@login_required
def packing_list_form():
    """Display the packing list creation form"""
    from utils.db_manager import DatabaseManager
    from flask import session, redirect, url_for, flash
    
    db_manager = DatabaseManager()
    user = db_manager.get_user(session['user_id'])
    if not user.can_access_documents() or not user.can_create_packing_lists():
        flash('You do not have permission to create packing lists', 'error')
        return redirect(url_for('main.index'))
    
    return render_template('documents/packing_list_form.html')

@documents_bp.route('/generate-commercial-invoice', methods=['POST'])
@login_required
def generate_commercial_invoice():
    """Generate commercial invoice from form data"""
    from utils.db_manager import DatabaseManager
    from flask import session, redirect, url_for, flash
    
    db_manager = DatabaseManager()
    user = db_manager.get_user(session['user_id'])
    if not user.can_access_documents() or not user.can_create_commercial_invoices():
        flash('You do not have permission to create commercial invoices', 'error')
        return redirect(url_for('main.index'))
    
    try:
        logger.info("DEBUG: Starting commercial invoice generation")
        # Get form data
        invoice_data = {
            'invoice_number': request.form.get('invoice_number'),
            'date': request.form.get('date'),
            'shipper_reference': request.form.get('shipper_reference'),
            'consignee_reference': request.form.get('consignee_reference'),
            'end_user_reference': request.form.get('end_user_reference'),
            'payment_terms': request.form.get('payment_terms'),
            'incoterms': request.form.get('incoterms'),
            'incoterms_named_place': request.form.get('incoterms_named_place'),
            'delivery_location': request.form.get('delivery_location'),
            'importer_name': request.form.get('importer_name'),
            'importer_address': request.form.get('importer_address'),
            'importer_phone': request.form.get('importer_phone'),
            'importer_mobile': request.form.get('importer_mobile'),
            'importer_email': request.form.get('importer_email'),
            'end_user': request.form.get('end_user'),
            'country_destination': request.form.get('country_destination'),
            'country_end_use': request.form.get('country_end_use'),
            'items': []
        }
        
        # Process items
        # Get all item indices from the form keys
        logger.info("DEBUG: Processing items from form")
        logger.info("DEBUG: All form keys: {list(request.form.keys())}")
        item_indices = set()
        for key in request.form.keys():
            if key.startswith('item_description_'):
                index = key.replace('item_description_', '')
                try:
                    item_indices.add(int(index))
                except ValueError:
                    continue
        logger.info("DEBUG: Found item indices: {item_indices}")
        
        for i in item_indices:
            logger.info("DEBUG: Processing item {i}")
            item = {
                'product_code': request.form.get(f'item_product_code_{i}'),
                'description': request.form.get(f'item_description_{i}'),
                'country_manufacture': request.form.get(f'item_country_manufacture_{i}'),
                'commodity_code': request.form.get(f'item_commodity_code_{i}'),
                'qty': request.form.get(f'item_qty_{i}'),
                'unit_value': request.form.get(f'item_unit_value_{i}'),
                'total_value': request.form.get(f'item_total_value_{i}')
            }
            logger.info("DEBUG: Item data: {item}")
            if item['description']:  # Only add if description is provided
                invoice_data['items'].append(item)
        
        # Calculate totals
        logger.info("DEBUG: Items for calculation: {invoice_data['items']}")
        try:
            logger.info("DEBUG: Starting subtotal calculation")
            subtotal = sum(float(item['total_value'] or 0) for item in invoice_data['items'] if item.get('total_value'))
            logger.info("DEBUG: Subtotal calculated: {subtotal}")
        except (ValueError, TypeError) as e:
            logger.info("DEBUG: Error in subtotal calculation: {e}")
            subtotal = 0
            
        total = subtotal  # Total equals subtotal since freight is removed
        logger.info("DEBUG: Total calculated: {total}")
        
        invoice_data.update({
            'subtotal': subtotal,
            'total': total,
            'currency': request.form.get('currency', 'USD')
        })
        
        logger.info("DEBUG: About to render template")
        logger.info("DEBUG: Final invoice_data: {invoice_data}")
        try:
            return render_template('documents/commercial_invoice_preview.html', data=invoice_data)
        except Exception as e:
            logger.info("DEBUG: Template rendering error: {str(e)}")
            logger.info("DEBUG: Error type: {type(e)}")
            import traceback
            traceback.print_exc()
            raise e
        
    except Exception as e:
        flash(f'Error generating commercial invoice: {str(e)}', 'error')
        return redirect(url_for('documents.commercial_invoice_form'))

@documents_bp.route('/generate-packing-list', methods=['POST'])
@login_required
def generate_packing_list():
    """Generate packing list from form data"""
    from utils.db_manager import DatabaseManager
    from flask import session, redirect, url_for, flash
    
    db_manager = DatabaseManager()
    user = db_manager.get_user(session['user_id'])
    if not user.can_access_documents() or not user.can_create_packing_lists():
        flash('You do not have permission to create packing lists', 'error')
        return redirect(url_for('main.index'))
    
    try:
        # Get form data
        packing_data = {
            'invoice_number': request.form.get('invoice_number'),
            'date': request.form.get('date'),
            'shipper_reference': request.form.get('shipper_reference'),
            'consignee_reference': request.form.get('consignee_reference'),
            'end_user_reference': request.form.get('end_user_reference'),
            'payment_terms': request.form.get('payment_terms'),
            'incoterms': request.form.get('incoterms'),
            'incoterms_named_place': request.form.get('incoterms_named_place'),
            'end_user_delivery_location': request.form.get('end_user_delivery_location'),
            'packages': [],
            'items': []
        }
        
        # Process packages
        # Get all package indices from the form keys
        package_indices = set()
        for key in request.form.keys():
            if key.startswith('package_number_'):
                index = key.replace('package_number_', '')
                try:
                    package_indices.add(int(index))
                except ValueError:
                    continue
        
        for i in package_indices:
            package = {
                'number': request.form.get(f'package_number_{i}'),
                'weight': request.form.get(f'package_weight_{i}'),
                'dimensions': request.form.get(f'package_dimensions_{i}')
            }
            if package['number']:  # Only add if package number is provided
                packing_data['packages'].append(package)
        
        # Process items
        # Get all item indices from the form keys
        item_indices = set()
        for key in request.form.keys():
            if key.startswith('item_description_'):
                index = key.replace('item_description_', '')
                try:
                    item_indices.add(int(index))
                except ValueError:
                    continue
        
        for i in item_indices:
            item = {
                'package_number': request.form.get(f'item_package_number_{i}'),
                'product_code': request.form.get(f'item_product_code_{i}'),
                'description': request.form.get(f'item_description_{i}'),
                'manufacturer': request.form.get(f'item_manufacturer_{i}'),
                'qty': request.form.get(f'item_qty_{i}'),
                'lithium_battery': request.form.get(f'item_lithium_battery_{i}') == 'on'
            }
            if item['description']:  # Only add if description is provided
                packing_data['items'].append(item)
        
        # Add country info
        packing_data.update({
            'country_destination': request.form.get('country_destination'),
            'country_end_use': request.form.get('country_end_use')
        })
        
        return render_template('documents/packing_list_preview.html', data=packing_data)
        
    except Exception as e:
        flash(f'Error generating packing list: {str(e)}', 'error')
        return redirect(url_for('documents.packing_list_form'))

@documents_bp.route('/save-invoice', methods=['POST'])
@login_required
def save_invoice():
    """Save a commercial invoice to the database"""
    try:
        db = SessionLocal()
        
        # Get JSON data from request
        if request.is_json:
            invoice_data = request.get_json()
        else:
            return jsonify({'success': False, 'error': 'Invalid request format'}), 400
        
        logger.info("DEBUG: Received invoice data: {invoice_data}")
        
        # Parse date
        invoice_date = datetime.strptime(invoice_data['date'], '%Y-%m-%d') if invoice_data.get('date') else datetime.utcnow()
        
        # Calculate totals from items
        items = invoice_data.get('items', [])
        subtotal = sum(float(item.get('total_value', 0) or 0) for item in items)
        total = subtotal  # Total equals subtotal since freight is removed
        
        # Create SavedInvoice object
        saved_invoice = SavedInvoice(
            invoice_number=invoice_data.get('invoice_number'),
            date=invoice_date,
            created_by=current_user.id,
            delivery_location=invoice_data.get('delivery_location'),
            importer_name=invoice_data.get('importer_name'),
            importer_address=invoice_data.get('importer_address'),
            importer_phone=invoice_data.get('importer_phone'),
            importer_mobile=invoice_data.get('importer_mobile'),
            importer_email=invoice_data.get('importer_email'),
            end_user=invoice_data.get('end_user'),
            shipper_reference=invoice_data.get('shipper_reference'),
            consignee_reference=invoice_data.get('consignee_reference'),
            end_user_reference=invoice_data.get('end_user_reference'),
            payment_terms=invoice_data.get('payment_terms'),
            incoterms=invoice_data.get('incoterms'),
            incoterms_named_place=invoice_data.get('incoterms_named_place'),
            country_destination=invoice_data.get('country_destination'),
            country_end_use=invoice_data.get('country_end_use'),
            currency=invoice_data.get('currency', 'USD'),
            subtotal=subtotal,
            freight=0.0,  # Set freight to 0 since it's removed
            total=total,
            items_json=json.dumps(items)
        )
        
        logger.info("DEBUG: About to save invoice: {saved_invoice.invoice_number}")
        
        db.add(saved_invoice)
        db.commit()
        
        logger.info("DEBUG: Invoice saved successfully: {saved_invoice.id}")
        
        return jsonify({
            'success': True, 
            'message': f'Invoice {invoice_data["invoice_number"]} saved successfully!',
            'invoice_id': saved_invoice.id
        })
        
    except Exception as e:
        logger.info("DEBUG: Error saving invoice: {str(e)}")
        import traceback
        traceback.print_exc()
        db.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()

@documents_bp.route('/saved-invoices')
@login_required
def saved_invoices():
    """Display list of saved invoices"""
    try:
        db = SessionLocal()
        
        # Get all saved invoices, ordered by creation date (newest first)
        if current_user.is_super_admin:
            # Super admins can see all invoices
            invoices = db.query(SavedInvoice).order_by(SavedInvoice.created_at.desc()).all()
        else:
            # Regular users can only see their own invoices
            invoices = db.query(SavedInvoice).filter_by(created_by=current_user.id).order_by(SavedInvoice.created_at.desc()).all()
        
        # Add item count to each invoice
        for invoice in invoices:
            try:
                if invoice.items_json:
                    items = json.loads(invoice.items_json)
                    invoice.item_count = len(items)
                else:
                    invoice.item_count = 0
            except (json.JSONDecodeError, TypeError):
                invoice.item_count = 0
        
        return render_template('documents/saved_invoices.html', invoices=invoices)
        
    except Exception as e:
        flash(f'Error loading saved invoices: {str(e)}', 'error')
        return redirect(url_for('documents.dashboard'))
    finally:
        db.close()

@documents_bp.route('/view-invoice/<int:invoice_id>')
@login_required
def view_saved_invoice(invoice_id):
    """View a saved invoice"""
    try:
        db = SessionLocal()
        
        # Get the invoice
        invoice = db.query(SavedInvoice).filter_by(id=invoice_id).first()
        
        if not invoice:
            flash('Invoice not found', 'error')
            return redirect(url_for('documents.saved_invoices'))
        
        # Check permissions
        if not current_user.is_super_admin and invoice.created_by != current_user.id:
            flash('You do not have permission to view this invoice', 'error')
            return redirect(url_for('documents.saved_invoices'))
        
        # Convert to format expected by the preview template
        invoice_data = {
            'invoice_number': invoice.invoice_number,
            'date': invoice.date.strftime('%Y-%m-%d') if invoice.date else '',
            'delivery_location': invoice.delivery_location,
            'importer_name': invoice.importer_name,
            'importer_address': invoice.importer_address,
            'importer_phone': invoice.importer_phone,
            'importer_mobile': invoice.importer_mobile,
            'importer_email': invoice.importer_email,
            'end_user': invoice.end_user,
            'shipper_reference': invoice.shipper_reference,
            'consignee_reference': invoice.consignee_reference,
            'end_user_reference': invoice.end_user_reference,
            'payment_terms': invoice.payment_terms,
            'incoterms': invoice.incoterms,
            'incoterms_named_place': invoice.incoterms_named_place,
            'country_destination': invoice.country_destination,
            'country_end_use': invoice.country_end_use,
            'currency': invoice.currency,
            'subtotal': invoice.subtotal,
            'total': invoice.total,
            'items': json.loads(invoice.items_json) if invoice.items_json else []
        }
        
        return render_template('documents/commercial_invoice_preview.html', data=invoice_data, is_saved=True)
        
    except Exception as e:
        flash(f'Error loading invoice: {str(e)}', 'error')
        return redirect(url_for('documents.saved_invoices'))
    finally:
        db.close()

@documents_bp.route('/dashboard')
@login_required
def dashboard():
    """Display the documents dashboard"""
    from utils.db_manager import DatabaseManager
    from flask import session, redirect, url_for, flash
    
    db_manager = DatabaseManager()
    user = db_manager.get_user(session['user_id'])
    if not user.can_access_documents():
        flash('You do not have permission to access documents', 'error')
        return redirect(url_for('main.index'))
    
    return render_template('documents/dashboard.html') 