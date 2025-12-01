from flask import Blueprint, render_template, redirect, url_for, session, request, flash, jsonify
from utils.auth_decorators import login_required, admin_required
from utils.store_instances import (
    user_store, activity_store, ticket_store, 
    inventory_store, queue_store
)
from utils.ticket_import_store import ticket_import_store
import logging

# Set up logging for this module
logger = logging.getLogger(__name__)
from utils.db_manager import DatabaseManager
from models.company import Company
from models.ticket import Ticket, TicketCategory, TicketStatus
import os
from werkzeug.utils import secure_filename
from models.asset import Asset, AssetStatus
from models.accessory import Accessory
from models.customer_user import CustomerUser
from models.user import UserType, User
from sqlalchemy import func, or_
from models.activity import Activity
from models.permission import Permission
from models.audit_session import AuditSession
from database import SessionLocal
from sqlalchemy.orm import Session
from flask_login import current_user

main_bp = Blueprint('main', __name__)
db_manager = DatabaseManager()

# Configure upload settings for dashboard
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'xlsx', 'xls', 'csv'}

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@main_bp.route('/debug-permissions-page')
@login_required
def debug_permissions_page():
    """Debug page to check permissions for the current user"""
    return render_template('debug_permissions.html')

@main_bp.route('/debug-permissions')
@login_required
def debug_permissions():
    """Debug route to check permissions for the current user"""
    user_permissions = {}
    
    if not current_user or not current_user.is_authenticated:
        return jsonify({
            "error": "User not authenticated",
            "user": None,
            "permissions": None
        })
        
    # Get user info
    user_info = {
        "id": current_user.id,
        "username": current_user.username,
        "user_type": current_user.user_type.value if current_user.user_type else None,
        "is_admin": current_user.is_admin,
        "is_supervisor": current_user.is_supervisor,
    }
    
    # Get permissions
    try:
        permissions = current_user.permissions
        if permissions:
            for attr in dir(permissions):
                if attr.startswith('can_') and not callable(getattr(permissions, attr)):
                    user_permissions[attr] = getattr(permissions, attr)
    except Exception as e:
        return jsonify({
            "error": str(e),
            "user": user_info,
            "permissions": None
        })
    
    return jsonify({
        "user": user_info,
        "permissions": user_permissions
    })

