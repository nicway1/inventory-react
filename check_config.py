import os
from flask import Flask
from sqlalchemy import inspect
import importlib.util
import logging

# Set up logging for this module
logger = logging.getLogger(__name__)


def load_module(filepath, module_name):
    """Dynamically load a Python module from file path"""
    spec = importlib.util.spec_from_file_location(module_name, filepath)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def check_app_config():
    """Check Flask application configuration including database URI"""
    try:
        # Try to load the app from various potential files
        app = None
        possible_files = ['app.py', 'wsgi.py', '__init__.py']
        
        for file in possible_files:
            if os.path.exists(file):
                logger.info("Trying to load app from {file}...")
                try:
                    # Try different methods of getting the app
                    module = load_module(file, file.replace('.py', ''))
                    
                    # Look for an 'app' variable
                    if hasattr(module, 'app'):
                        app = module.app
                        logger.info("Found app in {file} via 'app' variable")
                        break
                    
                    # Look for a 'create_app' function
                    elif hasattr(module, 'create_app'):
                        app = module.create_app()
                        logger.info("Found app in {file} via 'create_app' function")
                        break
                        
                    # Look for an 'application' variable (for wsgi)
                    elif hasattr(module, 'application'):
                        app = module.application
                        logger.info("Found app in {file} via 'application' variable")
                        break
                        
                except Exception as e:
                    logger.info("Error loading from {file}: {str(e)}")
        
        if not app:
            logger.info("Could not find Flask application. Make sure app.py or wsgi.py exists in current directory.")
            return
        
        # Print app configuration
        with app.app_context():
            logger.info("\nApplication Configuration:")
            logger.info("DEBUG mode: {app.config.get('DEBUG', 'Not set')}")
            logger.info("Database URI: {app.config.get('SQLALCHEMY_DATABASE_URI', 'Not set')}")
            logger.info("Database track modifications: {app.config.get('SQLALCHEMY_TRACK_MODIFICATIONS', 'Not set')}")
            
            # If SQLAlchemy is available, try to connect and inspect
            try:
                from flask_sqlalchemy import SQLAlchemy
                db = SQLAlchemy(app)
                
                # Check if we can connect to the database
                logger.info("\nAttempting to connect to the database...")
                with db.engine.connect() as connection:
                    logger.info("Successfully connected to the database.")
                    
                    # Get database tables
                    inspector = inspect(db.engine)
                    tables = inspector.get_table_names()
                    logger.info("\nDatabase Tables: {tables}")
                    
                    # Check tickets table columns
                    if 'tickets' in tables:
                        columns = inspector.get_columns('tickets')
                        column_names = [col['name'] for col in columns]
                        logger.info("\nTickets Table Columns: {sorted(column_names)}")
                        
                        # Check for the required columns
                        required_columns = [
                            'shipping_tracking_2',
                            'return_tracking',
                            'shipping_carrier',
                            'shipping_status',
                            'secondary_tracking_carrier',
                            'secondary_tracking_status'
                        ]
                        
                        for col in required_columns:
                            if col in column_names:
                                logger.info("Column '{col}' exists.")
                            else:
                                logger.info("Column '{col}' is MISSING!")
                    else:
                        logger.info("No 'tickets' table found in the database.")
                
                # Try to find the Ticket model
                logger.info("\nChecking for Ticket model...")
                try:
                    from models.ticket import Ticket
                    logger.info("Ticket model class found.")
                    
                    # Check model attributes
                    logger.info("\nTicket model attributes: {dir(Ticket)}")
                    
                    # Check model __table__ attributes
                    logger.info("\nTicket model table columns: {Ticket.__table__.columns.keys()}")
                    
                    # Check if the required columns are in the model
                    for col in required_columns:
                        if col in Ticket.__table__.columns:
                            logger.info("Column '{col}' exists in the Ticket model.")
                        else:
                            logger.info("Column '{col}' is MISSING from the Ticket model!")
                    
                except Exception as e:
                    logger.info("Error checking Ticket model: {str(e)}")
                
            except Exception as e:
                logger.info("Error with SQLAlchemy connection: {str(e)}")
    
    except Exception as e:
        logger.info("Error checking configuration: {str(e)}")

if __name__ == "__main__":
    logger.info("Checking application configuration...")
    logger.info("Current working directory: {os.getcwd()}")
    check_app_config() 