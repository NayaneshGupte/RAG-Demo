# Sequence Diagrams

This document provides detailed sequence diagrams for all major system workflows.

## 1. Email Processing Workflow (Complete Flow)

```mermaid
sequenceDiagram
    actor User as Gmail User
    participant Gmail as Gmail API
    participant Agent as AgentService
    participant GmailSvc as GmailService
    participant LLM as LLMFactory
    participant Gemini as GeminiProvider
    participant Claude as ClaudeProvider
    participant Vector as VectorStoreService
    participant VectorDB as PineconeProvider
    participant DB as DatabaseService
    
    Note over Agent: Polling every 60s
    Agent->>GmailSvc: get_unread_emails(after_timestamp)
    GmailSvc->>Gmail: messages.list(q="is:unread after:timestamp")
    Gmail-->>GmailSvc: email list
    GmailSvc->>Gmail: messages.get(id) for each
    Gmail-->>GmailSvc: full email details
    GmailSvc-->>Agent: List[Email]
    
    loop For each email
        Agent->>Agent: should_process_email(email)
        
        alt Email from ignored domain
            Agent->>DB: log_email(sender, "IGNORED", "Domain excluded")
        else Valid email to process
            Note over Agent: Step 1: Classify Email
            Agent->>LLM: generate_content(classification_prompt + email.body)
            LLM->>Gemini: classify(email)
            
            alt Gemini succeeds
                Gemini-->>LLM: "Customer Support Inquiry"
            else Gemini quota exceeded (429)
                Gemini--XLM: HTTP 429 Error
                LLM->>LLM: Detect quota error
                LLM->>Claude: Fallback classification
                Claude-->>LLM: "Customer Support Inquiry"
            end
            
            LLM-->>Agent: Classification result
            
            alt Is Customer Support Inquiry
                Note over Agent: Step 2: RAG Retrieval
                Agent->>Vector: similarity_search(email.body, k=3)
                Vector->>VectorDB: query(embedding(email.body))
                VectorDB-->>Vector: top 3 relevant chunks
                Vector-->>Agent: context documents
                
                Note over Agent: Step 3: Generate Response
                Agent->>LLM: generate_content(response_prompt + email + context)
                LLM->>Gemini: generate response
                
                alt Gemini succeeds
                    Gemini-->>LLM: response text
                else Gemini fails again
                    Gemini--XLLM: Error
                    LLM->>Claude: Fallback generation
                    Claude-->>LLM: response text
                end
                
                LLM-->>Agent: Generated response
                
                Note over Agent: Step 4: Send Reply
                Agent->>GmailSvc: send_reply(to, subject, body, thread_id, message_id)
                GmailSvc->>GmailSvc: Compose message with headers
                GmailSvc->>Gmail: messages.send(raw_message)
                Gmail-->>GmailSvc: sent message
                GmailSvc-->>Agent: Success
                
                Note over Agent: Step 5: Mark as Read
                Agent->>GmailSvc: mark_as_read(msg_id)
                GmailSvc->>Gmail: messages.modify(removeLabels=["UNREAD"])
                Gmail-->>GmailSvc: modified
                
                Note over Agent: Step 6: Log Success
                Agent->>DB: log_email(sender, subject, "RESPONDED", category, agent_email)
                DB-->>Agent: Logged
                
                Gmail->>User: Email notification
                
            else Not Support Inquiry
                Agent->>DB: log_email(sender, subject, "IGNORED", "Not support inquiry")
            end
        end
    end
```

## 2. Web Authentication & Routing Flow

