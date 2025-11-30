from flask import render_template
from app.web import web_bp

# Web routes don't need to check auth - the dashboard JavaScript will handle that

@web_bp.route('/')
def index():
    """Render landing page."""
    return render_template('landing.html')

@web_bp.route('/dashboard')
def dashboard():
    """Render dashboard."""
    return render_template('dashboard.html')

@web_bp.route('/knowledge-base')
def knowledge_base():
    """Render knowledge base viewer."""
    return render_template('knowledge-base.html')

@web_bp.route('/recent-activity')
def recent_activity():
    """Render recent activity page."""
    return render_template('recent-activity.html')

@web_bp.route('/how-it-works')
def how_it_works():
    """Render how it works page."""
    return render_template('how-it-works.html')
