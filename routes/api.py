from flask import Blueprint, jsonify, request
from utils.auth_decorators import login_required
from utils.db_manager import DatabaseManager
from models.asset import Asset

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