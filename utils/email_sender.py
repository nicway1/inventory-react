from flask_mail import Mail, Message
from flask import current_app
import logging

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
            'Welcome to TrueLog - Your Account Information',
            sender=('TrueLog Inventory', current_app.config['MAIL_DEFAULT_SENDER']),
            recipients=[user_email]
        )
        
        # Simple plain text format
        msg.body = f"""Hello {username},

Your TrueLog account has been created successfully.

Access Details:
- Website: truelog.site
- Username: {username}
- Password: {password}

Please change your password after your first login.

Best regards,
TrueLog Support Team"""
        
        mail.send(msg)
        logging.info(f"Welcome email sent successfully to {user_email}")
        return True
    except Exception as e:
        logging.error(f"Error sending email to {user_email}: {str(e)}")
        print(f"Error sending email: {str(e)}")
        return False 