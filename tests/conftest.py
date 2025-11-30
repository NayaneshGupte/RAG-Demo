# Pytest configuration and shared fixtures

import pytest
import os
import tempfile
from datetime import datetime, timedelta
from app import create_app
from app.services.database_service import DatabaseService


@pytest.fixture
def app():
    """Create and configure a new app instance for each test."""
    # Use a temporary database for testing
    db_fd, db_path = tempfile.mkstemp()
    
    app = create_app()
    app.config.update({
        "TESTING": True,
        "DATABASE": db_path,
        "SECRET_KEY": "test-secret-key",
        "WTF_CSRF_ENABLED": False
    })

    yield app

    # Cleanup
    os.close(db_fd)
    os.unlink(db_path)


@pytest.fixture
def client(app):
    """A test client for the app."""
    return app.test_client()


@pytest.fixture
def runner(app):
    """A test runner for the app's Click commands."""
    return app.test_cli_runner()


@pytest.fixture
def test_db():
    """Create a temporary test database."""
    db_fd, db_path = tempfile.mkstemp()
    db = DatabaseService(db_path)
    
    yield db
    
    # Cleanup
    os.close(db_fd)
    os.unlink(db_path)


@pytest.fixture
def sample_email_data():
    """Sample email data for testing."""
    return {
        "sender": "test@example.com",
        "subject": "Test Email",
        "status": "RESPONDED",
        "details": "Test response generated",
        "category": "Support",
        "agent_email": "demo@example.com",
        "email_timestamp": datetime.now().isoformat()
    }


@pytest.fixture
def demo_user_session(client):
    """Create a demo user session."""
    with client.session_transaction() as sess:
        sess['user_email'] = 'demo@example.com'
        sess['is_demo'] = True
        sess['authenticated'] = True
    return client


@pytest.fixture
def sample_logs_data():
    """Generate sample log entries for testing."""
    base_date = datetime.now()
    logs = []
    
    statuses = ['RESPONDED', 'IGNORED', 'ERROR']
    categories = ['Support', 'Sales', 'General', 'Billing']
    
    for i in range(30):
        email_timestamp = base_date - timedelta(days=i // 3, hours=i % 24)
        logs.append({
            "sender": f"user{i}@example.com",
            "subject": f"Test Email {i}",
            "status": statuses[i % len(statuses)],
            "details": f"Test details {i}",
            "category": categories[i % len(categories)],
            "agent_email": "demo@example.com",
            "email_timestamp": email_timestamp.isoformat()
        })
    
    return logs


@pytest.fixture
def mock_gmail_service(mocker):
    """Mock Gmail service for testing."""
    mock = mocker.Mock()
    mock.get_current_email.return_value = "test@example.com"
    mock.fetch_unread_emails.return_value = []
    return mock


@pytest.fixture
def mock_ai_service(mocker):
    """Mock AI service for testing."""
    mock = mocker.Mock()
    mock.generate_response.return_value = "Test AI response"
    mock.classify_email.return_value = {"category": "Support", "should_respond": True}
    return mock
