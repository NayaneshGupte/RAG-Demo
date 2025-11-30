"""
API blueprint for REST endpoints.
"""
from flask import Blueprint

api_bp = Blueprint('api', __name__, url_prefix='/api')

from app.api import routes, agent_routes
