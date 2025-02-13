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
            'Welcome to TrueLog - Your Account Details',
            sender=current_app.config['MAIL_DEFAULT_SENDER'],
            recipients=[user_email]
        )
        
        msg.html = f'''
        <h2>Welcome to TrueLog!</h2>
        <p>Your account has been created successfully. Here are your login details:</p>
        <p><strong>Username:</strong> {username}</p>
        <p><strong>Password:</strong> {password}</p>
        <p><strong>Login URL:</strong> <a href="https://truelog.site">truelog.site</a></p>
        <p>For security reasons, we recommend changing your password after your first login.</p>
        <br>
        <p>If you have any questions or need assistance, please contact your administrator.</p>
        <br>
        <p>Best regards,</p>
        <p>The TrueLog Team</p>
        '''
        
        mail.send(msg)
        logging.info(f"Welcome email sent successfully to {user_email}")
        return True
    except Exception as e:
        logging.error(f"Error sending email to {user_email}: {str(e)}")
        print(f"Error sending email: {str(e)}")
        return False 