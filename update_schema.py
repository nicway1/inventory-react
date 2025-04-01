from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, Text
from database import Base, engine
from models.ticket import Ticket

def update_schema():
    # Add new columns to the tickets table
    with engine.connect() as connection:
        try:
            # Add shipping_address column
            connection.execute('ALTER TABLE tickets ADD COLUMN shipping_address TEXT')
            print("Added shipping_address column")
        except Exception as e:
            print(f"shipping_address column might already exist: {e}")

        try:
            # Add shipping_tracking column
            connection.execute('ALTER TABLE tickets ADD COLUMN shipping_tracking TEXT')
            print("Added shipping_tracking column")
        except Exception as e:
            print(f"shipping_tracking column might already exist: {e}")

        try:
            # Add customer_id column
            connection.execute('ALTER TABLE tickets ADD COLUMN customer_id INTEGER REFERENCES customer_users(id)')
            print("Added customer_id column")
        except Exception as e:
            print(f"customer_id column might already exist: {e}")

        try:
            # Add shipping_status column
            connection.execute('ALTER TABLE tickets ADD COLUMN shipping_status VARCHAR(20)')
            print("Added shipping_status column")
        except Exception as e:
            print(f"shipping_status column might already exist: {e}")

        try:
            # Add return_status column
            connection.execute('ALTER TABLE tickets ADD COLUMN return_status VARCHAR(20)')
            print("Added return_status column")
        except Exception as e:
            print(f"return_status column might already exist: {e}")

        try:
            # Add replacement_status column
            connection.execute('ALTER TABLE tickets ADD COLUMN replacement_status VARCHAR(20)')
            print("Added replacement_status column")
        except Exception as e:
            print(f"replacement_status column might already exist: {e}")

        try:
            # Add shipping_carrier column
            connection.execute('ALTER TABLE tickets ADD COLUMN shipping_carrier VARCHAR(50) DEFAULT \'singpost\'')
            print("Added shipping_carrier column")
        except Exception as e:
            print(f"shipping_carrier column might already exist: {e}")

        # Add Asset Intake specific fields
        try:
            connection.execute('ALTER TABLE tickets ADD COLUMN packing_list_path VARCHAR(500)')
            print("Added packing_list_path column")
        except Exception as e:
            print(f"packing_list_path column might already exist: {e}")
        
        try:
            connection.execute('ALTER TABLE tickets ADD COLUMN asset_csv_path VARCHAR(500)')
            print("Added asset_csv_path column")
        except Exception as e:
            print(f"asset_csv_path column might already exist: {e}")
        
        try:
            connection.execute('ALTER TABLE tickets ADD COLUMN notes VARCHAR(2000)')
            print("Added notes column")
        except Exception as e:
            print(f"notes column might already exist: {e}")

if __name__ == '__main__':
    print("Updating database schema...")
    update_schema()
    print("Schema update completed") 