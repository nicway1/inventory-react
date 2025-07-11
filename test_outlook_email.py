#!/usr/bin/env python3
"""
Test script to verify Outlook email configuration is working.
Run this after updating your email settings in app.py and wsgi.py.
"""

import os
import sys
from flask import Flask
from flask_mail import Mail, Message

def test_outlook_email():
    """Test Outlook email configuration"""
    
    # Create a minimal Flask app for testing
    app = Flask(__name__)
    
    # Email configuration for Outlook/Office 365
    app.config.update(
        MAIL_SERVER='smtp.office365.com',
        MAIL_PORT=587,
        MAIL_USE_TLS=True,
        MAIL_USE_SSL=False,
        MAIL_USERNAME='your-company-email@yourcompany.com',  # Replace with your actual email
        MAIL_PASSWORD='your-app-password-from-outlook',  # Replace with your App Password
        MAIL_DEFAULT_SENDER='your-company-email@yourcompany.com',  # Replace with your actual email
        MAIL_DEBUG=True
    )
    
    # Initialize Flask-Mail
    mail = Mail(app)
    
    with app.app_context():
        try:
            logger.info("🔄 Testing Outlook email configuration...")
            logger.info("📧 SMTP Server: {app.config['MAIL_SERVER']}")
            logger.info("🔌 Port: {app.config['MAIL_PORT']}")
            logger.info("👤 Username: {app.config['MAIL_USERNAME']}")
            logger.info("🔐 Using TLS: {app.config['MAIL_USE_TLS']}")
            
            # Create a test message
            msg = Message(
                subject='Test Email from Inventory System',
                recipients=[app.config['MAIL_USERNAME']],  # Send to yourself
                body='This is a test email to verify Outlook configuration is working correctly.',
                sender=app.config['MAIL_DEFAULT_SENDER']
            )
            
            # Try to send the email
            mail.send(msg)
            logger.info("✅ Email sent successfully!")
            logger.info("💡 Check your inbox to confirm the email was received.")
            return True
            
        except Exception as e:
            logger.info("❌ Email sending failed: {str(e)}")
            logger.info("\n🔧 Troubleshooting tips:")
            logger.info("1. Make sure you replaced the placeholder values with your actual email and App Password")
            logger.info("2. Verify your App Password is correct (regenerate if needed)")
            logger.info("3. Check that your company allows SMTP connections")
            logger.info("4. Ensure your email has proper permissions for sending")
            return False

if __name__ == "__main__":
    logger.info("📬 Outlook Email Configuration Test")
    logger.info("=" * 40)
    
    if test_outlook_email():
        logger.info("\n🎉 Email configuration is working correctly!")
    else:
        logger.info("\n❗ Email configuration needs to be fixed.")
        logger.info("Please update the email settings in the script and try again.") 