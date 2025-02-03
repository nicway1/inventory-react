from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from utils.auth_decorators import admin_required
from models.sale import Sale, Platform
from models.user import User, UserType
from models.asset import Asset
from models.company import Company
from utils.db_manager import DatabaseManager
from datetime import datetime, timedelta
import json

sales_bp = Blueprint('sales', __name__, url_prefix='/sales')
db_manager = DatabaseManager()

@sales_bp.route('/')
@login_required
def dashboard():
    db_session = db_manager.get_session()
    try:
        # Get fresh user object from database
        user = db_session.query(User).options(
            db_manager.joinedload('company')
        ).get(current_user.id)
        
        if not user or not user.company:
            flash('No company assigned', 'error')
            return redirect(url_for('main.index'))

        company = user.company

        # Get company statistics
        total_users = company.users.count()
        
        # Get sales data
        sales_query = db_session.query(Sale).filter(Sale.company_id == company.id)
        total_sales = sum(sale.selling_price for sale in sales_query.all())
        total_profit = sum(sale.profit for sale in sales_query.all() if sale.profit is not None)

        # Get recent sales
        recent_sales = sales_query.order_by(Sale.sale_date.desc()).limit(10).all()

        # Get top salespeople
        users = company.users.all()
        user_sales = {}
        for user in users:
            user_sales_data = sales_query.filter(Sale.user_id == user.id).all()
            if user_sales_data:
                user_sales[user.id] = {
                    'user': user,
                    'total_sales': sum(sale.selling_price for sale in user_sales_data),
                    'total_profit': sum(sale.profit for sale in user_sales_data if sale.profit is not None)
                }
        
        # Sort by total sales and get top 5
        top_salespeople = sorted(
            user_sales.values(),
            key=lambda x: x['total_sales'],
            reverse=True
        )[:5]

        return render_template('sales/dashboard.html',
                             company=company,
                             total_users=total_users,
                             total_sales=total_sales,
                             total_profit=total_profit,
                             top_salespeople=top_salespeople,
                             recent_sales=recent_sales)
    finally:
        db_session.close()

@sales_bp.route('/record', methods=['GET', 'POST'])
@login_required
def record_sale():
    if request.method == 'POST':
        db_session = db_manager.get_session()
        try:
            # Get form data
            product_id = request.form.get('product_id')
            platform = request.form.get('platform')
            selling_price = request.form.get('selling_price')
            customer_name = request.form.get('customer_name')
            sale_date = request.form.get('sale_date')
            notes = request.form.get('notes')

            # Validate required fields
            if not all([product_id, platform, selling_price, customer_name]):
                flash('Please fill in all required fields', 'error')
                return redirect(url_for('sales.record_sale'))

            # Create new sale
            sale = Sale(
                product_id=product_id,
                user_id=current_user.id,
                company_id=current_user.company_id,
                platform=Platform[platform.upper()],
                selling_price=float(selling_price),
                customer_name=customer_name,
                sale_date=datetime.strptime(sale_date, '%Y-%m-%d') if sale_date else datetime.utcnow(),
                notes=notes
            )

            # Calculate profit
            sale.calculate_profit()

            db_session.add(sale)
            db_session.commit()
            flash('Sale recorded successfully!', 'success')
            return redirect(url_for('sales.dashboard'))

        except Exception as e:
            db_session.rollback()
            flash(f'Error recording sale: {str(e)}', 'error')
            return redirect(url_for('sales.record_sale'))
        finally:
            db_session.close()

    # GET request - show form
    db_session = db_manager.get_session()
    try:
        # Get fresh user object
        user = db_session.query(User).get(current_user.id)
        
        # Get available products (assets)
        products = db_session.query(Asset).filter(
            Asset.company_id == user.company_id
        ).all()

        return render_template('sales/record_sale.html',
                             products=products,
                             platforms=Platform)
    finally:
        db_session.close()

