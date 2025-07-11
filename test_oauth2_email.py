#!/usr/bin/env python3
"""
Test script for OAuth2 email configuration using Microsoft Graph API.
Run this after setting up your Azure AD app registration.
"""

import os
import sys
from flask import Flask
from utils.oauth2_email_sender import OAuth2Mail

def test_oauth2_email():
    """Test OAuth2 email configuration"""
    
    logger.info("🔄 Testing OAuth2 email configuration...")
    
    # Create a minimal Flask app for testing
    app = Flask(__name__)
    
    # OAuth2 configuration - Replace these with your actual values
    app.config.update(
        OAUTH2_CLIENT_ID='your-azure-client-id',  # Replace with your Application (client) ID
        OAUTH2_CLIENT_SECRET='your-azure-client-secret',  # Replace with your Client secret
        OAUTH2_TENANT_ID='your-azure-tenant-id',  # Replace with your Directory (tenant) ID
        OAUTH2_DEFAULT_SENDER='your-company-email@yourcompany.com',  # Replace with your email
    )
    
    # Initialize OAuth2 Mail
    oauth2_mail = OAuth2Mail()
    oauth2_mail.init_app(app)
    
    with app.app_context():
        try:
            logger.info("🏢 Tenant ID: {app.config['OAUTH2_TENANT_ID']}")
            logger.info("📱 Client ID: {app.config['OAUTH2_CLIENT_ID']}")
            logger.info("👤 Default Sender: {app.config['OAUTH2_DEFAULT_SENDER']}")
            print()
            
            # Test connection first
            logger.info("🔗 Testing OAuth2 connection...")
            if not oauth2_mail.test_connection():
                logger.info("❌ OAuth2 connection failed!")
                logger.info("\n🔧 Troubleshooting tips:")
                logger.info("1. Verify your Client ID, Client Secret, and Tenant ID are correct")
                logger.info("2. Make sure you've granted admin consent for the API permissions")
                logger.info("3. Check that your app registration has 'Mail.Send' application permission")
                logger.info("4. Ensure your client secret hasn't expired")
                return False
            
            logger.info("✅ OAuth2 connection successful!")
            print()
            
            # Test sending email
            logger.info("📧 Sending test email...")
            success = oauth2_mail.send(
                to_emails=[app.config['OAUTH2_DEFAULT_SENDER']],  # Send to yourself
                subject='OAuth2 Test Email from Inventory System',
                body='''This is a test email sent using OAuth2 and Microsoft Graph API.

If you received this email, your OAuth2 configuration is working correctly!

Configuration Details:
- Method: Microsoft Graph API
- Authentication: OAuth2 (Client Credentials Flow)
- Permissions: Application-level Mail.Send

This is more secure than using SMTP with app passwords.''',
                from_email=app.config['OAUTH2_DEFAULT_SENDER']
            )
            
            if success:
                logger.info("✅ Email sent successfully using OAuth2!")
                logger.info("💡 Check your inbox to confirm the email was received.")
                return True
            else:
                logger.info("❌ Email sending failed!")
                return False
                
        except Exception as e:
            logger.info("❌ Test failed with error: {str(e)}")
            logger.info("\n🔧 Common issues:")
            logger.info("1. Missing or incorrect Azure AD configuration")
            logger.info("2. Insufficient API permissions")
            logger.info("3. Network connectivity issues")
            logger.info("4. Invalid email address format")
            return False

def show_setup_instructions():
    """Show setup instructions for Azure AD"""
    logger.info("\n📋 OAuth2 Setup Instructions:")
    logger.info("=" * 50)
    print()
    logger.info("1. 🌐 Register App in Azure AD:")
    logger.info("   - Go to: https://portal.azure.com")
    logger.info("   - Search for 'App registrations'")
    logger.info("   - Click 'New registration'")
    logger.info("   - Name: 'Inventory System Email'")
    logger.info("   - Account types: 'Single tenant'")
    print()
    logger.info("2. 🔑 Configure API Permissions:")
    logger.info("   - Go to 'API permissions'")
    logger.info("   - Add 'Microsoft Graph' -> 'Application permissions'")
    logger.info("   - Add 'Mail.Send' permission")
    logger.info("   - Click 'Grant admin consent'")
    print()
    logger.info("3. 🔐 Create Client Secret:")
    logger.info("   - Go to 'Certificates & secrets'")
    logger.info("   - Create new client secret")
    logger.info("   - Copy the secret value immediately!")
    print()
    logger.info("4. 📝 Get Required Values:")
    logger.info("   - Application (client) ID")
    logger.info("   - Directory (tenant) ID")
    logger.info("   - Client secret value")
    print()
    logger.info("5. ✏️  Update Configuration:")
    logger.info("   - Replace values in this test script")
    logger.info("   - Update app.py and wsgi.py with the same values")

if __name__ == "__main__":
    logger.info("🔐 OAuth2 Email Configuration Test")
    logger.info("=" * 40)
    
    # Check if configuration looks like defaults
    test_app = Flask(__name__)
    test_app.config.update(
        OAUTH2_CLIENT_ID='your-azure-client-id',
        OAUTH2_CLIENT_SECRET='your-azure-client-secret',
        OAUTH2_TENANT_ID='your-azure-tenant-id',
    )
    
    if (test_app.config['OAUTH2_CLIENT_ID'] == 'your-azure-client-id' or
        test_app.config['OAUTH2_CLIENT_SECRET'] == 'your-azure-client-secret' or
        test_app.config['OAUTH2_TENANT_ID'] == 'your-azure-tenant-id'):
        
        logger.info("⚠️  Configuration contains placeholder values!")
        logger.info("Please update the values in this script first.")
        show_setup_instructions()
    else:
        if test_oauth2_email():
            logger.info("\n🎉 OAuth2 email configuration is working correctly!")
            logger.info("You can now use OAuth2 for sending emails in your inventory system.")
        else:
            logger.info("\n❗ OAuth2 email configuration needs to be fixed.")
            show_setup_instructions() 