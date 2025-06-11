from flask_mail import Mail, Message
from flask import current_app
import logging
import os
from .microsoft_email import get_microsoft_email_client

mail = Mail()

def _send_email_via_method(to_emails, subject, html_body, text_body=None, attachments=None):
    """
    Send email using the best available method (Microsoft OAuth2 or SMTP)
    """
    # Try Microsoft Graph first if configured
    microsoft_client = get_microsoft_email_client()
    if microsoft_client:
        try:
            return microsoft_client.send_email(
                to_emails=to_emails,
                subject=subject,
                body=text_body or "Please view this email in an HTML-capable client.",
                html_body=html_body,
                attachments=attachments
            )
        except Exception as e:
            logging.warning(f"Microsoft email failed, falling back to SMTP: {e}")
    
    # Fallback to regular SMTP
    if not current_app:
        logging.error("No Flask application context")
        return False
        
    if not current_app.config.get('MAIL_USERNAME') or not current_app.config.get('MAIL_PASSWORD'):
        logging.error("Mail configuration is incomplete")
        return False
    
    # Convert single email to list
    if isinstance(to_emails, str):
        to_emails = [to_emails]
    
    msg = Message(
        subject,
        sender=('TrueLog Inventory', current_app.config['MAIL_DEFAULT_SENDER']),
        recipients=to_emails
    )
    
    if html_body:
        msg.html = html_body
    if text_body:
        msg.body = text_body
        
    # Add attachments if provided
    if attachments:
        for attachment in attachments:
            if isinstance(attachment, str):
                with open(attachment, 'rb') as f:
                    msg.attach(
                        os.path.basename(attachment),
                        'application/octet-stream',
                        f.read()
                    )
    
    mail.send(msg)
    return True

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
        
        result = _send_email_via_method(
            to_emails=user_email,
            subject='Welcome to TrueLog - Your Account Information',
            html_body=msg.html,
            text_body=msg.body
        )
        
        if result:
            logging.info(f"Welcome email sent successfully to {user_email}")
        return result
    except Exception as e:
        logging.error(f"Error sending email to {user_email}: {str(e)}")
        print(f"Error sending email: {str(e)}")
        return False 


