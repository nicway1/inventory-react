from database import Base, engine
from models.asset import Asset
from models.accessory import Accessory

def recreate_database():
    print("Dropping all tables...")
    Base.metadata.drop_all(engine)
    
    print("Creating all tables...")
    Base.metadata.create_all(engine)
    
    print("Database tables recreated successfully!")

if __name__ == "__main__":
    recreate_database() 