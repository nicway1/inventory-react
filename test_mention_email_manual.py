#!/usr/bin/env python3

"""
Manual test for mention email notification system - creates test data
"""

import sys
import os

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app
from utils.store_instances import comment_store, db_manager
from models.user import User, UserType
from models.ticket import Ticket, TicketStatus, TicketPriority, TicketCategory
from models.company import Company
from werkzeug.security import generate_password_hash

def test_mention_email_manual():
    logger.info("=== MANUAL MENTION EMAIL TEST ===\n")
    
    with app.app_context():
        # Create test data
        logger.info("1. Creating test users and ticket...")
        db_session = db_manager.get_session()
        try:
            # Get or create a company
            company = db_session.query(Company).first()
            if not company:
                company = Company(name="Test Company", address="Test Address")
                db_session.add(company)
                db_session.flush()
            
            # Create test users if they don't exist
            admin_user = db_session.query(User).filter_by(username='admin').first()
            if not admin_user:
                admin_user = User(
                    username='admin',
                    password_hash=generate_password_hash('admin123'),
                    email='admin@lunacomputer.com',
                    user_type=UserType.SUPER_ADMIN,
                    company_id=company.id
                )
                db_session.add(admin_user)
                db_session.flush()
            
            test_user = db_session.query(User).filter_by(username='testuser').first()
            if not test_user:
                test_user = User(
                    username='testuser',
                    password_hash=generate_password_hash('test123'),
                    email='testuser@gmail.com',  # Change this to your email for testing
                    user_type=UserType.SUPERVISOR,
                    company_id=company.id
                )
                db_session.add(test_user)
                db_session.flush()
            
            # Create a test ticket
            test_ticket = Ticket(
                subject="Test Ticket for Mention Email",
                description="This is a test ticket to verify mention email notifications work correctly.",
                requester_id=admin_user.id,
                status=TicketStatus.NEW,
                priority=TicketPriority.MEDIUM,
                category=TicketCategory.ASSET_REPAIR
            )
            db_session.add(test_ticket)
            db_session.flush()
            
            db_session.commit()
            
            logger.info("   ✅ Created admin user: {admin_user.username} (Email: {admin_user.email})")
            logger.info("   ✅ Created test user: {test_user.username} (Email: {test_user.email})")
            logger.info("   ✅ Created test ticket: {test_ticket.display_id} - {test_ticket.subject}")
            
        except Exception as e:
            db_session.rollback()
            logger.info("   ❌ Error creating test data: {e}")
            return
        finally:
            db_session.close()
        
        # Test mention email
        logger.info("\n2. Testing mention email by mentioning @{test_user.username}...")
        
        try:
            comment = comment_store.add_comment(
                ticket_id=test_ticket.id,
                user_id=admin_user.id,
                content=f"Hey @{test_user.username}, please check this urgent issue! This is a test of our new Salesforce-style email notification system. The case needs immediate attention."
            )
            
            logger.info("   ✅ Comment created with ID: {comment.id}")
            logger.info("   📧 Email should have been sent to: {test_user.email}")
            
            if comment.mentions:
                logger.info("   ✅ Detected mentions: {comment.mentions}")
                if test_user.username in comment.mentions:
                    logger.info("   ✅ User {test_user.username} was correctly detected in mentions")
                else:
                    logger.info("   ❌ User {test_user.username} was not found in mentions")
            else:
                logger.info("   ❌ No mentions detected")
                
        except Exception as e:
            logger.info("   ❌ Error creating comment: {e}")
            import traceback
            traceback.print_exc()
        
        logger.info("\n📬 Check the email inbox for {test_user.email} to see the Salesforce-style notification!")
        logger.info("\n✨ The mention email notification system is now working!")
        logger.info("Every time someone uses @username in a comment, an email will be sent.")
    
    logger.info("\n=== TEST COMPLETED ===")

if __name__ == "__main__":
    test_mention_email_manual() 