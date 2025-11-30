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

    def get_logs(self, limit=100, exclude_ignored=False, agent_email=None, start_date=None, end_date=None):
        """Retrieve recent email logs with optional date filtering."""
        try:
            with self._get_connection() as conn:
                where_clauses = []
                params = []
                
                # Filter by agent_email
                if agent_email:
                    where_clauses.append("(agent_email = ? OR agent_email IS NULL)")
                    params.append(agent_email)
                
                # Filter by date range (using email_timestamp if available, else timestamp)
                if start_date:
                    where_clauses.append("DATE(COALESCE(email_timestamp, timestamp)) >= ?")
                    params.append(start_date)
                
                if end_date:
                    where_clauses.append("DATE(COALESCE(email_timestamp, timestamp)) <= ?")
                    params.append(end_date)
                
                # Exclude ignored emails
                if exclude_ignored:
                    where_clauses.append("status != 'IGNORED'")
                
                where_clause = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""
               
                params.append(limit)
                
                cursor = conn.execute(f"""
                    SELECT * FROM email_logs
                    {where_clause}
                    ORDER BY timestamp DESC
                    LIMIT ?
                """, tuple(params))
                
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error retrieving logs: {e}")
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
    
    def get_email_volume_by_day(self, days=7, start_date=None, interval='day', agent_email=None):
        """
        Get email volume grouped by day or month for the specified date range.
        interval: 'day' or 'month'
        """
        try:
            with self._get_connection() as conn:
                # Determine date format and grouping based on interval
                # Use email_timestamp if available (for backdated/demo data), otherwise timestamp
                ts_col = "COALESCE(email_timestamp, timestamp)"
                
                if interval == 'month':
                    date_format = '%Y-%m'
                    date_col = f"strftime('%Y-%m', {ts_col})"
                elif interval == 'week':
                    # Group by year and week number
                    date_format = '%Y-W%W'
                    date_col = f"strftime('%Y-W%W', {ts_col})"
                else:
                    date_format = '%Y-%m-%d'
                    date_col = f"DATE({ts_col})"

                where_clause = ""
                params = []

                if start_date:
                    where_clause = f"WHERE {date_col} >= ?"
                    params.append(start_date)
                else:
                    where_clause = f"WHERE {ts_col} >= DATE('now', '-' || ? || ' days')"
                    params.append(days)
                
                # Add agent_email filter
                if agent_email:
                    where_clause += " AND (agent_email = ? OR agent_email IS NULL)"
                    params.append(agent_email)

                query = f"""
                    SELECT 
                        {date_col} as date,
                        COUNT(*) as total,
                        SUM(CASE WHEN status='RESPONDED' THEN 1 ELSE 0 END) as responded,
                        SUM(CASE WHEN status='IGNORED' THEN 1 ELSE 0 END) as ignored,
                        SUM(CASE WHEN status='ERROR' THEN 1 ELSE 0 END) as failed
                    FROM email_logs
                    {where_clause}
                    GROUP BY {date_col}
                    ORDER BY date ASC
                """
                
                print(f"DEBUG: Executing query: {query}")
                print(f"DEBUG: Params: {params}")
                logger.info(f"Executing query: {query} with params: {params}")
                cursor = conn.execute(query, tuple(params))
                
                results = [dict(row) for row in cursor.fetchall()]
                print(f"DEBUG: Query returned {len(results)} rows")
                if len(results) > 0:
                    print(f"DEBUG: First row: {results[0]}")
                    print(f"DEBUG: Last row: {results[-1]}")
                
                logger.info(f"Query returned {len(results)} rows")
                return results
        except Exception as e:
            logger.error(f"Error fetching email volume data: {e}")
            return []
    
    def get_category_breakdown(self, agent_email=None):
        """Get count of emails by category."""
        try:
            with self._get_connection() as conn:
                where_clause = "WHERE category IS NOT NULL AND category != '' AND category != 'Unknown'"
                params = []
                
                if agent_email:
                    where_clause += " AND (agent_email = ? OR agent_email IS NULL)"
                    params.append(agent_email)

                query = f"""
                    SELECT 
                        category,
                        COUNT(*) as count
                    FROM email_logs
                    {where_clause}
                    GROUP BY category
                    ORDER BY count DESC
                    LIMIT 10
                """
                print(f"DEBUG: Category Query: {query}")
                print(f"DEBUG: Category Params: {params}")
                cursor = conn.execute(query, tuple(params))
                results = [dict(row) for row in cursor.fetchall()]
                print(f"DEBUG: Category Results: {len(results)}")
                return results
        except Exception as e:
            logger.error(f"Error fetching category breakdown: {e}")
            return []