```mermaid
sequenceDiagram
    actor User
    participant Browser
    participant AuthJS as auth.js
    participant Flask as Flask Routes
    participant AuthAPI as Auth Routes
    participant Session
    participant Gmail as GmailService
    
    User->>Browser: Navigate to /
    Browser->>Flask: GET /
    Flask-->>Browser: Render landing.html
    Browser->>AuthJS: DOMContentLoaded
    AuthJS->>AuthAPI: GET /auth/status
    AuthAPI->>Session: Check session
    
    alt User authenticated
        Session-->>AuthAPI: {authenticated: true, user_email: "user@example.com"}
        AuthAPI-->>AuthJS: User data
        AuthJS->>Browser: Redirect to /dashboard
        Browser->>Flask: GET /dashboard
        Flask-->>Browser: Render dashboard.html
        AuthJS->>AuthJS: initializeDashboard(user_email)
    else Not authenticated
        Session-->>AuthAPI: {authenticated: false}
        AuthAPI-->>AuthJS: No auth
        Note over Browser: Stay on landing page
    end
    
    Note over User: User clicks "Connect Gmail"
    User->>Browser: Click login button
    Browser->>AuthAPI: GET /auth/gmail/login
    AuthAPI->>Gmail: OAuth flow
    Gmail-->>AuthAPI: Authorization code
    AuthAPI->>Session: Set session
    Session-->>AuthAPI: Success
    AuthAPI-->>Browser: Redirect to /dashboard
```

## 3. Dashboard Data Fetching Flow

```mermaid
sequenceDiagram
    actor User
    participant Browser
    participant DashboardJS as dashboard.js
    participant ChartsJS as charts.js
    participant API as API Routes
    participant DB as DatabaseService
    participant Vector as VectorStoreService
    
    Note over Browser: User authenticated on /dashboard
    Browser->>DashboardJS: DOMContentLoaded
    DashboardJS->>DashboardJS: fetchData()
    
    par Fetch Summary Metrics
        DashboardJS->>API: GET /api/metrics/summary
        API->>DB: get_stats(agent_email=current_user)
        DB-->>API: {total: 47, responded: 20, ignored: 25}
        API-->>DashboardJS: Stats data
        DashboardJS->>Browser: Update metric cards
    and Fetch Chart Data
        ChartsJS->>API: GET /api/metrics/email-volume?start_date=...&end_date=...
        API->>DB: get_email_volume_by_day(days, start_date, interval, agent_email)
        DB-->>API: Volume data
        API-->>ChartsJS: {labels, total, responded, ignored, failed}
        ChartsJS->>Browser: Render ApexCharts line chart
    and Fetch Category Data
        ChartsJS->>API: GET /api/metrics/categories
        API->>DB: get_category_breakdown(agent_email)
        DB-->>API: Category data
        API-->>ChartsJS: {labels, values}
        ChartsJS->>Browser: Render ApexCharts donut chart
    end
    
    Note over Browser: Auto-refresh every 30 seconds
    loop Every 30s
        DashboardJS->>API: GET /api/metrics/summary
        API-->>DashboardJS: Updated stats
        DashboardJS->>Browser: Update UI
    end
```

## 4. PDF Upload via Dashboard

