from flask import render_template
from app.web import web_bp
from app.services.gmail_service import GmailService

# Initialize service
gmail_service = GmailService()

@web_bp.route('/')
def index():
    """Render dashboard home."""
    current_user = gmail_service.get_current_email()
    return render_template('dashboard.html', current_user=current_user)

@web_bp.route('/knowledge-base')
def knowledge_base():
    """Render knowledge base viewer."""
    current_user = gmail_service.get_current_email()
    return render_template('knowledge_base.html', current_user=current_user)
