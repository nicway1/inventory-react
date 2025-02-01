import sys
import os

# Add your project directory to the sys.path
path = '/home/nicway3/inventory'
if path not in sys.path:
    sys.path.append(path)

# Set environment variables
os.environ['SECRET_KEY'] = 'your-secret-key-here'
os.environ['DATABASE_URL'] = 'sqlite:////home/nicway3/inventory/inventory.db'

# Import your application
from app import app as application

if __name__ == "__main__":
    application.run() 