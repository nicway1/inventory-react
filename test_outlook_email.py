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
            print("🔄 Testing Outlook email configuration...")
            print(f"📧 SMTP Server: {app.config['MAIL_SERVER']}")
            print(f"🔌 Port: {app.config['MAIL_PORT']}")
            print(f"👤 Username: {app.config['MAIL_USERNAME']}")
            print(f"🔐 Using TLS: {app.config['MAIL_USE_TLS']}")
            
            # Create a test message
            msg = Message(
                subject='Test Email from Inventory System',
                recipients=[app.config['MAIL_USERNAME']],  # Send to yourself
                body='This is a test email to verify Outlook configuration is working correctly.',
                sender=app.config['MAIL_DEFAULT_SENDER']
            )
            
            # Try to send the email
            mail.send(msg)
            print("✅ Email sent successfully!")
            print("💡 Check your inbox to confirm the email was received.")
            return True
            
        except Exception as e:
            print(f"❌ Email sending failed: {str(e)}")
            print("\n🔧 Troubleshooting tips:")
            print("1. Make sure you replaced the placeholder values with your actual email and App Password")
            print("2. Verify your App Password is correct (regenerate if needed)")
            print("3. Check that your company allows SMTP connections")
            print("4. Ensure your email has proper permissions for sending")
            return False

if __name__ == "__main__":
    print("📬 Outlook Email Configuration Test")
    print("=" * 40)
    
    if test_outlook_email():
        print("\n🎉 Email configuration is working correctly!")
    else:
        print("\n❗ Email configuration needs to be fixed.")
        print("Please update the email settings in the script and try again.") 