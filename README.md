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
| **[Setup Guide](docs/walkthroughs/setup/README.md)** | **Start Here!** Project setup and installation. | Users |
| **[Usage Guide](docs/walkthroughs/usage/README.md)** | How to use the system for ingestion/search/email. | Users |
| **[Troubleshooting](docs/walkthroughs/troubleshooting.md)** | Common issues and solutions. | Users |
| **[Architecture Overview](docs/architecture/README.md)** | High-level and component architecture. | Developers |
| **[Vector DB Architecture](docs/architecture/vector_db/README.md)** | Pluggable vector DB provider design. | Developers |
| **[LLM Architecture](docs/architecture/llm/README.md)** | LLM provider design. | Developers |
| **[Prompts Guide](docs/prompts/README.md)** | System prompts and templates. | Developers |
| **[Trigger-Based Arch](docs/architecture/trigger_based/README.md)** | Real-time event design. | Architects |

## 🚀 Quick Start

1.  **Install Dependencies**: `pip install -r requirements.txt`
2.  **Setup**: Follow the **[Setup Guide](docs/walkthroughs/setup/README.md)** to configure `.env` and Gmail.
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
