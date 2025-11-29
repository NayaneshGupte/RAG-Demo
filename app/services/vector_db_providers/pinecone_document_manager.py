import logging
from typing import List, Dict, Optional, Any
from langchain_core.documents import Document
from app.services.vector_db_providers.base import VectorDBResponse

logger = logging.getLogger(__name__)

class PineconeDocumentManager:
    """Handles document CRUD and search operations for Pinecone."""
    def __init__(self, pc_client, embeddings, index_name):
        self.pc_client = pc_client
        self.embeddings = embeddings
        self.index_name = index_name

    def add_documents(self, documents: List[Dict], index_name: Optional[str] = None) -> VectorDBResponse:
        try:
            if not self.pc_client:
                return VectorDBResponse(success=False, error="Pinecone client not initialized")
            if not index_name:
                index_name = self.index_name
            index = self.pc_client.Index(index_name)
            vectors = []
            for i, doc in enumerate(documents):
                if isinstance(doc, Document):
                    content = doc.page_content
                    metadata = doc.metadata or {}
                else:
                    content = doc.get('page_content', '')
                    metadata = doc.get('metadata', {})
                embedding = self.embeddings.embed_documents([content])[0]
                if all(v == 0.0 for v in embedding):
                    logger.warning(f"Skipping document {i} due to zero-vector embedding")
                    continue
                vectors.append({
                    'id': f'doc_{i}_{hash(content)}',
                    'values': embedding,
                    'metadata': {'text': content, **metadata}
                })
            batch_size = 100
            for i in range(0, len(vectors), batch_size):
                batch = vectors[i:i+batch_size]
                index.upsert(vectors=batch)
                logger.debug(f"Upserted batch {i//batch_size + 1} ({len(batch)} vectors)")
            logger.info(f"Successfully added {len(vectors)} documents to {index_name}")
            return VectorDBResponse(success=True, data=len(vectors), metadata={'index': index_name, 'vectors_added': len(vectors)})
        except Exception as e:
            logger.error(f"Error adding documents to Pinecone: {e}")
            return VectorDBResponse(success=False, error=str(e))

    def similarity_search(self, query: str, k: int = 3, index_name: Optional[str] = None) -> VectorDBResponse:
        try:
            if not self.pc_client:
                return VectorDBResponse(success=False, error="Pinecone client not initialized")
            if not index_name:
                index_name = self.index_name
            index = self.pc_client.Index(index_name)
            query_embedding = self.embeddings.embed_query(query)
            results = index.query(vector=query_embedding, top_k=k, include_metadata=True)
            docs = []
            for match in results.get('matches', []):
                metadata = match.get('metadata', {})
                text = metadata.get('text', '')
                docs.append(Document(page_content=text, metadata=metadata))
            logger.debug(f"Similarity search found {len(docs)} documents")
            return VectorDBResponse(success=True, data=docs, metadata={'index': index_name, 'query': query, 'results_count': len(docs)})
        except Exception as e:
            logger.error(f"Error in similarity search: {e}")
            return VectorDBResponse(success=False, error=str(e))

    def list_documents(self, index_name: Optional[str] = None, limit: int = 10, pagination_token: Optional[str] = None) -> VectorDBResponse:
        try:
            if not self.pc_client:
                return VectorDBResponse(success=False, error="Pinecone client not initialized")
            if not index_name:
                index_name = self.index_name
            index = self.pc_client.Index(index_name)
            list_args = {'limit': limit}
            if pagination_token:
                list_args['pagination_token'] = pagination_token
            results = index.list(**list_args)
            ids = []
            next_token = None
            try:
                for batch in results:
                    ids.extend(batch)
                    break
            except TypeError:
                if hasattr(results, 'vectors'):
                    ids = [v.id for v in results.vectors]
                if hasattr(results, 'pagination'):
                    next_token = results.pagination.next
            documents = []
            if ids:
                fetch_response = index.fetch(ids)
                for vector_id, vector_data in fetch_response.vectors.items():
                    metadata = vector_data.metadata or {}
                    text = metadata.get('text', '')
                    documents.append({'id': vector_id, 'text': text, 'metadata': metadata})
            logger.debug(f"Listed {len(documents)} documents from {index_name}")
            return VectorDBResponse(success=True, data=documents, metadata={'index': index_name, 'count': len(documents), 'next_token': next_token})
        except Exception as e:
            logger.error(f"Error listing documents: {e}")
            return VectorDBResponse(success=False, error=str(e))

    def delete_document(self, document_id: str, index_name: Optional[str] = None) -> VectorDBResponse:
        try:
            if not self.pc_client:
                return VectorDBResponse(success=False, error="Pinecone client not initialized")
            if not index_name:
                index_name = self.index_name
            index = self.pc_client.Index(index_name)
            index.delete(ids=[document_id])
            logger.info(f"Deleted document {document_id} from {index_name}")
            return VectorDBResponse(success=True, metadata={'index': index_name, 'document_id': document_id})
        except Exception as e:
            logger.error(f"Error deleting document: {e}")
            return VectorDBResponse(success=False, error=str(e))
