import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, DateTime, ForeignKey, JSON, Enum
from datetime import datetime
from models.database import AssetStatus

def create_tables():
    engine = create_engine('sqlite:///inventory.db')
    metadata = MetaData()

    # Define the locations table first (no foreign key dependencies)
    locations = Table('locations', metadata,
        Column('id', Integer, primary_key=True),
        Column('name', String(100), nullable=False),
        Column('country', String(100)),
        Column('address', String(200))
    )

    # Define the companies table (no foreign key dependencies)
    companies = Table('companies', metadata,
        Column('id', Integer, primary_key=True),
        Column('name', String(100), nullable=False, unique=True),
        Column('contact_name', String(100)),
        Column('contact_email', String(100))
    )

    # Define the users table (depends on companies)
    users = Table('users', metadata,
        Column('id', Integer, primary_key=True),
        Column('username', String(50), unique=True, nullable=False),
        Column('email', String(120), unique=True, nullable=False),
        Column('password_hash', String(128)),
        Column('company_id', Integer, ForeignKey('companies.id')),
        Column('created_at', DateTime, default=datetime.utcnow)
    )

    # Define the accessories table (depends on locations)
    accessories = Table('accessories', metadata,
        Column('id', Integer, primary_key=True),
        Column('name', String(100), nullable=False),
        Column('category', String(50)),
        Column('status', String(50), default='Available'),
        Column('total_quantity', Integer, default=0),
        Column('available_quantity', Integer, default=0),
        Column('customer', String(100)),
        Column('location_id', Integer, ForeignKey('locations.id')),
        Column('created_at', DateTime, default=datetime.utcnow),
        Column('updated_at', DateTime, default=datetime.utcnow)
    )

    # Define the accessory_history table (depends on accessories and users)
    accessory_history = Table('accessory_history', metadata,
        Column('id', Integer, primary_key=True),
        Column('accessory_id', Integer, ForeignKey('accessories.id'), nullable=False),
        Column('user_id', Integer, ForeignKey('users.id'), nullable=False),
        Column('action', String(50), nullable=False),
        Column('changes', JSON),
        Column('notes', String(1000)),
        Column('created_at', DateTime, default=datetime.utcnow)
    )

    # Create all tables in the correct order
    metadata.create_all(engine)
    print("All tables created successfully")

if __name__ == "__main__":
    create_tables() 