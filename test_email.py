from app import app
from utils.email_sender import send_welcome_email

def test_email():
    with app.app_context():
        test_recipient = 'nicway88@gmail.com'  # Replace with your test email
        result = send_welcome_email(test_recipient, 'testuser', 'testpass123')
        print(f'Email sent: {result}')

if __name__ == "__main__":
    test_email() 