"""
Database service for logging email processing activities.
"""
import sqlite3
import logging
from datetime import datetime
import os

logger = logging.getLogger(__name__)

class DatabaseService:
    """Service for managing SQLite database operations."""
    
    def __init__(self, db_path="email_logs.db"):
        self.db_path = db_path
        self._init_db()
    
    def _get_connection(self):
        """Get database connection."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def _init_db(self):
        """Initialize database schema."""
        try:
            with self._get_connection() as conn:
                # Create table if not exists
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS email_logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                        sender TEXT,
                        subject TEXT,
                        status TEXT,
                        details TEXT,
                        category TEXT,
                        agent_email TEXT
                    )
                """)
                
                # Check if agent_email column exists (migration for existing db)
                cursor = conn.execute("PRAGMA table_info(email_logs)")
                columns = [info[1] for info in cursor.fetchall()]
                if 'agent_email' not in columns:
                    logger.info("Migrating database: Adding agent_email column")
                    conn.execute("ALTER TABLE email_logs ADD COLUMN agent_email TEXT")

                if 'email_timestamp' not in columns:
                    logger.info("Migrating database: Adding email_timestamp column")
                    conn.execute("ALTER TABLE email_logs ADD COLUMN email_timestamp DATETIME")
                
                conn.commit()
        except Exception as e:
            logger.error(f"Database initialization error: {e}")

    def log_email(self, sender, subject, status, details="", category="Unknown", agent_email=None, email_timestamp=None):
        """Log an email processing event."""
        try:
            with self._get_connection() as conn:
                conn.execute("""
                    INSERT INTO email_logs (sender, subject, status, details, category, agent_email, email_timestamp, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (sender, subject, status, details, category, agent_email, email_timestamp, datetime.now()))
                conn.commit()
            logger.info(f"Logged email event: {subject} - {status}")
        except Exception as e:
            logger.error(f"Error logging to database: {e}")

    def get_logs(self, limit=50, exclude_ignored=False, agent_email=None):
        """Get recent logs."""
        try:
            with self._get_connection() as conn:
                query = "SELECT * FROM email_logs WHERE 1=1"
                params = []
                
                if exclude_ignored:
                    query += " AND status != 'IGNORED'"
                
                if agent_email:
                    query += " AND (agent_email = ? OR agent_email IS NULL)"
                    params.append(agent_email)
                
                query += " ORDER BY timestamp DESC LIMIT ?"
                params.append(limit)
                
                cursor = conn.execute(query, tuple(params))
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error fetching logs: {e}")
            return []

    def get_stats(self, agent_email=None):
        """Get basic statistics."""
        try:
            with self._get_connection() as conn:
                where_clause = ""
                params = []
                if agent_email:
                    where_clause = " WHERE (agent_email = ? OR agent_email IS NULL)"
                    params.append(agent_email)

                total = conn.execute(f"SELECT COUNT(*) FROM email_logs{where_clause}", tuple(params)).fetchone()[0]
                
                resp_where = where_clause + (" AND" if where_clause else " WHERE") + " status='RESPONDED'"
                responded = conn.execute(f"SELECT COUNT(*) FROM email_logs{resp_where}", tuple(params)).fetchone()[0]
                
                ign_where = where_clause + (" AND" if where_clause else " WHERE") + " status='IGNORED'"
                ignored = conn.execute(f"SELECT COUNT(*) FROM email_logs{ign_where}", tuple(params)).fetchone()[0]
                
                return {
                    "total": total,
                    "responded": responded,
                    "ignored": ignored
                }
        except Exception as e:
            logger.error(f"Error fetching stats: {e}")
            return {"total": 0, "responded": 0, "ignored": 0}
