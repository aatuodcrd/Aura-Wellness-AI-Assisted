from pydantic import BaseModel
from typing import List, Optional
import uuid

class DocumentUpload(BaseModel):
    title: str
    content: str

class DocumentResponse(DocumentUpload):
    id: uuid.UUID
    project_id: uuid.UUID

class ChatRequest(BaseModel):
    user_id: uuid.UUID
    project_id: uuid.UUID
    question: str

class Source(BaseModel):
    title: str
    content: str

class ChatResponse(BaseModel):
    answer: str
    sources: List[Source]
