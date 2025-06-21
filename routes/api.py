from flask import Blueprint, jsonify, request, session
from utils.auth_decorators import login_required
from utils.db_manager import DatabaseManager
from models.asset import Asset
from models.customer_user import CustomerUser
from models.company import Company
from models.user import User, UserType
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
        user = db_manager.get_user(session['user_id'])
        
        # Base query
        customers_query = db_session.query(CustomerUser).join(Company, CustomerUser.company_id == Company.id, isouter=True)
        
        # Apply permission-based filtering for non-SUPER_ADMIN users
        if user.user_type != UserType.SUPER_ADMIN and user.company_id:
            from models.company_customer_permission import CompanyCustomerPermission
            
            # Get companies this user's company has permission to view customers from
            permitted_company_ids = db_session.query(CompanyCustomerPermission.customer_company_id)\
                .filter(
                    CompanyCustomerPermission.company_id == user.company_id,
                    CompanyCustomerPermission.can_view == True
                ).subquery()
            
            # Users can see their own company's customers plus any permitted ones
            customers_query = customers_query.filter(
                or_(
                    CustomerUser.company_id == user.company_id,  # Own company customers
                    CustomerUser.company_id.in_(permitted_company_ids)  # Permitted customers
                )
            )
        
        if query and len(query) >= 2:
            # Search customers by name, email, company name, or address
            customers = customers_query.filter(
                or_(
                    CustomerUser.name.ilike(f'%{query}%'),
                    CustomerUser.email.ilike(f'%{query}%'),
                    CustomerUser.address.ilike(f'%{query}%'),
                    Company.name.ilike(f'%{query}%')
                )
            ).limit(20).all()
        else:
            # No query or query too short - return all customers (limited)
            customers = customers_query.limit(50).all()
        
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

