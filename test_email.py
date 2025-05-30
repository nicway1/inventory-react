from app import app
from utils.email_sender import send_welcome_email

def test_email():
    with app.app_context():
        # Test with your email address - replace with your actual email for testing
        test_recipient = 'support@truelog.com.sg'  # Test with your own email first
        username = 'testuser'
        password = 'testpass123'
        
        print("Testing SMTP configuration...")
        print(f"Server: {app.config['MAIL_SERVER']}")
        print(f"Port: {app.config['MAIL_PORT']}")
        print(f"Username: {app.config['MAIL_USERNAME']}")
        print(f"Default Sender: {app.config['MAIL_DEFAULT_SENDER']}")
        print(f"Use TLS: {app.config['MAIL_USE_TLS']}")
        print(f"Use OAuth2: {app.config['USE_OAUTH2_EMAIL']}")
        print(f"Password (first 4 chars): {app.config['MAIL_PASSWORD'][:4]}...")
        print("")
        
        result = send_welcome_email(test_recipient, username, password)
        print(f'Email sent successfully: {result}')
        
        if result:
            print("✅ SMTP configuration is working correctly!")
        else:
            print("❌ SMTP configuration failed.")
            print("\n🔧 Troubleshooting suggestions:")
            print("1. Verify the app password is exactly: gpptrsvqcrtzcvqc")
            print("2. Make sure you generated the app password for support@truelog.com.sg")
            print("3. Try generating a new app password")
            print("4. Check if 2FA is enabled on the account")

if __name__ == '__main__':
    test_email() 