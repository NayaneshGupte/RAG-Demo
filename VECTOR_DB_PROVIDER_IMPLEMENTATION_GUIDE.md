# Adding New Vector Database Providers - Step-by-Step Guide

## Quick Start: Add a New Provider in 5 Steps

This guide shows you how to add support for a new vector database (e.g., Weaviate, Chroma, Milvus) to the application.

---

## Step 1: Study the Provider Interface

First, understand what methods your provider must implement:

**File:** `app/services/vector_db_providers/base.py`

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

@dataclass
class VectorDBResponse:
    """Standardized response from vector DB operations"""
    success: bool
    data: Any = None
    error: str = None
    metadata: Dict[str, Any] = None

class VectorDBProvider(ABC):
    """Abstract base class all vector DB providers must implement"""
    
    @abstractmethod
    def validate_credentials(self) -> bool:
        """Check if credentials are valid"""
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if provider is currently available"""
    
    @abstractmethod
    def initialize(self) -> VectorDBResponse:
        """Initialize the provider, create indexes, etc."""
    
    @abstractmethod
    def get_or_create_index(self, index_name: str) -> VectorDBResponse:
        """Create index if it doesn't exist, or get existing index"""
    
    @abstractmethod
    def add_documents(self, documents: List[Dict], index_name: str) -> VectorDBResponse:
        """Add documents to index. Returns count of added documents"""
    
    @abstractmethod
    def similarity_search(self, query: str, index_name: str, k: int = 5) -> VectorDBResponse:
        """Search for similar documents. Returns list of documents with scores"""
    
    @abstractmethod
    def get_index_stats(self, index_name: str) -> VectorDBResponse:
        """Get statistics about the index"""
    
    @abstractmethod
    def list_documents(self, index_name: str, limit: int = 100, offset: int = 0) -> VectorDBResponse:
        """List documents in index with pagination"""
    
    @abstractmethod
    def delete_document(self, doc_id: str, index_name: str) -> VectorDBResponse:
        """Delete a document from the index"""
    
    @abstractmethod
    def get_provider_name(self) -> str:
        """Return the name of this provider (e.g., 'pinecone')"""
    
    @abstractmethod
    def get_provider_status(self) -> Dict[str, Any]:
        """Return status information about the provider"""
```

**Key Points:**
- ✅ All methods must return `VectorDBResponse`
- ✅ `VectorDBResponse.success` indicates success/failure
- ✅ On error, set `success=False` and populate `error` field
- ✅ On success, set `success=True` and populate `data` field

---

## Step 2: Create Your Provider Implementation

Create a new file: `app/services/vector_db_providers/[provider_name]_provider.py`

### Example: Weaviate Provider

**File:** `app/services/vector_db_providers/weaviate_provider.py`

```python
import logging
from typing import Any, Dict, List, Optional
from app.services.vector_db_providers.base import VectorDBProvider, VectorDBResponse
from app.config import Config

logger = logging.getLogger(__name__)

