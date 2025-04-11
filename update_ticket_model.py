import os
import sys
import inspect
import importlib.util

def load_module(filepath, module_name):
    """Dynamically load a Python module from file path"""
    spec = importlib.util.spec_from_file_location(module_name, filepath)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def update_ticket_model():
    """Update the Ticket model to ensure it has all the required attributes"""
    try:
        # Try to import the Ticket model from the models directory
        print("Trying to load Ticket model...")
        
        # Method 1: Try direct import
        try:
            sys.path.append(os.getcwd())
            from models.ticket import Ticket
            print("Successfully imported Ticket model")
        except Exception as e:
            print(f"Error importing Ticket model: {str(e)}")
            
            # Method 2: Try loading module manually
            try:
                ticket_module = load_module('models/ticket.py', 'ticket')
                Ticket = getattr(ticket_module, 'Ticket')
                print("Successfully loaded Ticket model via manual loading")
            except Exception as e2:
                print(f"Error loading Ticket model manually: {str(e2)}")
                print("Could not load Ticket model. Exiting.")
                return
        
        # Check if the Ticket model is a SQLAlchemy model
        if not hasattr(Ticket, '__table__'):
            print("Ticket model does not appear to be a SQLAlchemy model.")
            return
        
        # Print current attributes
        print(f"\nCurrent Ticket model columns: {Ticket.__table__.columns.keys()}")
        
        # Get the SQLAlchemy Column class and String type
        try:
            # Get the SQLAlchemy type used in the model
            print("\nAttempting to determine SQLAlchemy types used in the model...")
            
            # Find which SQLAlchemy Column class is used
            model_source = inspect.getsource(Ticket)
            print("Ticket model source found.")
            
            # Try to import Column and String from sqlalchemy
            from sqlalchemy import Column, String
            print("Imported Column and String from sqlalchemy")
            
            # Check if the required columns exist in the model
            required_columns = [
                'shipping_tracking_2',
                'return_tracking',
                'shipping_carrier',
                'shipping_status',
                'secondary_tracking_carrier',
                'secondary_tracking_status'
            ]
            
            missing_columns = []
            for col in required_columns:
                if col not in Ticket.__table__.columns:
                    missing_columns.append(col)
                    print(f"Column '{col}' is missing from the Ticket model.")
            
            if not missing_columns:
                print("\nAll required columns exist in the Ticket model.")
                print("Try restarting the web application on PythonAnywhere.")
                return
            
            # Add alert about the needed model changes
            print("\n=== IMPORTANT ===")
            print("The Ticket model needs to be updated with the following columns:")
            for col in missing_columns:
                print(f"    {col} = Column(String, nullable=True)")
            
            print("\nYou need to manually edit the models/ticket.py file to add these columns.")
            print("After adding the columns, restart the web application on PythonAnywhere.")
            
        except Exception as e:
            print(f"Error determining SQLAlchemy types: {str(e)}")
    
    except Exception as e:
        print(f"Error updating Ticket model: {str(e)}")

if __name__ == "__main__":
    print("Updating Ticket model...")
    print(f"Current working directory: {os.getcwd()}")
    update_ticket_model() 