# Flux - AI Email Automation Walkthrough

This guide provides a complete walkthrough for setting up, running, and using the Flux AI Email Automation system.

## 📋 Prerequisites

- **Python 3.12+** installed
- **Gmail Account** with API access
- **API Keys**:
  - Google Gemini API key
  - Pinecone API key
  - (Optional) Anthropic Claude API key for fallback

## 🚀 Installation

### 1. Clone Repository
```bash
git clone https://github.com/NayaneshGupte/RAG-Demo.git
cd RAG-Demo
```

### 2. Create Virtual Environment
```bash
python3.12 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

## ⚙️ Configuration

### 1. Environment Variables

Create a `.env` file in the project root:

```env
# LLM Configuration
GOOGLE_API_KEY=your_gemini_api_key
ANTHROPIC_API_KEY=your_claude_api_key     # Optional fallback
LLM_PRIMARY_PROVIDER=gemini
LLM_FALLBACK_PROVIDERS=claude

# Vector Database
PINECONE_API_KEY=your_pinecone_api_key
PINECONE_INDEX_NAME=your_index_name
VECTOR_DB_TYPE=pinecone

# Web Application
SECRET_KEY=your_secret_key_for_sessions

# Document Processing
CHUNK_SIZE=1000
CHUNK_OVERLAP=150
```

### 2. Gmail OAuth Setup

Follow the **[OAuth Setup Guide](../guides/OAUTH_SETUP.md)** to:
1. Create a Google Cloud project
2. Enable Gmail API
3. Download `credentials.json`
4. Place `credentials.json` in the project root

**Important**: The first time you log in via the web interface, you'll be redirected to Google OAuth consent screen. After authorization, a `token.json` file will be created automatically.

## 🏃‍♂️ Running the System

The system consists of two main components that run concurrently:

### 1. Start the Web Application

```bash
source venv/bin/activate
python wsgi.py
```

**Access the application**: [http://127.0.0.1:5001](http://127.0.0.1:5001)

This will show the **Landing Page** with:
- Features showcase
- "How It Works" link
- "Connect Gmail" button for authentication

### 2. Start the Email Agent

In a **separate terminal**:

```bash
source venv/bin/activate
python run.py agent --poll-interval 60
```

The agent will:
- Poll for new emails every 60 seconds
- Process customer support inquiries
- Generate and send automated responses
- Log all activities to the database

## 🔐 Authentication Flow

### First-Time Setup

1. **Open Dashboard**: Navigate to [http://127.0.0.1:5001](http://127.0.0.1:5001)
2. **Landing Page**: You'll see the unauthenticated landing page
3. **Connect Gmail**: Click the "Connect Gmail" button
4. **OAuth Flow**: 
   - Redirected to Google OAuth consent screen
   - Authorize Flux to access your Gmail account
   - Redirected back to Dashboard upon success
5. **Dashboard Access**: Now you can access [http://127.0.0.1:5001/dashboard](http://127.0.0.1:5001/dashboard)

### Subsequent Logins

- **Automatic Redirect**: If you visit `/`, you'll be automatically redirected to `/dashboard` when authenticated
- **Session-Based**: Your session persists until you logout or clear cookies

### Demo Mode (Testing)

For testing without Gmail OAuth:

```bash
# Visit: http://127.0.0.1:5001/auth/demo/login
```

This creates a demo session with email `demo@example.com`.

## 💡 Usage Walkthrough

### Scenario: Customer Support Auto-Response

#### Step 1: Add Knowledge Base Content

1. **Navigate to Knowledge Base**:
   - From Dashboard, click "Knowledge Base" in the sidebar
   - Or visit: [http://127.0.0.1:5001/knowledge-base](http://127.0.0.1:5001/knowledge-base)

2. **Upload PDF**:
   - Click "Select PDF" or drag-and-drop a file
   - Example: "Product_Return_Policy.pdf"
   - Click "Upload & Ingest"
   - Wait for success message: "✅ Ingested X chunks"

3. **Verify Upload**:
   - Browse uploaded documents in the Knowledge Base viewer
   - Check "Total Knowledge Chunks" count on Dashboard

#### Step 2: Customer Sends Email

A customer sends an email to your Gmail account:

**From**: customer@example.com  
**Subject**: Need help with product return  
**Body**: 
```
Hi,

I received my order yesterday, but the product is defective. 
How can I return it and get a refund?

