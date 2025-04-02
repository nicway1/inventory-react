from sqlalchemy import create_engine, MetaData
from database import engine
from models.company import Company
from models.user_company_permission import UserCompanyPermission
from models.base import Base

def update_company_schema():
    print("Starting company schema update...")
    
    # Create new tables
    Base.metadata.create_all(engine, tables=[
        Company.__table__,
        UserCompanyPermission.__table__
    ])
    
    # Add company_id column to assets table if it doesn't exist
    with engine.connect() as connection:
        try:
            connection.execute('ALTER TABLE assets ADD COLUMN company_id INTEGER REFERENCES companies(id)')
            print("Added company_id column to assets table")
        except Exception as e:
            print(f"company_id column might already exist: {e}")
    
    print("Company schema update completed")

if __name__ == '__main__':
    update_company_schema() 