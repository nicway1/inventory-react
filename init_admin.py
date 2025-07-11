from app import app
from database import init_db, engine, SessionLocal
from models.user import User, UserType
from models.company import Company
from werkzeug.security import generate_password_hash
from utils.auth import safe_generate_password_hash
import logging

# Set up logging for this module
logger = logging.getLogger(__name__)


def init_admin():
    logger.info("Starting initialization...")
    with app.app_context():
        init_db()
        db = SessionLocal()
        try:
            # Create default company
            default_company = db.query(Company).filter_by(name="LunaComputer").first()
            if not default_company:
                logger.info("Creating default company...")
                default_company = Company(
                    name="LunaComputer",
                    address="Default Address"
                )
                db.add(default_company)
                db.commit()
                logger.info("Default company created successfully")
            else:
                logger.info("Default company already exists")
            
            # Create admin user
            admin_user = db.query(User).filter_by(username="admin").first()
            if not admin_user:
                logger.info("Creating admin user...")
                admin_user = User(
                    username="admin",
                    email="admin@lunacomputer.com",
                    password_hash=safe_generate_password_hash("admin123"),
                    user_type=UserType.SUPER_ADMIN,
                    company_id=default_company.id
                )
                db.add(admin_user)
                db.commit()
                logger.info("Admin user created successfully")
                logger.info("Username: admin")
                logger.info("Password: admin123")
            else:
                logger.info("Admin user already exists")
        
        except Exception as e:
            logger.info("An error occurred: {str(e)}")
            db.rollback()
        finally:
            db.close()
            logger.info("Initialization complete")

if __name__ == "__main__":
    init_admin() 