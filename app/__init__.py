from flask import Flask
from flask_cors import CORS
from app.config import Config
import os

def create_app(config_class=Config):
    """Create and configure the Flask application."""
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Initialize extensions
    CORS(app, resources={r"/api/*": {"origins": "*"}})
    
    # Register Blueprints
    from app.api import api_bp
    from app.web import web_bp
    
    app.register_blueprint(api_bp)
    app.register_blueprint(web_bp)
    
    return app
