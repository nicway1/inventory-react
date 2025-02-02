import sys
import os

# Add your project directory to the sys.path
project_path = '/home/nicway3/inventory'
if project_path not in sys.path:
    sys.path.insert(0, project_path)

# Set environment variables
os.environ['FLASK_ENV'] = 'production'
os.environ['SECRET_KEY'] = os.urandom(24).hex()
os.environ['DATABASE_URL'] = 'sqlite:////home/nicway3/inventory/inventory.db'

# Import your application
from app import app as application

if __name__ == "__main__":
    application.run() 