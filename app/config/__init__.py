"""
Configuration module for the RAG Customer Support System.
"""
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """Application configuration."""
    
    # Google Gemini
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
    
    # Pinecone
    PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
    PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "customer-support-index")
    
    # Telegram
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    
    # Gmail
    GMAIL_CREDENTIALS_FILE = os.getenv("GMAIL_CREDENTIALS_FILE", "credentials.json")
    GMAIL_TOKEN_FILE = os.getenv("GMAIL_TOKEN_FILE", "token.json")

    # RAG Settings
    CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "1000"))
    CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "150"))
    EMBEDDING_MODEL = "models/embedding-001"
    CHAT_MODEL = "models/gemini-2.0-flash"  # Using valid available model
    
    # Pinecone Index Settings
    PINECONE_DIMENSION = int(os.getenv("PINECONE_DIMENSION", "768"))  # Gemini embedding dimension
    PINECONE_METRIC = os.getenv("PINECONE_METRIC", "cosine")
    PINECONE_CLOUD = os.getenv("PINECONE_CLOUD", "aws")
    PINECONE_REGION = os.getenv("PINECONE_REGION", "us-east-1")
    
    # Prompt Files
    AGENT_SYSTEM_PROMPT_FILE = os.getenv("AGENT_SYSTEM_PROMPT_FILE", "prompts/agent_system_prompt.txt")
    RETRIEVER_TOOL_DESC_FILE = os.getenv("RETRIEVER_TOOL_DESC_FILE", "prompts/retriever_tool_description.txt")
    EMAIL_CLASSIFICATION_PROMPT_FILE = os.getenv("EMAIL_CLASSIFICATION_PROMPT_FILE", "prompts/email_classification_prompt.txt")
    
    # Logging
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE = os.getenv("LOG_FILE", "logs/app.log")

    @staticmethod
    def validate():
        """Validate required configuration."""
        missing = []
        if not Config.GOOGLE_API_KEY:
            missing.append("GOOGLE_API_KEY")
        if not Config.PINECONE_API_KEY:
            missing.append("PINECONE_API_KEY")
        if not Config.TELEGRAM_BOT_TOKEN:
            missing.append("TELEGRAM_BOT_TOKEN")
        
        if missing:
            raise ValueError(f"Missing environment variables: {', '.join(missing)}")
        
        return True
