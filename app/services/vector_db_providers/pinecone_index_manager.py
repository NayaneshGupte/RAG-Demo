import logging
from typing import Optional, List
from pinecone import Pinecone, ServerlessSpec
from app.config import Config

logger = logging.getLogger(__name__)

class PineconeIndexManager:
    """Handles Pinecone index creation, listing, and stats."""
    def __init__(self, pc_client: Pinecone, default_dimension: int, metric: str, cloud: str, region: str):
        self.pc_client = pc_client
        self.default_dimension = default_dimension
        self.metric = metric
        self.cloud = cloud
        self.region = region

    def get_or_create_index(self, index_name: str, dimension: Optional[int] = None) -> bool:
        try:
            existing_indexes = [idx.name for idx in self.pc_client.list_indexes()]
            if index_name not in existing_indexes:
                logger.info(f"Creating new Pinecone index: {index_name}")
                if not dimension:
                    dimension = self.default_dimension
                self.pc_client.create_index(
                    name=index_name,
                    dimension=dimension,
                    metric=self.metric,
                    spec=ServerlessSpec(cloud=self.cloud, region=self.region)
                )
                logger.info(f"Index {index_name} created successfully")
            else:
                logger.info(f"Using existing Pinecone index: {index_name}")
            return True
        except Exception as e:
            logger.error(f"Error creating/getting index {index_name}: {e}")
            return False

    def list_indexes(self) -> List[str]:
        try:
            return [idx.name for idx in self.pc_client.list_indexes()]
        except Exception as e:
            logger.error(f"Error listing indexes: {e}")
            return []

    def describe_index(self, index_name: str) -> dict:
        try:
            index = self.pc_client.Index(index_name)
            return index.describe_index_stats()
        except Exception as e:
            logger.error(f"Error describing index {index_name}: {e}")
            return {}
