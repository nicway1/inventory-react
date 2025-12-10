from flask_mail import Mail, Message
from flask import current_app
import logging
import os
from .microsoft_email import get_microsoft_email_client

# Set up logging for this module
logger = logging.getLogger(__name__)


mail = Mail()

def _send_email_via_method(to_emails, subject, html_body, text_body=None, attachments=None):
    """
    Send email using the best available method (Microsoft OAuth2 or SMTP)
    """
    try:
        # Try Microsoft Graph first if configured
        microsoft_client = get_microsoft_email_client()
        if microsoft_client:
            try:
                logging.info(f"Attempting to send email via Microsoft Graph to {to_emails}")
                result = microsoft_client.send_email(
                    to_emails=to_emails,
                    subject=subject,
                    body=text_body or "Please view this email in an HTML-capable client.",
                    html_body=html_body,
                    attachments=attachments
                )
                logging.info(f"Microsoft Graph email sent successfully to {to_emails}")
                return result
            except Exception as e:
                logging.warning(f"Microsoft email failed, falling back to SMTP: {e}", exc_info=True)

        # Fallback to regular SMTP
        if not current_app:
            logging.error("No Flask application context for SMTP email")
            return False

        if not current_app.config.get('MAIL_USERNAME') or not current_app.config.get('MAIL_PASSWORD'):
            logging.error("Mail configuration is incomplete - missing MAIL_USERNAME or MAIL_PASSWORD")
            return False

        # Convert single email to list
        if isinstance(to_emails, str):
            to_emails = [to_emails]

        logging.info(f"Attempting to send email via SMTP to {to_emails}")

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
        logging.info(f"SMTP email sent successfully to {to_emails}")
        return True
    except Exception as e:
        logging.error(f"Failed to send email to {to_emails}: {str(e)}", exc_info=True)
        return False

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
                        <a href="https://inventory.truelog.com.sg" style="color: #2563eb; text-decoration: none;">inventory.truelog.com.sg</a>
                    </li>
                    <li style="margin-bottom: 10px;"><strong>Username:</strong> {username}</li>
                    <li style="margin-bottom: 10px;"><strong>Password:</strong> {password}</li>
                </ul>
            </div>
            
            <div style="text-align: center; margin-bottom: 25px;">
                <a href="https://inventory.truelog.com.sg" 
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
- Website: https://inventory.truelog.com.sg
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
        logger.info("Error sending email: {str(e)}")
        return False 


