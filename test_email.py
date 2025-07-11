from app import app
from utils.email_sender import send_welcome_email
import logging

# Set up logging for this module
logger = logging.getLogger(__name__)


def test_email():
    with app.app_context():
        # Test with your email address - replace with your actual email for testing
        test_recipient = 'support@truelog.com.sg'  # Test with your own email first
        username = 'testuser'
        password = 'testpass123'
        
        logger.info("Testing SMTP configuration...")
        logger.info("Server: {app.config['MAIL_SERVER']}")
        logger.info("Port: {app.config['MAIL_PORT']}")
        logger.info("Username: {app.config['MAIL_USERNAME']}")
        logger.info("Default Sender: {app.config['MAIL_DEFAULT_SENDER']}")
        logger.info("Use TLS: {app.config['MAIL_USE_TLS']}")
        logger.info("Use OAuth2: {app.config['USE_OAUTH2_EMAIL']}")
        logger.info("Password (first 4 chars): {app.config['MAIL_PASSWORD'][:4]}...")
        logger.info("")
        
        result = send_welcome_email(test_recipient, username, password)
        logger.info(f\'Email sent successfully: {result}\')
        
        if result:
            logger.info("✅ SMTP configuration is working correctly!")
        else:
            logger.info("❌ SMTP configuration failed.")
            logger.info("\n🔧 Troubleshooting suggestions:")
            logger.info("1. Verify the app password is exactly: gpptrsvqcrtzcvqc")
            logger.info("2. Make sure you generated the app password for support@truelog.com.sg")
            logger.info("3. Try generating a new app password")
            logger.info("4. Check if 2FA is enabled on the account")

if __name__ == '__main__':
    test_email() 