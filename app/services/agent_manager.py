"""
Agent Manager Service
Manages the email agent as a background process with auto-resume capability.
"""
import os
import json
import logging
import time
import threading
from typing import Optional, Dict
from datetime import datetime
from app.config import Config

logger = logging.getLogger(__name__)

class AgentManager:
    """
    Manages agent lifecycle as a background thread.
    Supports start, stop, status check, and auto-resume on Flask restart.
    """
    
    STATUS_FILE = "agent_status.json"
    _instance = None
    _agent_thread = None
    _should_stop = False
    
    def __new__(cls):
        """Singleton pattern to ensure one agent manager instance."""
        if cls._instance is None:
            cls._instance = super(AgentManager, cls).__new__(cls)
        return cls._instance
    
    def start_agent(self, user_email: str):
        """
        Start the email agent in a background thread.
        
        Args:
            user_email: Email of authenticated user
        """
        if self.is_running():
            logger.warning("Agent already running")
            return
        
        try:
            logger.info(f"Starting agent for {user_email}")
            
            # Reset stop flag
            AgentManager._should_stop = False
            
            # Start agent in background thread
            AgentManager._agent_thread = threading.Thread(
                target=self._run_agent,
                args=(user_email,),
                daemon=True,
                name="EmailAgentThread"
            )
            AgentManager._agent_thread.start()
            
            # Update status file
            self._update_status({
                'running': True,
                'user_email': user_email,
                'started_at': datetime.now().isoformat(),
                'pid': os.getpid(),
                'last_poll': None,
                'processed_count': 0
            })
            
            logger.info(f"Agent started successfully for {user_email}")
            
        except Exception as e:
            logger.error(f"Failed to start agent: {e}")
            raise
    
    def stop_agent(self):
        """Stop the running agent gracefully."""
        if not self.is_running():
            logger.warning("Agent not running")
            return
        
        try:
            logger.info("Stopping agent...")
            
            # Set stop flag
            AgentManager._should_stop = True
            
            # Wait for thread to finish (with timeout)
            if AgentManager._agent_thread:
                AgentManager._agent_thread.join(timeout=5.0)
            
            # Update status file
            self._update_status({
                'running': False,
                'stopped_at': datetime.now().isoformat()
            })
            
            AgentManager._agent_thread = None
            logger.info("Agent stopped successfully")
            
        except Exception as e:
            logger.error(f"Error stopping agent: {e}")
            raise
    
    def is_running(self) -> bool:
        """Check if agent is currently running."""
        return (AgentManager._agent_thread is not None and 
                AgentManager._agent_thread.is_alive())
    
    def get_status(self) -> Dict:
        """
        Get current agent status.
        
        Returns:
            Dict with status information
        """
        status = self._load_status()
        
        # Update running state based on actual thread
        status['running'] = self.is_running()
        
        # Calculate uptime if running
        if status['running'] and status.get('started_at'):
            try:
                started = datetime.fromisoformat(status['started_at'])
                uptime_seconds = (datetime.now() - started).total_seconds()
                status['uptime'] = int(uptime_seconds)
                status['uptime_formatted'] = self._format_uptime(uptime_seconds)
            except Exception:
                status['uptime'] = 0
                status['uptime_formatted'] = "Unknown"
        
        return status
    
    def auto_resume_if_authenticated(self):
        """
        Auto-resume agent if valid authentication exists.
        Called on Flask app startup.
        """
        try:
            # Check if token file exists
            if not os.path.exists(Config.GMAIL_TOKEN_FILE):
                logger.info("No token file found, agent auto-resume skipped")
                return
            
            # Check if credentials are valid
            from google.oauth2.credentials import Credentials
            try:
                creds = Credentials.from_authorized_user_file(
                    Config.GMAIL_TOKEN_FILE,
                    ['https://www.googleapis.com/auth/gmail.modify']
                )
                
                if not creds or not creds.valid:
                    logger.info("Token invalid, agent auto-resume skipped")
                    return
                
                # Get user email
                from googleapiclient.discovery import build
                service = build('gmail', 'v1', credentials=creds)
                profile = service.users().getProfile(userId='me').execute()
                user_email = profile.get('emailAddress')
                
                # Start agent
                if not self.is_running():
                    self.start_agent(user_email)
                    logger.info(f"Agent auto-resumed for {user_email}")
                
            except Exception as e:
                logger.debug(f"Could not auto-resume agent: {e}")
                
        except Exception as e:
            logger.error(f"Error in auto-resume: {e}")
    
    def _run_agent(self, user_email: str):
        """
        Run the agent loop in background thread.
        
        Args:
            user_email: Email of authenticated user
        """
        try:
            # Import here to avoid circular imports
            from app.services.agent_service import AgentService
            
            # Create agent instance
            agent = AgentService()
            
            logger.info(f"Agent loop starting for {user_email}")
            processed_count = 0
            
            # Main agent loop
            while not AgentManager._should_stop:
                try:
                    # Process emails
                    agent.process_emails()
                    
                    # Update status
                    self._update_status({
                        'last_poll': datetime.now().isoformat(),
                        'processed_count': processed_count
                    })
                    
                    # Sleep for poll interval (default 60s)
                    poll_interval = Config.AGENT_POLL_INTERVAL if hasattr(Config, 'AGENT_POLL_INTERVAL') else 60
                    
                    # Sleep in small chunks to allow quick shutdown
                    for _ in range(poll_interval):
                        if AgentManager._should_stop:
                            break
                        time.sleep(1)
                    
                except Exception as e:
                    logger.error(f"Error in agent loop: {e}")
                    time.sleep(10)  # Wait before retry
            
            logger.info("Agent loop ended")
            
        except Exception as e:
            logger.error(f"Fatal error in agent thread: {e}")
            self._update_status({'running': False, 'error': str(e)})
    
    def _load_status(self) -> Dict:
        """Load status from file."""
        if os.path.exists(self.STATUS_FILE):
            try:
                with open(self.STATUS_FILE, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.debug(f"Could not load status file: {e}")
        
        return {
            'running': False,
            'user_email': None,
            'started_at': None,
            'last_poll': None,
            'processed_count': 0
        }
    
    def _update_status(self, updates: Dict):
        """Update status file with new information."""
        try:
            status = self._load_status()
            status.update(updates)
            
            with open(self.STATUS_FILE, 'w') as f:
                json.dump(status, f, indent=2)
        except Exception as e:
            logger.error(f"Could not update status file: {e}")
    
    def _format_uptime(self, seconds: float) -> str:
        """Format uptime in human-readable format."""
        seconds = int(seconds)
        
        if seconds < 60:
            return f"{seconds}s"
        elif seconds < 3600:
            minutes = seconds // 60
            return f"{minutes}m"
        elif seconds < 86400:
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            return f"{hours}h {minutes}m"
        else:
            days = seconds // 86400
            hours = (seconds % 86400) // 3600
            return f"{days}d {hours}h"
