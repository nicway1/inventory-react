import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import SessionLocal
from models.accessory import Accessory

def check_accessories():
    session = SessionLocal()
    try:
        # Query all accessories
        accessories = session.query(Accessory).all()
        
        if not accessories:
            print("No accessories found in the database!")
            return
        
        print("\nAccessories in the database:")
        print("-" * 80)
        for accessory in accessories:
            print(f"Name: {accessory.name}")
            print(f"Category: {accessory.category}")
            print(f"Manufacturer: {accessory.manufacturer}")
            print(f"Model: {accessory.model_no}")
            print(f"Total Quantity: {accessory.total_quantity}")
            print(f"Available Quantity: {accessory.available_quantity}")
            print(f"Status: {accessory.status}")
            print(f"Notes: {accessory.notes}")
            print("-" * 80)
            
    except Exception as e:
        print(f"Error checking accessories: {str(e)}")
    finally:
        session.close()

if __name__ == '__main__':
    check_accessories() 