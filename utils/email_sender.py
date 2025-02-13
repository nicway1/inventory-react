from flask_mail import Mail, Message
from flask import current_app
import logging
import socket

mail = Mail()

def send_welcome_email(user_email, username, password):
    """
    Send a welcome email to a newly created user with their credentials
    """
    try:
        logging.info(f"Attempting to send welcome email to {user_email}")
        
        if not current_app:
            logging.error("No Flask application context")
            return False
            
        if not current_app.config.get('MAIL_USERNAME') or not current_app.config.get('MAIL_PASSWORD'):
            logging.error("Mail configuration is incomplete")
            return False
            
        msg = Message(
            'TrueLog Access',
            sender=('TrueLog Support', current_app.config['MAIL_DEFAULT_SENDER']),
            recipients=[user_email]
        )
        
        # Add authentication headers
        msg.extra_headers = {
            'X-Originating-IP': '[127.0.0.1]',
            'X-Remote-Host': socket.gethostname(),
            'Received': f'from {socket.gethostname()} (localhost [127.0.0.1]) by mail.privateemail.com',
            'Authentication-Results': 'mail.privateemail.com; auth=pass',
            'MIME-Version': '1.0',
            'Precedence': 'bulk'
        }
        
        # Simple plain text format that worked on PythonAnywhere
        msg.body = f"""{username}

Access: truelog.site
User: {username}
Pass: {password}

Support"""
        
        mail.send(msg)
        logging.info(f"Welcome email sent successfully to {user_email}")
        return True
    except Exception as e:
        logging.error(f"Error sending email to {user_email}: {str(e)}")
        print(f"Error sending email: {str(e)}")
        return False 