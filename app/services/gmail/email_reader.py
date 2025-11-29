"""
Gmail email reading and parsing service.
Handles fetching unread emails, parsing headers, and extracting body content.
"""
import base64
import logging
from typing import List, Dict, Optional
from googleapiclient.discovery import Resource

logger = logging.getLogger(__name__)


class GmailEmailReader:
    """Service for reading and parsing emails from Gmail."""
    
    def __init__(self, service: Resource):
        """
        Initialize email reader service.
        
        Args:
            service: Gmail API service instance
        """
        self.service = service
    
    def get_unread_emails(self, after_timestamp: Optional[int] = None) -> List[Dict]:
        """
        Fetch unread emails with optional timestamp filtering.
        
        Args:
            after_timestamp: Optional timestamp in seconds to filter emails
            
        Returns:
            List[Dict]: List of email objects with metadata
        """
        query = self._build_query(after_timestamp)
        logger.info(f"Fetching emails with query: {query}")
        
        try:
            messages = self._fetch_message_list(query)
            email_data = self._parse_messages(messages)
            logger.info(f"Retrieved {len(email_data)} unread emails")
            return email_data
        except Exception as e:
            logger.error(f"Error fetching emails: {e}", exc_info=True)
            return []
    
    def _build_query(self, after_timestamp: Optional[int] = None) -> str:
        """
        Build Gmail search query.
        
        Args:
            after_timestamp: Optional timestamp to filter newer emails
            
        Returns:
            str: Gmail search query string
        """
        query = 'is:unread'
        if after_timestamp:
            # Gmail 'after' accepts seconds since epoch
            query += f' after:{int(after_timestamp)}'
        
        return query
    
    def _fetch_message_list(self, query: str) -> List[Dict]:
        """
        Fetch message list from Gmail API.
        
        Args:
            query: Gmail search query
            
        Returns:
            List[Dict]: List of message metadata
        """
        try:
            results = self.service.users().messages().list(userId='me', q=query).execute()
            messages = results.get('messages', [])
            logger.debug(f"Fetched {len(messages)} message IDs from API")
            return messages
        except Exception as e:
            logger.error(f"Error fetching message list: {e}")
            raise
    
    def _parse_messages(self, messages: List[Dict]) -> List[Dict]:
        """
        Parse raw messages into structured format.
        
        Args:
            messages: List of message metadata from API
            
        Returns:
            List[Dict]: List of structured email objects
        """
        email_data = []
        
        for msg in messages:
            try:
                msg_detail = self.service.users().messages().get(
                    userId='me', id=msg['id']
                ).execute()
                
                payload = msg_detail.get('payload', {})
                headers = self._extract_headers(payload.get('headers', []))
                body = self._extract_body(payload)
                
                email_obj = {
                    'id': msg['id'],
                    'threadId': msg['threadId'],
                    'messageId': headers.get('message_id', ''),
                    'references': headers.get('references', ''),
                    'sender': headers.get('from', 'Unknown'),
                    'subject': headers.get('subject', 'No Subject'),
                    'body': body,
                    'snippet': msg_detail.get('snippet', ''),
                    'internalDate': int(msg_detail.get('internalDate', 0))
                }
                
                email_data.append(email_obj)
                logger.debug(f"Parsed email: {email_obj['subject']}")
            except Exception as e:
                logger.error(f"Error parsing message {msg['id']}: {e}")
                continue
        
        return email_data
    
    def _extract_headers(self, headers: List[Dict]) -> Dict[str, str]:
        """
        Extract specific headers from message.
        
        Args:
            headers: List of header dicts from API
            
        Returns:
            Dict: Dictionary of extracted headers
        """
        header_map = {
            'Subject': 'subject',
            'From': 'from',
            'Message-ID': 'message_id',
            'References': 'references'
        }
        
        extracted = {}
        for header in headers:
            name = header.get('name')
            value = header.get('value', '')
            
            if name in header_map:
                extracted[header_map[name]] = value
        
        return extracted
    
    def _extract_body(self, payload: Dict) -> str:
        """
        Extract and decode email body.
        
        Args:
            payload: Message payload from API
            
        Returns:
            str: Decoded email body
        """
        body = ""
        
        try:
            if 'parts' in payload:
                for part in payload['parts']:
                    if part.get('mimeType') == 'text/plain':
                        data = part.get('body', {}).get('data')
                        if data:
                            body = base64.urlsafe_b64decode(data).decode()
                            break
            else:
                data = payload.get('body', {}).get('data')
                if data:
                    body = base64.urlsafe_b64decode(data).decode()
            
            logger.debug(f"Extracted body: {len(body)} characters")
        except Exception as e:
            logger.error(f"Error extracting body: {e}")
        
        return body
