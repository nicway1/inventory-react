import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, DateTime, ForeignKey, JSON
from datetime import datetime

def create_asset_history_table():
    engine = create_engine('sqlite:///inventory.db')
    metadata = MetaData()

    # Define the asset_history table
    asset_history = Table('asset_history', metadata,
        Column('id', Integer, primary_key=True),
        Column('asset_id', Integer, ForeignKey('assets.id'), nullable=False),
        Column('user_id', Integer, ForeignKey('users.id'), nullable=False),
        Column('action', String(50), nullable=False),
        Column('changes', JSON),
        Column('notes', String(1000)),
        Column('created_at', DateTime, default=datetime.utcnow)
    )

    # Create the table
    metadata.create_all(engine)
    print("Asset history table created successfully")

if __name__ == "__main__":
    create_asset_history_table() 