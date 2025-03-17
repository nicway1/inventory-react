from flask import Blueprint, render_template, request, flash, redirect, url_for, current_app, send_file
from werkzeug.utils import secure_filename
import os
from datetime import datetime
from models.intake_ticket import IntakeTicket, IntakeStatus, IntakeAttachment
from models.asset import Asset
from utils.auth_decorators import login_required
from utils.store_instances import db_manager
from flask_login import current_user

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

@intake_bp.route('/ticket/<int:ticket_id>/import-assets', methods=['POST'])
@login_required
def import_assets(ticket_id):
    db_session = db_manager.get_session()
    try:
        ticket = db_session.query(IntakeTicket).get(ticket_id)
        if not ticket:
            flash('Ticket not found', 'error')
            return redirect(url_for('intake.list_tickets'))

        # Handle asset import logic here
        # This will be implemented based on your specific requirements
        
        flash('Assets imported successfully!', 'success')
        return redirect(url_for('intake.view_ticket', ticket_id=ticket_id))
    finally:
        db_session.close() 