class WeaviateProvider(VectorDBProvider):
    """Weaviate vector database provider."""
    
    def __init__(self):
        """Initialize Weaviate provider."""
        self.url = Config.WEAVIATE_URL or "http://localhost:8080"
        self.api_key = Config.WEAVIATE_API_KEY
        self.client = None
        self._initialized = False
    
    def validate_credentials(self) -> bool:
        """Validate Weaviate credentials."""
        try:
            if not self.url:
                logger.warning("WEAVIATE_URL not configured")
                return False
            
            logger.info(f"Validating Weaviate credentials for {self.url}")
            # Try importing client and testing connection
            import weaviate
            client = weaviate.Client(
                url=self.url,
                auth_client_secret=weaviate.auth.AuthApiKey(api_key=self.api_key) if self.api_key else None
            )
            
            # Test connection
            result = client.schema.get()
            logger.info("✓ Weaviate credentials validated")
            return True
            
        except Exception as e:
            logger.error(f"✗ Weaviate validation failed: {str(e)}")
            return False
    
    def is_available(self) -> bool:
        """Check if Weaviate is available."""
        try:
            if not self.client:
                return False
            
            # Try a simple health check
            import weaviate
            ready = self.client.is_ready()
            return ready
            
        except Exception as e:
            logger.warning(f"Weaviate availability check failed: {str(e)}")
            return False
    
    def initialize(self) -> VectorDBResponse:
        """Initialize Weaviate provider."""
        try:
            logger.info("Initializing Weaviate provider...")
            
            # Validate credentials first
            if not self.validate_credentials():
                return VectorDBResponse(
                    success=False,
                    error="Invalid Weaviate credentials"
                )
            
            # Import and create client
            import weaviate
            import weaviate.auth
            
            auth = None
            if self.api_key:
                auth = weaviate.auth.AuthApiKey(api_key=self.api_key)
            
            self.client = weaviate.Client(url=self.url, auth_client_secret=auth)
            
            # Check connection
            if not self.client.is_ready():
                raise Exception("Weaviate is not ready")
            
            self._initialized = True
            logger.info("✓ Weaviate provider initialized")
            
            return VectorDBResponse(
                success=True,
                data={"status": "initialized"},
                metadata={"provider": "weaviate", "url": self.url}
            )
            
        except Exception as e:
            logger.error(f"✗ Weaviate initialization failed: {str(e)}")
            return VectorDBResponse(
                success=False,
                error=f"Initialization failed: {str(e)}"
            )
    
    def get_or_create_index(self, index_name: str) -> VectorDBResponse:
        """Get or create a Weaviate class."""
        try:
            if not self._initialized:
                raise Exception("Provider not initialized")
            
            class_name = index_name.upper()
            
            # Check if class exists
            schema = self.client.schema.get()
            existing_classes = [c["class"] for c in schema.get("classes", [])]
            
            if class_name in existing_classes:
                logger.info(f"Using existing Weaviate class: {class_name}")
                return VectorDBResponse(
                    success=True,
                    data={"class": class_name, "created": False}
                )
            
            # Create new class
            logger.info(f"Creating Weaviate class: {class_name}")
            class_obj = {
                "class": class_name,
                "description": f"Documents for {index_name}",
                "vectorizer": "text2vec-openai",  # or other vectorizer
                "properties": [
                    {
                        "name": "content",
                        "dataType": ["text"],
                        "description": "Document content"
                    },
                    {
                        "name": "metadata",
                        "dataType": ["text"],
                        "description": "Document metadata"
                    }
                ]
            }
            
            self.client.schema.create_class(class_obj)
            logger.info(f"✓ Created Weaviate class: {class_name}")
            
            return VectorDBResponse(
                success=True,
                data={"class": class_name, "created": True}
            )
            
        except Exception as e:
            logger.error(f"✗ Failed to get/create index: {str(e)}")
            return VectorDBResponse(
                success=False,
                error=f"Failed to get/create index: {str(e)}"
            )
    
    def add_documents(self, documents: List[Dict], index_name: str) -> VectorDBResponse:
        """Add documents to Weaviate."""
        try:
            if not self._initialized:
                raise Exception("Provider not initialized")
            
            class_name = index_name.upper()
            
            # Prepare batch
            with self.client.batch as batch:
                batch.batch_size = 100
                
                for i, doc in enumerate(documents):
                    # Extract content and metadata
                    content = doc.get("content", "")
                    metadata = doc.get("metadata", {})
                    
                    # Create object
                    obj = {
                        "content": content,
                        "metadata": str(metadata)
                    }
                    
                    # Add to batch
                    batch.add_data_object(
                        data_object=obj,
                        class_name=class_name
                    )
            
            logger.info(f"✓ Added {len(documents)} documents to {class_name}")
            
            return VectorDBResponse(
                success=True,
                data=len(documents),
                metadata={"added": len(documents), "class": class_name}
            )
            
        except Exception as e:
            logger.error(f"✗ Failed to add documents: {str(e)}")
            return VectorDBResponse(
                success=False,
                error=f"Failed to add documents: {str(e)}"
            )
    
    def similarity_search(self, query: str, index_name: str, k: int = 5) -> VectorDBResponse:
        """Search for similar documents in Weaviate."""
        try:
            if not self._initialized:
                raise Exception("Provider not initialized")
            
            class_name = index_name.upper()
            
            # Perform search
            where_filter = {
                "path": ["content"],
                "operator": "Like",
                "valueString": f"*{query}*"
            }
            
            result = (
                self.client.query
                .get(class_name, ["content", "metadata", "_additional {certainty}"])
                .with_where(where_filter)
                .with_limit(k)
                .do()
            )
            
            # Extract documents
            documents = []
            if "data" in result and "Get" in result["data"]:
                for obj in result["data"]["Get"].get(class_name, []):
                    documents.append({
                        "content": obj.get("content", ""),
                        "metadata": obj.get("metadata", "{}"),
                        "score": obj.get("_additional", {}).get("certainty", 0)
                    })
            
            logger.info(f"Found {len(documents)} similar documents")
            
            return VectorDBResponse(
                success=True,
                data=documents,
                metadata={"query": query, "count": len(documents), "class": class_name}
            )
            
        except Exception as e:
            logger.error(f"✗ Similarity search failed: {str(e)}")
            return VectorDBResponse(
                success=False,
                error=f"Similarity search failed: {str(e)}"
            )
    
    def get_index_stats(self, index_name: str) -> VectorDBResponse:
        """Get statistics about a Weaviate class."""
        try:
            if not self._initialized:
                raise Exception("Provider not initialized")
            
            class_name = index_name.upper()
            
            # Get class statistics
            result = (
                self.client.query
                .aggregate(class_name)
                .with_meta_count()
                .do()
            )
            
            count = 0
            if "data" in result and "Aggregate" in result["data"]:
                meta = result["data"]["Aggregate"][class_name][0]
                count = meta.get("meta", {}).get("count", 0)
            
            return VectorDBResponse(
                success=True,
                data={
                    "index_name": index_name,
                    "document_count": count,
                    "status": "active"
                }
            )
            
        except Exception as e:
            logger.error(f"✗ Failed to get index stats: {str(e)}")
            return VectorDBResponse(
                success=False,
                error=f"Failed to get index stats: {str(e)}"
            )
    
    def list_documents(self, index_name: str, limit: int = 100, offset: int = 0) -> VectorDBResponse:
        """List documents in a Weaviate class."""
        try:
            if not self._initialized:
                raise Exception("Provider not initialized")
            
            class_name = index_name.upper()
            
            # Query documents with pagination
            result = (
                self.client.query
                .get(class_name, ["content", "metadata"])
                .with_limit(limit)
                .with_offset(offset)
                .do()
            )
            
            documents = []
            if "data" in result and "Get" in result["data"]:
                for obj in result["data"]["Get"].get(class_name, []):
                    documents.append({
                        "content": obj.get("content", ""),
                        "metadata": obj.get("metadata", "{}")
                    })
            
            return VectorDBResponse(
                success=True,
                data=documents,
                metadata={"limit": limit, "offset": offset, "count": len(documents)}
            )
            
        except Exception as e:
            logger.error(f"✗ Failed to list documents: {str(e)}")
            return VectorDBResponse(
                success=False,
                error=f"Failed to list documents: {str(e)}"
            )
    
    def delete_document(self, doc_id: str, index_name: str) -> VectorDBResponse:
        """Delete a document from Weaviate."""
        try:
            if not self._initialized:
                raise Exception("Provider not initialized")
            
            class_name = index_name.upper()
            
            # Delete document by UUID
            self.client.data_object.delete(uuid=doc_id, class_name=class_name)
            
            logger.info(f"✓ Deleted document {doc_id}")
            
            return VectorDBResponse(
                success=True,
                data={"deleted": True}
            )
            
        except Exception as e:
            logger.error(f"✗ Failed to delete document: {str(e)}")
            return VectorDBResponse(
                success=False,
                error=f"Failed to delete document: {str(e)}"
            )
    
    def get_provider_name(self) -> str:
        """Return provider name."""
        return "weaviate"
    
    def get_provider_status(self) -> Dict[str, Any]:
        """Return provider status."""
        return {
            "name": "weaviate",
            "available": self.is_available(),
            "initialized": self._initialized,
            "url": self.url,
            "has_api_key": bool(self.api_key)
        }
