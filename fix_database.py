import sqlite3
import os
import logging

# Set up logging for this module
logger = logging.getLogger(__name__)


def fix_database():
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'inventory.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Check if tech_notes column exists in assets table
        cursor.execute("PRAGMA table_info(assets)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'tech_notes' not in columns:
            logger.info("Adding tech_notes column to assets table...")
            cursor.execute("ALTER TABLE assets ADD COLUMN tech_notes TEXT")
        
        # Check if erased column exists and its type
        if 'erased' in columns:
            logger.info("Converting erased column to TEXT type...")
            # Create new table with correct schema
            cursor.execute("""
                CREATE TABLE assets_new (
                    id INTEGER PRIMARY KEY,
                    asset_tag TEXT,
                    serial_num TEXT,
                    name TEXT,
                    model TEXT,
                    manufacturer TEXT,
                    category TEXT,
                    status TEXT,
                    cost_price REAL,
                    location_id INTEGER,
                    company_id INTEGER,
                    specifications TEXT,
                    notes TEXT,
                    tech_notes TEXT,
                    created_at TIMESTAMP,
                    updated_at TIMESTAMP,
                    assigned_to_id INTEGER,
                    customer_id INTEGER,
                    hardware_type TEXT,
                    inventory TEXT,
                    customer TEXT,
                    country TEXT,
                    asset_type TEXT,
                    receiving_date TIMESTAMP,
                    keyboard TEXT,
                    po TEXT,
                    erased TEXT,
                    condition TEXT,
                    diag TEXT,
                    cpu_type TEXT,
                    cpu_cores INTEGER,
                    gpu_cores INTEGER,
                    memory INTEGER,
                    harddrive INTEGER,
                    charger TEXT
                )
            """)
            
            # Copy data, converting erased to TEXT
            cursor.execute("""
                INSERT INTO assets_new 
                SELECT id, asset_tag, serial_num, name, model, manufacturer, 
                       category, status, cost_price, location_id, company_id,
                       specifications, notes, tech_notes, created_at, updated_at,
                       assigned_to_id, customer_id, hardware_type, inventory,
                       customer, country, asset_type, receiving_date, keyboard,
                       po, CAST(erased AS TEXT), condition, diag, cpu_type,
                       cpu_cores, gpu_cores, memory, harddrive, charger
                FROM assets
            """)
            
            # Drop old table and rename new one
            cursor.execute("DROP TABLE assets")
            cursor.execute("ALTER TABLE assets_new RENAME TO assets")
        
        # Check users table
        cursor.execute("PRAGMA table_info(users)")
        user_columns = [col[1] for col in cursor.fetchall()]
        
        if 'role' not in user_columns:
            logger.info("Adding role column to users table...")
            cursor.execute("ALTER TABLE users ADD COLUMN role TEXT")
        
        conn.commit()
        logger.info("Database schema updated successfully!")
        
    except Exception as e:
        logger.info("Error updating database: {str(e)}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    fix_database() 