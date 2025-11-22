"""
Logging configuration for the application.
"""
import logging
import os
from app.config import Config

def setup_logging():
    """Configure application logging."""
    # Create logs directory if it doesn't exist
    os.makedirs(os.path.dirname(Config.LOG_FILE), exist_ok=True)
    
    # Configure logging
    logging.basicConfig(
        level=getattr(logging, Config.LOG_LEVEL),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(Config.LOG_FILE),
            logging.StreamHandler()
        ]
    )
    
    return logging.getLogger(__name__)
