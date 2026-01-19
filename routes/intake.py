from flask import Blueprint, render_template, request, flash, redirect, url_for, current_app, send_file, jsonify
from werkzeug.utils import secure_filename
import os
from datetime import datetime
from models.intake_ticket import IntakeTicket, IntakeStatus, IntakeAttachment
from models.asset import Asset, AssetStatus
from models.company import Company
from utils.auth_decorators import login_required
from utils.store_instances import db_manager
from utils.pdf_extractor import extract_assets_from_pdf
from flask_login import current_user
import logging

# Set up logging for this module
logger = logging.getLogger(__name__)


intake_bp = Blueprint('intake', __name__, url_prefix='/intake')

# Configure upload settings
UPLOAD_FOLDER = 'uploads/intake'
ALLOWED_EXTENSIONS = {'pdf', 'jpg', 'jpeg', 'png'}

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@intake_bp.route('/')
@login_required
def list_tickets():
    db_session = db_manager.get_session()
    try:
        tickets = db_session.query(IntakeTicket).order_by(IntakeTicket.created_at.desc()).all()
        return render_template('intake/list_tickets.html', tickets=tickets)
    finally:
        db_session.close()

@intake_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create_ticket():
    if request.method == 'POST':
        db_session = db_manager.get_session()
        try:
            # Create new ticket
            ticket = IntakeTicket(
                title=request.form['title'],
                description=request.form['description'],
                created_by=current_user.id,
                assigned_to=request.form.get('assigned_to')
            )
            db_session.add(ticket)
            db_session.commit()

            # Handle file uploads
            if 'attachments' in request.files:
                files = request.files.getlist('attachments')
                for file in files:
                    if file and allowed_file(file.filename):
                        filename = secure_filename(file.filename)
                        file_path = os.path.join(UPLOAD_FOLDER, f"{ticket.id}_{filename}")
                        file.save(file_path)
                        
                        attachment = IntakeAttachment(
                            ticket_id=ticket.id,
                            filename=filename,
                            file_path=file_path,
                            file_type=file.content_type,
                            uploaded_by=current_user.id
                        )
                        db_session.add(attachment)
                
                db_session.commit()

            flash('Intake ticket created successfully!', 'success')
            return redirect(url_for('intake.view_ticket', ticket_id=ticket.id))
            
        except Exception as e:
            db_session.rollback()
            flash(f'Error creating ticket: {str(e)}', 'error')
        finally:
            db_session.close()

    return render_template('intake/create_ticket.html')

@intake_bp.route('/ticket/<int:ticket_id>')
@login_required
def view_ticket(ticket_id):
    db_session = db_manager.get_session()
    try:
        ticket = db_session.query(IntakeTicket).get(ticket_id)
        if not ticket:
            flash('Ticket not found', 'error')
            return redirect(url_for('intake.list_tickets'))
            
        return render_template('intake/view_ticket.html', ticket=ticket)
    finally:
        db_session.close()

@intake_bp.route('/ticket/<int:ticket_id>/update-status', methods=['POST'])
@login_required
def update_ticket_status(ticket_id):
    db_session = db_manager.get_session()
    try:
        ticket = db_session.query(IntakeTicket).get(ticket_id)
        if not ticket:
            flash('Ticket not found', 'error')
            return redirect(url_for('intake.list_tickets'))

        new_status = request.form.get('status')
        if new_status:
            ticket.status = IntakeStatus[new_status]
            if new_status == 'COMPLETED':
                ticket.completed_at = datetime.utcnow()
            
            db_session.commit()
            flash('Ticket status updated successfully!', 'success')
            
        return redirect(url_for('intake.view_ticket', ticket_id=ticket_id))
    finally:
        db_session.close()

@intake_bp.route('/ticket/<int:ticket_id>/upload', methods=['POST'])
@login_required
def upload_attachment(ticket_id):
    db_session = db_manager.get_session()
    try:
        ticket = db_session.query(IntakeTicket).get(ticket_id)
        if not ticket:
            flash('Ticket not found', 'error')
            return redirect(url_for('intake.list_tickets'))

        if 'attachment' in request.files:
            file = request.files['attachment']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file_path = os.path.join(UPLOAD_FOLDER, f"{ticket.id}_{filename}")
                file.save(file_path)
                
                attachment = IntakeAttachment(
                    ticket_id=ticket.id,
                    filename=filename,
                    file_path=file_path,
                    file_type=file.content_type,
                    uploaded_by=current_user.id
                )
                db_session.add(attachment)
                db_session.commit()
                flash('File uploaded successfully!', 'success')
            else:
                flash('Invalid file type', 'error')
                
        return redirect(url_for('intake.view_ticket', ticket_id=ticket_id))
    finally:
        db_session.close()

