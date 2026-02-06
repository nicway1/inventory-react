"""
API v2 Ticket Attachment Endpoints

This module provides file upload operations for ticket attachments:
- POST /api/v2/tickets/<id>/attachments - Upload attachment to ticket
- DELETE /api/v2/tickets/<id>/attachments/<attachment_id> - Delete attachment
- GET /api/v2/tickets/<id>/attachments - List ticket attachments
- GET /api/v2/tickets/<id>/attachments/<attachment_id>/download - Download attachment

All endpoints require dual authentication (JWT token or API key).
"""

from flask import request, send_file, current_app
from werkzeug.utils import secure_filename
import os
import uuid
import logging
from datetime import datetime

from . import api_v2_bp
from .utils import (
    api_response,
    api_error,
    api_created,
    api_no_content,
    handle_exceptions,
    ErrorCodes,
    dual_auth_required
)
from models.ticket import Ticket
from models.ticket_attachment import TicketAttachment
from models.user import UserType
from utils.db_manager import DatabaseManager

logger = logging.getLogger(__name__)
db_manager = DatabaseManager()

# Allowed file extensions
ALLOWED_EXTENSIONS = {
    'pdf', 'doc', 'docx', 'xls', 'xlsx', 'csv', 'txt',
    'png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp',
    'zip', 'rar', '7z', 'tar', 'gz'
}

# Maximum file size (25 MB)
MAX_FILE_SIZE = 25 * 1024 * 1024

# Upload folder path
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'uploads', 'tickets')


