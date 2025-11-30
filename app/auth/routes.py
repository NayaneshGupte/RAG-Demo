"""
OAuth authentication routes for Gmail.
Handles web-based OAuth flow with callback.
"""
import os
import logging
from flask import request, redirect, url_for, session, jsonify
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from app.auth import auth_bp
from app.config import Config

logger = logging.getLogger(__name__)

# Allow OAuth over HTTP for local development
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

# OAuth scopes
SCOPES = ['https://www.googleapis.com/auth/gmail.modify']


@auth_bp.route('/gmail/login')
def gmail_login():
    """
    Initiate Gmail OAuth flow.
    Redirects user to Google's consent screen.
    """
    try:
        # Create OAuth flow
        flow = Flow.from_client_secrets_file(
            Config.GMAIL_CREDENTIALS_FILE,
            scopes=SCOPES,
            redirect_uri=Config.OAUTH_REDIRECT_URI
        )
        
        # Generate authorization URL with state
        authorization_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent'  # Force consent to get refresh token
        )
        
        # Store state in session for verification
        session['oauth_state'] = state
        
        logger.info("Redirecting to Gmail OAuth consent screen")
        return redirect(authorization_url)
        
    except FileNotFoundError:
        logger.error(f"Credentials file not found: {Config.GMAIL_CREDENTIALS_FILE}")
        return jsonify({
            'error': 'Gmail credentials file not configured',
            'message': 'Please add credentials.json to the project root'
        }), 500
    except Exception as e:
        logger.error(f"Error initiating OAuth flow: {e}")
        return jsonify({'error': str(e)}), 500


@auth_bp.route('/gmail/callback')
def gmail_callback():
    """
    Handle OAuth callback from Google.
    Exchanges authorization code for credentials and saves token.
    """
    try:
        # Verify state parameter
        state = session.get('oauth_state')
        if not state:
            logger.error("No OAuth state found in session")
            return "Invalid session state", 400
        
        if request.args.get('state') != state:
            logger.error("OAuth state mismatch")
            return "Invalid state parameter", 400
        
        # Check for errors from OAuth provider
        if 'error' in request.args:
            error = request.args.get('error')
            logger.error(f"OAuth error: {error}")
            return f"OAuth authorization failed: {error}", 400
        
        # Create flow with same settings
        flow = Flow.from_client_secrets_file(
            Config.GMAIL_CREDENTIALS_FILE,
            scopes=SCOPES,
            state=state,
            redirect_uri=Config.OAUTH_REDIRECT_URI
        )
        
        # Exchange authorization code for credentials
        flow.fetch_token(authorization_response=request.url)
        credentials = flow.credentials
        
        # Save credentials to token file
        _save_credentials(credentials)
        
        # Get user email for session
        user_email = _get_user_email(credentials)
        
        # Store in session
        session['authenticated'] = True
        session['user_email'] = user_email
        session.permanent = True  # Make session persist
        
        logger.info(f"Gmail authentication successful for {user_email}")
        
        # Auto-start agent after successful auth
        from app.services.agent_manager import AgentManager
        agent_manager = AgentManager()
        try:
            agent_manager.start_agent(user_email)
            logger.info(f"Agent auto-started for {user_email}")
        except Exception as e:
            logger.error(f"Failed to auto-start agent: {e}")
        
        # Redirect to dashboard
        return redirect(url_for('web.index'))
        
    except Exception as e:
        logger.error(f"Error in OAuth callback: {e}")
        return jsonify({'error': str(e)}), 500


@auth_bp.route('/status')
def auth_status():
    """
    Get current authentication status.
    Returns JSON with auth state and user email.
    """
    authenticated = session.get('authenticated', False)
    user_email = session.get('user_email', None)
    
    # Also check if token file exists and is valid (but don't trigger OAuth)
    if not authenticated and os.path.exists(Config.GMAIL_TOKEN_FILE):
        try:
            creds = Credentials.from_authorized_user_file(Config.GMAIL_TOKEN_FILE, SCOPES)
            if creds and creds.valid:
                # Get user email without triggering full service init
                from googleapiclient.discovery import build
                service = build('gmail', 'v1', credentials=creds)
                profile = service.users().getProfile(userId='me').execute()
                user_email = profile.get('emailAddress')
                
                session['authenticated'] = True
                session['user_email'] = user_email
                authenticated = True
        except Exception as e:
            # Token invalid or expired - user needs to re-authenticate
            logger.debug(f"Could not load credentials from file: {e}")
            authenticated = False
            user_email = None
    
    return jsonify({
        'authenticated': authenticated,
        'user_email': user_email
    })


@auth_bp.route('/logout', methods=['POST'])
def logout():
    """
    Logout user and optionally stop agent.
    Clears session and can delete token file.
    """
    try:
        user_email = session.get('user_email')
        
        # Stop agent if running
        from app.services.agent_manager import AgentManager
        agent_manager = AgentManager()
        try:
            if agent_manager.is_running():
                agent_manager.stop_agent()
                logger.info(f"Agent stopped for {user_email}")
        except Exception as e:
            logger.error(f"Error stopping agent: {e}")
        
        # Clear session
        session.clear()
        
        # Optionally delete token file (uncomment if desired)
        # if os.path.exists(Config.GMAIL_TOKEN_FILE):
        #     os.remove(Config.GMAIL_TOKEN_FILE)
        
        logger.info(f"User logged out: {user_email}")
        return jsonify({'success': True})
        
    except Exception as e:
        logger.error(f"Error during logout: {e}")
        return jsonify({'error': str(e)}), 500


def _save_credentials(credentials: Credentials):
    """Save credentials to token file."""
    try:
        with open(Config.GMAIL_TOKEN_FILE, 'w') as token:
            token.write(credentials.to_json())
        logger.debug("Credentials saved to token file")
    except Exception as e:
        logger.error(f"Error saving credentials: {e}")
        raise


def _get_user_email(credentials: Credentials) -> str:
    """Get user email from credentials."""
    try:
        from googleapiclient.discovery import build
        service = build('gmail', 'v1', credentials=credentials)
        profile = service.users().getProfile(userId='me').execute()
        return profile.get('emailAddress', 'unknown')
    except Exception as e:
        logger.error(f"Error getting user email: {e}")
        return 'unknown'
