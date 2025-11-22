"""
Flask dashboard for monitoring email agent activity.
"""
from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
from werkzeug.utils import secure_filename
import tempfile
from app.services.database_service import DatabaseService
from app.services.gmail_service import GmailService
from app.services.ingestion_service import IngestionService
from app.services.vector_store_service import VectorStoreService
import os

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})
db_service = DatabaseService()
gmail_service = GmailService()
ingestion_service = IngestionService()
vector_store_service = VectorStoreService()

@app.route('/')
def index():
    """Render dashboard home."""
    current_user = gmail_service.get_current_email()
    return render_template('dashboard.html', current_user=current_user)

@app.route('/api/logs')
def get_logs():
    """Get recent logs as JSON."""
    current_user = gmail_service.get_current_email()
    # Return all logs, frontend will handle filtering
    logs = db_service.get_logs(limit=100, exclude_ignored=False, agent_email=current_user)
    stats = db_service.get_stats(agent_email=current_user)
    
    # Get KB stats
    kb_stats = vector_store_service.get_stats()
    total_vectors = kb_stats.get('total_vector_count', 0)
    
    return jsonify({
        "logs": logs,
        "stats": stats,
        "kb_stats": {"total_vectors": total_vectors},
        "current_user": current_user
    })

@app.route('/knowledge-base')
def knowledge_base():
    """Render knowledge base viewer."""
    current_user = gmail_service.get_current_email()
    return render_template('knowledge_base.html', current_user=current_user)

@app.route('/api/knowledge-base')
def get_knowledge_base():
    """Get paginated knowledge base documents."""
    limit = request.args.get('limit', 3, type=int)
    token = request.args.get('token', None)
    
    result = vector_store_service.list_documents(limit=limit, pagination_token=token)
    
    return jsonify(result)

@app.route('/api/upload', methods=['POST'])
def upload_file():
    """Handle PDF file upload and ingestion."""
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
        
    if file and file.filename.lower().endswith('.pdf'):
        try:
            # Save to temp file
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
                file.save(temp_file.name)
                temp_path = temp_file.name
            
            # Process
            chunks = ingestion_service.process_pdf(temp_path, file.filename)
            
            # Cleanup
            if os.path.exists(temp_path):
                os.remove(temp_path)
                
            return jsonify({'message': f'Successfully ingested {chunks} chunks from {file.filename}'}), 200
            
        except Exception as e:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            return jsonify({'error': str(e)}), 500
    else:
        return jsonify({'error': 'Invalid file type. Only PDF allowed.'}), 400

if __name__ == '__main__':
    app.run(debug=True, port=5000)
