"""
Unit tests for DatabaseService

Tests cover:
- Database initialization
- Logging email events
- Retrieving logs with filters
- Statistics generation
- Date range filtering
- User isolation
- Email volume aggregation by day/week/month
- Category breakdown
"""

import pytest
from datetime import datetime, timedelta
from app.services.database_service import DatabaseService


class TestDatabaseInitialization:
    """Test database initialization and schema creation."""
    
    def test_db_creates_table(self, test_db):
        """Test that database creates email_logs table."""
        with test_db._get_connection() as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='email_logs'"
            )
            assert cursor.fetchone() is not None
    
    def test_db_has_required_columns(self, test_db):
        """Test that table has all required columns."""
        with test_db._get_connection() as conn:
            cursor = conn.execute("PRAGMA table_info(email_logs)")
            columns = {row[1] for row in cursor.fetchall()}
            
            required_columns = {
                'id', 'timestamp', 'sender', 'subject', 'status',
                'details', 'category', 'agent_email', 'email_timestamp'
            }
            assert required_columns.issubset(columns)


class TestEmailLogging:
    """Test logging email events."""
    
    def test_log_email_basic(self, test_db, sample_email_data):
        """Test logging a basic email event."""
        test_db.log_email(**sample_email_data)
        
        logs = test_db.get_logs(limit=1)
        assert len(logs) == 1
        assert logs[0]['sender'] == sample_email_data['sender']
        assert logs[0]['subject'] == sample_email_data['subject']
        assert logs[0]['status'] == sample_email_data['status']
    
    def test_log_email_without_optional_fields(self, test_db):
        """Test logging email with only required fields."""
        test_db.log_email(
            sender="test@example.com",
            subject="Test",
            status="RESPONDED"
        )
        
        logs = test_db.get_logs(limit=1)
        assert len(logs) == 1
        assert logs[0]['category'] == 'Unknown'
    
    def test_log_multiple_emails(self, test_db, sample_logs_data):
        """Test logging multiple emails."""
        for log_data in sample_logs_data:
            test_db.log_email(**log_data)
        
        logs = test_db.get_logs(limit=100)
        assert len(logs) == len(sample_logs_data)


class TestRetrievingLogs:
    """Test retrieving and filtering logs."""
    
    def test_get_logs_with_limit(self, test_db, sample_logs_data):
        """Test that log retrieval respects limit parameter."""
        for log_data in sample_logs_data:
            test_db.log_email(**log_data)
        
        logs = test_db.get_logs(limit=10)
        assert len(logs) == 10
    
    def test_get_logs_ordered_by_timestamp_desc(self, test_db, sample_logs_data):
        """Test that logs are returned in descending order by timestamp."""
        for log_data in sample_logs_data:
            test_db.log_email(**log_data)
        
        logs = test_db.get_logs(limit=5)
        timestamps = [log['timestamp'] for log in logs]
        assert timestamps == sorted(timestamps, reverse=True)
    
    def test_get_logs_exclude_ignored(self, test_db, sample_logs_data):
        """Test filtering out ignored emails."""
        for log_data in sample_logs_data:
            test_db.log_email(**log_data)
        
        logs = test_db.get_logs(limit=100, exclude_ignored=True)
        assert all(log['status'] != 'IGNORED' for log in logs)
    
    def test_get_logs_by_agent_email(self, test_db):
        """Test user isolation by agent_email."""
        # Create logs for different users
        test_db.log_email(
            sender="test1@example.com",
            subject="Test 1",
            status="RESPONDED",
            agent_email="user1@example.com"
        )
        test_db.log_email(
            sender="test2@example.com",
            subject="Test 2",
            status="RESPONDED",
            agent_email="user2@example.com"
        )
        
        # Get logs for user1
        user1_logs = test_db.get_logs(limit=100, agent_email="user1@example.com")
        assert len(user1_logs) == 1
        assert user1_logs[0]['sender'] == "test1@example.com"
    
    def test_get_logs_empty_database(self, test_db):
        """Test retrieving logs from empty database."""
        logs = test_db.get_logs(limit=10)
        assert len(logs) == 0


class TestDateRangeFiltering:
    """Test date range filtering for logs."""
    
    def test_get_logs_with_start_date(self, test_db):
        """Test filtering logs by start date."""
        base_date = datetime.now()
        
        # Create logs with different dates
        test_db.log_email(
            sender="old@example.com",
            subject="Old",
            status="RESPONDED",
            email_timestamp=(base_date - timedelta(days=10)).isoformat()
        )
        test_db.log_email(
            sender="recent@example.com",
            subject="Recent",
            status="RESPONDED",
            email_timestamp=(base_date - timedelta(days=2)).isoformat()
        )
        
        # Filter by start date
        start_date = (base_date - timedelta(days=5)).strftime('%Y-%m-%d')
        logs = test_db.get_logs(limit=100, start_date=start_date)
        
        assert len(logs) == 1
        assert logs[0]['sender'] == "recent@example.com"
    
    def test_get_logs_with_date_range(self, test_db):
        """Test filtering logs with both start and end dates."""
        base_date = datetime.now()
        
        # Create logs spanning multiple days
        for i in range(10):
            test_db.log_email(
                sender=f"user{i}@example.com",
                subject=f"Email {i}",
                status="RESPONDED",
                email_timestamp=(base_date - timedelta(days=i)).isoformat()
            )
        
        # Filter to get emails from days 3-6
        start_date = (base_date - timedelta(days=6)).strftime('%Y-%m-%d')
        end_date = (base_date - timedelta(days=3)).strftime('%Y-%m-%d')
        
        logs = test_db.get_logs(limit=100, start_date=start_date, end_date=end_date)
        assert len(logs) == 4


