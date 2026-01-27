import os
import sys

# Add your project directory to the sys.path
path = '/home/nicway2/mysite3'
if path not in sys.path:
    sys.path.append(path)

# Set Python path and enable debugging
os.environ['PYTHONPATH'] = '/home/nicway2/mysite3'
os.environ['MAIL_DEBUG'] = '1'
os.environ['MAIL_USE_TLS'] = 'True'

# Set environment variables
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

# Database - MySQL on PythonAnywhere
os.environ['SECRET_KEY'] = 'your-secret-key-here'
os.environ['DATABASE_URL'] = 'mysql+pymysql://nicway2:truelog123%40@nicway2.mysql.pythonanywhere-services.com/nicway2$inventory'

os.environ['TRACKING_PROXY_URL'] = 'http://182.52.25.243:8080'

# Microsoft 365 OAuth2 Configuration
os.environ['MS_CLIENT_ID'] = 'b5d3d9b5-5ec0-4bb3-a127-5bce2c8e632d'
os.environ['MS_CLIENT_SECRET'] = 'kya8Q~XzoQ_tNWojqhph5woMH1VdOPxcemELvaOW'
os.environ['MS_TENANT_ID'] = 'fdc52ee0-3b36-4a9b-ad4f-216bd2d20c4e'
os.environ['MS_FROM_EMAIL'] = 'support@truelog.com.sg'
os.environ['USE_OAUTH2_EMAIL'] = 'true'

# SingPost Tracking API Configuration
os.environ['SINGPOST_TRACKING_API_KEY'] = '10307e4981034e6fbaf1395c4d4e2982'
os.environ['SINGPOST_TRACKING_USE_PRODUCTION'] = 'true'

# Import your Flask app
from app import app as application

if __name__ == "__main__":
    application.run()
