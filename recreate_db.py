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
from utils.auth import safe_generate_password_hash
from datetime import datetime
import logging

# Set up logging for this module
logger = logging.getLogger(__name__)


def recreate_database():
    logger.info("Starting database recreation...")
    
    # Create a new database
    db_path = 'inventory.db'
    if os.path.exists(db_path):
        os.remove(db_path)
        logger.info("Removed existing database")
    
    # Create new database and tables
    engine = create_engine('sqlite:///inventory.db')
    Base.metadata.create_all(engine)  # Let SQLAlchemy handle the table creation order
    logger.info("Created new database with all tables")
    
    # Create default company
    with engine.begin() as conn:
        conn.execute(
            text("INSERT INTO companies (name, address) VALUES (:name, :address)"),
            {"name": "LunaComputer", "address": "Default Address"}
        )
        logger.info("Created default company")
        
        # Get the company id
        result = conn.execute(text("SELECT id FROM companies WHERE name = 'LunaComputer'"))
        company_id = result.scalar()
        
        # Create admin user
        admin_user = {
            "username": "admin",
            "email": "admin@lunacomputer.com",
            "password_hash": safe_generate_password_hash("admin123"),
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
        logger.info("Created admin user (username: admin, password: admin123)")
        
        # Create default queue
        conn.execute(
            text("INSERT INTO queues (name, description) VALUES (:name, :description)"),
            {"name": "General", "description": "Default queue for all tickets"}
        )
        logger.info("Created default queue")
            
        # Create default permissions for each user type
        for user_type in UserType:
            default_permissions = Permission.get_default_permissions(user_type)
            conn.execute(
                text("""
                    INSERT INTO permissions 
                    (user_type, can_view_assets, can_edit_assets, can_delete_assets, 
                     can_create_assets, can_view_country_assets, can_edit_country_assets,
                     can_delete_country_assets, can_create_country_assets,
                     can_view_accessories, can_edit_accessories, can_delete_accessories,
                     can_create_accessories, can_view_companies, can_edit_companies,
                     can_delete_companies, can_create_companies, can_view_users,
                     can_edit_users, can_delete_users, can_create_users,
                     can_view_reports, can_generate_reports, can_import_data,
                     can_export_data)
                    VALUES
                    (:user_type, :can_view_assets, :can_edit_assets, :can_delete_assets,
                     :can_create_assets, :can_view_country_assets, :can_edit_country_assets,
                     :can_delete_country_assets, :can_create_country_assets,
                     :can_view_accessories, :can_edit_accessories, :can_delete_accessories,
                     :can_create_accessories, :can_view_companies, :can_edit_companies,
                     :can_delete_companies, :can_create_companies, :can_view_users,
                     :can_edit_users, :can_delete_users, :can_create_users,
                     :can_view_reports, :can_generate_reports, :can_import_data,
                     :can_export_data)
                """),
                {
                    "user_type": user_type.value,
                    **default_permissions
                }
            )
        logger.info("Created default permissions for all user types")
    
    logger.info("\nDatabase recreation completed successfully!")
    logger.info("You can now log in with:")
    logger.info("Username: admin")
    logger.info("Password: admin123")

if __name__ == "__main__":
    recreate_database() 