@main_bp.route('/', methods=['GET', 'POST'])
@login_required
def index():
    user_id = session['user_id']
    # Create a session for this request to avoid concurrency issues with shared db_manager
    db_session = db_manager.get_session()
    try:
        user = db_manager.get_user(user_id)

        if not user:
            session.clear()
            return redirect(url_for('auth.login'))

        # Check if user should see the new customizable dashboard
        # Skip redirect for POST requests (file uploads) and if use_classic is set
        if request.method == 'GET' and not request.args.get('use_classic'):
            # Check if user explicitly wants classic mode
            if not session.get('use_classic_home'):
                should_use_new_dashboard = False

                # Check system setting for default homepage
                try:
                    from models.system_settings import SystemSettings
                    db_session = SessionLocal()
                    try:
                        # Get homepage preference setting
                        homepage_setting = db_session.query(SystemSettings).filter_by(
                            setting_key='default_homepage'
                        ).first()

                        if homepage_setting:
                            setting_value = homepage_setting.get_value()
                            if setting_value == 'new':
                                should_use_new_dashboard = True
                            elif setting_value == 'classic':
                                should_use_new_dashboard = False

                        # DEVELOPER users default to new dashboard unless system says classic
                        if user.user_type == UserType.DEVELOPER:
                            # Check if there's a user-specific preference
                            if user.preferences and 'use_new_dashboard' in user.preferences:
                                should_use_new_dashboard = user.preferences['use_new_dashboard']
                            elif not homepage_setting or homepage_setting.get_value() != 'classic':
                                should_use_new_dashboard = True

                        # Check user-specific preference (overrides system default for all users)
                        if user.preferences and 'use_new_dashboard' in user.preferences:
                            should_use_new_dashboard = user.preferences['use_new_dashboard']

                    finally:
                        db_session.close()
                except Exception as e:
                    logger.warning(f"Could not check dashboard preference: {str(e)}")

                if should_use_new_dashboard:
                    return redirect(url_for('dashboard.index'))

        # Clear the use_classic_home flag if use_classic query param is present
        if request.args.get('use_classic'):
            session['use_classic_home'] = True

        # Handle file upload if POST request
        if request.method == 'POST':
            import_type = request.form.get('import_type', 'asset')  # Default to asset import
            
            # Check permissions based on import type
            if import_type == 'asset' and user.user_type not in [UserType.SUPER_ADMIN, UserType.DEVELOPER, UserType.COUNTRY_ADMIN]:
                flash('You do not have permission to import assets')
                return redirect(url_for('main.index'))
            elif import_type == 'ticket' and user.user_type not in [UserType.SUPER_ADMIN, UserType.DEVELOPER, UserType.COUNTRY_ADMIN, UserType.SUPERVISOR]:
                flash('You do not have permission to import tickets')
                return redirect(url_for('main.index'))
            
            if 'file' not in request.files:
                flash('No file uploaded')
                return redirect(request.url)
            
            file = request.files['file']
            if file.filename == '':
                flash('No file selected')
                return redirect(request.url)
            
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                filepath = os.path.join(UPLOAD_FOLDER, filename)
                file.save(filepath)
                
                if import_type == 'asset':
                    # Handle asset import
                    if inventory_store.import_from_excel(filepath):
                        flash('Inventory imported successfully')
                        os.remove(filepath)
                    else:
                        flash('Error importing inventory')
                        os.remove(filepath)
                elif import_type == 'ticket':
                    # Handle ticket import - redirect to preview
                    return redirect(url_for('main.preview_ticket_import', filename=filename))
                    
                return redirect(url_for('main.index'))
            else:
                flash('Invalid file type. Please upload an Excel file (.xlsx, .xls) or CSV file (.csv)')
                return redirect(request.url)

        # Get queues with filtering based on user permissions
        if user.user_type in [UserType.SUPER_ADMIN, UserType.DEVELOPER]:
            # Super admins and developers can see all queues
            queues = queue_store.get_all_queues()
        else:
            # For all other user types, filter queues based on company permissions
            queues = []
            all_queues = queue_store.get_all_queues()
            for queue in all_queues:
                if user.can_access_queue(queue.id):
                    queues.append(queue)

        # Get counts from database
        # For queue cards, show ALL tickets in the queue regardless of country/company
        # since queue permissions already control which queues the user can see
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
        
        # Apply filtering to asset counts for COUNTRY_ADMIN and SUPERVISOR
        if user.user_type in [UserType.COUNTRY_ADMIN, UserType.SUPERVISOR]:
            from models.user_company_permission import UserCompanyPermission
            asset_query = db_session.query(Asset)

            # Filter by assigned countries
            if user.assigned_countries:
                asset_query = asset_query.filter(Asset.country.in_(user.assigned_countries))

            # Filter by company permissions (same logic as inventory page)
            company_permissions = db_session.query(UserCompanyPermission).filter_by(
                user_id=user.id,
                can_view=True
            ).all()

            if company_permissions:
                permitted_company_ids = [perm.company_id for perm in company_permissions]
                permitted_companies = db_session.query(Company).filter(Company.id.in_(permitted_company_ids)).all()
                permitted_company_names = [c.name.strip() for c in permitted_companies]

                # Include child companies of parent companies
                all_company_names = list(permitted_company_names)
                for company in permitted_companies:
                    if company.is_parent_company or company.child_companies.count() > 0:
                        child_names = [c.name.strip() for c in company.child_companies.all()]
                        all_company_names.extend(child_names)

                # Filter by company_id OR customer name
                name_conditions = [func.lower(Asset.customer).like(f"%{name.lower()}%") for name in all_company_names]
                asset_query = asset_query.filter(
                    or_(
                        Asset.company_id.in_(permitted_company_ids),
                        *name_conditions
                    )
                )
                tech_assets_count = asset_query.count()
            else:
                # No company permissions - show 0
                tech_assets_count = 0
        else:
            tech_assets_count = db_session.query(Asset).count()
        
        accessories_count = db_session.query(func.sum(Accessory.total_quantity)).scalar() or 0
        total_inventory = tech_assets_count + accessories_count
        
        # Apply filtering to customer counts for COUNTRY_ADMIN
        if user.user_type == UserType.COUNTRY_ADMIN and user.company_id:
            total_customers = db_session.query(CustomerUser).filter(
                CustomerUser.company_id == user.company_id
            ).count()
        else:
            total_customers = db_session.query(CustomerUser).count()
        
        # Apply filtering to total tickets for COUNTRY_ADMIN
        if user.user_type == UserType.COUNTRY_ADMIN:
            total_ticket_query = db_session.query(Ticket)
            if user.assigned_countries:
                total_ticket_query = total_ticket_query.filter(Ticket.country.in_(user.assigned_countries))
            if user.company_id:
                total_ticket_query = total_ticket_query.filter(
                    or_(
                        Ticket.requester_id.in_(
                            db_session.query(User.id).filter(User.company_id == user.company_id)
                        ),
                        Ticket.assigned_to_id.in_(
                            db_session.query(User.id).filter(User.company_id == user.company_id)
                        ),
                        Ticket.subject.in_(
                            db_session.query(Asset.asset_tag).filter(Asset.company_id == user.company_id)
                        )
                    )
                )
            total_tickets = total_ticket_query.count()
        else:
            total_tickets = db_session.query(Ticket).count()
        
        # Get shipment tickets with filtering for COUNTRY_ADMIN
        shipment_tickets = []
        # Only load shipment tickets for non-CLIENT users
        if user.user_type != UserType.CLIENT:
            shipment_query = db_session.query(Ticket).filter(
                Ticket.category.in_([
                    TicketCategory.ASSET_CHECKOUT,
                    TicketCategory.ASSET_CHECKOUT_SINGPOST,
                    TicketCategory.ASSET_CHECKOUT_DHL,
                    TicketCategory.ASSET_CHECKOUT_UPS,
                    TicketCategory.ASSET_CHECKOUT_BLUEDART,
                    TicketCategory.ASSET_CHECKOUT_DTDC,
                    TicketCategory.ASSET_CHECKOUT_AUTO,
                    TicketCategory.ASSET_CHECKOUT_CLAW,
                    TicketCategory.ASSET_RETURN_CLAW
                ])
            )
            
            # Apply COUNTRY_ADMIN filtering to shipment tickets
            if user.user_type == UserType.COUNTRY_ADMIN:
                if user.assigned_countries:
                    shipment_query = shipment_query.filter(Ticket.country.in_(user.assigned_countries))
                if user.company_id:
                    shipment_query = shipment_query.filter(
                        or_(
                            Ticket.requester_id.in_(
                                db_session.query(User.id).filter(User.company_id == user.company_id)
                            ),
                            Ticket.assigned_to_id.in_(
                                db_session.query(User.id).filter(User.company_id == user.company_id)
                            ),
                            Ticket.subject.in_(
                                db_session.query(Asset.asset_tag).filter(Asset.company_id == user.company_id)
                            )
                        )
                    )
            
            shipment_tickets = shipment_query.order_by(Ticket.created_at.desc()).all()

        # Calculate summary statistics
        stats = {
            'total_inventory': total_inventory,
            'total_shipments': total_tickets,  # Using total_tickets instead of shipments
            'total_queues': len(queues),
            'total_customers': total_customers
        }

        # Get activities
        activities = activity_store.get_user_activities(user_id)

        # Get user activities
        user_activities = []
        if 'user_id' in session:
            user_id = session['user_id']
            user_activities = activity_store.get_user_activities(user_id)
        
        # Get counts for dashboard with filtering for COUNTRY_ADMIN and SUPERVISOR
        if user.user_type in [UserType.COUNTRY_ADMIN, UserType.SUPERVISOR]:
            from models.user_company_permission import UserCompanyPermission
            asset_query = db_session.query(Asset)

            # Filter by assigned countries
            if user.assigned_countries:
                asset_query = asset_query.filter(Asset.country.in_(user.assigned_countries))

            # Filter by company permissions
            company_permissions = db_session.query(UserCompanyPermission).filter_by(
                user_id=user.id,
                can_view=True
            ).all()

            if company_permissions:
                permitted_company_ids = [perm.company_id for perm in company_permissions]
                permitted_companies = db_session.query(Company).filter(Company.id.in_(permitted_company_ids)).all()
                permitted_company_names = [c.name.strip() for c in permitted_companies]

                # Include child companies of parent companies
                all_company_names = list(permitted_company_names)
                for company in permitted_companies:
                    if company.is_parent_company or company.child_companies.count() > 0:
                        child_names = [c.name.strip() for c in company.child_companies.all()]
                        all_company_names.extend(child_names)

                # Filter by company_id OR customer name
                name_conditions = [func.lower(Asset.customer).like(f"%{name.lower()}%") for name in all_company_names]
                asset_query = asset_query.filter(
                    or_(
                        Asset.company_id.in_(permitted_company_ids),
                        *name_conditions
                    )
                )

                total_assets = asset_query.count()
                deployed_assets = db_session.query(Asset).filter(
                    Asset.status == AssetStatus.DEPLOYED,
                    or_(Asset.company_id.in_(permitted_company_ids), *name_conditions)
                ).count()
                in_stock_assets = db_session.query(Asset).filter(
                    Asset.status == AssetStatus.IN_STOCK,
                    or_(Asset.company_id.in_(permitted_company_ids), *name_conditions)
                ).count()
            else:
                total_assets = 0
                deployed_assets = 0
                in_stock_assets = 0
        else:
            total_assets = db_session.query(Asset).count()
            deployed_assets = db_session.query(Asset).filter(Asset.status == AssetStatus.DEPLOYED).count()
            in_stock_assets = db_session.query(Asset).filter(Asset.status == AssetStatus.IN_STOCK).count()
        
        # Accessory counts
        total_accessories = db_session.query(Accessory).count()
        
        # Ticket counts with filtering for COUNTRY_ADMIN
        if user.user_type == UserType.COUNTRY_ADMIN:
            open_ticket_query = db_session.query(Ticket).filter(
                Ticket.status != TicketStatus.RESOLVED,
                Ticket.status != TicketStatus.RESOLVED_DELIVERED
            )
            resolved_ticket_query = db_session.query(Ticket).filter(
                Ticket.status.in_([TicketStatus.RESOLVED, TicketStatus.RESOLVED_DELIVERED])
            )
            
            if user.assigned_countries:
                open_ticket_query = open_ticket_query.filter(Ticket.country.in_(user.assigned_countries))
                resolved_ticket_query = resolved_ticket_query.filter(Ticket.country.in_(user.assigned_countries))
                
            if user.company_id:
                company_filter = or_(
                    Ticket.requester_id.in_(
                        db_session.query(User.id).filter(User.company_id == user.company_id)
                    ),
                    Ticket.assigned_to_id.in_(
                        db_session.query(User.id).filter(User.company_id == user.company_id)
                    ),
                    Ticket.subject.in_(
                        db_session.query(Asset.asset_tag).filter(Asset.company_id == user.company_id)
                    )
                )
                open_ticket_query = open_ticket_query.filter(company_filter)
                resolved_ticket_query = resolved_ticket_query.filter(company_filter)
            
            open_tickets = open_ticket_query.count()
            resolved_tickets = resolved_ticket_query.count()
        else:
            open_tickets = db_session.query(Ticket).filter(
                Ticket.status != TicketStatus.RESOLVED,
                Ticket.status != TicketStatus.RESOLVED_DELIVERED
            ).count()
            resolved_tickets = db_session.query(Ticket).filter(
                Ticket.status.in_([TicketStatus.RESOLVED, TicketStatus.RESOLVED_DELIVERED])
            ).count()
        
        # Get the 5 most recent activities for all users (no filtering needed here)
        recent_activities = db_session.query(Activity).order_by(
            Activity.created_at.desc()
        ).limit(5).all()
        
        # Get user count (no filtering needed)
        user_count = db_session.query(User).count()
        
        # Get ticket counts
        ticket_counts = {
            'total': total_tickets,
            'open': open_tickets,
            'resolved': resolved_tickets
        }

        # Check for active audit session
        current_audit = None
        if user.permissions and user.permissions.can_access_inventory_audit:
            current_audit = db_session.query(AuditSession).filter(
                AuditSession.is_active == True
            ).first()

        # Check system setting for queue cards visibility on dashboard
        # Always show for COUNTRY_ADMIN users, otherwise check system setting
        show_queue_cards = False
        if user.user_type == UserType.COUNTRY_ADMIN:
            show_queue_cards = True
        else:
            try:
                from models.system_settings import SystemSettings
                setting = db_session.query(SystemSettings).filter_by(setting_key='show_queue_cards').first()
                if setting:
                    show_queue_cards = setting.get_value()
            except Exception as e:
                logging.warning(f"Could not load show_queue_cards setting: {str(e)}")

        # Calculate weekly ticket data (Monday to Friday)
        from datetime import datetime, timedelta
        weekly_ticket_data = []

        # Get current week's Monday
        today = datetime.now()
        weekday = today.weekday()  # 0 = Monday, 6 = Sunday
        monday = today - timedelta(days=weekday)

        # Get ticket counts for Monday through Friday
        for i in range(5):  # 0-4 for Mon-Fri
            day = monday + timedelta(days=i)
            day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
            day_end = day.replace(hour=23, minute=59, second=59, microsecond=999999)

            # Query tickets created on this day
            day_query = db_session.query(Ticket).filter(
                Ticket.created_at >= day_start,
                Ticket.created_at <= day_end
            )

            # Apply same filtering as other ticket queries for COUNTRY_ADMIN
            if user.user_type == UserType.COUNTRY_ADMIN:
                if user.assigned_countries:
                    day_query = day_query.filter(Ticket.country.in_(user.assigned_countries))
                if user.company_id:
                    day_query = day_query.filter(
                        or_(
                            Ticket.requester_id.in_(
                                db_session.query(User.id).filter(User.company_id == user.company_id)
                            ),
                            Ticket.assigned_to_id.in_(
                                db_session.query(User.id).filter(User.company_id == user.company_id)
                            ),
                            Ticket.subject.in_(
                                db_session.query(Asset.asset_tag).filter(Asset.company_id == user.company_id)
                            )
                        )
                    )

            count = day_query.count()
            weekly_ticket_data.append({
                'day': day.strftime('%a'),  # Mon, Tue, Wed, Thu, Fri
                'date': day.strftime('%m/%d'),
                'full_date': day.strftime('%Y-%m-%d'),  # For URL filtering
                'count': count
            })

        return render_template('home.html',
            queues=queues,
            queue_ticket_counts=queue_ticket_counts,
            stats=stats,
            activities=activities,
            user=user,
            singpost_tickets=shipment_tickets,
            user_activities=user_activities,
            total_assets=total_assets,
            deployed_assets=deployed_assets,
            in_stock_assets=in_stock_assets,
            total_accessories=total_accessories,
            open_tickets=open_tickets,
            recent_activities=recent_activities,
            user_count=user_count,
            ticket_counts=ticket_counts,
            current_audit=current_audit,
            show_queue_cards=show_queue_cards,
            weekly_ticket_data=weekly_ticket_data
        )
    except Exception as e:
        logging.error(f"Error in index route: {str(e)}", exc_info=True)
        flash('An error occurred while loading the dashboard')
        return redirect(url_for('auth.login'))
    finally:
        db_session.close()

