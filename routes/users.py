from flask import Blueprint, render_template, redirect, url_for, flash, session, request, jsonify
from utils.auth_decorators import login_required, admin_required, super_admin_required
from utils.user_store import UserStore
from utils.ticket_store import TicketStore
from utils.snipeit_api import get_all_assets
from forms.user_form import UserCreateForm
from models.user import UserType, Country
from werkzeug.security import generate_password_hash
from utils.auth import safe_generate_password_hash
import logging

# Set up logging for this module
logger = logging.getLogger(__name__)


users_bp = Blueprint('users', __name__, url_prefix='/users')
user_store = UserStore()
ticket_store = TicketStore()

@users_bp.route('/profile/<int:user_id>')
@login_required
def view_profile(user_id):
    user = user_store.get_user_by_id(user_id)
    if not user:
        flash('User not found')
        return redirect(url_for('index'))

    # Get user's tickets
    tickets = ticket_store.get_user_tickets(user_id, user.user_type)
    
    # Calculate statistics
    open_statuses = ['New', 'In Progress', 'Pending']
    statistics = {
        'total_tickets': len(tickets),
        'open_tickets': len([t for t in tickets if t.status in open_statuses]),
        'resolved_tickets': len([t for t in tickets if t.status == 'Resolved'])
    }

    # Get recent activity
    recent_activity = []
    for ticket in sorted(tickets, key=lambda x: x.updated_at, reverse=True)[:5]:
        recent_activity.append({
            'type': 'Ticket Update',
            'timestamp': ticket.updated_at,
            'description': f'Ticket {ticket.display_id}: {ticket.subject}'
        })

    # Get assigned assets from Snipe-IT
    all_assets = get_all_assets()
    assigned_assets = [
        asset for asset in all_assets 
        if asset.get('assigned_to') and asset['assigned_to'].get('id') == user_id
    ]

    return render_template(
        'users/profile.html',
        user=user,
        statistics=statistics,
        recent_activity=recent_activity,
        assigned_assets=assigned_assets
    )

@users_bp.route('/profile')
@login_required
def my_profile():
    logger.info("Accessing my_profile route")  # Debug print
    if 'user_id' not in session:
        logger.info("No user_id in session")  # Debug print
        flash('Please log in first')
        return redirect(url_for('auth.login'))
    
    user_id = session.get('user_id')
    logger.info("User ID from session: {user_id}")  # Debug print
    user = user_store.get_user_by_id(user_id)
    logger.info("User found: {user}")  # Debug print
    
    if not user:
        logger.info("User not found in store")  # Debug print
        flash('User profile not found')
        return redirect(url_for('index'))

    # Get user's tickets
    tickets = ticket_store.get_user_tickets(user_id, user.user_type)
    
    # Calculate statistics
    open_statuses = ['New', 'In Progress', 'Pending']
    statistics = {
        'total_tickets': len(tickets),
        'open_tickets': len([t for t in tickets if t.status in open_statuses]),
        'resolved_tickets': len([t for t in tickets if t.status == 'Resolved'])
    }

    # Get recent activity
    recent_activity = []
    for ticket in sorted(tickets, key=lambda x: x.updated_at, reverse=True)[:5]:
        recent_activity.append({
            'type': 'Ticket Update',
            'timestamp': ticket.updated_at,
            'description': f'Ticket {ticket.display_id}: {ticket.subject}'
        })

    # Get assigned assets from Snipe-IT
    all_assets = get_all_assets()
    assigned_assets = [
        asset for asset in all_assets 
        if asset.get('assigned_to') and asset['assigned_to'].get('id') == user_id
    ]

    return render_template(
        'users/profile.html',
        user=user,
        statistics=statistics,
        recent_activity=recent_activity,
        assigned_assets=assigned_assets
    ) 

@users_bp.route('/manage/<int:user_id>', methods=['GET', 'POST'])
@admin_required  # Make sure only admins can access this
def manage_user(user_id):
    from models.enums import UserType, Country

    user = user_store.get_user_by_id(user_id)
    if not user:
        flash('User not found')
        return redirect(url_for('auth.list_users'))

    if request.method == 'POST':
        # Update user details
        user.username = request.form.get('username', user.username)
        user.company = request.form.get('company', user.company)
        user.role = request.form.get('role', user.role)

        # Update user type
        user_type_value = request.form.get('user_type')
        if user_type_value:
            user.user_type = UserType(user_type_value)

        # Update assigned country for COUNTRY_ADMIN
        assigned_country_value = request.form.get('assigned_country')
        if user.user_type == UserType.COUNTRY_ADMIN and assigned_country_value:
            user.assigned_country = Country(assigned_country_value)
        elif user.user_type != UserType.COUNTRY_ADMIN:
            user.assigned_country = None

        # Save changes
        user_store.save_users()
        flash('User settings updated successfully')
        return redirect(url_for('users.manage_user', user_id=user_id))

    return render_template(
        'users/manage.html',
        user=user,
        user_types=[ut.value for ut in UserType],
        countries=[c.value for c in Country if not c.value in ['IN', 'SG', 'TW', 'CN']]  # Exclude legacy codes
    )

@users_bp.route('/manage/<int:user_id>/reset-password', methods=['POST'])
@admin_required
def reset_user_password(user_id):
    user = user_store.get_user_by_id(user_id)
    if not user:
        flash('User not found')
        return redirect(url_for('auth.list_users'))

    new_password = request.form.get('new_password')
    if new_password:
        user.password_hash = new_password  # In production, hash this password
        user_store.save_users()
        flash('Password reset successfully')
    else:
        flash('New password is required')

    return redirect(url_for('users.manage_user', user_id=user_id))

@users_bp.route('/create', methods=['GET', 'POST'])
@login_required
@super_admin_required
def create_user():
    form = UserCreateForm()
    
    if request.method == 'POST' and form.validate_on_submit():
        try:
            user_data = {
                'username': form.username.data,
                'email': form.email.data,
                'password_hash': safe_generate_password_hash(form.password.data),
                'user_type': UserType(form.user_type.data)
            }
            
            # Add assigned country only for Country Admin
            if form.user_type.data == UserType.COUNTRY_ADMIN.value:
                if not form.assigned_country.data:
                    return jsonify({'error': 'Country selection is required for Country Admin'}), 400
                user_data['assigned_country'] = Country(form.assigned_country.data)
            
            new_user = User(**user_data)
            db.session.add(new_user)
            db.session.commit()
            
            return jsonify({'message': 'User created successfully'}), 201
            
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 400
            
    return render_template('users/create.html', form=form) 