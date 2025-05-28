from flask import Blueprint, jsonify, request
from utils.auth_decorators import login_required
from utils.db_manager import DatabaseManager
from models.asset import Asset
from models.customer_user import CustomerUser
from models.company import Company
from sqlalchemy import or_
from flask import current_app

api_bp = Blueprint('api', __name__, url_prefix='/api')
db_manager = DatabaseManager()

@api_bp.route('/assets/details', methods=['GET'])
@login_required
def get_asset_details():
    serial_number = request.args.get('serial_number')
    if not serial_number:
        return jsonify({'error': 'Serial number is required'}), 400

    db_session = db_manager.get_session()
    try:
        asset = db_session.query(Asset).filter(Asset.serial_num == serial_number).first()
        if not asset:
            return jsonify({'error': 'Asset not found'}), 404

        # Get customer company name from either customer_user or legacy customer field
        customer_company = None
        if asset.customer_user and asset.customer_user.company:
            customer_company = asset.customer_user.company.name
        elif asset.customer:
            customer_company = asset.customer

        return jsonify({
            'model': asset.model,
            'customer_company': customer_company,
            'serial_number': asset.serial_num,
            'asset_tag': asset.asset_tag
        })
    finally:
        db_session.close()

@api_bp.route('/customers/search', methods=['GET'])
@login_required
def search_customers():
    """Search customers by name, company, email, or address"""
    try:
        query = request.args.get('q', '').strip()
        
        db_session = db_manager.get_session()
        
        if query and len(query) >= 2:
            # Search customers by name, email, company name, or address
            customers = db_session.query(CustomerUser).join(Company, CustomerUser.company_id == Company.id, isouter=True).filter(
                or_(
                    CustomerUser.name.ilike(f'%{query}%'),
                    CustomerUser.email.ilike(f'%{query}%'),
                    CustomerUser.address.ilike(f'%{query}%'),
                    Company.name.ilike(f'%{query}%')
                )
            ).limit(20).all()
        else:
            # No query or query too short - return all customers (limited)
            customers = db_session.query(CustomerUser).join(Company, CustomerUser.company_id == Company.id, isouter=True).limit(50).all()
        
        results = []
        for customer in customers:
            results.append({
                'id': customer.id,
                'name': customer.name,
                'email': customer.email or '',
                'company': customer.company.name if customer.company else '',
                'address': customer.address or '',
                'text': f"{customer.name} ({customer.company.name if customer.company else 'No Company'})"
            })
        
        return jsonify(results)
        
    except Exception as e:
        current_app.logger.error(f"Error searching customers: {str(e)}")
        return jsonify({'error': 'Search failed'}), 500 