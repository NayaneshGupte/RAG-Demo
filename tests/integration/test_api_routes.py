"""
Integration tests for API routes

Tests cover:
- Authentication requirements
- User data isolation
- Date range filtering
- Pagination
- Response formats
- Error handling
- Cache headers
"""

import pytest
import json
from datetime import datetime, timedelta


class TestAuthenticationRequired:
    """Test that API routes require authentication."""
    
    def test_logs_endpoint_requires_auth(self, client):
        """Test that /api/logs requires authentication."""
        response = client.get('/api/logs')
        assert response.status_code == 401
    
    def test_metrics_endpoint_requires_auth(self, client):
        """Test that /api/metrics/* requires authentication."""
        endpoints = [
            '/api/metrics/email-volume',
            '/api/metrics/categories'
        ]
        
        for endpoint in endpoints:
            response = client.get(endpoint)
            assert response.status_code == 401


class TestLogsEndpoint:
    """Test /api/logs endpoint."""
    
    def test_get_logs_success(self, demo_user_session, test_db, sample_logs_data):
        """Test successful log retrieval."""
        # Seed database
        for log_data in sample_logs_data[:10]:
            test_db.log_email(**log_data)
        
        response = demo_user_session.get('/api/logs')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert 'logs' in data
        assert isinstance(data['logs'], list)
    
    def test_get_logs_pagination(self, demo_user_session, test_db, sample_logs_data):
        """Test log pagination."""
        # Seed database with 30 logs
        for log_data in sample_logs_data:
            test_db.log_email(**log_data)
        
        # Get first page
        response = demo_user_session.get('/api/logs?page=1&per_page=10')
        data = json.loads(response.data)
        
        assert len(data['logs']) == 10
        assert data['pagination']['page'] == 1
        assert data['pagination']['total_pages'] >= 3
    
    def test_get_logs_with_date_filter(self, demo_user_session, test_db):
        """Test filtering logs by date range."""
        base_date = datetime.now()
        
        # Create old and recent logs
        test_db.log_email(
            sender="old@example.com",
            subject="Old Email",
            status="RESPONDED",
            agent_email="demo@example.com",
            email_timestamp=(base_date - timedelta(days=10)).isoformat()
        )
        test_db.log_email(
            sender="recent@example.com",
            subject="Recent Email",
            status="RESPONDED",
            agent_email="demo@example.com",
            email_timestamp=(base_date - timedelta(days=2)).isoformat()
        )
        
        # Filter to get only recent logs
        start_date = (base_date - timedelta(days=5)).strftime('%Y-%m-%d')
        response = demo_user_session.get(f'/api/logs?start_date={start_date}')
        data = json.loads(response.data)
        
        assert len(data['logs']) == 1
        assert data['logs'][0]['sender'] == "recent@example.com"
    
    def test_get_logs_exclude_ignored(self, demo_user_session, test_db):
        """Test excluding ignored emails from logs."""
        test_db.log_email(
            sender="1@ex.com",
            subject="1",
            status="RESPONDED",
            agent_email="demo@example.com"
        )
        test_db.log_email(
            sender="2@ex.com",
            subject="2",
            status="IGNORED",
            agent_email="demo@example.com"
        )
        
        response = demo_user_session.get('/api/logs?exclude_ignored=true')
        data = json.loads(response.data)
        
        assert len(data['logs']) == 1
        assert data['logs'][0]['status'] == 'RESPONDED'
    
    def test_get_logs_user_isolation(self, client, test_db):
        """Test that users only see their own logs."""
        # Create logs for two different users
        test_db.log_email(
            sender="test1@example.com",
            subject="User 1 Email",
            status="RESPONDED",
            agent_email="user1@example.com"
        )
        test_db.log_email(
            sender="test2@example.com",
            subject="User  2 Email",
            status="RESPONDED",
            agent_email="user2@example.com"
        )
        
        # Login as user1
        with client.session_transaction() as sess:
            sess['user_email'] = 'user1@example.com'
            sess['authenticated'] = True
        
        response = client.get('/api/logs')
        data = json.loads(response.data)
        
        # Should only see user1's logs
        assert len(data['logs']) == 1
        assert data['logs'][0]['sender'] == "test1@example.com"


