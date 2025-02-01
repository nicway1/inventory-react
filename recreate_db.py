from database import Base, engine
from models.inventory_item import InventoryItem
from models.accessory import Accessory
from models.user import User
from werkzeug.security import generate_password_hash
from sqlalchemy.orm import Session

def recreate_database():
    print("Dropping all tables...")
    Base.metadata.drop_all(engine)
    
    print("Creating all tables...")
    Base.metadata.create_all(engine)
    
    # Create initial admin user
    with Session(engine) as session:
        admin_user = User(
            username='admin',
            email='admin@example.com',
            password_hash=generate_password_hash('admin123'),
            role='admin'
        )
        session.add(admin_user)
        session.commit()
    
    print("Database tables recreated successfully!")
    print("Initial admin user created with username: 'admin' and password: 'admin123'")

if __name__ == "__main__":
    recreate_database() 