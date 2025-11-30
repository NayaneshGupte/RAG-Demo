"""
Agent control API routes.
"""
import logging
from flask import jsonify, session
from app.api import api_bp
from app.services.agent_manager import AgentManager

logger = logging.getLogger(__name__)


@api_bp.route('/agent/start', methods=['POST'])
def start_agent():
    """Start the email agent."""
    try:
        # Check if authenticated
        if not session.get('authenticated'):
            return jsonify({'error': 'Not authenticated'}), 401
        
        user_email = session.get('user_email')
        if not user_email:
            return jsonify({'error': 'User email not found in session'}), 400
        
        # Start agent
        agent_manager = AgentManager()
        
        if agent_manager.is_running():
            return jsonify({
                'success': False,
                'message': 'Agent already running'
            })
        
        agent_manager.start_agent(user_email)
        
        return jsonify({
            'success': True,
            'message': f'Agent started for {user_email}'
        })
        
    except Exception as e:
        logger.error(f"Error starting agent: {e}")
        return jsonify({'error': str(e)}), 500


@api_bp.route('/agent/stop', methods=['POST'])
def stop_agent():
    """Stop the email agent."""
    try:
        agent_manager = AgentManager()
        
        if not agent_manager.is_running():
            return jsonify({
                'success': False,
                'message': 'Agent not running'
            })
        
        agent_manager.stop_agent()
        
        return jsonify({
            'success': True,
            'message': 'Agent stopped'
        })
        
    except Exception as e:
        logger.error(f"Error stopping agent: {e}")
        return jsonify({'error': str(e)}), 500


@api_bp.route('/agent/status')
def agent_status():
    """
    Get agent status.
    Returns JSON with agent state and metrics.
    """
    try:
        # Check if this is a demo user
        is_demo = session.get('is_demo', False)
        
        if is_demo:
            # Return realistic mock values for demo mode
            from datetime import datetime, timedelta
            import random
            
            # Simulate agent running with realistic values
            mock_start_time = datetime.now() - timedelta(hours=3, minutes=27)
            last_poll_time = datetime.now() - timedelta(minutes=random.randint(1, 5))
            
            return jsonify({
                'running': True,
                'user_email': 'demo@example.com',
                'started_at': mock_start_time.isoformat(),
                'last_poll': last_poll_time.isoformat(),
                'processed_count': 325,  # Match the dashboard total
                'uptime': int((datetime.now() - mock_start_time).total_seconds()),
                'uptime_formatted': '3h 27m'
            })
        
        # For real users, get actual agent status
        agent_manager = AgentManager()
        status = agent_manager.get_status()
        
        return jsonify(status)
        
    except Exception as e:
        logger.error(f"Error getting agent status: {e}")
        return jsonify({'error': str(e)}), 500
