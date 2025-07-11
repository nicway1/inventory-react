from app import app
from utils.email_sender import send_welcome_email
import logging

# Set up logging for this module
logger = logging.getLogger(__name__)


def test_welcome_email():
    with app.app_context():
        result = send_welcome_email('nicway1@gmail.com', 'tom', 'newpassword123')
        logger.info(f\'Welcome email sent: {result}\')

if __name__ == '__main__':
    test_welcome_email() 