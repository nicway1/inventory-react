from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from utils.user_store import UserStore
from utils.auth_decorators import admin_required
from utils.snipeit_client import SnipeITClient
from utils.db_manager import DatabaseManager

auth_bp = Blueprint('auth', __name__)
user_store = UserStore()
snipe_client = SnipeITClient()
db_manager = DatabaseManager()

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        print("\nLogin attempt:")
        print(f"- Username: {username}")
        print(f"- Password: {password}")
        
        user = db_manager.get_user_by_username(username)
        if user:
            print("\nUser found:")
            print(f"- ID: {user.id}")
            print(f"- Username: {user.username}")
            print(f"- Password Hash: {user.password_hash}")
            print(f"- User Type: {user.user_type}")
            
            if user.check_password(password):
                print("\nPassword check passed")
                session['user_id'] = user.id
                session['user_type'] = user.user_type.value
                session['username'] = user.username
                print(f"Session data set: {session}")
                return redirect(url_for('main.index'))
            else:
                print("\nPassword check failed")
        else:
            print(f"\nNo user found with username: {username}")
            
        flash('Invalid username or password')
    
    return render_template('auth/login.html')

@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.login'))

@auth_bp.route('/users')
@admin_required
def list_users():
    users = user_store.get_all_users()
    return render_template('auth/users.html', users=users)

@auth_bp.route('/users/new', methods=['GET', 'POST'])
@admin_required
def create_user():
    print("Accessing create_user route")  # Debug print
    
    if request.method == 'POST':
        print("POST request received")  # Debug print
        print("Form data:", request.form)  # Debug print
        
        username = request.form.get('username')
        password = request.form.get('password')
        user_type = request.form.get('user_type')
        company = request.form.get('company')
        role = request.form.get('role')
        
        print(f"Creating user: {username}, type: {user_type}, company: {company}, role: {role}")  # Debug print
        
        user = user_store.create_user(
            username=username,
            password=password,
            user_type=user_type,
            company=company,
            role=role
        )
        
        if user:
            print(f"User created successfully: {user.id}")  # Debug print
            flash('User created successfully')
            return redirect(url_for('auth.list_users'))
        else:
            print("User creation failed")  # Debug print
            flash('Failed to create user')
            return redirect(url_for('auth.create_user'))
    
    try:
        companies = snipe_client.get_companies()
        print(f"Retrieved companies: {companies}")  # Debug print
    except Exception as e:
        print(f"Error fetching companies: {e}")  # Debug print
        companies = []
    
    return render_template(
        'auth/create_user.html',
        companies=companies,
        user_types=['user', 'admin', 'super_admin']
    )

@auth_bp.route('/register', methods=['POST'])
def register():
    username = request.form.get('username')
    password = request.form.get('password')
    company = request.form.get('company')
    role = request.form.get('role')
    
    user = user_store.create_user(
        username=username,
        password=password,
        company=company,
        role=role
    )
    
    if user:
        flash('Registration successful')
        return redirect(url_for('auth.login'))
    else:
        flash('Username already exists')
        return redirect(url_for('auth.register')) 