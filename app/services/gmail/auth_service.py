"""
Gmail authentication and credential management service.
Handles OAuth flow, token refresh, and API service initialization.
"""
import os
import logging
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.discovery import Resource

logger = logging.getLogger(__name__)

SCOPES = ['https://www.googleapis.com/auth/gmail.modify']


class GmailAuthService:
    """Service for Gmail authentication and credential management."""
    
    def __init__(self, credentials_file: str, token_file: str):
        """
        Initialize authentication service.
        
        Args:
            credentials_file: Path to Gmail credentials JSON file
            token_file: Path to store/load OAuth tokens
        """
        self.credentials_file = credentials_file
        self.token_file = token_file
        self.service = None
    
    def get_service(self) -> Resource:
        """
        Get authenticated Gmail API service.
        
        Returns:
            Resource: Gmail API service instance
            
        Raises:
            FileNotFoundError: If credentials file not found
            PermissionError: If authentication required (no valid credentials)
        """
        if self.service is not None:
            return self.service
        
        creds = self._load_credentials()
        
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                logger.info("Refreshing Gmail credentials")
                try:
                    creds = self._refresh_credentials(creds)
                    self._save_credentials(creds)
                except Exception as e:
                    logger.error(f"Failed to refresh credentials: {e}")
                    # Don't auto-trigger OAuth - let user click button
                    raise PermissionError("Authentication required. Please authenticate via dashboard.")
            else:
                # Don't auto-trigger OAuth flow - require user to click "Connect Gmail" button
                logger.info("No valid credentials found - user must authenticate via dashboard")
                raise PermissionError("Authentication required. Please authenticate via dashboard.")
        
        self.service = build('gmail', 'v1', credentials=creds)
        logger.info("Gmail service authenticated successfully")
        return self.service
    
    def _load_credentials(self) -> Credentials:
        """
        Load existing credentials from token file.
        
        Returns:
            Credentials: OAuth credentials or None if not found
        """
        if os.path.exists(self.token_file):
            try:
                creds = Credentials.from_authorized_user_file(self.token_file, SCOPES)
                logger.debug("Loaded credentials from token file")
                return creds
            except Exception as e:
                logger.warning(f"Failed to load credentials: {e}")
                return None
        
        return None
    
    def _refresh_credentials(self, creds: Credentials) -> Credentials:
        """
        Refresh expired credentials.
        
        Args:
            creds: Credentials object to refresh
            
        Returns:
            Credentials: Refreshed credentials
        """
        try:
            creds.refresh(Request())
            logger.debug("Successfully refreshed credentials")
            return creds
        except Exception as e:
            logger.error(f"Error refreshing credentials: {e}")
            raise
    
    def _start_oauth_flow(self) -> Credentials:
        """
        Start new OAuth flow to get credentials.
        
        Returns:
            Credentials: New OAuth credentials
        """
        try:
            flow = InstalledAppFlow.from_client_secrets_file(
                self.credentials_file, SCOPES
            )
            creds = flow.run_local_server(port=0)
            logger.info("OAuth flow completed successfully")
            return creds
        except Exception as e:
            logger.error(f"Error during OAuth flow: {e}")
            raise
    
    def _save_credentials(self, creds: Credentials) -> None:
        """
        Save credentials to token file.
        
        Args:
            creds: Credentials to save
        """
        try:
            with open(self.token_file, 'w') as token:
                token.write(creds.to_json())
            logger.debug("Credentials saved to token file")
        except Exception as e:
            logger.error(f"Error saving credentials: {e}")
            raise
