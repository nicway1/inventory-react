from flask_mail import Mail, Message
from flask import current_app
import logging
import uuid
from email.utils import make_msgid

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
            sender=current_app.config['MAIL_DEFAULT_SENDER'],
            recipients=[user_email]
        )
        
        # Generate a proper Message-ID with the domain
        msg.msgId = make_msgid(domain='truelog.site')
        
        # Plain text version only - no HTML to avoid spam triggers
        msg.body = f"""
{username}

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