```mermaid
sequenceDiagram
    actor User
    participant Browser
    participant API as API Routes
    participant Ingestion as IngestionService
    participant Loader as PyPDFLoader
    participant Splitter as TextSplitter
    participant Vector as VectorStoreService
    participant VectorDB as PineconeProvider
    participant Gemini as Gemini Embedding API
    participant Temp as Temp File
    
    User->>Browser: Select PDF + Click Upload
    Browser->>API: POST /api/upload (multipart/form-data)
    
    API->>API: Validate 'file' in request.files
    alt No file
        API-->>Browser: 400 Error: No file part
    else Empty filename
        API-->>Browser: 400 Error: No selected file
    else Not PDF
        API-->>Browser: 400 Error: Only PDF allowed
    else Valid PDF
        API->>Temp: Save to temp file
        Temp-->>API: temp_path
        
        API->>Ingestion: process_pdf(temp_path, filename)
        Ingestion->>Loader: PyPDFLoader(temp_path)
        Loader->>Loader: Load PDF pages
        Loader-->>Ingestion: List[Document]
        
        Ingestion->>Splitter: split_documents(docs)
        Splitter->>Splitter: Recursive split (chunk_size=1000, overlap=150)
        Splitter-->>Ingestion: List[Document chunks]
        
        Ingestion->>Ingestion: Filter empty chunks
        
        alt No valid chunks
            Ingestion-->>API: 0 chunks
            API-->>Browser: Warning: No valid text found
        else Has valid chunks
            Ingestion->>Vector: get_vector_store()
            Vector-->>Ingestion: SimplifiedVectorStore
            
            Ingestion->>Vector: add_documents(chunks)
            Vector->>VectorDB: add_documents(chunks, index_name)
            
            loop For each chunk
                VectorDB->>Gemini: Generate embedding(chunk.text)
                Gemini-->>VectorDB: 768-dim vector
                VectorDB->>VectorDB: Create vector {id, values, metadata}
            end
            
            VectorDB->>VectorDB: Upsert vectors to Pinecone (batch)
            VectorDB-->>Vector: VectorDBResponse(success=True, data=num_chunks)
            Vector-->>Ingestion: num_chunks
            
            Ingestion->>Temp: Delete temp file
            Ingestion-->>API: num_chunks
            API-->>Browser: 200 Success: Ingested X chunks
            Browser->>Browser: Display success message
        end
    end
```

## 5. LLM Provider Fallback Flow

```mermaid
sequenceDiagram
    participant Agent as AgentService
    participant Factory as LLMFactory
    participant Primary as GeminiProvider
    participant Fallback as ClaudeProvider
    participant Retry as Retry Logic
    
    Agent->>Factory: generate_content(prompt, temp=0.0)
    Factory->>Factory: current_provider = GeminiProvider
    
    Note over Factory: Attempt 1 with Gemini
    Factory->>Primary: generate_content(prompt)
    Primary->>Primary: Call Gemini API
    
    alt API Success
        Primary-->>Factory: LLMResponse(success=True, content="...")
        Factory-->>Agent: Response
    else Quota Error (429)
        Primary--XFactory: HTTP 429 Error
        Factory->>Factory: Detect quota error
        Factory->>Factory: _is_quota_error() = True
        Factory->>Factory: _handle_provider_error(error, is_quota=True)
        Factory->>Factory: _switch_to_fallback()
        Factory->>Factory: current_provider = ClaudeProvider
        
        Note over Factory: Attempt 2 with Claude
        Factory->>Fallback: generate_content(prompt)
        Fallback->>Fallback: Call Claude API
        
        alt Claude Success
            Fallback-->>Factory: LLMResponse(success=True, content="...")
            Factory-->>Agent: Response (from Claude)
        else Claude Also Fails
            Fallback--XFactory: Error
            Factory->>Retry: Exponential backoff
            
            loop Max 5 retries
                Retry->>Fallback: Retry after delay
                
                alt Retry succeeds
                    Fallback-->>Retry: Success
                    Retry-->>Factory: Response
                else Max retries exceeded
                    Retry--XFactory: All retries failed
                    Factory-->>Agent: LLMResponse(success=False, error="All providers failed")
                end
            end
        end
    else Other Error
        Primary--XFactory: Connection Error / Timeout
        Factory->>Retry: Exponential backoff (same provider)
        
        loop Max 5 retries
            Retry->>Primary: Retry after delay (2^attempt seconds)
            
            alt Retry succeeds
                Primary-->>Retry: Success
                Retry-->>Factory: Response
            else Max retries but should try fallback
                Retry->>Factory: Try fallback
                Factory->>Fallback: generate_content(prompt)
            end
        end
    end
```

## 6. Vector DB Search Flow

