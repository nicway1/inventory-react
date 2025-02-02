from database import Base, engine
from models.inventory_item import InventoryItem
from models.accessory import Accessory
from models.user import User, UserType
from models.ticket import Ticket
from models.activity import Activity
from models.comment import Comment
from models.queue import Queue
from models.shipment import Shipment
from models.company import Company
from models.asset import Asset
from models.location import Location
from werkzeug.security import generate_password_hash
from sqlalchemy.orm import Session

# Function to recreate the database and create initial admin user
def recreate_database():
    print("Dropping all tables...")
    Base.metadata.drop_all(engine)
    
    print("Creating all tables...")
    Base.metadata.create_all(engine)
    
    # Create initial admin user
    with Session(engine) as session:
        # Create a default company first (optional)
        default_company = Company(
            name="Default Company",
            address="Default Address"
        )
        session.add(default_company)
        session.flush()  # This assigns an ID to the company
        
        # Create admin user
        admin_user = User(
            username='admin',
            email='admin@example.com',
            password_hash=generate_password_hash('admin123'),
            user_type=UserType.SUPER_ADMIN,
            company_id=default_company.id  # Optional: link to default company
        )
        session.add(admin_user)
        session.commit()
    
    print("Database tables recreated successfully!")
    print("Initial super admin user created with username: 'admin' and password: 'admin123'")

if __name__ == "__main__":
    recreate_database() 