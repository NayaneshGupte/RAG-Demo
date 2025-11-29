"""
Gmail email sending service.
Handles sending composed email messages via Gmail API.
"""
import logging
from typing import Dict, Optional
from googleapiclient.discovery import Resource
from app.services.gmail.email_composer import GmailEmailComposer

logger = logging.getLogger(__name__)


class GmailEmailSender:
    """Service for sending email messages."""
    
    def __init__(self, service: Resource):
        """
        Initialize email sender service.
        
        Args:
            service: Gmail API service instance
        """
        self.service = service
        self.composer = GmailEmailComposer()
    
    def send_reply(self, to: str, subject: str, body: str,
                   thread_id: str, message_id: Optional[str] = None,
                   references: Optional[str] = None) -> Optional[Dict]:
        """
        Send a reply to an email.
        
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
        try:
            # Compose the message
            composed_message = self.composer.create_reply(
                to, subject, body, thread_id, message_id, references
            )
            
            # Send it
            return self.send_message(composed_message, thread_id)
        except Exception as e:
            logger.error(f"Error in send_reply: {e}", exc_info=True)
            return None
    
    def send_message(self, composed_message: Dict, thread_id: str) -> Optional[Dict]:
        """
        Send already-composed message.
        
        Args:
            composed_message: Composed message dict with 'raw' content
            thread_id: Thread ID for grouping
            
        Returns:
            Dict: Sent message info or None if failed
        """
        try:
            raw_message = self._create_raw_message(composed_message, thread_id)
            sent_message = self.service.users().messages().send(
                userId='me', body=raw_message
            ).execute()
            
            logger.info(f'Sent message: {sent_message["id"]}')
            return sent_message
        except Exception as e:
            logger.error(f'Error sending message: {e}', exc_info=True)
            return None
    
    def _create_raw_message(self, composed_message: Dict,
                           thread_id: str) -> Dict:
        """
        Create raw message format for API.
        
        Args:
            composed_message: Composed message dict
            thread_id: Thread ID for grouping
            
        Returns:
            Dict: Message in format expected by Gmail API
        """
        return {
            'raw': composed_message['raw'],
            'threadId': thread_id
        }
