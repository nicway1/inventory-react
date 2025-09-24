from flask import Blueprint, render_template, jsonify, request
from flask_login import login_required, current_user
from utils.auth_decorators import permission_required

# CSRF exemption will be handled at the app level for API routes
from sqlalchemy import func, extract, and_, or_, case
from datetime import datetime, timedelta
import json
import logging
from database import SessionLocal
from models import (
    Ticket, Asset, AssetTransaction, AccessoryTransaction,
    User, Company, CustomerUser, TicketStatus, TicketPriority,
    TicketCategory
)

# Set up logging for this module
logger = logging.getLogger(__name__)
from models.asset import AssetStatus

reports_bp = Blueprint('reports', __name__, url_prefix='/reports')

@reports_bp.route('/')
@login_required
@permission_required('can_view_reports')
def index():
    """Reports dashboard"""
    return render_template('reports/index.html')

@reports_bp.route('/cases')
@login_required
@permission_required('can_view_reports')
def case_reports():
    """Case/Ticket reports with various visualizations"""
    # Get date range from request
    days = request.args.get('days', 30, type=int)
    start_date = datetime.utcnow() - timedelta(days=days)
    
    # Get database session
    db = SessionLocal()
    try:
        # Query tickets based on user permissions
        query = db.query(Ticket)
        
        # Apply permission filters
        if current_user.user_type.value == 'COUNTRY_ADMIN':
            # Country admins see tickets from their country
            query = query.join(CustomerUser).filter(CustomerUser.country == current_user.country)
        elif current_user.user_type.value == 'CLIENT':
            # Clients see only their tickets
            query = query.filter(Ticket.requester_id == current_user.id)
        
        # Get all tickets for the period
        tickets = query.filter(Ticket.created_at >= start_date).all()
        
        # Prepare data for charts
        # 1. Tickets by Status (Pie Chart)
        status_counts = {}
        for ticket in tickets:
            status_name = ticket.status.value if ticket.status else 'No Status'
            status_counts[status_name] = status_counts.get(status_name, 0) + 1
        
        # 2. Tickets by Priority (Donut Chart)
        priority_counts = {}
        for ticket in tickets:
            priority_name = ticket.priority.value if ticket.priority else 'No Priority'
            priority_counts[priority_name] = priority_counts.get(priority_name, 0) + 1
        
        # 3. Tickets by Category (Bar Chart)
        category_counts = {}
        for ticket in tickets:
            category_name = ticket.get_category_display_name() if ticket.category else 'No Category'
            category_counts[category_name] = category_counts.get(category_name, 0) + 1
        
        # 4. Tickets over Time (Line Chart)
        tickets_by_date = {}
        for ticket in tickets:
            date_str = ticket.created_at.strftime('%Y-%m-%d')
            tickets_by_date[date_str] = tickets_by_date.get(date_str, 0) + 1
        
        # Sort dates and fill missing dates
        all_dates = []
        current_date = start_date.date()
        end_date = datetime.utcnow().date()
        while current_date <= end_date:
            date_str = current_date.strftime('%Y-%m-%d')
            all_dates.append({
                'date': date_str,
                'count': tickets_by_date.get(date_str, 0)
            })
            current_date += timedelta(days=1)
        
        # 5. Average Resolution Time by Category
        resolution_times = {}
        resolved_counts = {}
        for ticket in tickets:
            if ticket.status and ticket.status.name in ['RESOLVED', 'RESOLVED_DELIVERED']:
                category_name = ticket.get_category_display_name() if ticket.category else 'No Category'
                # Calculate resolution time in hours
                resolution_time = (ticket.updated_at - ticket.created_at).total_seconds() / 3600
                if category_name not in resolution_times:
                    resolution_times[category_name] = 0
                    resolved_counts[category_name] = 0
                resolution_times[category_name] += resolution_time
                resolved_counts[category_name] += 1
        
        avg_resolution_times = {}
        for category, total_time in resolution_times.items():
            avg_resolution_times[category] = round(total_time / resolved_counts[category], 2)
        
        # 6. Top Customers by Ticket Count
        customer_counts = {}
        for ticket in tickets:
            if ticket.customer and hasattr(ticket.customer, 'name'):
                customer_name = ticket.customer.name
                customer_counts[customer_name] = customer_counts.get(customer_name, 0) + 1
        
        # Sort and get top 10
        top_customers = sorted(customer_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        
        # 7. Summary Statistics
        total_tickets = len(tickets)
        open_tickets = len([t for t in tickets if t.status and t.status.name not in ['RESOLVED', 'RESOLVED_DELIVERED']])
        resolved_tickets = total_tickets - open_tickets
        resolution_rate = (resolved_tickets / total_tickets * 100) if total_tickets > 0 else 0
        
        high_priority = len([t for t in tickets if t.priority and t.priority.name == 'HIGH'])
        critical_priority = len([t for t in tickets if t.priority and t.priority.name == 'CRITICAL'])
        
        return render_template('reports/case_reports.html',
            status_data=json.dumps(status_counts),
            priority_data=json.dumps(priority_counts),
            category_data=json.dumps(category_counts),
            timeline_data=json.dumps(all_dates),
            resolution_data=json.dumps(avg_resolution_times),
            top_customers=json.dumps(top_customers),
            stats={
                'total': total_tickets,
                'open': open_tickets,
                'resolved': resolved_tickets,
                'resolution_rate': round(resolution_rate, 1),
                'high_priority': high_priority,
                'critical_priority': critical_priority
            },
            days=days
        )
    finally:
        db.close()

@reports_bp.route('/assets')
@login_required
@permission_required('can_view_reports')
def asset_reports():
    """Asset reports with various visualizations"""
    # Get database session
    db = SessionLocal()
    try:
        # Query assets based on user permissions
        query = db.query(Asset)
        
        # Apply permission filters
        if current_user.user_type.value == 'COUNTRY_ADMIN':
            # Country admins see assets from their country
            query = query.filter(Asset.country == current_user.country)
        elif current_user.user_type.value == 'CLIENT':
            # Clients see only assets assigned to them
            query = query.filter(Asset.customer_id == current_user.id)
        
        assets = query.all()
        
        # 1. Assets by Status (Pie Chart)
        status_counts = {}
        for asset in assets:
            status_name = asset.status.value if asset.status else 'No Status'
            status_counts[status_name] = status_counts.get(status_name, 0) + 1
        
        # 2. Assets by Type (Bar Chart)
        type_counts = {}
        for asset in assets:
            # Normalize asset type to avoid duplicates like "Apple" and "APPLE"
            raw_type = (asset.asset_type or 'Unknown').strip()
            asset_type = raw_type.title()  # Convert to Title Case (e.g., "apple" -> "Apple")
            
            # Special handling for PC types to display as "Windows (PC)"
            if asset_type.lower() == 'pc':
                asset_type = 'Windows (PC)'
            elif asset_type.lower() == 'desktop pc':
                asset_type = 'Windows (PC)'
            
            type_counts[asset_type] = type_counts.get(asset_type, 0) + 1
        
        # 3. Assets by Model (Horizontal Bar Chart - Top 10)
        model_counts = {}
        for asset in assets:
            # Handle model field more robustly
            if asset.model is None:
                model = 'Unknown Model'
            elif isinstance(asset.model, str) and asset.model.strip() == '':
                model = 'Unknown Model'
            else:
                model = str(asset.model).strip()
                # If it's still empty after stripping, mark as unknown
                if not model:
                    model = 'Unknown Model'
            
            model_counts[model] = model_counts.get(model, 0) + 1
        
        # Sort and get top 10
        top_models = sorted(model_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        
        # 4. Assets by Country (Map or Bar Chart)
        country_counts = {}
        for asset in assets:
            country = asset.country or 'Unknown'
            country_counts[country] = country_counts.get(country, 0) + 1
        
        # 5. Asset Age Distribution (Histogram)
        age_distribution = {
            '0-6 months': 0,
            '6-12 months': 0,
            '1-2 years': 0,
            '2-3 years': 0,
            '3+ years': 0
        }
        
        current_date = datetime.utcnow()
        for asset in assets:
            if asset.receiving_date:
                age_days = (current_date - asset.receiving_date).days
                if age_days <= 180:
                    age_distribution['0-6 months'] += 1
                elif age_days <= 365:
                    age_distribution['6-12 months'] += 1
                elif age_days <= 730:
                    age_distribution['1-2 years'] += 1
                elif age_days <= 1095:
                    age_distribution['2-3 years'] += 1
                else:
                    age_distribution['3+ years'] += 1
        
        # 6. Assets by Customer (Top 10)
        customer_counts = {}
        for asset in assets:
            customer_name = None
            if asset.customer_user:
                # Use the relationship to CustomerUser
                customer_name = asset.customer_user.name
            elif asset.customer:
                # Use the string field if customer_user relationship is not set
                customer_name = asset.customer
            
            if customer_name:
                customer_counts[customer_name] = customer_counts.get(customer_name, 0) + 1
        
        top_asset_customers = sorted(customer_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        
        # 7. Asset Transaction History (Dynamic time range)
        # Try last 30 days first, then 90 days, then all transactions
        time_periods = [30, 90, None]  # None means all transactions
        transaction_period = "Last 30 days"
        transactions = []
        
        for days in time_periods:
            if days:
                cutoff_date = datetime.utcnow() - timedelta(days=days)
                transactions = db.query(AssetTransaction).filter(
                    AssetTransaction.transaction_date >= cutoff_date
                ).all()
                if days == 30:
                    transaction_period = "Last 30 days"
                elif days == 90:
                    transaction_period = "Last 90 days"
            else:
                # Get all transactions
                transactions = db.query(AssetTransaction).all()
                transaction_period = "All time"
            
            # If we found transactions, break out of the loop
            if transactions:
                break
        
        transaction_counts = {}
        for transaction in transactions:
            date_str = transaction.transaction_date.strftime('%Y-%m-%d')
            transaction_counts[date_str] = transaction_counts.get(date_str, 0) + 1
        
        # 8. Summary Statistics
        total_assets = len(assets)
        active_assets = len([a for a in assets if a.status and a.status == AssetStatus.READY_TO_DEPLOY])
        deployed_assets = len([a for a in assets if a.status and a.status == AssetStatus.DEPLOYED])
        # Maintenance uses the same logic as inventory Maintenance tab (assets where ERASED is not COMPLETED)
        maintenance = len([a for a in assets if not a.erased or a.erased.strip() == '' or a.erased.lower() != 'completed'])
        
        # Calculate asset utilization rate
        utilization_rate = ((active_assets + deployed_assets) / total_assets * 100) if total_assets > 0 else 0
        
        return render_template('reports/asset_reports.html',
            status_data=json.dumps(status_counts),
            type_data=json.dumps(type_counts),
            model_data=json.dumps(dict(top_models)),
            country_data=json.dumps(country_counts),
            age_data=json.dumps(age_distribution),
            customer_data=json.dumps(top_asset_customers),
            transaction_data=json.dumps(transaction_counts),
            stats={
                'total': total_assets,
                'active': active_assets,
                'deployed': deployed_assets,
                'maintenance': maintenance,
                'utilization_rate': round(utilization_rate, 1),
                'transaction_period': transaction_period,
                'total_transactions': len(transactions)
            }
        )
    finally:
        db.close()

# Removed unused export route - now using client-side CSV generation

@reports_bp.route('/assets/by-model/<model_name>')
@login_required
@permission_required('can_view_reports')
def assets_by_model(model_name):
    """View all assets for a specific model"""
    # Get database session
    db = SessionLocal()
    try:
        # Handle "Unknown Model" case
        if model_name == 'Unknown Model':
            # Get all assets first, then filter using the same logic as the main chart
            all_assets = db.query(Asset)
            
            # Apply permission filters first
            if current_user.user_type.value == 'COUNTRY_ADMIN':
                all_assets = all_assets.filter(Asset.country == current_user.country)
            elif current_user.user_type.value == 'CLIENT':
                all_assets = all_assets.filter(Asset.customer_id == current_user.id)
            
            # Get all assets and filter using the same logic as the main chart
            all_assets_list = all_assets.all()
            assets = []
            
            for asset in all_assets_list:
                # Use the EXACT same logic as the main chart
                if asset.model is None:
                    model = 'Unknown Model'
                elif isinstance(asset.model, str) and asset.model.strip() == '':
                    model = 'Unknown Model'
                else:
                    model = str(asset.model).strip()
                    # If it's still empty after stripping, mark as unknown
                    if not model:
                        model = 'Unknown Model'
                
                # If this asset would be classified as Unknown Model, include it
                if model == 'Unknown Model':
                    assets.append(asset)
            
            # Skip the normal query since we already have our filtered assets
            query = None
        else:
            # Query assets with the specific model (exact match after stripping)
            query = db.query(Asset).filter(Asset.model == model_name)
            
            # Apply permission filters
            if current_user.user_type.value == 'COUNTRY_ADMIN':
                # Country admins see assets from their country
                query = query.filter(Asset.country == current_user.country)
            elif current_user.user_type.value == 'CLIENT':
                # Clients see only assets assigned to them
                query = query.filter(Asset.customer_id == current_user.id)
            
            assets = query.all()
        
        # Group assets by status for display
        status_groups = {}
        for asset in assets:
            status_name = asset.status.value if asset.status else 'No Status'
            if status_name not in status_groups:
                status_groups[status_name] = []
            status_groups[status_name].append(asset)
        
        return render_template('reports/assets_by_model.html',
            model_name=model_name,
            assets=assets,
            status_groups=status_groups,
            total_count=len(assets)
        )
    finally:
        db.close()

@reports_bp.route('/debug/unknown-models')
@login_required
@permission_required('can_view_reports')
def debug_unknown_models():
    """Debug route to investigate Unknown Model assets"""
    # Get database session
    db = SessionLocal()
    try:
        # Use the EXACT same logic as the main chart and assets_by_model route
        query = db.query(Asset)

        # Apply permission filters
        if current_user.user_type.value == 'COUNTRY_ADMIN':
            query = query.filter(Asset.country == current_user.country)
        elif current_user.user_type.value == 'CLIENT':
            query = query.filter(Asset.customer_id == current_user.id)

        # Get all assets and filter using the same logic as the main chart
        all_assets = query.all()
        unknown_model_assets = []

        for asset in all_assets:
            # Use the EXACT same logic as the main chart
            if asset.model is None:
                model = 'Unknown Model'
            elif isinstance(asset.model, str) and asset.model.strip() == '':
                model = 'Unknown Model'
            else:
                model = str(asset.model).strip()
                # If it's still empty after stripping, mark as unknown
                if not model:
                    model = 'Unknown Model'

            # If this asset would be classified as Unknown Model, include it
            if model == 'Unknown Model':
                unknown_model_assets.append(asset)

        # Show first 50 for debugging, but report the actual total
        debug_info = []
        sample_assets = unknown_model_assets[:50]  # First 50 for debugging

        for asset in sample_assets:
            debug_info.append({
                'id': asset.id,
                'asset_tag': asset.asset_tag,
                'serial_num': asset.serial_num,
                'model': asset.model,
                'model_repr': repr(asset.model),
                'model_type': type(asset.model).__name__,
                'model_length': len(asset.model) if asset.model else 0,
                'name': asset.name,
                'asset_type': asset.asset_type
            })

        return jsonify({
            'total_unknown_models': len(unknown_model_assets),
            'sample_assets': debug_info,
            'message': f'Found {len(unknown_model_assets)} assets with Unknown Model (showing first {len(sample_assets)} for debugging)'
        })
    finally:
        db.close()

# New API endpoints for dynamic report builder

@reports_bp.route('/builder')
@login_required
@permission_required('can_view_reports')
def case_reports_builder():
    """Advanced case reports builder with dynamic filtering"""
    return render_template('reports/case_reports_builder.html')

@reports_bp.route('/api/filters')
@login_required
@permission_required('can_view_reports')
def get_available_filters():
    """Get all available filter options with counts"""
    db = SessionLocal()
    try:
        # Base query with permissions
        query = db.query(Ticket)

        # Apply permission filters more safely
        try:
            if hasattr(current_user, 'user_type') and current_user.user_type:
                if current_user.user_type.value == 'COUNTRY_ADMIN':
                    # Only join CustomerUser if we need country filtering
                    query = query.outerjoin(CustomerUser, Ticket.customer_id == CustomerUser.id)
                    if hasattr(current_user, 'country') and current_user.country:
                        query = query.filter(CustomerUser.country == current_user.country)
                elif current_user.user_type.value == 'CLIENT':
                    query = query.filter(Ticket.requester_id == current_user.id)
        except Exception as e:
            logger.error(f"Error applying user permissions: {e}")
            # Continue without user-specific filtering

        tickets = query.all()
        logger.info(f"Found {len(tickets)} tickets for filter options")

        # Get unique values with counts
        statuses = {}
        priorities = {}
        categories = {}
        users = {}
        countries = {}

        for ticket in tickets:
            try:
                # Status
                status = ticket.status.value if ticket.status else 'No Status'
                statuses[status] = statuses.get(status, 0) + 1

                # Priority
                priority = ticket.priority.value if ticket.priority else 'No Priority'
                priorities[priority] = priorities.get(priority, 0) + 1

                # Category
                category = ticket.get_category_display_name() if ticket.category else 'No Category'
                categories[category] = categories.get(category, 0) + 1

                # Assigned user
                user = ticket.assigned_to.username if ticket.assigned_to else 'Unassigned'
                users[user] = users.get(user, 0) + 1

                # Country (if available)
                if hasattr(ticket, 'country') and ticket.country:
                    countries[ticket.country] = countries.get(ticket.country, 0) + 1
                elif ticket.customer and hasattr(ticket.customer, 'country') and ticket.customer.country:
                    countries[ticket.customer.country] = countries.get(ticket.customer.country, 0) + 1
            except Exception as e:
                logger.error(f"Error processing ticket {ticket.id}: {e}")
                continue

        return jsonify({
            'success': True,
            'statuses': [{'value': k, 'label': k, 'count': v} for k, v in sorted(statuses.items())],
            'priorities': [{'value': k, 'label': k, 'count': v} for k, v in sorted(priorities.items())],
            'categories': [{'value': k, 'label': k, 'count': v} for k, v in sorted(categories.items())],
            'users': [{'value': k, 'label': k, 'count': v} for k, v in sorted(users.items())],
            'countries': [{'value': k, 'label': k, 'count': v} for k, v in sorted(countries.items())]
        })
    except Exception as e:
        logger.error(f"Error in get_available_filters: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'statuses': [{'value': 'New', 'label': 'New', 'count': 0}, {'value': 'In Progress', 'label': 'In Progress', 'count': 0}],
            'priorities': [{'value': 'Medium', 'label': 'Medium', 'count': 0}, {'value': 'High', 'label': 'High', 'count': 0}],
            'categories': [{'value': 'PIN Request', 'label': 'PIN Request', 'count': 0}, {'value': 'Asset Repair', 'label': 'Asset Repair', 'count': 0}],
            'users': [{'value': 'Unassigned', 'label': 'Unassigned', 'count': 0}],
            'countries': []
        }), 500
    finally:
        db.close()

@reports_bp.route('/api/case-data', methods=['POST'])
@login_required
@permission_required('can_view_reports')
def get_case_data():
    """Get filtered case data for dynamic reporting"""
    try:
        filters = request.get_json() or {}
        logger.info(f"Received filters: {filters}")

        db = SessionLocal()

        try:
            # Base query with permissions
            query = db.query(Ticket)

            # Apply permission filters more safely
            try:
                if hasattr(current_user, 'user_type') and current_user.user_type:
                    if current_user.user_type.value == 'COUNTRY_ADMIN':
                        query = query.outerjoin(CustomerUser, Ticket.customer_id == CustomerUser.id)
                        if hasattr(current_user, 'country') and current_user.country:
                            query = query.filter(CustomerUser.country == current_user.country)
                    elif current_user.user_type.value == 'CLIENT':
                        query = query.filter(Ticket.requester_id == current_user.id)
            except Exception as e:
                logger.error(f"Error applying user permissions: {e}")

            # Apply date range filter
            if filters.get('startDate'):
                try:
                    start_date = datetime.fromisoformat(filters['startDate'])
                    query = query.filter(Ticket.created_at >= start_date)
                except ValueError as e:
                    logger.error(f"Invalid start date format: {e}")

            if filters.get('endDate'):
                try:
                    end_date = datetime.fromisoformat(filters['endDate'])
                    # Add one day to include the end date
                    end_date = end_date + timedelta(days=1)
                    query = query.filter(Ticket.created_at < end_date)
                except ValueError as e:
                    logger.error(f"Invalid end date format: {e}")

            tickets = query.all()
            logger.info(f"Found {len(tickets)} tickets before additional filtering")

            # Apply additional filters
            filtered_tickets = []
            for ticket in tickets:
                # Status filter
                if filters.get('statuses') and len(filters['statuses']) > 0:
                    ticket_status = ticket.status.value if ticket.status else 'No Status'
                    if ticket_status not in filters['statuses']:
                        continue

                # Priority filter
                if filters.get('priorities') and len(filters['priorities']) > 0:
                    ticket_priority = ticket.priority.value if ticket.priority else 'No Priority'
                    if ticket_priority not in filters['priorities']:
                        continue

                # Category filter
                if filters.get('categories') and len(filters['categories']) > 0:
                    ticket_category = ticket.get_category_display_name() if ticket.category else 'No Category'
                    if ticket_category not in filters['categories']:
                        continue

                # Assigned to filter
                if filters.get('assignedTo') and len(filters['assignedTo']) > 0:
                    ticket_user = ticket.assigned_to.username if ticket.assigned_to else 'Unassigned'
                    if ticket_user not in filters['assignedTo']:
                        continue

                # Country filter (if applicable)
                if filters.get('countries') and len(filters['countries']) > 0:
                    if hasattr(ticket, 'country') and ticket.country:
                        if ticket.country not in filters['countries']:
                            continue

                filtered_tickets.append(ticket)

            # Generate grouped data based on groupBy parameter
            group_by = filters.get('groupBy', 'status')
            grouped_data = {}

            for ticket in filtered_tickets:
                group_key = get_group_key(ticket, group_by)
                grouped_data[group_key] = grouped_data.get(group_key, 0) + 1

            # Generate timeline data (cases created over time)
            timeline_data = {}
            for ticket in filtered_tickets:
                date_key = ticket.created_at.strftime('%Y-%m-%d')
                timeline_data[date_key] = timeline_data.get(date_key, 0) + 1

            # Generate table data
            table_data = []
            for ticket in filtered_tickets[:100]:  # Limit to first 100 for performance
                table_data.append({
                    'case_id': ticket.display_id if hasattr(ticket, 'display_id') and ticket.display_id else str(ticket.id),
                    'subject': ticket.subject or 'Untitled',
                    'status': ticket.status.value if ticket.status else 'No Status',
                    'priority': ticket.priority.value if ticket.priority else 'No Priority',
                    'category': ticket.get_category_display_name() if ticket.category else 'No Category',
                    'created_at': ticket.created_at.isoformat(),
                    'assigned_to': ticket.assigned_to.username if ticket.assigned_to else None
                })

            # Calculate summary statistics
            total_tickets = len(filtered_tickets)
            open_tickets = len([t for t in filtered_tickets if t.status and t.status.name not in ['RESOLVED', 'RESOLVED_DELIVERED']])
            resolved_tickets = total_tickets - open_tickets
            resolution_rate = (resolved_tickets / total_tickets * 100) if total_tickets > 0 else 0

            logger.info(f"Returning data for {total_tickets} tickets")
            return jsonify({
                'success': True,
                'total': total_tickets,
                'summary': {
                    'total': total_tickets,
                    'open': open_tickets,
                    'resolved': resolved_tickets,
                    'resolution_rate': round(resolution_rate, 1)
                },
                'groupedData': {
                    group_by: grouped_data
                },
                'timelineData': timeline_data,
                'tableData': table_data
            })

        finally:
            db.close()

    except Exception as e:
        logger.error(f"Error in get_case_data: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'total': 0,
            'summary': {
                'total': 0,
                'open': 0,
                'resolved': 0,
                'resolution_rate': 0
            },
            'groupedData': {},
            'timelineData': {},
            'tableData': []
        }), 500

def get_group_key(ticket, group_by):
    """Get the grouping key for a ticket based on the group_by parameter"""
    if group_by == 'status':
        return ticket.status.value if ticket.status else 'No Status'
    elif group_by == 'priority':
        return ticket.priority.value if ticket.priority else 'No Priority'
    elif group_by == 'category':
        return ticket.get_category_display_name() if ticket.category else 'No Category'
    elif group_by == 'assigned_to':
        return ticket.assigned_to.username if ticket.assigned_to else 'Unassigned'
    elif group_by == 'country':
        return getattr(ticket, 'country', 'Unknown') or 'Unknown'
    elif group_by == 'created_date':
        return ticket.created_at.strftime('%Y-%m-%d')
    elif group_by == 'resolution_time':
        if ticket.status and ticket.status.name in ['RESOLVED', 'RESOLVED_DELIVERED']:
            hours = (ticket.updated_at - ticket.created_at).total_seconds() / 3600
            if hours < 24:
                return '< 1 day'
            elif hours < 72:
                return '1-3 days'
            elif hours < 168:  # 7 days
                return '3-7 days'
            else:
                return '> 7 days'
        return 'Not Resolved'
    else:
        return 'Unknown' 