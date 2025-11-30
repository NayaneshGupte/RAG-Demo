"""
Gmail service facade for email operations.
Provides unified interface to all Gmail functionality while maintaining backward compatibility.
"""
import logging
from typing import Optional, Dict, List
from app.config import Config
from app.services.gmail.auth_service import GmailAuthService
from app.services.gmail.email_reader import GmailEmailReader
from app.services.gmail.email_composer import GmailEmailComposer
from app.services.gmail.email_sender import GmailEmailSender
from app.services.gmail.email_modifier import GmailEmailModifier
from app.services.gmail.user_service import GmailUserService

logger = logging.getLogger(__name__)


class GmailService:
    """Facade service for Gmail operations.
    
    Provides a unified interface to all Gmail functionality by delegating
    to specialized services, maintaining 100% backward compatibility with
    the original monolithic GmailService class.
    """
    
    def __init__(self):
        """Initialize Gmail Service as facade."""
        try:
            # Initialize auth service with proper credentials
            self.auth_service = GmailAuthService(
                Config.GMAIL_CREDENTIALS_FILE,
                Config.GMAIL_TOKEN_FILE
            )
            self.service = self.auth_service.get_service()
            
            self.reader = GmailEmailReader(self.service)
            self.composer = GmailEmailComposer()
            self.sender = GmailEmailSender(self.service)
            self.modifier = GmailEmailModifier(self.service)
            self.user_service = GmailUserService(self.service)
            
            logger.info("Gmail service initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing Gmail service: {e}", exc_info=True)
            raise
    
    def get_unread_emails(self, after_timestamp: Optional[float] = None) -> List[Dict]:
        """
        Fetch unread emails, optionally filtering by timestamp.
        
        Args:
            after_timestamp: Optional Unix timestamp to filter emails after
            
        Returns:
            List[Dict]: List of unread email messages
        """
        return self.reader.get_unread_emails(after_timestamp)
    
    def send_reply(self, to: str, subject: str, body: str, thread_id: str,
                   message_id: Optional[str] = None,
                   references: Optional[str] = None) -> Optional[Dict]:
        """
        Send a reply to an email thread.
        
        Args:
            to: Recipient email address
            subject: Email subject
            body: Email body text
            thread_id: Thread ID for grouping
            message_id: Original message ID for threading
            references: References header value
            
        Returns:
            Dict: Sent message info or None if failed
        """
        return self.sender.send_reply(to, subject, body, thread_id, message_id, references)
    
    def mark_as_read(self, msg_id: str) -> bool:
        """
        Mark an email as read.
        
        Args:
            msg_id: Gmail message ID
            
        Returns:
            bool: True if successful, False otherwise
        """
        return self.modifier.mark_as_read(msg_id)
    
    def get_current_email(self) -> Optional[str]:
        """
        Get the email address of the authenticated user.
        
        Returns:
            str: Email address or None if failed
        """
        return self.user_service.get_current_email()