@intake_bp.route('/attachment/<int:attachment_id>/download')
@login_required
def download_attachment(attachment_id):
    db_session = db_manager.get_session()
    try:
        attachment = db_session.query(IntakeAttachment).get(attachment_id)
        if not attachment:
            flash('Attachment not found', 'error')
            return redirect(url_for('intake.list_tickets'))
            
        return send_file(
            attachment.file_path,
            as_attachment=True,
            download_name=attachment.filename
        )
    finally:
        db_session.close()

@intake_bp.route('/ticket/<int:ticket_id>/preview-assets', methods=['GET'])
@login_required
def preview_assets(ticket_id):
    """Preview assets extracted from PDF attachments before importing"""
    db_session = db_manager.get_session()
    try:
        ticket = db_session.query(IntakeTicket).get(ticket_id)
        if not ticket:
            flash('Ticket not found', 'error')
            return redirect(url_for('intake.list_tickets'))

        # Get all PDF attachments
        pdf_attachments = [a for a in ticket.attachments if a.filename.lower().endswith('.pdf')]

        if not pdf_attachments:
            flash('No PDF attachments found to process', 'warning')
            return redirect(url_for('intake.view_ticket', ticket_id=ticket_id))

        all_results = []
        total_assets = 0

        for attachment in pdf_attachments:
            try:
                result = extract_assets_from_pdf(attachment.file_path)
                if result:
                    result['attachment_id'] = attachment.id
                    result['filename'] = attachment.filename
                    all_results.append(result)
                    total_assets += len(result.get('assets', []))
                    logger.info(f"Extracted {len(result.get('assets', []))} assets from {attachment.filename}")
                else:
                    all_results.append({
                        'attachment_id': attachment.id,
                        'filename': attachment.filename,
                        'error': 'Failed to extract data from PDF',
                        'assets': []
                    })
            except Exception as e:
                logger.error(f"Error processing {attachment.filename}: {e}")
                all_results.append({
                    'attachment_id': attachment.id,
                    'filename': attachment.filename,
                    'error': str(e),
                    'assets': []
                })

        # Get list of companies for assignment
        companies = db_session.query(Company).order_by(Company.name).all()

        return render_template('intake/preview_assets.html',
                             ticket=ticket,
                             results=all_results,
                             total_assets=total_assets,
                             companies=companies)
    finally:
        db_session.close()