def send_ticket_assignment_notification(assigned_user, assigner, ticket, previous_assignee=None):
    """
    Send a Salesforce-style ticket assignment notification email
    """
    try:
        logging.info(f"Attempting to send ticket assignment notification to {assigned_user.email}")
        
        if not current_app:
            logging.error("No Flask application context")
            return False
            
        if not assigned_user.email:
            logging.warning(f"User {assigned_user.username} has no email address")
            return False
        
        # Create the ticket URL
        ticket_url = f"https://inventory.truelog.com.sg/tickets/{ticket.id}"
        
        # Determine the action type and message
        action_type = "Ticket Assignment Notification"
        if previous_assignee:
            action_text = f"You have a ticket being assigned to you from {previous_assignee.username}"
        else:
            action_text = "You have a ticket being assigned to you"
        
        # Salesforce-style HTML email template
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{action_type} - {ticket.subject}</title>
        </head>
        <body style="margin: 0; padding: 0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f4f6f9;">
            <div style="max-width: 600px; margin: 0 auto; background-color: #ffffff;">
                <!-- Header -->
                <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px 40px; text-align: center;">
                    <h1 style="color: #ffffff; margin: 0; font-size: 24px; font-weight: 600;">
                        🎫 {action_type}
                    </h1>
                    <p style="color: #e8f0fe; margin: 8px 0 0 0; font-size: 16px;">
                        TrueLog Inventory Management
                    </p>
                </div>
                
                <!-- Main Content -->
                <div style="padding: 40px;">
                    <div style="background-color: #f8f9fa; border-left: 4px solid #667eea; padding: 20px; margin-bottom: 30px; border-radius: 0 8px 8px 0;">
                        <h2 style="color: #1a202c; margin: 0 0 10px 0; font-size: 20px;">
                            Hello {assigned_user.username}!
                        </h2>
                        <p style="color: #4a5568; margin: 0; font-size: 16px; line-height: 1.5;">
                            <strong>{action_text}</strong> by {assigner.username}.
                        </p>
                    </div>
                    
                    <!-- Ticket Details Card -->
                    <div style="border: 1px solid #e2e8f0; border-radius: 12px; overflow: hidden; margin-bottom: 30px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                        <div style="background-color: #667eea; color: white; padding: 15px 20px;">
                            <h3 style="margin: 0; font-size: 16px; font-weight: 600;">📋 Ticket Details</h3>
                        </div>
                        <div style="padding: 20px;">
                            <table style="width: 100%; border-collapse: collapse;">
                                <tr>
                                    <td style="padding: 8px 0; color: #718096; font-weight: 600; width: 120px;">Ticket ID:</td>
                                    <td style="padding: 8px 0; color: #2d3748;">#{ticket.display_id or ticket.id}</td>
                                </tr>
                                <tr>
                                    <td style="padding: 8px 0; color: #718096; font-weight: 600;">Subject:</td>
                                    <td style="padding: 8px 0; color: #2d3748; font-weight: 600;">{ticket.subject}</td>
                                </tr>
                                <tr>
                                    <td style="padding: 8px 0; color: #718096; font-weight: 600;">Priority:</td>
                                    <td style="padding: 8px 0;">
                                        <span style="background-color: {'#fee2e2' if ticket.priority and ticket.priority.value == 'High' else '#fef3c7' if ticket.priority and ticket.priority.value == 'Medium' else '#dcfce7'}; 
                                                     color: {'#dc2626' if ticket.priority and ticket.priority.value == 'High' else '#d97706' if ticket.priority and ticket.priority.value == 'Medium' else '#16a34a'}; 
                                                     padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: 600;">
                                            {ticket.priority.value if ticket.priority else 'Normal'}
                                        </span>
                                    </td>
                                </tr>
                                <tr>
                                    <td style="padding: 8px 0; color: #718096; font-weight: 600;">Status:</td>
                                    <td style="padding: 8px 0;">
                                        <span style="background-color: #e0f2fe; color: #0277bd; padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: 600;">
                                            {ticket.status.value if ticket.status else 'New'}
                                        </span>
                                    </td>
                                </tr>
                                <tr>
                                    <td style="padding: 8px 0; color: #718096; font-weight: 600;">Assigned by:</td>
                                    <td style="padding: 8px 0; color: #2d3748;">{assigner.username}</td>
                                </tr>
                            </table>
                        </div>
                    </div>
                    
                    <!-- Description Preview -->
                    {f'''
                    <div style="background-color: #f7fafc; border-radius: 8px; padding: 20px; margin-bottom: 30px;">
                        <h4 style="color: #2d3748; margin: 0 0 10px 0; font-size: 14px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px;">Description Preview</h4>
                        <p style="color: #4a5568; margin: 0; line-height: 1.6; font-size: 14px;">
                            {(ticket.description[:200] + "..." if len(ticket.description) > 200 else ticket.description) if ticket.description else "No description provided."}
                        </p>
                    </div>
                    ''' if ticket.description else ''}
                    
                    <!-- Action Button -->
                    <div style="text-align: center; margin-bottom: 30px;">
                        <a href="{ticket_url}" 
                           style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                                  color: white; 
                                  text-decoration: none; 
                                  padding: 14px 28px; 
                                  border-radius: 8px; 
                                  font-weight: 600; 
                                  font-size: 16px; 
                                  display: inline-block; 
                                  box-shadow: 0 4px 6px rgba(102, 126, 234, 0.3);
                                  transition: all 0.3s ease;">
                            🔗 View Ticket
                        </a>
                    </div>
                    
                    <!-- Next Steps -->
                    <div style="background-color: #e6fffa; border: 1px solid #81e6d9; border-radius: 8px; padding: 20px;">
                        <h4 style="color: #234e52; margin: 0 0 10px 0; font-size: 16px; font-weight: 600;">
                            ✅ What's Next?
                        </h4>
                        <ul style="color: #2c7a7b; margin: 0; padding-left: 20px; line-height: 1.6;">
                            <li>Review the ticket details and priority</li>
                            <li>Update the ticket status as you work on it</li>
                            <li>Add comments to keep stakeholders informed</li>
                            <li>Close the ticket when resolved</li>
                        </ul>
                    </div>
                </div>
                
                <!-- Footer -->
                <div style="background-color: #f7fafc; padding: 30px 40px; text-align: center; border-top: 1px solid #e2e8f0;">
                    <p style="color: #718096; margin: 0 0 10px 0; font-size: 14px;">
                        This notification was sent because you were assigned to this ticket.
                    </p>
                    <p style="color: #a0aec0; margin: 0; font-size: 12px;">
                        TrueLog Inventory Management System | 
                        <a href="https://inventory.truelog.com.sg" style="color: #667eea; text-decoration: none;">inventory.truelog.com.sg</a>
                    </p>
                </div>
            </div>
        </body>
        </html>
        """
        
        # Plain text version as fallback
        text_body = f"""
{action_type} - TrueLog Inventory