Thanks,
John
```

#### Step 3: Agent Processes Email

The agent (running in background) automatically:

1. **Detects** new unread email
2. **Classifies** it as "Customer Support Inquiry"
3. **Retrieves** relevant context from Knowledge Base (RAG):
   - Searches for "return" and "refund" policies
   - Finds top 3 relevant chunks from uploaded PDFs
4. **Generates** response using Gemini (or Claude if quota exceeded)
5. **Sends** threaded reply to customer
6. **Marks** email as read
7. **Logs** activity to database

#### Step 4: Monitor Activity

1. **View Dashboard**: [http://127.0.0.1:5001/dashboard](http://127.0.0.1:5001/dashboard)

2. **Key Metrics** (updated every 30 seconds):
   - Total Processed: 1
   - Responded: 1
   - Ignored: 0

3. **Agent Status**:
   - 🟢 Agent Running
   - Uptime: 2h 15m
   - Last Poll: 5 seconds ago

4. **Email Volume Chart**:
   - Interactive ApexCharts line chart
   - Filter by date range (Today, 7D, 1M, 3M, etc.)
   - See email processing trends

5. **Recent Activity** page:
   - Navigate to [http://127.0.0.1:5001/recent-activity](http://127.0.0.1:5001/recent-activity)
   - View detailed log entry:
     - Email Time: 2025-11-30 14:23:15
     - Response Time: 2025-11-30 14:23:22
     - Status: RESPONDED
     - Customer: customer@example.com
     - Subject: Need help with product return
     - Category: Customer Support Inquiry

## 🎨 Dashboard Features

### Landing Page (`/`)
- Modern, visually appealing design
- Features showcase with glassmorphism effects
- "How It Works" link to workflow explanation
- "Connect Gmail" authentication button

### Dashboard (`/dashboard`)
- **Real-Time Metrics**: Auto-refresh every 30 seconds
- **ApexCharts Visualizations**:
  - Email volume line chart
  - Category distribution donut chart
- **Agent Status Indicator**: Running/Stopped with pulse animation
- **Date Range Selector**: Flatpickr integration for custom ranges

### Knowledge Base (`/knowledge-base`)
- Browse uploaded PDF documents
- Infinite scroll pagination (3 documents per load)
- Chunk preview with metadata

### Recent Activity (`/recent-activity`)
- Comprehensive activity logs
- Filter by status: All, Responded, Ignored, Failed
- Pagination support
- Search and date range filtering

### How It Works (`/how-it-works`)
- Step-by-step workflow explanation
- Visual screenshots of each step
- Feature highlights

## 🛡️ Key Features

### Multi-LLM Fallback
- **Primary**: Google Gemini (gemini-1.5-flash)
- **Fallback**: Anthropic Claude (claude-3-5-sonnet)
- **Automatic Switching**: On quota errors (HTTP 429)
- **Exponential Backoff**: For transient errors

### User Isolation
- **Session-Based Auth**: Each user sees only their data
- **Database Filtering**: All queries filtered by `agent_email`
- **Multi-User Support**: Multiple agents can run concurrently

### Separated Architecture
- **Landing Page** (`/`): Public, unauthenticated
- **Dashboard** (`/dashboard`): Protected, requires authentication
- **Client-Side Routing**: `auth.js` manages redirects automatically

## 🧹 Maintenance

### Reset Database

To clear all email logs:

```bash
rm email_logs.db
```

*The database will be recreated automatically on next run.*

### Logout

Click "Logout" in the dashboard sidebar to:
- Clear session
- Redirect to landing page
- Require re-authentication

### Re-authenticate Gmail

If your `token.json` expires or is deleted:
1. Delete `token.json`
2. Navigate to Dashboard
3. Click "Connect Gmail"
4. Complete OAuth flow again

## 🔧 Troubleshooting

### Agent Not Processing Emails
- **Check Agent Status**: Verify "Agent Running" on dashboard
- **Check Logs**: Review terminal output for errors
- **Verify Gmail Authentication**: Ensure `token.json` exists and is valid

### Dashboard Shows Blank Page
- **Clear Browser Cache**: Hard refresh with Ctrl+Shift+R (Cmd+Shift+R on Mac)
- **Check Console**: Open browser DevTools → Console for JavaScript errors
- **Verify Port**: Ensure Flask is running on [http://127.0.0.1:5001](http://127.0.0.1:5001)

### PDF Upload Fails
- **Check File Type**: Only PDF files are supported
- **Check File Size**: Very large PDFs may take longer to process
- **Check Logs**: Review terminal output for processing errors

## 📚 Further Reading

- [OAuth Setup Guide](../guides/OAUTH_SETUP.md) - Detailed Gmail OAuth configuration
- [Gmail Setup Guide](../guides/gmail_setup_guide.md) - Gmail API setup
- [Architecture Overview](../architecture/README.md) - System architecture
- [Code Walkthrough](code_walkthrough.md) - Critical code flows
- [PRD](../PRD.md) - Product requirements and specifications

---

**Need Help?** Check the troubleshooting section or review the comprehensive documentation in the `docs/` directory.
