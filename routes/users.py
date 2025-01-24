from flask import Blueprint, render_template, redirect, url_for, flash, session, request
from utils.auth_decorators import login_required, admin_required
from utils.user_store import UserStore
from utils.ticket_store import TicketStore
from utils.snipeit_api import get_all_assets

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
    print("Accessing my_profile route")  # Debug print
    if 'user_id' not in session:
        print("No user_id in session")  # Debug print
        flash('Please log in first')
        return redirect(url_for('auth.login'))
    
    user_id = session.get('user_id')
    print(f"User ID from session: {user_id}")  # Debug print
    user = user_store.get_user_by_id(user_id)
    print(f"User found: {user}")  # Debug print
    
    if not user:
        print("User not found in store")  # Debug print
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
    user = user_store.get_user_by_id(user_id)
    if not user:
        flash('User not found')
        return redirect(url_for('auth.list_users'))

    if request.method == 'POST':
        # Update user details
        user.username = request.form.get('username', user.username)
        user.company = request.form.get('company', user.company)
        user.role = request.form.get('role', user.role)
        user.user_type = request.form.get('user_type', user.user_type)
        
        # Save changes
        user_store.save_users()
        flash('User settings updated successfully')
        return redirect(url_for('users.manage_user', user_id=user_id))

    return render_template(
        'users/manage.html',
        user=user,
        user_types=['admin', 'user']
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