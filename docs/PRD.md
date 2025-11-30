# Product Requirements Document (PRD)
## AI Customer Support Agent & Dashboard

**Version:** 2.0  
**Date:** November 30, 2025  
**Status:** Implemented

---

## 1. Executive Summary
The **AI Customer Support Agent** is an intelligent automation system designed to monitor a Gmail inbox, classify incoming customer inquiries, and generate context-aware responses using a Retrieval-Augmented Generation (RAG) pipeline. It includes a web-based **Dashboard** for real-time monitoring, statistics, and knowledge base management.

The system aims to reduce manual support workload by automatically handling routine queries while ensuring high accuracy and reliability through multi-model fallback strategies.

---

## 2. User Stories

### 2.1 Customer Support Manager
- **As a Manager**, I want to **upload PDF product manuals** via a web interface so that the AI has the latest information to answer customer queries.
- **As a Manager**, I want to **monitor the agent's activity** (responded, ignored, failed emails) on a dashboard to ensure it is performing correctly.
- **As a Manager**, I want to see **key statistics** (total emails, response count) to gauge the system's impact.

### 2.2 System Administrator
- **As an Admin**, I want the system to **automatically handle API rate limits** by switching to a backup model (Claude Sonnet) so that service is not interrupted.
- **As an Admin**, I want the agent to **only process new emails** that arrive after it starts, avoiding the reprocessing of old backlog.
- **As an Admin**, I want detailed **logs of errors and ignored emails** to troubleshoot issues effectively.

### 2.3 End User (Customer)
- **As a Customer**, I want to receive a **helpful, accurate reply** to my email query within minutes.
- **As a Customer**, I want the reply to be **threaded** to my original email so I can easily follow the conversation.

---

## 3. Functional Requirements

### 3.1 Email Processing Engine
- **Inbox Monitoring**: The system must poll the Gmail inbox at a configurable interval (default: 60s).
- **New Email Filtering**: The system must strictly process only emails received *after* the agent's start time.
- **Classification**:
    - Use an LLM to classify emails as "Customer Support Inquiry" or "Other".
    - **Include**: Explicitly handle follow-up emails and replies (starting with "Re:") as valid inquiries.
    - **Exclude**: Ignore emails from specific domains (e.g., `@phonepe.com`) or non-support categories (spam, promotions).
- **RAG Response Generation**:
    - Retrieve relevant context from the Pinecone vector database based on the email query.
    - Generate a response using **Google Gemini** (primary model).
    - **Fallback**: If Gemini fails (e.g., rate limit 429), automatically retry using **Claude 3 Sonnet**.
- **Email Sending**:
    - Send replies via Gmail API.
    - **Threading**: Must set `In-Reply-To` and `References` headers to maintain email threads.
    - Mark processed emails as "Read".

### 3.2 Knowledge Base Ingestion
- **Web Upload**: Provide a drag-and-drop or file selection interface on the Dashboard for PDF files.
- **Processing**:
    - Extract text from uploaded PDFs.
    - Split text into chunks (size: 1000 chars, overlap: 150 chars).
    - **Validation**: Filter out empty or whitespace-only chunks.
    - **Zero-Vector Guard**: Skip chunks that generate invalid (zero) embeddings.
- **Storage**: Generate embeddings using Gemini and upsert them to the Pinecone vector database.

### 3.3 Web Application & Dashboard
- **Separated Architecture**:
    - **Landing Page** (`/`): Unauthenticated landing page with features showcase and "Connect Gmail" button.
    - **Dashboard** (`/dashboard`): Protected dashboard requiring authentication.
    - **Client-Side Routing**: `auth.js` handles automatic redirects based on session status.
    - **How It Works Page** (`/how-it-works`): Public page explaining system workflow.
- **Authentication**:
    - Gmail OAuth 2.0 with session-based auth.
    - Demo mode support for testing (`/auth/demo/login`).
    - Secure logout with session cleanup.
- **Real-Time Analytics**:
    - **ApexCharts Integration**: Interactive line charts for email volume, donut charts for category distribution.
    - **Date Range Selection**: Flatpickr integration for custom date ranges (Today, 7D, 1M, 3M, 6M, 12M, Custom).
    - **Auto-Refresh**: Dashboard updates every 30 seconds via `dashboard.js`.
