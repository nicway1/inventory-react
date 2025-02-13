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
        
        # HTML version of the email
        msg.html = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="text-align: center; margin-bottom: 30px;">
                <h1 style="color: #2563eb;">Welcome to TrueLog</h1>
            </div>
            
            <p style="color: #374151; font-size: 16px; margin-bottom: 20px;">Hello {username},</p>
            
            <p style="color: #374151; font-size: 16px; margin-bottom: 20px;">
                Your TrueLog Inventory Management account has been created successfully. You can now access the system using the credentials below.
            </p>
            
            <div style="background-color: #f3f4f6; padding: 20px; border-radius: 8px; margin-bottom: 25px;">
                <h2 style="color: #1f2937; font-size: 18px; margin-bottom: 15px;">Your Access Details</h2>
                <ul style="list-style: none; padding: 0; margin: 0;">
                    <li style="margin-bottom: 10px;">
                        <strong>Website:</strong> 
                        <a href="https://www.truelog.site" style="color: #2563eb; text-decoration: none;">truelog.site</a>
                    </li>
                    <li style="margin-bottom: 10px;"><strong>Username:</strong> {username}</li>
                    <li style="margin-bottom: 10px;"><strong>Password:</strong> {password}</li>
                </ul>
            </div>
            
            <div style="text-align: center; margin-bottom: 25px;">
                <a href="https://www.truelog.site" 
                   style="background-color: #2563eb; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: bold;">
                    Login to TrueLog
                </a>
            </div>
            
            <div style="border-left: 4px solid #fde68a; padding: 10px 15px; background-color: #fef3c7; margin-bottom: 25px;">
                <p style="color: #92400e; margin: 0;">
                    <strong>Security Note:</strong> For your security, please change your password after your first login.
                </p>
            </div>
            
            <p style="color: #374151; font-size: 16px; margin-bottom: 10px;">
                If you have any questions or need assistance, please don't hesitate to contact our support team.
            </p>
            
            <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #e5e7eb;">
                <p style="color: #6b7280; font-size: 14px; margin: 0;">
                    Best regards,<br>
                    TrueLog Support Team
                </p>
            </div>
        </div>
        """
        
        # Plain text version as fallback
        msg.body = f"""Hello {username},

Welcome to TrueLog! Your account has been created successfully.

Access Details:
- Website: https://www.truelog.site
- Username: {username}
- Password: {password}

For security reasons, please change your password after your first login.

If you need any assistance, please contact our support team.

Best regards,
TrueLog Support Team"""
        
        mail.send(msg)
        logging.info(f"Welcome email sent successfully to {user_email}")
        return True
    except Exception as e:
        logging.error(f"Error sending email to {user_email}: {str(e)}")
        print(f"Error sending email: {str(e)}")
        return False 