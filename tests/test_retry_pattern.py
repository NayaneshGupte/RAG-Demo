"""
Test script for RabbitMQ retry pattern with simulated 429 errors.

This script helps you test the retry mechanism by:
1. Publishing test emails to the queue
2. Simulating LLM quota errors (429)
3. Observing retry behavior with exponential backoff

Usage:
    python test_retry_pattern.py
"""

import pika
import json
import time
from datetime import datetime


def publish_test_email(priority=5):
    """Publish a test email to emails.to_classify queue."""
    
    connection = pika.BlockingConnection(
        pika.ConnectionParameters(
            host='localhost',
            port=5672,
            credentials=pika.PlainCredentials('admin', 'admin123')
        )
    )
    channel = connection.channel()
    
    # Ensure queue exists
    channel.queue_declare(queue='emails.to_classify', durable=True)
    
    # Test email
    test_email = {
        "message_id": f"test-retry-{int(time.time())}",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "email_id": "test-gmail-id-123",
        "thread_id": "test-thread-456",
        "from": "test@example.com",
        "to": "support@company.com",
        "subject": "Test email for retry pattern",
        "body": "This email will trigger retry logic when LLM returns 429",
        "agent_email": "support@company.com",
        "priority": priority,
        "metadata": {
            "test": True,
            "simulate_429": True
        }
    }
    
    # Publish
    channel.basic_publish(
        exchange='',
        routing_key='emails.to_classify',
        body=json.dumps(test_email),
        properties=pika.BasicProperties(
            delivery_mode=2,  # Persistent
            priority=priority
        )
    )
    
    print(f"✅ Published test email: {test_email['message_id']}")
    print(f"   Priority: {priority}")
    print(f"   Subject: {test_email['subject']}")
    
    connection.close()
    return test_email['message_id']


def check_queue_status():
    """Check status of all queues."""
    
    connection = pika.BlockingConnection(
        pika.ConnectionParameters(
            host='localhost',
            credentials=pika.PlainCredentials('admin', 'admin123')
        )
    )
    channel = connection.channel()
    
    queues = [
        'emails.to_classify',
        'emails.to_respond',
        'dead_letter_queue'
    ]
    
    print("\n📊 Queue Status:")
    print("-" * 50)
    
    for queue_name in queues:
        try:
            # Passive declare just to get queue stats
            method = channel.queue_declare(queue=queue_name, durable=True, passive=True)
            message_count = method.method.message_count
            consumer_count = method.method.consumer_count
            
            print(f"  {queue_name}:")
            print(f"    Messages: {message_count}")
            print(f"    Consumers: {consumer_count}")
        except Exception as e:
            print(f"  {queue_name}: Queue not found or error")
    
    connection.close()


def list_retry_queues():
    """List all dynamic retry queues."""
    import subprocess
    
    try:
        result = subprocess.run(
            ['docker', 'exec', 'rabbitmq-server', 'rabbitmqctl', 'list_queues', 'name', 'messages'],
            capture_output=True,
            text=True
        )
        
        print("\n🔄 Retry Queues:")
        print("-" * 50)
        
        found_retry = False
        for line in result.stdout.split('\n'):
            if 'retry' in line.lower():
                print(f"  {line}")
                found_retry = True
        
        if not found_retry:
            print("  No retry queues found (all emails processed or waiting)")
    
    except Exception as e:
        print(f"  Could not list retry queues: {e}")
        print("  (Docker might not be running or rabbitmqctl not accessible)")


def monitor_queues(duration_seconds=120):
    """
    Monitor queue status over time.
    
    Watch as messages move through retry queues with exponential backoff.
    
    Args:
        duration_seconds: How long to monitor (default: 120s = 2 minutes)
    """
    print(f"\n👁️  Monitoring queues for {duration_seconds} seconds...")
    print("   Watch as messages move through retry queues!")
    print("   Expected timeline:")
    print("     t=0s: Message in emails.to_classify")
    print("     t=1s: Message in emails.to_classify.retry.30000")
    print("     t=30s: Message back in emails.to_classify (retry 1)")
    print("     t=31s: Message in emails.to_classify.retry.60000")
    print("     t=91s: Message back in emails.to_classify (retry 2)")
    print("     t=92s: Message in emails.to_classify.retry.120000")
    print("     t=212s: Message in dead_letter_queue (max retries)")
    print()
    
    start_time = time.time()
    iteration = 0
    
    while time.time() - start_time < duration_seconds:
        iteration += 1
        elapsed = int(time.time() - start_time)
        
        print(f"\n[{elapsed}s elapsed - Iteration {iteration}]")
        check_queue_status()
        list_retry_queues()
        
        time.sleep(10)  # Check every 10 seconds
    
    print("\n✅ Monitoring complete!")


def purge_all_queues():
    """Purge all messages from queues (for testing cleanup)."""
    
    connection = pika.BlockingConnection(
        pika.ConnectionParameters(
            host='localhost',
            credentials=pika.PlainCredentials('admin', 'admin123')
        )
    )
    channel = connection.channel()
    
    queues = [
        'emails.to_classify',
        'emails.to_respond',
        'dead_letter_queue'
    ]
    
    print("\n🗑️  Purging queues...")
    
    for queue_name in queues:
        try:
            channel.queue_purge(queue_name)
            print(f"  ✅ Purged {queue_name}")
        except Exception as e:
            print(f"  ⚠️  Could not purge {queue_name}: {e}")
    
    connection.close()
    print("  Done!")


def main():
    """Main test routine."""
    
    print("=" * 60)
    print("RabbitMQ Retry Pattern Test Script")
    print("=" * 60)
    
    # Check initial status
    print("\n1️⃣  Checking initial queue status...")
    check_queue_status()
    
    # Publish test email
    print("\n2️⃣  Publishing test email...")
    message_id = publish_test_email(priority=8)
    
    # Give consumer a moment to process
    time.sleep(2)
    
    # Check status after publish
    print("\n3️⃣  Queue status after publish:")
    check_queue_status()
    list_retry_queues()
    
    # Monitor for a while
    print("\n4️⃣  Starting queue monitor...")
    print("     Press Ctrl+C to stop monitoring")
    print()
    
    try:
        monitor_queues(duration_seconds=240)  # 4 minutes
    except KeyboardInterrupt:
        print("\n\n⏹️  Monitoring stopped by user")
    
    # Final status
    print("\n5️⃣  Final queue status:")
    check_queue_status()
    list_retry_queues()
    
    # Cleanup option
    print("\n" + "=" * 60)
    cleanup = input("Do you want to purge all queues? (yes/no): ")
    if cleanup.lower() in ['yes', 'y']:
        purge_all_queues()
    
    print("\n✅ Test complete!")
    print("\nNext steps:")
    print("  - Check RabbitMQ UI: http://localhost:15672")
    print("  - View dead_letter_queue for failed messages")
    print("  - Start consumer with: python -m app.consumers.email_classifier_with_retry")


if __name__ == '__main__':
    main()