def send_mention_notification_email(mentioned_user, commenter, ticket, comment_content):
    """
    Send a Salesforce-style mention notification email when a user is @mentioned
    """
    try:
        logging.info(f"Attempting to send mention notification to {mentioned_user.email}")
        
        if not current_app:
            logging.error("No Flask application context")
            return False
            
        if not mentioned_user.email:
            logging.warning(f"User {mentioned_user.username} has no email address")
            return False
        
        # Clean the comment content for display (remove HTML tags)
        import re
        clean_content = re.sub(r'<span class="mention">(@[^<]+)</span>', r'\1', comment_content)
        clean_content = re.sub(r'<[^>]+>', '', clean_content).strip()
        
        # Truncate content if too long for preview
        content_preview = clean_content[:200] + "..." if len(clean_content) > 200 else clean_content
        
        # Create the ticket URL
        ticket_url = f"https://www.truelog.site/tickets/{ticket.id}"
        
        # Salesforce-style HTML email template
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>You were mentioned</title>
        </head>
        <body style="margin: 0; padding: 0; font-family: 'Salesforce Sans', Arial, sans-serif; background-color: #f3f3f3;">
            <div style="width: 100%; max-width: 600px; margin: 0 auto; background-color: #ffffff;">
                <!-- Header -->
                <div style="background: linear-gradient(90deg, #1589ee 0%, #0176d3 100%); padding: 20px; text-align: center;">
                    <h1 style="color: white; margin: 0; font-size: 24px; font-weight: bold;">TrueLog</h1>
                    <p style="color: #e1f5fe; margin: 5px 0 0 0; font-size: 14px;">Inventory Management System</p>
                </div>
                
                <!-- Main Content -->
                <div style="padding: 30px;">
                    <!-- Notification Icon & Title -->
                    <div style="text-align: center; margin-bottom: 25px;">
                        <div style="display: inline-block; background-color: #0176d3; border-radius: 50%; width: 60px; height: 60px; line-height: 60px; margin-bottom: 15px;">
                            <span style="color: white; font-size: 24px; font-weight: bold;">@</span>
                        </div>
                        <h2 style="color: #16325c; margin: 0; font-size: 22px; font-weight: 600;">You were mentioned</h2>
                    </div>
                    
                    <!-- User Info -->
                    <div style="background-color: #fafbfc; border-left: 4px solid #0176d3; padding: 20px; margin-bottom: 25px; border-radius: 0 4px 4px 0;">
                        <p style="margin: 0 0 10px 0; color: #16325c; font-size: 16px;">
                            <strong>{commenter.username}</strong> mentioned you in Case <strong>{ticket.display_id}</strong>
                        </p>
                        <p style="margin: 0; color: #706e6b; font-size: 14px;">
                            <strong>Case Subject:</strong> {ticket.subject}
                        </p>
                    </div>
                    
                    <!-- Comment Preview -->
                    <div style="background-color: #ffffff; border: 1px solid #dddbda; border-radius: 4px; padding: 20px; margin-bottom: 25px;">
                        <h3 style="margin: 0 0 15px 0; color: #16325c; font-size: 16px; font-weight: 600; border-bottom: 1px solid #dddbda; padding-bottom: 10px;">
                            💬 Comment
                        </h3>
                        <div style="background-color: #f8f9fa; border-radius: 4px; padding: 15px; font-style: italic; color: #3e3e3c; line-height: 1.5;">
                            "{content_preview}"
                        </div>
                    </div>
                    
                    <!-- Case Details -->
                    <div style="background-color: #fafbfc; border-radius: 4px; padding: 20px; margin-bottom: 25px;">
                        <h3 style="margin: 0 0 15px 0; color: #16325c; font-size: 16px; font-weight: 600;">📋 Case Details</h3>
                        <table style="width: 100%; border-collapse: collapse;">
                            <tr>
                                <td style="padding: 8px 0; color: #706e6b; font-size: 14px; font-weight: 600; width: 30%;">Case ID:</td>
                                <td style="padding: 8px 0; color: #16325c; font-size: 14px;">{ticket.display_id}</td>
                            </tr>
                            <tr>
                                <td style="padding: 8px 0; color: #706e6b; font-size: 14px; font-weight: 600;">Status:</td>
                                <td style="padding: 8px 0; color: #16325c; font-size: 14px;">
                                    <span style="background-color: #0176d3; color: white; padding: 2px 8px; border-radius: 12px; font-size: 12px; font-weight: bold;">
                                        {ticket.status.value if hasattr(ticket.status, 'value') else ticket.status}
                                    </span>
                                </td>
                            </tr>
                            <tr>
                                <td style="padding: 8px 0; color: #706e6b; font-size: 14px; font-weight: 600;">Priority:</td>
                                <td style="padding: 8px 0; color: #16325c; font-size: 14px;">
                                    <span style="background-color: #ff6b6b; color: white; padding: 2px 8px; border-radius: 12px; font-size: 12px; font-weight: bold;">
                                        {ticket.priority.value if hasattr(ticket.priority, 'value') else ticket.priority}
                                    </span>
                                </td>
                            </tr>
                        </table>
                    </div>
                    
                    <!-- Call to Action -->
                    <div style="text-align: center; margin-bottom: 25px;">
                        <a href="{ticket_url}" 
                           style="display: inline-block; background: linear-gradient(90deg, #1589ee 0%, #0176d3 100%); color: white; padding: 14px 32px; text-decoration: none; border-radius: 4px; font-weight: bold; font-size: 16px; box-shadow: 0 2px 4px rgba(1, 118, 211, 0.3);">
                            View Case & Reply
                        </a>
                    </div>
                    
                    <!-- Help Text -->
                    <div style="background-color: #fff9e6; border: 1px solid #ffeb3b; border-radius: 4px; padding: 15px; margin-bottom: 25px;">
                        <p style="margin: 0; color: #856404; font-size: 14px; text-align: center;">
                            💡 <strong>Tip:</strong> Click the button above to respond to this mention and keep the conversation going.
                        </p>
                    </div>
                </div>
                
                <!-- Footer -->
                <div style="background-color: #16325c; padding: 20px; text-align: center;">
                    <p style="color: #ffffff; margin: 0 0 10px 0; font-size: 14px;">
                        This notification was sent because you were mentioned in a case comment.
                    </p>
                    <p style="color: #a8b8c8; margin: 0; font-size: 12px;">
                        TrueLog Inventory Management System<br>
                        © 2025 TrueLog. All rights reserved.
                    </p>
                </div>
            </div>
        </body>
        </html>
        """
        
        # Plain text version as fallback
        text_body = f"""You were mentioned in Case {ticket.display_id}

{commenter.username} mentioned you in a case comment:

Case: {ticket.display_id} - {ticket.subject}
Status: {ticket.status.value if hasattr(ticket.status, 'value') else ticket.status}
Priority: {ticket.priority.value if hasattr(ticket.priority, 'value') else ticket.priority}

Comment:
"{content_preview}"

View the case and reply: {ticket_url}

---
TrueLog Inventory Management System
This notification was sent because you were mentioned in a case comment."""
        
        result = _send_email_via_method(
            to_emails=mentioned_user.email,
            subject=f'You were mentioned in Case {ticket.display_id}',
            html_body=html_body,
            text_body=text_body
        )
        
        if result:
            logging.info(f"Mention notification email sent successfully to {mentioned_user.email}")
        return result
        
    except Exception as e:
        logging.error(f"Error sending mention notification email to {mentioned_user.email if mentioned_user else 'unknown'}: {str(e)}")
        print(f"Error sending mention notification email: {str(e)}")
        import traceback
        traceback.print_exc()
        return False 