from flask import Blueprint, render_template, request, jsonify, redirect, url_for
from utils.auth_decorators import admin_required
from utils.snipeit_client import SnipeITClient

admin_bp = Blueprint('admin', __name__)
snipe_client = SnipeITClient()

@admin_bp.route('/settings')
@admin_required
def settings():
    """Admin settings page"""
    return render_template('admin/settings.html')

@admin_bp.route('/companies')
@admin_required
def list_companies():
    """List all companies"""
    try:
        # Get companies from Snipe-IT
        companies = snipe_client.get_companies()
        
        # Get asset counts for each company
        for company in companies:
            assets = snipe_client.get_all_assets()
            company['assets_count'] = len([
                asset for asset in assets 
                if asset.get('company') and asset['company'].get('id') == company['id']
            ])
            
            # Get user counts
            users = snipe_client.get_users()
            company['users_count'] = len([
                user for user in users 
                if user.get('company') and user['company'].get('id') == company['id']
            ])
            
        return render_template('admin/companies/list.html', companies=companies)
    except Exception as e:
        print(f"Error fetching companies: {e}")
        return render_template('admin/companies/list.html', companies=[])

@admin_bp.route('/companies/add', methods=['GET', 'POST'])
@admin_required
def add_company():
    if request.method == 'POST':
        company_data = request.form.to_dict()
        success = snipe_client.create_company(company_data)
        if success:
            return redirect(url_for('admin.list_companies'))
        return "Error creating company", 400
    return render_template('admin/companies/add.html')

@admin_bp.route('/companies/<int:company_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_company(company_id):
    if request.method == 'POST':
        company_data = request.form.to_dict()
        success = snipe_client.update_company(company_id, company_data)
        if success:
            return redirect(url_for('admin.list_companies'))
        return "Error updating company", 400
    
    company = snipe_client.get_company(company_id)
    return render_template('admin/companies/edit.html', company=company)

@admin_bp.route('/companies/<int:company_id>')
@admin_required
def view_company(company_id):
    company = snipe_client.get_company(company_id)
    return render_template('admin/companies/view.html', company=company)

@admin_bp.route('/companies/<int:company_id>/delete', methods=['POST'])
@admin_required
def delete_company(company_id):
    success = snipe_client.delete_company(company_id)
    if success:
        return jsonify({'status': 'success'})
    return jsonify({'status': 'error'}), 400 