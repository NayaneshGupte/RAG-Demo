import sqlite3
import os

def inspect_db():
    db_path = 'email_logs.db'
    if not os.path.exists(db_path):
        print("Database not found")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("--- Schema ---")
    cursor.execute("PRAGMA table_info(email_logs)")
    for col in cursor.fetchall():
        print(col)
        
    print("\n--- Sample Data (Limit 5) ---")
    cursor.execute("SELECT id, email_timestamp, timestamp FROM email_logs LIMIT 5")
    for row in cursor.fetchall():
        print(row)
        
    print("\n--- Count of NULL email_timestamp ---")
    cursor.execute("SELECT COUNT(*) FROM email_logs WHERE email_timestamp IS NULL")
    print(cursor.fetchone()[0])

    print("\n--- Count of non-NULL email_timestamp ---")
    cursor.execute("SELECT COUNT(*) FROM email_logs WHERE email_timestamp IS NOT NULL")
    print(cursor.fetchone()[0])
    
    conn.close()

if __name__ == "__main__":
    inspect_db()