```mermaid
sequenceDiagram
    participant Agent as AgentService
    participant Vector as VectorStoreService
    participant Factory as VectorDBFactory
    participant Provider as PineconeProvider
    participant Embedder as Embedding Generator
    participant Pinecone as Pinecone API
    
    Agent->>Vector: similarity_search(query="how to return product?", k=3)
    Vector->>Factory: similarity_search(query, k=3, index_name)
    
    Factory->>Provider: similarity_search(query, k=3, index_name)
    
    Note over Provider: Step 1: Generate Query Embedding
    Provider->>Embedder: generate_embedding(query)
    Embedder->>Embedder: Call Gemini embedding-004
    Embedder-->>Provider: 768-dim query vector
    
    Note over Provider: Step 2: Query Pinecone
    Provider->>Pinecone: query(vector=query_vector, top_k=3)
    Pinecone->>Pinecone: Cosine similarity search
    Pinecone-->>Provider: matches (id, score, metadata)
    
    Note over Provider: Step 3: Format Results
    Provider->>Provider: Extract metadata.text from matches
    Provider-->>Factory: VectorDBResponse(success=True, data=[{text, score}])
    
    Factory-->>Vector: Response
    Vector-->>Agent: List[Dict[text, score]]
    
    Agent->>Agent: Format context for LLM prompt
```

## 7. Gmail Authentication Flow

```mermaid
sequenceDiagram
    participant App as Application
    participant Auth as GmailAuthService
    participant FS as File System
    participant Browser
    participant Google as Google OAuth
    
    App->>Auth: get_service()
    Auth->>Auth: _load_credentials()
    Auth->>FS: Read token.json
    
    alt Token exists and valid
        FS-->>Auth: Valid credentials
        Auth-->>App: Gmail API service
    else Token exists but expired
        FS-->>Auth: Expired credentials
        Auth->>Auth: _refresh_credentials(creds)
        Auth->>Google: Refresh token request
        Google-->>Auth: New access token
        Auth->>FS: Save updated token.json
        Auth-->>App: Gmail API service
    else No token exists
        Auth->>FS: Read credentials.json
        FS-->>Auth: Client credentials
        
        Auth->>Auth: _start_oauth_flow()
        Auth->>Browser: Open OAuth consent screen
        Browser->>Google: User authorizes app
        Google->>Browser: Authorization code
        Browser-->>Auth: Authorization code
        
        Auth->>Google: Exchange code for tokens
        Google-->>Auth: Access token + Refresh token
        
        Auth->>Auth: _save_credentials(creds)
        Auth->>FS: Save token.json
        Auth-->>App: Gmail API service
    end
```

## 8. Knowledge Base Pagination Flow

```mermaid
sequenceDiagram
    actor User
    participant Browser
    participant API as API Routes
    participant Vector as VectorStoreService
    participant VectorDB as VectorDBFactory
    participant Pinecone
    
    User->>Browser: Open /knowledge-base
    Browser->>API: GET /api/knowledge-base?limit=3
    
    API->>Vector: list_documents(limit=3, pagination_token=None)
    Vector->>VectorDB: list_documents(index_name, limit=3, token=None)
    VectorDB->>Pinecone: list(limit=3)
    Pinecone-->>VectorDB: {vectors: [...], pagination: {next: "token123"}}
    VectorDB-->>Vector: VectorDBResponse(data=[...], metadata={next_token: "token123"})
    Vector-->>API: {documents: [...], next_token: "token123"}
    
    API-->>Browser: JSON response
    Browser->>Browser: Display first 3 documents
    
    Note over User: Scroll down (infinite scroll)
    User->>Browser: Scroll trigger
    Browser->>API: GET /api/knowledge-base?limit=3&token=token123
    
    API->>Vector: list_documents(limit=3, pagination_token="token123")
    Vector->>VectorDB: list_documents(index_name, limit=3, token="token123")
    VectorDB->>Pinecone: list(limit=3, pagination_token="token123")
    Pinecone-->>VectorDB: {vectors: [...], pagination: {next: "token456"}}
    VectorDB-->>Vector: VectorDBResponse(data=[...], metadata={next_token: "token456"})
    Vector-->>API: {documents: [...], next_token: "token456"}
    
    API-->>Browser: JSON response
    Browser->>Browser: Append next 3 documents
    
    Note over Browser: Repeat until next_token is null
```

