# Code Walkthrough

This document provides a comprehensive tour of the codebase, explaining key components, design patterns, and code organization.

## Table of Contents

1. [Project Structure](#project-structure)
2. [Entry Points](#entry-points)
3. [Service Layer](#service-layer)
4. [Provider System](#provider-system)
5. [Gmail Integration](#gmail-integration)
6. [Web Application](#web-application)
7. [Key Design Patterns](#key-design-patterns)

## Project Structure

```
RAG-Demo/
├── run.py                      # CLI entry point
├── wsgi.py                     # WSGI entry point for Flask
├── requirements.txt            # Python dependencies
├── .env                        # Configuration (not in git)
├── credentials.json            # Gmail OAuth credentials
├── token.json                  # Gmail OAuth token (generated)
├── email_logs.db              # SQLite database
│
├── app/                        # Main application package
│   ├── __init__.py            # Flask app factory
│   ├── config/__init__.py     # Configuration management
│   │
│   ├── api/                   # API Blueprint
│   │   ├── __init__.py
│   │   └── routes.py          # REST API endpoints
│   │
│   ├── web/                   # Web Blueprint
│   │   ├── __init__.py
│   │   └── routes.py          # Web page routes
│   │
│   ├── services/              # Business logic layer
│   │   ├── agent_service.py           # Email processing orchestration
│   │   ├── gmail_service.py           # Gmail facade
│   │   ├── gmail/                     # Gmail sub-services
│   │   │   ├── auth_service.py
│   │   │   ├── email_reader.py
│   │   │   ├── email_composer.py
│   │   │   ├── email_sender.py
│   │   │   ├── email_modifier.py
│   │   │   └── user_service.py
│   │   ├── llm_providers/             # LLM abstraction
│   │   │   ├── base.py               # LLMProvider interface
│   │   │   ├── factory.py            # LLMFactory with fallback
│   │   │   ├── gemini_provider.py
│   │   │   └── claude_provider.py
│   │   ├── vector_db_providers/       # Vector DB abstraction
│   │   │   ├── base.py               # VectorDBProvider interface
│   │   │   ├── factory.py            # VectorDBFactory
│   │   │   ├── pinecone_provider.py
│   │   │   ├── pinecone_index_manager.py
│   │   │   └── pinecone_document_manager.py
│   │   ├── vector_store_service.py    # Vector DB facade
│   │   ├── ingestion_service.py       # PDF ingestion
│   │   └── database_service.py        # SQLite logging
│   │
│   ├── utils/                 # Utilities
│   │   ├── logger.py          # Logging setup
│   │   └── prompt_loader.py   # Load prompts from files
│   │
│   ├── templates/             # Jinja2 templates
│   │   ├── dashboard.html
│   │   └── knowledge_base.html
│   │
│   └── static/                # Static assets
│       ├── css/
│       └── js/
│
└── docs/                      # Documentation
    ├── architecture/
    ├── guides/
    ├── walkthroughs/
    └── prompts/
```

## Entry Points

### 1. CLI Entry Point (`run.py`)

**Purpose**: Command-line interface for running agent and ingestion bot

**Key Function**: `main()`

```python
def main():
    parser = argparse.ArgumentParser(...)
    subparsers = parser.add_subparsers(dest="command")
    
    # Ingestion command
    ingest_parser = subparsers.add_parser("ingest", ...)
    
    # Agent command  
    agent_parser = subparsers.add_parser("agent", ...)
    agent_parser.add_argument("--poll-interval", default=60, ...)
    
    # ...
    
    if args.command == "ingest":
        ingestion_service = IngestionService()
        ingestion_service.run_telegram_bot()
        
    elif args.command == "agent":
        agent = AgentService()
        agent.run(poll_interval=args.poll_interval)
```

**Usage**:
```bash
python run.py agent --poll-interval 60
python run.py ingest
```

### 2. Flask App Factory (`app/__init__.py`)

**Purpose**: Create and configure Flask application

**Key Function**: `create_app()`

```python
def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Initialize CORS
    CORS(app, resources={r"/api/*": {"origins": "*"}})
    
    # Register Blueprints
    from app.api import api_bp
    from app.web import web_bp
    
    app.register_blueprint(api_bp)    # /api/*
    app.register_blueprint(web_bp)    # /
    
    return app
```

**Blueprint Registration**:
- `api_bp` (prefix: `/api`) - REST API routes
- `web_bp` (no prefix) - Web page routes

## Service Layer

### 1. AgentService (`services/agent_service.py`)

**Purpose**: Orchestrates email processing workflow

**Key Methods**:

#### `__init__()`
Initializes all dependencies:
```python
def __init__(self):
    self.gmail_service = GmailService()
    self.vector_store_service = VectorStoreService()
    self.db_service = DatabaseService()
    
    # Initialize LLM factory with fallback
    self.llm_factory = LLMFactory(
        primary_provider=Config.LLM_PRIMARY_PROVIDER,    # gemini
        fallback_providers=Config.LLM_FALLBACK_PROVIDERS  # [claude]
    )
    
    # Load prompts from files
    self.classification_prompt = self._load_classification_prompt()
    self.response_prompt = self._load_response_prompt()
```

#### `should_process_email(email)`
Determines if email should be processed:
```python
def should_process_email(self, email):
    # Check if from excluded domain
    sender_email = email.get('from', '')
    excluded_domains = ['@phonepe.com', '@notifications.google.com']
    
    if any(domain in sender_email.lower() for domain in excluded_domains):
        return False, "Domain excluded"
    
    # Check if already processed (using message_id)
    # ...
    
    # Classify with LLM
    classification_result = self.llm_factory.generate_content(
        prompt=f"{self.classification_prompt}\n\nEmail:\n{email['body']}",
        temperature=0.0
    )
    
    if "customer support inquiry" in classification_result.content.lower():
        return True, "Customer Support Inquiry"
    else:
        return False, "Not support inquiry"
```

#### `generate_response(email)`
Generates response using RAG:
```python
def generate_response(self, email) Results from vector search
    context_docs = self.vector_store_service.similarity_search(
        query=email['body'],
        k=3
    )
    
    # Format context
    context = "\n\n".join([doc['text'] for doc in context_docs])
    
    # Generate response with LLM
    prompt = f"""{self.response_prompt}

Email from {email['from']}:
{email['body']}

Relevant context:
{context}

Generate a helpful response:"""
    
    response = self.llm_factory.generate_content(
        prompt=prompt,
        temperature=0.7,  # Slightly creative for natural responses
        max_tokens=1024
    )
    
    return response.content if response.success else None
```

#### `process_email(email)`
Complete email processing workflow:
```python
def process_email(self, email):
    try:
        # Step 1: Check if should process
        should_process, category = self.should_process_email(email)
        
        if not should_process:
            self.db_service.log_email(
                sender=email['from'],
                subject=email['subject'],
                status="IGNORED",
                category=category
            )
            return
        
        # Step 2: Generate response
        response = self.generate_response(email)
        
        if not response:
            raise Exception("Failed to generate response")
        
        # Step 3: Send reply
        self.gmail_service.send_reply(
            to=email['from'],
            subject=email['subject'],
            body=response,
            thread_id=email['thread_id'],
            message_id=email['message_id']
        )
        
        # Step 4: Mark as read
        self.gmail_service.mark_as_read(email['message_id'])
        
        # Step 5: Log success
        self.db_service.log_email(
            sender=email['from'],
            subject=email['subject'],
            status="RESPONDED",
            category=category,
            details="Successfully replied"
        )
        
    except Exception as e:
        logger.error(f"Error processing email: {e}")
        self.db_service.log_email(
            sender=email['from'],
            subject=email['subject'],
            status="FAILED",
            details=str(e)
        )
```

#### `run(poll_interval=60)`
Continuous polling loop:
```python
def run(self, poll_interval=60):
    start_time = int(time.time())
    
    while True:
        try:
            self.process_emails()  # Fetch and process new emails
            time.sleep(poll_interval)
        except KeyboardInterrupt:
            logger.info("Agent stopped by user")
            break
        except Exception as e:
            logger.error(f"Error in agent loop: {e}")
            time.sleep(poll_interval)
```

### 2. GmailService - Facade Pattern (`services/gmail_service.py`)

**Purpose**: Unified interface to Gmail operations

**Implementation**:
```python
class GmailService:
    """Facade for Gmail operations."""
    
    def __init__(self):
        # Initialize auth service
        self.auth_service = GmailAuthService(
            Config.GMAIL_CREDENTIALS_FILE,
            Config.GMAIL_TOKEN_FILE
        )
        self.api_service = self.auth_service.get_service()
        
        # Initialize sub-services
        self.reader = GmailEmailReader(self.api_service)
        self.composer = GmailEmailComposer()
        self.sender = GmailEmailSender(self.api_service)
        self.modifier = GmailEmailModifier(self.api_service)
        self.user_service = GmailUserService(self.api_service)
    
    # Delegated methods
    def get_unread_emails(self, after_timestamp=None):
        """Delegate to reader"""
        return self.reader.get_unread_emails(after_timestamp)
    
    def send_reply(self, to, subject, body, thread_id, message_id=None, references=None):
        """Delegate to sender (which uses composer)"""
        return self.sender.send_reply(to, subject, body, thread_id, message_id, references)
    
    def mark_as_read(self, msg_id):
        """Delegate to modifier"""
        return self.modifier.mark_as_read(msg_id)
    
    def get_current_email(self):
        """Delegate to user service"""
        return self.user_service.get_current_email()
```

**Why Facade Pattern?**
- Maintains backward compatibility
- Simplifies client code
- Internally uses Single Responsibility sub-services

### 3. VectorStoreService (`services/vector_store_service.py`)

**Purpose**: Simplified interface to vector database operations

**Key Methods**:

```python
class VectorStoreService:
    def __init__(self, vector_db_type=None, fallback_providers=None):
        self.factory = VectorDBFactory(
            primary_provider=vector_db_type or Config.VECTOR_DB_TYPE,
            fallback_providers=fallback_providers or Config.VECTOR_DB_FALLBACK_PROVIDERS
        )
    
    def similarity_search(self, query: str, k: int = 3) -> List[Dict]:
        """Search for similar documents"""
        response = self.factory.similarity_search(query, k, index_name)
        return response.data if response.success else []
    
    def add_documents(self, documents: List[Dict]) -> int:
        """Add documents, return count"""
        response = self.factory.add_documents(documents, index_name)
        return response.data if response.success else 0
    
    def get_vector_store(self):
        """Get simplified wrapper for backward compatibility"""
        # Returns object with similarity_search() and add_documents()
        # Used by IngestionService
        ...
```

## Provider System

### LLMFactory (`services/llm_providers/factory.py`)

**Key Features**:
1. **Provider Registry**: Dictionary mapping names to classes
2. **Fallback Manager**: Switches providers on quota errors
3. **Retry Logic**: Exponential backoff for transient errors

**Critical Method**: `generate_content()`

```python
def generate_content(self, prompt, temperature=0.0, max_tokens=1024, 
                    max_retries=5, retry_delay=5):
    """Generate content with automatic fallback"""
    
    for attempt in range(max_retries):
        try:
            # Try current provider
            response = self.current_provider.generate_content(
                prompt, temperature, max_tokens
            )
            
            if response.success:
                return response
            else:
                raise Exception(response.error)
                
        except Exception as e:
            is_quota = self._is_quota_error(e)
            
            if is_quota:
                # Permanent switch to fallback
                if self._switch_to_fallback():
                    logger.warning(f"Switched to fallback: {self.current_provider.get_provider_name()}")
                    # Retry immediately with new provider
                    continue
                else:
                    # No fallbacks available
                    break
            else:
                # Transient error - retry with backoff
                if attempt < max_retries - 1:
                    wait = min(retry_delay * (2 ** attempt), 60)
                    time.sleep(wait)
                else:
                    break
    
    # All retries exhausted
    return LLMResponse(
        success=False,
        content="",
        provider_name="unknown",
        error="All providers failed"
    )
```

### VectorDBFactory (`services/vector_db_providers/factory.py`)

**Similar Pattern to LLMFactory**:
```python
class VectorDBFactory:
    _PROVIDER_REGISTRY = {}
    
    @classmethod
    def register_provider(cls, name, provider_class):
        """Register provider in registry"""
        cls._PROVIDER_REGISTRY[name] = provider_class
    
    def similarity_search(self, query, k, index_name):
        """Delegate to current provider"""
        provider = self.get_current_provider()
        return provider.similarity_search(query, k, index_name)
```

## Gmail Integration

### Gmail Sub-Services (SRP Pattern)

#### 1. GmailEmailReader (`services/gmail/email_reader.py`)

**Responsibility**: Fetch and parse emails

```python
class GmailEmailReader:
    def __init__(self, service):
        self.service = service  # Gmail API service
    
    def get_unread_emails(self, after_timestamp=None):
        """Fetch unread emails with optional timestamp filter"""
        
        # Build query
        query = "is:unread"
        if after_timestamp:
            query += f" after:{after_timestamp}"
        
        # Fetch message list
        results = self.service.users().messages().list(
            userId='me',
            q=query
        ).execute()
        
        messages = results.get('messages', [])
        
        # Fetch full details for each
        emails = []
        for msg in messages:
            full_msg = self.service.users().messages().get(
                userId='me',
                id=msg['id'],
                format='full'
            ).execute()
            
            # Parse headers and body
            email_data = self._parse_message(full_msg)
            emails.append(email_data)
        
        return emails
    
    def _parse_message(self, msg):
        """Extract headers and body"""
        headers = {h['name']: h['value'] for h in msg['payload']['headers']}
        body = self._extract_body(msg['payload'])
        
        return {
            'message_id': msg['id'],
            'thread_id': msg['threadId'],
            'from': headers.get('From', ''),
            'subject': headers.get('Subject', ''),
            'body': body,
            'timestamp': int(msg['internalDate']) // 1000
        }
    
    def _extract_body(self, payload):
        """Recursively extract email body (handles multipart)"""
        if 'body' in payload and 'data' in payload['body']:
            return base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8')
        
        if 'parts' in payload:
            for part in payload['parts']:
                if part['mimeType'] == 'text/plain':
                    return self._extract_body(part)
        
        return ""
```

#### 2. GmailEmailSender (`services/gmail/email_sender.py`)

**Responsibility**: Send email replies

```python
class GmailEmailSender:
    def send_reply(self, to, subject, body, thread_id, message_id=None, references=None):
        """Send reply email"""
        
        # Use composer to create message
        from app.services.gmail.email_composer import GmailEmailComposer
        composer = GmailEmailComposer()
        
        composed = composer.create_reply(
            to=to,
            subject=subject,
            body=body,
            thread_id=thread_id,
            message_id=message_id,
            references=references
        )
        
        # Send via Gmail API
        sent_message = self.service.users().messages().send(
            userId='me',
            body={
                'raw': composed['raw'],
                'threadId': thread_id
            }
        ).execute()
        
        return sent_message
```

## Web Application

### API Routes (`app/api/routes.py`)

**REST Endpoints**:

```python
@api_bp.route('/logs')
def get_logs():
    """Get email processing logs"""
    current_user = gmail_service.get_current_email()
    
    logs = db_service.get_logs(
        limit=100,
        agent_email=current_user
    )
    stats = db_service.get_stats(agent_email=current_user)
    kb_stats = vector_store_service.get_stats()
    
    return jsonify({
        "logs": logs,
        "stats": stats,
        "kb_stats": kb_stats,
        "current_user": current_user
    })

@api_bp.route('/upload', methods=['POST'])
def upload_file():
    """Handle PDF upload and ingestion"""
    file = request.files['file']
    
    if not file.filename.endswith('.pdf'):
        return jsonify({'error': 'Only PDF allowed'}), 400
    
    # Save to temp, process, cleanup
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp:
        file.save(temp.name)
        chunks = ingestion_service.process_pdf(temp.name, file.filename)
        os.remove(temp.name)
    
    return jsonify({'message': f'Ingested {chunks} chunks'}), 200
```

### Web Routes (`app/web/routes.py`)

**HTML Pages**:

```python
@web_bp.route('/')
def index():
    """Render dashboard"""
    current_user = gmail_service.get_current_email()
    return render_template('dashboard.html', current_user=current_user)

@web_bp.route('/knowledge-base')
def knowledge_base():
    """Render KB viewer"""
    current_user = gmail_service.get_current_email()
    return render_template('knowledge_base.html', current_user=current_user)
```

## Key Design Patterns

### 1. Factory Pattern
**Where**: `LLMFactory`, `VectorDBFactory`  
**Why**: Provider abstraction, runtime selection, easy extension

### 2. Facade Pattern
**Where**: `GmailService`, `VectorStoreService`  
**Why**: Simplified interface, backward compatibility

### 3. Single Responsibility Principle
**Where**: Gmail sub-services (Reader, Sender, Composer, etc.)  
**Why**: Each class has one reason to change, easier testing

### 4. Dependency Injection
**Where**: Services accept dependencies in `__init__`  
**Why**: Testability, flexibility

### 5. Registry Pattern
**Where**: Provider registries in factories  
**Why**: Dynamic provider registration

## Code Flow Examples

### Example 1: Email Processing

```
1. AgentService.run() starts polling loop
2. AgentService.process_emails()
3. GmailService.get_unread_emails()
   └─> GmailEmailReader.get_unread_emails()
4. For each email:
   a. AgentService.should_process_email()
      └─> LLMFactory.generate_content() [classification]
   b. If customer inquiry:
      └─> AgentService.generate_response()
          ├─> VectorStoreService.similarity_search()
          └─> LLMFactory.generate_content() [response]
   c. GmailService.send_reply()
      ├─> GmailEmailComposer.create_reply()
      └─> GmailEmailSender.send_message()
   d. GmailService.mark_as_read()
   e. DatabaseService.log_email()
```

### Example 2: PDF Ingestion

```
1. User uploads PDF to Telegram
2. Telegram Bot calls IngestionService.handle_document()
3. IngestionService.process_pdf()
   ├─> PyPDFLoader.load() - Extract text
   ├─> RecursiveCharacterTextSplitter.split() - Chunk text
   └─> VectorStoreService.add_documents()
       └─> VectorDBFactory.add_documents()
           ├─> PineconeProvider.add_documents()
           │   ├─> Generate embeddings (Gemini)
           │   └─> Upsert to Pinecone
           └─> Return VectorDBResponse
```

## Configuration Management

**File**: `app/config/__init__.py`

```python
class Config:
    # LLM Configuration
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
    LLM_PRIMARY_PROVIDER = os.getenv("LLM_PRIMARY_PROVIDER", "gemini")
    LLM_FALLBACK_PROVIDERS = os.getenv("LLM_FALLBACK_PROVIDERS", "claude").split(",")
    
    # Vector DB Configuration
    VECTOR_DB_TYPE = os.getenv("VECTOR_DB_TYPE", "pinecone")
    PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
    PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME")
    
    # Gmail Configuration
    GMAIL_CREDENTIALS_FILE = "credentials.json"
    GMAIL_TOKEN_FILE = "token.json"
    
    # Document Processing
    CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "1000"))
    CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "150"))
    
    @classmethod
    def validate(cls):
        """Validate required configuration"""
        required = ['GOOGLE_API_KEY', 'PINECONE_API_KEY']
        missing = [key for key in required if not getattr(cls, key)]
        if missing:
            raise ValueError(f"Missing config: {', '.join(missing)}")
```

## Further Reading

- [Architecture Overview](../architecture/README.md)
- [Sequence Diagrams](../architecture/SEQUENCE_DIAGRAMS.md)
- [Multi-LLM Architecture](../architecture/llm/README.md)
- [Multi-Vector DB Architecture](../architecture/vector_db/README.md)