@main_bp.route('/refresh-supervisor-permissions')
def refresh_supervisor_permissions():
    """Force refresh permissions for all supervisor users"""
    try:
        # Get a database session
        db_session = SessionLocal()
        
        try:
            # Get the permission record for supervisors
            supervisor_permission = db_session.query(Permission).filter_by(
                user_type=UserType.SUPERVISOR
            ).first()
            
            # If no permission record exists, create one with default permissions
            if not supervisor_permission:
                default_permissions = Permission.get_default_permissions(UserType.SUPERVISOR)
                supervisor_permission = Permission(
                    user_type=UserType.SUPERVISOR, 
                    **default_permissions
                )
                db_session.add(supervisor_permission)
            else:
                # Update the existing permission with new defaults
                default_permissions = Permission.get_default_permissions(UserType.SUPERVISOR)
                for key, value in default_permissions.items():
                    setattr(supervisor_permission, key, value)
            
            # Commit the changes
            db_session.commit()
            
            # Return success
            return "Supervisor permissions updated successfully! Please log out and log back in to see the changes."
            
        finally:
            db_session.close()
            
    except Exception as e:
        return f"Error updating permissions: {str(e)}"

@main_bp.route('/fix-supervisor-permissions')
def fix_supervisor_permissions():
    """Force set can_edit_assets=True for supervisors directly in the database"""
    try:
        # Get a database session
        db_session = SessionLocal()
        
        try:
            # Get the permission record for supervisors
            supervisor_permission = db_session.query(Permission).filter_by(
                user_type=UserType.SUPERVISOR
            ).first()
            
            if not supervisor_permission:
                return "No supervisor permission record found."
            
            # Update the can_edit_assets permission
            supervisor_permission.can_edit_assets = True
            
            # Commit the changes
            db_session.commit()
            
            # Return success
            return "Successfully set can_edit_assets=True for supervisors!"
            
        finally:
            db_session.close()
            
    except Exception as e:
        return f"Error updating permissions: {str(e)}"

