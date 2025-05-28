import os
import sys
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Add the project directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set Python path and enable debugging
os.environ['PYTHONPATH'] = '/home/nicway2/inventory'
os.environ['FLASK_DEBUG'] = '1'
os.environ['MAIL_DEBUG'] = '1'

# Email configuration - Outlook/Office 365 SMTP
os.environ['MAIL_SERVER'] = 'smtp.office365.com'
os.environ['MAIL_PORT'] = '587'
os.environ['MAIL_USE_TLS'] = 'True'
os.environ['MAIL_USE_SSL'] = 'False'
os.environ['MAIL_USERNAME'] = 'your-company-email@yourcompany.com'  # Replace with your actual company email
os.environ['MAIL_PASSWORD'] = 'your-app-password-from-outlook'  # Use App Password (not regular password) for 2FA accounts
os.environ['MAIL_DEFAULT_SENDER'] = 'your-company-email@yourcompany.com'  # Replace with your actual company email
os.environ['MAIL_MAX_EMAILS'] = '1'  # Limit for testing
os.environ['MAIL_SUPPRESS_SEND'] = 'False'
os.environ['MAIL_ASCII_ATTACHMENTS'] = 'False'

#db
os.environ['SECRET_KEY'] = 'your-secret-key-here'
os.environ['DATABASE_URL'] = 'sqlite:////home/nicway2/inventory/inventory.db'

# Import your Flask app
from app import create_app

# Enable debug logging for Flask-Mail
app = create_app()
app.logger.setLevel(logging.DEBUG)

if __name__ == "__main__":
    app.run() 