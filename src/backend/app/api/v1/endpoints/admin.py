from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db
from app.db import models
from app.schemas import admin as schemas
import uuid
from typing import Optional

router = APIRouter()

async def get_current_user_from_header(
    x_user_id: Optional[uuid.UUID] = Header(None),
    db: AsyncSession = Depends(get_db)
) -> models.User:
    if not x_user_id:
        return None # Return None if not provided (for unauthed endpoints like init tenant/user)
        
    user = await db.get(models.User, x_user_id)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid User ID Header")
    return user

@router.post("/tenants", response_model=schemas.TenantResponse)
async def create_tenant(tenant: schemas.TenantCreate, db: AsyncSession = Depends(get_db)):
    # Open endpoint for initialization
    db_tenant = models.Tenant(name=tenant.name)
    db.add(db_tenant)
    await db.commit()
    await db.refresh(db_tenant)
    return db_tenant

@router.post("/projects", response_model=schemas.ProjectResponse)
async def create_project(
    project: schemas.ProjectCreate, 
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user_from_header)
):
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")

    # Verify tenant exists
    tenant = await db.get(models.Tenant, project.tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
        
    # RBAC Check
    if current_user.tenant_id != project.tenant_id:
         raise HTTPException(status_code=403, detail="Cross-tenant action denied")

    if current_user.role == "admin":
        # Admin can create project for any department
        pass
    elif current_user.role == "manager":
        # Manager can only create project for purely their own department
        if not project.department or project.department != current_user.department:
            raise HTTPException(status_code=403, detail="Managers can only create projects in their own department")
    else:
        raise HTTPException(status_code=403, detail="Permission denied")

    db_project = models.Project(**project.model_dump())
    db.add(db_project)
    await db.commit()
    await db.refresh(db_project)
    # Ensure vector collection exists
    from app.services.vector import vector_service
    vector_service.ensure_collection_exists(str(project.tenant_id), str(db_project.id))
    
    return db_project

@router.post("/users", response_model=schemas.UserResponse)
async def create_user(
    user: schemas.UserCreate, 
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user_from_header)
):
    # If creating the FIRST admin or generic setup, might need bypass.
    # But for RBAC compliance:
    if current_user:
        # Allow creation if DB is empty or via Bootstrap Key
        # FOR SEEDING: Check for X-Bootstrap-Token
        # In a real app, this would be a secure token in ENV.
        # Here we just look for a header presence to allow "God Mode" creation.
        # You must send this header in seed.py for the first admin.
        pass  # placeholder for bootstrap logic

        # Check if acting user is admin
        if current_user.role != "admin":
            raise HTTPException(status_code=403, detail="Only Admins can create/promote users")
        if current_user.tenant_id != user.tenant_id:
            raise HTTPException(status_code=403, detail="Cross-tenant action denied")
    else:
        # No current_user (No X-User-Id)
        # Allow bootstrap creation only if no users exist for this tenant.
        result = await db.execute(
            select(models.User).where(models.User.tenant_id == user.tenant_id)
        )
        existing_user = result.scalars().first()
        if existing_user and user.role in ["admin", "manager"]:
            raise HTTPException(status_code=403, detail="Registration for Admin/Manager requires Admin privileges")

    # Idempotency: if user already exists by email in the same tenant, return it.
    result = await db.execute(select(models.User).where(models.User.email == user.email))
    existing_user = result.scalars().first()
    if existing_user:
        if existing_user.tenant_id != user.tenant_id:
            raise HTTPException(
                status_code=409,
                detail="Email already exists in another tenant"
            )
        return existing_user

    db_user = models.User(**user.model_dump())
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user
