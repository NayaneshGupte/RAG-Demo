"""
Gmail email composing service.
Handles creating and formatting email messages for sending.
"""
import base64
import logging
from typing import Dict, Optional
from email.mime.text import MIMEText

logger = logging.getLogger(__name__)


class GmailEmailComposer:
    """Service for composing email messages."""
    
    def create_reply(self, to: str, subject: str, body: str,
                     thread_id: str, message_id: Optional[str] = None,
                     references: Optional[str] = None) -> Dict:
        """
        Create a reply message.
        
        Args:
            to: Recipient email address
            subject: Email subject
            body: Email body text
            thread_id: Thread ID for grouping
            message_id: Original message ID for threading
            references: References header value
            
        Returns:
            Dict: Formatted message ready for sending
        """
        logger.debug(f"Creating reply to {to}: {subject}")
        
        try:
            # Compose base message
            message = self._compose_message(to, subject, body)
            
            # Add reply-specific headers
            message = self._add_reply_headers(
                message, message_id, references
            )
            
            # Encode message
            encoded = self._encode_message(message)
            
            return {
                'raw': encoded,
                'threadId': thread_id
            }
        except Exception as e:
            logger.error(f"Error creating reply: {e}")
            raise
    
    def _compose_message(self, to: str, subject: str, body: str) -> MIMEText:
        """
        Create MIMEText message.
        
        Args:
            to: Recipient email address
            subject: Email subject
            body: Email body text
            
        Returns:
            MIMEText: Composed message object
        """
        try:
            message = MIMEText(body)
            message['to'] = to
            message['subject'] = self._format_subject(subject)
            logger.debug("Composed base message")
            return message
        except Exception as e:
            logger.error(f"Error composing message: {e}")
            raise
    
    def _add_reply_headers(self, message: MIMEText,
                           message_id: Optional[str] = None,
                           references: Optional[str] = None) -> MIMEText:
        """
        Add In-Reply-To and References headers.
        
        Args:
            message: Message to add headers to
            message_id: Original message ID
            references: References header value
            
        Returns:
            MIMEText: Message with reply headers added
        """
        try:
            if message_id:
                message['In-Reply-To'] = message_id
                if references:
                    message['References'] = f"{references} {message_id}"
                else:
                    message['References'] = message_id
                logger.debug("Added reply headers")
            return message
        except Exception as e:
            logger.error(f"Error adding reply headers: {e}")
            raise
    
    def _format_subject(self, subject: str) -> str:
        """
        Ensure subject has 'Re:' prefix.
        
        Args:
            subject: Original subject
            
        Returns:
            str: Subject with 'Re:' prefix if needed
        """
        if subject.lower().startswith('re:'):
            return subject
        return f"Re: {subject}"
    
    def _encode_message(self, message: MIMEText) -> str:
        """
        Encode message for sending.
        
        Args:
            message: Message to encode
            
        Returns:
            str: Base64 encoded message
        """
        try:
            encoded = base64.urlsafe_b64encode(message.as_bytes()).decode()
            logger.debug("Encoded message successfully")
            return encoded
        except Exception as e:
            logger.error(f"Error encoding message: {e}")
            raise
