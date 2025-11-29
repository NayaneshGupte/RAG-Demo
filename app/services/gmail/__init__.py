"""
Gmail service module.
Provides unified interface for all Gmail operations.
"""
from app.services.gmail.auth_service import GmailAuthService
from app.services.gmail.email_reader import GmailEmailReader
from app.services.gmail.email_composer import GmailEmailComposer
from app.services.gmail.email_sender import GmailEmailSender
from app.services.gmail.email_modifier import GmailEmailModifier
from app.services.gmail.user_service import GmailUserService

__all__ = [
    'GmailAuthService',
    'GmailEmailReader',
    'GmailEmailComposer',
    'GmailEmailSender',
    'GmailEmailModifier',
    'GmailUserService',
]