```

---

## Step 3: Add Configuration Variables

Update `app/config/__init__.py` to add provider-specific configuration:

```python
# Weaviate Configuration
WEAVIATE_URL = os.getenv("WEAVIATE_URL", "http://localhost:8080")
WEAVIATE_API_KEY = os.getenv("WEAVIATE_API_KEY")
```

---

## Step 4: Register the Provider

Update `app/services/vector_db_providers/factory.py` to register your provider:

Add this at the end of the file:

```python
# Import and register Weaviate provider
try:
    from app.services.vector_db_providers.weaviate_provider import WeaviateProvider
    VectorDBFactory.register_provider('weaviate', WeaviateProvider)
    logger.info("✓ Weaviate provider registered")
except ImportError:
    logger.warning("Weaviate provider not available")
except Exception as e:
    logger.warning(f"Failed to register Weaviate provider: {e}")
```

---

## Step 5: Use Your New Provider

### Option A: Set Environment Variable

```bash
export VECTOR_DB_TYPE=weaviate
export WEAVIATE_URL=http://localhost:8080
```

Then use as normal:
```python
from app.services.vector_store_service import VectorStoreService

vector_store = VectorStoreService()
docs = vector_store.similarity_search("query")
```

### Option B: Specify at Runtime

```python
from app.services.vector_store_service import VectorStoreService

