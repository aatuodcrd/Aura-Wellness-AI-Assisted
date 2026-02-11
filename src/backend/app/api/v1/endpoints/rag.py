from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db
from app.db import models
from app.schemas import rag as schemas
from app.services.rag import rag_service
from langchain_openai import ChatOpenAI
from app.core.config import settings
from langchain_core.prompts import ChatPromptTemplate
import uuid
from typing import Optional

router = APIRouter()

async def get_current_user_from_header(
    x_user_id: Optional[uuid.UUID] = Header(None),
    db: AsyncSession = Depends(get_db)
) -> models.User:
    if not x_user_id:
        raise HTTPException(status_code=401, detail="Authentication required (X-User-Id)")
        
    user = await db.get(models.User, x_user_id)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid User ID Header")
    return user

async def verify_management_permission(user: models.User, project: models.Project):
    """
    Checks if user has management rights (delete/upload) for the project.
    """
    if user.tenant_id != project.tenant_id:
        raise HTTPException(status_code=403, detail="Cross-tenant access denied")

    if user.role == "admin":
        return True
    
    if user.role == "manager":
        if user.department == project.department:
            return True
        raise HTTPException(status_code=403, detail="Manager can only manage projects in their department")
        
    raise HTTPException(status_code=403, detail="Only Admin or Manager can manage documents")

@router.post("/projects/{project_id}/documents", response_model=schemas.DocumentResponse)
async def upload_document(
    project_id: uuid.UUID,
    doc: schemas.DocumentUpload,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user_from_header)
):
    # 1. Verify Project
    project = await db.get(models.Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # 2. Check Permission
    await verify_management_permission(current_user, project)

    # 3. Save to PG
    db_doc = models.Document(
        project_id=project_id,
        title=doc.title,
        content=doc.content
    )
    db.add(db_doc)
    await db.commit()
    await db.refresh(db_doc)

    # 4. Trigger Async Ingestion (RAG)
    background_tasks.add_task(
        rag_service.ingest_document,
        tenant_id=str(project.tenant_id),
        project_id=str(project_id),
        doc_id=str(db_doc.id),
        content=doc.content,
        title=doc.title
    )

    return db_doc

@router.delete("/projects/{project_id}/documents/{doc_id}")
async def delete_document(
    project_id: uuid.UUID,
    doc_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user_from_header)
):
    # 1. Verify Project
    project = await db.get(models.Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # 2. Check Permission
    await verify_management_permission(current_user, project)
    
    # 3. Get Doc
    doc = await db.get(models.Document, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    if doc.project_id != project_id:
         raise HTTPException(status_code=400, detail="Document does not belong to this project")

    # 4. Delete from DB
    await db.delete(doc)
    await db.commit()
    
    # 5. TODO: Delete from Vector DB (Qdrant)
    # Note: Qdrant deletion by payload/filter is needed. 
    # For now, we remove the Record. 
    # To fully support this, we need a method in vector_service to delete vectors by doc_id.
    from app.services.vector import vector_service
    vector_service.delete_vectors_by_doc_id(str(project.tenant_id), str(project_id), str(doc_id))

    return {"status": "deleted", "id": str(doc_id)}

@router.post("/chat", response_model=schemas.ChatResponse)
async def chat(
    request: schemas.ChatRequest, 
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user_from_header)
):
    # 1. Verify access & RBAC using header user
    # Note: request.user_id is redundant now, but we keep it or validate it matches.
    if request.user_id != current_user.id:
         raise HTTPException(status_code=400, detail="User ID mismatch between header and body")

    project = await db.get(models.Project, request.project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
        
    # Check 1: Tenant Isolation
    if current_user.tenant_id != project.tenant_id:
        raise HTTPException(status_code=403, detail="Cross-tenant access denied")

    # Check 2: RBAC
    if current_user.role == "admin":
        pass 
    elif current_user.role == "manager":
        if current_user.department != project.department:
            raise HTTPException(
                status_code=403, 
                detail=f"Manager access denied. User Dept: {current_user.department}, Project Dept: {project.department}"
            )
    else:
        if current_user.department != project.department:
             raise HTTPException(status_code=403, detail="Access denied. Department mismatch.")

    # 2. Retrieve Context
    context_docs = await rag_service.retrieve(
        tenant_id=str(project.tenant_id),
        project_id=str(project.id),
        query=request.question,
        limit=settings.RAG_TOP_K
    )

    # 3. Generate Answer
    context_text = "\n\n".join([f"Source: {d['title']}\n{d['content']}" for d in context_docs])
    
    if not context_text:
        return schemas.ChatResponse(
            answer="I don't have enough information in the provided documents to answer that question.",
            sources=[]
        )

    llm = ChatOpenAI(model=settings.RAG_LLM_MODEL, api_key=settings.OPENAI_API_KEY)
    
    prompt = ChatPromptTemplate.from_template("""
    You are an intelligent internal knowledge assistant.

    INSTRUCTIONS:
    1. Answer the user's question based EXCLUSIVELY on the provided context below.
    2. The context contains up to {top_k} most relevant document chunks. Synthesize information from them to answer accurately.
    3. Do not use outside knowledge or make up information.
    4. If the answer cannot be found in the context, state clearly that you do not know.
    5. You MUST cite the source of your information for every claim, using the format [Source Title].

    CONTEXT:
    {context}

    USER QUESTION:
    {question}
    """)
    
    chain = prompt | llm
    
    response = await chain.ainvoke({
        "context": context_text,
        "question": request.question,
        "top_k": settings.RAG_TOP_K
    })

    # 4. Save Chat Log
    chat_log = models.ChatLog(
        user_id=current_user.id,
        project_id=request.project_id,
        question=request.question,
        answer=response.content,
        sources=[{"title": d["title"]} for d in context_docs]
    )
    db.add(chat_log)
    await db.commit()

    return schemas.ChatResponse(
        answer=response.content,
        sources=[schemas.Source(title=d['title'], content=d['content'][:200] + "...") for d in context_docs]
    )
