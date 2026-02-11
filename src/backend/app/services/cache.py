import redis.asyncio as redis
import json
from app.core.config import settings

class CacheService:
    def __init__(self):
        self.redis = redis.from_url(settings.REDIS_URL, encoding="utf-8", decode_responses=True)
        self.ttl = 3600  # 1 hour cache

    async def get_cache(self, key: str):
        return await self.redis.get(key)

    async def set_cache(self, key: str, value: str):
        await self.redis.set(key, value, ex=self.ttl)

    def generate_key(self, tenant_id: str, project_id: str, query: str) -> str:
        return f"rag:{tenant_id}:{project_id}:{query}"

cache_service = CacheService()
