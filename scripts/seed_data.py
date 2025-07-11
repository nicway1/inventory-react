from utils.db_manager import DatabaseManager
from models.asset import Asset, AssetStatus
from models.user import User
from datetime import datetime
import logging

# Set up logging for this module
logger = logging.getLogger(__name__)


def seed_assets():
    db = DatabaseManager()
    session = db.get_session()
    
    try:
        # Get the first user's company_id
        user = session.query(User).first()
        if not user or not user.company_id:
            logger.info("No user or company found. Please create a user and company first.")
            return
            
        company_id = user.company_id
        
        # Sample assets
        assets = [
            {
                'asset_tag': 'LAP001',
                'serial_num': 'SN001',
                'name': 'MacBook Pro 16"',
                'model': 'MacBook Pro',
                'manufacturer': 'Apple',
                'category': 'Laptop',
                'status': AssetStatus.IN_STOCK,
                'cost_price': 1200.00,
                'company_id': company_id,
                'specifications': {
                    'cpu': 'M1 Pro',
                    'memory': '16GB',
                    'storage': '512GB SSD'
                }
            },
            {
                'asset_tag': 'LAP002',
                'serial_num': 'SN002',
                'name': 'ThinkPad X1',
                'model': 'X1 Carbon',
                'manufacturer': 'Lenovo',
                'category': 'Laptop',
                'status': AssetStatus.IN_STOCK,
                'cost_price': 900.00,
                'company_id': company_id,
                'specifications': {
                    'cpu': 'Intel i7',
                    'memory': '16GB',
                    'storage': '1TB SSD'
                }
            },
            {
                'asset_tag': 'MON001',
                'serial_num': 'SN003',
                'name': 'Dell UltraSharp',
                'model': 'U2720Q',
                'manufacturer': 'Dell',
                'category': 'Monitor',
                'status': AssetStatus.IN_STOCK,
                'cost_price': 400.00,
                'company_id': company_id,
                'specifications': {
                    'resolution': '4K',
                    'size': '27"',
                    'panel': 'IPS'
                }
            }
        ]
        
        # Add assets to database
        for asset_data in assets:
            asset = Asset(**asset_data)
            session.add(asset)
        
        session.commit()
        logger.info("Sample assets added successfully!")
        
    except Exception as e:
        session.rollback()
        logger.info("Error adding sample assets: {str(e)}")
    finally:
        session.close()

if __name__ == '__main__':
    seed_assets() 