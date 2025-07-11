import os
import traceback
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, send_file
from utils.auth_decorators import login_required
from models.ticket import Ticket
from models.ticket_attachment import TicketAttachment
from sqlalchemy.orm import joinedload
from utils.store_instances import db_manager
import logging

# Set up logging for this module
logger = logging.getLogger(__name__)


# Create a new blueprint for debug routes
debug_bp = Blueprint('debug', __name__, url_prefix='/debug')

@debug_bp.route('/documents/<int:ticket_id>')
@login_required
def view_documents(ticket_id):
    """Debug view for showing documents tab content directly."""
    try:
        db_session = db_manager.get_session()
        
        # Get ticket with eagerly loaded relationships
        ticket = db_session.query(Ticket).options(
            joinedload(Ticket.attachments)
        ).filter(Ticket.id == ticket_id).first()
        
        if not ticket:
            flash('Ticket not found', 'error')
            return redirect(url_for('tickets.list_tickets'))
            
        # Skip permissions check for debug purposes
        
        # Render the debug template showing just the documents section
        return render_template('debug/documents.html', 
                              ticket=ticket)
                              
    except Exception as e:
        logger.info("Error in debug view_documents: {str(e)}")
        traceback.print_exc()
        flash(f'Error loading ticket data: {str(e)}', 'error')
        return redirect(url_for('tickets.list_tickets'))
    finally:
        db_session.close()

@debug_bp.route('/attachment/<int:ticket_id>/<int:attachment_id>')
@login_required
def get_attachment(ticket_id, attachment_id):
    """Debug view for getting an attachment file."""
    try:
        db_session = db_manager.get_session()
        
        # Get the attachment
        attachment = db_session.query(TicketAttachment).filter_by(
            id=attachment_id, 
            ticket_id=ticket_id
        ).first()
        
        if not attachment:
            flash('Attachment not found', 'error')
            return redirect(url_for('debug.view_documents', ticket_id=ticket_id))
        
        # Skip permissions check for debug purposes
        
        # Get file path
        file_path = attachment.file_path
        
        # Send the file
        return send_file(
            file_path,
            mimetype=attachment.file_type,
            as_attachment=False
        )
        
    except Exception as e:
        logger.info("Error getting attachment: {str(e)}")
        traceback.print_exc()
        flash(f'Error accessing attachment: {str(e)}', 'error')
        return redirect(url_for('debug.view_documents', ticket_id=ticket_id))
    finally:
        db_session.close() 