import os
import sys

# Add your project directory to the sys.path
path = '/home/nicway2/inventory'
if path not in sys.path:
    sys.path.append(path)

# Set environment variables
os.environ['PYTHONPATH'] = '/home/nicway2/inventory'
os.environ['MAIL_DEBUG'] = '1'

# Email configuration with TLS
os.environ['MAIL_SERVER'] = 'mail.privateemail.com'
os.environ['MAIL_PORT'] = '587'  # TLS port
os.environ['MAIL_USE_TLS'] = 'True'
os.environ['MAIL_USE_SSL'] = 'False'
os.environ['MAIL_USERNAME'] = 'support@truelog.site'
os.environ['MAIL_PASSWORD'] = '123456'
os.environ['MAIL_DEFAULT_SENDER'] = 'support@truelog.site'

# Database configuration
os.environ['DATABASE_URL'] = 'sqlite:////home/nicway2/inventory/inventory.db'
os.environ['SECRET_KEY'] = 'your-secret-key-here'

# Import your Flask app
from app import app as application

if __name__ == "__main__":
    application.run() 