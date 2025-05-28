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
    
    print("🔄 Testing OAuth2 email configuration...")
    
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
            print(f"🏢 Tenant ID: {app.config['OAUTH2_TENANT_ID']}")
            print(f"📱 Client ID: {app.config['OAUTH2_CLIENT_ID']}")
            print(f"👤 Default Sender: {app.config['OAUTH2_DEFAULT_SENDER']}")
            print()
            
            # Test connection first
            print("🔗 Testing OAuth2 connection...")
            if not oauth2_mail.test_connection():
                print("❌ OAuth2 connection failed!")
                print("\n🔧 Troubleshooting tips:")
                print("1. Verify your Client ID, Client Secret, and Tenant ID are correct")
                print("2. Make sure you've granted admin consent for the API permissions")
                print("3. Check that your app registration has 'Mail.Send' application permission")
                print("4. Ensure your client secret hasn't expired")
                return False
            
            print("✅ OAuth2 connection successful!")
            print()
            
            # Test sending email
            print("📧 Sending test email...")
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
                print("✅ Email sent successfully using OAuth2!")
                print("💡 Check your inbox to confirm the email was received.")
                return True
            else:
                print("❌ Email sending failed!")
                return False
                
        except Exception as e:
            print(f"❌ Test failed with error: {str(e)}")
            print("\n🔧 Common issues:")
            print("1. Missing or incorrect Azure AD configuration")
            print("2. Insufficient API permissions")
            print("3. Network connectivity issues")
            print("4. Invalid email address format")
            return False

def show_setup_instructions():
    """Show setup instructions for Azure AD"""
    print("\n📋 OAuth2 Setup Instructions:")
    print("=" * 50)
    print()
    print("1. 🌐 Register App in Azure AD:")
    print("   - Go to: https://portal.azure.com")
    print("   - Search for 'App registrations'")
    print("   - Click 'New registration'")
    print("   - Name: 'Inventory System Email'")
    print("   - Account types: 'Single tenant'")
    print()
    print("2. 🔑 Configure API Permissions:")
    print("   - Go to 'API permissions'")
    print("   - Add 'Microsoft Graph' -> 'Application permissions'")
    print("   - Add 'Mail.Send' permission")
    print("   - Click 'Grant admin consent'")
    print()
    print("3. 🔐 Create Client Secret:")
    print("   - Go to 'Certificates & secrets'")
    print("   - Create new client secret")
    print("   - Copy the secret value immediately!")
    print()
    print("4. 📝 Get Required Values:")
    print("   - Application (client) ID")
    print("   - Directory (tenant) ID")
    print("   - Client secret value")
    print()
    print("5. ✏️  Update Configuration:")
    print("   - Replace values in this test script")
    print("   - Update app.py and wsgi.py with the same values")

if __name__ == "__main__":
    print("🔐 OAuth2 Email Configuration Test")
    print("=" * 40)
    
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
        
        print("⚠️  Configuration contains placeholder values!")
        print("Please update the values in this script first.")
        show_setup_instructions()
    else:
        if test_oauth2_email():
            print("\n🎉 OAuth2 email configuration is working correctly!")
            print("You can now use OAuth2 for sending emails in your inventory system.")
        else:
            print("\n❗ OAuth2 email configuration needs to be fixed.")
            show_setup_instructions() 