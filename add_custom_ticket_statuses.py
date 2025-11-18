#!/usr/bin/env python
"""
Migration script to create custom_ticket_statuses table
"""

import sys
import os

# Add the parent directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, MetaData, Table
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
    print("Creating custom_ticket_statuses table...")

    # Create the table
    Base.metadata.create_all(engine)

    print("✅ Table created successfully!")

    # Check if we should add some default custom statuses
    existing_count = session.query(CustomTicketStatus).count()

    if existing_count == 0:
        print("\nAdding sample custom statuses...")

        sample_statuses = [
            CustomTicketStatus(
                name="AWAITING_APPROVAL",
                display_name="Awaiting Approval",
                color="yellow",
                is_active=True,
                is_system=False,
                sort_order=1
            ),
            CustomTicketStatus(
                name="UNDER_REVIEW",
                display_name="Under Review",
                color="blue",
                is_active=True,
                is_system=False,
                sort_order=2
            ),
            CustomTicketStatus(
                name="ESCALATED",
                display_name="Escalated",
                color="red",
                is_active=True,
                is_system=False,
                sort_order=3
            ),
            CustomTicketStatus(
                name="PENDING_CUSTOMER",
                display_name="Pending Customer Response",
                color="purple",
                is_active=True,
                is_system=False,
                sort_order=4
            ),
        ]

        for status in sample_statuses:
            session.add(status)

        session.commit()
        print(f"✅ Added {len(sample_statuses)} sample custom statuses!")

        for status in sample_statuses:
            print(f"  - {status.display_name} ({status.color})")
    else:
        print(f"\nTable already has {existing_count} custom status(es).")

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
