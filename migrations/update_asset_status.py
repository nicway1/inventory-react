import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from models.asset import AssetStatus

def update_asset_statuses():
    engine = create_engine('sqlite:///inventory.db')
    
    # Update existing statuses to match new enum values
    with engine.begin() as conn:  # This automatically handles the transaction
        # Map old values to new display values
        status_updates = [
            ("UPDATE assets SET status = 'In Stock' WHERE status IN ('IN STOCK', 'IN_STOCK')"),
            ("UPDATE assets SET status = 'Ready to Deploy' WHERE status IN ('Ready to Deploy', 'READY_TO_DEPLOY')"),
            ("UPDATE assets SET status = 'Shipped' WHERE status IN ('SHIPPED')"),
            ("UPDATE assets SET status = 'Deployed' WHERE status IN ('DEPLOYED')"),
            ("UPDATE assets SET status = 'Repair' WHERE status IN ('REPAIR')"),
            ("UPDATE assets SET status = 'Archived' WHERE status IN ('ARCHIVED')")
        ]
        
        for update_sql in status_updates:
            conn.execute(text(update_sql))

if __name__ == "__main__":
    update_asset_statuses() 