## 9. Multi-User Email Isolation

```mermaid
sequenceDiagram
    participant Agent1 as Agent Instance 1<br/>(user1@gmail.com)
    participant Agent2 as Agent Instance 2<br/>(user2@gmail.com)
    participant Gmail1 as Gmail API<br/>(user1)
    participant Gmail2 as Gmail API<br/>(user2)
    participant DB as DatabaseService
    
    Note over Agent1,Agent2: Both agents running concurrently
    
    Agent1->>Gmail1: get_current_email()
    Gmail1-->>Agent1: user1@gmail.com
    
    Agent2->>Gmail2: get_current_email()
    Gmail2-->>Agent2: user2@gmail.com
    
    Agent1->>Gmail1: get_unread_emails()
    Gmail1-->>Agent1: Emails for user1
    
    Agent2->>Gmail2: get_unread_emails()
    Gmail2-->>Agent2: Emails for user2
    
    Agent1->>DB: log_email(..., agent_email="user1@gmail.com")
    Agent2->>DB: log_email(..., agent_email="user2@gmail.com")
    
    Note over DB: Logs stored with agent_email for isolation
    
    Note over Agent1: Dashboard queries for user1
    Agent1->>DB: get_logs(agent_email="user1@gmail.com")
    DB-->>Agent1: Only user1's logs
    
    Note over Agent2: Dashboard queries for user2
    Agent2->>DB: get_logs(agent_email="user2@gmail.com")
    DB-->>Agent2: Only user2's logs
```

## Sequence Flow Summary

| Workflow | Primary Components | Key Interactions |
|----------|-------------------|------------------|
| **Email Processing** | Agent, Gmail, LLM, Vector DB, Database | Classify → RAG → Generate → Send → Log |
| **Web Auth & Routing** | Browser, auth.js, Flask, Session | Check Auth → Redirect → Initialize |
| **Dashboard Data Fetching** | dashboard.js, charts.js, API, Database | Fetch Metrics → Render Charts → Auto-refresh |
| **PDF Upload** | Browser, API, Ingestion, Vector DB | Upload → Validate → Process → Store → Respond |
| **LLM Fallback** | LLM Factory, Gemini, Claude | Primary → Detect Error → Switch → Retry |
| **Vector Search** | Vector Store, Pinecone, Embedder | Query → Embed → Search → Format |
| **Gmail Auth** | Auth Service, Google OAuth, File System | Load → Validate → Refresh/Authorize → Save |
| **KB Pagination** | Browser, API, Vector DB, Pinecone | Initial → Scroll → Load More → Append |
| **Multi-User Isolation** | Multiple Agents, Gmail APIs, Database | Concurrent Processing with User Segregation |

## Error Handling Patterns

### Pattern 1: Provider Fallback (LLM)
- Detect error type (quota vs. other)
- Switch to fallback provider if quota
- Retry with exponential backoff if transient
- Return error only if all options exhausted

### Pattern 2: Graceful Degradation
- If email processing fails, log error and continue
- If PDF ingestion fails, inform user but don't crash
- If vector search fails, generate response without context

### Pattern 3: Retry with Exponential Backoff
```
Delay = min(baseDelay * (2 ^ attemptNumber), maxDelay)
```
- Prevents overwhelming failed services
- Gives temporary issues time to resolve

## Further Reading

- [Architecture Overview](README.md)
- [High-Level Design](HIGH_LEVEL_DESIGN.md)
- [Multi-LLM Architecture](llm/README.md)
- [Multi-Vector DB Architecture](vector_db/README.md)
