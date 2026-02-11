from fastapi import APIRouter
from app.api.v1.endpoints import admin, rag

api_router = APIRouter()
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
api_router.include_router(rag.router, prefix="/rag", tags=["rag"])
