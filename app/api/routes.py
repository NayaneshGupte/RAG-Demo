from flask import jsonify, request, session, make_response
from app.api import api_bp
from app.services.database_service import DatabaseService
from app.services.gmail_service import GmailService
from app.services.ingestion_service import IngestionService
from app.services.vector_store_service import VectorStoreService
import tempfile
import os
from functools import wraps

# Security decorator to prevent caching
def no_cache(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        resp = make_response(f(*args, **kwargs))
        resp.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, private'
        resp.headers['Pragma'] = 'no-cache'
        resp.headers['Expires'] = '0'
        return resp
    return decorated_function

# Don't initialize services globally - they'll be initialized in each route
# This avoids requiring auth before the user can access the dashboard


@api_bp.route('/logs')
@no_cache
def get_logs():
    """Get recent logs as JSON with user isolation and optional date filtering."""
    try:
        # Check for session-based auth (demo mode or OAuth)
        current_user = session.get('user_email')
        is_demo = session.get('is_demo', False)
        
        if not current_user:
            # Try Gmail OAuth if no session
            try:
                gmail_service = GmailService()
                current_user = gmail_service.get_current_email()
                # Store in session for subsequent requests
                session['user_email'] = current_user
                session['is_demo'] = False
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
        
        # Get optional date range parameters
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        # CRITICAL: Filter all data by agent_email to prevent data leakage
        logs = db_service.get_logs(
            limit=100, 
            exclude_ignored=False, 
            agent_email=current_user,
            start_date=start_date,
            end_date=end_date
        )
        stats = db_service.get_stats(agent_email=current_user)
        
        # Get KB stats
        kb_stats = vector_store_service.get_stats()
        total_vectors = kb_stats.get('total_vector_count', 0)
        
        return jsonify({
            "logs": logs,
            "stats": stats,
            "kb_stats": {"total_vectors": total_vectors},
            "current_user": current_user,
            "auth_required": False,
            "is_demo": is_demo
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


@api_bp.route('/metrics/email-volume')
def get_email_volume_metrics():
    """Get email volume data for charts with optional date range."""
    try:
        from datetime import datetime, timedelta
        
        db_service = DatabaseService()
        
        # Get date range from query parameters
        start_date_str = request.args.get('start_date')
        end_date_str = request.args.get('end_date')
        interval = request.args.get('interval', 'day')
        
        # Default to last 7 days if not provided
        if not start_date_str or not end_date_str:
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=7)
            days = 7
        else:
            try:
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
                days = (end_date - start_date).days + 1
            except ValueError:
                return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400
        
        # Get current user from session for isolation
        current_user = session.get('user_email')
        
        # Get data for the specified date range
        volume_data = db_service.get_email_volume_by_day(
            days=days, 
            start_date=start_date.isoformat(), 
            interval=interval,
            agent_email=current_user
        )
        
        labels = [item['date'] for item in volume_data]
        total = [item['total'] for item in volume_data]
        responded = [item['responded'] for item in volume_data]
        ignored = [item['ignored'] for item in volume_data]
        failed = [item['failed'] for item in volume_data]
        
        return jsonify({
            'labels': labels,
            'total': total,
            'responded': responded,
            'ignored': ignored,
            'failed': failed
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/metrics/categories')
def get_category_metrics():
    """Get category breakdown for pie/donut chart."""
    try:
        db_service = DatabaseService()
        
        # Get current user from session for isolation
        current_user = session.get('user_email')
        
        # Get category counts
        categories = db_service.get_category_breakdown(agent_email=current_user)
        
        labels = [item['category'] for item in categories]
        values = [item['count'] for item in categories]
        
        return jsonify({
            'labels': labels,
            'values': values
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/knowledge-base/stats')
def get_kb_stats():
    """Get knowledge base statistics."""
    try:
        vector_store_service = VectorStoreService()
        stats = vector_store_service.get_stats()
        
        return jsonify({
            'total_chunks': stats.get('total_vector_count', 0),
            'total_documents': stats.get('total_documents', 0),
            'last_updated': stats.get('last_updated', '--')
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
@api_bp.route('/metrics/summary')
def get_summary_metrics():
    """Get summary statistics (total, responded, ignored)."""
    try:
        db_service = DatabaseService()
        current_user = session.get('user_email')
        
        stats = db_service.get_stats(agent_email=current_user)
        
        return jsonify(stats)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
