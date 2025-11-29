"""
AI Agent service for automated email responses.
Simplified version compatible with Python 3.14.
Uses pluggable LLM providers for maximum flexibility.
"""
import time
import logging
import json
from datetime import datetime
import os
from langchain_core.prompts import PromptTemplate
from app.config import Config
from app.services.llm_providers.factory import LLMFactory
from app.services.vector_store_service import VectorStoreService
from app.services.gmail_service import GmailService
from app.services.database_service import DatabaseService
from app.utils.prompt_loader import load_prompt

logger = logging.getLogger(__name__)

class AgentService:
    """Service for AI-powered email response agent."""
    
    def __init__(self):
        self.gmail_service = GmailService()
        self.vector_store_service = VectorStoreService()
        self.db_service = DatabaseService()
        self.current_email = self.gmail_service.get_current_email()
        self.start_time = time.time() * 1000  # Current time in milliseconds
        logger.info(f"Agent initialized for user: {self.current_email}")
        logger.info(f"Agent start time: {self.start_time} (Filter active for older emails)")
        
        # Initialize LLM factory with configured primary and fallback providers
        self.llm_factory = LLMFactory(
            primary_provider=Config.LLM_PRIMARY_PROVIDER,
            fallback_providers=Config.LLM_FALLBACK_PROVIDERS
        )
        
        # Log LLM provider status
        provider_status = self.llm_factory.get_provider_status()
        logger.info(f"LLM Provider Status: {provider_status}")
        
        if self.llm_factory.get_current_provider() is None:
            raise ValueError("No LLM providers available. Please configure at least one LLM provider.")
        
        self.classification_prompt = self._load_classification_prompt()
        self.response_prompt = self._load_response_prompt()
    
    def _load_classification_prompt(self):
        """Load email classification prompt."""
        prompt_text = load_prompt(Config.EMAIL_CLASSIFICATION_PROMPT_FILE)
        return PromptTemplate(
            template=prompt_text,
            input_variables=["subject", "body"]
        )
    
    def _load_response_prompt(self):
        """Load response generation prompt."""
        system_prompt = load_prompt(Config.AGENT_SYSTEM_PROMPT_FILE)
        
        template = f"""{system_prompt}

**RETRIEVED CONTEXT:**
{{context}}

**CUSTOMER EMAIL:**
Subject: {{subject}}
Body: {{body}}

**YOUR RESPONSE:**
"""
        return PromptTemplate(
            template=template,
            input_variables=["context", "subject", "body"]
        )

    
    def should_process_email(self, email):
        """Determine if an email should be processed by the agent."""
        try:
            formatted_prompt = self.classification_prompt.format(
                subject=email['subject'],
                body=email['body'][:500]
            )
            
            # Use LLM factory to generate content with automatic retry and fallback
            response = self.llm_factory.generate_content(
                prompt=formatted_prompt,
                temperature=Config.LLM_TEMPERATURE,
                max_tokens=Config.LLM_MAX_TOKENS,
                max_retries=Config.LLM_RETRY_MAX_ATTEMPTS,
                retry_delay=Config.LLM_RETRY_DELAY_SECONDS
            )
            decision_text = response.text.strip()
            
            # Try to parse JSON response
            try:
                # Clean up potential markdown code blocks
                if "```json" in decision_text:
                    decision_text = decision_text.split("```json")[1].split("```")[0].strip()
                elif "```" in decision_text:
                    decision_text = decision_text.split("```")[1].split("```")[0].strip()

                decision_json = json.loads(decision_text)
                should_process = decision_json.get("classification", "").upper() == "RESPOND"
                category = decision_json.get("category", "Unknown")
                reason = decision_json.get("reason", "")
                
                logger.info(
                    f"Email '{email['subject']}': {decision_json.get('classification')} "
                    f"[{category}] - {reason}"
                )
                
                # Log classification result
                email_ts = datetime.fromtimestamp(email.get('internalDate', 0) / 1000) if email.get('internalDate') else None
                
                if not should_process:
                    self.db_service.log_email(
                        sender=email['sender'],
                        subject=email['subject'],
                        status="IGNORED",
                        details=f"Category: {category}. Reason: {reason}",
                        category=category,
                        agent_email=self.current_email,
                        email_timestamp=email_ts
                    )
                
                return should_process, category
                
            except json.JSONDecodeError:
                # Fallback to simple YES/NO check
                should_process = "RESPOND" in decision_text.upper() or "YES" in decision_text.upper()
                logger.info(
                    f"Email '{email['subject']}': "
                    f"{'PROCESS' if should_process else 'IGNORE'}"
                )
                return should_process, "Unknown"
            
        except Exception as e:
            logger.error(f"Error classifying email: {e}", exc_info=True)
            return True, "Error"  # Default to processing if classification fails
    
    def generate_response(self, email):
        """Generate a response to an email using RAG."""
        try:
            # Get vector store and search for relevant context
            vector_store = self.vector_store_service.get_vector_store()
            query = f"{email['subject']} {email['body']}"
            
            # Retrieve relevant documents
            docs = vector_store.similarity_search(query, k=3)
            context = "\n\n".join([doc.page_content for doc in docs])
            
            logger.info(f"Retrieved {len(docs)} relevant documents from knowledge base")
            
            # Generate response using LLM factory with automatic retry and fallback
            formatted_prompt = self.response_prompt.format(
                context=context,
                subject=email['subject'],
                body=email['body']
            )
            
            response = self.llm_factory.generate_content(
                prompt=formatted_prompt,
                temperature=Config.LLM_TEMPERATURE,
                max_tokens=Config.LLM_MAX_TOKENS,
                max_retries=Config.LLM_RETRY_MAX_ATTEMPTS,
                retry_delay=Config.LLM_RETRY_DELAY_SECONDS
            )
            return response.text.strip()
            
        except Exception as e:
            logger.error(f"Error generating response: {e}", exc_info=True)
            return None
    
    def process_email(self, email):
        """Process a single email and send response."""
        logger.info(f"Evaluating email from {email['sender']}: {email['subject']}")
        
        # Check if email should be processed
        should_process, category = self.should_process_email(email)
        
        if not should_process:
            logger.info(f"Skipping email '{email['subject']}' - not a customer support inquiry")
            # Mark as read so we don't process it again
            self.gmail_service.mark_as_read(email['id'])
            # Rate limit: Sleep after classification
            time.sleep(5)
            return
        
        # Rate limit: Sleep after classification
        time.sleep(5)
        
        logger.info(f"Processing email '{email['subject']}'")
        
        try:
            # Generate response
            answer = self.generate_response(email)
            
            email_ts = datetime.fromtimestamp(email.get('internalDate', 0) / 1000) if email.get('internalDate') else None
            
            if not answer:
                logger.error(f"Failed to generate response for email {email['id']}")
                self.db_service.log_email(
                    sender=email['sender'],
                    subject=email['subject'],
                    status="ERROR",
                    details="Failed to generate response",
                    category=category,
                    agent_email=self.current_email,
                    email_timestamp=email_ts
                )
                return
            
            # Rate limit: Sleep after generation
            time.sleep(5)
            
            # Send reply
            self.gmail_service.send_reply(
                email['sender'],
                email['subject'],
                answer,
                email['threadId']
            )
            
            # Mark as read
            self.gmail_service.mark_as_read(email['id'])
            logger.info(f"Successfully processed email {email['id']}")
            
            # Log success
            self.db_service.log_email(
                sender=email['sender'],
                subject=email['subject'],
                status="RESPONDED",
                details="Successfully replied",
                category=category,
                agent_email=self.current_email,
                email_timestamp=email_ts
            )
            
        except Exception as e:
            logger.error(f"Error processing email {email['id']}: {e}", exc_info=True)
            email_ts = datetime.fromtimestamp(email.get('internalDate', 0) / 1000) if email.get('internalDate') else None
            self.db_service.log_email(
                sender=email['sender'],
                subject=email['subject'],
                status="ERROR",
                details=str(e),
                category=category,
                agent_email=self.current_email,
                email_timestamp=email_ts
            )
    
    def process_emails(self):
        """Check for new emails and process them."""
        logger.info("Checking for unread emails...")
        try:
            # Pass start_time (converted to seconds) to filter at API level
            emails = self.gmail_service.get_unread_emails(after_timestamp=self.start_time / 1000)
            
            if not emails:
                logger.info("No unread emails found.")
                return

            logger.info(f"Found {len(emails)} unread email(s)")
            
            # Filter out old emails
            new_emails = [e for e in emails if e['internalDate'] > self.start_time]
            skipped_count = len(emails) - len(new_emails)
            
            if skipped_count > 0:
                logger.info(f"Skipping {skipped_count} old email(s) received before agent start.")
            
            if not new_emails:
                logger.info("No new emails to process.")
                return

            for email in new_emails:
                self.process_email(email)
                # Additional safety sleep between emails
                time.sleep(5)

        except Exception as e:
            logger.error(f"Error in process_emails: {e}", exc_info=True)
    
    def run(self, poll_interval=60):
        """Run the agent in continuous polling mode."""
        logger.info("🤖 AI Support Agent started with LLM Provider Factory")
        print(f"🤖 AI Support Agent is running. Checking emails every {poll_interval} seconds...")
        provider_status = self.llm_factory.get_provider_status()
        print(f"   Current LLM Provider: {provider_status['current_provider']}")
        
        while True:
            self.process_emails()
            time.sleep(poll_interval)
