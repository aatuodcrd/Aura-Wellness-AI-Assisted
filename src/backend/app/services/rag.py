from app.services.cache import cache_service
from app.services.vector import vector_service
from app.core.config import settings
from langchain_openai import OpenAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from typing import List, Dict
import json
import asyncio

class RagService:
    def __init__(self):
        self.embeddings = OpenAIEmbeddings(
            model=settings.RAG_EMBEDDING_MODEL,
            api_key=settings.OPENAI_API_KEY
        )
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.CHUNK_SIZE,
            chunk_overlap=settings.CHUNK_OVERLAP,
            length_function=len
        )

    async def ingest_document(self, tenant_id: str, project_id: str, doc_id: str, content: str, title: str):
        """
        Chunks, embeds, and upserts a document into the vector database.
        """
        import uuid
        
        # 1. Chunking
        chunks = self.text_splitter.split_text(content)
        
        # 2. Prepare Payloads
        vectors = await self.embeddings.aembed_documents(chunks)
        
        ids = []
        payloads = []
        # vectors list is already ready
        
        for i, chunk in enumerate(chunks):
            # Generate deterministic UUID for the chunk to ensure idempotency
            chunk_uuid = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{doc_id}_{i}"))
            ids.append(chunk_uuid)
            payloads.append({
                "doc_id": doc_id,
                "content": chunk,
                "title": title,
                "chunk_index": i
            })
            
        # 3. Upsert to Qdrant
        vector_service.ensure_collection_exists(tenant_id, project_id)
        
        vector_service.upsert_vectors(
            tenant_id=tenant_id,
            project_id=project_id,
            ids=ids,
            vectors=vectors,
            payloads=payloads
        )

    async def retrieve(self, tenant_id: str, project_id: str, query: str, limit: int = 5) -> List[Dict]:
        """
        Retrieves relevant context for a query.
        """
        # 0. Check Cache
        cache_key = cache_service.generate_key(tenant_id, project_id, query)
        cached_data = await cache_service.get_cache(cache_key)
        if cached_data:
             return json.loads(cached_data)

        # 1. Embed Query
        query_vector = await self.embeddings.aembed_query(query)
        
        # 2. Search in Vector DB
        results = vector_service.search(
            tenant_id=tenant_id,
            project_id=project_id,
            query_vector=query_vector,
            limit=limit
        )
        
        # 3. Format Results
        context = []
        for hit in results:
            context.append({
                "content": hit.payload["content"],
                "title": hit.payload["title"],
                "score": hit.score
            })
            
        # 4. Set Cache
        if context:
            await cache_service.set_cache(cache_key, json.dumps(context))

        return context

rag_service = RagService()