@api_bp.route('/search', methods=['GET'])
@login_required
def unified_search():
    """Unified search API endpoint for assets, tickets, accessories, and customers"""
    try:
        from models.ticket import Ticket, TicketCategory, TicketStatus, TicketPriority
        from models.asset import Asset
        from models.accessory import Accessory
        from models.customer_user import CustomerUser
        from models.company import Company
        from models.user import User, UserType
        
        query = request.args.get('q', '').strip()
        result_type = request.args.get('type', 'all')  # all, assets, tickets, accessories, customers
        limit = request.args.get('limit', 10, type=int)
        
        if not query:
            return jsonify({'results': []})
        
        db_session = db_manager.get_session()
        user = db_session.query(User).get(session['user_id'])
        
        results = {
            'query': query,
            'assets': [],
            'tickets': [],
            'accessories': [],
            'customers': [],
            'related_tickets': []
        }
        
        # Search assets
        if result_type in ['all', 'assets']:
            asset_query = db_session.query(Asset)
            
            # Apply user-based filters
            if user.user_type == UserType.CLIENT and user.company:
                asset_query = asset_query.filter(
                    or_(
                        Asset.company_id == user.company_id,
                        Asset.customer == user.company.name
                    )
                )
            elif user.user_type == UserType.COUNTRY_ADMIN and user.assigned_country:
                asset_query = asset_query.filter(Asset.country == user.assigned_country.value)
            
            assets = asset_query.filter(
                or_(
                    Asset.name.ilike(f'%{query}%'),
                    Asset.model.ilike(f'%{query}%'),
                    Asset.serial_num.ilike(f'%{query}%'),
                    Asset.asset_tag.ilike(f'%{query}%'),
                    Asset.category.ilike(f'%{query}%'),
                    Asset.customer.ilike(f'%{query}%'),
                    Asset.hardware_type.ilike(f'%{query}%'),
                    Asset.cpu_type.ilike(f'%{query}%')
                )
            ).limit(limit).all()
            
            for asset in assets:
                results['assets'].append({
                    'id': asset.id,
                    'asset_tag': asset.asset_tag or '',
                    'serial_num': asset.serial_num or '',
                    'name': asset.name or '',
                    'model': asset.model or '',
                    'status': asset.status.value if asset.status else '',
                    'customer': asset.customer or '',
                    'url': f"/inventory/asset/{asset.id}"
                })
        
        # Search tickets
        if result_type in ['all', 'tickets']:
            ticket_query = db_session.query(Ticket)
            
            # Apply user-based filters
            if user.user_type == UserType.COUNTRY_ADMIN and user.assigned_country:
                ticket_query = ticket_query.filter(Ticket.country == user.assigned_country.value)
            
            tickets = ticket_query.filter(
                or_(
                    Ticket.subject.ilike(f'%{query}%'),
                    Ticket.description.ilike(f'%{query}%'),
                    Ticket.notes.ilike(f'%{query}%'),
                    Ticket.serial_number.ilike(f'%{query}%'),
                    Ticket.damage_description.ilike(f'%{query}%'),
                    Ticket.return_description.ilike(f'%{query}%'),
                    Ticket.shipping_tracking.ilike(f'%{query}%'),
                    Ticket.return_tracking.ilike(f'%{query}%'),
                    Ticket.shipping_tracking_2.ilike(f'%{query}%'),
                    *([Ticket.id == int(query.replace('TICK-', '').replace('#', ''))] 
                      if query.replace('TICK-', '').replace('#', '').isdigit() else [])
                )
            ).limit(limit).all()
            
            for ticket in tickets:
                results['tickets'].append({
                    'id': ticket.id,
                    'display_id': ticket.display_id,
                    'subject': ticket.subject or '',
                    'category': ticket.category.value if ticket.category else '',
                    'status': ticket.status.value if ticket.status else '',
                    'priority': ticket.priority.value if ticket.priority else '',
                    'created_at': ticket.created_at.strftime('%Y-%m-%d') if ticket.created_at else '',
                    'url': f"/tickets/{ticket.id}"
                })
        
        # Search accessories
        if result_type in ['all', 'accessories']:
            accessory_query = db_session.query(Accessory)
            
            # Apply user-based filters
            if user.user_type == UserType.COUNTRY_ADMIN and user.assigned_country:
                accessory_query = accessory_query.filter(Accessory.country == user.assigned_country.value)
            
            accessories = accessory_query.filter(
                or_(
                    Accessory.name.ilike(f'%{query}%'),
                    Accessory.category.ilike(f'%{query}%'),
                    Accessory.manufacturer.ilike(f'%{query}%'),
                    Accessory.model_no.ilike(f'%{query}%'),
                    Accessory.notes.ilike(f'%{query}%')
                )
            ).limit(limit).all()
            
            for accessory in accessories:
                results['accessories'].append({
                    'id': accessory.id,
                    'name': accessory.name or '',
                    'category': accessory.category or '',
                    'manufacturer': accessory.manufacturer or '',
                    'total_quantity': accessory.total_quantity or 0,
                    'available_quantity': accessory.available_quantity or 0,
                    'status': accessory.status or '',
                    'url': f"/inventory/accessory/{accessory.id}"
                })
        
        # Search customers - apply company filtering for non-SUPER_ADMIN users
        if result_type in ['all', 'customers']:
            customers_query = db_session.query(CustomerUser).join(Company, CustomerUser.company_id == Company.id, isouter=True)
            
            # Apply permission-based filtering for non-SUPER_ADMIN users
            if user.user_type != UserType.SUPER_ADMIN and user.company_id:
                from models.company_customer_permission import CompanyCustomerPermission
                
                # Get companies this user's company has permission to view customers from
                permitted_company_ids = db_session.query(CompanyCustomerPermission.customer_company_id)\
                    .filter(
                        CompanyCustomerPermission.company_id == user.company_id,
                        CompanyCustomerPermission.can_view == True
                    ).subquery()
                
                # Users can see their own company's customers plus any permitted ones
                customers_query = customers_query.filter(
                    or_(
                        CustomerUser.company_id == user.company_id,  # Own company customers
                        CustomerUser.company_id.in_(permitted_company_ids)  # Permitted customers
                    )
                )
            
            customers = customers_query.filter(
                or_(
                    CustomerUser.name.ilike(f'%{query}%'),
                    CustomerUser.email.ilike(f'%{query}%'),
                    CustomerUser.contact_number.ilike(f'%{query}%'),
                    CustomerUser.address.ilike(f'%{query}%'),
                    Company.name.ilike(f'%{query}%')
                )
            ).limit(limit).all()
            
            for customer in customers:
                results['customers'].append({
                    'id': customer.id,
                    'name': customer.name or '',
                    'email': customer.email or '',
                    'contact_number': customer.contact_number or '',
                    'company': customer.company.name if customer.company else '',
                    'address': customer.address or '',
                    'url': f"/inventory/customer-users/{customer.id}"
                })
        
        # Find related tickets for found assets
        if result_type in ['all', 'assets'] and results['assets']:
            asset_serial_numbers = [a['serial_num'] for a in results['assets'] if a['serial_num']]
            asset_tags = [a['asset_tag'] for a in results['assets'] if a['asset_tag']]
            asset_ids = [a['id'] for a in results['assets']]
            
            if asset_serial_numbers or asset_tags or asset_ids:
                related_tickets_query = db_session.query(Ticket).filter(
                    or_(
                        Ticket.serial_number.in_(asset_serial_numbers) if asset_serial_numbers else False,
                        Ticket.asset_id.in_(asset_ids) if asset_ids else False,
                        *[Ticket.description.ilike(f'%{tag}%') for tag in asset_tags if tag],
                        *[Ticket.notes.ilike(f'%{tag}%') for tag in asset_tags if tag],
                        *[Ticket.description.ilike(f'%{serial}%') for serial in asset_serial_numbers if serial],
                        *[Ticket.notes.ilike(f'%{serial}%') for serial in asset_serial_numbers if serial]
                    )
                )
                
                related_tickets = related_tickets_query.limit(limit).all()
                ticket_ids = [t['id'] for t in results['tickets']]
                related_tickets = [t for t in related_tickets if t.id not in ticket_ids]
                
                for ticket in related_tickets:
                    results['related_tickets'].append({
                        'id': ticket.id,
                        'display_id': ticket.display_id,
                        'subject': ticket.subject or '',
                        'category': ticket.category.value if ticket.category else '',
                        'status': ticket.status.value if ticket.status else '',
                        'asset_info': ticket.asset.asset_tag if ticket.asset else ticket.serial_number,
                        'url': f"/tickets/{ticket.id}"
                    })
        
        return jsonify(results)
        
    except Exception as e:
        current_app.logger.error(f"Error in unified search: {str(e)}")
        return jsonify({'error': 'Search failed'}), 500
    finally:
        db_session.close() 