# Comprehensive Prompt: Build RAG Customer Support Agent

**Role**: You are an expert AI Engineer and Full-Stack Developer.
**Objective**: Build a production-grade **AI Customer Support Agent** that monitors a Gmail inbox, answers customer queries using RAG (Retrieval-Augmented Generation), and provides a real-time Web Dashboard.

**Context**: I have the following API keys available in my environment: `GOOGLE_API_KEY`, `PINECONE_API_KEY`, `ANTHROPIC_API_KEY`, and `GMAIL_CREDENTIALS` (OAuth).

---

## 1. Core Requirements

### A. Email Processing (The Agent)
1.  **Polling**: Create a CLI command (`python run.py agent`) that polls Gmail every 60 seconds.
2.  **Filtering**: Only process *new* emails received after the agent started. Ignore emails from specific domains (e.g., `@phonepe.com`) or spam.
3.  **Classification**: Use **Google Gemini** to classify emails as "Customer Support" or "Other".
    *   *Critical*: Explicitly include follow-up emails (starting with "Re:") as valid inquiries.
4.  **RAG Pipeline**:
    *   Generate embeddings for the query using **Gemini Embeddings**.
    *   Retrieve relevant context from **Pinecone**.
    *   Generate a response using **Gemini Pro**.
5.  **Resilience & Fallback**:
    *   Implement **Exponential Backoff** for API calls.
    *   **Fallback Mechanism**: If Gemini hits a rate limit (429), automatically switch to **Claude 3 Sonnet** (Anthropic) to generate the response.
6.  **Action**: Send the reply via Gmail API, ensuring proper threading (`In-Reply-To` headers), and mark the email as "Read".

### B. Knowledge Base (Ingestion)
1.  **Web Upload**: Create a feature in the Dashboard to upload PDF files.
2.  **Processing**:
    *   Extract text from PDFs.
    *   Split into chunks (1000 chars, 150 overlap).
    *   Filter out empty/whitespace-only chunks.
    *   Generate embeddings and upsert to Pinecone.
    *   *Guard*: Skip chunks that produce zero-vector embeddings.

### C. Web Dashboard (Flask)
1.  **Structure**: Use a **Production-Grade** folder structure with **Blueprints** and **Application Factory** pattern.
    *   `app/__init__.py`: `create_app()` factory.
    *   `app/api/`: JSON API routes (`/api/logs`, `/api/upload`).
    *   `app/web/`: HTML UI routes.
    *   `app/static/`: Separate `css/style.css` and `js/main.js`.
2.  **Features**:
    *   **Recent Activity**: Table showing Email Time, Response Time, Status (Responded/Ignored/Failed), and Subject.
    *   **Statistics**: Cards for Total Processed, Responded, Ignored.
    *   **Knowledge Base Viewer**: A page (`/knowledge-base`) to view ingested chunks with **Pagination** (3 items/page) and **Infinite Scroll**.
    *   **KB Stats**: Show "Total Knowledge Chunks" count on the dashboard.
3.  **Real-Time**: Auto-refresh data every 30 minutes; update "Last Updated" timer every minute.

---

## 2. Technical Architecture & File Structure

Please generate the following file structure:

```text
RAG Demo/
├── app/
│   ├── api/                  # API Blueprint
│   ├── web/                  # Web Blueprint
│   ├── services/             # Business Logic
│   │   ├── agent_service.py  # Orchestration & Fallback Logic
│   │   ├── gmail_service.py  # Gmail API Wrapper
│   │   ├── vector_store_service.py # Pinecone Logic
│   │   ├── ingestion_service.py    # PDF Processing
│   │   └── database_service.py     # SQLite Logging
│   ├── static/               # CSS & JS
│   ├── templates/            # HTML (Dashboard & KB Viewer)
│   ├── config/               # Config Class
│   └── __init__.py           # App Factory
├── wsgi.py                   # Web Entry Point
├── run.py                    # CLI Entry Point (Agent)
├── requirements.txt          # Dependencies
└── README.md                 # Documentation
```

## 3. Specific Implementation Details

*   **`agent_service.py`**: Must contain the `_retry_with_backoff` decorator that handles the switch from Gemini to Claude.
*   **`gmail_service.py`**: Must handle OAuth 2.0 flow using `credentials.json` and store `token.json`.
*   **`dashboard.html`**: Use a clean, modern UI with a "Stats Grid" and "Logs Table". Use the `fetch` API to load data from `/api/logs`.
*   **`knowledge_base.html`**: Implement the infinite scroll logic using a `Load More` button that triggers the next page fetch.

## 4. Documentation

Generate a comprehensive **README.md** that includes:
1.  **Quick Start**: How to install dependencies and run `python wsgi.py` (Dashboard) and `python run.py agent` (Agent).
2.  **Tech Stack**: List Python, Flask, Pinecone, Gemini, Claude.
3.  **Documentation Index**: Link to `walkthrough.md`, `code_walkthrough.md`, and `PRD.md` (create placeholders for these).

---

**Action**: Please start by setting up the project structure and installing dependencies, then proceed to implement the Core Services followed by the Dashboard.
