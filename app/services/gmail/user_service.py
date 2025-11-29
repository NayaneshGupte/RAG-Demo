"""
Gmail user information service.
Handles retrieving user profile and account information.
"""
import logging
from typing import Optional, Dict
from googleapiclient.discovery import Resource

logger = logging.getLogger(__name__)


class GmailUserService:
    """Service for retrieving user information."""
    
    def __init__(self, service: Resource):
        """
        Initialize user service.
        
        Args:
            service: Gmail API service instance
        """
        self.service = service
    
    def get_current_email(self) -> Optional[str]:
        """
        Get current logged-in user's email address.
        
        Returns:
            str: Email address or None if failed
        """
        try:
            profile = self.get_profile()
            if profile:
                email = profile.get('emailAddress')
                logger.debug(f"Retrieved current email: {email}")
                return email
            return None
        except Exception as e:
            logger.error(f"Error getting current email: {e}", exc_info=True)
            return None
    
    def get_profile(self) -> Optional[Dict]:
        """
        Get user profile information.
        
        Returns:
            Dict: User profile info or None if failed
        """
        try:
            profile = self.service.users().getProfile(userId='me').execute()
            logger.info("Retrieved user profile")
            return profile
        except Exception as e:
            logger.error(f"Error retrieving profile: {e}", exc_info=True)
            return None
