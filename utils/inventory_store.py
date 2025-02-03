from models.database import Asset, Accessory, AssetStatus
from utils.db_manager import DatabaseManager
import pandas as pd
from datetime import datetime
import os

class InventoryStore:
    def __init__(self):
        self.db_manager = DatabaseManager()

    def import_from_excel(self, file_path):
        try:
            # Read CSV file
            df = pd.read_csv(file_path)
            
            # Debug: Print column names
            print("CSV columns:", df.columns.tolist())
            
            db_session = self.db_manager.get_session()
            try:
                # Convert DataFrame to inventory items
                for _, row in df.iterrows():
                    # Get serial number from the correct column name
                    serial_num = str(row.get('SERIAL NUMBER', ''))
                    if pd.isna(serial_num):
                        serial_num = ''
                    
                    print(f"Found serial number: {serial_num}")
                    
                    # Convert date if it exists
                    receiving_date = None
                    if 'Receiving date' in row and pd.notna(row['Receiving date']):
                        try:
                            receiving_date = pd.to_datetime(row['Receiving date']).to_pydatetime()
                        except:
                            receiving_date = None

                    # Get cost price if it exists
                    cost_price = None
                    if 'COST PRICE' in row and pd.notna(row['COST PRICE']):
                        try:
                            cost_price = float(row['COST PRICE'])
                        except:
                            cost_price = None

                    # Create new Asset
                    asset = Asset(
                        asset_tag=str(row.get('ASSET TAG', '')),
                        serial_num=serial_num,
                        name=str(row.get('Product', '')),
                        model=str(row.get('MODEL', '')),
                        manufacturer='',  # Add if available in CSV
                        category=str(row.get('Asset Type', '')),
                        status=AssetStatus.IN_STOCK,  # Default status
                        cost_price=cost_price,  # Add cost price
                        specifications={
                            'cpu_type': str(row.get('CPU TYPE', '')),
                            'cpu_cores': str(row.get('CPU CORES', '')),
                            'gpu_cores': str(row.get('GPU CORES', '')),
                            'memory': str(row.get('MEMORY', '')),
                            'harddrive': str(row.get('HARDDRIVE', '')),
                            'charger': str(row.get('CHARGER', '')),
                            'keyboard': str(row.get('Keyboard', '')),
                            'erased': str(row.get('ERASED', '')),
                            'condition': str(row.get('CONDITION', '')),
                            'diag': str(row.get('DIAG', '')),
                        },
                        notes='',
                        hardware_type=str(row.get('HARDWARE TYPE', '')),
                        inventory=str(row.get('INVENTORY', '')),
                        customer=str(row.get('CUSTOMER', '')),
                        country=str(row.get('COUNTRY', '')),
                        receiving_date=receiving_date,
                        keyboard=str(row.get('Keyboard', '')),
                        po=str(row.get('PO', '')),
                        erased=str(row.get('ERASED', '')),
                        condition=str(row.get('CONDITION', '')),
                        diag=str(row.get('DIAG', '')),
                        cpu_type=str(row.get('CPU TYPE', '')),
                        cpu_cores=str(row.get('CPU CORES', '')),
                        gpu_cores=str(row.get('GPU CORES', '')),
                        memory=str(row.get('MEMORY', '')),
                        harddrive=str(row.get('HARDDRIVE', '')),
                        charger=str(row.get('CHARGER', ''))
                    )
                    db_session.add(asset)
                
                db_session.commit()
                return True
            except Exception as e:
                db_session.rollback()
                raise e
            finally:
                db_session.close()
                
        except Exception as e:
            print(f"Error importing CSV file: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

    def get_item(self, item_id):
        db_session = self.db_manager.get_session()
        try:
            return db_session.query(Asset).get(item_id)
        finally:
            db_session.close()

    def get_all_items(self):
        db_session = self.db_manager.get_session()
        try:
            return db_session.query(Asset).all()
        finally:
            db_session.close()

    def update_item(self, item_id, updated_data):
        db_session = self.db_manager.get_session()
        try:
            item = db_session.query(Asset).get(item_id)
            if item:
                for key, value in updated_data.items():
                    setattr(item, key, value)
                item.updated_at = datetime.now()
                db_session.commit()
                return item
            return None
        finally:
            db_session.close()

    def delete_item(self, item_id):
        db_session = self.db_manager.get_session()
        try:
            item = db_session.query(Asset).get(item_id)
            if item:
                db_session.delete(item)
                db_session.commit()
                return True
            return False
        finally:
            db_session.close()

# Create singleton instance
inventory_store = InventoryStore() 