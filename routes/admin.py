from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash, current_app, session, send_file
from flask_login import current_user
from flask_wtf.csrf import CSRFProtect
from utils.auth_decorators import admin_required, super_admin_required, login_required
import logging
from utils.snipeit_client import SnipeITClient
from utils.db_manager import DatabaseManager
from models.user import User, UserType, Country
from models.permission import Permission
from datetime import datetime
from models.company import Company
from models.queue import Queue
from models.company_queue_permission import CompanyQueuePermission
from models.user_queue_permission import UserQueuePermission
from utils.email_sender import send_welcome_email
from sqlalchemy import or_, func, and_
import os
import shutil
import glob
from werkzeug.utils import secure_filename
import uuid
from werkzeug.security import generate_password_hash
from utils.auth import safe_generate_password_hash
from database import SessionLocal
from models.activity import Activity
from models.asset_history import AssetHistory
from models.accessory_history import AccessoryHistory
import traceback
from models.firecrawl_key import FirecrawlKey
from models.ticket_category_config import TicketCategoryConfig, CategoryDisplayConfig
import tempfile
import sqlite3
import subprocess
import pandas as pd
import csv
import io
import json
from models.ticket import Ticket, TicketStatus, TicketPriority, TicketCategory
from models.customer_user import CustomerUser
from models.asset import Asset
from sqlalchemy import text
from models.accessory import Accessory
from models.company_customer_permission import CompanyCustomerPermission

admin_bp = Blueprint('admin', __name__)
snipe_client = SnipeITClient()
db_manager = DatabaseManager()
csrf = CSRFProtect()

# Set up logging for this module
logger = logging.getLogger(__name__)

def cleanup_old_csv_files():
    """Clean up old CSV temporary files (older than 1 hour)"""
    try:
        import glob
        import time
        temp_dir = tempfile.gettempdir()
        pattern = os.path.join(temp_dir, 'csv_import_*.json')
        current_time = time.time()
        
        for filepath in glob.glob(pattern):
            file_age = current_time - os.path.getmtime(filepath)
            if file_age > 3600:  # 1 hour
                try:
                    os.remove(filepath)
                    logger.info(f"DEBUG: Cleaned up old CSV file: {filepath}")
                except Exception as e:
                    logger.info(f"DEBUG: Failed to cleanup {filepath}: {e}")
    except Exception as e:
        logger.info(f"DEBUG: CSV cleanup error: {e}")

def allowed_file(filename):
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_company_logo(file):
    if file and allowed_file(file.filename):
        # Generate a unique filename
        filename = str(uuid.uuid4()) + os.path.splitext(file.filename)[1]
        file.save(os.path.join('static/company_logos', filename))
        return filename
    return None

@admin_bp.route('/permission-management')
@admin_required
def permission_management():
    """Manage user type permissions"""
    if 'user_id' not in session:
        flash('Please log in to continue', 'error')
        return redirect(url_for('auth.login'))

    db_session = db_manager.get_session()
    try:
        # Get current user
        user = db_manager.get_user(session['user_id'])
        if not user:
            session.clear()
            return redirect(url_for('auth.login'))

        # Get all permissions
        permissions = db_session.query(Permission).all()
        
        # Check for duplicate permissions and remove them
        user_types_seen = set()
        duplicates_found = False
        
        for permission in permissions[:]:  # Use a copy of the list to avoid modification issues
            if permission.user_type in user_types_seen:
                # This is a duplicate
                duplicates_found = True
                db_session.delete(permission)
            else:
                user_types_seen.add(permission.user_type)
        
        if duplicates_found:
            db_session.commit()
            permissions = db_session.query(Permission).all()  # Refresh the list
        
        # Initialize default permissions if needed
        existing_types = {p.user_type for p in permissions}
        missing_types = [user_type for user_type in UserType if user_type not in existing_types]
        
        if missing_types:
            for user_type in missing_types:
                default_permissions = Permission.get_default_permissions(user_type)
                permission = Permission(user_type=user_type, **default_permissions)
                db_session.add(permission)
            db_session.commit()
            permissions = db_session.query(Permission).all()

        return render_template('admin/permission_management.html', 
                             permissions=permissions,
                             user=user,
                             UserType=UserType)
    except Exception as e:
        db_session.rollback()
        flash(f'Error loading permissions: {str(e)}', 'error')
        return redirect(url_for('main.index'))
    finally:
        db_session.close()

@admin_bp.route('/companies')
@admin_required
def manage_companies():
    """List all companies - only show parent companies and standalone companies"""
    from sqlalchemy import func
    from database import engine
    from sqlalchemy.orm import Session

    session = Session(engine)
    try:
        # Get all companies that are either:
        # 1. Parent companies (is_parent_company = True OR have child companies)
        # 2. Standalone companies (parent_company_id is NULL and is_parent_company = False)

        # First, get all parent/standalone companies
        parent_companies = session.query(Company).filter(
            Company.parent_company_id.is_(None)  # Only show companies that are not children
        ).order_by(Company.name).all()

        # For each company, count its children
        for company in parent_companies:
            # Count child companies for this parent
            child_count = session.query(Company).filter(
                Company.parent_company_id == company.id
            ).count()
            company.child_count = child_count

        return render_template('admin/companies/list.html', companies=parent_companies)
    finally:
        session.close()

@admin_bp.route('/companies/create', methods=['GET', 'POST'])
@admin_required
def create_company():
    """Create a new company"""
    if request.method == 'POST':
        name = request.form.get('name')
        contact_name = request.form.get('contact_name')
        contact_email = request.form.get('contact_email')
        address = request.form.get('address')
        
        # Handle logo upload
        logo_path = None
        if 'logo' in request.files:
            logo_file = request.files['logo']
            logo_path = save_company_logo(logo_file)

        try:
            company = Company(
                name=name,
                contact_name=contact_name,
                contact_email=contact_email,
                address=address,
                logo_path=logo_path
            )
            db_session = db_manager.get_session()
            db_session.add(company)
            db_session.commit()
            flash('Company created successfully', 'success')
            return redirect(url_for('admin.manage_companies'))
        except Exception as e:
            flash(f'Error creating company: {str(e)}', 'error')
            return redirect(url_for('admin.create_company'))

    return render_template('admin/create_company.html')

@admin_bp.route('/companies/<int:company_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_company(company_id):
    """Edit an existing company"""
    db_session = db_manager.get_session()
    company = db_session.query(Company).get(company_id)
    
    if not company:
        flash('Company not found', 'error')
        return redirect(url_for('admin.manage_companies'))

    if request.method == 'POST':
        company.name = request.form.get('name')
        company.contact_name = request.form.get('contact_name')
        company.contact_email = request.form.get('contact_email')
        company.address = request.form.get('address')
        
        # Handle logo upload
        if 'logo' in request.files:
            logo_file = request.files['logo']
            if logo_file.filename:
                # Delete old logo if it exists
                if company.logo_path:
                    old_logo_path = os.path.join('static/company_logos', company.logo_path)
                    if os.path.exists(old_logo_path):
                        os.remove(old_logo_path)
                
                # Save new logo
                logo_path = save_company_logo(logo_file)
                if logo_path:
                    company.logo_path = logo_path

        try:
            db_session.commit()
            flash('Company updated successfully', 'success')
            return redirect(url_for('admin.manage_companies'))
        except Exception as e:
            db_session.rollback()
            flash(f'Error updating company: {str(e)}', 'error')
    
    return render_template('admin/create_company.html', company=company)

@admin_bp.route('/companies/<int:company_id>/delete', methods=['POST'])
@admin_required
def delete_company(company_id):
    """Delete a company"""
    logger.info("DEBUG: Delete company request received for company_id={company_id}")
    
    db_session = db_manager.get_session()
    try:
        # Check if company exists
        company = db_session.query(Company).get(company_id)
        if not company:
            logger.info("DEBUG: Company with ID {company_id} not found")
            flash('Company not found', 'error')
            return redirect(url_for('admin.manage_companies'))
        
        # Check if company has associated users
        users_count = db_session.query(User).filter_by(company_id=company_id).count()
        if users_count > 0:
            logger.info("DEBUG: Cannot delete company - it has {users_count} associated users")
            flash(f'Cannot delete company: It has {users_count} associated users. Please reassign or delete the users first.', 'error')
            return redirect(url_for('admin.manage_companies'))
        
        # First delete all related company queue permissions
        logger.info("DEBUG: Deleting queue permissions for company_id={company_id}")
        deleted_permissions = db_session.query(CompanyQueuePermission).filter_by(company_id=company_id).delete()
        logger.info("DEBUG: Deleted {deleted_permissions} queue permissions")
        
        # Then delete the company
        logger.info("DEBUG: Deleting company: {company.name} (ID: {company.id})")
        db_session.delete(company)
        db_session.commit()
        flash('Company deleted successfully', 'success')
        return redirect(url_for('admin.manage_companies'))
    
    except Exception as e:
        db_session.rollback()
        logger.info("DEBUG: Error deleting company: {str(e)}")
        logger.info("DEBUG: {traceback.format_exc()}")
        flash(f'Error deleting company: {str(e)}', 'error')
        return redirect(url_for('admin.manage_companies'))
    
    finally:
        db_session.close()

@admin_bp.route('/users')
@admin_required
def manage_users():
    from flask import request
    show_deleted = request.args.get('show_deleted', 'false').lower() == 'true'
    users = db_manager.get_all_users(include_deleted=show_deleted)
    return render_template('admin/users.html', users=users, show_deleted=show_deleted)


@admin_bp.route('/api/users/<int:user_id>/quick-details')
@admin_required
def get_user_quick_details(user_id):
    """API endpoint to get user details for expandable row view"""
    from models.queue import Queue
    from models.company_queue_permission import CompanyQueuePermission
    from models.user_company_permission import UserCompanyPermission
    from models.user_country_permission import UserCountryPermission
    from models.group import Group
    from models.group_membership import GroupMembership

    db_session = db_manager.get_session()
    try:
        user = db_session.query(User).get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404

        # Get permission flags for user's type
        permission = db_session.query(Permission).filter_by(user_type=user.user_type).first()

        # Get company permissions with parent info
        company_permissions = db_session.query(UserCompanyPermission).filter_by(user_id=user.id).all()
        companies = []
        for perm in company_permissions:
            company = db_session.query(Company).get(perm.company_id)
            if company:
                company_info = {
                    'name': company.name,
                    'parent': company.parent_company.name if company.parent_company else None
                }
                companies.append(company_info)

        # Get country permissions
        country_permissions = db_session.query(UserCountryPermission).filter_by(user_id=user.id).all()
        countries = [cp.country for cp in country_permissions]

        # Get queue access (per-user permissions)
        queues = []
        user_queue_perms = db_session.query(UserQueuePermission).filter_by(user_id=user.id).all()
        for perm in user_queue_perms:
            queue = db_session.query(Queue).get(perm.queue_id)
            if queue and perm.can_view:
                queues.append(queue.name)

        # Get group memberships
        group_memberships = db_session.query(GroupMembership).filter_by(user_id=user.id, is_active=True).all()
        groups = []
        for membership in group_memberships:
            group = db_session.query(Group).get(membership.group_id)
            if group and group.is_active:
                groups.append(group.name)

        # Get user's company
        user_company = db_session.query(Company).get(user.company_id) if user.company_id else None

        # Key permissions summary - expanded
        key_perms = {}
        if permission:
            key_perms = {
                'can_view_assets': permission.can_view_assets,
                'can_edit_assets': permission.can_edit_assets,
                'can_create_assets': permission.can_create_assets,
                'can_delete_assets': permission.can_delete_assets,
                'can_view_tickets': permission.can_view_tickets,
                'can_create_tickets': permission.can_create_tickets,
                'can_edit_tickets': permission.can_edit_tickets,
                'can_delete_tickets': permission.can_delete_tickets,
                'can_export_tickets': permission.can_export_tickets,
                'can_view_reports': permission.can_view_reports,
                'can_generate_reports': permission.can_generate_reports,
                'can_view_companies': permission.can_view_companies,
                'can_edit_companies': permission.can_edit_companies,
                'can_view_users': permission.can_view_users,
                'can_edit_users': permission.can_edit_users,
                'can_access_inventory_audit': permission.can_access_inventory_audit,
                'can_view_knowledge_base': permission.can_view_knowledge_base,
                'can_create_articles': permission.can_create_articles,
                'can_import_data': permission.can_import_data,
                'can_export_data': permission.can_export_data,
                'can_access_development': permission.can_access_development,
            }

        # Get last session info
        last_session = None
        try:
            from models.user_session import UserSession
            session_record = db_session.query(UserSession).filter_by(
                user_id=user.id
            ).order_by(UserSession.login_at.desc()).first()
            if session_record:
                last_session = {
                    'login_at': session_record.login_at.strftime('%Y-%m-%d %H:%M') if session_record.login_at else None,
                    'last_activity': session_record.last_activity_at.strftime('%Y-%m-%d %H:%M') if session_record.last_activity_at else None,
                    'device': session_record.device_type,
                    'browser': session_record.browser,
                    'is_active': session_record.is_active,
                    'pages_visited': session_record.pages_visited or 0,
                }
        except Exception:
            pass

        return jsonify({
            'success': True,
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'user_type': user.user_type.value if user.user_type else None,
                'company': user_company.name if user_company else None,
                'companies': companies,
                'countries': countries,
                'queues': queues,
                'groups': groups,
                'permissions': key_perms,
                'created_at': user.created_at.strftime('%Y-%m-%d') if user.created_at else None,
                'theme': user.theme_preference or 'default',
                'mention_filter': user.mention_filter_enabled,
                'last_session': last_session,
            }
        })
    finally:
        db_session.close()

