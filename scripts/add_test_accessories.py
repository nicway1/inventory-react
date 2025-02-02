import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import SessionLocal
from models.accessory import Accessory

def add_test_accessories():
    session = SessionLocal()
    try:
        # Create test accessories
        accessories = [
            Accessory(
                name='Logitech MX Keys',
                category='Keyboard',
                manufacturer='Logitech',
                model_no='MX Keys',
                total_quantity=5,
                available_quantity=5,
                status='Available',
                notes='Wireless keyboard with backlight'
            ),
            Accessory(
                name='Dell USB-C Dock',
                category='Docking Station',
                manufacturer='Dell',
                model_no='WD19TB',
                total_quantity=3,
                available_quantity=3,
                status='Available',
                notes='Thunderbolt docking station'
            ),
            Accessory(
                name='Apple Magic Mouse',
                category='Mouse',
                manufacturer='Apple',
                model_no='A1657',
                total_quantity=4,
                available_quantity=4,
                status='Available',
                notes='Wireless mouse with touch surface'
            )
        ]
        
        # Add all accessories to the session
        for accessory in accessories:
            session.add(accessory)
        
        # Commit the changes
        session.commit()
        print("Test accessories added successfully!")
        
    except Exception as e:
        print(f"Error adding test accessories: {str(e)}")
        session.rollback()
    finally:
        session.close()

if __name__ == '__main__':
    add_test_accessories() 