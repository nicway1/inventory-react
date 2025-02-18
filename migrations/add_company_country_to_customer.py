import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from models.user import Country

def upgrade_customer_users():
    engine = create_engine('sqlite:///inventory.db')
    
    with engine.begin() as conn:
        # Create new table with the desired schema
        conn.execute(text("""
            CREATE TABLE customer_users_new (
                id INTEGER PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                contact_number VARCHAR(20) NOT NULL,
                email VARCHAR(100) NOT NULL,
                address VARCHAR(500) NOT NULL,
                company_id INTEGER REFERENCES companies(id),
                country VARCHAR(50) NOT NULL DEFAULT 'USA',
                created_at DATETIME,
                updated_at DATETIME,
                FOREIGN KEY(company_id) REFERENCES companies(id)
            )
        """))
        
        # Copy data from old table to new table
        conn.execute(text("""
            INSERT INTO customer_users_new (
                id, name, contact_number, email, address, created_at, updated_at
            )
            SELECT 
                id, name, contact_number, email, address, created_at, updated_at
            FROM customer_users
        """))
        
        # Set default country for existing records
        conn.execute(text("""
            UPDATE customer_users_new
            SET country = 'USA'
            WHERE country IS NULL
        """))
        
        # Drop old table
        conn.execute(text("DROP TABLE customer_users"))
        
        # Rename new table
        conn.execute(text("ALTER TABLE customer_users_new RENAME TO customer_users"))
        
        print("Successfully added company_id and country columns to customer_users table")

if __name__ == "__main__":
    upgrade_customer_users() 