def allowed_file(filename):
    """Check if a file has an allowed extension."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def get_file_size(file):
    """Get the size of an uploaded file."""
    file.seek(0, 2)  # Seek to end
    size = file.tell()
    file.seek(0)  # Seek back to start
    return size


def format_attachment(attachment):
    """
    Format a TicketAttachment model instance to a dictionary for API response.

    Args:
        attachment: TicketAttachment model instance

    Returns:
        Dictionary representation of the attachment
    """
    return {
        'id': attachment.id,
        'ticket_id': attachment.ticket_id,
        'filename': attachment.filename,
        'file_type': attachment.file_type,
        'file_size': attachment.file_size,
        'uploaded_by': attachment.uploaded_by,
        'uploader_name': attachment.uploader.username if attachment.uploader else None,
        'created_at': attachment.created_at.isoformat() + 'Z' if attachment.created_at else None,
        'download_url': f'/api/v2/tickets/{attachment.ticket_id}/attachments/{attachment.id}/download'
    }


def can_access_ticket(db_session, user, ticket):
    """
    Check if user has permission to access a ticket.

    Args:
        db_session: Database session
        user: Current user object
        ticket: Ticket object

    Returns:
        Boolean indicating if user can access the ticket
    """
    # SUPER_ADMIN and DEVELOPER can access all tickets
    if user.user_type in [UserType.SUPER_ADMIN, UserType.DEVELOPER]:
        return True

    # User can access their own tickets
    if ticket.created_by == user.id:
        return True

    # User can access tickets assigned to them
    if ticket.assigned_to_id == user.id:
        return True

    # Check queue permissions for staff
    if user.user_type in [UserType.COUNTRY_ADMIN, UserType.SUPERVISOR]:
        if ticket.queue_id and hasattr(user, 'can_access_queue'):
            return user.can_access_queue(ticket.queue_id)

    # CLIENT users can only see tickets they created
    if user.user_type == UserType.CLIENT:
        return ticket.created_by == user.id

    return False


@api_v2_bp.route('/tickets/<int:ticket_id>/attachments', methods=['GET'])
@dual_auth_required
@handle_exceptions
def list_attachments(ticket_id):
    """
    List all attachments for a ticket.

    GET /api/v2/tickets/<id>/attachments

    Returns:
        {
            "success": true,
            "data": [
                {
                    "id": 1,
                    "ticket_id": 123,
                    "filename": "document.pdf",
                    "file_type": "application/pdf",
                    "file_size": 1024,
                    ...
                }
            ]
        }
    """
    user = request.current_api_user
    db_session = db_manager.get_session()

    try:
        # Get ticket
        ticket = db_session.query(Ticket).get(ticket_id)

        if not ticket:
            return api_error(
                code=ErrorCodes.RESOURCE_NOT_FOUND,
                message=f'Ticket with ID {ticket_id} not found',
                status_code=404
            )

        # Check permission
        if not can_access_ticket(db_session, user, ticket):
            return api_error(
                code=ErrorCodes.PERMISSION_DENIED,
                message='You do not have permission to access this ticket',
                status_code=403
            )

        # Get attachments
        attachments = db_session.query(TicketAttachment).filter(
            TicketAttachment.ticket_id == ticket_id
        ).order_by(TicketAttachment.created_at.desc()).all()

        attachments_data = [format_attachment(a) for a in attachments]

        return api_response(
            data=attachments_data,
            message=f'Found {len(attachments_data)} attachment(s)'
        )

    finally:
        db_session.close()


@api_v2_bp.route('/tickets/<int:ticket_id>/attachments', methods=['POST'])
@dual_auth_required
@handle_exceptions
def upload_attachment(ticket_id):
    """
    Upload attachment(s) to a ticket.

    POST /api/v2/tickets/<id>/attachments
    Content-Type: multipart/form-data

    Form Data:
        attachments: File(s) to upload (can be multiple)

    Allowed file types: pdf, doc, docx, xls, xlsx, csv, txt, png, jpg, jpeg, gif, bmp, webp, zip, rar, 7z, tar, gz
    Maximum file size: 25 MB per file

    Returns:
        201: List of uploaded attachments
        400: Validation error (invalid file type, file too large)
        404: Ticket not found
    """
    user = request.current_api_user
    db_session = db_manager.get_session()

    try:
        # Get ticket
        ticket = db_session.query(Ticket).get(ticket_id)

        if not ticket:
            return api_error(
                code=ErrorCodes.RESOURCE_NOT_FOUND,
                message=f'Ticket with ID {ticket_id} not found',
                status_code=404
            )

        # Check permission
        if not can_access_ticket(db_session, user, ticket):
            return api_error(
                code=ErrorCodes.PERMISSION_DENIED,
                message='You do not have permission to add attachments to this ticket',
                status_code=403
            )

        # Check for files in request
        if 'attachments' not in request.files:
            return api_error(
                code=ErrorCodes.VALIDATION_ERROR,
                message='No files provided. Please include files with key "attachments"',
                status_code=400
            )

        files = request.files.getlist('attachments')
        if not files or all(not f.filename for f in files):
            return api_error(
                code=ErrorCodes.VALIDATION_ERROR,
                message='No valid files selected',
                status_code=400
            )

        # Ensure upload directory exists
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)

        uploaded_attachments = []
        errors = []

        for file in files:
            if not file or not file.filename:
                continue

            # Validate file extension
            if not allowed_file(file.filename):
                errors.append({
                    'filename': file.filename,
                    'error': f'File type not allowed. Allowed types: {", ".join(ALLOWED_EXTENSIONS)}'
                })
                continue

            # Validate file size
            file_size = get_file_size(file)
            if file_size > MAX_FILE_SIZE:
                errors.append({
                    'filename': file.filename,
                    'error': f'File too large. Maximum size is {MAX_FILE_SIZE // (1024 * 1024)} MB'
                })
                continue

            try:
                # Secure the filename
                original_filename = secure_filename(file.filename)

                # Create unique filename with timestamp
                timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
                unique_id = str(uuid.uuid4())[:8]
                file_extension = original_filename.rsplit('.', 1)[1].lower() if '.' in original_filename else 'bin'
                unique_filename = f"{ticket_id}_{timestamp}_{unique_id}.{file_extension}"

                # Save file
                file_path = os.path.join(UPLOAD_FOLDER, unique_filename)
                file.save(file_path)

                # Create attachment record
                attachment = TicketAttachment(
                    ticket_id=ticket_id,
                    filename=original_filename,
                    file_path=file_path,
                    file_type=file.content_type or 'application/octet-stream',
                    file_size=file_size,
                    uploaded_by=user.id,
                    created_at=datetime.utcnow()
                )

                db_session.add(attachment)
                db_session.flush()  # Get attachment ID

                uploaded_attachments.append(format_attachment(attachment))

                logger.info(f"Attachment uploaded: {original_filename} to ticket {ticket_id} by user {user.username}")

            except Exception as e:
                logger.exception(f"Error uploading file {file.filename}: {str(e)}")
                errors.append({
                    'filename': file.filename,
                    'error': str(e)
                })

        if not uploaded_attachments:
            return api_error(
                code=ErrorCodes.VALIDATION_ERROR,
                message='No files were successfully uploaded',
                status_code=400,
                details={'errors': errors} if errors else None
            )

        db_session.commit()

        response_data = {
            'uploaded': uploaded_attachments,
            'count': len(uploaded_attachments)
        }

        if errors:
            response_data['errors'] = errors

        return api_created(
            data=response_data,
            message=f'Successfully uploaded {len(uploaded_attachments)} file(s)'
        )

    except Exception as e:
        db_session.rollback()
        logger.exception(f"Error uploading attachment: {str(e)}")
        raise

    finally:
        db_session.close()


@api_v2_bp.route('/tickets/<int:ticket_id>/attachments/<int:attachment_id>', methods=['GET'])
@dual_auth_required
@handle_exceptions
def get_attachment(ticket_id, attachment_id):
    """
    Get a single attachment metadata.

    GET /api/v2/tickets/<ticket_id>/attachments/<attachment_id>

    Returns:
        200: Attachment metadata
        404: Attachment not found
    """
    user = request.current_api_user
    db_session = db_manager.get_session()

    try:
        # Get ticket
        ticket = db_session.query(Ticket).get(ticket_id)

        if not ticket:
            return api_error(
                code=ErrorCodes.RESOURCE_NOT_FOUND,
                message=f'Ticket with ID {ticket_id} not found',
                status_code=404
            )

        # Check permission
        if not can_access_ticket(db_session, user, ticket):
            return api_error(
                code=ErrorCodes.PERMISSION_DENIED,
                message='You do not have permission to access this ticket',
                status_code=403
            )

        # Get attachment
        attachment = db_session.query(TicketAttachment).filter(
            TicketAttachment.id == attachment_id,
            TicketAttachment.ticket_id == ticket_id
        ).first()

        if not attachment:
            return api_error(
                code=ErrorCodes.RESOURCE_NOT_FOUND,
                message=f'Attachment with ID {attachment_id} not found for ticket {ticket_id}',
                status_code=404
            )

        return api_response(data=format_attachment(attachment))

    finally:
        db_session.close()


@api_v2_bp.route('/tickets/<int:ticket_id>/attachments/<int:attachment_id>/download', methods=['GET'])
@dual_auth_required
@handle_exceptions
def download_attachment(ticket_id, attachment_id):
    """
    Download an attachment file.

    GET /api/v2/tickets/<ticket_id>/attachments/<attachment_id>/download

    Query Parameters:
        inline (bool): If true, display in browser (default: false - force download)

    Returns:
        200: File download
        404: Attachment not found
    """
    user = request.current_api_user
    db_session = db_manager.get_session()

    try:
        # Get ticket
        ticket = db_session.query(Ticket).get(ticket_id)

        if not ticket:
            return api_error(
                code=ErrorCodes.RESOURCE_NOT_FOUND,
                message=f'Ticket with ID {ticket_id} not found',
                status_code=404
            )

        # Check permission
        if not can_access_ticket(db_session, user, ticket):
            return api_error(
                code=ErrorCodes.PERMISSION_DENIED,
                message='You do not have permission to download attachments from this ticket',
                status_code=403
            )

        # Get attachment
        attachment = db_session.query(TicketAttachment).filter(
            TicketAttachment.id == attachment_id,
            TicketAttachment.ticket_id == ticket_id
        ).first()

        if not attachment:
            return api_error(
                code=ErrorCodes.RESOURCE_NOT_FOUND,
                message=f'Attachment with ID {attachment_id} not found for ticket {ticket_id}',
                status_code=404
            )

        # Check if file exists
        if not os.path.exists(attachment.file_path):
            logger.error(f"Attachment file not found on disk: {attachment.file_path}")
            return api_error(
                code=ErrorCodes.RESOURCE_NOT_FOUND,
                message='Attachment file not found on server',
                status_code=404
            )

        # Determine if inline display is requested
        inline = request.args.get('inline', 'false').lower() == 'true'

        # For PDF files, default to inline display
        is_pdf = attachment.filename.lower().endswith('.pdf')
        as_attachment = not (inline or is_pdf)

        logger.info(f"Attachment downloaded: {attachment.filename} from ticket {ticket_id} by user {user.username}")

        return send_file(
            attachment.file_path,
            as_attachment=as_attachment,
            download_name=attachment.filename,
            mimetype=attachment.file_type
        )

    finally:
        db_session.close()


@api_v2_bp.route('/tickets/<int:ticket_id>/attachments/<int:attachment_id>', methods=['DELETE'])
@dual_auth_required
@handle_exceptions
def delete_attachment(ticket_id, attachment_id):
    """
    Delete an attachment.

    DELETE /api/v2/tickets/<ticket_id>/attachments/<attachment_id>

    Returns:
        204: Successfully deleted
        404: Attachment not found
        403: Permission denied
    """
    user = request.current_api_user
    db_session = db_manager.get_session()

    try:
        # Get ticket
        ticket = db_session.query(Ticket).get(ticket_id)

        if not ticket:
            return api_error(
                code=ErrorCodes.RESOURCE_NOT_FOUND,
                message=f'Ticket with ID {ticket_id} not found',
                status_code=404
            )

        # Check permission to access ticket
        if not can_access_ticket(db_session, user, ticket):
            return api_error(
                code=ErrorCodes.PERMISSION_DENIED,
                message='You do not have permission to access this ticket',
                status_code=403
            )

        # Get attachment
        attachment = db_session.query(TicketAttachment).filter(
            TicketAttachment.id == attachment_id,
            TicketAttachment.ticket_id == ticket_id
        ).first()

        if not attachment:
            return api_error(
                code=ErrorCodes.RESOURCE_NOT_FOUND,
                message=f'Attachment with ID {attachment_id} not found for ticket {ticket_id}',
                status_code=404
            )

        # Additional permission check: only uploader, ticket owner, or admin can delete
        can_delete = (
            user.user_type in [UserType.SUPER_ADMIN, UserType.DEVELOPER] or
            attachment.uploaded_by == user.id or
            ticket.created_by == user.id or
            ticket.assigned_to_id == user.id
        )

        if not can_delete:
            return api_error(
                code=ErrorCodes.PERMISSION_DENIED,
                message='You do not have permission to delete this attachment',
                status_code=403
            )

        # Delete file from disk
        if os.path.exists(attachment.file_path):
            try:
                os.remove(attachment.file_path)
            except Exception as e:
                logger.warning(f"Could not delete file from disk: {str(e)}")

        # Delete attachment record
        filename = attachment.filename
        db_session.delete(attachment)
        db_session.commit()

        logger.info(f"Attachment deleted: {filename} from ticket {ticket_id} by user {user.username}")

        return api_no_content()

    except Exception as e:
        db_session.rollback()
        logger.exception(f"Error deleting attachment: {str(e)}")
        raise

    finally:
        db_session.close()
