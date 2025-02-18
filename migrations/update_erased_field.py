import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text

def update_erased_field():
    engine = create_engine('sqlite:///inventory.db')
    
    with engine.begin() as conn:
        # Create new table with the desired schema
        conn.execute(text("""
            CREATE TABLE assets_new (
                id INTEGER PRIMARY KEY,
                asset_tag VARCHAR(50) NOT NULL,
                serial_num VARCHAR(50),
                name VARCHAR(100),
                model VARCHAR(100),
                manufacturer VARCHAR(100),
                category VARCHAR(50),
                status VARCHAR(50),
                cost_price FLOAT,
                location_id INTEGER,
                company_id INTEGER,
                specifications JSON,
                notes VARCHAR(1000),
                created_at DATETIME,
                updated_at DATETIME,
                assigned_to_id INTEGER,
                customer_id INTEGER,
                hardware_type VARCHAR(100),
                inventory VARCHAR(50),
                customer VARCHAR(100),
                country VARCHAR(100),
                asset_type VARCHAR(100),
                receiving_date DATETIME,
                keyboard VARCHAR(100),
                po VARCHAR(100),
                erased BOOLEAN DEFAULT FALSE,
                condition VARCHAR(100),
                diag VARCHAR(1000),
                cpu_type VARCHAR(100),
                cpu_cores VARCHAR(100),
                gpu_cores VARCHAR(100),
                memory VARCHAR(100),
                harddrive VARCHAR(100),
                charger VARCHAR(100),
                FOREIGN KEY(location_id) REFERENCES locations(id),
                FOREIGN KEY(company_id) REFERENCES companies(id),
                FOREIGN KEY(assigned_to_id) REFERENCES users(id),
                FOREIGN KEY(customer_id) REFERENCES customer_users(id)
            )
        """))
        
        # Copy data from old table to new table, converting erased to boolean
        conn.execute(text("""
            INSERT INTO assets_new 
            SELECT 
                id, asset_tag, serial_num, name, model, manufacturer, category, 
                status, cost_price, location_id, company_id, specifications, notes,
                created_at, updated_at, assigned_to_id, customer_id, hardware_type,
                inventory, customer, country, asset_type, receiving_date, keyboard,
                po, CASE WHEN erased = 'true' THEN 1 ELSE 0 END, condition, diag,
                cpu_type, cpu_cores, gpu_cores, memory, harddrive, charger
            FROM assets
        """))
        
        # Drop old table and rename new table
        conn.execute(text("DROP TABLE assets"))
        conn.execute(text("ALTER TABLE assets_new RENAME TO assets"))

if __name__ == "__main__":
    update_erased_field() 