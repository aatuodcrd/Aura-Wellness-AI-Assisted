from pydantic import BaseModel
import uuid
from typing import Optional

class TenantCreate(BaseModel):
    name: str

class TenantResponse(TenantCreate):
    id: uuid.UUID

class ProjectCreate(BaseModel):
    tenant_id: uuid.UUID
    name: str
    description: Optional[str] = None
    department: Optional[str] = None

class ProjectResponse(ProjectCreate):
    id: uuid.UUID

class UserCreate(BaseModel):
    tenant_id: uuid.UUID
    email: str
    full_name: str
    role: str = "employee"
    department: Optional[str] = None

class UserResponse(UserCreate):
    id: uuid.UUID