@main_bp.route('/debug-user-company-permissions/<int:user_id>')
def debug_user_company_permissions(user_id):
    """Debug route to check UserCompanyPermission for a user"""
    from models.user_company_permission import UserCompanyPermission
    db_session = SessionLocal()
    try:
        user = db_session.query(User).get(user_id)
        if not user:
            return f"User {user_id} not found"

        perms = db_session.query(UserCompanyPermission).filter_by(user_id=user_id).all()

        result = f"<h2>User: {user.username} ({user.email})</h2>"
        result += f"<p>User Type: {user.user_type.value}</p>"
        result += f"<p>Company ID: {user.company_id}</p>"
        result += f"<p>Assigned Countries: {user.assigned_countries}</p>"
        result += f"<h3>UserCompanyPermission records ({len(perms)}):</h3>"

        if perms:
            result += "<ul>"
            for p in perms:
                company = db_session.query(Company).get(p.company_id)
                company_name = company.name if company else "Unknown"
                result += f"<li>Company ID: {p.company_id} ({company_name}) - can_view: {p.can_view}</li>"
            result += "</ul>"
        else:
            result += "<p style='color:red'>NO COMPANY PERMISSIONS - This user will see 0 assets!</p>"
            result += f"<p><a href='/fix-user-company-permissions/{user_id}' style='color:blue;font-weight:bold'>Click here to auto-fix</a></p>"

        return result
    finally:
        db_session.close()

