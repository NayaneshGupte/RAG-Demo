"""Test script to verify chart query logic and database content."""
import sqlite3
from datetime import datetime, timedelta

# Connect to database
conn = sqlite3.connect('email_logs.db')
conn.row_factory = sqlite3.Row

print("=== DATABASE CONTENT CHECK ===\n")

# Check date range in database
print("1. Date Range in Database:")
cursor = conn.execute("""
    SELECT 
        MIN(DATE(COALESCE(email_timestamp, timestamp))) as earliest,
        MAX(DATE(COALESCE(email_timestamp, timestamp))) as latest,
        COUNT(*) as total
    FROM email_logs 
    WHERE agent_email = 'demo@example.com'
""")
result = cursor.fetchone()
print(f"   Earliest: {result['earliest']}")
print(f"   Latest: {result['latest']}")
print(f"   Total emails: {result['total']}")

print("\n2. Sample of dates (first 10 emails):")
cursor = conn.execute("""
    SELECT 
        id,
        DATE(COALESCE(email_timestamp, timestamp)) as date,
        email_timestamp,
        timestamp
    FROM email_logs 
    WHERE agent_email = 'demo@example.com'
    ORDER BY COALESCE(email_timestamp, timestamp) ASC
    LIMIT 10
""")
for row in cursor.fetchall():
    print(f"   ID {row['id']}: date={row['date']}, email_ts={row['email_timestamp']}, ts={row['timestamp']}")

print("\n=== SIMULATING 1-MONTH QUERY ===\n")

# Simulate what the API would do for "Last 1 Month"
end = datetime.now()
start = datetime.now() - timedelta(days=30)
start_date = start.date().isoformat()
interval = 'day'

print(f"3. Query Parameters:")
print(f"   Start Date: {start_date}")
print(f"   End Date: {end.date().isoformat()}")
print(f"   Interval: {interval}")

# Build the exact query that DatabaseService would generate
ts_col = "COALESCE(email_timestamp, timestamp)"
date_col = f"DATE({ts_col})"

query = f"""
    SELECT 
        {date_col} as date,
        COUNT(*) as total,
        SUM(CASE WHEN status='RESPONDED' THEN 1 ELSE 0 END) as responded,
        SUM(CASE WHEN status='IGNORED' THEN 1 ELSE 0 END) as ignored,
        SUM(CASE WHEN status='ERROR' THEN 1 ELSE 0 END) as failed
    FROM email_logs
    WHERE {date_col} >= ? AND (agent_email = ? OR agent_email IS NULL)
    GROUP BY {date_col}
    ORDER BY date ASC
"""

print(f"\n4. Executed Query:")
print(query)
print(f"   Params: ('{start_date}', 'demo@example.com')")

cursor = conn.execute(query, (start_date, 'demo@example.com'))
results = cursor.fetchall()

print(f"\n5. Query Results ({len(results)} rows):")
if len(results) == 0:
    print("   NO RESULTS - This explains why chart is blank!")
else:
    for i, row in enumerate(results[:5]):  # Show first 5
        print(f"   {row['date']}: total={row['total']}, responded={row['responded']}, ignored={row['ignored']}, failed={row['failed']}")
    if len(results) > 5:
        print(f"   ... and {len(results) - 5} more rows")

conn.close()

print("\n=== DIAGNOSIS ===")
if len(results) == 0:
    print("❌ NO DATA MATCHES THE QUERY")
    print("   This means all demo data has dates BEFORE the start_date filter.")
    print(f"   The query filters for dates >= {start_date}")
    print("   But the seed script is creating dates in the PAST (days_ago).")
    print("   These backdated timestamps are likely older than 30 days ago!")
elif len(results) == 1:
    print("❌ ONLY ONE DATE IN RESULTS")
    print("   All data is grouped to a single date.")
    print("   Check if email_timestamp is being set correctly during seeding.")
else:
    print("✅ MULTIPLE DATES FOUND")
    print(f"   Query returned {len(results)} different dates, which should plot correctly.")
