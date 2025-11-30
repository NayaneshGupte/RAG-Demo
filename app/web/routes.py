from flask import render_template
from app.web import web_bp

# Web routes don't need to check auth - the dashboard JavaScript will handle that

@web_bp.route('/')
def index():
    """Render dashboard home."""
    # Just render the template - auth.js will check auth status and show appropriate UI
    return render_template('dashboard.html')

@web_bp.route('/knowledge-base')
def knowledge_base():
    """Render knowledge base viewer."""
    return render_template('knowledge_base.html')