@main_bp.route('/fix-user-company-permissions/<int:user_id>')
def fix_user_company_permissions(user_id):
    """Auto-fix missing UserCompanyPermission for a SUPERVISOR/COUNTRY_ADMIN"""
    from models.user_company_permission import UserCompanyPermission
    db_session = SessionLocal()
    try:
        user = db_session.query(User).get(user_id)
        if not user:
            return f"User {user_id} not found"

        if user.user_type not in [UserType.SUPERVISOR, UserType.COUNTRY_ADMIN]:
            return f"User {user.username} is not a SUPERVISOR or COUNTRY_ADMIN"

        # Check if user has a company_id but no permissions
        existing_perms = db_session.query(UserCompanyPermission).filter_by(user_id=user_id).all()

        if existing_perms:
            return f"User already has {len(existing_perms)} company permissions. No fix needed."

        if not user.company_id:
            return f"User has no company_id assigned. Please edit user in Admin > User Management first."

        # Create permission for the user's company
        new_perm = UserCompanyPermission(
            user_id=user.id,
            company_id=user.company_id,
            can_view=True,
            can_edit=False,
            can_delete=False
        )
        db_session.add(new_perm)

        # Also add permissions for child companies if this is a parent company
        company = db_session.query(Company).get(user.company_id)
        added_companies = [company.name]

        if company and (company.is_parent_company or company.child_companies.count() > 0):
            for child in company.child_companies.all():
                child_perm = UserCompanyPermission(
                    user_id=user.id,
                    company_id=child.id,
                    can_view=True,
                    can_edit=False,
                    can_delete=False
                )
                db_session.add(child_perm)
                added_companies.append(child.name)

        db_session.commit()

        return f"Fixed! Added permissions for: {', '.join(added_companies)}. <a href='/inventory'>Go to Inventory</a>"
    except Exception as e:
        db_session.rollback()
        return f"Error: {str(e)}"
    finally:
        db_session.close()

