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
    
    SECURITY: Only checks session. Does NOT auto-login from token.json.
    This prevents unauthorized access from different browsers/sessions.
    """
    authenticated = session.get('authenticated', False)
    user_email = session.get('user_email', None)
    
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
        
        # Delete token file to prevent auto-login after logout
        if os.path.exists(Config.GMAIL_TOKEN_FILE):
            os.remove(Config.GMAIL_TOKEN_FILE)
            logger.info("Token file deleted on logout")
        
        logger.info(f"User logged out: {user_email}")
        return jsonify({'success': True})
        
    except Exception as e:
        logger.error(f"Error during logout: {e}")
        return jsonify({'error': 'Logout failed'}), 500


@auth_bp.route('/demo/login')
def demo_login():
    """
    Demo mode login - bypasses OAuth and creates a demo session.
    For demonstration purposes only.
    """
    try:
        # Clear any existing session
        session.clear()
        
        # Auto-clear and reseed demo data for fresh start
        demo_email = 'demo@example.com'
        logger.info(f"Clearing old data for {demo_email}...")
        
        from app.services.database_service import DatabaseService
        db = DatabaseService()
        
        # Delete all existing demo user data
        try:
            with db._get_connection() as conn:
                conn.execute("DELETE FROM email_logs WHERE agent_email = ? OR agent_email IS NULL", (demo_email,))
                conn.commit()
                logger.info("Deleted old demo data")
        except Exception as e:
            logger.error(f"Error clearing demo data: {e}")
        
        # Reseed with fresh 12-month dataset
        logger.info("Reseeding demo data from demo.json...")
        try:
            import sys
            import os
            # Add project root to path to import seed function
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            if project_root not in sys.path:
                sys.path.insert(0, project_root)
            
            from seed_demo_data import seed_demo_data
            seed_demo_data()
            logger.info("Demo data reseeded successfully")
        except Exception as e:
            logger.error(f"Error reseeding demo data: {e}")
        
        # Create demo session
        session['user_email'] = demo_email
        session['is_demo'] = True
        session['authenticated'] = True
        session.permanent = False  # Session expires when browser closes
        
        # Prevent caching
        response = redirect(url_for('web.index'))
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        
        logger.info("Demo session created for demo@example.com")
        return response
        
    except Exception as e:
        logger.error(f"Error creating demo session: {e}")
        return jsonify({'error': 'Failed to create demo session'}), 500


@auth_bp.route('/demo/logout', methods=['POST'])
def demo_logout():
    """
    Demo mode logout - clears demo session.
    """
    try:
        # Check if it's actually a demo session
        is_demo = session.get('is_demo', False)
        
        # Clear session
        session.clear()
        
        logger.info("Demo session cleared")
        return jsonify({'success': True, 'is_demo': is_demo})
        
    except Exception as e:
        logger.error(f"Error during demo logout: {e}")
        return jsonify({'error': 'Demo logout failed'}), 500


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
