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
            'Your TrueLog Account Information',
            sender=current_app.config['MAIL_DEFAULT_SENDER'],
            recipients=[user_email]
        )
        
        msg.html = f'''
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <p>Dear {username},</p>
            
            <p>Your TrueLog account has been created. Please find your account details below:</p>
            
            <div style="background-color: #f8f9fa; padding: 15px; margin: 15px 0; border-radius: 5px;">
                <p style="margin: 5px 0;">Username: {username}</p>
                <p style="margin: 5px 0;">Temporary Password: {password}</p>
            </div>
            
            <p>Please log in at <a href="https://truelog.site">truelog.site</a> and change your password.</p>
            
            <p>For security purposes, this password should be changed upon your first login.</p>
            
            <p>Regards,<br>TrueLog Support Team</p>
        </div>
        '''
        
        mail.send(msg)
        logging.info(f"Welcome email sent successfully to {user_email}")
        return True
    except Exception as e:
        logging.error(f"Error sending email to {user_email}: {str(e)}")
        print(f"Error sending email: {str(e)}")
        return False 