@main_bp.route('/preview-ticket-import/<filename>')
@login_required
def preview_ticket_import(filename):
    """Preview tickets from CSV before importing"""
    user_id = session['user_id']
    try:
        with db_manager as db:
            user = db.get_user(user_id)
            
        if not user:
            session.clear()
            return redirect(url_for('auth.login'))
        
        # Check permissions
        if user.user_type not in [UserType.SUPER_ADMIN, UserType.DEVELOPER, UserType.COUNTRY_ADMIN, UserType.SUPERVISOR]:
            flash('You do not have permission to import tickets')
            return redirect(url_for('main.index'))

        # Get preview data
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        if not os.path.exists(filepath):
            flash('Upload file not found')
            return redirect(url_for('main.index'))
        
        preview_data = ticket_import_store.preview_tickets_from_csv(filepath)
        
        if not preview_data['success']:
            flash(f'Error previewing tickets: {preview_data["error"]}')
            os.remove(filepath)
            return redirect(url_for('main.index'))
        
        return render_template('ticket_import_preview.html', 
                             preview_data=preview_data, 
                             filename=filename,
                             user=user)
        
    except Exception as e:
        logger.error(f"Error in preview_ticket_import: {str(e)}")
        flash('An error occurred while previewing tickets')
        return redirect(url_for('main.index'))

