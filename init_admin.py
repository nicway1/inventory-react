from app import app
from database import init_db, engine, SessionLocal
from models.user import User, UserType
from models.company import Company
from werkzeug.security import generate_password_hash

def init_admin():
    print("Starting initialization...")
    with app.app_context():
        init_db()
        db = SessionLocal()
        try:
            # Create default company
            default_company = db.query(Company).filter_by(name="LunaComputer").first()
            if not default_company:
                print("Creating default company...")
                default_company = Company(
                    name="LunaComputer",
                    address="Default Address"
                )
                db.add(default_company)
                db.commit()
                print("Default company created successfully")
            else:
                print("Default company already exists")
            
            # Create admin user
            admin_user = db.query(User).filter_by(username="admin").first()
            if not admin_user:
                print("Creating admin user...")
                admin_user = User(
                    username="admin",
                    email="admin@lunacomputer.com",
                    password_hash=generate_password_hash("admin123"),
                    user_type=UserType.SUPER_ADMIN,
                    company_id=default_company.id
                )
                db.add(admin_user)
                db.commit()
                print("Admin user created successfully")
                print("Username: admin")
                print("Password: admin123")
            else:
                print("Admin user already exists")
        
        except Exception as e:
            print(f"An error occurred: {str(e)}")
            db.rollback()
        finally:
            db.close()
            print("Initialization complete")

if __name__ == "__main__":
    init_admin() 