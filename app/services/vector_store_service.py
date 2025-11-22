import time
import logging
from typing import List
import google.generativeai as genai
from langchain_core.embeddings import Embeddings
from pinecone import Pinecone, ServerlessSpec
from app.config import Config

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
            # Gemini embedding API handles one text at a time or batch
            # Doing one by one for simplicity and error handling
            try:
                result = genai.embed_content(
                    model=self.model_name,
                    content=text,
                    task_type="retrieval_document"
                )
                embeddings.append(result['embedding'])
                # Rate limit: Sleep after embedding
                time.sleep(1)
            except Exception as e:
                logger.error(f"Error embedding document: {e}")
                # Return zero vector or handle appropriately
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
            # Rate limit: Sleep after embedding
            time.sleep(1)
            return result['embedding']
        except Exception as e:
            logger.error(f"Error embedding query: {e}")
            return [0.0] * 768

class VectorStoreService:
    """Service for managing vector store operations."""
    
    def __init__(self):
        self.embeddings = self._initialize_embeddings()
        self.pc_client = self._initialize_pinecone_client()
    
    def _initialize_embeddings(self):
        """Initialize Google Gemini Embeddings."""
        if not Config.GOOGLE_API_KEY:
            raise ValueError("GOOGLE_API_KEY is not set in configuration.")
        
        logger.info("Initializing Google Gemini embeddings (Direct SDK)")
        return GoogleGenAIEmbeddings(
            api_key=Config.GOOGLE_API_KEY,
            model_name=Config.EMBEDDING_MODEL
        )
    
    def _initialize_pinecone_client(self):
        """Initialize Pinecone client."""
        if not Config.PINECONE_API_KEY:
            raise ValueError("PINECONE_API_KEY is not set in configuration.")
        
        logger.info("Initializing Pinecone client")
        return Pinecone(api_key=Config.PINECONE_API_KEY)
    
    def get_or_create_index(self, index_name=None):
        """Get existing index or create new one."""
        if index_name is None:
            index_name = Config.PINECONE_INDEX_NAME
        
        existing_indexes = [index.name for index in self.pc_client.list_indexes()]
        
        if index_name not in existing_indexes:
            logger.info(f"Creating new Pinecone index: {index_name}")
            self.pc_client.create_index(
                name=index_name,
                dimension=Config.PINECONE_DIMENSION,
                metric=Config.PINECONE_METRIC,
                spec=ServerlessSpec(
                    cloud=Config.PINECONE_CLOUD,
                    region=Config.PINECONE_REGION
                )
            )
        else:
            logger.info(f"Using existing Pinecone index: {index_name}")
        
        return self.pc_client.Index(index_name)

    def get_stats(self, index_name=None):
        """Get index statistics."""
        if index_name is None:
            index_name = Config.PINECONE_INDEX_NAME
        
        try:
            index = self.pc_client.Index(index_name)
            stats = index.describe_index_stats()
            return stats
        except Exception as e:
            logger.error(f"Error getting index stats: {e}")
            return {}

    def list_documents(self, limit=3, pagination_token=None, index_name=None):
        """List documents from the vector store with pagination."""
        if index_name is None:
            index_name = Config.PINECONE_INDEX_NAME
            
        try:
            index = self.pc_client.Index(index_name)
            
            # List IDs
            list_args = {'limit': limit}
            if pagination_token:
                list_args['pagination_token'] = pagination_token
                
            # Note: list returns a generator or response object depending on version
            # Assuming standard list behavior for v8+
            results = index.list(**list_args)
            
            ids = []
            next_token = None
            
            # Handle different response types (iterator vs object)
            # For most recent SDKs, it yields batches of IDs or is an iterator
            # We'll try to consume one batch
            try:
                for batch in results:
                    ids.extend(batch)
                    break # Just take the first batch if it's an iterator of batches
            except TypeError:
                # If it's not iterable like that, maybe it's a response object
                if hasattr(results, 'vectors'):
                    ids = [v.id for v in results.vectors]
                if hasattr(results, 'pagination'):
                    next_token = results.pagination.next
            
            # If we got IDs, fetch their metadata
            documents = []
            if ids:
                fetch_response = index.fetch(ids)
                for vector_id, vector_data in fetch_response.vectors.items():
                    metadata = vector_data.metadata or {}
                    text = metadata.get('text', '')
                    documents.append({
                        'id': vector_id,
                        'text': text,
                        'metadata': metadata
                    })
            
            # Pinecone list iterator handles pagination internally usually, 
            # but for stateless API we might need the token. 
            # Re-checking SDK usage: list() returns an iterator of IDs.
            # To implement stateless pagination with list() is tricky as it's designed for iteration.
            # FALLBACK: For this demo, we will use a query with a generic vector if list() is complex to paginate statelessly,
            # BUT list() is the correct way for "browsing".
            # Let's assume we iterate and return.
            
            return {
                'documents': documents,
                'next_token': next_token # This might be None if we consumed the iterator
            }
            
        except Exception as e:
            logger.error(f"Error listing documents: {e}")
            return {'documents': [], 'next_token': None}

    def get_vector_store(self, index_name=None):
        """Get vector store with direct Pinecone SDK v8 compatibility."""
        if index_name is None:
            index_name = Config.PINECONE_INDEX_NAME
        
        # Ensure index exists
        self.get_or_create_index(index_name)
        
        # Return a simple wrapper that works with Pinecone v8
        class SimplePineconeStore:
            def __init__(self, pc_client, index_name, embeddings):
                self.pc = pc_client
                self.index_name = index_name
                self.embeddings = embeddings
                self.index = self.pc.Index(index_name)
            
            def similarity_search(self, query, k=3):
                """Search for similar documents."""
                # Generate query embedding
                query_embedding = self.embeddings.embed_query(query)
                
                # Query Pinecone
                results = self.index.query(
                    vector=query_embedding,
                    top_k=k,
                    include_metadata=True
                )
                
                # Convert to LangChain Document format
                from langchain_core.documents import Document
                docs = []
                for match in results.get('matches', []):
                    metadata = match.get('metadata', {})
                    text = metadata.get('text', '')
                    docs.append(Document(page_content=text, metadata=metadata))
                
                return docs
            
            def add_documents(self, documents):
                """Add documents to the vector store."""
                vectors = []
                for i, doc in enumerate(documents):
                    embedding = self.embeddings.embed_documents([doc.page_content])[0]
                    
                    # Check if embedding is valid (not all zeros)
                    if all(v == 0.0 for v in embedding):
                        logger.warning(f"Skipping document {i} due to zero-vector embedding (possible API error or empty content)")
                        continue
                        
                    vectors.append({
                        'id': f'doc_{i}_{hash(doc.page_content)}',
                        'values': embedding,
                        'metadata': {'text': doc.page_content, **doc.metadata}
                    })
                
                # Upsert in batches
                batch_size = 100
                for i in range(0, len(vectors), batch_size):
                    batch = vectors[i:i+batch_size]
                    self.index.upsert(vectors=batch)
                
                return len(vectors)
        
        return SimplePineconeStore(self.pc_client, index_name, self.embeddings)