@main_bp.route('/import-tickets', methods=['POST'])
@login_required
def import_tickets():
    """Import tickets from CSV file"""
    user_id = session['user_id']
    try:
        with db_manager as db:
            user = db.get_user(user_id)
            
        if not user:
            session.clear()
            return redirect(url_for('auth.login'))
        
        # Check permissions
        if user.user_type not in [UserType.SUPER_ADMIN, UserType.DEVELOPER, UserType.COUNTRY_ADMIN, UserType.SUPERVISOR]:
            flash('You do not have permission to import tickets')
            return redirect(url_for('main.index'))

        filename = request.form.get('filename')
        if not filename:
            flash('No filename provided')
            return redirect(url_for('main.index'))
        
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        if not os.path.exists(filepath):
            flash('Upload file not found')
            return redirect(url_for('main.index'))
        
        # Import tickets
        import_result = ticket_import_store.import_tickets_from_csv(filepath, user_id)
        
        # Clean up file
        os.remove(filepath)
        
        if import_result['success']:
            message_parts = [f'Successfully imported {import_result["imported_count"]} tickets to {import_result["queue_name"]} queue']
            
            if import_result.get('skipped_processing_count', 0) > 0:
                message_parts.append(f'{import_result["skipped_processing_count"]} tickets skipped (PROCESSING status)')
            
            if import_result.get('skipped_duplicates_count', 0) > 0:
                message_parts.append(f'{import_result["skipped_duplicates_count"]} tickets skipped (duplicate order IDs)')
            
            flash('. '.join(message_parts))
        else:
            flash(f'Error importing tickets: {import_result["error"]}')
        
        return redirect(url_for('main.index'))
        
    except Exception as e:
        logger.error(f"Error in import_tickets: {str(e)}")
        flash('An error occurred while importing tickets')
        return redirect(url_for('main.index'))