- **Dashboard Components**:
    - Agent status indicator (running/stopped with pulse animation).
    - Key metrics cards: Total Processed, Responded, Ignored.
    - Email volume chart with time series data.
    - Category distribution donut chart.
- **Knowledge Base Management**:
    - Dedicated page (`/knowledge-base`) to browse ingested documents.
    - **Web Upload**: Drag-and-drop PDF upload interface.
    - **Pagination**: Infinite scroll with 3 documents per page load.
    - **Stats**: Live counter of "Total Knowledge Chunks" displayed on dashboard.
- **Recent Activity**:
    - Dedicated activity logs page (`/recent-activity`).
    - Filter by status: All, Responded, Ignored, Failed.
    - Pagination with date range filtering.
- **User Isolation**: Ensure data and logs are scoped to the currently authenticated Gmail user.

---

## 4. Non-Functional Requirements

### 4.1 Performance & Reliability
- **Latency**: Email processing and response generation should typically complete within 30 seconds.
- **Resilience**: The system must handle API errors gracefully (exponential backoff) and not crash on malformed inputs (e.g., empty PDFs).

### 4.2 Security
- **Authentication**: Use OAuth 2.0 for Gmail access. Store credentials securely (`token.json`).
- **Data Privacy**: Only access and process emails relevant to the authenticated user.

### 4.3 Usability
- **Dashboard UI**: Clean, modern interface using CSS variables for easy theming.
- **Feedback**: Provide immediate visual feedback for file uploads (Success/Error messages).

---

## 5. Technical Architecture

### 5.1 Tech Stack
- **Language**: Python 3.12+
- **Backend Framework**: Flask with Application Factory pattern
  - **Blueprints**: `api_bp` (REST API), `web_bp` (Web pages), `auth_bp` (Authentication)
- **Frontend**: 
  - HTML5, CSS3 with modern design (Glassmorphism, gradients)
  - Vanilla JavaScript (no framework dependencies)
  - **ApexCharts**: Interactive charts
  - **Flatpickr**: Date range picker
- **Database**: SQLite (for operation logs: `email_logs.db`)
- **Vector Database**: Pinecone (Serverless)

### 5.2 External APIs
- **Google Gemini API**: Embeddings (`embedding-004`) and Chat (`gemini-1.5-flash`).
- **Anthropic API**: Fallback Chat (`claude-3-5-sonnet-20241022`).
- **Gmail API**: Email reading, sending, and OAuth authentication.

### 5.3 Key Components
| Component | Responsibility |
|-----------|----------------|
| `AgentService` | Orchestrates fetching, classification, RAG, and response generation. |
| `GmailService` | Facade for Gmail API interactions (auth, reading, sending, modifying). |
| `LLMFactory` | Multi-provider LLM system with automatic fallback (Gemini → Claude). |
| `VectorStoreService` | Simplified interface to vector database operations. |
| `VectorDBFactory` | Abstraction layer for vector database providers. |
| `IngestionService` | Processes PDFs and updates the vector store via web upload. |
| `DatabaseService` | Manages SQLite logs with user isolation. |
| **Frontend JavaScript** | |
| `auth.js` | Handles authentication flow, session checks, and page redirects. |
| `dashboard.js` | Manages dashboard data fetching and metric updates. |
| `charts.js` | Initializes and manages ApexCharts visualizations. |
| `date-range-manager.js` | Handles date range selection and persistence. |

---

## 6. Implemented Features (v2.0)
- ✅ Separated Landing and Dashboard pages with client-side routing
- ✅ ApexCharts integration for real-time analytics
- ✅ Flatpickr date range selection
- ✅ Multi-LLM fallback system (Gemini → Claude)
- ✅ Multi-Vector DB abstraction layer
- ✅ Web-based PDF upload (removed Telegram dependency)
- ✅ Demo authentication mode
- ✅ Session-based user isolation
- ✅ Auto-refresh dashboard (30s intervals)

## 7. Future Roadmap (Out of Scope for v2.0)
- Support for multiple file formats (DOCX, TXT, CSV).
- User feedback mechanism (Thumbs up/down on AI responses).
- Multi-turn conversation memory (currently handles single-turn replies).
- Email templates and customizable response prompts.
- Advanced analytics (sentiment analysis, response time trends).
- Scheduled reports and email digests.
