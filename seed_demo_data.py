"""
Demo Data Seeding Script
Creates realistic dummy data for demo mode
"""
from app.services.database_service import DatabaseService
from datetime import datetime, timedelta
import random
import json

def seed_demo_data():
    """Seed the database with realistic demo data."""
    db = DatabaseService()
    
    # Demo user email
    demo_email = 'demo@example.com'
    
    print("🌱 Seeding demo data...")
    
    # Generate dates over the past 7 days
    base_date = datetime.now()
    
    # Load data from demo.json
    try:
        with open('demo.json', 'r') as f:
            emails = json.load(f)
    except FileNotFoundError:
        print("❌ Error: demo.json not found. Please run generate_demo_json.py first.")
        return

    print(f"🌱 Seeding {len(emails)} emails from demo.json...")
    
    # Insert all emails
    count = 0
    responded = 0
    ignored = 0
    failed = 0
    
    for email in emails:
        timestamp = base_date - timedelta(days=email['days_ago'], hours=email['hours'])
        email_timestamp = timestamp - timedelta(minutes=random.randint(1, 60))
        
        db.log_email(
            sender=email['sender'],
            subject=email['subject'],
            status=email['status'],
            details=email['details'],
            category=email['category'],
            agent_email=demo_email,
            email_timestamp=email_timestamp.isoformat()
        )
        count += 1
        if email['status'] == 'RESPONDED': responded += 1
        elif email['status'] == 'IGNORED': ignored += 1
        elif email['status'] == 'ERROR': failed += 1
    
    print(f"✅ Successfully seeded {count} demo email entries")
    print(f"   - {responded} RESPONDED")
    print(f"   - {ignored} IGNORED")
    print(f"   - {failed} FAILED")
    print(f"   All tagged with agent_email: {demo_email}")

if __name__ == '__main__':
    seed_demo_data()
