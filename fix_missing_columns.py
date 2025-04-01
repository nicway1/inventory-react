from sqlalchemy import create_engine
from database import engine

def add_missing_columns():
    with engine.connect() as connection:
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
    print("Adding missing columns to database...")
    add_missing_columns()
    print("Column addition completed") 