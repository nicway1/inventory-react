import os
import requests
import json
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import base64
import logging

logger = logging.getLogger(__name__)

class MicrosoftEmailClient:
    def __init__(self):
        self.client_id = os.getenv('MS_CLIENT_ID')
        self.client_secret = os.getenv('MS_CLIENT_SECRET')
        self.tenant_id = os.getenv('MS_TENANT_ID')
        self.from_email = os.getenv('MS_FROM_EMAIL')
        
        if not all([self.client_id, self.client_secret, self.tenant_id, self.from_email]):
            raise ValueError("Missing Microsoft OAuth2 configuration. Please set MS_CLIENT_ID, MS_CLIENT_SECRET, MS_TENANT_ID, and MS_FROM_EMAIL environment variables.")
        
        self.token_url = f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token"
        self.graph_url = "https://graph.microsoft.com/v1.0"
        self.access_token = None
        self.token_expires = None

    def get_access_token(self):
        """Get access token using client credentials flow"""
        try:
            # Check if we have a valid token
            if (self.access_token and self.token_expires and 
                datetime.now() < self.token_expires - timedelta(minutes=5)):
                return self.access_token

            # Request new token
            data = {
                'grant_type': 'client_credentials',
                'client_id': self.client_id,
                'client_secret': self.client_secret,
                'scope': 'https://graph.microsoft.com/.default'
            }
            
            response = requests.post(self.token_url, data=data)
            response.raise_for_status()
            
            token_data = response.json()
            self.access_token = token_data['access_token']
            expires_in = token_data.get('expires_in', 3600)
            self.token_expires = datetime.now() + timedelta(seconds=expires_in)
            
            logger.info("Successfully obtained Microsoft access token")
            return self.access_token
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get Microsoft access token: {e}")
            raise Exception(f"Authentication failed: {e}")

    def send_email(self, to_emails, subject, body, html_body=None, attachments=None):
        """Send email using Microsoft Graph API"""
        try:
            token = self.get_access_token()
            
            # Prepare recipients
            if isinstance(to_emails, str):
                to_emails = [to_emails]
            
            recipients = [{"emailAddress": {"address": email}} for email in to_emails]
            
            # Prepare email message
            message = {
                "subject": subject,
                "body": {
                    "contentType": "HTML" if html_body else "Text",
                    "content": html_body if html_body else body
                },
                "toRecipients": recipients,
                "from": {
                    "emailAddress": {
                        "address": self.from_email
                    }
                }
            }
            
            # Add attachments if provided
            if attachments:
                message["attachments"] = []
                for attachment in attachments:
                    if isinstance(attachment, dict):
                        # Attachment is already in the correct format
                        message["attachments"].append(attachment)
                    else:
                        # Convert file path to attachment
                        with open(attachment, 'rb') as f:
                            file_content = f.read()
                            file_name = os.path.basename(attachment)
                            
                        attachment_data = {
                            "@odata.type": "#microsoft.graph.fileAttachment",
                            "name": file_name,
                            "contentBytes": base64.b64encode(file_content).decode('utf-8')
                        }
                        message["attachments"].append(attachment_data)
            
            # Send email via Graph API
            headers = {
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json'
            }
            
            send_url = f"{self.graph_url}/users/{self.from_email}/sendMail"
            payload = {"message": message}
            
            response = requests.post(send_url, headers=headers, json=payload)
            response.raise_for_status()
            
            logger.info(f"Email sent successfully to {to_emails}")
            return True
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to send email: {e}")
            if hasattr(e, 'response') and e.response:
                logger.error(f"Response content: {e.response.text}")
            raise Exception(f"Email sending failed: {e}")
        except Exception as e:
            logger.error(f"Unexpected error sending email: {e}")
            raise

    def send_html_email(self, to_emails, subject, html_content, text_content=None, attachments=None):
        """Send HTML email with optional text fallback"""
        return self.send_email(
            to_emails=to_emails,
            subject=subject,
            body=text_content or "Please view this email in an HTML-capable client.",
            html_body=html_content,
            attachments=attachments
        )

    def test_connection(self):
        """Test the Microsoft Graph connection"""
        try:
            token = self.get_access_token()
            
            # Test by getting user profile
            headers = {'Authorization': f'Bearer {token}'}
            response = requests.get(f"{self.graph_url}/users/{self.from_email}", headers=headers)
            response.raise_for_status()
            
            user_data = response.json()
            logger.info(f"Microsoft Graph connection successful. User: {user_data.get('displayName', 'Unknown')}")
            return True, f"Connection successful. User: {user_data.get('displayName', 'Unknown')}"
            
        except Exception as e:
            logger.error(f"Microsoft Graph connection test failed: {e}")
            return False, str(e)

# Global instance
microsoft_email_client = None

def get_microsoft_email_client():
    """Get or create Microsoft email client instance"""
    global microsoft_email_client
    
    if microsoft_email_client is None:
        try:
            microsoft_email_client = MicrosoftEmailClient()
        except ValueError as e:
            logger.warning(f"Microsoft email client not configured: {e}")
            return None
    
    return microsoft_email_client

def send_microsoft_email(to_emails, subject, body, html_body=None, attachments=None):
    """Convenience function to send email using Microsoft Graph"""
    client = get_microsoft_email_client()
    if client:
        return client.send_email(to_emails, subject, body, html_body, attachments)
    else:
        raise Exception("Microsoft email client not configured") 