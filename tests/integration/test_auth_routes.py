"""
Integration tests for authentication routes

Tests cover:
- Demo mode login/logout
- Session management
- Data isolation
- Auto-reseed functionality
- OAuth flow (mocked)
"""

import pytest
import json
from datetime import datetime


class TestDemoModeLogin:
    """Test demo mode authentication."""
    
    def test_demo_login_creates_session(self, client):
        """Test that demo login creates a valid session."""
        response = client.get('/auth/demo/login', follow_redirects=False)
        
        assert response.status_code == 302  # Redirect
        assert response.location == '/'
        
        # Check session
        with client.session_transaction() as sess:
            assert sess.get('user_email') == 'demo@example.com'
            assert sess.get('is_demo') is True
            assert sess.get('authenticated') is True
    
    def test_demo_login_clears_old_data(self, client, test_db):
        """Test that demo login clears old demo data."""
        # Create some old demo data
        test_db.log_email(
            sender="old@example.com",
            subject="Old Email",
            status="RESPONDED",
            agent_email="demo@example.com"
        )
        
        # Demo login
        response = client.get('/auth/demo/login')
        
        # Check that old data was cleared
        logs = test_db.get_logs(limit=100, agent_email="demo@example.com")
        # After reseeding, there should be fresh data, not the old email
        assert not any(log['sender'] == "old@example.com" for log in logs)
    
    def test_demo_login_reseeds_data(self, client, test_db):
        """Test that demo login seeds fresh data."""
        response = client.get('/auth/demo/login')
        
        # Check that demo data was seeded
        logs = test_db.get_logs(limit=100, agent_email="demo@example.com")
        assert len(logs) > 0
    
    def test_demo_login_sets_cache_headers(self, client):
        """Test that demo login response has no-cache headers."""
        response = client.get('/auth/demo/login', follow_redirects=False)
        
        assert 'Cache-Control' in response.headers
        assert 'no-cache' in response.headers['Cache-Control']


class TestDemoModeLogout:
    """Test demo mode logout."""
    
    def test_demo_logout_clears_session(self, client):
        """Test that logout clears the session."""
        # First login
        client.get('/auth/demo/login')
        
        # Then logout
        response = client.get('/auth/logout', follow_redirects=False)
        
        assert response.status_code == 302
        
        # Check session is cleared
        with client.session_transaction() as sess:
            assert sess.get('user_email') is None
            assert sess.get('is_demo') is None
            assert sess.get('authenticated') is None
    
    def test_logout_redirects_to_home(self, client):
        """Test that logout redirects to home page."""
        response = client.get('/auth/logout', follow_redirects=False)
        assert response.location == '/'


class TestSessionManagement:
    """Test session persistence and validation."""
    
    def test_session_persists_across_requests(self, client):
        """Test that session data persists across multiple requests."""
        # Login
        client.get('/auth/demo/login')
        
        # Make another request
        with client.session_transaction() as sess:
            assert sess.get('user_email') == 'demo@example.com'
        
        # Session should still be valid
        response = client.get('/api/logs')
        assert response.status_code == 200
    
    def test_unauthenticated_request_fails(self, client):
        """Test that unauthenticated requests are rejected."""
        response = client.get('/api/logs')
        assert response.status_code == 401


class TestUserDataIsolation:
    """Test that users can only access their own data."""
    
    def test_different_users_see_different_data(self, client, test_db):
        """Test data isolation between users."""
        # Create data for two users
        test_db.log_email(
            sender="test1@example.com",
            subject="User 1 Email",
            status="RESPONDED",
            agent_email="user1@example.com"
        )
        test_db.log_email(
            sender="test2@example.com",
            subject="User 2 Email",
            status="RESPONDED",
            agent_email="user2@example.com"
        )
        
        # Login as user1
        with client.session_transaction() as sess:
            sess['user_email'] = 'user1@example.com'
            sess['authenticated'] = True
        
        # Request logs
        response = client.get('/api/logs')
        data = json.loads(response.data)
        
        # Should only see user1's data
        assert len(data['logs']) == 1
        assert data['logs'][0]['sender'] == "test1@example.com"
    
    def test_demo_user_isolation(self, client, test_db):
        """Test that demo user only sees demo data."""
        # Create regular user data
        test_db.log_email(
            sender="regular@example.com",
            subject="Regular Email",
            status="RESPONDED",
            agent_email="regular@example.com"
        )
        
        # Login as demo user
        client.get('/auth/demo/login')
        
        # Request logs
        response = client.get('/api/logs')
        data = json.loads(response.data)
        
        # Should not see regular user's data
        assert not any(log['sender'] == "regular@example.com" for log in data['logs'])


class TestOAuthFlow:
    """Test OAuth authentication flow (mocked)."""
    
    def test_oauth_login_redirects(self, client):
        """Test that OAuth login initiates redirect."""
        response = client.get('/auth/login', follow_redirects=False)
        
        # Should redirect to OAuth provider
        assert response.status_code == 302
        assert 'accounts.google.com' in response.location or response.location == '/auth/demo/login'
    
    @pytest.mark.skip(reason="Requires OAuth configuration")
    def test_oauth_callback_success(self, client, mocker):
        """Test successful OAuth callback (mocked)."""
        # This would require mocking the entire OAuth flow
        # Skipping for now as it requires extensive OAuth setup
        pass
    
    def test_unauthorized_access_returns_401(self, client):
        """Test that unauthorized API access returns 401."""
        response = client.get('/api/logs')
        assert response.status_code == 401
        
        data = json.loads(response.data)
        assert 'error' in data
