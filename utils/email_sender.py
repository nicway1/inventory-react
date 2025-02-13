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
            'Account Information',
            sender=current_app.config['MAIL_DEFAULT_SENDER'],
            recipients=[user_email]
        )
        
        # Plain text version
        msg.body = f"""
Dear {username},

Your account has been created.

Account Details:
Username: {username}
Password: {password}

Please visit truelog.site to log in.

Regards,
Support Team
"""
        
        # Simple HTML version
        msg.html = f"""
<p>Dear {username},</p>
<p>Your account has been created.</p>
<p>Account Details:<br>
Username: {username}<br>
Password: {password}</p>
<p>Please visit truelog.site to log in.</p>
<p>Regards,<br>
Support Team</p>
"""
        
        mail.send(msg)
        logging.info(f"Welcome email sent successfully to {user_email}")
        return True
    except Exception as e:
        logging.error(f"Error sending email to {user_email}: {str(e)}")
        print(f"Error sending email: {str(e)}")
        return False 