@intake_bp.route('/ticket/<int:ticket_id>/import-assets', methods=['POST'])
@login_required
def import_assets(ticket_id):
    """Import extracted assets into the inventory"""
    db_session = db_manager.get_session()
    try:
        ticket = db_session.query(IntakeTicket).get(ticket_id)
        if not ticket:
            flash('Ticket not found', 'error')
            return redirect(url_for('intake.list_tickets'))

        # Get form data
        company_id = request.form.get('company_id')
        customer_name = request.form.get('customer_name', '')
        country = request.form.get('country', 'Singapore')
        status = request.form.get('status', 'Available')

        # Get selected asset indices from form
        selected_assets = request.form.getlist('selected_assets')

        if not selected_assets:
            flash('No assets selected for import', 'warning')
            return redirect(url_for('intake.preview_assets', ticket_id=ticket_id))

        # Re-extract assets from PDFs to get the data
        pdf_attachments = [a for a in ticket.attachments if a.filename.lower().endswith('.pdf')]

        all_assets = []
        for attachment in pdf_attachments:
            try:
                result = extract_assets_from_pdf(attachment.file_path)
                if result and result.get('assets'):
                    for asset_data in result['assets']:
                        asset_data['po_number'] = result.get('po_number')
                        asset_data['do_number'] = result.get('do_number')
                        asset_data['supplier'] = result.get('supplier')
                        asset_data['customer_from_pdf'] = result.get('customer')
                        all_assets.append(asset_data)
            except Exception as e:
                logger.error(f"Error re-extracting from {attachment.filename}: {e}")

        # Import selected assets
        imported_count = 0
        skipped_count = 0
        errors = []

        for idx_str in selected_assets:
            try:
                idx = int(idx_str)
                if idx < 0 or idx >= len(all_assets):
                    continue

                asset_data = all_assets[idx]

                # Check for duplicate serial number
                existing = db_session.query(Asset).filter(
                    Asset.serial_num == asset_data['serial_num']
                ).first()

                if existing:
                    skipped_count += 1
                    errors.append(f"Serial {asset_data['serial_num']} already exists (Asset #{existing.id})")
                    continue

                # Create new asset
                new_asset = Asset(
                    name=asset_data.get('name', 'Unknown'),
                    model=asset_data.get('model', ''),
                    serial_num=asset_data['serial_num'],
                    manufacturer=asset_data.get('manufacturer', ''),
                    category=asset_data.get('category', 'Laptop'),
                    asset_type=asset_data.get('hardware_type', 'Laptop'),
                    cpu_type=asset_data.get('cpu_type', ''),
                    cpu_cores=asset_data.get('cpu_cores', ''),
                    gpu_cores=asset_data.get('gpu_cores', ''),
                    memory=asset_data.get('memory', ''),
                    harddrive=asset_data.get('harddrive', ''),
                    keyboard=asset_data.get('keyboard', ''),
                    condition=asset_data.get('condition', 'New'),
                    erased='COMPLETED',  # New assets from delivery orders are factory fresh
                    status=AssetStatus(status) if status else AssetStatus.AVAILABLE,
                    country=country,
                    customer=customer_name or asset_data.get('customer_from_pdf', ''),
                    po=asset_data.get('po_number', ''),
                    notes=asset_data.get('notes', ''),
                    company_id=int(company_id) if company_id else None,
                )

                db_session.add(new_asset)
                imported_count += 1

            except Exception as e:
                errors.append(f"Error importing asset {idx_str}: {str(e)}")
                logger.error(f"Error importing asset: {e}")

        db_session.commit()

        # Update ticket status
        if imported_count > 0:
            ticket.status = IntakeStatus.COMPLETED
            ticket.completed_at = datetime.utcnow()
            db_session.commit()

        # Flash results
        if imported_count > 0:
            flash(f'Successfully imported {imported_count} assets!', 'success')
        if skipped_count > 0:
            flash(f'Skipped {skipped_count} duplicate assets', 'warning')
        if errors:
            for error in errors[:5]:  # Show first 5 errors
                flash(error, 'error')
            if len(errors) > 5:
                flash(f'... and {len(errors) - 5} more errors', 'error')

        return redirect(url_for('intake.view_ticket', ticket_id=ticket_id))

    except Exception as e:
        db_session.rollback()
        logger.error(f"Error importing assets: {e}")
        flash(f'Error importing assets: {str(e)}', 'error')
        return redirect(url_for('intake.view_ticket', ticket_id=ticket_id))
    finally:
        db_session.close()


@intake_bp.route('/api/extract-pdf/<int:attachment_id>', methods=['GET'])
@login_required
def api_extract_pdf(attachment_id):
    """API endpoint to extract and return asset data from a single PDF"""
    db_session = db_manager.get_session()
    try:
        attachment = db_session.query(IntakeAttachment).get(attachment_id)
        if not attachment:
            return jsonify({'success': False, 'error': 'Attachment not found'}), 404

        if not attachment.filename.lower().endswith('.pdf'):
            return jsonify({'success': False, 'error': 'Not a PDF file'}), 400

        result = extract_assets_from_pdf(attachment.file_path)
        if result:
            return jsonify({
                'success': True,
                'data': {
                    'po_number': result.get('po_number'),
                    'do_number': result.get('do_number'),
                    'reference': result.get('reference'),
                    'ship_date': result.get('ship_date'),
                    'supplier': result.get('supplier'),
                    'customer': result.get('customer'),
                    'total_quantity': result.get('total_quantity'),
                    'assets': result.get('assets', []),
                }
            })
        else:
            return jsonify({'success': False, 'error': 'Failed to extract data from PDF'}), 400

    except Exception as e:
        logger.error(f"API extract error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db_session.close() 