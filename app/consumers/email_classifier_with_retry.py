"""
RabbitMQ Retry Pattern for Handling LLM Quota Errors (429).

This module implements an intelligent retry mechanism that:
1. Tries primary LLM provider (Gemini)
2. Falls back to secondary provider (Claude)
3. If all providers fail with 429, uses exponential backoff retry
4. After max retries, sends to Dead Letter Queue

Author: AI Architecture Team
Date: December 6, 2025
"""

import pika
import json
import logging
from datetime import datetime
from typing import Optional, Dict, Any
import time

logger = logging.getLogger(__name__)


class QuotaExceededError(Exception):
    """Raised when LLM API quota is exceeded (HTTP 429)."""
    pass


class RetryConfig:
    """Configuration for retry behavior."""
    MAX_RETRIES = 3
    BASE_DELAY_MS = 30000  # 30 seconds
    MAX_DELAY_MS = 900000  # 15 minutes
    EXPONENTIAL_BASE = 2


class RabbitMQRetryHandler:
    """
    Handles retry logic for RabbitMQ messages with exponential backoff.
    """
    
    @staticmethod
    def calculate_retry_delay(retry_count: int) -> int:
        """
        Calculate exponential backoff delay in milliseconds.
        
        Args:
            retry_count: Current retry attempt (0-indexed)
        
        Returns:
            Delay in milliseconds
        
        Examples:
            - Retry 0: 30 seconds
            - Retry 1: 60 seconds
            - Retry 2: 120 seconds
            - Retry 3: 240 seconds (capped at 15 minutes)
        """
        delay = RetryConfig.BASE_DELAY_MS * (RetryConfig.EXPONENTIAL_BASE ** retry_count)
        return min(delay, RetryConfig.MAX_DELAY_MS)
    
    @staticmethod
    def get_retry_count(properties: pika.BasicProperties) -> int:
        """Extract retry count from message headers."""
        if properties.headers and 'x-retry-count' in properties.headers:
            return properties.headers['x-retry-count']
        return 0
    
    @staticmethod
    def should_retry(retry_count: int, error: Exception) -> bool:
        """
        Determine if message should be retried.
        
        Args:
            retry_count: Current retry count
            error: Exception that was raised
        
        Returns:
            True if message should be retried, False otherwise
        """
        # Don't retry if max retries exceeded
        if retry_count >= RetryConfig.MAX_RETRIES:
            return False
        
        # Only retry on quota errors (429)
        if isinstance(error, QuotaExceededError):
            return True
        
        # Don't retry other errors
        return False
    
    @staticmethod
    def create_retry_queue(channel: pika.channel.Channel, 
                          base_queue: str, 
                          delay_ms: int) -> str:
        """
        Create a temporary retry queue with TTL.
        
        Args:
            channel: RabbitMQ channel
            base_queue: Original queue name
            delay_ms: Delay in milliseconds
        
        Returns:
            Name of created retry queue
        """
        retry_queue_name = f'{base_queue}.retry.{delay_ms}'
        
        channel.queue_declare(
            queue=retry_queue_name,
            durable=True,
            arguments={
                'x-dead-letter-exchange': '',  # Default exchange
                'x-dead-letter-routing-key': base_queue,  # Route back to main queue
                'x-message-ttl': delay_ms,  # Auto-expire after delay
                'x-expires': delay_ms + 60000  # Delete queue 1 min after last message
            }
        )
        
        return retry_queue_name
    
    @staticmethod
    def publish_to_retry(channel: pika.channel.Channel,
                        base_queue: str,
                        message_body: bytes,
                        retry_count: int,
                        original_properties: Optional[pika.BasicProperties] = None) -> None:
        """
        Publish message to retry queue with exponential backoff.
        
        Args:
            channel: RabbitMQ channel
            base_queue: Original queue name
            message_body: Message content
            retry_count: Current retry count
            original_properties: Original message properties
        """
        # Calculate delay
        delay_ms = RabbitMQRetryHandler.calculate_retry_delay(retry_count)
        
        # Create retry queue
        retry_queue = RabbitMQRetryHandler.create_retry_queue(
            channel, base_queue, delay_ms
        )
        
        # Prepare headers
        headers = original_properties.headers.copy() if original_properties and original_properties.headers else {}
        headers['x-retry-count'] = retry_count + 1
        headers['x-first-retry-time'] = headers.get('x-first-retry-time', datetime.utcnow().isoformat())
        headers['x-last-retry-time'] = datetime.utcnow().isoformat()
        
        # Publish to retry queue
        channel.basic_publish(
            exchange='',
            routing_key=retry_queue,
            body=message_body,
            properties=pika.BasicProperties(
                delivery_mode=2,  # Persistent
                headers=headers
            )
        )
        
        logger.info(
            f"Message sent to retry queue {retry_queue} "
            f"(attempt {retry_count + 1}/{RetryConfig.MAX_RETRIES}, "
            f"will retry in {delay_ms/1000}s)"
        )
    
    @staticmethod
    def send_to_dlq(channel: pika.channel.Channel,
                   message_body: bytes,
                   original_queue: str,
                   error: Exception,
                   retry_count: int,
                   properties: Optional[pika.BasicProperties] = None) -> None:
        """
        Send message to Dead Letter Queue with error details.
        
        Args:
            channel: RabbitMQ channel
            message_body: Message content
            original_queue: Queue where message originated
            error: Exception that caused failure
            retry_count: Number of retry attempts
            properties: Original message properties
        """
        message = json.loads(message_body)
        
        dlq_message = {
            "message_id": message.get("message_id"),
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "original_queue": original_queue,
            "original_message": message,
            "failure_info": {
                "error_message": str(error),
                "error_type": type(error).__name__,
                "retry_count": retry_count,
                "first_retry_time": properties.headers.get('x-first-retry-time') if properties and properties.headers else None,
                "final_failure_time": datetime.utcnow().isoformat()
            }
        }
        
        channel.basic_publish(
            exchange='',
            routing_key='dead_letter_queue',
            body=json.dumps(dlq_message),
            properties=pika.BasicProperties(delivery_mode=2)
        )
        
        logger.error(
            f"Message {message.get('message_id')} sent to DLQ after {retry_count} retries. "
            f"Error: {error}"
        )


