from flask import Blueprint, render_template, jsonify, request
from flask_login import login_required, current_user
from utils.auth_decorators import permission_required
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