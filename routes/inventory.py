from flask import Blueprint, render_template, request, jsonify, session, flash, redirect, url_for, send_file, abort, Response, current_app
from datetime import datetime
from utils.timezone_utils import singapore_now_as_utc
from utils.auth_decorators import login_required, admin_required, permission_required
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
from models.ticket import Ticket
from models.accessory_transaction import AccessoryTransaction
from models.audit_session import AuditSession
import os
from werkzeug.utils import secure_filename
import pandas as pd
from sqlalchemy import func, case, or_, and_, text, false as sa_false
from sqlalchemy.orm.attributes import flag_modified
from sqlalchemy.orm import joinedload
from utils.db_manager import DatabaseManager
from flask_wtf.csrf import generate_csrf
from flask_login import current_user
import json
import time
import io
import csv
from io import StringIO, BytesIO
import logging
import random
import traceback
from utils.countries import COUNTRIES

# Set up logging for this module
logger = logging.getLogger(__name__)


inventory_bp = Blueprint('inventory', __name__, url_prefix='/inventory')
db_manager = DatabaseManager()

def get_customer_display_name(db_session, customer_name):
    """Get the grouped display name for a customer by looking up the company"""
    if not customer_name:
        return None
    
    try:
        # Look up company by name
        company = db_session.query(Company).filter(Company.name == customer_name).first()
        if company:
            return company.grouped_display_name
        else:
            # If no company found, return the original customer name
            return customer_name
    except Exception as e:
        logger.error(f"Error getting customer display name for '{customer_name}': {e}")
        return customer_name

def get_filtered_customers(db_session, user):
    """Get customers filtered by company permissions for non-SUPER_ADMIN users"""
    from models.company_customer_permission import CompanyCustomerPermission
    from models.user_company_permission import UserCompanyPermission

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

def _safely_assign_asset_to_ticket(ticket, asset, db_session):
    """
    Safely assign an asset to a ticket, checking for existing relationships first.
    Uses direct SQL INSERT with ON CONFLICT to avoid race conditions.

    Args:
        ticket: Ticket object
        asset: Asset object
        db_session: Database session

    Returns:
        bool: True if assignment was successful or already exists, False otherwise
    """
    try:
        # Use INSERT OR IGNORE to handle the race condition properly
        # This way, if the link already exists, it's silently ignored
        stmt = text("""
            INSERT OR IGNORE INTO ticket_assets (ticket_id, asset_id)
            VALUES (:ticket_id, :asset_id)
        """)
        result = db_session.execute(stmt, {"ticket_id": ticket.id, "asset_id": asset.id})

        if result.rowcount > 0:
            logger.info(f"Successfully linked asset {asset.id} ({asset.asset_tag}) to ticket {ticket.id}")
        else:
            logger.info(f"Asset {asset.id} already linked to ticket {ticket.id} (no action needed)")

        return True

    except Exception as e:
        logger.error(f"Error assigning asset to ticket: {str(e)}")
        return False

# Configure upload settings
UPLOAD_FOLDER = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'uploads'))
ALLOWED_EXTENSIONS = {'csv'}

if not os.path.exists(UPLOAD_FOLDER): 
    os.makedirs(UPLOAD_FOLDER)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@inventory_bp.route('/debug-permissions')
@login_required
def debug_user_permissions():
    """Debug endpoint to check current user's company permissions"""
    from models.user_company_permission import UserCompanyPermission
    from models.user_country_permission import UserCountryPermission

    db_session = db_manager.get_session()
    try:
        user = db_manager.get_user(session['user_id'])

        # Get company permissions
        company_perms = db_session.query(UserCompanyPermission).filter_by(user_id=user.id).all()
        permitted_company_ids = [perm.company_id for perm in company_perms]

        company_perm_data = []
        all_company_ids = list(permitted_company_ids)

        for perm in company_perms:
            company = db_session.query(Company).get(perm.company_id)
            child_companies = []
            if company and (company.is_parent_company or company.child_companies.count() > 0):
                children = company.child_companies.all()
                child_companies = [{'id': c.id, 'name': c.name} for c in children]
                all_company_ids.extend([c.id for c in children])

            company_perm_data.append({
                'company_id': perm.company_id,
                'company_name': company.name if company else 'NOT FOUND',
                'is_parent': company.is_parent_company if company else None,
                'child_count': company.child_companies.count() if company else 0,
                'child_companies': child_companies,
                'can_view': perm.can_view
            })

        # Get country permissions
        country_perms = db_session.query(UserCountryPermission).filter_by(user_id=user.id).all()
        country_data = [perm.country for perm in country_perms]

        # Count assets that would be visible
        all_company_ids = list(set(all_company_ids))

        # Assets matching company IDs only
        assets_by_company = db_session.query(Asset).filter(Asset.company_id.in_(all_company_ids)).count()

        # Assets matching country only
        assets_by_country = 0
        if country_data:
            assets_by_country = db_session.query(Asset).filter(Asset.country.in_(country_data)).count()

        # Assets matching BOTH company AND country (what user actually sees)
        assets_with_both_filters = 0
        if country_data:
            assets_with_both_filters = db_session.query(Asset).filter(
                Asset.company_id.in_(all_company_ids),
                Asset.country.in_(country_data)
            ).count()
        else:
            assets_with_both_filters = assets_by_company

        total_assets = db_session.query(Asset).count()

        return {
            'user_id': user.id,
            'username': user.username,
            'user_type': user.user_type.value if user.user_type else None,
            'company_id': user.company_id,
            'assigned_countries': country_data,
            'company_permissions': company_perm_data,
            'total_company_permissions': len(company_perm_data),
            'all_permitted_company_ids': all_company_ids,
            'assets_matching_companies_only': assets_by_company,
            'assets_matching_country_only': assets_by_country,
            'assets_matching_BOTH_filters': assets_with_both_filters,
            'total_assets_in_db': total_assets,
            'NOTE': 'Inventory shows assets matching BOTH company AND country filters!'
        }
    finally:
        db_session.close()

