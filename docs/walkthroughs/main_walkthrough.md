# AI Customer Support Agent - Walkthrough

This guide provides a complete walkthrough for setting up, running, and using the AI Customer Support Agent.

## 📋 Prerequisites


## 🚀 Installation

1.  **Clone the repository** (if not already done).
2.  **Create a virtual environment**:
    ```bash
    python3.12 -m venv venv
    source venv/bin/activate
    ```
3.  **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

## ⚙️ Configuration

1.  **Environment Variables**:
    Ensure your `.env` file is configured with the following keys:
    ```env
    GOOGLE_API_KEY=your_gemini_api_key
    PINECONE_API_KEY=your_pinecone_api_key
    PINECONE_ENV=your_pinecone_env
    TELEGRAM_TOKEN=your_telegram_bot_token
    ANTHROPIC_API_KEY=your_anthropic_api_key  # For fallback model
    ```

2.  **Gmail Authentication**:
    - Follow the [Gmail Setup Guide](../guides/gmail_setup_guide.md) to generate your `credentials.json`.
    - Place `credentials.json` in the root directory.
    - The first time you run the agent, a browser window will open to authenticate with your Gmail account.
    - A `token.json` file will be created automatically to store the session.


## 🏃‍♂️ Running the System

The system consists of two main components: the **Agent** (backend) and the **Dashboard** (frontend).

### 1. Start the AI Agent
The agent monitors your inbox, processes new emails, and sends replies.

```bash
source venv/bin/activate
python run.py agent --poll-interval 60
```
*The agent will poll for new emails every 60 seconds.*

### 2. Start the Dashboard
The dashboard provides a real-time view of email processing, logs, and statistics.

```bash
source venv/bin/activate
python wsgi.py
```
*Access the dashboard at: [http://127.0.0.1:5000](http://127.0.0.1:5000)*

### 3. Knowledge Base Ingestion
To add new knowledge to the system, use the **Web Dashboard**:

1.  Open the Dashboard: [http://127.0.0.1:5000](http://127.0.0.1:5000)
2.  Locate the **Knowledge Base Ingestion** card.
3.  Click **Select PDF** to choose a file.
4.  Click **Upload & Ingest** to process it.

## 💡 Usage Walkthrough

### Scenario: Customer Support Auto-Response

1.  **Knowledge Base Update**:
    - Upload a PDF (e.g., "Product Manual.pdf") via the Dashboard.
    - The system ingests the content and stores it in the Vector Database.

2.  **Customer Inquiry**:
    - A customer sends an email to your monitored Gmail account (e.g., `nayanesh.gupte@gmail.com`).
    - **Subject**: "Issue with my order"
    - **Body**: "I received a defective product. How can I return it?"

3.  **Agent Processing**:
    - The Agent detects the **new** unread email.
    - It classifies the email (e.g., "Returns & Refunds").
    - It retrieves relevant policies from the Knowledge Base (RAG).
    - It generates a helpful, grounded response using Gemini (or Claude Sonnet if quota is hit).

4.  **Automated Reply**:
    - The Agent sends a reply **threaded** to the original email.
    - The email is marked as "Read" in Gmail.

5.  **Monitoring**:
    - Open the **Dashboard** ([http://127.0.0.1:5000](http://127.0.0.1:5000)).
    - You will see the email listed under **Recent Activity**.
    - **Status**: `RESPONDED`
    - **Details**: "Successfully replied"
    - **Timestamps**: View exact "Email Time" and "Response Time".

## 🛡️ Features


## 🧹 Maintenance

  ```bash
  rm email_logs.db
  ```
  *The database will be recreated automatically on the next run.*
