from flask import jsonify, request, session
from app.api import api_bp
from app.services.database_service import DatabaseService
from app.services.gmail_service import GmailService
from app.services.ingestion_service import IngestionService
from app.services.vector_store_service import VectorStoreService
import tempfile
import os

# Don't initialize services globally - they'll be initialized in each route
# This avoids requiring auth before the user can access the dashboard

@api_bp.route('/logs')
def get_logs():
    """Get recent logs as JSON."""
    try:
        # Initialize services only when needed
        # If no valid auth, this will raise PermissionError
        try:
            gmail_service = GmailService()
            current_user = gmail_service.get_current_email()
        except PermissionError:
            # No valid auth - return empty data
            return jsonify({
                "logs": [],
                "stats": {"total": 0, "responded": 0, "ignored": 0, "failed": 0},
                "kb_stats": {"total_vectors": 0},
                "current_user": None,
                "auth_required": True
            })
        
        db_service = DatabaseService()
        vector_store_service = VectorStoreService()
        
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
            "current_user": current_user,
            "auth_required": False
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api_bp.route('/knowledge-base')
def get_knowledge_base():
    """Get paginated knowledge base documents."""
    try:
        limit = request.args.get('limit', 3, type=int)
        token = request.args.get('token', None)
        
        vector_store_service = VectorStoreService()
        result = vector_store_service.list_documents(limit=limit, pagination_token=token)
        
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api_bp.route('/upload', methods=['POST'])
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
            ingestion_service = IngestionService()
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
