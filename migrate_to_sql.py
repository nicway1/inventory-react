import json
from datetime import datetime
from database import SessionLocal, init_db
from models.asset import Asset
from models.accessory import Accessory
import logging

# Set up logging for this module
logger = logging.getLogger(__name__)


def migrate_data():
    # Initialize database
    init_db()
    db = SessionLocal()

    try:
        # Read JSON data
        with open('data/inventory.json', 'r') as f:
            items = json.load(f)

        # Migrate each item
        for item_data in items:
            # Convert receiving date if it exists
            if item_data.get('receiving_date'):
                try:
                    receiving_date = datetime.strptime(item_data['receiving_date'], '%Y-%m-%d')
                except ValueError:
                    receiving_date = None
            else:
                receiving_date = None

            # Determine if item is an asset or accessory based on type
            if item_data.get('asset_type', '').lower() in ['laptop', 'desktop', 'server', 'tablet']:
                # Create asset
                asset = Asset(
                    asset_type=item_data.get('asset_type', ''),
                    product=item_data.get('product', ''),
                    asset_tag=item_data.get('asset_tag', ''),
                    receiving_date=receiving_date,
                    keyboard=item_data.get('keyboard', ''),
                    serial_num=item_data.get('serial_num', ''),
                    po=item_data.get('po', ''),
                    model=item_data.get('model', ''),
                    erased=item_data.get('erased', ''),
                    customer=item_data.get('customer', ''),
                    condition=item_data.get('condition', ''),
                    diag=item_data.get('diag', ''),
                    hardware_type=item_data.get('hardware_type', ''),
                    cpu_type=item_data.get('cpu_type', ''),
                    cpu_cores=item_data.get('cpu_cores', ''),
                    gpu_cores=item_data.get('gpu_cores', ''),
                    memory=item_data.get('memory', ''),
                    harddrive=item_data.get('harddrive', ''),
                    charger=item_data.get('charger', ''),
                    inventory=item_data.get('inventory', ''),
                    country=item_data.get('country', ''),
                    status='Ready to Deploy'
                )
                db.add(asset)
            else:
                # Create accessory
                accessory = Accessory(
                    name=item_data.get('product', ''),
                    category=item_data.get('asset_type', ''),
                    model=item_data.get('model', ''),
                    manufacturer=item_data.get('hardware_type', ''),
                    serial_num=item_data.get('serial_num', ''),
                    asset_tag=item_data.get('asset_tag', ''),
                    po=item_data.get('po', ''),
                    receiving_date=receiving_date,
                    condition=item_data.get('condition', ''),
                    location=item_data.get('customer', ''),
                    customer=item_data.get('customer', ''),
                    country=item_data.get('country', ''),
                    status='Available',
                    notes=f"Memory: {item_data.get('memory', '')}\nStorage: {item_data.get('harddrive', '')}"
                )
                db.add(accessory)

        # Commit changes
        db.commit()
        logger.info("Migration completed successfully!")

    except Exception as e:
        logger.info("Error during migration: {str(e)}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    migrate_data() 