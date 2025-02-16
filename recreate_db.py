import os
import sys
from sqlalchemy import create_engine, text
from models import Base
from models.user import User, UserType, Country
from models.company import Company
from models.location import Location
from models.asset import Asset, AssetStatus
from models.accessory import Accessory
from models.customer_user import CustomerUser
from models.activity import Activity
from models.ticket import Ticket, TicketStatus, TicketPriority, TicketCategory, RMAStatus
from models.queue import Queue
from models.asset_history import AssetHistory
from models.permission import Permission
from werkzeug.security import generate_password_hash
from datetime import datetime

def recreate_database():
    print("Starting database recreation...")
    
    # Create a new database
    db_path = 'inventory.db'
    if os.path.exists(db_path):
        os.remove(db_path)
        print("Removed existing database")
    
    # Create new database and tables
    engine = create_engine('sqlite:///inventory.db')
    Base.metadata.create_all(engine)  # Let SQLAlchemy handle the table creation order
    print("Created new database with all tables")
    
    # Create default company
    with engine.begin() as conn:
        conn.execute(
            text("INSERT INTO companies (name, address) VALUES (:name, :address)"),
            {"name": "LunaComputer", "address": "Default Address"}
        )
        print("Created default company")
        
        # Get the company id
        result = conn.execute(text("SELECT id FROM companies WHERE name = 'LunaComputer'"))
        company_id = result.scalar()
        
        # Create admin user
        admin_user = {
            "username": "admin",
            "email": "admin@lunacomputer.com",
            "password_hash": generate_password_hash("admin123"),
            "user_type": UserType.SUPER_ADMIN.value,
            "company_id": company_id,
            "created_at": datetime.utcnow()
        }
        
        conn.execute(
            text("""
                INSERT INTO users 
                (username, email, password_hash, user_type, company_id, created_at) 
                VALUES 
                (:username, :email, :password_hash, :user_type, :company_id, :created_at)
            """),
            admin_user
        )
        print("Created admin user (username: admin, password: admin123)")
        
        # Create default queue
        conn.execute(
            text("INSERT INTO queues (name, description) VALUES (:name, :description)"),
            {"name": "General", "description": "Default queue for all tickets"}
        )
        print("Created default queue")
            
        # Create default permissions for each user type
        for user_type in UserType:
            conn.execute(
                text("""
                    INSERT INTO permissions 
                    (user_type, can_view_assets, can_edit_assets, can_delete_assets, 
                     can_create_assets, can_view_accessories, can_edit_accessories, 
                     can_delete_accessories, can_create_accessories, can_import_data, 
                     can_export_data, can_view_reports, can_generate_reports)
                    VALUES
                    (:user_type, :can_view, :can_edit, :can_delete, :can_create,
                     :can_view_acc, :can_edit_acc, :can_delete_acc, :can_create_acc,
                     :can_import, :can_export, :can_view_rep, :can_gen_rep)
                """),
                {
                    "user_type": user_type.value,
                    "can_view": True,
                    "can_edit": user_type == UserType.SUPER_ADMIN,
                    "can_delete": user_type == UserType.SUPER_ADMIN,
                    "can_create": user_type in [UserType.SUPER_ADMIN, UserType.COUNTRY_ADMIN],
                    "can_view_acc": True,
                    "can_edit_acc": user_type in [UserType.SUPER_ADMIN, UserType.COUNTRY_ADMIN],
                    "can_delete_acc": user_type == UserType.SUPER_ADMIN,
                    "can_create_acc": user_type in [UserType.SUPER_ADMIN, UserType.COUNTRY_ADMIN],
                    "can_import": user_type in [UserType.SUPER_ADMIN, UserType.COUNTRY_ADMIN],
                    "can_export": True,
                    "can_view_rep": True,
                    "can_gen_rep": user_type in [UserType.SUPER_ADMIN, UserType.COUNTRY_ADMIN]
                }
            )
        print("Created default permissions for all user types")
    
    print("\nDatabase recreation completed successfully!")
    print("You can now log in with:")
    print("Username: admin")
    print("Password: admin123")

if __name__ == "__main__":
    recreate_database() 