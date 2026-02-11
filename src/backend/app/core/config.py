from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    PROJECT_NAME: str = "Internal Knowledge Assistant"
    API_V1_STR: str = "/api/v1"
    
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "knowledge_db"
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@db:5432/knowledge_db"
    
    REDIS_URL: str = "redis://redis:6379/0"
    QDRANT_URL: str = "http://qdrant:6333"
    
    OPENAI_API_KEY: str

    # RAG Settings
    RAG_LLM_MODEL: str = "gpt-4o-mini"
    RAG_EMBEDDING_MODEL: str = "text-embedding-3-small"
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 200
    RAG_TOP_K: int = 3

    class Config:
        env_file = ".env"

settings = Settings()
