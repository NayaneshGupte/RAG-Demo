# RAG Customer Support System

An intelligent customer support automation system using Retrieval-Augmented Generation (RAG) with Google Gemini and Pinecone.

## 🎯 Features

- **📄 Knowledge Base**: Web-based PDF upload and ingestion
- **🤖 AI-Powered Responses**: Automated email replies using RAG
- **🔍 Semantic Search**: Pinecone vector database for accurate retrieval
- **📧 Gmail Integration**: Automatic email monitoring and responses
- **🔐 Secure**: OAuth 2.0 authentication for Gmail

## 📚 Documentation Index

| Document | Description | Target Audience |
|----------|-------------|-----------------|
| **[User Guide (Walkthrough)](walkthrough.md)** | **Start Here!** Complete setup, installation, and usage guide. | Users |
| **[Code Walkthrough](code_walkthrough.md)** | Technical deep dive into the codebase and architecture. | Developers |
| **[Gmail Setup Guide](gmail_setup_guide.md)** | Step-by-step guide to get your `credentials.json`. | Users |
| **[PRD](PRD.md)** | Product Requirements Document. | Stakeholders |
| **[Prompts Guide](prompts/README.md)** | System prompts, including the **Master Prompt** to rebuild the app. | Developers |
| **[Trigger-Based Arch](TRIGGER_BASED_ARCHITECTURE.md)** | Design doc for future real-time implementation. | Architects |

## 🚀 Quick Start

1.  **Install Dependencies**: `pip install -r requirements.txt`
2.  **Setup**: Follow the **[User Guide](walkthrough.md)** to configure `.env` and Gmail.
3.  **Run Agent**: `python run.py agent`
4.  **Run Dashboard**: `python wsgi.py`


## 🛠️ Tech Stack

- **LLM**: Google Gemini (gemini-pro)
- **Embeddings**: Google Gemini Embeddings (models/embedding-001)
- **Vector DB**: Pinecone
- **Framework**: LangChain

- **Email**: Gmail API

## Demo Videos


https://github.com/user-attachments/assets/97c3da8f-53a3-40ea-b103-be73e20b46c4


https://github.com/user-attachments/assets/c42d6a63-6e20-4cfa-af7b-88b67e21cbc9


## 📝 License

MIT License
