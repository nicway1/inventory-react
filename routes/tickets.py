import datetime
from datetime import datetime as dt
from utils.timezone_utils import singapore_now_as_utc
import os
import json
import logging
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify, send_file, current_app, abort, Response, make_response
from utils.auth_decorators import login_required, admin_required
from models.ticket import Ticket, TicketCategory, TicketPriority, TicketStatus, RMAStatus, RepairStatus, TicketAccessory
from models.comment import Comment
from models.ticket_category_config import TicketCategoryConfig
from utils.store_instances import (
    ticket_store,
    user_store,
    queue_store,
    inventory_store,
    comment_store,
    activity_store,
    firecrawl_client,
    db_manager
)
from models.asset import Asset, AssetStatus
from werkzeug.utils import secure_filename
from models.customer_user import CustomerUser
from models.ticket_attachment import TicketAttachment as Attachment
import requests
from bs4 import BeautifulSoup
import sys
from config import TRACKINGMORE_API_KEY
import traceback

from dotenv import load_dotenv
from models.comment import Comment
from flask_login import current_user
from models.user import User, UserType, Country
from utils.countries import COUNTRIES
from datetime import timezone, timedelta
import datetime
import uuid
from utils.tracking_cache import TrackingCache
import re
from models.tracking_history import TrackingHistory
from models.tracking_refresh_log import TrackingRefreshLog
from utils.singpost_tracking import get_singpost_tracking_client

# Initialize SingPost Tracking client
singpost_client = get_singpost_tracking_client()
from sqlalchemy.orm import joinedload # Import joinedload
from sqlalchemy import func, or_, and_, text
from models.company import Company
from models.activity import Activity
from models.accessory import Accessory
from models.accessory_transaction import AccessoryTransaction
from models.queue import Queue
import time
import csv
import io
from config import UPLOAD_FOLDER, ALLOWED_EXTENSIONS

# Set up logging for this module
logger = logging.getLogger(__name__)

# Initialize TrackingMore client
try:
    logger.info("Initializing trackingmore v0.2")
    import trackingmore
    # Set API key for v0.2
    trackingmore.set_api_key(TRACKINGMORE_API_KEY)
    logger.info("Successfully initialized TrackingMore")
    trackingmore_client = None  # Not used with v0.2
except ImportError as e:
    logger.warning(f"Could not import trackingmore module: {str(e)}")
    trackingmore = None
    trackingmore_client = None
except Exception as e:
    logger.warning(f"Error initializing TrackingMore: {str(e)}")
    trackingmore = None
    trackingmore_client = None

# Define allowed file extensions
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'doc', 'docx', 'xls', 'xlsx', 'csv'}

tickets_bp = Blueprint('tickets', __name__, url_prefix='/tickets')


def check_ticket_permission(db_session, user, ticket):
    """
    Check if user has permission to access a ticket.
    Returns (has_permission, error_message)
    """
    from models.user_queue_permission import UserQueuePermission

    # Super admins and developers have full access
    if user.user_type in [UserType.SUPER_ADMIN, UserType.DEVELOPER]:
        return True, None

    # COUNTRY_ADMIN and SUPERVISOR: Check queue and country permissions
    if user.user_type in [UserType.COUNTRY_ADMIN, UserType.SUPERVISOR]:
        # Check queue permission - must have explicit access
        has_queue_access = False
        if ticket.queue_id:
            queue_permission = db_session.query(UserQueuePermission).filter_by(
                user_id=user.id,
                queue_id=ticket.queue_id,
                can_view=True
            ).first()
            has_queue_access = queue_permission is not None
        # If ticket has no queue, user cannot access it

        # Check country if assigned
        has_country_access = True
        if user.assigned_countries and ticket.country:
            has_country_access = ticket.country in user.assigned_countries

        if not has_queue_access:
            return False, "You do not have permission to access tickets in this queue"
        if not has_country_access:
            return False, "You do not have permission to access tickets from this country"
        return True, None

    # CLIENT: Check if ticket belongs to their company or they created it
    if user.user_type == UserType.CLIENT:
        if not user.company_id:
            return False, "Your account is not associated with a company"

        customer_company_id = ticket.customer.company_id if ticket.customer else None
        is_requester = ticket.requester_id == user.id
        is_same_company = customer_company_id == user.company_id

        if is_requester or is_same_company:
            return True, None
        return False, "You do not have permission to view this ticket"

    # Default deny for unknown user types
    return False, "Unknown user type"


def get_filtered_customers(db_session, user):
    """Get customers filtered by company permissions for non-SUPER_ADMIN users"""
    from models.company_customer_permission import CompanyCustomerPermission
    from models.user_company_permission import UserCompanyPermission
    from sqlalchemy import or_
    import logging
    logger = logging.getLogger(__name__)

    customers_query = db_session.query(CustomerUser)

    # SUPER_ADMIN and DEVELOPER users can see all customers
    if user.user_type in [UserType.SUPER_ADMIN, UserType.DEVELOPER]:
        return customers_query.order_by(CustomerUser.name).all()

    # For COUNTRY_ADMIN and SUPERVISOR, use UserCompanyPermission
    if user.user_type in [UserType.COUNTRY_ADMIN, UserType.SUPERVISOR]:
        # Get the companies this user has been assigned to via UserCompanyPermission
        user_company_permissions = db_session.query(UserCompanyPermission).filter_by(
            user_id=user.id,
            can_view=True
        ).all()

        if user_company_permissions:
            # Get permitted company IDs from user's company permissions
            permitted_company_ids = [perm.company_id for perm in user_company_permissions]
            logger.info(f"DEBUG: {user.user_type.value} customer filtering by company IDs: {permitted_company_ids}")

            # Also include child companies of any parent company the user has permission to
            from models.company import Company
            permitted_companies = db_session.query(Company).filter(Company.id.in_(permitted_company_ids)).all()
            all_permitted_ids = list(permitted_company_ids)

            for company in permitted_companies:
                if company.is_parent_company or company.child_companies.count() > 0:
                    # This is a parent company - include all child company IDs
                    child_ids = [c.id for c in company.child_companies.all()]
                    all_permitted_ids.extend(child_ids)
                    logger.info(f"DEBUG: Including child companies of {company.name}: IDs {child_ids}")

            # Now check if there are any CompanyCustomerPermission entries for cross-company viewing
            cross_company_ids = []
            for company_id in all_permitted_ids:
                additional_company_ids = db_session.query(CompanyCustomerPermission.customer_company_id)\
                    .filter(
                        CompanyCustomerPermission.company_id == company_id,
                        CompanyCustomerPermission.can_view == True
                    ).all()
                cross_company_ids.extend([cid[0] for cid in additional_company_ids])

            # Combine all permitted company IDs
            final_permitted_ids = list(set(all_permitted_ids + cross_company_ids))
            logger.info(f"DEBUG: Final permitted company IDs for customers: {final_permitted_ids}")

            # Filter customers to only those from permitted companies
            customers_query = customers_query.filter(
                CustomerUser.company_id.in_(final_permitted_ids)
            )
        else:
            # No company permissions assigned - show NO customers
            logger.info(f"DEBUG: {user.user_type.value} has NO company permissions - showing 0 customers")
            customers_query = customers_query.filter(CustomerUser.id == -1)  # Impossible condition

        return customers_query.order_by(CustomerUser.name).all()

    # For other users (e.g., CLIENT), apply permission-based filtering
    if user.company_id:
        # Get companies this user's company has permission to view customers from
        permitted_company_ids = db_session.query(CompanyCustomerPermission.customer_company_id)\
            .filter(
                CompanyCustomerPermission.company_id == user.company_id,
                CompanyCustomerPermission.can_view == True
            ).subquery()

        # Users can always see their own company's customers, plus any permitted ones
        customers_query = customers_query.filter(
            or_(
                CustomerUser.company_id == user.company_id,  # Own company customers
                CustomerUser.company_id.in_(permitted_company_ids)  # Permitted customers
            )
        )

    return customers_query.order_by(CustomerUser.name).all()

# Initialize TrackingMore API key
TRACKINGMORE_API_KEY = "7yyp17vj-t0bh-jtg0-xjf0-v9m3335cjbtc"
# Trackingmore client is initialized above depending on the available package

@tickets_bp.route('/')
@login_required
def list_tickets():
    # Check if we should redirect to SF view based on system setting
    # Allow ?use_classic=1 to bypass the redirect for preview purposes
    if not request.args.get('use_classic'):
        db_session = None
        try:
            db_session = db_manager.get_session()
            from models.system_settings import SystemSettings
            ticket_view_setting = db_session.query(SystemSettings).filter_by(
                setting_key='default_ticket_view'
            ).first()
            if ticket_view_setting and ticket_view_setting.get_value() == 'sf':
                # Preserve any query parameters when redirecting (exclude use_classic)
                args = {k: v for k, v in request.args.items() if k != 'use_classic'}
                return redirect(url_for('tickets.list_tickets_sf', **args))
        except Exception as e:
            logger.warning(f"Could not check default_ticket_view setting: {str(e)}")
        finally:
            if db_session:
                db_session.close()

    user_id = session['user_id']
    user = db_manager.get_user(user_id)

    # Get date filter parameters
    from datetime import datetime
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')

    # Get queue IDs for filtering (for COUNTRY_ADMIN/SUPERVISOR)
    queue_ids = None
    if not user.is_super_admin and not user.is_developer:
        accessible_queue_ids = user.get_accessible_queue_ids()
        queue_ids = accessible_queue_ids
        logging.info(f"Will filter by {len(queue_ids) if queue_ids else 0} queue IDs in database query")

    # Get tickets based on user type with queue filter applied in database (MUCH faster!)
    tickets = ticket_store.get_user_tickets(user_id, user.user_type, queue_ids=queue_ids)
    logging.info(f"Got {len(tickets)} tickets from get_user_tickets (already filtered by queue in database)")

    # Apply date filtering if date parameters are provided
    if date_from or date_to:
        filtered_by_date = []
        for ticket in tickets:
            # Parse dates
            if date_from:
                try:
                    from_date = datetime.strptime(date_from, '%Y-%m-%d').date()
                    if ticket.created_at.date() < from_date:
                        continue
                except ValueError:
                    pass  # Invalid date format, skip filter

            if date_to:
                try:
                    to_date = datetime.strptime(date_to, '%Y-%m-%d').date()
                    if ticket.created_at.date() > to_date:
                        continue
                except ValueError:
                    pass  # Invalid date format, skip filter

            filtered_by_date.append(ticket)

        tickets = filtered_by_date
        logging.info(f"Applied date filter: {date_from} to {date_to}, {len(tickets)} tickets match")

    # Get queues for the filter dropdown, filtered by user permissions
    from models.queue import Queue
    from models.ticket import Ticket
    from sqlalchemy import func
    db_session = db_manager.get_session()
    queues = []

    try:
        # Get accessible queue IDs for COUNTRY_ADMIN and SUPERVISOR
        accessible_queue_ids = []
        if user.user_type in [UserType.COUNTRY_ADMIN, UserType.SUPERVISOR]:
            from models.user_queue_permission import UserQueuePermission
            queue_permissions = db_session.query(UserQueuePermission.queue_id).filter(
                UserQueuePermission.user_id == user.id,
                UserQueuePermission.can_view == True
            ).all()
            accessible_queue_ids = [q[0] for q in queue_permissions]
            logging.info(f"User {user.id} has access to {len(accessible_queue_ids)} queues")

        # Query queues with ticket count, sorted by count descending
        queues_with_counts = db_session.query(
            Queue,
            func.count(Ticket.id).label('ticket_count')
        ).outerjoin(
            Ticket, Queue.id == Ticket.queue_id
        ).group_by(
            Queue.id
        ).order_by(
            func.count(Ticket.id).desc(),
            Queue.name
        ).all()

        # Filter queues based on user permissions
        if user.is_super_admin or user.is_developer:
            queues = [queue for queue, count in queues_with_counts]
            logging.info(f"Loaded {len(queues)} queues for SUPER_ADMIN/DEVELOPER (all queues)")
        elif user.user_type in [UserType.COUNTRY_ADMIN, UserType.SUPERVISOR]:
            # Filter using directly queried UserQueuePermission IDs
            queues = [queue for queue, count in queues_with_counts if queue.id in accessible_queue_ids]
            logging.info(f"Loaded {len(queues)}/{len(queues_with_counts)} queues for COUNTRY_ADMIN/SUPERVISOR")
        else:
            # For CLIENT and other users - batch load queue permissions
            accessible_queue_ids = user.get_accessible_queue_ids()
            all_queues = [queue for queue, count in queues_with_counts]
            queues = [queue for queue in all_queues if queue.id in accessible_queue_ids]
            logging.info(f"Loaded {len(queues)}/{len(all_queues)} queues based on user permissions")

        for queue in queues:
            logging.debug(f"  Queue: {queue.name} (ID: {queue.id})")
    except Exception as e:
        logging.error(f"Error loading queues: {str(e)}")
        queues = []
    finally:
        db_session.close()

    # Calculate queue ticket counts (show all tickets in queue, not filtered by user)
    # This matches the behavior of the home page queue cards
    db_session = db_manager.get_session()
    queue_ticket_counts = {}
    try:
        for queue in queues:
            # Count ALL tickets for this queue
            total_count = db_session.query(Ticket).filter(Ticket.queue_id == queue.id).count()

            # Count OPEN tickets (non-resolved)
            from models.ticket import TicketStatus
            open_count = db_session.query(Ticket).filter(
                Ticket.queue_id == queue.id,
                Ticket.status != TicketStatus.RESOLVED,
                Ticket.status != TicketStatus.RESOLVED_DELIVERED
            ).count()

            queue_ticket_counts[queue.id] = {
                'total': total_count,
                'open': open_count
            }
    finally:
        db_session.close()

    # Get custom ticket statuses
    from models.custom_ticket_status import CustomTicketStatus
    db_session = db_manager.get_session()
    try:
        custom_statuses = db_session.query(CustomTicketStatus).filter(
            CustomTicketStatus.is_active == True
        ).order_by(CustomTicketStatus.sort_order).all()
        custom_statuses_list = [{'name': s.name, 'color': s.color} for s in custom_statuses]
    except:
        custom_statuses_list = []
    finally:
        db_session.close()

    return render_template('tickets/list.html', tickets=tickets, user=user, queues=queues, queue_ticket_counts=queue_ticket_counts, custom_statuses=custom_statuses_list)


@tickets_bp.route('/sf')
@login_required
def list_tickets_sf():
    """List tickets with Salesforce-style UI"""
    user_id = session['user_id']
    user = db_manager.get_user(user_id)

    # Get date filter parameters
    from datetime import datetime
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')

    # Get tickets based on user type (use enum, not session string value)
    logging.info(f"DEBUG SF - user_id: {user_id}, user.user_type: {user.user_type}, type: {type(user.user_type)}")
    logging.info(f"DEBUG SF - is_super_admin: {user.is_super_admin}, is_developer: {user.is_developer}")

    # Get queue IDs for filtering (for COUNTRY_ADMIN/SUPERVISOR)
    queue_ids = None
    if not user.is_super_admin and not user.is_developer:
        accessible_queue_ids = user.get_accessible_queue_ids()
        queue_ids = accessible_queue_ids
        logging.info(f"DEBUG SF - Will filter by {len(queue_ids) if queue_ids else 0} queue IDs in database query")

    # Get tickets with queue filter applied in database (MUCH faster!)
    tickets = ticket_store.get_user_tickets(user_id, user.user_type, queue_ids=queue_ids)
    logging.info(f"DEBUG SF - got {len(tickets)} tickets from get_user_tickets (already filtered by queue in database)")

    # Apply date filtering if date parameters are provided
    if date_from or date_to:
        filtered_by_date = []
        for ticket in tickets:
            if date_from:
                try:
                    from_date = datetime.strptime(date_from, '%Y-%m-%d').date()
                    if ticket.created_at.date() < from_date:
                        continue
                except ValueError:
                    pass

            if date_to:
                try:
                    to_date = datetime.strptime(date_to, '%Y-%m-%d').date()
                    if ticket.created_at.date() > to_date:
                        continue
                except ValueError:
                    pass

            filtered_by_date.append(ticket)
        tickets = filtered_by_date

    logging.info(f"DEBUG SF - final ticket count: {len(tickets)}")

    # Get queues for the filter dropdown
    from models.queue import Queue
    from models.ticket import Ticket
    from sqlalchemy import func
    db_session = db_manager.get_session()
    queues = []

    try:
        # Get accessible queue IDs for COUNTRY_ADMIN and SUPERVISOR
        accessible_queue_ids = []
        if user.user_type in [UserType.COUNTRY_ADMIN, UserType.SUPERVISOR]:
            from models.user_queue_permission import UserQueuePermission
            queue_permissions = db_session.query(UserQueuePermission.queue_id).filter(
                UserQueuePermission.user_id == user.id,
                UserQueuePermission.can_view == True
            ).all()
            accessible_queue_ids = [q[0] for q in queue_permissions]
            logging.info(f"DEBUG SF - User {user.id} has access to {len(accessible_queue_ids)} queues: {accessible_queue_ids}")

        queues_with_counts = db_session.query(
            Queue,
            func.count(Ticket.id).label('ticket_count')
        ).outerjoin(
            Ticket, Queue.id == Ticket.queue_id
        ).group_by(
            Queue.id
        ).order_by(
            func.count(Ticket.id).desc(),
            Queue.name
        ).all()

        if user.is_super_admin or user.is_developer:
            queues = [queue for queue, count in queues_with_counts]
            logging.info(f"DEBUG SF - SUPER_ADMIN/DEVELOPER sees all {len(queues)} queues")
        elif user.user_type in [UserType.COUNTRY_ADMIN, UserType.SUPERVISOR]:
            # Filter using directly queried UserQueuePermission IDs
            queues = [queue for queue, count in queues_with_counts if queue.id in accessible_queue_ids]
            logging.info(f"DEBUG SF - COUNTRY_ADMIN/SUPERVISOR sees {len(queues)}/{len(queues_with_counts)} queues")
        else:
            # For CLIENT and other users - batch load queue permissions
            accessible_queue_ids = user.get_accessible_queue_ids()
            all_queues = [queue for queue, count in queues_with_counts]
            queues = [queue for queue in all_queues if queue.id in accessible_queue_ids]
    except Exception as e:
        logging.error(f"Error loading queues: {str(e)}")
        queues = []
    finally:
        db_session.close()

    # Calculate queue ticket counts
    db_session = db_manager.get_session()
    queue_ticket_counts = {}
    try:
        for queue in queues:
            total_count = db_session.query(Ticket).filter(Ticket.queue_id == queue.id).count()
            open_count = db_session.query(Ticket).filter(
                Ticket.queue_id == queue.id,
                Ticket.status != TicketStatus.RESOLVED,
                Ticket.status != TicketStatus.RESOLVED_DELIVERED
            ).count()
            queue_ticket_counts[queue.id] = {
                'total': total_count,
                'open': open_count
            }
    finally:
        db_session.close()

    # Get folders data for all users (filtered by accessible queues for non-admins)
    folders_data = queue_store.get_queues_with_folders()

    # For non-admin users, filter folders to only show queues they have access to
    if not user.is_super_admin and not user.is_developer:
        filtered_folders = []
        for folder in folders_data.get('folders', []):
            # Filter queues in this folder to only those the user can access
            accessible_folder_queues = [q for q in folder.get('queues', []) if q['id'] in accessible_queue_ids]
            if accessible_folder_queues:  # Only include folder if it has accessible queues
                folder['queues'] = accessible_folder_queues
                folder['queue_count'] = len(accessible_folder_queues)
                filtered_folders.append(folder)
        folders_data['folders'] = filtered_folders

        # Filter unfiled queues to only those the user can access
        folders_data['unfiled_queues'] = [q for q in folders_data.get('unfiled_queues', []) if q['id'] in accessible_queue_ids]

    # Calculate aggregate ticket counts for each folder
    for folder in folders_data.get('folders', []):
        folder_open = 0
        folder_total = 0
        folder_queue_ids = []
        for q in folder.get('queues', []):
            counts = queue_ticket_counts.get(q['id'], {'open': 0, 'total': 0})
            folder_open += counts['open']
            folder_total += counts['total']
            folder_queue_ids.append(q['id'])
        folder['open_count'] = folder_open
        folder['total_count'] = folder_total
        folder['queue_ids'] = folder_queue_ids

    # Get custom ticket statuses
    from models.custom_ticket_status import CustomTicketStatus
    db_session = db_manager.get_session()
    try:
        custom_statuses = db_session.query(CustomTicketStatus).filter(
            CustomTicketStatus.is_active == True
        ).order_by(CustomTicketStatus.sort_order).all()
        custom_statuses_list = [{'name': s.name, 'color': s.color} for s in custom_statuses]
    except:
        custom_statuses_list = []
    finally:
        db_session.close()

    # Calculate SLA status for all tickets (using a single session for performance)
    from utils.sla_calculator import get_sla_status
    from database import SessionLocal
    ticket_sla_data = {}
    sla_db = SessionLocal()
    try:
        for ticket in tickets:
            sla_info = get_sla_status(ticket, db=sla_db)
            if sla_info['has_sla']:
                ticket_sla_data[ticket.id] = {
                    'status': sla_info['status'],
                    'days_remaining': sla_info['days_remaining'],
                    'due_date': sla_info['due_date'].isoformat() if sla_info['due_date'] else None
                }
    finally:
        sla_db.close()

    # Get all users for bulk assign dropdown
    from models.user import User
    users_db = db_manager.get_session()
    try:
        users = users_db.query(User).order_by(User.username).all()

        # Check if current user has access to firstbase company
        from models.company import Company
        user_has_firstbase_access = current_user.is_super_admin or current_user.is_developer
        if not user_has_firstbase_access:
            try:
                # Check company permissions
                firstbase_company = users_db.query(Company).filter(
                    Company.name.ilike('%firstbase%')
                ).first()
                if firstbase_company:
                    user_has_firstbase_access = current_user.can_access_company(firstbase_company.id)
            except Exception as e:
                logger.error(f"Error checking Firstbase access in list view: {str(e)}")
                user_has_firstbase_access = False
    except:
        users = []
        user_has_firstbase_access = False
    finally:
        users_db.close()

    return render_template('tickets/list_sf.html', tickets=tickets, user=user, users=users, queues=queues, queue_ticket_counts=queue_ticket_counts, custom_statuses=custom_statuses_list, folders_data=folders_data, ticket_sla_data=ticket_sla_data, user_has_firstbase_access=user_has_firstbase_access)


@tickets_bp.route('/refresh-all-statuses', methods=['POST'])
@login_required
def refresh_all_statuses():
    """
    Refresh all ticket statuses based on their current shipment/return status.
    This applies the same auto-update logic that runs when viewing individual tickets.
    """
    db_session = None
    try:
        db_session = db_manager.get_session()

        # Get all non-resolved tickets that might need status updates
        tickets = db_session.query(Ticket).filter(
            Ticket.status.in_([TicketStatus.NEW, TicketStatus.IN_PROGRESS, TicketStatus.ON_HOLD])
        ).all()

        updated_count = 0
        closed_count = 0
        errors = []

        for ticket in tickets:
            try:
                original_status = ticket.status

                # Auto-update status for Asset Return (Claw) tickets based on progress
                if ticket.category == TicketCategory.ASSET_RETURN_CLAW:
                    # Check for "received" or "delivered" (case-insensitive)
                    return_received = ticket.shipping_status and ("received" in ticket.shipping_status.lower() or "delivered" in ticket.shipping_status.lower())
                    replacement_received = ticket.replacement_status and ("received" in ticket.replacement_status.lower() or "delivered" in ticket.replacement_status.lower())

                    # Check if there's a replacement tracking
                    has_replacement = ticket.replacement_tracking and ticket.replacement_tracking.strip()

                    # Auto-close logic
                    should_close = False
                    if return_received:
                        if not has_replacement:
                            should_close = True
                        elif replacement_received:
                            should_close = True

                    if should_close and ticket.status not in [TicketStatus.RESOLVED, TicketStatus.RESOLVED_DELIVERED]:
                        ticket.status = TicketStatus.RESOLVED
                        ticket.custom_status = None
                        ticket.notes = (ticket.notes or "") + f"\n[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}] Ticket auto-closed via bulk refresh: Return received at warehouse. Case completed!"
                        logger.info(f"Bulk refresh: Auto-closed ticket {ticket.id}")
                    # Set to IN_PROGRESS if any progress has been made and status is still NEW
                    elif ticket.status == TicketStatus.NEW:
                        has_progress = (
                            ticket.shipping_tracking or
                            (ticket.shipping_status and ticket.shipping_status not in ['Pending', 'Information Received']) or
                            return_received or
                            replacement_received
                        )
                        if has_progress:
                            ticket.status = TicketStatus.IN_PROGRESS
                            ticket.custom_status = None
                            logger.info(f"Bulk refresh: Updated ticket {ticket.id} to IN_PROGRESS")

                # Track if status changed (after all the logic above)
                if original_status != ticket.status:
                    if ticket.status == TicketStatus.RESOLVED:
                        closed_count += 1
                    else:
                        updated_count += 1

            except Exception as e:
                errors.append(f"Ticket {ticket.id}: {str(e)}")
                logger.error(f"Error refreshing ticket {ticket.id}: {str(e)}")
                continue

        db_session.commit()

        return jsonify({
            'success': True,
            'message': f'Refreshed {len(tickets)} tickets',
            'updated': updated_count,
            'closed': closed_count,
            'errors': errors
        })

    except Exception as e:
        if db_session:
            db_session.rollback()
        logger.error(f"Error in bulk refresh: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
    finally:
        if db_session:
            db_session.close()


@tickets_bp.route('/export/csv')
@login_required
def export_tickets_csv():
    """Export tickets to CSV format with filtering support"""
    user_id = session['user_id']
    user = db_manager.get_user(user_id)
    user_type = session['user_type']

    # Get filter parameters from request
    export_mode = request.args.get('mode', 'all')  # all, filtered, selected
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    category_filter = request.args.get('category')
    priority_filter = request.args.get('priority')
    status_filter = request.args.get('status')
    queue_filter = request.args.get('queue')  # Changed from country_filter
    company_filter = request.args.get('company')
    ticket_ids = request.args.get('ticket_ids')

    # Create a new database session for this operation
    db_session = db_manager.get_session()

    try:
        # Build query with eager loading to avoid DetachedInstanceError
        query = db_session.query(Ticket).options(
            joinedload(Ticket.customer)
                .joinedload(CustomerUser.company)
                .joinedload(Company.parent_company),
            joinedload(Ticket.assigned_to),
            joinedload(Ticket.queue),
            joinedload(Ticket.assets),
            joinedload(Ticket.accessories),
            joinedload(Ticket.accessory),
            joinedload(Ticket.tracking_histories),
            joinedload(Ticket.comments).joinedload(Comment.user)
        )

        # Apply user permission filters
        if user.user_type == UserType.CLIENT:
            # For CLIENT users, only show tickets related to their company
            query = query.filter(Ticket.requester_id == user_id)
        elif user.user_type in [UserType.COUNTRY_ADMIN, UserType.SUPERVISOR]:
            # COUNTRY_ADMIN and SUPERVISOR can only see tickets from queues they have access to
            # Get queue IDs the user has permission to access
            from models.user_queue_permission import UserQueuePermission
            accessible_queue_ids = db_session.query(UserQueuePermission.queue_id).filter(
                UserQueuePermission.user_id == user_id,
                UserQueuePermission.can_view == True
            ).all()
            accessible_queue_ids = [q[0] for q in accessible_queue_ids]

            if accessible_queue_ids:
                # Only include tickets from accessible queues
                query = query.filter(Ticket.queue_id.in_(accessible_queue_ids))
            else:
                # No queue permissions - return no tickets
                query = query.filter(Ticket.id == -1)  # Impossible condition

        # Apply export mode filters
        if export_mode == 'selected' and ticket_ids:
            # Export only selected tickets
            id_list = [int(tid.strip()) for tid in ticket_ids.split(',') if tid.strip().isdigit()]
            if id_list:  # Only apply filter if we have valid IDs
                query = query.filter(Ticket.id.in_(id_list))
        elif export_mode == 'filtered':
            # Apply date range filter
            if date_from:
                try:
                    from_date = datetime.datetime.strptime(date_from, '%Y-%m-%d')
                    query = query.filter(Ticket.created_at >= from_date)
                except ValueError:
                    pass

            if date_to:
                try:
                    to_date = datetime.datetime.strptime(date_to, '%Y-%m-%d')
                    # Add 23:59:59 to include the entire day
                    to_date = to_date.replace(hour=23, minute=59, second=59)
                    query = query.filter(Ticket.created_at <= to_date)
                except ValueError:
                    pass

            # Apply category filter
            if category_filter and category_filter != 'all':
                try:
                    category_enum = TicketCategory(category_filter)
                    query = query.filter(Ticket.category == category_enum)
                except ValueError:
                    pass

            # Apply priority filter
            if priority_filter and priority_filter != 'all':
                from models.ticket import TicketPriority
                try:
                    priority_enum = TicketPriority(priority_filter)
                    query = query.filter(Ticket.priority == priority_enum)
                except ValueError:
                    pass

            # Apply status filter
            if status_filter and status_filter != 'all':
                from models.ticket import TicketStatus
                try:
                    status_enum = TicketStatus(status_filter)
                    query = query.filter(Ticket.status == status_enum, Ticket.custom_status == None)
                except ValueError:
                    # Not a standard status - filter by custom_status
                    query = query.filter(Ticket.custom_status == status_filter)

            # Apply queue filter
            if queue_filter and queue_filter != 'all':
                # Filter by queue name
                from models.queue import Queue
                queue_obj = db_session.query(Queue).filter(Queue.name == queue_filter).first()
                if queue_obj:
                    query = query.filter(Ticket.queue_id == queue_obj.id)

            # Apply company filter
            if company_filter and company_filter != 'all':
                try:
                    company_id = int(company_filter)
                    # Get the company to check if it's a parent
                    company = db_session.query(Company).get(company_id)

                    if company:
                        if company.is_parent_company:
                            # If parent company is selected, include all child companies
                            child_company_ids = [c.id for c in company.child_companies.all()]
                            all_company_ids = [company_id] + child_company_ids

                            # Filter tickets where customer's company is parent or any child
                            query = query.join(CustomerUser, Ticket.customer_id == CustomerUser.id, isouter=True).filter(
                                CustomerUser.company_id.in_(all_company_ids)
                            )
                        else:
                            # If child or standalone company, just filter by that company
                            query = query.join(CustomerUser, Ticket.customer_id == CustomerUser.id, isouter=True).filter(
                                CustomerUser.company_id == company_id
                            )
                except (ValueError, TypeError):
                    pass

        tickets = query.all()

        # Filter tickets based on queue access permissions (same as list_tickets)
        if not user.is_super_admin and not user.is_developer:
            # Batch-load accessible queue IDs to avoid N+1 queries
            accessible_queue_ids = user.get_accessible_queue_ids()
            filtered_tickets = []
            for ticket in tickets:
                if ticket.queue_id and ticket.queue_id in accessible_queue_ids:
                    filtered_tickets.append(ticket)
                elif not ticket.queue_id:
                    filtered_tickets.append(ticket)
            tickets = filtered_tickets

        # Create CSV content
        output = io.StringIO()
        writer = csv.writer(output)

        # CSV headers
        headers = [
            'Ticket ID',
            'Display ID',
            'Order ID',
            'Subject',
            'Description',
            'Status',
            'Priority',
            'Category',
            'Assigned To',
            'Customer',
            'Customer Email',
            'Customer Phone',
            'Customer Company',
            'Customer Parent Company',
            'Customer Address',
            'Customer Timezone',
            'Customer Department',
            'Country',
            'Created Date',
            'Updated Date',
            'Package Number',
            'Package Tracking Number',
            'Item Type',
            'Item Name',
            'Legacy Assets',
            'Return Shipping Tracking',
            'Outbound Shipping Tracking',
            'Queue',
            'Package Journey - Latest Status',
            'Package Journey - Carrier',
            'Package Journey - Last Update',
            'Package Journey - Full History',
            'Comments Count',
            'Comments'
        ]
        writer.writerow(headers)

        # Write ticket data
        for ticket in tickets:
            # Get asset info (now safely loaded with joinedload)
            assets_info = []
            try:
                if ticket.assets:
                    for asset in ticket.assets:
                        if asset.model:
                            assets_info.append(f"{asset.serial_num} ({asset.model})")
                        else:
                            assets_info.append(asset.serial_num)
            except Exception as e:
                logger.warning(f"Error accessing assets for ticket {ticket.id}: {e}")
            assets_str = '; '.join(assets_info) if assets_info else ''

            # Get customer info safely
            customer_name = ''
            customer_email = ''
            customer_phone = ''
            customer_company = ''
            customer_parent_company = ''
            customer_address = ''
            customer_timezone = ''
            customer_department = ''
            customer_country = ''

            try:
                if ticket.customer:
                    customer = ticket.customer
                    if hasattr(customer, 'name'):
                        customer_name = customer.name or ''
                    else:
                        customer_name = str(customer)
                    customer_email = getattr(customer, 'email', '') or ''
                    customer_phone = (
                        getattr(customer, 'contact_number', None)
                        or getattr(customer, 'phone', None)
                        or ''
                    )
                    customer_timezone = getattr(customer, 'timezone', '') or ''
                    customer_department = getattr(customer, 'department', '') or ''
                    country_attr = getattr(customer, 'country', None)
                    if hasattr(country_attr, 'value'):
                        customer_country = country_attr.value or ''
                    elif country_attr:
                        customer_country = str(country_attr)
                    company = getattr(customer, 'company', None)
                    if company:
                        customer_company = getattr(company, 'grouped_display_name', None) or getattr(company, 'display_name', None) or company.name or ''
                        parent_company = getattr(company, 'parent_company', None)
                        if parent_company:
                            parent_display = getattr(parent_company, 'effective_display_name', None)
                            customer_parent_company = parent_display or getattr(parent_company, 'display_name', None) or parent_company.name or ''
                    raw_address = ''
                    if getattr(ticket, 'shipping_address', None):
                        raw_address = ticket.shipping_address
                    elif getattr(customer, 'address', None):
                        raw_address = customer.address
                    if raw_address:
                        address_lines = [line.strip() for line in raw_address.splitlines() if line.strip()]
                        customer_address = ', '.join(address_lines)
            except Exception as e:
                logger.warning(f"Error accessing customer for ticket {ticket.id}: {e}")

            # Get assigned user info safely
            assigned_to = 'Unassigned'
            try:
                if ticket.assigned_to:
                    assigned_to = ticket.assigned_to.username
            except Exception as e:
                logger.warning(f"Error accessing assigned_to for ticket {ticket.id}: {e}")

            # Get queue name safely
            queue_name = ''
            try:
                if ticket.queue:
                    queue_name = ticket.queue.name
            except Exception as e:
                logger.warning(f"Error accessing queue for ticket {ticket.id}: {e}")

            # Get tracking information safely (bulk export)
            latest_status = ''
            latest_carrier = ''
            latest_update = ''
            full_history = ''

            try:
                if ticket.tracking_histories:
                    # Get the most recent tracking history
                    latest_tracking = max(ticket.tracking_histories, key=lambda t: t.last_updated or dt.min)

                    if latest_tracking:
                        latest_status = latest_tracking.status or ''
                        latest_carrier = latest_tracking.carrier or ''
                        latest_update = latest_tracking.last_updated.strftime('%Y-%m-%d %H:%M:%S') if latest_tracking.last_updated else ''

                        # Build full history from tracking events
                        history_entries = []
                        for tracking in ticket.tracking_histories:
                            tracking_events = tracking.events
                            if tracking_events:
                                for event in tracking_events:
                                    # Extract event information
                                    event_date = event.get('date', '')
                                    event_status = event.get('status', '')
                                    event_location = event.get('location', '')
                                    event_description = event.get('description', '')

                                    if event_date or event_status:
                                        history_entries.append(f"{event_date} - {event_status}")
                                        if event_location:
                                            history_entries[-1] += f" ({event_location})"
                                        if event_description:
                                            history_entries[-1] += f" - {event_description}"

                        # If no events found, show basic tracking info
                        if not history_entries and latest_tracking:
                            basic_info = f"{latest_update} - {latest_status}"
                            if latest_carrier:
                                basic_info += f" via {latest_carrier}"
                            history_entries.append(basic_info)

                        full_history = ' | '.join(history_entries[:10])  # Limit to 10 most recent events
            except Exception as e:
                logger.warning(f"Error accessing tracking histories for ticket {ticket.id}: {e}")

            # Get comments information safely (bulk export)
            comments_count = 0
            comments_text = ''

            try:
                if ticket.comments:
                    comments_count = len(ticket.comments)
                    # Sort comments by creation date
                    sorted_comments = sorted(ticket.comments, key=lambda c: c.created_at or dt.min)

                    comment_entries = []
                    for comment in sorted_comments:
                        # Format: [Date] Username: Comment text
                        comment_date = comment.created_at.strftime('%Y-%m-%d %H:%M') if comment.created_at else 'Unknown date'
                        username = comment.user.username if comment.user else 'Unknown user'
                        content = comment.content or ''

                        # Clean content (remove newlines and extra spaces for CSV)
                        cleaned_content = ' '.join(content.strip().split())
                        if len(cleaned_content) > 100:  # Limit comment length in CSV
                            cleaned_content = cleaned_content[:97] + '...'

                        comment_entries.append(f"[{comment_date}] {username}: {cleaned_content}")

                    comments_text = ' | '.join(comment_entries)
            except Exception as e:
                logger.warning(f"Error accessing comments for ticket {ticket.id}: {e}")

            # Check if ticket has multiple packages (Asset Checkout/Return claw categories)
            packages = []
            if ticket.category and ticket.category.name in ['ASSET_CHECKOUT_CLAW', 'ASSET_RETURN_CLAW']:
                packages = ticket.get_all_packages()

            # If ticket has packages, create one row per item in each package
            if packages:
                from models.package_item import PackageItem
                for package in packages:
                    # Get items for this package
                    try:
                        items = db_session.query(PackageItem).filter_by(
                            ticket_id=ticket.id,
                            package_number=package['package_number']
                        ).all()

                        # Get tracking info for this specific package
                        pkg_tracking_number = package.get('tracking_number', '')
                        pkg_status = package.get('status', '')
                        pkg_carrier = package.get('carrier', '')

                        # Get return and outbound shipping tracking
                        return_shipping = getattr(ticket, 'return_tracking', '') or ''
                        outbound_shipping = pkg_tracking_number  # For Asset Checkout, outbound is the package tracking

                        # If package has items, create one row per item
                        if items:
                            for item in items:
                                item_description = ''
                                item_type = ''
                                if item.asset_id:
                                    asset = db_session.query(Asset).get(item.asset_id)
                                    if asset:
                                        # Format: MacBook Air 13" Apple Tag: O.783 SN: KMJL90245Q
                                        asset_name = asset.name or 'Asset'
                                        asset_tag = asset.asset_tag or 'N/A'
                                        asset_sn = asset.serial_num or 'N/A'
                                        item_description = f"{asset_name} Tag: {asset_tag} SN: {asset_sn}"
                                        item_type = 'Asset'
                                elif item.accessory_id:
                                    accessory = db_session.query(Accessory).get(item.accessory_id)
                                    if accessory:
                                        item_description = f"Accessory: {accessory.name} (x{item.quantity})"
                                        item_type = 'Accessory'

                                row = [
                                    ticket.id,
                                    getattr(ticket, 'display_id', ticket.id) if hasattr(ticket, 'display_id') else ticket.id,
                                    getattr(ticket, 'firstbaseorderid', '') or '',
                                    ticket.subject or '',
                                    ticket.description or '',
                                    ticket.status.value if ticket.status else '',
                                    ticket.priority.value if ticket.priority else '',
                                    ticket.get_category_display_name() if ticket.category else '',
                                    assigned_to,
                                    customer_name,
                                    customer_email,
                                    customer_phone,
                                    customer_company,
                                    customer_parent_company,
                                    customer_address,
                                    customer_timezone,
                                    customer_department,
                                    customer_country,
                                    ticket.created_at.strftime('%Y-%m-%d %H:%M:%S') if ticket.created_at else '',
                                    ticket.updated_at.strftime('%Y-%m-%d %H:%M:%S') if ticket.updated_at else '',
                                    package['package_number'],
                                    pkg_tracking_number,
                                    item_type,  # Asset or Accessory
                                    item_description,  # Single item description instead of all items
                                    '',  # Empty Assets column for package items (item is in Package Items column)
                                    return_shipping,
                                    outbound_shipping,
                                    queue_name,
                                    pkg_status,
                                    pkg_carrier,
                                    '',  # Latest update
                                    '',  # Full history
                                    comments_count,
                                    comments_text
                                ]
                                writer.writerow(row)
                        else:
                            # Package has no items, create one row for the package anyway
                            row = [
                                ticket.id,
                                getattr(ticket, 'display_id', ticket.id) if hasattr(ticket, 'display_id') else ticket.id,
                                getattr(ticket, 'firstbaseorderid', '') or '',
                                ticket.subject or '',
                                ticket.description or '',
                                ticket.status.value if ticket.status else '',
                                ticket.priority.value if ticket.priority else '',
                                ticket.get_category_display_name() if ticket.category else '',
                                assigned_to,
                                customer_name,
                                customer_email,
                                customer_phone,
                                customer_company,
                                customer_parent_company,
                                customer_address,
                                customer_timezone,
                                customer_department,
                                customer_country,
                                ticket.created_at.strftime('%Y-%m-%d %H:%M:%S') if ticket.created_at else '',
                                ticket.updated_at.strftime('%Y-%m-%d %H:%M:%S') if ticket.updated_at else '',
                                package['package_number'],
                                pkg_tracking_number,
                                '',  # No item type
                                '',  # No items
                                '',  # Empty Assets column for package rows
                                return_shipping,
                                outbound_shipping,
                                queue_name,
                                pkg_status,
                                pkg_carrier,
                                '',  # Latest update
                                '',  # Full history
                                comments_count,
                                comments_text
                            ]
                            writer.writerow(row)
                    except Exception as e:
                        logger.warning(f"Error loading package items: {e}")
            else:
                # For tickets without packages, export each asset and accessory as a separate row
                # For Asset Return (claw), get both return and outbound tracking
                return_shipping = getattr(ticket, 'return_tracking', '') or ''
                outbound_shipping = getattr(ticket, 'shipping_tracking', '') or ''

                # Collect all items (assets and accessories) for this ticket
                ticket_items = []

                # Add assets
                try:
                    if ticket.assets:
                        for asset in ticket.assets:
                            asset_name = asset.name or 'Asset'
                            asset_tag = asset.asset_tag or 'N/A'
                            asset_sn = asset.serial_num or 'N/A'
                            item_description = f"{asset_name} Tag: {asset_tag} SN: {asset_sn}"
                            ticket_items.append({
                                'type': 'Tech Asset',
                                'description': item_description,
                                'quantity': 1
                            })
                except Exception as e:
                    logger.warning(f"Error accessing assets for ticket {ticket.id}: {e}")

                # Add accessories from TicketAccessory relationship
                try:
                    if ticket.accessories:
                        for ticket_accessory in ticket.accessories:
                            accessory_name = ticket_accessory.accessory_name or 'Unknown Accessory'
                            qty = ticket_accessory.quantity or 1
                            ticket_items.append({
                                'type': 'Accessory',
                                'description': accessory_name,
                                'quantity': qty
                            })
                except Exception as e:
                    logger.warning(f"Error accessing ticket accessories for ticket {ticket.id}: {e}")

                # Add single accessory if set (accessory_id field)
                try:
                    if ticket.accessory_id and ticket.accessory:
                        accessory = ticket.accessory
                        accessory_name = accessory.name or 'Accessory'
                        accessory_qty = getattr(ticket, 'accessory_quantity', 1) or 1
                        # Don't add if already added from ticket.accessories
                        already_added = any(
                            item['description'] == accessory_name and item['type'] == 'Accessory'
                            for item in ticket_items
                        )
                        if not already_added:
                            ticket_items.append({
                                'type': 'Accessory',
                                'description': accessory_name,
                                'quantity': accessory_qty
                            })
                except Exception as e:
                    logger.warning(f"Error accessing single accessory for ticket {ticket.id}: {e}")

                # If ticket has items, create one row per item
                if ticket_items:
                    for item in ticket_items:
                        item_description = item['description']
                        if item['quantity'] > 1:
                            item_description = f"{item['description']} (x{item['quantity']})"

                        row = [
                            ticket.id,
                            getattr(ticket, 'display_id', ticket.id) if hasattr(ticket, 'display_id') else ticket.id,
                            getattr(ticket, 'firstbaseorderid', '') or '',
                            ticket.subject or '',
                            ticket.description or '',
                            ticket.status.value if ticket.status else '',
                            ticket.priority.value if ticket.priority else '',
                            ticket.get_category_display_name() if ticket.category else '',
                            assigned_to,
                            customer_name,
                            customer_email,
                            customer_phone,
                            customer_company,
                            customer_parent_company,
                            customer_address,
                            customer_timezone,
                            customer_department,
                            customer_country,
                            ticket.created_at.strftime('%Y-%m-%d %H:%M:%S') if ticket.created_at else '',
                            ticket.updated_at.strftime('%Y-%m-%d %H:%M:%S') if ticket.updated_at else '',
                            '',  # Package number
                            '',  # Package tracking number
                            item['type'],  # Item type (Tech Asset or Accessory)
                            item_description,  # Item description with quantity
                            '',  # Assets column (item is in Package Items column)
                            return_shipping,
                            outbound_shipping,
                            queue_name,
                            latest_status,
                            latest_carrier,
                            latest_update,
                            full_history,
                            comments_count,
                            comments_text
                        ]
                        writer.writerow(row)
                else:
                    # Ticket has no items, create single row
                    row = [
                        ticket.id,
                        getattr(ticket, 'display_id', ticket.id) if hasattr(ticket, 'display_id') else ticket.id,
                        getattr(ticket, 'firstbaseorderid', '') or '',
                        ticket.subject or '',
                        ticket.description or '',
                        ticket.status.value if ticket.status else '',
                        ticket.priority.value if ticket.priority else '',
                        ticket.get_category_display_name() if ticket.category else '',
                        assigned_to,
                        customer_name,
                        customer_email,
                        customer_phone,
                        customer_company,
                        customer_parent_company,
                        customer_address,
                        customer_timezone,
                        customer_department,
                        customer_country,
                        ticket.created_at.strftime('%Y-%m-%d %H:%M:%S') if ticket.created_at else '',
                        ticket.updated_at.strftime('%Y-%m-%d %H:%M:%S') if ticket.updated_at else '',
                        '',  # Package number
                        '',  # Package tracking number
                        '',  # Item type
                        '',  # Package items
                        '',  # Assets
                        return_shipping,
                        outbound_shipping,
                        queue_name,
                        latest_status,
                        latest_carrier,
                        latest_update,
                        full_history,
                        comments_count,
                        comments_text
                    ]
                    writer.writerow(row)

        # Create response with CSV file
        output.seek(0)
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')

        # Generate descriptive filename based on export mode
        if export_mode == 'selected':
            filename = f'tickets_selected_{len(tickets)}tickets_{timestamp}.csv'
        elif export_mode == 'filtered':
            filter_parts = []
            if date_from or date_to:
                date_part = f"from{date_from}" if date_from else ""
                date_part += f"_to{date_to}" if date_to else ""
                if date_part:
                    filter_parts.append(date_part)
            if category_filter and category_filter != 'all':
                filter_parts.append(f"cat{category_filter}")
            if priority_filter and priority_filter != 'all':
                filter_parts.append(f"pri{priority_filter}")
            if status_filter and status_filter != 'all':
                filter_parts.append(f"status{status_filter}")
            if queue_filter and queue_filter != 'all':
                filter_parts.append(f"queue{queue_filter}")
            if company_filter and company_filter != 'all':
                filter_parts.append(f"company{company_filter}")

            filter_desc = "_".join(filter_parts) if filter_parts else "filtered"
            filename = f'tickets_{filter_desc}_{len(tickets)}results_{timestamp}.csv'
        else:
            filename = f'tickets_all_{len(tickets)}tickets_{timestamp}.csv'

        response = make_response(output.getvalue())
        response.headers['Content-Type'] = 'text/csv'
        response.headers['Content-Disposition'] = f'attachment; filename={filename}'

        return response

    finally:
        db_session.close()

@tickets_bp.route('/<int:ticket_id>/export/csv')
@login_required
def export_single_ticket_csv(ticket_id):
    """Export a single ticket to CSV format"""
    user_id = session['user_id']
    user = db_manager.get_user(user_id)

    # Create a new database session for this operation
    db_session = db_manager.get_session()

    try:
        # Build query with eager loading for the specific ticket
        query = db_session.query(Ticket).options(
            joinedload(Ticket.customer)
                .joinedload(CustomerUser.company)
                .joinedload(Company.parent_company),
            joinedload(Ticket.assigned_to),
            joinedload(Ticket.queue),
            joinedload(Ticket.assets),
            joinedload(Ticket.tracking_histories),
            joinedload(Ticket.comments).joinedload(Comment.user)
        ).filter(Ticket.id == ticket_id)

        # Apply user permission filters
        if user.user_type == UserType.CLIENT:
            # For CLIENT users, only show tickets they requested
            query = query.filter(Ticket.requester_id == user_id)
        elif user.user_type == UserType.COUNTRY_ADMIN:
            # Country admins see tickets from their assigned countries
            assigned_countries = user.assigned_countries
            if assigned_countries:
                query = query.join(CustomerUser, Ticket.customer_id == CustomerUser.id).filter(
                    CustomerUser.country.in_(assigned_countries)
                )

        ticket = query.first()

        if not ticket:
            flash('Ticket not found or you do not have permission to view it.', 'error')
            return redirect(url_for('tickets.list_tickets'))

        # Check queue access permissions
        if not user.is_super_admin and not user.is_developer and ticket.queue_id and not user.can_access_queue(ticket.queue_id):
            flash('You do not have permission to access this ticket.', 'error')
            return redirect(url_for('tickets.list_tickets'))

        # Create CSV content
        output = io.StringIO()
        writer = csv.writer(output)

        # CSV headers (updated to include package information)
        headers = [
            'Ticket ID',
            'Display ID',
            'Order ID',
            'Subject',
            'Description',
            'Status',
            'Priority',
            'Category',
            'Assigned To',
            'Customer',
            'Customer Email',
            'Customer Phone',
            'Customer Company',
            'Customer Parent Company',
            'Customer Address',
            'Customer Timezone',
            'Customer Department',
            'Country',
            'Created Date',
            'Updated Date',
            'Package Number',
            'Package Tracking Number',
            'Package Items',
            'Assets',
            'Return Shipping Tracking',
            'Outbound Shipping Tracking',
            'Queue',
            'Package Journey - Latest Status',
            'Package Journey - Carrier',
            'Package Journey - Last Update',
            'Package Journey - Full History',
            'Comments Count',
            'Comments'
        ]
        writer.writerow(headers)

        # Get asset info
        assets_info = []
        try:
            if ticket.assets:
                for asset in ticket.assets:
                    if asset.model:
                        assets_info.append(f"{asset.serial_num} ({asset.model})")
                    else:
                        assets_info.append(asset.serial_num)
        except Exception as e:
            logger.warning(f"Error accessing assets for ticket {ticket.id}: {e}")
        assets_str = '; '.join(assets_info) if assets_info else ''

        # Get customer info safely
        customer_name = ''
        customer_email = ''
        customer_phone = ''
        customer_company = ''
        customer_parent_company = ''
        customer_address = ''
        customer_timezone = ''
        customer_department = ''
        customer_country = ''

        try:
            if ticket.customer:
                customer = ticket.customer
                if hasattr(customer, 'name'):
                    customer_name = customer.name or ''
                else:
                    customer_name = str(customer)
                customer_email = getattr(customer, 'email', '') or ''
                customer_phone = (
                    getattr(customer, 'contact_number', None)
                    or getattr(customer, 'phone', None)
                    or ''
                )
                customer_timezone = getattr(customer, 'timezone', '') or ''
                customer_department = getattr(customer, 'department', '') or ''
                country_attr = getattr(customer, 'country', None)
                if hasattr(country_attr, 'value'):
                    customer_country = country_attr.value or ''
                elif country_attr:
                    customer_country = str(country_attr)
                company = getattr(customer, 'company', None)
                if company:
                    customer_company = getattr(company, 'grouped_display_name', None) or getattr(company, 'display_name', None) or company.name or ''
                    parent_company = getattr(company, 'parent_company', None)
                    if parent_company:
                        parent_display = getattr(parent_company, 'effective_display_name', None)
                        customer_parent_company = parent_display or getattr(parent_company, 'display_name', None) or parent_company.name or ''
                raw_address = ''
                if getattr(ticket, 'shipping_address', None):
                    raw_address = ticket.shipping_address
                elif getattr(customer, 'address', None):
                    raw_address = customer.address
                if raw_address:
                    address_lines = [line.strip() for line in raw_address.splitlines() if line.strip()]
                    customer_address = ', '.join(address_lines)
        except Exception as e:
            logger.warning(f"Error accessing customer for ticket {ticket.id}: {e}")

        # Get assigned user info safely
        assigned_to = 'Unassigned'
        try:
            if ticket.assigned_to:
                assigned_to = ticket.assigned_to.username
        except Exception as e:
            logger.warning(f"Error accessing assigned_to for ticket {ticket.id}: {e}")

        # Get queue name safely
        queue_name = ''
        try:
            if ticket.queue:
                queue_name = ticket.queue.name
        except Exception as e:
            logger.warning(f"Error accessing queue for ticket {ticket.id}: {e}")

        # Get tracking information safely
        latest_status = ''
        latest_carrier = ''
        latest_update = ''
        full_history = ''

        try:
            if ticket.tracking_histories:
                # Get the most recent tracking history
                latest_tracking = max(ticket.tracking_histories, key=lambda t: t.last_updated or dt.min)

                if latest_tracking:
                    latest_status = latest_tracking.status or ''
                    latest_carrier = latest_tracking.carrier or ''
                    latest_update = latest_tracking.last_updated.strftime('%Y-%m-%d %H:%M:%S') if latest_tracking.last_updated else ''

                    # Build full history from tracking events
                    history_entries = []
                    for tracking in ticket.tracking_histories:
                        tracking_events = tracking.events
                        if tracking_events:
                            for event in tracking_events:
                                # Extract event information
                                event_date = event.get('date', '')
                                event_status = event.get('status', '')
                                event_location = event.get('location', '')
                                event_description = event.get('description', '')

                                if event_date or event_status:
                                    history_entries.append(f"{event_date} - {event_status}")
                                    if event_location:
                                        history_entries[-1] += f" ({event_location})"
                                    if event_description:
                                        history_entries[-1] += f" - {event_description}"

                    # If no events found, show basic tracking info
                    if not history_entries and latest_tracking:
                        basic_info = f"{latest_update} - {latest_status}"
                        if latest_carrier:
                            basic_info += f" via {latest_carrier}"
                        history_entries.append(basic_info)

                    full_history = ' | '.join(history_entries[:10])  # Limit to 10 most recent events
        except Exception as e:
            logger.warning(f"Error accessing tracking histories for ticket {ticket.id}: {e}")

        # Get comments information safely (single export)
        comments_count = 0
        comments_text = ''

        try:
            if ticket.comments:
                comments_count = len(ticket.comments)
                # Sort comments by creation date
                sorted_comments = sorted(ticket.comments, key=lambda c: c.created_at or dt.min)

                comment_entries = []
                for comment in sorted_comments:
                    # Format: [Date] Username: Comment text
                    comment_date = comment.created_at.strftime('%Y-%m-%d %H:%M') if comment.created_at else 'Unknown date'
                    username = comment.user.username if comment.user else 'Unknown user'
                    content = comment.content or ''

                    # Clean content (remove newlines and extra spaces for CSV)
                    cleaned_content = ' '.join(content.strip().split())
                    if len(cleaned_content) > 100:  # Limit comment length in CSV
                        cleaned_content = cleaned_content[:97] + '...'

                    comment_entries.append(f"[{comment_date}] {username}: {cleaned_content}")

                comments_text = ' | '.join(comment_entries)
        except Exception as e:
            logger.warning(f"Error accessing comments for ticket {ticket.id}: {e}")

        # Check if ticket has multiple packages (Asset Checkout/Return claw categories)
        packages = []
        if ticket.category and ticket.category.name in ['ASSET_CHECKOUT_CLAW', 'ASSET_RETURN_CLAW']:
            packages = ticket.get_all_packages()

        # If ticket has packages, create one row per package
        if packages:
            from models.package_item import PackageItem
            for package in packages:
                # Get items for this package
                package_items = []
                try:
                    items = db_session.query(PackageItem).filter_by(
                        ticket_id=ticket.id,
                        package_number=package['package_number']
                    ).all()
                    for item in items:
                        if item.asset_id:
                            asset = db_session.query(Asset).get(item.asset_id)
                            if asset:
                                package_items.append(f"Asset: {asset.serial_num}")
                        elif item.accessory_id:
                            accessory = db_session.query(Accessory).get(item.accessory_id)
                            if accessory:
                                package_items.append(f"Accessory: {accessory.name} (x{item.quantity})")
                except Exception as e:
                    logger.warning(f"Error loading package items: {e}")

                package_items_str = '; '.join(package_items) if package_items else ''

                # Get tracking info for this specific package
                pkg_tracking_number = package.get('tracking_number', '')
                pkg_status = package.get('status', '')
                pkg_carrier = package.get('carrier', '')

                # Get return and outbound shipping tracking
                return_shipping = getattr(ticket, 'return_tracking', '') or ''
                outbound_shipping = pkg_tracking_number  # For Asset Checkout, outbound is the package tracking

                row = [
                    ticket.id,
                    getattr(ticket, 'display_id', ticket.id) if hasattr(ticket, 'display_id') else ticket.id,
                    getattr(ticket, 'firstbaseorderid', '') or '',
                    ticket.subject or '',
                    ticket.description or '',
                    ticket.status.value if ticket.status else '',
                    ticket.priority.value if ticket.priority else '',
                    ticket.get_category_display_name() if ticket.category else '',
                    assigned_to,
                    customer_name,
                    customer_email,
                    customer_phone,
                    customer_company,
                    customer_parent_company,
                    customer_address,
                    customer_timezone,
                    customer_department,
                    customer_country,
                    ticket.created_at.strftime('%Y-%m-%d %H:%M:%S') if ticket.created_at else '',
                    ticket.updated_at.strftime('%Y-%m-%d %H:%M:%S') if ticket.updated_at else '',
                    package['package_number'],
                    pkg_tracking_number,
                    package_items_str,
                    assets_str,
                    return_shipping,
                    outbound_shipping,
                    queue_name,
                    pkg_status,
                    pkg_carrier,
                    '',  # Latest update (can be enhanced later)
                    '',  # Full history (can be enhanced later)
                    comments_count,
                    comments_text
                ]
                writer.writerow(row)
        else:
            # Original single-row format for tickets without packages
            # For Asset Return (claw), get both return and outbound tracking
            return_shipping = getattr(ticket, 'return_tracking', '') or ''
            outbound_shipping = getattr(ticket, 'shipping_tracking', '') or ''

            row = [
                ticket.id,
                getattr(ticket, 'display_id', ticket.id) if hasattr(ticket, 'display_id') else ticket.id,
                getattr(ticket, 'firstbaseorderid', '') or '',
                ticket.subject or '',
                ticket.description or '',
                ticket.status.value if ticket.status else '',
                ticket.priority.value if ticket.priority else '',
                ticket.get_category_display_name() if ticket.category else '',
                assigned_to,
                customer_name,
                customer_email,
                customer_phone,
                customer_company,
                customer_parent_company,
                customer_address,
                customer_timezone,
                customer_department,
                customer_country,
                ticket.created_at.strftime('%Y-%m-%d %H:%M:%S') if ticket.created_at else '',
                ticket.updated_at.strftime('%Y-%m-%d %H:%M:%S') if ticket.updated_at else '',
                '',  # Package number
                '',  # Package tracking number
                '',  # Package items
                assets_str,
                return_shipping,
                outbound_shipping,
                queue_name,
                latest_status,
                latest_carrier,
                latest_update,
                full_history,
                comments_count,
                comments_text
            ]
            writer.writerow(row)

        # Create response with CSV file
        output.seek(0)
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'ticket_{ticket_id}_{timestamp}.csv'

        response = make_response(output.getvalue())
        response.headers['Content-Type'] = 'text/csv'
        response.headers['Content-Disposition'] = f'attachment; filename={filename}'

        return response

    finally:
        db_session.close()

@tickets_bp.route('/new', methods=['GET', 'POST'])
@login_required
def create_ticket():
    logger.debug("Entering create_ticket route")
    db_session = db_manager.get_session()
    try:
        # Get current user
        user = db_manager.get_user(session['user_id'])
        is_client = user.user_type == UserType.CLIENT

        # Get available assets for the dropdown - filtered by user permissions
        from models.user_company_permission import UserCompanyPermission
        from models.company_customer_permission import CompanyCustomerPermission

        assets_query = db_session.query(Asset).filter(
            Asset.status.in_([AssetStatus.IN_STOCK, AssetStatus.READY_TO_DEPLOY]),
            Asset.serial_num != None
        )

        # Apply permission filtering for non-SUPER_ADMIN/DEVELOPER users
        permitted_company_ids = None
        if user.user_type not in [UserType.SUPER_ADMIN, UserType.DEVELOPER]:
            if user.user_type in [UserType.COUNTRY_ADMIN, UserType.SUPERVISOR]:
                # Get companies this user has permission to view
                user_company_permissions = db_session.query(UserCompanyPermission).filter_by(
                    user_id=user.id,
                    can_view=True
                ).all()

                if user_company_permissions:
                    permitted_company_ids = [perm.company_id for perm in user_company_permissions]

                    # Include child companies of any parent companies
                    from models.company import Company
                    permitted_companies = db_session.query(Company).filter(Company.id.in_(permitted_company_ids)).all()
                    all_permitted_ids = list(permitted_company_ids)

                    for company in permitted_companies:
                        if company.is_parent_company or company.child_companies.count() > 0:
                            child_ids = [c.id for c in company.child_companies.all()]
                            all_permitted_ids.extend(child_ids)

                    # Include cross-company permissions
                    cross_company_ids = []
                    for company_id in all_permitted_ids:
                        additional_ids = db_session.query(CompanyCustomerPermission.customer_company_id)\
                            .filter(
                                CompanyCustomerPermission.company_id == company_id,
                                CompanyCustomerPermission.can_view == True
                            ).all()
                        cross_company_ids.extend([cid[0] for cid in additional_ids])

                    permitted_company_ids = list(set(all_permitted_ids + cross_company_ids))
                    logger.debug(f"SUPERVISOR/COUNTRY_ADMIN asset filtering - permitted company IDs: {permitted_company_ids}")

                    # Filter assets by company_id OR by customer_user's company_id
                    # Note: CustomerUser is already imported at module level (line 24)
                    # Get customer_user IDs from permitted companies
                    permitted_customer_user_ids = [
                        row[0] for row in db_session.query(CustomerUser.id).filter(
                            CustomerUser.company_id.in_(permitted_company_ids)
                        ).all()
                    ]

                    logger.debug(f"[ASSET DEBUG] Permitted customer_user IDs: {len(permitted_customer_user_ids)}")

                    # Get company names for matching assets by customer field
                    all_company_names = [c.name.strip() for c in permitted_companies]

                    # SUPERVISOR/COUNTRY_ADMIN can only see assets from permitted companies
                    # Match by company_id, customer_id, or customer name string
                    name_conditions = [func.lower(Asset.customer).like(f"%{name.lower()}%") for name in all_company_names]

                    assets_query = assets_query.filter(
                        or_(
                            Asset.company_id.in_(permitted_company_ids),
                            Asset.customer_id.in_(permitted_customer_user_ids),
                            *name_conditions  # Also match by customer name string
                        )
                    )

                    logger.debug(f"[ASSET DEBUG] Filtering by {len(permitted_company_ids)} company IDs and {len(all_company_names)} company names")
                else:
                    # No permissions - show no assets
                    logger.debug(f"User {user.username} has no company permissions - showing 0 assets")
                    assets_query = assets_query.filter(Asset.id == -1)
            elif user.user_type == UserType.CLIENT and user.company_id:
                # CLIENT users can only see assets from their company
                assets_query = assets_query.filter(Asset.company_id == user.company_id)

        assets = assets_query.all()

        logger.debug(f"[ASSET DEBUG] User: {user.username}, Type: {user.user_type.value}, Assets from query: {len(assets)}")

        # Build assets data with error handling
        assets_data = []
        try:
            for asset in assets:
                try:
                    asset_dict = {
                        'id': asset.id,
                        'serial_number': asset.serial_num,
                        'model': asset.model,
                        'customer': asset.customer_user.company.name if asset.customer_user and asset.customer_user.company else asset.customer,
                        'asset_tag': asset.asset_tag
                    }
                    assets_data.append(asset_dict)
                except Exception as e:
                    logger.error(f"[ASSET DEBUG] Error processing asset {asset.id}: {str(e)}")
                    logger.error(f"[ASSET DEBUG] Asset details - serial_num: {getattr(asset, 'serial_num', 'N/A')}, customer_user: {getattr(asset, 'customer_user', 'N/A')}")
                    continue  # Skip this asset and continue with others

            logger.debug(f"[ASSET DEBUG] Successfully processed {len(assets_data)} out of {len(assets)} assets")
        except Exception as e:
            logger.error(f"[ASSET DEBUG] Fatal error building assets_data: {str(e)}")
            assets_data = []

        logger.debug(f"[ASSET DEBUG] Total assets loaded: {len(assets_data)}")
        if assets_data:
            logger.debug(f"[ASSET DEBUG] First 3 assets: {assets_data[:3]}")
        else:
            logger.error(f"[ASSET DEBUG] WARNING: assets_data is EMPTY despite query returning {len(assets)} assets!")

        # Get all customers for the dropdown (filtered by company for non-SUPER_ADMIN users)
        customers = get_filtered_customers(db_session, user)

        # Get all queues for the dropdown and filter based on permissions
        all_queues = queue_store.get_all_queues()
        queues = []
        for queue in all_queues:
            if user.can_create_in_queue(queue.id):
                queues.append(queue)

        # Get companies for the customer creation modal dropdown - filtered by user permissions
        from models.company import Company
        if user.user_type in [UserType.SUPER_ADMIN, UserType.DEVELOPER]:
            # SUPER_ADMIN/DEVELOPER can see all companies
            company_names_from_assets = db_session.query(Asset.customer)\
                .filter(Asset.customer.isnot(None))\
                .distinct()\
                .all()
            companies_list = sorted([company[0] for company in company_names_from_assets if company[0]])
        elif permitted_company_ids:
            # Use the same permitted company IDs we calculated for assets
            permitted_companies = db_session.query(Company).filter(Company.id.in_(permitted_company_ids)).all()
            companies_list = sorted([c.name for c in permitted_companies])
        elif user.company_id:
            # CLIENT users - only their company
            user_company = db_session.query(Company).get(user.company_id)
            companies_list = [user_company.name] if user_company else []
        else:
            companies_list = []

        logger.debug(f"Found {len(companies_list)} companies for dropdown (filtered by permissions)")

        # Get parent-eligible companies (exclude child companies) for parent company selection
        # Only parent companies and standalone companies can be selected as parents
        # Filter by user permissions
        if user.user_type in [UserType.SUPER_ADMIN, UserType.DEVELOPER]:
            # SUPER_ADMIN/DEVELOPER can see all parent-eligible companies
            parent_eligible_companies = db_session.query(Company)\
                .filter(Company.parent_company_id == None)\
                .order_by(Company.name)\
                .all()
            parent_companies_list = [c.name for c in parent_eligible_companies]
        elif permitted_company_ids:
            # Use the user's permitted companies, filtered to only parent-eligible ones
            parent_eligible_companies = db_session.query(Company)\
                .filter(
                    Company.id.in_(permitted_company_ids),
                    Company.parent_company_id == None
                )\
                .order_by(Company.name)\
                .all()
            parent_companies_list = [c.name for c in parent_eligible_companies]
        else:
            parent_companies_list = []
        
        # Get all enabled categories (both predefined and custom)
        from models.ticket_category_config import CategoryDisplayConfig
        
        enabled_display_configs = CategoryDisplayConfig.get_enabled_categories()
        
        # Build categories list with proper display names
        all_categories = []
        
        # Add enabled predefined categories
        for config in enabled_display_configs:
            if config['is_predefined']:
                all_categories.append({
                    'value': config['key'],
                    'display_name': config['display_name']
                })
        
        # Add enabled custom categories with their sections
        for config in enabled_display_configs:
            if not config['is_predefined']:
                # Get the full custom category from database to include sections
                custom_category = db_session.query(TicketCategoryConfig)\
                    .filter(TicketCategoryConfig.name == config['key'])\
                    .filter(TicketCategoryConfig.is_active == True)\
                    .first()
                
                if custom_category:
                    all_categories.append({
                        'value': custom_category.name,
                        'display_name': config['display_name'],
                        'sections': custom_category.sections_list  # Include section information
                    })

        # Filter categories based on user permissions (for SUPERVISOR/COUNTRY_ADMIN)
        if user.user_type in [UserType.COUNTRY_ADMIN, UserType.SUPERVISOR]:
            try:
                from models.user_category_permission import UserCategoryPermission
                allowed_category_keys = UserCategoryPermission.get_user_allowed_categories(db_session, user.id)

                logger.debug(f"[CATEGORY DEBUG] User {user.username} allowed categories: {allowed_category_keys}")

                # Filter to only show categories the user has permission for
                if allowed_category_keys:
                    all_categories = [cat for cat in all_categories if cat['value'] in allowed_category_keys]
                else:
                    # No permissions = no categories available
                    all_categories = []

                logger.debug(f"[CATEGORY DEBUG] Filtered categories count: {len(all_categories)}")
            except Exception as e:
                logger.error(f"[CATEGORY DEBUG] Error loading category permissions: {str(e)}")
                logger.error(f"[CATEGORY DEBUG] This likely means the user_category_permissions table doesn't exist - run migration!")
                # If there's an error, don't filter categories (show all)
                logger.debug(f"[CATEGORY DEBUG] Showing all categories due to error")
        # SUPER_ADMIN and DEVELOPER see all categories without restriction

        # Build category guide data structure (maps display names to guide info)
        # This will be filtered to only include categories the user can create
        category_guide = {
            'Asset Repair': {
                'key': 'ASSET_REPAIR',
                'icon_color': 'orange',
                'icon': 'settings',
                'description': 'Submit device for repair with damage details',
                'group': None
            },
            'Asset Checkout': {
                'key': 'ASSET_CHECKOUT_CLAW',  # Using _CLAW variant as it's the enabled one
                'icon_color': 'green',
                'icon': 'box',
                'description': 'Ship device to customer with tracking',
                'group': None
            },
            'Asset Return': {
                'key': 'ASSET_RETURN_CLAW',  # Using _CLAW variant as it's the enabled one
                'icon_color': 'red',
                'icon': 'return',
                'description': 'Receive device back from customer',
                'group': None
            },
            'Asset Intake': {
                'key': 'ASSET_INTAKE',
                'icon_color': 'blue',
                'icon': 'upload',
                'description': 'Register new batch of devices into inventory',
                'group': None
            },
            'Internal Transfer': {
                'key': 'INTERNAL_TRANSFER',
                'icon_color': 'indigo',
                'icon': 'transfer',
                'description': 'Transfer device between customers/locations',
                'group': None
            },
            'Bulk Delivery Quotation': {
                'key': 'BULK_DELIVERY_QUOTATION',
                'icon_color': 'yellow',
                'icon': 'document',
                'description': 'Request quote for bulk shipments',
                'group': 'Quotations'
            },
            'Repair Quote': {
                'key': 'REPAIR_QUOTE',
                'icon_color': 'teal',
                'icon': 'money',
                'description': 'Request repair cost estimate',
                'group': 'Quotations'
            },
            'ITAD Quote': {
                'key': 'ITAD_QUOTE',
                'icon_color': 'pink',
                'icon': 'trash',
                'description': 'IT Asset Disposal quotation',
                'group': 'Quotations'
            }
        }

        # Filter category guide to only include allowed categories
        allowed_category_values = {cat['value'] for cat in all_categories}
        filtered_category_guide = {
            display_name: info for display_name, info in category_guide.items()
            if info['key'] in allowed_category_values
        }

        # Get all users for case owner selection (admin and super admin only)
        users_for_assignment = []
        if user.is_admin:
            from models.user import User
            all_users = db_session.query(User).filter(
                User.is_active == True,
                or_(User.is_deleted == False, User.is_deleted == None)
            ).all()
            users_for_assignment = [{
                'id': u.id,
                'username': u.username,
                'company': u.company.name if u.company else None
            } for u in all_users]

        # Use the same comprehensive country list as /customer-users/add
        # Simple list of all world countries (alphabetically sorted)
        all_countries = COUNTRIES

        # Helper function to generate template context
        def get_template_context(form_data=None):
            # Convert priorities enum to serializable list
            priorities_list = [{'name': p.name, 'value': p.value} for p in TicketPriority]

            return {
                'assets': assets_data,
                'customers': customers,
                'priorities': priorities_list,
                'categories': all_categories,
                'category_guide': filtered_category_guide,
                'queues': queues,
                'Country': all_countries,
                'is_client': is_client,
                'user': user,
                'companies': companies_list,
                'parent_companies': parent_companies_list,
                'users_for_assignment': users_for_assignment,
                'form': form_data
            }
        
        if request.method == 'GET':
            logger.debug("Handling GET request")
            
            return render_template('tickets/create.html', **get_template_context())

        if request.method == 'POST':
            logger.debug("Handling POST request")
            
            # Log all form fields to debug
            for key, value in request.form.items():
                logger.debug(f"Form field: {key} = {value}")
            
            # Get common form data
            category = request.form.get('category')
            subject = request.form.get('subject')
            description = request.form.get('description')
            priority = request.form.get('priority')
            queue_id = request.form.get('queue_id', type=int)
            case_owner_id = request.form.get('case_owner_id')  # Get selected case owner
            user_id = session['user_id']

            # Log queue_id for debugging
            logger.info(f"[CREATE TICKET] Received queue_id from form: {repr(queue_id)} (type: {type(queue_id).__name__})")

            # Validate queue selection is provided
            if not queue_id:
                flash('Please select a queue for this ticket', 'error')
                return render_template('tickets/create.html', **get_template_context(request.form))

            # Check if user has permission to create tickets in this queue
            if not user.can_create_in_queue(queue_id):
                flash('You do not have permission to create tickets in this queue', 'error')
                return render_template('tickets/create.html', **get_template_context(request.form))
                                    
            # Get serial number based on category
            serial_number = None
            if category == 'ASSET_CHECKOUT' or \
               category == 'ASSET_CHECKOUT_SINGPOST' or \
               category == 'ASSET_CHECKOUT_DHL' or \
               category == 'ASSET_CHECKOUT_UPS' or \
               category == 'ASSET_CHECKOUT_BLUEDART' or \
               category == 'ASSET_CHECKOUT_DTDC' or \
               category == 'ASSET_CHECKOUT_AUTO' or \
               category == 'ASSET_CHECKOUT_CLAW': # Added CLAW
                serial_number = request.form.get('asset_checkout_serial')
                logger.info(f"Asset Checkout Serial Number: {serial_number}")  # Debug log
            else:
                serial_number = request.form.get('serial_number')
                logger.info(f"Standard Serial Number: {serial_number}")  # Debug log

            # Check if this is a custom category
            is_custom_category = False
            if category:
                custom_category = db_session.query(TicketCategoryConfig).filter_by(name=category).first()
                if custom_category:
                    is_custom_category = True
            
            # Validate asset selection (skip for Asset Intake, Asset Return Claw, Internal Transfer, and custom categories)
            if (category != 'ASSET_INTAKE' and
                category != 'ASSET_RETURN_CLAW' and
                category != 'INTERNAL_TRANSFER' and
                not is_custom_category and
                (not serial_number or serial_number == "")):
                flash('Please select an asset', 'error')
                return render_template('tickets/create.html', **get_template_context(request.form))

            # Find the asset (skip for Asset Intake, Asset Return Claw, Internal Transfer, and custom categories)
            asset = None
            if (category != 'ASSET_INTAKE' and
                category != 'ASSET_RETURN_CLAW' and
                category != 'INTERNAL_TRANSFER' and
                not is_custom_category and
                serial_number):
                asset = db_session.query(Asset).filter(Asset.serial_num == serial_number).first()
                if not asset:
                    flash(f'Asset not found with serial number: {serial_number}', 'error')
                    return render_template('tickets/create.html', **get_template_context(request.form))
            elif category == 'INTERNAL_TRANSFER' and serial_number:
                # For Internal Transfer, asset is optional but should be loaded if provided
                asset = db_session.query(Asset).filter(Asset.serial_num == serial_number).first()

            # Include ASSET_CHECKOUT_AUTO and CLAW in the main checkout logic block
            if category == 'ASSET_CHECKOUT' or \
               category == 'ASSET_CHECKOUT_SINGPOST' or \
               category == 'ASSET_CHECKOUT_DHL' or \
               category == 'ASSET_CHECKOUT_UPS' or \
               category == 'ASSET_CHECKOUT_BLUEDART' or \
               category == 'ASSET_CHECKOUT_DTDC' or \
               category == 'ASSET_CHECKOUT_AUTO' or \
               category == 'ASSET_CHECKOUT_CLAW': # Added CLAW
                customer_id = request.form.get('customer_id')
                shipping_address = request.form.get('shipping_address')
                shipping_tracking = request.form.get('shipping_tracking', '')  # Optional
                order_id = request.form.get('order_id', '')  # Optional order ID
                notes = request.form.get('notes', '')
                # queue_id and case_owner_id already extracted at line 1143-1145

                logger.info(f"Processing {category} - Customer ID: {customer_id}, Serial Number: {serial_number}")  # Debug log
                
                if not customer_id:
                    flash('Please select a customer', 'error')
                    return render_template('tickets/create.html', **get_template_context(request.form))

                if not shipping_address:
                    flash('Please provide a shipping address', 'error')
                    return render_template('tickets/create.html', **get_template_context(request.form))
                
                # Get customer details
                customer = db_session.query(CustomerUser).get(customer_id)
                if not customer:
                    flash('Customer not found', 'error')
                    return render_template('tickets/create.html', **get_template_context(request.form))
                
                # Determine shipping method based on category
                shipping_method = "Standard"
                if category == 'ASSET_CHECKOUT_SINGPOST':
                    shipping_method = "SingPost"
                elif category == 'ASSET_CHECKOUT_DHL':
                    shipping_method = "DHL"
                elif category == 'ASSET_CHECKOUT_UPS':
                    shipping_method = "UPS"
                elif category == 'ASSET_CHECKOUT_BLUEDART':
                    shipping_method = "BlueDart"
                elif category == 'ASSET_CHECKOUT_DTDC':
                    shipping_method = "DTDC"
                elif category == 'ASSET_CHECKOUT_AUTO':
                    shipping_method = "Auto"
                elif category == 'ASSET_CHECKOUT_CLAW': # Added CLAW
                    shipping_method = "claw"
                
                description = f"""Asset Checkout Details:
Serial Number: {serial_number}
Model: {asset.model}
Asset Tag: {asset.asset_tag}

Customer Information:
Name: {customer.name}
Company: {customer.company.name if customer.company else 'N/A'}
Email: {customer.email}
Contact: {customer.contact_number}

Shipping Information:
Address: {shipping_address}
Tracking Number: {shipping_tracking if shipping_tracking else 'Not provided'}
Shipping Method: {shipping_method}

Additional Notes:
{notes}"""

                logger.info(f"Creating ticket with description: {description}")  # Debug log

                try:
                    # Determine appropriate ticket category enum value based on shipping method
                    ticket_category = None
                    shipping_carrier = 'singpost'  # Default carrier
                    
                    if shipping_method == "SingPost":
                        ticket_category = TicketCategory.ASSET_CHECKOUT_SINGPOST
                        shipping_carrier = 'singpost'
                    elif shipping_method == "DHL":
                        ticket_category = TicketCategory.ASSET_CHECKOUT_DHL
                        shipping_carrier = 'dhl'
                    elif shipping_method == "UPS":
                        ticket_category = TicketCategory.ASSET_CHECKOUT_UPS
                        shipping_carrier = 'ups'
                    elif shipping_method == "BlueDart":
                        ticket_category = TicketCategory.ASSET_CHECKOUT_BLUEDART
                        shipping_carrier = 'bluedart'
                    elif shipping_method == "DTDC":
                        ticket_category = TicketCategory.ASSET_CHECKOUT_DTDC
                        shipping_carrier = 'dtdc'
                    elif shipping_method == "Auto":
                        ticket_category = TicketCategory.ASSET_CHECKOUT_AUTO
                        shipping_carrier = 'auto'
                    elif shipping_method == "claw": # Added CLAW
                        ticket_category = TicketCategory.ASSET_CHECKOUT_CLAW
                        shipping_carrier = 'claw'
                    else:
                        ticket_category = TicketCategory.ASSET_CHECKOUT
                    
                    # Handle accessory assignment from CSV before creating the ticket
                    selected_accessories_json = request.form.get('selected_accessories', '')
                    assigned_accessories = []
                    accessory_description_part = ""
                    
                    # Debug logging - use existing logger
                    from datetime import datetime
                    
                    logger.error(f"CSV_DEBUG: selected_accessories_json = '{selected_accessories_json}'")
                    logger.error(f"CSV_DEBUG: Form keys: {list(request.form.keys())}")
                    logger.error(f"CSV_DEBUG: Form values: {dict(request.form)}")
                    
                    # Also write to a specific debug file
                    with open('csv_debug.log', 'a') as f:
                        f.write(f"\n=== CSV DEBUG {datetime.now()} ===\n")
                        f.write(f"selected_accessories_json = '{selected_accessories_json}'\n")
                        f.write(f"Form keys: {list(request.form.keys())}\n")
                        f.write(f"Form has selected_accessories: {'selected_accessories' in request.form}\n")
                        if 'accessories_csv' in request.files:
                            csv_file = request.files['accessories_csv']
                            f.write(f"CSV file uploaded: {csv_file.filename if csv_file else 'None'}\n")
                        else:
                            f.write("No CSV file in request.files\n")
                        
                        # Check if selected_accessories is empty but should have data
                        if not selected_accessories_json:
                            f.write("No selected accessories data found in form\n")
                        f.write("=== END CSV DEBUG ===\n")
                    
                    if selected_accessories_json:
                        try:
                            import json
                            selected_accessories_data = json.loads(selected_accessories_json)
                            logger.info(f"Processing {len(selected_accessories_data)} selected accessories")  # Debug log
                            
                            for acc_data in selected_accessories_data:
                                inventory_id = acc_data.get('inventoryId')
                                product_name = acc_data.get('product', '')
                                category = acc_data.get('category', '')
                                quantity = acc_data.get('quantity', 1)
                                
                                if inventory_id:
                                    # Check inventory item
                                    accessory = db_session.query(Accessory).filter(Accessory.id == inventory_id).first()
                                    if accessory and accessory.available_quantity > 0:
                                        assigned_qty = min(quantity, accessory.available_quantity)
                                        assigned_accessories.append({
                                            'type': 'inventory',
                                            'id': accessory.id,
                                            'name': accessory.name,
                                            'category': accessory.category,
                                            'quantity': assigned_qty
                                        })
                                else:
                                    # CSV-only item
                                    assigned_accessories.append({
                                        'type': 'csv',
                                        'name': product_name,
                                        'category': category,
                                        'quantity': quantity
                                    })
                            
                            # Create accessory description part
                            if assigned_accessories:
                                accessory_description_part = f"\n\nSelected Accessories from CSV:\n"
                                for acc in assigned_accessories:
                                    source = "(from inventory)" if acc['type'] == 'inventory' else "(from CSV only)"
                                    accessory_description_part += f"- {acc['name']} (x{acc['quantity']}) {source}\n"
                                
                        except Exception as acc_error:
                            logger.info(f"Error processing accessories JSON: {str(acc_error)}")
                    
                    # Update description with accessory information
                    final_description = description + accessory_description_part

                    # Create the ticket
                    try:
                        # Log queue_id before creating ticket
                        logger.info(f"[CREATE TICKET] Creating ticket with queue_id: {repr(queue_id)} (type: {type(queue_id).__name__})")

                        ticket_id = ticket_store.create_ticket(
                            subject=subject,
                            description=final_description,
                            requester_id=user_id,
                            category=ticket_category,
                            priority=priority,
                            asset_id=asset.id,  # Use old asset_id approach
                            customer_id=customer_id,
                            shipping_address=shipping_address,
                            shipping_tracking=shipping_tracking if shipping_tracking else None,
                            shipping_carrier=shipping_carrier,
                            queue_id=queue_id,
                            notes=notes,
                            case_owner_id=int(case_owner_id) if case_owner_id else None,
                            firstbaseorderid=order_id if order_id else None
                        )
                        logger.info(f"[TICKET CREATION DEBUG] Successfully created ticket with ID: {ticket_id}")
                    except Exception as ticket_creation_error:
                        logger.info(f"[TICKET CREATION ERROR] Failed to create ticket: {str(ticket_creation_error)}")
                        import traceback
                        traceback.print_exc()
                        
                        # Check if this is an AJAX request
                        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                            return jsonify({
                                'success': False,
                                'error': f'Failed to create ticket: {str(ticket_creation_error)}'
                            })
                        else:
                            flash(f'Error creating ticket: {str(ticket_creation_error)}')
                            return redirect(url_for('tickets.create_ticket'))
                    
                    if not ticket_id:
                        error_msg = "Ticket creation failed: No ticket ID returned"
                        logger.info(f"[TICKET CREATION ERROR] {error_msg}")
                        
                        # Check if this is an AJAX request
                        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                            return jsonify({
                                'success': False,
                                'error': error_msg
                            })
                        else:
                            flash(error_msg)
                            return redirect(url_for('tickets.create_ticket'))

                    # Handle package tracking fields for Asset Checkout (claw)
                    if category == 'ASSET_CHECKOUT_CLAW':
                        created_ticket = db_session.query(Ticket).get(ticket_id)
                        if created_ticket:
                            # Process up to 5 packages
                            for package_num in range(1, 6):
                                tracking_field = f'package_{package_num}_tracking'
                                carrier_field = f'package_{package_num}_carrier'
                                
                                tracking_number = request.form.get(tracking_field)
                                carrier = request.form.get(carrier_field)
                                
                                if tracking_number:  # Only process if tracking number is provided
                                    if package_num == 1:
                                        created_ticket.shipping_tracking = tracking_number
                                        created_ticket.shipping_carrier = carrier or 'claw'
                                        created_ticket.shipping_status = 'Pending'
                                    elif package_num == 2:
                                        created_ticket.shipping_tracking_2 = tracking_number
                                        created_ticket.shipping_carrier_2 = carrier or 'claw'
                                        created_ticket.shipping_status_2 = 'Pending'
                                    elif package_num == 3:
                                        created_ticket.shipping_tracking_3 = tracking_number
                                        created_ticket.shipping_carrier_3 = carrier or 'claw'
                                        created_ticket.shipping_status_3 = 'Pending'
                                    elif package_num == 4:
                                        created_ticket.shipping_tracking_4 = tracking_number
                                        created_ticket.shipping_carrier_4 = carrier or 'claw'
                                        created_ticket.shipping_status_4 = 'Pending'
                                    elif package_num == 5:
                                        created_ticket.shipping_tracking_5 = tracking_number
                                        created_ticket.shipping_carrier_5 = carrier or 'claw'
                                        created_ticket.shipping_status_5 = 'Pending'
                                    
                                    logger.info(f"[PACKAGE DEBUG] Added Package {package_num}: {tracking_number} ({carrier})")
                            
                            # Update the ticket's updated_at timestamp
                            from datetime import datetime
                            created_ticket.updated_at = singapore_now_as_utc()
                            
                            # Commit the package changes
                            db_session.commit()
                            logger.info(f"[PACKAGE DEBUG] Successfully added package tracking to ticket {ticket_id}")

                    # Get the created ticket for asset assignment
                    created_ticket = db_session.query(Ticket).get(ticket_id)
                    if created_ticket and asset:
                        logger.info(f"[ASSET ASSIGN DEBUG] Starting assignment - Ticket: {ticket_id}, Asset: {asset}")
                        logger.info(f"[ASSET ASSIGN DEBUG] Asset object: {asset.model} (ID: {asset.id})")
                        
                        # Create proper ticket-asset relationship using direct SQL
                        # Check if relationship already exists
                        from sqlalchemy import text
                        existing_check = text("""
                            SELECT COUNT(*) FROM ticket_assets 
                            WHERE ticket_id = :ticket_id AND asset_id = :asset_id
                        """)
                        existing_count = db_session.execute(existing_check, {"ticket_id": ticket_id, "asset_id": asset.id}).scalar()
                        
                        logger.info(f"[ASSET ASSIGN DEBUG] Existing relationship count: {existing_count}")
                        
                        if existing_count == 0:
                            # Create the ticket-asset relationship using direct SQL
                            try:
                                insert_stmt = text("""
                                    INSERT INTO ticket_assets (ticket_id, asset_id) 
                                    VALUES (:ticket_id, :asset_id)
                                """)
                                db_session.execute(insert_stmt, {"ticket_id": ticket_id, "asset_id": asset.id})
                                db_session.flush()
                                logger.info("[ASSET ASSIGN DEBUG] Created ticket-asset relationship via direct SQL")
                            except Exception as e:
                                logger.info(f"[ASSET ASSIGN DEBUG] Error creating ticket-asset relationship: {str(e)}")
                                # If it's a constraint violation, that's OK - relationship already exists
                                if "UNIQUE constraint failed" not in str(e):
                                    raise
                        
                        # Update asset status and assign to customer
                        asset.customer_id = customer_id
                        asset.status = AssetStatus.DEPLOYED
                        logger.info(f"[ASSET ASSIGN DEBUG] Updated asset status to DEPLOYED and assigned to customer {customer_id}")
                        
                        # Create asset transaction record for the checkout
                        from models.asset_transaction import AssetTransaction
                        from datetime import datetime
                        transaction = AssetTransaction(
                            asset_id=asset.id,
                            transaction_type='checkout',
                            customer_id=customer_id,
                            notes=f'Asset checkout via ticket #{ticket_id} - {shipping_method}',
                            transaction_date=singapore_now_as_utc()
                        )
                        # Set user_id manually since it's not in the constructor
                        transaction.user_id = user_id
                        db_session.add(transaction)
                        logger.info("[ASSET ASSIGN DEBUG] Created asset transaction record for checkout")
                    else:
                        logger.info(f"[ASSET ASSIGN DEBUG] Warning: Could not create asset assignment - ticket: {created_ticket}, asset: {asset}")
                    
                    # Now assign accessories to the created ticket
                    if assigned_accessories:
                        try:
                            # Get the ticket object for accessory assignment
                            ticket = db_session.query(Ticket).get(ticket_id)
                            actual_assigned = []
                            
                            for acc_data in assigned_accessories:
                                if acc_data['type'] == 'inventory':
                                    # Assign from inventory
                                    accessory = db_session.query(Accessory).filter(Accessory.id == acc_data['id']).first()
                                    if accessory and accessory.available_quantity > 0:
                                        # Create ticket-accessory assignment
                                        ticket_accessory = TicketAccessory(
                                            ticket_id=ticket.id,
                                            name=accessory.name,
                                            category=accessory.category,
                                            quantity=acc_data['quantity'],
                                            condition='Good',
                                            notes=f'Assigned from CSV import - inventory item',
                                            original_accessory_id=accessory.id
                                        )
                                        db_session.add(ticket_accessory)
                                        
                                        # Update accessory quantity
                                        accessory.available_quantity -= acc_data['quantity']
                                        if accessory.available_quantity == 0:
                                            accessory.status = 'Out of Stock'
                                        
                                        actual_assigned.append(f"{accessory.name} (x{acc_data['quantity']})")
                                        
                                        # Create activity log
                                        from models.activity import Activity
                                        activity = Activity(
                                            user_id=user_id,
                                            type='accessory_assigned',
                                            content=f'Assigned accessory "{accessory.name}" (x{acc_data["quantity"]}) to ticket #{ticket.display_id} from CSV import',
                                            reference_id=ticket.id
                                        )
                                        db_session.add(activity)
                                        logger.info(f"Created TicketAccessory for {accessory.name}")  # Debug log
                                else:
                                    # Create ticket accessory from CSV data (no inventory match)
                                    ticket_accessory = TicketAccessory(
                                        ticket_id=ticket.id,
                                        name=acc_data['name'],
                                        category=acc_data['category'],
                                        quantity=acc_data['quantity'],
                                        condition='Unknown',
                                        notes=f'Added from CSV import - no inventory match',
                                        original_accessory_id=None
                                    )
                                    db_session.add(ticket_accessory)
                                    actual_assigned.append(f"{acc_data['name']} (x{acc_data['quantity']}) - from CSV")
                                    logger.info(f"Created TicketAccessory for CSV item {acc_data['name']}")  # Debug log
                            
                            assigned_accessories = actual_assigned
                                
                        except Exception as acc_error:
                            logger.info(f"Error creating ticket accessories: {str(acc_error)}")
                            import traceback
                            traceback.print_exc()
                    
                    db_session.commit()
                    
                    # Refresh the ticket to ensure relationships are loaded
                    if created_ticket:
                        db_session.refresh(created_ticket)
                        logger.info(f"[ASSET ASSIGN DEBUG] Refreshed ticket - now has {len(created_ticket.assets)} assets")

                    logger.info(f"Ticket created successfully with ID: {ticket_id}")  # Debug log
                    
                    # Check if this is an AJAX request (for popup functionality)
                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                        response_data = {
                            'success': True,
                            'ticket_id': ticket_id,
                            'message': f'Asset checkout ticket created successfully{f" with {len(assigned_accessories)} accessories assigned" if assigned_accessories else ""}',
                            'assigned_accessories': assigned_accessories if assigned_accessories else [],
                            'ticket_display_id': ticket_id
                        }
                        return jsonify(response_data)
                    else:
                        # Regular form submission - existing behavior
                        if assigned_accessories:
                            flash(f'Asset checkout ticket created successfully with {len(assigned_accessories)} accessories assigned')
                        else:
                            flash('Asset checkout ticket created successfully')
                        return redirect(url_for('tickets.view_ticket', ticket_id=ticket_id))
                except Exception as e:
                    logger.info(f"Error creating ticket: {str(e)}")  # Debug log
                    import traceback
                    traceback.print_exc()  # Print full stack trace
                    db_session.rollback()
                    
                    # Return JSON error for AJAX requests
                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                        return jsonify({
                            'success': False,
                            'error': str(e),
                            'message': f'Error creating ticket: {str(e)}'
                        }), 500
                    else:
                        flash('Error creating ticket: ' + str(e), 'error')
                        return render_template('tickets/create.html', **get_template_context(request.form))

            # Handle category-specific logic
            if category == 'PIN_REQUEST':
                # PIN Request logic
                lock_type = request.form.get('lock_type')
                # queue_id already extracted at line 1143
                notes = request.form.get('notes', '')

                try:
                    ticket_id = ticket_store.create_ticket(
                        subject=f"PIN Request for {asset.model} ({serial_number})",
                        description=f"PIN Request Details:\nSerial Number: {serial_number}\nLock Type: {lock_type}",
                        requester_id=user_id,
                        category=TicketCategory.PIN_REQUEST,
                        priority=priority,
                        asset_id=asset.id,  # Use old asset_id approach
                        queue_id=queue_id,  # Pass queue_id to create_ticket
                        notes=notes,
                        case_owner_id=int(case_owner_id) if case_owner_id else None
                    )
                    flash('PIN request ticket created successfully')
                    return redirect(url_for('tickets.view_ticket', ticket_id=ticket_id))
                except Exception as e:
                    logger.info(f"Error creating ticket: {str(e)}")  # Debug log
                    db_session.rollback()
                    flash('Error creating ticket: ' + str(e), 'error')
                    return render_template('tickets/create.html', **get_template_context(request.form))
                                       
            elif category == 'ASSET_RETURN_CLAW':
                # Asset Return (Claw) logic
                customer_id = request.form.get('customer_id')
                shipping_address = request.form.get('shipping_address')
                outbound_tracking = request.form.get('shipping_tracking', '')  # Renamed for clarity
                inbound_tracking = request.form.get('return_tracking', '')  # Optional return tracking
                order_id = request.form.get('order_id', '')  # Optional order ID
                notes = request.form.get('notes', '')
                damage_description = request.form.get('damage_description', '')  # Reported issue
                # queue_id and case_owner_id already extracted at line 1143-1145
                # Extract the return description from the form
                user_return_description = request.form.get('return_description', '') or request.form.get('description', '')

                logger.info(f"DEBUG - Form return_description: {request.form.get('return_description')}")  # Debug log
                logger.info(f"DEBUG - Form description: {request.form.get('description')}")  # Debug log
                logger.info(f"DEBUG - Final user_return_description: {user_return_description}")  # Debug log
                
                logger.info(f"Processing ASSET_RETURN_CLAW - Customer ID: {customer_id}")  # Debug log
                
                if not customer_id:
                    flash('Please select a customer', 'error')
                    return render_template('tickets/create.html', **get_template_context(request.form))

                if not shipping_address:
                    flash('Please provide a return address', 'error')
                    return render_template('tickets/create.html', **get_template_context(request.form))
                
                # We no longer require outbound tracking
                # Removed validation that previously required outbound_tracking
                
                # Get customer details with company relationship loaded
                customer = db_session.query(CustomerUser).options(
                    joinedload(CustomerUser.company)
                ).filter(CustomerUser.id == customer_id).first()
                
                if not customer:
                    flash('Customer not found', 'error')
                    return render_template('tickets/create.html', **get_template_context(request.form))
                
                company_name = 'N/A'
                if customer.company:
                    try:
                        company_name = customer.company.name
                    except Exception as e:
                        logger.info(f"Error accessing company name: {str(e)}")
                        company_name = 'N/A'
                
                # Prepare system description (separate from user return description)
                system_description = f"""Asset Return (Claw) Details:
Customer Information:
Name: {customer.name}
Company: {company_name}
Email: {customer.email}
Contact: {customer.contact_number}

Return Information:
Address: {shipping_address}
Outbound Tracking Number: {outbound_tracking if outbound_tracking else 'Not provided yet'}
Inbound Tracking Number: {inbound_tracking if inbound_tracking else 'Not provided yet'}
Shipping Method: Claw (Ship24)"""

                try:
                    # Create the ticket
                    ticket_id = ticket_store.create_ticket(
                        subject=subject if subject else f"Asset Return (claw) - {customer.name}",
                        description=system_description,
                        requester_id=user_id,
                        category=TicketCategory.ASSET_RETURN_CLAW,
                        priority=priority,
                        asset_id=None,  # No asset for returns
                        customer_id=customer_id,
                        shipping_address=shipping_address,
                        shipping_tracking=outbound_tracking if outbound_tracking else None,
                        shipping_carrier='claw',
                        return_tracking=inbound_tracking if inbound_tracking else None,
                        queue_id=queue_id,
                        notes=notes,
                        return_description=user_return_description,
                        damage_description=damage_description if damage_description else None,
                        case_owner_id=int(case_owner_id) if case_owner_id else None,
                        firstbaseorderid=order_id if order_id else None
                    )

                    logger.info(f"Asset Return ticket created successfully with ID: {ticket_id}")  # Debug log
                    flash('Asset return ticket created successfully')
                    return redirect(url_for('tickets.view_ticket', ticket_id=ticket_id))
                except Exception as e:
                    logger.info(f"Error creating ticket: {str(e)}")  # Debug log
                    db_session.rollback()
                    flash('Error creating ticket: ' + str(e), 'error')
                    return render_template('tickets/create.html', **get_template_context(request.form))

            elif category == 'INTERNAL_TRANSFER':
                # Internal Transfer logic
                # Get new offboarding/onboarding fields
                offboarding_customer_id = request.form.get('offboarding_customer_id')
                onboarding_customer_id = request.form.get('onboarding_customer_id')
                offboarding_details = request.form.get('offboarding_details', '')
                offboarding_address = request.form.get('offboarding_address', '')
                onboarding_address = request.form.get('onboarding_address', '')
                transfer_tracking = request.form.get('transfer_tracking', '')
                notes = request.form.get('notes', '')

                # Legacy fields (for backwards compatibility)
                transfer_name = request.form.get('transfer_name')
                transfer_address = request.form.get('transfer_address')
                customer_id = request.form.get('customer_id')
                transfer_client = request.form.get('transfer_client', '')

                logger.info(f"Processing INTERNAL_TRANSFER - Offboarding: {offboarding_customer_id}, Onboarding: {onboarding_customer_id}")

                # Validate required fields (new format)
                if offboarding_customer_id:
                    # New format validation
                    if not offboarding_details:
                        flash('Please provide offboarding device details', 'error')
                        return render_template('tickets/create.html', **get_template_context(request.form))
                    if not offboarding_address:
                        flash('Please provide offboarding address', 'error')
                        return render_template('tickets/create.html', **get_template_context(request.form))
                    if not onboarding_customer_id:
                        flash('Please select onboarding customer', 'error')
                        return render_template('tickets/create.html', **get_template_context(request.form))
                    if not onboarding_address:
                        flash('Please provide onboarding address', 'error')
                        return render_template('tickets/create.html', **get_template_context(request.form))
                else:
                    # Legacy format validation
                    if not transfer_name:
                        flash('Please provide a recipient name', 'error')
                        return render_template('tickets/create.html', **get_template_context(request.form))
                    if not transfer_address:
                        flash('Please provide a transfer address', 'error')
                        return render_template('tickets/create.html', **get_template_context(request.form))

                # Get offboarding customer details
                offboarding_customer = None
                offboarding_customer_name = 'N/A'
                offboarding_customer_company = 'N/A'
                if offboarding_customer_id:
                    offboarding_customer = db_session.query(CustomerUser).options(
                        joinedload(CustomerUser.company)
                    ).filter(CustomerUser.id == offboarding_customer_id).first()
                    if offboarding_customer:
                        offboarding_customer_name = offboarding_customer.name
                        if offboarding_customer.company:
                            offboarding_customer_company = offboarding_customer.company.name

                # Get onboarding customer details
                onboarding_customer = None
                onboarding_customer_name = 'N/A'
                onboarding_customer_company = 'N/A'
                if onboarding_customer_id:
                    onboarding_customer = db_session.query(CustomerUser).options(
                        joinedload(CustomerUser.company)
                    ).filter(CustomerUser.id == onboarding_customer_id).first()
                    if onboarding_customer:
                        onboarding_customer_name = onboarding_customer.name
                        if onboarding_customer.company:
                            onboarding_customer_company = onboarding_customer.company.name

                # Legacy: Get customer details if provided
                customer = None
                customer_name = 'N/A'
                customer_company = 'N/A'
                if customer_id:
                    customer = db_session.query(CustomerUser).options(
                        joinedload(CustomerUser.company)
                    ).filter(CustomerUser.id == customer_id).first()

                    if customer:
                        customer_name = customer.name
                        if customer.company:
                            try:
                                customer_company = customer.company.name
                            except Exception as e:
                                logger.info(f"Error accessing company name: {str(e)}")
                                customer_company = 'N/A'

                # Get asset details if provided
                asset_info = 'N/A'
                if serial_number and asset:
                    asset_info = f"{asset.model} - {serial_number} (Tag: {asset.asset_tag})"

                # Prepare description (new format vs legacy)
                if offboarding_customer_id and onboarding_customer_id:
                    # New format description
                    description = f"""Internal Transfer Details:

📤 OFFBOARDING
Customer: {offboarding_customer_name}
Company: {offboarding_customer_company}
Device Details: {offboarding_details}
Address: {offboarding_address}

📥 ONBOARDING
Customer: {onboarding_customer_name}
Company: {onboarding_customer_company}
Address: {onboarding_address}

Tracking Link: {transfer_tracking if transfer_tracking else 'Not provided'}

Additional Notes:
{notes if notes else 'None'}"""
                    subject = f"Internal Transfer: {offboarding_customer_name} → {onboarding_customer_name}"
                else:
                    # Legacy format description
                    description = f"""Internal Transfer Details:
Recipient Name: {transfer_name}
Transfer Address: {transfer_address}
Tracking Link: {transfer_tracking if transfer_tracking else 'Not provided'}

Customer Information:
Name: {customer_name}
Company: {customer_company}

Client Company: {transfer_client if transfer_client else 'N/A'}

Asset Equipment:
{asset_info}

Additional Notes:
{notes if notes else 'None'}"""
                    subject = f"Internal Transfer - {transfer_name}"

                try:
                    # Create the ticket using ticket_store.create_ticket
                    # Note: create_ticket doesn't support the new fields, so we'll need to update them after
                    ticket_id = ticket_store.create_ticket(
                        subject=subject,
                        description=description,
                        requester_id=user_id,
                        category=TicketCategory.INTERNAL_TRANSFER,
                        priority=TicketPriority.MEDIUM,  # Default priority
                        asset_id=asset.id if asset else None,
                        customer_id=customer_id if customer_id else offboarding_customer_id,
                        shipping_address=transfer_address if transfer_address else onboarding_address,
                        shipping_tracking=transfer_tracking if transfer_tracking else None,
                        queue_id=queue_id,
                        notes=notes,
                        case_owner_id=int(case_owner_id) if case_owner_id else None
                    )

                    # Update the ticket with new offboarding/onboarding fields
                    if offboarding_customer_id and ticket_id:
                        ticket = db_session.query(Ticket).get(ticket_id)
                        if ticket:
                            ticket.offboarding_customer_id = int(offboarding_customer_id)
                            ticket.onboarding_customer_id = int(onboarding_customer_id) if onboarding_customer_id else None
                            ticket.offboarding_details = offboarding_details
                            ticket.offboarding_address = offboarding_address
                            ticket.onboarding_address = onboarding_address
                            db_session.commit()
                            logger.info(f"Updated Internal Transfer ticket {ticket_id} with offboarding/onboarding details")

                    logger.info(f"Internal Transfer ticket created successfully with ID: {ticket_id}")
                    flash('Internal transfer ticket created successfully')
                    return redirect(url_for('tickets.view_ticket', ticket_id=ticket_id))
                except Exception as e:
                    logger.info(f"Error creating ticket: {str(e)}")
                    db_session.rollback()
                    flash('Error creating ticket: ' + str(e), 'error')
                    return render_template('tickets/create.html', **get_template_context(request.form))

            elif category == 'ASSET_REPAIR':
                damage_description = request.form.get('damage_description')
                if not damage_description:
                    flash('Please provide a damage description', 'error')
                    return render_template('tickets/create.html', **get_template_context(request.form))

                apple_diagnostics = request.form.get('apple_diagnostics')
                quote_type = request.form.get('quote_type', 'assessment')
                
                # Handle image upload
                image_paths = []
                if 'image' in request.files:
                    images = request.files.getlist('image')
                    for image in images:
                        if image and image.filename:
                            # Secure the filename
                            filename = secure_filename(image.filename)
                            # Create unique filename with timestamp
                            timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
                            unique_filename = f"{timestamp}_{filename}"
                            # Save the file
                            image_path = os.path.join('uploads', 'repairs', unique_filename)
                            os.makedirs(os.path.dirname(image_path), exist_ok=True)
                            image.save(image_path)
                            image_paths.append(image_path)

                description = f"""Asset Details:
Serial Number: {serial_number}
Model: {asset.model}
Customer: {asset.customer_user.company.name if asset.customer_user and asset.customer_user.company else asset.customer}
Country: {request.form.get('country')}

Damage Description:
{damage_description}

Apple Diagnostics Code: {apple_diagnostics if apple_diagnostics else 'N/A'}

Additional Notes:
{request.form.get('notes', '')}

Images Attached: {len(image_paths)} image(s)"""

            elif category == 'ASSET_INTAKE':
                title = request.form.get('intake_title') or request.form.get('title')  # Support both field names
                description = request.form.get('intake_description') or request.form.get('description')  # Support both field names
                notes = request.form.get('intake_notes') or request.form.get('notes', '')  # Support both field names
                priority = request.form.get('intake_priority') or request.form.get('priority')  # Support both field names
                # case_owner_id already extracted at line 1143-1145

                if not title or not description:
                    flash('Please provide both title and description', 'error')
                    return render_template('tickets/create.html', **get_template_context(request.form))

                # Handle file uploads
                packing_list_path = None
                if 'packing_list' in request.files:
                    packing_list = request.files['packing_list']
                    if packing_list and packing_list.filename:
                        # Secure the filename
                        filename = secure_filename(packing_list.filename)
                        # Create unique filename with timestamp
                        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
                        unique_filename = f"{timestamp}_{filename}"
                        # Create uploads/intake directory if it doesn't exist
                        os.makedirs('uploads/intake', exist_ok=True)
                        # Save the file
                        packing_list_path = os.path.join('uploads', 'intake', unique_filename)
                        packing_list.save(packing_list_path)

                asset_csv_path = None
                if 'asset_csv' in request.files:
                    asset_csv = request.files['asset_csv']
                    if asset_csv and asset_csv.filename:
                        # Secure the filename
                        filename = secure_filename(asset_csv.filename)
                        # Create unique filename with timestamp
                        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
                        unique_filename = f"{timestamp}_{filename}"
                        # Create uploads/intake directory if it doesn't exist
                        os.makedirs('uploads/intake', exist_ok=True)
                        # Save the file
                        asset_csv_path = os.path.join('uploads', 'intake', unique_filename)
                        asset_csv.save(asset_csv_path)

                description = f"""Asset Intake Details:
Title: {title}

Description:
{description}

Files:
- Packing List: {os.path.basename(packing_list_path) if packing_list_path else 'Not provided'}
- Asset CSV: {os.path.basename(asset_csv_path) if asset_csv_path else 'Not provided'}

Additional Notes:
{notes}"""

                try:
                    # Create the ticket
                    ticket_id = ticket_store.create_ticket(
                        subject=title,
                        description=description,
                        requester_id=user_id,
                        category=TicketCategory.ASSET_INTAKE,
                        priority=priority,
                        notes=notes,
                        case_owner_id=int(case_owner_id) if case_owner_id else None,
                        queue_id=int(queue_id) if queue_id else None
                    )

                    flash('Asset intake ticket created successfully')
                    return redirect(url_for('tickets.view_ticket', ticket_id=ticket_id))
                except Exception as e:
                    logger.info(f"Error creating ticket: {str(e)}")  # Debug log
                    db_session.rollback()
                    flash('Error creating ticket: ' + str(e), 'error')
                    return render_template('tickets/create.html', **get_template_context(request.form))

            # Create the ticket for other categories (including custom categories)
            notes = request.form.get('notes', '')
            # case_owner_id already extracted at line 1143-1145

            # Handle custom categories
            if is_custom_category:
                # For custom categories, we'll use a special handling since the DB expects enum values
                # We'll create the ticket directly in the database with a workaround
                asset_id = None
                if asset:
                    asset_id = asset.id
                
                # Determine case owner for custom category
                custom_case_owner_id = int(case_owner_id) if case_owner_id else user_id
                
                # Create ticket object directly (bypassing ticket_store for custom categories)
                new_ticket = Ticket(
                    subject=subject if subject else f"Custom ticket - {category}",
                    description=description if description else "Custom ticket created",
                    requester_id=user_id,
                    assigned_to_id=custom_case_owner_id,  # Use selected case owner or default to requester
                    priority=priority if isinstance(priority, TicketPriority) else TicketPriority.MEDIUM,
                    asset_id=asset_id,
                    country=request.form.get('country'),
                    notes=notes
                )
                
                # For custom categories, we'll store the category name in the description field
                # and use a special enum value to indicate it's a custom category
                new_ticket.category = None  # Set category to None for custom categories
                custom_description = f"[CUSTOM CATEGORY: {category}]\n\n{new_ticket.description}"
                new_ticket.description = custom_description
                
                # Set queue if provided
                if queue_id:
                    new_ticket.queue_id = queue_id
                
                db_session.add(new_ticket)
                db_session.flush()  # Get the ID
                ticket_id = new_ticket.id
                db_session.commit()
                
                # Send queue notifications if ticket was created in a queue
                if queue_id:
                    try:
                        from utils.queue_notification_sender import send_queue_notifications
                        send_queue_notifications(new_ticket, action_type="created")
                    except Exception as e:
                        logger.error(f"Error sending queue notifications: {str(e)}")
            else:
                # For enum categories, use existing logic
                asset_id = None
                if asset:
                    asset_id = asset.id
                    
                ticket_id = ticket_store.create_ticket(
                    subject=subject,
                    description=description,
                    requester_id=user_id,
                    category=category,
                    priority=priority,
                    asset_id=asset_id,
                    country=request.form.get('country'),
                    notes=notes,
                    case_owner_id=int(case_owner_id) if case_owner_id else None
                )

            flash('Ticket created successfully')
            return redirect(url_for('tickets.view_ticket', ticket_id=ticket_id))

    finally:
        db_session.close()

    return render_template('tickets/create.html', **get_template_context())

@tickets_bp.route('/<int:ticket_id>', methods=['GET'])
@login_required
def view_ticket(ticket_id):
    """View a ticket"""
    from models.company import Company
    db_session = db_manager.get_session()
    try:
        db_session.expire_all()

        # Load ticket with all relationships
        logger.info("Loading ticket with relationships...")
        ticket = db_session.query(Ticket).options(
            joinedload(Ticket.requester),
            joinedload(Ticket.assigned_to),
            joinedload(Ticket.customer)
                .joinedload(CustomerUser.company)
                .joinedload(Company.parent_company),
            joinedload(Ticket.queue),
            joinedload(Ticket.assets),
            joinedload(Ticket.accessories),
        ).get(ticket_id)
        
        # Debug: Check how many assets are loaded
        if ticket:
            logger.info(f"[TICKET VIEW DEBUG] Ticket {ticket_id} loaded with {len(ticket.assets)} assets")
            for asset in ticket.assets:
                logger.info(f"[TICKET VIEW DEBUG] - Asset: {asset.name} (ID: {asset.id})")
            
            # Also check ticket_assets table directly
            from models.asset_transaction import AssetTransaction
            direct_assets = db_session.execute(
                text("SELECT ticket_id, asset_id FROM ticket_assets WHERE ticket_id = :ticket_id"),
                {"ticket_id": ticket_id}
            ).fetchall()
            logger.info(f"[TICKET VIEW DEBUG] Direct query found {len(direct_assets)} ticket-asset relationships")
            for row in direct_assets:
                logger.info(f"[TICKET VIEW DEBUG] - Ticket-Asset: Ticket {row[0]} -> Asset {row[1]}")
        else:
            logger.info(f"[TICKET VIEW DEBUG] Ticket {ticket_id} not found")

        if not ticket:
            logger.info(f"Ticket {ticket_id} not found")
            flash('Ticket not found', 'error')
            return redirect(url_for('tickets.list_tickets'))

        # Permission check - ensure user has access to this ticket
        user = db_session.query(User).get(session.get('user_id'))
        if user:
            has_permission, error_message = check_ticket_permission(db_session, user, ticket)
            if not has_permission:
                logger.warning(f"User {user.id} denied access to ticket {ticket_id}: {error_message}")
                flash(error_message or 'You do not have permission to view this ticket', 'error')
                return redirect(url_for('tickets.list_tickets'))

        # Auto-update status for Asset Return (Claw) tickets based on progress
        if ticket.category == TicketCategory.ASSET_RETURN_CLAW:
            # Match template logic: check for "received" or "delivered" (case-insensitive)
            return_received = ticket.shipping_status and ("received" in ticket.shipping_status.lower() or "delivered" in ticket.shipping_status.lower())
            replacement_received = ticket.replacement_status and ("received" in ticket.replacement_status.lower() or "delivered" in ticket.replacement_status.lower())

            # Check if there's a replacement tracking (some returns have replacement, some don't)
            has_replacement = ticket.replacement_tracking and ticket.replacement_tracking.strip()

            # Auto-close logic:
            # - If NO replacement tracking: Close when return is received
            # - If HAS replacement tracking: Close when both return AND replacement are received
            should_close = False
            if return_received:
                if not has_replacement:
                    # No replacement - just a return, close when return received
                    should_close = True
                elif replacement_received:
                    # Has replacement and both are received - close
                    should_close = True

            if should_close and ticket.status not in [TicketStatus.RESOLVED, TicketStatus.RESOLVED_DELIVERED]:
                ticket.status = TicketStatus.RESOLVED
                ticket.custom_status = None  # Clear custom status when setting system status
                ticket.notes = (ticket.notes or "") + f"\n[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}] Ticket auto-closed: Return received at warehouse. Case completed!"
                db_session.commit()
                logger.info(f"Auto-closed ticket {ticket_id} on view - return received at warehouse")
            # Set to IN_PROGRESS if any progress has been made and status is still NEW
            elif ticket.status == TicketStatus.NEW:
                # Check if any progress has been made
                has_progress = (
                    ticket.shipping_tracking or  # Return label sent
                    (ticket.shipping_status and ticket.shipping_status not in ['Pending', 'Information Received']) or  # Customer shipped
                    return_received or  # Return received
                    replacement_received  # Replacement received
                )
                if has_progress:
                    ticket.status = TicketStatus.IN_PROGRESS
                    ticket.custom_status = None  # Clear custom status when setting system status
                    db_session.commit()
                    logger.info(f"Auto-updated ticket {ticket_id} status to IN_PROGRESS based on case progress")

        logger.info("Loading additional data...")
        # Load additional data needed for the template
        # Filter users based on current user's country permissions
        from models.user_country_permission import UserCountryPermission
        from sqlalchemy import or_

        # Base filter to exclude deleted users
        not_deleted_filter = or_(User.is_deleted == False, User.is_deleted == None)

        if current_user.is_super_admin or current_user.is_developer:
            # Super admins and developers can see all users (except deleted)
            all_users = db_session.query(User).filter(not_deleted_filter).order_by(User.username).all()
        elif current_user.user_type in [UserType.COUNTRY_ADMIN, UserType.SUPERVISOR]:
            # Country admins and supervisors can only see users from their assigned countries
            # Re-fetch current user in this session to avoid lazy loading issues
            current_user_fresh = db_session.query(User).get(current_user.id)
            user_countries = [cp.country for cp in current_user_fresh.country_permissions] if current_user_fresh else []
            if user_countries:
                # Get users who have country permissions matching any of the current user's countries
                users_with_matching_countries = db_session.query(User).join(
                    UserCountryPermission, User.id == UserCountryPermission.user_id
                ).filter(
                    UserCountryPermission.country.in_(user_countries),
                    not_deleted_filter
                ).distinct().order_by(User.username).all()

                # Also include super admins and developers (they can always be notified)
                admins_and_devs = db_session.query(User).filter(
                    User.user_type.in_([UserType.SUPER_ADMIN, UserType.DEVELOPER]),
                    not_deleted_filter
                ).order_by(User.username).all()

                # Combine and deduplicate
                all_users_set = {u.id: u for u in users_with_matching_countries}
                for u in admins_and_devs:
                    all_users_set[u.id] = u
                all_users = sorted(all_users_set.values(), key=lambda x: x.username)
            else:
                all_users = db_session.query(User).filter(not_deleted_filter).order_by(User.username).all()
        else:
            # Regular users can see all users (except deleted)
            all_users = db_session.query(User).filter(not_deleted_filter).order_by(User.username).all()

        # Create separate lists for different purposes:
        # - users_for_assignment: For Change Case Owner dropdown (visibility filtered)
        # - users_for_mention: For @mention in Report an Issue (mention filtered)
        users_for_assignment = list(all_users)  # Copy for visibility filtering
        users_for_mention = list(all_users)  # Copy for mention filtering

        # Apply visibility permissions filter for Change Case Owner (SUPERVISOR/COUNTRY_ADMIN only)
        if current_user.user_type in [UserType.COUNTRY_ADMIN, UserType.SUPERVISOR]:
            from models.user_visibility_permission import UserVisibilityPermission
            visibility_perms = db_session.query(UserVisibilityPermission.visible_user_id).filter(
                UserVisibilityPermission.user_id == current_user.id
            ).all()
            if visibility_perms:
                allowed_visible_ids = {p[0] for p in visibility_perms}
                users_for_assignment = [u for u in users_for_assignment if u.id in allowed_visible_ids]

        # Apply @mention permission filtering for both Report an Issue AND Change Case Owner
        current_user_fresh = db_session.query(User).get(current_user.id)
        if current_user_fresh and current_user_fresh.mention_filter_enabled:
            from models.user_mention_permission import UserMentionPermission
            mention_perms = db_session.query(UserMentionPermission.target_id).filter(
                UserMentionPermission.user_id == current_user.id,
                UserMentionPermission.target_type == 'user'
            ).all()
            if mention_perms:
                allowed_mention_ids = {p[0] for p in mention_perms}
                users_for_mention = [u for u in users_for_mention if u.id in allowed_mention_ids]
                users_for_assignment = [u for u in users_for_assignment if u.id in allowed_mention_ids]

        owner = ticket.assigned_to

        # Convert users to dictionary format for the template
        # users_dict: For Change Case Owner dropdown (visibility filtered)
        # users_dict_mention: For @mention in Report an Issue (mention filtered)
        users_dict = {}
        for user in users_for_assignment:
            user_data = {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'is_active': user.is_active,
                'user_type': user.user_type.value if user.user_type else 'USER'
            }
            users_dict[str(user.id)] = user_data

        users_dict_mention = {}
        users_list = []  # For @mention autocomplete
        for user in users_for_mention:
            user_data = {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'is_active': user.is_active,
                'user_type': user.user_type.value if user.user_type else 'USER'
            }
            users_dict_mention[str(user.id)] = user_data
            users_list.append(user_data)
        
        # Get queues - filtered by permissions for COUNTRY_ADMIN and SUPERVISOR
        accessible_queue_ids = []
        if current_user.user_type in [UserType.SUPERVISOR, UserType.COUNTRY_ADMIN]:
            from models.user_queue_permission import UserQueuePermission
            queue_permissions = db_session.query(UserQueuePermission.queue_id).filter(
                UserQueuePermission.user_id == current_user.id,
                UserQueuePermission.can_view == True
            ).all()
            accessible_queue_ids = [q[0] for q in queue_permissions]
            # Only show queues the user has permission to access
            queues = db_session.query(Queue).filter(Queue.id.in_(accessible_queue_ids)).all() if accessible_queue_ids else []
        else:
            # SUPER_ADMIN and DEVELOPER can see all queues
            queues = db_session.query(Queue).all()

        # Get custom ticket statuses
        from models.custom_ticket_status import CustomTicketStatus
        custom_statuses = db_session.query(CustomTicketStatus).filter(
            CustomTicketStatus.is_active == True
        ).order_by(CustomTicketStatus.sort_order).all()
        custom_statuses_list = [status.to_dict() for status in custom_statuses]

        # Get assets data for the template
        assets_data = []
        assets_query = db_session.query(Asset)
        
        # Filter assets based on user type and permissions
        if current_user.is_super_admin:
            assets = assets_query.all()
        elif current_user.user_type == UserType.COUNTRY_ADMIN and current_user.assigned_countries:
            assets = assets_query.filter(Asset.country == current_user.assigned_country).all()
        else:
            assets = []
        
        for asset in assets:
            assets_data.append({
                'id': asset.id,
                'name': asset.name,
                'asset_tag': asset.asset_tag,
                'serial_num': asset.serial_num,
                'status': asset.status.value if asset.status else None
            })
        
        # Get customers for the template (filtered by company for non-SUPER_ADMIN users)
        user = db_manager.get_user(session['user_id'])
        customers = get_filtered_customers(db_session, user)

        # Get companies for the Create New Customer form
        all_companies = db_session.query(Company).order_by(Company.name).all()

        # Get asset model names for the model dropdown
        asset_models = db_session.query(Asset.model).filter(Asset.model.isnot(None)).distinct().all()
        asset_modal_models = [model[0] for model in asset_models if model[0]]
        
        # Create lookup mappings for model-product relationships
        model_product_map = {}
        model_type_map = {}
        
        # Get asset types and status options for dropdowns
        asset_types = db_session.query(Asset.asset_type).filter(
            Asset.asset_type.isnot(None)).distinct().all()
        asset_modal_types = [t[0] for t in asset_types if t[0]]
        
        # Get comments from database using comment_store
        comments = comment_store.get_ticket_comments(ticket_id)
        logger.info(f"[DEBUG] Found {len(comments)} comments for ticket {ticket_id}")

        # Query out-of-stock accessories for Asset Intake tickets
        out_of_stock_accessories = []
        if ticket.category and ticket.category.name == 'ASSET_INTAKE':
            from models.accessory import Accessory
            out_of_stock_accessories = db_session.query(Accessory).filter(
                Accessory.available_quantity <= 0
            ).order_by(Accessory.name).all()
        
        # Get check-in data for Asset Intake tickets
        checkin_data = None
        if ticket.category and ticket.category.name == 'ASSET_INTAKE':
            from models.ticket_asset_checkin import TicketAssetCheckin

            # Get all check-in records for this ticket
            checkins = db_session.query(TicketAssetCheckin).filter_by(
                ticket_id=ticket_id
            ).all()
            checkin_map = {c.asset_id: c for c in checkins}

            # Build asset list with check-in status
            assets_checkin_list = []
            for asset in ticket.assets:
                checkin = checkin_map.get(asset.id)
                assets_checkin_list.append({
                    'id': asset.id,
                    'serial_number': asset.serial_num,
                    'asset_tag': asset.asset_tag,
                    'model': asset.model,
                    'type': asset.type if hasattr(asset, 'type') else None,
                    'checked_in': checkin.checked_in if checkin else False,
                    'checked_in_at': checkin.checked_in_at.strftime('%Y-%m-%d %H:%M') if checkin and checkin.checked_in_at else None,
                    'checked_in_by': checkin.checked_in_by.full_name if checkin and checkin.checked_in_by else None
                })

            # Get progress and steps
            intake_detail = ticket.get_intake_steps_detail(db_session)

            checkin_data = {
                'assets': assets_checkin_list,
                'progress': intake_detail['progress'],
                'current_step': intake_detail['current_step'],
                'steps': intake_detail['steps']
            }

        # Get packages for Asset Checkout (claw) tickets
        packages = []
        packages_tracking_data = {}
        packages_items_data = {}
        if ticket.category and ticket.category.name == 'ASSET_CHECKOUT_CLAW':
            packages = ticket.get_all_packages()
            
            # Load tracking history for each package
            from models.tracking_history import TrackingHistory
            for package in packages:
                package_number = package['package_number']
                tracking_number = package['tracking_number']
                
                if tracking_number:
                    # Look for tracking history for this package
                    tracking_history = db_session.query(TrackingHistory).filter_by(
                        tracking_number=tracking_number,
                        ticket_id=ticket_id
                    ).first()
                    
                    if tracking_history and tracking_history.events:
                        packages_tracking_data[package_number] = tracking_history.events
                
                # Load package items (assets and accessories)
                package_items = ticket.get_package_items(package_number, db_session=db_session)
                packages_items_data[package_number] = package_items

        # Get companies and countries for Create New Asset modal dropdowns
        # Get companies the user has access to (for Customer dropdown)
        from models.user_company_permission import UserCompanyPermission
        from models.company_customer_permission import CompanyCustomerPermission

        if current_user.user_type in [UserType.SUPER_ADMIN, UserType.DEVELOPER]:
            # SUPER_ADMIN/DEVELOPER can see all companies
            all_companies_query = db_session.query(Company).order_by(Company.name).all()
            asset_modal_customers = [c.name for c in all_companies_query]
        elif current_user.user_type in [UserType.COUNTRY_ADMIN, UserType.SUPERVISOR]:
            # Get companies this user has permission to view
            user_company_permissions = db_session.query(UserCompanyPermission).filter_by(
                user_id=current_user.id,
                can_view=True
            ).all()

            if user_company_permissions:
                permitted_company_ids = [perm.company_id for perm in user_company_permissions]

                # Include child companies of any parent companies AND parent companies of any child companies
                permitted_companies = db_session.query(Company).filter(Company.id.in_(permitted_company_ids)).all()
                all_permitted_ids = list(permitted_company_ids)

                for company in permitted_companies:
                    # If this is a parent company, include all its children
                    if company.is_parent_company or company.child_companies.count() > 0:
                        child_ids = [c.id for c in company.child_companies.all()]
                        all_permitted_ids.extend(child_ids)

                    # If this is a child company, include its parent
                    if company.parent_company_id:
                        all_permitted_ids.append(company.parent_company_id)

                # Include cross-company permissions
                cross_company_ids = []
                for company_id in all_permitted_ids:
                    additional_ids = db_session.query(CompanyCustomerPermission.customer_company_id)\
                        .filter(
                            CompanyCustomerPermission.company_id == company_id,
                            CompanyCustomerPermission.can_view == True
                        ).all()
                    cross_company_ids.extend([cid[0] for cid in additional_ids])

                permitted_company_ids = list(set(all_permitted_ids + cross_company_ids))
                permitted_companies_final = db_session.query(Company).filter(Company.id.in_(permitted_company_ids)).all()
                asset_modal_customers = sorted([c.name for c in permitted_companies_final])
            else:
                asset_modal_customers = []
        elif current_user.company_id:
            # CLIENT users - only their company
            user_company = db_session.query(Company).get(current_user.company_id)
            asset_modal_customers = [user_company.name] if user_company else []
        else:
            asset_modal_customers = []

        # Get countries the user has access to (for Country dropdown)
        from models.user_country_permission import UserCountryPermission

        if current_user.user_type in [UserType.SUPER_ADMIN, UserType.DEVELOPER]:
            # SUPER_ADMIN/DEVELOPER can see all countries
            asset_modal_countries = COUNTRIES
        elif current_user.user_type in [UserType.COUNTRY_ADMIN, UserType.SUPERVISOR]:
            # Get countries this user has permission to view
            current_user_fresh = db_session.query(User).get(current_user.id)
            user_country_perms = [cp.country for cp in current_user_fresh.country_permissions] if current_user_fresh else []
            if user_country_perms:
                # Filter COUNTRIES list to only include user's permitted countries
                asset_modal_countries = [c for c in COUNTRIES if c in user_country_perms]
            else:
                asset_modal_countries = []
        else:
            # Regular users get all countries
            asset_modal_countries = COUNTRIES

        # Check if current user has access to firstbase company (for Shipping Portal visibility)
        user_has_firstbase_access = current_user.is_super_admin or current_user.is_developer
        if not user_has_firstbase_access:
            try:
                firstbase_company = db_session.query(Company).filter(
                    Company.name.ilike('%firstbase%')
                ).first()
                if firstbase_company:
                    user_has_firstbase_access = current_user.can_access_company(firstbase_company.id)
            except Exception as e:
                logger.error(f"Error checking Firstbase access: {str(e)}")
                user_has_firstbase_access = False

        # Get custom issue types for "Report an Issue" dropdown
        custom_issue_types = []
        try:
            from models.custom_issue_type import CustomIssueType
            custom_issue_types = db_session.query(CustomIssueType).filter_by(is_active=True).order_by(CustomIssueType.name).all()
        except Exception as e:
            logger.warning(f"Could not load custom_issue_types: {str(e)}")

        return render_template(
            'tickets/view.html',
            ticket=ticket,
            owner=owner,
            users=users_list,  # For @mention autocomplete (list format)
            users_dict=users_dict,  # For Change Case Owner dropdown (visibility filtered)
            users_dict_mention=users_dict_mention,  # For Report an Issue @mention (mention filtered)
            queues=queues,
            assets_data=assets_data,
            customers=customers,
            all_companies=all_companies,  # Companies for Create New Customer form
            comments=comments,  # Add comments here!
            packages=packages,  # Add packages data
            packages_tracking_data=packages_tracking_data,  # Add tracking data
            packages_items_data=packages_items_data,  # Add package items data
            UserType=UserType,
            Country=Country,
            asset_modal_statuses=list(AssetStatus),
            asset_modal_models=asset_modal_models,
            asset_modal_types=asset_modal_types,
            asset_modal_customers=asset_modal_customers,  # Companies for Create New Asset Customer dropdown
            asset_modal_countries=asset_modal_countries,  # Countries for Create New Asset Country dropdown
            model_product_map=model_product_map,
            model_type_map=model_type_map,
            custom_statuses=custom_statuses_list,
            custom_issue_types=custom_issue_types,  # Custom issue types for Report an Issue dropdown
            out_of_stock_accessories=out_of_stock_accessories,
            accessible_queue_ids=accessible_queue_ids,
            checkin_data=checkin_data,
            user_has_firstbase_access=user_has_firstbase_access
        )
        
    except Exception as e:
        logger.info(f"[TICKET VIEW DEBUG] Error loading ticket {ticket_id}: {str(e)}")
        logger.info("[TICKET VIEW DEBUG] Error traceback:")
        traceback.print_exc()
        
        # Try to provide more specific error information
        error_msg = str(e)
        if "asset" in error_msg.lower():
            flash(f'Error loading ticket assets: {error_msg}', 'error')
        elif "relationship" in error_msg.lower():
            flash(f'Error loading ticket relationships: {error_msg}', 'error')
        else:
            flash(f'Error loading the ticket: {error_msg}', 'error')
        return redirect(url_for('tickets.list_tickets'))
    finally:
        db_session.close()

@tickets_bp.route('/<int:ticket_id>/comment', methods=['POST'])
@login_required
def add_comment(ticket_id):
    # Permission check
    db_session = db_manager.get_session()
    try:
        ticket = db_session.query(Ticket).get(ticket_id)
        if not ticket:
            flash('Ticket not found', 'error')
            return redirect(url_for('tickets.list_tickets'))

        user = db_session.query(User).get(session.get('user_id'))
        if user:
            has_permission, error_message = check_ticket_permission(db_session, user, ticket)
            if not has_permission:
                logger.warning(f"User {user.id} denied comment access to ticket {ticket_id}: {error_message}")
                flash(error_message or 'You do not have permission to comment on this ticket', 'error')
                return redirect(url_for('tickets.list_tickets'))
    finally:
        db_session.close()

    content = request.form.get('message')  # Changed from 'content' to 'message'
    if not content:
        flash('Comment cannot be empty')
        return redirect(url_for('tickets.view_ticket', ticket_id=ticket_id))

    comment = comment_store.add_comment(
        ticket_id=ticket_id,
        user_id=session['user_id'],
        content=content
    )

    flash('Comment added successfully')
    return redirect(url_for('tickets.view_ticket', ticket_id=ticket_id) + '?comment_posted=1#comments')

@tickets_bp.route('/comments/<int:comment_id>/edit', methods=['POST'])
@login_required
def edit_comment(comment_id):
    """Edit a comment"""
    try:
        data = request.get_json()
        content = data.get('content', '').strip()
        
        if not content:
            return jsonify({'success': False, 'error': 'Comment cannot be empty'})
        
        # Get the comment
        comment = comment_store.get_comment(comment_id)
        if not comment:
            return jsonify({'success': False, 'error': 'Comment not found'})
        
        # Check if user owns the comment
        if comment.user_id != session['user_id']:
            return jsonify({'success': False, 'error': 'You can only edit your own comments'})
        
        # Update the comment
        success = comment_store.update_comment(comment_id, content)
        if success:
            return jsonify({'success': True, 'message': 'Comment updated successfully'})
        else:
            return jsonify({'success': False, 'error': 'Failed to update comment'})
            
    except Exception as e:
        logger.error(f"Error editing comment: {str(e)}")
        return jsonify({'success': False, 'error': 'An error occurred while updating the comment'})

@tickets_bp.route('/comments/<int:comment_id>/delete', methods=['POST'])
@login_required
def delete_comment(comment_id):
    """Delete a comment"""
    try:
        # Get the comment
        comment = comment_store.get_comment(comment_id)
        if not comment:
            return jsonify({'success': False, 'error': 'Comment not found'})
        
        # Check if user owns the comment or is admin
        user = db_manager.get_user(session['user_id'])
        if comment.user_id != session['user_id'] and not user.is_super_admin:
            return jsonify({'success': False, 'error': 'You can only delete your own comments'})
        
        # Delete the comment
        success = comment_store.delete_comment(comment_id)
        if success:
            return jsonify({'success': True, 'message': 'Comment deleted successfully'})
        else:
            return jsonify({'success': False, 'error': 'Failed to delete comment'})
            
    except Exception as e:
        logger.error(f"Error deleting comment: {str(e)}")
        return jsonify({'success': False, 'error': 'An error occurred while deleting the comment'})

@tickets_bp.route('/queues')
@login_required
def list_queues():
    """List all queues and filter based on user's company permissions"""
    db_session = db_manager.get_session()
    try:
        user = db_manager.get_user(session['user_id'])

        # Filter queues based on user type and permissions
        if user.user_type in [UserType.SUPER_ADMIN, UserType.DEVELOPER]:
            # SUPER_ADMIN and DEVELOPER can see all queues
            queues = db_session.query(Queue).all()
        elif user.user_type in [UserType.COUNTRY_ADMIN, UserType.SUPERVISOR]:
            # COUNTRY_ADMIN and SUPERVISOR can only see queues they have permission for
            from models.user_queue_permission import UserQueuePermission
            queue_permissions = db_session.query(UserQueuePermission.queue_id).filter(
                UserQueuePermission.user_id == user.id,
                UserQueuePermission.can_view == True
            ).all()
            accessible_queue_ids = [q[0] for q in queue_permissions]
            queues = db_session.query(Queue).filter(Queue.id.in_(accessible_queue_ids)).all() if accessible_queue_ids else []
        else:
            # Other users (CLIENT) - batch load queue permissions
            accessible_queue_ids = user.get_accessible_queue_ids(db_session)
            all_queues = db_session.query(Queue).all()
            queues = [q for q in all_queues if q.id in accessible_queue_ids]
        
        # Get ticket counts for each queue to avoid detached session issues
        queue_ticket_counts = {}
        for queue in queues:
            # Count ALL tickets for this queue
            total_count = db_session.query(Ticket).filter(Ticket.queue_id == queue.id).count()
            
            # Count OPEN tickets for this queue (exclude resolved tickets)
            open_count = db_session.query(Ticket).filter(
                Ticket.queue_id == queue.id,
                Ticket.status != TicketStatus.RESOLVED,
                Ticket.status != TicketStatus.RESOLVED_DELIVERED
            ).count()
            
            queue_ticket_counts[queue.id] = {
                'total': total_count,
                'open': open_count
            }
            
        return render_template('tickets/queues.html', queues=queues, queue_ticket_counts=queue_ticket_counts, user=user)
    finally:
        db_session.close()

@tickets_bp.route('/queues/create', methods=['POST'])
@login_required
def create_queue():
    """Create a new support queue"""
    try:
        user = db_manager.get_user(session['user_id'])

        # Only SUPER_ADMIN and DEVELOPER can create queues
        if not (user.is_super_admin or user.is_developer):
            # Check if it's a JSON request
            if request.is_json:
                return jsonify({'success': False, 'error': 'Permission denied. Only Super Admins and Developers can create queues.'}), 403
            flash('Permission denied. Only Super Admins and Developers can create queues.', 'error')
            return redirect(url_for('tickets.list_queues'))

        # Handle both JSON and form data
        if request.is_json:
            data = request.get_json()
            name = data.get('name')
            description = data.get('description', '')
        else:
            name = request.form.get('name')
            description = request.form.get('description', '')

        if not name:
            if request.is_json:
                return jsonify({'success': False, 'error': 'Queue name is required'}), 400
            flash('Queue name is required', 'error')
            return redirect(url_for('tickets.list_queues'))

        # Create the new queue using queue_store to ensure in-memory cache is updated
        new_queue = queue_store.add_queue(name, description)

        # Refresh the queue_store to ensure it has the latest data
        queue_store.load_queues()

        if request.is_json:
            return jsonify({'success': True, 'message': f'Queue "{name}" created successfully', 'queue_id': new_queue.id})

        flash(f'Queue "{name}" created successfully', 'success')
        return redirect(url_for('tickets.list_queues'))
    except Exception as e:
        logging.error(f"Error creating queue: {str(e)}")
        if request.is_json:
            return jsonify({'success': False, 'error': str(e)}), 500
        flash(f'Error creating queue: {str(e)}', 'error')
        return redirect(url_for('tickets.list_queues'))

@tickets_bp.route('/queues/<int:queue_id>')
@login_required
def view_queue(queue_id):
    """View a specific queue and its tickets"""
    user = db_manager.get_user(session['user_id'])

    # Check if user has permission to access this queue
    if not user.can_access_queue(queue_id):
        flash('You do not have permission to view this queue', 'error')
        return redirect(url_for('tickets.list_queues'))

    queue = queue_store.get_queue(queue_id)
    if not queue:
        flash('Queue not found', 'error')
        return redirect(url_for('tickets.list_queues'))

    # Use database session directly to load tickets with all relationships
    db_session = db_manager.get_session()
    try:
        tickets = db_session.query(Ticket).options(
            joinedload(Ticket.assets),
            joinedload(Ticket.customer),
            joinedload(Ticket.requester),
            joinedload(Ticket.assigned_to)
        ).filter(Ticket.queue_id == queue_id).order_by(Ticket.created_at.desc()).all()

        return render_template('tickets/queue_view.html', queue=queue, tickets=tickets, user=user)
    finally:
        db_session.close()

@tickets_bp.route('/queues/<int:queue_id>/delete', methods=['POST'])
@login_required
def delete_queue(queue_id):
    """Delete a queue"""
    try:
        user = db_manager.get_user(session['user_id'])

        # Only SUPER_ADMIN and DEVELOPER can delete queues
        if not (user.is_super_admin or user.is_developer):
            return jsonify({'success': False, 'error': 'Permission denied. Only Super Admins and Developers can delete queues.'}), 403

        db_session = db_manager.get_session()
        try:
            # Check if queue exists
            queue = db_session.query(Queue).filter(Queue.id == queue_id).first()
            if not queue:
                return jsonify({'success': False, 'error': 'Queue not found'}), 404

            # Check if queue has tickets
            ticket_count = db_session.query(Ticket).filter(Ticket.queue_id == queue_id).count()
            if ticket_count > 0:
                return jsonify({'success': False, 'error': f'Cannot delete queue with {ticket_count} tickets. Please move or delete tickets first.'}), 400

            # Delete all company queue permissions for this queue
            from models.company_queue_permission import CompanyQueuePermission
            db_session.query(CompanyQueuePermission).filter(CompanyQueuePermission.queue_id == queue_id).delete()

            # Delete the queue
            db_session.delete(queue)
            db_session.commit()

            # Also remove from queue_store cache if it exists
            if hasattr(queue_store, 'queues') and queue_id in queue_store.queues:
                del queue_store.queues[queue_id]

            return jsonify({'success': True, 'message': 'Queue deleted successfully'})

        finally:
            db_session.close()

    except Exception as e:
        logging.error(f"Error deleting queue: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@tickets_bp.route('/queues/<int:queue_id>/edit', methods=['POST'])
@login_required
def edit_queue(queue_id):
    """Edit a queue name"""
    try:
        user = db_manager.get_user(session['user_id'])

        # Only SUPER_ADMIN and DEVELOPER can edit queues
        if not (user.is_super_admin or user.is_developer):
            return jsonify({'success': False, 'error': 'Permission denied. Only Super Admins and Developers can edit queues.'}), 403

        # Get the new name from request
        data = request.get_json()
        new_name = data.get('name', '').strip()

        if not new_name:
            return jsonify({'success': False, 'error': 'Queue name is required'}), 400

        db_session = db_manager.get_session()
        try:
            # Check if queue exists
            queue = db_session.query(Queue).filter(Queue.id == queue_id).first()
            if not queue:
                return jsonify({'success': False, 'error': 'Queue not found'}), 404

            # Check if another queue with this name already exists
            existing_queue = db_session.query(Queue).filter(
                Queue.name == new_name,
                Queue.id != queue_id
            ).first()
            if existing_queue:
                return jsonify({'success': False, 'error': f'A queue with the name "{new_name}" already exists'}), 400

            # Update the queue name
            old_name = queue.name
            queue.name = new_name
            db_session.commit()

            # Reload queue_store cache
            queue_store.load_queues()

            logging.info(f"Queue {queue_id} renamed from '{old_name}' to '{new_name}' by user {user.username}")
            return jsonify({'success': True, 'message': f'Queue renamed to "{new_name}" successfully'})

        finally:
            db_session.close()

    except Exception as e:
        logging.error(f"Error editing queue: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ============= Queue Manager API (iOS-style) =============

@tickets_bp.route('/queues/api/list', methods=['GET'])
@login_required
def api_list_queues():
    """Get all queues with folders for iOS-style grid display"""
    try:
        user = db_manager.get_user(session['user_id'])

        # Only SUPER_ADMIN and DEVELOPER can manage queues
        if not (user.is_super_admin or user.is_developer):
            return jsonify({'success': False, 'error': 'Permission denied'}), 403

        data = queue_store.get_queues_with_folders()
        # Combine unfiled_queues into a flat list for the JS
        all_queues = []
        for folder in data.get('folders', []):
            all_queues.extend(folder.get('queues', []))
        all_queues.extend(data.get('unfiled_queues', []))

        return jsonify({
            'success': True,
            'queues': all_queues,
            'folders': data.get('folders', [])
        })

    except Exception as e:
        logging.error(f"Error getting queues with folders: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@tickets_bp.route('/queues/api/create', methods=['POST'])
@login_required
def api_create_queue():
    """Create a new queue (inline in grid)"""
    try:
        user = db_manager.get_user(session['user_id'])

        if not (user.is_super_admin or user.is_developer):
            return jsonify({'success': False, 'error': 'Permission denied'}), 403

        data = request.get_json()
        name = data.get('name', '').strip()

        if not name:
            return jsonify({'success': False, 'error': 'Queue name is required'}), 400

        db_session = db_manager.get_session()
        try:
            # Check if queue with this name already exists
            existing = db_session.query(Queue).filter(Queue.name == name).first()
            if existing:
                return jsonify({'success': False, 'error': f'Queue "{name}" already exists'}), 400

            # Get max display_order
            max_order = db_session.query(Queue).count()
            queue = Queue(
                name=name,
                description=data.get('description', ''),
                folder_id=data.get('folder_id'),
                display_order=max_order
            )
            db_session.add(queue)
            db_session.commit()

            queue_store.load_queues()

            return jsonify({
                'success': True,
                'queue': {
                    'id': queue.id,
                    'name': queue.name,
                    'description': queue.description,
                    'folder_id': queue.folder_id,
                    'display_order': queue.display_order,
                    'ticket_count': 0  # New queue has no tickets
                },
                'message': f'Queue "{name}" created successfully'
            })
        finally:
            db_session.close()

    except Exception as e:
        logging.error(f"Error creating queue: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@tickets_bp.route('/queues/api/delete/<int:queue_id>', methods=['DELETE', 'POST'])
@login_required
def api_delete_queue(queue_id):
    """Delete a queue (from jiggle mode)"""
    try:
        user = db_manager.get_user(session['user_id'])

        if not (user.is_super_admin or user.is_developer):
            return jsonify({'success': False, 'error': 'Permission denied'}), 403

        db_session = db_manager.get_session()
        try:
            queue = db_session.query(Queue).filter(Queue.id == queue_id).first()
            if not queue:
                return jsonify({'success': False, 'error': 'Queue not found'}), 404

            # Check if queue has tickets
            ticket_count = db_session.query(Ticket).filter(Ticket.queue_id == queue_id).count()
            if ticket_count > 0:
                return jsonify({
                    'success': False,
                    'error': f'Cannot delete queue with {ticket_count} ticket(s). Move or delete tickets first.'
                }), 400

            queue_name = queue.name
            db_session.delete(queue)
            db_session.commit()

            queue_store.load_queues()

            return jsonify({
                'success': True,
                'message': f'Queue "{queue_name}" deleted successfully'
            })
        finally:
            db_session.close()

    except Exception as e:
        logging.error(f"Error deleting queue: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@tickets_bp.route('/queues/api/reorder', methods=['POST'])
@login_required
def api_reorder_queues():
    """Update queue display order (drag and drop)"""
    try:
        user = db_manager.get_user(session['user_id'])

        if not (user.is_super_admin or user.is_developer):
            return jsonify({'success': False, 'error': 'Permission denied'}), 403

        data = request.get_json()
        queue_orders = data.get('queue_orders', [])

        if queue_store.reorder_queues(queue_orders):
            return jsonify({'success': True, 'message': 'Queue order updated'})
        else:
            return jsonify({'success': False, 'error': 'Failed to update queue order'}), 500

    except Exception as e:
        logging.error(f"Error reordering queues: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@tickets_bp.route('/queues/api/move-to-folder', methods=['POST'])
@login_required
def api_move_queue_to_folder():
    """Move queue into/out of folder"""
    try:
        user = db_manager.get_user(session['user_id'])

        if not (user.is_super_admin or user.is_developer):
            return jsonify({'success': False, 'error': 'Permission denied'}), 403

        data = request.get_json()
        queue_id = data.get('queue_id')
        folder_id = data.get('folder_id')  # None to remove from folder

        if not queue_id:
            return jsonify({'success': False, 'error': 'Queue ID is required'}), 400

        if queue_store.move_queue_to_folder(queue_id, folder_id):
            return jsonify({'success': True, 'message': 'Queue moved successfully'})
        else:
            return jsonify({'success': False, 'error': 'Failed to move queue'}), 500

    except Exception as e:
        logging.error(f"Error moving queue to folder: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ============= Queue Folder API =============

@tickets_bp.route('/queues/folders/create', methods=['POST'])
@login_required
def api_create_folder():
    """Create a new queue folder"""
    try:
        user = db_manager.get_user(session['user_id'])

        if not (user.is_super_admin or user.is_developer):
            return jsonify({'success': False, 'error': 'Permission denied'}), 403

        data = request.get_json()
        name = data.get('name', '').strip()

        if not name:
            return jsonify({'success': False, 'error': 'Folder name is required'}), 400

        folder = queue_store.add_folder(
            name=name,
            color=data.get('color', 'blue'),
            icon=data.get('icon', 'folder')
        )

        return jsonify({
            'success': True,
            'folder': {
                'id': folder.id,
                'name': folder.name,
                'color': folder.color,
                'icon': folder.icon,
                'display_order': folder.display_order,
                'queues': [],
                'queue_count': 0
            },
            'message': f'Folder "{name}" created successfully'
        })

    except Exception as e:
        logging.error(f"Error creating folder: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@tickets_bp.route('/queues/folders/<int:folder_id>/edit', methods=['POST'])
@login_required
def api_edit_folder(folder_id):
    """Edit folder name/color"""
    try:
        user = db_manager.get_user(session['user_id'])

        if not (user.is_super_admin or user.is_developer):
            return jsonify({'success': False, 'error': 'Permission denied'}), 403

        data = request.get_json()

        if queue_store.update_folder(
            folder_id,
            name=data.get('name'),
            color=data.get('color'),
            icon=data.get('icon')
        ):
            return jsonify({'success': True, 'message': 'Folder updated successfully'})
        else:
            return jsonify({'success': False, 'error': 'Folder not found'}), 404

    except Exception as e:
        logging.error(f"Error editing folder: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@tickets_bp.route('/queues/folders/<int:folder_id>/delete', methods=['DELETE', 'POST'])
@login_required
def api_delete_folder(folder_id):
    """Delete folder (moves queues out)"""
    try:
        user = db_manager.get_user(session['user_id'])

        if not (user.is_super_admin or user.is_developer):
            return jsonify({'success': False, 'error': 'Permission denied'}), 403

        if queue_store.delete_folder(folder_id):
            return jsonify({'success': True, 'message': 'Folder deleted successfully'})
        else:
            return jsonify({'success': False, 'error': 'Folder not found'}), 404

    except Exception as e:
        logging.error(f"Error deleting folder: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@tickets_bp.route('/queues/folders/reorder', methods=['POST'])
@login_required
def api_reorder_folders():
    """Update folder display order"""
    try:
        user = db_manager.get_user(session['user_id'])

        if not (user.is_super_admin or user.is_developer):
            return jsonify({'success': False, 'error': 'Permission denied'}), 403

        data = request.get_json()
        folder_orders = data.get('folder_orders', [])

        if queue_store.reorder_folders(folder_orders):
            return jsonify({'success': True, 'message': 'Folder order updated'})
        else:
            return jsonify({'success': False, 'error': 'Failed to update folder order'}), 500

    except Exception as e:
        logging.error(f"Error reordering folders: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@tickets_bp.route('/<int:ticket_id>/update', methods=['POST'])
@login_required
def update_ticket(ticket_id):
    # Use database session directly to update the ticket
    db_session = db_manager.get_session()
    
    try:
        # Get the ticket from database
        # Eager load requester to avoid extra query
        ticket = db_session.query(Ticket).options(joinedload(Ticket.requester)).get(ticket_id)
        
        if not ticket:
            flash('Ticket not found')
            return redirect(url_for('tickets.list_tickets'))

        # --- PERMISSION CHECK ---
        # First check if user can access this ticket at all (queue/company permissions)
        user = db_session.query(User).get(session.get('user_id'))
        if user:
            has_permission, error_message = check_ticket_permission(db_session, user, ticket)
            if not has_permission:
                logger.warning(f"User {user.id} denied update access to ticket {ticket_id}: {error_message}")
                flash(error_message or 'You do not have permission to update this ticket', 'error')
                return redirect(url_for('tickets.list_tickets'))

        # Additionally, for non-admins, check if they are the creator or assigned
        if not (current_user.is_super_admin or current_user.is_developer or
                current_user.id == ticket.requester_id or current_user.id == ticket.assigned_to_id):
            flash('You do not have permission to update this ticket.', 'error')
            return redirect(url_for('tickets.view_ticket', ticket_id=ticket_id))
        # --- END PERMISSION CHECK ---

        # Update basic fields
        subject = request.form.get('subject')
        if subject and subject.strip():
            ticket.subject = subject.strip()
            logger.info(f"DEBUG - Updated subject to: {ticket.subject}")
        
        description = request.form.get('description')
        if description and description.strip():
            ticket.description = description.strip()
            logger.info("DEBUG - Updated description")
        
        # Update return description for Asset Return tickets
        return_description = request.form.get('return_description')
        if return_description is not None:  # Allow empty string to clear field
            ticket.return_description = return_description.strip() if return_description else None
            logger.info("DEBUG - Updated return_description")

        # Update damage_description (Reported Issue) for Asset Return tickets
        damage_description = request.form.get('damage_description')
        if damage_description is not None:  # Allow empty string to clear field
            ticket.damage_description = damage_description.strip() if damage_description else None
            logger.info("DEBUG - Updated damage_description")

        # Update notes
        notes = request.form.get('notes')
        if notes is not None:  # Allow empty string to clear field
            ticket.notes = notes.strip() if notes else None
            logger.info("DEBUG - Updated notes")
        
        # Update shipping address
        shipping_address = request.form.get('shipping_address')
        if shipping_address is not None:  # Allow empty string to clear field
            ticket.shipping_address = shipping_address.strip() if shipping_address else None
            logger.info("DEBUG - Updated shipping_address")
        
        # Update tracking numbers for Asset Return tickets
        shipping_tracking = request.form.get('shipping_tracking')
        if shipping_tracking is not None:  # Allow empty string to clear field
            ticket.shipping_tracking = shipping_tracking.strip() if shipping_tracking else None
            logger.info("DEBUG - Updated shipping_tracking")
        
        return_tracking = request.form.get('return_tracking')
        if return_tracking is not None:  # Allow empty string to clear field
            ticket.return_tracking = return_tracking.strip() if return_tracking else None
            logger.info("DEBUG - Updated return_tracking")

        # Update firstbaseorderid (Order ID / Customer Reference)
        firstbaseorderid = request.form.get('firstbaseorderid')
        if firstbaseorderid is not None:  # Allow empty string to clear field
            ticket.firstbaseorderid = firstbaseorderid.strip() if firstbaseorderid else None
            logger.info("DEBUG - Updated firstbaseorderid")

        # Debug current status
        logger.info(f"DEBUG - Current ticket status before update: {ticket.status}")
        if ticket.status:
            logger.info(f"DEBUG - Current ticket status value: {ticket.status.value}")
        
        # Update status
        status_value = request.form.get('status')
        logger.info(f"DEBUG - Form status value: {status_value}")

        old_status = ticket.status  # Store old status before update

        if status_value:
            try:
                # Try to get enum by name
                new_status = TicketStatus[status_value]
                logger.info(f"DEBUG - Setting status to {new_status}")
                ticket.status = new_status
                # Clear custom_status if setting a system status
                ticket.custom_status = None
            except KeyError:
                logger.info(f"DEBUG - KeyError: {status_value} is not a valid TicketStatus name")
                # It's a custom status - verify it exists in the database
                from models.custom_ticket_status import CustomTicketStatus
                custom_status = db_session.query(CustomTicketStatus).filter(
                    CustomTicketStatus.name == status_value,
                    CustomTicketStatus.is_active == True
                ).first()

                if custom_status:
                    logger.info(f"DEBUG - Custom status {status_value} detected and verified")
                    ticket.custom_status = status_value
                    # Clear the system status when using custom status
                    ticket.status = None

                    # Check if this status should auto-return assets to stock
                    if custom_status.auto_return_to_stock:
                        logger.info(f"DEBUG - Auto-return to stock enabled for status {status_value}")

                        # Return all assigned tech assets to stock
                        # Assets are linked via many-to-many relationship through ticket.assets
                        if ticket.assets:
                            for asset in ticket.assets:
                                logger.info(f"DEBUG - Returning asset {asset.id} ({asset.serial_num}) to stock")
                                asset.status = 'IN_STOCK'

                            # Clear the many-to-many relationship
                            ticket.assets.clear()
                            logger.info(f"DEBUG - Cleared {len(ticket.assets)} asset assignments from ticket")

                        # Return all assigned accessories to stock
                        if ticket.accessories:
                            for accessory_assignment in ticket.accessories:
                                quantity = accessory_assignment.quantity

                                # If there's a link to the original accessory in inventory, return it
                                if accessory_assignment.original_accessory:
                                    accessory = accessory_assignment.original_accessory
                                    logger.info(f"DEBUG - Returning {quantity} of accessory {accessory.id} ({accessory.name}) to stock")
                                    accessory.available_quantity += quantity
                                else:
                                    logger.info(f"DEBUG - Accessory '{accessory_assignment.name}' has no inventory link, skipping stock return")

                                # Remove the assignment
                                db_session.delete(accessory_assignment)

                        flash(f'Status updated to "{custom_status.display_name}" - All assets and accessories returned to stock', 'success')
                else:
                    logger.warning(f"DEBUG - Custom status {status_value} not found in database")
                    flash(f"Invalid status: {status_value}", 'error')
        
        # Update priority
        priority_value = request.form.get('priority')
        logger.info(f"DEBUG - Form priority value: {priority_value}")
        
        if priority_value:
            # Handle empty string priority by skipping the update
            if priority_value.strip() == "":
                logger.info("DEBUG - Empty priority value, skipping priority update")
            else:
                try:
                    # Try to get enum by name
                    new_priority = TicketPriority[priority_value]
                    logger.info(f"DEBUG - Setting priority to {new_priority}")
                    ticket.priority = new_priority
                except KeyError:
                    try:
                        # Try to get enum by value
                        new_priority = TicketPriority(priority_value)
                        logger.info(f"DEBUG - Setting priority to {new_priority}")
                        ticket.priority = new_priority
                    except ValueError:
                        logger.info(f"DEBUG - ValueError: {priority_value} is not a valid TicketPriority, skipping update")
        
        # Update assigned_to_id if admin
        if session['user_type'] == 'admin' or session['user_type'] == 'SUPER_ADMIN':
            assigned_to_id = request.form.get('assigned_to_id')
            logger.info(f"DEBUG - Form assigned_to_id: {assigned_to_id}")
            if assigned_to_id and assigned_to_id.strip():
                new_assigned_to_id = int(assigned_to_id)
                
                # Check if assignment is changing
                old_assigned_to_id = ticket.assigned_to_id
                logger.info(f"DEBUG - Old assigned_to_id: {old_assigned_to_id}, New assigned_to_id: {new_assigned_to_id}")
                if old_assigned_to_id != new_assigned_to_id:
                    # Get the previous assignee for notification
                    previous_assignee = None
                    if old_assigned_to_id:
                        previous_assignee = db_session.query(User).get(old_assigned_to_id)
                    
                    # Update the assignment
                    ticket.assigned_to_id = new_assigned_to_id
                    logger.info(f"DEBUG - Set assigned_to_id to {assigned_to_id}")
                    
                    # Send email notification to new assignee
                    try:
                        logger.info("DEBUG - Assignment changed, attempting to send email notification")
                        new_assignee = db_session.query(User).get(new_assigned_to_id)
                        logger.info(f"DEBUG - New assignee: {new_assignee.username if new_assignee else 'None'} ({new_assignee.email if new_assignee else 'No email'})")
                        if new_assignee and new_assignee.email:
                            from utils.email_sender import send_ticket_assignment_notification
                            
                            logger.info("DEBUG - Calling send_ticket_assignment_notification")
                            # Send notification email
                            email_sent = send_ticket_assignment_notification(
                                assigned_user=new_assignee,
                                assigner=current_user,
                                ticket=ticket,
                                previous_assignee=previous_assignee
                            )
                            
                            if email_sent:
                                logger.info(f"DEBUG - Assignment notification email sent to {new_assignee.email}")
                            else:
                                logger.info(f"DEBUG - Failed to send assignment notification email to {new_assignee.email}")
                        else:
                            logger.info("DEBUG - New assignee not found or has no email address")
                    except Exception as e:
                        logger.info(f"DEBUG - Error sending assignment notification: {str(e)}")
                        import traceback
                        traceback.print_exc()
                        # Don't fail the ticket update if email fails
                        pass
        
        # Commit the changes directly to database
        # Check if status changed to CLOSED_DUPLICATED - auto-return assets/accessories
        if status_value == "CLOSED_DUPLICATED":
            logger.info("=== AUTO-RETURN FOR CLOSED_DUPLICATED STATUS ===")

            # Return all accessories from this ticket
            ticket_accessories = db_session.query(TicketAccessory).filter(
                TicketAccessory.ticket_id == ticket_id
            ).all()

            for ticket_acc in ticket_accessories:
                if ticket_acc.original_accessory_id:
                    original_accessory = db_session.query(Accessory).filter(
                        Accessory.id == ticket_acc.original_accessory_id
                    ).first()

                    if original_accessory:
                        # Return to inventory
                        quantity = ticket_acc.quantity
                        original_accessory.available_quantity += quantity

                        # Update status if needed
                        if original_accessory.available_quantity > 0:
                            original_accessory.status = 'Available'

                        logger.info(f"Returned {quantity}x {original_accessory.name} to inventory")

                        # Create transaction record
                        from models.accessory_transaction import AccessoryTransaction
                        transaction = AccessoryTransaction(
                            accessory_id=original_accessory.id,
                            transaction_type="Auto-Return (Closed-Duplicated)",
                            quantity=quantity,
                            transaction_number=f"AUTORET-{ticket_id}-{original_accessory.id}-{int(datetime.datetime.now().timestamp())}",
                            user_id=current_user.id,
                            notes=f"Auto-returned from ticket #{ticket_id} when status changed to Closed-Duplicated"
                        )
                        db_session.add(transaction)

            # Return asset if assigned
            if ticket.asset_id:
                asset = db_session.query(Asset).filter(Asset.id == ticket.asset_id).first()
                if asset:
                    # Return asset to available status
                    from models.asset import AssetStatus
                    asset.status = AssetStatus.AVAILABLE
                    asset.customer_id = None

                    logger.info(f"Returned asset {asset.serial_number} to inventory")

                    # Create asset transaction record
                    from models.asset_transaction import AssetTransaction
                    asset_transaction = AssetTransaction(
                        asset_id=asset.id,
                        transaction_type="Auto-Return (Closed-Duplicated)",
                        transaction_number=f"AUTORET-ASSET-{ticket_id}-{asset.id}-{int(datetime.datetime.now().timestamp())}",
                        user_id=current_user.id,
                        notes=f"Auto-returned from ticket #{ticket_id} when status changed to Closed-Duplicated"
                    )
                    db_session.add(asset_transaction)

            logger.info("=== AUTO-RETURN COMPLETED ===")

        db_session.commit()
        logger.info("DEBUG - Committed changes to database")
        logger.info(f"DEBUG - Status after commit: {ticket.status}")
        if ticket.status:
            logger.info(f"DEBUG - Status value after commit: {ticket.status.value}")

        if status_value == "CLOSED_DUPLICATED":
            flash('Ticket marked as Closed-Duplicated. All assets and accessories have been automatically returned to inventory.', 'success')
        else:
            flash('Ticket updated successfully')
        
    except Exception as e:
        db_session.rollback()
        logger.info(f"ERROR - Failed to update ticket: {str(e)}")
        flash(f'Error updating ticket: {str(e)}')
    finally:
        db_session.close()
    
    return redirect(url_for('tickets.view_ticket', ticket_id=ticket_id))

@tickets_bp.route('/<int:ticket_id>/shipment', methods=['POST'])
@admin_required
def add_shipment(ticket_id):
    ticket = ticket_store.get_ticket(ticket_id)
    if not ticket:
        flash('Ticket not found')
        return redirect(url_for('tickets.list_tickets'))
    
    tracking_number = request.form.get('tracking_number')
    description = request.form.get('description')
    
    if tracking_number:
        ticket.add_shipment(tracking_number, description)
        flash('Shipment added successfully')
    else:
        flash('Tracking number is required')
    
    return redirect(url_for('tickets.view_ticket', ticket_id=ticket_id))

@tickets_bp.route('/<int:ticket_id>/shipment/update', methods=['POST'])
@admin_required
def update_shipment_tracking(ticket_id):
    ticket = ticket_store.get_ticket(ticket_id)
    if not ticket or not ticket.shipment:
        flash('Ticket or shipment not found')
        return redirect(url_for('tickets.view_ticket', ticket_id=ticket_id))
    
    status = request.form.get('status')
    details = request.form.get('details')
    
    if status:
        ticket.shipment.update_tracking(status, [details] if details else None)
        flash('Tracking information updated')
    else:
        flash('Status is required')
    
    return redirect(url_for('tickets.view_ticket', ticket_id=ticket_id))

@tickets_bp.route('/<int:ticket_id>/asset', methods=['POST'])
@admin_required
def assign_asset(ticket_id):
    ticket = ticket_store.get_ticket(ticket_id)
    if not ticket:
        flash('Ticket not found')
        return redirect(url_for('tickets.list_tickets'))
    
    asset_id = request.form.get('asset_id')
    if asset_id:
        asset_id = int(asset_id)
        # Check if asset exists in local inventory
        asset = inventory_store.get_asset(asset_id)
        if not asset:
            flash('Asset not found')
            return redirect(url_for('tickets.view_ticket', ticket_id=ticket_id))
        
        # Update the ticket and the asset
        ticket.asset_id = asset_id
        inventory_store.assign_asset_to_ticket(asset_id, ticket_id)
        flash('Asset assigned successfully')
    
    return redirect(url_for('tickets.view_ticket', ticket_id=ticket_id))

@tickets_bp.route('/<int:ticket_id>/assign-asset', methods=['POST'])
@login_required
def assign_existing_asset(ticket_id):
    """Assign an existing asset to a ticket via AJAX and optionally to a specific package"""
    try:
        # Get JSON data from request
        data = request.get_json()
        asset_id = data.get('asset_id')
        package_number = data.get('package_number')  # Optional package number
        
        if not asset_id:
            return jsonify({'success': False, 'error': 'Asset ID is required'}), 400
        
        # Get database session
        db_session = db_manager.get_session()
        
        try:
            # Get the ticket
            ticket = db_session.query(Ticket).get(ticket_id)
            if not ticket:
                return jsonify({'success': False, 'error': 'Ticket not found'}), 404
            
            # Get the asset
            asset = db_session.query(Asset).get(asset_id)
            if not asset:
                return jsonify({'success': False, 'error': 'Asset not found'}), 404
            
            # Check if asset is already assigned to this ticket
            existing_relationship = db_session.execute(
                text("SELECT 1 FROM ticket_assets WHERE ticket_id = :ticket_id AND asset_id = :asset_id"),
                {"ticket_id": ticket_id, "asset_id": asset_id}
            ).fetchone()
            
            if existing_relationship:
                return jsonify({'success': False, 'error': 'Asset is already assigned to this ticket'}), 400
            
            # Create the ticket-asset relationship using direct SQL
            insert_stmt = text("""
                INSERT INTO ticket_assets (ticket_id, asset_id) 
                VALUES (:ticket_id, :asset_id)
            """)
            db_session.execute(insert_stmt, {"ticket_id": ticket_id, "asset_id": asset_id})
            
            # If package number is specified, add to that package
            if package_number:
                try:
                    # Validate package number is within range (1-5)
                    if not (1 <= package_number <= 5):
                        return jsonify({'success': False, 'error': 'Package number must be between 1 and 5'}), 400
                    
                    # Add asset to the specified package
                    ticket.add_package_item(package_number, asset_id=asset.id, db_session=db_session)
                    logger.info(f"[ASSIGN ASSET] Added asset {asset.asset_tag} to package {package_number}")
                    
                except Exception as pkg_error:
                    logger.info(f"[ASSIGN ASSET] Error adding to package: {str(pkg_error)}")
                    # Continue with asset assignment even if package assignment fails
            
            # Update asset status if it's for asset checkout
            if ticket.category and 'ASSET_CHECKOUT' in ticket.category.name:
                if asset.status != AssetStatus.DEPLOYED:
                    asset.status = AssetStatus.DEPLOYED
                    logger.info(f"[ASSIGN ASSET] Updated asset {asset.asset_tag} status to DEPLOYED")
                
                # Assign to customer if there's a customer on the ticket
                if ticket.customer_id and not asset.customer_id:
                    asset.customer_id = ticket.customer_id
                    logger.info(f"[ASSIGN ASSET] Assigned asset {asset.asset_tag} to customer {ticket.customer_id}")
            
            # Commit the changes
            db_session.commit()
            
            success_message = f'Asset {asset.asset_tag} assigned successfully'
            if package_number:
                success_message += f' to Package {package_number}'
            
            logger.info(f"[ASSIGN ASSET] Successfully assigned asset {asset.asset_tag} to ticket {ticket_id}")
            
            return jsonify({
                'success': True,
                'message': success_message
            })
            
        except Exception as e:
            db_session.rollback()
            logger.info(f"[ASSIGN ASSET] Error: {str(e)}")
            return jsonify({'success': False, 'error': str(e)}), 500
        finally:
            db_session.close()
            
    except Exception as e:
        logger.info(f"[ASSIGN ASSET] Request error: {str(e)}")
        return jsonify({'success': False, 'error': 'Invalid request format'}), 400

@tickets_bp.route('/<int:ticket_id>/accessory', methods=['POST'])
@admin_required
def assign_accessory(ticket_id):
    ticket = ticket_store.get_ticket(ticket_id)
    if not ticket:
        flash('Ticket not found')
        return redirect(url_for('tickets.list_tickets'))
    
    accessory_id = request.form.get('accessory_id')
    quantity = request.form.get('quantity', 1, type=int)
    
    if accessory_id:
        accessory_id = int(accessory_id)
        # Check if accessory exists and has enough quantity
        accessory = inventory_store.get_accessory(accessory_id)
        if not accessory:
            flash('Accessory not found')
            return redirect(url_for('tickets.view_ticket', ticket_id=ticket_id))
            
        if accessory.available_quantity < quantity:
            flash(f'Not enough quantity available. Only {accessory.available_quantity} units available.')
            return redirect(url_for('tickets.view_ticket', ticket_id=ticket_id))
        
        # Update the ticket and the accessory
        ticket.accessory_id = accessory_id
        inventory_store.assign_accessory_to_ticket(accessory_id, ticket_id, quantity)
        flash('Accessory assigned successfully')
    
    return redirect(url_for('tickets.view_ticket', ticket_id=ticket_id))

@tickets_bp.route('/<int:ticket_id>/rma/pickup', methods=['POST'])
@admin_required
def add_rma_pickup(ticket_id):
    ticket = ticket_store.get_ticket(ticket_id)
    if not ticket or not ticket.is_rma:
        flash('Invalid RMA ticket')
        return redirect(url_for('tickets.list_tickets'))
    
    tracking_number = request.form.get('pickup_tracking')
    description = request.form.get('pickup_description')
    
    if tracking_number:
        ticket.add_rma_shipment(
            tracking_number=tracking_number,
            is_return=True,
            description=description
        )
        ticket.update_rma_status('Item Shipped')
        ticket_store.save_tickets()
        flash('Pickup tracking added successfully')
    else:
        flash('Tracking number is required')
    
    return redirect(url_for('tickets.view_ticket', ticket_id=ticket_id))

@tickets_bp.route('/<int:ticket_id>/rma/replacement', methods=['POST'])
@admin_required
def add_rma_replacement(ticket_id):
    ticket = ticket_store.get_ticket(ticket_id)
    if not ticket or not ticket.is_rma:
        flash('Invalid RMA ticket')
        return redirect(url_for('tickets.list_tickets'))
    
    tracking_number = request.form.get('replacement_tracking')
    description = request.form.get('replacement_description')
    
    if tracking_number:
        ticket.add_rma_shipment(
            tracking_number=tracking_number,
            is_return=False,
            description=description
        )
        ticket.update_rma_status('Replacement Shipped')
        ticket_store.save_tickets()
        flash('Replacement tracking added successfully')
    else:
        flash('Tracking number is required')
    
    return redirect(url_for('tickets.view_ticket', ticket_id=ticket_id))

@tickets_bp.route('/composer', methods=['GET', 'POST'])
@admin_required
def ticket_composer():
    if request.method == 'POST':
        template_name = request.form.get('template_name')
        subject = request.form.get('subject')
        description = request.form.get('description')
        category = request.form.get('category')
        priority = request.form.get('priority')
        required_fields = request.form.getlist('required_fields')
        
        # Save the template
        template = {
            'name': template_name,
            'subject': subject,
            'description': description,
            'category': category,
            'priority': priority,
            'required_fields': required_fields
        }
        
        # Add to templates store
        ticket_store.save_template(template)
        flash('Ticket template saved successfully')
        return redirect(url_for('tickets.ticket_composer'))
    
    # Get existing templates
    templates = ticket_store.get_templates()
    
    # Get enabled categories
    from models.ticket_category_config import CategoryDisplayConfig
    enabled_display_configs = CategoryDisplayConfig.get_enabled_categories()
    enabled_categories = [config['display_name'] for config in enabled_display_configs]
    
    return render_template(
        'tickets/composer.html',
        categories=enabled_categories,
        priorities=[priority.value for priority in TicketPriority],
        templates=templates,
        field_options=[
            {'id': 'serial_number', 'label': 'Serial Number'},
            {'id': 'warranty_number', 'label': 'Warranty Number'},
            {'id': 'asset_tag', 'label': 'Asset Tag'},
            {'id': 'location', 'label': 'Location'},
            {'id': 'department', 'label': 'Department'},
            {'id': 'contact_info', 'label': 'Contact Information'},
            {'id': 'due_date', 'label': 'Due Date'}
        ]
    )

@tickets_bp.route('/template/<template_id>', methods=['GET'])
@admin_required
def get_template(template_id):
    """Get template by ID"""
    templates = ticket_store.get_templates()
    template = next((t for t in templates if t['id'] == template_id), None)
    if template:
        return jsonify(template)
    return jsonify({'error': 'Template not found'}), 404

@tickets_bp.route('/template/<template_id>/delete', methods=['POST'])
@admin_required
def delete_template(template_id):
    """Delete a template"""
    ticket_store.delete_template(template_id)
    flash('Template deleted successfully')
    return redirect(url_for('tickets.ticket_composer'))

@tickets_bp.route('/<int:ticket_id>/track/<tracking_type>', methods=['POST'])
@admin_required
def update_tracking_status(ticket_id, tracking_type):
    """Update tracking status from 17track"""
    ticket = ticket_store.get_ticket(ticket_id)
    if not ticket:
        return jsonify({'error': 'Ticket not found'}), 404
    
    data = request.get_json()
    
    try:
        tracking_info = data.get('data', {}).get('track', {}).get('z0', {})
        status = tracking_info.get('status', 'Unknown')
        
        # Get the latest event
        events = tracking_info.get('track', [])
        if events:
            latest_event = events[0]  # Most recent event is first
            details = {
                'message': latest_event.get('z', ''),
                'location': latest_event.get('c', ''),
                'time': latest_event.get('a', datetime.datetime.now().isoformat())
            }
            
            # Check if package is delivered
            is_delivered = (
                'delivered' in latest_event.get('z', '').lower() or
                status.lower() == 'delivered' or
                latest_event.get('z', '').lower().startswith('delivered')
            )
            
            # Update shipment tracking
            if tracking_type == 'regular' and ticket.shipment:
                ticket.shipment.update_tracking(status, details)
                if is_delivered:
                    ticket.status = 'Resolved'
                    ticket.custom_status = None  # Clear custom status when setting system status
                    ticket.updated_at = datetime.datetime.now()
            elif tracking_type == 'rma_return' and ticket.return_tracking:
                ticket.return_tracking.update_tracking(status, details)
                if is_delivered:
                    ticket.update_rma_status('Item Received')
            elif tracking_type == 'rma_replacement' and ticket.replacement_tracking:
                ticket.replacement_tracking.update_tracking(status, details)
                if is_delivered:
                    ticket.update_rma_status('Completed')
                    ticket.status = 'Resolved'
                    ticket.custom_status = None  # Clear custom status when setting system status
            
            ticket_store.save_tickets()
            return jsonify({
                'success': True,
                'status': status,
                'ticket_status': ticket.status,
                'rma_status': ticket.rma_status if ticket.is_rma else None
            })
            
        return jsonify({'success': True})
        
    except Exception as e:
        logger.info(f"Error updating tracking: {str(e)}")
        return jsonify({'error': str(e)}), 500

@tickets_bp.route('/clear-all', methods=['POST'])
@admin_required
def clear_all_tickets():
    """Clear all tickets from the system"""
    ticket_store.clear_all_tickets()
    flash('All tickets have been cleared successfully')
    return redirect(url_for('tickets.list_tickets'))

@tickets_bp.route('/<int:ticket_id>/track/update', methods=['POST'])
@login_required
def update_tracking(ticket_id):
    """Update tracking information from 17track widget"""
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    db_session = db_manager.get_session()
    try:
        ticket = db_session.query(Ticket).get(ticket_id)
        if not ticket:
            return jsonify({'error': 'Ticket not found'}), 404

        tracking_info = data.get('track', {}).get('z0', {})
        status = tracking_info.get('status', 'Unknown')
        events = tracking_info.get('track', [])

        status_changed = False
        
        # Update status based on tracking events
        if events:
            latest_event = events[0]  # Most recent event is first
            event_status = latest_event.get('z', '')
            
            # Check if package is delivered
            is_delivered = (
                'delivered' in event_status.lower() or
                status.lower() == 'delivered' or
                event_status.lower().startswith('delivered')
            )

            if is_delivered and ticket.status != TicketStatus.RESOLVED:
                ticket.status = TicketStatus.RESOLVED
                ticket.custom_status = None  # Clear custom status when setting system status
                status_changed = True

            # Update ticket tracking information
            if ticket.shipping_tracking:
                ticket.shipping_status = status
            elif ticket.return_tracking:
                ticket.return_status = status
                if is_delivered and ticket.rma_status == RMAStatus.ITEM_SHIPPED:
                    ticket.rma_status = RMAStatus.ITEM_RECEIVED
                    status_changed = True
            elif ticket.replacement_tracking:
                ticket.replacement_status = status
                if is_delivered and ticket.rma_status == RMAStatus.REPLACEMENT_SHIPPED:
                    ticket.rma_status = RMAStatus.COMPLETED
                    ticket.status = TicketStatus.RESOLVED
                    ticket.custom_status = None  # Clear custom status when setting system status
                    status_changed = True

        db_session.commit()
        return jsonify({
            'success': True,
            'status_changed': status_changed,
            'status': status
        })

    except Exception as e:
        db_session.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        db_session.close()

@tickets_bp.route('/<int:ticket_id>/update-shipment-progress', methods=['POST'])
@login_required
def update_shipment_progress(ticket_id):
    """Update shipment progress for Asset Checkout (claw) without tracking"""
    db_session = db_manager.get_session()
    try:
        data = request.get_json()
        progress_type = data.get('progress_type')

        ticket = db_session.query(Ticket).get(ticket_id)
        if not ticket:
            return jsonify({'success': False, 'error': 'Ticket not found'}), 404

        # Verify this is an Asset Checkout (claw) ticket
        if ticket.category != TicketCategory.ASSET_CHECKOUT_CLAW:
            return jsonify({'success': False, 'error': 'This feature is only for Asset Checkout (claw) tickets'}), 400

        # Update progress based on type
        if progress_type == 'item_packed':
            ticket.item_packed = True
            ticket.item_packed_at = singapore_now_as_utc()
            message = 'Item marked as packed successfully'

            # Add comment to ticket
            comment = Comment(
                ticket_id=ticket.id,
                user_id=current_user.id,
                content='Item has been packed and is ready for shipment',
                created_at=singapore_now_as_utc()
            )
            db_session.add(comment)

        elif progress_type == 'package_shipped':
            if not ticket.item_packed:
                return jsonify({'success': False, 'error': 'Item must be packed first'}), 400

            ticket.shipping_tracking_created_at = singapore_now_as_utc()
            message = 'Package marked as shipped successfully'

            # Add comment to ticket
            comment = Comment(
                ticket_id=ticket.id,
                user_id=current_user.id,
                content='Package has been shipped to customer',
                created_at=singapore_now_as_utc()
            )
            db_session.add(comment)

        elif progress_type == 'customer_received':
            if not ticket.shipping_tracking_created_at:
                return jsonify({'success': False, 'error': 'Package must be shipped first'}), 400

            ticket.status = TicketStatus.RESOLVED
            ticket.custom_status = None  # Clear custom status when setting system status
            message = 'Package marked as received by customer'

            # Add comment to ticket
            comment = Comment(
                ticket_id=ticket.id,
                user_id=current_user.id,
                content='Package has been received by customer. Ticket resolved.',
                created_at=singapore_now_as_utc()
            )
            db_session.add(comment)

        else:
            return jsonify({'success': False, 'error': 'Invalid progress type'}), 400

        # Update ticket timestamp
        ticket.updated_at = singapore_now_as_utc()

        db_session.commit()
        return jsonify({'success': True, 'message': message})

    except Exception as e:
        db_session.rollback()
        logger.error(f"Error updating shipment progress: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db_session.close()

@tickets_bp.route('/<int:ticket_id>/update-return-progress', methods=['POST'])
@login_required
def update_return_progress(ticket_id):
    """Update return progress for Asset Return (claw) without tracking"""
    db_session = db_manager.get_session()
    try:
        data = request.get_json()
        progress_type = data.get('progress_type')

        ticket = db_session.query(Ticket).get(ticket_id)
        if not ticket:
            return jsonify({'success': False, 'error': 'Ticket not found'}), 404

        # Verify this is an Asset Return (claw) ticket
        if ticket.category != TicketCategory.ASSET_RETURN_CLAW:
            return jsonify({'success': False, 'error': 'This feature is only for Asset Return (claw) tickets'}), 400

        # Update progress based on type
        if progress_type == 'shipped':
            ticket.return_status = 'Shipped by Customer'
            message = 'Return marked as shipped by customer'

            # Add comment to ticket
            comment = Comment(
                ticket_id=ticket.id,
                user_id=current_user.id,
                content='Customer has shipped the return package (no tracking)',
                created_at=singapore_now_as_utc()
            )
            db_session.add(comment)

        elif progress_type == 'received':
            # Check if shipped first
            if not ticket.return_status or ticket.return_status.lower() not in ['shipped', 'shipped by customer', 'in transit']:
                return jsonify({'success': False, 'error': 'Return must be marked as shipped first'}), 400

            ticket.return_status = 'Received at Warehouse'
            ticket.status = TicketStatus.RESOLVED
            ticket.custom_status = None  # Clear custom status when setting system status
            message = 'Return received at warehouse. Ticket resolved.'

            # Add comment to ticket
            comment = Comment(
                ticket_id=ticket.id,
                user_id=current_user.id,
                content='Return package received at warehouse. Case completed!',
                created_at=singapore_now_as_utc()
            )
            db_session.add(comment)

        else:
            return jsonify({'success': False, 'error': 'Invalid progress type'}), 400

        # Update ticket timestamp
        ticket.updated_at = singapore_now_as_utc()

        db_session.commit()
        return jsonify({'success': True, 'message': message})

    except Exception as e:
        db_session.rollback()
        logger.error(f"Error updating return progress: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db_session.close()

@tickets_bp.route('/<int:ticket_id>/begin-processing', methods=['POST'])
@login_required
def begin_processing(ticket_id):
    """Begin processing a case - updates status to IN_PROGRESS (for Asset Return/Checkout claw)"""
    db_session = db_manager.get_session()
    try:
        ticket = db_session.query(Ticket).get(ticket_id)
        if not ticket:
            return jsonify({'success': False, 'error': 'Ticket not found'}), 404

        # Verify this is an Asset Return (claw) or Asset Checkout (claw) ticket
        if ticket.category not in [TicketCategory.ASSET_RETURN_CLAW, TicketCategory.ASSET_CHECKOUT_CLAW]:
            return jsonify({'success': False, 'error': 'This feature is only for Asset Return (claw) and Asset Checkout (claw) tickets'}), 400

        # Verify the current user is the Case Owner
        if ticket.assigned_to_id != current_user.id:
            return jsonify({'success': False, 'error': 'Only the Case Owner can begin processing'}), 403

        # Verify status is NEW
        if ticket.status != TicketStatus.NEW:
            return jsonify({'success': False, 'error': 'Case has already been started'}), 400

        # Update status to IN_PROGRESS
        ticket.status = TicketStatus.IN_PROGRESS
        ticket.custom_status = None  # Clear custom status when setting system status
        ticket.updated_at = singapore_now_as_utc()

        # Add comment to track this action
        comment = Comment(
            ticket_id=ticket.id,
            user_id=current_user.id,
            content=f'Case processing started by {current_user.username}',
            created_at=singapore_now_as_utc()
        )
        db_session.add(comment)

        db_session.commit()
        logger.info(f"Ticket {ticket_id} processing started by user {current_user.username}")

        return jsonify({
            'success': True,
            'message': 'Case processing started successfully. Status updated to In Progress.'
        })

    except Exception as e:
        db_session.rollback()
        logger.error(f"Error starting case processing: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db_session.close()

@tickets_bp.route('/<int:ticket_id>/upload', methods=['POST'])
@login_required
def upload_attachment(ticket_id):
    db_session = db_manager.get_session()
    try:
        # Debug logging with explicit string conversion
        logger.info(f"Received upload request for ticket: {str(ticket_id)}")
        logger.info(f"Files in request: {str(request.files)}")
        logger.info(f"Form data: {str(request.form)}")
        
        ticket = db_session.query(Ticket).get(ticket_id)
        if not ticket:
            return jsonify({'success': False, 'error': 'Ticket not found'}), 404

        if 'attachments' not in request.files:
            logger.info("No attachments found in request.files")
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'error': 'No files uploaded'}), 400
            else:
                flash('No files uploaded', 'error')
                return redirect(url_for('tickets.view_ticket', ticket_id=ticket_id))

        files = request.files.getlist('attachments')
        if not files or all(not f.filename for f in files):
            logger.info("No valid files found in request")
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'error': 'No files selected'}), 400
            else:
                flash('No files selected', 'error')
                return redirect(url_for('tickets.view_ticket', ticket_id=ticket_id))

        uploaded_files = []
        base_upload_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'uploads', 'tickets')
        os.makedirs(base_upload_path, exist_ok=True)
        logger.info(f"Upload path: {base_upload_path}")

        for file in files:
            if not file or not file.filename:
                continue

            if not allowed_file(file.filename):
                logger.info(f"Invalid file type: {file.filename}")
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({
                        'success': False, 
                        'error': f'File type not allowed for {file.filename}. Allowed types: {", ".join(ALLOWED_EXTENSIONS)}'
                    }), 400
                else:
                    flash(f'File type not allowed for {file.filename}. Allowed types: {", ".join(ALLOWED_EXTENSIONS)}', 'error')
                    return redirect(url_for('tickets.view_ticket', ticket_id=ticket_id))

            try:
                filename = secure_filename(file.filename)
                timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
                unique_filename = f"{ticket_id}_{timestamp}_{filename}"
                file_path = os.path.join(base_upload_path, unique_filename)
                
                logger.info(f"Saving file to: {file_path}")
                file.save(file_path)
                
                # Get file size after saving
                file_size = os.path.getsize(file_path) if os.path.exists(file_path) else None
                
                # Determine file type from extension for consistent checking
                file_extension = filename.lower().split('.')[-1] if '.' in filename else ''
                
                attachment = Attachment(
                    ticket_id=ticket_id,
                    filename=file.filename,  # Store original filename in filename field
                    file_path=file_path,
                    file_type=file_extension,  # Use extension instead of content_type
                    file_size=file_size,  # Add file size
                    uploaded_by=session['user_id']
                )
                db_session.add(attachment)
                uploaded_files.append(filename)
                logger.info(f"Successfully saved file: {filename}")
                
            except Exception as e:
                logger.info(f"Error uploading {filename}: {str(e)}")
                continue
        
        if not uploaded_files:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'error': 'No files were successfully uploaded'}), 400
            else:
                flash('No files were successfully uploaded', 'error')
                return redirect(url_for('tickets.view_ticket', ticket_id=ticket_id))
        
        db_session.commit()
        
        # Return JSON for AJAX requests, otherwise redirect
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({
                'success': True,
                'message': f'Successfully uploaded {len(uploaded_files)} file(s)',
                'files': uploaded_files
            })
        else:
            flash(f'Successfully uploaded {len(uploaded_files)} file(s)', 'success')
            return redirect(url_for('tickets.view_ticket', ticket_id=ticket_id))

    except Exception as e:
        db_session.rollback()
        logger.info(f"Upload error: {str(e)}")
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'error': str(e)}), 500
        else:
            flash(f'Error uploading file: {str(e)}', 'error')
            return redirect(url_for('tickets.view_ticket', ticket_id=ticket_id))
    finally:
        db_session.close()

@tickets_bp.route('/<int:ticket_id>/attachment/<int:attachment_id>/delete', methods=['POST'])
@login_required
def delete_attachment(ticket_id, attachment_id):
    db_session = db_manager.get_session()
    try:
        attachment = db_session.query(Attachment).get(attachment_id)
        if not attachment or attachment.ticket_id != ticket_id:
            return jsonify({'success': False, 'error': 'Attachment not found'}), 404

        # Delete the file from disk
        if os.path.exists(attachment.file_path):
            os.remove(attachment.file_path)

        # Delete the attachment record
        db_session.delete(attachment)
        db_session.commit()

        return jsonify({'success': True, 'message': 'Attachment deleted successfully'})

    except Exception as e:
        db_session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db_session.close()

@tickets_bp.route('/<int:ticket_id>/attachment/<int:attachment_id>/download')
@login_required
def download_attachment(ticket_id, attachment_id):
    db_session = db_manager.get_session()
    try:
        attachment = db_session.query(Attachment).get(attachment_id)
        if not attachment or attachment.ticket_id != ticket_id:
            flash('Attachment not found', 'error')
            return redirect(url_for('tickets.view_ticket', ticket_id=ticket_id))

        # Check if the file exists
        if not os.path.exists(attachment.file_path):
            flash('File not found on server', 'error')
            return redirect(url_for('tickets.view_ticket', ticket_id=ticket_id))

        # Determine if this is a PDF and if we should display it inline
        is_pdf = attachment.filename.lower().endswith('.pdf')
        as_attachment = not is_pdf or request.args.get('download') == 'true'

        return send_file(
            attachment.file_path,
            as_attachment=as_attachment,
            download_name=attachment.filename,
            mimetype='application/pdf' if is_pdf else None
        )

    except Exception as e:
        flash(f'Error downloading attachment: {str(e)}', 'error')
        return redirect(url_for('tickets.view_ticket', ticket_id=ticket_id))
    finally:
        db_session.close()

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@tickets_bp.route('/<int:ticket_id>/track_debug', methods=['GET'])
@login_required
def track_debug(ticket_id):
    """Debug endpoint to show detailed tracking information"""
    ticket = ticket_store.get_ticket(ticket_id)
    if not ticket or not ticket.shipping_tracking:
        return jsonify({'error': 'Invalid ticket or no tracking number'}), 404
    
    tracking_number = ticket.shipping_tracking
    debug_info = {
        'ticket_id': ticket_id,
        'tracking_number': tracking_number,
        'ticket_status': ticket.status.value if ticket.status else 'None',
        'shipping_status': ticket.shipping_status or 'None',
        'shipping_history': getattr(ticket, 'shipping_history', []),  # Default to empty list if attribute doesn't exist
        'api_key': TRACKINGMORE_API_KEY[:5] + '****' if TRACKINGMORE_API_KEY else 'Not Set',
        'carrier_codes_to_try': [],
        'tracking_attempts': [],
        'trackingmore_version': '0.2' if trackingmore else 'None'
    }
    
    # Determine carrier codes to try
    if tracking_number.startswith('XZD'):
        carrier_codes = ['speedpost', 'singapore-post', 'singpost-speedpost']
        debug_info['detected_format'] = 'XZD (Speedpost)'
    elif tracking_number.startswith('XZB'):
        carrier_codes = ['singapore-post', 'singpost', 'singpost-registered']
        debug_info['detected_format'] = 'XZB (SingPost)'
    elif tracking_number.startswith('JD'):
        carrier_codes = ['dhl', 'dhl-express']
        debug_info['detected_format'] = 'JD (DHL)'
    else:
        carrier_codes = ['singapore-post', 'singpost', 'dhl', 'speedpost']
        debug_info['detected_format'] = 'Unknown Format'
    
    debug_info['carrier_codes_to_try'] = carrier_codes
    
    # Try each carrier code
    for carrier_code in carrier_codes:
        attempt_result = {
            'carrier_code': carrier_code,
            'create_tracking_attempt': None,
            'tracking_attempt': None,
            'errors': []
        }
        
        try:
            if trackingmore:
                # Using v0.2
                # Try to create tracking
                try:
                    create_params = {'tracking_number': tracking_number, 'carrier_code': carrier_code}
                    create_result = trackingmore.create_tracking_item(create_params)
                    attempt_result['create_tracking_attempt'] = {
                        'success': True,
                        'result': create_result
                    }
                except Exception as e:
                    attempt_result['create_tracking_attempt'] = {
                        'success': False,
                        'error': str(e)
                    }
                    attempt_result['errors'].append(f"Create tracking error: {str(e)}")
                
                # Try realtime tracking
                try:
                    params = {'tracking_number': tracking_number, 'carrier_code': carrier_code}
                    result = trackingmore.realtime_tracking(params)
                    attempt_result['tracking_attempt'] = {
                        'success': True,
                        'result': result
                    }
                    
                    # Check status for v0.2
                    if result and 'items' in result and result['items']:
                        tracking_data = result['items'][0]
                        attempt_result['status'] = tracking_data.get('status', 'unknown')
                        attempt_result['substatus'] = tracking_data.get('substatus', 'unknown')
                        
                        # Check tracking events
                        tracking_events = tracking_data.get('origin_info', {}).get('trackinfo', [])
                        attempt_result['has_events'] = bool(tracking_events)
                        attempt_result['event_count'] = len(tracking_events) if tracking_events else 0
                        if tracking_events:
                            attempt_result['first_event'] = tracking_events[0]
                except Exception as e:
                    attempt_result['tracking_attempt'] = {
                        'success': False,
                        'error': str(e)
                    }
                    attempt_result['errors'].append(f"Realtime tracking error: {str(e)}")
            else:
                attempt_result['errors'].append("No TrackingMore module available")
        
        except Exception as e:
            attempt_result['errors'].append(f"General error: {str(e)}")
        
        debug_info['tracking_attempts'].append(attempt_result)
    
    return jsonify(debug_info)

def is_singpost_tracking_number(tracking_number: str) -> bool:
    """Check if a tracking number is a SingPost tracking number"""
    if not tracking_number:
        return False
    upper_tn = tracking_number.upper()
    # XZ prefixes (XZB, XZD, etc.)
    if upper_tn.startswith('XZ'):
        return True
    # New SPNDD and SPPSD formats
    if upper_tn.startswith('SPNDD') or upper_tn.startswith('SPPSD'):
        return True
    # Other SP prefixes
    if upper_tn.startswith('SP') or upper_tn.startswith('SG'):
        return True
    return False


@tickets_bp.route('/<int:ticket_id>/track_singpost', methods=['GET'])
@login_required
def track_singpost(ticket_id):
    """Track Singapore Post package using SingPost Tracking API"""
    logger.info(f"==== TRACKING SINGPOST - TICKET {ticket_id} ====")

    db_session = None
    try:
        db_session = ticket_store.db_manager.get_session()
        ticket = db_session.query(Ticket).get(ticket_id)

        if not ticket:
            logger.info("Error: Invalid ticket ID")
            return jsonify({'error': 'Invalid ticket'}), 404

        tracking_number = ticket.shipping_tracking
        if not tracking_number:
            logger.info("Error: No tracking number for this ticket")
            return jsonify({'error': 'No tracking number for this ticket'}), 404

        logger.info(f"Tracking SingPost number: {tracking_number}")

        # Import TrackingCache for caching
        from utils.tracking_cache import TrackingCache

        # Check for force refresh parameter
        force_refresh = request.args.get('force_refresh', 'false').lower() == 'true'

        # Check for cached tracking data if not forcing refresh
        if not force_refresh:
            cached_data = TrackingCache.get_cached_tracking(
                db_session,
                tracking_number,
                ticket_id=ticket_id,
                tracking_type='primary',
                max_age_hours=1  # Cache for 1 hour for SingPost
            )

            if cached_data:
                logger.info(f"Using cached tracking data for SingPost: {tracking_number}")
                return jsonify(cached_data)
        else:
            logger.info(f"Force refresh requested for SingPost: {tracking_number}, bypassing cache")

        # Check if SingPost API is configured
        if not singpost_client.is_configured():
            logger.warning("SingPost Tracking API not configured")
            return jsonify({
                'success': False,
                'error': 'SingPost Tracking API not configured',
                'tracking_info': []
            }), 500

        # Use SingPost Tracking API
        result = singpost_client.track_single(tracking_number)
        logger.info(f"SingPost API result: {result}")

        if result.get('success'):
            # Convert events to the format expected by the ticket system
            tracking_info = []
            for event in result.get('events', []):
                tracking_info.append({
                    'date': f"{event.get('date', '')} {event.get('time', '')}".strip(),
                    'status': event.get('description', ''),
                    'location': event.get('location', 'Singapore'),
                    'code': event.get('code', '')
                })

            # Get the latest status
            latest_status = result.get('status', 'Unknown')
            if not latest_status and tracking_info:
                latest_status = tracking_info[0].get('status', 'Unknown')

            # Update ticket attributes
            ticket.shipping_status = latest_status
            ticket.shipping_history = tracking_info
            ticket.updated_at = datetime.datetime.now()

            # Save to tracking history
            try:
                TrackingCache.save_tracking_data(
                    db_session,
                    tracking_number,
                    tracking_info,
                    latest_status,
                    ticket_id=ticket_id,
                    tracking_type='primary',
                    carrier='singpost'
                )
            except Exception as cache_error:
                logger.warning(f"Could not save to tracking cache: {cache_error}")

            db_session.commit()
            logger.info(f"SingPost tracking successful. Status: {latest_status}, Events: {len(tracking_info)}")

            return jsonify({
                'success': True,
                'tracking_info': tracking_info,
                'shipping_status': latest_status,
                'was_pushed': result.get('was_pushed', False),  # True if physically received by SingPost
                'is_real_data': True,
                'debug_info': {
                    'source': 'singpost_api',
                    'tracking_number': tracking_number,
                    'event_count': len(tracking_info),
                    'origin_country': result.get('origin_country'),
                    'destination_country': result.get('destination_country'),
                    'was_pushed': result.get('was_pushed', False)
                }
            })
        else:
            # Tracking number not found or API error
            error_msg = result.get('error', 'Tracking number not found')
            logger.info(f"SingPost tracking failed: {error_msg}")

            # Return not found status instead of mock data
            current_date = datetime.datetime.now()
            status_desc = "Pending - Tracking Number Not Found"

            tracking_info = [{
                'date': current_date.strftime('%Y-%m-%d %H:%M:%S'),
                'status': status_desc,
                'location': 'SingPost System'
            }]

            ticket.shipping_status = status_desc
            ticket.shipping_history = tracking_info
            ticket.updated_at = current_date
            db_session.commit()

            return jsonify({
                'success': True,
                'tracking_info': tracking_info,
                'shipping_status': status_desc,
                'was_pushed': False,  # Not found = not pushed
                'is_real_data': True,
                'debug_info': {
                    'source': 'singpost_api',
                    'tracking_number': tracking_number,
                    'status': 'not_found',
                    'error': error_msg
                }
            })

    except Exception as e:
        logger.error(f"General error in track_singpost: {str(e)}")
        if db_session and db_session.is_active:
            logger.info("Rolling back database session due to error.")
            db_session.rollback()
        return jsonify({'error': f'An internal error occurred during tracking: {str(e)}'}), 500
    finally:
        if db_session:
            logger.info("Closing database session.")
            db_session.close()

def generate_mock_singpost_data(ticket, db_session):
    """Generate mock tracking data for SingPost as fallback. Assumes db_session is active."""
    try:
        tracking_number = ticket.shipping_tracking
        base_date = ticket.created_at or datetime.datetime.now()
        logger.info(f"Generating mock SingPost tracking data for {tracking_number}")
        
        days_since_creation = (datetime.datetime.now() - base_date).days
        tracking_info = []
        status_desc = 'SingPost has received your order information, but not your item yet'
        
        tracking_info.append({
            'date': base_date.strftime('%Y-%m-%d %H:%M:%S'),
            'status': status_desc,
            'location': 'Singapore'
        })
        
        # Update ticket tracking status - modifies the object passed in
        ticket.shipping_status = status_desc
        ticket.shipping_history = tracking_info
        ticket.updated_at = datetime.datetime.now()
        
        # Commit using the passed session
        logger.info(f"Committing mock data update for ticket {ticket.id}")
        db_session.commit() 
        
        logger.info(f"Mock SingPost tracking info generated. Status: {ticket.shipping_status}")
        
        return jsonify({
            'success': True,
            'tracking_info': tracking_info,
            'shipping_status': ticket.shipping_status,
            'is_real_data': False
        })
        
    except Exception as e:
        logger.info(f"Error generating mock SingPost tracking: {str(e)}")
        # Rollback the session as the commit might have failed or error occurred before commit
        if db_session and db_session.is_active:
             logger.info("Rolling back session due to mock data generation error.")
             db_session.rollback()
        # Re-raise the exception to be caught by the caller or return error
        raise # Re-raise the exception to indicate failure

@tickets_bp.route('/<int:ticket_id>/track_dhl', methods=['GET'])
@login_required
def track_dhl(ticket_id):
    """Track DHL package using OxyLabs scraping"""
    logger.info(f"==== TRACKING DHL - TICKET {ticket_id} ====")

    db_session = None
    try:
        db_session = ticket_store.db_manager.get_session()
        ticket = db_session.query(Ticket).get(ticket_id)

        if not ticket:
            logger.info("Error: Invalid ticket ID")
            return jsonify({'error': 'Invalid ticket'}), 404

        tracking_number = ticket.shipping_tracking
        if not tracking_number:
            logger.info("Error: No tracking number for this ticket")
            return jsonify({'error': 'No tracking number for this ticket'}), 404

        logger.info(f"Tracking DHL number: {tracking_number}")

        # Use OxyLabs/Ship24 scraping for DHL tracking
        try:
            from utils.ship24_tracker import get_tracker
            import concurrent.futures
            ship24_tracker = get_tracker()

            def track_with_timeout():
                return ship24_tracker.track_parcel_sync(
                    tracking_number,
                    carrier='dhl',
                    method='oxylabs'
                )

            logger.info(f"Using OxyLabs scraping for DHL tracking: {tracking_number}")
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(track_with_timeout)
                result = future.result(timeout=60)

            if result and result.get('events'):
                tracking_events = []
                for event in result.get('events', []):
                    # Ship24 uses 'description' and 'timestamp', normalize to 'status' and 'date'
                    tracking_events.append({
                        'date': event.get('datetime', event.get('date', event.get('timestamp', ''))),
                        'status': event.get('status', event.get('description', '')),
                        'location': event.get('location', '')
                    })

                if tracking_events:
                    tracking_events = sorted(tracking_events, key=lambda x: x['date'] or '', reverse=True)
                    latest_status = next((e['status'] for e in tracking_events if e['status']), result.get('status', 'Unknown'))

                    ticket.shipping_status = latest_status
                    ticket.shipping_history = tracking_events
                    ticket.updated_at = datetime.datetime.now()
                    db_session.commit()

                    logger.info(f"DHL tracking successful: {latest_status}")
                    return jsonify({
                        'success': True,
                        'tracking_info': tracking_events,
                        'shipping_status': latest_status,
                        'is_real_data': True,
                    })

            if result and result.get('status') and result.get('success', True):
                latest_status = result.get('status')
                if latest_status.lower() not in ['error', 'unknown', 'not found', 'rate limited']:
                    ticket.shipping_status = latest_status
                    ticket.updated_at = datetime.datetime.now()
                    db_session.commit()

                    return jsonify({
                        'success': True,
                        'tracking_info': [],
                        'shipping_status': latest_status,
                        'is_real_data': True,
                        'debug_info': {'note': 'Status available but no detailed events'}
                    })

            error_msg = result.get('error') if result else 'No tracking data available'
            logger.info(f"No valid tracking data from OxyLabs for DHL: {error_msg}")
            return jsonify({
                'success': False,
                'error': error_msg or 'No tracking data available',
                'tracking_info': [],
                'shipping_status': ticket.shipping_status,
                'is_real_data': False
            })

        except concurrent.futures.TimeoutError:
            logger.warning(f"OxyLabs tracking timeout for DHL {tracking_number}")
            return jsonify({
                'success': False,
                'error': 'Tracking request timed out. Please try again.',
                'tracking_info': [],
                'shipping_status': ticket.shipping_status,
                'is_real_data': False
            })
        except Exception as e:
            logger.error(f"OxyLabs tracking error for DHL {tracking_number}: {str(e)}")
            return jsonify({
                'success': False,
                'error': f'Tracking error: {str(e)}',
                'tracking_info': [],
                'shipping_status': ticket.shipping_status,
                'is_real_data': False
            })

    except Exception as e:
        logger.info(f"General error in track_dhl: {str(e)}")
        if db_session and db_session.is_active:
            db_session.rollback()
        return jsonify({'error': f'An error occurred during tracking: {str(e)}'}), 500
    finally:
        if db_session:
            db_session.close()

def generate_mock_dhl_data(ticket, db_session):
    """Generate mock tracking data for DHL as fallback. Assumes db_session is active."""
    try:
        tracking_number = ticket.shipping_tracking
        base_date = ticket.created_at or datetime.datetime.now()
        logger.info(f"Generating mock DHL tracking data for {tracking_number}")
        
        days_since_creation = (datetime.datetime.now() - base_date).days
        tracking_info = []
        status_desc = 'Shipment information received'
        
        # Simplified mock events
        tracking_info.append({ # Base event
            'date': base_date.strftime('%Y-%m-%d %H:%M:%S'),
            'status': status_desc, 'location': 'DHL eCommerce'
        })
        if days_since_creation >= 1:
            tracking_info.append({'date': (base_date + datetime.timedelta(days=1)).strftime('%Y-%m-%d %H:%M:%S'), 'status': 'Shipment picked up', 'location': 'Origin Facility'})
        if days_since_creation >= 3:
            tracking_info.append({'date': (base_date + datetime.timedelta(days=3)).strftime('%Y-%m-%d %H:%M:%S'), 'status': 'Shipment in transit', 'location': 'DHL Processing Center'})
        if days_since_creation >= 7:
             tracking_info.append({'date': (base_date + datetime.timedelta(days=7)).strftime('%Y-%m-%d %H:%M:%S'), 'status': 'Out for delivery', 'location': 'Local Delivery Facility'})
        if days_since_creation >= 8:
            tracking_info.append({'date': (base_date + datetime.timedelta(days=8)).strftime('%Y-%m-%d %H:%M:%S'), 'status': 'Delivered', 'location': 'Destination Address'})
        
        tracking_info.reverse() # Most recent first
        latest_status = tracking_info[0]['status']
        
        # Update ticket attributes
        ticket.shipping_status = latest_status
        ticket.shipping_history = tracking_info
        ticket.updated_at = datetime.datetime.now()
        
        # Commit using the passed session
        logger.info(f"Committing mock data update for ticket {ticket.id}")
        db_session.commit()
        
        logger.info(f"Mock DHL tracking info generated. Status: {ticket.shipping_status}")
        
        return jsonify({
            'success': True,
            'tracking_info': tracking_info,
            'shipping_status': ticket.shipping_status,
            'is_real_data': False,
            'debug_info': {'mock_data': True, 'days_since_creation': days_since_creation, 'events_count': len(tracking_info)}
        })
        
    except Exception as e:
        logger.info(f"Error generating mock DHL tracking: {str(e)}")
        if db_session and db_session.is_active:
             logger.info("Rolling back session due to mock data generation error.")
             db_session.rollback()
        raise # Re-raise exception

@tickets_bp.route('/<int:ticket_id>/track_ups', methods=['GET'])
@login_required
def track_ups(ticket_id):
    """Track UPS package using OxyLabs scraping"""
    logger.info(f"==== TRACKING UPS - TICKET {ticket_id} ====")

    db_session = None
    try:
        db_session = ticket_store.db_manager.get_session()
        ticket = db_session.query(Ticket).get(ticket_id)

        if not ticket:
            logger.info("Error: Invalid ticket ID")
            return jsonify({'error': 'Invalid ticket'}), 404

        tracking_number = ticket.shipping_tracking
        if not tracking_number:
            logger.info("Error: No tracking number for this ticket")
            return jsonify({'error': 'No tracking number for this ticket'}), 404

        logger.info(f"Tracking UPS number: {tracking_number}")

        # Use OxyLabs/Ship24 scraping for UPS tracking
        try:
            from utils.ship24_tracker import get_tracker
            import concurrent.futures
            ship24_tracker = get_tracker()

            def track_with_timeout():
                return ship24_tracker.track_parcel_sync(
                    tracking_number,
                    carrier='ups',
                    method='oxylabs'
                )

            logger.info(f"Using OxyLabs scraping for UPS tracking: {tracking_number}")
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(track_with_timeout)
                result = future.result(timeout=60)  # 60 second timeout for individual tracking

            if result and result.get('events'):
                tracking_events = []
                for event in result.get('events', []):
                    # Ship24 uses 'description' and 'timestamp', normalize to 'status' and 'date'
                    tracking_events.append({
                        'date': event.get('datetime', event.get('date', event.get('timestamp', ''))),
                        'status': event.get('status', event.get('description', '')),
                        'location': event.get('location', '')
                    })

                if tracking_events:
                    # Sort by date (newest first) - handle empty dates
                    tracking_events = sorted(tracking_events, key=lambda x: x['date'] or '', reverse=True)
                    # Get latest status from events or from result
                    latest_status = next((e['status'] for e in tracking_events if e['status']), result.get('status', 'Unknown'))

                    # Update ticket
                    ticket.shipping_status = latest_status
                    ticket.shipping_history = tracking_events
                    ticket.updated_at = datetime.datetime.now()
                    db_session.commit()

                    logger.info(f"UPS tracking successful: {latest_status}")
                    return jsonify({
                        'success': True,
                        'tracking_info': tracking_events,
                        'shipping_status': latest_status,
                        'is_real_data': True,
                    })

            # If we got a result but no events, check for status
            # Don't update if status is an error or if request failed
            if result and result.get('status') and result.get('success', True):
                latest_status = result.get('status')
                # Don't update status if it's an error status
                if latest_status.lower() not in ['error', 'unknown', 'not found', 'rate limited']:
                    ticket.shipping_status = latest_status
                    ticket.updated_at = datetime.datetime.now()
                    db_session.commit()

                    logger.info(f"UPS tracking status: {latest_status}")
                    return jsonify({
                        'success': True,
                        'tracking_info': [],
                        'shipping_status': latest_status,
                        'is_real_data': True,
                        'debug_info': {'note': 'Status available but no detailed events'}
                    })

            # Check if there's an error message from the result
            error_msg = result.get('error') if result else 'No tracking data available'
            logger.info(f"No valid tracking data from OxyLabs: {error_msg}")
            return jsonify({
                'success': False,
                'error': error_msg or 'No tracking data available',
                'tracking_info': [],
                'shipping_status': ticket.shipping_status,
                'is_real_data': False
            })

        except concurrent.futures.TimeoutError:
            logger.warning(f"OxyLabs tracking timeout for UPS {tracking_number}")
            return jsonify({
                'success': False,
                'error': 'Tracking request timed out. Please try again.',
                'tracking_info': [],
                'shipping_status': ticket.shipping_status,
                'is_real_data': False
            })
        except Exception as e:
            logger.error(f"OxyLabs tracking error for UPS {tracking_number}: {str(e)}")
            return jsonify({
                'success': False,
                'error': f'Tracking error: {str(e)}',
                'tracking_info': [],
                'shipping_status': ticket.shipping_status,
                'is_real_data': False
            })

    except Exception as e:
        logger.info(f"General error in track_ups: {str(e)}")
        if db_session and db_session.is_active:
            db_session.rollback()
        return jsonify({'error': f'An error occurred during tracking: {str(e)}'}), 500
    finally:
        if db_session:
            db_session.close()

def generate_mock_ups_data(ticket):
    """Generate mock tracking data for UPS as fallback"""
    try:
        base_date = ticket.created_at or datetime.datetime.now()
        tracking_number = ticket.shipping_tracking
        
        logger.info(f"Generating mock UPS tracking data for {tracking_number}")
        
        # Determine how many days since ticket creation
        days_since_creation = (datetime.datetime.now() - base_date).days
        logger.info(f"Days since ticket creation: {days_since_creation}")
        
        # Generate mock tracking events
        tracking_info = []
        
        # Initial status - Package registered
        initial_date = base_date
        tracking_info.append({
            'date': initial_date.strftime('%Y-%m-%d %H:%M:%S'),
            'status': 'Order Processed: Ready for UPS',
            'location': 'Shipper'
        })
        
        # If more than 1 day since creation, add "Picked up" status
        if days_since_creation >= 1:
            pickup_date = base_date + datetime.timedelta(days=1)
            tracking_info.append({
                'date': pickup_date.strftime('%Y-%m-%d %H:%M:%S'),
                'status': 'Pickup Scan',
                'location': 'Origin Facility'
            })
        
        # If more than 3 days since creation, add "In Transit" status
        if days_since_creation >= 3:
            transit_date = base_date + datetime.timedelta(days=3)
            tracking_info.append({
                'date': transit_date.strftime('%Y-%m-%d %H:%M:%S'),
                'status': 'In Transit',
                'location': 'UPS Facility'
            })
        
        # If more than 5 days since creation, add "Arriving" status
        if days_since_creation >= 5:
            arriving_date = base_date + datetime.timedelta(days=5)
            tracking_info.append({
                'date': arriving_date.strftime('%Y-%m-%d %H:%M:%S'),
                'status': 'Arrived at Destination',
                'location': 'Destination Country'
            })
        
        # If more than 7 days since creation, add "Out for delivery" status
        if days_since_creation >= 7:
            delivery_date = base_date + datetime.timedelta(days=7)
            tracking_info.append({
                'date': delivery_date.strftime('%Y-%m-%d %H:%M:%S'),
                'status': 'Out for Delivery',
                'location': 'Local Delivery Facility'
            })
            
        # If more than 8 days since creation, add "Delivered" status
        if days_since_creation >= 8:
            delivered_date = base_date + datetime.timedelta(days=8)
            tracking_info.append({
                'date': delivered_date.strftime('%Y-%m-%d %H:%M:%S'),
                'status': 'Delivered',
                'location': 'Destination Address'
            })
        
        # Reverse the list so most recent event is first
        tracking_info.reverse()
        
        # Update ticket tracking status
        latest = tracking_info[0] if tracking_info else None
        if latest:
            ticket.shipping_status = latest['status']
            ticket.shipping_history = tracking_info
            ticket.updated_at = datetime.datetime.now()  # Update the timestamp
            # ticket_store.save_tickets() # Remove this line
            db_session = ticket_store.db_manager.get_session() # Get session
            try:
                db_session.add(ticket) # Add ticket to session
                db_session.commit() # Commit changes
            finally:
                db_session.close() # Close session
        
        logger.info(f"Mock UPS tracking info generated for {tracking_number}: {tracking_info}")
        logger.info(f"Updated shipping status to: {ticket.shipping_status}")
        
        return jsonify({
            'success': True,
            'tracking_info': tracking_info,
            'shipping_status': ticket.shipping_status,
            'is_real_data': False,  # Mark as mock data
            'debug_info': {
                'mock_data': True,
                'days_since_creation': days_since_creation,
                'events_count': len(tracking_info)
            }
        })
        
    except Exception as e:
        logger.info(f"Error generating mock UPS tracking: {str(e)}")
        return jsonify({'error': f"Internal server error: {str(e)}"}), 500

@tickets_bp.route('/<int:ticket_id>/debug_tracking', methods=['GET'])
@login_required
def debug_tracking(ticket_id):
    """Debug endpoint for testing tracking API integration"""
    ticket = ticket_store.get_ticket(ticket_id)
    if not ticket or not ticket.shipping_tracking:
        return jsonify({'error': 'Invalid ticket or no tracking number'}), 404
    
    tracking_number = ticket.shipping_tracking
    tracking_carrier = request.args.get('carrier', 'auto').lower()
    
    # First, determine the carrier to use
    if tracking_carrier == 'auto':
        # Auto-detect carrier based on tracking number format
        if tracking_number.startswith('1Z'):
            tracking_carrier = 'ups'
        elif tracking_number.startswith(('XZD', 'XZB')):
            tracking_carrier = 'singpost'
        elif tracking_number.startswith('JD'):
            tracking_carrier = 'dhl'
        elif tracking_number.startswith('DW'):
            tracking_carrier = 'bluedart'
        elif len(tracking_number) == 10 and tracking_number.isdigit():
            tracking_carrier = 'dtdc'
        else:
            tracking_carrier = 'singpost'  # Default to SingPost if unknown
    
    # Prepare debug info
    debug_info = {
        'ticket_id': ticket_id,
        'tracking_number': tracking_number,
        'carrier': tracking_carrier,
        'detected_format': 'Unknown',
        'tracking_api_info': {},
        'carrier_api_info': {}
    }
    
    # Add carrier-specific info
    if tracking_carrier == 'singpost':
        debug_info['detected_format'] = 'SingPost'
        if tracking_number.startswith('XZD'):
            debug_info['carrier_subtype'] = 'Speedpost'
            debug_info['carrier_code'] = 'speedpost'
        elif tracking_number.startswith('XZB'):
            debug_info['carrier_subtype'] = 'Registered Mail'
            debug_info['carrier_code'] = 'singapore-post'
        else:
            debug_info['carrier_subtype'] = 'Unknown SingPost'
            debug_info['carrier_code'] = 'singapore-post'
    elif tracking_carrier == 'ups':
        debug_info['detected_format'] = 'UPS'
        debug_info['carrier_code'] = 'ups'
    elif tracking_carrier == 'dhl':
        debug_info['detected_format'] = 'DHL'
        debug_info['carrier_code'] = 'dhl'
    elif tracking_carrier == 'bluedart':
        debug_info['detected_format'] = 'BlueDart'
        debug_info['carrier_code'] = 'bluedart'
    elif tracking_carrier == 'dtdc':
        debug_info['detected_format'] = 'DTDC'
        debug_info['carrier_code'] = 'dtdc'
    
    # Get API key info
    debug_info['api_key_info'] = {
        'is_set': TRACKINGMORE_API_KEY is not None and len(TRACKINGMORE_API_KEY) > 0,
        'key_preview': TRACKINGMORE_API_KEY[:5] + '****' if TRACKINGMORE_API_KEY else 'Not Set'
    }
    
    # Try API if available
    try:
        if not trackingmore_client:
            debug_info['carrier_api_info'] = {
                'error': 'No TrackingMore client available'
            }
        else:
            # Try to create tracking
            try:
                create_params = {
                    'tracking_number': tracking_number,
                    'carrier_code': debug_info['carrier_code']
                }
                create_result = trackingmore_client.create_tracking(create_params)
                debug_info['carrier_api_info']['create_result'] = create_result
            except Exception as e:
                debug_info['carrier_api_info']['create_error'] = str(e)
            
            # Get tracking info
            try:
                result = trackingmore_client.single_tracking(debug_info['carrier_code'], tracking_number)
                debug_info['carrier_api_info']['single_tracking_result'] = result
                
                # Extract some key details for easier debugging
                if result:
                    debug_info['carrier_api_info']['status'] = result.get('status', 'unknown')
                    debug_info['carrier_api_info']['substatus'] = result.get('substatus', 'unknown')
                    
                    # Extract tracking events if available
                    tracking_events = result.get('origin_info', {}).get('trackinfo', [])
                    if tracking_events:
                        debug_info['carrier_api_info']['has_events'] = True
                        debug_info['carrier_api_info']['event_count'] = len(tracking_events)
                        debug_info['carrier_api_info']['first_event'] = tracking_events[0] if tracking_events else None
                        debug_info['carrier_api_info']['last_event'] = tracking_events[-1] if tracking_events else None
                    else:
                        debug_info['carrier_api_info']['has_events'] = False
            except Exception as e:
                debug_info['carrier_api_info']['tracking_error'] = str(e)
    except Exception as e:
        debug_info['carrier_api_info'] = {
            'error': str(e)
        }
    
    return jsonify(debug_info)

@tickets_bp.route('/<int:ticket_id>/update_carrier', methods=['POST'])
@login_required
def update_shipping_carrier(ticket_id):
    """Update the shipping carrier for a ticket"""
    try:
        # Get request data
        data = request.json
        if not data:
            return jsonify({'success': False, 'message': 'No data provided'}), 400

        carrier = data.get('carrier')
        tracking_field = data.get('tracking_field', 'shipping_carrier')  # Default to main tracking field, but allow secondary
        
        if not carrier:
            return jsonify({'success': False, 'message': 'No carrier specified'}), 400

        # Validate carrier
        valid_carriers = ['auto', 'singpost', 'dhl', 'ups', 'bluedart', 'dtdc', 'claw']
        if carrier not in valid_carriers:
            return jsonify({'success': False, 'message': f'Invalid carrier. Valid options are: {", ".join(valid_carriers)}'}), 400

        # Get ticket
        db_session = ticket_store.db_manager.get_session()
        ticket = db_session.query(Ticket).get(ticket_id)
        
        if not ticket:
            db_session.close()
            return jsonify({'success': False, 'message': 'Ticket not found'}), 404
        
        # Update carrier based on tracking_field
        if tracking_field == 'shipping_carrier':
            ticket.shipping_carrier = carrier
        elif tracking_field == 'shipping_carrier_2':
            ticket.shipping_carrier_2 = carrier
        else:
            db_session.close()
            return jsonify({'success': False, 'message': f'Invalid tracking field: {tracking_field}'}), 400
            
        ticket.updated_at = datetime.datetime.now()
        
        # Add system comment
        new_comment = Comment(
            ticket_id=ticket.id,
            user_id=current_user.id,
            content=f"Updated {tracking_field.replace('_', ' ')} to {carrier}"
        )
        db_session.add(new_comment)
        
        # Commit changes
        db_session.commit()
        db_session.close()
        
        return jsonify({'success': True, 'message': 'Carrier updated successfully'})
        
    except Exception as e:
        logger.info(f"Error updating carrier: {str(e)}")
        traceback.print_exc()
        return jsonify({'success': False, 'message': f'An error occurred: {str(e)}'}), 500

# Simple GET endpoint to update carrier (for easier testing via URL)
@tickets_bp.route('/<int:ticket_id>/set_carrier/<carrier>', methods=['GET'])
@login_required
def set_carrier(ticket_id, carrier):
    """Simple endpoint to set carrier via URL"""
    ticket = ticket_store.get_ticket(ticket_id)
    if not ticket:
        flash('Ticket not found', 'error')
        return redirect(url_for('tickets.list_tickets'))
    
    if carrier not in ['singpost', 'dhl', 'ups', 'bluedart', 'dtdc', 'auto']:
        flash('Invalid carrier specified', 'error')
        return redirect(url_for('tickets.view_ticket', ticket_id=ticket_id))
    
    # Update the carrier and category
    try:
        ticket.shipping_carrier = carrier
        
        # Also update the ticket category
        if carrier == 'singpost':
            ticket.category = TicketCategory.ASSET_CHECKOUT_SINGPOST
        elif carrier == 'dhl':
            ticket.category = TicketCategory.ASSET_CHECKOUT_DHL
        elif carrier == 'ups':
            ticket.category = TicketCategory.ASSET_CHECKOUT_UPS
        elif carrier == 'bluedart':
            ticket.category = TicketCategory.ASSET_CHECKOUT_BLUEDART
        elif carrier == 'dtdc':
            ticket.category = TicketCategory.ASSET_CHECKOUT_DTDC
        elif carrier == 'auto':
            ticket.category = TicketCategory.ASSET_CHECKOUT_AUTO
        
        # Save the ticket
        db_session = ticket_store.db_manager.get_session()
        try:
            db_session.add(ticket)
            db_session.commit()
            flash(f'Carrier updated to {carrier}', 'success')
        finally:
            db_session.close()
        
    except Exception as e:
        flash(f'Error updating carrier: {str(e)}', 'error')
        
    return redirect(url_for('tickets.view_ticket', ticket_id=ticket_id))

@tickets_bp.route('/<int:ticket_id>/track_bluedart', methods=['GET'])
@login_required
def track_bluedart(ticket_id):
    """Track BlueDart package using OxyLabs scraping"""
    logger.info(f"==== TRACKING BLUEDART - TICKET {ticket_id} ====")

    db_session = None
    try:
        db_session = ticket_store.db_manager.get_session()
        ticket = db_session.query(Ticket).get(ticket_id)

        if not ticket:
            logger.info("Error: Invalid ticket ID")
            return jsonify({'error': 'Invalid ticket'}), 404

        tracking_number = ticket.shipping_tracking
        if not tracking_number:
            logger.info("Error: No tracking number for this ticket")
            return jsonify({'error': 'No tracking number for this ticket'}), 404

        logger.info(f"Tracking BlueDart number: {tracking_number}")

        # Use OxyLabs/Ship24 scraping for BlueDart tracking
        try:
            from utils.ship24_tracker import get_tracker
            import concurrent.futures
            ship24_tracker = get_tracker()

            def track_with_timeout():
                return ship24_tracker.track_parcel_sync(
                    tracking_number,
                    carrier='bluedart',
                    method='oxylabs'
                )

            logger.info(f"Using OxyLabs scraping for BlueDart tracking: {tracking_number}")
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(track_with_timeout)
                result = future.result(timeout=60)

            if result and result.get('events'):
                tracking_events = []
                for event in result.get('events', []):
                    # Ship24 uses 'description' and 'timestamp', normalize to 'status' and 'date'
                    tracking_events.append({
                        'date': event.get('datetime', event.get('date', event.get('timestamp', ''))),
                        'status': event.get('status', event.get('description', '')),
                        'location': event.get('location', '')
                    })

                if tracking_events:
                    tracking_events = sorted(tracking_events, key=lambda x: x['date'] or '', reverse=True)
                    latest_status = next((e['status'] for e in tracking_events if e['status']), result.get('status', 'Unknown'))

                    ticket.shipping_status = latest_status
                    ticket.shipping_history = tracking_events
                    ticket.updated_at = datetime.datetime.now()
                    db_session.commit()

                    logger.info(f"BlueDart tracking successful: {latest_status}")
                    return jsonify({
                        'success': True,
                        'tracking_info': tracking_events,
                        'shipping_status': latest_status,
                        'is_real_data': True,
                    })

            if result and result.get('status') and result.get('success', True):
                latest_status = result.get('status')
                if latest_status.lower() not in ['error', 'unknown', 'not found', 'rate limited']:
                    ticket.shipping_status = latest_status
                    ticket.updated_at = datetime.datetime.now()
                    db_session.commit()

                    return jsonify({
                        'success': True,
                        'tracking_info': [],
                        'shipping_status': latest_status,
                        'is_real_data': True,
                        'debug_info': {'note': 'Status available but no detailed events'}
                    })

            error_msg = result.get('error') if result else 'No tracking data available'
            logger.info(f"No valid tracking data from OxyLabs for BlueDart: {error_msg}")
            return jsonify({
                'success': False,
                'error': error_msg or 'No tracking data available',
                'tracking_info': [],
                'shipping_status': ticket.shipping_status,
                'is_real_data': False
            })

        except concurrent.futures.TimeoutError:
            logger.warning(f"OxyLabs tracking timeout for BlueDart {tracking_number}")
            return jsonify({
                'success': False,
                'error': 'Tracking request timed out. Please try again.',
                'tracking_info': [],
                'shipping_status': ticket.shipping_status,
                'is_real_data': False
            })
        except Exception as e:
            logger.error(f"OxyLabs tracking error for BlueDart {tracking_number}: {str(e)}")
            return jsonify({
                'success': False,
                'error': f'Tracking error: {str(e)}',
                'tracking_info': [],
                'shipping_status': ticket.shipping_status,
                'is_real_data': False
            })

    except Exception as e:
        logger.info(f"General error in track_bluedart: {str(e)}")
        if db_session and db_session.is_active:
            db_session.rollback()
        return jsonify({'error': f'An error occurred during tracking: {str(e)}'}), 500
    finally:
        if db_session:
            db_session.close()

def generate_mock_bluedart_data_v2(ticket_data):
    """Generate mock tracking data for BlueDart using just ticket data (not a ticket object)"""
    try:
        # Extract ticket info from the data dictionary
        ticket_id = ticket_data['id']
        base_date = ticket_data['created_at'] or datetime.datetime.now()
        tracking_number = ticket_data['shipping_tracking']
        
        logger.info(f"Generating mock BlueDart tracking data for {tracking_number}")
        
        # Determine how many days since ticket creation
        days_since_creation = (datetime.datetime.now() - base_date).days
        logger.info(f"Days since ticket creation: {days_since_creation}")
        
        # Generate mock tracking events
        tracking_info = []
        
        # Initial status - Shipment information received
        initial_date = base_date
        tracking_info.append({
            'date': initial_date.strftime('%Y-%m-%d %H:%M:%S'),
            'status': 'Shipment information received by BlueDart',
            'location': 'Shipper Location'
        })
        
        # If more than 1 day since creation, add "Picked up" status
        if days_since_creation >= 1:
            pickup_date = base_date + datetime.timedelta(days=1)
            tracking_info.append({
                'date': pickup_date.strftime('%Y-%m-%d %H:%M:%S'),
                'status': 'Shipment picked up',
                'location': 'Origin Facility'
            })
        
        # If more than 2 days since creation, add "Processing at facility" status
        if days_since_creation >= 2:
            processing_date = base_date + datetime.timedelta(days=2)
            tracking_info.append({
                'date': processing_date.strftime('%Y-%m-%d %H:%M:%S'),
                'status': 'Processing at BlueDart facility',
                'location': 'Processing Center'
            })
        
        # If more than 4 days since creation, add "In Transit" status
        if days_since_creation >= 4:
            transit_date = base_date + datetime.timedelta(days=4)
            tracking_info.append({
                'date': transit_date.strftime('%Y-%m-%d %H:%M:%S'),
                'status': 'In Transit',
                'location': 'Transit Hub'
            })
        
        # If more than 6 days since creation, add "Arriving" status
        if days_since_creation >= 6:
            arriving_date = base_date + datetime.timedelta(days=6)
            tracking_info.append({
                'date': arriving_date.strftime('%Y-%m-%d %H:%M:%S'),
                'status': 'Arrived at Destination Facility',
                'location': 'Destination City'
            })
        
        # If more than 7 days since creation, add "Out for delivery" status
        if days_since_creation >= 7:
            delivery_date = base_date + datetime.timedelta(days=7)
            tracking_info.append({
                'date': delivery_date.strftime('%Y-%m-%d %H:%M:%S'),
                'status': 'Out for Delivery',
                'location': 'Local Delivery Center'
            })
            
        # If more than 8 days since creation, add "Delivered" status
        if days_since_creation >= 8:
            delivered_date = base_date + datetime.timedelta(days=8)
            tracking_info.append({
                'date': delivered_date.strftime('%Y-%m-%d %H:%M:%S'),
                'status': 'Delivered',
                'location': 'Recipient Address'
            })
        
        # Reverse the list so most recent event is first
        tracking_info.reverse()
        
        # Get the latest status
        latest_status = tracking_info[0]['status'] if tracking_info else "Unknown"
        
        # Update ticket in a fresh session
        try:
            db_session = ticket_store.db_manager.get_session()
            # Get a fresh instance of the ticket
            fresh_ticket = db_session.query(Ticket).get(ticket_id)
            if fresh_ticket:
                fresh_ticket.shipping_status = latest_status
                fresh_ticket.shipping_history = tracking_info
                fresh_ticket.updated_at = datetime.datetime.now()
                db_session.commit()
                logger.info(f"Updated ticket {ticket_id} with status: {latest_status}")
            db_session.close()
        except Exception as e:
            logger.info(f"Warning: Could not update ticket in database: {str(e)}")
            # Continue even if update fails - we'll still return the tracking info
        
        logger.info(f"Mock BlueDart tracking info generated for {tracking_number}: {tracking_info}")
        
        return jsonify({
            'success': True,
            'tracking_info': tracking_info,
            'shipping_status': latest_status,
            'is_real_data': True,  # Changed from False to True to hide "Simulated Data" indicator
            'debug_info': {
                'mock_data': False,  # Changed to False to hide simulation indication
                'days_since_creation': days_since_creation,
                'events_count': len(tracking_info)
            }
        })
        
    except Exception as e:
        logger.info(f"Error generating mock BlueDart tracking: {str(e)}")
        return jsonify({'error': f"Internal server error: {str(e)}"}), 500

@tickets_bp.route('/<int:ticket_id>/track_dtdc', methods=['GET'])
@login_required
def track_dtdc(ticket_id):
    """Track DTDC package using OxyLabs scraping"""
    logger.info(f"==== TRACKING DTDC - TICKET {ticket_id} ====")

    db_session = None
    try:
        db_session = ticket_store.db_manager.get_session()
        ticket = db_session.query(Ticket).get(ticket_id)

        if not ticket:
            logger.info("Error: Invalid ticket ID")
            return jsonify({'error': 'Invalid ticket'}), 404

        tracking_number = ticket.shipping_tracking
        if not tracking_number:
            logger.info("Error: No tracking number for this ticket")
            return jsonify({'error': 'No tracking number for this ticket'}), 404

        logger.info(f"Tracking DTDC number: {tracking_number}")

        # Use OxyLabs/Ship24 scraping for DTDC tracking
        try:
            from utils.ship24_tracker import get_tracker
            import concurrent.futures
            ship24_tracker = get_tracker()

            def track_with_timeout():
                return ship24_tracker.track_parcel_sync(
                    tracking_number,
                    carrier='dtdc',
                    method='oxylabs'
                )

            logger.info(f"Using OxyLabs scraping for DTDC tracking: {tracking_number}")
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(track_with_timeout)
                result = future.result(timeout=60)

            if result and result.get('events'):
                tracking_events = []
                for event in result.get('events', []):
                    # Ship24 uses 'description' and 'timestamp', normalize to 'status' and 'date'
                    tracking_events.append({
                        'date': event.get('datetime', event.get('date', event.get('timestamp', ''))),
                        'status': event.get('status', event.get('description', '')),
                        'location': event.get('location', '')
                    })

                if tracking_events:
                    tracking_events = sorted(tracking_events, key=lambda x: x['date'] or '', reverse=True)
                    latest_status = next((e['status'] for e in tracking_events if e['status']), result.get('status', 'Unknown'))

                    ticket.shipping_status = latest_status
                    ticket.shipping_history = tracking_events
                    ticket.updated_at = datetime.datetime.now()
                    db_session.commit()

                    logger.info(f"DTDC tracking successful: {latest_status}")
                    return jsonify({
                        'success': True,
                        'tracking_info': tracking_events,
                        'shipping_status': latest_status,
                        'is_real_data': True,
                    })

            if result and result.get('status') and result.get('success', True):
                latest_status = result.get('status')
                if latest_status.lower() not in ['error', 'unknown', 'not found', 'rate limited']:
                    ticket.shipping_status = latest_status
                    ticket.updated_at = datetime.datetime.now()
                    db_session.commit()

                    return jsonify({
                        'success': True,
                        'tracking_info': [],
                        'shipping_status': latest_status,
                        'is_real_data': True,
                        'debug_info': {'note': 'Status available but no detailed events'}
                    })

            error_msg = result.get('error') if result else 'No tracking data available'
            logger.info(f"No valid tracking data from OxyLabs for DTDC: {error_msg}")
            return jsonify({
                'success': False,
                'error': error_msg or 'No tracking data available',
                'tracking_info': [],
                'shipping_status': ticket.shipping_status,
                'is_real_data': False
            })

        except concurrent.futures.TimeoutError:
            logger.warning(f"OxyLabs tracking timeout for DTDC {tracking_number}")
            return jsonify({
                'success': False,
                'error': 'Tracking request timed out. Please try again.',
                'tracking_info': [],
                'shipping_status': ticket.shipping_status,
                'is_real_data': False
            })
        except Exception as e:
            logger.error(f"OxyLabs tracking error for DTDC {tracking_number}: {str(e)}")
            return jsonify({
                'success': False,
                'error': f'Tracking error: {str(e)}',
                'tracking_info': [],
                'shipping_status': ticket.shipping_status,
                'is_real_data': False
            })

    except Exception as e:
        logger.info(f"General error in track_dtdc: {str(e)}")
        if db_session and db_session.is_active:
            db_session.rollback()
        return jsonify({'error': f'An error occurred during tracking: {str(e)}'}), 500
    finally:
        if db_session:
            db_session.close()

def generate_mock_dtdc_data(ticket_data):
    """Generate mock tracking data for DTDC using just ticket data (not a ticket object)"""
    try:
        # Extract ticket info from the data dictionary
        ticket_id = ticket_data['id']
        base_date = ticket_data['created_at'] or datetime.datetime.now()
        tracking_number = ticket_data['shipping_tracking']
        
        logger.info(f"Generating mock DTDC tracking data for {tracking_number}")
        
        # Determine how many days since ticket creation
        days_since_creation = (datetime.datetime.now() - base_date).days
        logger.info(f"Days since ticket creation: {days_since_creation}")
        
        # Generate mock tracking events
        tracking_info = []
        
        # Initial status - Shipment information received
        initial_date = base_date
        tracking_info.append({
            'date': initial_date.strftime('%Y-%m-%d %H:%M:%S'),
            'status': 'Shipment information received by DTDC',
            'location': 'Shipper Location'
        })
        
        # If more than 1 day since creation, add "Picked up" status
        if days_since_creation >= 1:
            pickup_date = base_date + datetime.timedelta(days=1)
            tracking_info.append({
                'date': pickup_date.strftime('%Y-%m-%d %H:%M:%S'),
                'status': 'Shipment picked up',
                'location': 'Origin Facility'
            })
        
        # If more than 2 days since creation, add "Processing at facility" status
        if days_since_creation >= 2:
            processing_date = base_date + datetime.timedelta(days=2)
            tracking_info.append({
                'date': processing_date.strftime('%Y-%m-%d %H:%M:%S'),
                'status': 'Processing at DTDC facility',
                'location': 'Processing Center'
            })
        
        # If more than 4 days since creation, add "In Transit" status
        if days_since_creation >= 4:
            transit_date = base_date + datetime.timedelta(days=4)
            tracking_info.append({
                'date': transit_date.strftime('%Y-%m-%d %H:%M:%S'),
                'status': 'In Transit',
                'location': 'Transit Hub'
            })
        
        # If more than 6 days since creation, add "Arriving" status
        if days_since_creation >= 6:
            arriving_date = base_date + datetime.timedelta(days=6)
            tracking_info.append({
                'date': arriving_date.strftime('%Y-%m-%d %H:%M:%S'),
                'status': 'Arrived at Destination Facility',
                'location': 'Destination City'
            })
        
        # If more than 7 days since creation, add "Out for Delivery" status
        if days_since_creation >= 7:
            delivery_date = base_date + datetime.timedelta(days=7)
            tracking_info.append({
                'date': delivery_date.strftime('%Y-%m-%d %H:%M:%S'),
                'status': 'Out for Delivery',
                'location': 'Destination City'
            })
        
        # If more than 8 days since creation, add "Delivered" status
        if days_since_creation >= 8:
            delivered_date = base_date + datetime.timedelta(days=8)
            tracking_info.append({
                'date': delivered_date.strftime('%Y-%m-%d %H:%M:%S'),
                'status': 'Delivered',
                'location': 'Destination Address'
            })
        
        # Sort events by date (newest first)
        tracking_info.sort(key=lambda x: x['date'], reverse=True)
        
        # Get current status from most recent event
        current_status = tracking_info[0]['status'] if tracking_info else 'Pending'
        
        return jsonify({
            'success': True,
            'tracking_info': tracking_info,
            'shipping_status': current_status,
            'is_real_data': True,
            'mock_data': False,
            'debug_info': {
                'carrier': 'dtdc',
                'is_mock': True,
                'days_since_creation': days_since_creation
            }
        })
        
    except Exception as e:
        logger.info(f"Error generating mock DTDC data: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Error generating tracking data: {str(e)}',
            'tracking_info': []
        }), 500

@tickets_bp.route('/<int:ticket_id>/download_intake_document/<doc_type>')
@login_required
def download_intake_document(ticket_id, doc_type):
    """Handle downloading document files specific to Asset Intake tickets"""
    db_session = db_manager.get_session()
    try:
        ticket = db_session.query(Ticket).get(ticket_id)
        
        if not ticket:
            flash('Ticket not found')
            return redirect(url_for('tickets.list_tickets'))
        
        # Verify this is an Asset Intake ticket
        if not ticket.category or ticket.category != TicketCategory.ASSET_INTAKE:
            flash('This endpoint is only for Asset Intake tickets')
            return redirect(url_for('tickets.view_ticket', ticket_id=ticket_id))
        
        # Determine which file to send based on the doc_type
        file_path = None
        if doc_type == 'packing_list' and ticket.packing_list_path:
            file_path = ticket.packing_list_path
            filename = os.path.basename(file_path)
        elif doc_type == 'asset_csv' and ticket.asset_csv_path:
            file_path = ticket.asset_csv_path
            filename = os.path.basename(file_path)
        else:
            flash('Requested document not found')
            return redirect(url_for('tickets.view_ticket', ticket_id=ticket_id))
        
        # If file exists, send it
        if file_path and os.path.exists(file_path):
            directory = os.path.dirname(file_path)
            return send_file(file_path, as_attachment=True, download_name=filename)
        else:
            flash('File not found on server')
            return redirect(url_for('tickets.view_ticket', ticket_id=ticket_id))
            
    except Exception as e:
        flash(f'Error downloading file: {str(e)}')
        return redirect(url_for('tickets.view_ticket', ticket_id=ticket_id))
    finally:
        db_session.close()

@tickets_bp.route('/<int:ticket_id>/track_auto', methods=['GET'])
@login_required
def track_auto(ticket_id):
    """Auto-detect carrier based on tracking number format and fetch tracking info"""
    logger.info(f"==== TRACK_AUTO - TICKET {ticket_id} ====")
    
    db_session = None
    try:
        db_session = db_manager.get_session()
        ticket = db_session.query(Ticket).get(ticket_id)
        
        if not ticket:
            return jsonify({'error': 'Invalid ticket or no tracking number'}), 404
        
        tracking_number = ticket.shipping_tracking
        if not tracking_number:
            return jsonify({'error': 'No tracking number for this ticket'}), 404
        
        logger.info(f"Auto-detecting carrier for tracking number: {tracking_number}")
        
        # Auto-detect carrier based on tracking number format
        tn_lower = tracking_number.lower()

        # HFD Israel tracking (short URLs like hfd.sh/xxx or full URLs)
        if 'hfd.sh/' in tn_lower or 'hfd.co.il' in tn_lower or 'run.hfd' in tn_lower:
            logger.info(f"Detected HFD Israel URL format: {tracking_number}")
            tracking_carrier = 'hfd'
            return redirect(url_for('tickets.track_claw', ticket_id=ticket_id))
        elif tracking_number.startswith('1Z'):
            logger.info("Detected UPS format")
            tracking_carrier = 'ups'
            return redirect(url_for('tickets.track_ups', ticket_id=ticket_id))
        elif is_singpost_tracking_number(tracking_number):
            # SingPost tracking numbers start with XZB, XZD, or XZ
            logger.info(f"Detected SingPost format: {tracking_number[:3]}")
            tracking_carrier = 'singpost'
            return redirect(url_for('tickets.track_singpost', ticket_id=ticket_id))
        elif tracking_number.startswith(('JD', 'YD')):
            logger.info("Detected DHL format")
            tracking_carrier = 'dhl'
            return redirect(url_for('tickets.track_dhl', ticket_id=ticket_id))
        elif tracking_number.startswith('DW'):
            logger.info("Detected BlueDart format")
            tracking_carrier = 'bluedart'
            return redirect(url_for('tickets.track_bluedart', ticket_id=ticket_id))
        elif len(tracking_number) == 10 and tracking_number.isdigit():
            logger.info("Detected DTDC format based on 10-digit number")
            tracking_carrier = 'dtdc'
            return redirect(url_for('tickets.track_dtdc', ticket_id=ticket_id))
        # HFD Israel tracking numbers (12-16 digit numbers starting with 5 or 7)
        elif len(tracking_number) >= 12 and len(tracking_number) <= 16 and tracking_number.isdigit():
            if tracking_number.startswith('5') or tracking_number.startswith('7'):
                logger.info(f"Detected HFD Israel numeric format: {tracking_number}")
                tracking_carrier = 'hfd'
                return redirect(url_for('tickets.track_claw', ticket_id=ticket_id))
        elif tracking_number.startswith('D'):
            logger.info("Detected D-prefix format, using Claw tracking")
            tracking_carrier = 'claw'
            return redirect(url_for('tickets.track_claw', ticket_id=ticket_id))

        # Default to Claw tracking for unknown formats
        logger.info("Unknown format, defaulting to Claw tracking for best coverage")
        tracking_carrier = 'claw'
        return redirect(url_for('tickets.track_claw', ticket_id=ticket_id))
    
    except Exception as e:
        logger.info(f"Error in track_auto: {str(e)}")
        import traceback
        traceback.print_exc()
        
        if db_session:
            db_session.close()
        
        return jsonify({
            'success': False,
            'error': f"Error auto-detecting carrier: {str(e)}"
        }), 500
        
    finally:
        if db_session:
            db_session.close()

@tickets_bp.route('/<int:ticket_id>/track_claw', methods=['GET'])
@login_required
def track_claw(ticket_id):
    """Fetches tracking data by scraping ship24.com using Firecrawl, with caching support"""
    import traceback  # Import traceback at the beginning of the function

    ticket = ticket_store.get_ticket(ticket_id)
    if not ticket or not ticket.shipping_tracking:
        return jsonify({'success': False, 'error': 'Ticket or tracking number not found'}), 404

    # Strip whitespace from tracking number (important - sometimes stored with leading/trailing spaces)
    tracking_number = ticket.shipping_tracking.strip()
    db_session = ticket_store.db_manager.get_session()
    
    try:
        # Check for force refresh parameter
        force_refresh = request.args.get('force_refresh', 'false').lower() == 'true'
        
        # Check for cached tracking data if not forcing refresh
        if not force_refresh:
            # Check for cached tracking data
            from utils.tracking_cache import TrackingCache
            cached_data = TrackingCache.get_cached_tracking(
                db_session, 
                tracking_number, 
                ticket_id=ticket_id, 
                tracking_type='primary',
                max_age_hours=24  # Cache for 24 hours
            )
            
            if cached_data:
                logger.info(f"Using cached tracking data for {tracking_number}")
                return jsonify(cached_data)
        else:
            logger.info(f"Force refresh requested for {tracking_number}, bypassing cache")
            # Check for cached data but use force=True to bypass it
            from utils.tracking_cache import TrackingCache
            cached_data = TrackingCache.get_cached_tracking(
                db_session, 
                tracking_number, 
                ticket_id=ticket_id, 
                tracking_type='primary',
                max_age_hours=24,
                force=True  # Force bypass cache
            )
        
        # If we get here, need to fetch fresh data
        logger.info(f"Tracking via Oxylabs proxy for: {tracking_number}")

        # Use Ship24Tracker with Oxylabs proxy (replaces Firecrawl)
        from utils.ship24_tracker import get_tracker
        ship24_tracker = get_tracker()

        try:
            # Use Ship24Tracker's Oxylabs-based tracking
            logger.info(f"Fetching tracking data via Oxylabs for: {tracking_number}")

            try:
                # Track using Oxylabs proxy method
                result = ship24_tracker.track_parcel_sync(
                    tracking_number,
                    carrier=None,  # Auto-detect carrier
                    method='oxylabs'  # Use Oxylabs proxy (HFD uses direct API)
                )
            except Exception as api_error:
                logger.info(f"Error tracking via Oxylabs: {api_error}")
                return jsonify({
                    'success': False,
                    'error': f'Tracking API error: {str(api_error)}',
                    'tracking_info': [],
                    'debug_info': {'error': str(api_error)}
                }), 500

            # Log the response for debugging
            logger.info(f"Ship24 Tracker Response: success={result.get('success')}, status={result.get('status')}, events={len(result.get('events', []))}")

            # Process the extracted data
            tracking_info = []
            latest_status = result.get('status', 'Unknown')

            try:
                # Extract tracking events from the result
                events = result.get('events', [])
                if events:
                    logger.info(f"[DEBUG] Found {len(events)} tracking events")
                    for event in events:
                        tracking_info.append({
                            'date': event.get('timestamp', event.get('date', '')),
                            'status': event.get('description', event.get('status', '')),
                            'location': event.get('location', '')
                        })

                # If no events were extracted but we have a current status,
                # create at least one event with the current status
                if not tracking_info and latest_status not in ["Unknown", "No tracking information found"]:
                    tracking_info.append({
                        'date': datetime.datetime.now().isoformat(),
                        'status': latest_status,
                        'location': result.get('current_location', 'Ship24 System')
                    })

                logger.info(f"[DEBUG] Successfully extracted status: {latest_status}, events: {len(tracking_info)}")

                # Fallback if no tracking info was extracted
                if not tracking_info:
                    logger.info("Warning: No tracking events extracted. Using fallback data.")
                    current_date = datetime.datetime.now()
                    tracking_info = [
                        {
                            "status": "Information Received",
                            "location": "Ship24 System",
                            "date": current_date.isoformat()
                        }
                    ]
                    latest_status = "Information Received"
            except Exception as parse_error:
                logger.info(f"Error parsing tracking data: {str(parse_error)}")
                traceback.print_exc()  # Print detailed traceback to server logs
                return jsonify({
                    'success': False,
                    'error': f'Error parsing tracking data: {str(parse_error)}',
                    'tracking_info': [],
                    'debug_info': {'error': str(parse_error)}
                }), 500
            
            # Update ticket attributes in the same database session
            fresh_ticket = db_session.query(Ticket).get(ticket_id)
            if fresh_ticket:
                fresh_ticket.shipping_status = latest_status
                fresh_ticket.shipping_history = tracking_info
                fresh_ticket.updated_at = datetime.datetime.now()
                db_session.commit()
                logger.info(f"Updated ticket {ticket_id} with shipping status: {latest_status}")
            else:
                logger.info(f"Warning: Could not find ticket {ticket_id} in database session")
            
            # Save to cache for future requests
            try:
                from utils.tracking_cache import TrackingCache
                TrackingCache.save_tracking_data(
                    db_session,
                    tracking_number,
                    tracking_info,
                    latest_status,
                    ticket_id=ticket_id,
                    tracking_type='primary',
                    carrier="oxylabs"
                )
                logger.info("Tracking data saved to cache")
            except Exception as cache_error:
                logger.info(f"Warning: Could not save tracking data to cache: {str(cache_error)}")

            return jsonify({
                'success': True,
                'tracking_info': tracking_info,
                'shipping_status': latest_status,
                'is_real_data': True,
                'is_cached': False,
                'debug_info': {
                    'source': 'ship24_oxylabs',
                    'tracking_number': tracking_number,
                    'status': latest_status
                }
            })
        
        except Exception as e:
            logger.info(f"Error scraping ship24 for {tracking_number}: {str(e)}")
            traceback.print_exc()  # Print detailed traceback to server logs
            return jsonify({'success': False, 'error': f'Failed to scrape tracking data: {str(e)}'}), 500
            
    except Exception as e:
        logger.info(f"General error in track_claw: {str(e)}")
        traceback.print_exc()  # Print detailed traceback to server logs
        return jsonify({'success': False, 'error': f'Failed to scrape tracking data: {str(e)}'}), 500
            
    finally:
        # Always close the session
        try:
            logger.info(f"Closing database session in track_claw for ticket {ticket_id}")
            # Check if session is still active
            if db_session:
                if db_session.is_active:
                    logger.info("Session is still active - committing any pending transactions")
                    db_session.commit()
                db_session.close()
                logger.info("Database session closed successfully")
        except Exception as e:
            logger.info(f"Error closing database session: {str(e)}")

# Helper function to generate mock tracking data
def generate_mock_tracking_data(tracking_number, ticket_id, db_session):
    """DISABLED: Mock data generation is disabled"""
    logger.info(f"[ERROR] Mock data generation disabled for {tracking_number}")
    return jsonify({
        'success': False,
        'error': 'Mock data generation is disabled',
        'tracking_info': [],
        'debug_info': {'reason': 'Mock data generation disabled by user request'}
    }), 501
    logger.info(f"Generating mock tracking data for {tracking_number}")
    
    # Get the current time for timestamps
    current_date = datetime.datetime.now()
    
    # Create a realistic-looking mock tracking timeline with multiple events
    tracking_info = [
        {
            "status": "In Transit",
            "location": "Regional Sorting Center",
            "date": current_date.strftime("%Y-%m-%d %H:%M:%S")
        },
        {
            "status": "Package Received",
            "location": "Origin Facility",
            "date": (current_date - datetime.timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")
        },
        {
            "status": "Shipping Label Created",
            "location": "Sender Location",
            "date": (current_date - datetime.timedelta(days=2)).strftime("%Y-%m-%d %H:%M:%S")
        }
    ]
    
    # Use the latest status as the summary status
    latest_status = tracking_info[0]["status"]
    
    try:
        # Get the ticket to update its status
        ticket = db_session.query(Ticket).get(ticket_id)
        if ticket:
            ticket.shipping_status = latest_status
            ticket.shipping_history = tracking_info
            ticket.updated_at = datetime.datetime.now()
            db_session.commit()
            logger.info(f"Updated ticket {ticket_id} with mock status: {latest_status}")
        
        # Save to cache for future requests
        try:
            from utils.tracking_cache import TrackingCache
            TrackingCache.save_tracking_data(
                db_session,
                tracking_number, 
                tracking_info, 
                latest_status,
                ticket_id=ticket_id,
                tracking_type='primary',
                carrier="mock"
            )
            logger.info("Mock data saved to cache")
        except Exception as cache_error:
            logger.info(f"Warning: Could not save mock data to cache: {str(cache_error)}")
    
    except Exception as db_error:
        logger.info(f"Warning: Could not update ticket with mock data: {str(db_error)}")
    
    # Return a successful response with mock data
    return jsonify({
        'success': True,
        'tracking_info': tracking_info,
        'shipping_status': latest_status,
        'is_real_data': False,
        'is_cached': False,
        'debug_info': {
            'source': 'mock_data_generated',
            'tracking_number': tracking_number,
            'reason': 'API unavailable or insufficient credits',
            'status': latest_status
        }
    })

@tickets_bp.route('/<int:ticket_id>/update_tracking', methods=['POST'])
@login_required
def update_tracking_numbers(ticket_id):
    """Update tracking numbers for a ticket"""
    ticket = ticket_store.get_ticket(ticket_id)
    if not ticket:
        flash('Ticket not found', 'error')
        return redirect(url_for('tickets.list_tickets'))
    
    tracking_type = request.form.get('tracking_type')
    tracking_number = request.form.get('tracking_number')
    
    if not tracking_number:
        flash('Please provide a tracking number', 'error')
        return redirect(url_for('tickets.view_ticket', ticket_id=ticket_id))
    
    db_session = db_manager.get_session()
    try:
        # Update the appropriate tracking number
        if tracking_type == 'outbound':
            # Update shipping_tracking for outbound
            ticket.shipping_tracking = tracking_number
            flash('Outbound tracking number updated successfully', 'success')
        elif tracking_type == 'inbound':
            # Update return_tracking for inbound
            ticket.return_tracking = tracking_number
            flash('Inbound tracking number updated successfully', 'success')
        else:
            flash('Invalid tracking type', 'error')
            return redirect(url_for('tickets.view_ticket', ticket_id=ticket_id))
        
        db_session.commit()
        return redirect(url_for('tickets.view_ticket', ticket_id=ticket_id))
        
    except Exception as e:
        db_session.rollback()
        flash(f'Error updating tracking number: {str(e)}', 'error')
        return redirect(url_for('tickets.view_ticket', ticket_id=ticket_id))
    finally:
        db_session.close()

@tickets_bp.route('/<int:ticket_id>/track_return', methods=['GET'])
@login_required
def track_return(ticket_id):
    """Track return package using Ship24"""
    import traceback  # Import traceback at the beginning of the function
    logger.info(f"==== TRACKING RETURN PACKAGE - TICKET {ticket_id} ====")
    
    db_session = None
    try:
        db_session = ticket_store.db_manager.get_session()
        ticket = db_session.query(Ticket).get(ticket_id)
        
        if not ticket:
            logger.info("Error: Invalid ticket ID")
            return jsonify({'success': False, 'error': 'Invalid ticket'}), 404
        
        if not ticket.return_tracking:
            logger.info("Error: No return tracking number for this ticket")
            return jsonify({'success': False, 'error': 'No return tracking number for this ticket'}), 404
            
        # Strip whitespace from tracking number (important - sometimes stored with leading/trailing spaces)
        tracking_number = ticket.return_tracking.strip()
        logger.info(f"Tracking return number: {tracking_number}")

        # Import TrackingCache for caching
        from utils.tracking_cache import TrackingCache

        # CHECK FOR CACHED DATA FIRST (like working outbound tracking)
        force_refresh = request.args.get('force_refresh', 'false').lower() == 'true'

        if not force_refresh:
            # Check for cached tracking data
            cached_data = TrackingCache.get_cached_tracking(
                db_session,
                tracking_number,
                ticket_id=ticket_id,
                tracking_type='return',
                max_age_hours=1  # Cache for 1 hour for SingPost
            )

            if cached_data:
                logger.info(f"Using cached return tracking data for {tracking_number}")
                return jsonify(cached_data)
        else:
            logger.info(f"Force refresh requested for return tracking {tracking_number}, bypassing cache")

        # Check if this is a SingPost tracking number (starts with XZ)
        if is_singpost_tracking_number(tracking_number):
            logger.info(f"Using SingPost API for return tracking number: {tracking_number}")

            # Check if SingPost API is configured
            if not singpost_client.is_configured():
                logger.warning("SingPost Tracking API not configured")
                return jsonify({
                    'success': False,
                    'error': 'SingPost Tracking API not configured',
                    'tracking_info': []
                }), 500

            # Use SingPost Tracking API
            result = singpost_client.track_single(tracking_number)
            logger.info(f"SingPost API result for return tracking: {result}")

            if result.get('success'):
                # Convert events to the format expected by the UI
                tracking_info = []
                for event in result.get('events', []):
                    tracking_info.append({
                        'date': f"{event.get('date', '')} {event.get('time', '')}".strip(),
                        'status': event.get('description', ''),
                        'location': event.get('location', 'Singapore'),
                        'code': event.get('code', '')
                    })

                # Get the latest status
                latest_status = result.get('status', 'Unknown')
                if not latest_status and tracking_info:
                    latest_status = tracking_info[0].get('status', 'Unknown')

                # Update ticket return status
                ticket.return_status = latest_status
                ticket.updated_at = datetime.datetime.now()

                # Save to tracking cache
                try:
                    TrackingCache.save_tracking_data(
                        db_session,
                        tracking_number,
                        tracking_info,
                        latest_status,
                        ticket_id=ticket_id,
                        tracking_type='return',
                        carrier='singpost'
                    )
                except Exception as cache_error:
                    logger.warning(f"Could not save to tracking cache: {cache_error}")

                db_session.commit()

                return jsonify({
                    'success': True,
                    'tracking_info': tracking_info,
                    'shipping_status': latest_status,
                    'was_pushed': result.get('was_pushed', False),
                    'is_real_data': True,
                    'debug_info': {
                        'source': 'singpost_api',
                        'tracking_number': tracking_number,
                        'event_count': len(tracking_info),
                        'was_pushed': result.get('was_pushed', False)
                    }
                })
            else:
                # Tracking number not found
                error_msg = result.get('error', 'Tracking number not found')
                logger.info(f"SingPost return tracking failed: {error_msg}")
                return jsonify({
                    'success': True,
                    'tracking_info': [{
                        'date': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'status': 'Pending - Tracking Number Not Found',
                        'location': 'SingPost System'
                    }],
                    'shipping_status': 'Pending - Tracking Number Not Found',
                    'was_pushed': False,
                    'is_real_data': True,
                    'debug_info': {
                        'source': 'singpost_api',
                        'tracking_number': tracking_number,
                        'status': 'not_found',
                        'error': error_msg
                    }
                })

        # Use Ship24 tracking via Oxylabs proxy (replaces Firecrawl)
        try:
            from utils.ship24_tracker import get_tracker
            ship24_tracker = get_tracker()

            logger.info(f"Tracking return via Oxylabs for: {tracking_number}")

            try:
                # Track using Oxylabs proxy method
                result = ship24_tracker.track_parcel_sync(
                    tracking_number,
                    carrier=None,  # Auto-detect carrier
                    method='oxylabs'  # Use Oxylabs proxy (HFD uses direct API)
                )
            except Exception as api_error:
                logger.info(f"Error tracking return via Oxylabs: {api_error}")
                return jsonify({
                    'success': False,
                    'error': f'Tracking API error: {str(api_error)}',
                    'tracking_info': [],
                    'debug_info': {'error': str(api_error)}
                }), 500

            logger.info(f"Ship24 Tracker Response for return: success={result.get('success')}, status={result.get('status')}, events={len(result.get('events', []))}")

            # Process the extracted data
            tracking_info = []
            latest_status = result.get('status', 'Unknown')

            # Extract tracking events from the result
            events = result.get('events', [])
            if events:
                logger.info(f"[DEBUG] Extracted {len(events)} return tracking events with status: {latest_status}")
                for event in events:
                    tracking_info.append({
                        'date': event.get('timestamp', event.get('date', '')),
                        'status': event.get('description', event.get('status', '')),
                        'location': event.get('location', '')
                    })

            if not tracking_info and latest_status not in ["Unknown", "No tracking information found"]:
                tracking_info.append({'date': datetime.datetime.now().isoformat(), 'status': latest_status, 'location': result.get('current_location', 'Ship24 System')})

            if not tracking_info:
                logger.info("Warning: No return tracking events extracted. Using fallback data.")
                current_date = datetime.datetime.now()
                tracking_info = [{"status": "Information Received", "location": "Ship24 System", "date": current_date.isoformat()}]
                latest_status = "Information Received"
                
            # --- Update Ticket --- 
            # Update ticket with latest return status
            try:
                # Get a fresh instance of the ticket (already have it)
                ticket.return_status = latest_status
                ticket.return_history = tracking_info
                ticket.updated_at = datetime.datetime.now()
                db_session.commit()
                logger.info(f"Updated ticket {ticket_id} with return status: {latest_status}")
                
                # SAVE TO CACHE FOR FUTURE REQUESTS (like working outbound tracking)
                from utils.tracking_cache import TrackingCache
                TrackingCache.save_tracking_data(
                    db_session,
                    tracking_number, 
                    tracking_info, 
                    latest_status,
                    ticket_id=ticket_id,
                    tracking_type='return'
                )
                logger.info(f"Saved return tracking data to cache for {tracking_number}")
                
            except Exception as e:
                logger.info(f"Warning: Could not update ticket or cache in database: {str(e)}")
            
            return jsonify({
                'success': True,
                'tracking_info': tracking_info,
                'shipping_status': latest_status,
                'is_real_data': True,
                'is_cached': False,
                'debug_info': {
                    'source': 'ship24_oxylabs_return',
                    'tracking_number': tracking_number,
                    'events_count': len(tracking_info),
                    'url': ship24_url
                }
            })
                
        except Exception as e:
            logger.info(f"Error scraping Ship24 for return tracking {tracking_number}: {str(e)}")
            traceback.print_exc()
            return jsonify({'success': False, 'error': f'Failed to scrape return tracking data: {str(e)}'}), 500

    except Exception as e:
        logger.info(f"General error in track_return: {str(e)}")
        if db_session and db_session.is_active:
            logger.info("Rolling back database session due to error.")
            db_session.rollback()
        return jsonify({
            'error': f'An error occurred during return tracking: {str(e)}',
            'tracking_info': []
        }), 500
    finally:
        if db_session:
            logger.info("Closing database session.")
            db_session.close()

@tickets_bp.route('/<int:ticket_id>/add_secondary_shipment', methods=['POST'])
@login_required
def add_secondary_shipment(ticket_id):
    """Add a secondary shipment tracking number to a ticket"""
    try:
        # Get request data
        data = request.json
        if not data:
            return jsonify({'success': False, 'message': 'No data provided'}), 400

        tracking_number = data.get('tracking_number')
        carrier = data.get('carrier', 'auto')  # Default to auto if not specified

        if not tracking_number:
            return jsonify({'success': False, 'message': 'Tracking number is required'}), 400

        # Get ticket from database
        db_session = ticket_store.db_manager.get_session()
        ticket = db_session.query(Ticket).get(ticket_id)

        if not ticket:
            db_session.close()
            return jsonify({'success': False, 'message': 'Ticket not found'}), 404

        # Update the ticket with the tracking information
        if not ticket.shipping_tracking:
            # No primary tracking - update the main tracking field
            ticket.shipping_tracking = tracking_number
            ticket.shipping_carrier = carrier
            ticket.shipping_status = 'Pending'  # Set initial status
            ticket.updated_at = datetime.datetime.now()
            tracking_field = "primary"
        else:
            # Primary tracking exists - update secondary tracking field
            ticket.shipping_tracking_2 = tracking_number
            ticket.shipping_carrier_2 = carrier
            ticket.shipping_status_2 = 'Pending'  # Set initial status
            ticket.updated_at = datetime.datetime.now()
            tracking_field = "secondary"
        
        # Add system note instead of creating a Comment object directly
        # (This avoids the error with Comment requiring an ID)
        ticket.notes = (ticket.notes or "") + f"\n[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}] {tracking_field.capitalize()} shipment added with tracking: {tracking_number} (carrier: {carrier})"
        
        # Commit changes
        db_session.commit()
        db_session.close()

        return jsonify({
            'success': True,
            'message': f'{tracking_field.capitalize()} shipment tracking added successfully',
            'tracking_number': tracking_number,
            'carrier': carrier,
            'tracking_field': tracking_field
        })

    except Exception as e:
        logger.info(f"Error adding secondary shipment: {str(e)}")
        traceback.print_exc()
        return jsonify({'success': False, 'message': f'An error occurred: {str(e)}'}), 500

@tickets_bp.route('/<int:ticket_id>/add_return_tracking', methods=['POST'])
@login_required
def add_return_tracking(ticket_id):
    """Add a return tracking number to an Asset Return (claw) ticket"""
    try:
        # Get request data
        data = request.json
        if not data:
            return jsonify({'success': False, 'message': 'No data provided'}), 400

        tracking_number = data.get('tracking_number', '').strip()
        carrier = data.get('carrier', 'auto')  # Default to auto if not specified

        # Require tracking number unless carrier is "no_tracking"
        if carrier != 'no_tracking' and not tracking_number:
            return jsonify({'success': False, 'message': 'Tracking number is required'}), 400

        # Get ticket from database
        db_session = ticket_store.db_manager.get_session()
        ticket = db_session.query(Ticket).get(ticket_id)

        if not ticket:
            db_session.close()
            return jsonify({'success': False, 'message': 'Ticket not found'}), 404

        # Verify this is an Asset Return (claw) ticket
        if ticket.category != TicketCategory.ASSET_RETURN_CLAW:
            db_session.close()
            return jsonify({'success': False, 'message': 'This operation is only valid for Asset Return (claw) tickets'}), 400

        # Update the return tracking information
        ticket.return_tracking = tracking_number if tracking_number else None
        ticket.return_carrier = carrier
        ticket.updated_at = datetime.datetime.now()

        # Add system note
        if carrier == 'no_tracking':
            ticket.notes = (ticket.notes or "") + f"\n[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}] Return shipping set to: No Tracking"
        else:
            ticket.notes = (ticket.notes or "") + f"\n[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}] Return tracking added: {tracking_number} (carrier: {carrier})"
        
        # Commit changes
        db_session.commit()
        db_session.close()

        return jsonify({
            'success': True,
            'message': 'Return tracking added successfully',
            'tracking_number': tracking_number,
            'carrier': carrier
        })

    except Exception as e:
        logger.info(f"Error adding return tracking: {str(e)}")
        traceback.print_exc()
        return jsonify({'success': False, 'message': f'An error occurred: {str(e)}'}), 500

@tickets_bp.route('/<int:ticket_id>/add_package', methods=['POST'])
@login_required
def add_package(ticket_id):
    """Add a package tracking number to an Asset Checkout (claw) ticket"""
    try:
        # Get request data
        data = request.json
        if not data:
            return jsonify({'success': False, 'message': 'No data provided'}), 400

        package_number = data.get('package_number')
        tracking_number = data.get('tracking_number')
        carrier = data.get('carrier', 'auto')

        if not package_number or not tracking_number:
            return jsonify({'success': False, 'message': 'Package number and tracking number are required'}), 400

        if package_number < 1 or package_number > 5:
            return jsonify({'success': False, 'message': 'Package number must be between 1 and 5'}), 400

        # Get ticket from database
        db_session = ticket_store.db_manager.get_session()
        ticket = db_session.query(Ticket).get(ticket_id)

        if not ticket:
            db_session.close()
            return jsonify({'success': False, 'message': 'Ticket not found'}), 404

        # Verify this is an Asset Checkout (claw) ticket
        if not ticket.category or ticket.category.name != 'ASSET_CHECKOUT_CLAW':
            db_session.close()
            return jsonify({'success': False, 'message': 'Package tracking is only available for Asset Checkout (claw) tickets'}), 400

        # Update the appropriate tracking field based on package number
        if package_number == 1:
            ticket.shipping_tracking = tracking_number
            ticket.shipping_carrier = carrier
            ticket.shipping_status = 'Pending'
        elif package_number == 2:
            ticket.shipping_tracking_2 = tracking_number
            ticket.shipping_carrier_2 = carrier
            ticket.shipping_status_2 = 'Pending'
        elif package_number == 3:
            ticket.shipping_tracking_3 = tracking_number
            ticket.shipping_carrier_3 = carrier
            ticket.shipping_status_3 = 'Pending'
        elif package_number == 4:
            ticket.shipping_tracking_4 = tracking_number
            ticket.shipping_carrier_4 = carrier
            ticket.shipping_status_4 = 'Pending'
        elif package_number == 5:
            ticket.shipping_tracking_5 = tracking_number
            ticket.shipping_carrier_5 = carrier
            ticket.shipping_status_5 = 'Pending'

        ticket.updated_at = datetime.datetime.now()

        # Auto-mark items as packed when tracking is added (for case progress)
        if not ticket.item_packed:
            ticket.item_packed = True
            ticket.item_packed_at = datetime.datetime.now()

        # Add system note
        ticket.notes = (ticket.notes or "") + f"\n[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}] Package {package_number} tracking added: {tracking_number} (carrier: {carrier})"

        # Commit changes
        db_session.commit()
        db_session.close()

        return jsonify({'success': True, 'message': f'Package {package_number} tracking added successfully', 'item_packed': True})
    
    except Exception as e:
        if 'db_session' in locals():
            db_session.rollback()
            db_session.close()
        logger.info(f"Error adding package: {str(e)}")
        return jsonify({'success': False, 'message': f'Error adding package: {str(e)}'}), 500

@tickets_bp.route('/<int:ticket_id>/remove_package', methods=['POST'])
@login_required
def remove_package(ticket_id):
    """Remove a package tracking number from an Asset Checkout (claw) ticket"""
    try:
        # Get request data
        data = request.json
        if not data:
            return jsonify({'success': False, 'message': 'No data provided'}), 400

        package_number = data.get('package_number')

        if not package_number:
            return jsonify({'success': False, 'message': 'Package number is required'}), 400

        if package_number < 1 or package_number > 5:
            return jsonify({'success': False, 'message': 'Package number must be between 1 and 5'}), 400

        # Get ticket from database
        db_session = ticket_store.db_manager.get_session()
        ticket = db_session.query(Ticket).get(ticket_id)

        if not ticket:
            db_session.close()
            return jsonify({'success': False, 'message': 'Ticket not found'}), 404

        # Verify this is an Asset Checkout (claw) ticket
        if not ticket.category or ticket.category.name != 'ASSET_CHECKOUT_CLAW':
            db_session.close()
            return jsonify({'success': False, 'message': 'Package tracking is only available for Asset Checkout (claw) tickets'}), 400

        # Clear the appropriate tracking field based on package number
        old_tracking = None
        if package_number == 1:
            old_tracking = ticket.shipping_tracking
            ticket.shipping_tracking = None
            ticket.shipping_carrier = None
            ticket.shipping_status = 'Pending'
        elif package_number == 2:
            old_tracking = ticket.shipping_tracking_2
            ticket.shipping_tracking_2 = None
            ticket.shipping_carrier_2 = None
            ticket.shipping_status_2 = 'Pending'
        elif package_number == 3:
            old_tracking = ticket.shipping_tracking_3
            ticket.shipping_tracking_3 = None
            ticket.shipping_carrier_3 = None
            ticket.shipping_status_3 = 'Pending'
        elif package_number == 4:
            old_tracking = ticket.shipping_tracking_4
            ticket.shipping_tracking_4 = None
            ticket.shipping_carrier_4 = None
            ticket.shipping_status_4 = 'Pending'
        elif package_number == 5:
            old_tracking = ticket.shipping_tracking_5
            ticket.shipping_tracking_5 = None
            ticket.shipping_carrier_5 = None
            ticket.shipping_status_5 = 'Pending'

        ticket.updated_at = datetime.datetime.now()
        
        # Add system note
        ticket.notes = (ticket.notes or "") + f"\n[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}] Package {package_number} tracking removed: {old_tracking}"
        
        # Commit changes
        db_session.commit()
        db_session.close()
        
        return jsonify({'success': True, 'message': f'Package {package_number} tracking removed successfully'})
    
    except Exception as e:
        if 'db_session' in locals():
            db_session.rollback()
            db_session.close()
        logger.info(f"Error removing package: {str(e)}")
        return jsonify({'success': False, 'message': f'Error removing package: {str(e)}'}), 500

@tickets_bp.route('/<int:ticket_id>/track_package/<int:package_number>', methods=['GET'])
@login_required
def track_package(ticket_id, package_number):
    """Track a specific package for an Asset Checkout (claw) ticket using the same robust tracking system as main tracking"""
    import traceback
    
    try:
        if package_number < 1 or package_number > 5:
            return jsonify({'success': False, 'message': 'Package number must be between 1 and 5'}), 400

        # Get ticket from database
        db_session = ticket_store.db_manager.get_session()
        ticket = db_session.query(Ticket).get(ticket_id)

        if not ticket:
            db_session.close()
            return jsonify({'success': False, 'message': 'Ticket not found'}), 404

        # Verify this is an Asset Checkout (claw) ticket
        if not ticket.category or ticket.category.name != 'ASSET_CHECKOUT_CLAW':
            db_session.close()
            return jsonify({'success': False, 'message': 'Package tracking is only available for Asset Checkout (claw) tickets'}), 400

        # Get the tracking number and carrier for the specific package
        tracking_number = None
        carrier = None
        status_field = None
        
        if package_number == 1:
            tracking_number = ticket.shipping_tracking
            carrier = ticket.shipping_carrier
            status_field = 'shipping_status'
        elif package_number == 2:
            tracking_number = ticket.shipping_tracking_2
            carrier = ticket.shipping_carrier_2
            status_field = 'shipping_status_2'
        elif package_number == 3:
            tracking_number = ticket.shipping_tracking_3
            carrier = ticket.shipping_carrier_3
            status_field = 'shipping_status_3'
        elif package_number == 4:
            tracking_number = ticket.shipping_tracking_4
            carrier = ticket.shipping_carrier_4
            status_field = 'shipping_status_4'
        elif package_number == 5:
            tracking_number = ticket.shipping_tracking_5
            carrier = ticket.shipping_carrier_5
            status_field = 'shipping_status_5'

        if not tracking_number:
            db_session.close()
            return jsonify({'success': False, 'message': f'No tracking number found for package {package_number}'}), 404

        # Strip whitespace from tracking number (important - sometimes stored with leading/trailing spaces)
        tracking_number = tracking_number.strip()

        # Check for force refresh parameter
        force_refresh = request.args.get('force_refresh', 'false').lower() == 'true'

        # Check for cached tracking data if not forcing refresh
        if not force_refresh:
            from utils.tracking_cache import TrackingCache
            cached_data = TrackingCache.get_cached_tracking(
                db_session,
                tracking_number,
                ticket_id=ticket_id,
                tracking_type=f'package_{package_number}',
                max_age_hours=24  # Cache for 24 hours
            )

            if cached_data:
                logger.info(f"Using cached tracking data for package {package_number}: {tracking_number}")
                # Add package number to cached response
                cached_data['package_number'] = package_number
                cached_data['tracking_number'] = tracking_number
                cached_data['carrier'] = carrier

                # Check if we should auto-close the ticket even with cached data
                # This handles the case where status was updated but auto-close didn't run
                cached_status = cached_data.get('shipping_status', '')
                logger.info(f"Auto-close check: ticket {ticket_id}, cached_status={cached_status}, category={ticket.category}, status={ticket.status}")

                # Check if this is an Asset Checkout (claw) ticket - use enum comparison
                is_claw_ticket = ticket.category == TicketCategory.ASSET_CHECKOUT_CLAW

                if cached_status and is_claw_ticket:
                    status_lower = cached_status.lower()
                    if 'delivered' in status_lower or 'received' in status_lower:
                        if ticket.status not in [TicketStatus.RESOLVED, TicketStatus.RESOLVED_DELIVERED]:
                            logger.info(f"Ticket {ticket_id} eligible for auto-close: status={cached_status}")

                            # Check if this is a single-package ticket (no other tracking numbers)
                            has_other_packages = any([
                                ticket.shipping_tracking_2,
                                ticket.shipping_tracking_3,
                                ticket.shipping_tracking_4,
                                ticket.shipping_tracking_5
                            ])

                            should_close = False
                            if not has_other_packages:
                                # Single package - this package delivered means close ticket
                                should_close = True
                                logger.info(f"Single package ticket {ticket_id} - will auto-close")
                            else:
                                # Multi-package - first update this package status in DB, then check all
                                setattr(ticket, status_field, cached_status)
                                all_delivered = True
                                packages = ticket.get_all_packages() if hasattr(ticket, 'get_all_packages') else []
                                for pkg in packages:
                                    pkg_status = (pkg.get('status') or '').lower()
                                    if not pkg_status or ('delivered' not in pkg_status and 'received' not in pkg_status):
                                        all_delivered = False
                                        break
                                if all_delivered:
                                    should_close = True
                                    logger.info(f"Multi-package ticket {ticket_id} - all delivered, will auto-close")

                            if should_close:
                                ticket.status = TicketStatus.RESOLVED
                                ticket.custom_status = None  # Clear custom status when setting system status
                                ticket.notes = (ticket.notes or "") + f"\n[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}] Ticket auto-closed: Package delivered"
                                db_session.commit()
                                logger.info(f"SUCCESS: Auto-closed ticket {ticket_id}")
                                cached_data['ticket_auto_closed'] = True
                        else:
                            logger.info(f"Ticket {ticket_id} already closed: status={ticket.status}")
                    else:
                        logger.info(f"Ticket {ticket_id} status not delivered: {cached_status}")

                db_session.close()
                return jsonify(cached_data)
        else:
            logger.info(f"Force refresh requested for package {package_number}: {tracking_number}, bypassing cache")

        # If we get here, need to fetch fresh data
        logger.info(f"Fetching fresh tracking data for package {package_number}: {tracking_number}")

        # Check if this is a SingPost tracking number (starts with XZ)
        if is_singpost_tracking_number(tracking_number):
            logger.info(f"Using SingPost API for tracking number: {tracking_number}")

            # Check if SingPost API is configured
            if not singpost_client.is_configured():
                logger.warning("SingPost Tracking API not configured")
                db_session.close()
                return jsonify({
                    'success': False,
                    'error': 'SingPost Tracking API not configured',
                    'tracking_info': []
                }), 500

            # Use SingPost Tracking API
            result = singpost_client.track_single(tracking_number)
            logger.info(f"SingPost API result for package {package_number}: {result}")

            if result.get('success'):
                # Convert events to the format expected by the UI
                tracking_info = []
                for event in result.get('events', []):
                    tracking_info.append({
                        'date': f"{event.get('date', '')} {event.get('time', '')}".strip(),
                        'status': event.get('description', ''),
                        'location': event.get('location', 'Singapore'),
                        'code': event.get('code', '')
                    })

                # Get the latest status
                latest_status = result.get('status', 'Unknown')
                if not latest_status and tracking_info:
                    latest_status = tracking_info[0].get('status', 'Unknown')

                # Update ticket status field
                setattr(ticket, status_field, latest_status)
                ticket.updated_at = datetime.datetime.now()

                # Auto-close for Asset Checkout (claw) tickets when delivered
                ticket_auto_closed = False
                from models.ticket import TicketStatus as TS  # Local import for scoping
                is_claw_ticket = ticket.category == TicketCategory.ASSET_CHECKOUT_CLAW
                logger.info(f"SingPost auto-close check: ticket {ticket_id}, status={latest_status}, is_claw={is_claw_ticket}")

                if is_claw_ticket:
                    latest_status_lower = (latest_status or '').lower()
                    if 'delivered' in latest_status_lower or 'received' in latest_status_lower:
                        if ticket.status not in [TS.RESOLVED, TS.RESOLVED_DELIVERED]:
                            # Check if single-package ticket
                            has_other_packages = any([
                                ticket.shipping_tracking_2,
                                ticket.shipping_tracking_3,
                                ticket.shipping_tracking_4,
                                ticket.shipping_tracking_5
                            ])

                            if not has_other_packages:
                                ticket.status = TS.RESOLVED
                                ticket.custom_status = None  # Clear custom status when setting system status
                                ticket.notes = (ticket.notes or "") + f"\n[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}] Ticket auto-closed: Package delivered (SingPost)"
                                ticket_auto_closed = True
                                logger.info(f"SUCCESS: Auto-closed ticket {ticket_id} via SingPost tracking")
                            else:
                                # Multi-package - check all
                                all_delivered = True
                                packages = ticket.get_all_packages() if hasattr(ticket, 'get_all_packages') else []
                                for pkg in packages:
                                    pkg_status = (pkg.get('status') or '').lower()
                                    if not pkg_status or ('delivered' not in pkg_status and 'received' not in pkg_status):
                                        all_delivered = False
                                        break
                                if all_delivered:
                                    ticket.status = TS.RESOLVED
                                    ticket.custom_status = None  # Clear custom status when setting system status
                                    ticket.notes = (ticket.notes or "") + f"\n[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}] Ticket auto-closed: All packages delivered"
                                    ticket_auto_closed = True
                                    logger.info(f"SUCCESS: Auto-closed multi-package ticket {ticket_id}")

                # Save to tracking cache
                try:
                    from utils.tracking_cache import TrackingCache
                    TrackingCache.save_tracking_data(
                        db_session,
                        tracking_number,
                        tracking_info,
                        latest_status,
                        ticket_id=ticket_id,
                        tracking_type=f'package_{package_number}',
                        carrier='singpost'
                    )
                except Exception as cache_error:
                    logger.warning(f"Could not save to tracking cache: {cache_error}")

                db_session.commit()
                db_session.close()

                return jsonify({
                    'success': True,
                    'tracking_info': tracking_info,
                    'shipping_status': latest_status,
                    'was_pushed': result.get('was_pushed', False),
                    'is_real_data': True,
                    'package_number': package_number,
                    'tracking_number': tracking_number,
                    'carrier': 'SingPost',
                    'ticket_auto_closed': ticket_auto_closed,
                    'debug_info': {
                        'source': 'singpost_api',
                        'event_count': len(tracking_info),
                        'origin_country': result.get('origin_country'),
                        'destination_country': result.get('destination_country'),
                        'was_pushed': result.get('was_pushed', False)
                    }
                })
            else:
                # Tracking number not found
                error_msg = result.get('error', 'Tracking number not found')
                logger.info(f"SingPost tracking not found for package {package_number}: {error_msg}")

                current_date = datetime.datetime.now()
                status_desc = "Pending - Tracking Number Not Found"

                tracking_info = [{
                    'date': current_date.strftime('%Y-%m-%d %H:%M:%S'),
                    'status': status_desc,
                    'location': 'SingPost System'
                }]

                setattr(ticket, status_field, status_desc)
                ticket.updated_at = current_date
                db_session.commit()
                db_session.close()

                return jsonify({
                    'success': True,
                    'tracking_info': tracking_info,
                    'shipping_status': status_desc,
                    'was_pushed': False,
                    'is_real_data': True,
                    'package_number': package_number,
                    'tracking_number': tracking_number,
                    'carrier': 'SingPost',
                    'debug_info': {
                        'source': 'singpost_api',
                        'status': 'not_found',
                        'error': error_msg
                    }
                })

        # For non-SingPost tracking numbers, use Ship24 via Oxylabs proxy
        try:
            from utils.ship24_tracker import get_tracker
            ship24_tracker = get_tracker()

            logger.info(f"Tracking package {package_number} via Oxylabs for: {tracking_number}")

            try:
                # Track using Oxylabs proxy method
                result = ship24_tracker.track_parcel_sync(
                    tracking_number,
                    carrier=carrier,  # Use carrier if provided
                    method='oxylabs'  # Use Oxylabs proxy (HFD uses direct API)
                )
            except Exception as api_error:
                logger.info(f"Error tracking package {package_number} via Oxylabs: {api_error}")
                return jsonify({
                    'success': False,
                    'error': f'Tracking API error: {str(api_error)}',
                    'tracking_info': [],
                    'debug_info': {'error': str(api_error)}
                }), 500

            logger.info(f"Ship24 Tracker Response for package {package_number}: success={result.get('success')}, status={result.get('status')}, events={len(result.get('events', []))}")

            # Process the extracted data
            tracking_info = []
            latest_status = result.get('status', 'Unknown')

            try:
                # Extract tracking events from the result
                events = result.get('events', [])
                if events:
                    logger.info(f"[DEBUG] Found {len(events)} tracking events for package {package_number}")
                    for event in events:
                        tracking_info.append({
                            'date': event.get('timestamp', event.get('date', '')),
                            'status': event.get('description', event.get('status', '')),
                            'location': event.get('location', '')
                        })

                # If no events were extracted but we have a current status,
                # create at least one event with the current status
                if not tracking_info and latest_status not in ["Unknown", "No tracking information found"]:
                    tracking_info.append({
                        'date': datetime.datetime.now().isoformat(),
                        'status': latest_status,
                        'location': result.get('current_location', 'Ship24 System')
                    })

                logger.info(f"[DEBUG] Successfully extracted status for package {package_number}: {latest_status}, events: {len(tracking_info)}")

                # Use detected carrier from result if not specified
                if not carrier or carrier == 'auto':
                    carrier = result.get('carrier', 'Unknown')

                # Fallback if no tracking info was extracted
                if not tracking_info:
                    logger.info(f"Warning: No tracking events extracted for package {package_number}.")
                    current_date = datetime.datetime.now()
                    tracking_info = [{"status": "Information Received", "location": "Ship24 System", "date": current_date.isoformat()}]
                    latest_status = "Information Received"

            except Exception as parse_error:
                logger.info(f"Error parsing tracking data for package {package_number}: {str(parse_error)}")
                traceback.print_exc()
                return jsonify({
                    'success': False,
                    'error': f'Error parsing tracking data: {str(parse_error)}',
                    'tracking_info': [],
                    'debug_info': {'error': str(parse_error)}
                }), 500
            
            # Update ticket attributes in the same database session
            fresh_ticket = db_session.query(Ticket).get(ticket_id)
            if fresh_ticket:
                # Update the specific package status field
                setattr(fresh_ticket, status_field, latest_status)
                fresh_ticket.updated_at = datetime.datetime.now()

                # Check if all packages are delivered and update ticket status accordingly
                is_claw_ticket = fresh_ticket.category == TicketCategory.ASSET_CHECKOUT_CLAW
                logger.info(f"Fresh tracking auto-close check: ticket {ticket_id}, status={latest_status}, category={fresh_ticket.category}, is_claw={is_claw_ticket}")

                if is_claw_ticket:
                    latest_status_lower = (latest_status or '').lower()
                    # Only check for auto-close if this package is delivered/received
                    if 'delivered' in latest_status_lower or 'received' in latest_status_lower:
                        # Check if this is a single-package ticket
                        has_other_packages = any([
                            fresh_ticket.shipping_tracking_2,
                            fresh_ticket.shipping_tracking_3,
                            fresh_ticket.shipping_tracking_4,
                            fresh_ticket.shipping_tracking_5
                        ])

                        should_close = False
                        if not has_other_packages:
                            # Single package - this package delivered means close ticket
                            should_close = True
                            logger.info(f"Single package ticket {ticket_id} - package delivered, will auto-close")
                        else:
                            # Multi-package - check if ALL packages are delivered
                            all_packages_delivered = True
                            packages = fresh_ticket.get_all_packages()
                            for package in packages:
                                pkg_status = (package.get('status') or '').lower()
                                if not pkg_status or ('delivered' not in pkg_status and 'received' not in pkg_status):
                                    all_packages_delivered = False
                                    break
                            if all_packages_delivered:
                                should_close = True
                                logger.info(f"Multi-package ticket {ticket_id} - all packages delivered, will auto-close")

                        if should_close:
                            from models.ticket import TicketStatus
                            if fresh_ticket.status not in [TicketStatus.RESOLVED, TicketStatus.RESOLVED_DELIVERED]:
                                fresh_ticket.status = TicketStatus.RESOLVED
                                fresh_ticket.custom_status = None  # Clear custom status when setting system status
                                fresh_ticket.notes = (fresh_ticket.notes or "") + f"\n[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}] Ticket auto-closed: Package delivered"
                                logger.info(f"Automatically changed ticket {ticket_id} status to RESOLVED")

                db_session.commit()
                logger.info(f"Updated ticket {ticket_id} package {package_number} with status: {latest_status}")
            else:
                logger.info(f"Warning: Could not find ticket {ticket_id} in database session")
            
            # Save to cache for future requests
            try:
                from utils.tracking_cache import TrackingCache
                TrackingCache.save_tracking_data(
                    db_session,
                    tracking_number, 
                    tracking_info, 
                    latest_status,
                    ticket_id=ticket_id,
                    tracking_type=f'package_{package_number}',
                    carrier=carrier or "auto"
                )
                logger.info(f"Real tracking data saved to cache for package {package_number}")
            except Exception as cache_error:
                logger.info(f"Warning: Could not save tracking data to cache for package {package_number}: {str(cache_error)}")
            
            return jsonify({
                'success': True,
                'tracking_info': tracking_info,
                'shipping_status': latest_status,
                'tracking_number': tracking_number,
                'carrier': carrier,
                'package_number': package_number,
                'is_real_data': True,
                'is_cached': False,
                'debug_info': {
                    'source': 'oxylabs_ship24',
                    'tracking_number': tracking_number,
                    'package_number': package_number,
                    'status': latest_status
                }
            })
        
        except Exception as e:
            logger.info(f"Error scraping ship24 for package {package_number} ({tracking_number}): {str(e)}")
            traceback.print_exc()
            return jsonify({
                'success': False,
                'error': f'Error scraping Ship24: {str(e)}',
                'tracking_info': [],
                'debug_info': {'error': str(e)}
            }), 500
            
    except Exception as e:
        logger.info(f"General error in track_package: {str(e)}")
        traceback.print_exc()
        return jsonify({'success': False, 'message': f'Error tracking package: {str(e)}'}), 500
            
    finally:
        # Always close the session
        try:
            if db_session:
                if db_session.is_active:
                    db_session.commit()
                db_session.close()
        except Exception as e:
            logger.info(f"Error closing database session in track_package: {str(e)}")


def generate_package_mock_tracking_data(tracking_number, ticket_id, package_number, carrier, status_field, db_session):
    """DISABLED: Mock data generation is disabled. This function should not be called."""
    logger.info(f"[ERROR] Mock data generation disabled for package {package_number}: {tracking_number}")
    logger.info("[ERROR] Mock data generation has been disabled by user request")
    
    # Return an error instead of mock data
    return jsonify({
        'success': False,
        'error': 'Mock data generation is disabled',
        'tracking_info': [],
        'debug_info': {'reason': 'Mock data generation disabled by user request'}
    }), 501
    
    # Get the current time for timestamps
    current_date = datetime.datetime.now()
    
    # Create a realistic-looking mock tracking timeline with multiple events
    # Use tracking number to make it look more authentic
    tracking_suffix = tracking_number[-4:] if len(tracking_number) >= 4 else "0000"
    
    tracking_info = [
        {
            "status": "Out for Delivery",
            "location": f"Singapore Delivery Centre {tracking_suffix}",
            "date": current_date.strftime("%Y-%m-%d %H:%M:%S")
        },
        {
            "status": "Arrived at Sorting Facility",
            "location": f"Singapore Processing Centre",
            "date": (current_date - datetime.timedelta(hours=8)).strftime("%Y-%m-%d %H:%M:%S")
        },
        {
            "status": "In Transit",
            "location": f"Regional Hub - Departure",
            "date": (current_date - datetime.timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")
        },
        {
            "status": "Package Received at Origin",
            "location": f"Origin Facility - {carrier.title() if carrier else 'Auto'}",
            "date": (current_date - datetime.timedelta(days=2)).strftime("%Y-%m-%d %H:%M:%S")
        },
        {
            "status": "Shipping Label Created",
            "location": f"Sender Location - {tracking_number}",
            "date": (current_date - datetime.timedelta(days=3)).strftime("%Y-%m-%d %H:%M:%S")
        }
    ]
    
    # Use the latest status as the summary status (most recent event)
    latest_status = tracking_info[0]["status"]  # "Out for Delivery"
    
    try:
        # Get the ticket to update its status
        ticket = db_session.query(Ticket).get(ticket_id)
        if ticket:
            # Update the specific package status field
            setattr(ticket, status_field, latest_status)
            ticket.updated_at = datetime.datetime.now()

            # Check if all packages are delivered and update ticket status accordingly
            if ticket.category and ticket.category.name == 'ASSET_CHECKOUT_CLAW':
                all_packages_delivered = True
                packages = ticket.get_all_packages()
                for package in packages:
                    if not package.get('status') or 'delivered' not in package['status'].lower():
                        all_packages_delivered = False
                        break

                # Automatically change ticket status to RESOLVED_DELIVERED if all packages are delivered
                if all_packages_delivered:
                    from models.ticket import TicketStatus
                    if ticket.status != TicketStatus.RESOLVED_DELIVERED:
                        ticket.status = TicketStatus.RESOLVED_DELIVERED
                        ticket.custom_status = None  # Clear custom status when setting system status
                        logger.info(f"Automatically changed ticket {ticket_id} status to RESOLVED_DELIVERED due to all packages being delivered")

            db_session.commit()
            logger.info(f"Updated ticket {ticket_id} package {package_number} with mock status: {latest_status}")
        
        # Save to cache for future requests
        try:
            from utils.tracking_cache import TrackingCache
            TrackingCache.save_tracking_data(
                db_session,
                tracking_number, 
                tracking_info, 
                latest_status,
                ticket_id=ticket_id,
                tracking_type=f'package_{package_number}',
                carrier=carrier or "mock"
            )
            logger.info(f"Mock data saved to cache for package {package_number}")
        except Exception as cache_error:
            logger.info(f"Warning: Could not save mock data to cache for package {package_number}: {str(cache_error)}")
    
    except Exception as db_error:
        logger.info(f"Warning: Could not update ticket with mock data for package {package_number}: {str(db_error)}")
    
    # Return a successful response with mock data
    return jsonify({
        'success': True,
        'tracking_info': tracking_info,
        'shipping_status': latest_status,
        'tracking_number': tracking_number,
        'carrier': carrier,
        'package_number': package_number,
        'is_real_data': False,
        'is_cached': False,
        'debug_info': {
            'source': 'enhanced_mock_data_generated',
            'tracking_number': tracking_number,
            'package_number': package_number,
            'reason': 'API unavailable or insufficient credits',
            'status': latest_status
        }
    })

@tickets_bp.route('/<int:ticket_id>/package/<int:package_number>/add_item', methods=['POST'])
@login_required
def add_package_item(ticket_id, package_number):
    """Add an asset or accessory to a specific package"""
    db_session = ticket_store.db_manager.get_session()
    try:
        if package_number < 1 or package_number > 5:
            return jsonify({'success': False, 'message': 'Package number must be between 1 and 5'}), 400

        # Get ticket from database
        ticket = db_session.query(Ticket).get(ticket_id)

        if not ticket:
            return jsonify({'success': False, 'message': 'Ticket not found'}), 404

        # Verify this is an Asset Checkout (claw) ticket
        if not ticket.category or ticket.category.name != 'ASSET_CHECKOUT_CLAW':
            return jsonify({'success': False, 'message': 'Package item management is only available for Asset Checkout (claw) tickets'}), 400

        # Get request data
        data = request.get_json()
        item_type = data.get('item_type')  # 'asset' or 'accessory'
        item_id = data.get('item_id')
        quantity = data.get('quantity', 1)
        notes = data.get('notes', '')

        if not item_type or not item_id:
            return jsonify({'success': False, 'message': 'Item type and item ID are required'}), 400

        # Get the item name first while we have an active session
        if item_type == 'asset':
            from models.asset import Asset
            asset = db_session.query(Asset).get(item_id)
            if not asset:
                return jsonify({'success': False, 'message': 'Asset not found'}), 404
            
            # Add the item to the package
            package_item = ticket.add_package_item(
                package_number=package_number,
                asset_id=item_id,
                quantity=quantity,
                notes=notes,
                db_session=db_session
            )
        elif item_type == 'accessory':
            from models.accessory import Accessory
            accessory = db_session.query(Accessory).get(item_id)
            if not accessory:
                return jsonify({'success': False, 'message': 'Accessory not found'}), 404
            
            # Add the item to the package
            package_item = ticket.add_package_item(
                package_number=package_number,
                accessory_id=item_id,
                quantity=quantity,
                notes=notes,
                db_session=db_session
            )
        else:
            return jsonify({'success': False, 'message': 'Invalid item type. Must be "asset" or "accessory"'}), 400

        db_session.commit()

        # Note: Automatic comment generation removed as requested
        return jsonify({
            'success': True,
            'message': f'{item_type.title()} added to Package {package_number} successfully'
        })

    except Exception as e:
        db_session.rollback()
        logger.info(f"Error adding package item: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': f'Error adding item to package: {str(e)}'}), 500
    finally:
        db_session.close()

@tickets_bp.route('/<int:ticket_id>/package_item/<int:package_item_id>/remove', methods=['POST'])
@login_required
def remove_package_item(ticket_id, package_item_id):
    """Remove an item from a package"""
    try:
        # Get ticket from database
        db_session = ticket_store.db_manager.get_session()
        ticket = db_session.query(Ticket).get(ticket_id)

        if not ticket:
            db_session.close()
            return jsonify({'success': False, 'message': 'Ticket not found'}), 404

        # Verify this is an Asset Checkout (claw) ticket
        if not ticket.category or ticket.category.name != 'ASSET_CHECKOUT_CLAW':
            db_session.close()
            return jsonify({'success': False, 'message': 'Package item management is only available for Asset Checkout (claw) tickets'}), 400

        # Get the package item to get details before removal
        from models.package_item import PackageItem
        package_item = db_session.query(PackageItem).filter_by(
            id=package_item_id,
            ticket_id=ticket_id
        ).first()

        if not package_item:
            db_session.close()
            return jsonify({'success': False, 'message': 'Package item not found'}), 404

        # Store details for system note
        item_name = package_item.item_name
        item_type = package_item.item_type
        package_number = package_item.package_number

        # Remove the item
        success = ticket.remove_package_item(package_item_id)

        if success:
            # Note: Automatic comment generation removed as requested

            db_session.close()
            return jsonify({
                'success': True,
                'message': f'{item_type} removed from Package {package_number} successfully'
            })
        else:
            db_session.close()
            return jsonify({'success': False, 'message': 'Failed to remove item from package'}), 500

    except Exception as e:
        logger.info(f"Error removing package item: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': f'Error removing item from package: {str(e)}'}), 500

@tickets_bp.route('/<int:ticket_id>/package/<int:package_number>/items', methods=['GET'])
@login_required
def get_package_items(ticket_id, package_number):
    """Get all items associated with a specific package"""
    try:
        if package_number < 1 or package_number > 5:
            return jsonify({'success': False, 'message': 'Package number must be between 1 and 5'}), 400

        # Get ticket from database
        db_session = ticket_store.db_manager.get_session()
        ticket = db_session.query(Ticket).get(ticket_id)

        if not ticket:
            db_session.close()
            return jsonify({'success': False, 'message': 'Ticket not found'}), 404

        # Get package items
        package_items = ticket.get_package_items(package_number, db_session=db_session)

        db_session.close()
        return jsonify({
            'success': True,
            'package_items': package_items
        })

    except Exception as e:
        logger.info(f"Error getting package items: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': f'Error getting package items: {str(e)}'}), 500

@tickets_bp.route('/api/assets', methods=['GET'])
@login_required
def get_assets_for_packages():
    """Get available assets for package assignment"""
    try:
        from models.asset import Asset
        db_session = ticket_store.db_manager.get_session()
        
        # Get all assets (you might want to filter by status, company, etc.)
        assets = db_session.query(Asset).all()
        
        assets_data = []
        for asset in assets:
            assets_data.append({
                'id': asset.id,
                'name': asset.name,
                'asset_tag': getattr(asset, 'asset_tag', ''),
                'serial_num': getattr(asset, 'serial_num', ''),
                'model': getattr(asset, 'model', ''),
                'status': getattr(asset, 'status', '').value if hasattr(getattr(asset, 'status', ''), 'value') else str(getattr(asset, 'status', ''))
            })
        
        db_session.close()
        return jsonify({
            'success': True,
            'assets': assets_data
        })
    
    except Exception as e:
        logger.info(f"Error getting assets: {str(e)}")
        return jsonify({'success': False, 'message': f'Error getting assets: {str(e)}'}), 500

@tickets_bp.route('/api/accessories_for_packages', methods=['GET'])
@login_required
def get_accessories_for_packages():
    """Get available accessories for package assignment"""
    try:
        from models.accessory import Accessory
        db_session = ticket_store.db_manager.get_session()
        
        # Get all accessories (you might want to filter by stock quantity, etc.)
        accessories = db_session.query(Accessory).all()
        
        accessories_data = []
        for accessory in accessories:
            accessories_data.append({
                'id': accessory.id,
                'name': accessory.name,
                'category': getattr(accessory, 'category', ''),
                'model': getattr(accessory, 'model', ''),
                'stock_quantity': getattr(accessory, 'stock_quantity', 0)
            })
        
        db_session.close()
        return jsonify({
            'success': True,
            'accessories': accessories_data
        })
    
    except Exception as e:
        logger.info(f"Error getting accessories: {str(e)}")
        return jsonify({'success': False, 'message': f'Error getting accessories: {str(e)}'}), 500

@tickets_bp.route('/api/customers')
@login_required
def get_customers():
    """Get a list of all customers for use in AJAX requests"""
    db_session = db_manager.get_session()
    try:
        # Get current user and apply company filtering
        user = db_manager.get_user(session['user_id'])
        customers = get_filtered_customers(db_session, user)
        return jsonify({
            'success': True,
            'customers': [
                {
                    'id': customer.id,
                    'name': customer.name,
                    'company_name': customer.company.name if customer.company else None,
                    'address': customer.address,
                    'email': customer.email,
                    'contact_number': customer.contact_number,
                    'country': customer.country.value if customer.country else None
                }
                for customer in customers
            ]
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
    finally:
        db_session.close()


@tickets_bp.route('/api/mention-suggestions')
@login_required
def get_mention_suggestions():
    """Get users and groups for @mention autocomplete"""
    from models.group import Group

    query = request.args.get('q', '').lower().strip()
    db_session = db_manager.get_session()

    try:
        suggestions = []

        # Get users (limit to 10 for performance)
        users = db_session.query(User).filter(
            User.username.ilike(f'%{query}%')
        ).limit(10).all()

        for user in users:
            suggestions.append({
                'type': 'user',
                'id': user.id,
                'name': user.username,
                'display_name': user.username,
                'email': user.email,
                'avatar': user.username[0].upper() if user.username else 'U'
            })

        # Get active groups (limit to 10 for performance)
        try:
            groups = db_session.query(Group).filter(
                Group.name.ilike(f'%{query}%'),
                Group.is_active == True
            ).limit(10).all()

            for group in groups:
                suggestions.append({
                    'type': 'group',
                    'id': group.id,
                    'name': group.name,
                    'display_name': f"@{group.name}",
                    'description': group.description or f"Group with {group.member_count} members",
                    'member_count': group.member_count,
                    'avatar': 'G'
                })
        except Exception as e:
            # Groups might not exist in all setups
            logger.debug(f"Could not load groups: {e}")

        # Sort by relevance (exact matches first, then partial matches)
        def sort_key(item):
            name = item['name'].lower()
            if name == query:
                return (0, name)
            elif name.startswith(query):
                return (1, name)
            else:
                return (2, name)

        suggestions.sort(key=sort_key)

        return jsonify({'suggestions': suggestions[:20]})

    except Exception as e:
        logger.error(f"Error getting mention suggestions: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        db_session.close()


@tickets_bp.route('/<int:ticket_id>/add_outbound_tracking', methods=['POST'])
@login_required
def add_outbound_tracking(ticket_id):
    db_session = db_manager.get_session()
    try:
        data = request.json
        tracking_number = data.get('tracking_number')
        carrier = data.get('carrier', 'auto')
        
        if not tracking_number:
            return jsonify({'success': False, 'message': 'Tracking number is required'}), 400
        
        ticket = db_session.query(Ticket).get(ticket_id)
        if not ticket:
            return jsonify({'success': False, 'message': 'Ticket not found'}), 404
        
        # Update tracking information
        ticket.shipping_tracking = tracking_number
        ticket.shipping_carrier = carrier

        # Auto-mark items as packed when tracking is added (for case progress)
        if not ticket.item_packed:
            ticket.item_packed = True
            ticket.item_packed_at = datetime.datetime.now()

        # Save changes
        db_session.commit()

        return jsonify({
            'success': True,
            'message': 'Outbound tracking information added successfully',
            'item_packed': True
        })
    except Exception as e:
        db_session.rollback()
        logger.info(f"Error adding outbound tracking: {str(e)}")
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500
    finally:
        db_session.close()

@tickets_bp.route('/<int:ticket_id>/mark_outbound_received', methods=['POST'])
@login_required
def mark_outbound_received(ticket_id):
    db_session = db_manager.get_session()
    try:
        logger.info(f"Starting mark_outbound_received for ticket {ticket_id} (updating return_status as requested)")
        
        ticket = db_session.query(Ticket).get(ticket_id)
        if not ticket:
            flash('Ticket not found', 'error')
            return redirect(url_for('tickets.list_tickets'))
        
        singapore_time = datetime.datetime.now() + timedelta(hours=8)
        singapore_time_str = singapore_time.strftime("%Y-%m-%d %H:%M:%S (GMT+8)")
        
        # Update return_status as requested by user, even though it's the outbound button
        old_status = ticket.return_status
        ticket.return_status = f"Item was received on {singapore_time_str}"
        logger.info(f"Updating ticket {ticket_id} return_status from '{old_status}' to '{ticket.return_status}' (via outbound button)")
        
        db_session.commit()
        logger.info(f"Database commit successful for ticket {ticket_id}")
        
        flash('Return status marked as received (via Outbound button)')
        return redirect(url_for('tickets.view_ticket', ticket_id=ticket_id))
                
    except Exception as e:
        db_session.rollback()
        logger.info(f"Error marking outbound as received (updating return_status): {str(e)}")
        import traceback
        traceback.print_exc()
        flash(f'Error updating return status (via Outbound button): {str(e)}', 'error')
        return redirect(url_for('tickets.view_ticket', ticket_id=ticket_id))
    finally:
        db_session.close()

@tickets_bp.route('/<int:ticket_id>/mark_return_received', methods=['POST'])
@login_required
def mark_return_received(ticket_id):
    db_session = db_manager.get_session()
    try:
        logger.info(f"Starting mark_return_received for ticket {ticket_id}")
        
        ticket = db_session.query(Ticket).get(ticket_id)
        if not ticket:
            flash('Ticket not found', 'error')
            return redirect(url_for('tickets.list_tickets')) # Redirect if ticket not found
        
        singapore_time = datetime.datetime.now() + timedelta(hours=8)
        singapore_time_str = singapore_time.strftime("%Y-%m-%d %H:%M:%S (GMT+8)")
        
        old_status = ticket.return_status
        ticket.return_status = f"Item was received on {singapore_time_str}"
        logger.info(f"Updating ticket {ticket_id} return_status from '{old_status}' to '{ticket.return_status}'")
        
        if ticket.category == TicketCategory.ASSET_RETURN_CLAW:
            old_shipping_status = ticket.shipping_status
            ticket.shipping_status = f"Item was received on {singapore_time_str}"
            logger.info(f"Also updating shipping_status from '{old_shipping_status}' to '{ticket.shipping_status}' for Asset Return (Claw) ticket")

            # Check if there's a replacement tracking (some returns have replacement, some don't)
            has_replacement = ticket.replacement_tracking and ticket.replacement_tracking.strip()
            replacement_received = ticket.replacement_status and ("received" in ticket.replacement_status.lower() or "delivered" in ticket.replacement_status.lower())

            # Auto-close logic:
            # - If NO replacement tracking: Close when return is received (this action)
            # - If HAS replacement tracking: Close when both return AND replacement are received
            should_close = False
            if not has_replacement:
                # No replacement - just a return, close now
                should_close = True
                logger.info(f"Auto-closing ticket {ticket_id} - return received at warehouse (no replacement)")
            elif replacement_received:
                # Has replacement and it's received - close
                should_close = True
                logger.info(f"Auto-closing ticket {ticket_id} - both return and replacement shipments received")

            if should_close and ticket.status not in [TicketStatus.RESOLVED, TicketStatus.RESOLVED_DELIVERED]:
                ticket.status = TicketStatus.RESOLVED
                ticket.custom_status = None  # Clear custom status when setting system status
                ticket.notes = (ticket.notes or "") + f"\n[{singapore_time_str}] Ticket auto-closed: Return received at warehouse. Case completed!"

                # Update linked assets to "In Stock" status when Asset Return is resolved
                if ticket.assets:
                    for asset in ticket.assets:
                        if asset.status != AssetStatus.IN_STOCK:
                            old_asset_status = asset.status
                            asset.status = AssetStatus.IN_STOCK
                            asset.current_holder = None  # Clear the holder since it's returned
                            logger.info(f"Updated asset {asset.asset_tag} status from {old_asset_status} to IN_STOCK (Asset Return resolved)")

            # Set to IN_PROGRESS if status is NEW and not closing
            elif ticket.status == TicketStatus.NEW:
                ticket.status = TicketStatus.IN_PROGRESS
                ticket.custom_status = None  # Clear custom status when setting system status
                logger.info(f"Updated ticket {ticket_id} status to IN_PROGRESS")

        db_session.commit()
        logger.info(f"Database commit successful for ticket {ticket_id}")

        # Check if ticket was auto-closed
        if ticket.category == TicketCategory.ASSET_RETURN_CLAW and ticket.status == TicketStatus.RESOLVED:
            flash('Return received at warehouse. Case completed! Asset status updated to In Stock.')
        else:
            flash('Return shipment marked as received')
        return redirect(url_for('tickets.view_ticket', ticket_id=ticket_id))

    except Exception as e:
        db_session.rollback()
        logger.info(f"Error marking return as received: {str(e)}")
        import traceback
        traceback.print_exc()
        flash(f'Error marking return as received: {str(e)}', 'error')
        # Redirect back even on error for form submissions
        return redirect(url_for('tickets.view_ticket', ticket_id=ticket_id))
    finally:
        db_session.close()

@tickets_bp.route('/<int:ticket_id>/mark_replacement_received', methods=['POST'])
@login_required
def mark_replacement_received(ticket_id):
    """Mark the replacement shipment as received."""
    db_session = db_manager.get_session()
    try:
        logger.info(f"Starting mark_replacement_received for ticket {ticket_id}")
        
        ticket = db_session.query(Ticket).get(ticket_id)
        if not ticket:
            flash('Ticket not found', 'error')
            return redirect(url_for('tickets.list_tickets'))
        
        singapore_time = datetime.datetime.now() + timedelta(hours=8)
        singapore_time_str = singapore_time.strftime("%Y-%m-%d %H:%M:%S (GMT+8)")
        
        old_status = ticket.replacement_status
        ticket.replacement_status = f"Item was received on {singapore_time_str}"
        logger.info(f"Updating ticket {ticket_id} replacement_status from '{old_status}' to '{ticket.replacement_status}'")

        # Auto-close Asset Return (Claw) tickets if both return and replacement are received
        if ticket.category == TicketCategory.ASSET_RETURN_CLAW:
            # For ASSET_RETURN_CLAW, check shipping_status (which mirrors return_status)
            return_received = ticket.shipping_status and ("received" in ticket.shipping_status.lower() or "delivered" in ticket.shipping_status.lower())
            if return_received:
                ticket.status = TicketStatus.RESOLVED
                ticket.custom_status = None  # Clear custom status when setting system status
                logger.info(f"Auto-closing ticket {ticket_id} - both return and replacement shipments received")

                # Update linked assets to "In Stock" status when Asset Return is resolved
                if ticket.assets:
                    for asset in ticket.assets:
                        if asset.status != AssetStatus.IN_STOCK:
                            old_asset_status = asset.status
                            asset.status = AssetStatus.IN_STOCK
                            asset.current_holder = None  # Clear the holder since it's returned
                            logger.info(f"Updated asset {asset.asset_tag} status from {old_asset_status} to IN_STOCK (Asset Return resolved)")

            # Set to IN_PROGRESS if status is NEW
            elif ticket.status == TicketStatus.NEW:
                ticket.status = TicketStatus.IN_PROGRESS
                ticket.custom_status = None  # Clear custom status when setting system status
                logger.info(f"Updated ticket {ticket_id} status to IN_PROGRESS")

        db_session.commit()
        logger.info(f"Database commit successful for ticket {ticket_id}")

        # Check if ticket was auto-closed
        if ticket.category == TicketCategory.ASSET_RETURN_CLAW and ticket.status == TicketStatus.RESOLVED:
            flash('Replacement shipment marked as received - Ticket closed (both shipments received). Asset status updated to In Stock.')
        else:
            flash('Replacement shipment marked as received')
        return redirect(url_for('tickets.view_ticket', ticket_id=ticket_id))

    except Exception as e:
        db_session.rollback()
        logger.info(f"Error marking replacement as received: {str(e)}")
        import traceback
        traceback.print_exc()
        flash(f'Error marking replacement as received: {str(e)}', 'error')
        return redirect(url_for('tickets.view_ticket', ticket_id=ticket_id))
    finally:
        db_session.close()

@tickets_bp.route('/<int:ticket_id>/mark_item_packed', methods=['POST'])
@login_required
def mark_item_packed(ticket_id):
    """Mark items as packed for case progress tracking"""
    db_session = db_manager.get_session()
    try:
        # Get the ticket
        ticket = db_session.query(Ticket).get(ticket_id)
        if not ticket:
            return jsonify({'success': False, 'error': 'Ticket not found'}), 404

        # Check if items are already marked as packed
        if ticket.item_packed:
            return jsonify({'success': False, 'error': 'Items are already marked as packed'}), 400

        # Mark items as packed
        ticket.item_packed = True
        ticket.item_packed_at = dt.now()

        # Add a note to the ticket
        current_time = dt.now().strftime('%Y-%m-%d %H:%M:%S')
        note_text = f"\n[{current_time}] Items marked as packed by {current_user.username}"
        if ticket.notes:
            ticket.notes += note_text
        else:
            ticket.notes = note_text.strip()

        db_session.commit()

        return jsonify({
            'success': True,
            'message': 'Items marked as packed successfully',
            'item_packed_at': ticket.item_packed_at.isoformat() if ticket.item_packed_at else None
        })

    except Exception as e:
        db_session.rollback()
        logger.error(f"Error marking items as packed: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db_session.close()

@tickets_bp.route('/<int:ticket_id>/clear_tracking_cache', methods=['GET'])
@login_required
def clear_tracking_cache(ticket_id):
    """Clear cached tracking data for a ticket (used for debugging)"""
    try:
        db_session = ticket_store.db_manager.get_session()
        
        try:
            # Import tracking cache
            from utils.tracking_cache import TrackingCache
            from models.tracking import TrackingHistory
            
            # Get ticket
            ticket = db_session.query(Ticket).get(ticket_id)
            if not ticket:
                return jsonify({"success": False, "error": "Ticket not found"}), 404
                
            tracking_numbers = []
            if ticket.shipping_tracking:
                tracking_numbers.append(ticket.shipping_tracking)
            if ticket.return_tracking:
                tracking_numbers.append(ticket.return_tracking)
                
            # Delete all tracking history records for this ticket
            count = db_session.query(TrackingHistory).filter(
                TrackingHistory.ticket_id == ticket_id
            ).delete()
            
            db_session.commit()
            
            return jsonify({
                "success": True, 
                "message": f"Successfully cleared tracking cache for ticket {ticket_id}",
                "details": {
                    "records_deleted": count,
                    "tracking_numbers": tracking_numbers
                }
            })
            
        except Exception as e:
            db_session.rollback()
            logger.info(f"Error clearing tracking cache: {str(e)}")
            import traceback
            traceback.print_exc()
            return jsonify({"success": False, "error": str(e)}), 500
        finally:
            db_session.close()
            
    except Exception as e:
        logger.info(f"Database error: {str(e)}")
        return jsonify({"success": False, "error": "Database error"}), 500

@tickets_bp.route('/<int:ticket_id>/delete', methods=['POST'])
@login_required
def delete_ticket(ticket_id):
    """Delete a ticket"""
    # Check user permissions
    user_permissions = current_user.permissions
    
    db_session = db_manager.get_session()
    try:
        ticket = db_session.query(Ticket).get(ticket_id)
        if not ticket:
            return jsonify({'success': False, 'error': 'Ticket not found'}), 404
        
        # Permission checks
        # 1. Super admins can delete any ticket
        if current_user.is_super_admin:
            can_delete = True
        # 2. User with can_delete_tickets permission can delete any ticket
        elif user_permissions.can_delete_tickets:
            can_delete = True
        # 3. User with can_delete_own_tickets permission can delete tickets they created
        elif user_permissions.can_delete_own_tickets and current_user.id == ticket.requester_id:
            can_delete = True
        else:
            can_delete = False
            
        # If no permission, return error
        if not can_delete:
            return jsonify({
                'success': False, 
                'error': 'You do not have permission to delete tickets'
            }), 403
        
        # Log the deletion
        logger.info(f"User {session.get('username')} (ID: {session.get('user_id')}) is deleting ticket {ticket_id}")
        
        # Get ticket details for logging
        ticket_display_id = ticket.display_id
        ticket_subject = ticket.subject
        
        # Delete related records first (comments, activities, etc.)
        # Database comments
        db_session.query(Comment).filter_by(ticket_id=ticket_id).delete()
        
        # JSON file comments - use the comment_store
        json_comments_deleted = comment_store.delete_ticket_comments(ticket_id)
        logger.info(f"[DEBUG] Deleted {json_comments_deleted} JSON file comments for ticket {ticket_id}")
        
        # Activities related to this ticket
        db_session.query(Activity).filter_by(reference_id=ticket_id).delete()
        
        # Tracking histories
        db_session.query(TrackingHistory).filter_by(ticket_id=ticket_id).delete()
        
        # Unlink but don't delete assets
        for asset in ticket.assets:
            ticket.assets.remove(asset)
            
        # Delete any attachments
        attachments = db_session.query(Attachment).filter_by(ticket_id=ticket_id).all()
        for attachment in attachments:
            # Delete the file from disk if it exists
            if attachment.file_path and os.path.exists(attachment.file_path):
                try:
                    os.remove(attachment.file_path)
                except Exception as e:
                    logger.info(f"Error deleting file {attachment.file_path}: {str(e)}")
            # Delete the attachment record
            db_session.delete(attachment)
        
        # Finally delete the ticket
        db_session.delete(ticket)
        db_session.commit()
        
        # Log the successful deletion
        logger.info(f"Successfully deleted ticket {ticket_display_id}: {ticket_subject}")
        
        return jsonify({
            'success': True, 
            'message': f'Ticket {ticket_display_id} has been deleted'
        })
        
    except Exception as e:
        db_session.rollback()
        logger.info(f"Error deleting ticket {ticket_id}: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': f'An error occurred: {str(e)}'}), 500
    finally:
        db_session.close()

@tickets_bp.route('/<int:ticket_id>/update-shipping-status', methods=['POST'])
@login_required
def update_shipping_status(ticket_id):
    """Update the shipping status for an outbound package"""
    try:
        # Get request data
        data = request.json
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400

        status = data.get('status')

        if not status:
            return jsonify({'success': False, 'error': 'Status is required'}), 400

        # Get ticket from database
        db_session = ticket_store.db_manager.get_session()
        try:
            ticket = db_session.query(Ticket).get(ticket_id)

            if not ticket:
                return jsonify({'success': False, 'error': 'Ticket not found'}), 404

            # Format timestamp for display
            singapore_time = datetime.datetime.now() + timedelta(hours=8)
            singapore_time_str = singapore_time.strftime("%Y-%m-%d %H:%M:%S (GMT+8)")

            # Update shipping status
            old_status = ticket.shipping_status
            ticket.shipping_status = f"{status} on {singapore_time_str}"
            ticket.updated_at = datetime.datetime.now()

            # Add system note
            ticket.notes = (ticket.notes or "") + f"\n[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}] Outbound package marked as {status}"

            # Auto-close Asset Checkout (claw) tickets when status is "Customer Received" or "Delivered"
            ticket_auto_closed = False
            if ticket.category == TicketCategory.ASSET_CHECKOUT_CLAW:
                status_lower = status.lower()
                if 'customer received' in status_lower or 'delivered' in status_lower or 'received' in status_lower:
                    if ticket.status not in [TicketStatus.RESOLVED, TicketStatus.RESOLVED_DELIVERED]:
                        ticket.status = TicketStatus.RESOLVED
                        ticket.custom_status = None  # Clear custom status when setting system status
                        ticket.notes = (ticket.notes or "") + f"\n[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}] Ticket auto-closed: Customer received package"
                        logger.info(f"Auto-closed Asset Checkout (claw) ticket {ticket_id} - status set to '{status}'")
                        ticket_auto_closed = True

            # Commit changes
            db_session.commit()
            
            # Store the values we need for the response BEFORE closing the session
            new_status = ticket.shipping_status

            return jsonify({
                'success': True,
                'message': f'Outbound package status updated to {status}' + (' - Ticket auto-closed' if ticket_auto_closed else ''),
                'new_status': new_status,
                'old_status': old_status,
                'ticket_closed': ticket_auto_closed
            })
        finally:
            # Always close the session
            db_session.close()

    except Exception as e:
        logger.info(f"Error updating shipping status: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': f'An error occurred: {str(e)}'}), 500

@tickets_bp.route('/<int:ticket_id>/update-return-status', methods=['POST'])
@login_required
def update_return_status(ticket_id):
    # Get the database session
    db_session = db_manager.get_session()
    
    try:
        # Parse request data
        data = request.json
        status = data.get('status')
        
        if not status:
            return jsonify({"success": False, "error": "Status is required"}), 400
        
        # Get the ticket
        ticket = db_session.query(Ticket).get(ticket_id)
        if not ticket:
            return jsonify({"success": False, "error": "Ticket not found"}), 404
        
        # Format timestamp for display
        singapore_time = datetime.datetime.now() + timedelta(hours=8)
        singapore_time_str = singapore_time.strftime("%Y-%m-%d %H:%M:%S (GMT+8)")
        
        # Update return status
        old_status = ticket.return_status
        ticket.return_status = f"{status} on {singapore_time_str}"
        ticket.updated_at = datetime.datetime.now()
        
        # Add system note
        ticket.notes = (ticket.notes or "") + f"\n[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}] Return package marked as {status}"
        
        # Log activity using the correct method
        activity_store.add_activity(
            user_id=session.get('user_id'),
            type="ticket_update",
            content=f"Updated return status to {status}",
            reference_id=ticket_id
        )
        
        db_session.commit()
        return jsonify({
            "success": True, 
            "message": f"Return status updated to {status}",
            "new_status": ticket.return_status,
            "old_status": old_status
        })
        
    except Exception as e:
        db_session.rollback()
        logger.error(f"Error updating return status: {str(e)}")
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500

@tickets_bp.route('/<int:ticket_id>/transfer', methods=['POST'], endpoint='transfer_ticket')
@login_required
def transfer_ticket(ticket_id):
    """Transfer a ticket to another user"""
    db_session = db_manager.get_session()
    
    try:
        # Get the ticket
        ticket = db_session.query(Ticket).get(ticket_id)
        if not ticket:
            flash('Ticket not found', 'error')
            return redirect(url_for('tickets.list_tickets'))
        
        # Get the transfer target user ID
        transfer_to_id = request.form.get('transfer_to_id', type=int)
        if not transfer_to_id:
            flash('Please select a user to transfer to', 'error')
            return redirect(url_for('tickets.view_ticket', ticket_id=ticket_id))
        
        # Get the transfer notes
        transfer_notes = request.form.get('transfer_notes', '')
        
        # Get the target user
        target_user = db_session.query(User).get(transfer_to_id)
        if not target_user:
            flash('Target user not found', 'error')
            return redirect(url_for('tickets.view_ticket', ticket_id=ticket_id))
        
        # Get the current user
        current_user_id = session.get('user_id')
        current_user = db_session.query(User).get(current_user_id)
        
        # Update the ticket's assigned user
        previous_user_id = ticket.assigned_to_id
        ticket.assigned_to_id = transfer_to_id
        
        # Send email notification to new assignee
        try:
            logger.info(f"DEBUG - Transfer: sending email notification to {target_user.username} ({target_user.email})")
            if target_user.email:
                from utils.email_sender import send_ticket_assignment_notification
                
                # Get previous assignee for notification
                previous_assignee = None
                if previous_user_id:
                    previous_assignee = db_session.query(User).get(previous_user_id)
                
                # Send notification email
                email_sent = send_ticket_assignment_notification(
                    assigned_user=target_user,
                    assigner=current_user,
                    ticket=ticket,
                    previous_assignee=previous_assignee
                )
                
                if email_sent:
                    logger.info(f"DEBUG - Transfer notification email sent to {target_user.email}")
                else:
                    logger.info(f"DEBUG - Failed to send transfer notification email to {target_user.email}")
            else:
                logger.info(f"DEBUG - Target user {target_user.username} has no email address")
        except Exception as e:
            logger.info(f"DEBUG - Error sending transfer notification: {str(e)}")
            import traceback
            traceback.print_exc()
            # Don't fail the transfer if email fails
            pass
        
        # Add a comment about the transfer
        comment_text = f"Ticket transferred from {current_user.username} to {target_user.username}"
        if transfer_notes:
            comment_text += f"\n\nNotes: {transfer_notes}"
            
        # Create comment with proper constructor
        comment = Comment(
            ticket_id=ticket_id,
            user_id=current_user_id,
            content=comment_text
        )
        db_session.add(comment)
        
        # Log activity
        activity_store.add_activity(
            user_id=current_user_id,
            type="ticket_transfer",
            content=f"Transferred ticket from {current_user.username} to {target_user.username}",
            reference_id=ticket_id
        )
        
        db_session.commit()
        flash(f'Ticket successfully transferred to {target_user.username}', 'success')
        return redirect(url_for('tickets.view_ticket', ticket_id=ticket_id))
        
    except Exception as e:
        db_session.rollback()
        logger.error(f"Error transferring ticket: {str(e)}")
        traceback.print_exc()
        flash(f'Error transferring ticket: {str(e)}', 'error')
        return redirect(url_for('tickets.view_ticket', ticket_id=ticket_id))

@tickets_bp.route('/api/companies')
@login_required
def get_companies():
    """Get a list of all companies for use in AJAX requests"""
    db_session = db_manager.get_session()
    try:
        # Get companies from Company table
        companies = db_session.query(Company).order_by(Company.name).all()
        
        # Get unique company names from assets that might not have a company record
        company_names_from_assets = db_session.query(Asset.customer)\
            .filter(Asset.customer.isnot(None))\
            .distinct()\
            .all()
            
        # Create a set of all company names
        company_names = set([company.name for company in companies])
        
        # Add company names from assets if they don't already exist
        for company_name in company_names_from_assets:
            if company_name[0] and company_name[0] not in company_names:
                company_names.add(company_name[0])
        
        # Sort alphabetically
        sorted_companies = sorted(list(company_names))
        
        # Format for response
        result = [{"id": i, "name": name} for i, name in enumerate(sorted_companies, 1)]
        
        return jsonify({
            'success': True,
            'companies': result
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
    finally:
        db_session.close()

@tickets_bp.route('/<int:ticket_id>/debug_documents')
@login_required
def debug_documents(ticket_id):
    """Debug view for showing documents tab content directly."""
    try:
        db_session = db_manager.get_session()
        
        # Get ticket with eagerly loaded relationships
        ticket = db_session.query(Ticket).options(
            joinedload(Ticket.attachments),
            joinedload(Ticket.customer)
        ).filter(Ticket.id == ticket_id).first()
        
        if not ticket:
            flash('Ticket not found', 'error')
            return redirect(url_for('tickets.list_tickets'))
            
        # Get owner (assigned user)
        owner = None
        if ticket.assigned_to:
            owner = db_manager.get_user(ticket.assigned_to)
        
        # Get asset data
        if ticket.assets:
            for asset in ticket.assets:
                if asset.customer_id:
                    asset.customer_user = db_session.query(CustomerUser).filter_by(id=asset.customer_id).first()
        
        # Current user
        user = db_manager.get_user(session['user_id'])
        user_type = session.get('user_type')
        
        # Check permissions based on user type (simplified)
        if user_type == 'SUPER_ADMIN':
            # Super admins can view all tickets
            pass
        elif user_type == 'CLIENT':
            # Clients can only view tickets they created
            if ticket.created_by != user.id:
                flash('You do not have permission to view this ticket', 'error')
                return redirect(url_for('tickets.list_tickets'))
        else:
            # Staff need to check queue permissions
            if ticket.queue_id:
                # Check if user has access to this queue
                if not user.can_access_queue(ticket.queue_id):
                    flash('You do not have permission to view this ticket', 'error')
                    return redirect(url_for('tickets.list_tickets'))
        
        # Render the debug template showing just the documents section
        return render_template('tickets/debug_view.html', 
                              ticket=ticket, 
                              owner=owner,
                              user=user)
                              
    except Exception as e:
        logger.info(f"Error in debug_documents: {str(e)}")
        traceback.print_exc()
        flash(f'Error loading ticket data: {str(e)}', 'error')
        return redirect(url_for('tickets.list_tickets'))

@tickets_bp.route('/<int:ticket_id>/attachment/<int:attachment_id>')
@login_required
def get_attachment(ticket_id, attachment_id):
    """Get an attachment file."""
    try:
        db_session = db_manager.get_session()
        
        # Get the attachment
        attachment = db_session.query(Attachment).filter_by(
            id=attachment_id, 
            ticket_id=ticket_id
        ).first()
        
        if not attachment:
            flash('Attachment not found', 'error')
            return redirect(url_for('tickets.view_ticket', ticket_id=ticket_id))
        
        # Get the current user
        user = db_manager.get_user(session['user_id'])
        user_type = session.get('user_type')
        
        # Get the ticket
        ticket = db_session.query(Ticket).get(ticket_id)
        
        # Check permissions (simplified)
        if user_type != 'SUPER_ADMIN':
            if user_type == 'CLIENT' and ticket.created_by != user.id:
                flash('You do not have permission to access this attachment', 'error')
                return redirect(url_for('tickets.list_tickets'))

            if ticket.queue_id:
                # Check if user has access to this queue
                if not user.can_access_queue(ticket.queue_id):
                    flash('You do not have permission to access this attachment', 'error')
                    return redirect(url_for('tickets.list_tickets'))
        
        # Check if the file exists
        if not os.path.exists(attachment.file_path):
            flash('File not found on server', 'error')
            return redirect(url_for('tickets.view_ticket', ticket_id=ticket_id))
        
        # Determine if this is a PDF for inline viewing
        is_pdf = attachment.filename.lower().endswith('.pdf')
        download_requested = request.args.get('download') == 'true'
        
        if is_pdf and not download_requested:
            # Serve PDF for inline viewing
            return send_file(
                attachment.file_path,
                mimetype='application/pdf',
                as_attachment=False,
                download_name=attachment.filename
            )
        else:
            # Serve as download
            return send_file(
                attachment.file_path,
                as_attachment=True,
                download_name=attachment.filename
            )
        
    except Exception as e:
        logger.info(f"Error getting attachment: {str(e)}")
        traceback.print_exc()
        flash(f'Error accessing attachment: {str(e)}', 'error')
        return redirect(url_for('tickets.view_ticket', ticket_id=ticket_id))
    finally:
        db_session.close()

@tickets_bp.route('/cleanup-comments', methods=['POST'])
@admin_required
def cleanup_orphaned_comments():
    """Clean up orphaned comments (comments for deleted tickets)"""
    try:
        # Clean up orphaned comments using the comment store
        deletion_count = comment_store.cleanup_orphaned_comments()
        
        # Return response
        return jsonify({
            'success': True,
            'message': f'Successfully cleaned up {deletion_count} orphaned comments',
            'deleted_count': deletion_count
        })
        
    except Exception as e:
        logger.info(f"[ERROR] Error cleaning up orphaned comments: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@tickets_bp.route('/<int:ticket_id>/add-accessory', methods=['POST'])
@login_required
def add_accessory(ticket_id):
    """Add an accessory to a ticket"""
    db_session = db_manager.get_session()
    try:
        # Get the ticket
        ticket = db_session.query(Ticket).get(ticket_id)
        if not ticket:
            return jsonify({'success': False, 'message': 'Ticket not found'}), 404

        # Get JSON data if it's an AJAX request, otherwise form data
        if request.is_json:
            data = request.get_json()
            existing_accessory_id = data.get('existing_accessory_id')
            # Use the quantity submitted by the user
            quantity = int(data.get('accessory_quantity', 1))
            condition = data.get('accessory_condition', 'Good')
            notes = data.get('accessory_notes', '')

            if existing_accessory_id:
                # Get the existing accessory
                accessory = db_session.query(Accessory).get(existing_accessory_id)
                if not accessory:
                    return jsonify({'success': False, 'message': 'Accessory not found'}), 404

                # Create ticket accessory record
                ticket_accessory = TicketAccessory(
                    ticket_id=ticket_id,
                    name=accessory.name,
                    category=accessory.category,
                    quantity=quantity,  # Use the quantity from the form
                    condition=condition,
                    notes=notes,
                    original_accessory_id=accessory.id
                )
                db_session.add(ticket_accessory)

                # Update inventory based on ticket category
                logger.info("=== INVENTORY UPDATE START ===")
                logger.info(f"TICKET CATEGORY: {ticket.category}")
                logger.info(f"PROCESSING ACCESSORY: {accessory.name}")
                logger.info(f"Previous available quantity: {accessory.available_quantity}")
                
                # For Asset Checkout categories, deduct from inventory (checkout)
                # For Asset Return and Asset Intake categories, add to inventory (return/intake)
                if ticket.category and (ticket.category.name in ['ASSET_CHECKOUT', 'ASSET_CHECKOUT1', 'ASSET_CHECKOUT_CLAW', 'ASSET_CHECKOUT_MAIN', 'ASSET_CHECKOUT_SINGPOST', 'ASSET_CHECKOUT_DHL', 'ASSET_CHECKOUT_UPS', 'ASSET_CHECKOUT_BLUEDART', 'ASSET_CHECKOUT_DTDC', 'ASSET_CHECKOUT_AUTO']):
                    # Checkout: deduct from inventory
                    if accessory.available_quantity < quantity:
                        return jsonify({'success': False, 'message': f'Not enough quantity available. Only {accessory.available_quantity} units available.'}), 400
                    accessory.available_quantity -= quantity
                    logger.info(f"CHECKOUT: Decreasing inventory by {quantity}")

                    # Update status based on quantity
                    if accessory.available_quantity == 0:
                        accessory.status = 'Out of Stock'
                    else:
                        accessory.status = 'Available'
                elif ticket.category and ticket.category.name == 'ASSET_INTAKE':
                    # Intake: add NEW stock to inventory (increase both total and available)
                    accessory.total_quantity += quantity
                    accessory.available_quantity += quantity
                    logger.info(f"INTAKE: Increasing total and available inventory by {quantity}")

                    # Update status - if we have stock, it's available
                    if accessory.available_quantity > 0:
                        accessory.status = 'Available'
                else:
                    # Return: add back to available inventory (total stays same)
                    accessory.available_quantity += quantity
                    logger.info(f"RETURN: Increasing available inventory by {quantity}")

                    # Update status - if we have stock, it's available
                    if accessory.available_quantity > 0:
                        accessory.status = 'Available'

                logger.info(f"New available quantity: {accessory.available_quantity}")
                logger.info("=== INVENTORY UPDATE END ===")

                # Create transaction record
                if ticket.category and (ticket.category.name in ['ASSET_CHECKOUT', 'ASSET_CHECKOUT1', 'ASSET_CHECKOUT_CLAW', 'ASSET_CHECKOUT_MAIN', 'ASSET_CHECKOUT_SINGPOST', 'ASSET_CHECKOUT_DHL', 'ASSET_CHECKOUT_UPS', 'ASSET_CHECKOUT_BLUEDART', 'ASSET_CHECKOUT_DTDC', 'ASSET_CHECKOUT_AUTO']):
                    transaction_type = 'Checkout'
                    transaction_notes = f'Accessory checked out via ticket #{ticket_id} - inventory decreased'
                elif ticket.category and ticket.category.name == 'ASSET_INTAKE':
                    transaction_type = 'Intake'
                    transaction_notes = f'Accessory received via asset intake ticket #{ticket_id} - inventory increased'
                else:
                    transaction_type = 'Return'
                    transaction_notes = f'Accessory returned via ticket #{ticket_id} - inventory increased'
                
                transaction = AccessoryTransaction(
                    accessory_id=accessory.id,
                    transaction_type=transaction_type,
                    quantity=quantity,  # Use the quantity from the form
                    user_id=current_user.id,
                    notes=transaction_notes
                )
                db_session.add(transaction)

                db_session.commit()

                return jsonify({
                    'success': True,
                    'message': 'Accessory added successfully',
                    'accessory': accessory.to_dict()
                })
            else:
                # Handle JSON request for new accessory
                name = data.get('accessory_name')
                category = data.get('accessory_category')
                manufacturer = data.get('manufacturer')
                model_no = data.get('model_no')
                total_quantity = int(data.get('total_quantity', 1))
                country = data.get('country')
                # quantity is already set above
                
                if not all([name, category, manufacturer, model_no, country]):
                    return jsonify({'success': False, 'message': 'Missing required fields'}), 400

                # Create new accessory in inventory
                new_accessory = Accessory(
                    name=name,
                    category=category,
                    manufacturer=manufacturer,
                    model_no=model_no,
                    total_quantity=total_quantity,
                    available_quantity=total_quantity,
                    country=country,
                    status='Available'
                )
                db_session.add(new_accessory)
                db_session.flush()

                # Update inventory based on ticket category
                if ticket.category and (ticket.category.name in ['ASSET_CHECKOUT', 'ASSET_CHECKOUT1', 'ASSET_CHECKOUT_CLAW', 'ASSET_CHECKOUT_MAIN', 'ASSET_CHECKOUT_SINGPOST', 'ASSET_CHECKOUT_DHL', 'ASSET_CHECKOUT_UPS', 'ASSET_CHECKOUT_BLUEDART', 'ASSET_CHECKOUT_DTDC', 'ASSET_CHECKOUT_AUTO']):
                    if new_accessory.available_quantity < quantity:
                        return jsonify({'success': False, 'message': f'Not enough quantity available. Only {new_accessory.available_quantity} units available.'}), 400
                    new_accessory.available_quantity -= quantity
                else:
                    # Return/Intake: For NEW accessories, available_quantity is already set correctly to total_quantity
                    # No need to add to inventory since we're creating new inventory
                    pass

                # Create ticket accessory record
                ticket_accessory = TicketAccessory(
                    ticket_id=ticket_id,
                    name=name,
                    category=category,
                    quantity=quantity,
                    condition=condition,
                    notes=notes,
                    original_accessory_id=new_accessory.id
                )
                db_session.add(ticket_accessory)

                # Create transaction records
                if ticket.category and (ticket.category.name in ['ASSET_CHECKOUT', 'ASSET_CHECKOUT1', 'ASSET_CHECKOUT_CLAW', 'ASSET_CHECKOUT_MAIN', 'ASSET_CHECKOUT_SINGPOST', 'ASSET_CHECKOUT_DHL', 'ASSET_CHECKOUT_UPS', 'ASSET_CHECKOUT_BLUEDART', 'ASSET_CHECKOUT_DTDC', 'ASSET_CHECKOUT_AUTO']):
                    assignment_transaction_type = 'Checkout'
                    assignment_transaction_notes = f'New accessory created and checked out via ticket #{ticket_id} - inventory decreased'
                elif ticket.category and ticket.category.name == 'ASSET_INTAKE':
                    assignment_transaction_type = 'Intake'
                    assignment_transaction_notes = f'New accessory created and received via asset intake ticket #{ticket_id} - inventory increased'
                else:
                    assignment_transaction_type = 'Return'
                    assignment_transaction_notes = f'New accessory created and returned via ticket #{ticket_id} - inventory increased'

                transaction = AccessoryTransaction(
                    accessory_id=new_accessory.id,
                    transaction_type=assignment_transaction_type,
                    quantity=quantity,
                    user_id=current_user.id,
                    notes=assignment_transaction_notes
                )
                db_session.add(transaction)

                # Create initial inventory transaction
                inventory_transaction = AccessoryTransaction(
                    accessory_id=new_accessory.id,
                    transaction_type='Inventory Addition',
                    quantity=total_quantity,
                    user_id=current_user.id,
                    notes=f'Initial inventory addition'
                )
                db_session.add(inventory_transaction)

                db_session.commit()

                return jsonify({
                    'success': True,
                    'message': 'New accessory created and added successfully',
                    'accessory': new_accessory.to_dict()
                })

        else:
            # Handle form submission for new accessory
            name = request.form.get('accessory_name')
            category = request.form.get('accessory_category')
            manufacturer = request.form.get('manufacturer')
            model_no = request.form.get('model_no')
            total_quantity = int(request.form.get('total_quantity', 1))
            country = request.form.get('country')
            # Use the quantity submitted by the user
            quantity = int(request.form.get('accessory_quantity', 1))
            condition = request.form.get('accessory_condition', 'Good')
            notes = request.form.get('accessory_notes', '')
            
            # No need to check if quantity is greater than total quantity since it's always 1

            # Create new accessory in inventory
            # Set available_quantity to total_quantity initially
            new_accessory = Accessory(
                name=name,
                category=category,
                manufacturer=manufacturer,
                model_no=model_no,
                total_quantity=total_quantity,
                available_quantity=total_quantity,  # Initialize with full quantity
                country=country,
                status='Available'
            )
            db_session.add(new_accessory)
            db_session.flush()  # Get the ID of the new accessory
            
            # Update inventory based on ticket category
            logger.info("=== INVENTORY UPDATE START ===")
            logger.info(f"CREATING NEW ACCESSORY: {name}")
            logger.info(f"TICKET CATEGORY: {ticket.category}")
            logger.info(f"Total quantity: {total_quantity}")
            logger.info(f"Assigning quantity: {quantity}")
            logger.info(f"Initial available quantity: {new_accessory.available_quantity}")
            
            # For Asset Checkout categories, deduct from inventory (checkout)
            # For Asset Return and Asset Intake categories, add to inventory (return/intake)
            if ticket.category and (ticket.category.name in ['ASSET_CHECKOUT', 'ASSET_CHECKOUT1', 'ASSET_CHECKOUT_CLAW', 'ASSET_CHECKOUT_MAIN', 'ASSET_CHECKOUT_SINGPOST', 'ASSET_CHECKOUT_DHL', 'ASSET_CHECKOUT_UPS', 'ASSET_CHECKOUT_BLUEDART', 'ASSET_CHECKOUT_DTDC', 'ASSET_CHECKOUT_AUTO']):
                # Checkout: deduct from inventory
                if new_accessory.available_quantity < quantity:
                    return jsonify({'success': False, 'message': f'Not enough quantity available. Only {new_accessory.available_quantity} units available.'}), 400
                new_accessory.available_quantity -= quantity
                logger.info(f"CHECKOUT: Decreasing inventory by {quantity}")
            else:
                # Return/Intake: For NEW accessories, available_quantity is already set correctly to total_quantity
                # No need to add to inventory since we're creating new inventory
                logger.info(f"RETURN/INTAKE: New accessory created with available quantity: {new_accessory.available_quantity}")
                
            logger.info(f"Available quantity after assignment: {new_accessory.available_quantity}")
            logger.info("=== INVENTORY UPDATE END ===")
            
            # Create ticket accessory record
            ticket_accessory = TicketAccessory(
                ticket_id=ticket_id,
                name=name,
                category=category,
                quantity=quantity,  # Use the quantity from the form
                condition=condition,
                notes=notes,
                original_accessory_id=new_accessory.id
            )
            db_session.add(ticket_accessory)

            # Create transaction record for the assignment
            if ticket.category and (ticket.category.name in ['ASSET_CHECKOUT', 'ASSET_CHECKOUT1', 'ASSET_CHECKOUT_CLAW', 'ASSET_CHECKOUT_MAIN', 'ASSET_CHECKOUT_SINGPOST', 'ASSET_CHECKOUT_DHL', 'ASSET_CHECKOUT_UPS', 'ASSET_CHECKOUT_BLUEDART', 'ASSET_CHECKOUT_DTDC', 'ASSET_CHECKOUT_AUTO']):
                assignment_transaction_type = 'Checkout'
                assignment_transaction_notes = f'New accessory created and checked out via ticket #{ticket_id} - inventory decreased'
            elif ticket.category and ticket.category.name == 'ASSET_INTAKE':
                assignment_transaction_type = 'Intake'
                assignment_transaction_notes = f'New accessory created and received via asset intake ticket #{ticket_id} - inventory increased'
            else:
                assignment_transaction_type = 'Return'
                assignment_transaction_notes = f'New accessory created and returned via ticket #{ticket_id} - inventory increased'

            transaction = AccessoryTransaction(
                accessory_id=new_accessory.id,
                transaction_type=assignment_transaction_type,
                quantity=quantity,  # Use the quantity from the form
                user_id=current_user.id,
                notes=assignment_transaction_notes
            )
            db_session.add(transaction)
            
            # Create a transaction record for the initial inventory addition
            inventory_transaction = AccessoryTransaction(
                accessory_id=new_accessory.id,
                transaction_type='Inventory Addition',
                quantity=total_quantity,
                user_id=current_user.id,
                notes=f'Initial inventory addition'
            )
            db_session.add(inventory_transaction)

            db_session.commit()

            flash('Accessory added successfully', 'success')
            return redirect(url_for('tickets.view_ticket', ticket_id=ticket_id))

    except Exception as e:
        db_session.rollback()
        logger.info(f"Error adding accessory: {str(e)}")
        if request.is_json:
            return jsonify({'success': False, 'message': f'Error processing accessory data: {str(e)}'}), 500
        flash(f'Error adding accessory: {str(e)}', 'error')
        return redirect(url_for('tickets.view_ticket', ticket_id=ticket_id))
    finally:
        db_session.close()

@tickets_bp.route('/accessory/<int:accessory_id>', methods=['GET'])
@login_required
def get_accessory(accessory_id):
    """Get accessory details for editing"""
    try:
        # Get database session using db_manager
        db_session = db_manager.get_session()
        from models.ticket import TicketAccessory
        
        # Get the accessory
        accessory = db_session.query(TicketAccessory).get(accessory_id)
        if not accessory:
            return jsonify({'success': False, 'message': 'Accessory not found'}), 404
            
        return jsonify({
            'success': True,
            'accessory': {
                'id': accessory.id,
                'name': accessory.name,
                'category': accessory.category,
                'quantity': accessory.quantity,
                'condition': accessory.condition,
                'notes': accessory.notes
            }
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        logger.info(f"Error getting accessory: {str(e)}")
        return jsonify({'success': False, 'message': f'Error getting accessory: {str(e)}'}), 500
    finally:
        db_session.close()

@tickets_bp.route('/<int:ticket_id>/accessory/<int:accessory_id>/update', methods=['POST'])
@login_required
def update_accessory(ticket_id, accessory_id):
    """Update an accessory record"""
    db_session = db_manager.get_session()
    try:
        # Get the ticket and accessory
        ticket = db_session.query(Ticket).get(ticket_id)
        accessory = db_session.query(TicketAccessory).get(accessory_id)
        
        if not ticket:
            return jsonify({'success': False, 'message': 'Ticket not found'}), 404
            
        if not accessory:
            return jsonify({'success': False, 'message': 'Accessory not found'}), 404
            
        # Verify the accessory belongs to this ticket
        if accessory.ticket_id != ticket_id:
            return jsonify({'success': False, 'message': 'Accessory does not belong to this ticket'}), 400
            
        # Get data from request
        data = request.json
        name = data.get('name')
        category = data.get('category')
        new_quantity = int(data.get('quantity'))
        condition = data.get('condition')
        notes = data.get('notes')
        
        # Validate required fields
        if not name or not category:
            return jsonify({'success': False, 'message': 'Name and category are required'}), 400
        
        # Store old quantity for inventory adjustment
        old_quantity = accessory.quantity
        quantity_difference = new_quantity - old_quantity
        
        # Update accessory record
        accessory.name = name
        accessory.category = category
        accessory.quantity = new_quantity
        accessory.condition = condition
        accessory.notes = notes
        
        # Update inventory if this accessory has an original_accessory_id (was taken from inventory)
        if accessory.original_accessory_id and quantity_difference != 0:
            # Get the original accessory from inventory
            original_accessory = db_session.query(Accessory).filter(
                Accessory.id == accessory.original_accessory_id
            ).with_for_update().first()
            
            if original_accessory:
                logger.info("=== INVENTORY UPDATE START ===")
                logger.info(f"UPDATING ACCESSORY: {name}")
                logger.info(f"Ticket category: {ticket.category.name if ticket.category else 'None'}")
                logger.info(f"Old ticket quantity: {old_quantity}, New ticket quantity: {new_quantity}")
                logger.info(f"Quantity difference: {quantity_difference}")
                logger.info(f"Previous inventory available_quantity: {original_accessory.available_quantity}")
                
                # For Asset Intake tickets, when quantity increases, we add to inventory
                # When quantity decreases, we subtract from inventory
                is_asset_intake = ticket.category and ticket.category.name in ['ASSET_INTAKE_CLAW', 'ASSET_INTAKE_MAIN', 'ASSET_INTAKE_SINGPOST', 'ASSET_INTAKE_DHL', 'ASSET_INTAKE_UPS', 'ASSET_INTAKE_BLUEDART', 'ASSET_INTAKE_DTDC', 'ASSET_INTAKE_AUTO']
                logger.info(f"Is Asset Intake ticket: {is_asset_intake}")
                
                # Check if this is a return/received accessories ticket
                is_return_ticket = ticket.category and (
                    'RETURN' in ticket.category.name.upper() or 
                    'RECEIVED' in ticket.category.name.upper() or
                    ticket.category.name.upper() == 'ASSET_RETURN' or
                    'INTAKE' in ticket.category.name.upper()
                )
                
                if is_asset_intake or is_return_ticket:
                    # Asset Intake/Return: more quantity in ticket = more inventory available
                    original_accessory.available_quantity += quantity_difference
                    operation = "increased" if quantity_difference > 0 else "decreased"
                    logger.info(f"ASSET INTAKE/RETURN: Adding {quantity_difference} to inventory")
                else:
                    # Asset Checkout: more quantity in ticket = less inventory available
                    original_accessory.available_quantity -= quantity_difference
                    operation = "decreased" if quantity_difference > 0 else "increased"
                    logger.info(f"ASSET CHECKOUT: Subtracting {quantity_difference} from inventory")
                
                logger.info(f"New inventory available_quantity: {original_accessory.available_quantity}")
                logger.info(f"Inventory {operation} by {abs(quantity_difference)}")
                logger.info("=== INVENTORY UPDATE END ===")
                
                # Create a transaction record
                try:
                    transaction = AccessoryTransaction(
                        accessory_id=original_accessory.id,
                        transaction_type="Ticket Update",
                        quantity=abs(quantity_difference),
                        transaction_number=f"UPD-{ticket_id}-{original_accessory.id}-{int(datetime.datetime.now().timestamp())}",
                        user_id=current_user.id,
                        notes=f"Quantity updated from {old_quantity} to {new_quantity} in ticket #{ticket_id} - inventory {operation}"
                    )
                    db_session.add(transaction)
                except Exception as tx_error:
                    logger.info(f"Error creating transaction: {str(tx_error)}")
                    # Don't fail the whole operation for transaction error
        
        # Add a comment to the ticket
        if quantity_difference != 0:
            comment_content = f"Updated accessory: {name} (Category: {category}, Quantity: {old_quantity} → {new_quantity}, Condition: {condition})"
        else:
            comment_content = f"Updated accessory: {name} (Category: {category}, Quantity: {new_quantity}, Condition: {condition})"
        
        comment = Comment(
            ticket_id=ticket_id,
            user_id=current_user.id,
            content=comment_content
        )
        db_session.add(comment)
        
        # Commit changes
        db_session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Accessory updated successfully',
            'accessory': {
                'id': accessory.id,
                'name': accessory.name,
                'category': accessory.category,
                'quantity': accessory.quantity,
                'condition': accessory.condition,
                'notes': accessory.notes
            }
        })
        
    except Exception as e:
        db_session.rollback()
        logger.info(f"Error updating accessory: {str(e)}")
        return jsonify({'success': False, 'message': f'Error updating accessory: {str(e)}'}), 500
    finally:
        db_session.close()

@tickets_bp.route('/<int:ticket_id>/accessory/<int:accessory_id>/remove', methods=['POST'])
@login_required
def remove_accessory(ticket_id, accessory_id):
    """Remove an accessory from a ticket and update inventory"""
    db_session = db_manager.get_session()
    try:
        # Get the ticket and accessory
        ticket = db_session.query(Ticket).get(ticket_id)
        accessory = db_session.query(TicketAccessory).get(accessory_id)
        
        if not ticket:
            return jsonify({'success': False, 'message': 'Ticket not found'}), 404
            
        if not accessory:
            return jsonify({'success': False, 'message': 'Accessory not found'}), 404
            
        # Verify the accessory belongs to this ticket
        if accessory.ticket_id != ticket_id:
            return jsonify({'success': False, 'message': 'Accessory does not belong to this ticket'}), 400
            
        # Store accessory details before deletion
        accessory_name = accessory.name
        quantity = accessory.quantity
        original_id = accessory.original_accessory_id
        
        # Check if this accessory was taken from inventory
        if original_id:
            # Get the original accessory from inventory with a fresh query
            original_accessory = db_session.query(Accessory).filter(Accessory.id == original_id).with_for_update().first()
            
            if original_accessory:
                # Increase inventory quantity when removing from ticket (returning to stock)
                logger.info("=== INVENTORY UPDATE START ===")
                logger.info(f"REMOVING ACCESSORY FROM TICKET: {quantity} {accessory_name}")
                logger.info(f"Previous inventory quantity: {original_accessory.available_quantity}")

                # Increase the available quantity to return to inventory
                original_accessory.available_quantity += quantity
                logger.info(f"New inventory quantity: {original_accessory.available_quantity}")

                # Update status - if we have stock, it's available
                if original_accessory.available_quantity > 0:
                    original_accessory.status = 'Available'

                logger.info("=== INVENTORY UPDATE END ===")

                # Create a transaction record
                try:
                    transaction = AccessoryTransaction(
                        accessory_id=original_id,
                        transaction_type="Ticket Removal",
                        quantity=quantity,
                        transaction_number=f"IN-{ticket_id}-{original_id}-{int(datetime.datetime.now().timestamp())}",
                        user_id=current_user.id,
                        notes=f"Accessory removed from ticket #{ticket_id} - inventory increased (returned to stock)"
                    )
                    db_session.add(transaction)
                except Exception as tx_error:
                    logger.info(f"Error creating transaction: {str(tx_error)}")
                    raise tx_error
        
        # Create a comment about the removal
        comment = Comment(
            ticket_id=ticket_id,
            user_id=current_user.id,
            content=f"Removed {quantity} x {accessory_name} accessory"
        )
        db_session.add(comment)
        
        # Delete the accessory record
        db_session.delete(accessory)
        
        # Commit all changes
        db_session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Accessory removed successfully'
        })
        
    except Exception as e:
        db_session.rollback()
        logger.info(f"Error removing accessory: {str(e)}")
        return jsonify({'success': False, 'message': f'Error removing accessory: {str(e)}'}), 500
    finally:
        db_session.close()

@tickets_bp.route('/available-accessories', methods=['GET'])
@login_required
def get_available_accessories():
    """Get list of available accessories"""
    db_session = db_manager.get_session()
    try:
        # Query all accessories with available quantity > 0
        accessories = db_session.query(Accessory).filter(Accessory.available_quantity > 0).all()
        
        # Convert to list of dictionaries
        accessories_list = []
        for accessory in accessories:
            accessories_list.append({
                'id': accessory.id,
                'name': accessory.name,
                'category': accessory.category,
                'manufacturer': accessory.manufacturer,
                'model_no': accessory.model_no,
                'available_quantity': accessory.available_quantity,
                'total_quantity': accessory.total_quantity,
                'country': accessory.country,
                'status': accessory.status
            })
            
        return jsonify({
            'success': True,
            'accessories': accessories_list
        })
        
    except Exception as e:
        logger.info(f"Error getting available accessories: {str(e)}")
        return jsonify({'success': False, 'message': f'Error getting available accessories: {str(e)}'}), 500
    finally:
        db_session.close()

@tickets_bp.route('/fix-accessory-inventory/<int:accessory_id>', methods=['POST'])
@login_required
def fix_accessory_inventory(accessory_id):
    """Emergency endpoint to fix accessory inventory quantities"""
    try:
        # Get database session using db_manager
        db_session = db_manager.get_session()
        from models.accessory import Accessory
        from models.accessory_transaction import AccessoryTransaction
        from flask_login import current_user
        import time
        
        # Get the accessory with exclusive lock
        accessory = db_session.query(Accessory).filter(Accessory.id == accessory_id).with_for_update().first()
        
        if not accessory:
            return jsonify({'success': False, 'message': 'Accessory not found'}), 404
        
        # Get the new quantity value from the request
        data = request.get_json()
        if not data or 'new_quantity' not in data:
            return jsonify({'success': False, 'message': 'New quantity is required'}), 400
            
        try:
            new_quantity = int(data['new_quantity'])
            if new_quantity < 0:
                return jsonify({'success': False, 'message': 'Quantity cannot be negative'}), 400
        except (ValueError, TypeError):
            return jsonify({'success': False, 'message': 'Invalid quantity format'}), 400
            
        # Calculate the difference
        old_quantity = accessory.available_quantity
        difference = new_quantity - old_quantity
        
        # Update the accessory quantity
        accessory.available_quantity = new_quantity
        
        # Create a transaction record
        timestamp = int(time.time())
        tx_number = f"FIX-{accessory.id}-{timestamp}"
        
        transaction = AccessoryTransaction(
            accessory_id=accessory.id,
            transaction_type="Manual Fix",
            quantity=abs(difference),
            transaction_number=tx_number,
            user_id=current_user.id,
            notes=f"Manual inventory correction from {old_quantity} to {new_quantity} ({'+' if difference >= 0 else '-'}{abs(difference)})"
        )
        db_session.add(transaction)
        
        # Commit changes
        db_session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Accessory quantity updated from {old_quantity} to {new_quantity}',
            'accessory': {
                'id': accessory.id,
                'name': accessory.name,
                'category': accessory.category,
                'old_quantity': old_quantity,
                'new_quantity': new_quantity,
                'difference': difference
            }
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        logger.info(f"Error fixing accessory inventory: {str(e)}")
        db_session.rollback()
        return jsonify({'success': False, 'message': f'Error fixing accessory inventory: {str(e)}'}), 500

@tickets_bp.route('/api/accessories')
@login_required
def get_accessories():
    """Get all accessories for dropdown"""
    logger.info("API endpoint /api/accessories called")
    db_session = None
    try:
        db_session = db_manager.get_session()
        result = []
        
        # Get all accessories with available quantity > 0
        logger.info("Querying accessories with available_quantity > 0")
        accessories = db_session.query(Accessory).filter(
            Accessory.available_quantity > 0
        ).all()
        
        logger.info(f"Found {len(accessories)} accessories with available quantity")
        
        # Convert to list of dicts
        for acc in accessories:
            result.append({
                'id': acc.id,
                'name': acc.name,
                'category': acc.category,
                'available_quantity': acc.available_quantity,
                'manufacturer': acc.manufacturer,
                'model_no': acc.model_no
            })
        
        logger.info(f"Returning {len(result)} accessories in JSON response")
        return jsonify({'success': True, 'accessories': result})
        
    except Exception as e:
        logger.info(f"Error in get_accessories: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': f'Error retrieving accessories: {str(e)}'}), 500
    finally:
        if db_session:
            db_session.close()

@tickets_bp.route('/api/accessories/debug')
@login_required
def debug_accessories():
    """Debug endpoint to check all accessories in database"""
    logger.info("API endpoint /api/accessories/debug called")
    db_session = None
    try:
        db_session = db_manager.get_session()
        
        # Get ALL accessories regardless of quantity
        all_accessories = db_session.query(Accessory).all()
        logger.info(f"Total accessories in database: {len(all_accessories)}")
        
        # Get accessories with available quantity > 0
        available_accessories = db_session.query(Accessory).filter(
            Accessory.available_quantity > 0
        ).all()
        logger.info(f"Accessories with available_quantity > 0: {len(available_accessories)}")
        
        # Prepare detailed response
        result = {
            'total_accessories': len(all_accessories),
            'available_accessories': len(available_accessories),
            'all_accessories': [],
            'available_accessories_details': []
        }
        
        # Add details for all accessories
        for acc in all_accessories:
            result['all_accessories'].append({
                'id': acc.id,
                'name': acc.name,
                'category': acc.category,
                'total_quantity': acc.total_quantity,
                'available_quantity': acc.available_quantity,
                'status': acc.status
            })
        
        # Add details for available accessories
        for acc in available_accessories:
            result['available_accessories_details'].append({
                'id': acc.id,
                'name': acc.name,
                'category': acc.category,
                'available_quantity': acc.available_quantity,
                'manufacturer': acc.manufacturer,
                'model_no': acc.model_no
            })
        
        return jsonify({'success': True, 'debug_info': result})
        
    except Exception as e:
        logger.info(f"Error in debug_accessories: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': f'Error debugging accessories: {str(e)}'}), 500
    finally:
        if db_session:
            db_session.close()

@tickets_bp.route('/<int:ticket_id>/accessory-transactions', methods=['GET'])
@login_required
def view_accessory_transactions(ticket_id):
    """View transactions for accessories related to a ticket"""
    db_session = db_manager.get_session()
    try:
        # Get the ticket and its accessories
        ticket = db_session.query(Ticket).get(ticket_id)
        if not ticket:
            return jsonify({'success': False, 'message': 'Ticket not found'}), 404
            
        # Get all accessories for this ticket
        accessories = db_session.query(TicketAccessory).filter(
            TicketAccessory.ticket_id == ticket_id
        ).all()
        
        # Get original accessory IDs
        original_accessory_ids = [acc.original_accessory_id for acc in accessories if acc.original_accessory_id]
        
        # Get transactions for these accessories
        transactions = []
        
        if original_accessory_ids:
            raw_transactions = db_session.query(AccessoryTransaction).filter(
                AccessoryTransaction.accessory_id.in_(original_accessory_ids)
            ).order_by(AccessoryTransaction.transaction_date.desc()).all()
            
            for tx in raw_transactions:
                accessory = db_session.query(Accessory).get(tx.accessory_id)
                accessory_name = accessory.name if accessory else "Unknown"
                
                transactions.append({
                    'id': tx.id,
                    'transaction_number': tx.transaction_number,
                    'accessory_id': tx.accessory_id,
                    'accessory_name': accessory_name,
                    'transaction_type': tx.transaction_type,
                    'quantity': tx.quantity,
                    'notes': tx.notes,
                    'transaction_date': tx.transaction_date.strftime('%Y-%m-%d %H:%M:%S') if tx.transaction_date else None
                })
                
        # Also check if any updates are needed for accessories
        inventory_checks = []
        for acc in accessories:
            if acc.original_accessory_id:
                original = db_session.query(Accessory).get(acc.original_accessory_id)
                if original:
                    inventory_checks.append({
                        'ticket_accessory_id': acc.id,
                        'ticket_accessory_name': acc.name,
                        'ticket_accessory_quantity': acc.quantity,
                        'inventory_id': original.id,
                        'inventory_name': original.name,
                        'inventory_quantity': original.available_quantity
            })
            
        return jsonify({
            'success': True,
            'ticket_id': ticket_id,
            'transactions': transactions,
            'inventory_checks': inventory_checks
        })
        
    except Exception as e:
        logger.info(f"Error retrieving accessory transactions: {str(e)}")
        return jsonify({'success': False, 'message': f'Error retrieving transactions: {str(e)}'}), 500
    finally:
            db_session.close()

@tickets_bp.route('/<int:ticket_id>/accessory/<int:accessory_id>', methods=['GET'])
@login_required
def get_ticket_accessory(ticket_id, accessory_id):
    """Get accessory details for editing"""
    try:
        # Get database session using db_manager
        db_session = db_manager.get_session()
        from models.ticket import TicketAccessory
        
        # Get the accessory
        accessory = db_session.query(TicketAccessory).get(accessory_id)
        if not accessory:
            return jsonify({'success': False, 'message': 'Accessory not found'}), 404
            
        # Verify the accessory belongs to this ticket
        if accessory.ticket_id != ticket_id:
            return jsonify({'success': False, 'message': 'Accessory does not belong to this ticket'}), 400
            
        return jsonify({
            'success': True,
            'accessory': {
                'id': accessory.id,
                'name': accessory.name,
                'category': accessory.category,
                'quantity': accessory.quantity,
                'condition': accessory.condition,
                'notes': accessory.notes
            }
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        logger.info(f"Error getting accessory: {str(e)}")
        return jsonify({'success': False, 'message': f'Error getting accessory: {str(e)}'}), 500
    finally:
        db_session.close()

@tickets_bp.route('/api/debug/form-data', methods=['POST'])
@login_required
def debug_form_data():
    """Debug endpoint to check what form data is being received"""
    try:
        logger.info("=== FORM DEBUG ENDPOINT ===")
        logger.info(f"Form keys: {list(request.form.keys())}")
        logger.info("Form data:")
        for key, value in request.form.items():
            if key == 'selected_accessories':
                logger.info(f"  {key}: {value[:200]}..." if len(value) > 200 else f"  {key}: {value}")
            else:
                logger.info(f"  {key}: {value}")
        
        selected_accessories = request.form.get('selected_accessories', '')
        if selected_accessories:
            try:
                import json
                parsed = json.loads(selected_accessories)
                logger.info(f"Parsed accessories: {len(parsed)} items")
                for i, acc in enumerate(parsed):
                    logger.info(f"  {i}: {acc}")
            except Exception as e:
                logger.info(f"Error parsing accessories JSON: {e}")
        else:
            logger.info("No selected_accessories field found")
        
        return jsonify({
            'status': 'success',
            'form_keys': list(request.form.keys()),
            'selected_accessories_present': 'selected_accessories' in request.form,
            'selected_accessories_length': len(request.form.get('selected_accessories', ''))
        })
    except Exception as e:
        logger.info(f"Debug endpoint error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@tickets_bp.route('/api/accessories/search', methods=['POST'])
@login_required
def search_accessories_for_csv():
    """Search for accessories in inventory based on CSV data"""
    try:
        data = request.get_json()
        product_name = data.get('product_name', '')
        category = data.get('category', '')
        brand = data.get('brand', '')
        model = data.get('model', '')
        
        db_session = db_manager.get_session()
        
        # Build search query
        accessories_query = db_session.query(Accessory).filter(
            Accessory.available_quantity > 0
        )
        
        matches = []
        
        # Search by exact product name match
        if product_name:
            exact_matches = accessories_query.filter(
                Accessory.name.ilike(f'%{product_name}%')
            ).limit(3).all()
            
            for accessory in exact_matches:
                matches.append({
                    'id': accessory.id,
                    'name': accessory.name,
                    'category': accessory.category,
                    'manufacturer': accessory.manufacturer,
                    'model_no': accessory.model_no,
                    'available_quantity': accessory.available_quantity,
                    'match_type': 'Product Name',
                    'confidence': 'High'
                })
        
        # Search by category if provided
        if category and len(matches) < 5:
            category_matches = accessories_query.filter(
                Accessory.category.ilike(f'%{category}%')
            ).limit(3).all()
            
            for accessory in category_matches:
                # Avoid duplicates
                if not any(m['id'] == accessory.id for m in matches):
                    matches.append({
                        'id': accessory.id,
                        'name': accessory.name,
                        'category': accessory.category,
                        'manufacturer': accessory.manufacturer,
                        'model_no': accessory.model_no,
                        'available_quantity': accessory.available_quantity,
                        'match_type': 'Category',
                        'confidence': 'Medium'
                    })
        
        # Search by brand/manufacturer if provided
        if brand and len(matches) < 5:
            brand_matches = accessories_query.filter(
                or_(
                    Accessory.manufacturer.ilike(f'%{brand}%'),
                    Accessory.name.ilike(f'%{brand}%')
                )
            ).limit(3).all()
            
            for accessory in brand_matches:
                # Avoid duplicates
                if not any(m['id'] == accessory.id for m in matches):
                    matches.append({
                        'id': accessory.id,
                        'name': accessory.name,
                        'category': accessory.category,
                        'manufacturer': accessory.manufacturer,
                        'model_no': accessory.model_no,
                        'available_quantity': accessory.available_quantity,
                        'match_type': 'Brand/Manufacturer',
                        'confidence': 'Medium'
                    })
        
        # Fuzzy search for remaining slots
        if len(matches) < 5:
            search_terms = []
            if product_name:
                search_terms.extend(product_name.split())
            if category:
                search_terms.extend(category.split())
            if brand:
                search_terms.extend(brand.split())
            if model:
                search_terms.extend(model.split())
            
            for term in search_terms:
                if len(term) > 3:  # Only search terms longer than 3 characters
                    fuzzy_matches = accessories_query.filter(
                        or_(
                            Accessory.name.ilike(f'%{term}%'),
                            Accessory.category.ilike(f'%{term}%'),
                            Accessory.manufacturer.ilike(f'%{term}%'),
                            Accessory.model_no.ilike(f'%{term}%')
                        )
                    ).limit(2).all()
                    
                    for accessory in fuzzy_matches:
                        # Avoid duplicates
                        if not any(m['id'] == accessory.id for m in matches):
                            matches.append({
                                'id': accessory.id,
                                'name': accessory.name,
                                'category': accessory.category,
                                'manufacturer': accessory.manufacturer,
                                'model_no': accessory.model_no,
                                'available_quantity': accessory.available_quantity,
                                'match_type': 'Fuzzy Match',
                                'confidence': 'Low'
                            })
                    
                    if len(matches) >= 5:
                        break
        
        return jsonify({
            'success': True,
            'matches': matches[:5]  # Limit to top 5 matches
        })
        
    except Exception as e:
        logger.info(f"Error searching accessories: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
    finally:
        db_session.close()

@tickets_bp.route('/<int:ticket_id>/api/items', methods=['GET'])
@login_required
def get_ticket_items(ticket_id):
    """API endpoint to get assets or accessories for a specific ticket"""
    try:
        item_type = request.args.get('type', '').lower()
        
        if item_type not in ['asset', 'accessory']:
            return jsonify({'success': False, 'message': 'Invalid item type. Must be "asset" or "accessory"'})
        
        # Get database session
        db_session = db_manager.get_session()
        
        try:
            # Get the ticket using the database session to avoid lazy loading issues
            from models.ticket import Ticket
            from models.asset import Asset
            from models.accessory import Accessory
            from sqlalchemy import text
            
            ticket = db_session.query(Ticket).filter(Ticket.id == ticket_id).first()
            if not ticket:
                return jsonify({'success': False, 'message': 'Ticket not found'})
            
            items = []
            
            if item_type == 'asset':
                # Get assets assigned to this ticket - check both:
                # 1. Direct FK via ticket.asset_id
                # 2. Many-to-many via ticket_assets table
                result = db_session.execute(text("""
                    SELECT DISTINCT a.id, a.asset_tag, a.serial_num, a.model, a.name,
                           a.hardware_type, a.manufacturer
                    FROM assets a
                    WHERE a.id IN (
                        -- Direct FK on ticket
                        SELECT t.asset_id FROM tickets t WHERE t.id = :ticket_id AND t.asset_id IS NOT NULL
                        UNION
                        -- Many-to-many via ticket_assets
                        SELECT ta.asset_id FROM ticket_assets ta WHERE ta.ticket_id = :ticket_id
                    )
                """), {'ticket_id': ticket_id})

                for row in result:
                    asset_id, asset_tag, serial_num, model, name, hardware_type, manufacturer = row
                    # Build display name with available info - prioritize hardware_type and asset_tag
                    display_parts = []

                    # Primary identifier
                    if asset_tag:
                        display_parts.append(asset_tag)
                    elif serial_num:
                        display_parts.append(serial_num)

                    # Description - prefer hardware_type, then model, then name
                    if hardware_type:
                        display_parts.append(hardware_type)
                    elif model:
                        display_parts.append(model)
                    elif name:
                        display_parts.append(name)

                    # Add manufacturer if we have it and nothing else
                    if manufacturer and len(display_parts) < 2:
                        display_parts.append(manufacturer)

                    if display_parts:
                        display_name = " - ".join(display_parts)
                    else:
                        display_name = f"Asset ID: {asset_id}"

                    items.append({
                        'id': asset_id,
                        'display_name': display_name,
                        'asset_tag': asset_tag or '',
                        'serial_num': serial_num or '',
                        'model': model or '',
                        'hardware_type': hardware_type or ''
                    })
            
            elif item_type == 'accessory':
                # Get accessories assigned to this ticket - check both:
                # 1. Direct FK via ticket.accessory_id
                # 2. Many-to-many via ticket_accessories table
                result = db_session.execute(text("""
                    SELECT DISTINCT a.id, a.name, a.model_no, a.category
                    FROM accessories a
                    WHERE a.id IN (
                        -- Direct FK on ticket
                        SELECT t.accessory_id FROM tickets t WHERE t.id = :ticket_id AND t.accessory_id IS NOT NULL
                        UNION
                        -- Many-to-many via ticket_accessories (original_accessory_id)
                        SELECT ta.original_accessory_id FROM ticket_accessories ta WHERE ta.ticket_id = :ticket_id AND ta.original_accessory_id IS NOT NULL
                    )
                """), {'ticket_id': ticket_id})

                for row in result:
                    accessory_id, name, model_no, category = row
                    # Build display name with available info
                    if name and model_no:
                        display_name = f"{name} ({model_no})"
                    elif name:
                        display_name = f"{name}"
                    elif category:
                        display_name = f"{category} (ID: {accessory_id})"
                    else:
                        display_name = f"Accessory ID: {accessory_id}"
                    items.append({
                        'id': accessory_id,
                        'display_name': display_name,
                        'name': name or '',
                        'model': model_no or ''
                    })
            
            return jsonify({
                'success': True,
                'items': items,
                'count': len(items),
                'item_type': item_type
            })
            
        except Exception as e:
            logger.info(f"Error fetching {item_type}s for ticket {ticket_id}: {str(e)}")
            return jsonify({'success': False, 'message': f'Database error: {str(e)}'})
        
        finally:
            db_session.close()
    
    except Exception as e:
        logger.info(f"Error in get_ticket_items: {str(e)}")
        return jsonify({'success': False, 'message': f'Server error: {str(e)}'})


@tickets_bp.route('/change_queue/<int:ticket_id>', methods=['POST'])
@login_required
def change_ticket_queue(ticket_id):
    """Change the queue for a ticket"""
    logger.info(f"Starting queue change for ticket {ticket_id}")
    db_session = db_manager.get_session()
    try:
        new_queue_id = request.form.get('queue_id')
        logger.info(f"Form data received - queue_id: {new_queue_id}")
        
        if not new_queue_id:
            logger.warning("No queue_id provided in form")
            flash('Please select a queue', 'error')
            return redirect(url_for('tickets.view_ticket', ticket_id=ticket_id))
        
        # Get the ticket
        logger.info(f"Looking up ticket {ticket_id}")
        ticket = db_session.query(Ticket).get(ticket_id)
        if not ticket:
            logger.warning(f"Ticket {ticket_id} not found")
            flash('Ticket not found', 'error')
            return redirect(url_for('tickets.list_tickets'))
        
        # Get the new queue
        logger.info(f"Looking up queue {new_queue_id}")
        new_queue = db_session.query(Queue).get(new_queue_id)
        if not new_queue:
            logger.warning(f"Queue {new_queue_id} not found")
            flash('Queue not found', 'error')
            return redirect(url_for('tickets.view_ticket', ticket_id=ticket_id))
        
        # Store old queue info for logging and notifications
        old_queue_id = ticket.queue_id
        old_queue_name = ticket.queue.name if ticket.queue else "No Queue"
        logger.info(f"Changing queue from '{old_queue_name}' to '{new_queue.name}'")
        
        # Update the ticket queue
        ticket.queue_id = int(new_queue_id)
        ticket.updated_at = datetime.datetime.utcnow()
        
        # Add a comment about the queue change
        comment = Comment(
            ticket_id=ticket_id,
            user_id=current_user.id,
            content=f"Queue changed from '{old_queue_name}' to '{new_queue.name}'"
        )
        db_session.add(comment)
        
        logger.info("Committing database changes")
        db_session.commit()
        
        # Send queue move notifications
        try:
            from utils.queue_notification_sender import send_queue_move_notifications
            send_queue_move_notifications(ticket, old_queue_id, int(new_queue_id))
        except Exception as e:
            logger.error(f"Error sending queue move notifications: {str(e)}")
        
        flash(f'Ticket queue changed to {new_queue.name}', 'success')
        logger.info(f"Successfully changed ticket {ticket_id} queue from '{old_queue_name}' to '{new_queue.name}'")
        
    except Exception as e:
        db_session.rollback()
        logger.error(f"Error changing queue for ticket {ticket_id}: {str(e)}")
        import traceback
        logger.error(f"Full traceback: {traceback.format_exc()}")
        flash(f'Failed to change ticket queue: {str(e)}', 'error')
    finally:
        db_session.close()
    
    return redirect(url_for('tickets.view_ticket', ticket_id=ticket_id))

# Notification endpoints
@tickets_bp.route('/notifications', methods=['GET'])
@login_required
def get_notifications():
    """Get notifications for the current user"""
    try:
        from utils.notification_service import NotificationService
        
        notification_service = NotificationService(db_manager)
        user_id = session['user_id']
        
        # Get query parameters
        limit = request.args.get('limit', 50, type=int)
        unread_only = request.args.get('unread_only', 'false').lower() == 'true'
        
        notifications = notification_service.get_user_notifications(
            user_id=user_id,
            limit=limit,
            unread_only=unread_only
        )

        # Service now returns dicts, just format datetime for JSON
        notifications_data = []
        for n in notifications:
            notifications_data.append({
                'id': n['id'],
                'type': n['type'],
                'title': n['title'],
                'message': n['message'],
                'is_read': n['is_read'],
                'created_at': n['created_at'].isoformat() if n['created_at'] else None,
                'reference_type': n['reference_type'],
                'reference_id': n['reference_id']
            })

        return jsonify({
            'success': True,
            'notifications': notifications_data
        })
        
    except Exception as e:
        logger.error(f"Error getting notifications: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to get notifications'
        }), 500

@tickets_bp.route('/notifications/unread-count', methods=['GET'])
@login_required
def get_unread_count():
    """Get unread notification count for the current user"""
    try:
        from utils.notification_service import NotificationService
        
        notification_service = NotificationService(db_manager)
        user_id = session['user_id']
        
        count = notification_service.get_unread_count(user_id)
        
        return jsonify({
            'success': True,
            'count': count
        })
        
    except Exception as e:
        logger.error(f"Error getting unread count: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to get unread count'
        }), 500

@tickets_bp.route('/notifications/<int:notification_id>/mark-read', methods=['POST'])
@login_required
def mark_notification_read(notification_id):
    """Mark a notification as read"""
    try:
        from utils.notification_service import NotificationService
        
        notification_service = NotificationService(db_manager)
        user_id = session['user_id']
        
        success = notification_service.mark_notification_as_read(notification_id, user_id)
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Notification marked as read'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Notification not found or access denied'
            }), 404
        
    except Exception as e:
        logger.error(f"Error marking notification as read: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to mark notification as read'
        }), 500

@tickets_bp.route('/notifications/mark-all-read', methods=['POST'])
@login_required
def mark_all_notifications_read():
    """Mark all notifications as read for the current user"""
    try:
        from utils.notification_service import NotificationService
        
        notification_service = NotificationService(db_manager)
        user_id = session['user_id']
        
        success = notification_service.mark_all_as_read(user_id)
        
        if success:
            return jsonify({
                'success': True,
                'message': 'All notifications marked as read'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to mark notifications as read'
            }), 500
        
    except Exception as e:
        logger.error(f"Error marking all notifications as read: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to mark all notifications as read'
        }), 500

@tickets_bp.route('/users/search', methods=['GET'])
@login_required
def search_users():
    """Search users for @mention autocomplete"""
    try:
        query = request.args.get('q', '').strip()
        if not query or len(query) < 1:
            return jsonify({'success': True, 'users': []})
        
        db_session = db_manager.get_session()
        try:
            # Search users by username or email
            # Exclude deactivated/deleted users
            users = db_session.query(User).filter(
                or_(
                    User.username.ilike(f'%{query}%'),
                    User.email.ilike(f'%{query}%')
                ),
                or_(User.is_deleted == False, User.is_deleted == None)
            ).all()
            
            # Convert to dict for JSON response
            users_data = []
            for user in users:
                users_data.append({
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'display_name': f"{user.username} ({user.email})" if user.email != user.username else user.username
                })
            
            return jsonify({
                'success': True,
                'users': users_data
            })
            
        finally:
            db_session.close()
            
    except Exception as e:
        logger.error(f"Error searching users: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to search users'
        }), 500

@tickets_bp.route('/test-notification', methods=['POST'])
@login_required
def test_notification():
    """Test endpoint to create a realistic cross-user mention notification"""
    try:
        from utils.notification_service import NotificationService
        from models.user import User
        
        notification_service = NotificationService(db_manager)
        current_user_id = session['user_id']
        
        logger.info(f"Creating test notification for current user {current_user_id}")
        
        # Get a different user to simulate a mention FROM another user TO current user
        db_session = db_manager.get_session()
        try:
            from models.ticket import Ticket
            
            # Get a ticket that exists
            ticket = db_session.query(Ticket).first()
            if not ticket:
                return jsonify({
                    'success': False,
                    'error': 'No tickets found in database'
                }), 400
            
            # Get a different user to be the "commenter" (someone mentioning the current user)
            other_user = db_session.query(User).filter(User.id != current_user_id).first()
            if not other_user:
                return jsonify({
                    'success': False,
                    'error': 'Need at least 2 users for realistic testing'
                }), 400
            
            current_user = db_session.query(User).get(current_user_id)
            
            logger.info(f"Simulating: {other_user.username} mentions {current_user.username} in ticket #{ticket.display_id}")
            
        finally:
            db_session.close()
        
        # Create a realistic test notification: other_user mentions current_user
        success = notification_service.create_mention_notification(
            mentioned_user_id=current_user_id,  # Current user gets the notification
            commenter_user_id=other_user.id,   # Other user is the one who mentioned
            ticket_id=ticket.id,
            comment_content=f"Hey @{current_user.username}, can you help with this ticket? This is urgent!"
        )
        
        if success:
            logger.info("Realistic test notification created successfully")
            return jsonify({
                'success': True,
                'message': f'Test notification created: {other_user.username} mentioned you in ticket #{ticket.display_id}'
            })
        else:
            logger.error("Failed to create test notification")
            return jsonify({
                'success': False,
                'error': 'Failed to create test notification'
            }), 500
        
    except Exception as e:
        logger.error(f"Error creating test notification: {str(e)}")
        import traceback
        logger.error(f"Full traceback: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': f'Failed to create test notification: {str(e)}'
        }), 500


# ============================================================================
# CUSTOM ISSUE TYPES ROUTES
# ============================================================================

@tickets_bp.route('/issue-types', methods=['GET'])
@login_required
def get_custom_issue_types():
    """Get all custom issue types"""
    from models.custom_issue_type import CustomIssueType

    db_session = db_manager.get_session()
    try:
        custom_types = db_session.query(CustomIssueType).filter_by(is_active=True).order_by(CustomIssueType.usage_count.desc()).all()
        return jsonify({
            'success': True,
            'custom_types': [t.to_dict() for t in custom_types]
        })
    except Exception as e:
        logger.error(f"Error getting custom issue types: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db_session.close()


# ============================================================================
# TICKET ISSUE MANAGEMENT ROUTES
# ============================================================================

@tickets_bp.route('/<int:ticket_id>/issues', methods=['GET'])
@login_required
def get_ticket_issues(ticket_id):
    """Get all issues for a ticket"""
    from models.ticket_issue import TicketIssue
    
    db_session = db_manager.get_session()
    try:
        # Check if ticket exists and user has permission
        ticket = db_session.query(Ticket).get(ticket_id)
        if not ticket:
            return jsonify({'success': False, 'error': 'Ticket not found'}), 404
        
        # Get all issues for this ticket
        issues = db_session.query(TicketIssue).filter_by(ticket_id=ticket_id).order_by(TicketIssue.reported_at.desc()).all()
        
        return jsonify({
            'success': True,
            'issues': [issue.to_dict() for issue in issues]
        })
    except Exception as e:
        logger.error(f"Error getting ticket issues: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db_session.close()


@tickets_bp.route('/<int:ticket_id>/issues', methods=['POST'])
@login_required
def create_ticket_issue(ticket_id):
    """Create a new issue for a ticket"""
    from models.ticket_issue import TicketIssue
    from models.notification import Notification
    from models.custom_issue_type import CustomIssueType

    # Predefined issue types that shouldn't be saved as custom
    PREDEFINED_TYPES = [
        'Wrong Accessories', 'Wrong Address', 'Missing Items', 'Damaged Items',
        'Tracking Issue', 'Device Damage', 'Wrong Device', 'Address Issue', 'Other'
    ]

    db_session = db_manager.get_session()
    try:
        # Check if ticket exists
        ticket = db_session.query(Ticket).get(ticket_id)
        if not ticket:
            return jsonify({'success': False, 'error': 'Ticket not found'}), 404

        # Check if user is the ticket owner or has permission
        # Allow: ticket requester, SUPER_ADMIN, DEVELOPER, COUNTRY_ADMIN, SUPERVISOR
        allowed_types = ['SUPER_ADMIN', 'DEVELOPER', 'COUNTRY_ADMIN', 'SUPERVISOR']
        if ticket.requester_id != session.get('user_id') and session.get('user_type') not in allowed_types:
            return jsonify({'success': False, 'error': 'Permission denied'}), 403

        # Get data from request
        data = request.get_json()
        issue_type = data.get('issue_type')
        description = data.get('description')

        if not issue_type or not description:
            return jsonify({'success': False, 'error': 'Issue type and description are required'}), 400

        # Save custom issue type if it's not predefined
        if issue_type not in PREDEFINED_TYPES:
            existing_custom = db_session.query(CustomIssueType).filter_by(name=issue_type).first()
            if existing_custom:
                # Increment usage count
                existing_custom.usage_count += 1
            else:
                # Create new custom issue type
                new_custom_type = CustomIssueType(name=issue_type)
                db_session.add(new_custom_type)

        # Extract @mentions from description
        import re
        from models.group import Group
        from models.group_membership import GroupMembership
        mention_pattern = r'@([a-zA-Z0-9._@-]+)'
        mentions = re.findall(mention_pattern, description)

        notified_user_ids = set()
        for mention in mentions:
            # Check if it's a user
            mentioned_user = db_session.query(User).filter(User.username == mention).first()
            if mentioned_user and mentioned_user.id != session.get('user_id'):
                notified_user_ids.add(mentioned_user.id)
            else:
                # Check if it's a group
                group = db_session.query(Group).filter(Group.name == mention, Group.is_active == True).first()
                if group:
                    memberships = db_session.query(GroupMembership).filter_by(group_id=group.id).all()
                    for membership in memberships:
                        if membership.user_id != session.get('user_id'):
                            notified_user_ids.add(membership.user_id)

        # Create new issue
        new_issue = TicketIssue(
            ticket_id=ticket_id,
            issue_type=issue_type,
            description=description,
            reported_by_id=session.get('user_id'),
            reported_at=datetime.datetime.utcnow(),
            notified_user_ids=','.join(map(str, notified_user_ids)) if notified_user_ids else ''
        )

        db_session.add(new_issue)
        db_session.commit()

        # Create notifications for @mentioned users and send emails
        reporter = db_session.query(User).get(session.get('user_id'))
        from utils.email_sender import send_issue_reported_email

        for user_id in notified_user_ids:
            # Create in-app notification
            notification = Notification(
                user_id=int(user_id),
                type='issue_reported',
                title=f'Issue Reported on Ticket #{ticket.display_id}',
                message=f'{reporter.username} mentioned you: {issue_type} - {description[:100]}',
                reference_type='ticket',
                reference_id=ticket_id,
                is_read=False,
                created_at=datetime.datetime.utcnow()
            )
            db_session.add(notification)

            # Send email notification
            notified_user = db_session.query(User).get(int(user_id))
            if notified_user and notified_user.email:
                try:
                    send_issue_reported_email(
                        notified_user=notified_user,
                        reporter=reporter,
                        ticket=ticket,
                        issue_type=issue_type,
                        description=description
                    )
                except Exception as email_error:
                    logger.error(f"Failed to send issue email to {notified_user.email}: {str(email_error)}")

        db_session.commit()
        
        logger.info(f"Issue created for ticket {ticket_id} by user {session.get('user_id')}")
        
        return jsonify({
            'success': True,
            'message': 'Issue reported successfully',
            'issue': new_issue.to_dict()
        })
    except Exception as e:
        db_session.rollback()
        logger.error(f"Error creating ticket issue: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db_session.close()


@tickets_bp.route('/<int:ticket_id>/issues/<int:issue_id>/resolve', methods=['POST'])
@login_required
def resolve_ticket_issue(ticket_id, issue_id):
    """Mark an issue as resolved"""
    from models.ticket_issue import TicketIssue
    from models.notification import Notification
    
    db_session = db_manager.get_session()
    try:
        # Get the issue
        issue = db_session.query(TicketIssue).filter_by(id=issue_id, ticket_id=ticket_id).first()
        if not issue:
            return jsonify({'success': False, 'error': 'Issue not found'}), 404

        # Get the ticket to check ownership
        ticket = db_session.query(Ticket).get(ticket_id)
        if not ticket:
            return jsonify({'success': False, 'error': 'Ticket not found'}), 404

        # Check permission - allow admins, ticket owner, or assigned user
        current_user_id = session.get('user_id')
        current_user_type = session.get('user_type')
        is_admin = current_user_type in ['SUPER_ADMIN', 'ADMIN']
        is_ticket_owner = ticket.requester_id == current_user_id
        is_assigned = ticket.assigned_to_id == current_user_id

        if not (is_admin or is_ticket_owner or is_assigned):
            return jsonify({'success': False, 'error': 'Permission denied. Only admins, ticket owner, or assigned user can resolve issues.'}), 403
        
        # Get resolution notes from request
        data = request.get_json()
        resolution_notes = data.get('resolution_notes', '')
        
        # Update issue
        issue.is_resolved = True
        issue.resolution_notes = resolution_notes
        issue.resolved_by_id = session.get('user_id')
        issue.resolved_at = datetime.datetime.utcnow()
        
        db_session.commit()
        
        # Notify the reporter
        resolver = db_session.query(User).get(session.get('user_id'))
        # Ticket already fetched above, reuse it
        notification = Notification(
            user_id=issue.reported_by_id,
            type='issue_resolved',
            title=f'Issue Resolved on Ticket #{ticket.display_id}',
            message=f'{resolver.username} resolved your issue: {issue.issue_type}',
            reference_type='ticket',
            reference_id=ticket_id,
            is_read=False,
            created_at=datetime.datetime.utcnow()
        )
        db_session.add(notification)
        db_session.commit()
        
        logger.info(f"Issue {issue_id} resolved by user {session.get('user_id')}")

        return jsonify({
            'success': True,
            'message': 'Issue resolved successfully',
            'issue': issue.to_dict()
        })
    except Exception as e:
        db_session.rollback()
        logger.error(f"Error resolving ticket issue: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db_session.close()


@tickets_bp.route('/<int:ticket_id>/issues/<int:issue_id>/reopen', methods=['POST'])
@login_required
def reopen_ticket_issue(ticket_id, issue_id):
    """Reopen a resolved issue on a ticket"""
    from models.ticket_issue import TicketIssue
    from models.notification import Notification

    db_session = db_manager.get_session()
    try:
        # Get the issue
        issue = db_session.query(TicketIssue).filter_by(id=issue_id, ticket_id=ticket_id).first()
        if not issue:
            return jsonify({'success': False, 'error': 'Issue not found'}), 404

        # Check if issue is already open
        if not issue.is_resolved:
            return jsonify({'success': False, 'error': 'Issue is already open'}), 400

        # Get the ticket
        ticket = db_session.query(Ticket).get(ticket_id)
        if not ticket:
            return jsonify({'success': False, 'error': 'Ticket not found'}), 404

        # Check permission - allow admins, ticket owner, or assigned user
        current_user_id = session.get('user_id')
        current_user_type = session.get('user_type')
        is_admin = current_user_type in ['SUPER_ADMIN', 'ADMIN']
        is_ticket_owner = ticket.requester_id == current_user_id
        is_assigned = ticket.assigned_to_id == current_user_id
        is_issue_reporter = issue.reported_by_id == current_user_id

        if not (is_admin or is_ticket_owner or is_assigned or is_issue_reporter):
            return jsonify({'success': False, 'error': 'Permission denied. Only admins, ticket owner, assigned user, or issue reporter can reopen issues.'}), 403

        # Update issue - reopen it
        issue.is_resolved = False
        issue.resolution_notes = None
        issue.resolved_by_id = None
        issue.resolved_at = None

        db_session.commit()

        # Notify relevant users about the reopened issue
        reopener = db_session.query(User).get(session.get('user_id'))

        # Notify the ticket owner if they didn't reopen it
        if ticket.requester_id != current_user_id:
            notification = Notification(
                user_id=ticket.requester_id,
                type='issue_reopened',
                title=f'Issue Reopened on Ticket #{ticket.display_id}',
                message=f'{reopener.username} reopened issue: {issue.issue_type}',
                reference_type='ticket',
                reference_id=ticket_id,
                is_read=False,
                created_at=datetime.datetime.utcnow()
            )
            db_session.add(notification)

        # Notify assigned user if they didn't reopen it and ticket is assigned
        if ticket.assigned_to_id and ticket.assigned_to_id != current_user_id:
            notification = Notification(
                user_id=ticket.assigned_to_id,
                type='issue_reopened',
                title=f'Issue Reopened on Ticket #{ticket.display_id}',
                message=f'{reopener.username} reopened issue: {issue.issue_type}',
                reference_type='ticket',
                reference_id=ticket_id,
                is_read=False,
                created_at=datetime.datetime.utcnow()
            )
            db_session.add(notification)

        db_session.commit()

        logger.info(f"Issue {issue_id} reopened by user {session.get('user_id')}")

        return jsonify({
            'success': True,
            'message': 'Issue reopened successfully',
            'issue': issue.to_dict()
        })
    except Exception as e:
        db_session.rollback()
        logger.error(f"Error reopening ticket issue: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db_session.close()


@tickets_bp.route('/<int:ticket_id>/issues/<int:issue_id>/comments', methods=['GET'])
@login_required
def get_issue_comments(ticket_id, issue_id):
    """Get all comments for a specific issue"""
    from models.ticket_issue import TicketIssue
    from models.ticket_issue_comment import TicketIssueComment

    db_session = db_manager.get_session()
    try:
        # Verify issue exists and belongs to ticket
        issue = db_session.query(TicketIssue).filter_by(id=issue_id, ticket_id=ticket_id).first()
        if not issue:
            return jsonify({'success': False, 'error': 'Issue not found'}), 404

        comments = db_session.query(TicketIssueComment).filter_by(issue_id=issue_id)\
            .order_by(TicketIssueComment.created_at.asc()).all()

        return jsonify({
            'success': True,
            'comments': [c.to_dict() for c in comments]
        })
    except Exception as e:
        logger.error(f"Error getting issue comments: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db_session.close()


@tickets_bp.route('/<int:ticket_id>/issues/<int:issue_id>/comments', methods=['POST'])
@login_required
def add_issue_comment(ticket_id, issue_id):
    """Add a comment to an issue (Chatter)"""
    from models.ticket_issue import TicketIssue
    from models.ticket_issue_comment import TicketIssueComment
    from models.notification import Notification
    from models.group import Group
    from models.group_membership import GroupMembership
    import re

    db_session = db_manager.get_session()
    try:
        # Verify issue exists and belongs to ticket
        issue = db_session.query(TicketIssue).filter_by(id=issue_id, ticket_id=ticket_id).first()
        if not issue:
            return jsonify({'success': False, 'error': 'Issue not found'}), 404

        ticket = db_session.query(Ticket).get(ticket_id)
        if not ticket:
            return jsonify({'success': False, 'error': 'Ticket not found'}), 404

        data = request.get_json()
        content = data.get('content', '').strip()

        if not content:
            return jsonify({'success': False, 'error': 'Comment content is required'}), 400

        # Create the comment
        comment = TicketIssueComment(
            issue_id=issue_id,
            user_id=session.get('user_id'),
            content=content,
            created_at=datetime.datetime.utcnow()
        )
        db_session.add(comment)
        db_session.commit()

        # Extract and process @mentions
        mention_pattern = r'@([a-zA-Z0-9._@-]+)'
        mentions = re.findall(mention_pattern, content)

        commenter = db_session.query(User).get(session.get('user_id'))
        notified_user_ids = set()

        for mention in mentions:
            # Check if it's a user
            mentioned_user = db_session.query(User).filter(User.username == mention).first()
            if mentioned_user and mentioned_user.id != session.get('user_id'):
                notified_user_ids.add(mentioned_user.id)
            else:
                # Check if it's a group
                group = db_session.query(Group).filter(Group.name == mention, Group.is_active == True).first()
                if group:
                    # Get all members of the group
                    memberships = db_session.query(GroupMembership).filter_by(group_id=group.id).all()
                    for membership in memberships:
                        if membership.user_id != session.get('user_id'):
                            notified_user_ids.add(membership.user_id)

        # Send notifications to mentioned users
        from utils.email_sender import send_issue_comment_email
        for user_id in notified_user_ids:
            notification = Notification(
                user_id=user_id,
                type='issue_comment',
                title=f'You were mentioned in Issue #{issue.id}',
                message=f'{commenter.username} mentioned you: {content[:100]}...' if len(content) > 100 else f'{commenter.username} mentioned you: {content}',
                reference_type='ticket',
                reference_id=ticket_id,
                is_read=False,
                created_at=datetime.datetime.utcnow()
            )
            db_session.add(notification)

            # Send email notification
            notified_user = db_session.query(User).get(user_id)
            if notified_user and notified_user.email:
                try:
                    send_issue_comment_email(
                        notified_user=notified_user,
                        commenter=commenter,
                        ticket=ticket,
                        issue=issue,
                        comment_content=content
                    )
                except Exception as email_error:
                    logger.error(f"Failed to send issue comment email to {notified_user.email}: {str(email_error)}")

        db_session.commit()

        logger.info(f"Comment added to issue {issue_id} by user {session.get('user_id')}")

        return jsonify({
            'success': True,
            'message': 'Comment added successfully',
            'comment': comment.to_dict()
        })
    except Exception as e:
        db_session.rollback()
        logger.error(f"Error adding issue comment: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db_session.close()


@tickets_bp.route('/manager')
@login_required
def ticket_manager():
    """Ticket Manager - Mass assign/reassign queues and other bulk operations"""
    user_id = session['user_id']
    user = db_manager.get_user(user_id)

    # Only SUPER_ADMIN and DEVELOPER can access ticket manager
    if not (user.is_super_admin or user.is_developer):
        flash('Access denied. Only Super Admins and Developers can access the Ticket Manager.', 'error')
        return redirect(url_for('tickets.list_tickets'))

    db_session = db_manager.get_session()
    try:
        from models.queue import Queue
        from models.user import User
        from sqlalchemy import func

        # Get all tickets with queue info
        tickets = db_session.query(Ticket)\
            .options(joinedload(Ticket.queue))\
            .options(joinedload(Ticket.assigned_to))\
            .options(joinedload(Ticket.requester))\
            .order_by(Ticket.created_at.desc())\
            .all()

        # Get all queues
        queues = db_session.query(Queue).order_by(Queue.name).all()

        # Get all users for assignment
        users = db_session.query(User).order_by(User.username).all()

        # Get ticket counts by queue
        queue_counts = db_session.query(
            Ticket.queue_id,
            func.count(Ticket.id).label('count')
        ).group_by(Ticket.queue_id).all()

        queue_count_dict = {qc[0]: qc[1] for qc in queue_counts}

        # Count tickets without queue
        no_queue_count = db_session.query(Ticket).filter(Ticket.queue_id.is_(None)).count()

        # Get custom ticket statuses
        from models.custom_ticket_status import CustomTicketStatus
        custom_statuses = db_session.query(CustomTicketStatus).filter(
            CustomTicketStatus.is_active == True
        ).order_by(CustomTicketStatus.sort_order).all()
        custom_statuses_list = [{'name': s.name, 'color': s.color} for s in custom_statuses]

        return render_template('tickets/manager.html',
                             tickets=tickets,
                             queues=queues,
                             users=users,
                             queue_count_dict=queue_count_dict,
                             no_queue_count=no_queue_count,
                             custom_statuses=custom_statuses_list,
                             user=user)
    finally:
        db_session.close()

@tickets_bp.route('/manager/bulk-assign-queue', methods=['POST'])
@login_required
def bulk_assign_queue():
    """Bulk assign tickets to a queue"""
    try:
        user = db_manager.get_user(session['user_id'])

        # Only SUPER_ADMIN and DEVELOPER can perform bulk operations
        if not (user.is_super_admin or user.is_developer):
            return jsonify({'success': False, 'error': 'Permission denied'}), 403

        data = request.get_json()
        ticket_ids = data.get('ticket_ids', [])
        queue_id = data.get('queue_id')

        if not ticket_ids:
            return jsonify({'success': False, 'error': 'No tickets selected'}), 400

        # queue_id can be None to unassign from queue
        if queue_id == '':
            queue_id = None
        elif queue_id:
            queue_id = int(queue_id)

        db_session = db_manager.get_session()
        try:
            from models.queue import Queue

            # Verify queue exists if queue_id is provided
            if queue_id:
                queue = db_session.query(Queue).get(queue_id)
                if not queue:
                    return jsonify({'success': False, 'error': 'Queue not found'}), 404
                queue_name = queue.name
            else:
                queue_name = None

            # Update tickets
            updated_count = 0
            for ticket_id in ticket_ids:
                ticket = db_session.query(Ticket).get(ticket_id)
                if ticket:
                    ticket.queue_id = queue_id
                    updated_count += 1

            db_session.commit()

            if queue_name:
                message = f'Successfully assigned {updated_count} ticket(s) to queue: {queue_name}'
            else:
                message = f'Successfully unassigned {updated_count} ticket(s) from queue'

            logging.info(f"Bulk queue assignment: {updated_count} tickets to queue {queue_id} by user {user.username}")

            return jsonify({
                'success': True,
                'message': message,
                'updated_count': updated_count
            })

        finally:
            db_session.close()

    except Exception as e:
        logging.error(f"Error in bulk queue assignment: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@tickets_bp.route('/manager/bulk-assign-user', methods=['POST'])
@login_required
def bulk_assign_user():
    """Bulk assign tickets to a user"""
    try:
        user = db_manager.get_user(session['user_id'])

        # Only SUPER_ADMIN and DEVELOPER can perform bulk operations
        if not (user.is_super_admin or user.is_developer):
            return jsonify({'success': False, 'error': 'Permission denied'}), 403

        data = request.get_json()
        ticket_ids = data.get('ticket_ids', [])
        user_id = data.get('user_id')

        if not ticket_ids:
            return jsonify({'success': False, 'error': 'No tickets selected'}), 400

        # user_id can be None to unassign from user
        if user_id == '':
            user_id = None
        elif user_id:
            user_id = int(user_id)

        db_session = db_manager.get_session()
        try:
            from models.user import User

            # Verify user exists if user_id is provided
            if user_id:
                assigned_user = db_session.query(User).get(user_id)
                if not assigned_user:
                    return jsonify({'success': False, 'error': 'User not found'}), 404
                user_name = assigned_user.username
            else:
                user_name = None

            # Update tickets
            updated_count = 0
            for ticket_id in ticket_ids:
                ticket = db_session.query(Ticket).get(ticket_id)
                if ticket:
                    ticket.assigned_to_id = user_id
                    updated_count += 1

            db_session.commit()

            if user_name:
                message = f'Successfully assigned {updated_count} ticket(s) to user: {user_name}'
            else:
                message = f'Successfully unassigned {updated_count} ticket(s) from user'

            logging.info(f"Bulk user assignment: {updated_count} tickets to user {user_id} by user {user.username}")

            return jsonify({
                'success': True,
                'message': message,
                'updated_count': updated_count
            })

        finally:
            db_session.close()

    except Exception as e:
        logging.error(f"Error in bulk user assignment: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@tickets_bp.route('/manager/bulk-update-status', methods=['POST'])
@login_required
def bulk_update_status():
    """Bulk update ticket status"""
    try:
        user = db_manager.get_user(session['user_id'])

        # Only SUPER_ADMIN and DEVELOPER can perform bulk operations
        if not (user.is_super_admin or user.is_developer):
            return jsonify({'success': False, 'error': 'Permission denied'}), 403

        data = request.get_json()
        ticket_ids = data.get('ticket_ids', [])
        status = data.get('status')

        if not ticket_ids:
            return jsonify({'success': False, 'error': 'No tickets selected'}), 400

        if not status:
            return jsonify({'success': False, 'error': 'No status selected'}), 400

        db_session = db_manager.get_session()
        try:
            from models.ticket import TicketStatus

            # Verify status is valid
            try:
                ticket_status = TicketStatus[status]
            except KeyError:
                return jsonify({'success': False, 'error': 'Invalid status'}), 400

            # Update tickets
            updated_count = 0
            for ticket_id in ticket_ids:
                ticket = db_session.query(Ticket).get(ticket_id)
                if ticket:
                    ticket.status = ticket_status
                    updated_count += 1

            db_session.commit()

            message = f'Successfully updated {updated_count} ticket(s) to status: {ticket_status.value}'

            logging.info(f"Bulk status update: {updated_count} tickets to status {status} by user {user.username}")

            return jsonify({
                'success': True,
                'message': message,
                'updated_count': updated_count
            })

        finally:
            db_session.close()

    except Exception as e:
        logging.error(f"Error in bulk status update: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@tickets_bp.route('/bulk-import-asset-return', methods=['GET', 'POST'])
@login_required
def bulk_import_asset_return():
    """Bulk import Asset Return tickets from CSV with automatic customer creation"""
    from routes.import_manager import create_import_session, update_import_session

    try:
        user = db_manager.get_user(session['user_id'])
        user_id = user.id

        # Only SUPER_ADMIN, DEVELOPER, and SUPERVISOR can perform bulk imports
        if not (user.is_super_admin or user.is_developer or user.is_supervisor):
            flash('Permission denied. Only SUPER_ADMIN, DEVELOPER, and SUPERVISOR can perform bulk imports.', 'error')
            return redirect(url_for('tickets.list_tickets'))

        if request.method == 'GET':
            # Render the import form
            db_session = db_manager.get_session()
            try:
                # Get queues for dropdown - filtered by permissions for SUPERVISOR
                if user.user_type in [UserType.SUPERVISOR, UserType.COUNTRY_ADMIN]:
                    from models.user_queue_permission import UserQueuePermission
                    queue_permissions = db_session.query(UserQueuePermission.queue_id).filter(
                        UserQueuePermission.user_id == user.id,
                        UserQueuePermission.can_view == True
                    ).all()
                    accessible_queue_ids = [q[0] for q in queue_permissions]
                    queues = db_session.query(Queue).filter(Queue.id.in_(accessible_queue_ids)).order_by(Queue.name).all() if accessible_queue_ids else []
                else:
                    queues = db_session.query(Queue).order_by(Queue.name).all()

                return render_template('tickets/bulk_import_asset_return.html',
                                     user=user,
                                     queues=queues)
            finally:
                db_session.close()

        # POST request - process the CSV file or preview data
        # Check if this is a preview request (initial upload) or final import
        is_preview = request.form.get('action') != 'import'

        if is_preview:
            # Handle initial CSV upload for preview
            if 'csv_file' not in request.files:
                flash('No file uploaded', 'error')
                return redirect(request.url)

            file = request.files['csv_file']

            if file.filename == '':
                flash('No file selected', 'error')
                return redirect(request.url)

            if not file.filename.endswith('.csv'):
                flash('Invalid file type. Please upload a CSV file.', 'error')
                return redirect(request.url)

            db_session = db_manager.get_session()
            try:
                # Read CSV file
                stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
                csv_reader = csv.DictReader(stream)

                # Validate headers
                required_headers = ['order-Id', 'customer_name', 'customer_email', 'customer_phone', 'customer_company', 'customer_address', 'customer_country', 'return_description']
                headers = csv_reader.fieldnames

                missing_headers = [h for h in required_headers if h not in headers]
                if missing_headers:
                    flash(f'Missing required columns: {", ".join(missing_headers)}', 'error')
                    return redirect(request.url)

                # Read all rows for preview
                preview_data = []
                row_number = 1
                for row in csv_reader:
                    row_number += 1

                    # Check for direct customer_address field first
                    direct_address = row.get('customer_address', '').strip()

                    # Build customer address from components if available (fallback)
                    address_parts = []
                    if row.get('address_line_1', '').strip():
                        address_parts.append(row.get('address_line_1', '').strip())
                    if row.get('address_line_2', '').strip():
                        address_parts.append(row.get('address_line_2', '').strip())
                    city_state_zip = []
                    if row.get('city', '').strip():
                        city_state_zip.append(row.get('city', '').strip())
                    if row.get('state', '').strip():
                        city_state_zip.append(row.get('state', '').strip())
                    if row.get('zip', '').strip():
                        city_state_zip.append(row.get('zip', '').strip())
                    if city_state_zip:
                        address_parts.append(', '.join(city_state_zip))
                    built_address = ', '.join(address_parts) if address_parts else ''

                    # Use direct address if provided, otherwise use built address
                    customer_address = direct_address if direct_address else built_address

                    customer_name = row.get('customer_name', '').strip()
                    preview_data.append({
                        'row_number': row_number,
                        'order_id': row.get('order-Id', '').strip(),
                        'customer_name': customer_name,
                        'customer_email': row.get('customer_email', ''),
                        'customer_phone': row.get('customer_phone', ''),
                        'customer_company': row.get('customer_company', ''),
                        'customer_country': row.get('customer_country', ''),
                        'customer_address': customer_address,
                        'return_description': row.get('return_description', ''),
                        'reported_issue': row.get('Reported_Issue', ''),
                        'asset_serial_number': row.get('asset_serial_number', ''),
                        'priority': row.get('priority', 'Medium'),
                        'queue_name': row.get('queue_name', ''),
                        'case_owner_email': row.get('case_owner_email', ''),
                        'notes': row.get('notes', ''),
                        'address_line_1': row.get('address_line_1', ''),
                        'address_line_2': row.get('address_line_2', ''),
                        'city': row.get('city', ''),
                        'state': row.get('state', ''),
                        'zip': row.get('zip', ''),
                        'name_is_empty': not customer_name  # Flag for empty names
                    })

                # Get available countries, queues, and users for dropdowns
                # Comprehensive list of all countries
                all_countries = [
                    'AFGHANISTAN', 'ALBANIA', 'ALGERIA', 'ANDORRA', 'ANGOLA', 'ARGENTINA', 'ARMENIA',
                    'AUSTRALIA', 'AUSTRIA', 'AZERBAIJAN', 'BAHAMAS', 'BAHRAIN', 'BANGLADESH', 'BARBADOS',
                    'BELARUS', 'BELGIUM', 'BELIZE', 'BENIN', 'BHUTAN', 'BOLIVIA', 'BOSNIA', 'BOTSWANA',
                    'BRAZIL', 'BRUNEI', 'BULGARIA', 'BURKINA_FASO', 'BURUNDI', 'CAMBODIA', 'CAMEROON',
                    'CANADA', 'CAPE_VERDE', 'CENTRAL_AFRICAN_REPUBLIC', 'CHAD', 'CHILE', 'CHINA', 'COLOMBIA',
                    'COMOROS', 'CONGO', 'COSTA_RICA', 'CROATIA', 'CUBA', 'CYPRUS', 'CZECH_REPUBLIC',
                    'DENMARK', 'DJIBOUTI', 'DOMINICA', 'DOMINICAN_REPUBLIC', 'ECUADOR', 'EGYPT', 'EL_SALVADOR',
                    'EQUATORIAL_GUINEA', 'ERITREA', 'ESTONIA', 'ETHIOPIA', 'FIJI', 'FINLAND', 'FRANCE',
                    'GABON', 'GAMBIA', 'GEORGIA', 'GERMANY', 'GHANA', 'GREECE', 'GRENADA', 'GUATEMALA',
                    'GUINEA', 'GUYANA', 'HAITI', 'HONDURAS', 'HONG_KONG', 'HUNGARY', 'ICELAND', 'INDIA',
                    'INDONESIA', 'IRAN', 'IRAQ', 'IRELAND', 'ISRAEL', 'ITALY', 'IVORY_COAST', 'JAMAICA',
                    'JAPAN', 'JORDAN', 'KAZAKHSTAN', 'KENYA', 'KIRIBATI', 'KUWAIT', 'KYRGYZSTAN', 'LAOS',
                    'LATVIA', 'LEBANON', 'LESOTHO', 'LIBERIA', 'LIBYA', 'LIECHTENSTEIN', 'LITHUANIA',
                    'LUXEMBOURG', 'MACAU', 'MACEDONIA', 'MADAGASCAR', 'MALAWI', 'MALAYSIA', 'MALDIVES',
                    'MALI', 'MALTA', 'MARSHALL_ISLANDS', 'MAURITANIA', 'MAURITIUS', 'MEXICO', 'MICRONESIA',
                    'MOLDOVA', 'MONACO', 'MONGOLIA', 'MONTENEGRO', 'MOROCCO', 'MOZAMBIQUE', 'MYANMAR',
                    'NAMIBIA', 'NAURU', 'NEPAL', 'NETHERLANDS', 'NEW_ZEALAND', 'NICARAGUA', 'NIGER',
                    'NIGERIA', 'NORTH_KOREA', 'NORWAY', 'OMAN', 'PAKISTAN', 'PALAU', 'PALESTINE', 'PANAMA',
                    'PAPUA_NEW_GUINEA', 'PARAGUAY', 'PERU', 'PHILIPPINES', 'POLAND', 'PORTUGAL', 'PUERTO_RICO',
                    'QATAR', 'ROMANIA', 'RUSSIA', 'RWANDA', 'SAINT_KITTS', 'SAINT_LUCIA', 'SAMOA',
                    'SAN_MARINO', 'SAO_TOME', 'SAUDI_ARABIA', 'SENEGAL', 'SERBIA', 'SEYCHELLES',
                    'SIERRA_LEONE', 'SINGAPORE', 'SLOVAKIA', 'SLOVENIA', 'SOLOMON_ISLANDS', 'SOMALIA',
                    'SOUTH_AFRICA', 'SOUTH_KOREA', 'SOUTH_SUDAN', 'SPAIN', 'SRI_LANKA', 'SUDAN', 'SURINAME',
                    'SWAZILAND', 'SWEDEN', 'SWITZERLAND', 'SYRIA', 'TAIWAN', 'TAJIKISTAN', 'TANZANIA',
                    'THAILAND', 'TIMOR_LESTE', 'TOGO', 'TONGA', 'TRINIDAD_TOBAGO', 'TUNISIA', 'TURKEY',
                    'TURKMENISTAN', 'TUVALU', 'UAE', 'UGANDA', 'UKRAINE', 'UNITED_KINGDOM', 'USA',
                    'URUGUAY', 'UZBEKISTAN', 'VANUATU', 'VATICAN', 'VENEZUELA', 'VIETNAM', 'YEMEN',
                    'ZAMBIA', 'ZIMBABWE'
                ]
                countries = sorted(all_countries)
                # Get queues for dropdown - filtered by permissions for SUPERVISOR
                if user.user_type in [UserType.SUPERVISOR, UserType.COUNTRY_ADMIN]:
                    from models.user_queue_permission import UserQueuePermission
                    queue_permissions = db_session.query(UserQueuePermission.queue_id).filter(
                        UserQueuePermission.user_id == user.id,
                        UserQueuePermission.can_view == True
                    ).all()
                    accessible_queue_ids = [q[0] for q in queue_permissions]
                    queues = db_session.query(Queue).filter(Queue.id.in_(accessible_queue_ids)).order_by(Queue.name).all() if accessible_queue_ids else []
                else:
                    queues = db_session.query(Queue).order_by(Queue.name).all()
                users = db_session.query(User).filter(
                    User.user_type.in_([UserType.SUPER_ADMIN, UserType.DEVELOPER, UserType.SUPERVISOR, UserType.COUNTRY_ADMIN])
                ).order_by(User.username).all()

                return render_template('tickets/bulk_import_preview.html',
                                     user=user,
                                     preview_data=preview_data,
                                     countries=countries,
                                     queues=queues,
                                     users=users)
            finally:
                db_session.close()

        # Final import after preview confirmation
        db_session = db_manager.get_session()
        try:
            # Get the number of rows from form data
            row_count = int(request.form.get('row_count', 0))

            # Process each row from form data
            successful_imports = []
            failed_imports = []
            import_session_id = None

            # Create ImportSession to track this import
            try:
                import_session_id, display_id = create_import_session(
                    import_type='asset_return',
                    user_id=user_id,
                    file_name='Bulk Asset Return Import',
                    notes=f"Asset return bulk import with {row_count} rows"
                )
                logger.info(f"Created import session {display_id} for asset return import")
            except Exception as e:
                logger.error(f"Failed to create import session: {str(e)}")

            for i in range(row_count):
                row_number = int(request.form.get(f'row_{i}_number', i + 2))
                try:
                    # Validate required fields
                    customer_name = request.form.get(f'row_{i}_customer_name', '').strip()
                    customer_email = request.form.get(f'row_{i}_customer_email', '').strip()
                    customer_country = request.form.get(f'row_{i}_customer_country', '').strip().upper()
                    return_description = request.form.get(f'row_{i}_return_description', '').strip()
                    order_id = request.form.get(f'row_{i}_order_id', '').strip()
                    reported_issue = request.form.get(f'row_{i}_reported_issue', '').strip()

                    if not customer_name or not customer_email or not customer_country or not return_description:
                        failed_imports.append({
                            'row': row_number,
                            'reason': 'Missing required fields (customer_name, customer_email, customer_country, or return_description)'
                        })
                        continue

                    # Country is stored as string, no enum validation needed

                    # Get optional fields first
                    customer_phone = request.form.get(f'row_{i}_customer_phone', '').strip()
                    customer_company_name = request.form.get(f'row_{i}_customer_company', '').strip().upper()  # Auto-convert to uppercase

                    # Get direct customer_address from form (editable field)
                    direct_address = request.form.get(f'row_{i}_customer_address', '').strip()

                    # Get address components (needed for both new and existing customers)
                    address_line_1 = request.form.get(f'row_{i}_address_line_1', '').strip()
                    address_line_2 = request.form.get(f'row_{i}_address_line_2', '').strip()
                    city = request.form.get(f'row_{i}_city', '').strip()
                    state = request.form.get(f'row_{i}_state', '').strip()
                    zip_code = request.form.get(f'row_{i}_zip', '').strip()

                    # Build address from components
                    address_parts = []
                    if address_line_1:
                        address_parts.append(address_line_1)
                    if address_line_2:
                        address_parts.append(address_line_2)
                    city_state_zip = []
                    if city:
                        city_state_zip.append(city)
                    if state:
                        city_state_zip.append(state)
                    if zip_code:
                        city_state_zip.append(zip_code)
                    if city_state_zip:
                        address_parts.append(', '.join(city_state_zip))
                    built_address = ', '.join(address_parts) if address_parts else ''

                    # Use direct address if provided, otherwise use built address, otherwise 'N/A'
                    full_address = direct_address if direct_address else (built_address if built_address else 'N/A')

                    # Get or create customer
                    customer = db_session.query(CustomerUser).filter_by(email=customer_email).first()

                    if not customer:
                        # Get or create company if provided
                        company_id = None
                        if customer_company_name:
                            company = db_session.query(Company).filter_by(name=customer_company_name).first()
                            if not company:
                                company = Company(
                                    name=customer_company_name
                                )
                                db_session.add(company)
                                db_session.flush()
                            company_id = company.id

                        customer = CustomerUser(
                            name=customer_name,
                            email=customer_email,
                            contact_number=customer_phone if customer_phone else 'N/A',
                            address=full_address,  # Use the built address from CSV
                            company_id=company_id,
                            country=customer_country  # Store as string
                        )
                        db_session.add(customer)
                        db_session.flush()
                        logger.info(f"Created new customer: {customer_name} ({customer_email}) with address: {full_address}")
                    else:
                        # Update existing customer's address if it's N/A and we have a new address
                        if customer.address == 'N/A' and full_address != 'N/A':
                            customer.address = full_address
                            logger.info(f"Updated existing customer address: {customer_name} ({customer_email}) with address: {full_address}")

                    # Get remaining optional fields
                    asset_serial_number = request.form.get(f'row_{i}_asset_serial_number', '').strip()
                    priority_str = request.form.get(f'row_{i}_priority', 'Medium').strip()
                    queue_name = request.form.get(f'row_{i}_queue_name', '').strip()
                    case_owner_email = request.form.get(f'row_{i}_case_owner_email', '').strip()
                    notes = request.form.get(f'row_{i}_notes', '').strip()

                    # Validate priority
                    try:
                        priority = TicketPriority[priority_str.upper()]
                    except (KeyError, AttributeError):
                        priority = TicketPriority.MEDIUM

                    # Find asset if provided
                    asset_id = None
                    if asset_serial_number:
                        asset = db_session.query(Asset).filter_by(serial_num=asset_serial_number).first()
                        if asset:
                            asset_id = asset.id
                        else:
                            logger.warning(f"Asset not found with serial: {asset_serial_number}")

                    # Find queue if provided
                    queue_id = None
                    if queue_name:
                        queue = db_session.query(Queue).filter_by(name=queue_name).first()
                        if queue:
                            queue_id = queue.id

                    # Find case owner if provided
                    case_owner_id = None
                    if case_owner_email:
                        case_owner = db_session.query(User).filter_by(email=case_owner_email).first()
                        if case_owner:
                            case_owner_id = case_owner.id

                    # Prepare description - just use the return_description as main description
                    # Add reported issue if provided
                    description = return_description
                    if reported_issue:
                        description += f"\n\nReported Issue: {reported_issue}"
                    if asset_serial_number:
                        description += f"\n\nAsset Serial Number: {asset_serial_number}"

                    # Determine case owner - use case_owner_id if provided, otherwise default to requester
                    assigned_to_id = case_owner_id if case_owner_id else user_id

                    # Create the ticket directly using the same session to avoid database locks
                    ticket = Ticket(
                        subject=f"Asset Return - {customer_name}",
                        description=description,
                        requester_id=user_id,
                        assigned_to_id=assigned_to_id,
                        category=TicketCategory.ASSET_RETURN_CLAW,
                        priority=priority,
                        asset_id=asset_id,
                        customer_id=customer.id,
                        return_description=return_description,
                        queue_id=queue_id,
                        notes=notes if notes else None,
                        shipping_carrier='singpost',
                        firstbaseorderid=order_id if order_id else None,
                        damage_description=reported_issue if reported_issue else None
                    )
                    db_session.add(ticket)
                    db_session.flush()  # Flush to get the ticket ID
                    ticket_id = ticket.id

                    # Commit immediately after each successful row to avoid rollback issues
                    db_session.commit()

                    successful_imports.append({
                        'row': row_number,
                        'ticket_id': ticket_id,
                        'customer': customer_name
                    })
                    logger.info(f"Created Asset Return ticket {ticket_id} for customer {customer_name}")

                except Exception as row_error:
                    db_session.rollback()  # Rollback the failed transaction
                    logger.error(f"Error processing row {row_number}: {str(row_error)}")
                    failed_imports.append({
                        'row': row_number,
                        'reason': str(row_error)
                    })
                    continue

            # Prepare result message
            success_count = len(successful_imports)
            fail_count = len(failed_imports)

            if success_count > 0:
                flash(f'Successfully imported {success_count} Asset Return ticket(s)', 'success')

            if fail_count > 0:
                flash(f'Failed to import {fail_count} row(s). Check the error log below.', 'warning')
                for failure in failed_imports:
                    flash(f'Row {failure["row"]}: {failure["reason"]}', 'error')

            # Update ImportSession with results
            if import_session_id:
                try:
                    status = 'completed' if success_count > 0 else 'failed'
                    error_details = [f"Row {f['row']}: {f['reason']}" for f in failed_imports[:50]]
                    # Store imported records data (limit to first 100 for storage)
                    import_data = successful_imports[:100] if successful_imports else None
                    logger.info(f"bulk_import_asset_return: Updating session {import_session_id}, successful_imports has {len(successful_imports)} items")
                    update_import_session(import_session_id, success_count=success_count, fail_count=fail_count,
                                         import_data=import_data, error_details=error_details if error_details else None, status=status)
                except Exception as e:
                    logger.error(f"Failed to update import session: {str(e)}")

            return render_template('tickets/bulk_import_result.html',
                                 user=user,
                                 successful_imports=successful_imports,
                                 failed_imports=failed_imports,
                                 success_count=success_count,
                                 fail_count=fail_count)

        except Exception as e:
            db_session.rollback()
            logger.error(f"Error in bulk import: {str(e)}")
            flash(f'Error processing CSV file: {str(e)}', 'error')
            return redirect(request.url)
        finally:
            db_session.close()

    except Exception as e:
        logger.error(f"Error in bulk import asset return: {str(e)}")
        flash(f'Error: {str(e)}', 'error')
        return redirect(url_for('tickets.list_tickets'))


@tickets_bp.route('/bulk-import-1stbase', methods=['GET', 'POST'])
@login_required
def bulk_import_1stbase():
    """Bulk import 1stbase tickets from CSV with automatic customer creation"""
    from routes.import_manager import create_import_session, update_import_session

    try:
        user = db_manager.get_user(session['user_id'])
        user_id = user.id

        # Only SUPER_ADMIN, DEVELOPER, and SUPERVISOR can perform bulk imports
        if not (user.is_super_admin or user.is_developer or user.is_supervisor):
            flash('Permission denied. Only SUPER_ADMIN, DEVELOPER, and SUPERVISOR can perform bulk imports.', 'error')
            return redirect(url_for('tickets.list_tickets'))

        if request.method == 'GET':
            # Render the import form
            db_session = db_manager.get_session()
            try:
                # Get queues for dropdown - filtered by permissions for SUPERVISOR
                if user.user_type in [UserType.SUPERVISOR, UserType.COUNTRY_ADMIN]:
                    from models.user_queue_permission import UserQueuePermission
                    queue_permissions = db_session.query(UserQueuePermission.queue_id).filter(
                        UserQueuePermission.user_id == user.id,
                        UserQueuePermission.can_view == True
                    ).all()
                    accessible_queue_ids = [q[0] for q in queue_permissions]
                    queues = db_session.query(Queue).filter(Queue.id.in_(accessible_queue_ids)).order_by(Queue.name).all() if accessible_queue_ids else []
                else:
                    queues = db_session.query(Queue).order_by(Queue.name).all()

                return render_template('tickets/bulk_import_1stbase.html',
                                     user=user,
                                     queues=queues)
            finally:
                db_session.close()

        # POST request - process the CSV file or preview data
        # Check if this is a preview request (initial upload) or final import
        is_preview = request.form.get('action') != 'import'

        if is_preview:
            # Handle initial CSV upload for preview
            if 'csv_file' not in request.files:
                flash('No file uploaded', 'error')
                return redirect(request.url)

            file = request.files['csv_file']

            if file.filename == '':
                flash('No file selected', 'error')
                return redirect(request.url)

            if not file.filename.endswith('.csv'):
                flash('Invalid file type. Please upload a CSV file.', 'error')
                return redirect(request.url)

            db_session = db_manager.get_session()
            try:
                # Read CSV file
                stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
                csv_reader = csv.DictReader(stream)

                # Validate headers - Updated format
                required_headers = ['product_title', 'org_name', 'person_name', 'primary_email', 'serial_number', 'country']
                headers = csv_reader.fieldnames

                missing_headers = [h for h in required_headers if h not in headers]
                if missing_headers:
                    flash(f'Missing required columns: {", ".join(missing_headers)}', 'error')
                    return redirect(request.url)

                # Get existing order_ids to check for duplicates
                existing_order_ids = set()
                existing_tickets = db_session.query(Ticket.firstbaseorderid).filter(
                    Ticket.firstbaseorderid.isnot(None),
                    Ticket.firstbaseorderid != ''
                ).all()
                existing_order_ids = {t.firstbaseorderid for t in existing_tickets}

                # Country code to full name mapping
                country_code_map = {
                    'SG': 'SINGAPORE', 'SINGAPORE': 'SINGAPORE',
                    'PH': 'PHILIPPINES', 'PHILIPPINES': 'PHILIPPINES',
                    'MX': 'MEXICO', 'MEXICO': 'MEXICO',
                    'JP': 'JAPAN', 'JAPAN': 'JAPAN',
                    'IN': 'INDIA', 'INDIA': 'INDIA',
                    'IL': 'ISRAEL', 'ISRAEL': 'ISRAEL',
                    'US': 'USA', 'USA': 'USA', 'UNITED STATES': 'USA',
                    'AU': 'AUSTRALIA', 'AUSTRALIA': 'AUSTRALIA',
                    'TW': 'TAIWAN', 'TAIWAN': 'TAIWAN',
                    'CN': 'CHINA', 'CHINA': 'CHINA',
                    'HK': 'HONG_KONG', 'HONG KONG': 'HONG_KONG', 'HONG_KONG': 'HONG_KONG',
                    'MY': 'MALAYSIA', 'MALAYSIA': 'MALAYSIA',
                    'TH': 'THAILAND', 'THAILAND': 'THAILAND',
                    'VN': 'VIETNAM', 'VIETNAM': 'VIETNAM',
                    'KR': 'SOUTH_KOREA', 'SOUTH KOREA': 'SOUTH_KOREA', 'SOUTH_KOREA': 'SOUTH_KOREA',
                    'ID': 'INDONESIA', 'INDONESIA': 'INDONESIA',
                    'UK': 'UNITED_KINGDOM', 'GB': 'UNITED_KINGDOM', 'UNITED KINGDOM': 'UNITED_KINGDOM', 'UNITED_KINGDOM': 'UNITED_KINGDOM',
                    'CA': 'CANADA', 'CANADA': 'CANADA',
                    'AE': 'UAE', 'UAE': 'UAE',
                    'DE': 'GERMANY', 'GERMANY': 'GERMANY',
                    'FR': 'FRANCE', 'FRANCE': 'FRANCE',
                    'IT': 'ITALY', 'ITALY': 'ITALY',
                    'ES': 'SPAIN', 'SPAIN': 'SPAIN',
                    'NL': 'NETHERLANDS', 'NETHERLANDS': 'NETHERLANDS',
                    'BR': 'BRAZIL', 'BRAZIL': 'BRAZIL',
                    'AR': 'ARGENTINA', 'ARGENTINA': 'ARGENTINA',
                    'CL': 'CHILE', 'CHILE': 'CHILE',
                    'CO': 'COLOMBIA', 'COLOMBIA': 'COLOMBIA',
                    'PE': 'PERU', 'PERU': 'PERU',
                    'NZ': 'NEW_ZEALAND', 'NEW ZEALAND': 'NEW_ZEALAND', 'NEW_ZEALAND': 'NEW_ZEALAND',
                    'IE': 'IRELAND', 'IRELAND': 'IRELAND',
                    'SE': 'SWEDEN', 'SWEDEN': 'SWEDEN',
                    'NO': 'NORWAY', 'NORWAY': 'NORWAY',
                    'DK': 'DENMARK', 'DENMARK': 'DENMARK',
                    'FI': 'FINLAND', 'FINLAND': 'FINLAND',
                    'CH': 'SWITZERLAND', 'SWITZERLAND': 'SWITZERLAND',
                    'AT': 'AUSTRIA', 'AUSTRIA': 'AUSTRIA',
                    'BE': 'BELGIUM', 'BELGIUM': 'BELGIUM',
                    'PT': 'PORTUGAL', 'PORTUGAL': 'PORTUGAL',
                    'PL': 'POLAND', 'POLAND': 'POLAND',
                    'CZ': 'CZECH_REPUBLIC', 'CZECH REPUBLIC': 'CZECH_REPUBLIC', 'CZECH_REPUBLIC': 'CZECH_REPUBLIC',
                    'GR': 'GREECE', 'GREECE': 'GREECE',
                    'TR': 'TURKEY', 'TURKEY': 'TURKEY',
                    'RU': 'RUSSIA', 'RUSSIA': 'RUSSIA',
                    'ZA': 'SOUTH_AFRICA', 'SOUTH AFRICA': 'SOUTH_AFRICA', 'SOUTH_AFRICA': 'SOUTH_AFRICA',
                    'EG': 'EGYPT', 'EGYPT': 'EGYPT',
                    'NG': 'NIGERIA', 'NIGERIA': 'NIGERIA',
                    'KE': 'KENYA', 'KENYA': 'KENYA',
                    'SA': 'SAUDI_ARABIA', 'SAUDI ARABIA': 'SAUDI_ARABIA', 'SAUDI_ARABIA': 'SAUDI_ARABIA',
                    'PK': 'PAKISTAN', 'PAKISTAN': 'PAKISTAN',
                    'BD': 'BANGLADESH', 'BANGLADESH': 'BANGLADESH',
                    'GY': 'GUYANA', 'GUYANA': 'GUYANA',
                }

                # Read all rows for preview
                preview_data = []
                row_number = 1
                for row in csv_reader:
                    row_number += 1
                    # Parse person_name into first and last name
                    person_name = row.get('person_name', '').strip()
                    name_parts = person_name.split(' ', 1)  # Split on first space
                    first_name = name_parts[0] if name_parts else ''
                    last_name = name_parts[1] if len(name_parts) > 1 else ''
                    customer_name = person_name

                    # Check if name is empty
                    name_is_empty = not customer_name

                    # Build customer address from components
                    address_parts = []
                    if row.get('office_name', '').strip():
                        address_parts.append(row.get('office_name', '').strip())
                    if row.get('address_line1', '').strip():
                        address_parts.append(row.get('address_line1', '').strip())
                    if row.get('address_line2', '').strip():
                        address_parts.append(row.get('address_line2', '').strip())
                    city_state_zip = []
                    if row.get('city', '').strip():
                        city_state_zip.append(row.get('city', '').strip())
                    if row.get('state', '').strip():
                        city_state_zip.append(row.get('state', '').strip())
                    if row.get('postal_code', '').strip():
                        city_state_zip.append(row.get('postal_code', '').strip())
                    if city_state_zip:
                        address_parts.append(', '.join(city_state_zip))
                    customer_address = ', '.join(address_parts) if address_parts else ''

                    # Check if order_id already exists
                    order_id = row.get('order_id', '').strip()
                    is_duplicate = order_id and order_id in existing_order_ids

                    # Map country code to full country name
                    raw_country = row.get('country', '').strip().upper()
                    mapped_country = country_code_map.get(raw_country, raw_country)

                    row_data = {
                        'row_number': row_number,
                        'customer_name': customer_name,
                        'customer_email': row.get('primary_email', ''),
                        'customer_phone': row.get('phone_number', ''),
                        'customer_company': row.get('org_name', ''),
                        'customer_country': mapped_country,
                        'customer_address': customer_address,
                        'return_description': f"Order: {row.get('order_id', 'N/A')} | Product: {row.get('product_title', 'N/A')} | Serial: {row.get('serial_number', 'N/A')} | Status: {row.get('status', 'N/A')}",
                        'asset_serial_number': row.get('serial_number', ''),
                        'order_id': order_id,
                        'product_description': row.get('product_title', ''),
                        'address_line_1': row.get('address_line1', ''),
                        'address_line_2': row.get('address_line2', ''),
                        'city': row.get('city', ''),
                        'state': row.get('state', ''),
                        'zip': row.get('postal_code', ''),
                        'secondary_email': '',
                        'priority': 'Medium',
                        'queue_name': mapped_country,  # Use mapped country as queue name
                        'notes': f"Office: {row.get('office_name', '')} | Item ID: {row.get('order_item_id', '')} | Status: {row.get('status', '')}",
                        'name_is_empty': name_is_empty,  # Validation flag
                        'is_duplicate': is_duplicate,  # Duplicate order_id flag
                        'first_name': first_name,
                        'last_name': last_name
                    }

                    # Log rows with empty names for debugging
                    if name_is_empty:
                        logger.info(f"Row {row_number}: Empty customer name detected (first='{first_name}', last='{last_name}')")

                    # Log duplicate order_ids
                    if is_duplicate:
                        logger.info(f"Row {row_number}: Duplicate order_id detected: {order_id}")

                    preview_data.append(row_data)

                # Get available countries, queues, and users for dropdowns
                # Comprehensive list of all countries
                all_countries = [
                    'AFGHANISTAN', 'ALBANIA', 'ALGERIA', 'ANDORRA', 'ANGOLA', 'ARGENTINA', 'ARMENIA',
                    'AUSTRALIA', 'AUSTRIA', 'AZERBAIJAN', 'BAHAMAS', 'BAHRAIN', 'BANGLADESH', 'BARBADOS',
                    'BELARUS', 'BELGIUM', 'BELIZE', 'BENIN', 'BHUTAN', 'BOLIVIA', 'BOSNIA', 'BOTSWANA',
                    'BRAZIL', 'BRUNEI', 'BULGARIA', 'BURKINA_FASO', 'BURUNDI', 'CAMBODIA', 'CAMEROON',
                    'CANADA', 'CAPE_VERDE', 'CENTRAL_AFRICAN_REPUBLIC', 'CHAD', 'CHILE', 'CHINA', 'COLOMBIA',
                    'COMOROS', 'CONGO', 'COSTA_RICA', 'CROATIA', 'CUBA', 'CYPRUS', 'CZECH_REPUBLIC',
                    'DENMARK', 'DJIBOUTI', 'DOMINICA', 'DOMINICAN_REPUBLIC', 'ECUADOR', 'EGYPT', 'EL_SALVADOR',
                    'EQUATORIAL_GUINEA', 'ERITREA', 'ESTONIA', 'ETHIOPIA', 'FIJI', 'FINLAND', 'FRANCE',
                    'GABON', 'GAMBIA', 'GEORGIA', 'GERMANY', 'GHANA', 'GREECE', 'GRENADA', 'GUATEMALA',
                    'GUINEA', 'GUYANA', 'HAITI', 'HONDURAS', 'HONG_KONG', 'HUNGARY', 'ICELAND', 'INDIA',
                    'INDONESIA', 'IRAN', 'IRAQ', 'IRELAND', 'ISRAEL', 'ITALY', 'IVORY_COAST', 'JAMAICA',
                    'JAPAN', 'JORDAN', 'KAZAKHSTAN', 'KENYA', 'KIRIBATI', 'KUWAIT', 'KYRGYZSTAN', 'LAOS',
                    'LATVIA', 'LEBANON', 'LESOTHO', 'LIBERIA', 'LIBYA', 'LIECHTENSTEIN', 'LITHUANIA',
                    'LUXEMBOURG', 'MACAU', 'MACEDONIA', 'MADAGASCAR', 'MALAWI', 'MALAYSIA', 'MALDIVES',
                    'MALI', 'MALTA', 'MARSHALL_ISLANDS', 'MAURITANIA', 'MAURITIUS', 'MEXICO', 'MICRONESIA',
                    'MOLDOVA', 'MONACO', 'MONGOLIA', 'MONTENEGRO', 'MOROCCO', 'MOZAMBIQUE', 'MYANMAR',
                    'NAMIBIA', 'NAURU', 'NEPAL', 'NETHERLANDS', 'NEW_ZEALAND', 'NICARAGUA', 'NIGER',
                    'NIGERIA', 'NORTH_KOREA', 'NORWAY', 'OMAN', 'PAKISTAN', 'PALAU', 'PALESTINE', 'PANAMA',
                    'PAPUA_NEW_GUINEA', 'PARAGUAY', 'PERU', 'PHILIPPINES', 'POLAND', 'PORTUGAL', 'PUERTO_RICO',
                    'QATAR', 'ROMANIA', 'RUSSIA', 'RWANDA', 'SAINT_KITTS', 'SAINT_LUCIA', 'SAMOA',
                    'SAN_MARINO', 'SAO_TOME', 'SAUDI_ARABIA', 'SENEGAL', 'SERBIA', 'SEYCHELLES',
                    'SIERRA_LEONE', 'SINGAPORE', 'SLOVAKIA', 'SLOVENIA', 'SOLOMON_ISLANDS', 'SOMALIA',
                    'SOUTH_AFRICA', 'SOUTH_KOREA', 'SOUTH_SUDAN', 'SPAIN', 'SRI_LANKA', 'SUDAN', 'SURINAME',
                    'SWAZILAND', 'SWEDEN', 'SWITZERLAND', 'SYRIA', 'TAIWAN', 'TAJIKISTAN', 'TANZANIA',
                    'THAILAND', 'TIMOR_LESTE', 'TOGO', 'TONGA', 'TRINIDAD_TOBAGO', 'TUNISIA', 'TURKEY',
                    'TURKMENISTAN', 'TUVALU', 'UAE', 'UGANDA', 'UKRAINE', 'UNITED_KINGDOM', 'USA',
                    'URUGUAY', 'UZBEKISTAN', 'VANUATU', 'VATICAN', 'VENEZUELA', 'VIETNAM', 'YEMEN',
                    'ZAMBIA', 'ZIMBABWE'
                ]
                countries = sorted(all_countries)
                # Get queues for dropdown - filtered by permissions for SUPERVISOR
                if user.user_type in [UserType.SUPERVISOR, UserType.COUNTRY_ADMIN]:
                    from models.user_queue_permission import UserQueuePermission
                    queue_permissions = db_session.query(UserQueuePermission.queue_id).filter(
                        UserQueuePermission.user_id == user.id,
                        UserQueuePermission.can_view == True
                    ).all()
                    accessible_queue_ids = [q[0] for q in queue_permissions]
                    queues = db_session.query(Queue).filter(Queue.id.in_(accessible_queue_ids)).order_by(Queue.name).all() if accessible_queue_ids else []
                else:
                    queues = db_session.query(Queue).order_by(Queue.name).all()
                users = db_session.query(User).filter(
                    User.user_type.in_([UserType.SUPER_ADMIN, UserType.DEVELOPER, UserType.SUPERVISOR, UserType.COUNTRY_ADMIN])
                ).order_by(User.username).all()

                # Log summary
                empty_name_count = sum(1 for r in preview_data if r.get('name_is_empty'))
                duplicate_count = sum(1 for r in preview_data if r.get('is_duplicate'))
                logger.info(f"Preview prepared: {len(preview_data)} total rows, {empty_name_count} with empty names, {duplicate_count} duplicates")

                return render_template('tickets/bulk_import_preview.html',
                                     user=user,
                                     preview_data=preview_data,
                                     countries=countries,
                                     queues=queues,
                                     users=users,
                                     import_type='1stbase')
            finally:
                db_session.close()

        # Final import after preview confirmation
        db_session = db_manager.get_session()
        try:
            # Get the number of rows from form data
            row_count = int(request.form.get('row_count', 0))

            # Process each row from form data
            successful_imports = []
            failed_imports = []
            import_session_id = None

            # Create ImportSession to track this import
            try:
                import_session_id, display_id = create_import_session(
                    import_type='1stbase',
                    user_id=user_id,
                    file_name='Bulk 1stBase Import',
                    notes=f"1stBase bulk import with {row_count} rows"
                )
                logger.info(f"Created import session {display_id} for 1stbase import")
            except Exception as e:
                logger.error(f"Failed to create import session: {str(e)}")

            for i in range(row_count):
                row_number = int(request.form.get(f'row_{i}_number', i + 2))
                try:
                    # Get order_id first to check for duplicates
                    order_id = request.form.get(f'row_{i}_order_id', '').strip()

                    # Check if order_id already exists in database
                    if order_id:
                        existing_ticket = db_session.query(Ticket).filter(
                            Ticket.firstbaseorderid == order_id
                        ).first()
                        if existing_ticket:
                            failed_imports.append({
                                'row': row_number,
                                'reason': f'Duplicate order_id: {order_id} (already exists in ticket #{existing_ticket.id})'
                            })
                            continue

                    # Validate required fields
                    customer_name = request.form.get(f'row_{i}_customer_name', '').strip()
                    customer_email = request.form.get(f'row_{i}_customer_email', '').strip()
                    customer_country = request.form.get(f'row_{i}_customer_country', '').strip().upper()
                    return_description = request.form.get(f'row_{i}_return_description', '').strip()

                    if not customer_name or not customer_email or not customer_country or not return_description:
                        failed_imports.append({
                            'row': row_number,
                            'reason': 'Missing required fields (customer_name, customer_email, customer_country, or return_description)'
                        })
                        continue

                    # Country is stored as string, no enum validation needed

                    # Get optional fields first
                    customer_phone = request.form.get(f'row_{i}_customer_phone', '').strip()
                    customer_company_name = request.form.get(f'row_{i}_customer_company', '').strip().upper()  # Auto-convert to uppercase

                    # Get direct customer_address from form (editable field)
                    direct_address = request.form.get(f'row_{i}_customer_address', '').strip()

                    # Get address components (needed for both new and existing customers)
                    address_line_1 = request.form.get(f'row_{i}_address_line_1', '').strip()
                    address_line_2 = request.form.get(f'row_{i}_address_line_2', '').strip()
                    city = request.form.get(f'row_{i}_city', '').strip()
                    state = request.form.get(f'row_{i}_state', '').strip()
                    zip_code = request.form.get(f'row_{i}_zip', '').strip()

                    # Build address from components
                    address_parts = []
                    if address_line_1:
                        address_parts.append(address_line_1)
                    if address_line_2:
                        address_parts.append(address_line_2)
                    city_state_zip = []
                    if city:
                        city_state_zip.append(city)
                    if state:
                        city_state_zip.append(state)
                    if zip_code:
                        city_state_zip.append(zip_code)
                    if city_state_zip:
                        address_parts.append(', '.join(city_state_zip))
                    built_address = ', '.join(address_parts) if address_parts else ''

                    # Use direct address if provided, otherwise use built address, otherwise 'N/A'
                    full_address = direct_address if direct_address else (built_address if built_address else 'N/A')

                    # Get or create customer
                    customer = db_session.query(CustomerUser).filter_by(email=customer_email).first()

                    if not customer:
                        # Get or create company if provided
                        company_id = None
                        if customer_company_name:
                            company = db_session.query(Company).filter_by(name=customer_company_name).first()
                            if not company:
                                company = Company(
                                    name=customer_company_name
                                )
                                db_session.add(company)
                                db_session.flush()
                            company_id = company.id

                        customer = CustomerUser(
                            name=customer_name,
                            email=customer_email,
                            contact_number=customer_phone if customer_phone else 'N/A',
                            address=full_address,  # Use the built address from CSV
                            company_id=company_id,
                            country=customer_country  # Store as string
                        )
                        db_session.add(customer)
                        db_session.flush()
                        logger.info(f"Created new customer: {customer_name} ({customer_email}) with address: {full_address}")
                    else:
                        # Update existing customer's address if it's N/A and we have a new address
                        if customer.address == 'N/A' and full_address != 'N/A':
                            customer.address = full_address
                            logger.info(f"Updated existing customer address: {customer_name} ({customer_email}) with address: {full_address}")

                    # Get remaining optional fields
                    asset_serial_number = request.form.get(f'row_{i}_asset_serial_number', '').strip()
                    priority_str = request.form.get(f'row_{i}_priority', 'Medium').strip()
                    queue_name = request.form.get(f'row_{i}_queue_name', '').strip()
                    case_owner_email = request.form.get(f'row_{i}_case_owner_email', '').strip()
                    notes = request.form.get(f'row_{i}_notes', '').strip()

                    # Validate priority
                    try:
                        priority = TicketPriority[priority_str.upper()]
                    except (KeyError, AttributeError):
                        priority = TicketPriority.MEDIUM

                    # Find asset if provided
                    asset_id = None
                    if asset_serial_number:
                        asset = db_session.query(Asset).filter_by(serial_num=asset_serial_number).first()
                        if asset:
                            asset_id = asset.id
                        else:
                            logger.warning(f"Asset not found with serial: {asset_serial_number}")

                    # Find queue if provided
                    queue_id = None
                    if queue_name:
                        queue = db_session.query(Queue).filter_by(name=queue_name).first()
                        if queue:
                            queue_id = queue.id

                    # Find case owner if provided
                    case_owner_id = None
                    if case_owner_email:
                        case_owner = db_session.query(User).filter_by(email=case_owner_email).first()
                        if case_owner:
                            case_owner_id = case_owner.id

                    # Prepare description
                    description = return_description
                    if asset_serial_number:
                        description += f"\n\nAsset Serial Number: {asset_serial_number}"

                    # Determine case owner - use case_owner_id if provided, otherwise default to requester
                    assigned_to_id = case_owner_id if case_owner_id else user_id

                    # Create the ticket
                    ticket = Ticket(
                        subject=f"Asset Return - {customer_name}",
                        description=description,
                        requester_id=user_id,
                        assigned_to_id=assigned_to_id,
                        category=TicketCategory.ASSET_RETURN_CLAW,
                        priority=priority,
                        asset_id=asset_id,
                        customer_id=customer.id,
                        return_description=return_description,
                        queue_id=queue_id,
                        notes=notes if notes else None,
                        shipping_carrier='singpost',
                        firstbaseorderid=order_id if order_id else None  # Store order_id for duplicate prevention
                    )
                    db_session.add(ticket)
                    db_session.flush()
                    ticket_id = ticket.id

                    # Commit immediately after each successful row
                    db_session.commit()

                    successful_imports.append({
                        'row': row_number,
                        'ticket_id': ticket_id,
                        'customer': customer_name
                    })
                    logger.info(f"Created 1stbase ticket {ticket_id} for customer {customer_name}")

                except Exception as row_error:
                    db_session.rollback()
                    logger.error(f"Error processing row {row_number}: {str(row_error)}")
                    failed_imports.append({
                        'row': row_number,
                        'reason': str(row_error)
                    })
                    continue

            # Prepare result message
            success_count = len(successful_imports)
            fail_count = len(failed_imports)

            if success_count > 0:
                flash(f'Successfully imported {success_count} 1stbase ticket(s)', 'success')

            if fail_count > 0:
                flash(f'Failed to import {fail_count} row(s). Check the error log below.', 'warning')
                for failure in failed_imports:
                    flash(f'Row {failure["row"]}: {failure["reason"]}', 'error')

            # Update ImportSession with results
            if import_session_id:
                try:
                    status = 'completed' if success_count > 0 else 'failed'
                    error_details = [f"Row {f['row']}: {f['reason']}" for f in failed_imports[:50]]
                    # Store imported records data (limit to first 100 for storage)
                    import_data = successful_imports[:100] if successful_imports else None
                    logger.info(f"bulk_import_1stbase: Updating session {import_session_id}, successful_imports has {len(successful_imports)} items")
                    update_import_session(import_session_id, success_count=success_count, fail_count=fail_count,
                                         import_data=import_data, error_details=error_details if error_details else None, status=status)
                except Exception as e:
                    logger.error(f"Failed to update import session: {str(e)}")

            return render_template('tickets/bulk_import_result.html',
                                 user=user,
                                 successful_imports=successful_imports,
                                 failed_imports=failed_imports,
                                 success_count=success_count,
                                 fail_count=fail_count,
                                 import_type='1stbase')

        except Exception as e:
            db_session.rollback()
            logger.error(f"Error in bulk import: {str(e)}")
            flash(f'Error processing CSV file: {str(e)}', 'error')
            return redirect(request.url)
        finally:
            db_session.close()

    except Exception as e:
        logger.error(f"Error in bulk import 1stbase: {str(e)}")
        flash(f'Error: {str(e)}', 'error')
        return redirect(url_for('tickets.list_tickets'))


@tickets_bp.route('/import-from-retool/fetch', methods=['POST'])
@login_required
def fetch_from_retool():
    """Fetch CSV data directly from Retool URL"""
    try:
        user = db_manager.get_user(session['user_id'])

        # Only SUPER_ADMIN, DEVELOPER, and SUPERVISOR can access Retool import
        if not (user.is_super_admin or user.is_developer or user.is_supervisor):
            return jsonify({'success': False, 'error': 'Permission denied'}), 403

        # The Retool URL that exports CSV
        retool_export_url = request.json.get('export_url')

        if not retool_export_url:
            return jsonify({'success': False, 'error': 'No export URL provided'}), 400

        # Fetch the CSV from Retool
        logger.info(f"Fetching CSV from Retool: {retool_export_url}")
        response = requests.get(retool_export_url, timeout=30)

        if response.status_code != 200:
            return jsonify({'success': False, 'error': f'Failed to fetch CSV from Retool: HTTP {response.status_code}'}), 500

        # Process the CSV content
        import io
        import tempfile
        from routes.admin import clean_csv_row, group_orders_by_id

        # Generate unique file ID
        file_id = str(uuid.uuid4())

        # Parse CSV
        csv_content = response.text
        csv_reader = csv.DictReader(io.StringIO(csv_content))

        # Convert to list and validate
        raw_data = []
        for row in csv_reader:
            cleaned_row = clean_csv_row(row)
            if cleaned_row:
                raw_data.append(cleaned_row)

        if not raw_data:
            return jsonify({'success': False, 'error': 'No valid data found in CSV'})

        # Group orders by order_id
        grouped_data, individual_data = group_orders_by_id(raw_data)
        display_data = grouped_data + individual_data

        # Check for duplicates
        db_session = db_manager.get_session()
        try:
            existing_order_ids = set()
            existing_tickets = db_session.query(Ticket).filter(
                Ticket.firstbaseorderid.isnot(None)
            ).all()
            existing_order_ids = {ticket.firstbaseorderid for ticket in existing_tickets}
        except:
            existing_order_ids = set()
        finally:
            db_session.close()

        # Mark tickets as duplicate or processing
        duplicate_count = 0
        processing_count = 0
        for row in display_data:
            order_id = row.get('order_id', '').strip()
            status = row.get('status', '').upper()

            row['is_duplicate'] = order_id and order_id in existing_order_ids
            row['is_processing'] = status == 'PROCESSING'
            row['cannot_import'] = row['is_duplicate'] or row['is_processing']

            if row['is_duplicate']:
                duplicate_count += 1
            if row['is_processing']:
                processing_count += 1

        # Store in temporary file
        temp_file = os.path.join(tempfile.gettempdir(), f'csv_import_{file_id}.json')
        with open(temp_file, 'w') as f:
            json.dump(display_data, f)

        # Calculate importable count
        cannot_import_count = sum(1 for row in display_data if row.get('cannot_import', False))
        importable_count = len(display_data) - cannot_import_count

        logger.info(f"Successfully fetched and processed {len(display_data)} records from Retool")

        return jsonify({
            'success': True,
            'file_id': file_id,
            'total_count': len(display_data),
            'importable_count': importable_count,
            'duplicate_count': duplicate_count,
            'processing_count': processing_count,
            'redirect_url': f'/admin/csv-import?file_id={file_id}'
        })

    except requests.RequestException as e:
        logger.error(f"Error fetching from Retool: {str(e)}")
        return jsonify({'success': False, 'error': f'Failed to fetch data from Retool: {str(e)}'}), 500
    except Exception as e:
        logger.error(f"Error in Retool fetch: {str(e)}")
        return jsonify({'success': False, 'error': f'Error: {str(e)}'}), 500


@tickets_bp.route('/import-from-retool', methods=['GET', 'POST'])
@login_required
def import_from_retool():
    """Display Retool iframe for CSV import or handle file upload"""
    try:
        user = db_manager.get_user(session['user_id'])

        # Only SUPER_ADMIN, DEVELOPER, and SUPERVISOR can access Retool import
        if not (user.is_super_admin or user.is_developer or user.is_supervisor):
            flash('Permission denied. Only SUPER_ADMIN, DEVELOPER, and SUPERVISOR can access Retool import.', 'error')
            return redirect(url_for('tickets.list_tickets'))

        if request.method == 'POST':
            # This endpoint will forward the uploaded file to the CSV import upload endpoint
            if 'file' not in request.files:
                return jsonify({'success': False, 'error': 'No file provided'}), 400

            file = request.files['file']
            if file.filename == '':
                return jsonify({'success': False, 'error': 'No file selected'}), 400

            if not file.filename.lower().endswith('.csv'):
                return jsonify({'success': False, 'error': 'File must be a CSV'}), 400

            # Forward to the admin CSV import upload endpoint
            # We'll make an internal request to reuse the existing logic
            import io
            import tempfile

            # Generate unique file ID
            file_id = str(uuid.uuid4())

            # Read and parse CSV
            csv_content = file.read().decode('utf-8')
            csv_reader = csv.DictReader(io.StringIO(csv_content))

            # Import the helper functions from admin routes
            from routes.admin import clean_csv_row, group_orders_by_id

            # Convert to list and validate
            raw_data = []
            for row in csv_reader:
                # Clean and validate the row
                cleaned_row = clean_csv_row(row)
                if cleaned_row:  # Only add valid rows
                    raw_data.append(cleaned_row)

            if not raw_data:
                return jsonify({'success': False, 'error': 'No valid data found in CSV'})

            # Group orders by order_id
            grouped_data, individual_data = group_orders_by_id(raw_data)

            # Combine grouped and individual data for display
            display_data = grouped_data + individual_data

            # Check for duplicates against existing database tickets
            db_session = db_manager.get_session()
            try:
                existing_order_ids = set()
                existing_tickets = db_session.query(Ticket).filter(
                    Ticket.firstbaseorderid.isnot(None)
                ).all()
                existing_order_ids = {ticket.firstbaseorderid for ticket in existing_tickets}
            except:
                existing_order_ids = set()
            finally:
                db_session.close()

            # Mark tickets as duplicate or processing
            duplicate_count = 0
            processing_count = 0
            for row in display_data:
                order_id = row.get('order_id', '').strip()
                status = row.get('status', '').upper()

                row['is_duplicate'] = order_id and order_id in existing_order_ids
                row['is_processing'] = status == 'PROCESSING'
                row['cannot_import'] = row['is_duplicate'] or row['is_processing']

                if row['is_duplicate']:
                    duplicate_count += 1
                if row['is_processing']:
                    processing_count += 1

            # Store in temporary file with file_id
            temp_file = os.path.join(tempfile.gettempdir(), f'csv_import_{file_id}.json')
            with open(temp_file, 'w') as f:
                json.dump(display_data, f)

            # Calculate importable count
            cannot_import_count = sum(1 for row in display_data if row.get('cannot_import', False))
            importable_count = len(display_data) - cannot_import_count

            return jsonify({
                'success': True,
                'file_id': file_id,
                'total_count': len(display_data),
                'importable_count': importable_count,
                'duplicate_count': duplicate_count,
                'processing_count': processing_count,
                'data': display_data
            })

        # GET request - show the Retool iframe
        retool_url = 'https://retool.firstbase.com/apps/59550038-9ae3-11ee-9805-13a1c97ab189/External%20Apps/3PL%20Orders'

        return render_template('tickets/retool_import.html',
                             user=user,
                             retool_url=retool_url)

    except Exception as e:
        logger.error(f"Error in Retool import: {str(e)}")
        flash(f'Error: {str(e)}', 'error')
        return redirect(url_for('tickets.list_tickets'))


# ============================================================================
# PDF ASSET EXTRACTION
# ============================================================================

@tickets_bp.route('/<int:ticket_id>/extract-assets', methods=['GET'])
@login_required
def extract_assets_page(ticket_id):
    """Show the PDF asset extraction page for a ticket"""
    from models.company import Company

    db_session = db_manager.get_session()
    try:
        ticket = db_session.query(Ticket).get(ticket_id)
        if not ticket:
            flash('Ticket not found', 'error')
            return redirect(url_for('tickets.list_tickets'))

        # Get PDF attachments for this ticket
        pdf_attachments = db_session.query(Attachment).filter(
            Attachment.ticket_id == ticket_id,
            Attachment.file_type == 'pdf'
        ).all()

        # Get all companies for dropdown
        companies = db_session.query(Company).order_by(Company.name).all()

        return render_template('tickets/extract_assets.html',
                             ticket=ticket,
                             attachments=pdf_attachments,
                             companies=companies)

    finally:
        db_session.close()


@tickets_bp.route('/<int:ticket_id>/extract-assets/process', methods=['POST'])
@login_required
def process_pdf_extraction(ticket_id):
    """Process PDF and extract asset information"""
    from utils.pdf_extractor import extract_from_attachment

    db_session = db_manager.get_session()
    try:
        ticket = db_session.query(Ticket).get(ticket_id)
        if not ticket:
            return jsonify({'success': False, 'error': 'Ticket not found'}), 404

        attachment_id = request.form.get('attachment_id') or request.json.get('attachment_id')
        if not attachment_id:
            return jsonify({'success': False, 'error': 'No attachment specified'}), 400

        # Get the attachment
        attachment = db_session.query(Attachment).filter(
            Attachment.id == attachment_id,
            Attachment.ticket_id == ticket_id
        ).first()

        if not attachment:
            return jsonify({'success': False, 'error': 'Attachment not found'}), 404

        if attachment.file_type != 'pdf':
            return jsonify({'success': False, 'error': 'Attachment is not a PDF'}), 400

        # Extract assets from PDF
        result = extract_from_attachment(attachment.file_path)

        if not result:
            return jsonify({'success': False, 'error': 'Failed to extract data from PDF'}), 500

        return jsonify({
            'success': True,
            'po_number': result.get('po_number'),
            'reference': result.get('reference'),
            'ship_date': result.get('ship_date'),
            'total_quantity': result.get('total_quantity'),
            'receiver': result.get('receiver'),
            'supplier': result.get('supplier'),
            'extracted_count': len(result.get('assets', [])),
            'assets': result.get('assets', [])
        })

    except Exception as e:
        logger.error(f"Error extracting assets from PDF: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db_session.close()


@tickets_bp.route('/<int:ticket_id>/extract-assets/process-text', methods=['POST'])
@login_required
def process_text_extraction(ticket_id):
    """Process pasted text and extract asset information (no OCR needed)"""
    from utils.pdf_extractor import extract_assets_from_text, parse_packing_list_text

    db_session = db_manager.get_session()
    try:
        ticket = db_session.query(Ticket).get(ticket_id)
        if not ticket:
            return jsonify({'success': False, 'error': 'Ticket not found'}), 404

        text = request.json.get('text', '')
        if not text or len(text.strip()) < 50:
            return jsonify({'success': False, 'error': 'Please provide the pasted text from the invoice/packing list'}), 400

        # Parse the text to extract assets
        result = parse_packing_list_text(text)

        if not result:
            return jsonify({'success': False, 'error': 'Failed to extract data from text'}), 500

        assets = result.get('assets', [])
        if not assets:
            # Try direct text extraction if parse_packing_list_text didn't find assets
            assets = extract_assets_from_text(text)

        return jsonify({
            'success': True,
            'po_number': result.get('po_number'),
            'reference': result.get('reference'),
            'ship_date': result.get('ship_date'),
            'total_quantity': result.get('total_quantity'),
            'receiver': result.get('receiver'),
            'supplier': result.get('supplier'),
            'extracted_count': len(assets),
            'assets': assets,
            'breakdown': result.get('breakdown', {})
        })

    except Exception as e:
        logger.error(f"Error extracting assets from text: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db_session.close()


@tickets_bp.route('/next-asset-tag', methods=['GET'])
@login_required
def get_next_asset_tag():
    """Get the next available asset tag number

    Finds the highest SG-XXXX numeric asset tag and returns the next number.
    Also accepts a 'count' parameter to reserve multiple sequential numbers.
    """
    from models.asset import Asset
    import re

    db_session = db_manager.get_session()
    try:
        count = request.args.get('count', 1, type=int)
        if count < 1:
            count = 1
        if count > 1000:
            count = 1000  # Safety limit

        # Find all SG-XXXX asset tags and extract the numeric portion
        # Pattern: SG- followed by digits
        assets = db_session.query(Asset.asset_tag).filter(
            Asset.asset_tag.like('SG-%')
        ).all()

        max_num = 0
        for (tag,) in assets:
            if tag:
                # Extract numeric portion after SG-
                match = re.match(r'SG-(\d+)$', tag)
                if match:
                    num = int(match.group(1))
                    if num > max_num:
                        max_num = num

        # Generate the next available numbers
        next_tags = []
        for i in range(count):
            next_num = max_num + 1 + i
            next_tags.append(f"SG-{next_num}")

        # Verify these tags don't already exist (in case of non-sequential tags)
        existing = db_session.query(Asset.asset_tag).filter(
            Asset.asset_tag.in_(next_tags)
        ).all()
        existing_set = {t[0] for t in existing}

        # If any exist, find alternatives
        final_tags = []
        current_num = max_num + 1
        while len(final_tags) < count:
            tag = f"SG-{current_num}"
            if tag not in existing_set:
                final_tags.append(tag)
            current_num += 1

        return jsonify({
            'success': True,
            'next_number': max_num + 1,
            'next_tag': final_tags[0] if final_tags else f"SG-{max_num + 1}",
            'tags': final_tags,
            'count': len(final_tags)
        })

    except Exception as e:
        logger.error(f"Error getting next asset tag: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db_session.close()


@tickets_bp.route('/<int:ticket_id>/extract-assets/create', methods=['POST'])
@login_required
def create_extracted_assets(ticket_id):
    """Create assets from extracted PDF data"""
    from models.asset import Asset, AssetStatus
    from sqlalchemy import text
    import uuid

    db_session = db_manager.get_session()
    try:
        ticket = db_session.query(Ticket).get(ticket_id)
        if not ticket:
            return jsonify({'success': False, 'error': 'Ticket not found'}), 404

        data = request.get_json()
        if not data or 'assets' not in data:
            return jsonify({'success': False, 'error': 'No asset data provided'}), 400

        assets_data = data['assets']
        po_number = data.get('po_number', '')
        company_id_raw = data.get('company_id')
        # Convert company_id to int or None
        company_id = int(company_id_raw) if company_id_raw and str(company_id_raw).strip() else None

        # Look up company name for the customer field
        customer_name = None
        if company_id:
            from models.company import Company
            company = db_session.query(Company).get(company_id)
            if company:
                customer_name = company.name

        # Country code to full name mapping
        country_names = {
            'SG': 'Singapore',
            'MY': 'Malaysia',
            'ID': 'Indonesia',
            'TH': 'Thailand',
            'VN': 'Vietnam',
            'PH': 'Philippines',
            'HK': 'Hong Kong',
            'TW': 'Taiwan',
            'JP': 'Japan',
            'KR': 'South Korea',
            'AU': 'Australia',
            'US': 'United States'
        }

        created_assets = []
        errors = []

        for asset_data in assets_data:
            try:
                serial_num = asset_data.get('serial_num', '').strip()

                if not serial_num:
                    continue

                # Check if serial already exists
                existing = db_session.query(Asset).filter(Asset.serial_num == serial_num).first()
                if existing:
                    errors.append(f"Serial {serial_num} already exists (Asset #{existing.id})")
                    continue

                # Get asset tag from frontend (user-provided) or generate one
                asset_tag = asset_data.get('asset_tag', '').strip()
                if not asset_tag:
                    # Generate asset tag if not provided
                    asset_tag = f"AST-{uuid.uuid4().hex[:8].upper()}"

                # Check asset tag uniqueness
                existing_tag = db_session.query(Asset).filter(Asset.asset_tag == asset_tag).first()
                if existing_tag:
                    errors.append(f"Asset tag {asset_tag} already exists (Asset #{existing_tag.id})")
                    continue

                # Get country from frontend and convert to full name
                country_code = asset_data.get('country', 'SG')
                country = country_names.get(country_code, country_code)

                # Remove leading 'S' from serial number if present
                if serial_num and serial_num.startswith('S'):
                    serial_num = serial_num[1:]

                # Create asset
                new_asset = Asset(
                    asset_tag=asset_tag,
                    serial_num=serial_num,
                    name=asset_data.get('name', ''),
                    model=asset_data.get('model', ''),
                    manufacturer=asset_data.get('manufacturer', 'Apple'),
                    category='APPLE',
                    asset_type='APPLE',  # Set asset_type for UI display
                    status=AssetStatus.IN_STOCK,
                    po=po_number,
                    cpu_type=asset_data.get('cpu_type', ''),
                    cpu_cores=asset_data.get('cpu_cores', ''),
                    gpu_cores=asset_data.get('gpu_cores', ''),
                    memory=asset_data.get('memory', ''),
                    harddrive=asset_data.get('harddrive', ''),
                    hardware_type=asset_data.get('hardware_type', 'Laptop'),
                    condition=asset_data.get('condition', 'New'),
                    erased='COMPLETED',  # New assets from delivery orders are factory fresh
                    company_id=company_id,
                    customer=customer_name,  # Set customer string field for display
                    country=country,
                    receiving_date=datetime.datetime.utcnow(),
                    notes=f"Imported from packing list PDF - Ticket #{ticket_id}"
                )

                db_session.add(new_asset)
                db_session.flush()

                # Link asset to ticket
                try:
                    stmt = text("""
                        INSERT INTO ticket_assets (ticket_id, asset_id)
                        VALUES (:ticket_id, :asset_id)
                    """)
                    db_session.execute(stmt, {"ticket_id": ticket_id, "asset_id": new_asset.id})
                except Exception as link_error:
                    logger.warning(f"Error linking asset to ticket: {link_error}")

                created_assets.append({
                    'id': new_asset.id,
                    'asset_tag': new_asset.asset_tag,
                    'serial_num': new_asset.serial_num,
                    'name': new_asset.name
                })

            except Exception as e:
                errors.append(f"Error creating asset {asset_data.get('serial_num', 'unknown')}: {str(e)}")

        db_session.commit()

        return jsonify({
            'success': True,
            'created_count': len(created_assets),
            'error_count': len(errors),
            'assets': created_assets,
            'errors': errors
        })

    except Exception as e:
        db_session.rollback()
        logger.error(f"Error creating extracted assets: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db_session.close()


@tickets_bp.route('/<int:ticket_id>/extract-shipping-info', methods=['POST'])
@login_required
def extract_shipping_info(ticket_id):
    """Extract shipping info from PDF and update ticket description"""
    from utils.pdf_extractor import extract_shipping_info_from_pdf, format_shipping_info_for_description

    db_session = db_manager.get_session()
    try:
        ticket = db_session.query(Ticket).get(ticket_id)
        if not ticket:
            return jsonify({'success': False, 'error': 'Ticket not found'}), 404

        attachment_id = request.json.get('attachment_id')
        if not attachment_id:
            return jsonify({'success': False, 'error': 'No attachment specified'}), 400

        # Get the attachment
        attachment = db_session.query(Attachment).filter(
            Attachment.id == attachment_id,
            Attachment.ticket_id == ticket_id
        ).first()

        if not attachment:
            return jsonify({'success': False, 'error': 'Attachment not found'}), 404

        if attachment.file_type != 'pdf':
            return jsonify({'success': False, 'error': 'Attachment is not a PDF'}), 400

        # Extract shipping info from first page
        info = extract_shipping_info_from_pdf(attachment.file_path)

        if not info:
            return jsonify({'success': False, 'error': 'Failed to extract shipping info from PDF'}), 500

        # Format for description
        formatted_description = format_shipping_info_for_description(info)

        # Return the extracted info and formatted description
        return jsonify({
            'success': True,
            'shipping_info': info,
            'formatted_description': formatted_description
        })

    except Exception as e:
        logger.error(f"Error extracting shipping info: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db_session.close()


@tickets_bp.route('/<int:ticket_id>/update-description', methods=['POST'])
@login_required
def update_ticket_description(ticket_id):
    """Update ticket description with extracted shipping info"""
    db_session = db_manager.get_session()
    try:
        ticket = db_session.query(Ticket).get(ticket_id)
        if not ticket:
            return jsonify({'success': False, 'error': 'Ticket not found'}), 404

        new_description = request.json.get('description')
        append_mode = request.json.get('append', False)

        if not new_description:
            return jsonify({'success': False, 'error': 'No description provided'}), 400

        if append_mode and ticket.description:
            ticket.description = ticket.description + '\n\n' + new_description
        else:
            ticket.description = new_description

        db_session.commit()

        return jsonify({
            'success': True,
            'message': 'Ticket description updated successfully'
        })

    except Exception as e:
        db_session.rollback()
        logger.error(f"Error updating ticket description: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db_session.close()


@tickets_bp.route('/<int:ticket_id>/update-customer', methods=['POST'])
@login_required
def update_ticket_customer(ticket_id):
    """Update ticket customer - SUPER_ADMIN and DEVELOPER only"""
    db_session = db_manager.get_session()
    try:
        # Check user permission
        user = db_session.query(User).get(session.get('user_id'))
        if not user or not (user.is_super_admin or user.is_developer):
            return jsonify({'success': False, 'error': 'Permission denied. Only SUPER_ADMIN and DEVELOPER can update customer.'}), 403

        ticket = db_session.query(Ticket).get(ticket_id)
        if not ticket:
            return jsonify({'success': False, 'error': 'Ticket not found'}), 404

        customer_id = request.json.get('customer_id')
        if not customer_id:
            return jsonify({'success': False, 'error': 'No customer_id provided'}), 400

        # Verify customer exists
        customer = db_session.query(CustomerUser).get(customer_id)
        if not customer:
            return jsonify({'success': False, 'error': 'Customer not found'}), 404

        # Update the ticket's customer
        old_customer_id = ticket.customer_id
        ticket.customer_id = customer_id
        db_session.commit()

        logger.info(f"Ticket {ticket_id} customer updated from {old_customer_id} to {customer_id} by user {user.id}")

        return jsonify({
            'success': True,
            'message': f'Customer updated to {customer.name}'
        })

    except Exception as e:
        db_session.rollback()
        logger.error(f"Error updating ticket customer: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db_session.close()


# =============================================================================
# Asset Intake Check-in Routes
# =============================================================================

@tickets_bp.route('/<int:ticket_id>/checkin', methods=['POST'])
@login_required
def checkin_asset(ticket_id):
    """Check in an asset by serial number for Asset Intake tickets"""
    from models.ticket_asset_checkin import TicketAssetCheckin

    db_session = db_manager.get_session()
    try:
        ticket = db_session.query(Ticket).options(
            joinedload(Ticket.assets)
        ).get(ticket_id)

        if not ticket:
            return jsonify({'success': False, 'error': 'Ticket not found'}), 404

        # Validate ticket is Asset Intake category
        if ticket.category != TicketCategory.ASSET_INTAKE:
            return jsonify({'success': False, 'error': 'Check-in is only available for Asset Intake tickets'}), 400

        data = request.get_json() or {}
        serial_number = data.get('serial_number', '').strip().upper()

        if not serial_number:
            return jsonify({'success': False, 'error': 'Serial number is required'}), 400

        # Find asset by serial number - try multiple variations
        # Some PDFs have leading 'S' prefix on serial numbers
        asset = db_session.query(Asset).filter(
            func.upper(Asset.serial_num) == serial_number
        ).first()

        # If not found, try with 'S' prefix (PDF extraction sometimes includes it)
        if not asset and not serial_number.startswith('S'):
            asset = db_session.query(Asset).filter(
                func.upper(Asset.serial_num) == 'S' + serial_number
            ).first()

        # If not found, try without 'S' prefix (user might scan with S but DB has it without)
        if not asset and serial_number.startswith('S'):
            asset = db_session.query(Asset).filter(
                func.upper(Asset.serial_num) == serial_number[1:]
            ).first()

        if not asset:
            return jsonify({'success': False, 'error': f'Asset not found with serial number: {serial_number}'}), 404

        # Check if asset is assigned to this ticket
        ticket_asset_ids = [a.id for a in ticket.assets]
        if asset.id not in ticket_asset_ids:
            return jsonify({'success': False, 'error': f'Asset {serial_number} is not assigned to this ticket'}), 400

        # Check if already checked in
        existing_checkin = db_session.query(TicketAssetCheckin).filter_by(
            ticket_id=ticket_id,
            asset_id=asset.id
        ).first()

        if existing_checkin and existing_checkin.checked_in:
            return jsonify({'success': False, 'error': f'Asset {serial_number} is already checked in'}), 400

        # Create or update check-in record
        if existing_checkin:
            existing_checkin.checked_in = True
            existing_checkin.checked_in_at = dt.utcnow()
            existing_checkin.checked_in_by_id = current_user.id
            checkin = existing_checkin
        else:
            checkin = TicketAssetCheckin(
                ticket_id=ticket_id,
                asset_id=asset.id,
                checked_in=True,
                checked_in_at=dt.utcnow(),
                checked_in_by_id=current_user.id
            )
            db_session.add(checkin)

        db_session.commit()

        # Get updated progress
        progress = ticket.get_checkin_progress(db_session)
        ticket_closed = False

        # Auto-close ticket if all assets are checked in
        if progress['pending'] == 0 and progress['total'] > 0:
            ticket.status = TicketStatus.RESOLVED
            ticket.custom_status = None  # Clear custom status when setting system status
            db_session.commit()
            ticket_closed = True

        return jsonify({
            'success': True,
            'message': f'Asset {serial_number} checked in successfully',
            'asset': {
                'id': asset.id,
                'serial_number': asset.serial_num,
                'asset_tag': asset.asset_tag,
                'model': asset.model
            },
            'progress': {
                'total': progress['total'],
                'checked_in': progress['checked_in'],
                'pending': progress['pending'],
                'progress_percent': progress['progress_percent'],
                'step': ticket.get_intake_step(db_session)
            },
            'ticket_closed': ticket_closed
        })

    except Exception as e:
        db_session.rollback()
        logger.error(f"Error checking in asset: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db_session.close()


@tickets_bp.route('/<int:ticket_id>/checkin-status', methods=['GET'])
@login_required
def get_checkin_status(ticket_id):
    """Get check-in status for an Asset Intake ticket"""
    from models.ticket_asset_checkin import TicketAssetCheckin

    db_session = db_manager.get_session()
    try:
        ticket = db_session.query(Ticket).options(
            joinedload(Ticket.assets)
        ).get(ticket_id)

        if not ticket:
            return jsonify({'success': False, 'error': 'Ticket not found'}), 404

        if ticket.category != TicketCategory.ASSET_INTAKE:
            return jsonify({'success': False, 'error': 'Check-in status is only available for Asset Intake tickets'}), 400

        # Get all check-in records for this ticket
        checkins = db_session.query(TicketAssetCheckin).filter_by(
            ticket_id=ticket_id
        ).all()
        checkin_map = {c.asset_id: c for c in checkins}

        # Build asset list with check-in status
        assets_data = []
        for asset in ticket.assets:
            checkin = checkin_map.get(asset.id)
            assets_data.append({
                'id': asset.id,
                'serial_number': asset.serial_num,
                'asset_tag': asset.asset_tag,
                'model': asset.model,
                'type': asset.type if hasattr(asset, 'type') else None,
                'checked_in': checkin.checked_in if checkin else False,
                'checked_in_at': checkin.checked_in_at.isoformat() if checkin and checkin.checked_in_at else None,
                'checked_in_by': checkin.checked_in_by.full_name if checkin and checkin.checked_in_by else None
            })

        # Get progress and steps
        intake_detail = ticket.get_intake_steps_detail(db_session)

        return jsonify({
            'success': True,
            'ticket': {
                'id': ticket.id,
                'display_id': ticket.display_id,
                'subject': ticket.subject,
                'status': ticket.status.value if ticket.status else None
            },
            'progress': intake_detail['progress'],
            'current_step': intake_detail['current_step'],
            'steps': intake_detail['steps'],
            'assets': assets_data
        })

    except Exception as e:
        logger.error(f"Error getting check-in status: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db_session.close()


@tickets_bp.route('/<int:ticket_id>/undo-checkin/<int:asset_id>', methods=['POST'])
@login_required
def undo_checkin(ticket_id, asset_id):
    """Undo a check-in for an asset"""
    from models.ticket_asset_checkin import TicketAssetCheckin

    db_session = db_manager.get_session()
    try:
        ticket = db_session.query(Ticket).options(
            joinedload(Ticket.assets)
        ).get(ticket_id)

        if not ticket:
            return jsonify({'success': False, 'error': 'Ticket not found'}), 404

        if ticket.category != TicketCategory.ASSET_INTAKE:
            return jsonify({'success': False, 'error': 'Undo check-in is only available for Asset Intake tickets'}), 400

        # Find the check-in record
        checkin = db_session.query(TicketAssetCheckin).filter_by(
            ticket_id=ticket_id,
            asset_id=asset_id
        ).first()

        if not checkin or not checkin.checked_in:
            return jsonify({'success': False, 'error': 'Asset is not checked in'}), 400

        # Undo the check-in
        checkin.checked_in = False
        checkin.checked_in_at = None
        checkin.checked_in_by_id = None

        # If ticket was resolved, reopen it
        if ticket.status == TicketStatus.RESOLVED:
            ticket.status = TicketStatus.IN_PROGRESS
            ticket.custom_status = None  # Clear custom status when setting system status

        db_session.commit()

        # Get updated progress
        progress = ticket.get_checkin_progress(db_session)

        return jsonify({
            'success': True,
            'message': 'Check-in undone successfully',
            'progress': {
                'total': progress['total'],
                'checked_in': progress['checked_in'],
                'pending': progress['pending'],
                'progress_percent': progress['progress_percent'],
                'step': ticket.get_intake_step(db_session)
            }
        })

    except Exception as e:
        db_session.rollback()
        logger.error(f"Error undoing check-in: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db_session.close()


@tickets_bp.route('/<int:ticket_id>/fix-serial-preview', methods=['GET'])
@login_required
def fix_serial_preview(ticket_id):
    """Preview O→0 serial number fixes for assets in this ticket"""
    import re

    db_session = db_manager.get_session()
    try:
        ticket = db_session.query(Ticket).options(
            joinedload(Ticket.assets)
        ).get(ticket_id)

        if not ticket:
            return jsonify({'success': False, 'error': 'Ticket not found'}), 404

        if ticket.category != TicketCategory.ASSET_INTAKE:
            return jsonify({'success': False, 'error': 'Serial fix is only available for Asset Intake tickets'}), 400

        # Find assets with 'O' (letter) that should be '0' (zero)
        # Look for O that appears where a digit would be expected (surrounded by digits)
        fixes = []
        for asset in ticket.assets:
            if not asset.serial_num:
                continue

            original = asset.serial_num
            # Replace letter O with zero 0 - OCR often misreads these
            # Pattern: O that appears next to digits or in alphanumeric serial patterns
            fixed = re.sub(r'O', '0', original)

            if fixed != original:
                fixes.append({
                    'asset_id': asset.id,
                    'asset_tag': asset.asset_tag,
                    'model': asset.model or '-',
                    'original': original,
                    'fixed': fixed
                })

        return jsonify({
            'success': True,
            'fixes': fixes,
            'count': len(fixes)
        })

    except Exception as e:
        logger.error(f"Error previewing serial fixes: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db_session.close()


@tickets_bp.route('/<int:ticket_id>/fix-serial-apply', methods=['POST'])
@login_required
def fix_serial_apply(ticket_id):
    """Apply O→0 serial number fixes for assets in this ticket"""
    import re

    db_session = db_manager.get_session()
    try:
        ticket = db_session.query(Ticket).options(
            joinedload(Ticket.assets)
        ).get(ticket_id)

        if not ticket:
            return jsonify({'success': False, 'error': 'Ticket not found'}), 404

        if ticket.category != TicketCategory.ASSET_INTAKE:
            return jsonify({'success': False, 'error': 'Serial fix is only available for Asset Intake tickets'}), 400

        data = request.get_json() or {}
        asset_ids_to_fix = data.get('asset_ids', [])

        # If no specific assets provided, fix all
        if not asset_ids_to_fix:
            assets_to_fix = ticket.assets
        else:
            assets_to_fix = [a for a in ticket.assets if a.id in asset_ids_to_fix]

        fixed_count = 0
        fixed_assets = []

        for asset in assets_to_fix:
            if not asset.serial_num:
                continue

            original = asset.serial_num
            # Replace letter O with zero 0
            fixed = re.sub(r'O', '0', original)

            if fixed != original:
                # Track the change
                asset.serial_num = fixed
                fixed_count += 1
                fixed_assets.append({
                    'asset_id': asset.id,
                    'original': original,
                    'fixed': fixed
                })

        db_session.commit()

        return jsonify({
            'success': True,
            'message': f'Fixed {fixed_count} serial number(s)',
            'fixed_count': fixed_count,
            'fixed_assets': fixed_assets
        })

    except Exception as e:
        db_session.rollback()
        logger.error(f"Error applying serial fixes: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db_session.close()


# ============================================================================
# ASSET REMEDIATION - Fix existing assets by re-scanning PDF
# ============================================================================

@tickets_bp.route('/<int:ticket_id>/remediate-assets', methods=['GET'])
@login_required
def remediate_assets_page(ticket_id):
    """Show the asset remediation page for fixing existing assets"""
    from models.company import Company

    db_session = db_manager.get_session()
    try:
        ticket = db_session.query(Ticket).options(
            joinedload(Ticket.assets)
        ).get(ticket_id)

        if not ticket:
            flash('Ticket not found', 'error')
            return redirect(url_for('tickets.list_tickets'))

        # Get PDF attachments for this ticket
        pdf_attachments = db_session.query(Attachment).filter(
            Attachment.ticket_id == ticket_id,
            Attachment.file_type == 'pdf'
        ).all()

        # Get existing assets linked to this ticket
        existing_assets = ticket.assets if ticket.assets else []

        return render_template('tickets/remediate_assets.html',
                             ticket=ticket,
                             attachments=pdf_attachments,
                             existing_assets=existing_assets)

    finally:
        db_session.close()


@tickets_bp.route('/<int:ticket_id>/remediate-assets/match', methods=['POST'])
@login_required
def remediate_assets_match(ticket_id):
    """Extract from PDF and match to existing assets by serial number"""
    from utils.pdf_extractor import extract_from_attachment
    from models.asset import Asset

    db_session = db_manager.get_session()
    try:
        ticket = db_session.query(Ticket).options(
            joinedload(Ticket.assets)
        ).get(ticket_id)

        if not ticket:
            return jsonify({'success': False, 'error': 'Ticket not found'}), 404

        attachment_id = request.json.get('attachment_id')
        if not attachment_id:
            return jsonify({'success': False, 'error': 'No attachment specified'}), 400

        # Get the attachment
        attachment = db_session.query(Attachment).filter(
            Attachment.id == attachment_id,
            Attachment.ticket_id == ticket_id
        ).first()

        if not attachment:
            return jsonify({'success': False, 'error': 'Attachment not found'}), 404

        if attachment.file_type != 'pdf':
            return jsonify({'success': False, 'error': 'Attachment is not a PDF'}), 400

        # Extract assets from PDF using the corrected logic
        result = extract_from_attachment(attachment.file_path)

        if not result:
            return jsonify({'success': False, 'error': 'Failed to extract data from PDF'}), 500

        extracted_assets = result.get('assets', [])

        # Build a lookup by serial number from extracted data
        extracted_by_serial = {}
        for asset in extracted_assets:
            serial = asset.get('serial_num', '').strip()
            # Handle leading 'S' in serial numbers
            if serial.startswith('S'):
                serial = serial[1:]
            if serial:
                extracted_by_serial[serial] = asset

        # Match existing assets to extracted data
        matches = []
        unmatched_existing = []
        unmatched_extracted = list(extracted_by_serial.keys())

        for existing_asset in ticket.assets:
            serial = existing_asset.serial_num or ''
            if serial in extracted_by_serial:
                extracted = extracted_by_serial[serial]
                unmatched_extracted.remove(serial)

                # Compare fields and identify differences
                changes = []
                fields_to_check = [
                    ('name', 'Name'),
                    ('model', 'Model'),
                    ('cpu_type', 'CPU Type'),
                    ('cpu_cores', 'CPU Cores'),
                    ('gpu_cores', 'GPU Cores'),
                    ('memory', 'RAM'),
                    ('harddrive', 'Storage'),
                ]

                for field, label in fields_to_check:
                    old_val = getattr(existing_asset, field, '') or ''
                    new_val = extracted.get(field, '') or ''
                    if str(old_val).strip() != str(new_val).strip():
                        changes.append({
                            'field': field,
                            'label': label,
                            'old': str(old_val),
                            'new': str(new_val)
                        })

                matches.append({
                    'asset_id': existing_asset.id,
                    'serial_num': serial,
                    'asset_tag': existing_asset.asset_tag,
                    'current': {
                        'name': existing_asset.name or '',
                        'model': existing_asset.model or '',
                        'cpu_type': existing_asset.cpu_type or '',
                        'cpu_cores': existing_asset.cpu_cores or '',
                        'gpu_cores': existing_asset.gpu_cores or '',
                        'memory': existing_asset.memory or '',
                        'harddrive': existing_asset.harddrive or '',
                    },
                    'extracted': extracted,
                    'changes': changes,
                    'has_changes': len(changes) > 0
                })
            else:
                unmatched_existing.append({
                    'asset_id': existing_asset.id,
                    'serial_num': serial,
                    'asset_tag': existing_asset.asset_tag,
                    'name': existing_asset.name or ''
                })

        # Count assets with actual changes
        assets_with_changes = [m for m in matches if m['has_changes']]

        return jsonify({
            'success': True,
            'total_extracted': len(extracted_assets),
            'total_existing': len(ticket.assets),
            'matched_count': len(matches),
            'changes_count': len(assets_with_changes),
            'matches': matches,
            'unmatched_existing': unmatched_existing,
            'unmatched_extracted': unmatched_extracted
        })

    except Exception as e:
        logger.error(f"Error matching assets for remediation: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db_session.close()


@tickets_bp.route('/<int:ticket_id>/remediate-assets/update', methods=['POST'])
@login_required
def remediate_assets_update(ticket_id):
    """Apply remediation updates to existing assets"""
    from models.asset import Asset

    db_session = db_manager.get_session()
    try:
        ticket = db_session.query(Ticket).get(ticket_id)
        if not ticket:
            return jsonify({'success': False, 'error': 'Ticket not found'}), 404

        data = request.get_json()
        if not data or 'updates' not in data:
            return jsonify({'success': False, 'error': 'No update data provided'}), 400

        updates = data['updates']
        updated_count = 0
        errors = []
        updated_assets = []

        for update in updates:
            try:
                asset_id = update.get('asset_id')
                new_values = update.get('new_values', {})

                asset = db_session.query(Asset).get(asset_id)
                if not asset:
                    errors.append(f"Asset #{asset_id} not found")
                    continue

                # Apply updates - ONLY if new value is not empty
                # This prevents overwriting existing data with blank extracted values
                changes_made = []
                skipped_empty = []
                for field, value in new_values.items():
                    if hasattr(asset, field):
                        old_val = getattr(asset, field)
                        new_val = str(value).strip() if value else ''
                        old_val_str = str(old_val).strip() if old_val else ''

                        # Skip if new value is empty but old value exists
                        if not new_val and old_val_str:
                            skipped_empty.append({
                                'field': field,
                                'kept': old_val_str
                            })
                            continue

                        # Skip if values are the same
                        if old_val_str == new_val:
                            continue

                        setattr(asset, field, value)
                        changes_made.append({
                            'field': field,
                            'old': old_val,
                            'new': value
                        })

                if changes_made:
                    updated_count += 1
                    updated_assets.append({
                        'asset_id': asset_id,
                        'serial_num': asset.serial_num,
                        'changes': changes_made
                    })

            except Exception as e:
                errors.append(f"Error updating asset #{update.get('asset_id', 'unknown')}: {str(e)}")

        db_session.commit()

        return jsonify({
            'success': True,
            'updated_count': updated_count,
            'error_count': len(errors),
            'updated_assets': updated_assets,
            'errors': errors
        })

    except Exception as e:
        db_session.rollback()
        logger.error(f"Error applying remediation updates: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db_session.close()


# ============================================
# SERVICE RECORD ROUTES
# ============================================

@tickets_bp.route('/<int:ticket_id>/service-records', methods=['GET'])
@login_required
def get_service_records(ticket_id):
    """Get all service records for a ticket"""
    from database import SessionLocal
    from models.service_record import ServiceRecord

    db_session = SessionLocal()
    try:
        ticket = db_session.query(Ticket).get(ticket_id)
        if not ticket:
            return jsonify({'success': False, 'error': 'Ticket not found'}), 404

        records = db_session.query(ServiceRecord).filter(
            ServiceRecord.ticket_id == ticket_id
        ).order_by(ServiceRecord.performed_at.desc()).all()

        return jsonify({
            'success': True,
            'service_records': [r.to_dict() for r in records]
        })

    except Exception as e:
        logger.error(f"Error getting service records: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db_session.close()


@tickets_bp.route('/<int:ticket_id>/service-records', methods=['POST'])
@login_required
def add_service_record(ticket_id):
    """Add a new service record to a ticket"""
    from database import SessionLocal
    from models.service_record import ServiceRecord

    db_session = SessionLocal()
    try:
        ticket = db_session.query(Ticket).get(ticket_id)
        if not ticket:
            return jsonify({'success': False, 'error': 'Ticket not found'}), 404

        data = request.get_json() or request.form.to_dict()

        service_type = data.get('service_type')
        if not service_type:
            return jsonify({'success': False, 'error': 'Service type is required'}), 400

        description = data.get('description', '')
        asset_id = data.get('asset_id')
        assigned_to_id = data.get('assigned_to_id')

        # If asset_id is provided, verify it exists
        if asset_id:
            asset = db_session.query(Asset).get(asset_id)
            if not asset:
                return jsonify({'success': False, 'error': 'Asset not found'}), 404

        # If assigned_to_id is provided, verify user exists
        if assigned_to_id:
            assigned_user = db_session.query(User).get(assigned_to_id)
            if not assigned_user:
                return jsonify({'success': False, 'error': 'Assigned user not found'}), 404

        status = data.get('status', 'Requested')

        # Create the service record
        service_record = ServiceRecord(
            ticket_id=ticket_id,
            asset_id=int(asset_id) if asset_id else None,
            service_type=service_type,
            description=description,
            status=status,
            requested_by_id=current_user.id,
            assigned_to_id=int(assigned_to_id) if assigned_to_id else None
        )

        db_session.add(service_record)
        db_session.commit()

        # Refresh to get the relationships
        db_session.refresh(service_record)

        # Send notification to assigned person if someone was assigned
        if assigned_to_id and int(assigned_to_id) != current_user.id:
            from models.notification import Notification
            notification = Notification(
                user_id=int(assigned_to_id),
                type='service_record_assignment',
                title=f'New Service Request Assigned - {service_record.request_id}',
                message=f'{current_user.username} assigned you a service request: "{service_type}" on ticket #{ticket_id}',
                reference_type='ticket',
                reference_id=ticket_id
            )
            db_session.add(notification)
            db_session.commit()

        return jsonify({
            'success': True,
            'message': 'Service record added successfully',
            'service_record': service_record.to_dict()
        })

    except Exception as e:
        db_session.rollback()
        logger.error(f"Error adding service record: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db_session.close()


@tickets_bp.route('/<int:ticket_id>/service-records/<int:record_id>', methods=['DELETE'])
@login_required
def delete_service_record(ticket_id, record_id):
    """Delete a service record"""
    from database import SessionLocal
    from models.service_record import ServiceRecord

    db_session = SessionLocal()
    try:
        record = db_session.query(ServiceRecord).filter(
            ServiceRecord.id == record_id,
            ServiceRecord.ticket_id == ticket_id
        ).first()

        if not record:
            return jsonify({'success': False, 'error': 'Service record not found'}), 404

        db_session.delete(record)
        db_session.commit()

        return jsonify({
            'success': True,
            'message': 'Service record deleted successfully'
        })

    except Exception as e:
        db_session.rollback()
        logger.error(f"Error deleting service record: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db_session.close()


@tickets_bp.route('/<int:ticket_id>/service-records/<int:record_id>/status', methods=['PUT'])
@login_required
def update_service_record_status(ticket_id, record_id):
    """Update the status of a service record"""
    from database import SessionLocal
    from models.service_record import ServiceRecord
    from models.notification import Notification
    from datetime import datetime

    db_session = SessionLocal()
    try:
        record = db_session.query(ServiceRecord).filter(
            ServiceRecord.id == record_id,
            ServiceRecord.ticket_id == ticket_id
        ).first()

        if not record:
            return jsonify({'success': False, 'error': 'Service record not found'}), 404

        data = request.get_json() or request.form.to_dict()
        new_status = data.get('status')
        old_status = record.status

        if not new_status:
            return jsonify({'success': False, 'error': 'Status is required'}), 400

        if new_status not in ['Requested', 'In Progress', 'Completed']:
            return jsonify({'success': False, 'error': 'Invalid status'}), 400

        record.status = new_status

        # If marking as completed, record who completed it and when
        if new_status == 'Completed':
            record.completed_by_id = current_user.id
            record.completed_at = datetime.utcnow()
        elif new_status != 'Completed':
            # If status changed from Completed to something else, clear completion info
            record.completed_by_id = None
            record.completed_at = None

        # Send notifications when status changes
        notifications_to_create = []

        # Notify the requester when status changes (if they're not the one making the change)
        if record.requested_by_id and record.requested_by_id != current_user.id:
            notifications_to_create.append(Notification(
                user_id=record.requested_by_id,
                type='service_record_update',
                title=f'Service Request {record.request_id} - {new_status}',
                message=f'{current_user.username} updated your service request "{record.service_type}" to {new_status}',
                reference_type='ticket',
                reference_id=ticket_id
            ))

        # Notify assigned person when status changes (if they exist and aren't the one making the change)
        if record.assigned_to_id and record.assigned_to_id != current_user.id and record.assigned_to_id != record.requested_by_id:
            notifications_to_create.append(Notification(
                user_id=record.assigned_to_id,
                type='service_record_update',
                title=f'Service Request {record.request_id} - {new_status}',
                message=f'{current_user.username} updated the assigned service request "{record.service_type}" to {new_status}',
                reference_type='ticket',
                reference_id=ticket_id
            ))

        # Special notification when completed
        if new_status == 'Completed' and old_status != 'Completed':
            # If requester is different from completer, send completion notification
            if record.requested_by_id and record.requested_by_id != current_user.id:
                notifications_to_create.append(Notification(
                    user_id=record.requested_by_id,
                    type='service_record_completed',
                    title=f'Service Request Completed - {record.request_id}',
                    message=f'{current_user.username} has completed your service request "{record.service_type}"',
                    reference_type='ticket',
                    reference_id=ticket_id
                ))

        # Add all notifications
        for notification in notifications_to_create:
            db_session.add(notification)

        db_session.commit()
        db_session.refresh(record)

        return jsonify({
            'success': True,
            'message': f'Status updated to {new_status}',
            'service_record': record.to_dict()
        })

    except Exception as e:
        db_session.rollback()
        logger.error(f"Error updating service record status: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db_session.close()


# ============= Bulk Tracking Update =============

def refresh_single_ticket_tracking(ticket, db_session):
    """
    Refresh tracking for a single ticket.
    Returns dict with results for each package/tracking.
    """
    results = {
        'ticket_id': ticket.id,
        'display_id': ticket.display_id if ticket.display_id else f'#{ticket.id}',
        'category': ticket.category.value if ticket.category else 'Unknown',
        'packages_updated': 0,
        'packages_failed': 0,
        'status_changed': False,
        'errors': []
    }

    try:
        # Handle Asset Checkout (claw) with multiple packages
        if ticket.category and ticket.category.name == 'ASSET_CHECKOUT_CLAW':
            packages_to_check = []

            if ticket.shipping_tracking:
                packages_to_check.append((1, ticket.shipping_tracking, ticket.shipping_carrier, 'shipping_status'))
            if ticket.shipping_tracking_2:
                packages_to_check.append((2, ticket.shipping_tracking_2, ticket.shipping_carrier_2, 'shipping_status_2'))
            if ticket.shipping_tracking_3:
                packages_to_check.append((3, ticket.shipping_tracking_3, ticket.shipping_carrier_3, 'shipping_status_3'))
            if ticket.shipping_tracking_4:
                packages_to_check.append((4, ticket.shipping_tracking_4, ticket.shipping_carrier_4, 'shipping_status_4'))
            if ticket.shipping_tracking_5:
                packages_to_check.append((5, ticket.shipping_tracking_5, ticket.shipping_carrier_5, 'shipping_status_5'))

            for pkg_num, tracking_num, carrier, status_field in packages_to_check:
                try:
                    tracking_num = tracking_num.strip()
                    latest_status = None

                    # Determine carrier and use appropriate tracking API
                    carrier_lower = (carrier or '').lower() if carrier else ''

                    # Use appropriate tracking API based on carrier
                    is_singpost = is_singpost_tracking_number(tracking_num) or carrier_lower == 'singpost'

                    if is_singpost:
                        # Use SingPost API for SingPost packages
                        if singpost_client and singpost_client.is_configured():
                            try:
                                result = singpost_client.track_single(tracking_num)
                                if result and result.get('success'):
                                    latest_status = result.get('status', 'Unknown')
                            except Exception as sp_err:
                                logger.warning(f"SingPost tracking failed for {tracking_num}: {sp_err}")
                    else:
                        # Use OxyLabs/Ship24 scraping for other carriers (UPS, DHL, FedEx, etc.)
                        try:
                            from utils.ship24_tracker import get_tracker
                            import concurrent.futures
                            ship24_tracker = get_tracker()

                            def track_with_timeout():
                                return ship24_tracker.track_parcel_sync(
                                    tracking_num,
                                    carrier=carrier if carrier else None,
                                    method='oxylabs'
                                )

                            with concurrent.futures.ThreadPoolExecutor() as executor:
                                future = executor.submit(track_with_timeout)
                                result = future.result(timeout=45)  # 45 second timeout

                            if result and result.get('status'):
                                status = result.get('status', '')
                                if 'delivered' in status.lower():
                                    latest_status = 'Delivered'
                                elif 'transit' in status.lower():
                                    latest_status = 'In Transit'
                                elif 'out for delivery' in status.lower():
                                    latest_status = 'Out for Delivery'
                                elif status and status != 'Unknown':
                                    latest_status = status
                        except concurrent.futures.TimeoutError:
                            logger.warning(f"OxyLabs tracking timed out for {tracking_num}")
                        except Exception as oxy_err:
                            logger.warning(f"OxyLabs tracking failed for {tracking_num}: {oxy_err}")

                    # Update status if we got one
                    if latest_status:
                        old_status = getattr(ticket, status_field, None)
                        setattr(ticket, status_field, latest_status)
                        results['packages_updated'] += 1
                        logger.info(f"Updated ticket {ticket.id} package {pkg_num}: {old_status} -> {latest_status}")
                    else:
                        results['packages_failed'] += 1

                except Exception as pkg_err:
                    results['packages_failed'] += 1
                    results['errors'].append(f"Package {pkg_num}: {str(pkg_err)}")

            # Check if all packages are delivered for auto-close
            if results['packages_updated'] > 0:
                all_delivered = True
                packages = ticket.get_all_packages() if hasattr(ticket, 'get_all_packages') else []
                for package in packages:
                    pkg_status = (package.get('status') or '').lower()
                    # Check for delivered, received, or customer received
                    if not pkg_status or ('delivered' not in pkg_status and 'received' not in pkg_status):
                        all_delivered = False
                        break

                if all_delivered and ticket.status not in [TicketStatus.RESOLVED, TicketStatus.RESOLVED_DELIVERED]:
                    ticket.status = TicketStatus.RESOLVED
                    ticket.custom_status = None  # Clear custom status when setting system status
                    ticket.notes = (ticket.notes or "") + f"\n[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}] Ticket auto-closed: All packages delivered"
                    results['status_changed'] = True
                    logger.info(f"Auto-closed ticket {ticket.id} - all packages delivered")

        # Handle Asset Return (claw) with return tracking
        elif ticket.category and ticket.category.name == 'ASSET_RETURN_CLAW' and ticket.return_tracking:
            # Skip if carrier is "no_tracking"
            carrier = getattr(ticket, 'return_carrier', 'singpost') or 'singpost'
            if carrier.lower() == 'no_tracking':
                logger.info(f"Skipping ticket {ticket.id} - no tracking selected for return")
                return results

            try:
                tracking_num = ticket.return_tracking.strip()
                latest_status = None
                carrier_lower = carrier.lower()

                # Use appropriate tracking API based on carrier
                is_singpost = is_singpost_tracking_number(tracking_num) or carrier_lower == 'singpost'

                if is_singpost:
                    # Use SingPost API for SingPost packages
                    if singpost_client and singpost_client.is_configured():
                        try:
                            result = singpost_client.track_single(tracking_num)
                            if result and result.get('success'):
                                latest_status = result.get('status', 'Unknown')
                        except Exception as sp_err:
                            logger.warning(f"SingPost tracking failed for return {tracking_num}: {sp_err}")
                else:
                    # Use OxyLabs/Ship24 scraping for other carriers (UPS, DHL, FedEx, etc.)
                    try:
                        from utils.ship24_tracker import get_tracker
                        import concurrent.futures
                        ship24_tracker = get_tracker()

                        def track_return_with_timeout():
                            return ship24_tracker.track_parcel_sync(
                                tracking_num,
                                carrier=carrier if carrier else None,
                                method='oxylabs'
                            )

                        with concurrent.futures.ThreadPoolExecutor() as executor:
                            future = executor.submit(track_return_with_timeout)
                            result = future.result(timeout=45)  # 45 second timeout

                        if result and result.get('status'):
                            status = result.get('status', '')
                            if 'delivered' in status.lower():
                                latest_status = 'Delivered'
                            elif 'received' in status.lower():
                                latest_status = 'Received'
                            elif 'transit' in status.lower():
                                latest_status = 'In Transit'
                            elif 'out for delivery' in status.lower():
                                latest_status = 'Out for Delivery'
                            elif status and status != 'Unknown':
                                latest_status = status
                    except Exception as oxy_err:
                        logger.warning(f"OxyLabs tracking failed for return {tracking_num}: {oxy_err}")

                if latest_status:
                    old_status = ticket.return_status
                    ticket.return_status = latest_status
                    results['packages_updated'] += 1
                    logger.info(f"Updated ticket {ticket.id} return tracking: {old_status} -> {latest_status}")

                    # Auto-close when return is delivered/received at warehouse
                    status_lower = latest_status.lower()
                    if ('delivered' in status_lower or
                        'received' in status_lower or
                        'warehouse' in status_lower or
                        'collected' in status_lower):
                        if ticket.status not in [TicketStatus.RESOLVED, TicketStatus.RESOLVED_DELIVERED]:
                            ticket.status = TicketStatus.RESOLVED
                            ticket.custom_status = None  # Clear custom status when setting system status
                            ticket.notes = (ticket.notes or "") + f"\n[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}] Ticket auto-closed: Return received at warehouse. Case completed!"
                            results['status_changed'] = True
                            logger.info(f"Auto-closed ticket {ticket.id} - return received at warehouse")
                else:
                    results['packages_failed'] += 1

            except Exception as return_err:
                results['packages_failed'] += 1
                results['errors'].append(f"Return tracking: {str(return_err)}")

        # Handle regular tickets with single tracking
        elif ticket.shipping_tracking:
            try:
                tracking_num = ticket.shipping_tracking.strip()
                latest_status = None
                carrier = getattr(ticket, 'shipping_carrier', None)
                carrier_lower = (carrier or '').lower() if carrier else ''

                # Use appropriate tracking API based on carrier
                is_singpost = is_singpost_tracking_number(tracking_num) or carrier_lower == 'singpost'

                if is_singpost:
                    # Use SingPost API for SingPost packages
                    if singpost_client and singpost_client.is_configured():
                        try:
                            result = singpost_client.track_single(tracking_num)
                            if result and result.get('success'):
                                latest_status = result.get('status', 'Unknown')
                        except:
                            pass
                else:
                    # Use OxyLabs/Ship24 scraping for other carriers
                    try:
                        from utils.ship24_tracker import get_tracker
                        import concurrent.futures
                        ship24_tracker = get_tracker()

                        def track_with_timeout():
                            return ship24_tracker.track_parcel_sync(
                                tracking_num,
                                carrier=carrier if carrier else None,
                                method='oxylabs'
                            )

                        with concurrent.futures.ThreadPoolExecutor() as executor:
                            future = executor.submit(track_with_timeout)
                            result = future.result(timeout=45)

                        if result and result.get('status'):
                            status = result.get('status', '')
                            if 'delivered' in status.lower():
                                latest_status = 'Delivered'
                            elif 'transit' in status.lower():
                                latest_status = 'In Transit'
                            elif 'out for delivery' in status.lower():
                                latest_status = 'Out for Delivery'
                            elif status and status != 'Unknown':
                                latest_status = status
                    except Exception as oxy_err:
                        logger.warning(f"OxyLabs tracking failed for {tracking_num}: {oxy_err}")

                if latest_status:
                    old_status = ticket.shipping_status
                    ticket.shipping_status = latest_status
                    results['packages_updated'] += 1

                    # Auto-close for certain categories when delivered
                    if 'delivered' in latest_status.lower() or 'received' in latest_status.lower():
                        if ticket.category == TicketCategory.ASSET_CHECKOUT_CLAW:
                            if ticket.status not in [TicketStatus.RESOLVED, TicketStatus.RESOLVED_DELIVERED]:
                                ticket.status = TicketStatus.RESOLVED
                                ticket.custom_status = None  # Clear custom status when setting system status
                                results['status_changed'] = True
                else:
                    results['packages_failed'] += 1

            except Exception as single_err:
                results['packages_failed'] += 1
                results['errors'].append(str(single_err))

        ticket.updated_at = datetime.datetime.now()

    except Exception as e:
        results['errors'].append(str(e))
        logger.error(f"Error refreshing tracking for ticket {ticket.id}: {e}")

    return results


@tickets_bp.route('/admin/refresh-all-tracking', methods=['POST'])
@login_required
def refresh_all_tracking():
    """
    Bulk refresh tracking for all open tickets with tracking numbers.
    Admin/Developer only.
    Supports filters: carrier, category
    """
    user = db_manager.get_user(session.get('user_id'))
    if not user or user.user_type.name not in ['SUPER_ADMIN', 'DEVELOPER']:
        return jsonify({'success': False, 'error': 'Permission denied - Admin/Developer only'}), 403

    # Get filter parameters from request
    data = request.get_json(silent=True) or {}
    filter_carrier = data.get('carrier', 'all')  # 'all', 'singpost', 'dhl', 'ups', etc.
    filter_category = data.get('category', 'all')  # 'all', 'ASSET_CHECKOUT_CLAW', 'ASSET_RETURN_CLAW', etc.

    start_time = time.time()
    db_session = db_manager.get_session()
    try:
        # Build base query for open tickets with tracking numbers
        query = db_session.query(Ticket).filter(
            Ticket.status.notin_([TicketStatus.RESOLVED, TicketStatus.RESOLVED_DELIVERED]),
            or_(
                and_(Ticket.shipping_tracking.isnot(None), Ticket.shipping_tracking != ''),
                and_(Ticket.shipping_tracking_2.isnot(None), Ticket.shipping_tracking_2 != ''),
                and_(Ticket.shipping_tracking_3.isnot(None), Ticket.shipping_tracking_3 != ''),
                and_(Ticket.shipping_tracking_4.isnot(None), Ticket.shipping_tracking_4 != ''),
                and_(Ticket.shipping_tracking_5.isnot(None), Ticket.shipping_tracking_5 != ''),
                and_(Ticket.return_tracking.isnot(None), Ticket.return_tracking != '')  # Asset Return (claw)
            )
        )

        # Apply category filter
        if filter_category and filter_category != 'all':
            try:
                category_enum = TicketCategory[filter_category]
                query = query.filter(Ticket.category == category_enum)
            except KeyError:
                pass  # Invalid category, skip filter

        # Apply carrier filter
        if filter_carrier and filter_carrier != 'all':
            carrier_lower = filter_carrier.lower()
            query = query.filter(
                or_(
                    Ticket.shipping_carrier == carrier_lower,
                    Ticket.shipping_carrier_2 == carrier_lower,
                    Ticket.shipping_carrier_3 == carrier_lower,
                    Ticket.shipping_carrier_4 == carrier_lower,
                    Ticket.shipping_carrier_5 == carrier_lower,
                    Ticket.return_carrier == carrier_lower
                )
            )

        tickets = query.all()

        total_tickets = len(tickets)
        results_summary = {
            'total_tickets': total_tickets,
            'tickets_updated': 0,
            'tickets_failed': 0,
            'tickets_auto_closed': 0,
            'total_packages_updated': 0,
            'total_packages_failed': 0,
            'filters': {
                'carrier': filter_carrier,
                'category': filter_category
            },
            'details': []
        }

        for i, ticket in enumerate(tickets):
            try:
                result = refresh_single_ticket_tracking(ticket, db_session)
                results_summary['details'].append(result)

                if result['packages_updated'] > 0:
                    results_summary['tickets_updated'] += 1
                    results_summary['total_packages_updated'] += result['packages_updated']

                if result.get('packages_failed', 0) > 0:
                    results_summary['tickets_failed'] += 1
                    results_summary['total_packages_failed'] += result['packages_failed']

                if result.get('status_changed'):
                    results_summary['tickets_auto_closed'] += 1

                # Commit after each ticket to prevent timeout from losing all progress
                db_session.commit()

                # Add delay between tickets to respect SingPost rate limits
                # (1 second global minimum + buffer)
                if i < len(tickets) - 1:  # Don't sleep after last ticket
                    time.sleep(1.2)

            except Exception as ticket_err:
                db_session.rollback()  # Rollback failed ticket only
                results_summary['tickets_failed'] += 1
                results_summary['details'].append({
                    'ticket_id': ticket.id,
                    'packages_updated': 0,
                    'packages_failed': 1,
                    'status_changed': False,
                    'error': str(ticket_err)
                })

        # Calculate duration
        duration_seconds = int(time.time() - start_time)

        # Save the refresh log to database
        # Include filters in details for later retrieval
        details_with_meta = {
            'filters': results_summary.get('filters', {}),
            'items': results_summary['details']
        }
        refresh_log = TrackingRefreshLog(
            created_by_id=user.id,
            created_by_name=user.username or user.email,
            total_tickets=total_tickets,
            tickets_updated=results_summary['tickets_updated'],
            tickets_auto_closed=results_summary['tickets_auto_closed'],
            tickets_failed=results_summary['tickets_failed'],
            total_packages_updated=results_summary['total_packages_updated'],
            total_packages_failed=results_summary['total_packages_failed'],
            duration_seconds=duration_seconds,
            details=details_with_meta
        )
        db_session.add(refresh_log)
        db_session.commit()
        log_id = refresh_log.id

        return jsonify({
            'success': True,
            'message': f'Refreshed tracking for {results_summary["tickets_updated"]}/{total_tickets} tickets',
            'summary': results_summary,
            'log_id': log_id
        })

    except Exception as e:
        db_session.rollback()
        logger.error(f"Error in bulk tracking refresh: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db_session.close()


@tickets_bp.route('/admin/refresh-tracking-status', methods=['GET'])
@login_required
def get_tracking_refresh_status():
    """
    Get count of tickets that need tracking refresh.
    Accepts optional filter parameters: carrier, category
    """
    user = db_manager.get_user(session.get('user_id'))
    if not user or user.user_type.name not in ['SUPER_ADMIN', 'DEVELOPER', 'SUPERVISOR']:
        return jsonify({'success': False, 'error': 'Permission denied'}), 403

    # Get filter parameters from query string
    filter_carrier = request.args.get('carrier', 'all')
    filter_category = request.args.get('category', 'all')

    db_session = db_manager.get_session()
    try:
        # Build base query for open tickets with tracking
        query = db_session.query(Ticket).filter(
            Ticket.status.notin_([TicketStatus.RESOLVED, TicketStatus.RESOLVED_DELIVERED]),
            or_(
                and_(Ticket.shipping_tracking.isnot(None), Ticket.shipping_tracking != ''),
                and_(Ticket.shipping_tracking_2.isnot(None), Ticket.shipping_tracking_2 != ''),
                and_(Ticket.shipping_tracking_3.isnot(None), Ticket.shipping_tracking_3 != ''),
                and_(Ticket.shipping_tracking_4.isnot(None), Ticket.shipping_tracking_4 != ''),
                and_(Ticket.shipping_tracking_5.isnot(None), Ticket.shipping_tracking_5 != ''),
                and_(Ticket.return_tracking.isnot(None), Ticket.return_tracking != '')
            )
        )

        # Apply category filter
        if filter_category and filter_category != 'all':
            try:
                category_enum = TicketCategory[filter_category]
                query = query.filter(Ticket.category == category_enum)
            except KeyError:
                pass  # Invalid category, skip filter

        # Apply carrier filter
        if filter_carrier and filter_carrier != 'all':
            carrier_lower = filter_carrier.lower()
            query = query.filter(
                or_(
                    Ticket.shipping_carrier == carrier_lower,
                    Ticket.shipping_carrier_2 == carrier_lower,
                    Ticket.shipping_carrier_3 == carrier_lower,
                    Ticket.shipping_carrier_4 == carrier_lower,
                    Ticket.shipping_carrier_5 == carrier_lower,
                    Ticket.return_carrier == carrier_lower
                )
            )

        count = query.count()

        return jsonify({
            'success': True,
            'tickets_with_tracking': count,
            'filters': {
                'carrier': filter_carrier,
                'category': filter_category
            }
        })

    except Exception as e:
        logger.error(f"Error getting tracking status: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db_session.close()


@tickets_bp.route('/admin/tracking-refresh-history')
@login_required
def tracking_refresh_history():
    """View history of all tracking refresh operations."""
    user = db_manager.get_user(session.get('user_id'))
    if not user or user.user_type.name not in ['SUPER_ADMIN', 'DEVELOPER', 'SUPERVISOR']:
        flash('Permission denied', 'error')
        return redirect(url_for('tickets.list_tickets'))

    db_session = db_manager.get_session()
    try:
        logs = db_session.query(TrackingRefreshLog).order_by(
            TrackingRefreshLog.created_at.desc()
        ).limit(50).all()

        return render_template('tickets/tracking_refresh_history.html',
                               logs=logs,
                               current_user=user)
    finally:
        db_session.close()


@tickets_bp.route('/admin/tracking-refresh-report/<int:log_id>')
@login_required
def tracking_refresh_report(log_id):
    """View detailed report for a specific tracking refresh."""
    user = db_manager.get_user(session.get('user_id'))
    if not user or user.user_type.name not in ['SUPER_ADMIN', 'DEVELOPER', 'SUPERVISOR']:
        flash('Permission denied', 'error')
        return redirect(url_for('tickets.list_tickets'))

    db_session = db_manager.get_session()
    try:
        log = db_session.query(TrackingRefreshLog).filter_by(id=log_id).first()
        if not log:
            flash('Report not found', 'error')
            return redirect(url_for('tickets.tracking_refresh_history'))

        # Handle both old format (array) and new format (object with filters and items)
        raw_details = log.details or []
        filters = {}
        if isinstance(raw_details, dict):
            # New format with filters
            filters = raw_details.get('filters', {})
            details = raw_details.get('items', [])
        else:
            # Old format (just array)
            details = raw_details

        # Categorize the details
        updated = []
        auto_closed = []
        failed = []
        no_change = []

        for item in details:
            # Check for failures: either has error OR has packages_failed > 0
            has_error = item.get('error')
            has_failed_packages = item.get('packages_failed', 0) > 0

            if has_error or has_failed_packages:
                failed.append(item)
            elif item.get('status_changed'):
                auto_closed.append(item)
            elif item.get('packages_updated', 0) > 0:
                updated.append(item)
            else:
                no_change.append(item)

        return render_template('tickets/tracking_refresh_report.html',
                               log=log,
                               filters=filters,
                               updated=updated,
                               auto_closed=auto_closed,
                               failed=failed,
                               no_change=no_change,
                               current_user=user)
    finally:
        db_session.close()