@admin_bp.route('/api/users/<int:user_id>/countries', methods=['POST'])
@admin_required
def save_user_countries(user_id):
    """API endpoint to save user's country permissions"""
    from models.user_country_permission import UserCountryPermission

    db_session = db_manager.get_session()
    try:
        user = db_session.query(User).get(user_id)
        if not user:
            return jsonify({'success': False, 'error': 'User not found'}), 404

        data = request.get_json()
        countries = data.get('countries', [])

        # Delete existing country permissions
        db_session.query(UserCountryPermission).filter_by(user_id=user_id).delete()

        # Create new country permissions
        for country in countries:
            permission = UserCountryPermission(user_id=user_id, country=country)
            db_session.add(permission)

        db_session.commit()
        logger.info(f"Updated country permissions for user {user_id}: {len(countries)} countries")

        return jsonify({'success': True, 'count': len(countries)})
    except Exception as e:
        db_session.rollback()
        logger.error(f"Error saving country permissions: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db_session.close()

@admin_bp.route('/api/users/<int:user_id>/companies', methods=['POST'])
@admin_required
def save_user_companies(user_id):
    """API endpoint to save user's company permissions"""
    from models.user_company_permission import UserCompanyPermission

    db_session = db_manager.get_session()
    try:
        user = db_session.query(User).get(user_id)
        if not user:
            return jsonify({'success': False, 'error': 'User not found'}), 404

        data = request.get_json()
        company_ids = data.get('company_ids', [])

        # Remove duplicates while preserving order
        company_ids = list(dict.fromkeys(company_ids))

        # Delete existing company permissions
        db_session.query(UserCompanyPermission).filter_by(user_id=user_id).delete()

        # Create new company permissions
        for company_id in company_ids:
            permission = UserCompanyPermission(
                user_id=user_id,
                company_id=int(company_id),
                can_view=True,
                can_edit=False,
                can_delete=False
            )
            db_session.add(permission)

        # Update user's primary company_id to first selected company (for backwards compatibility)
        if company_ids:
            user.company_id = int(company_ids[0])

        db_session.commit()
        logger.info(f"Updated company permissions for user {user_id}: {len(company_ids)} companies")

        return jsonify({'success': True, 'count': len(company_ids)})
    except Exception as e:
        db_session.rollback()
        logger.error(f"Error saving company permissions: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db_session.close()

@admin_bp.route('/api/users/<int:user_id>/queues', methods=['POST'])
@admin_required
def save_user_queues(user_id):
    """API endpoint to save user's queue permissions (per-user, not per-company)"""
    from models.user_queue_permission import UserQueuePermission

    db_session = db_manager.get_session()
    try:
        user = db_session.query(User).get(user_id)
        if not user:
            return jsonify({'success': False, 'error': 'User not found'}), 404

        data = request.get_json()
        queue_ids = data.get('queue_ids', [])

        # Delete existing queue permissions for this user (not the whole company!)
        db_session.query(UserQueuePermission).filter_by(user_id=user.id).delete()

        # Create new queue permissions for this user
        for queue_id in queue_ids:
            permission = UserQueuePermission(
                user_id=user.id,
                queue_id=int(queue_id),
                can_view=True,
                can_create=True
            )
            db_session.add(permission)

        db_session.commit()
        logger.info(f"Updated queue permissions for user {user_id}: {len(queue_ids)} queues")

        return jsonify({'success': True, 'count': len(queue_ids)})
    except Exception as e:
        db_session.rollback()
        logger.error(f"Error saving queue permissions: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db_session.close()

@admin_bp.route('/api/users/<int:user_id>/mentions', methods=['POST'])
@admin_required
def save_user_mentions(user_id):
    """API endpoint to save user's mention settings"""
    from models.user_mention_permission import UserMentionPermission

    db_session = db_manager.get_session()
    try:
        user = db_session.query(User).get(user_id)
        if not user:
            return jsonify({'success': False, 'error': 'User not found'}), 404

        data = request.get_json()
        enabled = data.get('enabled', False)
        user_ids = data.get('user_ids', [])
        group_ids = data.get('group_ids', [])

        # Update mention filter enabled status
        user.mention_filter_enabled = enabled

        # Delete existing mention permissions
        db_session.query(UserMentionPermission).filter_by(user_id=user_id).delete()

        # Create new mention permissions if filtering is enabled
        if enabled:
            for uid in user_ids:
                permission = UserMentionPermission(
                    user_id=user_id,
                    target_type='user',
                    target_id=int(uid)
                )
                db_session.add(permission)

            for gid in group_ids:
                permission = UserMentionPermission(
                    user_id=user_id,
                    target_type='group',
                    target_id=int(gid)
                )
                db_session.add(permission)

        db_session.commit()
        logger.info(f"Updated mention settings for user {user_id}: enabled={enabled}, users={len(user_ids)}, groups={len(group_ids)}")

        return jsonify({'success': True, 'enabled': enabled, 'user_count': len(user_ids), 'group_count': len(group_ids)})
    except Exception as e:
        db_session.rollback()
        logger.error(f"Error saving mention settings: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db_session.close()

def _format_parent_companies(parent_companies):
    """Helper to format parent companies with their child companies"""
    return [
        {
            'id': c.id,
            'name': c.name,
            'child_companies': [{'id': child.id, 'name': child.name} for child in c.child_companies.all()]
        }
        for c in parent_companies
    ]

@admin_bp.route('/users/create', methods=['GET', 'POST'])
@admin_required
def create_user():
    """Create a new user"""
    from models.user import User, UserType, Country
    from models.queue import Queue
    from models.user_queue_permission import UserQueuePermission
    from models.user_company_permission import UserCompanyPermission
    from models.user_mention_permission import UserMentionPermission
    from models.group import Group

    db_session = db_manager.get_session()
    try:
        # Get all companies for CLIENT user type
        companies = db_session.query(Company).all()
        # Get only parent companies for COUNTRY_ADMIN filtering
        parent_companies = db_session.query(Company).filter(Company.is_parent_company == True).all()
        queues = db_session.query(Queue).all()

        # Get all users and groups for @mention settings
        all_users = db_session.query(User).filter(User.is_deleted == False).order_by(User.username).all()
        all_groups = db_session.query(Group).filter(Group.is_active == True).order_by(Group.name).all()

        # Get unique countries from assets for COUNTRY_ADMIN dropdown
        from models.asset import Asset
        asset_countries = db_session.query(Asset.country).filter(
            Asset.country.isnot(None),
            Asset.country != ''
        ).distinct().all()
        available_countries = sorted([c[0] for c in asset_countries if c[0]])

        if request.method == 'POST':
            username = request.form.get('username')
            email = request.form.get('email')
            password = request.form.get('password')
            company_id = request.form.get('company_id')
            user_type = request.form.get('user_type')
            assigned_countries = request.form.getlist('assigned_countries')  # Changed to getlist for multiple countries
            country_admin_company = request.form.get('country_admin_company')
            child_company_ids = request.form.getlist('child_company_ids')
            queue_ids = request.form.getlist('queue_ids')
            # @Mention settings
            mention_filter_enabled = request.form.get('mention_filter_enabled') == '1'
            mention_user_ids = request.form.getlist('mention_user_ids')
            mention_group_ids = request.form.getlist('mention_group_ids')

            # Check if user with this email already exists
            existing_user = db_session.query(User).filter_by(email=email).first()
            if existing_user:
                flash('A user with this email already exists. Please use a different email address.', 'error')
                companies_data = [{'id': c.id, 'name': c.name} for c in companies]
                parent_companies_data = _format_parent_companies(parent_companies)
                queues_data = [{'id': q.id, 'name': q.name} for q in queues]
                return render_template('admin/create_user.html', companies=companies_data, parent_companies=parent_companies_data, queues=queues_data, available_countries=available_countries, all_users=all_users, all_groups=all_groups)

            try:
                # Create user data dictionary
                user_data = {
                    'username': username,
                    'email': email,
                    'password_hash': safe_generate_password_hash(password),
                    'company_id': company_id if company_id else None,
                    'user_type': UserType[user_type],
                    'mention_filter_enabled': mention_filter_enabled if user_type in ['COUNTRY_ADMIN', 'SUPERVISOR'] else False
                }

                # Add assigned countries for Country Admin
                if user_type == 'COUNTRY_ADMIN':
                    if not assigned_countries:
                        flash('At least one country selection is required for Country Admin', 'error')
                        companies_data = [{'id': c.id, 'name': c.name} for c in companies]
                        parent_companies_data = _format_parent_companies(parent_companies)
                        queues_data = [{'id': q.id, 'name': q.name} for q in queues]
                        return render_template('admin/create_user.html', companies=companies_data, parent_companies=parent_companies_data, queues=queues_data, available_countries=available_countries, all_users=all_users, all_groups=all_groups)

                    logger.info(f"DEBUG: Assigned countries: {assigned_countries}")

                    # Set company for Country Admin (to filter assets by parent company)
                    if country_admin_company:
                        user_data['company_id'] = country_admin_company

                # Company is required for CLIENT users
                if user_type == 'CLIENT' and not company_id:
                    flash('Company selection is required for Client users', 'error')
                    companies_data = [{'id': c.id, 'name': c.name} for c in companies]
                    parent_companies_data = _format_parent_companies(parent_companies)
                    queues_data = [{'id': q.id, 'name': q.name} for q in queues]
                    return render_template('admin/create_user.html', companies=companies_data, parent_companies=parent_companies_data, queues=queues_data, available_countries=available_countries, all_users=all_users, all_groups=all_groups)

                user = User(**user_data)
                db_session.add(user)
                db_session.flush()  # Get the user ID before committing

                # Create country permissions for Country Admin/Supervisor
                if user_type in ['COUNTRY_ADMIN', 'SUPERVISOR'] and assigned_countries:
                    from models.user_country_permission import UserCountryPermission
                    for country in assigned_countries:
                        country_permission = UserCountryPermission(
                            user_id=user.id,
                            country=country
                        )
                        db_session.add(country_permission)
                        logger.info(f"DEBUG: Created country permission for {country}")

                # Create company permissions for Country Admin/Supervisor
                if user_type in ['COUNTRY_ADMIN', 'SUPERVISOR']:
                    # First add permission for the PARENT company itself
                    if country_admin_company:
                        company_permission = UserCompanyPermission(
                            user_id=user.id,
                            company_id=int(country_admin_company),
                            can_view=True,
                            can_edit=False,
                            can_delete=False
                        )
                        db_session.add(company_permission)
                        logger.info(f"DEBUG: Added permission for PARENT company {country_admin_company}")

                    # Then add permissions for selected CHILD companies
                    if child_company_ids:
                        for child_company_id in child_company_ids:
                            # Skip if same as parent (already added)
                            if str(child_company_id) == str(country_admin_company):
                                continue
                            company_permission = UserCompanyPermission(
                                user_id=user.id,
                                company_id=int(child_company_id),
                                can_view=True,
                                can_edit=False,
                                can_delete=False
                            )
                            db_session.add(company_permission)
                            logger.info(f"DEBUG: Added permission for CHILD company {child_company_id}")

                # Create queue permissions for Country Admin/Supervisor (per-user, not per-company)
                if user_type in ['COUNTRY_ADMIN', 'SUPERVISOR'] and queue_ids:
                    for queue_id in queue_ids:
                        permission = UserQueuePermission(
                            user_id=user.id,
                            queue_id=int(queue_id),
                            can_view=True,
                            can_create=True
                        )
                        db_session.add(permission)

                # Create @mention permissions for Country Admin/Supervisor
                if user_type in ['COUNTRY_ADMIN', 'SUPERVISOR'] and mention_filter_enabled:
                    # Add user mention permissions
                    for mention_user_id in mention_user_ids:
                        mention_perm = UserMentionPermission(
                            user_id=user.id,
                            target_type='user',
                            target_id=int(mention_user_id)
                        )
                        db_session.add(mention_perm)
                    # Add group mention permissions
                    for mention_group_id in mention_group_ids:
                        mention_perm = UserMentionPermission(
                            user_id=user.id,
                            target_type='group',
                            target_id=int(mention_group_id)
                        )
                        db_session.add(mention_perm)

                db_session.commit()

                # Send welcome email
                if send_welcome_email(email, username, password):
                    flash('User created successfully and welcome email sent', 'success')
                else:
                    flash('User created successfully but failed to send welcome email', 'warning')

                return redirect(url_for('admin.manage_users'))
            except Exception as e:
                db_session.rollback()
                flash(f'Error creating user: {str(e)}', 'error')
                companies_data = [{'id': c.id, 'name': c.name} for c in companies]
                parent_companies_data = _format_parent_companies(parent_companies)
                queues_data = [{'id': q.id, 'name': q.name} for q in queues]
                return render_template('admin/create_user.html', companies=companies_data, parent_companies=parent_companies_data, queues=queues_data, available_countries=available_countries, all_users=all_users, all_groups=all_groups)

        # Convert companies, parent companies and queues to list of dicts to avoid detached instance errors
        companies_data = [{'id': c.id, 'name': c.name} for c in companies]
        parent_companies_data = _format_parent_companies(parent_companies)
        queues_data = [{'id': q.id, 'name': q.name} for q in queues]
        return render_template('admin/create_user.html', companies=companies_data, parent_companies=parent_companies_data, queues=queues_data, available_countries=available_countries, all_users=all_users, all_groups=all_groups)
    finally:
        db_session.close()

@admin_bp.route('/users/<int:user_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_user(user_id):
    """Edit an existing user"""
    from models.queue import Queue
    from models.company_queue_permission import CompanyQueuePermission
    from models.user_queue_permission import UserQueuePermission
    from models.user_company_permission import UserCompanyPermission
    from models.user_mention_permission import UserMentionPermission
    from models.group import Group

    logger.info("DEBUG: Entering edit_user route for user_id={user_id}")
    db_session = db_manager.get_session()
    user = db_session.query(User).get(user_id)
    if not user:
        logger.info("DEBUG: User not found")
        flash('User not found', 'error')
        return redirect(url_for('admin.manage_users'))

    logger.info("DEBUG: User found: {user.username}, type={user.user_type}")
    companies = db_session.query(Company).all()
    parent_companies = db_session.query(Company).filter(Company.is_parent_company == True).all()
    queues = db_session.query(Queue).all()
    logger.info("DEBUG: Found {len(companies)} companies")

    # Get unique countries from assets for COUNTRY_ADMIN dropdown
    from models.asset import Asset
    asset_countries = db_session.query(Asset.country).filter(
        Asset.country.isnot(None),
        Asset.country != ''
    ).distinct().all()
    available_countries = sorted([c[0] for c in asset_countries if c[0]])

    # Get existing permissions for COUNTRY_ADMIN and SUPERVISOR users
    existing_parent_companies = []
    existing_child_companies = []
    existing_queues = []
    existing_countries = []
    if user.user_type in [UserType.COUNTRY_ADMIN, UserType.SUPERVISOR]:
        # Get assigned countries
        existing_countries = user.assigned_countries

        # Get all company permissions for this user
        company_permissions = db_session.query(UserCompanyPermission).filter_by(user_id=user.id).all()
        permission_company_ids = [perm.company_id for perm in company_permissions]

        # Separate into parent and child companies
        for perm in company_permissions:
            company = db_session.query(Company).get(perm.company_id)
            if company:
                if company.is_parent_company:
                    existing_parent_companies.append(str(perm.company_id))
                else:
                    existing_child_companies.append(str(perm.company_id))

        # Get queue permissions for user (per-user, not per-company)
        user_queue_perms = db_session.query(UserQueuePermission).filter_by(user_id=user.id).all()
        existing_queues = [str(perm.queue_id) for perm in user_queue_perms]

    # Get all users and groups for mention control panel
    all_users = db_session.query(User).filter(User.is_deleted == False).order_by(User.username).all()
    all_groups = db_session.query(Group).filter(Group.is_active == True).order_by(Group.name).all()

    # Get existing mention permissions
    allowed_mention_users = []
    allowed_mention_groups = []
    mention_permissions = db_session.query(UserMentionPermission).filter_by(user_id=user.id).all()
    for perm in mention_permissions:
        if perm.target_type == 'user':
            allowed_mention_users.append(perm.target_id)
        elif perm.target_type == 'group':
            allowed_mention_groups.append(perm.target_id)

    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        company_id = request.form.get('company_id')
        user_type = request.form.get('user_type')
        password = request.form.get('password')
        assigned_countries = request.form.getlist('assigned_countries')  # Changed to getlist for multiple countries
        parent_company_ids = request.form.getlist('parent_company_ids')  # Multiple parent companies
        child_company_ids = request.form.getlist('child_company_ids')
        queue_ids = request.form.getlist('queue_ids')
        mention_filter_enabled = request.form.get('mention_filter_enabled') == '1'
        mention_user_ids = request.form.getlist('mention_user_ids')
        mention_group_ids = request.form.getlist('mention_group_ids')

        logger.info(f"DEBUG: Form submission - user_type={user_type}, company_id={company_id}, parent_company_ids={parent_company_ids}, assigned_countries={assigned_countries}")
        logger.info(f"DEBUG: child_company_ids={child_company_ids}, queue_ids={queue_ids}")

        try:
            # Update basic user information
            user.username = username
            user.email = email
            user.user_type = UserType[user_type]

            # Handle company assignment - use company_id dropdown for all user types
            if company_id:
                user.company_id = int(company_id)
            elif user_type in ['COUNTRY_ADMIN', 'SUPERVISOR'] and parent_company_ids:
                # Fallback: if no company selected but parent companies exist, use first parent
                user.company_id = int(parent_company_ids[0])
            else:
                user.company_id = None

            # Company is required for CLIENT users
            if user_type == 'CLIENT' and not company_id:
                logger.info("DEBUG: CLIENT type but no company selected")
                flash('Company selection is required for Client users', 'error')
                companies_data = [{'id': c.id, 'name': c.name} for c in companies]
                parent_companies_data = _format_parent_companies(parent_companies)
                queues_data = [{'id': q.id, 'name': q.name} for q in queues]
                return render_template('admin/edit_user.html', user=user, companies=companies_data,
                                     parent_companies=parent_companies_data, queues=queues_data,
                                     existing_parent_companies=existing_parent_companies,
                                     existing_child_companies=existing_child_companies,
                                     existing_queues=existing_queues, available_countries=available_countries,
                                     existing_countries=existing_countries)

            # Update password if provided
            if password:
                user.password_hash = safe_generate_password_hash(password)

            # Handle country assignment for COUNTRY_ADMIN and SUPERVISOR
            if user_type in ['COUNTRY_ADMIN', 'SUPERVISOR']:
                if not assigned_countries:
                    flash('At least one country selection is required for Country Admin/Supervisor', 'error')
                    companies_data = [{'id': c.id, 'name': c.name} for c in companies]
                    parent_companies_data = _format_parent_companies(parent_companies)
                    queues_data = [{'id': q.id, 'name': q.name} for q in queues]
                    return render_template('admin/edit_user.html', user=user, companies=companies_data,
                                         parent_companies=parent_companies_data, queues=queues_data,
                                         existing_parent_companies=existing_parent_companies,
                                         existing_child_companies=existing_child_companies,
                                         existing_queues=existing_queues, available_countries=available_countries,
                                         existing_countries=existing_countries)

                # Delete existing country permissions
                from models.user_country_permission import UserCountryPermission
                db_session.query(UserCountryPermission).filter_by(user_id=user.id).delete()
                logger.info(f"DEBUG: Deleted existing country permissions for user {user.id}")

                # Create new country permissions
                for country in assigned_countries:
                    country_permission = UserCountryPermission(
                        user_id=user.id,
                        country=country
                    )
                    db_session.add(country_permission)
                    logger.info(f"DEBUG: Created country permission for {country}")

                # Update company permissions (both parent and child companies)
                # Delete existing permissions
                deleted_count = db_session.query(UserCompanyPermission).filter_by(user_id=user.id).delete()
                logger.info(f"DEBUG: Deleted {deleted_count} existing company permissions for user {user.id}")

                # Add permissions for PARENT companies first
                if parent_company_ids:
                    logger.info(f"DEBUG: Adding {len(parent_company_ids)} parent company permissions: {parent_company_ids}")
                    for parent_company_id in parent_company_ids:
                        company_permission = UserCompanyPermission(
                            user_id=user.id,
                            company_id=int(parent_company_id),
                            can_view=True,
                            can_edit=False,
                            can_delete=False
                        )
                        db_session.add(company_permission)
                        logger.info(f"DEBUG: Added permission for user {user.id} to view PARENT company {parent_company_id}")

                # Add permissions for CHILD companies
                if child_company_ids:
                    logger.info(f"DEBUG: Adding {len(child_company_ids)} child company permissions: {child_company_ids}")
                    for child_company_id in child_company_ids:
                        # Skip if already added as parent
                        if child_company_id in parent_company_ids:
                            continue
                        company_permission = UserCompanyPermission(
                            user_id=user.id,
                            company_id=int(child_company_id),
                            can_view=True,
                            can_edit=False,
                            can_delete=False
                        )
                        db_session.add(company_permission)
                        logger.info(f"DEBUG: Added permission for user {user.id} to view CHILD company {child_company_id}")

                if not parent_company_ids and not child_company_ids:
                    logger.info(f"DEBUG: No company IDs provided - user will see NO assets (must assign companies)")

                # Update queue permissions (per-user, not per-company)
                # Delete existing queue permissions for this user
                db_session.query(UserQueuePermission).filter_by(user_id=user.id).delete()
                # Add new queue permissions
                if queue_ids:
                    for queue_id in queue_ids:
                        permission = UserQueuePermission(
                            user_id=user.id,
                            queue_id=int(queue_id),
                            can_view=True,
                            can_create=True
                        )
                        db_session.add(permission)
                logger.info(f"DEBUG: Updated queue permissions for user {user.id}: {queue_ids}")

                # Update mention permissions
                user.mention_filter_enabled = mention_filter_enabled
                # Delete existing mention permissions
                db_session.query(UserMentionPermission).filter_by(user_id=user.id).delete()
                # Add new mention permissions if filtering is enabled
                if mention_filter_enabled:
                    for uid in mention_user_ids:
                        mention_perm = UserMentionPermission(
                            user_id=user.id,
                            target_type='user',
                            target_id=int(uid)
                        )
                        db_session.add(mention_perm)
                    for gid in mention_group_ids:
                        mention_perm = UserMentionPermission(
                            user_id=user.id,
                            target_type='group',
                            target_id=int(gid)
                        )
                        db_session.add(mention_perm)
                logger.info(f"DEBUG: Updated mention permissions for user {user.id}: filter_enabled={mention_filter_enabled}, users={len(mention_user_ids)}, groups={len(mention_group_ids)}")
            else:
                # Clean up permissions if changing from COUNTRY_ADMIN/SUPERVISOR to another type
                from models.user_country_permission import UserCountryPermission
                db_session.query(UserCountryPermission).filter_by(user_id=user.id).delete()
                db_session.query(UserCompanyPermission).filter_by(user_id=user.id).delete()
                db_session.query(UserQueuePermission).filter_by(user_id=user.id).delete()
                # Also clean up mention permissions
                user.mention_filter_enabled = False
                db_session.query(UserMentionPermission).filter_by(user_id=user.id).delete()

            db_session.commit()
            flash('User updated successfully', 'success')
            return redirect(url_for('admin.manage_users'))
        except Exception as e:
            db_session.rollback()
            logger.info("DEBUG: Error updating user: {str(e)}")
            flash(f'Error updating user: {str(e)}', 'error')
        finally:
            db_session.close()

    logger.info("DEBUG: Rendering edit_user template")
    companies_data = [{'id': c.id, 'name': c.name} for c in companies]
    parent_companies_data = _format_parent_companies(parent_companies)
    queues_data = [{'id': q.id, 'name': q.name} for q in queues]
    return render_template('admin/edit_user.html', user=user, companies=companies_data,
                         parent_companies=parent_companies_data, queues=queues_data,
                         existing_parent_companies=existing_parent_companies,
                         existing_child_companies=existing_child_companies,
                         existing_queues=existing_queues, available_countries=available_countries,
                         existing_countries=existing_countries,
                         all_users=all_users, all_groups=all_groups,
                         allowed_mention_users=allowed_mention_users,
                         allowed_mention_groups=allowed_mention_groups)

@admin_bp.route('/users/<int:user_id>/delete', methods=['POST'])
@admin_required
def delete_user(user_id):
    user = db_manager.get_user(user_id)
    if not user:
        flash('User not found', 'error')
        return redirect(url_for('admin.manage_users'))

    # Allow DEVELOPER and SUPER_ADMIN to delete admin users
    current_user_type = session.get('user_type')
    if user.is_admin and current_user_type not in ['DEVELOPER', 'SUPER_ADMIN']:
        flash('Cannot delete admin user', 'error')
        return redirect(url_for('admin.manage_users'))

    try:
        db_manager.delete_user(user_id)
        flash(f'User "{user.username}" has been deactivated', 'success')
    except Exception as e:
        flash(f'Error deleting user: {str(e)}', 'error')

    return redirect(url_for('admin.manage_users'))

@admin_bp.route('/users/<int:user_id>/restore', methods=['POST'])
@admin_required
def restore_user(user_id):
    """Restore a soft-deleted user"""
    user = db_manager.get_user(user_id)
    if not user:
        flash('User not found', 'error')
        return redirect(url_for('admin.manage_users'))

    try:
        db_manager.restore_user(user_id)
        flash(f'User "{user.username}" has been restored', 'success')
    except Exception as e:
        flash(f'Error restoring user: {str(e)}', 'error')

    return redirect(url_for('admin.manage_users'))

@admin_bp.route('/users/<int:user_id>/overview')
@admin_required
def user_overview(user_id):
    """Display comprehensive overview of user settings and permissions"""
    from models.queue import Queue
    from models.company_queue_permission import CompanyQueuePermission
    from models.user_company_permission import UserCompanyPermission
    from models.user_country_permission import UserCountryPermission
    from models.user_mention_permission import UserMentionPermission
    from models.company_customer_permission import CompanyCustomerPermission
    from models.group import Group
    from models.group_membership import GroupMembership

    db_session = db_manager.get_session()
    try:
        user = db_session.query(User).get(user_id)
        if not user:
            flash('User not found', 'error')
            return redirect(url_for('admin.manage_users'))

        # Get permission flags for user's type
        permission = db_session.query(Permission).filter_by(user_type=user.user_type).first()

        # Get company permissions
        company_permissions = db_session.query(UserCompanyPermission).filter_by(user_id=user.id).all()
        company_access = []
        for perm in company_permissions:
            company = db_session.query(Company).get(perm.company_id)
            if company:
                company_access.append({
                    'company': company,
                    'can_view': perm.can_view,
                    'can_edit': perm.can_edit,
                    'can_delete': perm.can_delete
                })

        # Get customer visibility permissions (which customers can this user's companies view)
        customer_visibility = []
        company_ids_with_access = [item['company'].id for item in company_access]
        if company_ids_with_access:
            customer_permissions = db_session.query(CompanyCustomerPermission).filter(
                CompanyCustomerPermission.company_id.in_(company_ids_with_access),
                CompanyCustomerPermission.can_view == True
            ).all()
            for perm in customer_permissions:
                customer_company = db_session.query(Company).get(perm.customer_company_id)
                granting_company = db_session.query(Company).get(perm.company_id)
                if customer_company:
                    customer_visibility.append({
                        'customer': customer_company,
                        'granted_by': granting_company
                    })

        # Get country permissions
        country_permissions = db_session.query(UserCountryPermission).filter_by(user_id=user.id).all()
        assigned_countries = [cp.country for cp in country_permissions]

        # Get queue permissions (per-user)
        queue_access = []
        user_queue_perms = db_session.query(UserQueuePermission).filter_by(user_id=user.id).all()
        for perm in user_queue_perms:
            queue = db_session.query(Queue).get(perm.queue_id)
            if queue:
                queue_access.append({
                    'queue': queue,
                    'can_view': perm.can_view,
                    'can_create': perm.can_create
                })

        # Get group memberships
        group_memberships = db_session.query(GroupMembership).filter_by(
            user_id=user.id, is_active=True
        ).all()
        groups = []
        for membership in group_memberships:
            group = db_session.query(Group).get(membership.group_id)
            if group and group.is_active:
                groups.append(group)

        # Get mention permissions
        mention_permissions = db_session.query(UserMentionPermission).filter_by(user_id=user.id).all()
        allowed_mention_users = []
        allowed_mention_groups = []
        for perm in mention_permissions:
            if perm.target_type == 'user':
                target_user = db_session.query(User).get(perm.target_id)
                if target_user:
                    allowed_mention_users.append(target_user)
            elif perm.target_type == 'group':
                target_group = db_session.query(Group).get(perm.target_id)
                if target_group:
                    allowed_mention_groups.append(target_group)

        # Get user's company info
        user_company = db_session.query(Company).get(user.company_id) if user.company_id else None

        # Get all users for side panel navigation and mention settings
        all_users = db_session.query(User).filter(User.is_deleted == False).order_by(User.username).all()

        # Get all data needed for inline editing panels
        # All available countries from assets
        from models.asset import Asset
        asset_countries = db_session.query(Asset.country).filter(
            Asset.country.isnot(None),
            Asset.country != ''
        ).distinct().all()
        all_countries = sorted([c[0] for c in asset_countries if c[0]])

        # All companies for company access editing
        all_companies = db_session.query(Company).order_by(Company.name).all()
        all_companies_data = []
        for c in all_companies:
            all_companies_data.append({
                'id': c.id,
                'name': c.name,
                'is_parent': c.is_parent_company,
                'parent_id': c.parent_company_id,
                'parent_name': c.parent_company.name if c.parent_company else None
            })

        # All queues for queue access editing
        all_queues = db_session.query(Queue).order_by(Queue.name).all()

        # All groups for mention settings editing
        all_groups = db_session.query(Group).filter(Group.is_active == True).order_by(Group.name).all()

        # Organize permissions by category for display
        permission_categories = {}
        if permission:
            permission_categories = {
                'Assets': {
                    'can_view_assets': permission.can_view_assets,
                    'can_edit_assets': permission.can_edit_assets,
                    'can_create_assets': permission.can_create_assets,
                    'can_delete_assets': permission.can_delete_assets,
                },
                'Country Assets': {
                    'can_view_country_assets': permission.can_view_country_assets,
                    'can_edit_country_assets': permission.can_edit_country_assets,
                    'can_create_country_assets': permission.can_create_country_assets,
                    'can_delete_country_assets': permission.can_delete_country_assets,
                },
                'Accessories': {
                    'can_view_accessories': permission.can_view_accessories,
                    'can_edit_accessories': permission.can_edit_accessories,
                    'can_create_accessories': permission.can_create_accessories,
                    'can_delete_accessories': permission.can_delete_accessories,
                },
                'Tickets': {
                    'can_view_tickets': permission.can_view_tickets,
                    'can_edit_tickets': permission.can_edit_tickets,
                    'can_create_tickets': permission.can_create_tickets,
                    'can_delete_tickets': permission.can_delete_tickets,
                    'can_delete_own_tickets': permission.can_delete_own_tickets,
                    'can_export_tickets': permission.can_export_tickets,
                },
                'Companies': {
                    'can_view_companies': permission.can_view_companies,
                    'can_edit_companies': permission.can_edit_companies,
                    'can_create_companies': permission.can_create_companies,
                    'can_delete_companies': permission.can_delete_companies,
                },
                'Users': {
                    'can_view_users': permission.can_view_users,
                    'can_edit_users': permission.can_edit_users,
                    'can_create_users': permission.can_create_users,
                    'can_delete_users': permission.can_delete_users,
                },
                'Reports': {
                    'can_view_reports': permission.can_view_reports,
                    'can_generate_reports': permission.can_generate_reports,
                },
                'Import/Export': {
                    'can_import_data': permission.can_import_data,
                    'can_export_data': permission.can_export_data,
                },
                'Documents': {
                    'can_access_documents': permission.can_access_documents,
                    'can_create_commercial_invoices': permission.can_create_commercial_invoices,
                    'can_create_packing_lists': permission.can_create_packing_lists,
                },
                'Knowledge Base': {
                    'can_view_knowledge_base': permission.can_view_knowledge_base,
                    'can_create_articles': permission.can_create_articles,
                    'can_edit_articles': permission.can_edit_articles,
                    'can_delete_articles': permission.can_delete_articles,
                    'can_manage_categories': permission.can_manage_categories,
                    'can_view_restricted_articles': permission.can_view_restricted_articles,
                },
                'Inventory Audit': {
                    'can_access_inventory_audit': permission.can_access_inventory_audit,
                    'can_start_inventory_audit': permission.can_start_inventory_audit,
                    'can_view_audit_reports': permission.can_view_audit_reports,
                },
                'Development': {
                    'can_access_development': permission.can_access_development,
                    'can_view_features': permission.can_view_features,
                    'can_create_features': permission.can_create_features,
                    'can_edit_features': permission.can_edit_features,
                    'can_approve_features': permission.can_approve_features,
                    'can_view_bugs': permission.can_view_bugs,
                    'can_create_bugs': permission.can_create_bugs,
                    'can_edit_bugs': permission.can_edit_bugs,
                    'can_view_releases': permission.can_view_releases,
                    'can_create_releases': permission.can_create_releases,
                    'can_edit_releases': permission.can_edit_releases,
                },
                'Debug': {
                    'can_access_debug_logs': permission.can_access_debug_logs,
                },
            }

        return render_template('admin/user_overview.html',
                             user=user,
                             user_company=user_company,
                             permission=permission,
                             permission_categories=permission_categories,
                             company_access=company_access,
                             customer_visibility=customer_visibility,
                             assigned_countries=assigned_countries,
                             queue_access=queue_access,
                             groups=groups,
                             mention_filter_enabled=user.mention_filter_enabled,
                             allowed_mention_users=allowed_mention_users,
                             allowed_mention_groups=allowed_mention_groups,
                             all_users=all_users,
                             # Data for inline editing panels
                             all_countries=all_countries,
                             all_companies=all_companies_data,
                             all_queues=all_queues,
                             all_groups=all_groups)
    finally:
        db_session.close()

@admin_bp.route('/users/<int:user_id>/manage')
@admin_required
def manage_user(user_id):
    user = db_manager.get_user(user_id)
    if not user:
        flash('User not found', 'error')
        return redirect(url_for('admin.manage_users'))

    # Get user's activities, assigned assets, etc.
    activities = db_manager.get_user_activities(user_id)
    assigned_assets = db_manager.get_user_assets(user_id)

    return render_template('admin/manage_user.html', 
                         user=user, 
                         activities=activities,
                         assigned_assets=assigned_assets)

@admin_bp.route('/permissions/update', methods=['POST'])
@super_admin_required
def update_permissions():
    """Update user type permissions based on form data"""
    if 'user_id' not in session:
        flash('Please log in to continue', 'error')
        return redirect(url_for('auth.login'))

    db_session = db_manager.get_session()
    try:
        # Log the form data
        logger.info(f"Form data received: {request.form}")
        
        user_type = request.form.get('user_type')
        logger.info(f"User type: {user_type}")
        
        if not user_type:
            flash('User type is required', 'error')
            return redirect(url_for('admin.permission_management'))

        try:
            user_type_enum = UserType[user_type]
            logger.info(f"User type enum: {user_type_enum}")
        except KeyError:
            flash('Invalid user type', 'error')
            return redirect(url_for('admin.permission_management'))

        # Get existing permission record
        permission = db_session.query(Permission).filter_by(user_type=user_type_enum).first()
        logger.info(f"Existing permission: {permission}")
        
        if not permission:
            permission = Permission(user_type=user_type_enum)
            db_session.add(permission)
            logger.info("Created new permission record")

        # Get all permission fields
        fields = Permission.permission_fields()
        logger.info(f"Permission fields: {fields}")

        # Update permissions from form data
        for field in fields:
            old_value = getattr(permission, field)
            # Check if the field exists in form and its value is 'true'
            new_value = request.form.get(field) == 'true'
            setattr(permission, field, new_value)
            logger.info(f"Updating {field}: {old_value} -> {new_value}")

        db_session.commit()
        logger.info("Changes committed successfully")
        
        flash('Permissions updated successfully', 'success')
        return redirect(url_for('admin.permission_management'))
    except Exception as e:
        db_session.rollback()
        logger.error(f"Error updating permissions: {str(e)}")
        flash(f'Error updating permissions: {str(e)}', 'error')
        return redirect(url_for('admin.permission_management'))
    finally:
        db_session.close()

@admin_bp.route('/permissions/reset/<user_type>', methods=['POST'])
@super_admin_required
def reset_permissions(user_type):
    """Reset permissions for a user type to default values"""
    if 'user_id' not in session:
        flash('Please log in to continue', 'error')
        return redirect(url_for('auth.login'))

    db_session = db_manager.get_session()
    try:
        # Validate user type
        try:
            user_type_enum = UserType[user_type]
        except KeyError:
            flash('Invalid user type', 'error')
            return redirect(url_for('admin.permission_management'))

        # Delete existing permissions
        db_session.query(Permission).filter_by(user_type=user_type_enum).delete()
        
        # Get default permissions
        default_permissions = Permission.get_default_permissions(user_type_enum)
        
        # Create new permission record with defaults
        permission = Permission(user_type=user_type_enum, **default_permissions)
        db_session.add(permission)
        db_session.commit()
        
        flash('Permissions reset to default values', 'success')
        return redirect(url_for('admin.permission_management'))
    except Exception as e:
        db_session.rollback()
        flash(f'Error resetting permissions: {str(e)}', 'error')
        return redirect(url_for('admin.permission_management'))
    finally:
        db_session.close()

@admin_bp.route('/users/<int:user_id>/resend-welcome', methods=['POST'])
@admin_required
def resend_welcome_email(user_id):
    """Resend welcome email to a user"""
    db_session = db_manager.get_session()
    try:
        user = db_session.query(User).get(user_id)
        if not user:
            flash('User not found', 'error')
            return redirect(url_for('admin.manage_users'))

        # Generate a new password for the user
        new_password = str(uuid.uuid4())[:8]  # Use first 8 characters of a UUID as password
        user.password_hash = safe_generate_password_hash(new_password)
        db_session.commit()

        # Send welcome email with new credentials
        if send_welcome_email(user.email, user.username, new_password):
            flash('Welcome email sent successfully with new credentials', 'success')
        else:
            flash('Failed to send welcome email', 'error')

    except Exception as e:
        db_session.rollback()
        flash(f'Error resending welcome email: {str(e)}', 'error')
    finally:
        db_session.close()
    
    return redirect(url_for('admin.manage_users'))

@admin_bp.route('/history')
@super_admin_required
def view_history():
    """View all system history/activity logs"""
    db_session = db_manager.get_session()
    try:
        # Get all activities with user information, ordered by most recent first
        activities = (db_session.query(Activity)
                     .join(Activity.user)
                     .order_by(Activity.created_at.desc())
                     .all())
        
        # Get all asset history with user information
        asset_history = (db_session.query(AssetHistory)
                        .join(AssetHistory.user)
                        .join(AssetHistory.asset)
                        .order_by(AssetHistory.created_at.desc())
                        .all())
                        
        # Get all accessory history with user information
        accessory_history = (db_session.query(AccessoryHistory)
                           .join(AccessoryHistory.user)
                           .join(AccessoryHistory.accessory)
                           .order_by(AccessoryHistory.created_at.desc())
                           .all())

        return render_template('admin/history.html',
                             activities=activities,
                             asset_history=asset_history,
                             accessory_history=accessory_history)
    finally:
        db_session.close()

@admin_bp.route('/update-user-type-permissions/<user_type>')
@admin_required
def update_user_type_permissions(user_type):
    """Update permissions for all users of a specific type"""
    try:
        # Convert string to UserType enum
        user_type_enum = UserType[user_type.upper()]
        
        # Get the session
        session = db_manager.get_session()
        
        try:
            # Get or create permission for this user type
            permission = session.query(Permission).filter_by(user_type=user_type_enum).first()
            
            if not permission:
                # Create new permission with default values
                default_permissions = Permission.get_default_permissions(user_type_enum)
                permission = Permission(user_type=user_type_enum, **default_permissions)
                session.add(permission)
            else:
                # Update existing permission with default values
                default_permissions = Permission.get_default_permissions(user_type_enum)
                for key, value in default_permissions.items():
                    setattr(permission, key, value)
            
            session.commit()
            flash(f'Successfully updated permissions for {user_type}', 'success')
            
        finally:
            session.close()
            
        return redirect(url_for('admin.permission_management'))

    except KeyError:
        flash(f'Invalid user type: {user_type}', 'error')
        return redirect(url_for('admin.permission_management'))
    except Exception as e:
        flash(f'Error updating permissions: {str(e)}', 'error')
        return redirect(url_for('admin.permission_management'))

@admin_bp.route('/queue-permissions')
@super_admin_required
def manage_queue_permissions():
    """Manage which companies can see which queues"""
    db_session = db_manager.get_session()
    try:
        companies = db_session.query(Company).all()
        queues = db_session.query(Queue).all()
        permissions = db_session.query(CompanyQueuePermission).all()
        
        # Create a mapping of company_id -> queue_id -> permission for easier access in template
        permission_map = {}
        for permission in permissions:
            if permission.company_id not in permission_map:
                permission_map[permission.company_id] = {}
            permission_map[permission.company_id][permission.queue_id] = permission
        
        return render_template('admin/queue_permissions_new.html',
                              companies=companies,
                              queues=queues,
                              permission_map=permission_map)
    except Exception as e:
        flash(f'Error loading queue permissions: {str(e)}', 'error')
        return redirect(url_for('admin.index'))
    finally:
        db_session.close()

@admin_bp.route('/queue-permissions/update', methods=['POST'])
@super_admin_required
def update_queue_permissions():
    """Update queue permissions for companies"""
    try:
        # Debug incoming request data
        logger.info(f"Form data received: {request.form}")
        logger.info(f"JSON data received: {request.get_json(silent=True)}")
        
        # Try multiple ways to get the data
        if request.form:
            company_id = request.form.get('company_id')
            queue_id = request.form.get('queue_id')
            has_permission = 'has_permission' in request.form
            can_view = 'can_view' in request.form
            can_create = 'can_create' in request.form
        else:
            data = request.get_json(silent=True) or {}
            company_id = data.get('company_id')
            queue_id = data.get('queue_id')
            has_permission = data.get('has_permission', False)
            can_view = data.get('can_view', False)
            can_create = data.get('can_create', False)
        
        logger.info(f"Raw company_id: {company_id}, type: {type(company_id)}")
        logger.info(f"Raw queue_id: {queue_id}, type: {type(queue_id)}")
        
        # Convert to integers with safer handling
        try:
            if company_id:
                company_id = int(company_id)
            if queue_id:
                queue_id = int(queue_id)
        except (ValueError, TypeError) as e:
            logger.info(f"Error converting IDs to integers: {str(e)}")
            flash(f"Invalid ID format: {str(e)}", 'error')
            return redirect(url_for('admin.manage_queue_permissions'))
        
        logger.info(f"Converted company_id: {company_id}, queue_id: {queue_id}")
        logger.info(f"Permission values - has_permission: {has_permission}, can_view: {can_view}, can_create: {can_create}")
        
        if not company_id or not queue_id:
            logger.info("INVALID: Missing company_id or queue_id")
            flash('Invalid company or queue ID', 'error')
            return redirect(url_for('admin.manage_queue_permissions'))
        
        db_session = db_manager.get_session()
        try:
            # Verify company and queue exist
            company = db_session.query(Company).get(company_id)
            queue = db_session.query(Queue).get(queue_id)
            
            if not company:
                logger.info(f"Company with ID {company_id} not found")
                flash(f"Company with ID {company_id} not found", 'error')
                return redirect(url_for('admin.manage_queue_permissions'))
                
            if not queue:
                logger.info(f"Queue with ID {queue_id} not found")
                flash(f"Queue with ID {queue_id} not found", 'error')
                return redirect(url_for('admin.manage_queue_permissions'))
            
            # Check if permission already exists
            permission = db_session.query(CompanyQueuePermission).filter_by(
                company_id=company_id, queue_id=queue_id).first()
            
            logger.info(f"Existing permission found: {permission is not None}")
            
            if not has_permission:
                # If no permission should be granted, delete existing permission if it exists
                if permission:
                    db_session.delete(permission)
                    db_session.commit()
                    flash('Permission removed successfully', 'success')
                    logger.info("Permission removed")
            else:
                if permission:
                    # Update existing permission
                    permission.can_view = can_view
                    permission.can_create = can_create
                    logger.info(f"Updated permission - can_view: {can_view}, can_create: {can_create}")
                else:
                    # Create new permission
                    permission = CompanyQueuePermission(
                        company_id=company_id,
                        queue_id=queue_id,
                        can_view=can_view,
                        can_create=can_create
                    )
                    db_session.add(permission)
                    logger.info(f"Created new permission - can_view: {can_view}, can_create: {can_create}")
            
                db_session.commit()
                flash('Queue permissions updated successfully', 'success')
                logger.info("Permission saved successfully")
            
            return jsonify({"status": "success", "message": "Permission updated successfully"})
            
        except Exception as e:
            db_session.rollback()
            logger.info(f"ERROR: {str(e)}")
            logger.info(f"Stack trace: {traceback.format_exc()}")
            flash(f'Error updating queue permissions: {str(e)}', 'error')
            return jsonify({"status": "error", "message": str(e)}), 500
        finally:
            db_session.close()
    
    except Exception as e:
        logger.info(f"Unexpected error: {str(e)}")
        logger.info(f"Stack trace: {traceback.format_exc()}")
        return jsonify({"status": "error", "message": f"Unexpected error: {str(e)}"}), 500
        
    return redirect(url_for('admin.manage_queue_permissions'))

@admin_bp.route('/queue-permissions/delete/<int:permission_id>', methods=['GET', 'POST'])
@super_admin_required
def delete_queue_permission(permission_id):
    """Delete queue permission (reset to default)"""
    if not permission_id:
        flash('Invalid permission ID', 'error')
        return redirect(url_for('admin.manage_queue_permissions'))
    
    db_session = db_manager.get_session()
    try:
        permission = db_session.query(CompanyQueuePermission).get(permission_id)
        if permission:
            db_session.delete(permission)
            db_session.commit()
            flash('Permission removed successfully', 'success')
        else:
            flash('Permission not found', 'error')
    except Exception as e:
        db_session.rollback()
        flash(f'Error removing permission: {str(e)}', 'error')
    finally:
        db_session.close()
    
    return redirect(url_for('admin.manage_queue_permissions'))

@admin_bp.route('/queue-notifications')
@admin_required
def manage_queue_notifications():
    """Manage queue notification subscriptions"""
    from models.queue_notification import QueueNotification
    from models.queue import Queue
    from models.user import User

    db_session = db_manager.get_session()
    try:
        # Get all users, queues, and existing notifications
        users = db_session.query(User).filter(User.is_deleted == False).order_by(User.username).all()
        queues = db_session.query(Queue).order_by(Queue.name).all()
        notifications = db_session.query(QueueNotification).all()

        # Create a mapping for easier template access - convert to dict to avoid detached session issues
        notification_map = {}
        for notification in notifications:
            key = f"{notification.user_id}_{notification.queue_id}"
            # Store as dict to avoid detached session issues
            notification_map[key] = {
                'id': notification.id,
                'user_id': notification.user_id,
                'queue_id': notification.queue_id,
                'notify_on_create': notification.notify_on_create,
                'notify_on_move': notification.notify_on_move,
                'is_active': notification.is_active,
                'created_at': notification.created_at
            }

        # Convert users and queues to avoid detached session issues
        users_list = [{
            'id': u.id,
            'username': u.username,
            'email': u.email,
            'user_type_value': u.user_type.value if u.user_type else 'USER'
        } for u in users]

        queues_list = [{
            'id': q.id,
            'name': q.name,
            'description': q.description
        } for q in queues]

        return render_template('admin/queue_notifications.html',
                              users=users_list,
                              queues=queues_list,
                              notification_map=notification_map)
    except Exception as e:
        flash(f'Error loading queue notifications: {str(e)}', 'error')
        return redirect(url_for('admin.manage_users'))
    finally:
        db_session.close()


@admin_bp.route('/queue-notifications/update', methods=['POST'])
@admin_required
def update_queue_notification():
    """Update or create a queue notification subscription"""
    from models.queue_notification import QueueNotification
    from datetime import datetime
    
    try:
        user_id = int(request.form.get('user_id'))
        queue_id = int(request.form.get('queue_id'))
        notify_on_create = request.form.get('notify_on_create') == 'on'
        notify_on_move = request.form.get('notify_on_move') == 'on'
        is_active = request.form.get('is_active') == 'on'
        
        db_session = db_manager.get_session()
        try:
            # Check if notification already exists
            notification = db_session.query(QueueNotification).filter_by(
                user_id=user_id, queue_id=queue_id).first()
            
            if notification:
                # Update existing notification
                notification.notify_on_create = notify_on_create
                notification.notify_on_move = notify_on_move
                notification.is_active = is_active
                notification.updated_at = datetime.utcnow()
                action = "updated"
            else:
                # Create new notification
                notification = QueueNotification(
                    user_id=user_id,
                    queue_id=queue_id,
                    notify_on_create=notify_on_create,
                    notify_on_move=notify_on_move,
                    is_active=is_active
                )
                db_session.add(notification)
                action = "created"
            
            db_session.commit()
            flash(f'Queue notification {action} successfully', 'success')
            
        except Exception as e:
            db_session.rollback()
            flash(f'Error updating queue notification: {str(e)}', 'error')
        finally:
            db_session.close()
            
    except Exception as e:
        flash(f'Invalid request data: {str(e)}', 'error')
    
    return redirect(url_for('admin.manage_queue_notifications'))


@admin_bp.route('/queue-notifications/delete/<int:notification_id>', methods=['POST'])
@admin_required
def delete_queue_notification(notification_id):
    """Delete a queue notification subscription"""
    from models.queue_notification import QueueNotification
    
    db_session = db_manager.get_session()
    try:
        notification = db_session.query(QueueNotification).get(notification_id)
        if notification:
            db_session.delete(notification)
            db_session.commit()
            flash('Queue notification deleted successfully', 'success')
        else:
            flash('Queue notification not found', 'error')
    except Exception as e:
        db_session.rollback()
        flash(f'Error deleting queue notification: {str(e)}', 'error')
    finally:
        db_session.close()
    
    return redirect(url_for('admin.manage_queue_notifications'))

@admin_bp.route('/system-config')
@super_admin_required
def system_config():
    """System configuration page"""
    from version import get_full_version_info
    
    db_session = db_manager.get_session()
    try:
        # Get current user
        user = db_manager.get_user(session['user_id'])
        if not user:
            session.clear()
            return redirect(url_for('auth.login'))

        # Try to get Firecrawl API keys, but handle the case when the table doesn't exist
        firecrawl_keys = []
        active_key = None
        try:
            firecrawl_keys = db_session.query(FirecrawlKey).order_by(FirecrawlKey.created_at.desc()).all()
            active_key = db_session.query(FirecrawlKey).filter_by(is_active=True).first()
            if not active_key:
                active_key = db_session.query(FirecrawlKey).filter_by(is_primary=True).first()
        except Exception as e:
            # If there's an error (like table doesn't exist), just ignore it
            # and use the API key from config
            logger.info("Error fetching Firecrawl keys: {str(e)}")
        
        # Add Microsoft 365 OAuth2 configuration to config for template
        import os
        
        # Get the current API key from the environment or config
        current_api_key = os.environ.get('FIRECRAWL_API_KEY') or current_app.config.get('FIRECRAWL_API_KEY', 'Not set')

        # Get version information
        version_info = get_full_version_info()
        config_with_ms = dict(current_app.config)
        config_with_ms.update({
            'MS_CLIENT_ID': os.getenv('MS_CLIENT_ID'),
            'MS_CLIENT_SECRET': os.getenv('MS_CLIENT_SECRET'),
            'MS_TENANT_ID': os.getenv('MS_TENANT_ID'),
            'MS_FROM_EMAIL': os.getenv('MS_FROM_EMAIL'),
        })

        # Get default homepage setting
        default_homepage = 'classic'
        try:
            from models.system_settings import SystemSettings
            homepage_setting = db_session.query(SystemSettings).filter_by(
                setting_key='default_homepage'
            ).first()
            if homepage_setting:
                default_homepage = homepage_setting.get_value()
        except Exception as e:
            logger.warning(f"Could not load default_homepage setting: {str(e)}")

        return render_template('admin/system_config.html',
                             user=user,
                             firecrawl_keys=firecrawl_keys,
                             active_key=active_key,
                             current_api_key=current_api_key,
                             version_info=version_info,
                             config=config_with_ms,
                             default_homepage=default_homepage)
    except Exception as e:
        db_session.rollback()
        flash(f'Error loading system configuration: {str(e)}', 'error')
        return redirect(url_for('main.index'))
    finally:
        db_session.close()


@admin_bp.route('/update-default-homepage', methods=['POST'])
@super_admin_required
def update_default_homepage():
    """Update the default homepage setting"""
    db_session = db_manager.get_session()
    try:
        from models.system_settings import SystemSettings

        homepage_value = request.form.get('homepage', 'classic')

        # Get or create the setting
        homepage_setting = db_session.query(SystemSettings).filter_by(
            setting_key='default_homepage'
        ).first()

        if homepage_setting:
            homepage_setting.setting_value = homepage_value
        else:
            homepage_setting = SystemSettings(
                setting_key='default_homepage',
                setting_value=homepage_value,
                setting_type='string',
                description='Default homepage for users (classic or new)'
            )
            db_session.add(homepage_setting)

        db_session.commit()
        flash(f'Default homepage changed to {"New Dashboard" if homepage_value == "new" else "Classic Homepage"}', 'success')

    except Exception as e:
        db_session.rollback()
        flash(f'Error updating homepage setting: {str(e)}', 'error')
    finally:
        db_session.close()

    return redirect(url_for('admin.system_config'))


@admin_bp.route('/customer-permissions')
@super_admin_required
def manage_customer_permissions():
    """Manage which companies can see which customers"""
    db_session = db_manager.get_session()
    try:
        # Get current user
        user = db_manager.get_user(session['user_id'])
        if not user:
            session.clear()
            return redirect(url_for('auth.login'))

        # Get all companies
        companies = db_session.query(Company).order_by(Company.name).all()
        
        # Get all existing permissions with company information
        from sqlalchemy.orm import aliased
        CompanyAlias = aliased(Company)
        
        permission_data = db_session.query(CompanyCustomerPermission, Company, CompanyAlias)\
            .join(Company, CompanyCustomerPermission.company_id == Company.id)\
            .join(CompanyAlias, CompanyCustomerPermission.customer_company_id == CompanyAlias.id)\
            .order_by(Company.name).all()
        
        # Structure the data for the template
        permissions = []
        for perm, company, customer_company in permission_data:
            # Add company and customer_company as attributes to the permission object
            perm.company = company
            perm.customer_company = customer_company
            permissions.append(perm)

        return render_template('admin/customer_permissions.html',
                             user=user,
                             companies=companies,
                             permissions=permissions)
    except Exception as e:
        db_session.rollback()
        flash(f'Error loading customer permissions: {str(e)}', 'error')
        return redirect(url_for('admin.system_config'))
    finally:
        db_session.close()

@admin_bp.route('/customer-permissions/update', methods=['POST'])
@super_admin_required
def update_customer_permissions():
    """Update customer viewing permissions (legacy single permission route)"""
    db_session = db_manager.get_session()
    try:
        company_id = request.form.get('company_id')
        customer_company_id = request.form.get('customer_company_id')
        can_view = request.form.get('can_view') == 'true'

        if not company_id or not customer_company_id:
            flash('Company and customer company are required', 'error')
            return redirect(url_for('admin.manage_customer_permissions'))

        # Check if permission already exists
        existing_permission = db_session.query(CompanyCustomerPermission)\
            .filter_by(company_id=company_id, customer_company_id=customer_company_id)\
            .first()

        if existing_permission:
            existing_permission.can_view = can_view
            existing_permission.updated_at = datetime.utcnow()
            action = "updated"
        else:
            # Create new permission
            new_permission = CompanyCustomerPermission(
                company_id=company_id,
                customer_company_id=customer_company_id,
                can_view=can_view
            )
            db_session.add(new_permission)
            action = "created"

        db_session.commit()
        flash(f'Customer permission {action} successfully', 'success')

    except Exception as e:
        db_session.rollback()
        flash(f'Error updating permission: {str(e)}', 'error')
    finally:
        db_session.close()

    return redirect(url_for('admin.manage_customer_permissions'))

@admin_bp.route('/customer-permissions/update-bulk', methods=['POST'])
@super_admin_required
def update_customer_permissions_bulk():
    """Update customer viewing permissions in bulk"""
    db_session = db_manager.get_session()
    try:
        company_id = request.form.get('company_id')
        customer_company_ids = request.form.getlist('customer_company_ids')
        can_view = request.form.get('can_view') == 'true'

        if not company_id:
            flash('Company is required', 'error')
            return redirect(url_for('admin.manage_customer_permissions'))

        if not customer_company_ids:
            flash('At least one customer company must be selected', 'error')
            return redirect(url_for('admin.manage_customer_permissions'))

        # Prevent self-permissions
        customer_company_ids = [cid for cid in customer_company_ids if cid != company_id]

        if not customer_company_ids:
            flash('Cannot grant permissions to view own customers (already have access)', 'error')
            return redirect(url_for('admin.manage_customer_permissions'))

        created_count = 0
        updated_count = 0

        for customer_company_id in customer_company_ids:
            # Check if permission already exists
            existing_permission = db_session.query(CompanyCustomerPermission)\
                .filter_by(company_id=company_id, customer_company_id=customer_company_id)\
                .first()

            if existing_permission:
                if existing_permission.can_view != can_view:
                    existing_permission.can_view = can_view
                    existing_permission.updated_at = datetime.utcnow()
                    updated_count += 1
            else:
                # Create new permission
                new_permission = CompanyCustomerPermission(
                    company_id=company_id,
                    customer_company_id=customer_company_id,
                    can_view=can_view
                )
                db_session.add(new_permission)
                created_count += 1

        db_session.commit()
        
        # Build success message
        messages = []
        if created_count > 0:
            messages.append(f'{created_count} permission(s) created')
        if updated_count > 0:
            messages.append(f'{updated_count} permission(s) updated')
        
        if messages:
            flash(f'Success: {", ".join(messages)}', 'success')
        else:
            flash('No changes were made (permissions already exist with the same settings)', 'info')

    except Exception as e:
        db_session.rollback()
        flash(f'Error updating permissions: {str(e)}', 'error')
    finally:
        db_session.close()

    return redirect(url_for('admin.manage_customer_permissions'))

@admin_bp.route('/customer-permissions/delete/<int:permission_id>', methods=['POST'])
@super_admin_required
def delete_customer_permission(permission_id):
    """Delete a customer permission"""
    db_session = db_manager.get_session()
    try:
        permission = db_session.query(CompanyCustomerPermission).get(permission_id)
        if not permission:
            flash('Permission not found', 'error')
            return redirect(url_for('admin.manage_customer_permissions'))

        db_session.delete(permission)
        db_session.commit()
        flash('Customer permission deleted successfully', 'success')

    except Exception as e:
        db_session.rollback()
        flash(f'Error deleting permission: {str(e)}', 'error')
    finally:
        db_session.close()

    return redirect(url_for('admin.manage_customer_permissions'))

@admin_bp.route('/theme-settings')
@super_admin_required
def theme_settings():
    """Theme configuration page"""
    db_session = db_manager.get_session()
    try:
        # Get current user
        user = db_manager.get_user(session['user_id'])
        if not user:
            session.clear()
            return redirect(url_for('auth.login'))
        
        # Get theme statistics
        theme_stats = db_session.execute(text("""
            SELECT theme_preference, COUNT(*) as count 
            FROM users 
            WHERE theme_preference IS NOT NULL 
            GROUP BY theme_preference
        """)).fetchall()
        
        theme_counts = {
            'light': 0,
            'dark': 0,
            'liquid_glass': 0,
            'ui_2_0': 0
        }
        
        for stat in theme_stats:
            if stat[0] == 'liquid-glass':
                theme_counts['liquid_glass'] = stat[1]
            elif stat[0] == 'ui-2.0':
                theme_counts['ui_2_0'] = stat[1]
            elif stat[0] in theme_counts:
                theme_counts[stat[0]] = stat[1]
        
        total_users = sum(theme_counts.values())
        
        return render_template('admin/theme_settings.html', 
                             user=user,
                             theme_counts=theme_counts,
                             total_users=total_users)
    except Exception as e:
        db_session.rollback()
        flash(f'Error loading theme settings: {str(e)}', 'error')
        return redirect(url_for('admin.system_config'))
    finally:
        db_session.close()


@admin_bp.route('/update-user-theme', methods=['POST'])
@login_required
def update_user_theme():
    """Update current user's theme preference"""
    theme = request.form.get('theme')
    
    if theme not in ['light', 'dark', 'liquid-glass', 'ui-2.0']:
        flash('Invalid theme selection', 'error')
        return redirect(request.referrer or url_for('main.index'))
    
    db_session = db_manager.get_session()
    try:
        # Get current user
        user = db_manager.get_user(session['user_id'])
        if not user:
            session.clear()
            return redirect(url_for('auth.login'))
        
        # Update theme preference
        user.theme_preference = theme
        db_session.commit()
        
        # Update session to reflect theme change immediately
        session['user_theme'] = theme
        
        flash(f'Theme updated to {theme} mode', 'success')
        
        # Return to previous page or theme settings
        return redirect(request.referrer or url_for('admin.theme_settings'))
        
    except Exception as e:
        db_session.rollback()
        flash(f'Error updating theme: {str(e)}', 'error')
        return redirect(request.referrer or url_for('main.index'))
    finally:
        db_session.close()

@admin_bp.route('/toggle-layout', methods=['POST'])
@login_required
def toggle_layout():
    """Toggle between widescreen and centered layout"""
    current_layout = session.get('layout_mode', 'widescreen')
    new_layout = 'centered' if current_layout == 'widescreen' else 'widescreen'

    session['layout_mode'] = new_layout

    flash(f'Layout changed to {new_layout} mode', 'success')
    return redirect(request.referrer or url_for('main.index'))

@admin_bp.route('/changelog')
@login_required
def changelog():
    """Application changelog page"""
    from version import get_full_version_info
    
    version_info = get_full_version_info()
    return render_template('admin/changelog.html', version_info=version_info)

@admin_bp.route('/firecrawl-keys/add', methods=['POST'])
@super_admin_required
def add_firecrawl_key():
    """Add a new Firecrawl API key"""
    db_session = db_manager.get_session()
    try:
        key = request.form.get('key')
        description = request.form.get('description')

        if not key or not description:
            flash('Both API key and description are required', 'error')
            return redirect(url_for('admin.system_config'))

        # Check if key already exists
        existing_key = db_session.query(FirecrawlKey).filter_by(api_key=key).first()
        if existing_key:
            flash('This API key already exists', 'error')
            return redirect(url_for('admin.system_config'))

        # Create new key
        new_key = FirecrawlKey(
            api_key=key,
            name=description,
            is_active=False,
            is_primary=False
        )
        db_session.add(new_key)
        db_session.commit()

        flash('API key added successfully', 'success')
    except Exception as e:
        db_session.rollback()
        flash(f'Error adding API key: {str(e)}', 'error')
    finally:
        db_session.close()
    
    return redirect(url_for('admin.system_config'))

@admin_bp.route('/firecrawl-keys/<int:key_id>/activate', methods=['POST'])
@super_admin_required
def activate_firecrawl_key(key_id):
    """Activate a Firecrawl API key and deactivate others"""
    db_session = db_manager.get_session()
    try:
        # Deactivate all keys
        db_session.query(FirecrawlKey).update({
            FirecrawlKey.is_active: False,
            FirecrawlKey.is_primary: False
        })
        
        # Activate the selected key
        key = db_session.query(FirecrawlKey).get(key_id)
        if key:
            key.is_active = True
            key.is_primary = True
            key.updated_at = datetime.utcnow()
            
            # Update the environment variable and application config
            os.environ['FIRECRAWL_API_KEY'] = key.api_key
            current_app.config['FIRECRAWL_API_KEY'] = key.api_key
            
            db_session.commit()
            flash(f'API key "{key.name}" activated successfully', 'success')
        else:
            flash('API key not found', 'error')
    except Exception as e:
        db_session.rollback()
        flash(f'Error activating API key: {str(e)}', 'error')
    finally:
        db_session.close()
    
    return redirect(url_for('admin.system_config'))

@admin_bp.route('/firecrawl-keys/<int:key_id>/delete', methods=['POST'])
@super_admin_required
def delete_firecrawl_key(key_id):
    """Delete a Firecrawl API key"""
    db_session = db_manager.get_session()
    try:
        key = db_session.query(FirecrawlKey).get(key_id)
        if key:
            if key.is_active or key.is_primary:
                flash('Cannot delete the active API key. Please activate another key first.', 'error')
            else:
                key_description = key.name
                db_session.delete(key)
                db_session.commit()
                flash(f'API key "{key_description}" deleted successfully', 'success')
        else:
            flash('API key not found', 'error')
    except Exception as e:
        db_session.rollback()
        flash(f'Error deleting API key: {str(e)}', 'error')
    finally:
        db_session.close()
    
    return redirect(url_for('admin.system_config'))

@admin_bp.route('/update-firecrawl-key', methods=['POST'])
@super_admin_required
def update_firecrawl_key():
    """Update Firecrawl API key"""
    try:
        new_key = request.form.get('firecrawl_api_key')
        if not new_key:
            flash('API key cannot be empty', 'error')
            return redirect(url_for('admin.system_config'))

        # Update the environment variable
        os.environ['FIRECRAWL_API_KEY'] = new_key
        
        # Update the config
        current_app.config['FIRECRAWL_API_KEY'] = new_key
        
        # Try to update the database if the table exists
        try:
            db_session = db_manager.get_session()
            # Check if we have any keys in the database
            existing_keys = db_session.query(FirecrawlKey).all()
            
            if existing_keys:
                # If we have keys, update the active one or create a new one
                # First deactivate all keys
                db_session.query(FirecrawlKey).update({FirecrawlKey.is_active: False})
                
                # Then either update existing key with same value or create new one
                existing_key = db_session.query(FirecrawlKey).filter_by(api_key=new_key).first()
                if existing_key:
                    existing_key.is_active = True
                    existing_key.is_primary = True
                else:
                    new_key_obj = FirecrawlKey(
                        api_key=new_key,
                        name="Updated via system config",
                        is_active=True,
                        is_primary=True
                    )
                    db_session.add(new_key_obj)
                
                db_session.commit()
        except Exception as e:
            logger.info("Error updating key in database (continuing anyway): {str(e)}")
            # Don't stop execution - we've already updated the config
        
        flash('Firecrawl API key updated successfully', 'success')
    except Exception as e:
        flash(f'Error updating Firecrawl API key: {str(e)}', 'error')
    
    return redirect(url_for('admin.system_config')) 


@admin_bp.route('/ticket-categories')
@super_admin_required
def manage_ticket_categories():
    """Manage all ticket categories (both predefined and custom)"""
    db_session = SessionLocal()
    try:
        # Initialize predefined categories if they don't exist
        CategoryDisplayConfig.initialize_predefined_categories()
        
        # Get all category display configs
        display_configs = db_session.query(CategoryDisplayConfig).order_by(CategoryDisplayConfig.sort_order).all()
        
        # Get custom categories
        custom_categories = db_session.query(TicketCategoryConfig).order_by(TicketCategoryConfig.created_at.desc()).all()
        
        available_sections = TicketCategoryConfig.get_available_sections()
        
        return render_template('admin/ticket_categories/manage_all.html', 
                             display_configs=display_configs,
                             custom_categories=custom_categories,
                             available_sections=available_sections)
    except Exception as e:
        flash(f'Error loading ticket categories: {str(e)}', 'error')
        return redirect(url_for('admin.system_config'))
    finally:
        db_session.close()


@admin_bp.route('/ticket-categories/predefined/<category_key>/edit', methods=['GET', 'POST'])
@super_admin_required
def edit_predefined_category(category_key):
    """Edit display settings for a predefined category"""
    db_session = SessionLocal()
    try:
        # Get or create the display config
        config = db_session.query(CategoryDisplayConfig).filter_by(category_key=category_key).first()
        if not config:
            # Create config for predefined category
            from models.ticket import TicketCategory
            try:
                category_enum = TicketCategory[category_key]
                config = CategoryDisplayConfig(
                    category_key=category_key,
                    display_name=category_enum.value,
                    is_enabled=True,
                    is_predefined=True,
                    sort_order=list(TicketCategory).index(category_enum)
                )
                db_session.add(config)
                db_session.commit()
            except KeyError:
                flash('Invalid category key', 'error')
                return redirect(url_for('admin.manage_ticket_categories'))
        
        if request.method == 'POST':
            display_name = request.form.get('display_name', '').strip()
            is_enabled = request.form.get('is_enabled') == 'on'
            sort_order = request.form.get('sort_order', 0)
            
            if not display_name:
                flash('Display name is required', 'error')
                return redirect(url_for('admin.edit_predefined_category', category_key=category_key))
            
            try:
                sort_order = int(sort_order)
            except (ValueError, TypeError):
                sort_order = 0
            
            # Update config
            config.display_name = display_name
            config.is_enabled = is_enabled
            config.sort_order = sort_order
            config.updated_at = datetime.utcnow()
            
            db_session.commit()
            
            flash(f'Category "{display_name}" updated successfully', 'success')
            return redirect(url_for('admin.manage_ticket_categories'))
        
        # GET request - show form
        return render_template('admin/ticket_categories/edit_predefined.html', config=config)
                             
    except Exception as e:
        db_session.rollback()
        flash(f'Error editing category: {str(e)}', 'error')
        return redirect(url_for('admin.manage_ticket_categories'))
    finally:
        db_session.close()


@admin_bp.route('/ticket-categories/bulk-update', methods=['POST'])
@super_admin_required
def bulk_update_categories():
    """Bulk update category enable/disable status and sort order"""
    db_session = SessionLocal()
    try:
        # Get all predefined categories that have configs
        predefined_configs = db_session.query(CategoryDisplayConfig).filter_by(is_predefined=True).all()
        
        # Process each predefined category
        for config in predefined_configs:
            category_key = config.category_key
            
            # Check if enabled checkbox was submitted (checked = True, not submitted = False)
            enabled_field = f'enabled_{category_key}'
            is_enabled = enabled_field in request.form and request.form[enabled_field] == 'on'
            config.is_enabled = is_enabled
            
            # Update sort order if provided
            sort_order_field = f'sort_order_{category_key}'
            if sort_order_field in request.form:
                try:
                    sort_order = int(request.form[sort_order_field])
                    config.sort_order = sort_order
                except (ValueError, TypeError):
                    pass  # Keep existing sort order if invalid
            
            config.updated_at = datetime.utcnow()
        
        db_session.commit()
        flash('Category settings updated successfully', 'success')
        
    except Exception as e:
        db_session.rollback()
        flash(f'Error updating categories: {str(e)}', 'error')
    finally:
        db_session.close()
    
    return redirect(url_for('admin.manage_ticket_categories'))


@admin_bp.route('/ticket-categories/create', methods=['GET', 'POST'])
@super_admin_required
def create_ticket_category():
    """Create a new custom ticket category"""
    if request.method == 'POST':
        db_session = SessionLocal()
        try:
            name = request.form.get('name', '').strip()
            display_name = request.form.get('display_name', '').strip()
            description = request.form.get('description', '').strip()
            enabled_sections = request.form.getlist('enabled_sections')
            
            if not name or not display_name:
                flash('Name and display name are required', 'error')
                return redirect(url_for('admin.create_ticket_category'))
            
            # Always include required sections
            required_sections = ['case_information', 'comments']
            final_sections = list(set(enabled_sections + required_sections))
            
            # Check if category name already exists
            existing = db_session.query(TicketCategoryConfig).filter_by(name=name).first()
            if existing:
                flash('A category with this name already exists', 'error')
                return redirect(url_for('admin.create_ticket_category'))
            
            # Create new category
            category = TicketCategoryConfig(
                name=name,
                display_name=display_name,
                description=description,
                created_by_id=current_user.id
            )
            category.sections_list = final_sections
            
            db_session.add(category)
            db_session.commit()
            
            flash(f'Ticket category "{display_name}" created successfully', 'success')
            return redirect(url_for('admin.manage_ticket_categories'))
            
        except Exception as e:
            db_session.rollback()
            flash(f'Error creating ticket category: {str(e)}', 'error')
            return redirect(url_for('admin.create_ticket_category'))
        finally:
            db_session.close()
    
    # GET request - show form
    available_sections = TicketCategoryConfig.get_available_sections()
    return render_template('admin/ticket_categories/create.html',
                         available_sections=available_sections)


@admin_bp.route('/ticket-categories/<int:category_id>/edit', methods=['GET', 'POST'])
@super_admin_required
def edit_ticket_category(category_id):
    """Edit an existing ticket category"""
    db_session = SessionLocal()
    try:
        category = db_session.query(TicketCategoryConfig).get(category_id)
        if not category:
            flash('Ticket category not found', 'error')
            return redirect(url_for('admin.manage_ticket_categories'))
        
        if request.method == 'POST':
            display_name = request.form.get('display_name', '').strip()
            description = request.form.get('description', '').strip()
            enabled_sections = request.form.getlist('enabled_sections')
            is_active = request.form.get('is_active') == 'on'
            
            if not display_name:
                flash('Display name is required', 'error')
                return redirect(url_for('admin.edit_ticket_category', category_id=category_id))
            
            # Always include required sections
            required_sections = ['case_information', 'comments']
            final_sections = list(set(enabled_sections + required_sections))
            
            # Update category
            category.display_name = display_name
            category.description = description
            category.is_active = is_active
            category.sections_list = final_sections
            category.updated_at = datetime.utcnow()
            
            db_session.commit()
            
            flash(f'Ticket category "{display_name}" updated successfully', 'success')
            return redirect(url_for('admin.manage_ticket_categories'))
        
        # GET request - show form
        available_sections = TicketCategoryConfig.get_available_sections()
        return render_template('admin/ticket_categories/edit.html',
                             category=category,
                             available_sections=available_sections)
                             
    except Exception as e:
        db_session.rollback()
        flash(f'Error editing ticket category: {str(e)}', 'error')
        return redirect(url_for('admin.manage_ticket_categories'))
    finally:
        db_session.close()


@admin_bp.route('/ticket-categories/<int:category_id>/delete', methods=['POST'])
@super_admin_required
def delete_ticket_category(category_id):
    """Delete a ticket category"""
    db_session = SessionLocal()
    try:
        category = db_session.query(TicketCategoryConfig).get(category_id)
        if not category:
            flash('Ticket category not found', 'error')
            return redirect(url_for('admin.manage_ticket_categories'))
        
        category_name = category.display_name
        db_session.delete(category)
        db_session.commit()
        
        flash(f'Ticket category "{category_name}" deleted successfully', 'success')
        
    except Exception as e:
        db_session.rollback()
        flash(f'Error deleting ticket category: {str(e)}', 'error')
    finally:
        db_session.close()
    
    return redirect(url_for('admin.manage_ticket_categories'))


@admin_bp.route('/ticket-categories/<int:category_id>/preview')
@super_admin_required
def preview_ticket_category(category_id):
    """Preview what a ticket form would look like for this category"""
    db_session = SessionLocal()
    try:
        category = db_session.query(TicketCategoryConfig).get(category_id)
        if not category:
            flash('Ticket category not found', 'error')
            return redirect(url_for('admin.manage_ticket_categories'))
        
        available_sections = TicketCategoryConfig.get_available_sections()
        sections_dict = {section['id']: section for section in available_sections}
        
        return render_template('admin/ticket_categories/preview.html',
                             category=category,
                             sections_dict=sections_dict)
                             
    except Exception as e:
        flash(f'Error previewing ticket category: {str(e)}', 'error')
        return redirect(url_for('admin.manage_ticket_categories'))
    finally:
        db_session.close() 

@admin_bp.route('/database/backup')
@super_admin_required
def create_database_backup():
    """Create a backup of the SQLite database"""
    try:
        # Create backups directory if it doesn't exist
        backup_dir = os.path.join(os.getcwd(), 'backups')
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir)
        
        # Get current database path
        db_path = 'inventory.db'  # Default SQLite database path
        if not os.path.exists(db_path):
            flash('Database file not found', 'error')
            return redirect(url_for('admin.system_config'))
        
        # Create backup filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_filename = f'inventory_backup_{timestamp}.db'
        backup_path = os.path.join(backup_dir, backup_filename)
        
        # Copy the database file
        shutil.copy2(db_path, backup_path)
        
        flash(f'Database backup created successfully: {backup_filename}', 'success')
        return send_file(backup_path, as_attachment=True, download_name=backup_filename)
        
    except Exception as e:
        flash(f'Error creating database backup: {str(e)}', 'error')
        return redirect(url_for('admin.system_config'))

@admin_bp.route('/database/backups')
@super_admin_required
def list_database_backups():
    """List all available database backups"""
    try:
        backup_dir = os.path.join(os.getcwd(), 'backups')
        if not os.path.exists(backup_dir):
            backups = []
        else:
            # Find all backup files
            backup_files = glob.glob(os.path.join(backup_dir, 'inventory_backup_*.db'))
            
            backups = []
            for file_path in backup_files:
                filename = os.path.basename(file_path)
                file_stat = os.stat(file_path)
                file_size = round(file_stat.st_size / (1024 * 1024), 2)  # Size in MB
                created_time = datetime.fromtimestamp(file_stat.st_ctime)
                
                backups.append({
                    'filename': filename,
                    'full_path': file_path,
                    'size_mb': file_size,
                    'created_at': created_time.strftime('%Y-%m-%d %H:%M:%S'),
                    'created_timestamp': created_time
                })
            
            # Sort by creation time (newest first)
            backups.sort(key=lambda x: x['created_timestamp'], reverse=True)
        
        return jsonify({
            'success': True,
            'backups': backups
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@admin_bp.route('/database/restore', methods=['POST'])
@super_admin_required
def restore_database():
    """Restore the database from a backup file"""
    try:
        backup_filename = request.form.get('backup_filename')
        if not backup_filename:
            flash('No backup file specified', 'error')
            return redirect(url_for('admin.system_config'))
        
        backup_dir = os.path.join(os.getcwd(), 'backups')
        backup_path = os.path.join(backup_dir, backup_filename)
        
        if not os.path.exists(backup_path):
            flash('Backup file not found', 'error')
            return redirect(url_for('admin.system_config'))
        
        # Verify it's a valid SQLite database
        try:
            conn = sqlite3.connect(backup_path)
            conn.execute("SELECT name FROM sqlite_master WHERE type='table';")
            conn.close()
        except sqlite3.Error:
            flash('Invalid database backup file', 'error')
            return redirect(url_for('admin.system_config'))
        
        # Create a backup of current database before restore
        current_db_path = 'inventory.db'
        if os.path.exists(current_db_path):
            pre_restore_backup = f'inventory_pre_restore_{datetime.now().strftime("%Y%m%d_%H%M%S")}.db'
            pre_restore_path = os.path.join(backup_dir, pre_restore_backup)
            shutil.copy2(current_db_path, pre_restore_path)
        
        # Restore the database
        shutil.copy2(backup_path, current_db_path)
        
        flash(f'Database restored successfully from {backup_filename}', 'success')
        return redirect(url_for('admin.system_config'))
        
    except Exception as e:
        flash(f'Error restoring database: {str(e)}', 'error')
        return redirect(url_for('admin.system_config'))

@admin_bp.route('/database/backup/download/<filename>')
@super_admin_required
def download_backup(filename):
    """Download a specific backup file"""
    try:
        # Sanitize filename
        safe_filename = secure_filename(filename)
        backup_dir = os.path.join(os.getcwd(), 'backups')
        backup_path = os.path.join(backup_dir, safe_filename)
        
        if not os.path.exists(backup_path):
            flash('Backup file not found', 'error')
            return redirect(url_for('admin.system_config'))
        
        return send_file(backup_path, as_attachment=True, download_name=safe_filename)
        
    except Exception as e:
        flash(f'Error downloading backup: {str(e)}', 'error')
        return redirect(url_for('admin.system_config'))

@admin_bp.route('/database/backup/delete/<filename>', methods=['POST'])
@super_admin_required
def delete_backup(filename):
    """Delete a specific backup file"""
    try:
        # Sanitize filename
        safe_filename = secure_filename(filename)
        backup_dir = os.path.join(os.getcwd(), 'backups')
        backup_path = os.path.join(backup_dir, safe_filename)
        
        if not os.path.exists(backup_path):
            flash('Backup file not found', 'error')
            return redirect(url_for('admin.system_config'))
        
        # Remove the file
        os.remove(backup_path)
        
        flash(f'Backup {safe_filename} deleted successfully', 'success')
        return redirect(url_for('admin.system_config'))
        
    except Exception as e:
        flash(f'Error deleting backup: {str(e)}', 'error')
        return redirect(url_for('admin.system_config'))

@admin_bp.route('/billing-generator')
@admin_required
def billing_generator():
    """Main billing generator page"""
    try:
        from models.ticket import Ticket
        from models.company import Company
        from models.user import Country
        from sqlalchemy import extract, func
        
        db_session = db_manager.get_session()
        
        # Get available months and years from tickets
        date_ranges = db_session.query(
            extract('year', Ticket.created_at).label('year'),
            extract('month', Ticket.created_at).label('month')
        ).distinct().order_by(
            extract('year', Ticket.created_at).desc(),
            extract('month', Ticket.created_at).desc()
        ).all()
        
        # Get all companies
        companies = db_session.query(Company).all()
        
        # Get all countries
        countries = [country.value for country in Country]
        
        return render_template('admin/billing_generator.html',
                             date_ranges=date_ranges,
                             companies=companies,
                             countries=countries)
        
    except Exception as e:
        flash(f'Error loading billing generator: {str(e)}', 'error')
        return redirect(url_for('admin.system_config'))
    finally:
        db_session.close()

@admin_bp.route('/billing-generator/tickets', methods=['POST'])
@admin_required
def get_billing_tickets():
    """Get tickets for billing based on filters"""
    try:
        from models.ticket import Ticket
        from models.user import User
        from models.company import Company
        from sqlalchemy import extract, and_, or_
        
        db_session = db_manager.get_session()
        
        # Get filter parameters
        year = request.json.get('year')
        month = request.json.get('month')
        country = request.json.get('country')
        company_id = request.json.get('company_id')
        category = request.json.get('category')
        
        # Build query
        query = db_session.query(Ticket).join(User, Ticket.requester_id == User.id)
        
        # Date filters
        if year and month:
            query = query.filter(
                and_(
                    extract('year', Ticket.created_at) == year,
                    extract('month', Ticket.created_at) == month
                )
            )
        elif year:
            query = query.filter(extract('year', Ticket.created_at) == year)
        
        # Country filter
        if country:
            query = query.filter(User.assigned_country == country)
        
        # Company filter
        if company_id:
            query = query.filter(User.company_id == company_id)
        
        # Category filter
        if category:
            query = query.filter(Ticket.category_id == category)
        
        # Get tickets
        tickets = query.all()
        
        # Convert to JSON-serializable format
        tickets_data = []
        for ticket in tickets:
            tickets_data.append({
                'id': ticket.id,
                'subject': ticket.subject,
                'status': ticket.status.value if hasattr(ticket.status, 'value') else str(ticket.status),
                'created_at': ticket.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                'requester': ticket.requester.username if ticket.requester else 'Unknown',
                'country': ticket.requester.assigned_country if ticket.requester and ticket.requester.assigned_country else 'Unknown',
                'company': ticket.requester.company.name if ticket.requester and ticket.requester.company else 'Unknown',
                'category': ticket.category.name if ticket.category else 'Unknown',
                'priority': ticket.priority.value if hasattr(ticket.priority, 'value') else str(ticket.priority) if ticket.priority else 'Normal'
            })
        
        return jsonify({
            'success': True,
            'tickets': tickets_data,
            'count': len(tickets_data)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })
    finally:
        db_session.close()

@admin_bp.route('/billing-generator/generate', methods=['POST'])
@admin_required
def generate_billing_report():
    """Generate billing report for selected tickets"""
    try:
        from models.ticket import Ticket
        from models.user import User
        from models.company import Company
        import json
        
        db_session = db_manager.get_session()
        
        # Get parameters
        ticket_ids = request.json.get('ticket_ids', [])
        year = request.json.get('year')
        month = request.json.get('month')
        
        if not ticket_ids:
            return jsonify({
                'success': False,
                'error': 'No tickets selected'
            })
        
        # Get tickets
        tickets = db_session.query(Ticket).filter(Ticket.id.in_(ticket_ids)).all()
        
        # Group tickets by country
        billing_data = {}
        
        for ticket in tickets:
            country = ticket.requester.assigned_country if ticket.requester and ticket.requester.assigned_country else 'Unknown'
            
            if country not in billing_data:
                billing_data[country] = {
                    'tickets': [],
                    'fees': {
                        'receiving_fee': 0,
                        'warehouse_storage_fee': 0,
                        'order_fee': 0,
                        'return_fee': 0,
                        'intake_fee': 0,
                        'management_fee': 0,
                        'cancelled_returns': 0,
                        'signature_fee': 0
                    },
                    'total_amount': 0,
                    'quantity': 0
                }
            
            billing_data[country]['tickets'].append({
                'id': ticket.id,
                'subject': ticket.subject,
                'status': ticket.status.value if hasattr(ticket.status, 'value') else str(ticket.status),
                'category': ticket.category.name if ticket.category else 'Unknown',
                'created_at': ticket.created_at.strftime('%Y-%m-%d')
            })
            
            billing_data[country]['quantity'] += 1
            
            # Calculate fees based on ticket category and type
            category_name = ticket.category.name if ticket.category else 'Unknown'
            
            if 'CHECKOUT' in category_name.upper():
                billing_data[country]['fees']['order_fee'] += 500  # Example fee
            elif 'RETURN' in category_name.upper():
                billing_data[country]['fees']['return_fee'] += 240
            elif 'INTAKE' in category_name.upper():
                billing_data[country]['fees']['intake_fee'] += 1100
            
            # Add receiving fee for all tickets
            billing_data[country]['fees']['receiving_fee'] += 80
            
            # Calculate warehouse storage fee (monthly)
            billing_data[country]['fees']['warehouse_storage_fee'] += 10
        
        # Calculate totals
        for country_data in billing_data.values():
            country_data['total_amount'] = sum(country_data['fees'].values())
        
        return jsonify({
            'success': True,
            'billing_data': billing_data,
            'year': year,
            'month': month,
            'month_name': datetime(int(year), int(month), 1).strftime('%B') if year and month else None
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })
    finally:
        db_session.close()

@admin_bp.route('/billing-generator/export', methods=['POST'])
@admin_required
def export_billing_report():
    """Export billing report to Excel"""
    try:
        import pandas as pd
        from io import BytesIO
        
        # Get the billing data from the request
        billing_data = request.json.get('billing_data', {})
        year = request.json.get('year')
        month = request.json.get('month')
        
        # Create Excel file in memory
        output = BytesIO()
        
        # Create a workbook and add worksheets
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            
            # Summary sheet
            summary_data = []
            for country, data in billing_data.items():
                row = {
                    'Country': country,
                    'Total Tickets': data['quantity'],
                    'Receiving Fee': data['fees']['receiving_fee'],
                    'Warehouse/Storage Fee': data['fees']['warehouse_storage_fee'],
                    'Order Fee': data['fees']['order_fee'],
                    'Return Fee': data['fees']['return_fee'],
                    'Intake Fee': data['fees']['intake_fee'],
                    'Management Fee': data['fees']['management_fee'],
                    'Total Amount': data['total_amount']
                }
                summary_data.append(row)
            
            summary_df = pd.DataFrame(summary_data)
            summary_df.to_excel(writer, sheet_name='Billing Summary', index=False)
            
            # Detailed sheets for each country
            for country, data in billing_data.items():
                if data['tickets']:
                    tickets_df = pd.DataFrame(data['tickets'])
                    sheet_name = f"{country} Details"[:31]  # Excel sheet name limit
                    tickets_df.to_excel(writer, sheet_name=sheet_name, index=False)
        
        output.seek(0)
        
        # Create filename
        filename = f"billing_report_{year}_{month:02d}.xlsx" if year and month else "billing_report.xlsx"
        
        return send_file(
            BytesIO(output.read()),
            as_attachment=True,
            download_name=filename,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        
    except Exception as e:
        flash(f'Error exporting billing report: {str(e)}', 'error')
        return redirect(url_for('admin.billing_generator'))

@admin_bp.route('/test-email', methods=['GET', 'POST'])
@super_admin_required
def test_email():
    """Test email configuration (Microsoft OAuth2 or SMTP)"""
    if request.method == 'POST':
        try:
            from utils.microsoft_email import get_microsoft_email_client
            from utils.email_sender import _send_email_via_method
            
            test_email = request.form.get('test_email')
            if not test_email:
                flash('Please provide a test email address', 'error')
                return redirect(url_for('admin.test_email'))
            
            # Test Microsoft Graph connection
            microsoft_client = get_microsoft_email_client()
            if microsoft_client:
                success, message = microsoft_client.test_connection()
                if success:
                    flash(f'Microsoft Graph connection successful: {message}', 'success')
                    
                    # Send test email
                    test_subject = 'TrueLog Email Test - Microsoft OAuth2'
                    test_html = f"""
                    <h2>Email Test Successful!</h2>
                    <p>This email was sent using Microsoft Graph API with OAuth2 authentication.</p>
                    <p><strong>Sent to:</strong> {test_email}</p>
                    <p><strong>Time:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                    <p>Your Microsoft 365 email integration is working correctly!</p>
                    """
                    
                    result = _send_email_via_method(
                        to_emails=test_email,
                        subject=test_subject,
                        html_body=test_html,
                        text_body="Email test successful! Microsoft OAuth2 is working."
                    )
                    
                    if result:
                        flash(f'Test email sent successfully to {test_email}', 'success')
                    else:
                        flash('Failed to send test email', 'error')
                        
                else:
                    flash(f'Microsoft Graph connection failed: {message}', 'error')
            else:
                flash('Microsoft email client not configured. Using SMTP fallback.', 'warning')
                
                # Test SMTP fallback
                try:
                    result = _send_email_via_method(
                        to_emails=test_email,
                        subject='TrueLog Email Test - SMTP Fallback',
                        html_body=f"""
                        <h2>SMTP Email Test</h2>
                        <p>This email was sent using SMTP fallback.</p>
                        <p><strong>Sent to:</strong> {test_email}</p>
                        <p><strong>Time:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                        """,
                        text_body="SMTP email test successful!"
                    )
                    
                    if result:
                        flash(f'Test email sent successfully via SMTP to {test_email}', 'success')
                    else:
                        flash('Failed to send test email via SMTP', 'error')
                        
                except Exception as smtp_error:
                    flash(f'SMTP test failed: {str(smtp_error)}', 'error')
            
        except Exception as e:
            flash(f'Error testing email: {str(e)}', 'error')
        
        return redirect(url_for('admin.test_email'))
    
    # GET request - show test form
    import os
    config_with_ms = dict(current_app.config)
    config_with_ms.update({
        'MS_CLIENT_ID': os.getenv('MS_CLIENT_ID'),
        'MS_CLIENT_SECRET': os.getenv('MS_CLIENT_SECRET'),
        'MS_TENANT_ID': os.getenv('MS_TENANT_ID'),
        'MS_FROM_EMAIL': os.getenv('MS_FROM_EMAIL'),
    })
    return render_template('admin/test_email.html', config=config_with_ms)


@admin_bp.route('/csv-import')
@admin_required
def csv_import():
    """CSV Import for Asset Checkout Tickets"""
    return render_template('admin/csv_import.html')


@admin_bp.route('/csv-import/upload', methods=['POST'])
@admin_required 
def csv_import_upload():
    """Upload and parse CSV file for ticket import"""
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'No file provided'})
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'})
        
        if not file.filename.lower().endswith('.csv'):
            return jsonify({'success': False, 'error': 'File must be a CSV'})
        
        # Generate unique file ID
        import uuid
        file_id = str(uuid.uuid4())
        
        # Read and parse CSV
        csv_content = file.read().decode('utf-8')
        csv_reader = csv.DictReader(io.StringIO(csv_content))
        
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
            existing_tickets = db_session.query(Ticket.firstbaseorderid).filter(
                Ticket.firstbaseorderid.isnot(None)
            ).all()
            existing_order_ids = {ticket.firstbaseorderid for ticket in existing_tickets}
        except:
            existing_order_ids = set()
        finally:
            db_session.close()

        # Mark tickets as duplicate or processing, and check for empty names
        duplicate_count = 0
        processing_count = 0
        empty_name_count = 0
        for row in display_data:
            order_id = row.get('order_id', '').strip()
            status = row.get('status', '').upper()
            person_name = row.get('person_name', '').strip()

            row['is_duplicate'] = order_id and order_id in existing_order_ids
            row['is_processing'] = status == 'PROCESSING'
            row['cannot_import'] = row['is_duplicate'] or row['is_processing']

            if row['is_duplicate']:
                duplicate_count += 1
            if row['is_processing']:
                processing_count += 1
            if not person_name:
                empty_name_count += 1
        
        # Store in temporary file with file_id
        temp_file = os.path.join(tempfile.gettempdir(), f'csv_import_{file_id}.json')
        with open(temp_file, 'w') as f:
            json.dump(display_data, f)
        
        # Clean up old files (older than 1 hour)
        cleanup_old_csv_files()
        
        # Calculate importable count
        cannot_import_count = sum(1 for row in display_data if row.get('cannot_import', False))
        importable_count = len(display_data) - cannot_import_count

        return jsonify({
            'success': True,
            'file_id': file_id,
            'total_rows': len(display_data),
            'grouped_orders': len(grouped_data),
            'individual_rows': len(individual_data),
            'duplicate_count': duplicate_count,
            'processing_count': processing_count,
            'empty_name_count': empty_name_count,
            'importable_count': importable_count,
            'data': display_data,  # Include the actual data for display
            'message': f'Successfully processed {len(raw_data)} rows into {len(display_data)} tickets ({len(grouped_data)} grouped orders, {len(individual_data)} individual items)'
        })
        
    except Exception as e:
        logger.info("Error in CSV upload: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': f'Failed to process CSV: {str(e)}'})


@admin_bp.route('/csv-import/load-data', methods=['GET'])
@admin_required
def csv_import_load_data():
    """Load CSV data from a file_id parameter"""
    try:
        file_id = request.args.get('file_id')

        if not file_id:
            return jsonify({'success': False, 'error': 'Missing file_id parameter'})

        # Load data from temporary file
        temp_file = os.path.join(tempfile.gettempdir(), f'csv_import_{file_id}.json')

        if not os.path.exists(temp_file):
            return jsonify({'success': False, 'error': 'CSV data not found. The file may have expired. Please upload again.'})

        with open(temp_file, 'r') as f:
            display_data = json.load(f)

        # Calculate statistics
        duplicate_count = sum(1 for row in display_data if row.get('is_duplicate', False))
        processing_count = sum(1 for row in display_data if row.get('is_processing', False))
        cannot_import_count = sum(1 for row in display_data if row.get('cannot_import', False))
        importable_count = len(display_data) - cannot_import_count

        return jsonify({
            'success': True,
            'file_id': file_id,
            'total_count': len(display_data),
            'duplicate_count': duplicate_count,
            'processing_count': processing_count,
            'importable_count': importable_count,
            'data': display_data
        })

    except Exception as e:
        logger.error(f"Error loading CSV data: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': f'Failed to load CSV data: {str(e)}'})


def cleanup_old_csv_files():
    """Clean up CSV files older than 1 hour"""
    try:
        import time
        temp_dir = tempfile.gettempdir()
        current_time = time.time()
        
        for filename in os.listdir(temp_dir):
            if filename.startswith('csv_import_') and filename.endswith('.json'):
                file_path = os.path.join(temp_dir, filename)
                file_time = os.path.getmtime(file_path)
                # Remove files older than 1 hour (3600 seconds)
                if current_time - file_time > 3600:
                    try:
                        os.remove(file_path)
                        logger.info("Cleaned up old CSV file: {filename}")
                    except Exception as e:
                        logger.info("Failed to clean up file {filename}: {e}")
    except Exception as e:
        logger.info("Error in cleanup: {e}")

def clean_csv_row(row):
    """Clean and validate a CSV row"""
    try:
        # Required fields for validation
        required_fields = ['product_title', 'org_name']
        
        # Clean whitespace and handle quoted empty values
        cleaned = {}
        for key, value in row.items():
            if value is None:
                cleaned[key] = ''
            else:
                # Strip whitespace and handle quoted spaces like " "
                cleaned_value = str(value).strip()
                if cleaned_value in ['" "', "'  '", '""', "''"]:
                    cleaned_value = ''
                cleaned[key] = cleaned_value
        
        # Check if required fields are present and non-empty
        for field in required_fields:
            if not cleaned.get(field):
                logger.info("Skipping row due to missing {field}: {cleaned}")
                return None
        
        # Set default values for missing fields
        defaults = {
            'person_name': cleaned.get('person_name') or '',  # Keep empty to allow validation
            'primary_email': cleaned.get('primary_email') or '',
            'phone_number': cleaned.get('phone_number') or '',
            'category_code': cleaned.get('category_code') or 'GENERAL',
            'brand': cleaned.get('brand') or '',
            'serial_number': cleaned.get('serial_number') or '',
            'preferred_condition': cleaned.get('preferred_condition') or 'Good',
            'priority': cleaned.get('priority') or '1',
            'order_id': cleaned.get('order_id') or '',
            'order_item_id': cleaned.get('order_item_id') or '',
            'organization_id': cleaned.get('organization_id') or '',
            'status': cleaned.get('status') or 'Pending',
            'start_date': cleaned.get('start_date') or '',
            'shipped_date': cleaned.get('shipped_date') or '',
            'delivery_date': cleaned.get('delivery_date') or '',
            'office_name': cleaned.get('office_name') or '',
            'address_line1': cleaned.get('address_line1') or '',
            'address_line2': cleaned.get('address_line2') or '',
            'city': cleaned.get('city') or '',
            'state': cleaned.get('state') or '',
            'postal_code': cleaned.get('postal_code') or '',
            'country_code': cleaned.get('country_code') or '',
            'carrier': cleaned.get('carrier') or '',
            'tracking_link': cleaned.get('tracking_link') or ''
        }
        
        # Update cleaned row with defaults
        for key, default_value in defaults.items():
            if not cleaned.get(key):
                cleaned[key] = default_value
        
        return cleaned
        
    except Exception as e:
        logger.info("Error cleaning row: {e}")
        return None

def group_orders_by_id(data):
    """Group CSV rows by order_id"""
    try:
        order_groups = {}
        individual_items = []
        
        # Group by order_id
        for row in data:
            order_id = row.get('order_id', '').strip()
            if order_id:
                if order_id not in order_groups:
                    order_groups[order_id] = []
                order_groups[order_id].append(row)
            else:
                # No order_id, treat as individual
                individual_items.append(row)
        
        grouped_orders = []
        
        # Process groups
        for order_id, items in order_groups.items():
            if len(items) > 1:
                # Multiple items - create grouped order
                primary_item = items[0]  # Use first item as primary
                
                # Create item summary
                product_titles = [item['product_title'] for item in items]
                if len(product_titles) <= 3:
                    title_summary = ', '.join(product_titles)
                else:
                    title_summary = f"{', '.join(product_titles[:2])} and {len(product_titles) - 2} more..."
                
                grouped_order = {
                    'is_grouped': True,
                    'order_id': order_id,
                    'item_count': len(items),
                    'title_summary': title_summary,
                    'all_items': items,
                    # Include primary item data for compatibility
                    **primary_item
                }
                grouped_orders.append(grouped_order)
            else:
                # Single item, add to individual
                item = items[0]
                item['is_grouped'] = False
                individual_items.append(item)
        
        # Mark individual items
        for item in individual_items:
            if 'is_grouped' not in item:
                item['is_grouped'] = False
        
        return grouped_orders, individual_items
        
    except Exception as e:
        logger.info("Error grouping orders: {e}")
        return [], data

@admin_bp.route('/csv-import/preview-ticket', methods=['POST'])
@admin_required
def csv_import_preview_ticket():
    """Preview a single ticket from CSV data with enhanced features"""
    try:
        data = request.json
        row_index = data.get('row_index')
        is_grouped = data.get('is_grouped', False)
        file_id = data.get('file_id')
        
        if file_id is None or row_index is None:
            return jsonify({'success': False, 'error': 'Missing file_id or row_index'})
            
        # Load data from file
        temp_file = os.path.join(tempfile.gettempdir(), f'csv_import_{file_id}.json')
        if not os.path.exists(temp_file):
            return jsonify({'success': False, 'error': 'CSV data not found. Please re-upload your file.'})
            
        with open(temp_file, 'r') as f:
            csv_data = json.load(f)
        
        if row_index >= len(csv_data):
            return jsonify({'success': False, 'error': 'Invalid row index'})
            
        row = csv_data[row_index]
        
        if is_grouped:
            all_items = row.get('all_items', [row])
            if not all_items or len(all_items) == 0:
                return jsonify({'success': False, 'error': 'No items found in grouped order'})
            primary_item = all_items[0]
            if not primary_item:
                return jsonify({'success': False, 'error': 'Primary item is null in grouped order'})
        else:
            all_items = [row]
            primary_item = row
            
        # Validate that primary_item has required fields
        if not primary_item or not primary_item.get('product_title'):
            return jsonify({'success': False, 'error': f'Invalid item data: {primary_item}'})
        
        # Enhanced category mapping with queue routing
        def determine_category_and_queue(product_title, category_code):
            """Determine category and queue based on product type"""
            product_lower = product_title.lower()
            category_lower = category_code.lower() if category_code else ""
            
            # Accessory detection patterns
            accessory_keywords = [
                'adapter', 'cable', 'charger', 'mouse', 'keyboard', 'headset', 
                'webcam', 'dock', 'hub', 'dongle', 'stand', 'pad', 'cover',
                'case', 'sleeve', 'bag', 'power supply', 'cord', 'usb'
            ]
            
            # Computer/laptop detection patterns  
            computer_keywords = [
                'macbook', 'laptop', 'computer', 'imac', 'pc', 'desktop', 
                'workstation', 'tower', 'all-in-one', 'surface', 'thinkpad'
            ]
            
            # Check if it's an accessory
            is_accessory = (
                any(keyword in product_lower for keyword in accessory_keywords) or
                any(keyword in category_lower for keyword in ['accessory', 'peripheral', 'cable', 'adapter'])
            )
            
            # Check if it's a computer/laptop
            is_computer = (
                any(keyword in product_lower for keyword in computer_keywords) or
                any(keyword in category_lower for keyword in ['computer', 'laptop', 'desktop'])
            )
            
            if is_accessory:
                return 'ASSET_CHECKOUT_CLAW', 'Checkout Accessories'
            elif is_computer:
                return 'ASSET_CHECKOUT_CLAW', 'Tech Asset'
            else:
                return 'ASSET_CHECKOUT_CLAW', 'General'
        
        # Check inventory for each item
        db_session = db_manager.get_session()
        try:
            inventory_info = []
            for item in all_items:
                product_title = item.get('product_title', '')
                serial_number = item.get('serial_number', '')
                brand = item.get('brand', '')
                category = item.get('category_code', '')
                
                # Initialize matches list
                matches = []
                
                # Search for matching assets in inventory
                asset_query = db_session.query(Asset)
                
                # 1. Search by serial number (highest priority for assets)
                if serial_number:
                    serial_matches = asset_query.filter(
                        Asset.serial_num.ilike(f'%{serial_number}%')
                    ).all()
                    
                    for asset in serial_matches:
                        # Check availability status
                        is_available = asset.status and asset.status.value in ['In Stock', 'Ready to Deploy']
                        status_display = asset.status.value if asset.status else 'Unknown'
                        availability_text = f"Available ({status_display})" if is_available else f"Not Available ({status_display})"
                        
                        matches.append({
                            'match_type': 'Serial Number (Asset)',
                            'item_type': 'asset',
                            'id': asset.id,
                            'name': asset.name or asset.model,
                            'identifier': f"Tag: {asset.asset_tag or 'N/A'} | Serial: {asset.serial_num or 'N/A'}",
                            'availability': availability_text,
                            'is_available': is_available,
                            'confidence': 'High'
                        })
                
                # 2. Search by product name in assets (medium priority) - IMPROVED ALGORITHM
                if product_title and len(matches) < 3:
                    # First try exact phrase matches (highest relevance)
                    exact_phrase_matches = asset_query.filter(
                        or_(
                            Asset.name.ilike(f'%{product_title}%'),
                            Asset.model.ilike(f'%{product_title}%'),
                            Asset.hardware_type.ilike(f'%{product_title}%')
                        )
                    ).limit(3).all()
                    
                    for asset in exact_phrase_matches:
                        if not any(m.get('id') == asset.id and m.get('item_type') == 'asset' for m in matches):
                            is_available = asset.status and asset.status.value in ['In Stock', 'Ready to Deploy']
                            status_display = asset.status.value if asset.status else 'Unknown'
                            availability_text = f"Available ({status_display})" if is_available else f"Not Available ({status_display})"
                            
                            matches.append({
                                'match_type': 'Exact Phrase (Asset)',
                                'item_type': 'asset',
                                'id': asset.id,
                                'name': asset.name or asset.model,
                                'identifier': f"Tag: {asset.asset_tag or 'N/A'} | Serial: {asset.serial_num or 'N/A'}",
                                'availability': availability_text,
                                'is_available': is_available,
                                'confidence': 'High'
                            })
                    
                    # If still need more matches, try smart keyword matching
                    if len(matches) < 3:
                        # Extract meaningful keywords (filter out common words)
                        common_words = {'with', 'and', 'or', 'the', 'a', 'an', 'in', 'on', 'at', 'to', 'for', 'of', 'by', 'from'}
                        search_terms = [term.lower() for term in product_title.split() 
                                      if len(term) > 3 and term.lower() not in common_words]
                        
                        # Only proceed if we have meaningful terms
                        if search_terms:
                            # Create a query that requires multiple term matches for better relevance
                            conditions = []
                            for term in search_terms[:3]:  # Limit to first 3 meaningful terms
                                conditions.append(
                                    or_(
                                        Asset.name.ilike(f'%{term}%'),
                                        Asset.model.ilike(f'%{term}%'),
                                        Asset.hardware_type.ilike(f'%{term}%'),
                                        Asset.manufacturer.ilike(f'%{term}%')
                                    )
                                )
                            
                            # Try to find assets that match multiple terms
                            if len(conditions) >= 2:
                                multi_term_matches = asset_query.filter(
                                    and_(*conditions[:2])  # Require at least 2 terms to match
                                ).limit(2).all()
                                
                                for asset in multi_term_matches:
                                    if not any(m.get('id') == asset.id and m.get('item_type') == 'asset' for m in matches):
                                        is_available = asset.status and asset.status.value in ['In Stock', 'Ready to Deploy']
                                        status_display = asset.status.value if asset.status else 'Unknown'
                                        availability_text = f"Available ({status_display})" if is_available else f"Not Available ({status_display})"
                                        
                                        matches.append({
                                            'match_type': 'Multi-term Match (Asset)',
                                            'item_type': 'asset',
                                            'id': asset.id,
                                            'name': asset.name or asset.model,
                                            'identifier': f"Tag: {asset.asset_tag or 'N/A'} | Serial: {asset.serial_num or 'N/A'}",
                                            'availability': availability_text,
                                            'is_available': is_available,
                                            'confidence': 'Medium'
                                        })
                
                # 3. Search by brand in assets (lower priority)
                if brand and len(matches) < 3:
                    brand_matches = asset_query.filter(
                        Asset.manufacturer.ilike(f'%{brand}%')
                    ).limit(2).all()
                    
                    for asset in brand_matches:
                        if not any(m.get('id') == asset.id and m.get('item_type') == 'asset' for m in matches):
                            is_available = asset.status and asset.status.value in ['In Stock', 'Ready to Deploy']
                            status_display = asset.status.value if asset.status else 'Unknown'
                            availability_text = f"Available ({status_display})" if is_available else f"Not Available ({status_display})"
                            
                            matches.append({
                                'match_type': 'Brand (Asset)',
                                'item_type': 'asset',
                                'id': asset.id,
                                'name': asset.name or asset.model,
                                'identifier': f"Tag: {asset.asset_tag or 'N/A'} | Serial: {asset.serial_num or 'N/A'}",
                                'availability': availability_text,
                                'is_available': is_available,
                                'confidence': 'Low'
                            })
                
                # 4. Search for accessories - IMPROVED ALGORITHM
                from models.accessory_alias import AccessoryAlias
                accessory_query = db_session.query(Accessory)

                # Debug logging for accessory matching
                logger.info(f"CSV_ACCESSORY_DEBUG: Searching for accessories with product_title='{product_title}'")

                # Search by exact product name in accessories (highest priority)
                if product_title:
                    # First try exact phrase matches (including aliases)
                    # Get accessories that match by name, model, or alias
                    alias_subquery = db_session.query(AccessoryAlias.accessory_id).filter(
                        AccessoryAlias.alias_name.ilike(f'%{product_title}%')
                    ).subquery()

                    exact_accessory_matches = accessory_query.filter(
                        or_(
                            Accessory.name.ilike(f'%{product_title}%'),
                            Accessory.model_no.ilike(f'%{product_title}%'),
                            Accessory.id.in_(alias_subquery)
                        )
                    ).limit(3).all()
                    
                    logger.info(f"CSV_ACCESSORY_DEBUG: Found {len(exact_accessory_matches)} exact phrase matches")

                    for accessory in exact_accessory_matches:
                        is_available = accessory.available_quantity > 0
                        availability_text = f"Available (Qty: {accessory.available_quantity})" if is_available else "Out of Stock"

                        # Check if this match was via alias
                        matched_via_alias = False
                        matched_alias_name = None
                        for alias in accessory.aliases:
                            if product_title.lower() in alias.alias_name.lower():
                                matched_via_alias = True
                                matched_alias_name = alias.alias_name
                                break

                        match_type = 'Exact Phrase (Accessory - Alias)' if matched_via_alias else 'Exact Phrase (Accessory)'
                        identifier = f"Category: {accessory.category or 'N/A'} | Model: {accessory.model_no or 'N/A'}"
                        if matched_via_alias:
                            identifier = f"Matched via alias: {matched_alias_name} | {identifier}"

                        matches.append({
                            'match_type': match_type,
                            'item_type': 'accessory',
                            'id': accessory.id,
                            'name': accessory.name,
                            'identifier': identifier,
                            'availability': availability_text,
                            'is_available': is_available,
                            'confidence': 'High'
                        })
                
                # 5. Search accessories by intelligent keyword matching
                if len(matches) < 5:
                    # Extract meaningful keywords (filter out common words)
                    common_words = {'with', 'and', 'or', 'the', 'a', 'an', 'in', 'on', 'at', 'to', 'for', 'of', 'by', 'from'}
                    search_terms = [term.lower() for term in product_title.split()
                                  if len(term) > 3 and term.lower() not in common_words] if product_title else []

                    logger.info(f"CSV_ACCESSORY_DEBUG: Intelligent search terms: {search_terms}")

                    if search_terms:
                        # Try multi-term matching for better relevance
                        conditions = []
                        for term in search_terms[:3]:  # Limit to first 3 meaningful terms
                            # Create subquery for alias matching
                            alias_term_subquery = db_session.query(AccessoryAlias.accessory_id).filter(
                                AccessoryAlias.alias_name.ilike(f'%{term}%')
                            ).subquery()

                            conditions.append(
                                or_(
                                    Accessory.name.ilike(f'%{term}%'),
                                    Accessory.category.ilike(f'%{term}%'),
                                    Accessory.manufacturer.ilike(f'%{term}%'),
                                    Accessory.model_no.ilike(f'%{term}%'),
                                    Accessory.id.in_(alias_term_subquery)
                                )
                            )

                        # Try to find accessories that match multiple terms
                        if len(conditions) >= 2:
                            logger.info(f"CSV_ACCESSORY_DEBUG: Searching for multi-term matches")
                            multi_term_accessory_matches = accessory_query.filter(
                                and_(*conditions[:2])  # Require at least 2 terms to match
                            ).limit(2).all()
                            
                            for accessory in multi_term_accessory_matches:
                                if not any(m.get('id') == accessory.id and m.get('item_type') == 'accessory' for m in matches):
                                    is_available = accessory.available_quantity > 0
                                    availability_text = f"Available (Qty: {accessory.available_quantity})" if is_available else "Out of Stock"
                                    
                                    matches.append({
                                        'match_type': 'Multi-term Match (Accessory)',
                                        'item_type': 'accessory',
                                        'id': accessory.id,
                                        'name': accessory.name,
                                        'identifier': f"Category: {accessory.category or 'N/A'} | Model: {accessory.model_no or 'N/A'}",
                                        'availability': availability_text,
                                        'is_available': is_available,
                                        'confidence': 'Medium'
                                    })
                        
                        # If still need matches, try single meaningful term matches (lower priority)
                        elif len(matches) < 5 and search_terms:
                            # Use only the most specific term (usually the product type)
                            primary_term = search_terms[0]  # Usually the most important term
                            logger.info(f"CSV_ACCESSORY_DEBUG: Searching single term matches for: '{primary_term}'")

                            # Create subquery for alias matching
                            alias_single_subquery = db_session.query(AccessoryAlias.accessory_id).filter(
                                AccessoryAlias.alias_name.ilike(f'%{primary_term}%')
                            ).subquery()

                            single_term_matches = accessory_query.filter(
                                or_(
                                    Accessory.name.ilike(f'%{primary_term}%'),
                                    Accessory.category.ilike(f'%{primary_term}%'),
                                    Accessory.manufacturer.ilike(f'%{primary_term}%'),
                                    Accessory.model_no.ilike(f'%{primary_term}%'),
                                    Accessory.id.in_(alias_single_subquery)
                                )
                            ).limit(2).all()
                            
                            for accessory in single_term_matches:
                                if not any(m.get('id') == accessory.id and m.get('item_type') == 'accessory' for m in matches):
                                    is_available = accessory.available_quantity > 0
                                    availability_text = f"Available (Qty: {accessory.available_quantity})" if is_available else "Out of Stock"
                                    
                                    matches.append({
                                        'match_type': 'Single Term Match (Accessory)',
                                        'item_type': 'accessory',
                                        'id': accessory.id,
                                        'name': accessory.name,
                                        'identifier': f"Category: {accessory.category or 'N/A'} | Model: {accessory.model_no or 'N/A'}",
                                        'availability': availability_text,
                                        'is_available': is_available,
                                        'confidence': 'Low'
                                    })
                
                # 6. Search accessories by brand
                if brand and len(matches) < 5:
                    brand_accessory_matches = accessory_query.filter(
                        Accessory.manufacturer.ilike(f'%{brand}%')
                    ).limit(2).all()
                    
                    for accessory in brand_accessory_matches:
                        if not any(m.get('id') == accessory.id and m.get('item_type') == 'accessory' for m in matches):
                            is_available = accessory.available_quantity > 0
                            availability_text = f"Available (Qty: {accessory.available_quantity})" if is_available else "Out of Stock"
                            
                            matches.append({
                                'match_type': 'Brand (Accessory)',
                                'item_type': 'accessory',
                                'id': accessory.id,
                                'name': accessory.name,
                                'identifier': f"Category: {accessory.category or 'N/A'} | Model: {accessory.model_no or 'N/A'}",
                                'availability': availability_text,
                                'is_available': is_available,
                                'confidence': 'Low'
                            })
                
                # Determine overall stock status
                if matches:
                    # Check if any match is available
                    available_matches = [m for m in matches if m.get('is_available', False)]
                    if available_matches:
                        stock_status = "In Stock"
                    else:
                        stock_status = "Found but Not Available"
                else:
                    stock_status = "Not Found"
                
                inventory_info.append({
                    'product_title': product_title,
                    'serial_number': serial_number,
                    'brand': brand,
                    'category': category,
                    'matches': matches[:5],  # Limit to top 5 matches
                    'stock_status': stock_status
                })
        finally:
            db_session.close()
        
        # Determine category and suggested queue
        primary_category, suggested_queue = determine_category_and_queue(
            primary_item.get('product_title', ''),
            primary_item.get('category_code', '')
        )
        
        # Get available queues for selection
        available_queues = []
        queue_session = db_manager.get_session()
        try:
            queues = queue_session.query(Queue).all()
            for queue in queues:
                available_queues.append({
                    'id': queue.id,
                    'name': queue.name,
                    'description': queue.description,
                    'suggested': queue.name == suggested_queue
                })
        finally:
            queue_session.close()
        
        # Get all users for case owner selection (admin and super admin only)
        available_users = []
        user_session = db_manager.get_session()
        try:
            from models.user import User
            from models.enums import UserType
            from flask_login import current_user
            
            # Check if user is admin or super admin
            is_admin = current_user.is_admin or current_user.is_super_admin
            
            if is_admin:
                all_users = user_session.query(User).all()
                for user in all_users:
                    available_users.append({
                        'id': user.id,
                        'name': user.username,
                        'email': user.email,
                        'is_current': user.id == current_user.id
                    })
        except Exception as e:
            logger.info("Error getting users for case owner selection: {str(e)}")
            import traceback
            traceback.print_exc()
        finally:
            user_session.close()
        
        # Create enhanced ticket preview
        if is_grouped:
            subject = f"Asset Checkout - Order {row['order_id']} ({row['item_count']} items)"
            description = f"Multi-item asset checkout request for {primary_item['person_name']} from {primary_item['org_name']} - {row['item_count']} items total"
            
            # Create asset list for grouped items
            asset_list = []
            for item in all_items:
                asset_list.append({
                    'product_title': item['product_title'],
                    'brand': item['brand'],
                    'serial_number': item['serial_number'],
                    'category': item['category_code'],
                    'condition': item['preferred_condition'] or 'Good'
                })
        else:
            subject = f"Asset Checkout - {row['product_title']}"
            description = f"Asset checkout request for {row['person_name']} from {row['org_name']}"
            asset_list = [{
                'product_title': row['product_title'],
                'brand': row['brand'],
                'serial_number': row['serial_number'],
                'category': row['category_code'],
                'condition': row['preferred_condition'] or 'Good'
            }]
        
        # Format shipping address
        shipping_address = f"""{primary_item['office_name']}
{primary_item['address_line1']}
{primary_item['address_line2']}
{primary_item['city']}, {primary_item['state']} {primary_item['postal_code']}
{primary_item['country_code']}""".strip()

        # Format order details for notes
        order_notes = f"""Order Details:
- Order ID: {primary_item['order_id']}
- Organization ID: {primary_item['organization_id']}
- Status: {primary_item['status']}
- Start Date: {primary_item['start_date'] or 'Not specified'}
- Shipped Date: {primary_item['shipped_date'] or 'Not specified'}
- Delivery Date: {primary_item['delivery_date'] or 'Not specified'}
- Carrier: {primary_item['carrier'] or 'Not specified'}
- Tracking: {primary_item['tracking_link'] or 'Not provided'}"""

        # Check if person_name is empty
        person_name = primary_item.get('person_name', '').strip() if primary_item.get('person_name') else ''
        name_is_empty = not person_name

        # Log if name is empty for debugging
        if name_is_empty:
            logger.info(f"CSV Import Preview: Empty customer name detected for order {primary_item.get('order_id')}")

        ticket_preview = {
            'subject': subject,
            'description': description,
            'category': primary_category,
            'priority': 'MEDIUM' if primary_item['priority'] == '2' else 'LOW',
            'status': 'OPEN',
            'is_grouped': is_grouped,
            'item_count': len(all_items),
            'customer_info': {
                'name': person_name,
                'email': primary_item['primary_email'],
                'phone': primary_item['phone_number'],
                'company': primary_item['org_name']
            },
            'name_is_empty': name_is_empty,
            'asset_info': asset_list[0],  # Always provide first asset for compatibility
            'all_assets': asset_list,  # All assets for grouped display
            'shipping_address': shipping_address,
            'notes': order_notes,
            'available_queues': available_queues,
            'suggested_queue_id': next((q['id'] for q in available_queues if q['suggested']), None),
            'available_users': available_users,
            'inventory_info': inventory_info,
            'shipping_info': {
                'office_name': primary_item['office_name'],
                'address_line1': primary_item['address_line1'],
                'address_line2': primary_item['address_line2'],
                'city': primary_item['city'],
                'state': primary_item['state'],
                'postal_code': primary_item['postal_code'],
                'country_code': primary_item['country_code'],
                'carrier': primary_item['carrier'],
                'tracking_link': primary_item['tracking_link'],
                'shipped_date': primary_item['shipped_date'],
                'delivery_date': primary_item['delivery_date']
            },
            'order_info': {
                'order_id': primary_item['order_id'],
                'order_item_id': primary_item.get('order_item_id'),
                'organization_id': primary_item['organization_id'],
                'status': primary_item['status'],
                'start_date': primary_item['start_date'],
                'shipped_date': primary_item['shipped_date'],
                'delivery_date': primary_item['delivery_date']
            }
        }
        
        return jsonify({'success': True, 'preview': ticket_preview})
        
    except Exception as e:
        logger.info("Error in preview: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': f'Failed to generate preview: {str(e)}'})

@admin_bp.route('/csv-import/import-ticket', methods=['POST'])
@admin_required
def csv_import_import_ticket():
    """Import a ticket from CSV data with enhanced data flow"""
    try:
        data = request.json
        row_index = data.get('row_index')
        is_grouped = data.get('is_grouped', False)
        file_id = data.get('file_id')
        selected_queue_id = data.get('queue_id')  # Get selected queue
        selected_case_owner_id = data.get('case_owner_id')  # Get selected case owner
        selected_accessories = data.get('selected_accessories', [])  # Get selected accessories
        selected_assets = data.get('selected_assets', [])  # Get selected assets
        updated_customer_name = data.get('updated_customer_name')  # Get updated customer name if provided

        # Add logging to see what we're receiving
        import logging
        logging.basicConfig(level=logging.INFO)
        logger = logging.getLogger(__name__)
        logger.info(f"[CSV IMPORT] Received {len(selected_accessories)} accessories and {len(selected_assets)} assets")
        logger.info("[CSV IMPORT] Received {len(selected_accessories)} accessories and {len(selected_assets)} assets")
        logger.info("[CSV IMPORT] Selected assets data: {selected_assets}")
        if updated_customer_name:
            logger.info(f"[CSV IMPORT] Updated customer name: {updated_customer_name}")
        
        if file_id is None or row_index is None:
            return jsonify({'success': False, 'error': 'Missing file_id or row_index'})
        
        # Load data from file
        temp_file = os.path.join(tempfile.gettempdir(), f'csv_import_{file_id}.json')
        if not os.path.exists(temp_file):
            return jsonify({'success': False, 'error': 'CSV data not found. Please re-upload your file.'})
            
        with open(temp_file, 'r') as f:
            csv_data = json.load(f)
        
        if row_index >= len(csv_data):
            return jsonify({'success': False, 'error': 'Invalid row index'})
            
        row = csv_data[row_index]
        
        # Check if the ticket has PROCESSING status and block import
        if row.get('status') == 'PROCESSING':
            return jsonify({
                'success': False, 
                'error': 'Cannot import tickets with PROCESSING status. Please wait for the order to progress to another status before importing.'
            })
        
        if is_grouped:
            all_items = row.get('all_items', [row])
            if not all_items or len(all_items) == 0:
                return jsonify({'success': False, 'error': 'No items found in grouped order'})
            
            # Check if any item in grouped order has PROCESSING status
            for item in all_items:
                if item.get('status') == 'PROCESSING':
                    return jsonify({
                        'success': False, 
                        'error': 'Cannot import tickets with PROCESSING status. One or more items in this order are still processing.'
                    })
        else:
            all_items = [row]
        
        primary_item = all_items[0]
        
        db_session = db_manager.get_session()
        try:
            # Configure SQLite for better concurrency
            from sqlalchemy import text
            db_session.execute(text("PRAGMA journal_mode=WAL;"))
            db_session.execute(text("PRAGMA synchronous=NORMAL;"))
            db_session.execute(text("PRAGMA busy_timeout=30000;"))  # 30 second timeout
            
            # 1. CREATE CUSTOMER FIRST (as requested)
            from models.customer_user import CustomerUser
            from models.company import Company

            # Check if customer already exists
            customer = db_session.query(CustomerUser).filter(
                CustomerUser.email == primary_item['primary_email']
            ).first()

            customer_created = False
            if not customer:
                # Get or create company (normalize name to uppercase for comparison)
                org_name = primary_item.get('org_name', '').strip().upper() if primary_item.get('org_name') else None
                company = None
                if org_name:
                    company = db_session.query(Company).filter(
                        Company.name == org_name
                    ).first()

                if not company and org_name:
                    company = Company(
                        name=org_name,
                        description=f"Auto-created from CSV import",
                        contact_email=primary_item['primary_email']
                    )
                    db_session.add(company)
                    db_session.flush()
                
                # Create customer with address from shipping information
                customer_address = f"{primary_item.get('address_line1', '')}\n{primary_item.get('address_line2', '')}\n{primary_item.get('city', '')}, {primary_item.get('state', '')} {primary_item.get('postal_code', '')}\n{primary_item.get('country_code', '')}".strip()
                if not customer_address or customer_address.replace('\n', '').replace(',', '').strip() == '':
                    customer_address = "Address not provided"
                
                # Map city to country as requested by user, with fallback to country_code
                city_to_country_mapping = {
                    'Singapore': Country.SINGAPORE,
                    'Kuala Lumpur': Country.MALAYSIA,
                    'Bangkok': Country.THAILAND,
                    'Manila': Country.PHILIPPINES,
                    'Jakarta': Country.INDONESIA,
                    'Ho Chi Minh City': Country.VIETNAM,
                    'Hanoi': Country.VIETNAM,
                    'Seoul': Country.SOUTH_KOREA,
                    'Tokyo': Country.JAPAN,
                    'Osaka': Country.JAPAN,
                    'Sydney': Country.AUSTRALIA,
                    'Melbourne': Country.AUSTRALIA,
                    'Mumbai': Country.INDIA,
                    'Delhi': Country.INDIA,
                    'Bangalore': Country.INDIA,
                    'Tel Aviv': Country.ISRAEL,
                    'Jerusalem': Country.ISRAEL,
                    'Toronto': Country.CANADA,
                    'Vancouver': Country.CANADA,
                    'New York': Country.USA,
                    'Los Angeles': Country.USA,
                    'San Francisco': Country.USA,
                    'Hong Kong': Country.HONG_KONG,
                    'Taipei': Country.TAIWAN,
                    'Beijing': Country.CHINA,
                    'Shanghai': Country.CHINA
                }
                
                # First try to map from city, then fallback to country_code
                city = primary_item.get('city', '')
                country_code = primary_item.get('country_code', '')
                
                if city and city in city_to_country_mapping:
                    customer_country = city_to_country_mapping[city]
                else:
                    # Fallback to country code mapping
                    country_code_mapping = {
                        'SG': Country.SINGAPORE,
                        'US': Country.USA,
                        'JP': Country.JAPAN,
                        'IN': Country.INDIA,
                        'AU': Country.AUSTRALIA,
                        'PH': Country.PHILIPPINES,
                        'IL': Country.ISRAEL,
                        'CA': Country.CANADA,
                        'TW': Country.TAIWAN,
                        'CN': Country.CHINA,
                        'HK': Country.HONG_KONG,
                        'MY': Country.MALAYSIA,
                        'TH': Country.THAILAND,
                        'VN': Country.VIETNAM,
                        'KR': Country.SOUTH_KOREA,
                        'ID': Country.INDONESIA
                    }
                    customer_country = country_code_mapping.get(country_code, Country.SINGAPORE)
                
                # Use updated customer name if provided, otherwise use person_name from CSV
                customer_name = updated_customer_name if updated_customer_name else primary_item.get('person_name', '')

                # Validate that we have a customer name
                if not customer_name or not customer_name.strip():
                    return jsonify({
                        'success': False,
                        'error': 'Customer name is required. Please provide a valid customer name.'
                    })

                customer = CustomerUser(
                    name=customer_name,
                    email=primary_item['primary_email'],
                    contact_number=primary_item.get('phone_number', ''),
                    address=customer_address,
                    company_id=company.id,
                    country=customer_country
                )
                db_session.add(customer)
                db_session.flush()
                customer_created = True
            
            # 2. DETERMINE CATEGORY AND QUEUE
            def determine_category_and_queue(product_title, category_code):
                """Determine category based on product type"""
                product_lower = product_title.lower()
                category_lower = category_code.lower() if category_code else ""
                
                # Accessory detection patterns
                accessory_keywords = [
                    'adapter', 'cable', 'charger', 'mouse', 'keyboard', 'headset', 
                    'webcam', 'dock', 'hub', 'dongle', 'stand', 'pad', 'cover',
                    'case', 'sleeve', 'bag', 'power supply', 'cord', 'usb'
                ]
                
                # Computer/laptop detection patterns  
                computer_keywords = [
                    'macbook', 'laptop', 'computer', 'imac', 'pc', 'desktop', 
                    'workstation', 'tower', 'all-in-one', 'surface', 'thinkpad'
                ]
                
                # Check if it's an accessory
                is_accessory = (
                    any(keyword in product_lower for keyword in accessory_keywords) or
                    any(keyword in category_lower for keyword in ['accessory', 'peripheral', 'cable', 'adapter'])
                )
                
                if is_accessory:
                    return 'ASSET_CHECKOUT_CLAW'  # Route accessories to checkout queue
                else:
                    return 'ASSET_CHECKOUT_CLAW'  # Route computers to tech asset queue
            
            # Get ticket category enum value
            category_name = determine_category_and_queue(
                primary_item.get('product_title', ''),
                primary_item.get('category_code', '')
            )
            
            # Convert string to TicketCategory enum
            try:
                category = getattr(TicketCategory, category_name)
            except AttributeError:
                # If category name doesn't exist in enum, use default
                category = TicketCategory.ASSET_CHECKOUT_CLAW
            
            # 3. MAP PRIORITY
            priority_mapping = {
                '1': TicketPriority.LOW,
                '2': TicketPriority.MEDIUM,
                '3': TicketPriority.HIGH
            }
            priority = priority_mapping.get(primary_item.get('priority', '1'), TicketPriority.LOW)
            
            # 4. CREATE ENHANCED DESCRIPTION WITH SELECTED ITEMS
            selected_items_text = ""
            if selected_assets:
                selected_items_text += f"""

Selected Assets from Inventory:
"""
                for asset in selected_assets:
                    selected_items_text += f"- {asset.get('assetName', 'Unknown Asset')} (ID: {asset.get('assetId', 'N/A')})\n"
            
            if selected_accessories:
                selected_items_text += f"""

Selected Accessories from Inventory:
"""
                for acc in selected_accessories:
                    selected_items_text += f"- {acc.get('accessoryName', 'Unknown Accessory')} (ID: {acc.get('accessoryId', 'N/A')})\n"
            
            if is_grouped:
                # Create description for multiple items
                csv_status = primary_item['status']
                status_indicator = f"📋 CSV Status: {csv_status}" + (" 🔴" if csv_status == 'PROCESSING' else " ✅")
                
                description = f"""Asset Checkout Request - CSV Import (Multi-Item Order)
{status_indicator}

Customer Information:
- Name: {primary_item['person_name']}
- Company: {primary_item['org_name']}
- Email: {primary_item['primary_email']}
- Phone: {primary_item['phone_number']}

Order Information:
- Order ID: {primary_item['order_id']}
- Total Items: {len(all_items)}
- Organization ID: {primary_item['organization_id']}
- CSV Import Status: {csv_status}
- Start Date: {primary_item['start_date'] or 'Not specified'}

Asset Information ({len(all_items)} items):
"""
                for i, item in enumerate(all_items, 1):
                    description += f"""
Item {i}:
- Product: {item['product_title']}
- Brand: {item['brand']}
- Serial Number: {item['serial_number']}
- Category: {item['category_code']}
- Condition: {item['preferred_condition'] or 'Not specified'}
- Item ID: {item['order_item_id']}
"""
                
                description += selected_items_text
                description += f"""
Imported from CSV on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"""
                
                subject = f"Asset Checkout - Order {primary_item['order_id']} ({len(all_items)} items) [{csv_status}]"
                
            else:
                # Single item description
                csv_status = primary_item['status']
                status_indicator = f"📋 CSV Status: {csv_status}" + (" 🔴" if csv_status == 'PROCESSING' else " ✅")
                
                description = f"""Asset Checkout Request - CSV Import
{status_indicator}

Customer Information:
- Name: {primary_item['person_name']}
- Company: {primary_item['org_name']}
- Email: {primary_item['primary_email']}
- Phone: {primary_item['phone_number']}

Asset Information:
- Product: {primary_item['product_title']}
- Brand: {primary_item['brand']}
- Serial Number: {primary_item['serial_number']}
- Category: {primary_item['category_code']}
- Condition: {primary_item['preferred_condition'] or 'Not specified'}
- CSV Import Status: {csv_status}
{selected_items_text}
Imported from CSV on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"""
                
                subject = f"Asset Checkout - {primary_item['product_title']} [{csv_status}]"
            
            # 5. FORMAT SHIPPING ADDRESS (as requested)
            shipping_address = f"""{primary_item['office_name']}
{primary_item['address_line1']}
{primary_item['address_line2']}
{primary_item['city']}, {primary_item['state']} {primary_item['postal_code']}
{primary_item['country_code']}""".strip()
            
            # 6. FORMAT ORDER DETAILS FOR NOTES (as requested)
            order_notes = f"""Order Details:
- Order ID: {primary_item['order_id']}
- Organization ID: {primary_item['organization_id']}
- Status: {primary_item['status']}
- Start Date: {primary_item['start_date'] or 'Not specified'}
- Shipped Date: {primary_item['shipped_date'] or 'Not specified'}
- Delivery Date: {primary_item['delivery_date'] or 'Not specified'}
- Carrier: {primary_item['carrier'] or 'Not specified'}
- Tracking: {primary_item['tracking_link'] or 'Not provided'}"""
            
            # 7. CREATE THE TICKET WITH PROPER DATA FLOW
            # Determine case owner (assigned_to_id)
            case_owner_id = current_user.id  # Default to current user
            if selected_case_owner_id:
                try:
                    case_owner_id = int(selected_case_owner_id)
                    logger.info("[CSV DEBUG] Using selected case owner: {case_owner_id}")
                except (ValueError, TypeError):
                    logger.info("[CSV DEBUG] Invalid case owner ID, using current user: {current_user.id}")
            
            logger.info("[CSV DEBUG] Creating ticket with subject: {subject}")
            ticket = Ticket(
                subject=subject,
                description=description,
                customer_id=customer.id,
                category=category,
                priority=priority,
                status=TicketStatus.NEW,
                requester_id=current_user.id,
                assigned_to_id=case_owner_id,  # Set case owner
                queue_id=int(selected_queue_id) if selected_queue_id else None,  # Assign to selected queue
                shipping_address=shipping_address,  # Shipping info goes to shipping_address field
                notes=order_notes,  # Order details go to Notes field
                firstbaseorderid=primary_item.get('order_id', None)  # Store Order ID for duplicate prevention
            )
            
            db_session.add(ticket)
            db_session.flush()  # Ensure ticket gets an ID
            db_session.commit()
            logger.info("[CSV DEBUG] Ticket created successfully with ID: {ticket.id}")
            
            # Send queue notifications for the imported ticket
            try:
                from utils.queue_notification_sender import send_queue_notifications
                send_queue_notifications(ticket, action_type="created")
            except Exception as e:
                logger.error(f"Error sending queue notifications for CSV imported ticket: {str(e)}")
            
            # 8. ASSIGN SELECTED ASSETS AND ACCESSORIES TO TICKET
            assigned_accessories = []
            assigned_assets = []
            
            # Assign selected assets
            logger.info("[CSV DEBUG] About to process assets. selected_assets = {selected_assets}")
            logger.info("[CSV DEBUG] Number of selected assets: {len(selected_assets)}")
            
            # Check for duplicate asset IDs in the selection
            asset_ids = [asset_data.get('assetId') for asset_data in selected_assets if asset_data.get('assetId')]
            unique_asset_ids = list(set(asset_ids))
            logger.info("[CSV DEBUG] Asset IDs: {asset_ids}")
            logger.info("[CSV DEBUG] Unique Asset IDs: {unique_asset_ids}")
            if len(asset_ids) != len(unique_asset_ids):
                logger.info("[CSV DEBUG] WARNING: Duplicate asset IDs detected in selection!")
            
            if selected_assets:
                from models.asset import Asset
                logger.info("[CSV DEBUG] Processing {len(selected_assets)} selected assets")
                
                # Deduplicate assets by ID to prevent constraint violations
                processed_asset_ids = set()
                
                for asset_data in selected_assets:
                    asset_id = asset_data.get('assetId')
                    logger.info("[CSV DEBUG] Processing asset ID: {asset_id}")
                    if asset_id and asset_id not in processed_asset_ids:
                        processed_asset_ids.add(asset_id)
                        # Get the asset from database
                        asset = db_session.query(Asset).filter(Asset.id == asset_id).first()
                        if asset:
                            logger.info("[CSV DEBUG] Found asset: {asset.name}, Status: {asset.status}")
                            if asset.status and asset.status.value in ['In Stock', 'Ready to Deploy']:
                                # Use the existing function to safely assign asset
                                try:
                                    logger.info("[CSV DEBUG] Attempting to assign asset {asset_id} to ticket {ticket.id}")
                                    success = safely_assign_asset_to_ticket(ticket, asset, db_session)
                                    if success:
                                        assigned_assets.append(asset.name)
                                        logger.info("[CSV DEBUG] Successfully assigned asset {asset.name}")
                                        
                                        # Also assign the asset to the customer and update status
                                        if ticket.customer_id:
                                            asset.customer_id = ticket.customer_id
                                            logger.info("[CSV DEBUG] Assigned asset {asset.name} to customer {ticket.customer_id}")
                                        
                                        if ticket.assigned_to_id:
                                            asset.assigned_to_id = ticket.assigned_to_id
                                            logger.info("[CSV DEBUG] Assigned asset {asset.name} to user {ticket.assigned_to_id}")
                                        
                                        # Update asset status to DEPLOYED
                                        from models.asset import AssetStatus
                                        asset.status = AssetStatus.DEPLOYED
                                        logger.info("[CSV DEBUG] Updated asset {asset.name} status to DEPLOYED")
                                        
                                        # Create activity log for asset assignment
                                        from models.activity import Activity
                                        
                                        # Use current_user.id, fallback to admin user
                                        activity_user_id = current_user.id if current_user else 1
                                        
                                        activity = Activity(
                                            user_id=activity_user_id,
                                            type='asset_assigned',
                                            content=f'Assigned asset "{asset.name}" (Serial: {asset.serial_num}) to ticket #{ticket.display_id}',
                                            reference_id=ticket.id
                                        )
                                        db_session.add(activity)
                                    else:
                                        logger.info("[CSV DEBUG] Asset {asset_id} assignment failed or already assigned")
                                except Exception as e:
                                    logger.info("[CSV DEBUG] Error assigning asset {asset_id}: {str(e)}")
                                    import traceback
                                    traceback.print_exc()
                            else:
                                logger.info("[CSV DEBUG] Asset {asset_id} not available for assignment. Status: {asset.status}")
                        else:
                            logger.info("[CSV DEBUG] Asset {asset_id} not found in database")
                    elif asset_id in processed_asset_ids:
                        logger.info("[CSV DEBUG] Asset {asset_id} already processed, skipping duplicate")
            
            # Commit asset assignments
            if assigned_assets:
                logger.info("[CSV DEBUG] Committing {len(assigned_assets)} asset assignments")
                db_session.commit()
            
            # Assign selected accessories
            if selected_accessories:
                from models.ticket import TicketAccessory
                from models.accessory import Accessory
                
                for acc_data in selected_accessories:
                    accessory_id = acc_data.get('accessoryId')
                    if accessory_id:
                        # Get the accessory from database
                        accessory = db_session.query(Accessory).filter(Accessory.id == accessory_id).first()
                        if accessory and accessory.available_quantity > 0:
                            # Create ticket-accessory assignment
                            ticket_accessory = TicketAccessory(
                                ticket_id=ticket.id,
                                name=accessory.name,
                                category=accessory.category,
                                quantity=1,
                                condition='Good',
                                notes=f'Assigned from CSV import',
                                original_accessory_id=accessory.id
                            )
                            db_session.add(ticket_accessory)
                            
                            # Update accessory quantity (decrease available)
                            accessory.available_quantity -= 1
                            if accessory.available_quantity == 0:
                                accessory.status = 'Out of Stock'
                            
                            assigned_accessories.append(accessory.name)
                            
                            # Create activity log for accessory assignment
                            from models.activity import Activity
                            
                            # Use current_user.id, fallback to admin user
                            activity_user_id = current_user.id if current_user else 1
                            
                            activity = Activity(
                                user_id=activity_user_id,
                                type='accessory_assigned',
                                content=f'Assigned accessory "{accessory.name}" to ticket #{ticket.display_id}',
                                reference_id=ticket.id
                            )
                            db_session.add(activity)
                
                # Commit all assignments at once to avoid database locks
                db_session.commit()
            
            return jsonify({
                'success': True, 
                'ticket_id': ticket.id,
                'ticket_display_id': ticket.display_id,
                'customer_created': customer_created,
                'assigned_accessories': assigned_accessories,
                'assigned_assets': assigned_assets,
                'message': f'Ticket {ticket.display_id} created successfully. Customer {"created" if customer_created else "updated"}. {len(assigned_assets)} assets and {len(assigned_accessories)} accessories assigned.'
            })
            
        except Exception as e:
            db_session.rollback()
            raise e
        finally:
            db_session.close()
            
    except Exception as e:
        logger.info("Error importing ticket: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': f'Failed to import ticket: {str(e)}'})


@admin_bp.route('/csv-import/bulk-import', methods=['POST'])
@admin_required
def csv_import_bulk_import():
    """Import multiple tickets from CSV data"""
    try:
        data = request.get_json()
        row_indices = data.get('row_indices', [])
        auto_create_customer = data.get('auto_create_customer', True)
        selected_accessories = data.get('selected_accessories', [])  # Get selected accessories
        selected_assets = data.get('selected_assets', [])  # Get selected assets
        
        if 'csv_import_file' not in session:
            return jsonify({'success': False, 'error': 'No CSV data found. Please upload a file first.'})
        
        # Load CSV data from temporary file
        import json
        import os
        import tempfile
        
        csv_filename = session['csv_import_file']
        csv_filepath = os.path.join(tempfile.gettempdir(), csv_filename)
        
        if not os.path.exists(csv_filepath):
            return jsonify({'success': False, 'error': 'CSV data file not found. Please upload the file again.'})
        
        try:
            with open(csv_filepath, 'r') as f:
                file_data = json.load(f)
                # Handle both old format (list) and new format (dict with grouped data)
                if isinstance(file_data, list):
                    csv_data = file_data  # Old format
                else:
                    csv_data = file_data.get('grouped_orders', file_data.get('individual_rows', []))
        except Exception as e:
            return jsonify({'success': False, 'error': f'Error reading CSV data: {str(e)}'})
        results = []
        
        for row_index in row_indices:
            if row_index >= len(csv_data):
                results.append({'row_index': row_index, 'success': False, 'error': 'Invalid row index'})
                continue

            row = csv_data[row_index]

            # Check if ticket cannot be imported (processing or duplicate)
            if row.get('cannot_import', False):
                if row.get('is_duplicate', False):
                    results.append({
                        'row_index': row_index,
                        'success': False,
                        'error': f'Order ID {row.get("order_id")} already exists in database'
                    })
                elif row.get('is_processing', False):
                    results.append({
                        'row_index': row_index,
                        'success': False,
                        'error': 'Cannot import tickets with PROCESSING status. Please wait for the order to progress to another status before importing.'
                    })
                else:
                    results.append({
                        'row_index': row_index,
                        'success': False,
                        'error': 'Ticket cannot be imported'
                    })
                continue
            
            # Import single ticket (reuse the logic)
            try:
                result = csv_import_import_ticket_internal(csv_data[row_index], auto_create_customer, selected_accessories, selected_assets, current_user.id)
                results.append({'row_index': row_index, **result})
            except Exception as e:
                results.append({'row_index': row_index, 'success': False, 'error': str(e)})
        
        successful_imports = sum(1 for r in results if r.get('success'))
        
        return jsonify({
            'success': True,
            'results': results,
            'total_processed': len(row_indices),
            'successful_imports': successful_imports,
            'failed_imports': len(row_indices) - successful_imports
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': f'Bulk import error: {str(e)}'})


def csv_import_import_ticket_internal(row, auto_create_customer=True, selected_accessories=[], selected_assets=[], user_id=None):
    """Internal function to import a single ticket (used by bulk import)"""

    # Check if the ticket has PROCESSING status and block import
    if row.get('status') == 'PROCESSING':
        return {
            'success': False,
            'error': 'Cannot import tickets with PROCESSING status. Please wait for the order to progress to another status before importing.'
        }

    # Check if the ticket is already imported (duplicate Order ID)
    order_id = row.get('order_id', '').strip()
    if order_id:
        db_session = db_manager.get_session()
        try:
            existing_ticket = db_session.query(Ticket).filter(
                Ticket.firstbaseorderid == order_id
            ).first()
            if existing_ticket:
                return {
                    'success': False,
                    'error': f'Order ID {order_id} already exists in database (Ticket #{existing_ticket.id})'
                }
        finally:
            db_session.close()
    
    db_session = db_manager.get_session()
    
    try:
        # Configure SQLite for better concurrency
        from sqlalchemy import text
        db_session.execute(text("PRAGMA journal_mode=WAL;"))
        db_session.execute(text("PRAGMA synchronous=NORMAL;"))
        db_session.execute(text("PRAGMA busy_timeout=30000;"))  # 30 second timeout
        
        # Add a small delay to prevent database lock conflicts
        import time
        time.sleep(0.1)
        # Check if customer exists or create new one
        customer = None
        customer_created = False
        
        if row['primary_email']:
            customer = db_session.query(CustomerUser).filter(CustomerUser.email == row['primary_email']).first()
        
        if not customer and auto_create_customer:
            # Create new customer
            from models.user import Country
            from models.company import Company

            # Get or create company (normalize name to uppercase for comparison)
            org_name = row.get('org_name', '').strip().upper() if row.get('org_name') else None
            company = None
            if org_name:
                company = db_session.query(Company).filter(
                    Company.name == org_name
                ).first()

            if not company and org_name:
                company = Company(
                    name=org_name,
                    description=f"Auto-created from CSV import",
                    contact_email=row['primary_email']
                )
                db_session.add(company)
                db_session.flush()
            
            # Map city to country as requested by user, with fallback to country_code
            city_to_country_mapping = {
                'Singapore': Country.SINGAPORE,
                'Kuala Lumpur': Country.MALAYSIA,
                'Bangkok': Country.THAILAND,
                'Manila': Country.PHILIPPINES,
                'Jakarta': Country.INDONESIA,
                'Ho Chi Minh City': Country.VIETNAM,
                'Hanoi': Country.VIETNAM,
                'Seoul': Country.SOUTH_KOREA,
                'Tokyo': Country.JAPAN,
                'Osaka': Country.JAPAN,
                'Sydney': Country.AUSTRALIA,
                'Melbourne': Country.AUSTRALIA,
                'Mumbai': Country.INDIA,
                'Delhi': Country.INDIA,
                'Bangalore': Country.INDIA,
                'Tel Aviv': Country.ISRAEL,
                'Jerusalem': Country.ISRAEL,
                'Toronto': Country.CANADA,
                'Vancouver': Country.CANADA,
                'New York': Country.USA,
                'Los Angeles': Country.USA,
                'San Francisco': Country.USA,
                'Hong Kong': Country.HONG_KONG,
                'Taipei': Country.TAIWAN,
                'Beijing': Country.CHINA,
                'Shanghai': Country.CHINA
            }
            
            # First try to map from city, then fallback to country_code
            city = row.get('city', '')
            country_code = row.get('country_code', '')
            
            if city and city in city_to_country_mapping:
                country = city_to_country_mapping[city]
            else:
                # Fallback to country code mapping
                country_code_mapping = {
                    'SG': Country.SINGAPORE,
                    'US': Country.USA,
                    'JP': Country.JAPAN,
                    'IN': Country.INDIA,
                    'AU': Country.AUSTRALIA,
                    'PH': Country.PHILIPPINES,
                    'IL': Country.ISRAEL,
                    'CA': Country.CANADA,
                    'TW': Country.TAIWAN,
                    'CN': Country.CHINA,
                    'HK': Country.HONG_KONG,
                    'MY': Country.MALAYSIA,
                    'TH': Country.THAILAND,
                    'VN': Country.VIETNAM,
                    'KR': Country.SOUTH_KOREA,
                    'ID': Country.INDONESIA
                }
                country = country_code_mapping.get(country_code, Country.SINGAPORE)
            
            # Create address from available fields
            address_parts = [
                row.get('address_line1', ''),
                row.get('address_line2', ''),
                row.get('city', ''),
                f"{row.get('state', '')} {row.get('postal_code', '')}".strip(),
                row.get('country_code', '')
            ]
            customer_address = ', '.join(filter(None, address_parts))
            if not customer_address.strip():
                customer_address = "Address not provided"
            
            customer = CustomerUser(
                name=row['person_name'],
                email=row['primary_email'],
                contact_number=row.get('phone_number', ''),
                address=customer_address,
                company_id=company.id,
                country=country
            )
            db_session.add(customer)
            db_session.flush()  # Get the customer ID
            customer_created = True
        
        if not customer:
            return {'success': False, 'error': 'Customer not found and auto-create is disabled'}
        
        # Get ticket category enum value
        category_mapping = {
            'COMPUTER': 'ASSET_CHECKOUT_CLAW',
            'LAPTOP': 'ASSET_CHECKOUT_CLAW', 
            'MONITOR': 'ASSET_CHECKOUT_CLAW',
            'KEYBOARD': 'ASSET_CHECKOUT_CLAW',
            'MOUSE': 'ASSET_CHECKOUT_CLAW',
            'HEADSET': 'ASSET_CHECKOUT_CLAW',
            'AV_ADAPTER': 'ASSET_CHECKOUT_CLAW',
            'COMPUTER_ACCESSORY': 'ASSET_CHECKOUT_CLAW'
        }
        
        category_name = category_mapping.get(row['category_code'], 'ASSET_CHECKOUT_CLAW')
        
        # Convert string to TicketCategory enum
        try:
            category = getattr(TicketCategory, category_name)
        except AttributeError:
            # If category name doesn't exist in enum, use default
            category = TicketCategory.ASSET_CHECKOUT_CLAW
        
        # Map priority
        priority_mapping = {
            '1': TicketPriority.LOW,
            '2': TicketPriority.MEDIUM,
            '3': TicketPriority.HIGH
        }
        priority = priority_mapping.get(row['priority'], TicketPriority.LOW)
        
        # Create detailed description
        selected_accessories_text = ""
        if selected_accessories:
            selected_accessories_text = f"""

Selected Accessories from Inventory:
"""
            for acc in selected_accessories:
                selected_accessories_text += f"- {acc.get('accessoryName', 'Unknown Accessory')} (ID: {acc.get('accessoryId', 'N/A')})\n"
        
        # Create CSV status indicator
        csv_status = row['status']
        status_indicator = f"📋 CSV Status: {csv_status}" + (" 🔴" if csv_status == 'PROCESSING' else " ✅")
        
        description = f"""Asset Checkout Request - CSV Import
{status_indicator}

Customer Information:
- Name: {row['person_name']}
- Company: {row['org_name']}
- Email: {row['primary_email']}
- Phone: {row['phone_number']}

Asset Information:
- Product: {row['product_title']}
- Brand: {row['brand']}
- Serial Number: {row['serial_number']}
- Category: {row['category_code']}
- Condition: {row['preferred_condition'] or 'Not specified'}
- CSV Import Status: {csv_status}

Shipping Information:
- Office: {row['office_name']}
- Address: {row['address_line1']}, {row['address_line2']}
- City: {row['city']}, {row['state']} {row['postal_code']}
- Country: {row['country_code']}
- Carrier: {row['carrier'] or 'Not specified'}
- Tracking: {row['tracking_link'] or 'Not provided'}

Order Information:
- Order ID: {row['order_id']}
- Order Item ID: {row['order_item_id']}
- Organization ID: {row['organization_id']}
- CSV Status: {csv_status}
- Start Date: {row['start_date'] or 'Not specified'}
- Shipped Date: {row['shipped_date'] or 'Not specified'}
- Delivery Date: {row['delivery_date'] or 'Not specified'}
{selected_accessories_text}
Imported from CSV on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"""
        
        # Create the ticket
        # Use provided user_id or try to get current_user.id, fallback to 1 (admin)
        requester_id = user_id
        if not requester_id:
            try:
                from flask_login import current_user
                requester_id = current_user.id if current_user and current_user.is_authenticated else 1
            except:
                requester_id = 1  # Fallback to admin user
        
        ticket = Ticket(
            subject=f"Asset Checkout - {row['product_title']} [{csv_status}]",
            description=description,
            customer_id=customer.id,
            category=category,
            priority=priority,
            status=TicketStatus.NEW,
            requester_id=requester_id,
            firstbaseorderid=row.get('order_id', None)  # Store Order ID for duplicate prevention
        )
        
        db_session.add(ticket)
        db_session.flush()  # Ensure ticket gets an ID
        db_session.commit()
        
        # Send queue notifications for the imported ticket
        try:
            from utils.queue_notification_sender import send_queue_notifications
            send_queue_notifications(ticket, action_type="created")
        except Exception as e:
            logger.error(f"Error sending queue notifications for CSV imported ticket: {str(e)}")
        
        # Assign selected assets and accessories to ticket
        assigned_accessories = []
        assigned_assets = []
        
        # Assign selected assets
        if selected_assets:
            from models.asset import Asset
            
            for asset_data in selected_assets:
                asset_id = asset_data.get('assetId')
                if asset_id:
                    # Get the asset from database
                    asset = db_session.query(Asset).filter(Asset.id == asset_id).first()
                    if asset and asset.status and asset.status.value in ['In Stock', 'Ready to Deploy']:
                        # Use the existing function to safely assign asset
                        try:
                            safely_assign_asset_to_ticket(ticket, asset, db_session)
                            assigned_assets.append(asset.name)
                            
                            # Also assign the asset to the customer and update status
                            if ticket.customer_id:
                                asset.customer_id = ticket.customer_id
                                logger.info("[CSV DEBUG] Assigned asset {asset.name} to customer {ticket.customer_id}")
                            
                            if ticket.assigned_to_id:
                                asset.assigned_to_id = ticket.assigned_to_id
                                logger.info("[CSV DEBUG] Assigned asset {asset.name} to user {ticket.assigned_to_id}")
                            
                            # Update asset status to DEPLOYED
                            from models.asset import AssetStatus
                            asset.status = AssetStatus.DEPLOYED
                            logger.info("[CSV DEBUG] Updated asset {asset.name} status to DEPLOYED")
                            
                            # Create activity log for asset assignment
                            from models.activity import Activity
                            activity = Activity(
                                user_id=requester_id,
                                type='asset_assigned',
                                content=f'Assigned asset "{asset.name}" (Serial: {asset.serial_num}) to ticket #{ticket.display_id}',
                                reference_id=ticket.id
                            )
                            db_session.add(activity)
                        except Exception as e:
                            logger.info("Error assigning asset {asset_id}: {str(e)}")
        
        # Assign selected accessories
        if selected_accessories:
            from models.ticket import TicketAccessory
            from models.accessory import Accessory
            
            for acc_data in selected_accessories:
                accessory_id = acc_data.get('accessoryId')
                if accessory_id:
                    # Get the accessory from database
                    accessory = db_session.query(Accessory).filter(Accessory.id == accessory_id).first()
                    if accessory and accessory.available_quantity > 0:
                        # Create ticket-accessory assignment
                        ticket_accessory = TicketAccessory(
                            ticket_id=ticket.id,
                            name=accessory.name,
                            category=accessory.category,
                            quantity=1,
                            condition='Good',
                            notes=f'Assigned from CSV import',
                            original_accessory_id=accessory.id
                        )
                        db_session.add(ticket_accessory)
                        
                        # Update accessory quantity (decrease available)
                        accessory.available_quantity -= 1
                        if accessory.available_quantity == 0:
                            accessory.status = 'Out of Stock'
                        
                        assigned_accessories.append(accessory.name)
                        
                        # Create activity log for accessory assignment
                        from models.activity import Activity
                        activity = Activity(
                            user_id=requester_id,
                            type='accessory_assigned',
                            content=f'Assigned accessory "{accessory.name}" to ticket #{ticket.display_id}',
                            reference_id=ticket.id
                        )
                        db_session.add(activity)
        
        # Commit all assignments at once to avoid database locks
        if assigned_assets or assigned_accessories:
            db_session.commit()
        
        return {
            'success': True, 
            'ticket_id': ticket.id,
            'ticket_display_id': ticket.display_id,
            'customer_created': customer_created,
            'assigned_accessories': assigned_accessories,
            'assigned_assets': assigned_assets
        }
        
    except Exception as e:
        db_session.rollback()
        raise e
    finally:
        db_session.close() 

def safely_assign_asset_to_ticket(ticket, asset, db_session):
    """
    Safely assign an asset to a ticket, checking for existing relationships first
    
    Args:
        ticket: Ticket object
        asset: Asset object or asset ID
        db_session: Database session
        
    Returns:
        bool: True if assignment was successful or already exists, False otherwise
    """
    try:
        logger.info("[ASSET ASSIGN DEBUG] Starting assignment - Ticket: {ticket.id}, Asset: {asset}")
        
        # If asset is an ID, get the asset object
        if isinstance(asset, int):
            asset_id = asset
            asset = db_session.query(Asset).get(asset_id)
            if not asset:
                logger.info("[ASSET ASSIGN DEBUG] Asset with ID {asset_id} not found")
                return False
        
        logger.info("[ASSET ASSIGN DEBUG] Asset object: {asset.name} (ID: {asset.id})")
        
        # Check if the relationship already exists in the database first
        from sqlalchemy import text
        stmt = text("""
            SELECT COUNT(*) FROM ticket_assets 
            WHERE ticket_id = :ticket_id AND asset_id = :asset_id
        """)
        result = db_session.execute(stmt, {"ticket_id": ticket.id, "asset_id": asset.id})
        count = result.scalar()
        
        logger.info("[ASSET ASSIGN DEBUG] Existing relationship count: {count}")
        
        if count > 0:
            logger.info("[ASSET ASSIGN DEBUG] Asset {asset.id} already linked to ticket {ticket.id} in database")
            return True
        
        # Check if asset is already assigned to this ticket in memory
        if asset in ticket.assets:
            logger.info("[ASSET ASSIGN DEBUG] Asset {asset.id} ({asset.asset_tag}) already assigned to ticket {ticket.id} in memory")
            return True
        
        # Safe to assign - insert directly into ticket_assets table
        logger.info("[ASSET ASSIGN DEBUG] Inserting directly into ticket_assets table")
        try:
            from sqlalchemy import text
            insert_stmt = text("""
                INSERT INTO ticket_assets (ticket_id, asset_id) 
                VALUES (:ticket_id, :asset_id)
            """)
            db_session.execute(insert_stmt, {"ticket_id": ticket.id, "asset_id": asset.id})
            db_session.flush()
            logger.info("[ASSET ASSIGN DEBUG] Successfully assigned asset {asset.id} ({asset.asset_tag}) to ticket {ticket.id}")
            return True
        except Exception as insert_error:
            logger.info("[ASSET ASSIGN DEBUG] Error during direct insert: {str(insert_error)}")
            # Check if it's a constraint violation (asset already assigned)
            if "UNIQUE constraint failed" in str(insert_error):
                logger.info("[ASSET ASSIGN DEBUG] Asset {asset.id} already assigned to ticket {ticket.id}")
                return True  # Consider this a success since the asset is already assigned
            else:
                logger.info("[ASSET ASSIGN DEBUG] Unexpected error during insert")
                return False
        
    except Exception as e:
        logger.info("[ASSET ASSIGN DEBUG] Error assigning asset to ticket: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

@admin_bp.route('/permissions/unified')
@login_required
@admin_required
def unified_permissions():
    """Unified permissions management page combining user permissions and queue permissions"""
    db_session = db_manager.get_session()
    try:
        # Get all users for permission management
        users = db_session.query(User).filter(User.is_deleted == False).all()
        
        # Get all companies and queues for queue permissions
        companies = db_session.query(Company).all()
        queues = db_session.query(Queue).all()
        
        # Get existing queue permissions
        queue_permissions = db_session.query(CompanyQueuePermission).all()
        
        # Get existing user permissions
        user_permissions = db_session.query(Permission).all()
        
        return render_template('admin/unified_permissions.html', 
                             users=users,
                             companies=companies,
                             queues=queues,
                             queue_permissions=queue_permissions,
                             user_permissions=user_permissions)
    except Exception as e:
        flash(f'Error loading permissions: {str(e)}', 'error')
        return redirect(url_for('main.index'))
    finally:
        db_session.close()


# Group Management Routes

@admin_bp.route('/groups')
@admin_required
def manage_groups():
    """Group management page"""
    if 'user_id' not in session:
        flash('Please log in to continue', 'error')
        return redirect(url_for('auth.login'))

    db_session = db_manager.get_session()
    try:
        # Get current user
        user = db_manager.get_user(session['user_id'])
        if not user:
            session.clear()
            return redirect(url_for('auth.login'))

        # Import the models here to avoid circular imports
        from models.group import Group
        from models.group_membership import GroupMembership
        
        # Get all groups with their memberships
        groups = db_session.query(Group).order_by(Group.created_at.desc()).all()
        
        # Get all users for the add member dropdown
        users = db_session.query(User).filter(User.is_deleted == False).order_by(User.username).all()

        return render_template('admin/manage_groups.html', 
                             user=user,
                             groups=groups,
                             users=users)

    except Exception as e:
        logger.error(f"Error loading groups page: {e}")
        flash(f'Error loading groups: {str(e)}', 'error')
        return redirect(url_for('admin.system_config'))
    finally:
        db_session.close()


@admin_bp.route('/groups/create', methods=['POST'])
@admin_required
def create_group():
    """Create a new group"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401

    db_session = db_manager.get_session()
    try:
        # Get current user
        user = db_manager.get_user(session['user_id'])
        if not user:
            return jsonify({'error': 'User not found'}), 404

        # Import the model here to avoid circular imports
        from models.group import Group
        
        # Get form data
        name = request.form.get('name', '').strip().lower()
        description = request.form.get('description', '').strip()
        
        if not name:
            return jsonify({'error': 'Group name is required'}), 400
            
        # Validate group name (alphanumeric and hyphens only)
        import re
        if not re.match(r'^[a-z0-9-]+$', name):
            return jsonify({'error': 'Group name can only contain lowercase letters, numbers, and hyphens'}), 400
        
        # Check if group name already exists
        existing_group = db_session.query(Group).filter(Group.name == name).first()
        if existing_group:
            return jsonify({'error': 'A group with this name already exists'}), 400
        
        # Create new group
        group = Group(
            name=name,
            description=description if description else None,
            created_by_id=user.id
        )
        
        db_session.add(group)
        db_session.commit()
        
        logger.info(f"Group '{name}' created by user {user.username}")
        flash(f"Group '@{name}' created successfully", 'success')
        
        return jsonify({'success': True, 'group_id': group.id})

    except Exception as e:
        logger.error(f"Error creating group: {e}")
        db_session.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        db_session.close()


@admin_bp.route('/groups/update', methods=['POST'])
@admin_required
def update_group():
    """Update an existing group"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401

    db_session = db_manager.get_session()
    try:
        # Get current user
        user = db_manager.get_user(session['user_id'])
        if not user:
            return jsonify({'error': 'User not found'}), 404

        # Import the model here to avoid circular imports
        from models.group import Group
        
        # Get form data
        group_id = request.form.get('group_id')
        name = request.form.get('name', '').strip().lower()
        description = request.form.get('description', '').strip()
        
        if not group_id or not name:
            return jsonify({'error': 'Group ID and name are required'}), 400
        
        # Validate group name
        import re
        if not re.match(r'^[a-z0-9-]+$', name):
            return jsonify({'error': 'Group name can only contain lowercase letters, numbers, and hyphens'}), 400
        
        # Get the group
        group = db_session.query(Group).filter(Group.id == group_id).first()
        if not group:
            return jsonify({'error': 'Group not found'}), 404
        
        # Check if new name conflicts with existing group (excluding current group)
        if group.name != name:
            existing_group = db_session.query(Group).filter(
                Group.name == name,
                Group.id != group_id
            ).first()
            if existing_group:
                return jsonify({'error': 'A group with this name already exists'}), 400
        
        # Update group
        old_name = group.name
        group.name = name
        group.description = description if description else None
        group.updated_at = datetime.utcnow()
        
        db_session.commit()
        
        logger.info(f"Group '{old_name}' updated to '{name}' by user {user.username}")
        flash(f"Group '@{name}' updated successfully", 'success')
        
        return jsonify({'success': True})

    except Exception as e:
        logger.error(f"Error updating group: {e}")
        db_session.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        db_session.close()


@admin_bp.route('/groups/add-member', methods=['POST'])
@admin_required
def add_group_member():
    """Add a member to a group"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401

    db_session = db_manager.get_session()
    try:
        # Get current user
        current_user = db_manager.get_user(session['user_id'])
        if not current_user:
            return jsonify({'error': 'User not found'}), 404

        # Import the models here to avoid circular imports
        from models.group import Group
        
        # Get form data
        group_id = request.form.get('group_id')
        user_id = request.form.get('user_id')
        
        if not group_id or not user_id:
            return jsonify({'error': 'Group ID and User ID are required'}), 400
        
        # Convert to integers
        try:
            group_id = int(group_id)
            user_id = int(user_id)
        except (ValueError, TypeError):
            return jsonify({'error': 'Invalid Group ID or User ID format'}), 400
        
        # Get the group and user
        group = db_session.query(Group).filter(Group.id == group_id).first()
        if not group:
            return jsonify({'error': 'Group not found'}), 404
            
        user = db_session.query(User).filter(User.id == user_id).first()
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Check if user is already a member
        if group.has_member(user_id):
            return jsonify({'error': f'{user.username} is already a member of this group'}), 400
        
        # Add member to group
        membership = group.add_member(user_id, current_user.id)
        
        db_session.commit()
        
        logger.info(f"User {user.username} added to group '{group.name}' by {current_user.username}")
        flash(f"{user.username} added to group '@{group.name}' successfully", 'success')
        
        return jsonify({'success': True})

    except Exception as e:
        logger.error(f"Error adding group member: {e}")
        db_session.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        db_session.close()


@admin_bp.route('/groups/remove-member', methods=['POST'])
@admin_required
def remove_group_member():
    """Remove a member from a group"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401

    db_session = db_manager.get_session()
    try:
        # Get current user
        current_user = db_manager.get_user(session['user_id'])
        if not current_user:
            return jsonify({'error': 'User not found'}), 404

        # Import the models here to avoid circular imports
        from models.group import Group
        
        # Get form data
        group_id = request.form.get('group_id')
        user_id = request.form.get('user_id')
        
        if not group_id or not user_id:
            return jsonify({'error': 'Group ID and User ID are required'}), 400
        
        # Convert to integers
        try:
            group_id = int(group_id)
            user_id = int(user_id)
        except (ValueError, TypeError):
            return jsonify({'error': 'Invalid Group ID or User ID format'}), 400
        
        # Get the group and user
        group = db_session.query(Group).filter(Group.id == group_id).first()
        if not group:
            return jsonify({'error': 'Group not found'}), 404
            
        user = db_session.query(User).filter(User.id == user_id).first()
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Debug: Check current group membership
        logger.info(f"Attempting to remove user {user.id} ({user.username}) from group {group.id} ({group.name})")
        logger.info(f"Group has {group.member_count} members: {[m.username for m in group.members]}")
        
        # Check if user is actually in the group before attempting removal
        if not group.has_member(user_id):
            current_members = [m.username for m in group.members]
            logger.warning(f"User {user.username} is not a member of group {group.name}. Current members: {current_members}")
            return jsonify({'error': f'User {user.username} is not a member of group @{group.name}. Current members: {", ".join(current_members) if current_members else "none"}'}), 400
        
        # Remove member from group
        if group.remove_member(user_id):
            db_session.commit()
            
            logger.info(f"User {user.username} removed from group '{group.name}' by {current_user.username}")
            flash(f"{user.username} removed from group '@{group.name}' successfully", 'success')
            
            return jsonify({'success': True})
        else:
            # This shouldn't happen if we got past the has_member check above
            logger.error(f"Unexpected: remove_member returned False even though user was a member")
            return jsonify({'error': f'Unexpected error removing user {user.username} from group @{group.name}'}), 500

    except Exception as e:
        logger.error(f"Error removing group member: {e}")
        db_session.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        db_session.close()


@admin_bp.route('/groups/toggle-status', methods=['POST'])
@admin_required
def toggle_group_status():
    """Activate or deactivate a group"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401

    db_session = db_manager.get_session()
    try:
        # Get current user
        current_user = db_manager.get_user(session['user_id'])
        if not current_user:
            return jsonify({'error': 'User not found'}), 404

        # Import the model here to avoid circular imports
        from models.group import Group
        
        # Get form data
        group_id = request.form.get('group_id')
        is_active = request.form.get('is_active', '').lower() == 'true'
        
        if not group_id:
            return jsonify({'error': 'Group ID is required'}), 400
        
        # Get the group
        group = db_session.query(Group).filter(Group.id == group_id).first()
        if not group:
            return jsonify({'error': 'Group not found'}), 404
        
        # Update group status
        group.is_active = is_active
        group.updated_at = datetime.utcnow()
        
        db_session.commit()
        
        status_text = "activated" if is_active else "deactivated"
        logger.info(f"Group '{group.name}' {status_text} by user {current_user.username}")
        flash(f"Group '@{group.name}' {status_text} successfully", 'success')
        
        return jsonify({'success': True})

    except Exception as e:
        logger.error(f"Error toggling group status: {e}")
        db_session.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        db_session.close()


@admin_bp.route('/groups/delete', methods=['POST'])
@admin_required
def delete_group():
    """Delete a group permanently"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401

    db_session = db_manager.get_session()
    try:
        # Get current user
        current_user = db_manager.get_user(session['user_id'])
        if not current_user:
            return jsonify({'error': 'User not found'}), 404

        # Import the model here to avoid circular imports
        from models.group import Group
        
        # Get form data
        group_id = request.form.get('group_id')
        
        if not group_id:
            return jsonify({'error': 'Group ID is required'}), 400
        
        # Get the group
        group = db_session.query(Group).filter(Group.id == group_id).first()
        if not group:
            return jsonify({'error': 'Group not found'}), 404
        
        group_name = group.name
        
        # Delete the group (this will cascade delete memberships due to the relationship)
        db_session.delete(group)
        db_session.commit()
        
        logger.info(f"Group '{group_name}' deleted by user {current_user.username}")
        flash(f"Group '@{group_name}' deleted successfully", 'success')
        
        return jsonify({'success': True})

    except Exception as e:
        logger.error(f"Error deleting group: {e}")
        db_session.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        db_session.close()


@admin_bp.route('/api/mention-suggestions')
@login_required
def get_mention_suggestions():
    """Get users and groups for @mention autocomplete"""
    query = request.args.get('q', '').lower().strip()

    db_session = db_manager.get_session()
    try:
        from models.group import Group
        from models.user_mention_permission import UserMentionPermission

        suggestions = []

        # Check if current user has mention filtering enabled
        current_user_obj = db_session.query(User).get(current_user.id)
        mention_filter_enabled = current_user_obj.mention_filter_enabled if current_user_obj else False

        # Get allowed user/group IDs if filtering is enabled
        allowed_user_ids = None
        allowed_group_ids = None
        if mention_filter_enabled:
            mention_perms = db_session.query(UserMentionPermission).filter_by(user_id=current_user.id).all()
            allowed_user_ids = [p.target_id for p in mention_perms if p.target_type == 'user']
            allowed_group_ids = [p.target_id for p in mention_perms if p.target_type == 'group']

        # Get users (limit to 10 for performance)
        user_query = db_session.query(User).filter(
            User.username.ilike(f'%{query}%')
        )

        # Apply filter if enabled
        if mention_filter_enabled and allowed_user_ids is not None:
            if allowed_user_ids:
                user_query = user_query.filter(User.id.in_(allowed_user_ids))
            else:
                # No users allowed, return empty list for users
                user_query = user_query.filter(User.id == -1)  # No match

        users = user_query.limit(10).all()

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
        group_query = db_session.query(Group).filter(
            Group.name.ilike(f'%{query}%'),
            Group.is_active == True
        )

        # Apply filter if enabled
        if mention_filter_enabled and allowed_group_ids is not None:
            if allowed_group_ids:
                group_query = group_query.filter(Group.id.in_(allowed_group_ids))
            else:
                # No groups allowed, return empty list for groups
                group_query = group_query.filter(Group.id == -1)  # No match

        groups = group_query.limit(10).all()

        for group in groups:
            suggestions.append({
                'type': 'group',
                'id': group.id,
                'name': group.name,
                'display_name': f"@{group.name}",
                'description': group.description or f"Group with {group.member_count} members",
                'member_count': group.member_count,
                'avatar': 'G'  # Group icon
            })

        # Sort by relevance (exact matches first, then partial matches)
        def sort_key(item):
            name = item['name'].lower()
            if name == query:
                return (0, name)  # Exact match
            elif name.startswith(query):
                return (1, name)  # Starts with query
            else:
                return (2, name)  # Contains query

        suggestions.sort(key=sort_key)

        return jsonify({'suggestions': suggestions[:20]})  # Limit to 20 total suggestions

    except Exception as e:
        logger.error(f"Error getting mention suggestions: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        db_session.close()
# API Management Routes

@admin_bp.route('/api-management')
@super_admin_required
def api_management():
    """API Management Dashboard"""
    from utils.api_key_manager import APIKeyManager
    from models.api_key import APIKey
    from models.api_usage import APIUsage
    
    db_session = SessionLocal()
    try:
        # Get all API keys with eager loading of relationships
        from sqlalchemy.orm import joinedload
        api_keys = db_session.query(APIKey).options(joinedload(APIKey.created_by)).order_by(APIKey.created_at.desc()).all()
        
        # Get usage statistics
        usage_stats = APIKeyManager.get_usage_stats(days=30)
        daily_usage = APIKeyManager.get_daily_usage(days=7)
        
        # Get permission groups
        permission_groups = APIKeyManager.get_permission_groups()
        
        return render_template('admin/api_management.html',
                             api_keys=api_keys,
                             usage_stats=usage_stats,
                             daily_usage=daily_usage,
                             permission_groups=permission_groups)
    except Exception as e:
        current_app.logger.error(f"Error in API management dashboard: {e}")
        flash(f'Error loading API management dashboard: {str(e)}', 'error')
        return redirect(url_for('admin.system_config'))
    finally:
        db_session.close()

@admin_bp.route('/api-management/keys/create', methods=['GET', 'POST'])
@super_admin_required
def create_api_key():
    """Create a new API key"""
    from utils.api_key_manager import APIKeyManager
    from datetime import datetime, timedelta
    
    if request.method == 'POST':
        db_session = SessionLocal()
        try:
            name = request.form.get('name', '').strip()
            permission_group = request.form.get('permission_group')
            custom_permissions = request.form.getlist('custom_permissions')
            expires_in_days = request.form.get('expires_in_days', type=int)
            
            # Validate input
            if not name:
                flash('API key name is required', 'error')
                return redirect(url_for('admin.create_api_key'))
            
            # Determine permissions
            permissions = []
            if permission_group and permission_group != 'custom':
                permission_groups = APIKeyManager.get_permission_groups()
                permissions = permission_groups.get(permission_group, [])
            elif custom_permissions:
                permissions = custom_permissions
            
            if not permissions:
                flash('At least one permission must be selected', 'error')
                return redirect(url_for('admin.create_api_key'))
            
            # Set expiration date
            expires_at = None
            if expires_in_days and expires_in_days > 0:
                expires_at = datetime.utcnow() + timedelta(days=expires_in_days)
            
            # Create API key
            success, message, api_key = APIKeyManager.generate_key(
                name=name,
                permissions=permissions,
                expires_at=expires_at,
                created_by_id=current_user.id
            )
            
            if success:
                flash(f'API key created successfully! Key: {api_key._raw_key}', 'success')
                return redirect(url_for('admin.api_management'))
            else:
                flash(f'Error creating API key: {message}', 'error')
                
        except Exception as e:
            current_app.logger.error(f"Error creating API key: {e}")
            flash(f'Error creating API key: {str(e)}', 'error')
        finally:
            db_session.close()
    
    # GET request - show form
    permission_groups = APIKeyManager.get_permission_groups()
    return render_template('admin/create_api_key.html', permission_groups=permission_groups)

@admin_bp.route('/api-management/keys/<int:key_id>/revoke', methods=['POST'])
@super_admin_required
def revoke_api_key(key_id):
    """Revoke an API key"""
    from utils.api_key_manager import APIKeyManager
    
    try:
        success, message = APIKeyManager.revoke_key(key_id)
        if success:
            flash('API key revoked successfully', 'success')
        else:
            flash(f'Error revoking API key: {message}', 'error')
    except Exception as e:
        current_app.logger.error(f"Error revoking API key: {e}")
        flash(f'Error revoking API key: {str(e)}', 'error')
    
    return redirect(url_for('admin.api_management'))

@admin_bp.route('/api-management/keys/<int:key_id>/activate', methods=['POST'])
@super_admin_required
def activate_api_key(key_id):
    """Activate a revoked API key"""
    from utils.api_key_manager import APIKeyManager
    
    try:
        success, message = APIKeyManager.activate_key(key_id)
        if success:
            flash('API key activated successfully', 'success')
        else:
            flash(f'Error activating API key: {message}', 'error')
    except Exception as e:
        current_app.logger.error(f"Error activating API key: {e}")
        flash(f'Error activating API key: {str(e)}', 'error')
    
    return redirect(url_for('admin.api_management'))

@admin_bp.route('/api-management/keys/<int:key_id>/extend', methods=['POST'])
@super_admin_required
def extend_api_key(key_id):
    """Extend API key expiration"""
    from utils.api_key_manager import APIKeyManager
    
    try:
        days = request.form.get('days', 30, type=int)
        success, message = APIKeyManager.extend_expiration(key_id, days)
        if success:
            flash(f'API key expiration extended by {days} days', 'success')
        else:
            flash(f'Error extending API key: {message}', 'error')
    except Exception as e:
        current_app.logger.error(f"Error extending API key: {e}")
        flash(f'Error extending API key: {str(e)}', 'error')
    
    return redirect(url_for('admin.api_management'))

@admin_bp.route('/api-management/keys/<int:key_id>/permissions', methods=['POST'])
@super_admin_required
def update_api_key_permissions(key_id):
    """Update API key permissions"""
    from utils.api_key_manager import APIKeyManager
    
    try:
        permissions = request.form.getlist('permissions')
        if not permissions:
            flash('At least one permission must be selected', 'error')
            return redirect(url_for('admin.api_management'))
        
        success, message = APIKeyManager.update_permissions(key_id, permissions)
        if success:
            flash('API key permissions updated successfully', 'success')
        else:
            flash(f'Error updating permissions: {message}', 'error')
    except Exception as e:
        current_app.logger.error(f"Error updating API key permissions: {e}")
        flash(f'Error updating permissions: {str(e)}', 'error')
    
    return redirect(url_for('admin.api_management'))

@admin_bp.route('/api-management/usage/<int:key_id>')
@super_admin_required
def api_key_usage(key_id):
    """View detailed usage for a specific API key"""
    from utils.api_key_manager import APIKeyManager
    from models.api_key import APIKey
    
    db_session = SessionLocal()
    try:
        # Get API key with eager loading
        from sqlalchemy.orm import joinedload
        api_key = db_session.query(APIKey).options(joinedload(APIKey.created_by)).filter(APIKey.id == key_id).first()
        if not api_key:
            flash('API key not found', 'error')
            return redirect(url_for('admin.api_management'))
        
        # Get usage statistics
        usage_stats = APIKeyManager.get_usage_stats(key_id, days=30)
        daily_usage = APIKeyManager.get_daily_usage(key_id, days=30)
        
        return render_template('admin/api_key_usage.html',
                             api_key=api_key,
                             usage_stats=usage_stats,
                             daily_usage=daily_usage)
    except Exception as e:
        current_app.logger.error(f"Error viewing API key usage: {e}")
        flash(f'Error loading usage data: {str(e)}', 'error')
        return redirect(url_for('admin.api_management'))
    finally:
        db_session.close()

@admin_bp.route('/api-management/cleanup-expired', methods=['POST'])
@super_admin_required
def cleanup_expired_keys():
    """Cleanup expired API keys"""
    from utils.api_key_manager import APIKeyManager
    
    try:
        count = APIKeyManager.cleanup_expired_keys()
        if count > 0:
            flash(f'Cleaned up {count} expired API keys', 'success')
        else:
            flash('No expired API keys found', 'info')
    except Exception as e:
        current_app.logger.error(f"Error cleaning up expired keys: {e}")
        flash(f'Error cleaning up expired keys: {str(e)}', 'error')
    
    return redirect(url_for('admin.api_management'))

@admin_bp.route('/api-management/export-usage')
@super_admin_required
def export_api_usage():
    """Export API usage data as CSV"""
    from utils.api_key_manager import APIKeyManager
    from models.api_usage import APIUsage
    import csv
    import io
    from flask import make_response
    
    db_session = SessionLocal()
    try:
        # Get usage data for the last 30 days
        from datetime import datetime, timedelta
        cutoff_date = datetime.utcnow() - timedelta(days=30)
        
        usage_records = db_session.query(APIUsage).filter(
            APIUsage.timestamp >= cutoff_date
        ).order_by(APIUsage.timestamp.desc()).all()
        
        # Create CSV
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow([
            'Timestamp', 'API Key Name', 'Endpoint', 'Method', 
            'Status Code', 'Response Time (ms)', 'IP Address', 'User Agent', 'Error Message'
        ])
        
        # Write data
        for record in usage_records:
            writer.writerow([
                record.timestamp.isoformat() if record.timestamp else '',
                record.api_key.name if record.api_key else 'Unknown',
                record.endpoint,
                record.method,
                record.status_code,
                record.response_time_ms or '',
                record.request_ip or '',
                record.user_agent or '',
                record.error_message or ''
            ])
        
        # Create response
        response = make_response(output.getvalue())
        response.headers['Content-Type'] = 'text/csv'
        response.headers['Content-Disposition'] = f'attachment; filename=api_usage_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        
        return response
        
    except Exception as e:
        current_app.logger.error(f"Error exporting API usage: {e}")
        flash(f'Error exporting usage data: {str(e)}', 'error')
        return redirect(url_for('admin.api_management'))
    finally:
        db_session.close()
@admin_bp.route('/api-documentation')
@super_admin_required
def api_documentation():
    """API Documentation Dashboard"""
    try:
        # Define available endpoints with their documentation
        endpoints = [
            {
                'method': 'GET',
                'path': '/api/v1/health',
                'name': 'Health Check',
                'description': 'Check API health status',
                'auth_required': False,
                'permissions': [],
                'parameters': [],
                'response_example': {
                    'status': 'healthy',
                    'timestamp': '2024-01-15T10:30:00Z',
                    'version': '1.0.0'
                }
            },
            {
                'method': 'POST',
                'path': '/api/v1/auth/login',
                'name': 'User Login',
                'description': 'Authenticate user and receive JWT token for API access',
                'auth_required': False,
                'permissions': [],
                'parameters': [
                    {'name': 'username', 'type': 'string', 'required': True, 'description': 'Username or email address'},
                    {'name': 'password', 'type': 'string', 'required': True, 'description': 'User password'}
                ],
                'request_body': {
                    'username': 'admin',
                    'password': 'your_password'
                },
                'response_example': {
                    'success': True,
                    'data': {
                        'id': 1,
                        'username': 'admin',
                        'email': 'admin@example.com',
                        'user_type': 'ADMIN',
                        'token': 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...',
                        'expires_at': '2024-01-16T10:30:00Z'
                    },
                    'message': 'Login successful'
                }
            },
            {
                'method': 'GET',
                'path': '/api/v1/auth/verify',
                'name': 'Verify Token',
                'description': 'Verify JWT token validity and get user information',
                'auth_required': True,
                'permissions': [],
                'parameters': [],
                'response_example': {
                    'success': True,
                    'data': {
                        'user_id': 1,
                        'username': 'admin',
                        'user_type': 'ADMIN',
                        'expires_at': '2024-01-16T10:30:00Z',
                        'valid': True
                    },
                    'message': 'Token is valid'
                }
            },
            {
                'method': 'POST',
                'path': '/api/v1/auth/refresh',
                'name': 'Refresh Token',
                'description': 'Refresh an existing JWT token to extend its validity',
                'auth_required': True,
                'permissions': [],
                'parameters': [],
                'response_example': {
                    'success': True,
                    'data': {
                        'token': 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...',
                        'expires_at': '2024-01-16T10:30:00Z',
                        'user_id': 1,
                        'username': 'admin'
                    },
                    'message': 'Token refreshed successfully'
                }
            },
            {
                'method': 'GET',
                'path': '/api/v1/auth/permissions',
                'name': 'Get User Permissions',
                'description': 'Get current user\'s permissions and capabilities',
                'auth_required': True,
                'permissions': [],
                'parameters': [],
                'response_example': {
                    'success': True,
                    'data': {
                        'user_id': 1,
                        'username': 'admin',
                        'user_type': 'ADMIN',
                        'permissions': [
                            'tickets:read',
                            'tickets:write',
                            'users:read',
                            'admin:read'
                        ],
                        'capabilities': {
                            'can_create_tickets': True,
                            'can_edit_tickets': True,
                            'can_delete_tickets': True,
                            'can_view_all_tickets': True,
                            'can_manage_users': True,
                            'can_access_admin': True
                        },
                        'company_id': 1,
                        'assigned_country': 'US'
                    },
                    'message': 'User permissions retrieved successfully'
                }
            },
            {
                'method': 'GET',
                'path': '/api/v1/auth/profile',
                'name': 'Get User Profile',
                'description': 'Get current user\'s detailed profile information',
                'auth_required': True,
                'permissions': [],
                'parameters': [],
                'response_example': {
                    'success': True,
                    'data': {
                        'id': 1,
                        'username': 'admin',
                        'email': 'admin@example.com',
                        'user_type': 'ADMIN',
                        'company_id': 1,
                        'company_name': 'Example Corp',
                        'assigned_country': 'US',
                        'role': 'administrator',
                        'theme_preference': 'light',
                        'created_at': '2024-01-15T10:30:00Z',
                        'last_login': '2024-01-15T15:45:00Z'
                    },
                    'message': 'User profile retrieved successfully'
                }
            },
            {
                'method': 'GET',
                'path': '/api/v1/tickets',
                'name': 'List Tickets',
                'description': 'Retrieve a paginated list of tickets with optional filtering',
                'auth_required': True,
                'permissions': ['tickets:read'],
                'parameters': [
                    {'name': 'page', 'type': 'integer', 'required': False, 'description': 'Page number (default: 1)'},
                    {'name': 'per_page', 'type': 'integer', 'required': False, 'description': 'Items per page (default: 50, max: 100)'},
                    {'name': 'status', 'type': 'string', 'required': False, 'description': 'Filter by ticket status'},
                    {'name': 'priority', 'type': 'string', 'required': False, 'description': 'Filter by priority level'}
                ],
                'response_example': {
                    'success': True,
                    'data': [
                        {
                            'id': 1,
                            'subject': 'Sample Ticket',
                            'description': 'Ticket description',
                            'status': 'NEW',
                            'priority': 'MEDIUM',
                            'created_at': '2024-01-15T10:30:00Z'
                        }
                    ],
                    'message': 'Retrieved 1 tickets',
                    'meta': {
                        'pagination': {
                            'page': 1,
                            'per_page': 50,
                            'total': 1,
                            'has_next': False,
                            'has_prev': False
                        }
                    }
                }
            },
            {
                'method': 'GET',
                'path': '/api/v1/tickets/{id}',
                'name': 'Get Ticket',
                'description': 'Retrieve detailed information about a specific ticket',
                'auth_required': True,
                'permissions': ['tickets:read'],
                'parameters': [
                    {'name': 'id', 'type': 'integer', 'required': True, 'description': 'Ticket ID'}
                ],
                'response_example': {
                    'success': True,
                    'data': {
                        'id': 1,
                        'subject': 'Sample Ticket',
                        'description': 'Detailed ticket description',
                        'status': 'NEW',
                        'priority': 'MEDIUM',
                        'category': 'Support',
                        'created_at': '2024-01-15T10:30:00Z',
                        'updated_at': '2024-01-15T10:30:00Z'
                    },
                    'message': 'Retrieved ticket 1'
                }
            },
            {
                'method': 'GET',
                'path': '/api/v1/users',
                'name': 'List Users',
                'description': 'Retrieve a paginated list of users',
                'auth_required': True,
                'permissions': ['users:read'],
                'parameters': [
                    {'name': 'page', 'type': 'integer', 'required': False, 'description': 'Page number (default: 1)'},
                    {'name': 'per_page', 'type': 'integer', 'required': False, 'description': 'Items per page (default: 50, max: 100)'}
                ],
                'response_example': {
                    'success': True,
                    'data': [
                        {
                            'id': 1,
                            'name': 'admin',
                            'email': 'admin@example.com',
                            'user_type': 'ADMIN',
                            'created_at': '2024-01-15T10:30:00Z'
                        }
                    ],
                    'message': 'Retrieved 1 users',
                    'meta': {
                        'pagination': {
                            'page': 1,
                            'per_page': 50,
                            'total': 1,
                            'has_next': False,
                            'has_prev': False
                        }
                    }
                }
            }
        ]
        
        return render_template('admin/api_documentation.html', endpoints=endpoints)
        
    except Exception as e:
        current_app.logger.error(f"Error loading API documentation: {e}")
        flash(f'Error loading API documentation: {str(e)}', 'error')
        return redirect(url_for('admin.api_management'))

@admin_bp.route('/company-grouping')
@admin_required
def manage_company_grouping():
    """Manage company grouping and parent/child relationships"""
    db_session = db_manager.get_session()
    try:
        # Get all companies from Company table
        existing_companies = db_session.query(Company).order_by(Company.name).all()
        
        # Get distinct customer names from Asset table that don't exist as companies yet
        asset_customers = db_session.query(Asset.customer).distinct().filter(
            Asset.customer.isnot(None),
            Asset.customer != ''
        ).all()
        
        existing_company_names = {c.name.upper() for c in existing_companies}

        # Create missing Company records for asset customers
        missing_companies = []
        for customer_tuple in asset_customers:
            customer_name = customer_tuple[0]
            # Compare uppercase to handle case-insensitive matching
            normalized_name = customer_name.upper().strip()
            if customer_name and normalized_name not in existing_company_names:
                # Create a new Company record (name will be auto-uppercased by model validator)
                new_company = Company(
                    name=customer_name,
                    is_parent_company=False,
                    parent_company_id=None,
                    display_name=None
                )
                db_session.add(new_company)
                missing_companies.append(new_company)
                # Add to set to prevent duplicates within same batch
                existing_company_names.add(normalized_name)
        
        # Commit new companies
        if missing_companies:
            db_session.commit()
            logger.info(f"Created {len(missing_companies)} new company records from asset customer field")
        
        # Get all companies again (including newly created ones)
        companies = db_session.query(Company).order_by(Company.name).all()
        
        # Separate parent companies and standalone companies
        parent_companies = [c for c in companies if c.is_parent_company or c.child_companies.count() > 0]
        standalone_companies = [c for c in companies if not c.parent_company_id and not c.is_parent_company]
        child_companies = [c for c in companies if c.parent_company_id]
        
        # Add information about which companies have assets
        for company in companies:
            asset_count = db_session.query(Asset).filter(Asset.customer == company.name).count()
            company.asset_count = asset_count
        
        return render_template('admin/company_grouping.html',
                              companies=companies,
                              parent_companies=parent_companies,
                              standalone_companies=standalone_companies,
                              child_companies=child_companies)
    except Exception as e:
        flash(f'Error loading company grouping: {str(e)}', 'error')
        return redirect(url_for('admin.manage_companies'))
    finally:
        db_session.close()

@admin_bp.route('/company-grouping/set-parent', methods=['POST'])
@admin_required
def set_company_parent():
    """Set a parent company for a child company"""
    child_company_id = request.form.get('child_company_id')
    parent_company_id = request.form.get('parent_company_id')
    
    if not child_company_id:
        flash('Child company is required', 'error')
        return redirect(url_for('admin.manage_company_grouping'))
    
    db_session = db_manager.get_session()
    try:
        child_company = db_session.query(Company).get(child_company_id)
        
        if not child_company:
            flash('Child company not found', 'error')
            return redirect(url_for('admin.manage_company_grouping'))
        
        # Prevent circular relationships
        if parent_company_id and int(parent_company_id) == child_company.id:
            flash('A company cannot be its own parent', 'error')
            return redirect(url_for('admin.manage_company_grouping'))
        
        if parent_company_id:
            parent_company = db_session.query(Company).get(parent_company_id)
            if not parent_company:
                flash('Parent company not found', 'error')
                return redirect(url_for('admin.manage_company_grouping'))
            
            # Check for circular reference
            if parent_company.parent_company_id == child_company.id:
                flash('This would create a circular reference', 'error')
                return redirect(url_for('admin.manage_company_grouping'))
            
            child_company.parent_company_id = parent_company.id
            
            # Mark parent company as parent
            parent_company.is_parent_company = True
            
            flash(f'Successfully grouped {child_company.name} under {parent_company.name}', 'success')
        else:
            # Remove parent relationship
            old_parent_name = child_company.parent_company.name if child_company.parent_company else None
            child_company.parent_company_id = None
            
            if old_parent_name:
                flash(f'Successfully removed {child_company.name} from {old_parent_name}', 'success')
        
        db_session.commit()
        
    except Exception as e:
        db_session.rollback()
        flash(f'Error updating company grouping: {str(e)}', 'error')
    finally:
        db_session.close()
    
    return redirect(url_for('admin.manage_company_grouping'))

@admin_bp.route('/company-grouping/set-display-name', methods=['POST'])
@admin_required
def set_company_display_name():
    """Set a custom display name for a company"""
    company_id = request.form.get('company_id')
    display_name = request.form.get('display_name', '').strip()
    
    if not company_id:
        flash('Company is required', 'error')
        return redirect(url_for('admin.manage_company_grouping'))
    
    db_session = db_manager.get_session()
    try:
        company = db_session.query(Company).get(company_id)
        
        if not company:
            flash('Company not found', 'error')
            return redirect(url_for('admin.manage_company_grouping'))
        
        # Set display name (can be empty to use default name)
        company.display_name = display_name if display_name else None
        
        db_session.commit()
        
        if display_name:
            flash(f'Successfully set display name for {company.name} to "{display_name}"', 'success')
        else:
            flash(f'Successfully removed custom display name for {company.name}', 'success')
        
    except Exception as e:
        db_session.rollback()
        flash(f'Error updating display name: {str(e)}', 'error')
    finally:
        db_session.close()
    
    return redirect(url_for('admin.manage_company_grouping'))

@admin_bp.route('/company-grouping/toggle-parent', methods=['POST'])
@admin_required
def toggle_parent_company():
    """Toggle parent company status"""
    company_id = request.form.get('company_id')
    
    if not company_id:
        flash('Company is required', 'error')
        return redirect(url_for('admin.manage_company_grouping'))
    
    db_session = db_manager.get_session()
    try:
        company = db_session.query(Company).get(company_id)
        
        if not company:
            flash('Company not found', 'error')
            return redirect(url_for('admin.manage_company_grouping'))
        
        # Check if company has children before removing parent status
        if company.is_parent_company and company.child_companies.count() > 0:
            flash(f'Cannot remove parent status from {company.name} - it still has child companies', 'error')
            return redirect(url_for('admin.manage_company_grouping'))
        
        company.is_parent_company = not company.is_parent_company
        db_session.commit()
        
        status = "enabled" if company.is_parent_company else "disabled"
        flash(f'Successfully {status} parent status for {company.name}', 'success')

    except Exception as e:
        db_session.rollback()
        flash(f'Error updating parent status: {str(e)}', 'error')
    finally:
        db_session.close()

    return redirect(url_for('admin.manage_company_grouping'))

@admin_bp.route('/company-grouping/remove-parent', methods=['POST'])
@admin_required
def remove_parent_company():
    """Remove parent status from a company and make all its children standalone"""
    company_id = request.form.get('company_id')

    if not company_id:
        flash('Company is required', 'error')
        return redirect(url_for('admin.manage_company_grouping'))

    db_session = db_manager.get_session()
    try:
        company = db_session.query(Company).get(company_id)

        if not company:
            flash('Company not found', 'error')
            return redirect(url_for('admin.manage_company_grouping'))

        if not company.is_parent_company:
            flash(f'{company.name} is not a parent company', 'error')
            return redirect(url_for('admin.manage_company_grouping'))

        # Get list of child companies for the flash message
        child_names = [child.name for child in company.child_companies]

        # Remove parent relationship from all child companies
        for child in company.child_companies:
            child.parent_company_id = None

        # Remove parent status from the company
        company.is_parent_company = False

        db_session.commit()

        child_count = len(child_names)
        if child_count > 0:
            flash(f'Successfully removed parent status from {company.name}. {child_count} child companies are now standalone: {", ".join(child_names)}', 'success')
        else:
            flash(f'Successfully removed parent status from {company.name}', 'success')

    except Exception as e:
        db_session.rollback()
        flash(f'Error removing parent status: {str(e)}', 'error')
    finally:
        db_session.close()

    return redirect(url_for('admin.manage_company_grouping'))

@admin_bp.route('/company-grouping/remove-child', methods=['POST'])
@admin_required
def remove_child_company():
    """Remove a company from its parent and make it standalone"""
    company_id = request.form.get('company_id')

    if not company_id:
        flash('Company is required', 'error')
        return redirect(url_for('admin.manage_company_grouping'))

    db_session = db_manager.get_session()
    try:
        company = db_session.query(Company).get(company_id)

        if not company:
            flash('Company not found', 'error')
            return redirect(url_for('admin.manage_company_grouping'))

        if not company.parent_company_id:
            flash(f'{company.name} is not a child company', 'error')
            return redirect(url_for('admin.manage_company_grouping'))

        parent_name = company.parent_company.name
        parent_company = company.parent_company

        # Remove the child from parent
        company.parent_company_id = None

        # Check if parent company still has other children
        remaining_children = db_session.query(Company).filter(
            Company.parent_company_id == parent_company.id,
            Company.id != company.id
        ).count()

        # If parent has no more children, remove its parent status
        if remaining_children == 0:
            parent_company.is_parent_company = False

        db_session.commit()

        if remaining_children == 0:
            flash(f'Successfully removed {company.name} from {parent_name}. {parent_name} is no longer a parent company as it has no remaining children.', 'success')
        else:
            flash(f'Successfully removed {company.name} from parent {parent_name}. It is now a standalone company.', 'success')

    except Exception as e:
        db_session.rollback()
        flash(f'Error removing child company: {str(e)}', 'error')
    finally:
        db_session.close()

    return redirect(url_for('admin.manage_company_grouping'))

@admin_bp.route('/company-grouping/bulk-remove-child', methods=['POST'])
@admin_required
def bulk_remove_child_companies():
    """Remove multiple companies from their parents and make them standalone"""
    child_company_ids = request.form.getlist('child_company_ids')

    if not child_company_ids:
        flash('Please select at least one company to remove', 'error')
        return redirect(url_for('admin.manage_company_grouping'))

    db_session = db_manager.get_session()
    try:
        removed_companies = []
        parent_companies_to_check = set()

        for company_id in child_company_ids:
            company = db_session.query(Company).get(company_id)

            if not company:
                continue

            if not company.parent_company_id:
                continue

            parent_companies_to_check.add(company.parent_company_id)
            removed_companies.append({
                'name': company.name,
                'parent_name': company.parent_company.name
            })

            # Remove the child from parent
            company.parent_company_id = None

        # Check each affected parent company and remove parent status if no children remain
        parent_status_removed = []
        for parent_id in parent_companies_to_check:
            parent_company = db_session.query(Company).get(parent_id)
            if parent_company:
                remaining_children = db_session.query(Company).filter(
                    Company.parent_company_id == parent_id
                ).count()

                if remaining_children == 0:
                    parent_company.is_parent_company = False
                    parent_status_removed.append(parent_company.name)

        db_session.commit()

        # Create success message
        if removed_companies:
            company_names = [comp['name'] for comp in removed_companies]
            message = f'Successfully removed {len(removed_companies)} companies from their parents: {", ".join(company_names)}'

            if parent_status_removed:
                message += f'. Parent status removed from: {", ".join(parent_status_removed)} (no remaining children)'

            flash(message, 'success')
        else:
            flash('No valid child companies were selected for removal', 'warning')

    except Exception as e:
        db_session.rollback()
        flash(f'Error removing child companies: {str(e)}', 'error')
    finally:
        db_session.close()

    return redirect(url_for('admin.manage_company_grouping'))

@admin_bp.route('/company-grouping/bulk-set-parent', methods=['POST'])
@admin_required
def bulk_set_company_parent():
    """Set a parent company for multiple child companies"""
    child_company_ids = request.form.getlist('child_company_ids')
    parent_company_id = request.form.get('parent_company_id')

    if not child_company_ids:
        flash('Please select at least one company to group', 'error')
        return redirect(url_for('admin.manage_company_grouping'))

    db_session = db_manager.get_session()
    try:
        grouped_companies = []
        ungrouped_companies = []
        errors = []

        # Get parent company if specified
        parent_company = None
        if parent_company_id:
            parent_company = db_session.query(Company).get(parent_company_id)
            if not parent_company:
                flash('Parent company not found', 'error')
                return redirect(url_for('admin.manage_company_grouping'))

        for company_id in child_company_ids:
            try:
                child_company = db_session.query(Company).get(company_id)

                if not child_company:
                    errors.append(f'Company with ID {company_id} not found')
                    continue

                # Prevent circular relationships
                if parent_company_id and int(parent_company_id) == child_company.id:
                    errors.append(f'{child_company.name} cannot be its own parent')
                    continue

                # Check for circular reference
                if parent_company and parent_company.parent_company_id == child_company.id:
                    errors.append(f'Setting {child_company.name} under {parent_company.name} would create a circular reference')
                    continue

                # Store old parent info for messaging
                old_parent_name = child_company.parent_company.name if child_company.parent_company else None

                if parent_company_id:
                    # Set new parent
                    child_company.parent_company_id = parent_company.id
                    grouped_companies.append({
                        'name': child_company.name,
                        'old_parent': old_parent_name,
                        'new_parent': parent_company.name
                    })
                else:
                    # Remove parent relationship
                    child_company.parent_company_id = None
                    ungrouped_companies.append({
                        'name': child_company.name,
                        'old_parent': old_parent_name
                    })

            except Exception as e:
                errors.append(f'Error processing {child_company.name if "child_company" in locals() else f"company {company_id}"}: {str(e)}')

        # Mark parent company as parent if grouping companies under it
        if parent_company and grouped_companies:
            parent_company.is_parent_company = True

        # Check if any previous parent companies should lose parent status
        if ungrouped_companies or grouped_companies:
            # Get all affected old parent companies
            old_parent_ids = set()
            for comp in grouped_companies:
                if comp['old_parent']:
                    old_parent = db_session.query(Company).filter(Company.name == comp['old_parent']).first()
                    if old_parent:
                        old_parent_ids.add(old_parent.id)

            for comp in ungrouped_companies:
                if comp['old_parent']:
                    old_parent = db_session.query(Company).filter(Company.name == comp['old_parent']).first()
                    if old_parent:
                        old_parent_ids.add(old_parent.id)

            # Check each old parent and remove parent status if no children remain
            for old_parent_id in old_parent_ids:
                remaining_children = db_session.query(Company).filter(
                    Company.parent_company_id == old_parent_id
                ).count()
                if remaining_children == 0:
                    old_parent = db_session.query(Company).get(old_parent_id)
                    if old_parent:
                        old_parent.is_parent_company = False

        db_session.commit()

        # Create success messages
        messages = []
        if grouped_companies:
            company_names = [comp['name'] for comp in grouped_companies]
            messages.append(f'Successfully grouped {len(grouped_companies)} companies under {parent_company.name}: {", ".join(company_names)}')

        if ungrouped_companies:
            company_names = [comp['name'] for comp in ungrouped_companies]
            messages.append(f'Successfully removed {len(ungrouped_companies)} companies from their parents: {", ".join(company_names)}')

        if errors:
            flash(f'Completed with some errors: {"; ".join(errors)}', 'warning')

        if messages:
            flash('. '.join(messages), 'success')
        elif not errors:
            flash('No changes were made', 'info')

    except Exception as e:
        db_session.rollback()
        flash(f'Error updating company grouping: {str(e)}', 'error')
    finally:
        db_session.close()

    return redirect(url_for('admin.manage_company_grouping'))

@admin_bp.route('/customer-company-grouping')
@admin_required
def manage_customer_company_grouping():
    """View all companies and their customer companies grouped together"""
    db_session = db_manager.get_session()
    try:
        from models.customer_user import CustomerUser

        # Get all companies with their customer users
        companies = db_session.query(Company).order_by(
            Company.is_parent_company.desc(),
            Company.parent_company_id.asc(),
            Company.name.asc()
        ).all()

        # Build company hierarchy with customer companies
        company_data = []
        for company in companies:
            # Get all customer users (customer companies) for this company
            customer_users = db_session.query(CustomerUser).filter(
                CustomerUser.company_id == company.id
            ).order_by(CustomerUser.name).all()

            # Count assets for this company
            asset_count = db_session.query(Asset).filter(Asset.customer == company.name).count()

            company_info = {
                'id': company.id,
                'name': company.name,
                'display_name': company.effective_display_name,
                'is_parent_company': company.is_parent_company,
                'parent_company_id': company.parent_company_id,
                'parent_company_name': company.parent_company.name if company.parent_company else None,
                'child_companies': [],
                'customer_companies': customer_users,
                'customer_company_count': len(customer_users),
                'asset_count': asset_count
            }

            # Get child companies if this is a parent
            if company.is_parent_company or company.child_companies.count() > 0:
                for child in company.child_companies.all():
                    child_customer_users = db_session.query(CustomerUser).filter(
                        CustomerUser.company_id == child.id
                    ).order_by(CustomerUser.name).all()

                    child_asset_count = db_session.query(Asset).filter(Asset.customer == child.name).count()

                    child_info = {
                        'id': child.id,
                        'name': child.name,
                        'display_name': child.effective_display_name,
                        'customer_companies': child_customer_users,
                        'customer_company_count': len(child_customer_users),
                        'asset_count': child_asset_count
                    }
                    company_info['child_companies'].append(child_info)

            company_data.append(company_info)

        # Separate into parent, child, and standalone companies
        parent_companies = [c for c in company_data if c['is_parent_company'] or c['child_companies']]
        standalone_companies = [c for c in company_data if not c['parent_company_id'] and not c['is_parent_company'] and not c['child_companies']]

        # Get unassigned customer companies
        unassigned_customers = db_session.query(CustomerUser).filter(
            CustomerUser.company_id.is_(None)
        ).order_by(CustomerUser.name).all()

        # Get all companies for the dropdown (for bulk assignment)
        all_companies_list = companies

        return render_template('admin/customer_company_grouping.html',
                              parent_companies=parent_companies,
                              standalone_companies=standalone_companies,
                              unassigned_customers=unassigned_customers,
                              all_companies=all_companies_list)
    except Exception as e:
        logger.error(f'Error loading customer company grouping: {str(e)}')
        flash(f'Error loading customer company grouping: {str(e)}', 'error')
        return redirect(url_for('main.index'))
    finally:
        db_session.close()

@admin_bp.route('/customer-company-grouping/assign', methods=['POST'])
@admin_required
def assign_customer_to_company():
    """Assign a customer company to a different company"""
    db_session = db_manager.get_session()
    try:
        from models.customer_user import CustomerUser

        customer_id = request.form.get('customer_id')
        new_company_id = request.form.get('company_id')

        if not customer_id:
            flash('Customer ID is required', 'error')
            return redirect(url_for('admin.manage_customer_company_grouping'))

        customer = db_session.query(CustomerUser).get(customer_id)
        if not customer:
            flash('Customer not found', 'error')
            return redirect(url_for('admin.manage_customer_company_grouping'))

        old_company_name = customer.company.name if customer.company else 'No Company'

        # Update company assignment (can be None to unassign)
        if new_company_id and new_company_id != 'none':
            new_company = db_session.query(Company).get(new_company_id)
            if not new_company:
                flash('Company not found', 'error')
                return redirect(url_for('admin.manage_customer_company_grouping'))

            customer.company_id = new_company.id
            new_company_name = new_company.name
            flash(f'Successfully moved "{customer.name}" from {old_company_name} to {new_company_name}', 'success')
        else:
            customer.company_id = None
            flash(f'Successfully removed "{customer.name}" from {old_company_name}', 'success')

        db_session.commit()

    except Exception as e:
        db_session.rollback()
        logger.error(f'Error assigning customer to company: {str(e)}')
        flash(f'Error assigning customer to company: {str(e)}', 'error')
    finally:
        db_session.close()

    return redirect(url_for('admin.manage_customer_company_grouping'))

@admin_bp.route('/customer-company-grouping/bulk-assign', methods=['POST'])
@admin_required
def bulk_assign_customers_to_company():
    """Bulk assign multiple customer companies to a company"""
    db_session = db_manager.get_session()
    try:
        from models.customer_user import CustomerUser

        customer_ids = request.form.getlist('customer_ids')
        new_company_id = request.form.get('company_id')

        if not customer_ids:
            flash('No customers selected', 'error')
            return redirect(url_for('admin.manage_customer_company_grouping'))

        if not new_company_id or new_company_id == 'none':
            flash('Please select a company', 'error')
            return redirect(url_for('admin.manage_customer_company_grouping'))

        new_company = db_session.query(Company).get(new_company_id)
        if not new_company:
            flash('Company not found', 'error')
            return redirect(url_for('admin.manage_customer_company_grouping'))

        updated_count = 0
        for customer_id in customer_ids:
            customer = db_session.query(CustomerUser).get(customer_id)
            if customer:
                customer.company_id = new_company.id
                updated_count += 1

        db_session.commit()
        flash(f'Successfully assigned {updated_count} customer companies to {new_company.name}', 'success')

    except Exception as e:
        db_session.rollback()
        logger.error(f'Error bulk assigning customers to company: {str(e)}')
        flash(f'Error bulk assigning customers to company: {str(e)}', 'error')
    finally:
        db_session.close()

    return redirect(url_for('admin.manage_customer_company_grouping'))

@admin_bp.route('/run-migration/add-screenshot-to-bugs')
@super_admin_required
def run_screenshot_migration():
    """Run migration to add screenshot_path column to bug_reports table"""
    from sqlalchemy import inspect
    from database import engine

    try:
        # Get inspector to check existing columns
        inspector = inspect(engine)

        # Check if bug_reports table exists
        if 'bug_reports' not in inspector.get_table_names():
            flash('Bug reports table does not exist', 'error')
            return redirect(url_for('admin.dashboard'))

        # Get existing columns
        columns = [col['name'] for col in inspector.get_columns('bug_reports')]

        if 'screenshot_path' in columns:
            flash('Screenshot column already exists in bug_reports table', 'info')
            return redirect(url_for('admin.dashboard'))

        # Determine database type
        db_type = engine.dialect.name
        logger.info(f"Running migration for database type: {db_type}")

        # Add the screenshot_path column
        db_session = SessionLocal()
        try:
            if db_type == 'mysql':
                db_session.execute(text("""
                    ALTER TABLE bug_reports
                    ADD COLUMN screenshot_path VARCHAR(500) NULL
                """))
            elif db_type == 'sqlite':
                db_session.execute(text("""
                    ALTER TABLE bug_reports
                    ADD COLUMN screenshot_path VARCHAR(500)
                """))
            elif db_type == 'postgresql':
                db_session.execute(text("""
                    ALTER TABLE bug_reports
                    ADD COLUMN screenshot_path VARCHAR(500)
                """))
            else:
                flash(f'Unsupported database type: {db_type}', 'error')
                return redirect(url_for('admin.dashboard'))

            db_session.commit()

            # Verify the column was added
            inspector = inspect(engine)
            columns = [col['name'] for col in inspector.get_columns('bug_reports')]

            if 'screenshot_path' in columns:
                flash('Successfully added screenshot_path column to bug_reports table!', 'success')
                logger.info('Screenshot migration completed successfully')
            else:
                flash('Failed to verify screenshot_path column addition', 'error')

        except Exception as e:
            db_session.rollback()
            logger.error(f'Error running migration: {str(e)}')
            flash(f'Error running migration: {str(e)}', 'error')
        finally:
            db_session.close()

    except Exception as e:
        logger.error(f'Error in migration route: {str(e)}')
        flash(f'Error in migration route: {str(e)}', 'error')

    return redirect(url_for('admin.dashboard'))


@admin_bp.route('/manage-ticket-statuses', methods=['GET', 'POST'])
@admin_required
def manage_ticket_statuses():
    """Manage custom ticket statuses"""
    from models.custom_ticket_status import CustomTicketStatus
    from sqlalchemy import func

    db_session = db_manager.get_session()

    try:
        if request.method == 'POST':
            action = request.form.get('action') or request.json.get('action')

            if action == 'add':
                # Add new status
                name = request.form.get('name', '').strip()
                display_name = request.form.get('display_name', '').strip()
                color = request.form.get('color', 'gray')
                auto_return_to_stock = request.form.get('auto_return_to_stock') == 'true'

                if not name or not display_name:
                    return jsonify({'success': False, 'error': 'Name and display name are required'}), 400

                # Check if status already exists
                existing = db_session.query(CustomTicketStatus).filter(
                    CustomTicketStatus.name == name
                ).first()

                if existing:
                    return jsonify({'success': False, 'error': 'Status with this name already exists'}), 400

                # Get max sort_order
                max_order = db_session.query(func.max(CustomTicketStatus.sort_order)).scalar() or 0

                new_status = CustomTicketStatus(
                    name=name,
                    display_name=display_name,
                    color=color,
                    is_active=True,
                    is_system=False,
                    auto_return_to_stock=auto_return_to_stock,
                    sort_order=max_order + 1
                )

                db_session.add(new_status)
                db_session.commit()

                flash(f'Status "{display_name}" added successfully', 'success')
                return jsonify({'success': True, 'status': new_status.to_dict()})

            elif action == 'update':
                # Update existing status
                status_id = request.form.get('status_id') or request.json.get('status_id')
                display_name = request.form.get('display_name', '').strip() or request.json.get('display_name', '').strip()
                color = request.form.get('color', 'gray') or request.json.get('color', 'gray')
                is_active = request.form.get('is_active') == 'true' if request.form.get('is_active') else request.json.get('is_active', True)
                auto_return_to_stock = request.form.get('auto_return_to_stock') == 'true' if request.form.get('auto_return_to_stock') else request.json.get('auto_return_to_stock', False)

                status = db_session.query(CustomTicketStatus).get(status_id)
                if not status:
                    return jsonify({'success': False, 'error': 'Status not found'}), 404

                status.display_name = display_name
                status.color = color
                status.is_active = is_active
                status.auto_return_to_stock = auto_return_to_stock

                db_session.commit()

                flash(f'Status "{display_name}" updated successfully', 'success')
                return jsonify({'success': True, 'status': status.to_dict()})

            elif action == 'delete':
                # Delete status (only if not system and not in use)
                status_id = request.form.get('status_id') or request.json.get('status_id')

                status = db_session.query(CustomTicketStatus).get(status_id)
                if not status:
                    return jsonify({'success': False, 'error': 'Status not found'}), 404

                if status.is_system:
                    return jsonify({'success': False, 'error': 'Cannot delete system status'}), 400

                # TODO: Check if status is in use by any tickets
                # For now, just delete it

                db_session.delete(status)
                db_session.commit()

                flash(f'Status "{status.display_name}" deleted successfully', 'success')
                return jsonify({'success': True})

            elif action == 'reorder':
                # Update sort order
                import json
                order_data_str = request.form.get('order_data', '[]')
                try:
                    order_data = json.loads(order_data_str)
                except:
                    order_data = []

                for item in order_data:
                    status = db_session.query(CustomTicketStatus).get(item['id'])
                    if status:
                        status.sort_order = item['order']

                db_session.commit()

                return jsonify({'success': True})

        # GET request - show management page
        statuses = db_session.query(CustomTicketStatus).order_by(
            CustomTicketStatus.sort_order,
            CustomTicketStatus.name
        ).all()

        # Convert statuses to dictionaries for JSON serialization
        statuses_list = [status.to_dict() for status in statuses]

        return render_template('admin/manage_ticket_statuses.html',
                             statuses=statuses_list)

    except Exception as e:
        db_session.rollback()
        logger.error(f'Error managing ticket statuses: {str(e)}')
        if request.is_json:
            return jsonify({'success': False, 'error': str(e)}), 500
        flash(f'Error: {str(e)}', 'error')
        return redirect(url_for('admin.system_config'))
    finally:
        db_session.close()


@admin_bp.route('/api/ticket-statuses', methods=['GET'])
@login_required
def get_ticket_statuses():
    """API endpoint to get all active ticket statuses for dropdowns"""
    from models.custom_ticket_status import CustomTicketStatus
    from models.ticket import TicketStatus

    db_session = db_manager.get_session()

    try:
        # Get system statuses (from enum)
        system_statuses = [
            {'name': status.name, 'display_name': status.value, 'color': 'blue', 'is_system': True}
            for status in TicketStatus
        ]

        # Get custom statuses
        custom_statuses = db_session.query(CustomTicketStatus).filter(
            CustomTicketStatus.is_active == True
        ).order_by(CustomTicketStatus.sort_order).all()

        custom_statuses_list = [status.to_dict() for status in custom_statuses]

        return jsonify({
            'success': True,
            'system_statuses': system_statuses,
            'custom_statuses': custom_statuses_list
        })

    except Exception as e:
        logger.error(f'Error fetching ticket statuses: {str(e)}')
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db_session.close()


@admin_bp.route('/widget-preview/<widget_id>')
@login_required
def widget_preview(widget_id):
    """
    Render a single widget in isolation for screenshot capture.
    Used by the automated screenshot tool.
    """
    from models.dashboard_widget import get_widget, WidgetCategory
    from routes.dashboard import load_widget_data

    widget = get_widget(widget_id)
    if not widget:
        return "Widget not found", 404

    # Load widget data
    widget_data = load_widget_data(widget_id, current_user)

    # Category info for display
    category_info = {
        WidgetCategory.STATS: {'name': 'Statistics', 'icon': 'fas fa-chart-bar'},
        WidgetCategory.CHARTS: {'name': 'Charts', 'icon': 'fas fa-chart-pie'},
        WidgetCategory.LISTS: {'name': 'Lists', 'icon': 'fas fa-list'},
        WidgetCategory.ACTIONS: {'name': 'Quick Actions', 'icon': 'fas fa-bolt'},
        WidgetCategory.SYSTEM: {'name': 'System', 'icon': 'fas fa-cog'},
    }

    return render_template('admin/widget_preview.html',
                         widget=widget,
                         widget_data=widget_data,
                         category_info=category_info)