class TestStatistics:
    """Test statistics generation."""
    
    def test_get_stats_basic(self, test_db):
        """Test basic statistics calculation."""
        # Create logs with different statuses
        test_db.log_email(sender="1@ex.com", subject="1", status="RESPONDED")
        test_db.log_email(sender="2@ex.com", subject="2", status="RESPONDED")
        test_db.log_email(sender="3@ex.com", subject="3", status="IGNORED")
        test_db.log_email(sender="4@ex.com", subject="4", status="ERROR")
        
        stats = test_db.get_stats()
        
        assert stats['total'] == 4
        assert stats['responded'] == 2
        assert stats['ignored'] == 1
    
    def test_get_stats_empty_database(self, test_db):
        """Test statistics for empty database."""
        stats = test_db.get_stats()
        
        assert stats['total'] == 0
        assert stats['responded'] == 0
        assert stats['ignored'] == 0
    
    def test_get_stats_with_agent_email_filter(self, test_db):
        """Test statistics filtering by agent_email."""
        test_db.log_email(
            sender="1@ex.com",
            subject="1",
            status="RESPONDED",
            agent_email="user1@example.com"
        )
        test_db.log_email(
            sender="2@ex.com",
            subject="2",
            status="RESPONDED",
            agent_email="user2@example.com"
        )
        
        stats = test_db.get_stats(agent_email="user1@example.com")
        assert stats['total'] == 1


class TestEmailVolumeAggregation:
    """Test email volume aggregation by different time intervals."""
    
    def test_get_email_volume_by_day(self, test_db):
        """Test daily email volume aggregation."""
        base_date = datetime.now()
        
        # Create multiple emails on same day
        for i in range(3):
            test_db.log_email(
                sender=f"user{i}@example.com",
                subject=f"Email {i}",
                status="RESPONDED" if i < 2 else "IGNORED",
                email_timestamp=(base_date - timedelta(hours=i)).isoformat()
            )
        
        volume_data = test_db.get_email_volume_by_day(
            days=1,
            start_date=base_date.strftime('%Y-%m-%d'),
            interval='day'
        )
        
        assert len(volume_data) >= 1
        assert volume_data[0]['total'] == 3
        assert volume_data[0]['responded'] == 2
        assert volume_data[0]['ignored'] == 1
    
    def test_get_email_volume_by_week(self, test_db):
        """Test weekly email volume aggregation."""
        base_date = datetime.now()
        
        # Create emails over multiple days
        for i in range(10):
            test_db.log_email(
                sender=f"user{i}@example.com",
                subject=f"Email {i}",
                status="RESPONDED",
                email_timestamp=(base_date - timedelta(days=i)).isoformat()
            )
        
        volume_data = test_db.get_email_volume_by_day(
            days=30,
            start_date=(base_date - timedelta(days=30)).strftime('%Y-%m-%d'),
            interval='week'
        )
        
        assert len(volume_data) >= 1
    
    def test_get_email_volume_by_month(self, test_db):
        """Test monthly email volume aggregation."""
        base_date = datetime.now()
        
        # Create emails over multiple months
        for i in range(60):
            test_db.log_email(
                sender=f"user{i}@example.com",
                subject=f"Email {i}",
                status="RESPONDED",
                email_timestamp=(base_date - timedelta(days=i)).isoformat()
            )
        
        volume_data = test_db.get_email_volume_by_day(
            days=365,
            start_date=(base_date - timedelta(days=365)).strftime('%Y-%m-%d'),
            interval='month'
        )
        
        assert len(volume_data) >= 1


class TestCategoryBreakdown:
    """Test category breakdown functionality."""
    
    def test_get_category_breakdown(self, test_db):
        """Test category breakdown retrieval."""
        categories = ['Support', 'Sales', 'Support', 'General', 'Support']
        
        for i, category in enumerate(categories):
            test_db.log_email(
                sender=f"user{i}@example.com",
                subject=f"Email {i}",
                status="RESPONDED",
                category=category
            )
        
        breakdown = test_db.get_category_breakdown()
        
        # Support should be the top category with 3 entries
        assert len(breakdown) > 0
        assert breakdown[0]['category'] == 'Support'
        assert breakdown[0]['count'] == 3
    
    def test_get_category_breakdown_excludes_unknown(self, test_db):
        """Test that Unknown categories are excluded."""
        test_db.log_email(
            sender="1@ex.com",
            subject="1",
            status="RESPONDED",
            category="Unknown"
        )
        test_db.log_email(
            sender="2@ex.com",
            subject="2",
            status="RESPONDED",
            category="Support"
        )
        
        breakdown = test_db.get_category_breakdown()
        
        # Should only return Support, not Unknown
        assert len(breakdown) == 1
        assert breakdown[0]['category'] == 'Support'
    
    def test_get_category_breakdown_with_agent_filter(self, test_db):
        """Test category breakdown with agent_email filtering."""
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
        
        breakdown = test_db.get_category_breakdown(agent_email="user1@example.com")
        
        assert len(breakdown) == 1
        assert breakdown[0]['category'] == 'Support'
