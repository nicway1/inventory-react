from models.inventory_item import InventoryItem
import pandas as pd
from datetime import datetime
import json
import os

class InventoryStore:
    def __init__(self):
        self.items = {}
        self.load_items()

    def load_items(self):
        try:
            # Check if data file exists
            if os.path.exists('data/inventory.json'):
                with open('data/inventory.json', 'r') as f:
                    items_data = json.load(f)
                    for item_data in items_data:
                        # Convert string dates back to datetime if they exist
                        if 'receiving_date' in item_data and item_data['receiving_date']:
                            try:
                                item_data['receiving_date'] = datetime.strptime(
                                    item_data['receiving_date'], 
                                    '%Y-%m-%d'
                                )
                            except ValueError:
                                item_data['receiving_date'] = None
                        
                        item = InventoryItem.create(**item_data)
                        self.items[item.id] = item
            print(f"Loaded {len(self.items)} items from storage")
        except Exception as e:
            print(f"Error loading inventory data: {str(e)}")

    def save_items(self):
        try:
            # Ensure data directory exists
            os.makedirs('data', exist_ok=True)
            
            # Convert items to serializable format
            items_data = []
            for item in self.items.values():
                item_dict = {
                    'asset_type': item.asset_type,
                    'product': item.product,
                    'asset_tag': item.asset_tag,
                    'receiving_date': item.receiving_date.strftime('%Y-%m-%d') if item.receiving_date else None,
                    'keyboard': item.keyboard,
                    'serial_num': item.serial_num,
                    'po': item.po,
                    'model': item.model,
                    'erased': item.erased,
                    'customer': item.customer,
                    'condition': item.condition,
                    'diag': item.diag,
                    'hardware_type': item.hardware_type,
                    'cpu_type': item.cpu_type,
                    'cpu_cores': item.cpu_cores,
                    'gpu_cores': item.gpu_cores,
                    'memory': item.memory,
                    'harddrive': item.harddrive,
                    'charger': item.charger,
                    'inventory': item.inventory,
                    'country': item.country
                }
                items_data.append(item_dict)
            
            with open('data/inventory.json', 'w') as f:
                json.dump(items_data, f, indent=2)
            print(f"Saved {len(self.items)} items to storage")
        except Exception as e:
            print(f"Error saving inventory data: {str(e)}")

    def import_from_excel(self, file_path):
        try:
            # Read CSV file
            df = pd.read_csv(file_path)
            
            # Debug: Print column names
            print("CSV columns:", df.columns.tolist())
            
            # Clear existing items
            self.items.clear()
            
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

                item = InventoryItem.create(
                    asset_type=str(row.get('Asset Type', '')),
                    product=str(row.get('Product', '')),
                    asset_tag=str(row.get('ASSET TAG', '')),
                    receiving_date=receiving_date,
                    keyboard=str(row.get('Keyboard', '')),
                    serial_num=serial_num,  # This should now contain the correct serial number
                    po=str(row.get('PO', '')),
                    model=str(row.get('MODEL', '')),
                    erased=str(row.get('ERASED', '')),
                    customer=str(row.get('CUSTOMER', '')),
                    condition=str(row.get('CONDITION', '')),
                    diag=str(row.get('DIAG', '')),
                    hardware_type=str(row.get('HARDWARE TYPE', '')),
                    cpu_type=str(row.get('CPU TYPE', '')),
                    cpu_cores=str(row.get('CPU CORES', '')),
                    gpu_cores=str(row.get('GPU CORES', '')),
                    memory=str(row.get('MEMORY', '')),
                    harddrive=str(row.get('HARDDRIVE', '')),
                    charger=str(row.get('CHARGER', '')),
                    inventory=str(row.get('INVENTORY', '')),
                    country=str(row.get('COUNTRY', ''))
                )
                self.items[item.id] = item
            
            # Save the imported data
            self.save_items()
            return True
        except Exception as e:
            print(f"Error importing CSV file: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

    def add_item(self, item):
        self.items[item.id] = item
        self.save_items()
        return item

    def get_item(self, item_id):
        return self.items.get(item_id)

    def get_all_items(self):
        return list(self.items.values())

    def update_item(self, item_id, **kwargs):
        item = self.get_item(item_id)
        if item:
            for key, value in kwargs.items():
                if hasattr(item, key):
                    setattr(item, key, value)
            item.updated_at = datetime.now()
            self.save_items()
            return True
        return False

    def delete_item(self, item_id):
        if item_id in self.items:
            del self.items[item_id]
            self.save_items()
            return True
        return False

    def assign_item(self, item_id, user_id):
        item = self.items.get(item_id)
        if item:
            item.assigned_to = user_id
            item.status = 'Assigned'
            item.updated_at = datetime.now()
            return item
        return None

    def unassign_item(self, item_id):
        item = self.items.get(item_id)
        if item:
            item.assigned_to = None
            item.status = 'Available'
            item.updated_at = datetime.now()
            return item
        return None

# Create singleton instance
inventory_store = InventoryStore() 