Hello {assigned_user.username}!

{action_text} by {assigner.username}.

Ticket Details:
- Ticket ID: #{ticket.display_id or ticket.id}
- Subject: {ticket.subject}
- Priority: {ticket.priority.value if ticket.priority else 'Normal'}
- Status: {ticket.status.value if ticket.status else 'New'}
- Assigned by: {assigner.username}

{f"Description: {ticket.description[:200]}{'...' if len(ticket.description) > 200 else ''}" if ticket.description else ""}

View the ticket: {ticket_url}

What's Next?
- Review the ticket details and priority
- Update the ticket status as you work on it
- Add comments to keep stakeholders informed
- Close the ticket when resolved

This notification was sent because you were assigned to this ticket.

TrueLog Inventory Management System
https://inventory.truelog.com.sg
        """
        
        result = _send_email_via_method(
            to_emails=assigned_user.email,
            subject=f"[TrueLog] {action_type}: {ticket.subject}",
            html_body=html_body,
            text_body=text_body
        )
        
        if result:
            logging.info(f"Ticket assignment notification sent successfully to {assigned_user.email}")
        return result
        
    except Exception as e:
        logging.error(f"Error sending ticket assignment notification to {assigned_user.email}: {str(e)}")
        logger.info("Error sending assignment notification: {str(e)}")
        return False


def send_mention_notification_email(mentioned_user, commenter, ticket, comment_content, group_name=None):
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
        ticket_url = f"https://inventory.truelog.com.sg/tickets/{ticket.id}"
        
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
                            <strong>{commenter.username}</strong> mentioned {'group @' + group_name if group_name else 'you'} in Case <strong>{ticket.display_id}</strong>
                        </p>
                        {f'<p style="margin: 0 0 10px 0; color: #706e6b; font-size: 14px;">You are receiving this notification because you are a member of the @{group_name} group.</p>' if group_name else ''}
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
        
        # Create appropriate subject line
        if group_name:
            subject = f'Group @{group_name} was mentioned in Case {ticket.display_id}'
        else:
            subject = f'You were mentioned in Case {ticket.display_id}'
        
        result = _send_email_via_method(
            to_emails=mentioned_user.email,
            subject=subject,
            html_body=html_body,
            text_body=text_body
        )
        
        if result:
            logging.info(f"Mention notification email sent successfully to {mentioned_user.email}")
        return result
        
    except Exception as e:
        logging.error(f"Error sending mention notification email to {mentioned_user.email if mentioned_user else 'unknown'}: {str(e)}")
        logger.info("Error sending mention notification email: {str(e)}")
        import traceback
        traceback.print_exc()
        return False 


def send_queue_notification_email(user, ticket, queue, action_type="created"):
    """
    Send a notification email when a ticket is created or moved to a queue
    
    Args:
        user: User to notify
        ticket: The ticket that was created/moved
        queue: The queue the ticket was created in or moved to
        action_type: "created" or "moved"
    """
    try:
        logging.info(f"Attempting to send queue notification to {user.email}")
        
        if not current_app:
            logging.error("No Flask application context")
            return False
            
        if not user.email:
            logging.warning(f"User {user.username} has no email address")
            return False
        
        # Helper function to safely get enum values
        def get_display_value(field):
            if field is None:
                return None
            if hasattr(field, 'value'):
                return field.value
            return str(field)
        
        # Get safe display values
        priority_value = get_display_value(ticket.priority) if ticket.priority else 'Normal'
        status_value = get_display_value(ticket.status) if ticket.status else 'New'
        
        # Create the ticket URL
        ticket_url = f"https://inventory.truelog.com.sg/tickets/{ticket.id}"
        
        # Determine the action text
        if action_type == "created":
            action_text = f"A new ticket has been created in the {queue.name} queue"
            action_title = "New Ticket Created"
            action_icon = "🎫"
        else:  # moved
            action_text = f"A ticket has been moved to the {queue.name} queue"
            action_title = "Ticket Moved to Queue"
            action_icon = "📋"
        
        # Salesforce-style HTML email template
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{action_title} - {ticket.subject}</title>
        </head>
        <body style="margin: 0; padding: 0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f4f6f9;">
            <div style="max-width: 600px; margin: 0 auto; background-color: #ffffff;">
                <!-- Header -->
                <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px 40px; text-align: center;">
                    <h1 style="color: #ffffff; margin: 0; font-size: 24px; font-weight: 600;">
                        {action_icon} {action_title}
                    </h1>
                    <p style="color: #e8f0fe; margin: 8px 0 0 0; font-size: 16px;">
                        TrueLog Inventory Management
                    </p>
                </div>
                
                <!-- Main Content -->
                <div style="padding: 40px;">
                    <div style="background-color: #f8f9fa; border-left: 4px solid #667eea; padding: 20px; margin-bottom: 30px; border-radius: 0 8px 8px 0;">
                        <h2 style="color: #1a202c; margin: 0 0 10px 0; font-size: 20px;">
                            Hello {user.username}!
                        </h2>
                        <p style="color: #4a5568; margin: 0; font-size: 16px; line-height: 1.5;">
                            <strong>{action_text}</strong> that you're subscribed to receive notifications for.
                        </p>
                    </div>
                    
                    <!-- Queue Info -->
                    <div style="background-color: #e6fffa; border: 1px solid #81e6d9; border-radius: 8px; padding: 20px; margin-bottom: 30px;">
                        <h3 style="color: #234e52; margin: 0 0 10px 0; font-size: 16px; font-weight: 600;">
                            📁 Queue: {queue.name}
                        </h3>
                        {f'<p style="color: #2c7a7b; margin: 0; font-size: 14px;">{queue.description}</p>' if queue.description else ''}
                    </div>
                    
                    <!-- Ticket Details Card -->
                    <div style="border: 1px solid #e2e8f0; border-radius: 12px; overflow: hidden; margin-bottom: 30px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                        <div style="background-color: #667eea; color: white; padding: 15px 20px;">
                            <h3 style="margin: 0; font-size: 16px; font-weight: 600;">📋 Ticket Details</h3>
                        </div>
                        <div style="padding: 20px;">
                            <table style="width: 100%; border-collapse: collapse;">
                                <tr>
                                    <td style="padding: 8px 0; color: #718096; font-weight: 600; width: 120px;">Ticket ID:</td>
                                    <td style="padding: 8px 0; color: #2d3748;">#{ticket.display_id or ticket.id}</td>
                                </tr>
                                <tr>
                                    <td style="padding: 8px 0; color: #718096; font-weight: 600;">Subject:</td>
                                    <td style="padding: 8px 0; color: #2d3748; font-weight: 600;">{ticket.subject}</td>
                                </tr>
                                <tr>
                                    <td style="padding: 8px 0; color: #718096; font-weight: 600;">Priority:</td>
                                    <td style="padding: 8px 0;">
                                        <span style="background-color: {'#fee2e2' if priority_value == 'High' else '#fef3c7' if priority_value == 'Medium' else '#dcfce7'}; 
                                                     color: {'#dc2626' if priority_value == 'High' else '#d97706' if priority_value == 'Medium' else '#16a34a'}; 
                                                     padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: 600;">
                                            {priority_value}
                                        </span>
                                    </td>
                                </tr>
                                <tr>
                                    <td style="padding: 8px 0; color: #718096; font-weight: 600;">Status:</td>
                                    <td style="padding: 8px 0;">
                                        <span style="background-color: #e0f2fe; color: #0277bd; padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: 600;">
                                            {status_value}
                                        </span>
                                    </td>
                                </tr>
                                {f'''
                                <tr>
                                    <td style="padding: 8px 0; color: #718096; font-weight: 600;">Requester:</td>
                                    <td style="padding: 8px 0; color: #2d3748;">{ticket.requester.username if ticket.requester else 'Unknown'}</td>
                                </tr>
                                ''' if ticket.requester else ''}
                                {f'''
                                <tr>
                                    <td style="padding: 8px 0; color: #718096; font-weight: 600;">Assigned to:</td>
                                    <td style="padding: 8px 0; color: #2d3748;">{ticket.assigned_to.username if ticket.assigned_to else 'Unassigned'}</td>
                                </tr>
                                ''' if hasattr(ticket, 'assigned_to') else ''}
                            </table>
                        </div>
                    </div>
                    
                    <!-- Description Preview -->
                    {f'''
                    <div style="background-color: #f7fafc; border-radius: 8px; padding: 20px; margin-bottom: 30px;">
                        <h4 style="color: #2d3748; margin: 0 0 10px 0; font-size: 14px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px;">Description Preview</h4>
                        <p style="color: #4a5568; margin: 0; line-height: 1.6; font-size: 14px;">
                            {(ticket.description[:200] + "..." if len(ticket.description) > 200 else ticket.description) if ticket.description else "No description provided."}
                        </p>
                    </div>
                    ''' if ticket.description else ''}
                    
                    <!-- Action Button -->
                    <div style="text-align: center; margin-bottom: 30px;">
                        <a href="{ticket_url}" 
                           style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                                  color: white; 
                                  text-decoration: none; 
                                  padding: 14px 28px; 
                                  border-radius: 8px; 
                                  font-weight: 600; 
                                  font-size: 16px; 
                                  display: inline-block; 
                                  box-shadow: 0 4px 6px rgba(102, 126, 234, 0.3);
                                  transition: all 0.3s ease;">
                            🔗 View Ticket
                        </a>
                    </div>
                    
                    <!-- Manage Subscriptions -->
                    <div style="background-color: #f0f9ff; border: 1px solid #bae6fd; border-radius: 8px; padding: 20px;">
                        <h4 style="color: #0c4a6e; margin: 0 0 10px 0; font-size: 16px; font-weight: 600;">
                            ⚙️ Manage Your Notifications
                        </h4>
                        <p style="color: #0369a1; margin: 0; line-height: 1.6; font-size: 14px;">
                            You're receiving this notification because you subscribed to updates for the <strong>{queue.name}</strong> queue. 
                            You can manage your queue notification preferences in your account settings.
                        </p>
                    </div>
                </div>
                
                <!-- Footer -->
                <div style="background-color: #f7fafc; padding: 30px 40px; text-align: center; border-top: 1px solid #e2e8f0;">
                    <p style="color: #718096; margin: 0 0 10px 0; font-size: 14px;">
                        This notification was sent because you subscribed to queue notifications.
                    </p>
                    <p style="color: #a0aec0; margin: 0; font-size: 12px;">
                        TrueLog Inventory Management System | 
                        <a href="https://inventory.truelog.com.sg" style="color: #667eea; text-decoration: none;">inventory.truelog.com.sg</a>
                    </p>
                </div>
            </div>
        </body>
        </html>
        """
        
        # Plain text version as fallback
        text_body = f"""
{action_title} - TrueLog Inventory

Hello {user.username}!

{action_text} that you're subscribed to receive notifications for.

Queue: {queue.name}
{f"Description: {queue.description}" if queue.description else ""}

Ticket Details:
- Ticket ID: #{ticket.display_id or ticket.id}
- Subject: {ticket.subject}
- Priority: {priority_value}
- Status: {status_value}
{f"- Requester: {ticket.requester.username}" if ticket.requester else ""}
{f"- Assigned to: {ticket.assigned_to.username if ticket.assigned_to else 'Unassigned'}" if hasattr(ticket, 'assigned_to') else ""}

{f"Description: {ticket.description[:200]}{'...' if len(ticket.description) > 200 else ''}" if ticket.description else ""}

View the ticket: {ticket_url}

Manage Your Notifications:
You're receiving this notification because you subscribed to updates for the {queue.name} queue. 
You can manage your queue notification preferences in your account settings.

This notification was sent because you subscribed to queue notifications.

TrueLog Inventory Management System
https://inventory.truelog.com.sg
        """
        
        result = _send_email_via_method(
            to_emails=user.email,
            subject=f"[TrueLog] {action_title}: {ticket.subject}",
            html_body=html_body,
            text_body=text_body
        )
        
        if result:
            logging.info(f"Queue notification sent successfully to {user.email}")
        return result

    except Exception as e:
        logging.error(f"Error sending queue notification to {user.email}: {str(e)}")
        logger.info("Error sending queue notification: {str(e)}")
        return False