vector_store = VeaviateService(vector_db_type="weaviate")
docs = vector_store.similarity_search("query")
```

### Option C: Use Factory Directly

```python
from app.services.vector_db_providers import VectorDBFactory

factory = VectorDBFactory(primary_provider="weaviate")
response = factory.similarity_search("query", k=5)

if response.success:
    print(f"Found {len(response.data)} documents")
else:
    print(f"Error: {response.error}")
```

---

## Complete Checklist: Adding a New Provider

- [ ] **Study Interface** - Review all 11 methods in `VectorDBProvider` base class
- [ ] **Create File** - Create `[provider_name]_provider.py` in `app/services/vector_db_providers/`
- [ ] **Implement Interface** - Implement all 11 abstract methods
- [ ] **Add Configuration** - Add environment variables to `app/config/__init__.py`
- [ ] **Import Dependencies** - Add provider library to `requirements.txt`
- [ ] **Register Provider** - Add registration code to `factory.py`
- [ ] **Test Credentials** - Verify provider can connect with test credentials
- [ ] **Test Operations** - Test add_documents, similarity_search, get_stats
- [ ] **Test Errors** - Verify error handling for invalid inputs
- [ ] **Document** - Update documentation with new provider details
- [ ] **Commit** - Git commit with clear message

---

## Common Implementation Patterns

### Pattern 1: Initialization with Lazy Loading

```python
def __init__(self):
    self.client = None
    self._initialized = False

def initialize(self):
    # Only create client when needed
    self.client = create_client(...)
    self._initialized = True
```

### Pattern 2: Error Handling with VectorDBResponse

```python
def some_operation(self):
    try:
        # Do operation
        result = perform_operation()
        return VectorDBResponse(success=True, data=result)
    except SpecificError as e:
        logger.error(f"Specific error: {e}")
        return VectorDBResponse(success=False, error=str(e))
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return VectorDBResponse(success=False, error="Unknown error")
```

### Pattern 3: Credential Validation

```python
def validate_credentials(self) -> bool:
    try:
        # Test connection with provided credentials
        test_client = create_test_client(
            api_key=self.api_key,
            url=self.url
        )
        # Try a simple operation
        test_client.health_check()
        return True
    except Exception as e:
        logger.warning(f"Credential validation failed: {e}")
        return False
```

### Pattern 4: Metadata Preservation

```python
def add_documents(self, documents: List[Dict], index_name: str) -> VectorDBResponse:
    added = 0
    for doc in documents:
        # Extract and preserve metadata
        content = doc.get("content", "")
        metadata = doc.get("metadata", {})
        
        # Add to provider
        provider_doc = {
            "content": content,
            "metadata": json.dumps(metadata)  # Store as JSON string
        }
        # ... add to provider
        added += 1
    
    return VectorDBResponse(success=True, data=added)
```

---

## Example: Quick Chroma Provider Skeleton

```python
# File: app/services/vector_db_providers/chroma_provider.py

from app.services.vector_db_providers.base import VectorDBProvider, VectorDBResponse
import logging

logger = logging.getLogger(__name__)

class ChromaProvider(VectorDBProvider):
    """Chroma vector database provider."""
    
    def __init__(self):
        self.persist_directory = Config.CHROMA_PATH or "./chroma_db"
        self.client = None
        self._initialized = False
    
    def validate_credentials(self) -> bool:
        # Chroma doesn't require credentials
        return True
    
    def initialize(self) -> VectorDBResponse:
        try:
            import chromadb
            self.client = chromadb.PersistentClient(path=self.persist_directory)
            self._initialized = True
            return VectorDBResponse(success=True, data={"status": "initialized"})
        except Exception as e:
            return VectorDBResponse(success=False, error=str(e))
    
    # ... implement remaining methods
```

---

## Troubleshooting

### Import Errors
**Problem:** `ModuleNotFoundError: No module named 'provider_lib'`
**Solution:** Add provider library to `requirements.txt` and reinstall

### Credentials Invalid
**Problem:** `Provider validation failed`
**Solution:** Check environment variables are set correctly

### Provider Not Found
**Problem:** `Provider 'xyz' not registered`
**Solution:** Verify registration code is in `factory.py` and module imports correctly

---

## Next Steps

1. ✅ Create your provider implementation
2. ✅ Test with configuration
3. ✅ Add to documentation
4. ✅ Commit and push
5. ✅ Create PR for review

**Questions?** Check the existing `PineconeProvider` for reference implementation.

---

**Last Updated:** After Vector DB Provider Architecture Implementation  
**Status:** ✅ Production Ready
