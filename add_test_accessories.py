from database import Base, engine
from models.accessory import Accessory
from sqlalchemy.orm import Session

def add_test_accessories():
    # Create a session
    session = Session(engine)
    
    try:
        # Sample accessories
        accessories = [
            {
                'name': 'Logitech MX Keys',
                'category': 'Keyboard',
                'manufacturer': 'Logitech',
                'model_no': 'MX KEYS',
                'total_quantity': 5,
                'available_quantity': 5,
                'status': 'Available',
                'notes': 'Wireless keyboard with backlight'
            },
            {
                'name': 'Dell USB-C Dock',
                'category': 'Docking Station',
                'manufacturer': 'Dell',
                'model_no': 'WD19TB',
                'total_quantity': 3,
                'available_quantity': 2,
                'status': 'Available',
                'notes': 'Thunderbolt dock with 180W power delivery'
            },
            {
                'name': 'Apple Magic Mouse',
                'category': 'Mouse',
                'manufacturer': 'Apple',
                'model_no': 'A1657',
                'total_quantity': 4,
                'available_quantity': 4,
                'status': 'Available',
                'notes': 'Wireless mouse with touch surface'
            }
        ]
        
        # Add each accessory to the database
        for acc_data in accessories:
            accessory = Accessory(**acc_data)
            session.add(accessory)
        
        # Commit the changes
        session.commit()
        print("Test accessories added successfully!")
        
    except Exception as e:
        session.rollback()
        print(f"Error adding test accessories: {str(e)}")
    finally:
        session.close()

if __name__ == "__main__":
    add_test_accessories() 