from qdrant_client import QdrantClient
from qdrant_client.http import models
from app.core.config import settings

class VectorService:
    def __init__(self):
        self.client = QdrantClient(url=settings.QDRANT_URL)
        self.embedding_size = 1536  # OpenAI text-embedding-3-small dimension

    def _get_collection_name(self, tenant_id: str, project_id: str) -> str:
        """Constructs the namespace-isolated collection name."""
        return f"{tenant_id}_{project_id}"

    def ensure_collection_exists(self, tenant_id: str, project_id: str):
        """Creates the collection if it doesn't exist."""
        collection_name = self._get_collection_name(tenant_id, project_id)
        if not self._collection_exists(collection_name):
            self.client.create_collection(
                collection_name=collection_name,
                vectors_config=models.VectorParams(
                    size=self.embedding_size,
                    distance=models.Distance.COSINE
                )
            )

    def upsert_vectors(self, tenant_id: str, project_id: str, vectors: list, payloads: list, ids: list):
        """Upserts vectors into the specific tenant-project collection."""
        collection_name = self._get_collection_name(tenant_id, project_id)
        self.ensure_collection_exists(tenant_id, project_id)
        
        self.client.upsert(
            collection_name=collection_name,
            points=models.Batch(
                ids=ids,
                vectors=vectors,
                payloads=payloads
            )
        )

    def search(self, tenant_id: str, project_id: str, query_vector: list, limit: int = 5):
        """Searches for similar vectors in the specific tenant-project collection."""
        collection_name = self._get_collection_name(tenant_id, project_id)
        
        # If collection doesn't exist, return empty list
        if not self._collection_exists(collection_name):
            return []

        return self.client.search(
            collection_name=collection_name,
            query_vector=query_vector,
            limit=limit
        )

    def delete_vectors_by_doc_id(self, tenant_id: str, project_id: str, doc_id: str):
        """Deletes vectors associated with a specific document ID."""
        collection_name = self._get_collection_name(tenant_id, project_id)
        if not self._collection_exists(collection_name):
            return

        self.client.delete(
            collection_name=collection_name,
            points_selector=models.FilterSelector(
                filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="doc_id",
                            match=models.MatchValue(value=doc_id)
                        )
                    ]
                )
            )
        )

    def _collection_exists(self, collection_name: str) -> bool:
        """Compatibility helper for older qdrant-client versions."""
        collections = self.client.get_collections().collections
        return any(c.name == collection_name for c in collections)

vector_service = VectorService()
