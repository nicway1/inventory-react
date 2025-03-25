import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Flask configuration
SECRET_KEY = os.environ.get('SECRET_KEY', 'dev_key_for_development_only')
DEBUG = os.environ.get('DEBUG', 'True').lower() in ('true', '1', 't')

# Database configuration
DATABASE_URL = os.environ.get('DATABASE_URL', 'sqlite:///inventory.db')

# File upload configuration
UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', 'uploads')
ALLOWED_EXTENSIONS = {'xlsx', 'xls', 'csv', 'pdf', 'jpg', 'jpeg', 'png'}

# TrackingMore API configuration
TRACKINGMORE_API_KEY = os.environ.get('TRACKINGMORE_API_KEY')

# Email configuration
MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.example.com')
MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'True').lower() in ('true', '1', 't')
MAIL_USERNAME = os.environ.get('MAIL_USERNAME', 'username')
MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD', 'password')
MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER', 'noreply@example.com') 