#!/usr/bin/env python3
"""
OAuth2 Email Sender using Microsoft Graph API
This replaces traditional SMTP with OAuth2 authentication for better security.
"""

import os
import json
import logging
from typing import List, Optional
import msal
import requests
from flask import current_app

class OAuth2EmailSender:
    """OAuth2 Email sender using Microsoft Graph API"""
    
    def __init__(self, client_id: str, client_secret: str, tenant_id: str):
        """
        Initialize OAuth2 Email Sender
        
        Args:
            client_id: Azure AD Application (client) ID
            client_secret: Azure AD Client secret
            tenant_id: Azure AD Directory (tenant) ID
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.tenant_id = tenant_id
        self.authority = f"https://login.microsoftonline.com/{tenant_id}"
        self.scope = ["https://graph.microsoft.com/.default"]
        self.graph_url = "https://graph.microsoft.com/v1.0"
        
        # Create MSAL app
        self.app = msal.ConfidentialClientApplication(
            client_id=self.client_id,
            client_credential=self.client_secret,
            authority=self.authority
        )
        
        self.logger = logging.getLogger(__name__)
    
    def get_access_token(self) -> Optional[str]:
        """Get access token using client credentials flow"""
        try:
            # Try to get token from cache first
            result = self.app.acquire_token_silent(self.scope, account=None)
            
            if not result:
                # If no cached token, acquire new one
                result = self.app.acquire_token_for_client(scopes=self.scope)
            
            if "access_token" in result:
                return result["access_token"]
            else:
                self.logger.error(f"Failed to acquire token: {result.get('error_description', 'Unknown error')}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error getting access token: {str(e)}")
            return None
    
    def send_email(self, to_emails: List[str], subject: str, body: str, 
                   from_email: Optional[str] = None, cc_emails: Optional[List[str]] = None,
                   bcc_emails: Optional[List[str]] = None, is_html: bool = False) -> bool:
        """
        Send email using Microsoft Graph API
        
        Args:
            to_emails: List of recipient email addresses
            subject: Email subject
            body: Email body content
            from_email: Sender email (if None, uses app's default)
            cc_emails: List of CC email addresses
            bcc_emails: List of BCC email addresses
            is_html: Whether body content is HTML
            
        Returns:
            bool: True if email sent successfully, False otherwise
        """
        try:
            # Get access token
            access_token = self.get_access_token()
            if not access_token:
                self.logger.error("Failed to get access token")
                return False
            
            # Prepare recipients
            to_recipients = [{"emailAddress": {"address": email}} for email in to_emails]
            cc_recipients = [{"emailAddress": {"address": email}} for email in (cc_emails or [])]
            bcc_recipients = [{"emailAddress": {"address": email}} for email in (bcc_emails or [])]
            
            # Prepare email message
            message = {
                "message": {
                    "subject": subject,
                    "body": {
                        "contentType": "HTML" if is_html else "Text",
                        "content": body
                    },
                    "toRecipients": to_recipients
                }
            }
            
            # Add CC and BCC if provided
            if cc_recipients:
                message["message"]["ccRecipients"] = cc_recipients
            if bcc_recipients:
                message["message"]["bccRecipients"] = bcc_recipients
            
            # Determine endpoint based on from_email
            if from_email:
                # Send as specific user
                endpoint = f"{self.graph_url}/users/{from_email}/sendMail"
            else:
                # Send using app permissions (requires Mail.Send application permission)
                # This will use the first user or a designated sender
                endpoint = f"{self.graph_url}/me/sendMail"
            
            # Send email
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            
            response = requests.post(endpoint, headers=headers, json=message)
            
            if response.status_code == 202:  # Accepted
                self.logger.info(f"Email sent successfully to {', '.join(to_emails)}")
                return True
            else:
                self.logger.error(f"Failed to send email. Status: {response.status_code}, Response: {response.text}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error sending email: {str(e)}")
            return False
    
    def test_connection(self) -> bool:
        """Test the OAuth2 connection"""
        try:
            access_token = self.get_access_token()
            if not access_token:
                return False
            
            # Test by getting user profile
            headers = {"Authorization": f"Bearer {access_token}"}
            response = requests.get(f"{self.graph_url}/me", headers=headers)
            
            return response.status_code == 200
            
        except Exception as e:
            self.logger.error(f"Connection test failed: {str(e)}")
            return False

# Flask extension wrapper
class OAuth2Mail:
    """Flask extension for OAuth2 email sending"""
    
    def __init__(self, app=None):
        self.sender = None
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize the extension with Flask app"""
        client_id = app.config.get('OAUTH2_CLIENT_ID')
        client_secret = app.config.get('OAUTH2_CLIENT_SECRET')
        tenant_id = app.config.get('OAUTH2_TENANT_ID')
        
        if not all([client_id, client_secret, tenant_id]):
            app.logger.warning("OAuth2 email configuration incomplete. Email sending will not work.")
            return
        
        self.sender = OAuth2EmailSender(client_id, client_secret, tenant_id)
        app.extensions['oauth2_mail'] = self
    
    def send(self, to_emails, subject, body, from_email=None, cc_emails=None, bcc_emails=None, is_html=False):
        """Send email using OAuth2"""
        if not self.sender:
            current_app.logger.error("OAuth2 email sender not initialized")
            return False
        
        # Ensure to_emails is a list
        if isinstance(to_emails, str):
            to_emails = [to_emails]
        
        return self.sender.send_email(
            to_emails=to_emails,
            subject=subject,
            body=body,
            from_email=from_email,
            cc_emails=cc_emails,
            bcc_emails=bcc_emails,
            is_html=is_html
        )
    
    def test_connection(self):
        """Test OAuth2 connection"""
        if not self.sender:
            return False
        return self.sender.test_connection()

# Global instance
oauth2_mail = OAuth2Mail() 