@inventory_bp.route('/')
@login_required
def view_inventory():
    # Check if we should redirect to SF view based on system setting
    # Allow ?use_classic=1 to bypass the redirect for preview purposes
    if not request.args.get('use_classic'):
        redirect_db_session = None
        try:
            redirect_db_session = db_manager.get_session()
            from models.system_settings import SystemSettings
            inventory_view_setting = redirect_db_session.query(SystemSettings).filter_by(
                setting_key='default_inventory_view'
            ).first()
            if inventory_view_setting and inventory_view_setting.get_value() == 'sf':
                # Preserve any query parameters when redirecting (exclude use_classic)
                args = {k: v for k, v in request.args.items() if k != 'use_classic'}
                return redirect(url_for('inventory.view_inventory_sf', **args))
        except Exception as e:
            logger.warning(f"Could not check default_inventory_view setting: {str(e)}")
        finally:
            if redirect_db_session:
                redirect_db_session.close()

    db_session = db_manager.get_session()
    try:
        # Get the current user
        user = db_manager.get_user(session['user_id'])

        # Debug info
        logger.info(f"DEBUG: User accessing inventory: ID={user.id}, Username={user.username}, Type={user.user_type}")
        logger.info(f"DEBUG: user.user_type == UserType.SUPERVISOR: {user.user_type == UserType.SUPERVISOR}")
        logger.info(f"DEBUG: user.user_type == UserType.COUNTRY_ADMIN: {user.user_type == UserType.COUNTRY_ADMIN}")

        # Base query for tech assets
        tech_assets_query = db_session.query(Asset)

        # Apply filtering for COUNTRY_ADMIN and SUPERVISOR users
        is_restricted_user = (user.user_type == UserType.COUNTRY_ADMIN or user.user_type == UserType.SUPERVISOR)
        logger.info(f"DEBUG: is_restricted_user = {is_restricted_user}")

        if is_restricted_user:
            logger.info(f"DEBUG: Applying company filtering for {user.user_type.value} user")
            from models.user_company_permission import UserCompanyPermission

            # Filter by country if assigned
            if user.assigned_countries:
                logger.info(f"DEBUG: Filtering by assigned countries: {user.assigned_countries}")
                tech_assets_query = tech_assets_query.filter(Asset.country.in_(user.assigned_countries))

            # ALWAYS filter by company permissions for COUNTRY_ADMIN/SUPERVISOR
            child_company_permissions = db_session.query(UserCompanyPermission).filter_by(
                user_id=user.id,
                can_view=True
            ).all()

            if child_company_permissions:
                # User has specific company permissions - filter by ONLY those companies
                permitted_company_ids = [perm.company_id for perm in child_company_permissions]
                logger.info(f"DEBUG: Filtering by company IDs: {permitted_company_ids}")

                # Get the actual company objects to also check by name
                permitted_companies = db_session.query(Company).filter(Company.id.in_(permitted_company_ids)).all()
                permitted_company_names = [c.name.strip() for c in permitted_companies]
                logger.info(f"DEBUG: Filtering by company names: {permitted_company_names}")

                # Also include child companies of any parent company the user has permission to
                # This enforces Asset Company Grouping for SUPERVISOR/COUNTRY_ADMIN
                all_company_names = list(permitted_company_names)
                all_company_ids = list(permitted_company_ids)
                for company in permitted_companies:
                    if company.is_parent_company or company.child_companies.count() > 0:
                        # This is a parent company - include all child company names AND IDs
                        child_companies = company.child_companies.all()
                        child_names = [c.name.strip() for c in child_companies]
                        child_ids = [c.id for c in child_companies]
                        all_company_names.extend(child_names)
                        all_company_ids.extend(child_ids)
                        logger.info(f"DEBUG: Including child companies of {company.name}: {child_names} (IDs: {child_ids})")

                # Build OR conditions for flexible name matching
                # Match by company_id OR customer name (with case-insensitive partial match)
                # IMPORTANT: Also exclude assets with no company_id (unknown company)
                name_conditions = [func.lower(Asset.customer).like(f"%{name.lower()}%") for name in all_company_names]
                tech_assets_query = tech_assets_query.filter(
                    and_(
                        Asset.company_id.isnot(None),  # Must have a company_id assigned
                        or_(
                            Asset.company_id.in_(all_company_ids),
                            *name_conditions
                        )
                    )
                )
                logger.info(f"DEBUG: {user.user_type.value} filtering by {len(all_company_ids)} company IDs (including children): {all_company_ids} and names: {all_company_names}")
            else:
                # No company permissions assigned - show NO assets
                # This forces admin to explicitly assign companies through the UI
                tech_assets_query = tech_assets_query.filter(Asset.id == -1)  # Impossible condition = no results
                logger.info(f"DEBUG: {user.user_type.value} has NO company permissions - showing 0 assets")

        # Filter by company if user is a client (can only see their company's assets)
        if user.user_type == UserType.CLIENT and user.company:
            # Filter by company_id and also by customer field matching company name
            tech_assets_query = tech_assets_query.filter(
                or_(
                    Asset.company_id == user.company_id,
                    Asset.customer == user.company.name
                )
            )
            logger.info("DEBUG: Filtering assets for client user. Company ID: {user.company_id}, Company Name: {user.company.name}")
        
        # Get counts
        tech_assets_count = tech_assets_query.count()
        logger.info(f"DEBUG: Final tech_assets_count = {tech_assets_count}")
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
        company_names_raw = tech_assets_query.with_entities(Asset.customer).distinct().all()
        # Check if there are assets with no company (empty or null)
        has_unknown_company = any(not c[0] or (c[0] and c[0].strip() == '') for c in company_names_raw)
        company_names = sorted(list(set([c[0] for c in company_names_raw if c[0] and c[0].strip()])))

        # Build company list with grouped display names for the filter dropdown
        companies = []

        # Add "Unknown" option first if there are assets without companies
        if has_unknown_company:
            companies.append({
                'value': '',
                'label': 'Unknown',
                'is_parent': False
            })

        for company_name in company_names:
            company_obj = db_session.query(Company).filter(Company.name == company_name).first()
            if company_obj:
                companies.append({
                    'value': company_name,
                    'label': company_obj.grouped_display_name,
                    'is_parent': company_obj.is_parent_company or company_obj.child_companies.count() > 0
                })
            else:
                companies.append({
                    'value': company_name,
                    'label': company_name,
                    'is_parent': False
                })

        models = tech_assets_query.with_entities(Asset.model).distinct().all()
        models = sorted(list(set([m[0] for m in models if m[0]])))

        # Get unique status values for the status filter
        statuses = tech_assets_query.with_entities(Asset.status).distinct().all()
        statuses = sorted(list(set([s[0].value for s in statuses if s[0]])))

        # For Country Admin or Supervisor, show actual countries from assets (not just assigned country)
        if (user.user_type == UserType.COUNTRY_ADMIN or user.user_type == UserType.SUPERVISOR) and user.assigned_countries:
            countries_raw = tech_assets_query.with_entities(Asset.country).distinct().all()
            # Use case-insensitive deduplication and proper capitalization
            countries_seen = set()
            countries = []
            for c in sorted([c[0] for c in countries_raw if c[0]]):
                country_lower = c.lower()
                if country_lower not in countries_seen:
                    countries_seen.add(country_lower)
                    # Use proper case format
                    countries.append(c.title())
        # For Client users, only show countries relevant to their company's assets
        elif user.user_type == UserType.CLIENT and user.company:
            countries_raw = tech_assets_query.with_entities(Asset.country).distinct().all()
            # Use case-insensitive deduplication and proper capitalization
            countries_seen = set()
            countries = []
            for c in sorted([c[0] for c in countries_raw if c[0]]):
                country_lower = c.lower()
                if country_lower not in countries_seen:
                    countries_seen.add(country_lower)
                    # Use proper case format
                    countries.append(c.title())
        else:
            countries_raw = tech_assets_query.with_entities(Asset.country).distinct().all()
            # Use case-insensitive deduplication and proper capitalization
            countries_seen = set()
            countries = []
            for c in sorted([c[0] for c in countries_raw if c[0]]):
                country_lower = c.lower()
                if country_lower not in countries_seen:
                    countries_seen.add(country_lower)
                    # Use proper case format
                    countries.append(c.title())

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

        # Get all customers for the checkout form (filtered by company for non-SUPER_ADMIN users)
        customers = get_filtered_customers(db_session, user)

        # Debug template data
        is_supervisor = user.user_type == UserType.SUPERVISOR
        is_client = user.user_type == UserType.CLIENT
        logger.info("DEBUG: Template vars - is_admin={user.is_admin}, is_country_admin={user.is_country_admin}, is_supervisor={is_supervisor}, is_client={is_client}")
        
        return render_template(
            'inventory/view.html',
            tech_assets_count=tech_assets_count,
            accessories_count=accessories_count,
            maintenance_assets_count=maintenance_assets_count,
            companies=companies,
            models=models,
            countries=countries,
            statuses=statuses,
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


# ============================================================
# Salesforce-style Inventory View (Developer Only)
# ============================================================

@inventory_bp.route('/sf')
@login_required
def view_inventory_sf():
    """Salesforce-style inventory view - Admin and Supervisor users"""
    user = db_manager.get_user(session['user_id'])

    # Allow SUPER_ADMIN, DEVELOPER, SUPERVISOR, and COUNTRY_ADMIN users to access this view
    if user.user_type not in [UserType.DEVELOPER, UserType.SUPER_ADMIN, UserType.SUPERVISOR, UserType.COUNTRY_ADMIN]:
        flash('This view is only available for authorized users.', 'error')
        return redirect(url_for('inventory.view_inventory'))

    return render_template('inventory/view_sf.html', user=user)


@inventory_bp.route('/api/sf/filters')
@login_required
def api_sf_filters():
    """Get filter options for SF inventory view"""
    try:
        user_id = session.get('user_id')
        user_type = session.get('user_type')

        logger.info(f"SF Filters API called - user_id: {user_id}, user_type: {user_type}")

        if not user_id:
            return jsonify({'success': False, 'error': 'No user in session'}), 403

        # Allow DEVELOPER, SUPER_ADMIN, SUPERVISOR, and COUNTRY_ADMIN users
        if user_type not in ['DEVELOPER', 'SUPER_ADMIN', 'SUPERVISOR', 'COUNTRY_ADMIN']:
            return jsonify({'success': False, 'error': f'Access denied (you are {user_type})'}), 403

        db_session = db_manager.get_session()
        try:
            # Build base query with filtering for SUPERVISOR and COUNTRY_ADMIN
            base_query = db_session.query(Asset)

            # Apply filtering for SUPERVISOR and COUNTRY_ADMIN users
            if user_type in ['SUPERVISOR', 'COUNTRY_ADMIN']:
                from models.user_company_permission import UserCompanyPermission
                user = db_manager.get_user(user_id)

                # Filter by assigned countries
                if user.assigned_countries:
                    base_query = base_query.filter(Asset.country.in_(user.assigned_countries))
                    logger.info(f"SF Filters API: Filtering by countries: {user.assigned_countries}")

                # Filter by company permissions
                company_permissions = db_session.query(UserCompanyPermission).filter_by(
                    user_id=user_id,
                    can_view=True
                ).all()

                if company_permissions:
                    permitted_company_ids = [perm.company_id for perm in company_permissions]
                    permitted_companies = db_session.query(Company).filter(Company.id.in_(permitted_company_ids)).all()

                    # Include child company IDs
                    all_company_ids = list(permitted_company_ids)
                    all_company_names = [c.name.strip() for c in permitted_companies]

                    for company in permitted_companies:
                        if company.is_parent_company or company.child_companies.count() > 0:
                            child_companies = company.child_companies.all()
                            all_company_ids.extend([c.id for c in child_companies])
                            all_company_names.extend([c.name.strip() for c in child_companies])

                    # Filter by company_id or customer name
                    name_conditions = [func.lower(Asset.customer).like(f"%{name.lower()}%") for name in all_company_names]
                    base_query = base_query.filter(
                        or_(
                            Asset.company_id.in_(all_company_ids),
                            *name_conditions
                        )
                    )
                    logger.info(f"SF Filters API: Filtering by {len(all_company_ids)} company IDs")
                else:
                    # No permissions - show no assets
                    base_query = base_query.filter(Asset.id == -1)
                    logger.info(f"SF Filters API: No company permissions - showing 0 assets")

            # Get filtered asset IDs for subqueries
            filtered_asset_ids = base_query.with_entities(Asset.id).subquery()

            # Get status counts from filtered assets
            status_counts = db_session.query(
                Asset.status, func.count(Asset.id)
            ).filter(Asset.id.in_(filtered_asset_ids)).group_by(Asset.status).all()

            statuses = [
                {'value': s[0].value if s[0] else 'Unknown', 'label': s[0].value if s[0] else 'Unknown', 'count': s[1]}
                for s in status_counts if s[0]
            ]

            # Get tech asset category counts from filtered assets
            asset_category_counts = db_session.query(
                Asset.asset_type, func.count(Asset.id)
            ).filter(Asset.id.in_(filtered_asset_ids)).group_by(Asset.asset_type).all()

            asset_categories = [
                {'value': c[0] or 'Unknown', 'label': c[0] or 'Unknown', 'count': c[1]}
                for c in asset_category_counts if c[0]
            ]

            # Get accessory category counts with filtering for SUPERVISOR and COUNTRY_ADMIN
            accessory_query = db_session.query(Accessory)

            if user_type in ['SUPERVISOR', 'COUNTRY_ADMIN']:
                from models.user_company_permission import UserCompanyPermission
                user = db_manager.get_user(user_id)

                # Filter accessories by country
                if user.assigned_countries:
                    accessory_query = accessory_query.filter(Accessory.country.in_(user.assigned_countries))

                # Filter by company permissions
                company_permissions = db_session.query(UserCompanyPermission).filter_by(
                    user_id=user_id,
                    can_view=True
                ).all()

                if company_permissions:
                    permitted_company_ids = [perm.company_id for perm in company_permissions]
                    permitted_companies_obj = db_session.query(Company).filter(Company.id.in_(permitted_company_ids)).all()
                    all_acc_company_ids = list(permitted_company_ids)

                    for comp in permitted_companies_obj:
                        if comp.is_parent_company or comp.child_companies.count() > 0:
                            child_comps = comp.child_companies.all()
                            all_acc_company_ids.extend([c.id for c in child_comps])

                    accessory_query = accessory_query.filter(
                        or_(
                            Accessory.company_id.in_(all_acc_company_ids),
                            Accessory.company_id.is_(None)
                        )
                    )

            filtered_accessory_ids = accessory_query.with_entities(Accessory.id).subquery()

            accessory_category_counts = db_session.query(
                Accessory.category, func.count(Accessory.id)
            ).filter(Accessory.id.in_(filtered_accessory_ids)).group_by(Accessory.category).all()

            accessory_categories = [
                {'value': c[0] or 'Unknown', 'label': c[0] or 'Unknown', 'count': c[1]}
                for c in accessory_category_counts if c[0]
            ]

            # Combined categories (for backward compatibility)
            categories = asset_categories

            # Get company counts from filtered assets
            company_counts = db_session.query(
                Asset.customer, func.count(Asset.id)
            ).filter(Asset.id.in_(filtered_asset_ids)).group_by(Asset.customer).all()

            # Build company list with parent/child relationship info
            companies = []
            company_grouping = {}  # Maps company name to parent company name

            for company_name, count in company_counts:
                # Handle empty/null company names as "Unknown"
                if not company_name or company_name.strip() == '':
                    companies.append({
                        'value': '',  # Empty value to match assets with no company
                        'label': 'Unknown',
                        'count': count,
                        'parent_company': None,
                        'is_parent': False,
                        'child_companies': []
                    })
                    continue

                # Look up company to get grouping info
                company_obj = db_session.query(Company).filter(Company.name == company_name).first()

                parent_company_name = None
                is_parent = False
                child_companies = []

                if company_obj:
                    # Check if this company has a parent
                    if company_obj.parent_company_id and company_obj.parent_company:
                        parent_company_name = company_obj.parent_company.name
                        company_grouping[company_name] = parent_company_name

                    # Check if this company is a parent (has children)
                    if company_obj.is_parent_company or company_obj.child_companies.count() > 0:
                        is_parent = True
                        child_companies = [c.name for c in company_obj.child_companies.all()]

                companies.append({
                    'value': company_name,
                    'label': company_obj.grouped_display_name if company_obj else company_name,
                    'count': count,
                    'parent_company': parent_company_name,
                    'is_parent': is_parent,
                    'child_companies': child_companies
                })

            # Get country counts from filtered assets
            country_counts = db_session.query(
                Asset.country, func.count(Asset.id)
            ).filter(Asset.id.in_(filtered_asset_ids)).group_by(Asset.country).all()

            countries = [
                {'value': c[0] or 'Unknown', 'label': c[0] or 'Unknown', 'count': c[1]}
                for c in country_counts if c[0]
            ]

            # Get location counts from filtered assets
            location_counts = db_session.query(
                Location.name, func.count(Asset.id)
            ).outerjoin(Asset, Asset.location_id == Location.id
            ).filter(Asset.id.in_(filtered_asset_ids)
            ).group_by(Location.name).all()

            locations = [
                {'value': l[0] or 'Unknown', 'label': l[0] or 'Unknown', 'count': l[1]}
                for l in location_counts if l[0]
            ]

            return jsonify({
                'success': True,
                'statuses': sorted(statuses, key=lambda x: x['label']),
                'categories': sorted(categories, key=lambda x: x['label']),
                'asset_categories': sorted(asset_categories, key=lambda x: x['label']),
                'accessory_categories': sorted(accessory_categories, key=lambda x: x['label']),
                'companies': sorted(companies, key=lambda x: x['label']),
                'company_grouping': company_grouping,  # Maps child company -> parent company
                'countries': sorted(countries, key=lambda x: x['label']),
                'locations': sorted(locations, key=lambda x: x['label'])
            })

        finally:
            db_session.close()

    except Exception as e:
        logger.error(f"Error getting SF filters: {e}")
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@inventory_bp.route('/api/sf/test')
@login_required
def api_sf_test():
    """Simple test endpoint"""
    try:
        user_id = session.get('user_id')
        user_type = session.get('user_type')
        return jsonify({
            'success': True,
            'user_id': user_id,
            'user_type': user_type,
            'message': 'API is working'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@inventory_bp.route('/api/sf/assets')
@login_required
def api_sf_assets():
    """Get all assets for SF inventory view"""
    try:
        user_id = session.get('user_id')
        user_type = session.get('user_type')

        logger.info(f"SF Assets API called - user_id: {user_id}, user_type: {user_type}")

        if not user_id:
            return jsonify({'success': False, 'error': 'No user in session'}), 403

        # Allow DEVELOPER, SUPER_ADMIN, SUPERVISOR, and COUNTRY_ADMIN users
        if user_type not in ['DEVELOPER', 'SUPER_ADMIN', 'SUPERVISOR', 'COUNTRY_ADMIN']:
            return jsonify({'success': False, 'error': f'Access denied (you are {user_type})'}), 403

        db_session = db_manager.get_session()
        try:
            # Build query with filtering for SUPERVISOR and COUNTRY_ADMIN
            assets_query = db_session.query(Asset)

            # Apply filtering for SUPERVISOR and COUNTRY_ADMIN users
            if user_type in ['SUPERVISOR', 'COUNTRY_ADMIN']:
                from models.user_company_permission import UserCompanyPermission
                user = db_manager.get_user(user_id)

                # Filter by assigned countries
                if user.assigned_countries:
                    assets_query = assets_query.filter(Asset.country.in_(user.assigned_countries))
                    logger.info(f"SF API: Filtering by countries: {user.assigned_countries}")

                # Filter by company permissions
                company_permissions = db_session.query(UserCompanyPermission).filter_by(
                    user_id=user_id,
                    can_view=True
                ).all()

                if company_permissions:
                    permitted_company_ids = [perm.company_id for perm in company_permissions]
                    permitted_companies = db_session.query(Company).filter(Company.id.in_(permitted_company_ids)).all()

                    # Include child company IDs
                    all_company_ids = list(permitted_company_ids)
                    all_company_names = [c.name.strip() for c in permitted_companies]

                    for company in permitted_companies:
                        if company.is_parent_company or company.child_companies.count() > 0:
                            child_companies = company.child_companies.all()
                            all_company_ids.extend([c.id for c in child_companies])
                            all_company_names.extend([c.name.strip() for c in child_companies])

                    # Filter by company_id or customer name
                    name_conditions = [func.lower(Asset.customer).like(f"%{name.lower()}%") for name in all_company_names]
                    assets_query = assets_query.filter(
                        or_(
                            Asset.company_id.in_(all_company_ids),
                            *name_conditions
                        )
                    )
                    logger.info(f"SF API: Filtering by {len(all_company_ids)} company IDs")
                else:
                    # No permissions - show no assets
                    assets_query = assets_query.filter(Asset.id == -1)
                    logger.info(f"SF API: No company permissions - showing 0 assets")

            # Get total count
            total_count = assets_query.count()
            logger.info(f"Total assets after filtering: {total_count}")

            # Get filtered assets
            assets = assets_query.all()
            logger.info(f"Fetched {len(assets)} assets")

            # Pre-fetch all locations into a map (avoids lazy loading)
            all_locations = db_session.query(Location).all()
            location_map = {loc.id: loc.name for loc in all_locations}

            # Pre-fetch all company info (avoids lazy loading)
            all_companies = db_session.query(Company).all()
            company_id_to_name = {c.id: c.name for c in all_companies}
            company_parent_map = {}  # Maps company name -> parent company name
            for company in all_companies:
                if company.parent_company_id:
                    parent_name = company_id_to_name.get(company.parent_company_id)
                    if parent_name:
                        company_parent_map[company.name] = parent_name

            assets_data = []
            error_count = 0
            for asset in assets:
                try:
                    # Get parent company if this asset's company has one
                    parent_company = company_parent_map.get(asset.customer, None)

                    # Get location name from pre-fetched map (avoids relationship access)
                    location_name = location_map.get(asset.location_id, '') if asset.location_id else ''

                    # Handle status - could be Enum, string, or None
                    if asset.status is None:
                        status_str = 'Unknown'
                    elif hasattr(asset.status, 'value'):
                        status_str = asset.status.value
                    else:
                        status_str = str(asset.status)

                    assets_data.append({
                        'id': asset.id,
                        'asset_tag': asset.asset_tag or '',
                        'name': asset.name or '',
                        'serial_number': asset.serial_num or '',
                        'status': status_str,
                        'category': asset.asset_type or '',
                        'customer': asset.customer or '',
                        'company': asset.customer or '',
                        'parent_company': parent_company,  # Parent company name for grouping filter
                        'country': asset.country or '',
                        'location': location_name,
                        'model': asset.model or '',
                        'manufacturer': asset.manufacturer or ''
                    })
                except Exception as asset_error:
                    error_count += 1
                    logger.error(f"Error processing asset {asset.id}: {asset_error}")
                    traceback.print_exc()
                    continue

            if error_count > 0:
                logger.warning(f"Failed to process {error_count} assets")

            logger.info(f"Processed {len(assets_data)} assets successfully")

            return jsonify({
                'success': True,
                'assets': assets_data,
                'total': len(assets_data)
            })

        finally:
            db_session.close()

    except Exception as e:
        logger.error(f"Error getting SF assets: {e}")
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@inventory_bp.route('/api/sf/accessories')
@login_required
def api_sf_accessories():
    """Get all accessories for SF inventory view"""
    try:
        user_id = session.get('user_id')
        user_type = session.get('user_type')

        logger.info(f"SF Accessories API called - user_id: {user_id}, user_type: {user_type}")

        if not user_id:
            return jsonify({'success': False, 'error': 'No user in session'}), 403

        # Allow DEVELOPER, SUPER_ADMIN, SUPERVISOR, and COUNTRY_ADMIN users
        if user_type not in ['DEVELOPER', 'SUPER_ADMIN', 'SUPERVISOR', 'COUNTRY_ADMIN']:
            return jsonify({'success': False, 'error': f'Access denied (you are {user_type})'}), 403

        db_session = db_manager.get_session()
        try:
            # Build query with filtering for SUPERVISOR and COUNTRY_ADMIN
            accessories_query = db_session.query(Accessory)

            # Apply filtering for SUPERVISOR and COUNTRY_ADMIN users
            if user_type in ['SUPERVISOR', 'COUNTRY_ADMIN']:
                from models.user_company_permission import UserCompanyPermission
                user = db_manager.get_user(user_id)

                # Filter by assigned countries
                if user.assigned_countries:
                    accessories_query = accessories_query.filter(Accessory.country.in_(user.assigned_countries))
                    logger.info(f"SF Accessories API: Filtering by countries: {user.assigned_countries}")

                # Filter by company permissions
                company_permissions = db_session.query(UserCompanyPermission).filter_by(
                    user_id=user_id,
                    can_view=True
                ).all()

                if company_permissions:
                    permitted_company_ids = [perm.company_id for perm in company_permissions]
                    permitted_companies = db_session.query(Company).filter(Company.id.in_(permitted_company_ids)).all()

                    # Include child company IDs
                    all_company_ids = list(permitted_company_ids)

                    for company in permitted_companies:
                        if company.is_parent_company or company.child_companies.count() > 0:
                            child_companies = company.child_companies.all()
                            all_company_ids.extend([c.id for c in child_companies])

                    # Filter by company_id (accessories use company_id directly, not customer name)
                    accessories_query = accessories_query.filter(
                        or_(
                            Accessory.company_id.in_(all_company_ids),
                            Accessory.company_id.is_(None)  # Also show accessories with no company assigned
                        )
                    )
                    logger.info(f"SF Accessories API: Filtering by {len(all_company_ids)} company IDs")
                else:
                    # No permissions - show only accessories without company assignment
                    accessories_query = accessories_query.filter(Accessory.company_id.is_(None))
                    logger.info(f"SF Accessories API: No company permissions - showing only unassigned accessories")

            # Get filtered accessories
            accessories = accessories_query.all()
            logger.info(f"Fetched {len(accessories)} accessories")

            # Pre-fetch all company info (avoids lazy loading)
            all_companies = db_session.query(Company).all()
            company_id_to_name = {c.id: c.name for c in all_companies}

            accessories_data = []
            for acc in accessories:
                try:
                    # Get company name from pre-fetched map
                    company_name = company_id_to_name.get(acc.company_id, '') if acc.company_id else ''

                    accessories_data.append({
                        'id': acc.id,
                        'name': acc.name or '',
                        'category': acc.category or '',
                        'manufacturer': acc.manufacturer or '',
                        'model_no': acc.model_no or '',
                        'total_quantity': acc.total_quantity or 0,
                        'available_quantity': acc.available_quantity or 0,
                        'country': acc.country or '',
                        'company': company_name,
                        'company_id': acc.company_id,
                        'status': acc.status or 'Unknown',
                        'notes': acc.notes or ''
                    })
                except Exception as acc_error:
                    logger.error(f"Error processing accessory {acc.id}: {acc_error}")
                    continue

            logger.info(f"Processed {len(accessories_data)} accessories successfully")

            return jsonify({
                'success': True,
                'accessories': accessories_data,
                'total': len(accessories_data)
            })

        finally:
            db_session.close()

    except Exception as e:
        logger.error(f"Error getting SF accessories: {e}")
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@inventory_bp.route('/api/sf/chart-settings', methods=['GET'])
@login_required
def api_sf_get_chart_settings():
    """Get user's saved chart settings for SF inventory view"""
    try:
        user_id = session.get('user_id')
        user_type = session.get('user_type')

        if not user_id:
            return jsonify({'success': False, 'error': 'No user in session'}), 403

        # Allow DEVELOPER, SUPER_ADMIN, SUPERVISOR, and COUNTRY_ADMIN users
        if user_type not in ['DEVELOPER', 'SUPER_ADMIN', 'SUPERVISOR', 'COUNTRY_ADMIN']:
            return jsonify({'success': False, 'error': 'Access denied'}), 403

        db_session = db_manager.get_session()
        try:
            user = db_session.query(User).filter_by(id=user_id).first()
            if not user:
                return jsonify({'success': False, 'error': 'User not found'}), 404

            # Get chart settings from user preferences
            preferences = user.preferences or {}
            # Handle stringified JSON stored in SQLite
            if isinstance(preferences, str):
                try:
                    import json as _json
                    preferences = _json.loads(preferences)
                except Exception:
                    preferences = {}

            chart_settings = preferences.get('sf_inventory_charts', [
                {'id': 1, 'chartType': 'doughnut', 'groupBy': 'status'}
            ])

            logger.info(f"Loading chart settings for user {user_id}: {chart_settings}")

            return jsonify({
                'success': True,
                'charts': chart_settings
            })

        finally:
            db_session.close()

    except Exception as e:
        logger.error(f"Error getting chart settings: {e}")
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@inventory_bp.route('/api/sf/chart-settings', methods=['POST'])
@login_required
def api_sf_save_chart_settings():
    """Save user's chart settings for SF inventory view"""
    try:
        user_id = session.get('user_id')
        user_type = session.get('user_type')

        if not user_id:
            return jsonify({'success': False, 'error': 'No user in session'}), 403

        # Allow DEVELOPER, SUPER_ADMIN, SUPERVISOR, and COUNTRY_ADMIN users
        if user_type not in ['DEVELOPER', 'SUPER_ADMIN', 'SUPERVISOR', 'COUNTRY_ADMIN']:
            return jsonify({'success': False, 'error': 'Access denied'}), 403

        data = request.get_json()
        if not data or 'charts' not in data:
            return jsonify({'success': False, 'error': 'No chart settings provided'}), 400

        db_session = db_manager.get_session()
        try:
            user = db_session.query(User).filter_by(id=user_id).first()
            if not user:
                return jsonify({'success': False, 'error': 'User not found'}), 404

            # Update user preferences
            preferences = user.preferences or {}
            if isinstance(preferences, str):
                try:
                    import json as _json
                    preferences = _json.loads(preferences)
                except Exception:
                    preferences = {}

            preferences['sf_inventory_charts'] = data['charts']
            user.preferences = preferences

            # Flag the preferences field as modified to ensure SQLAlchemy detects the change
            flag_modified(user, 'preferences')

            db_session.commit()

            logger.info(f"Saved chart settings for user {user_id}: {data['charts']}")

            return jsonify({
                'success': True,
                'message': 'Chart settings saved successfully',
                'charts': data['charts']
            })

        finally:
            db_session.close()

    except Exception as e:
        logger.error(f"Error saving chart settings: {e}")
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@inventory_bp.route('/api/sf/bulk-update', methods=['POST'])
@login_required
def api_bulk_update_assets():
    """Bulk update multiple assets"""
    try:
        user_id = session.get('user_id')
        user_type = session.get('user_type')

        if not user_id:
            return jsonify({'success': False, 'error': 'No user in session'}), 403

        # Only allow DEVELOPER and SUPER_ADMIN users
        if user_type not in ['DEVELOPER', 'SUPER_ADMIN']:
            return jsonify({'success': False, 'error': 'Access denied - Admin only'}), 403

        data = request.get_json()
        if data is None:
            return jsonify({'success': False, 'error': 'No JSON data provided'}), 400

        asset_ids = data.get('asset_ids', [])
        changes = data.get('changes', {})

        if not asset_ids:
            return jsonify({'success': False, 'error': 'No assets selected'}), 400

        if not changes:
            return jsonify({'success': False, 'error': 'No changes specified'}), 400

        db_session = db_manager.get_session()
        try:
            updated_count = 0

            for asset_id in asset_ids:
                asset = db_session.query(Asset).get(asset_id)
                if not asset:
                    continue

                # Apply changes
                if 'name' in changes:
                    asset.name = changes['name']

                if 'asset_tag' in changes:
                    asset.asset_tag = changes['asset_tag']

                if 'serial_number' in changes:
                    asset.serial_number = changes['serial_number']

                if 'status' in changes:
                    try:
                        asset.status = AssetStatus(changes['status'])
                    except ValueError:
                        # If status value doesn't match enum, try setting directly
                        pass

                if 'country' in changes:
                    asset.country = changes['country']

                if 'company' in changes:
                    # Find company by name
                    company = db_session.query(Company).filter(
                        Company.name == changes['company']
                    ).first()
                    if company:
                        asset.company_id = company.id

                if 'asset_type' in changes:
                    asset.asset_type = changes['asset_type']

                if 'location' in changes:
                    location_name = changes['location']
                    if location_name:
                        # Find location by name
                        location = db_session.query(Location).filter(
                            Location.name == location_name
                        ).first()
                        if location:
                            asset.location_id = location.id
                    else:
                        # Empty location - clear the location_id
                        asset.location_id = None

                if 'notes' in changes and changes['notes']:
                    # Append notes
                    existing_notes = asset.notes or ''
                    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')
                    new_note = f"\n[Bulk Edit {timestamp}]: {changes['notes']}"
                    asset.notes = existing_notes + new_note

                asset.updated_at = datetime.now()
                updated_count += 1

            db_session.commit()

            return jsonify({
                'success': True,
                'updated_count': updated_count,
                'message': f'Successfully updated {updated_count} assets'
            })

        except Exception as e:
            db_session.rollback()
            logger.error(f"Bulk update error: {str(e)}")
            return jsonify({'success': False, 'error': str(e)}), 500
        finally:
            db_session.close()

    except Exception as e:
        logger.error(f"Bulk update API error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@inventory_bp.route('/api/sf/bulk-update-individual', methods=['POST'])
@login_required
def api_bulk_update_individual():
    """Bulk update multiple assets with individual changes per asset"""
    try:
        user_id = session.get('user_id')
        user_type = session.get('user_type')

        if not user_id:
            return jsonify({'success': False, 'error': 'No user in session'}), 403

        # Only allow DEVELOPER and SUPER_ADMIN users
        if user_type not in ['DEVELOPER', 'SUPER_ADMIN']:
            return jsonify({'success': False, 'error': 'Access denied - Admin only'}), 403

        data = request.get_json()
        if data is None:
            return jsonify({'success': False, 'error': 'No JSON data provided'}), 400

        assets_data = data.get('assets', [])

        if not assets_data:
            return jsonify({'success': False, 'error': 'No assets provided'}), 400

        db_session = db_manager.get_session()
        try:
            updated_count = 0
            errors = []

            for asset_data in assets_data:
                asset_id = asset_data.get('id')
                changes = asset_data.get('changes', {})

                if not asset_id:
                    continue

                if not changes:
                    continue

                asset = db_session.query(Asset).get(asset_id)
                if not asset:
                    errors.append(f"Asset {asset_id} not found")
                    continue

                # Apply individual changes for this asset
                if 'name' in changes:
                    asset.name = changes['name']

                if 'asset_tag' in changes:
                    asset.asset_tag = changes['asset_tag']

                if 'serial_number' in changes:
                    asset.serial_number = changes['serial_number']

                if 'status' in changes:
                    try:
                        asset.status = AssetStatus(changes['status'])
                    except ValueError:
                        # If status value doesn't match enum, skip
                        errors.append(f"Invalid status for asset {asset_id}: {changes['status']}")

                if 'country' in changes:
                    asset.country = changes['country']

                if 'company' in changes:
                    # Update the customer field (text field used for display)
                    asset.customer = changes['company']

                    # Also update company_id if a matching company exists
                    company = db_session.query(Company).filter(
                        Company.name == changes['company']
                    ).first()
                    if company:
                        asset.company_id = company.id

                if 'asset_type' in changes:
                    asset.asset_type = changes['asset_type']

                if 'location' in changes:
                    location_name = changes['location']
                    if location_name:
                        # Find location by name
                        location = db_session.query(Location).filter(
                            Location.name == location_name
                        ).first()
                        if location:
                            asset.location_id = location.id
                        else:
                            errors.append(f"Location '{location_name}' not found for asset {asset_id}")
                    else:
                        # Empty location - clear the location_id
                        asset.location_id = None

                asset.updated_at = datetime.now()
                updated_count += 1

            db_session.commit()

            result = {
                'success': True,
                'updated_count': updated_count,
                'message': f'Successfully updated {updated_count} assets'
            }

            if errors:
                result['warnings'] = errors

            return jsonify(result)

        except Exception as e:
            db_session.rollback()
            logger.error(f"Individual bulk update error: {str(e)}")
            return jsonify({'success': False, 'error': str(e)}), 500
        finally:
            db_session.close()

    except Exception as e:
        logger.error(f"Individual bulk update API error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@inventory_bp.route('/api/asset/<int:asset_id>/image', methods=['POST'])
@login_required
def api_update_asset_image(asset_id):
    """Update asset product image URL"""
    try:
        user_id = session.get('user_id')
        user_type = session.get('user_type')

        if not user_id:
            return jsonify({'success': False, 'error': 'No user in session'}), 403

        # Only allow DEVELOPER and SUPER_ADMIN users
        if user_type not in ['DEVELOPER', 'SUPER_ADMIN']:
            return jsonify({'success': False, 'error': 'Access denied - Admin only'}), 403

        data = request.get_json()
        if data is None:
            return jsonify({'success': False, 'error': 'No JSON data provided'}), 400

        image_url = data.get('image_url', '').strip()

        db_session = db_manager.get_session()
        try:
            asset = db_session.query(Asset).get(asset_id)
            if not asset:
                return jsonify({'success': False, 'error': 'Asset not found'}), 404

            # Update the image URL
            asset.image_url = image_url if image_url else None
            db_session.commit()

            logger.info(f"Updated asset {asset_id} image_url to: {image_url[:50] if image_url else 'None'}...")

            return jsonify({
                'success': True,
                'asset_id': asset_id,
                'image_url': asset.image_url
            })

        finally:
            db_session.close()

    except Exception as e:
        logger.error(f"Error updating asset image: {e}")
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@inventory_bp.route('/api/asset/<int:asset_id>/location', methods=['POST'])
@login_required
def api_update_asset_location(asset_id):
    """Update asset location"""
    try:
        user_id = session.get('user_id')
        user_type = session.get('user_type')

        if not user_id:
            return jsonify({'success': False, 'error': 'No user in session'}), 403

        # Only allow DEVELOPER and SUPER_ADMIN users
        if user_type not in ['DEVELOPER', 'SUPER_ADMIN']:
            return jsonify({'success': False, 'error': 'Access denied - Admin only'}), 403

        data = request.get_json()
        if data is None:
            return jsonify({'success': False, 'error': 'No JSON data provided'}), 400

        location_id = data.get('location_id')

        db_session = db_manager.get_session()
        try:
            asset = db_session.query(Asset).get(asset_id)
            if not asset:
                return jsonify({'success': False, 'error': 'Asset not found'}), 404

            # Update the location
            if location_id:
                from models.location import Location
                location = db_session.query(Location).get(int(location_id))
                if not location:
                    return jsonify({'success': False, 'error': 'Location not found'}), 404
                asset.location_id = location.id
                location_name = location.name
            else:
                asset.location_id = None
                location_name = None

            db_session.commit()

            logger.info(f"Updated asset {asset_id} location_id to: {location_id}")

            return jsonify({
                'success': True,
                'asset_id': asset_id,
                'location_id': asset.location_id,
                'location_name': location_name
            })

        finally:
            db_session.close()

    except Exception as e:
        logger.error(f"Error updating asset location: {e}")
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@inventory_bp.route('/api/asset/<int:asset_id>/update', methods=['POST'])
@login_required
def api_update_asset(asset_id):
    """Update asset details via inline edit"""
    try:
        user_id = session.get('user_id')
        user_type = session.get('user_type')

        if not user_id:
            return jsonify({'success': False, 'error': 'No user in session'}), 403

        # Only allow DEVELOPER and SUPER_ADMIN users
        if user_type not in ['DEVELOPER', 'SUPER_ADMIN']:
            return jsonify({'success': False, 'error': 'Access denied - Admin only'}), 403

        data = request.get_json()
        if data is None:
            return jsonify({'success': False, 'error': 'No JSON data provided'}), 400

        db_session = db_manager.get_session()
        try:
            asset = db_session.query(Asset).get(asset_id)
            if not asset:
                return jsonify({'success': False, 'error': 'Asset not found'}), 404

            # List of updatable fields
            updatable_fields = [
                'asset_tag', 'serial_num', 'name', 'model', 'manufacturer',
                'asset_type', 'condition', 'customer', 'country', 'inventory',
                'cpu_type', 'cpu_cores', 'memory', 'harddrive', 'gpu_cores',
                'keyboard', 'charger', 'diag', 'notes', 'tech_notes',
                'cost_price', 'po', 'erased'
            ]

            # Update each field if present in data
            for field in updatable_fields:
                if field in data:
                    value = data[field]
                    # Handle empty strings as None
                    if value == '' or value == 'null':
                        value = None
                    # Handle numeric fields
                    if field == 'cost_price' and value is not None:
                        try:
                            value = float(value)
                        except (ValueError, TypeError):
                            value = None
                    setattr(asset, field, value)

            # Handle status separately (it's an enum)
            if 'status' in data and data['status']:
                try:
                    from models.asset import AssetStatus
                    asset.status = AssetStatus[data['status']]
                except (KeyError, ValueError):
                    pass  # Invalid status, ignore

            # Handle location_id separately
            if 'location_id' in data:
                loc_id = data['location_id']
                if loc_id and loc_id != '':
                    try:
                        asset.location_id = int(loc_id)
                    except (ValueError, TypeError):
                        pass
                else:
                    asset.location_id = None

            # Handle receiving_date separately
            if 'receiving_date' in data:
                date_str = data['receiving_date']
                if date_str and date_str != '':
                    try:
                        from datetime import datetime
                        asset.receiving_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                    except (ValueError, TypeError):
                        pass
                else:
                    asset.receiving_date = None

            db_session.commit()

            logger.info(f"Updated asset {asset_id} via inline edit by user {user_id}")

            return jsonify({
                'success': True,
                'asset_id': asset_id
            })

        finally:
            db_session.close()

    except Exception as e:
        logger.error(f"Error updating asset: {e}")
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@inventory_bp.route('/api/locations', methods=['POST'])
@login_required
def api_create_location():
    """Create a new location"""
    try:
        user_id = session.get('user_id')
        user_type = session.get('user_type')

        if not user_id:
            return jsonify({'success': False, 'error': 'No user in session'}), 403

        # Allow DEVELOPER, SUPER_ADMIN, and ADMIN users
        if user_type not in ['DEVELOPER', 'SUPER_ADMIN', 'ADMIN']:
            return jsonify({'success': False, 'error': 'Access denied - Admin only'}), 403

        data = request.get_json()
        if data is None:
            return jsonify({'success': False, 'error': 'No JSON data provided'}), 400

        name = data.get('name', '').strip()
        country = data.get('country', '').strip() if data.get('country') else None
        address = data.get('address', '').strip() if data.get('address') else None

        if not name:
            return jsonify({'success': False, 'error': 'Location name is required'}), 400

        db_session = db_manager.get_session()
        try:
            from models.location import Location

            # Check if location with same name already exists
            existing = db_session.query(Location).filter_by(name=name).first()
            if existing:
                return jsonify({'success': False, 'error': 'Location with this name already exists'}), 400

            # Create new location
            location = Location(name=name, country=country, address=address)
            db_session.add(location)
            db_session.commit()

            logger.info(f"Created new location: {name} (ID: {location.id})")

            return jsonify({
                'success': True,
                'location_id': location.id,
                'name': location.name,
                'country': location.country
            })

        finally:
            db_session.close()

    except Exception as e:
        logger.error(f"Error creating location: {e}")
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@inventory_bp.route('/sf/asset/<int:asset_id>')
@login_required
def view_asset_sf(asset_id):
    """Salesforce-style asset detail view - Admin and Supervisor"""
    user_type = session.get('user_type')

    # Allow DEVELOPER, SUPER_ADMIN, SUPERVISOR, and COUNTRY_ADMIN users
    if user_type not in ['DEVELOPER', 'SUPER_ADMIN', 'SUPERVISOR', 'COUNTRY_ADMIN']:
        flash('This view is only available for authorized users.', 'error')
        return redirect(url_for('inventory.view_asset', asset_id=asset_id))

    db_session = db_manager.get_session()
    try:
        user = db_manager.get_user(session['user_id'])

        # Get the asset with related data
        asset = db_session.query(Asset).get(asset_id)
        if not asset:
            flash('Asset not found', 'error')
            return redirect(url_for('inventory.view_inventory_sf'))

        # Check permission for SUPERVISOR and COUNTRY_ADMIN to view this specific asset
        if user_type in ['SUPERVISOR', 'COUNTRY_ADMIN']:
            from models.user_company_permission import UserCompanyPermission
            has_permission = False

            # Check country permission
            country_ok = True
            if user.assigned_countries and asset.country:
                country_ok = asset.country in user.assigned_countries

            # Check company permission
            company_permissions = db_session.query(UserCompanyPermission).filter_by(
                user_id=user.id,
                can_view=True
            ).all()

            if company_permissions:
                permitted_company_ids = [perm.company_id for perm in company_permissions]
                permitted_companies = db_session.query(Company).filter(Company.id.in_(permitted_company_ids)).all()

                # Include child company IDs and names
                all_company_ids = list(permitted_company_ids)
                all_company_names = [c.name.strip().lower() for c in permitted_companies]

                for company in permitted_companies:
                    if company.is_parent_company or company.child_companies.count() > 0:
                        child_companies = company.child_companies.all()
                        all_company_ids.extend([c.id for c in child_companies])
                        all_company_names.extend([c.name.strip().lower() for c in child_companies])

                # Check if asset's company_id is in permitted list or customer name matches
                company_ok = asset.company_id in all_company_ids
                if not company_ok and asset.customer:
                    # Check by customer name
                    customer_lower = asset.customer.lower()
                    company_ok = any(name in customer_lower for name in all_company_names)

                has_permission = country_ok and company_ok
            else:
                # No company permissions - deny access
                has_permission = False

            if not has_permission:
                flash('You do not have permission to view this asset.', 'error')
                return redirect(url_for('inventory.view_inventory_sf'))

        # Get related tickets/cases - include tickets linked by relationship AND by serial number
        from models.ticket import Ticket
        related_tickets_set = set()

        # Add tickets from relationship
        if asset.tickets:
            for t in asset.tickets:
                related_tickets_set.add(t.id)

        # Also find tickets by serial number
        if asset.serial_num:
            serial_tickets = db_session.query(Ticket).filter(
                Ticket.serial_number == asset.serial_num
            ).all()
            for t in serial_tickets:
                related_tickets_set.add(t.id)

        # Also find tickets by asset_id
        asset_id_tickets = db_session.query(Ticket).filter(
            Ticket.asset_id == asset.id
        ).all()
        for t in asset_id_tickets:
            related_tickets_set.add(t.id)

        # Get full ticket objects, sorted by created_at desc
        if related_tickets_set:
            related_tickets = db_session.query(Ticket).filter(
                Ticket.id.in_(related_tickets_set)
            ).order_by(Ticket.created_at.desc()).all()
        else:
            related_tickets = []

        # Get asset history
        asset_history = asset.history[:10] if asset.history else []  # Last 10 entries

        # Get asset transactions
        asset_transactions = asset.transactions[:10] if asset.transactions else []

        # Get all locations for dropdown
        from models.location import Location
        locations = db_session.query(Location).order_by(Location.name).all()

        # Build filtered asset query for dropdowns based on user permissions
        dropdown_query = db_session.query(Asset)

        if user_type in ['SUPERVISOR', 'COUNTRY_ADMIN']:
            from models.user_company_permission import UserCompanyPermission

            # Filter by assigned countries
            if user.assigned_countries:
                dropdown_query = dropdown_query.filter(Asset.country.in_(user.assigned_countries))

            # Filter by company permissions
            company_permissions = db_session.query(UserCompanyPermission).filter_by(
                user_id=user.id,
                can_view=True
            ).all()

            if company_permissions:
                permitted_company_ids = [perm.company_id for perm in company_permissions]
                permitted_companies = db_session.query(Company).filter(Company.id.in_(permitted_company_ids)).all()

                # Include child company IDs
                all_company_ids = list(permitted_company_ids)
                all_company_names = [c.name.strip() for c in permitted_companies]

                for company in permitted_companies:
                    if company.is_parent_company or company.child_companies.count() > 0:
                        child_companies = company.child_companies.all()
                        all_company_ids.extend([c.id for c in child_companies])
                        all_company_names.extend([c.name.strip() for c in child_companies])

                # Filter by company_id or customer name
                name_conditions = [func.lower(Asset.customer).like(f"%{name.lower()}%") for name in all_company_names]
                dropdown_query = dropdown_query.filter(
                    or_(
                        Asset.company_id.in_(all_company_ids),
                        *name_conditions
                    )
                )

        # Get filtered asset IDs for dropdown queries
        from sqlalchemy import select
        filtered_ids_subq = dropdown_query.with_entities(Asset.id).subquery()
        filtered_ids = select(filtered_ids_subq.c.id)

        # Get unique values for edit dropdowns from filtered assets
        models = db_session.query(Asset.model).distinct().filter(Asset.id.in_(filtered_ids), Asset.model.isnot(None)).all()
        models = sorted([m[0] for m in models if m[0]])

        chargers = db_session.query(Asset.charger).distinct().filter(Asset.id.in_(filtered_ids), Asset.charger.isnot(None)).all()
        chargers = sorted([c[0] for c in chargers if c[0]])

        customers = db_session.query(Asset.customer).distinct().filter(Asset.id.in_(filtered_ids), Asset.customer.isnot(None)).all()
        customers = sorted([c[0] for c in customers if c[0]])

        countries = db_session.query(Asset.country).distinct().filter(Asset.id.in_(filtered_ids), Asset.country.isnot(None)).all()
        countries = sorted([c[0] for c in countries if c[0]])

        asset_types = db_session.query(Asset.asset_type).distinct().filter(Asset.id.in_(filtered_ids), Asset.asset_type.isnot(None)).all()
        asset_types = sorted([t[0] for t in asset_types if t[0]])

        conditions = db_session.query(Asset.condition).distinct().filter(Asset.id.in_(filtered_ids), Asset.condition.isnot(None)).all()
        conditions = sorted([c[0] for c in conditions if c[0]])

        diags = db_session.query(Asset.diag).distinct().filter(Asset.id.in_(filtered_ids), Asset.diag.isnot(None)).all()
        diags = sorted([d[0] for d in diags if d[0]])

        keyboards = db_session.query(Asset.keyboard).distinct().filter(Asset.id.in_(filtered_ids), Asset.keyboard.isnot(None)).all()
        keyboards = sorted([k[0] for k in keyboards if k[0]])

        from models.asset import AssetStatus

        return render_template('inventory/view_asset_sf.html',
                             asset=asset,
                             user=user,
                             related_tickets=related_tickets,
                             asset_history=asset_history,
                             asset_transactions=asset_transactions,
                             locations=locations,
                             models=models,
                             chargers=chargers,
                             customers=customers,
                             countries=countries,
                             asset_types=asset_types,
                             conditions=conditions,
                             diags=diags,
                             keyboards=keyboards,
                             statuses=AssetStatus)
    finally:
        db_session.close()


@inventory_bp.route('/sf/accessory/<int:accessory_id>')
@login_required
def view_accessory_sf(accessory_id):
    """Salesforce-style accessory detail view - Admin and Supervisor"""
    user_type = session.get('user_type')

    # Allow DEVELOPER, SUPER_ADMIN, SUPERVISOR, and COUNTRY_ADMIN users
    if user_type not in ['DEVELOPER', 'SUPER_ADMIN', 'SUPERVISOR', 'COUNTRY_ADMIN']:
        flash('This view is only available for authorized users.', 'error')
        return redirect(url_for('inventory.view_accessory', id=accessory_id))

    db_session = db_manager.get_session()
    try:
        user = db_manager.get_user(session['user_id'])

        # Get the accessory with related data
        accessory = db_session.query(Accessory).get(accessory_id)
        if not accessory:
            flash('Accessory not found', 'error')
            return redirect(url_for('inventory.view_inventory_sf'))

        # Check permission for SUPERVISOR and COUNTRY_ADMIN to view this specific accessory
        if user_type in ['SUPERVISOR', 'COUNTRY_ADMIN']:
            from models.user_company_permission import UserCompanyPermission
            has_permission = False

            # Check country permission
            country_ok = True
            if user.assigned_countries and accessory.country:
                country_ok = accessory.country in user.assigned_countries

            # Check company permission
            company_permissions = db_session.query(UserCompanyPermission).filter_by(
                user_id=user.id,
                can_view=True
            ).all()

            if company_permissions:
                permitted_company_ids = [perm.company_id for perm in company_permissions]
                permitted_companies = db_session.query(Company).filter(Company.id.in_(permitted_company_ids)).all()

                # Include child company IDs
                all_company_ids = list(permitted_company_ids)
                for company in permitted_companies:
                    if company.is_parent_company or company.child_companies.count() > 0:
                        child_companies = company.child_companies.all()
                        all_company_ids.extend([c.id for c in child_companies])

                # Check if accessory's company is in permitted list (or has no company)
                company_ok = accessory.company_id is None or accessory.company_id in all_company_ids
                has_permission = country_ok and company_ok
            else:
                # No company permissions - only allow if accessory has no company
                has_permission = country_ok and accessory.company_id is None

            if not has_permission:
                flash('You do not have permission to view this accessory.', 'error')
                return redirect(url_for('inventory.view_inventory_sf'))

        # Get related tickets/cases
        related_tickets = list(accessory.tickets) if accessory.tickets else []

        # Get accessory history
        accessory_history = accessory.history[:10] if accessory.history else []  # Last 10 entries

        # Get accessory transactions
        accessory_transactions = accessory.transactions[:10] if accessory.transactions else []

        # Get customer info
        customer = accessory.customer_user if accessory.customer_id else None

        # Build filtered accessory query for SUPERVISOR and COUNTRY_ADMIN
        base_accessory_query = db_session.query(Accessory)

        if user_type in ['SUPERVISOR', 'COUNTRY_ADMIN']:
            from models.user_company_permission import UserCompanyPermission

            # Filter by assigned countries
            if user.assigned_countries:
                base_accessory_query = base_accessory_query.filter(Accessory.country.in_(user.assigned_countries))

            # Filter by company permissions
            company_permissions = db_session.query(UserCompanyPermission).filter_by(
                user_id=user.id,
                can_view=True
            ).all()

            if company_permissions:
                permitted_company_ids = [perm.company_id for perm in company_permissions]
                permitted_companies = db_session.query(Company).filter(Company.id.in_(permitted_company_ids)).all()

                # Include child company IDs
                all_company_ids = list(permitted_company_ids)

                for company in permitted_companies:
                    if company.is_parent_company or company.child_companies.count() > 0:
                        child_companies = company.child_companies.all()
                        all_company_ids.extend([c.id for c in child_companies])

                # Filter by company_id
                base_accessory_query = base_accessory_query.filter(
                    or_(
                        Accessory.company_id.in_(all_company_ids),
                        Accessory.company_id.is_(None)
                    )
                )

        # Get prev/next accessories for navigation (filtered)
        prev_accessory = base_accessory_query.filter(Accessory.id < accessory_id).order_by(Accessory.id.desc()).first()
        next_accessory = base_accessory_query.filter(Accessory.id > accessory_id).order_by(Accessory.id.asc()).first()

        # Get all accessories for sidebar (same category first, then others) - filtered
        same_category = base_accessory_query.filter(
            Accessory.category == accessory.category,
            Accessory.id != accessory_id
        ).order_by(Accessory.name).all()

        other_accessories = base_accessory_query.filter(
            Accessory.category != accessory.category,
            Accessory.id != accessory_id
        ).order_by(Accessory.name).all()

        sidebar_accessories = same_category + other_accessories

        return render_template('inventory/view_accessory_sf.html',
                             accessory=accessory,
                             user=user,
                             customer=customer,
                             related_tickets=related_tickets,
                             accessory_history=accessory_history,
                             accessory_transactions=accessory_transactions,
                             prev_accessory=prev_accessory,
                             next_accessory=next_accessory,
                             sidebar_accessories=sidebar_accessories)
    finally:
        db_session.close()


@inventory_bp.route('/api/sf/accessory/<int:accessory_id>/image', methods=['POST'])
@login_required
def update_accessory_image(accessory_id):
    """Update accessory image URL - Admin only"""
    user_type = session.get('user_type')

    if user_type not in ['DEVELOPER', 'SUPER_ADMIN']:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403

    db_session = db_manager.get_session()
    try:
        data = request.get_json()
        image_url = data.get('image_url', '').strip()

        accessory = db_session.query(Accessory).get(accessory_id)
        if not accessory:
            return jsonify({'success': False, 'error': 'Accessory not found'}), 404

        accessory.image_url = image_url if image_url else None
        db_session.commit()

        return jsonify({'success': True, 'image_url': accessory.image_url})
    except Exception as e:
        db_session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db_session.close()


@inventory_bp.route('/api/sf/accessory/search-image')
@login_required
def search_accessory_image():
    """Search for product images using Unsplash API - Admin only"""
    user_type = session.get('user_type')

    if user_type not in ['DEVELOPER', 'SUPER_ADMIN']:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403

    query = request.args.get('q', '')
    if not query:
        return jsonify({'success': False, 'error': 'Query required'}), 400

    # Return placeholder URLs based on category
    # These are free-to-use placeholder images
    placeholder_urls = {
        'keyboard': 'https://images.unsplash.com/photo-1587829741301-dc798b83add3?w=400&h=400&fit=crop',
        'mouse': 'https://images.unsplash.com/photo-1527864550417-7fd91fc51a46?w=400&h=400&fit=crop',
        'monitor': 'https://images.unsplash.com/photo-1527443224154-c4a3942d3acf?w=400&h=400&fit=crop',
        'headset': 'https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=400&h=400&fit=crop',
        'headphone': 'https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=400&h=400&fit=crop',
        'cable': 'https://images.unsplash.com/photo-1558618666-fcd25c85cd64?w=400&h=400&fit=crop',
        'charger': 'https://images.unsplash.com/photo-1583863788434-e62bd23c3da2?w=400&h=400&fit=crop',
        'adapter': 'https://images.unsplash.com/photo-1625772452859-1c03d5bf1137?w=400&h=400&fit=crop',
        'docking': 'https://images.unsplash.com/photo-1593062096033-9a26b09da705?w=400&h=400&fit=crop',
        'audio': 'https://images.unsplash.com/photo-1545454675-3531b543be5d?w=400&h=400&fit=crop',
    }

    # Find matching placeholder
    query_lower = query.lower()
    suggested_url = None
    for key, url in placeholder_urls.items():
        if key in query_lower:
            suggested_url = url
            break

    return jsonify({
        'success': True,
        'query': query,
        'suggested_url': suggested_url,
        'placeholder_urls': placeholder_urls
    })


@inventory_bp.route('/tech-assets')
@login_required
def view_tech_assets():
    db_session = db_manager.get_session()
    try:
        # Get the current user
        user = db_manager.get_user(session['user_id'])

        # Get pagination parameters
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)  # Default 50 items per page
        per_page = min(per_page, 200)  # Max 200 items per page

        # Base query for assets
        assets_query = db_session.query(Asset)

        # Apply filtering for COUNTRY_ADMIN and SUPERVISOR users
        if user.user_type == UserType.COUNTRY_ADMIN or user.user_type == UserType.SUPERVISOR:
            from models.user_company_permission import UserCompanyPermission

            # Filter by country if assigned
            if user.assigned_countries:
                assets_query = assets_query.filter(Asset.country.in_(user.assigned_countries))

            # ALWAYS filter by company permissions
            company_permissions = db_session.query(UserCompanyPermission).filter_by(
                user_id=user.id,
                can_view=True
            ).all()

            if company_permissions:
                permitted_company_ids = [perm.company_id for perm in company_permissions]
                permitted_companies = db_session.query(Company).filter(Company.id.in_(permitted_company_ids)).all()
                permitted_company_names = [c.name.strip() for c in permitted_companies]

                # Include child companies of parent companies (both names AND IDs)
                all_company_names = list(permitted_company_names)
                all_company_ids = list(permitted_company_ids)
                for company in permitted_companies:
                    if company.is_parent_company or company.child_companies.count() > 0:
                        child_companies = company.child_companies.all()
                        child_names = [c.name.strip() for c in child_companies]
                        child_ids = [c.id for c in child_companies]
                        all_company_names.extend(child_names)
                        all_company_ids.extend(child_ids)

                # Filter by company_id OR customer name
                name_conditions = [func.lower(Asset.customer).like(f"%{name.lower()}%") for name in all_company_names]
                assets_query = assets_query.filter(
                    or_(
                        Asset.company_id.in_(all_company_ids),
                        *name_conditions
                    )
                )
            else:
                # No company permissions - show NO assets
                assets_query = assets_query.filter(Asset.id == -1)

        # Filter by company if user is a client (can only see their company's assets)
        elif user.user_type == UserType.CLIENT and user.company:
            # Filter by company_id and also by customer field matching company name
            assets_query = assets_query.filter(
                or_(
                    Asset.company_id == user.company_id,
                    Asset.customer == user.company.name
                )
            )

        # Get total count before pagination
        total_count = assets_query.count()

        # Apply pagination
        offset = (page - 1) * per_page
        assets = assets_query.offset(offset).limit(per_page).all()
        
        # Calculate pagination info
        total_pages = (total_count + per_page - 1) // per_page
        has_next = page < total_pages
        has_prev = page > 1

        # Format response
        return jsonify({
            'total_count': total_count,
            'page': page,
            'per_page': per_page,
            'total_pages': total_pages,
            'has_next': has_next,
            'has_prev': has_prev,
            'assets': [
                {
                    'id': asset.id,
                    'name': asset.name or f"{asset.hardware_type} {asset.model}" if asset.hardware_type else asset.model,
                    'product': f"{asset.hardware_type} {asset.model}" if asset.hardware_type else asset.model,
                    'asset_tag': asset.asset_tag,
                    'serial_num': asset.serial_num,
                    'model': asset.model,
                    'inventory': asset.status.value if asset.status else 'Unknown',
                    'customer': get_customer_display_name(db_session, asset.customer),
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
        from models.user_company_permission import UserCompanyPermission

        # Get the current user
        user = db_manager.get_user(session['user_id'])

        # Base query for accessories
        accessories_query = db_session.query(Accessory)

        # Filter by company for non-SUPER_ADMIN/DEVELOPER users
        permitted_company_ids = []
        if user.user_type in [UserType.COUNTRY_ADMIN, UserType.SUPERVISOR]:
            # Get the companies this user has permission to view
            user_company_permissions = db_session.query(UserCompanyPermission).filter_by(
                user_id=user.id,
                can_view=True
            ).all()

            if user_company_permissions:
                permitted_company_ids = [perm.company_id for perm in user_company_permissions]

                # Also include child companies of any parent company the user has permission to
                permitted_companies = db_session.query(Company).filter(Company.id.in_(permitted_company_ids)).all()
                all_permitted_ids = list(permitted_company_ids)

                for company in permitted_companies:
                    if company.is_parent_company or company.child_companies.count() > 0:
                        child_ids = [c.id for c in company.child_companies.all()]
                        all_permitted_ids.extend(child_ids)

                permitted_company_ids = list(set(all_permitted_ids))

                # Filter accessories by company_id
                # Include accessories with NULL company_id OR matching company_id
                from sqlalchemy import or_
                accessories_query = accessories_query.filter(
                    or_(
                        Accessory.company_id.in_(permitted_company_ids),
                        Accessory.company_id.is_(None)
                    )
                )
                logger.info(f"Filtering accessories by company IDs: {permitted_company_ids}")

        # Execute query and get accessories
        accessories = accessories_query.all()

        # Log for debugging
        logger.info(f"User type: {user.user_type}, Accessories returned: {len(accessories)}")

        # Get customers for checkout (filtered by company for non-SUPER_ADMIN users)
        customers = get_filtered_customers(db_session, user)

        # Get companies for bulk assignment (filtered for non-admin users)
        if user.user_type in [UserType.SUPER_ADMIN, UserType.DEVELOPER]:
            companies = db_session.query(Company).order_by(Company.name).all()
        elif permitted_company_ids:
            companies = db_session.query(Company).filter(Company.id.in_(permitted_company_ids)).order_by(Company.name).all()
        else:
            companies = []

        # Render the template with appropriate context
        return render_template('inventory/accessories.html',
                             accessories=accessories,
                             customers=customers,
                             companies=companies,
                             is_admin=user.is_admin,
                             is_country_admin=user.is_country_admin,
                             is_supervisor=user.user_type == UserType.SUPERVISOR,
                             user=user)
    finally:
        db_session.close()

@inventory_bp.route('/api/accessories/bulk-update-company', methods=['POST'])
@login_required
def bulk_update_accessory_company():
    """Bulk update company for multiple accessories"""
    try:
        user_id = session.get('user_id')
        user_type = session.get('user_type')

        if not user_id:
            return jsonify({'success': False, 'error': 'No user in session'}), 403

        # Only allow DEVELOPER and SUPER_ADMIN users
        if user_type not in ['DEVELOPER', 'SUPER_ADMIN']:
            return jsonify({'success': False, 'error': 'Access denied - Admin only'}), 403

        data = request.get_json()
        if data is None:
            return jsonify({'success': False, 'error': 'No JSON data provided'}), 400

        accessory_ids = data.get('accessory_ids', [])
        company_id = data.get('company_id')

        if not accessory_ids:
            return jsonify({'success': False, 'error': 'No accessories selected'}), 400

        db_session = db_manager.get_session()
        try:
            # Verify company exists if provided
            company = None
            if company_id:
                company = db_session.query(Company).get(company_id)
                if not company:
                    return jsonify({'success': False, 'error': 'Company not found'}), 400

            updated_count = 0
            for accessory_id in accessory_ids:
                accessory = db_session.query(Accessory).get(accessory_id)
                if not accessory:
                    continue

                old_company_id = accessory.company_id
                accessory.company_id = company_id if company_id else None
                accessory.updated_at = datetime.now()

                # Track change in history
                if old_company_id != accessory.company_id:
                    old_company_name = None
                    if old_company_id:
                        old_company = db_session.query(Company).get(old_company_id)
                        old_company_name = old_company.name if old_company else None

                    history_entry = accessory.track_change(
                        user_id=user_id,
                        action='bulk_company_update',
                        changes={
                            'company': {
                                'old': old_company_name,
                                'new': company.name if company else None
                            }
                        }
                    )
                    db_session.add(history_entry)

                updated_count += 1

            db_session.commit()

            return jsonify({
                'success': True,
                'updated_count': updated_count,
                'message': f'Successfully updated {updated_count} accessories'
            })

        except Exception as e:
            db_session.rollback()
            logger.error(f"Bulk accessory company update error: {str(e)}")
            return jsonify({'success': False, 'error': str(e)}), 500
        finally:
            db_session.close()

    except Exception as e:
        logger.error(f"Bulk accessory company update API error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

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
        
        # CLIENT user permissions check - can only see their company's assets
        if user.user_type == UserType.CLIENT and user.company:
            # Filter by company_id and also by customer field matching company name
            query = query.filter(
                or_(
                    Asset.company_id == user.company_id,
                    Asset.customer == user.company.name
                )
            )
            logger.info("DEBUG: Filtering search results for client user. Company ID: {user.company_id}, Company Name: {user.company.name}")
        
        # Country filter for Country Admin or Supervisor
        if (user.user_type == UserType.COUNTRY_ADMIN or user.user_type == UserType.SUPERVISOR) and user.assigned_countries:
            query = query.filter(Asset.country.in_(user.assigned_countries))
        
        # Apply filters from request
        if 'country' in data and data['country']:
            # Use case-insensitive comparison for country filter
            query = query.filter(func.lower(Asset.country) == func.lower(data['country']))
        
        if 'status' in data and data['status'] or 'inventory_status' in data and data['inventory_status']:
            status_value = data.get('status') or data.get('inventory_status')
            # Convert status value to enum for comparison
            try:
                # Try to match by enum value (case-insensitive)
                for status_enum in AssetStatus:
                    if status_enum.value.lower() == status_value.lower():
                        query = query.filter(Asset.status == status_enum)
                        break
            except (AttributeError, TypeError):
                pass
        
        if 'customer' in data or 'company' in data:
            company_value = data.get('customer') or data.get('company')
            # Handle empty string to filter for assets with no company ("Unknown")
            if company_value == '' or company_value == '__unknown__':
                # Filter for assets with empty/null company
                query = query.filter(or_(
                    Asset.customer.is_(None),
                    Asset.customer == '',
                    func.trim(Asset.customer) == ''
                ))
                logger.info("Filtering for assets with no company (Unknown)")
            elif company_value:
                # Check if this company is a parent company - if so, include all child companies
                company_obj = db_session.query(Company).filter(Company.name == company_value).first()
                if company_obj and (company_obj.is_parent_company or company_obj.child_companies.count() > 0):
                    # This is a parent company - include assets from all child companies
                    child_company_names = [c.name for c in company_obj.child_companies.all()]
                    all_company_names = [company_value] + child_company_names
                    query = query.filter(Asset.customer.in_(all_company_names))
                    logger.info(f"Company grouping: filtering by parent '{company_value}' + children: {child_company_names}")
                else:
                    # Regular company or no grouping - filter by exact match
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

        # Date created filter
        if 'date_from' in data and data['date_from']:
            try:
                from datetime import datetime
                date_from = datetime.strptime(data['date_from'], '%Y-%m-%d')
                query = query.filter(Asset.created_at >= date_from)
            except (ValueError, TypeError):
                pass

        if 'date_to' in data and data['date_to']:
            try:
                from datetime import datetime, timedelta
                date_to = datetime.strptime(data['date_to'], '%Y-%m-%d')
                # Add one day to include the entire end date
                date_to_end = date_to + timedelta(days=1)
                query = query.filter(Asset.created_at < date_to_end)
            except (ValueError, TypeError):
                pass

        # Get pagination parameters
        page = data.get('page', 1)
        per_page = data.get('per_page', 50)
        per_page = min(per_page, 200)  # Max 200 items per page

        # Get total count before pagination
        total_count = query.count()

        # Apply pagination
        offset = (page - 1) * per_page
        assets = query.offset(offset).limit(per_page).all()

        # Calculate pagination info
        total_pages = (total_count + per_page - 1) // per_page
        has_next = page < total_pages
        has_prev = page > 1

        # Format response
        return jsonify({
            'total_count': total_count,
            'page': page,
            'per_page': per_page,
            'total_pages': total_pages,
            'has_next': has_next,
            'has_prev': has_prev,
            'assets': [
                {
                    'id': asset.id,
                    'product': f"{asset.hardware_type} {asset.model}" if asset.hardware_type else asset.model,
                    'asset_tag': asset.asset_tag,
                    'serial_num': asset.serial_num,
                    'model': asset.model,
                    'inventory': asset.status.value if asset.status else 'Unknown',
                    'customer': get_customer_display_name(db_session, asset.customer),
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
            
        accessory.checkout_date = singapore_now_as_utc()
        accessory.customer_id = customer_id
        accessory.customer_user = customer

        # Create transaction record
        transaction = AccessoryTransaction(
            accessory_id=id,
            customer_id=customer_id,
            transaction_date=singapore_now_as_utc(),
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
                ticket_id = request.form.get('ticket_id')  # Get ticket_id from form
                
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
                                logger.info("Failed to read CSV with encoding {encoding}: {last_error}")
                                continue

                        if df is None:
                            raise Exception(f"Failed to read CSV with any encoding. Please check the file format.")

                        # Create preview data based on import type
                        preview_data = []
                        if import_type == 'tech_assets':
                            # Create a case-insensitive column mapping
                            column_mapping = {col.lower(): col for col in df.columns}

                            for _, row in df.iterrows():
                                asset_tag = clean_value(row.get(column_mapping.get('asset tag', 'ASSET TAG'), ''))
                                serial_number = clean_value(row.get(column_mapping.get('serial number', 'SERIAL NUMBER'), ''))

                                # Check for duplicates in database
                                duplicate_warning = None
                                existing_asset = None

                                if serial_number:
                                    existing_asset = db_session.query(Asset).filter_by(serial_num=serial_number).first()
                                    if existing_asset:
                                        duplicate_warning = f"Serial number already exists (Asset Tag: {existing_asset.asset_tag})"

                                if not duplicate_warning and asset_tag:
                                    existing_asset = db_session.query(Asset).filter_by(asset_tag=asset_tag).first()
                                    if existing_asset:
                                        duplicate_warning = f"Asset tag already exists (Serial: {existing_asset.serial_num or 'N/A'})"

                                preview_row = {
                                    'Asset Type': clean_value(row.get(column_mapping.get('asset type', 'Asset Type'), '')),
                                    'Asset Tag': asset_tag,
                                    'Serial Number': serial_number,
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
                                    'Included': clean_value(row.get(column_mapping.get('included', 'INCLUDED'), '')),
                                    'duplicate_warning': duplicate_warning,
                                    'is_duplicate': duplicate_warning is not None
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

                                accessory_name = clean_value(row.get(column_mapping.get('name', 'NAME'), ''))

                                # Check for duplicate accessory name
                                duplicate_warning = None
                                if accessory_name:
                                    existing_accessory = db_session.query(Accessory).filter_by(name=accessory_name).first()
                                    if existing_accessory:
                                        duplicate_warning = f"Accessory already exists (Current quantity: {existing_accessory.available_quantity})"

                                preview_row = {
                                    'Name': accessory_name,
                                    'Category': clean_value(row.get(column_mapping.get('category', 'CATEGORY'), '')),
                                    'Manufacturer': clean_value(row.get(column_mapping.get('manufacturer', 'MANUFACTURER'), '')),
                                    'Model Number': clean_value(row.get(column_mapping.get('model no', 'MODEL NO'), '')),
                                    'Status': clean_value(row.get(column_mapping.get('status', 'Status'), 'Available')),
                                    'Total Quantity': quantity,
                                    'Country': clean_value(row.get(column_mapping.get('country', 'COUNTRY'), '')),
                                    'Notes': clean_value(row.get(column_mapping.get('notes', 'NOTES'), '')),
                                    'duplicate_warning': duplicate_warning,
                                    'is_duplicate': duplicate_warning is not None
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
                        if ticket_id:  # Store ticket_id if provided
                            session['import_ticket_id'] = ticket_id

                        return render_template('inventory/import.html',
                                            preview_data=preview_data,
                                            filename=filename,
                                            filepath=filepath,
                                            import_type=import_type,
                                            total_rows=len(preview_data))

                    except Exception as e:
                        db_session.rollback()
                        logger.info("Error processing file: {str(e)}")
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
    # Import helper functions for ImportSession tracking
    from routes.import_manager import create_import_session, update_import_session

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
    import_session_id = None  # Track import session
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

        # Create ImportSession to track this import
        try:
            file_name = session.get('filename', 'Unknown file')
            import_session_id, display_id = create_import_session(
                import_type='inventory',
                user_id=current_user.id,
                file_name=file_name,
                notes=f"Import type: {preview_data.get('import_type', 'unknown')}"
            )
            logger.info(f"Created import session {display_id} for inventory import")
        except Exception as e:
            logger.error(f"Failed to create import session: {str(e)}")
            # Continue with import even if session creation fails

        successful = 0
        failed = 0
        errors = []
        successful_imports = []  # Track successfully imported items

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
                    
                    # Link asset to ticket if ticket_id is provided (via many-to-many relationship)
                    ticket_id = session.get('import_ticket_id')
                    if ticket_id:
                        try:
                            from models.ticket import Ticket  # Import Ticket model
                            ticket = db_session.query(Ticket).get(int(ticket_id))
                            if ticket:
                                # Use many-to-many relationship, not intake_ticket_id (which is for IntakeTicket)
                                if hasattr(ticket, 'assets'):
                                    _safely_assign_asset_to_ticket(ticket, new_asset, db_session)

                                db_session.commit()
                                logger.info(f"Linked asset {new_asset.asset_tag} to ticket {ticket.id}")
                        except Exception as e:
                            logger.error(f"Error linking asset to ticket: {str(e)}")
                            # Don't fail the import if ticket linking fails

                    successful += 1
                    # Track successful import
                    successful_imports.append({
                        'row': index,
                        'type': 'asset',
                        'asset_id': new_asset.id,
                        'asset_tag': new_asset.asset_tag,
                        'serial': new_asset.serial_num,
                        'product': new_asset.name
                    })
                    print(f"[INVENTORY_DEBUG] Added asset to successful_imports, now has {len(successful_imports)} items")
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
                    # Track successful import
                    successful_imports.append({
                        'row': index,
                        'type': 'accessory',
                        'accessory_id': accessory.id,
                        'name': accessory.name,
                        'category': accessory.category,
                        'quantity': accessory.total_quantity
                    })

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
                # Parse the error to make it user-friendly
                error_str = str(e)

                # Check for duplicate serial number
                if 'UNIQUE constraint failed: assets.serial_num' in error_str:
                    serial = clean_value(row.get('Serial Number', 'Unknown'))
                    error_msg = f"Row {index}: Duplicate serial number '{serial}' - this asset already exists in the system"
                # Check for duplicate asset tag
                elif 'UNIQUE constraint failed: assets.asset_tag' in error_str:
                    tag = clean_value(row.get('Asset Tag', 'Unknown'))
                    error_msg = f"Row {index}: Duplicate asset tag '{tag}' - this tag is already in use"
                # Check for duplicate accessory name
                elif 'UNIQUE constraint failed: accessories.name' in error_str:
                    name = clean_value(row.get('Name', 'Unknown'))
                    error_msg = f"Row {index}: Duplicate accessory name '{name}' - this accessory already exists"
                # Other errors
                else:
                    # Clean up the error message by removing SQL details
                    if '[SQL:' in error_str:
                        error_str = error_str.split('[SQL:')[0].strip()
                    if '(Background on this error' in error_str:
                        error_str = error_str.split('(Background on this error')[0].strip()
                    error_msg = f"Row {index}: {error_str}"

                logger.error(f"Import error on row {index}: {str(e)}")
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

            # Update ImportSession with success
            if import_session_id:
                try:
                    # Store successful imports data (limit to first 100)
                    print(f"[INVENTORY_DEBUG] Before update: successful_imports has {len(successful_imports)} items")
                    import_data = successful_imports[:100] if successful_imports else None
                    print(f"[INVENTORY_DEBUG] import_data is: {type(import_data)}, truthy: {bool(import_data)}")
                    update_import_session(import_session_id, success_count=successful, fail_count=0,
                                         import_data=import_data, status='completed')
                except Exception as e:
                    logger.error(f"Failed to update import session: {str(e)}")

            flash(f'Successfully imported {successful} items.', 'success')
        else:
            # Create a more helpful error summary
            if successful > 0:
                error_summary = f"Partially successful: Imported {successful} items, but {failed} items failed."
            else:
                error_summary = f"Import failed for all {failed} items."

            # Add helpful suggestions based on error types
            has_duplicate_serial = any('Duplicate serial number' in e for e in errors)
            has_duplicate_tag = any('Duplicate asset tag' in e for e in errors)

            suggestions = []
            if has_duplicate_serial or has_duplicate_tag:
                suggestions.append("💡 Tip: These items already exist in the system. To update existing items, search for them in the inventory and edit them individually, or remove the duplicate rows from your CSV.")

            error_details = '<br><br>'.join(errors[:10])
            if len(errors) > 10:
                error_details += f'<br><br>... and {len(errors) - 10} more errors'

            if suggestions:
                flash(f'{error_summary}<br><br><strong>Failed Items:</strong><br>{error_details}<br><br>{" ".join(suggestions)}', 'error')
            else:
                flash(f'{error_summary}<br><br><strong>Failed Items:</strong><br>{error_details}', 'error')

            # If some items succeeded, show partial success
            if successful > 0:
                flash(f'✓ Successfully imported {successful} items', 'success')

            # Update ImportSession with partial/failure results
            if import_session_id:
                try:
                    status = 'completed' if successful > 0 else 'failed'
                    # Store successful imports data (limit to first 100)
                    import_data = successful_imports[:100] if successful_imports else None
                    update_import_session(import_session_id, success_count=successful, fail_count=failed,
                                         import_data=import_data, error_details=errors[:50], status=status)
                except Exception as e:
                    logger.error(f"Failed to update import session: {str(e)}")

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
        session.pop('import_ticket_id', None)  # Clear ticket ID
        
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
        if user.user_type == UserType.COUNTRY_ADMIN and user.assigned_countries:
            if asset.country not in user.assigned_countries:
                flash('You do not have permission to view this asset', 'error')
                return redirect(url_for('inventory.view_inventory'))
        
        # Get all customers for the deployment dropdown (filtered by company for non-SUPER_ADMIN users)
        customers = get_filtered_customers(db_session, user)
        
        # Get grouped display name for the asset company
        asset_company_display = get_customer_display_name(db_session, asset.customer)

        # Get related tickets/cases - include tickets linked by relationship AND by serial number
        from models.ticket import Ticket
        related_tickets_set = set()

        # Add tickets from relationship
        if asset.tickets:
            for t in asset.tickets:
                related_tickets_set.add(t.id)

        # Also find tickets by serial number
        if asset.serial_num:
            serial_tickets = db_session.query(Ticket).filter(
                Ticket.serial_number == asset.serial_num
            ).all()
            for t in serial_tickets:
                related_tickets_set.add(t.id)

        # Also find tickets by asset_id
        asset_id_tickets = db_session.query(Ticket).filter(
            Ticket.asset_id == asset.id
        ).all()
        for t in asset_id_tickets:
            related_tickets_set.add(t.id)

        # Get full ticket objects, sorted by created_at desc
        if related_tickets_set:
            related_tickets = db_session.query(Ticket).filter(
                Ticket.id.in_(related_tickets_set)
            ).order_by(Ticket.created_at.desc()).all()
        else:
            related_tickets = []

        return render_template('inventory/asset_details.html',
                             asset=asset,
                             customers=customers,
                             user=user,
                             asset_company_display=asset_company_display,
                             related_tickets=related_tickets)
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

        # Try to get JSON data, but don't fail if it's not JSON
        data = request.get_json(silent=True)

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
        
        # Store old values for change tracking
        old_values = {
            'status': original_status.value if original_status else None,
            'customer_id': original_customer_id
        }
        
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
        for field in old_values:
            new_value = getattr(asset, field)
            if isinstance(new_value, AssetStatus):
                new_value = new_value.value
            
            # Only record changes where values are actually different
            # and avoid tracking None → None changes
            if old_values[field] != new_value and not (old_values[field] is None and new_value is None):
                changes[field] = {
                    'old': old_values[field],
                    'new': new_value
                }
        
        logger.info("Changes detected: {changes}")  # Debug log
        
        if changes:
            history_entry = asset.track_change(
                user_id=current_user.id,
                action='update',
                changes=changes,
                notes=f"Asset updated by {current_user.username}"
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
    db_session = db_manager.get_session()
    try:
        if request.method == 'POST':
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
            db_session.flush()  # Flush to get the accessory ID

            # Handle aliases
            from models.accessory_alias import AccessoryAlias
            aliases_str = request.form.get('aliases', '').strip()
            if aliases_str:
                alias_names = [alias.strip() for alias in aliases_str.split(',') if alias.strip()]
                for alias_name in alias_names:
                    new_alias = AccessoryAlias(
                        accessory_id=new_accessory.id,
                        alias_name=alias_name
                    )
                    db_session.add(new_alias)

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

        # GET request - render the form with out of stock accessories
        out_of_stock_accessories = db_session.query(Accessory).filter(
            Accessory.available_quantity <= 0
        ).order_by(Accessory.name).all()

        return render_template('inventory/add_accessory.html',
                               out_of_stock_accessories=out_of_stock_accessories)

    except Exception as e:
        db_session.rollback()
        flash(f'Error: {str(e)}', 'error')
        return redirect(url_for('inventory.view_accessories'))
    finally:
        db_session.close()

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

                # Handle aliases - get comma-separated string and split into individual aliases
                from models.accessory_alias import AccessoryAlias
                aliases_str = request.form.get('aliases', '').strip()
                if aliases_str:
                    new_aliases = [alias.strip() for alias in aliases_str.split(',') if alias.strip()]
                else:
                    new_aliases = []

                # Get current aliases
                current_aliases = [alias.alias_name for alias in accessory.aliases]

                # Remove aliases that are no longer in the list
                for alias in accessory.aliases[:]:  # Use slice to avoid modifying list while iterating
                    if alias.alias_name not in new_aliases:
                        db_session.delete(alias)

                # Add new aliases that don't exist yet
                for alias_name in new_aliases:
                    if alias_name not in current_aliases:
                        new_alias = AccessoryAlias(
                            accessory_id=accessory.id,
                            alias_name=alias_name
                        )
                        db_session.add(new_alias)

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


@inventory_bp.route('/api/generate-asset-tag', methods=['GET'])
@login_required
def generate_asset_tag():
    """Generate the next available asset tag in format SG-R###"""
    db_session = db_manager.get_session()
    try:
        import re

        # Get all existing asset tags matching the pattern SG-R###
        existing_tags = db_session.query(Asset.asset_tag).filter(
            Asset.asset_tag.ilike('SG-R%')
        ).all()

        # Extract numbers from existing tags
        max_number = 0
        pattern = re.compile(r'^SG-R(\d+)$', re.IGNORECASE)

        for (tag,) in existing_tags:
            if tag:
                match = pattern.match(tag.strip())
                if match:
                    num = int(match.group(1))
                    if num > max_number:
                        max_number = num

        # Generate next tag
        next_number = max_number + 1
        next_tag = f"SG-R{next_number:03d}"

        # Double-check it doesn't exist (case-insensitive)
        while db_session.query(Asset).filter(
            func.lower(Asset.asset_tag) == next_tag.lower()
        ).first():
            next_number += 1
            next_tag = f"SG-R{next_number:03d}"

        return jsonify({
            'success': True,
            'asset_tag': next_tag,
            'next_number': next_number
        })

    except Exception as e:
        logger.error(f"Error generating asset tag: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db_session.close()


@inventory_bp.route('/assets/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_asset():
    db_session = db_manager.get_session()
    try:
        user = db_manager.get_user(session['user_id'])
        # ... (existing code to fetch unique models, chargers, etc.) ...
        
        # Get unique values for dropdown fields
        model_info = db_session.query(
            Asset.model, 
            Asset.name,
            Asset.asset_type
        ).distinct().filter(
            Asset.model.isnot(None),
            Asset.name.isnot(None) # Only get models that have a product name
        ).all()
        
        unique_chargers = db_session.query(Asset.charger).distinct().filter(Asset.charger.isnot(None)).all()
        unique_customers = db_session.query(Asset.customer).distinct().filter(Asset.customer.isnot(None)).all()
        unique_conditions = db_session.query(Asset.condition).distinct().filter(Asset.condition.isnot(None)).all()
        unique_diags = db_session.query(Asset.diag).distinct().filter(Asset.diag.isnot(None)).all()
        unique_asset_types = db_session.query(Asset.asset_type).distinct().filter(Asset.asset_type.isnot(None)).all()
        
        if user.user_type == UserType.COUNTRY_ADMIN and user.assigned_countries:
            unique_countries = user.assigned_countries
        else:
            unique_countries_query = db_session.query(Asset.country).distinct().filter(Asset.country.isnot(None)).all()
            # Use case-insensitive deduplication and proper capitalization
            countries_seen = set()
            unique_countries = []
            for c in sorted([c[0] for c in unique_countries_query if c[0]]):
                country_lower = c.lower()
                if country_lower not in countries_seen:
                    countries_seen.add(country_lower)
                    # Use proper case format
                    unique_countries.append(c.title())
        
        unique_models = []
        model_product_map = {}
        model_type_map = {}
        for model, product_name, asset_type in model_info:
            if model and model not in model_product_map:
                unique_models.append(model)
                model_product_map[model] = product_name
                model_type_map[model] = asset_type if asset_type else ''

        unique_chargers = sorted([c[0] for c in unique_chargers if c[0]])
        unique_customers = sorted([c[0] for c in unique_customers if c[0]])
        unique_conditions = sorted([c[0] for c in unique_conditions if c[0]])
        unique_diags = sorted([d[0] for d in unique_diags if d[0]])
        unique_asset_types = sorted([t[0] for t in unique_asset_types if t[0]])

        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

        if request.method == 'POST':
            try:
                # Debug log the form data
                logger.info("Form data received in add_asset:")
                for key, value in request.form.items():
                    logger.info(f"  {key}: '{value}'")
                
                # Check for required fields
                required_fields = {
                    'asset_tag': 'Asset Tag',
                    'serial_num': 'Serial Number',
                    'model': 'Model',
                    'asset_type': 'Asset Type',
                    'status': 'Status'
                }
                
                missing_fields = []
                empty_fields = []
                
                # First check if fields exist in request.form
                for field, display_name in required_fields.items():
                    if field not in request.form:
                        missing_fields.append(f"{display_name} (missing from form)")
                    elif not request.form.get(field, '').strip():
                        # Allow either asset_tag or serial_num to be empty, but not both
                        if (field == 'asset_tag' and request.form.get('serial_num', '').strip()) or \
                           (field == 'serial_num' and request.form.get('asset_tag', '').strip()):
                            continue
                        empty_fields.append(f"{display_name} (empty)")
                
                all_missing = missing_fields + empty_fields
                
                if all_missing:
                    error_msg = f"Missing required fields: {', '.join(all_missing)}"
                    logger.warning(f"Form validation failed: {error_msg}")
                    if is_ajax:
                        return jsonify({'success': False, 'error': error_msg, 'missing_fields': all_missing}), 400
                    else:
                        flash(error_msg, 'error')
                        return render_template('inventory/add_asset.html',
                                        statuses=AssetStatus, models=unique_models, 
                                        model_product_map=model_product_map, model_type_map=model_type_map, 
                                        chargers=unique_chargers, customers=unique_customers, 
                                        countries=unique_countries, conditions=unique_conditions, 
                                        diags=unique_diags, asset_types=unique_asset_types, user=user, 
                                        form_data=request.form)
                
                # Check for existing asset by serial number or asset tag
                serial_num = request.form.get('serial_num', '').strip()
                asset_tag = request.form.get('asset_tag', '').strip()
                
                if not serial_num and not asset_tag:
                    error_msg = "Either Serial Number or Asset Tag is required."
                    if is_ajax:
                        return jsonify({'success': False, 'error': error_msg}), 400
                    else:
                        flash(error_msg, 'error')
                        # Render template with error
                        return render_template('inventory/add_asset.html',
                                        statuses=AssetStatus, models=unique_models, 
                                        model_product_map=model_product_map, model_type_map=model_type_map, 
                                        chargers=unique_chargers, customers=unique_customers, 
                                        countries=unique_countries, conditions=unique_conditions, 
                                        diags=unique_diags, asset_types=unique_asset_types, user=user, 
                                        form_data=request.form)

                existing_asset = None
                if serial_num:
                    existing_asset = db_session.query(Asset).filter(func.lower(Asset.serial_num) == func.lower(serial_num)).first()
                if not existing_asset and asset_tag:
                    existing_asset = db_session.query(Asset).filter(func.lower(Asset.asset_tag) == func.lower(asset_tag)).first()

                if existing_asset:
                    error_msg = f"An asset with {'Serial Number ' + serial_num if serial_num and existing_asset.serial_num.lower() == serial_num.lower() else 'Asset Tag ' + asset_tag} already exists (ID: {existing_asset.id})."
                    if is_ajax:
                        return jsonify({'success': False, 'error': error_msg}), 409 # 409 Conflict
                    else:
                        flash(error_msg, 'error')
                        # Render template with error
                        return render_template('inventory/add_asset.html',
                                        statuses=AssetStatus, models=unique_models, 
                                        model_product_map=model_product_map, model_type_map=model_type_map, 
                                        chargers=unique_chargers, customers=unique_customers, 
                                        countries=unique_countries, conditions=unique_conditions, 
                                        diags=unique_diags, asset_types=unique_asset_types, user=user, 
                                        form_data=request.form)

                inventory_status_str = request.form.get('status', '').upper()
                try:
                    status = AssetStatus[inventory_status_str] if inventory_status_str else AssetStatus.IN_STOCK
                except KeyError:
                    status = AssetStatus.IN_STOCK # Default if status string is invalid

                model = request.form.get('model')
                if not model:
                    error_msg = 'Model is required'
                    if is_ajax:
                         return jsonify({'success': False, 'error': error_msg}), 400
                    else:
                        flash(error_msg, 'error')
                        return render_template('inventory/add_asset.html',
                                            statuses=AssetStatus, models=unique_models, 
                                            model_product_map=model_product_map, model_type_map=model_type_map, 
                                            chargers=unique_chargers, customers=unique_customers, 
                                            countries=unique_countries, conditions=unique_conditions, 
                                            diags=unique_diags, asset_types=unique_asset_types, user=user, 
                                            form_data=request.form)

                receiving_date_str = request.form.get('receiving_date')
                receiving_date = datetime.strptime(receiving_date_str, '%Y-%m-%d').date() if receiving_date_str else None

                new_asset = Asset(
                    asset_tag=asset_tag,
                    name=request.form.get('product', ''),
                    asset_type=request.form.get('asset_type', ''),
                    receiving_date=receiving_date,
                    keyboard=request.form.get('keyboard', ''),
                    serial_num=serial_num,
                    po=request.form.get('po', ''),
                    model=model,
                    erased='COMPLETED' if request.form.get('erased') == 'true' else None,
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
                    status=status,
                    notes=request.form.get('notes', ''), 
                    tech_notes=request.form.get('tech_notes', '') 
                )

                # Handle ticket linking (for regular Tickets via many-to-many relationship)
                # Note: intake_ticket_id is for IntakeTicket, not regular Ticket
                ticket_id_to_link = request.form.get('intake_ticket_id')
                if ticket_id_to_link:
                    try:
                        ticket_id = int(ticket_id_to_link)
                        ticket = db_session.query(Ticket).get(ticket_id)
                        if ticket:
                            # More careful approach to linking - check if already linked first
                            logger.info(f"Linking asset to ticket {ticket.id}")

                            # First add the asset
                            db_session.add(new_asset)
                            db_session.flush()  # Get the new asset ID

                            # Safely link asset to ticket via many-to-many relationship
                            _safely_assign_asset_to_ticket(ticket, new_asset, db_session)
                            
                            # Log activity
                            activity_content = f"Asset {new_asset.asset_tag or new_asset.serial_num} created and linked to ticket {ticket.display_id}."
                        else:
                            # Still create the asset, just don't link to a ticket
                            db_session.add(new_asset)
                            db_session.flush()
                            activity_content = f"Asset {new_asset.asset_tag or new_asset.serial_num} created. Ticket ID {ticket_id_to_link} not found for linking."
                            logger.warning(f"Ticket ID {ticket_id_to_link} not found for linking with new asset")
                    except ValueError:
                        # Still create the asset, just don't link to a ticket
                        db_session.add(new_asset)
                        db_session.flush()
                        activity_content = f"Asset {new_asset.asset_tag or new_asset.serial_num} created. Invalid ticket ID {ticket_id_to_link} provided."
                        logger.warning(f"Invalid ticket ID format: {ticket_id_to_link}")
                else:
                    # No ticket to link, just create the asset
                    db_session.add(new_asset)
                    db_session.flush() # Flush to get the new_asset ID
                    activity_content = f'Created new asset: {new_asset.name} (Asset Tag: {new_asset.asset_tag or new_asset.serial_num})'

                # Add activity tracking
                activity = Activity(
                    user_id=current_user.id,
                    type='asset_created',
                    content=activity_content,
                    reference_id=new_asset.id
                )
                db_session.add(activity)
                
                # Commit asset and activity
                db_session.commit()

                # Mark spec as processed if imported from MacBook Specs Collector
                from_spec_id = request.form.get('from_spec_id')
                if from_spec_id:
                    try:
                        from models.device_spec import DeviceSpec
                        spec = db_session.query(DeviceSpec).get(int(from_spec_id))
                        if spec:
                            spec.processed = True
                            spec.processed_at = datetime.utcnow()
                            spec.asset_id = new_asset.id
                            spec.notes = f"Asset created: {new_asset.asset_tag or new_asset.serial_num}"
                            db_session.commit()
                            logger.info(f"Marked spec {from_spec_id} as processed, linked to asset {new_asset.id}")
                    except Exception as e:
                        logger.error(f"Error marking spec as processed: {e}")

                # Prepare asset data for JSON response
                asset_data = {
                    'id': new_asset.id,
                    'asset_tag': new_asset.asset_tag or '-',
                    'serial_num': new_asset.serial_num or '-', # Changed from serial_number
                    'name': new_asset.name or new_asset.model or '-',
                    'status': new_asset.status.value if new_asset.status else 'Unknown'
                }

                if is_ajax:
                    return jsonify({'success': True, 'message': 'Asset added successfully!', 'asset': asset_data})
                else:
                    flash('Asset added successfully!', 'success')
                    # Check for redirect_url (from modal form)
                    redirect_url = request.form.get('redirect_url')
                    if redirect_url:
                         return redirect(redirect_url)
                    return redirect(url_for('inventory.view_inventory'))

            except Exception as e:
                db_session.rollback()
                error_msg = str(e)
                logger.error(f"Error adding asset: {error_msg}")
                
                # Log full exception for debugging
                logger.error(traceback.format_exc())
                
                # Check for specific constraint violations - order matters!
                # Check more specific constraints first before general ones
                error_lower = error_msg.lower()

                if "assets.serial_num" in error_lower:
                    error = "An asset with this serial number already exists."
                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                        return jsonify({'error': error}), 409
                    else:
                        flash(error, 'error')
                elif "assets.asset_tag" in error_lower:
                    error = "An asset with this asset tag already exists."
                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                        return jsonify({'error': error}), 409
                    else:
                        flash(error, 'error')
                else:
                    # Show the actual error message so we can diagnose the real issue
                    error = f"An error occurred while adding the asset: {error_msg}"
                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                        return jsonify({'error': error}), 500
                    else:
                        flash(error, 'error')

        # GET request - render the form
        # Check if intake_ticket_id is passed in query params for GET request
        ticket_id_from_query = request.args.get('ticket_id')

        # Check if importing from MacBook Specs Collector
        from_spec_id = request.args.get('from_spec')
        spec_data = None
        if from_spec_id:
            try:
                from models.device_spec import DeviceSpec
                from utils.mac_models import get_mac_model_name, get_mac_model_number
                spec = db_session.query(DeviceSpec).get(int(from_spec_id))
                if spec:
                    # Translate model ID to human-readable name and A-number
                    model_name_translated = get_mac_model_name(spec.model_id) if spec.model_id else spec.model_name
                    model_number = get_mac_model_number(spec.model_id) if spec.model_id else ''
                    spec_data = {
                        'id': spec.id,
                        'serial_number': spec.serial_number or '',
                        'model_id': spec.model_id or '',
                        'model_name': model_name_translated or spec.model_name or '',
                        'model_number': model_number,  # A-number (e.g., A2442)
                        'cpu': spec.cpu or '',
                        'cpu_cores': spec.cpu_cores or '',
                        'gpu': spec.gpu or '',
                        'gpu_cores': spec.gpu_cores or '',
                        'ram_gb': spec.ram_gb or '',
                        'memory_type': spec.memory_type or '',
                        'storage_gb': spec.storage_gb or '',
                        'storage_type': spec.storage_type or '',
                        'os_version': spec.os_version or '',
                        'wifi_mac': spec.wifi_mac or '',
                        # Default values for import
                        'status': 'IN_STOCK',
                        'condition': 'Used',
                        'receiving_date': datetime.now().strftime('%Y-%m-%d'),
                        'customer': '',
                        'country': '',
                    }

                    # If ticket_id is provided, get customer company and country from ticket
                    if ticket_id_from_query:
                        try:
                            ticket = db_session.query(Ticket).get(int(ticket_id_from_query))
                            if ticket and ticket.customer:
                                # Get company name (not customer name, not parent company)
                                if ticket.customer.company:
                                    spec_data['customer'] = ticket.customer.company.name or ''
                                # Get country from customer - normalize to Title Case for dropdown matching
                                if ticket.customer.country:
                                    spec_data['country'] = ticket.customer.country.title() if isinstance(ticket.customer.country, str) else str(ticket.customer.country).title()
                                elif ticket.country:
                                    spec_data['country'] = ticket.country.title() if isinstance(ticket.country, str) else str(ticket.country).title()
                        except Exception as e:
                            logger.error(f"Error loading ticket data for spec import: {e}")

                    logger.info(f"Importing spec data for asset creation: {spec.serial_number}")
            except Exception as e:
                logger.error(f"Error loading spec data: {e}")

        # Query out-of-stock accessories
        out_of_stock_accessories = db_session.query(Accessory).filter(
            Accessory.available_quantity <= 0
        ).order_by(Accessory.name).all()

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
                                user=user,
                                intake_ticket_id=ticket_id_from_query,
                                out_of_stock_accessories=out_of_stock_accessories,
                                spec_data=spec_data,
                                from_spec_id=from_spec_id)

    except Exception as e:
        # ... existing error handling ...
        flash(f'Error loading form: {str(e)}', 'error')
        logger.error(f"Error loading add_asset form: {e}", exc_info=True)
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
        
        conditions = db_session.query(Asset.condition).distinct().filter(Asset.condition.isnot(None)).all()
        conditions = sorted([c[0] for c in conditions if c[0]])
        
        diags = db_session.query(Asset.diag).distinct().filter(Asset.diag.isnot(None)).all()
        diags = sorted([d[0] for d in diags if d[0]])
        
        keyboards = db_session.query(Asset.keyboard).distinct().filter(Asset.keyboard.isnot(None)).all()
        keyboards = sorted([k[0] for k in keyboards if k[0]])

        # Get all locations for dropdown
        from models.location import Location
        locations = db_session.query(Location).order_by(Location.name).all()

        if request.method == 'POST':
            try:
                logger.info("Received POST request for asset edit")  # Debug log
                
                # Validate required fields
                required_fields = ['asset_tag', 'serial_num', 'model', 'asset_type']
                for field in required_fields:
                    value = request.form.get(field)
                    logger.info("Checking required field {field}: {value}")  # Debug log
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
                    'location_id': asset.location_id,
                    'hardware_type': asset.hardware_type,
                    'cpu_type': asset.cpu_type,
                    'cpu_cores': asset.cpu_cores,
                    'gpu_cores': asset.gpu_cores,
                    'memory': asset.memory,
                    'harddrive': asset.harddrive,
                    'po': asset.po,
                    'charger': asset.charger,
                    'erased': asset.erased,
                    'condition': asset.condition,
                    'diag': asset.diag,
                    'keyboard': asset.keyboard,
                    'notes': asset.notes,
                    'tech_notes': asset.tech_notes
                }
                
                logger.info("Old values stored")  # Debug log
                
                # Update asset with new values
                asset.asset_tag = request.form.get('asset_tag')
                asset.serial_num = request.form.get('serial_num')
                asset.name = request.form.get('product')  # form field is 'product'
                asset.model = request.form.get('model')
                asset.asset_type = request.form.get('asset_type')
                
                logger.info("Basic fields updated")  # Debug log
                
                # Handle receiving date
                receiving_date = request.form.get('receiving_date')
                if receiving_date:
                    try:
                        asset.receiving_date = datetime.strptime(receiving_date, '%Y-%m-%d')
                        logger.info("Receiving date set to: {asset.receiving_date}")  # Debug log
                    except ValueError as e:
                        logger.info("Error parsing receiving date: {str(e)}")  # Debug log
                        flash('Invalid receiving date format. Please use YYYY-MM-DD', 'error')
                        raise
                else:
                    asset.receiving_date = None
                
                # Handle status
                status = request.form.get('status')
                logger.info("Status from form: {status}")  # Debug log
                if status:
                    try:
                        status_value = status.upper().replace(' ', '_')
                        logger.info("Converted status value: {status_value}")  # Debug log
                        if not hasattr(AssetStatus, status_value):
                            logger.info("Invalid status value: {status_value}")  # Debug log
                            flash(f'Invalid status value: {status}', 'error')
                            raise ValueError(f'Invalid status value: {status}')
                        asset.status = AssetStatus[status_value]
                        logger.info("Status set to: {asset.status}")  # Debug log
                    except (KeyError, ValueError) as e:
                        logger.info("Error setting status: {str(e)}")  # Debug log
                        flash(f'Error setting status: {str(e)}', 'error')
                        raise
                
                # Update remaining fields
                asset.customer = request.form.get('customer')
                asset.country = request.form.get('country')

                # Handle location
                location_id = request.form.get('location_id')
                asset.location_id = int(location_id) if location_id else None

                asset.hardware_type = request.form.get('hardware_type')
                asset.cpu_type = request.form.get('cpu_type')
                asset.cpu_cores = request.form.get('cpu_cores')
                asset.gpu_cores = request.form.get('gpu_cores')
                asset.memory = request.form.get('memory')
                asset.harddrive = request.form.get('harddrive')
                asset.po = request.form.get('po')
                asset.charger = request.form.get('charger')
                asset.erased = request.form.get('erased')
                asset.condition = request.form.get('condition')
                asset.diag = request.form.get('diag')
                asset.keyboard = request.form.get('keyboard')
                asset.notes = request.form.get('notes')
                asset.tech_notes = request.form.get('tech_notes')
                
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
                
                logger.info("Changes detected: {changes}")  # Debug log
                
                if changes:
                    history_entry = asset.track_change(
                        user_id=current_user.id,
                        action='update',
                        changes=changes,
                        notes=f"Asset updated by {current_user.username}"
                    )
                    db_session.add(history_entry)
                
                db_session.commit()
                logger.info("Changes committed to database")  # Debug log
                flash('Asset updated successfully', 'success')
                return redirect(url_for('inventory.view_asset', asset_id=asset.id))
                
            except Exception as e:
                db_session.rollback()
                logger.info("Error in edit_asset: {str(e)}")  # Debug log
                flash(f'Error updating asset: {str(e)}', 'error')
                return render_template('inventory/edit_asset.html',
                                     asset=asset,
                                     models=models,
                                     chargers=chargers,
                                     customers=customers,
                                     countries=countries,
                                     locations=locations,
                                     asset_types=asset_types,
                                     conditions=conditions,
                                     diags=diags,
                                     keyboards=keyboards,
                                     statuses=AssetStatus)

        return render_template('inventory/edit_asset.html',
                             asset=asset,
                             models=models,
                             chargers=chargers,
                             customers=customers,
                             countries=countries,
                             locations=locations,
                             asset_types=asset_types,
                             conditions=conditions,
                             diags=diags,
                             keyboards=keyboards,
                             statuses=AssetStatus)
                             
    except Exception as e:
        db_session.rollback()
        logger.info("Error in edit_asset outer block: {str(e)}")  # Debug log
        flash(f'Error updating asset: {str(e)}', 'error')
        return redirect(url_for('inventory.view_asset', asset_id=asset_id))
    finally:
        db_session.close()

@inventory_bp.route('/asset/<int:asset_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_asset(asset_id):
    db_session = db_manager.get_session()
    # Get redirect destination (sf or classic view)
    redirect_to = request.form.get('redirect_to', 'classic')

    try:
        asset = db_session.query(Asset).get(asset_id)
        if not asset:
            flash('Asset not found', 'error')
            if redirect_to == 'sf':
                return redirect(url_for('inventory.view_inventory_sf'))
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

        if redirect_to == 'sf':
            return redirect(url_for('inventory.view_inventory_sf'))
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
        
        # Get current user
        user = db_manager.get_user(session['user_id'])
        
        # Get all customers for the checkout form (filtered by company for non-SUPER_ADMIN users)
        customers = get_filtered_customers(db_session, user)
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

        # Use the centralized customer filtering function
        customers = get_filtered_customers(db_session, user)

        # Get filter parameters from request
        search_name = request.args.get('search_name', '').strip()
        filter_company = request.args.get('filter_company', '').strip()
        filter_country = request.args.get('filter_country', '').strip()

        # Apply filters
        if search_name:
            customers = [c for c in customers if search_name.lower() in c.name.lower()]

        if filter_company:
            customers = [c for c in customers if c.company and filter_company.lower() in c.company.name.lower()]

        if filter_country:
            customers = [c for c in customers if c.country and filter_country.upper() == c.country.upper()]

        # Get unique companies and countries for filter dropdowns
        all_customers = get_filtered_customers(db_session, user)
        companies = sorted(set([c.company.name for c in all_customers if c.company]), key=str.lower)
        countries = sorted(set([c.country for c in all_customers if c.country]))

        # Get all companies for bulk update dropdown
        all_companies = db_session.query(Company).order_by(Company.name).all()

        return render_template('inventory/customer_users.html',
                             customers=customers,
                             len=len,
                             Country=Country,
                             companies=companies,
                             countries=countries,
                             all_companies=all_companies,
                             search_name=search_name,
                             filter_company=filter_company,
                             filter_country=filter_country)
    finally:
        db_session.close()

@inventory_bp.route('/customer-users/add', methods=['GET', 'POST'])
def add_customer_user():
    """Add a new customer user"""
    db_session = db_manager.get_session()
    try:
        if request.method == 'POST':
            try:
                # Get form data
                name = request.form.get('name')
                contact_number = request.form.get('contact_number')
                email = request.form.get('email')
                address = request.form.get('address')
                company_name = request.form.get('company')  # Get company name instead of ID
                country_name = request.form.get('country')
                
                # Validate required fields
                if not name or not contact_number or not address or not company_name or not country_name:
                    return "Missing required fields", 400
                
                # Handle country - normalize the format
                # Convert to uppercase with underscores for consistency
                country_value = country_name.upper().replace(' ', '_')

                # Create new customer user
                customer = CustomerUser(
                    name=name,
                    contact_number=contact_number,
                    email=email if email and email.strip() else None,  # Handle empty email properly
                    address=address,
                    country=country_value
                )

                # Look for existing company by name (normalize to uppercase for comparison)
                company_name_normalized = company_name.strip().upper() if company_name else None
                company = None
                if company_name_normalized:
                    company = db_session.query(Company).filter(Company.name == company_name_normalized).first()
                    if not company:
                        # Create new company if it doesn't exist
                        company = Company(name=company_name_normalized)
                        db_session.add(company)
                        db_session.flush()

                customer.company = company
                db_session.add(customer)
                db_session.commit()
                
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({'success': True}), 200
                
                flash('Customer user added successfully!', 'success')
                return redirect(url_for('inventory.list_customer_users'))
            except Exception as e:
                db_session.rollback()
                logger.info("Error creating customer: {str(e)}")
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({'success': False, 'error': str(e)}), 500
                flash(f'Error creating customer: {str(e)}', 'error')
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
                             available_countries=COUNTRIES)
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

        # Get related tickets for this customer
        from models.ticket import Ticket
        related_tickets = db_session.query(Ticket)\
            .filter(Ticket.customer_id == customer.id)\
            .order_by(Ticket.created_at.desc())\
            .all()

        return render_template('inventory/view_customer_user.html',
                              customer=customer,
                              accessory_quantities=accessory_quantities,
                              related_tickets=related_tickets)
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

        # Use complete list of world countries
        available_countries = COUNTRIES
        
        if not customer:
            flash('Customer user not found', 'error')
            return redirect(url_for('inventory.list_customer_users'))
            
        if request.method == 'POST':
            customer.name = request.form['name']
            customer.contact_number = request.form['contact_number']
            customer.email = request.form['email']
            customer.address = request.form['address']
            customer.company_id = request.form['company_id']

            # Handle country - normalize the format
            country_name = request.form.get('country')
            if country_name:
                customer.country = country_name.upper().replace(' ', '_')

            db_session.commit()
            flash('Customer user updated successfully', 'success')
            return redirect(url_for('inventory.list_customer_users'))
            
        return render_template('inventory/edit_customer_user.html',
                             customer=customer,
                             companies=companies,
                             available_countries=available_countries)
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

@inventory_bp.route('/customer-users/bulk-update-country', methods=['POST'])
@login_required
def bulk_update_customers_country():
    """Bulk update customer country"""
    db_session = db_manager.get_session()
    try:
        user = db_manager.get_user(session['user_id'])

        # Check permissions - only super admin and developer can bulk update
        if not (user.is_super_admin or user.is_developer):
            return jsonify({'success': False, 'error': 'Permission denied'}), 403

        data = request.get_json()
        customer_ids = data.get('customer_ids', [])
        country = data.get('country')

        if not customer_ids:
            return jsonify({'success': False, 'error': 'No customers selected'})

        if not country:
            return jsonify({'success': False, 'error': 'No country specified'})

        # Update customers
        updated_count = 0
        for customer_id in customer_ids:
            customer = db_session.query(CustomerUser).get(customer_id)
            if customer:
                customer.country = country
                updated_count += 1

        db_session.commit()
        return jsonify({'success': True, 'message': f'Successfully updated {updated_count} customer(s) country to {country}'})

    except Exception as e:
        db_session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db_session.close()

@inventory_bp.route('/customer-users/bulk-update-company', methods=['POST'])
@login_required
def bulk_update_customers_company():
    """Bulk update customer company"""
    db_session = db_manager.get_session()
    try:
        user = db_manager.get_user(session['user_id'])

        # Check permissions - only super admin and developer can bulk update
        if not (user.is_super_admin or user.is_developer):
            return jsonify({'success': False, 'error': 'Permission denied'}), 403

        data = request.get_json()
        customer_ids = data.get('customer_ids', [])
        company_id = data.get('company_id')

        if not customer_ids:
            return jsonify({'success': False, 'error': 'No customers selected'})

        if not company_id:
            return jsonify({'success': False, 'error': 'No company specified'})

        # Verify company exists
        company = db_session.query(Company).get(company_id)
        if not company:
            return jsonify({'success': False, 'error': 'Company not found'})

        # Update customers
        updated_count = 0
        for customer_id in customer_ids:
            customer = db_session.query(CustomerUser).get(customer_id)
            if customer:
                customer.company_id = company_id
                updated_count += 1

        db_session.commit()
        return jsonify({'success': True, 'message': f'Successfully updated {updated_count} customer(s) company to {company.name}'})

    except Exception as e:
        db_session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
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
    """Search for assets, accessories, customers, and tickets"""
    search_term = request.args.get('q', '').strip()
    if not search_term:
        return redirect(url_for('inventory.view_inventory'))

    db_session = db_manager.get_session()
    try:
        from models.ticket import Ticket, TicketCategory, TicketStatus, TicketPriority
        from models.customer_user import CustomerUser
        from models.company import Company
        
        user = db_session.query(User).get(session['user_id'])
        
        # Base queries
        asset_query = db_session.query(Asset)
        accessory_query = db_session.query(Accessory)
        customer_query = db_session.query(CustomerUser)
        ticket_query = db_session.query(Ticket)

        # Filter by company for CLIENT users - can only see their company's data
        if user.user_type == UserType.CLIENT and user.company:
            # Assets: filter by company_id or customer name
            asset_query = asset_query.filter(
                or_(
                    Asset.company_id == user.company_id,
                    Asset.customer == user.company.name
                )
            )
            # Accessories: filter by company_id
            accessory_query = accessory_query.filter(Accessory.company_id == user.company_id)
            # Tickets: filter by customer's company (join CustomerUser to check company_id)
            ticket_query = ticket_query.outerjoin(
                CustomerUser, Ticket.customer_id == CustomerUser.id
            ).filter(
                or_(
                    CustomerUser.company_id == user.company_id,
                    Ticket.requester_id == user.id  # Also show tickets they created
                )
            )
            logger.info(f"DEBUG: Filtering search results for client user. Company ID: {user.company_id}, Company Name: {user.company.name}")

        # Initialize permission variables (used for filtering additional ticket queries)
        accessible_queue_ids = []
        permitted_company_ids = []
        permitted_company_names = []

        # Filter for COUNTRY_ADMIN and SUPERVISOR users
        if user.user_type in [UserType.COUNTRY_ADMIN, UserType.SUPERVISOR]:
            from models.user_company_permission import UserCompanyPermission
            from models.user_queue_permission import UserQueuePermission

            # Get permitted company IDs from UserCompanyPermission
            company_permissions = db_session.query(UserCompanyPermission).filter_by(
                user_id=user.id,
                can_view=True
            ).all()
            if company_permissions:
                permitted_company_ids = [perm.company_id for perm in company_permissions]
                # Get company names and include child companies
                permitted_companies = db_session.query(Company).filter(Company.id.in_(permitted_company_ids)).all()
                permitted_company_names = [c.name.strip() for c in permitted_companies if c.name]

                # Include child company IDs
                for company in permitted_companies:
                    if company.child_companies.count() > 0:
                        child_ids = [c.id for c in company.child_companies.all()]
                        permitted_company_ids.extend(child_ids)
                        child_names = [c.name.strip() for c in company.child_companies.all() if c.name]
                        permitted_company_names.extend(child_names)

            # Get accessible queue IDs from UserQueuePermission
            queue_permissions = db_session.query(UserQueuePermission.queue_id).filter(
                UserQueuePermission.user_id == user.id,
                UserQueuePermission.can_view == True
            ).all()
            accessible_queue_ids = [q[0] for q in queue_permissions] if queue_permissions else []

            # Filter assets by country AND company permissions
            if user.assigned_countries:
                asset_query = asset_query.filter(Asset.country.in_(user.assigned_countries))

            if permitted_company_ids:
                asset_query = asset_query.filter(
                    or_(
                        Asset.company_id.in_(permitted_company_ids),
                        Asset.customer.in_(permitted_company_names) if permitted_company_names else sa_false()
                    )
                )
            else:
                # No company permissions = no assets
                asset_query = asset_query.filter(Asset.id == -1)

            # Filter accessories by country AND company permissions
            if user.assigned_countries:
                accessory_query = accessory_query.filter(Accessory.country.in_(user.assigned_countries))
            if permitted_company_ids:
                accessory_query = accessory_query.filter(Accessory.company_id.in_(permitted_company_ids))
            else:
                accessory_query = accessory_query.filter(Accessory.id == -1)

            # Filter tickets by country AND queue permissions
            if user.assigned_countries:
                ticket_query = ticket_query.filter(Ticket.country.in_(user.assigned_countries))

            if accessible_queue_ids:
                ticket_query = ticket_query.filter(Ticket.queue_id.in_(accessible_queue_ids))
            else:
                # No queue permissions = no tickets
                ticket_query = ticket_query.filter(Ticket.id == -1)

            # Filter customers by company permissions
            if permitted_company_ids:
                customer_query = customer_query.filter(CustomerUser.company_id.in_(permitted_company_ids))
            else:
                customer_query = customer_query.filter(CustomerUser.id == -1)

            logger.info(f"DEBUG: Filtering search for {user.user_type.value}. Companies: {permitted_company_ids}, Queues: {accessible_queue_ids}")

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

        # Search customers - apply company filtering for DEVELOPER users with company_id
        # (CLIENT, COUNTRY_ADMIN, SUPERVISOR already filtered above)
        customers = []
        if user.user_type == UserType.DEVELOPER and user.company_id:
            # Filter customers by company for developer users
            customer_query = customer_query.filter(CustomerUser.company_id == user.company_id)

        # Join with Company to search by company name
        customers = customer_query.outerjoin(
            Company, CustomerUser.company_id == Company.id
        ).filter(
            or_(
                CustomerUser.name.ilike(f'%{search_term}%'),
                CustomerUser.email.ilike(f'%{search_term}%'),
                CustomerUser.contact_number.ilike(f'%{search_term}%'),
                CustomerUser.address.ilike(f'%{search_term}%'),
                Company.name.ilike(f'%{search_term}%')
            )
        ).all()

        # Search tickets
        tickets = ticket_query.filter(
            or_(
                Ticket.subject.ilike(f'%{search_term}%'),
                Ticket.description.ilike(f'%{search_term}%'),
                Ticket.notes.ilike(f'%{search_term}%'),
                Ticket.serial_number.ilike(f'%{search_term}%'),
                Ticket.damage_description.ilike(f'%{search_term}%'),
                Ticket.return_description.ilike(f'%{search_term}%'),
                Ticket.shipping_tracking.ilike(f'%{search_term}%'),
                Ticket.return_tracking.ilike(f'%{search_term}%'),
                Ticket.shipping_tracking_2.ilike(f'%{search_term}%'),
                # Search by ticket ID (e.g., "TICK-1001" or just "1001")
                *([Ticket.id == int(search_term.replace('TICK-', '').replace('#', ''))] 
                  if search_term.replace('TICK-', '').replace('#', '').isdigit() else [])
            )
        ).all()

        # Find tickets directly linked to assets matching the search term
        # This finds tickets where the related asset (via asset_id) matches our search
        asset_linked_tickets = []
        try:
            # Search for tickets where the linked asset matches our search term (via asset_id FK)
            asset_linked_query = db_session.query(Ticket).join(
                Asset, Ticket.asset_id == Asset.id
            ).filter(
                or_(
                    Asset.serial_num.ilike(f'%{search_term}%'),
                    Asset.asset_tag.ilike(f'%{search_term}%'),
                    Asset.name.ilike(f'%{search_term}%'),
                    Asset.model.ilike(f'%{search_term}%')
                )
            )

            # Apply permission filters for COUNTRY_ADMIN and SUPERVISOR
            if user.user_type in [UserType.COUNTRY_ADMIN, UserType.SUPERVISOR]:
                if user.assigned_countries:
                    asset_linked_query = asset_linked_query.filter(Ticket.country.in_(user.assigned_countries))
                if accessible_queue_ids:
                    asset_linked_query = asset_linked_query.filter(Ticket.queue_id.in_(accessible_queue_ids))
                else:
                    asset_linked_query = asset_linked_query.filter(Ticket.id == -1)
            elif user.user_type == UserType.CLIENT and user.company:
                asset_linked_query = asset_linked_query.outerjoin(
                    CustomerUser, Ticket.customer_id == CustomerUser.id
                ).filter(
                    or_(
                        CustomerUser.company_id == user.company_id,
                        Ticket.requester_id == user.id
                    )
                )

            asset_linked_tickets = asset_linked_query.all()

            # Also search for tickets linked via ticket_assets many-to-many table
            from models.asset import ticket_assets
            multi_asset_query = db_session.query(Ticket).join(
                ticket_assets, Ticket.id == ticket_assets.c.ticket_id
            ).join(
                Asset, ticket_assets.c.asset_id == Asset.id
            ).filter(
                or_(
                    Asset.serial_num.ilike(f'%{search_term}%'),
                    Asset.asset_tag.ilike(f'%{search_term}%'),
                    Asset.name.ilike(f'%{search_term}%'),
                    Asset.model.ilike(f'%{search_term}%')
                )
            )

            # Apply permission filters for COUNTRY_ADMIN and SUPERVISOR
            if user.user_type in [UserType.COUNTRY_ADMIN, UserType.SUPERVISOR]:
                if user.assigned_countries:
                    multi_asset_query = multi_asset_query.filter(Ticket.country.in_(user.assigned_countries))
                if accessible_queue_ids:
                    multi_asset_query = multi_asset_query.filter(Ticket.queue_id.in_(accessible_queue_ids))
                else:
                    multi_asset_query = multi_asset_query.filter(Ticket.id == -1)
            elif user.user_type == UserType.CLIENT and user.company:
                multi_asset_query = multi_asset_query.outerjoin(
                    CustomerUser, Ticket.customer_id == CustomerUser.id
                ).filter(
                    or_(
                        CustomerUser.company_id == user.company_id,
                        Ticket.requester_id == user.id
                    )
                )

            multi_asset_tickets = multi_asset_query.all()

            # Merge multi_asset_tickets into asset_linked_tickets (avoid duplicates)
            existing_ids = {t.id for t in asset_linked_tickets}
            for t in multi_asset_tickets:
                if t.id not in existing_ids:
                    asset_linked_tickets.append(t)
                    existing_ids.add(t.id)
        except Exception as e:
            logger.error(f"Error searching asset-linked tickets: {e}")

        # Merge asset_linked_tickets with tickets (avoid duplicates)
        ticket_ids = [t.id for t in tickets]
        for t in asset_linked_tickets:
            if t.id not in ticket_ids:
                tickets.append(t)
                ticket_ids.append(t.id)

        # Find related tickets for found assets (additional related results)
        related_tickets = []
        if assets:
            # Get asset serial numbers and asset tags
            asset_serial_numbers = [asset.serial_num for asset in assets if asset.serial_num]
            asset_tags = [asset.asset_tag for asset in assets if asset.asset_tag]
            asset_ids = [asset.id for asset in assets]

            # Build conditions list for the query
            conditions = []
            if asset_serial_numbers:
                conditions.append(Ticket.serial_number.in_(asset_serial_numbers))
            if asset_ids:
                conditions.append(Ticket.asset_id.in_(asset_ids))

            # Add description/notes search for asset tags and serial numbers
            for tag in asset_tags[:5]:  # Limit to avoid too many conditions
                if tag:
                    conditions.append(Ticket.description.ilike(f'%{tag}%'))
                    conditions.append(Ticket.notes.ilike(f'%{tag}%'))
            for serial in asset_serial_numbers[:5]:
                if serial:
                    conditions.append(Ticket.description.ilike(f'%{serial}%'))
                    conditions.append(Ticket.notes.ilike(f'%{serial}%'))

            if conditions:
                related_tickets_query = ticket_query.filter(or_(*conditions))
                related_tickets = related_tickets_query.all()

            # Also find tickets linked to these assets via ticket_assets many-to-many table
            if asset_ids:
                try:
                    from models.asset import ticket_assets
                    multi_asset_related_query = db_session.query(Ticket).join(
                        ticket_assets, Ticket.id == ticket_assets.c.ticket_id
                    ).filter(
                        ticket_assets.c.asset_id.in_(asset_ids)
                    )

                    # Apply permission filters for COUNTRY_ADMIN and SUPERVISOR
                    if user.user_type in [UserType.COUNTRY_ADMIN, UserType.SUPERVISOR]:
                        if user.assigned_countries:
                            multi_asset_related_query = multi_asset_related_query.filter(Ticket.country.in_(user.assigned_countries))
                        if accessible_queue_ids:
                            multi_asset_related_query = multi_asset_related_query.filter(Ticket.queue_id.in_(accessible_queue_ids))
                        else:
                            multi_asset_related_query = multi_asset_related_query.filter(Ticket.id == -1)
                    elif user.user_type == UserType.CLIENT and user.company:
                        multi_asset_related_query = multi_asset_related_query.outerjoin(
                            CustomerUser, Ticket.customer_id == CustomerUser.id
                        ).filter(
                            or_(
                                CustomerUser.company_id == user.company_id,
                                Ticket.requester_id == user.id
                            )
                        )

                    multi_asset_related = multi_asset_related_query.all()

                    # Merge into related_tickets
                    existing_related_ids = {t.id for t in related_tickets}
                    for t in multi_asset_related:
                        if t.id not in existing_related_ids:
                            related_tickets.append(t)
                            existing_related_ids.add(t.id)
                except Exception as e:
                    logger.error(f"Error searching multi-asset related tickets: {e}")

            # Remove duplicates if a ticket appears in both direct search and related search
            related_tickets = [t for t in related_tickets if t.id not in ticket_ids]

        return render_template('inventory/search_results.html',
                             query=search_term,
                             assets=assets,
                             accessories=accessories,
                             customers=customers,
                             tickets=tickets,
                             related_tickets=related_tickets,
                             user=user)
    finally:
        db_session.close()


@inventory_bp.route('/search/suggestions')
@login_required
def search_suggestions():
    """Return search suggestions for autocomplete"""
    from flask import jsonify
    from models.ticket import Ticket
    from models.customer_user import CustomerUser

    search_term = request.args.get('q', '').strip()
    if not search_term or len(search_term) < 2:
        return jsonify({'suggestions': []})

    db_session = db_manager.get_session()
    try:
        user = db_session.query(User).get(session['user_id'])
        suggestions = []

        # Get permission data for COUNTRY_ADMIN and SUPERVISOR users
        permitted_company_ids = []
        permitted_company_names = []
        accessible_queue_ids = []

        if user.user_type in [UserType.COUNTRY_ADMIN, UserType.SUPERVISOR]:
            from models.user_company_permission import UserCompanyPermission
            from models.user_queue_permission import UserQueuePermission
            from models.company import Company

            # Get permitted company IDs
            company_permissions = db_session.query(UserCompanyPermission).filter_by(
                user_id=user.id, can_view=True
            ).all()
            if company_permissions:
                permitted_company_ids = [perm.company_id for perm in company_permissions]
                permitted_companies = db_session.query(Company).filter(Company.id.in_(permitted_company_ids)).all()
                permitted_company_names = [c.name.strip() for c in permitted_companies if c.name]
                # Include child companies
                for company in permitted_companies:
                    if company.child_companies.count() > 0:
                        child_ids = [c.id for c in company.child_companies.all()]
                        permitted_company_ids.extend(child_ids)
                        child_names = [c.name.strip() for c in company.child_companies.all() if c.name]
                        permitted_company_names.extend(child_names)

            # Get accessible queue IDs
            queue_permissions = db_session.query(UserQueuePermission.queue_id).filter(
                UserQueuePermission.user_id == user.id,
                UserQueuePermission.can_view == True
            ).all()
            accessible_queue_ids = [q[0] for q in queue_permissions] if queue_permissions else []

        # Search assets (limit 5)
        asset_query = db_session.query(Asset)
        if user.user_type == UserType.CLIENT and user.company:
            asset_query = asset_query.filter(
                or_(Asset.company_id == user.company_id, Asset.customer == user.company.name)
            )
        elif user.user_type in [UserType.COUNTRY_ADMIN, UserType.SUPERVISOR]:
            # Filter by country if assigned
            if user.assigned_countries:
                asset_query = asset_query.filter(Asset.country.in_(user.assigned_countries))
            # Filter by company permissions
            if permitted_company_ids:
                asset_query = asset_query.filter(
                    or_(
                        Asset.company_id.in_(permitted_company_ids),
                        Asset.customer.in_(permitted_company_names) if permitted_company_names else sa_false()
                    )
                )
            else:
                asset_query = asset_query.filter(Asset.id == -1)

        assets = asset_query.filter(
            or_(
                Asset.serial_num.ilike(f'%{search_term}%'),
                Asset.asset_tag.ilike(f'%{search_term}%'),
                Asset.name.ilike(f'%{search_term}%'),
                Asset.model.ilike(f'%{search_term}%')
            )
        ).limit(5).all()

        for asset in assets:
            suggestions.append({
                'type': 'asset',
                'icon': 'laptop',
                'title': asset.asset_tag or asset.serial_num or asset.name,
                'subtitle': f"{asset.name} • {asset.model or 'No model'}",
                'url': url_for('inventory.view_asset', asset_id=asset.id)
            })

        # Search tickets (limit 5)
        ticket_query = db_session.query(Ticket)
        # Filter by company for CLIENT users (via customer's company)
        if user.user_type == UserType.CLIENT and user.company:
            ticket_query = ticket_query.outerjoin(
                CustomerUser, Ticket.customer_id == CustomerUser.id
            ).filter(
                or_(
                    CustomerUser.company_id == user.company_id,
                    Ticket.requester_id == user.id  # Also show tickets they created
                )
            )
        elif user.user_type in [UserType.COUNTRY_ADMIN, UserType.SUPERVISOR]:
            # Filter by country if assigned
            if user.assigned_countries:
                ticket_query = ticket_query.filter(Ticket.country.in_(user.assigned_countries))
            # Filter by queue permissions
            if accessible_queue_ids:
                ticket_query = ticket_query.filter(Ticket.queue_id.in_(accessible_queue_ids))
            else:
                ticket_query = ticket_query.filter(Ticket.id == -1)

        tickets = ticket_query.filter(
            or_(
                Ticket.subject.ilike(f'%{search_term}%'),
                Ticket.serial_number.ilike(f'%{search_term}%'),
                Ticket.shipping_tracking.ilike(f'%{search_term}%'),
                *([Ticket.id == int(search_term.replace('TICK-', '').replace('#', ''))]
                  if search_term.replace('TICK-', '').replace('#', '').isdigit() else [])
            )
        ).limit(5).all()

        for ticket in tickets:
            status_color = {
                'New': 'blue', 'In Progress': 'yellow', 'On Hold': 'orange',
                'Resolved': 'green'
            }.get(ticket.status.value if ticket.status else '', 'gray')
            suggestions.append({
                'type': 'ticket',
                'icon': 'ticket-alt',
                'title': ticket.display_id,
                'subtitle': ticket.subject[:50] + ('...' if len(ticket.subject) > 50 else ''),
                'status': ticket.status.value if ticket.status else 'Unknown',
                'status_color': status_color,
                'url': url_for('tickets.view_ticket', ticket_id=ticket.id)
            })

        # Search accessories (limit 3)
        accessory_query = db_session.query(Accessory)
        # Filter by company for CLIENT users
        if user.user_type == UserType.CLIENT and user.company:
            accessory_query = accessory_query.filter(Accessory.company_id == user.company_id)
        elif user.user_type in [UserType.COUNTRY_ADMIN, UserType.SUPERVISOR]:
            # Filter by country if assigned
            if user.assigned_countries:
                accessory_query = accessory_query.filter(Accessory.country.in_(user.assigned_countries))
            # Filter by company permissions
            if permitted_company_ids:
                accessory_query = accessory_query.filter(Accessory.company_id.in_(permitted_company_ids))
            else:
                accessory_query = accessory_query.filter(Accessory.id == -1)

        accessories = accessory_query.filter(
            or_(
                Accessory.name.ilike(f'%{search_term}%'),
                Accessory.model_no.ilike(f'%{search_term}%'),
                Accessory.category.ilike(f'%{search_term}%')
            )
        ).limit(3).all()

        for acc in accessories:
            suggestions.append({
                'type': 'accessory',
                'icon': 'plug',
                'title': acc.name,
                'subtitle': f"{acc.category or 'Accessory'} • Qty: {acc.available_quantity}/{acc.total_quantity}",
                'url': url_for('inventory.view_accessory', id=acc.id)
            })

        # Search customers (limit 5) - for staff users
        if user.user_type in [UserType.SUPER_ADMIN, UserType.DEVELOPER, UserType.SUPERVISOR, UserType.COUNTRY_ADMIN]:
            from models.company import Company

            # Build customer query with company join for company name search
            customer_query = db_session.query(CustomerUser).outerjoin(
                Company, CustomerUser.company_id == Company.id
            ).filter(
                or_(
                    CustomerUser.name.ilike(f'%{search_term}%'),
                    CustomerUser.email.ilike(f'%{search_term}%'),
                    CustomerUser.contact_number.ilike(f'%{search_term}%'),
                    Company.name.ilike(f'%{search_term}%')
                )
            )

            # Filter by company for non-super admin users
            if user.user_type != UserType.SUPER_ADMIN and user.company_id:
                customer_query = customer_query.filter(CustomerUser.company_id == user.company_id)

            customers = customer_query.limit(5).all()

            for cust in customers:
                company_name = cust.company.name if cust.company else ''
                suggestions.append({
                    'type': 'customer',
                    'icon': 'user',
                    'title': cust.name,
                    'subtitle': f"{company_name} • {cust.email or 'No email'}",
                    'url': url_for('inventory.view_customer_user', id=cust.id)
                })

        return jsonify({'suggestions': suggestions})
    finally:
        db_session.close()


@inventory_bp.route('/export/<string:item_type>', methods=['GET', 'POST'])
@login_required
def export_inventory(item_type):
    # Ensure user has permission to export data - allow SUPER_ADMIN, DEVELOPER, SUPERVISOR, and COUNTRY_ADMIN
    if not (current_user.is_super_admin or current_user.is_developer or current_user.is_supervisor or current_user.is_country_admin):
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

            # Apply user permission filters for SUPERVISOR and COUNTRY_ADMIN
            if current_user.is_supervisor or current_user.is_country_admin:
                from models.user_company_permission import UserCompanyPermission

                # Filter by assigned countries
                if current_user.assigned_countries:
                    query = query.filter(Asset.country.in_(current_user.assigned_countries))

                # Filter by company permissions
                company_permissions = db_session.query(UserCompanyPermission).filter_by(
                    user_id=current_user.id,
                    can_view=True
                ).all()

                if company_permissions:
                    permitted_company_ids = [perm.company_id for perm in company_permissions]
                    permitted_companies = db_session.query(Company).filter(Company.id.in_(permitted_company_ids)).all()

                    # Include child company IDs
                    all_company_ids = list(permitted_company_ids)
                    all_company_names = [c.name.strip() for c in permitted_companies]

                    for company in permitted_companies:
                        if company.is_parent_company or company.child_companies.count() > 0:
                            child_companies = company.child_companies.all()
                            all_company_ids.extend([c.id for c in child_companies])
                            all_company_names.extend([c.name.strip() for c in child_companies])

                    # Filter by company_id or customer name
                    name_conditions = [func.lower(Asset.customer).like(f"%{name.lower()}%") for name in all_company_names]
                    query = query.filter(
                        or_(
                            Asset.company_id.in_(all_company_ids),
                            *name_conditions
                        )
                    )
                else:
                    # No permissions - export nothing
                    query = query.filter(Asset.id == -1)

            # Apply filters from query parameters (from inventory view)
            status_filter = request.args.get('status')
            if status_filter and status_filter != 'all':
                from models.enums import AssetStatus
                try:
                    status_enum = AssetStatus(status_filter)
                    query = query.filter(Asset.status == status_enum)
                except ValueError:
                    pass

            model_filter = request.args.get('model')
            if model_filter and model_filter != 'all':
                query = query.filter(Asset.model == model_filter)

            company_filter = request.args.get('company')
            if company_filter and company_filter != 'all':
                if company_filter == '__unknown__' or company_filter == '':
                    # Filter for assets with empty/null company
                    query = query.filter(or_(
                        Asset.customer.is_(None),
                        Asset.customer == '',
                        func.trim(Asset.customer) == ''
                    ))
                else:
                    query = query.filter(Asset.customer == company_filter)

            country_filter = request.args.get('country')
            if country_filter and country_filter != 'all':
                query = query.filter(Asset.country == country_filter)

            search_filter = request.args.get('search')
            if search_filter:
                search_term = f"%{search_filter}%"
                query = query.filter(
                    or_(
                        Asset.serial_num.ilike(search_term),
                        Asset.asset_tag.ilike(search_term),
                        Asset.model.ilike(search_term),
                        Asset.name.ilike(search_term)
                    )
                )

            assets = query.all()
            
            if not assets:
                flash('No assets selected for export', 'error')
                return redirect(url_for('inventory.view_inventory'))
            
            # Write header
            writer.writerow([
                'Package Number', 'Asset Type', 'Product', 'ASSET TAG', 'Receiving date', 'Keyboard',
                'SERIAL NUMBER', 'PO', 'MODEL', 'ERASED', 'CUSTOMER', 'CONDITION',
                'DIAG', 'HARDWARE TYPE', 'CPU TYPE', 'CPU CORES', 'GPU CORES',
                'MEMORY', 'HARDDRIVE', 'STATUS', 'CHARGER', 'INCLUDED', 'INVENTORY',
                'country'
            ])

            # Import PackageItem model
            from models.package_item import PackageItem

            # Write data
            for asset in assets:
                # Check if this asset has package items
                package_items = db_session.query(PackageItem).filter(
                    PackageItem.asset_id == asset.id
                ).order_by(PackageItem.package_number).all()

                if package_items:
                    # Create one row per package item
                    for pkg_item in package_items:
                        writer.writerow([
                            f'Package {pkg_item.package_number}',
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
                else:
                    # No package items, create one row as normal
                    writer.writerow([
                        '',  # No package number
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
            # Get accessories based on user permissions and selection
            query = db_session.query(Accessory)

            # Handle selected accessories if POST request
            if request.method == 'POST' and request.form.get('selected_ids'):
                try:
                    selected_ids = json.loads(request.form.get('selected_ids'))
                    if selected_ids:
                        query = query.filter(Accessory.id.in_(selected_ids))
                except json.JSONDecodeError:
                    flash('Invalid selection data', 'error')
                    return redirect(url_for('inventory.view_accessories'))

            # Apply user permission filters
            if not current_user.is_super_admin:
                if current_user.is_country_admin and current_user.assigned_countries:
                    query = query.filter(Accessory.country == current_user.assigned_country)

            accessories = query.all()

            if not accessories:
                flash('No accessories selected for export', 'error')
                return redirect(url_for('inventory.view_accessories'))
            
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
            download_name=f'inventory_{item_type}_{singapore_now_as_utc().strftime("%Y%m%d_%H%M%S")}.csv'
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
        logger.error(f"Error in bulk_checkout: {str(e)}")
        return jsonify({'error': f"Unexpected error during checkout: {str(e)}"}), 500
    finally:
        db_session.close()

@inventory_bp.route('/bulk-delete', methods=['POST'])
@login_required
@admin_required
def bulk_delete():
    """Delete multiple assets and accessories - Optimized for large batches"""
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

        # Process assets in batches for better performance
        BATCH_SIZE = 100  # Process 100 assets at a time
        
        if asset_ids:
            logger.info(f"Starting bulk deletion of {len(asset_ids)} assets")
            
            # Get asset info for activity logging before deletion
            assets_info = []
            if len(asset_ids) <= 1000:  # Only get detailed info for reasonable batch sizes
                assets_query = db_session.query(Asset.id, Asset.name, Asset.asset_tag, Asset.serial_num)\
                    .filter(Asset.id.in_(asset_ids)).all()
                assets_info = {asset.id: {
                    'name': asset.name or 'Unknown',
                    'asset_tag': asset.asset_tag or 'Unknown',
                    'serial_num': asset.serial_num or 'Unknown'
                } for asset in assets_query}

            # Process assets in batches
            for i in range(0, len(asset_ids), BATCH_SIZE):
                batch_ids = asset_ids[i:i + BATCH_SIZE]
                
                try:
                    # Delete related data first using bulk operations
                    # 1. Delete asset history
                    deleted_history = db_session.query(AssetHistory)\
                        .filter(AssetHistory.asset_id.in_(batch_ids)).delete(synchronize_session=False)
                    
                    # 2. Delete asset transactions
                    deleted_transactions = db_session.query(AssetTransaction)\
                        .filter(AssetTransaction.asset_id.in_(batch_ids)).delete(synchronize_session=False)
                    
                    # 3. Remove ticket-asset associations
                    if batch_ids:
                        from models.asset import ticket_assets
                        db_session.execute(
                            ticket_assets.delete().where(ticket_assets.c.asset_id.in_(batch_ids))
                        )
                    
                    # 4. Delete the assets themselves
                    deleted_count = db_session.query(Asset)\
                        .filter(Asset.id.in_(batch_ids)).delete(synchronize_session=False)
                    
                    deleted_assets += deleted_count
                    
                    # Commit this batch
                    db_session.commit()
                    
                    logger.info(f"Deleted batch {i//BATCH_SIZE + 1}: {deleted_count} assets, {deleted_history} history records, {deleted_transactions} transactions")
                    
                except Exception as e:
                    db_session.rollback()
                    error_msg = f'Error deleting asset batch {i//BATCH_SIZE + 1}: {str(e)}'
                    errors.append(error_msg)
                    logger.error(error_msg)
                    continue

            # Add a single activity log for the bulk operation
            if deleted_assets > 0:
                try:
                    activity = Activity(
                        user_id=current_user.id,
                        type='bulk_asset_deleted',
                        content=f'Bulk deleted {deleted_assets} assets',
                        reference_id=0
                    )
                    db_session.add(activity)
                    db_session.commit()
                except Exception as e:
                    logger.error(f"Error adding activity log: {str(e)}")

        # Process accessories in batches
        if accessory_ids:
            logger.info(f"Starting bulk deletion of {len(accessory_ids)} accessories")
            
            for i in range(0, len(accessory_ids), BATCH_SIZE):
                batch_ids = accessory_ids[i:i + BATCH_SIZE]
                
                try:
                    # Delete accessory history first
                    deleted_history = db_session.query(AccessoryHistory)\
                        .filter(AccessoryHistory.accessory_id.in_(batch_ids)).delete(synchronize_session=False)
                    
                    # Delete accessory transactions
                    deleted_transactions = db_session.query(AccessoryTransaction)\
                        .filter(AccessoryTransaction.accessory_id.in_(batch_ids)).delete(synchronize_session=False)
                    
                    # Delete the accessories
                    deleted_count = db_session.query(Accessory)\
                        .filter(Accessory.id.in_(batch_ids)).delete(synchronize_session=False)
                    
                    deleted_accessories += deleted_count
                    
                    # Commit this batch
                    db_session.commit()
                    
                    logger.info(f"Deleted accessory batch {i//BATCH_SIZE + 1}: {deleted_count} accessories, {deleted_history} history records, {deleted_transactions} transactions")
                    
                except Exception as e:
                    db_session.rollback()
                    error_msg = f'Error deleting accessory batch {i//BATCH_SIZE + 1}: {str(e)}'
                    errors.append(error_msg)
                    logger.error(error_msg)
                    continue

            # Add activity log for accessory bulk operation
            if deleted_accessories > 0:
                try:
                    activity = Activity(
                        user_id=current_user.id,
                        type='bulk_accessory_deleted',
                        content=f'Bulk deleted {deleted_accessories} accessories',
                        reference_id=0
                    )
                    db_session.add(activity)
                    db_session.commit()
                except Exception as e:
                    logger.error(f"Error adding accessory activity log: {str(e)}")

        # Report results
        if errors:
            error_message = '<br>'.join(errors[:10])  # Limit error messages
            if len(errors) > 10:
                error_message += f'<br>... and {len(errors) - 10} more errors'
            flash(f'Partial deletion completed. {deleted_assets} assets and {deleted_accessories} accessories deleted.<br>Errors:<br>{error_message}', 'warning')
        else:
            flash(f'Successfully deleted {deleted_assets} assets and {deleted_accessories} accessories.', 'success')

        return redirect(url_for('inventory.view_inventory'))

    except Exception as e:
        db_session.rollback()
        logger.error(f'Critical error during bulk deletion: {str(e)}')
        logger.error(traceback.format_exc())
        flash(f'Critical error during bulk deletion: {str(e)}', 'error')
        return redirect(url_for('inventory.view_inventory'))
    finally:
        db_session.close()

@inventory_bp.route('/bulk-delete-large', methods=['POST'])
@login_required
@admin_required
def bulk_delete_large():
    """Handle very large bulk deletions (1000+ items) with progress tracking"""
    if not current_user.is_admin:
        return jsonify({'error': 'Permission denied'}), 403

    try:
        # Get selected IDs
        data = request.get_json()
        asset_ids = data.get('asset_ids', [])
        accessory_ids = data.get('accessory_ids', [])
        
        if not asset_ids and not accessory_ids:
            return jsonify({'error': 'No items selected'}), 400

        total_items = len(asset_ids) + len(accessory_ids)
        
        # For very large operations, process in background
        if total_items > 500:
            # Store the deletion job in session for progress tracking
            session['bulk_delete_job'] = {
                'asset_ids': asset_ids,
                'accessory_ids': accessory_ids,
                'total_items': total_items,
                'processed': 0,
                'status': 'starting',
                'start_time': singapore_now_as_utc().isoformat()
            }
            
            return jsonify({
                'status': 'started',
                'total_items': total_items,
                'message': f'Started bulk deletion of {total_items} items. This may take several minutes.'
            })
        else:
            # For smaller batches, process immediately
            return jsonify({'status': 'redirect', 'url': url_for('inventory.bulk_delete')})
            
    except Exception as e:
        logger.error(f'Error starting bulk delete: {str(e)}')
        return jsonify({'error': str(e)}), 500

@inventory_bp.route('/bulk-delete-progress', methods=['GET'])
@login_required
@admin_required
def bulk_delete_progress():
    """Get progress of bulk deletion operation"""
    job = session.get('bulk_delete_job')
    if not job:
        return jsonify({'error': 'No active deletion job'}), 404
    
    # If job is starting, begin processing
    if job['status'] == 'starting':
        try:
            _process_bulk_delete_job(job)
        except Exception as e:
            job['status'] = 'error'
            job['error'] = str(e)
            session['bulk_delete_job'] = job
    
    return jsonify(job)

def _process_bulk_delete_job(job):
    """Process the bulk deletion job in chunks"""
    db_session = db_manager.get_session()
    
    try:
        job['status'] = 'processing'
        session['bulk_delete_job'] = job
        
        asset_ids = job['asset_ids']
        accessory_ids = job['accessory_ids']
        
        deleted_assets = 0
        deleted_accessories = 0
        BATCH_SIZE = 50  # Smaller batches for large operations
        
        # Process assets
        if asset_ids:
            for i in range(0, len(asset_ids), BATCH_SIZE):
                batch_ids = asset_ids[i:i + BATCH_SIZE]
                
                try:
                    # Delete related data first
                    db_session.query(AssetHistory)\
                        .filter(AssetHistory.asset_id.in_(batch_ids)).delete(synchronize_session=False)
                    
                    db_session.query(AssetTransaction)\
                        .filter(AssetTransaction.asset_id.in_(batch_ids)).delete(synchronize_session=False)
                    
                    # Remove ticket associations
                    if batch_ids:
                        from models.asset import ticket_assets
                        db_session.execute(
                            ticket_assets.delete().where(ticket_assets.c.asset_id.in_(batch_ids))
                        )
                    
                    # Delete assets
                    deleted_count = db_session.query(Asset)\
                        .filter(Asset.id.in_(batch_ids)).delete(synchronize_session=False)
                    
                    deleted_assets += deleted_count
                    db_session.commit()
                    
                    # Update progress
                    job['processed'] += len(batch_ids)
                    job['deleted_assets'] = deleted_assets
                    session['bulk_delete_job'] = job
                    
                except Exception as e:
                    db_session.rollback()
                    logger.error(f"Error in asset batch {i//BATCH_SIZE + 1}: {str(e)}")
                    continue
        
        # Process accessories
        if accessory_ids:
            for i in range(0, len(accessory_ids), BATCH_SIZE):
                batch_ids = accessory_ids[i:i + BATCH_SIZE]
                
                try:
                    # Delete related data first
                    db_session.query(AccessoryHistory)\
                        .filter(AccessoryHistory.accessory_id.in_(batch_ids)).delete(synchronize_session=False)
                    
                    db_session.query(AccessoryTransaction)\
                        .filter(AccessoryTransaction.accessory_id.in_(batch_ids)).delete(synchronize_session=False)
                    
                    # Delete accessories
                    deleted_count = db_session.query(Accessory)\
                        .filter(Accessory.id.in_(batch_ids)).delete(synchronize_session=False)
                    
                    deleted_accessories += deleted_count
                    db_session.commit()
                    
                    # Update progress
                    job['processed'] += len(batch_ids)
                    job['deleted_accessories'] = deleted_accessories
                    session['bulk_delete_job'] = job
                    
                except Exception as e:
                    db_session.rollback()
                    logger.error(f"Error in accessory batch {i//BATCH_SIZE + 1}: {str(e)}")
                    continue
        
        # Mark as completed
        job['status'] = 'completed'
        job['deleted_assets'] = deleted_assets
        job['deleted_accessories'] = deleted_accessories
        job['end_time'] = singapore_now_as_utc().isoformat()
        session['bulk_delete_job'] = job
        
        # Add activity log
        try:
            if deleted_assets > 0:
                activity = Activity(
                    user_id=current_user.id,
                    type='bulk_asset_deleted',
                    content=f'Bulk deleted {deleted_assets} assets',
                    reference_id=0
                )
                db_session.add(activity)
            
            if deleted_accessories > 0:
                activity = Activity(
                    user_id=current_user.id,
                    type='bulk_accessory_deleted',
                    content=f'Bulk deleted {deleted_accessories} accessories',
                    reference_id=0
                )
                db_session.add(activity)
            
            db_session.commit()
        except Exception as e:
            logger.error(f"Error adding activity logs: {str(e)}")
        
    except Exception as e:
        job['status'] = 'error'
        job['error'] = str(e)
        session['bulk_delete_job'] = job
        logger.error(f"Critical error in bulk delete job: {str(e)}")
        logger.error(traceback.format_exc())
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
        # Get current user
        user = db_manager.get_user(session['user_id'])
        
        # Base query for customers
        customers_query = db_session.query(CustomerUser)\
            .options(joinedload(CustomerUser.company))\
            .options(joinedload(CustomerUser.assigned_assets))\
            .options(joinedload(CustomerUser.assigned_accessories))
        
        # Apply company filtering for non-SUPER_ADMIN users
        if user.user_type != UserType.SUPER_ADMIN and user.company_id:
            customers_query = customers_query.filter(CustomerUser.company_id == user.company_id)
        
        customers = customers_query.order_by(CustomerUser.name).all()
        
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

@inventory_bp.route('/api/assets')
@login_required
def get_assets_api():
    """Get all assets for asset selection modal"""
    logger.info("[ASSETS API] Starting assets API request for user_id: {session.get('user_id')}")
    db_session = db_manager.get_session()
    try:
        # Get current user for filtering
        user = db_manager.get_user(session['user_id'])
        logger.info("[ASSETS API] User {user.username} (Type: {user.user_type}) requesting assets")
        
        # Build query with permissions filtering
        assets_query = db_session.query(Asset)
        
        # Filter assets based on user type and permissions
        if user.is_super_admin:
            assets = assets_query.all()
        elif user.user_type == UserType.COUNTRY_ADMIN and user.assigned_countries:
            assets = assets_query.filter(Asset.country.in_(user.assigned_countries)).all()
        elif user.user_type == UserType.SUPERVISOR and user.assigned_countries:
            # Supervisors can see assets from their assigned country
            assets = assets_query.filter(Asset.country.in_(user.assigned_countries)).all()
        elif user.user_type == UserType.CLIENT and user.company:
            # Clients can see assets from their company
            assets = assets_query.filter(
                or_(
                    Asset.company_id == user.company_id,
                    Asset.customer == user.company.name
                )
            ).all()
        else:
            # For other user types, show all assets (this includes regular staff who might need to assign assets)
            assets = assets_query.all()
        
        # Convert to dictionaries for JSON response
        assets_data = []
        for asset in assets:
            try:
                # Safely get customer name with proper error handling
                customer_name = None
                try:
                    if asset.customer_user:
                        customer_name = asset.customer_user.name
                except Exception as customer_err:
                    logger.info("[ASSETS API] Error getting customer for asset {asset.id}: {customer_err}")
                    customer_name = None
                
                assets_data.append({
                    # Basic Info
                    'id': asset.id,
                    'asset_tag': asset.asset_tag,
                    'serial_num': asset.serial_num,
                    'name': asset.name,
                    'model': asset.model,
                    'manufacturer': asset.manufacturer,
                    'category': asset.category,
                    'status': asset.status.value if asset.status else 'Unknown',

                    # Hardware Specs
                    'cpu_type': asset.cpu_type,
                    'cpu_cores': asset.cpu_cores,
                    'gpu_cores': asset.gpu_cores,
                    'memory': asset.memory,
                    'storage': asset.harddrive,  # harddrive field is storage
                    'asset_type': asset.asset_type,
                    'hardware_type': asset.hardware_type,

                    # Condition Fields
                    'condition': asset.condition,
                    'is_erased': asset.erased,
                    'has_keyboard': asset.keyboard,
                    'has_charger': asset.charger,
                    'diagnostics_code': asset.diag,

                    # Location/Assignment Fields
                    'current_customer': customer_name,
                    'customer': asset.customer,  # Legacy customer field
                    'country': asset.country,
                    'asset_company': asset.company.name if asset.company else None,
                    'company_id': asset.company_id,
                    'location_id': asset.location_id,
                    'location': asset.location.name if asset.location else None,

                    # Additional Fields
                    'cost_price': asset.cost_price,
                    'notes': asset.notes,
                    'tech_notes': asset.tech_notes,
                    'specifications': asset.specifications,
                    'po': asset.po,
                    'receiving_date': asset.receiving_date.isoformat() if asset.receiving_date else None,
                    'created_at': asset.created_at.isoformat() if asset.created_at else None,
                    'updated_at': asset.updated_at.isoformat() if asset.updated_at else None
                })
            except Exception as asset_err:
                logger.info("[ASSETS API] Error processing asset {asset.id}: {asset_err}")
                continue
        
        logger.info("[ASSETS API] Returning {len(assets_data)} assets")
        return jsonify({
            'success': True,
            'assets': assets_data
        })
    except Exception as e:
        import traceback
        logger.info("[ASSETS API ERROR] Full traceback: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
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
    from routes.import_manager import create_import_session, update_import_session

    if request.method == 'POST':
        db_session = db_manager.get_session()
        import_session_id = None
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
                
                # Create ImportSession to track this import
                try:
                    import_session_id, display_id = create_import_session(
                        import_type='customers',
                        user_id=current_user.id,
                        file_name=file.filename,
                        notes=f"Customer users import with {len(df)} rows"
                    )
                    logger.info(f"Created import session {display_id} for customers import")
                except Exception as e:
                    logger.error(f"Failed to create import session: {str(e)}")

                # Process the data
                success_count = 0
                error_count = 0
                errors = []
                successful_imports = []  # Track successfully imported customers

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

                        # Look for existing company by name (normalize to uppercase for comparison)
                        company_name_normalized = company_name.strip().upper() if company_name else None
                        company = None
                        if company_name_normalized:
                            company = db_session.query(Company).filter(Company.name == company_name_normalized).first()
                            if not company:
                                # Create new company if it doesn't exist
                                company = Company(name=company_name_normalized)
                                db_session.add(company)
                                db_session.flush()

                        # Create new customer user
                        customer = CustomerUser(
                            name=name,
                            contact_number=contact_number,
                            email=email if email and email.strip() else None,  # Ensure empty emails are stored as None
                            address=address,
                            country=country
                        )

                        customer.company = company
                        db_session.add(customer)
                        db_session.flush()  # Get customer ID
                        success_count += 1

                        # Track successful import
                        successful_imports.append({
                            'row': index + 2,
                            'customer_id': customer.id,
                            'name': name,
                            'company': company_name_normalized,
                            'country': country_str,
                            'email': email
                        })

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

                # Update ImportSession with results
                if import_session_id:
                    try:
                        status = 'completed' if success_count > 0 else 'failed'
                        # Store successful imports data (limit to first 100)
                        import_data = successful_imports[:100] if successful_imports else None
                        update_import_session(import_session_id, success_count=success_count, fail_count=error_count,
                                             import_data=import_data, error_details=errors[:50] if errors else None, status=status)
                    except Exception as e:
                        logger.error(f"Failed to update import session: {str(e)}")

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
    logger.debug(f"Fetching transactions for accessory {id}")
    db_session = db_manager.get_session()
    try:
        # First check if the accessory exists
        accessory = db_session.query(Accessory).get(id)
        if not accessory:
            logger.error(f"Accessory {id} not found")
            return jsonify({'error': 'Accessory not found'}), 404

        logger.debug(f"Found accessory: {accessory.name}")
        
        # Get transactions
        transactions = db_session.query(AccessoryTransaction).filter(
            AccessoryTransaction.accessory_id == id
        ).order_by(AccessoryTransaction.transaction_date.desc()).all()
        
        logger.debug(f"Found {len(transactions)} transactions")
        
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
                logger.debug(f"Processed transaction: {t.transaction_number}")
            except Exception as e:
                logger.error(f"Error processing transaction {t.id}: {str(e)}")
                continue
        
        logger.debug(f"Successfully processed {len(transaction_list)} transactions")
        return jsonify(transaction_list)
    except Exception as e:
        logger.error(f"Error fetching transactions: {str(e)}")
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
                    'asset_name': t.asset.name if t.asset else None,
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
        logger.info("Error deleting transaction: {str(e)}")
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
        logger.info("Error deleting transaction: {str(e)}")
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
        
        # Filter by company for CLIENT users - can only see their company's assets
        if user.user_type == UserType.CLIENT and user.company:
            query = query.filter(
                or_(
                    Asset.company_id == user.company_id,
                    Asset.customer == user.company.name
                )
            )
            logger.info("DEBUG: Filtering maintenance assets for client user. Company ID: {user.company_id}, Company Name: {user.company.name}")
        
        # Filter by country if user is Country Admin or Supervisor
        if (user.user_type == UserType.COUNTRY_ADMIN or user.user_type == UserType.SUPERVISOR) and user.assigned_countries:
            query = query.filter(Asset.country.in_(user.assigned_countries))
        
        # Apply search if provided
        if search_term:
            search_term = f"%{search_term}%"
            query = query.filter(
                or_(
                    Asset.serial_num.ilike(search_term),
                    Asset.asset_tag.ilike(search_term),
                    Asset.name.ilike(search_term),
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
                customer = db_session.query(CustomerUser).filter_by(id=asset.customer_id).first()
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
                'customer': get_customer_display_name(db_session, asset.customer or customer_name),
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
        logger.error(f"Error retrieving maintenance assets: {str(e)}")
        return jsonify({'error': f"Error retrieving maintenance assets: {str(e)}"}), 500
    finally:
        db_session.close()

@inventory_bp.route('/bulk-update-erased', methods=['POST'])
@login_required
@admin_required
def bulk_update_erased():
    """API endpoint to bulk update the ERASED status of multiple assets"""
    db_session = db_manager.get_session()
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
        logger.error(f"Error updating assets: {str(e)}")
        return jsonify({'error': f"Error updating assets: {str(e)}"}), 500
    finally:
        db_session.close()

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

        # Store old value before updating
        old_erased_status = asset.erased

        # Update the asset
        asset.erased = erased_status

        # Track changes in asset history
        history_entry = asset.track_change(
            user_id=session.get('user_id'),
            action="UPDATE",
            changes={'erased': {'old': old_erased_status, 'new': erased_status}},
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
        logger.error(f"Error updating erase status: {str(e)}")
        return jsonify({'error': f"Error updating erase status: {str(e)}"}), 500
    finally:
        db_session.close()

# ===============================
# INVENTORY AUDIT FUNCTIONALITY
# ===============================

@inventory_bp.route('/audit')
@login_required
@permission_required('can_access_inventory_audit')
def audit_inventory():
    """Inventory audit main page"""
    user_id = session['user_id']
    db_session = db_manager.get_session()
    
    try:
        user = db_manager.get_user(user_id)
        if not user:
            flash('User not found')
            return redirect(url_for('auth.login'))
        
        # Get available countries from actual inventory data based on user permissions
        available_countries = []
        
        # Base query to get countries from assets
        country_query = db_session.query(Asset.country).distinct().filter(Asset.country.isnot(None), Asset.country != '')
        
        if user.user_type == UserType.SUPER_ADMIN:
            # Super admin can audit any country with assets
            countries_raw = country_query.all()
            available_countries = sorted([country[0] for country in countries_raw if country[0]])
        elif user.user_type == UserType.COUNTRY_ADMIN and user.assigned_countries:
            # Country admin can only audit their assigned country if it has assets
            country_assets = country_query.filter(func.lower(Asset.country) == func.lower(user.assigned_country)).first()
            if country_assets:
                available_countries = [user.assigned_country]
        elif user.user_type == UserType.SUPERVISOR:
            # Supervisors can audit all countries with assets
            countries_raw = country_query.all()
            available_countries = sorted([country[0] for country in countries_raw if country[0]])
        
        # Apply additional filtering for Country Admin based on company
        if user.user_type == UserType.COUNTRY_ADMIN and user.company_id:
            company_country_query = db_session.query(Asset.country).distinct().filter(
                Asset.country.isnot(None), 
                Asset.country != '',
                Asset.company_id == user.company_id
            )
            if user.assigned_countries:
                company_country_query = company_country_query.filter(func.lower(Asset.country) == func.lower(user.assigned_country))
            
            company_countries_raw = company_country_query.all()
            available_countries = sorted([country[0] for country in company_countries_raw if country[0]])
        
        # Debug logging
        logger.info(f"Available countries for audit: {available_countries}")
        total_assets_count = db_session.query(Asset).count()
        logger.info(f"Total assets in database: {total_assets_count}")
        
        return render_template('inventory/audit.html', 
                             user=user, 
                             available_countries=available_countries)
    
    except Exception as e:
        logger.error(f"Error loading audit page: {str(e)}")
        flash('Error loading audit page')
        return redirect(url_for('main.index'))
    finally:
        db_session.close()

@inventory_bp.route('/audit/start', methods=['POST'])
@login_required
@permission_required('can_start_inventory_audit')
def start_audit():
    """Start a new inventory audit session"""
    user_id = session['user_id']
    db_session = db_manager.get_session()
    
    try:
        user = db_manager.get_user(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Check permissions
        if user.user_type not in [UserType.SUPER_ADMIN, UserType.COUNTRY_ADMIN, UserType.SUPERVISOR]:
            return jsonify({'error': 'Permission denied'}), 403
        
        data = request.get_json()
        selected_country = data.get('country')
        
        if not selected_country:
            return jsonify({'error': 'Country is required'}), 400
        
        # Validate country permissions
        if user.user_type == UserType.COUNTRY_ADMIN and user.assigned_countries:
            if selected_country .notin_(user.assigned_countries):
                return jsonify({'error': 'You can only audit your assigned country'}), 403
        
        # Get inventory for the selected country (case-insensitive)
        inventory_query = db_session.query(Asset).filter(func.lower(Asset.country) == func.lower(selected_country))
        
        # Apply additional filtering for Country Admin
        if user.user_type == UserType.COUNTRY_ADMIN and user.company_id:
            inventory_query = inventory_query.filter(
                or_(Asset.company_id == user.company_id, Asset.company_id.is_(None))
            )
        
        inventory_assets = inventory_query.all()
        
        # Debug logging
        logger.info(f"Audit for country '{selected_country}': Found {len(inventory_assets)} assets")
        if len(inventory_assets) == 0:
            # Check what countries actually exist
            all_countries = db_session.query(Asset.country).distinct().filter(Asset.country.isnot(None)).all()
            logger.info(f"Available countries in database: {[c[0] for c in all_countries if c[0]]}")
            
            # Check if there are any assets at all
            total_assets = db_session.query(Asset).count()
            logger.info(f"Total assets in database: {total_assets}")
        
        # Create audit session data
        audit_session = {
            'country': selected_country,
            'total_assets': len(inventory_assets),
            'scanned_assets': [],
            'missing_assets': [],
            'unexpected_assets': [],
            'started_at': singapore_now_as_utc().isoformat(),
            'started_by': user_id
        }
        
        # Debug logging for session storage
        logger.info(f"About to store audit session with {len(inventory_assets)} assets")
        logger.info(f"User type: {user.user_type}, Company ID: {user.company_id}")
        
        # Don't start audit if no assets found
        if len(inventory_assets) == 0:
            return jsonify({'error': f'No assets found for country: {selected_country}. Cannot start audit.'}), 400
        
        # Create audit ID
        audit_id = f"audit_{int(time.time())}"
        
        # Prepare inventory data for database storage
        inventory_data = [
            {
                'id': asset.id,
                'asset_tag': asset.asset_tag,
                'serial_num': asset.serial_num,
                'name': asset.name,
                'model': asset.model,
                'status': asset.status.value if asset.status else 'Unknown',
                'location': asset.location.name if asset.location else 'Unknown'
            } for asset in inventory_assets
        ]
        
        # Create audit session in database
        audit_session_db = AuditSession(
            id=audit_id,
            country=selected_country,
            total_assets=len(inventory_assets),
            started_by=user_id,
            scanned_assets=json.dumps([]),
            missing_assets=json.dumps([]),
            unexpected_assets=json.dumps([]),
            audit_inventory=json.dumps(inventory_data)
        )
        
        db_session.add(audit_session_db)
        db_session.commit()
        
        # Store minimal session data (just the audit ID)
        session['current_audit_id'] = audit_id
        
        # Verify session was stored
        logger.info(f"Audit session created in database with ID: {audit_id}, Total assets: {len(inventory_assets)}")
        
        return jsonify({
            'success': True,
            'audit_id': audit_id,
            'country': selected_country,
            'total_assets': len(inventory_assets),
            'message': f'Audit started for {selected_country}. Found {len(inventory_assets)} assets to audit.'
        })
    
    except Exception as e:
        logger.error(f"Error starting audit: {str(e)}")
        return jsonify({'error': f'Error starting audit: {str(e)}'}), 500
    finally:
        db_session.close()

@inventory_bp.route('/audit/reports')
@login_required
@permission_required('can_view_audit_reports')
def view_audit_reports():
    """View all completed audit reports"""
    user_id = session['user_id']
    db_session = db_manager.get_session()
    
    try:
        user = db_manager.get_user(user_id)
        if not user:
            flash('User not found')
            return redirect(url_for('auth.login'))
        
        # Check permissions - only certain user types can view audit reports
        if user.user_type not in [UserType.SUPER_ADMIN, UserType.COUNTRY_ADMIN, UserType.SUPERVISOR]:
            flash('You do not have permission to view audit reports')
            return redirect(url_for('main.index'))
        
        # Get audit sessions based on user permissions
        query = db_session.query(AuditSession).filter(AuditSession.completed_at.isnot(None))
        
        if user.user_type == UserType.COUNTRY_ADMIN and user.assigned_countries:
            # Country admin can only see reports for their assigned country
            query = query.filter(func.lower(AuditSession.country) == func.lower(user.assigned_country))
        
        # Order by completion date, most recent first
        audit_reports = query.order_by(AuditSession.completed_at.desc()).all()
        
        # Parse JSON data for each report
        for report in audit_reports:
            try:
                report.scanned_assets_data = json.loads(report.scanned_assets) if report.scanned_assets else []
                report.missing_assets_data = json.loads(report.missing_assets) if report.missing_assets else []
                report.unexpected_assets_data = json.loads(report.unexpected_assets) if report.unexpected_assets else []
                
                # Calculate summary statistics
                report.total_scanned = len(report.scanned_assets_data)
                report.total_missing = len(report.missing_assets_data)
                report.total_unexpected = len(report.unexpected_assets_data)
                report.completion_percentage = round((report.total_scanned / report.total_assets * 100), 1) if report.total_assets > 0 else 0
            except (json.JSONDecodeError, TypeError):
                # Handle corrupted JSON data
                report.scanned_assets_data = []
                report.missing_assets_data = []
                report.unexpected_assets_data = []
                report.total_scanned = 0
                report.total_missing = 0
                report.total_unexpected = 0
                report.completion_percentage = 0
        
        return render_template('inventory/audit_reports_list.html', 
                             audit_reports=audit_reports,
                             user=user)
    
    except Exception as e:
        logger.error(f"Error loading audit reports: {str(e)}")
        flash('Error loading audit reports')
        return redirect(url_for('main.index'))
    finally:
        db_session.close()

@inventory_bp.route('/audit/reports/<audit_id>')
@login_required
@permission_required('can_view_audit_reports')
def view_audit_report_detail(audit_id):
    """View detailed audit report"""
    user_id = session['user_id']
    db_session = db_manager.get_session()
    
    try:
        user = db_manager.get_user(user_id)
        if not user:
            flash('User not found')
            return redirect(url_for('auth.login'))
        
        # Check permissions
        if user.user_type not in [UserType.SUPER_ADMIN, UserType.COUNTRY_ADMIN, UserType.SUPERVISOR]:
            flash('You do not have permission to view audit reports')
            return redirect(url_for('main.index'))
        
        # Get the specific audit session
        audit_session = db_session.query(AuditSession).filter(AuditSession.id == audit_id).first()
        
        if not audit_session:
            flash('Audit report not found')
            return redirect(url_for('inventory.view_audit_reports'))
        
        # Check if user has permission to view this specific report
        if user.user_type == UserType.COUNTRY_ADMIN and user.assigned_countries:
            if audit_session.country.lower() != user.assigned_country.lower():
                flash('You do not have permission to view this audit report')
                return redirect(url_for('inventory.view_audit_reports'))
        
        # Parse JSON data
        try:
            scanned_assets = json.loads(audit_session.scanned_assets) if audit_session.scanned_assets else []
            missing_assets = json.loads(audit_session.missing_assets) if audit_session.missing_assets else []
            unexpected_assets = json.loads(audit_session.unexpected_assets) if audit_session.unexpected_assets else []
            audit_inventory = json.loads(audit_session.audit_inventory) if audit_session.audit_inventory else []
        except (json.JSONDecodeError, TypeError):
            scanned_assets = []
            missing_assets = []
            unexpected_assets = []
            audit_inventory = []
        
        # Create report data structure
        report_data = {
            'audit_session': audit_session,
            'summary': {
                'total_expected': audit_session.total_assets,
                'total_scanned': len(scanned_assets),
                'total_missing': len(missing_assets),
                'total_unexpected': len(unexpected_assets),
                'completion_percentage': round((len(scanned_assets) / audit_session.total_assets * 100), 1) if audit_session.total_assets > 0 else 0
            },
            'scanned_assets': scanned_assets,
            'missing_assets': missing_assets,
            'unexpected_assets': unexpected_assets,
            'audit_inventory': audit_inventory
        }
        
        return render_template('inventory/audit_report_detail.html', 
                             report=report_data,
                             user=user)
    
    except Exception as e:
        logger.error(f"Error loading audit report detail: {str(e)}")
        flash('Error loading audit report')
        return redirect(url_for('inventory.view_audit_reports'))
    finally:
        db_session.close()

@inventory_bp.route('/audit/scan', methods=['POST'])
@login_required
def scan_asset():
    """Scan a single asset during audit"""
    user_id = session['user_id']
    db_session = db_manager.get_session()
    
    try:
        user = db_manager.get_user(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Check if audit session exists
        if 'current_audit_id' not in session:
            return jsonify({'error': 'No active audit session'}), 400
        
        # Get audit session from database
        audit_session_db = db_session.query(AuditSession).filter(
            AuditSession.id == session['current_audit_id'],
            AuditSession.is_active == True
        ).first()
        
        if not audit_session_db:
            return jsonify({'error': 'No active audit session'}), 400
        
        data = request.get_json()
        scanned_identifier = data.get('identifier', '').strip()
        
        if not scanned_identifier:
            return jsonify({'error': 'Asset identifier is required'}), 400
        
        # Parse JSON data from database
        audit_inventory = json.loads(audit_session_db.audit_inventory)
        scanned_assets = json.loads(audit_session_db.scanned_assets)
        
        # Look for the asset in the expected inventory
        found_asset = None
        for asset in audit_inventory:
            if (asset['asset_tag'] == scanned_identifier or 
                asset['serial_num'] == scanned_identifier):
                found_asset = asset
                break
        
        if found_asset:
            # Asset found in expected inventory
            if found_asset['id'] not in scanned_assets:
                scanned_assets.append(found_asset['id'])
                
                # Update database
                audit_session_db.scanned_assets = json.dumps(scanned_assets)
                db_session.commit()
                
                return jsonify({
                    'success': True,
                    'status': 'found',
                    'asset': found_asset,
                    'message': f'Asset {scanned_identifier} found and marked as present',
                    'scanned_count': len(scanned_assets),
                    'total_count': audit_session_db.total_assets
                })
            else:
                return jsonify({
                    'success': True,
                    'status': 'already_scanned',
                    'asset': found_asset,
                    'message': f'Asset {scanned_identifier} was already scanned',
                    'scanned_count': len(scanned_assets),
                    'total_count': audit_session_db.total_assets
                })
        else:
            # Asset not found in expected inventory - might be unexpected
            unexpected_asset = {
                'identifier': scanned_identifier,
                'scanned_at': singapore_now_as_utc().isoformat()
            }
            
            unexpected_assets = json.loads(audit_session_db.unexpected_assets)
            if unexpected_asset not in unexpected_assets:
                unexpected_assets.append(unexpected_asset)
                audit_session_db.unexpected_assets = json.dumps(unexpected_assets)
                db_session.commit()
            
            return jsonify({
                'success': True,
                'status': 'unexpected',
                'message': f'Asset {scanned_identifier} not expected in this location',
                'scanned_count': len(scanned_assets),
                'total_count': audit_session_db.total_assets,
                'unexpected_count': len(unexpected_assets)
            })
    
    except Exception as e:
        logger.error(f"Error scanning asset: {str(e)}")
        return jsonify({'error': f'Error scanning asset: {str(e)}'}), 500
    finally:
        db_session.close()

@inventory_bp.route('/audit/upload-csv', methods=['POST'])
@login_required
def upload_audit_csv():
    """Upload CSV file with scanned asset identifiers"""
    user_id = session['user_id']
    db_session = None
    
    try:
        db_session = db_manager.get_session()
        user = db_manager.get_user(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Check if audit session exists
        if 'current_audit_id' not in session:
            return jsonify({'error': 'No active audit session'}), 400
        
        # Get audit session from database
        audit_session_db = db_session.query(AuditSession).filter(
            AuditSession.id == session['current_audit_id'],
            AuditSession.is_active == True
        ).first()
        
        if not audit_session_db:
            return jsonify({'error': 'No active audit session'}), 400
        
        if 'file' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not file.filename.lower().endswith('.csv'):
            return jsonify({'error': 'File must be a CSV'}), 400
        
        # Read CSV content and normalize line endings
        content = file.read().decode('utf-8-sig')  # Handle BOM if present
        content = content.replace('\r\n', '\n').replace('\r', '\n')  # Normalize line endings
        csv_reader = csv.reader(StringIO(content), skipinitialspace=True)
        
        # Parse JSON data from database
        audit_inventory = json.loads(audit_session_db.audit_inventory)
        scanned_assets = json.loads(audit_session_db.scanned_assets)
        unexpected_assets = json.loads(audit_session_db.unexpected_assets)
        
        processed_count = 0
        found_count = 0
        unexpected_count = 0
        already_scanned_count = 0
        
        for row in csv_reader:
            if not row or not row[0].strip():
                continue
            
            scanned_identifier = row[0].strip()
            processed_count += 1
            
            # Look for the asset in the expected inventory
            found_asset = None
            for asset in audit_inventory:
                if (asset['asset_tag'] == scanned_identifier or 
                    asset['serial_num'] == scanned_identifier):
                    found_asset = asset
                    break
            
            if found_asset:
                if found_asset['id'] not in scanned_assets:
                    scanned_assets.append(found_asset['id'])
                    found_count += 1
                else:
                    already_scanned_count += 1
            else:
                # Unexpected asset
                unexpected_asset = {
                    'identifier': scanned_identifier,
                    'scanned_at': singapore_now_as_utc().isoformat()
                }
                
                if unexpected_asset not in unexpected_assets:
                    unexpected_assets.append(unexpected_asset)
                    unexpected_count += 1
        
        # Update database
        audit_session_db.scanned_assets = json.dumps(scanned_assets)
        audit_session_db.unexpected_assets = json.dumps(unexpected_assets)
        db_session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Processed {processed_count} entries from CSV',
            'summary': {
                'processed': processed_count,
                'found': found_count,
                'unexpected': unexpected_count,
                'already_scanned': already_scanned_count,
                'total_scanned': len(scanned_assets),
                'total_expected': audit_session_db.total_assets
            }
        })
    
    except Exception as e:
        logger.error(f"Error uploading audit CSV: {str(e)}")
        return jsonify({'error': f'Error processing CSV: {str(e)}'}), 500
    finally:
        if db_session:
            db_session.close()

@inventory_bp.route('/audit/status')
@login_required
def audit_status():
    """Get current audit status"""
    db_session = None
    try:
        if 'current_audit_id' not in session:
            return jsonify({'error': 'No active audit session'}), 400
        
        # Get audit session from database
        db_session = db_manager.get_session()
        audit_session_db = db_session.query(AuditSession).filter(
            AuditSession.id == session['current_audit_id'],
            AuditSession.is_active == True
        ).first()
        
        if not audit_session_db:
            return jsonify({'error': 'No active audit session'}), 400
        
        # Parse JSON data
        audit_inventory = json.loads(audit_session_db.audit_inventory)
        scanned_assets = json.loads(audit_session_db.scanned_assets)
        
        # Calculate missing assets
        scanned_asset_ids = set(scanned_assets)
        missing_assets = [asset for asset in audit_inventory if asset['id'] not in scanned_asset_ids]
        
        return jsonify({
            'success': True,
            'country': audit_session_db.country,
            'total_assets': audit_session_db.total_assets,
            'scanned_count': len(scanned_assets),
            'missing_count': len(missing_assets),
            'unexpected_count': len(json.loads(audit_session_db.unexpected_assets)),
            'completion_percentage': round((len(scanned_assets) / audit_session_db.total_assets * 100), 2) if audit_session_db.total_assets > 0 else 0,
            'started_at': audit_session_db.started_at.isoformat()
        })
    
    except Exception as e:
        logger.error(f"Error getting audit status: {str(e)}")
        return jsonify({'error': f'Error getting audit status: {str(e)}'}), 500
    finally:
        if db_session:
            db_session.close()

@inventory_bp.route('/audit/report')
@login_required
def generate_audit_report():
    """Generate final audit report"""
    db_session = None
    try:
        if 'current_audit_id' not in session:
            flash('No active audit session')
            return redirect(url_for('inventory.audit_inventory'))
        
        # Get audit session from database
        db_session = db_manager.get_session()
        audit_session_db = db_session.query(AuditSession).filter(
            AuditSession.id == session['current_audit_id'],
            AuditSession.is_active == True
        ).first()
        
        if not audit_session_db:
            flash('No active audit session')
            return redirect(url_for('inventory.audit_inventory'))
        
        # Parse JSON data
        audit_inventory = json.loads(audit_session_db.audit_inventory)
        scanned_assets = json.loads(audit_session_db.scanned_assets)
        unexpected_assets = json.loads(audit_session_db.unexpected_assets)
        
        # Calculate missing assets
        scanned_asset_ids = set(scanned_assets)
        missing_assets = [asset for asset in audit_inventory if asset['id'] not in scanned_asset_ids]
        
        # Prepare report data
        report_data = {
            'audit_session': {
                'country': audit_session_db.country,
                'total_assets': audit_session_db.total_assets,
                'started_at': audit_session_db.started_at.isoformat(),
                'started_by': audit_session_db.started_by
            },
            'missing_assets': missing_assets,
            'unexpected_assets': unexpected_assets,
            'scanned_assets': [asset for asset in audit_inventory if asset['id'] in scanned_asset_ids],
            'summary': {
                'total_expected': len(audit_inventory),
                'total_scanned': len(scanned_assets),
                'total_missing': len(missing_assets),
                'total_unexpected': len(unexpected_assets),
                'completion_percentage': round((len(scanned_assets) / len(audit_inventory) * 100), 2) if len(audit_inventory) > 0 else 0
            }
        }
        
        return render_template('inventory/audit_report.html', report=report_data)
    
    except Exception as e:
        logger.error(f"Error generating audit report: {str(e)}")
        flash('Error generating audit report')
        return redirect(url_for('inventory.audit_inventory'))
    finally:
        if db_session:
            db_session.close()

@inventory_bp.route('/audit/export-report')
@login_required
def export_audit_report():
    """Export audit report as CSV"""
    db_session = None
    try:
        if 'current_audit_id' not in session:
            return jsonify({'error': 'No active audit session'}), 400
        
        # Get audit session from database
        db_session = db_manager.get_session()
        audit_session_db = db_session.query(AuditSession).filter(
            AuditSession.id == session['current_audit_id'],
            AuditSession.is_active == True
        ).first()
        
        if not audit_session_db:
            return jsonify({'error': 'No active audit session'}), 400
        
        # Parse JSON data
        audit_inventory = json.loads(audit_session_db.audit_inventory)
        scanned_assets = json.loads(audit_session_db.scanned_assets)
        
        # Calculate missing assets
        scanned_asset_ids = set(scanned_assets)
        missing_assets = [asset for asset in audit_inventory if asset['id'] not in scanned_asset_ids]
        
        # Create CSV content
        output = StringIO()
        writer = csv.writer(output)
        
        # Parse unexpected assets
        unexpected_assets = json.loads(audit_session_db.unexpected_assets)
        
        # Write header
        writer.writerow(['Audit Report - Generated at', singapore_now_as_utc().strftime('%Y-%m-%d %H:%M:%S')])
        writer.writerow(['Country', audit_session_db.country])
        writer.writerow(['Started at', audit_session_db.started_at.isoformat()])
        writer.writerow([])
        
        # Summary
        writer.writerow(['SUMMARY'])
        writer.writerow(['Total Expected Assets', len(audit_inventory)])
        writer.writerow(['Assets Scanned', len(scanned_assets)])
        writer.writerow(['Missing Assets', len(missing_assets)])
        writer.writerow(['Unexpected Assets', len(unexpected_assets)])
        writer.writerow([])
        
        # Missing assets
        writer.writerow(['MISSING ASSETS'])
        writer.writerow(['Asset Tag', 'Serial Number', 'Name', 'Model', 'Status', 'Location'])
        for asset in missing_assets:
            writer.writerow([
                asset['asset_tag'],
                asset['serial_num'],
                asset['name'],
                asset['model'],
                asset['status'],
                asset['location']
            ])
        writer.writerow([])
        
        # Unexpected assets
        writer.writerow(['UNEXPECTED ASSETS'])
        writer.writerow(['Identifier', 'Scanned At'])
        for unexpected in unexpected_assets:
            writer.writerow([
                unexpected['identifier'],
                unexpected['scanned_at']
            ])
        
        # Create response
        output.seek(0)
        filename = f"audit_report_{audit_session_db.country}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
        
        return Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={'Content-Disposition': f'attachment; filename={filename}'}
        )
    
    except Exception as e:
        logger.error(f"Error exporting audit report: {str(e)}")
        return jsonify({'error': f'Error exporting report: {str(e)}'}), 500
    finally:
        if db_session:
            db_session.close()

@inventory_bp.route('/audit/clear')
@login_required  
def clear_audit_session():
    """Clear current audit session"""
    db_session = None
    try:
        if 'current_audit_id' in session:
            # Mark audit session as inactive in database
            db_session = db_manager.get_session()
            audit_session_db = db_session.query(AuditSession).filter(
                AuditSession.id == session['current_audit_id']
            ).first()
            
            if audit_session_db:
                audit_session_db.is_active = False
                audit_session_db.completed_at = datetime.utcnow()
                db_session.commit()
            
            del session['current_audit_id']
        
        return jsonify({'success': True, 'message': 'Audit session cleared'})
    
    except Exception as e:
        logger.error(f"Error clearing audit session: {str(e)}")
        return jsonify({'error': f'Error clearing session: {str(e)}'}), 500
    finally:
        if db_session:
            db_session.close()

@inventory_bp.route('/audit/end', methods=['POST'])
@login_required
def end_audit():
    """End the current audit and prepare for remediation"""
    db_session = None
    try:
        if 'current_audit_id' not in session:
            return jsonify({'error': 'No active audit session'}), 400
        
        # Get audit session from database
        db_session = db_manager.get_session()
        audit_session_db = db_session.query(AuditSession).filter(
            AuditSession.id == session['current_audit_id'],
            AuditSession.is_active == True
        ).first()
        
        if not audit_session_db:
            return jsonify({'error': 'No active audit session'}), 400
        
        # Mark audit as completed
        audit_session_db.is_active = False
        audit_session_db.completed_at = datetime.utcnow()
        db_session.commit()
        
        # Keep the audit ID in session for remediation page
        audit_id = session['current_audit_id']
        
        logger.info(f"Audit {audit_id} ended successfully")
        
        return jsonify({
            'success': True,
            'audit_id': audit_id,
            'message': 'Audit ended successfully'
        })
        
    except Exception as e:
        logger.error(f"Error ending audit: {str(e)}")
        return jsonify({'error': f'Error ending audit: {str(e)}'}), 500
    finally:
        if db_session:
            db_session.close()

@inventory_bp.route('/audit/details/<detail_type>')
@login_required
def get_audit_details(detail_type):
    """Get detailed asset lists for audit categories"""
    db_session = None
    try:
        if 'current_audit_id' not in session:
            return jsonify({'error': 'No active audit session'}), 400
        
        # Get audit session from database
        db_session = db_manager.get_session()
        audit_session_db = db_session.query(AuditSession).filter(
            AuditSession.id == session['current_audit_id'],
            AuditSession.is_active == True
        ).first()
        
        if not audit_session_db:
            return jsonify({'error': 'No active audit session'}), 400
        
        # Parse JSON data from database
        audit_inventory = json.loads(audit_session_db.audit_inventory)
        scanned_assets = json.loads(audit_session_db.scanned_assets)
        unexpected_assets = json.loads(audit_session_db.unexpected_assets)
        
        if detail_type == 'total':
            return jsonify({
                'success': True,
                'title': f'All Assets ({len(audit_inventory)})',
                'assets': audit_inventory
            })
        elif detail_type == 'scanned':
            scanned_asset_list = [asset for asset in audit_inventory if asset['id'] in scanned_assets]
            return jsonify({
                'success': True,
                'title': f'Scanned Assets ({len(scanned_asset_list)})',
                'assets': scanned_asset_list
            })
        elif detail_type == 'missing':
            missing_asset_list = [asset for asset in audit_inventory if asset['id'] not in scanned_assets]
            return jsonify({
                'success': True,
                'title': f'Missing Assets ({len(missing_asset_list)})',
                'assets': missing_asset_list
            })
        elif detail_type == 'unexpected':
            return jsonify({
                'success': True,
                'title': f'Unexpected Assets ({len(unexpected_assets)})',
                'assets': unexpected_assets
            })
        else:
            return jsonify({'error': 'Invalid detail type'}), 400
            
    except Exception as e:
        logger.error(f"Error getting audit details: {str(e)}")
        return jsonify({'error': f'Error getting audit details: {str(e)}'}), 500
    finally:
        if db_session:
            db_session.close()

@inventory_bp.route('/audit/remediation/<audit_id>')
@login_required
def audit_remediation(audit_id):
    """Audit remediation page for handling missing assets"""
    db_session = None
    try:
        db_session = db_manager.get_session()
        
        # Get the completed audit session
        audit_session_db = db_session.query(AuditSession).filter(
            AuditSession.id == audit_id,
            AuditSession.is_active == False
        ).first()
        
        if not audit_session_db:
            flash('Audit session not found or still active')
            return redirect(url_for('inventory.audit_inventory'))
        
        # Parse audit data
        audit_inventory = json.loads(audit_session_db.audit_inventory)
        scanned_assets = json.loads(audit_session_db.scanned_assets)
        unexpected_assets = json.loads(audit_session_db.unexpected_assets)
        
        # Calculate missing assets
        missing_assets = [asset for asset in audit_inventory if asset['id'] not in scanned_assets]
        scanned_asset_list = [asset for asset in audit_inventory if asset['id'] in scanned_assets]
        
        # Get customers for dropdown
        customers = db_session.query(CustomerUser).all()
        logger.info(f"Found {len(customers)} customers for dropdown")
        
        # Get companies for dropdown
        companies = db_session.query(Company).all()
        
        # Prepare audit summary
        audit_summary = {
            'audit_id': audit_id,
            'country': audit_session_db.country,
            'started_at': audit_session_db.started_at,
            'completed_at': audit_session_db.completed_at,
            'total_assets': audit_session_db.total_assets,
            'scanned_count': len(scanned_assets),
            'missing_count': len(missing_assets),
            'unexpected_count': len(unexpected_assets)
        }
        
        return render_template('inventory/audit_remediation.html',
                             audit_summary=audit_summary,
                             missing_assets=missing_assets,
                             scanned_assets=scanned_asset_list,
                             unexpected_assets=unexpected_assets,
                             customers=customers,
                             companies=companies)
        
    except Exception as e:
        logger.error(f"Error loading audit remediation: {str(e)}")
        flash('Error loading audit remediation page')
        return redirect(url_for('inventory.audit_inventory'))
    finally:
        if db_session:
            db_session.close()

@inventory_bp.route('/audit/mark-found', methods=['POST'])
@login_required
def mark_asset_found():
    """Mark a missing asset as found during remediation"""
    db_session = None
    try:
        data = request.get_json()
        asset_id = data.get('asset_id')
        
        if not asset_id:
            return jsonify({'error': 'Asset ID is required'}), 400
        
        db_session = db_manager.get_session()
        
        # Get the asset
        asset = db_session.query(Asset).filter(Asset.id == asset_id).first()
        if not asset:
            return jsonify({'error': 'Asset not found'}), 404
        
        # Update asset status to indicate it was found during remediation
        asset.status = AssetStatus.AVAILABLE
        
        # Create activity log
        activity = Activity(
            asset_id=asset_id,
            action='AUDIT_FOUND',
            details=f'Asset marked as found during audit remediation',
            performed_by=session['user_id'],
            timestamp=datetime.utcnow()
        )
        db_session.add(activity)
        
        db_session.commit()
        
        logger.info(f"Asset {asset_id} marked as found during audit remediation")
        
        return jsonify({
            'success': True,
            'message': 'Asset marked as found successfully'
        })
        
    except Exception as e:
        if db_session:
            db_session.rollback()
        logger.error(f"Error marking asset as found: {str(e)}")
        return jsonify({'error': f'Error marking asset as found: {str(e)}'}), 500
    finally:
        if db_session:
            db_session.close()

@inventory_bp.route('/audit/ship-out', methods=['POST'])
@login_required
def ship_out_asset():
    """Create checkout case for missing asset that was shipped out"""
    db_session = None
    try:
        data = request.get_json()
        asset_id = data.get('asset_id')
        customer_id = data.get('customer_id')
        notes = data.get('notes', '')
        
        if not asset_id:
            return jsonify({'error': 'Asset ID is required'}), 400
        
        if not customer_id:
            return jsonify({'error': 'Customer is required'}), 400
        
        db_session = db_manager.get_session()
        
        # Get the asset
        asset = db_session.query(Asset).filter(Asset.id == asset_id).first()
        if not asset:
            return jsonify({'error': 'Asset not found'}), 404
        
        # Get customer info
        customer = db_session.query(CustomerUser).filter(CustomerUser.id == customer_id).first()
        if not customer:
            return jsonify({'error': 'Customer not found'}), 404
        
        # Create a checkout case/ticket
        from models.ticket import Ticket, TicketStatus, TicketPriority, TicketCategory
        
        case_title = f"Asset Checkout - {asset.asset_tag or asset.serial_num}"
        case_description = f"""Asset checkout case created during audit remediation.

Asset Details:
- Asset Tag: {asset.asset_tag or 'N/A'}
- Serial Number: {asset.serial_num or 'N/A'}
- Name: {asset.name or 'N/A'}
- Model: {asset.model or 'N/A'}

Customer: {customer.name} ({customer.company.name if customer.company else 'No Company'})
Notes: {notes}

This asset was identified as missing during audit but has been shipped out to the customer."""
        
        ticket = Ticket(
            subject=case_title,
            description=case_description,
            status=TicketStatus.NEW,
            priority=TicketPriority.MEDIUM,
            category=TicketCategory.ASSET_CHECKOUT,
            customer_id=customer_id,
            asset_id=asset_id,
            requester_id=session['user_id'],
            created_at=datetime.utcnow()
        )
        db_session.add(ticket)
        db_session.flush()
        
        # Safely assign asset to ticket using the proper function
        from routes.admin import safely_assign_asset_to_ticket
        safely_assign_asset_to_ticket(ticket, asset, db_session)
        

        
        # Update asset status and assign to customer
        asset.status = AssetStatus.DEPLOYED
        asset.customer_id = customer_id
        
        # Create activity log
        activity = Activity(
            user_id=session['user_id'],
            type='asset_shipped',
            content=f'Asset marked as shipped out during audit remediation to {customer.name} ({customer.company.name if customer.company else "No Company"}). Case #{ticket.id} created.',
            reference_id=asset_id
        )
        db_session.add(activity)
        
        db_session.commit()
        
        logger.info(f"Asset {asset_id} marked as shipped out during audit remediation. Case #{ticket.id} created.")
        
        # Get display name for customer
        customer_display = f"{customer.name}"
        if customer.company:
            customer_display += f" ({customer.company.name})"
        
        return jsonify({
            'success': True,
            'case_id': ticket.id,
            'customer_name': customer_display,
            'message': 'Checkout case created successfully'
        })
        
    except Exception as e:
        if db_session:
            db_session.rollback()
        logger.error(f"Error creating ship out case: {str(e)}")
        return jsonify({'error': f'Error creating checkout case: {str(e)}'}), 500
    finally:
        if db_session:
            db_session.close()

@inventory_bp.route('/customers/create', methods=['POST'])
@login_required
def create_customer():
    """Create a new customer"""
    db_session = None
    try:
        data = request.get_json()
        
        name = data.get('name', '').strip()
        contact_number = data.get('contact_number', '').strip()
        email = data.get('email', '').strip()
        company_id = data.get('company_id')
        country = data.get('country', '').strip()
        address = data.get('address', '').strip()
        
        if not name or not contact_number or not country or not address:
            return jsonify({'error': 'Name, contact number, country, and address are required'}), 400

        db_session = db_manager.get_session()

        # Check if customer with the same name already exists
        existing_customer = db_session.query(CustomerUser).filter(
            CustomerUser.name.ilike(name)
        ).first()

        if existing_customer:
            return jsonify({
                'error': f'A customer with the name "{existing_customer.name}" already exists',
                'existing_customer': {
                    'id': existing_customer.id,
                    'name': existing_customer.name,
                    'company': existing_customer.company.name if existing_customer.company else None
                }
            }), 409

        # Convert country string to enum if it exists, otherwise use as string
        from models.enums import Country
        try:
            country_enum = Country(country.upper())
            country_value = country_enum
        except (ValueError, AttributeError):
            # If country is not in enum, use it as a custom string value
            country_value = country.upper()

        # Create new customer
        customer = CustomerUser(
            name=name,
            contact_number=contact_number,
            email=email,
            address=address,
            company_id=company_id,
            country=country_value,
            created_at=datetime.utcnow()
        )
        
        db_session.add(customer)
        db_session.commit()
        
        logger.info(f"New customer created: {customer.name} (ID: {customer.id})")
        
        return jsonify({
            'success': True,
            'customer': {
                'id': customer.id,
                'name': customer.name,
                'contact_number': customer.contact_number,
                'email': customer.email,
                'country': customer.country.value if hasattr(customer.country, 'value') else customer.country,
                'address': customer.address,
                'company': customer.company.name if customer.company else None
            },
            'message': 'Customer created successfully'
        })
        
    except Exception as e:
        if db_session:
            db_session.rollback()
        logger.error(f"Error creating customer: {str(e)}")
        return jsonify({'error': f'Error creating customer: {str(e)}'}), 500
    finally:
        if db_session:
            db_session.close()

@inventory_bp.route('/audit/debug')
@login_required
def debug_audit_data():
    """Debug route to check audit data"""
    user_id = session['user_id']
    db_session = db_manager.get_session()
    
    try:
        user = db_manager.get_user(user_id)
        
        # Get total assets count
        total_assets = db_session.query(Asset).count()
        
        # Get all countries
        all_countries = db_session.query(Asset.country).distinct().filter(Asset.country.isnot(None)).all()
        countries_list = [c[0] for c in all_countries if c[0]]
        
        # Get assets by country
        country_counts = {}
        for country in countries_list:
            count = db_session.query(Asset).filter(func.lower(Asset.country) == func.lower(country)).count()
            country_counts[country] = count
        
        # Check user permissions
        user_info = {
            'user_type': user.user_type.value if user.user_type else None,
            'assigned_country': user.assigned_country if user.assigned_country else None,
            'company_id': user.company_id
        }
        
        return jsonify({
            'success': True,
            'total_assets': total_assets,
            'countries': countries_list,
            'country_counts': country_counts,
            'user_info': user_info
        })
    
    except Exception as e:
        return jsonify({'error': f'Debug error: {str(e)}'}), 500
    finally:
        db_session.close()


@inventory_bp.route('/api/assets/<int:asset_id>/service-records', methods=['GET'])
@login_required
def get_asset_service_records(asset_id):
    """Get all service records for an asset"""
    from database import SessionLocal
    from models.service_record import ServiceRecord

    db_session = SessionLocal()
    try:
        asset = db_session.query(Asset).get(asset_id)
        if not asset:
            return jsonify({'success': False, 'error': 'Asset not found'}), 404

        records = db_session.query(ServiceRecord).filter(
            ServiceRecord.asset_id == asset_id
        ).order_by(ServiceRecord.performed_at.desc()).all()

        return jsonify({
            'success': True,
            'service_records': [r.to_dict() for r in records]
        })

    except Exception as e:
        import logging
        logging.error(f"Error getting asset service records: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db_session.close()
