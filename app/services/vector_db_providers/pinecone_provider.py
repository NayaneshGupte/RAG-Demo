"""
Pinecone vector database provider.
Implements VectorDBProvider interface for Pinecone vector DB.
"""
import time
import logging
from typing import List, Dict, Optional, Any
import google.generativeai as genai
from langchain_core.embeddings import Embeddings
from langchain_core.documents import Document
from pinecone import Pinecone, ServerlessSpec
from app.services.vector_db_providers.pinecone_index_manager import PineconeIndexManager
from app.config import Config
from app.services.vector_db_providers.base import VectorDBProvider, VectorDBResponse
from app.services.vector_db_providers.pinecone_document_manager import PineconeDocumentManager

logger = logging.getLogger(__name__)


class GoogleGenAIEmbeddings(Embeddings):
    """Custom wrapper for Google Generative AI Embeddings to be compatible with LangChain."""
    
    def __init__(self, api_key, model_name="models/embedding-001"):
        genai.configure(api_key=api_key)
        self.model_name = model_name
        
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed a list of documents."""
        embeddings = []
        for text in texts:
            try:
                result = genai.embed_content(
                    model=self.model_name,
                    content=text,
                    task_type="retrieval_document"
                )
                embeddings.append(result['embedding'])
                time.sleep(1)  # Rate limit
            except Exception as e:
                logger.error(f"Error embedding document: {e}")
                embeddings.append([0.0] * 768)
        return embeddings

    def embed_query(self, text: str) -> List[float]:
        """Embed a query."""
        try:
            result = genai.embed_content(
                model=self.model_name,
                content=text,
                task_type="retrieval_query"
            )
            time.sleep(1)  # Rate limit
            return result['embedding']
        except Exception as e:
            logger.error(f"Error embedding query: {e}")
            return [0.0] * 768


class PineconeProvider(VectorDBProvider):
    """Pinecone vector database provider implementation."""
    
    def __init__(self):
        """Initialize Pinecone provider."""
        self.api_key = Config.PINECONE_API_KEY
        self.index_name = Config.PINECONE_INDEX_NAME
        self.dimension = Config.PINECONE_DIMENSION
        self.metric = Config.PINECONE_METRIC
        self.cloud = Config.PINECONE_CLOUD
        self.region = Config.PINECONE_REGION
        self.embedding_model = Config.EMBEDDING_MODEL

        self.pc_client = None
        self.embeddings = None
        self.index_manager = None
    self.document_manager = None
    self._initialized = False
    logger.info("PineconeProvider initialized")
    
    def validate_credentials(self) -> bool:
        """Validate Pinecone credentials."""
        try:
            if not self.api_key:
                logger.error("PINECONE_API_KEY not configured")
                return False
            
            # Try to create client
            pc = Pinecone(api_key=self.api_key)
            logger.info("Pinecone credentials validated successfully")
            return True
        except Exception as e:
            logger.error(f"Pinecone credential validation failed: {e}")
            return False
    
    def is_available(self) -> bool:
        """Check if Pinecone is available."""
        try:
            if not self.pc_client:
                return False
            # Try to list indexes
            self.pc_client.list_indexes()
            logger.debug("Pinecone is available")
            return True
        except Exception as e:
            logger.error(f"Pinecone availability check failed: {e}")
            return False
    
    def initialize(self) -> bool:
        """Initialize Pinecone provider."""
        try:
            if not self.validate_credentials():
                return False

            # Initialize embeddings
            if not Config.GOOGLE_API_KEY:
                logger.error("GOOGLE_API_KEY not set for embeddings")
                return False

            self.embeddings = GoogleGenAIEmbeddings(
                api_key=Config.GOOGLE_API_KEY,
                model_name=self.embedding_model
            )

            # Initialize Pinecone client
            self.pc_client = Pinecone(api_key=self.api_key)

            # Initialize index manager
            self.index_manager = PineconeIndexManager(
                pc_client=self.pc_client,
                default_dimension=self.dimension,
                metric=self.metric,
                cloud=self.cloud,
                region=self.region
            )

            # Initialize document manager
            self.document_manager = PineconeDocumentManager(
                pc_client=self.pc_client,
                embeddings=self.embeddings,
                index_name=self.index_name
            )
            logger.info("PineconeProvider initialized successfully")
            self._initialized = True
            return True
        except Exception as e:
            logger.error(f"PineconeProvider initialization failed: {e}")
            return False
    
    def get_or_create_index(self, index_name: str, dimension: Optional[int] = None) -> bool:
        """Get existing index or create new one (delegated to PineconeIndexManager)."""
        if not self._initialized or not self.index_manager:
            logger.error("PineconeProvider not initialized")
            return False
        return self.index_manager.get_or_create_index(index_name, dimension)
    
    def add_documents(self, documents: List[Dict], index_name: str) -> VectorDBResponse:
        """Add documents to Pinecone (delegated to PineconeDocumentManager)."""
        if not self._initialized or not self.document_manager:
            return VectorDBResponse(success=False, error="PineconeProvider not initialized")
        return self.document_manager.add_documents(documents, index_name)
    
    def similarity_search(self, query: str, k: int = 3, index_name: Optional[str] = None) -> VectorDBResponse:
        """Search for similar documents in Pinecone (delegated to PineconeDocumentManager)."""
        if not self._initialized or not self.document_manager:
            return VectorDBResponse(success=False, error="PineconeProvider not initialized")
        return self.document_manager.similarity_search(query, k, index_name)
    
    def get_index_stats(self, index_name: Optional[str] = None) -> VectorDBResponse:
        """Get Pinecone index statistics."""
        try:
            if not self._initialized or not self.pc_client:
                return VectorDBResponse(
                    success=False,
                    error="PineconeProvider not initialized"
                )
            
            if not index_name:
                index_name = self.index_name
            
            index = self.pc_client.Index(index_name)
            stats = index.describe_index_stats()
            
            logger.debug(f"Retrieved stats for index {index_name}")
            return VectorDBResponse(
                success=True,
                data=stats,
                metadata={'index': index_name}
            )
        except Exception as e:
            logger.error(f"Error getting index stats: {e}")
            return VectorDBResponse(success=False, error=str(e))
    
    def list_documents(self, index_name: Optional[str] = None, limit: int = 10, pagination_token: Optional[str] = None) -> VectorDBResponse:
        """List documents in Pinecone index (delegated to PineconeDocumentManager)."""
        if not self._initialized or not self.document_manager:
            return VectorDBResponse(success=False, error="PineconeProvider not initialized")
        return self.document_manager.list_documents(index_name, limit, pagination_token)
    
    def delete_document(self, document_id: str, index_name: Optional[str] = None) -> VectorDBResponse:
        """Delete a document from Pinecone (delegated to PineconeDocumentManager)."""
        if not self._initialized or not self.document_manager:
            return VectorDBResponse(success=False, error="PineconeProvider not initialized")
        return self.document_manager.delete_document(document_id, index_name)
    
    def get_provider_name(self) -> str:
        """Get provider name."""
        return "pinecone"
    
    def get_provider_status(self) -> Dict[str, Any]:
        """Get Pinecone provider status."""
        try:
            if not self._initialized or not self.pc_client:
                return {
                    'name': 'pinecone',
                    'status': 'not_initialized',
                    'available': False
                }
            
            indexes = [idx.name for idx in self.pc_client.list_indexes()]
            
            return {
                'name': 'pinecone',
                'status': 'initialized',
                'available': True,
                'default_index': self.index_name,
                'indexes': indexes,
                'dimension': self.dimension,
                'metric': self.metric,
                'region': self.region
            }
        except Exception as e:
            logger.error(f"Error getting provider status: {e}")
            return {
                'name': 'pinecone',
                'status': 'error',
                'available': False,
                'error': str(e)
            }