def send_issue_reported_email(notified_user, reporter, ticket, issue_type, description):
    """
    Send an email notification when an issue is reported on a ticket

    Args:
        notified_user: User to notify
        reporter: User who reported the issue
        ticket: The ticket the issue was reported on
        issue_type: Type of issue reported
        description: Description of the issue
    """
    try:
        logging.info(f"Attempting to send issue reported email to {notified_user.email}")

        if not current_app:
            logging.error("No Flask application context")
            return False

        if not notified_user.email:
            logging.warning(f"User {notified_user.username} has no email address")
            return False

        # Truncate description if too long
        description_preview = description[:300] + "..." if len(description) > 300 else description

        # Create the ticket URL
        ticket_url = f"https://inventory.truelog.com.sg/tickets/{ticket.id}"

        # HTML email template
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Issue Reported - Ticket #{ticket.display_id or ticket.id}</title>
        </head>
        <body style="margin: 0; padding: 0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f4f6f9;">
            <div style="max-width: 600px; margin: 0 auto; background-color: #ffffff;">
                <!-- Header -->
                <div style="background: linear-gradient(135deg, #dc2626 0%, #991b1b 100%); padding: 30px 40px; text-align: center;">
                    <h1 style="color: #ffffff; margin: 0; font-size: 24px; font-weight: 600;">
                        ⚠️ Issue Reported
                    </h1>
                    <p style="color: #fecaca; margin: 8px 0 0 0; font-size: 16px;">
                        TrueLog Inventory Management
                    </p>
                </div>

                <!-- Main Content -->
                <div style="padding: 40px;">
                    <div style="background-color: #fef2f2; border-left: 4px solid #dc2626; padding: 20px; margin-bottom: 30px; border-radius: 0 8px 8px 0;">
                        <h2 style="color: #1a202c; margin: 0 0 10px 0; font-size: 20px;">
                            Hello {notified_user.username}!
                        </h2>
                        <p style="color: #4a5568; margin: 0; font-size: 16px; line-height: 1.5;">
                            <strong>{reporter.username}</strong> has reported an issue on Ticket <strong>#{ticket.display_id or ticket.id}</strong> and notified you.
                        </p>
                    </div>

                    <!-- Issue Details Card -->
                    <div style="border: 1px solid #fecaca; border-radius: 12px; overflow: hidden; margin-bottom: 30px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                        <div style="background-color: #dc2626; color: white; padding: 15px 20px;">
                            <h3 style="margin: 0; font-size: 16px; font-weight: 600;">🚨 Issue Details</h3>
                        </div>
                        <div style="padding: 20px;">
                            <table style="width: 100%; border-collapse: collapse;">
                                <tr>
                                    <td style="padding: 10px 0; color: #718096; font-weight: 600; width: 120px; vertical-align: top;">Issue Type:</td>
                                    <td style="padding: 10px 0;">
                                        <span style="background-color: #fef3c7; color: #d97706; padding: 4px 12px; border-radius: 4px; font-size: 14px; font-weight: 600;">
                                            {issue_type}
                                        </span>
                                    </td>
                                </tr>
                                <tr>
                                    <td style="padding: 10px 0; color: #718096; font-weight: 600; vertical-align: top;">Description:</td>
                                    <td style="padding: 10px 0; color: #2d3748; line-height: 1.6;">{description_preview}</td>
                                </tr>
                                <tr>
                                    <td style="padding: 10px 0; color: #718096; font-weight: 600;">Reported by:</td>
                                    <td style="padding: 10px 0; color: #2d3748;">{reporter.username}</td>
                                </tr>
                            </table>
                        </div>
                    </div>

                    <!-- Ticket Info Card -->
                    <div style="border: 1px solid #e2e8f0; border-radius: 12px; overflow: hidden; margin-bottom: 30px;">
                        <div style="background-color: #667eea; color: white; padding: 15px 20px;">
                            <h3 style="margin: 0; font-size: 16px; font-weight: 600;">📋 Ticket Information</h3>
                        </div>
                        <div style="padding: 20px;">
                            <table style="width: 100%; border-collapse: collapse;">
                                <tr>
                                    <td style="padding: 8px 0; color: #718096; font-weight: 600; width: 120px;">Ticket ID:</td>
                                    <td style="padding: 8px 0; color: #2d3748;">#{ticket.display_id or ticket.id}</td>
                                </tr>
                                <tr>
                                    <td style="padding: 8px 0; color: #718096; font-weight: 600;">Subject:</td>
                                    <td style="padding: 8px 0; color: #2d3748; font-weight: 600;">{ticket.subject}</td>
                                </tr>
                                <tr>
                                    <td style="padding: 8px 0; color: #718096; font-weight: 600;">Status:</td>
                                    <td style="padding: 8px 0;">
                                        <span style="background-color: #e0f2fe; color: #0277bd; padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: 600;">
                                            {ticket.status.value if ticket.status else 'New'}
                                        </span>
                                    </td>
                                </tr>
                            </table>
                        </div>
                    </div>

                    <!-- Action Button -->
                    <div style="text-align: center; margin-bottom: 30px;">
                        <a href="{ticket_url}"
                           style="background: linear-gradient(135deg, #dc2626 0%, #991b1b 100%);
                                  color: white;
                                  text-decoration: none;
                                  padding: 14px 28px;
                                  border-radius: 8px;
                                  font-weight: 600;
                                  font-size: 16px;
                                  display: inline-block;
                                  box-shadow: 0 4px 6px rgba(220, 38, 38, 0.3);">
                            🔗 View Ticket & Issue
                        </a>
                    </div>

                    <!-- Action Required -->
                    <div style="background-color: #fff7ed; border: 1px solid #fed7aa; border-radius: 8px; padding: 20px;">
                        <h4 style="color: #c2410c; margin: 0 0 10px 0; font-size: 16px; font-weight: 600;">
                            ⚡ Action Required
                        </h4>
                        <p style="color: #ea580c; margin: 0; line-height: 1.6; font-size: 14px;">
                            Please review this issue and take appropriate action. You can resolve the issue or add comments directly on the ticket.
                        </p>
                    </div>
                </div>

                <!-- Footer -->
                <div style="background-color: #f7fafc; padding: 30px 40px; text-align: center; border-top: 1px solid #e2e8f0;">
                    <p style="color: #718096; margin: 0 0 10px 0; font-size: 14px;">
                        You were notified because you were selected to receive this issue report.
                    </p>
                    <p style="color: #a0aec0; margin: 0; font-size: 12px;">
                        TrueLog Inventory Management System |
                        <a href="https://inventory.truelog.com.sg" style="color: #667eea; text-decoration: none;">inventory.truelog.com.sg</a>
                    </p>
                </div>
            </div>
        </body>
        </html>
        """

        # Plain text version
        text_body = f"""Issue Reported - TrueLog Inventory