@sales_bp.route('/user/<int:user_id>')
@login_required
def user_sales(user_id):
    db_session = db_manager.get_session()
    try:
        user = db_session.query(User).options(
            db_manager.joinedload('company')
        ).get(user_id)
        
        if not user or user.company_id != current_user.company_id:
            flash('User not found', 'error')
            return redirect(url_for('sales.dashboard'))

        # Get sales data
        sales_query = db_session.query(Sale).filter(Sale.user_id == user.id)
        total_sales = sum(sale.selling_price for sale in sales_query.all())
        total_profit = sum(sale.profit for sale in sales_query.all() if sale.profit is not None)
        recent_sales = sales_query.order_by(Sale.sale_date.desc()).limit(5).all()

        # Get sales data for chart (last 30 days)
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=30)
        sales_data = sales_query.filter(
            Sale.sale_date >= start_date,
            Sale.sale_date <= end_date
        ).all()

        # Format data for chart
        chart_data = {
            'labels': [],
            'sales': [],
            'profit': []
        }

        for sale in sales_data:
            chart_data['labels'].append(sale.sale_date.strftime('%Y-%m-%d'))
            chart_data['sales'].append(float(sale.selling_price))
            chart_data['profit'].append(float(sale.profit) if sale.profit else 0)

        return render_template('sales/user_sales.html',
                             user=user,
                             total_sales=total_sales,
                             total_profit=total_profit,
                             recent_sales=recent_sales,
                             chart_data=json.dumps(chart_data))
    finally:
        db_session.close()

@sales_bp.route('/api/stats')
@login_required
def get_stats():
    """API endpoint for getting sales statistics"""
    db_session = db_manager.get_session()
    try:
        user = db_session.query(User).options(
            db_manager.joinedload('company')
        ).get(current_user.id)
        
        company = user.company
        if not company:
            return jsonify({'error': 'No company assigned'}), 400

        # Get date range from query parameters
        days = request.args.get('days', 30, type=int)
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)

        # Get sales data
        sales_query = db_session.query(Sale).filter(
            Sale.company_id == company.id,
            Sale.sale_date >= start_date,
            Sale.sale_date <= end_date
        )
        sales_data = sales_query.all()

        # Calculate statistics
        stats = {
            'total_sales': sum(sale.selling_price for sale in sales_data),
            'total_profit': sum(sale.profit for sale in sales_data if sale.profit),
            'total_transactions': len(sales_data),
            'by_platform': {}
        }

        # Group by platform
        for sale in sales_data:
            platform = sale.platform.value
            if platform not in stats['by_platform']:
                stats['by_platform'][platform] = {
                    'sales': 0,
                    'profit': 0,
                    'count': 0
                }
            stats['by_platform'][platform]['sales'] += sale.selling_price
            stats['by_platform'][platform]['profit'] += (sale.profit or 0)
            stats['by_platform'][platform]['count'] += 1

        return jsonify(stats)
    finally:
        db_session.close()

@sales_bp.route('/api/user/<int:user_id>/sales')
@login_required
def get_user_sales(user_id):
    """API endpoint for getting user sales data"""
    db_session = db_manager.get_session()
    try:
        user = db_session.query(User).options(
            db_manager.joinedload('company')
        ).get(user_id)
        
        if not user or user.company_id != current_user.company_id:
            return jsonify({'error': 'User not found'}), 404

        # Get date range from query parameters
        days = request.args.get('days', 30, type=int)
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)

        # Get sales data
        sales_query = db_session.query(Sale).filter(
            Sale.user_id == user.id,
            Sale.sale_date >= start_date,
            Sale.sale_date <= end_date
        )
        sales = sales_query.all()
        
        # Format sales data
        sales_data = [{
            'id': sale.id,
            'product': sale.product.name if sale.product else 'Unknown',
            'platform': sale.platform.value,
            'selling_price': float(sale.selling_price),
            'profit': float(sale.profit) if sale.profit else 0,
            'customer_name': sale.customer_name,
            'sale_date': sale.sale_date.isoformat(),
            'notes': sale.notes
        } for sale in sales]

        return jsonify(sales_data)
    finally:
        db_session.close() 