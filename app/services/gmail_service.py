"""
Gmail service for email operations.
"""
import os
import base64
import logging
from email.mime.text import MIMEText
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from app.config import Config

logger = logging.getLogger(__name__)

SCOPES = ['https://www.googleapis.com/auth/gmail.modify']

class GmailService:
    """Service for Gmail operations."""
    
    def __init__(self):
        self.service = self._authenticate()
    
    def _authenticate(self):
        """Authenticate and return Gmail API service."""
        creds = None
        
        if os.path.exists(Config.GMAIL_TOKEN_FILE):
            creds = Credentials.from_authorized_user_file(Config.GMAIL_TOKEN_FILE, SCOPES)
        
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                logger.info("Refreshing Gmail credentials")
                creds.refresh(Request())
            else:
                if not os.path.exists(Config.GMAIL_CREDENTIALS_FILE):
                    raise FileNotFoundError(
                        f"Gmail credentials file not found: {Config.GMAIL_CREDENTIALS_FILE}"
                    )
                
                logger.info("Starting Gmail OAuth flow")
                flow = InstalledAppFlow.from_client_secrets_file(
                    Config.GMAIL_CREDENTIALS_FILE, SCOPES
                )
                creds = flow.run_local_server(port=0)
            
            with open(Config.GMAIL_TOKEN_FILE, 'w') as token:
                token.write(creds.to_json())
        
        logger.info("Gmail service authenticated successfully")
        return build('gmail', 'v1', credentials=creds)
    
    def get_unread_emails(self, after_timestamp=None):
        """Fetch unread emails, optionally filtering by timestamp."""
        query = 'is:unread'
        if after_timestamp:
            # Gmail 'after' accepts seconds since epoch
            query += f' after:{int(after_timestamp)}'
            
        logger.info(f"Fetching emails with query: {query}")
        results = self.service.users().messages().list(userId='me', q=query).execute()
        messages = results.get('messages', [])
        
        email_data = []
        
        for msg in messages:
            msg_detail = self.service.users().messages().get(userId='me', id=msg['id']).execute()
            payload = msg_detail.get('payload', {})
            headers = payload.get('headers', [])
            
            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
            sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown')
            message_id = next((h['value'] for h in headers if h['name'] == 'Message-ID'), '')
            references = next((h['value'] for h in headers if h['name'] == 'References'), '')
            
            body = self._extract_body(payload)
            
            email_data.append({
                'id': msg['id'],
                'threadId': msg['threadId'],
                'messageId': message_id,
                'references': references,
                'sender': sender,
                'subject': subject,
                'body': body,
                'snippet': msg_detail.get('snippet', ''),
                'internalDate': int(msg_detail.get('internalDate', 0))
            })
        
        logger.info(f"Retrieved {len(email_data)} unread emails")
        return email_data
    
    def _extract_body(self, payload):
        """Extract email body from payload."""
        body = ""
        
        if 'parts' in payload:
            for part in payload['parts']:
                if part['mimeType'] == 'text/plain':
                    data = part['body'].get('data')
                    if data:
                        body = base64.urlsafe_b64decode(data).decode()
                        break
        else:
            data = payload['body'].get('data')
            if data:
                body = base64.urlsafe_b64decode(data).decode()
        
        return body
    
    def send_reply(self, to, subject, body, thread_id, message_id=None, references=None):
        """Send a reply to an email thread."""
        message = MIMEText(body)
        message['to'] = to
        message['subject'] = subject if subject.lower().startswith('re:') else f"Re: {subject}"
        
        if message_id:
            message['In-Reply-To'] = message_id
            message['References'] = f"{references} {message_id}" if references else message_id
        
        create_message = {
            'raw': base64.urlsafe_b64encode(message.as_bytes()).decode(),
            'threadId': thread_id
        }
        
        try:
            sent_message = (
                self.service.users().messages()
                .send(userId='me', body=create_message)
                .execute()
            )
            logger.info(f'Sent reply to {to}, Message Id: {sent_message["id"]}')
            return sent_message
        except Exception as error:
            logger.error(f'Error sending reply: {error}')
            return None
    
    def mark_as_read(self, msg_id):
        """Mark an email as read."""
        try:
            self.service.users().messages().modify(
                userId='me',
                id=msg_id,
                body={'removeLabelIds': ['UNREAD']}
            ).execute()
            logger.debug(f"Marked email {msg_id} as read")
        except Exception as error:
            logger.error(f'Error marking email as read: {error}')

    def get_current_email(self):
        """Get the email address of the authenticated user."""
        try:
            profile = self.service.users().getProfile(userId='me').execute()
            return profile['emailAddress']
        except Exception as error:
            logger.error(f'Error fetching profile: {error}')
            return "Unknown"
