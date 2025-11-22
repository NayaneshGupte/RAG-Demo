# Code Walkthrough - AI Customer Support Agent

This document provides a technical deep dive into the codebase of the RAG-based Customer Support Agent.

## 📂 Project Structure

```
RAG Demo/
├── app/
│   ├── api/                      # API Blueprint
│   │   ├── __init__.py
│   │   └── routes.py
│   ├── web/                      # Web Blueprint
│   │   ├── __init__.py
│   │   └── routes.py
│   ├── services/                 # Core business logic
│   │   ├── agent_service.py
│   │   ├── gmail_service.py
│   │   ├── database_service.py
│   │   ├── vector_store_service.py
│   │   └── ingestion_service.py
│   ├── static/                   # Static assets
│   │   ├── css/
│   │   └── js/
│   ├── templates/                # HTML templates
│   │   ├── dashboard.html
│   │   └── knowledge_base.html
│   ├── utils/                    # Helper utilities
│   ├── config/                   # Configuration
│   └── __init__.py               # App Factory
├── wsgi.py                       # Production entry point
├── run.py                        # CLI entry point
├── requirements.txt              # Dependencies
└── email_logs.db                 # SQLite database
```

## 🧩 Key Components

### 1. Agent Service (`app/services/agent_service.py`)
The brain of the application. It coordinates the entire email processing flow.
-   **`process_emails()`**: The main loop. Fetches unread emails using `GmailService`.
-   **`should_process_email()`**: Uses Gemini to classify if an email is a customer inquiry.
-   **`generate_response()`**:
    1.  Generates embeddings for the email query.
    2.  Retrieves relevant documents from Pinecone via `VectorStoreService`.
    3.  Constructs a prompt with the retrieved context.
    4.  Generates a response using Gemini (or Claude Sonnet fallback).
-   **`_retry_with_backoff()`**: Handles API rate limits with exponential backoff and model fallback.

### 2. Gmail Service (`app/services/gmail_service.py`)
Handles all interactions with the Gmail API.
-   **`get_unread_emails(after_timestamp)`**: Fetches unread emails, filtering by timestamp to ignore old messages.
-   **`send_reply()`**: Sends a reply, ensuring proper threading headers (`In-Reply-To`, `References`) are set.
-   **`mark_as_read()`**: Marks processed emails as read to prevent re-processing.

### 3. Database Service (`app/services/database_service.py`)
Manages the SQLite database for logging and dashboard data.
-   **Schema**: `email_logs` table stores sender, subject, status (`RESPONDED`, `IGNORED`, `ERROR`), details, and timestamps.
-   **`log_email()`**: Records processing events.
-   **`get_logs()`**: Retrieves logs for the dashboard, supporting filtering.

### 4. Vector Store Service (`app/services/vector_store_service.py`)
Manages the Knowledge Base.
-   **`initialize_vector_store()`**: Connects to Pinecone.
-   **`add_documents()`**: Embeds text using Gemini and upserts vectors to Pinecone.
-   **`similarity_search()`**: Finds relevant documents for a given query.

### 5. Dashboard (Blueprints: `app/web` & `app/api`)
A Flask-based web interface organized into Blueprints.
-   **`app/web`**: Serves HTML pages (`/`, `/knowledge-base`).
-   **`app/api`**: Serves JSON endpoints (`/api/logs`, `/api/upload`).
-   **Frontend**: Uses centralized static assets (`style.css`, `main.js`).

## 🔄 Data Flow

1.  **Ingestion**: PDF Upload (Dashboard) -> `IngestionService` -> Text Splitter -> Embeddings -> Pinecone.
2.  **Trigger**: `run.py agent` starts the polling loop.
3.  **Detection**: `GmailService` finds a new email.
4.  **Classification**: `AgentService` asks LLM: "Is this a support query?"
5.  **Retrieval**: If yes, `VectorStoreService` finds relevant knowledge.
6.  **Generation**: LLM generates a response using the email + knowledge.
7.  **Action**: `GmailService` sends the reply.
8.  **Logging**: `DatabaseService` records the outcome.
9.  **Monitoring**: User views the result on the Dashboard.

## 🛡️ Resilience Features

-   **Model Fallback**: If Gemini API hits a rate limit (`429`), the system automatically switches to **Claude 3 Sonnet** (via Anthropic API) to ensure continuity.
-   **Timestamp Filtering**: The agent records its start time and only processes emails received *after* that time, preventing it from churning through old inbox clutter.
-   **User Isolation**: The system identifies the authenticated Gmail user and tags all logs with their email, ensuring the dashboard only shows data relevant to the current user.
