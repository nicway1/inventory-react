from utils.db_manager import DatabaseManager
from models.asset import Asset, AssetStatus
from models.accessory import Accessory
import pandas as pd
from datetime import datetime
import os
import logging

# Set up logging for this module
logger = logging.getLogger(__name__)


class InventoryStore:
    def __init__(self):
        self.db_manager = DatabaseManager()

    def import_from_excel(self, file_path):
        try:
            # Read CSV file
            df = pd.read_csv(file_path)
            
            # Debug: Print column names
            logger.info("CSV columns:", df.columns.tolist())
            
            db_session = self.db_manager.get_session()
            try:
                # Convert DataFrame to inventory items
                for _, row in df.iterrows():
                    # Get serial number from the correct column name
                    serial_num = str(row.get('SERIAL NUMBER', ''))
                    if pd.isna(serial_num):
                        serial_num = ''
                    
                    logger.info("Found serial number: {serial_num}")
                    
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
            logger.info("Error importing CSV file: {str(e)}")
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

    def get_all_assets(self):
        """Get all assets (alias for get_all_items for API compatibility)"""
        db_session = self.db_manager.get_session()
        try:
            # Query only the columns we need to avoid relationship loading
            from sqlalchemy import text
            result = db_session.execute(text("""
                SELECT id, name, asset_tag, serial_num, model, status, location_id, 
                       created_at, updated_at, notes, cost_price, manufacturer
                FROM assets
            """))
            
            # Create simple objects from the raw data
            assets = []
            for row in result:
                asset = type('Asset', (), {})()
                asset.id = row.id
                asset.name = row.name
                asset.asset_tag = row.asset_tag
                asset.serial_number = row.serial_num
                asset.model = row.model
                asset.status = row.status
                asset.location_id = row.location_id
                asset.created_at = row.created_at
                asset.updated_at = row.updated_at
                asset.description = row.notes
                asset.cost_price = row.cost_price
                asset.manufacturer = row.manufacturer
                assets.append(asset)
            
            return assets
        finally:
            db_session.close()

    def get_asset_by_id(self, asset_id):
        """Get a specific asset by ID (alias for get_item for API compatibility)"""
        db_session = self.db_manager.get_session()
        try:
            # Query only the columns we need to avoid relationship loading
            from sqlalchemy import text
            result = db_session.execute(text("""
                SELECT id, name, asset_tag, serial_num, model, status, location_id, 
                       created_at, updated_at, notes, cost_price, manufacturer
                FROM assets
                WHERE id = :asset_id
            """), {"asset_id": asset_id})
            
            row = result.first()
            if row:
                asset = type('Asset', (), {})()
                asset.id = row.id
                asset.name = row.name
                asset.asset_tag = row.asset_tag
                asset.serial_number = row.serial_num
                asset.model = row.model
                asset.status = row.status
                asset.location_id = row.location_id
                asset.created_at = row.created_at
                asset.updated_at = row.updated_at
                asset.description = row.notes
                asset.cost_price = row.cost_price
                asset.manufacturer = row.manufacturer
                return asset
            
            return None
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

    def get_available_assets(self):
        """Get all assets that are available for assignment to tickets"""
        db_session = self.db_manager.get_session()
        try:
            # Get assets that are in stock or ready to deploy
            available_assets = db_session.query(Asset).filter(
                Asset.status.in_([AssetStatus.IN_STOCK, AssetStatus.READY_TO_DEPLOY])
            ).all()
            return available_assets
        finally:
            db_session.close()

    def get_available_accessories(self):
        """Get all accessories that have available quantity"""
        db_session = self.db_manager.get_session()
        try:
            # Get accessories with available quantity > 0
            available_accessories = db_session.query(Accessory).filter(
                Accessory.available_quantity > 0
            ).all()
            return available_accessories
        finally:
            db_session.close()

    def assign_asset_to_ticket(self, asset_id, ticket_id):
        """Assign an asset to a ticket and update its status"""
        db_session = self.db_manager.get_session()
        try:
            asset = db_session.query(Asset).get(asset_id)
            if asset:
                # Update asset status to indicate it's assigned
                asset.status = AssetStatus.DEPLOYED
                db_session.commit()
                return True
            return False
        finally:
            db_session.close()

    def assign_accessory_to_ticket(self, accessory_id, ticket_id, quantity=1):
        """Assign an accessory to a ticket and update its quantity"""
        db_session = self.db_manager.get_session()
        try:
            accessory = db_session.query(Accessory).get(accessory_id)
            if accessory:
                # Update available quantity
                accessory.available_quantity += quantity
                db_session.commit()
                return True
            return False
        finally:
            db_session.close()

# Create singleton instance
inventory_store = InventoryStore() 