Hello {notified_user.username}!

{reporter.username} has reported an issue on Ticket #{ticket.display_id or ticket.id} and notified you.

Issue Details:
- Issue Type: {issue_type}
- Description: {description_preview}
- Reported by: {reporter.username}

Ticket Information:
- Ticket ID: #{ticket.display_id or ticket.id}
- Subject: {ticket.subject}
- Status: {ticket.status.value if ticket.status else 'New'}

View the ticket: {ticket_url}

Action Required:
Please review this issue and take appropriate action. You can resolve the issue or add comments directly on the ticket.

---
TrueLog Inventory Management System
https://inventory.truelog.com.sg
        """

        result = _send_email_via_method(
            to_emails=notified_user.email,
            subject=f"[TrueLog] ⚠️ Issue Reported: {issue_type} on Ticket #{ticket.display_id or ticket.id}",
            html_body=html_body,
            text_body=text_body
        )

        if result:
            logging.info(f"Issue reported email sent successfully to {notified_user.email}")
        return result

    except Exception as e:
        logging.error(f"Error sending issue reported email to {notified_user.email}: {str(e)}")
        return False


def send_issue_comment_email(notified_user, commenter, ticket, issue, comment_content):
    """
    Send an email notification when someone is mentioned in an issue comment

    Args:
        notified_user: User to notify
        commenter: User who wrote the comment
        ticket: The ticket the issue belongs to
        issue: The issue being commented on
        comment_content: Content of the comment
    """
    try:
        logging.info(f"Attempting to send issue comment email to {notified_user.email}")

        if not current_app:
            logging.error("No Flask application context")
            return False

        if not notified_user.email:
            logging.warning(f"User {notified_user.username} has no email address")
            return False

        # Truncate content if too long
        content_preview = comment_content[:300] + "..." if len(comment_content) > 300 else comment_content

        # Create the ticket URL
        ticket_url = f"https://inventory.truelog.com.sg/tickets/{ticket.id}"

        # HTML email template
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>You were mentioned - Ticket #{ticket.display_id or ticket.id}</title>
        </head>
        <body style="margin: 0; padding: 0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f4f6f9;">
            <div style="max-width: 600px; margin: 0 auto; background-color: #ffffff;">
                <!-- Header -->
                <div style="background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%); padding: 30px 40px; text-align: center;">
                    <h1 style="color: #ffffff; margin: 0; font-size: 24px; font-weight: 600;">
                        💬 You were mentioned
                    </h1>
                    <p style="color: #bfdbfe; margin: 8px 0 0 0; font-size: 16px;">
                        TrueLog Inventory Management
                    </p>
                </div>

                <!-- Main Content -->
                <div style="padding: 40px;">
                    <div style="background-color: #eff6ff; border-left: 4px solid #3b82f6; padding: 20px; margin-bottom: 30px; border-radius: 0 8px 8px 0;">
                        <h2 style="color: #1a202c; margin: 0 0 10px 0; font-size: 20px;">
                            Hello {notified_user.username}!
                        </h2>
                        <p style="color: #4a5568; margin: 0; font-size: 16px; line-height: 1.5;">
                            <strong>{commenter.username}</strong> mentioned you in a comment on issue <strong>{issue.issue_type}</strong>.
                        </p>
                    </div>

                    <!-- Comment Card -->
                    <div style="border: 1px solid #bfdbfe; border-radius: 12px; overflow: hidden; margin-bottom: 30px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                        <div style="background-color: #3b82f6; color: white; padding: 15px 20px;">
                            <h3 style="margin: 0; font-size: 16px; font-weight: 600;">💬 Comment</h3>
                        </div>
                        <div style="padding: 20px;">
                            <div style="background-color: #f8fafc; border-radius: 8px; padding: 15px; margin-bottom: 15px;">
                                <p style="color: #2d3748; margin: 0; line-height: 1.6; white-space: pre-wrap;">{content_preview}</p>
                            </div>
                            <p style="color: #718096; margin: 0; font-size: 14px;">
                                Posted by <strong>{commenter.username}</strong>
                            </p>
                        </div>
                    </div>

                    <!-- Issue Info Card -->
                    <div style="border: 1px solid #fed7aa; border-radius: 12px; overflow: hidden; margin-bottom: 30px;">
                        <div style="background-color: #f97316; color: white; padding: 15px 20px;">
                            <h3 style="margin: 0; font-size: 16px; font-weight: 600;">🚨 Issue: {issue.issue_type}</h3>
                        </div>
                        <div style="padding: 20px;">
                            <p style="color: #2d3748; margin: 0; line-height: 1.6;">
                                {issue.description[:200] + '...' if len(issue.description) > 200 else issue.description}
                            </p>
                        </div>
                    </div>

                    <!-- Action Button -->
                    <div style="text-align: center; margin-bottom: 30px;">
                        <a href="{ticket_url}"
                           style="background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%);
                                  color: white;
                                  text-decoration: none;
                                  padding: 14px 28px;
                                  border-radius: 8px;
                                  font-weight: 600;
                                  font-size: 16px;
                                  display: inline-block;
                                  box-shadow: 0 4px 6px rgba(59, 130, 246, 0.3);">
                            🔗 View Ticket & Reply
                        </a>
                    </div>
                </div>

                <!-- Footer -->
                <div style="background-color: #f7fafc; padding: 30px 40px; text-align: center; border-top: 1px solid #e2e8f0;">
                    <p style="color: #718096; margin: 0 0 10px 0; font-size: 14px;">
                        You were notified because you were @mentioned in a comment.
                    </p>
                    <p style="color: #a0aec0; margin: 0; font-size: 12px;">
                        TrueLog Inventory Management System |
                        <a href="https://inventory.truelog.com.sg" style="color: #667eea; text-decoration: none;">inventory.truelog.com.sg</a>
                    </p>
                </div>
            </div>
        </body>
        </html>
        """

        # Plain text version
        text_body = f"""You were mentioned - TrueLog Inventory

Hello {notified_user.username}!

{commenter.username} mentioned you in a comment on issue "{issue.issue_type}".

Comment:
{content_preview}

Posted by: {commenter.username}

Issue: {issue.issue_type}
{issue.description[:200] + '...' if len(issue.description) > 200 else issue.description}

View the ticket: {ticket_url}

---
TrueLog Inventory Management System
https://inventory.truelog.com.sg
        """

        result = _send_email_via_method(
            to_emails=notified_user.email,
            subject=f"[TrueLog] 💬 {commenter.username} mentioned you on Ticket #{ticket.display_id or ticket.id}",
            html_body=html_body,
            text_body=text_body
        )

        if result:
            logging.info(f"Issue comment email sent successfully to {notified_user.email}")
        return result

    except Exception as e:
        logging.error(f"Error sending issue comment email to {notified_user.email}: {str(e)}")
        return False