class TestEmailVolumeMetrics:
    """Test /api/metrics/email-volume endpoint."""
    
    def test_get_email_volume_default(self, demo_user_session, test_db):
        """Test email volume with default parameters (last 7 days)."""
        base_date = datetime.now()
        
        # Create logs for the last 7 days
        for i in range(7):
            test_db.log_email(
                sender=f"user{i}@example.com",
                subject=f"Email {i}",
                status="RESPONDED",
                agent_email="demo@example.com",
                email_timestamp=(base_date - timedelta(days=i)).isoformat()
            )
        
        response = demo_user_session.get('/api/metrics/email-volume')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert 'labels' in data
        assert 'total' in data
        assert 'responded' in data
        assert len(data['labels']) >= 1
    
    def test_get_email_volume_with_date_range(self, demo_user_session, test_db):
        """Test email volume with custom date range."""
        base_date = datetime.now()
        start_date = (base_date - timedelta(days=30)).strftime('%Y-%m-%d')
        end_date = base_date.strftime('%Y-%m-%d')
        
        # Create some logs
        for i in range(10):
            test_db.log_email(
                sender=f"user{i}@example.com",
                subject=f"Email {i}",
                status="RESPONDED",
                agent_email="demo@example.com",
                email_timestamp=(base_date - timedelta(days=i)).isoformat()
            )
        
        response = demo_user_session.get(
            f'/api/metrics/email-volume?start_date={start_date}&end_date={end_date}&interval=day'
        )
        
        data = json.loads(response.data)
        assert response.status_code == 200
        assert len(data['labels']) >= 1
    
    def test_get_email_volume_weekly_interval(self, demo_user_session, test_db):
        """Test email volume with weekly interval."""
        base_date = datetime.now()
        start_date = (base_date - timedelta(days=90)).strftime('%Y-%m-%d')
        end_date = base_date.strftime('%Y-%m-%d')
        
        # Create logs spread over 90 days
        for i in range(30):
            test_db.log_email(
                sender=f"user{i}@example.com",
                subject=f"Email {i}",
                status="RESPONDED",
                agent_email="demo@example.com",
                email_timestamp=(base_date - timedelta(days=i * 3)).isoformat()
            )
        
        response = demo_user_session.get(
            f'/api/metrics/email-volume?start_date={start_date}&end_date={end_date}&interval=week'
        )
        
        data = json.loads(response.data)
        assert response.status_code == 200
    
    def test_get_email_volume_monthly_interval(self, demo_user_session, test_db):
        """Test email volume with monthly interval."""
        base_date = datetime.now()
        start_date = (base_date - timedelta(days=365)).strftime('%Y-%m-%d')
        end_date = base_date.strftime('%Y-%m-%d')
        
        response = demo_user_session.get(
            f'/api/metrics/email-volume?start_date={start_date}&end_date={end_date}&interval=month'
        )
        
        data = json.loads(response.data)
        assert response.status_code == 200
    
    def test_get_email_volume_invalid_date_format(self, demo_user_session):
        """Test email volume with invalid date format."""
        response = demo_user_session.get(
            '/api/metrics/email-volume?start_date=invalid&end_date=2024-01-01'
        )
        
        assert response.status_code == 400


class TestCategoryMetrics:
    """Test /api/metrics/categories endpoint."""
    
    def test_get_category_breakdown(self, demo_user_session, test_db):
        """Test category breakdown retrieval."""
        categories = ['Support', 'Sales', 'General', 'Support', 'Support']
        
        for i, category in enumerate(categories):
            test_db.log_email(
                sender=f"user{i}@example.com",
                subject=f"Email {i}",
                status="RESPONDED",
                category=category,
                agent_email="demo@example.com"
            )
        
        response = demo_user_session.get('/api/metrics/categories')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert 'labels' in data
        assert 'values' in data
        assert len(data['labels']) > 0
        
        # Support should have the highest count
        support_index = data['labels'].index('Support')
        assert data['values'][support_index] == 3
    
    def test_get_category_breakdown_user_isolation(self, client, test_db):
        """Test that category breakdown respects user isolation."""
        # Create categories for different users
        test_db.log_email(
            sender="1@ex.com",
            subject="1",
            status="RESPONDED",
            category="Support",
            agent_email="user1@example.com"
        )
        test_db.log_email(
            sender="2@ex.com",
            subject="2",
            status="RESPONDED",
            category="Sales",
            agent_email="user2@example.com"
        )
        
        # Login as user1
        with client.session_transaction() as sess:
            sess['user_email'] = 'user1@example.com'
            sess['authenticated'] = True
        
        response = client.get('/api/metrics/categories')
        data = json.loads(response.data)
        
        # Should only see Support category
        assert len(data['labels']) == 1
        assert data['labels'][0] == 'Support'


class TestCacheHeaders:
    """Test cache control headers on API responses."""
    
    def test_logs_has_no_cache_headers(self, demo_user_session):
        """Test that logs endpoint has no-cache headers in development."""
        response = demo_user_session.get('/api/logs')
        
        assert 'Cache-Control' in response.headers
        assert 'no-cache' in response.headers['Cache-Control']
    
    def test_metrics_has_no_cache_headers(self, demo_user_session):
        """Test that metrics endpoints have no-cache headers."""
        endpoints = [
            '/api/metrics/email-volume',
            '/api/metrics/categories'
        ]
        
        for endpoint in endpoints:
            response = demo_user_session.get(endpoint)
            assert 'Cache-Control' in response.headers


class TestErrorHandling:
    """Test error handling in API routes."""
    
    def test_invalid_endpoint_returns_404(self, demo_user_session):
        """Test that invalid endpoints return 404."""
        response = demo_user_session.get('/api/invalid-endpoint')
        assert response.status_code == 404
    
    def test_database_error_returns_500(self, demo_user_session, mocker):
        """Test that database errors return 500."""
        # Mock database service to raise an exception
        mocker.patch(
            'app.services.database_service.DatabaseService.get_logs',
            side_effect=Exception("Database error")
        )
        
        response = demo_user_session.get('/api/logs')
        assert response.status_code == 500
        
        data = json.loads(response.data)
        assert 'error' in data
