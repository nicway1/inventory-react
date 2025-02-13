import os
import sys
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Add your project directory to the sys.path
path = '/home/nicway2/inventory'
if path not in sys.path:
    sys.path.append(path)

# Set Python path and enable debugging
os.environ['PYTHONPATH'] = '/home/nicway2/inventory'
os.environ['FLASK_DEBUG'] = '1'
os.environ['MAIL_DEBUG'] = '1'

# Email configuration - Gmail SMTP
os.environ['MAIL_SERVER'] = 'smtp.gmail.com'
os.environ['MAIL_PORT'] = '587'
os.environ['MAIL_USE_TLS'] = 'True'
os.environ['MAIL_USE_SSL'] = 'False'
os.environ['MAIL_USERNAME'] = 'trueloginventory@gmail.com'
os.environ['MAIL_PASSWORD'] = 'lfve nald ymnl vrzf'  # Gmail App Password
os.environ['MAIL_DEFAULT_SENDER'] = 'trueloginventory@gmail.com'
os.environ['MAIL_MAX_EMAILS'] = '1'  # Limit for testing
os.environ['MAIL_SUPPRESS_SEND'] = 'False'
os.environ['MAIL_ASCII_ATTACHMENTS'] = 'False'

#db
os.environ['SECRET_KEY'] = 'your-secret-key-here'
os.environ['DATABASE_URL'] = 'sqlite:////home/nicway2/inventory/inventory.db'

# Import your Flask app
from app import app as application

# Enable debug logging for Flask-Mail
application.logger.setLevel(logging.DEBUG)

if __name__ == "__main__":
    application.run() 