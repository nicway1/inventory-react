#!/usr/bin/env python
"""
Quick script to set accessory ID 78 to quantity 1
"""

from models.base import Base
from models.accessory import Accessory
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Database connection
engine = create_engine('sqlite:///inventory.db')
Session = sessionmaker(bind=engine)
session = Session()

try:
    # Get accessory ID 78
    accessory = session.query(Accessory).filter(Accessory.id == 78).first()

    if not accessory:
        print("❌ Accessory ID 78 not found!")
    else:
        print(f"Found accessory: {accessory.name}")
        print(f"Current quantity: {accessory.available_quantity}")

        # Set it to 1
        accessory.available_quantity = 1
        session.commit()

        print(f"✅ Updated quantity to: {accessory.available_quantity}")

except Exception as e:
    session.rollback()
    print(f"❌ Error: {str(e)}")
finally:
    session.close()