@main_bp.route('/debug-supervisor-tickets')
@login_required
def debug_supervisor_tickets():
    """Debug route to check SUPERVISOR user tickets"""
    user_id = session['user_id']
    try:
        with db_manager as db:
            user = db.get_user(user_id)
            
        if not user:
            return jsonify({'error': 'User not found'})
        
        # Get database session
        db_session = db_manager.get_session()
        try:
            # Get all tickets where this user is requester
            requester_tickets = db_session.query(Ticket).filter(Ticket.requester_id == user_id).all()
            
            # Get all tickets where this user is assigned
            assigned_tickets = db_session.query(Ticket).filter(Ticket.assigned_to_id == user_id).all()
            
            # Get all tickets regardless of filter
            all_tickets = db_session.query(Ticket).all()
            
            # Get tickets using the store method
            store_tickets = ticket_store.get_user_tickets(user_id, user.user_type)
            
            # Get FirstBase New Orders queue
            from models.queue import Queue
            firstbase_queue = db_session.query(Queue).filter(Queue.name == 'FirstBase New Orders').first()
            firstbase_queue_id = firstbase_queue.id if firstbase_queue else None
            
            # Check queue access for FirstBase New Orders queue
            can_access_firstbase = user.can_access_queue(firstbase_queue_id) if firstbase_queue_id else False
            
            result = {
                'user_info': {
                    'id': user_id,
                    'username': user.username,
                    'user_type': user.user_type.value,
                    'is_supervisor': user.is_supervisor,
                    'is_super_admin': user.is_super_admin,
                    'company_id': user.company_id
                },
                'queue_info': {
                    'firstbase_queue_id': firstbase_queue_id,
                    'firstbase_queue_name': firstbase_queue.name if firstbase_queue else None,
                    'can_access_firstbase': can_access_firstbase
                },
                'ticket_counts': {
                    'requester_tickets': len(requester_tickets),
                    'assigned_tickets': len(assigned_tickets),
                    'all_tickets': len(all_tickets),
                    'store_tickets': len(store_tickets)
                },
                'requester_tickets': [
                    {
                        'id': t.id,
                        'subject': t.subject,
                        'requester_id': t.requester_id,
                        'assigned_to_id': t.assigned_to_id,
                        'queue_id': t.queue_id,
                        'queue_name': t.queue.name if t.queue else None,
                        'created_at': t.created_at.isoformat() if t.created_at else None
                    } for t in requester_tickets[:5]  # Show first 5
                ],
                'store_tickets': [
                    {
                        'id': t.id,
                        'subject': t.subject,
                        'requester_id': t.requester_id,
                        'assigned_to_id': t.assigned_to_id,
                        'queue_id': t.queue_id,
                        'queue_name': t.queue.name if t.queue else None,
                        'created_at': t.created_at.isoformat() if t.created_at else None
                    } for t in store_tickets[:5]  # Show first 5
                ]
            }
            
            return jsonify(result)
            
        finally:
            db_session.close()
            
    except Exception as e:
        logger.error(f"Error in debug_supervisor_tickets: {str(e)}")
        return jsonify({'error': str(e)})

@main_bp.route('/api/customers/search')
@login_required
def search_customers():
    """Customer search endpoint for ticket creation form"""
    db_session = db_manager.get_session()
    try:
        search_term = request.args.get('q', '').strip()
        
        # Get current user and apply company filtering
        user = db_session.query(User).get(session['user_id'])
        if not user:
            return jsonify([]), 401
            
        customers_query = db_session.query(CustomerUser)
        
        # Apply the same filtering logic as get_filtered_customers
        from models.company_customer_permission import CompanyCustomerPermission
        
        # SUPER_ADMIN users can see all customers
        if user.user_type != UserType.SUPER_ADMIN:
            # For other users, apply permission-based filtering
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
        
        # Apply search filter if provided
        if search_term:
            search_filter = or_(
                CustomerUser.name.ilike(f'%{search_term}%'),
                CustomerUser.email.ilike(f'%{search_term}%'),
                CustomerUser.contact_number.ilike(f'%{search_term}%'),
                CustomerUser.address.ilike(f'%{search_term}%')
            )
            customers_query = customers_query.filter(search_filter)
        
        # Get results with limit for performance
        customers = customers_query.order_by(CustomerUser.name).limit(50).all()
        
        # Format response for Select2 frontend
        results = []
        for customer in customers:
            # Create display text combining name and company
            display_text = customer.name
            if customer.company:
                display_text += f" ({customer.company.name})"
            
            results.append({
                'id': customer.id,
                'text': display_text,  # This is what Select2 displays
                'name': customer.name,
                'email': customer.email,
                'company': customer.company.name if customer.company else None,
                'address': customer.address,
                'contact_number': customer.contact_number
            })
        
        return jsonify(results)
        
    except Exception as e:
        logger.error(f"Customer search error: {str(e)}")
        return jsonify([]), 500
    finally:
        db_session.close()