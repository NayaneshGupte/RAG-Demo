"""
Gmail email modification service.
Handles modifying email attributes like read/unread status and labels.
"""
import logging
from typing import Optional, List
from googleapiclient.discovery import Resource

logger = logging.getLogger(__name__)


class GmailEmailModifier:
    """Service for modifying email messages."""
    
    def __init__(self, service: Resource):
        """
        Initialize email modifier service.
        
        Args:
            service: Gmail API service instance
        """
        self.service = service
    
    def mark_as_read(self, message_id: str) -> bool:
        """
        Mark message as read by removing UNREAD label.
        
        Args:
            message_id: Gmail message ID
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            self._modify_message(message_id, remove_labels=['UNREAD'])
            logger.debug(f"Marked message {message_id} as read")
            return True
        except Exception as e:
            logger.error(f"Error marking message as read: {e}", exc_info=True)
            return False
    
    def mark_as_unread(self, message_id: str) -> bool:
        """
        Mark message as unread by adding UNREAD label.
        
        Args:
            message_id: Gmail message ID
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            self._modify_message(message_id, add_labels=['UNREAD'])
            logger.debug(f"Marked message {message_id} as unread")
            return True
        except Exception as e:
            logger.error(f"Error marking message as unread: {e}", exc_info=True)
            return False
    
    def add_label(self, message_id: str, label_id: str) -> bool:
        """
        Add label to message.
        
        Args:
            message_id: Gmail message ID
            label_id: Label ID to add
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            self._modify_message(message_id, add_labels=[label_id])
            logger.debug(f"Added label {label_id} to message {message_id}")
            return True
        except Exception as e:
            logger.error(f"Error adding label: {e}", exc_info=True)
            return False
    
    def remove_label(self, message_id: str, label_id: str) -> bool:
        """
        Remove label from message.
        
        Args:
            message_id: Gmail message ID
            label_id: Label ID to remove
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            self._modify_message(message_id, remove_labels=[label_id])
            logger.debug(f"Removed label {label_id} from message {message_id}")
            return True
        except Exception as e:
            logger.error(f"Error removing label: {e}", exc_info=True)
            return False
    
    def _modify_message(self, message_id: str,
                       add_labels: Optional[List[str]] = None,
                       remove_labels: Optional[List[str]] = None) -> bool:
        """
        Modify message labels.
        
        Args:
            message_id: Gmail message ID
            add_labels: List of label IDs to add
            remove_labels: List of label IDs to remove
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            modify_body = {}
            if add_labels:
                modify_body['addLabelIds'] = add_labels
            if remove_labels:
                modify_body['removeLabelIds'] = remove_labels
            
            self.service.users().messages().modify(
                userId='me',
                id=message_id,
                body=modify_body
            ).execute()
            
            logger.debug(f"Modified message {message_id}")
            return True
        except Exception as e:
            logger.error(f"Error modifying message {message_id}: {e}", exc_info=True)
            return False
