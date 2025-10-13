#!/usr/bin/env python3
"""
Script to create the ticket_issues table for the issue reporting system
"""

from database import engine, Base
from models.ticket_issue import TicketIssue
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_ticket_issues_table():
    """Create the ticket_issues table"""
    logger.info("Creating ticket_issues table...")

    # Import the model to register it with Base
    # This ensures the table schema is known

    # Create only the ticket_issues table
    Base.metadata.create_all(engine, tables=[TicketIssue.__table__])

    logger.info("✅ ticket_issues table created successfully!")
    logger.info("The issue reporting system is now ready to use.")

if __name__ == "__main__":
    create_ticket_issues_table()
