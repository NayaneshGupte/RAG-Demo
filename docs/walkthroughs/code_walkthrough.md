# Code Walkthrough - Critical Flows

This document explains the critical code flows in the application. For detailed component documentation, see the [Architecture Overview](../architecture/README.md).

## Table of Contents

1. [Web Authentication & Routing](#1-web-authentication--routing)
2. [Dashboard Data Fetching](#2-dashboard-data-fetching)
3. [Email Processing](#3-email-processing)
4. [Knowledge Base Upload](#4-knowledge-base-upload)

---

## 1. Web Authentication & Routing

### Architecture

The application uses **separated templates** with **client-side routing** for auth management:

```
/ (landing.html) ←→ /dashboard (dashboard.html)
         ↑                    ↑
         └─── auth.js ────────┘
              (session-based redirects)
```

### Flow

#### 1.1 Landing Page Access (`/`)

**File**: `app/web/routes.py`
```python
@web_bp.route('/')
def index():
    """Render landing page."""
    return render_template('landing.html')
```

**File**: `app/static/js/auth.js`
```javascript
// On page load
async function checkAuthStatus() {
    const response = await fetch('/auth/status');
    const data = await response.json();
    const currentPath = window.location.pathname;
    const urlParams = new URLSearchParams(window.location.search);
    const showLanding = urlParams.get('show_landing') === 'true';

    if (data.authenticated && data.user_email) {
        // User is authenticated
        if ((currentPath === '/' || currentPath === '/index.html') && !showLanding) {
            window.location.href = '/dashboard';  // Redirect to dashboard
        } else {
            initializeDashboard(data.user_email);  // Initialize UI
        }
    } else {
        // Not authenticated - stay on landing or redirect from protected routes
        if (!isPublicPage(currentPath)) {
            window.location.href = '/';
        }
    }
}
```

#### 1.2 Dashboard Access (`/dashboard`)

**File**: `app/web/routes.py`
```python
@web_bp.route('/dashboard')
def dashboard():
    """Render dashboard."""
    return render_template('dashboard.html')
```

**Auth Check**: If user is not authenticated, `auth.js` redirects to `/`.

#### 1.3 Gmail OAuth Login

**File**: `app/auth/routes.py`
```python
@auth_bp.route('/gmail/login')
def gmail_login():
    """Initiate Gmail OAuth flow."""
    # Redirect to Google OAuth consent screen
    # After authorization, callback sets session
    session['user_email'] = email
    return redirect('/dashboard')
```

### Key Takeaway
- **Server-side**: Flask routes serve the correct template
- **Client-side**: `auth.js` enforces redirects based on session status checked via `/auth/status`

---

## 2. Dashboard Data Fetching

### Architecture

The dashboard uses **multiple JavaScript modules** for data fetching:

```
dashboard.js    → /api/metrics/summary        → Summary stats
charts.js       → /api/metrics/email-volume   → Time series data
                → /api/metrics/categories     → Category distribution
```

### Flow

#### 2.1 Page Load

**File**: `app/static/js/dashboard.js`
```javascript
document.addEventListener('DOMContentLoaded', () => {
    fetchData();  // Initial load
    setInterval(fetchData, 30000);  // Auto-refresh every 30 seconds
});

async function fetchData() {
    // Refresh charts
    if (window.refreshCharts) {
        window.refreshCharts();
    }

    // Fetch summary metrics
    await fetchSummaryMetrics();
}

async function fetchSummaryMetrics() {
    const response = await fetch('/api/metrics/summary');
    const data = await response.json();
    
    updateMetric('total-emails', data.total);
    updateMetric('responded-emails', data.responded);
    updateMetric('ignored-emails', data.ignored);
}
```

#### 2.2 Chart Initialization

**File**: `app/static/js/charts.js`
```javascript
function initializeCharts() {
    // Load saved date range
    loadSavedDateRange();
    
    // Listen to date range changes
    DateRangeManager.onChange((params) => {
        renderEmailVolumeChart();  // Re-render on date change
    });
    
    // Initial render
    renderEmailVolumeChart();
    renderCategoryChart();
}

async function renderEmailVolumeChart() {
    const dateParams = DateRangeManager.getParams();
    const url = `/api/metrics/email-volume?start_date=${dateParams.start_date}&end_date=${dateParams.end_date}&interval=${dateParams.interval}`;
    
    const response = await fetch(url);
    const data = await response.json();
    
    // Initialize ApexCharts instance
    emailVolumeChartInstance = new ApexCharts(chartElement, options);
    emailVolumeChartInstance.render();
}
```

#### 2.3 Backend API

**File**: `app/api/routes.py`
```python
@api_bp.route('/metrics/summary')
def get_summary_metrics():
    """Get summary statistics."""
    db_service = DatabaseService()
    current_user = session.get('user_email')
    
    stats = db_service.get_stats(agent_email=current_user)
    return jsonify(stats)

@api_bp.route('/metrics/email-volume')
def get_email_volume_metrics():
    """Get email volume data for charts."""
    # Parse date range from query params
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    interval = request.args.get('interval', 'day')
    
    db_service = DatabaseService()
    current_user = session.get('user_email')
    
    volume_data = db_service.get_email_volume_by_day(
        days=days, 
        start_date=start_date, 
        interval=interval,
        agent_email=current_user  # User isolation
    )
    
    return jsonify({
        'labels': [item['date'] for item in volume_data],
        'total': [item['total'] for item in volume_data],
        'responded': [item['responded'] for item in volume_data],
        # ...
    })
```

### Key Takeaway
- **Separation of Concerns**: `dashboard.js` handles metrics, `charts.js` handles visualizations
- **User Isolation**: All API endpoints filter by `agent_email` from session
- **Auto-Refresh**: Dashboard refreshes every 30 seconds for real-time updates

---

## 3. Email Processing

### Flow

**File**: `app/services/agent_service.py`

```python
class AgentService:
    def run(self, poll_interval=60):
        """Main polling loop."""
        while True:
            self.process_emails()
            time.sleep(poll_interval)
    
    def process_emails(self):
        """Fetch and process new emails."""
        emails = self.gmail_service.get_unread_emails()
        
        for email in emails:
            self.process_email(email)
    
    def process_email(self, email):
        """Complete email processing workflow."""
        # Step 1: Check if should process
        should_process, category = self.should_process_email(email)
        
        if not should_process:
            self.db_service.log_email(status="IGNORED", category=category)
            return
        
        # Step 2: Generate response using RAG
        context_docs = self.vector_store_service.similarity_search(
            query=email['body'], 
            k=3
        )
        
        response = self.llm_factory.generate_content(
            prompt=f"{self.response_prompt}\n\nContext: {context}\n\nEmail: {email['body']}"
        )
        
        # Step 3: Send reply
        self.gmail_service.send_reply(
            to=email['from'],
            subject=email['subject'],
            body=response.content,
            thread_id=email['thread_id']
        )
        
        # Step 4: Mark as read and log
        self.gmail_service.mark_as_read(email['message_id'])
        self.db_service.log_email(status="RESPONDED", category=category)
```

### LLM Fallback Flow

**File**: `app/services/llm_providers/factory.py`

```python
def generate_content(self, prompt, temperature=0.0, max_tokens=1024):
    """Generate content with automatic fallback."""
    for attempt in range(max_retries):
        try:
            response = self.current_provider.generate_content(prompt, temperature, max_tokens)
            
            if response.success:
                return response
                
        except Exception as e:
            is_quota = self._is_quota_error(e)
            
            if is_quota:
                # Permanent switch to fallback
                if self._switch_to_fallback():
                    logger.warning(f"Switched to fallback: {self.current_provider.get_provider_name()}")
                    continue  # Retry immediately with new provider
            else:
                # Transient error - exponential backoff
                wait = min(retry_delay * (2 ** attempt), 60)
                time.sleep(wait)
    
    return LLMResponse(success=False, error="All providers failed")
```

### Key Takeaway
- **Orchestration**: `AgentService` coordinates Gmail, LLM, Vector DB, and Database
- **Resilience**: Multi-LLM fallback ensures continued operation during quota errors
- **RAG Pipeline**: Retrieval → Context Injection → Generation → Response

---

## 4. Knowledge Base Upload

### Flow

**File**: `app/api/routes.py`

```python
@api_bp.route('/upload', methods=['POST'])
def upload_file():
    """Handle PDF file upload and ingestion."""
    file = request.files['file']
    
    if not file.filename.endswith('.pdf'):
        return jsonify({'error': 'Only PDF allowed'}), 400
    
    # Save to temp file
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp:
        file.save(temp.name)
        temp_path = temp.name
    
    # Process PDF
    ingestion_service = IngestionService()
    chunks = ingestion_service.process_pdf(temp_path, file.filename)
    
    # Cleanup
    os.remove(temp_path)
    
    return jsonify({'message': f'Ingested {chunks} chunks'}), 200
```

**File**: `app/services/ingestion_service.py`

```python
class IngestionService:
    def process_pdf(self, file_path, file_name):
        """Process PDF: load, split, and upsert to vector store."""
        # Load PDF
        loader = PyPDFLoader(file_path)
        docs = loader.load()
        
        # Split text
        splits = self.text_splitter.split_documents(docs)
        
        # Filter empty chunks
        splits = [doc for doc in splits if doc.page_content.strip()]
        
        if not splits:
            logger.warning(f"No valid text chunks found in {file_name}")
            return 0
        
        # Embed and upsert to Pinecone
        vector_store = self.vector_store_service.get_vector_store()
        vector_store.add_documents(documents=splits)
        
        logger.info(f"Successfully ingested {file_name}")
        return len(splits)
```

### Vector DB Abstraction

**File**: `app/services/vector_store_service.py`

```python
class VectorStoreService:
    def add_documents(self, documents: List[Dict]) -> int:
        """Add documents to vector store."""
        response = self.factory.add_documents(documents, index_name)
        return response.data if response.success else 0
```

**File**: `app/services/vector_db_providers/pinecone_provider.py`

```python
class PineconeProvider(VectorDBProvider):
    def add_documents(self, documents, index_name):
        """Add documents to Pinecone index."""
        vectors = []
        
        for doc in documents:
            # Generate embedding
            embedding = self._generate_embedding(doc['text'])
            
            # Create vector
            vectors.append({
                'id': str(uuid.uuid4()),
                'values': embedding,
                'metadata': {'text': doc['text'], 'source': doc.get('source', '')}
            })
        
        # Batch upsert to Pinecone
        index = self.pc.Index(index_name)
        index.upsert(vectors=vectors)
        
        return VectorDBResponse(success=True, data=len(vectors))
```

### Key Takeaway
- **PDF Processing**: PyPDFLoader → TextSplitter → Embedding → Pinecone
- **Abstraction**: `VectorStoreService` provides simple interface, `VectorDBFactory` handles provider switching
- **Error Handling**: Empty chunk filtering and validation at multiple levels

---

## Design Patterns Used

### 1. Factory Pattern
- **LLMFactory**: Runtime provider selection with fallback
- **VectorDBFactory**: Abstract vector database operations

### 2. Facade Pattern
- **GmailService**: Unified interface to multiple Gmail sub-services
- **VectorStoreService**: Simplified vector DB operations

### 3. Single Responsibility Principle
- **Gmail sub-services**: Separate classes for reading, sending, modifying emails
- **Frontend JS modules**: Separate files for auth, dashboard, charts

### 4. Session-Based Isolation
- All database queries filtered by `agent_email` from session
- Prevents data leakage between users

---

## Further Reading

- [Architecture Overview](../architecture/README.md) - Complete system architecture
- [Sequence Diagrams](../architecture/SEQUENCE_DIAGRAMS.md) - Detailed workflow diagrams
- [PRD](../PRD.md) - Product requirements and specifications
- [Multi-LLM Architecture](../architecture/llm/README.md) - LLM provider system details
