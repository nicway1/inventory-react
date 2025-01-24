from database import Base, engine
from models.asset import Asset
from models.accessory import Accessory

def clear_database():
    print("Clearing database...")
    # Drop all tables
    Base.metadata.drop_all(bind=engine)
    print("All tables dropped.")
    
    # Recreate all tables
    Base.metadata.create_all(bind=engine)
    print("Tables recreated successfully.")

if __name__ == "__main__":
    clear_database() 