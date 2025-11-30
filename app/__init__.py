from flask import Flask
from flask_cors import CORS
from app.config import Config
import os
import logging

logger = logging.getLogger(__name__)

def create_app(config_class=Config):
    """Create and configure the Flask application."""
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Set secret key for sessions
    app.secret_key = config_class.SECRET_KEY
    app.config['SESSION_TYPE'] = 'filesystem'
    app.config['PERMANENT_SESSION_LIFETIME'] = 86400 * 30  # 30 days
    
    # Initialize extensions
    CORS(app, resources={r"/api/*": {"origins": "*"}})
    
    # Register Blueprints
    from app.api import api_bp
    from app.web import web_bp
    from app.auth import auth_bp
    
    app.register_blueprint(api_bp)
    app.register_blueprint(web_bp)
    app.register_blueprint(auth_bp)
    
    # Register agent API routes
    from app.api import agent_routes
    
    # Auto-resume agent if authenticated (on app startup)
    with app.app_context():
        try:
            from app.services.agent_manager import AgentManager
            agent_manager = AgentManager()
            agent_manager.auto_resume_if_authenticated()
        except Exception as e:
            logger.error(f"Error auto-resuming agent: {e}")
    
    return app