class EmailClassifierConsumerWithRetry:
    """
    Email Classifier Consumer with intelligent retry logic.
    
    Handles LLM quota errors (429) gracefully:
    1. Primary: Try Gemini
    2. Fallback: Try Claude
    3. Retry: If all fail, retry with exponential backoff
    4. DLQ: After max retries, send to dead letter queue
    """
    
    def __init__(self, rabbitmq_url: str, llm_factory):
        """Initialize consumer with retry support."""
        self.llm_factory = llm_factory
        self.retry_handler = RabbitMQRetryHandler()
        
        # Connect to RabbitMQ
        params = pika.URLParameters(rabbitmq_url)
        self.connection = pika.BlockingConnection(params)
        self.channel = self.connection.channel()
        
        # Declare queues
        self.channel.queue_declare(queue='emails.to_classify', durable=True)
        self.channel.queue_declare(queue='emails.to_respond', durable=True)
        self.channel.queue_declare(queue='dead_letter_queue', durable=True)
        
        # QoS
        self.channel.basic_qos(prefetch_count=1)
        
        logger.info("Email Classifier Consumer initialized with retry support")
    
    def classify_email(self, email_body: str, subject: str) -> dict:
        """
        Classify an email using LLM with automatic provider fallback.
        
        The LLMFactory already handles fallback between providers,
        but if ALL providers return 429, this raises QuotaExceededError.
        """
        prompt = f"""
        Classify the following email as either a "CUSTOMER_SUPPORT_INQUIRY" or "OTHER".
        
        Subject: {subject}
        Body: {email_body}
        
        Return JSON: {{"is_support_inquiry": true/false, "category": "...", "confidence": 0.0-1.0}}
        """
        
        try:
            # LLMFactory handles Gemini -> Claude fallback internally
            response = self.llm_factory.generate(prompt)
            return json.loads(response)
        except Exception as e:
            # Check if it's a quota error from ALL providers
            if "429" in str(e) or "quota" in str(e).lower():
                raise QuotaExceededError(f"All LLM providers exceeded quota: {e}")
            raise
    
    def callback(self, ch, method, properties, body):
        """
        Process a single email message with retry logic.
        """
        try:
            message = json.loads(body)
            retry_count = self.retry_handler.get_retry_count(properties)
            
            logger.info(
                f"Processing email {message.get('message_id')} "
                f"(retry attempt {retry_count})"
            )
            
            # Check if max retries exceeded
            if retry_count >= RetryConfig.MAX_RETRIES:
                logger.warning(
                    f"Max retries ({RetryConfig.MAX_RETRIES}) exceeded for "
                    f"{message.get('message_id')}, sending to DLQ"
                )
                raise Exception(f"Max retries exceeded after {retry_count} attempts")
            
            # Attempt classification
            classification = self.classify_email(
                email_body=message.get('body', ''),
                subject=message.get('subject', '')
            )
            
            # Success! Handle based on classification
            if classification.get('is_support_inquiry'):
                # Publish to next queue
                response_message = {
                    "message_id": message.get('message_id'),
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "email_id": message.get('email_id'),
                    "thread_id": message.get('thread_id'),
                    "from": message.get('from'),
                    "to": message.get('to'),
                    "subject": message.get('subject'),
                    "body": message.get('body'),
                    "classification": classification,
                    "agent_email": message.get('agent_email')
                }
                
                ch.basic_publish(
                    exchange='',
                    routing_key='emails.to_respond',
                    body=json.dumps(response_message),
                    properties=pika.BasicProperties(delivery_mode=2)
                )
                
                logger.info(f"Email classified as SUPPORT, sent to respond queue")
            else:
                logger.info(f"Email classified as OTHER, ignored")
            
            # Acknowledge successful processing
            ch.basic_ack(delivery_tag=method.delivery_tag)
            
        except QuotaExceededError as e:
            # LLM quota exceeded - retry with backoff
            logger.warning(
                f"LLM quota exceeded for {message.get('message_id')}: {e}"
            )
            
            if self.retry_handler.should_retry(retry_count, e):
                # Publish to retry queue
                self.retry_handler.publish_to_retry(
                    channel=ch,
                    base_queue='emails.to_classify',
                    message_body=body,
                    retry_count=retry_count,
                    original_properties=properties
                )
                
                # Acknowledge original message (we've queued the retry)
                ch.basic_ack(delivery_tag=method.delivery_tag)
            else:
                # Max retries exceeded, send to DLQ
                self.retry_handler.send_to_dlq(
                    channel=ch,
                    message_body=body,
                    original_queue='emails.to_classify',
                    error=e,
                    retry_count=retry_count,
                    properties=properties
                )
                
                # Acknowledge original message
                ch.basic_ack(delivery_tag=method.delivery_tag)
        
        except Exception as e:
            # Permanent error - send to DLQ immediately
            logger.error(f"Permanent error processing email: {e}")
            
            self.retry_handler.send_to_dlq(
                channel=ch,
                message_body=body,
                original_queue='emails.to_classify',
                error=e,
                retry_count=retry_count,
                properties=properties
            )
            
            # Acknowledge message (it's in DLQ now)
            ch.basic_ack(delivery_tag=method.delivery_tag)
    
    def start(self):
        """Start consuming messages."""
        logger.info("Starting Email Classifier Consumer with retry support...")
        
        self.channel.basic_consume(
            queue='emails.to_classify',
            on_message_callback=self.callback
        )
        
        try:
            self.channel.start_consuming()
        except KeyboardInterrupt:
            logger.info("Shutting down consumer...")
            self.channel.stop_consuming()
        finally:
            self.connection.close()


# Example usage
if __name__ == '__main__':
    import os
    from app.services.llm_providers.factory import LLMFactory
    
    # Configuration
    rabbitmq_url = os.getenv(
        'RABBITMQ_URL',
        'amqp://admin:admin123@localhost:5672/'
    )
    
    # Initialize LLM factory with fallback providers
    llm_factory = LLMFactory()
    
    # Start consumer
    consumer = EmailClassifierConsumerWithRetry(rabbitmq_url, llm_factory)
    consumer.start()
