#!/usr/bin/env python
"""
Migration script to add CLOSED_DUPLICATED custom ticket status
"""

import sys
import os

# Add the parent directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()


# Define the table structure inline
class CustomTicketStatus(Base):
    """Model for custom ticket statuses"""
    __tablename__ = 'custom_ticket_statuses'

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False, unique=True)
    display_name = Column(String(100), nullable=False)
    color = Column(String(20), default='gray')
    is_active = Column(Boolean, default=True)
    is_system = Column(Boolean, default=False)
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)


# Database connection
engine = create_engine('sqlite:///inventory.db')
Session = sessionmaker(bind=engine)
session = Session()

try:
    print("Adding CLOSED_DUPLICATED status...")

    # Check if it already exists
    existing = session.query(CustomTicketStatus).filter(
        CustomTicketStatus.name == "CLOSED_DUPLICATED"
    ).first()

    if existing:
        print(f"⚠️  CLOSED_DUPLICATED status already exists (ID: {existing.id})")
    else:
        # Get max sort_order
        from sqlalchemy import func
        max_order = session.query(func.max(CustomTicketStatus.sort_order)).scalar() or 0

        # Add the new status
        new_status = CustomTicketStatus(
            name="CLOSED_DUPLICATED",
            display_name="Closed - Duplicated",
            color="gray",
            is_active=True,
            is_system=True,  # System status so it can't be deleted
            sort_order=max_order + 1
        )

        session.add(new_status)
        session.commit()

        print("✅ CLOSED_DUPLICATED status added successfully!")
        print(f"   Display Name: {new_status.display_name}")
        print(f"   Color: {new_status.color}")
        print(f"   System Status: Yes (cannot be deleted)")

    print("\n" + "="*60)
    print("Migration completed successfully!")
    print("="*60)

except Exception as e:
    session.rollback()
    print(f"❌ Error: {str(e)}")
    import traceback
    traceback.print_exc()
finally:
    session.close()
