"""
API Routes for Task Management and AI Inference

This module provides FastAPI endpoints for:
- Task CRUD operations with comments, attachments, and notes
- AI-powered task extraction from text and PDFs
- Keyboard shortcut configuration
- System health checks
- Cognitive Nexus context ingestion (Phase 1)

All task queries use eager loading (selectinload) to avoid async relationship issues.
Comments and attachments are stored in separate tables with cascade delete.
"""
import os
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text, delete
from sqlalchemy.orm import selectinload
import uuid
from datetime import datetime

from api.schemas import (
    TaskSchema,
    TaskCreateRequest,
    TaskUpdateRequest,
    InferenceRequest,
    InferenceResponse,
    HealthResponse,
    CommentSchema,
    ShortcutConfigSchema,
    ShortcutCreateRequest,
    ShortcutUpdateRequest,
    ShortcutBulkUpdateRequest,
    ShortcutResetRequest,
    DocumentSchema,
    DocumentUploadResponse,
    DocumentListResponse,
    KnowledgeBaseSummaryResponse
)
from db.database import get_db
from db.models import Task, Comment, Attachment, InferenceHistory, ShortcutConfig, Document
from db.default_shortcuts import get_default_shortcuts
from agents.task_extractor import TaskExtractor
from agents.pdf_processor import PDFProcessor
from agents.advanced_pdf_processor import AdvancedPDFProcessor
from agents.document_analyzer import DocumentAnalyzer
from agents.document_processor import DocumentProcessor
from agents.document_storage import DocumentStorage
from agents.knowledge_base import KnowledgeBase

# Import Cognitive Nexus routers
from api.context_routes import router as context_router
from api.knowledge_routes import router as knowledge_router

router = APIRouter()

# Include Cognitive Nexus routes
router.include_router(context_router)
router.include_router(knowledge_router)

# Initialize AI components
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:7b-instruct")
DOCUMENT_STORAGE_PATH = os.getenv("DOCUMENT_STORAGE_PATH", "./data/documents")

task_extractor = TaskExtractor(OLLAMA_BASE_URL, OLLAMA_MODEL)
pdf_processor = PDFProcessor()
advanced_pdf_processor = AdvancedPDFProcessor()
document_analyzer = DocumentAnalyzer(OLLAMA_BASE_URL, OLLAMA_MODEL)
document_processor = DocumentProcessor()
document_storage = DocumentStorage(DOCUMENT_STORAGE_PATH)
knowledge_base = KnowledgeBase()


# ============= Health Check =============

@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Check API, Ollama, and database health"""
    ollama_connected = await task_extractor.check_connection()

    return HealthResponse(
        status="healthy",
        ollama_connected=ollama_connected,
        database_connected=True,
        model=OLLAMA_MODEL
    )


# ============= Task CRUD =============

@router.get("/tasks", response_model=List[TaskSchema])
async def get_tasks(db: AsyncSession = Depends(get_db)):
    """Get all tasks"""
    result = await db.execute(
        select(Task)
        .options(selectinload(Task.comments), selectinload(Task.attachments))
    )
    tasks = result.scalars().all()

    # Convert to response format with loaded relationships
    return [_task_to_schema(task, load_relationships=True) for task in tasks]


@router.post("/tasks", response_model=TaskSchema)
async def create_task(
    task_data: TaskCreateRequest,
    db: AsyncSession = Depends(get_db)
):
    """Create a new task"""
    task_id = str(uuid.uuid4())
    now = datetime.utcnow()

    task = Task(
        id=task_id,
        title=task_data.title,
        status=task_data.status,
        assignee=task_data.assignee,
        start_date=task_data.startDate,
        due_date=task_data.dueDate,
        value_stream=task_data.valueStream,
        description=task_data.description,
        notes=task_data.notes,
        created_at=now,
        updated_at=now
    )

    db.add(task)
    await db.commit()
    await db.refresh(task, ['attachments', 'comments'])

    return _task_to_schema(task)


@router.get("/tasks/{task_id}", response_model=TaskSchema)
async def get_task(task_id: str, db: AsyncSession = Depends(get_db)):
    """Get a specific task"""
    result = await db.execute(
        select(Task)
        .where(Task.id == task_id)
        .options(selectinload(Task.comments), selectinload(Task.attachments))
    )
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    return _task_to_schema(task, load_relationships=True)


@router.put("/tasks/{task_id}", response_model=TaskSchema)
async def update_task(
    task_id: str,
    task_data: TaskUpdateRequest,
    db: AsyncSession = Depends(get_db)
):
    """Update a task with provided fields"""
    result = await db.execute(
        select(Task)
        .where(Task.id == task_id)
        .options(selectinload(Task.comments), selectinload(Task.attachments))
    )
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # Update only provided fields
    update_data = task_data.model_dump(exclude_unset=True)
    field_mapping = {
        "title": "title",
        "status": "status",
        "assignee": "assignee",
        "startDate": "start_date",
        "dueDate": "due_date",
        "valueStream": "value_stream",
        "description": "description",
        "notes": "notes"
    }
    
    for api_field, db_field in field_mapping.items():
        if api_field in update_data:
            setattr(task, db_field, update_data[api_field])

    # Handle comments - full replacement strategy
    # Delete all existing comments and recreate from request
    # This ensures frontend state is source of truth
    if "comments" in update_data and update_data["comments"] is not None:
        # Delete existing comments (cascade handled by DB)
        await db.execute(delete(Comment).where(Comment.task_id == task_id))
        # Recreate all comments from request
        for comment_data in update_data["comments"]:
            comment = Comment(
                id=comment_data.get("id", str(uuid.uuid4())),
                task_id=task_id,
                text=comment_data["text"],
                author=comment_data["author"],
                created_at=datetime.fromisoformat(comment_data["createdAt"].replace("Z", "+00:00")) if "createdAt" in comment_data else datetime.utcnow()
            )
            db.add(comment)

    # Handle attachments - replace all
    if "attachments" in update_data and update_data["attachments"] is not None:
        # Delete existing attachments
        await db.execute(delete(Attachment).where(Attachment.task_id == task_id))
        # Add new attachments
        for attachment_url in update_data["attachments"]:
            attachment = Attachment(
                task_id=task_id,
                url=attachment_url
            )
            db.add(attachment)

    task.updated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(task)

    return _task_to_schema(task)


@router.delete("/tasks/{task_id}")
async def delete_task(task_id: str, db: AsyncSession = Depends(get_db)):
    """Delete a task"""
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    await db.delete(task)
    await db.commit()

    return {"message": "Task deleted successfully"}


# ============= AI Task Inference =============

@router.post("/infer-tasks", response_model=InferenceResponse)
async def infer_tasks_from_text(
    request: InferenceRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Infer tasks from text using AI
    """
    try:
        # Extract tasks using AI
        result = await task_extractor.extract_tasks(
            request.text,
            request.assignee
        )

        # Save tasks to database
        saved_tasks = []
        for task_data in result["tasks"]:
            task = _create_task_from_data(task_data)
            db.add(task)
            saved_tasks.append(task)

        # Save inference history
        history = InferenceHistory(
            input_text=request.text[:1000],  # Limit stored text
            input_type="text",
            tasks_inferred=len(saved_tasks),
            model_used=result["model_used"],
            inference_time=result["inference_time_ms"]
        )
        db.add(history)

        await db.commit()

        # Refresh all tasks
        for task in saved_tasks:
            await db.refresh(task)

        return InferenceResponse(
            tasks=[_task_to_schema(task) for task in saved_tasks],
            inference_time_ms=result["inference_time_ms"],
            model_used=result["model_used"],
            tasks_inferred=len(saved_tasks)
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Task inference failed: {str(e)}")


@router.post("/infer-tasks-pdf", response_model=InferenceResponse)
async def infer_tasks_from_pdf(
    file: UploadFile = File(...),
    assignee: str = Form("You"),
    db: AsyncSession = Depends(get_db)
):
    """
    Infer tasks from PDF file and save the document
    """
    try:
        # Read file
        pdf_bytes = await file.read()
        filename = file.filename or "document.pdf"

        # Validate PDF
        if not await pdf_processor.validate_pdf(pdf_bytes):
            raise HTTPException(status_code=400, detail="Invalid PDF file")

        # Extract text from PDF
        extracted_text = await pdf_processor.extract_text_from_pdf(pdf_bytes)

        if not extracted_text.strip():
            raise HTTPException(status_code=400, detail="No text found in PDF")

        # Extract tasks using AI
        result = await task_extractor.extract_tasks(extracted_text, assignee)

        # Save tasks to database
        saved_tasks = []
        for task_data in result["tasks"]:
            task = _create_task_from_data(task_data)
            db.add(task)
            saved_tasks.append(task)

        # Save inference history
        history = InferenceHistory(
            input_text=extracted_text[:1000],
            input_type="pdf",
            tasks_inferred=len(saved_tasks),
            model_used=result["model_used"],
            inference_time=result["inference_time_ms"]
        )
        db.add(history)

        # Flush to get history ID
        await db.flush()

        # Save document to storage
        doc_info = await document_storage.save_document(
            pdf_bytes,
            filename,
            category="inference",
            metadata={
                "inference_id": history.id,
                "tasks_inferred": len(saved_tasks)
            }
        )

        # Get document metadata
        doc_metadata = await document_processor.get_document_info(pdf_bytes, filename)

        # Create document record
        document = Document(
            id=str(uuid.uuid4()),
            file_id=doc_info["file_id"],
            original_filename=filename,
            file_extension=doc_metadata.get("extension", ".pdf"),
            mime_type=doc_metadata.get("mime_type"),
            file_hash=doc_info["file_hash"],
            size_bytes=doc_info["size_bytes"],
            storage_path=doc_info["relative_path"],
            category="inference",
            extracted_text=extracted_text,
            text_preview=extracted_text[:500] if extracted_text else None,
            page_count=doc_metadata.get("page_count"),
            inference_history_id=history.id
        )
        db.add(document)

        await db.commit()

        # Reload tasks with eager-loaded relationships to avoid greenlet errors
        task_ids = [task.id for task in saved_tasks]
        stmt = select(Task).where(Task.id.in_(task_ids)).options(
            selectinload(Task.comments),
            selectinload(Task.attachments)
        )
        result_tasks = await db.execute(stmt)
        refreshed_tasks = result_tasks.scalars().all()

        return InferenceResponse(
            tasks=[_task_to_schema(task) for task in refreshed_tasks],
            inference_time_ms=result["inference_time_ms"],
            model_used=result["model_used"],
            tasks_inferred=len(refreshed_tasks)
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF processing failed: {str(e)}")


@router.post("/analyze-document")
async def analyze_document(
    file: UploadFile = File(...),
    assignee: str = Form("You"),
    db: AsyncSession = Depends(get_db)
):
    """
    Advanced PDF analysis with structure extraction, summarization, and entity extraction

    Returns:
    - Document summary (executive summary, key points, document type)
    - Extracted entities (people, organizations, dates, locations, decisions)
    - Extracted tasks with full context
    - Document metadata and statistics
    """
    try:
        # Read and validate PDF file
        pdf_bytes = await file.read()

        if not advanced_pdf_processor.validate_pdf(pdf_bytes):
            raise HTTPException(status_code=400, detail="Invalid PDF file")

        # Process PDF with advanced extraction
        processed_doc = await advanced_pdf_processor.process_document(pdf_bytes)

        # Perform AI analysis
        analysis = await document_analyzer.analyze_document(processed_doc)

        # Extract tasks with context
        task_result = await document_analyzer.extract_tasks_with_context(
            processed_doc,
            assignee
        )

        # Save tasks to database
        saved_tasks = []
        for task_data in task_result["tasks"]:
            task = _create_task_from_data(task_data)
            db.add(task)
            saved_tasks.append(task)

        # Save inference history
        history = InferenceHistory(
            input_text=processed_doc.raw_text[:1000],
            input_type="pdf_advanced",
            tasks_inferred=len(saved_tasks),
            model_used=analysis.model_used,
            inference_time=analysis.inference_time_ms
        )
        db.add(history)

        await db.commit()

        # Refresh all tasks
        for task in saved_tasks:
            await db.refresh(task)

        # Build comprehensive response
        from dataclasses import asdict

        return {
            "tasks": [_task_to_schema(task) for task in saved_tasks],
            "summary": asdict(analysis.summary),
            "entities": asdict(analysis.entities),
            "metadata": asdict(processed_doc.metadata),
            "statistics": {
                **processed_doc.summary_stats,
                "inference_time_ms": analysis.inference_time_ms
            },
            "tables": processed_doc.tables,
            "model_used": analysis.model_used
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Document analysis failed: {str(e)}")


@router.post("/summarize-pdf")
async def summarize_pdf(
    file: UploadFile = File(...)
):
    """
    Quick document summarization without task extraction

    Returns:
    - Executive summary
    - Key points
    - Document type classification
    - Topics
    - Metadata
    """
    try:
        # Read and validate PDF file
        pdf_bytes = await file.read()

        if not advanced_pdf_processor.validate_pdf(pdf_bytes):
            raise HTTPException(status_code=400, detail="Invalid PDF file")

        # Process PDF
        processed_doc = await advanced_pdf_processor.process_document(pdf_bytes)

        # Generate summary only (faster than full analysis)
        analysis = await document_analyzer.analyze_document(processed_doc)

        from dataclasses import asdict

        return {
            "summary": asdict(analysis.summary),
            "metadata": asdict(processed_doc.metadata),
            "statistics": processed_doc.summary_stats,
            "tables_count": len(processed_doc.tables),
            "inference_time_ms": analysis.inference_time_ms,
            "model_used": analysis.model_used
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Document summarization failed: {str(e)}")


@router.post("/extract-document-structure")
async def extract_document_structure(
    file: UploadFile = File(...)
):
    """
    Extract document structure without AI analysis (fast)

    Returns:
    - Structured sections (headings, paragraphs, lists)
    - Tables with markdown formatting
    - Metadata
    - Intelligent chunks for further processing
    """
    try:
        # Read and validate PDF file
        pdf_bytes = await file.read()

        if not advanced_pdf_processor.validate_pdf(pdf_bytes):
            raise HTTPException(status_code=400, detail="Invalid PDF file")

        # Process PDF
        processed_doc = await advanced_pdf_processor.process_document(pdf_bytes)

        from dataclasses import asdict

        return {
            "metadata": asdict(processed_doc.metadata),
            "sections": [asdict(section) for section in processed_doc.structured_sections],
            "tables": processed_doc.tables,
            "chunks": processed_doc.chunks,
            "statistics": processed_doc.summary_stats
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Structure extraction failed: {str(e)}")


# ============= Keyboard Shortcuts =============

@router.get("/shortcuts", response_model=List[ShortcutConfigSchema])
async def get_shortcuts(
    user_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Get all keyboard shortcuts
    Returns defaults merged with user overrides if user_id is provided
    """
    # Get all shortcuts from database
    result = await db.execute(select(ShortcutConfig))
    db_shortcuts = result.scalars().all()

    # If no shortcuts in DB, seed with defaults
    if not db_shortcuts:
        await seed_default_shortcuts(db)
        result = await db.execute(select(ShortcutConfig))
        db_shortcuts = result.scalars().all()

    # Convert to schemas
    shortcuts = [_shortcut_to_schema(s) for s in db_shortcuts]

    # If user_id provided, filter to show only defaults and user overrides
    if user_id is not None:
        shortcuts = [s for s in shortcuts if s.user_id is None or s.user_id == user_id]

    return shortcuts


@router.get("/shortcuts/defaults", response_model=List[ShortcutConfigSchema])
async def get_default_shortcuts_api(db: AsyncSession = Depends(get_db)):
    """Get default keyboard shortcuts"""
    result = await db.execute(
        select(ShortcutConfig).where(ShortcutConfig.user_id == None)
    )
    shortcuts = result.scalars().all()

    # If no defaults, seed them
    if not shortcuts:
        await seed_default_shortcuts(db)
        result = await db.execute(
            select(ShortcutConfig).where(ShortcutConfig.user_id == None)
        )
        shortcuts = result.scalars().all()

    return [_shortcut_to_schema(s) for s in shortcuts]


@router.put("/shortcuts/{shortcut_id}", response_model=ShortcutConfigSchema)
async def update_shortcut(
    shortcut_id: str,
    update_data: ShortcutUpdateRequest,
    user_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Update a specific shortcut
    If user_id is provided, creates a user override
    """
    # Find the shortcut
    result = await db.execute(
        select(ShortcutConfig).where(ShortcutConfig.id == shortcut_id)
    )
    shortcut = result.scalar_one_or_none()

    if not shortcut:
        raise HTTPException(status_code=404, detail="Shortcut not found")

    # If user_id provided and this is a default, create user override
    if user_id is not None and shortcut.user_id is None:
        # Create new user override
        user_shortcut = ShortcutConfig(
            id=f"{shortcut_id}_user_{user_id}",
            category=shortcut.category,
            action=shortcut.action,
            key=update_data.key if update_data.key else shortcut.key,
            modifiers=update_data.modifiers if update_data.modifiers is not None else shortcut.modifiers,
            enabled=update_data.enabled if update_data.enabled is not None else shortcut.enabled,
            description=shortcut.description,
            user_id=user_id,
            is_default=False,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db.add(user_shortcut)
        await db.commit()
        await db.refresh(user_shortcut)
        return _shortcut_to_schema(user_shortcut)

    # Otherwise update existing
    if update_data.key is not None:
        shortcut.key = update_data.key
    if update_data.modifiers is not None:
        shortcut.modifiers = update_data.modifiers
    if update_data.enabled is not None:
        shortcut.enabled = update_data.enabled

    shortcut.updated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(shortcut)

    return _shortcut_to_schema(shortcut)


@router.post("/shortcuts/bulk-update")
async def bulk_update_shortcuts(
    request: ShortcutBulkUpdateRequest,
    db: AsyncSession = Depends(get_db)
):
    """Bulk update or create shortcuts"""
    updated_shortcuts = []

    for shortcut_data in request.shortcuts:
        # Check if shortcut exists
        result = await db.execute(
            select(ShortcutConfig).where(ShortcutConfig.id == shortcut_data.id)
        )
        existing = result.scalar_one_or_none()

        if existing:
            # Update existing
            existing.key = shortcut_data.key
            existing.modifiers = shortcut_data.modifiers
            existing.enabled = shortcut_data.enabled
            existing.updated_at = datetime.utcnow()
            updated_shortcuts.append(existing)
        else:
            # Create new
            new_shortcut = ShortcutConfig(
                id=shortcut_data.id,
                category=shortcut_data.category,
                action=shortcut_data.action,
                key=shortcut_data.key,
                modifiers=shortcut_data.modifiers,
                enabled=shortcut_data.enabled,
                description=shortcut_data.description,
                user_id=shortcut_data.user_id,
                is_default=shortcut_data.user_id is None,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            db.add(new_shortcut)
            updated_shortcuts.append(new_shortcut)

    await db.commit()

    return {
        "message": f"Updated {len(updated_shortcuts)} shortcuts",
        "count": len(updated_shortcuts)
    }


@router.post("/shortcuts/reset")
async def reset_shortcuts(
    request: ShortcutResetRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Reset shortcuts to defaults
    If user_id provided, removes user overrides
    If user_id is None, resets all shortcuts
    """
    if request.user_id is not None:
        # Delete user overrides
        result = await db.execute(
            select(ShortcutConfig).where(ShortcutConfig.user_id == request.user_id)
        )
        user_shortcuts = result.scalars().all()

        for shortcut in user_shortcuts:
            await db.delete(shortcut)

        await db.commit()
        return {"message": f"Reset shortcuts for user {request.user_id}"}
    else:
        # Delete all and reseed
        await db.execute(text("DELETE FROM shortcut_configs"))
        await db.commit()
        await seed_default_shortcuts(db)
        return {"message": "Reset all shortcuts to defaults"}


@router.get("/shortcuts/export")
async def export_shortcuts(
    user_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db)
):
    """Export shortcut configuration as JSON"""
    query = select(ShortcutConfig)
    if user_id is not None:
        query = query.where(
            (ShortcutConfig.user_id == None) | (ShortcutConfig.user_id == user_id)
        )

    result = await db.execute(query)
    shortcuts = result.scalars().all()

    return {
        "version": "1.0",
        "exported_at": datetime.utcnow().isoformat(),
        "user_id": user_id,
        "shortcuts": [_shortcut_to_dict(s) for s in shortcuts]
    }


@router.post("/shortcuts/import")
async def import_shortcuts(
    config: dict,
    db: AsyncSession = Depends(get_db)
):
    """Import shortcut configuration from JSON"""
    try:
        shortcuts_data = config.get("shortcuts", [])
        imported_count = 0

        for shortcut_data in shortcuts_data:
            # Check if exists
            result = await db.execute(
                select(ShortcutConfig).where(ShortcutConfig.id == shortcut_data["id"])
            )
            existing = result.scalar_one_or_none()

            if existing:
                # Update
                existing.key = shortcut_data["key"]
                existing.modifiers = shortcut_data["modifiers"]
                existing.enabled = shortcut_data["enabled"]
                existing.updated_at = datetime.utcnow()
            else:
                # Create
                new_shortcut = ShortcutConfig(
                    id=shortcut_data["id"],
                    category=shortcut_data["category"],
                    action=shortcut_data["action"],
                    key=shortcut_data["key"],
                    modifiers=shortcut_data["modifiers"],
                    enabled=shortcut_data["enabled"],
                    description=shortcut_data["description"],
                    user_id=shortcut_data.get("user_id"),
                    is_default=shortcut_data.get("is_default", True),
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                db.add(new_shortcut)

            imported_count += 1

        await db.commit()
        return {
            "message": "Shortcuts imported successfully",
            "imported_count": imported_count
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Import failed: {str(e)}")


# ============= Document Management =============

@router.post("/documents/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    category: str = Form("knowledge"),
    task_id: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db)
):
    """
    Upload a document (PDF, Word, Markdown, etc.) to the knowledge base

    Supports: .pdf, .docx, .doc, .txt, .md, .xlsx, .xls
    """
    try:
        # Read file
        file_bytes = await file.read()
        filename = file.filename or "document"

        # Validate document
        is_valid, error_msg = await document_processor.validate_document(file_bytes, filename)
        if not is_valid:
            raise HTTPException(status_code=400, detail=error_msg)

        # Extract text
        extracted_text = await document_processor.extract_text(file_bytes, filename)

        # Save to storage
        doc_info = await document_storage.save_document(
            file_bytes,
            filename,
            category=category,
            metadata={"task_id": task_id} if task_id else {}
        )

        # Get document metadata
        doc_metadata = await document_processor.get_document_info(file_bytes, filename)

        # Create document record
        document = Document(
            id=str(uuid.uuid4()),
            file_id=doc_info["file_id"],
            original_filename=filename,
            file_extension=doc_metadata.get("extension", ""),
            mime_type=doc_metadata.get("mime_type"),
            file_hash=doc_info["file_hash"],
            size_bytes=doc_info["size_bytes"],
            storage_path=doc_info["relative_path"],
            category=category,
            extracted_text=extracted_text,
            text_preview=extracted_text[:500] if extracted_text else None,
            page_count=doc_metadata.get("page_count"),
            task_id=task_id
        )
        db.add(document)
        await db.commit()
        await db.refresh(document)

        # Index for knowledge base
        await knowledge_base.index_document(db, document.id, extracted_text)

        return DocumentUploadResponse(
            document=_document_to_schema(document),
            message=f"Document '{filename}' uploaded successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Document upload failed: {str(e)}")


@router.post("/documents/upload-for-inference", response_model=InferenceResponse)
async def upload_document_for_inference(
    file: UploadFile = File(...),
    assignee: str = Form("You"),
    db: AsyncSession = Depends(get_db)
):
    """
    Upload any supported document for AI task inference

    Supports: .pdf, .docx, .doc, .txt, .md, .xlsx, .xls
    """
    try:
        # Read file
        file_bytes = await file.read()
        filename = file.filename or "document"

        # Validate and extract text
        is_valid, error_msg = await document_processor.validate_document(file_bytes, filename)
        if not is_valid:
            raise HTTPException(status_code=400, detail=error_msg)

        extracted_text = await document_processor.extract_text(file_bytes, filename)

        if not extracted_text.strip():
            raise HTTPException(status_code=400, detail="No text found in document")

        # Extract tasks using AI
        result = await task_extractor.extract_tasks(extracted_text, assignee)

        # Save tasks to database
        saved_tasks = []
        for task_data in result["tasks"]:
            task = _create_task_from_data(task_data)
            db.add(task)
            saved_tasks.append(task)

        # Save inference history
        doc_metadata = await document_processor.get_document_info(file_bytes, filename)
        history = InferenceHistory(
            input_text=extracted_text[:1000],
            input_type=doc_metadata.get("extension", "document"),
            tasks_inferred=len(saved_tasks),
            model_used=result["model_used"],
            inference_time=result["inference_time_ms"]
        )
        db.add(history)
        await db.flush()

        # Save document to storage
        doc_info = await document_storage.save_document(
            file_bytes,
            filename,
            category="inference",
            metadata={
                "inference_id": history.id,
                "tasks_inferred": len(saved_tasks)
            }
        )

        # Create document record
        document = Document(
            id=str(uuid.uuid4()),
            file_id=doc_info["file_id"],
            original_filename=filename,
            file_extension=doc_metadata.get("extension", ""),
            mime_type=doc_metadata.get("mime_type"),
            file_hash=doc_info["file_hash"],
            size_bytes=doc_info["size_bytes"],
            storage_path=doc_info["relative_path"],
            category="inference",
            extracted_text=extracted_text,
            text_preview=extracted_text[:500] if extracted_text else None,
            page_count=doc_metadata.get("page_count"),
            inference_history_id=history.id
        )
        db.add(document)

        await db.commit()

        # Reload tasks with eager-loaded relationships to avoid greenlet errors
        task_ids = [task.id for task in saved_tasks]
        stmt = select(Task).where(Task.id.in_(task_ids)).options(
            selectinload(Task.comments),
            selectinload(Task.attachments)
        )
        result_tasks = await db.execute(stmt)
        refreshed_tasks = result_tasks.scalars().all()

        return InferenceResponse(
            tasks=[_task_to_schema(task) for task in refreshed_tasks],
            inference_time_ms=result["inference_time_ms"],
            model_used=result["model_used"],
            tasks_inferred=len(refreshed_tasks)
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Document processing failed: {str(e)}")


@router.get("/documents", response_model=DocumentListResponse)
async def list_documents(
    category: Optional[str] = None,
    task_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    List all documents, optionally filtered by category or task
    """
    try:
        stmt = select(Document)

        if category:
            stmt = stmt.where(Document.category == category)

        if task_id:
            stmt = stmt.where(Document.task_id == task_id)

        result = await db.execute(stmt)
        documents = result.scalars().all()

        return DocumentListResponse(
            documents=[_document_to_schema(doc) for doc in documents],
            total=len(documents),
            category=category
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list documents: {str(e)}")


@router.get("/documents/{document_id}", response_model=DocumentSchema)
async def get_document(document_id: str, db: AsyncSession = Depends(get_db)):
    """
    Get document metadata by ID
    """
    result = await db.execute(
        select(Document).where(Document.id == document_id)
    )
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    return _document_to_schema(document)


@router.get("/documents/{document_id}/download")
async def download_document(document_id: str, db: AsyncSession = Depends(get_db)):
    """
    Download document file
    """
    from fastapi.responses import Response

    # Get document metadata
    result = await db.execute(
        select(Document).where(Document.id == document_id)
    )
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    # Retrieve file from storage
    file_bytes = await document_storage.get_document(document.file_id, document.category)

    if not file_bytes:
        raise HTTPException(status_code=404, detail="Document file not found in storage")

    # Return file with appropriate headers
    return Response(
        content=file_bytes,
        media_type=document.mime_type or "application/octet-stream",
        headers={
            "Content-Disposition": f'attachment; filename="{document.original_filename}"'
        }
    )


@router.delete("/documents/{document_id}")
async def delete_document(document_id: str, db: AsyncSession = Depends(get_db)):
    """
    Delete a document and its file
    """
    # Get document
    result = await db.execute(
        select(Document).where(Document.id == document_id)
    )
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    # Delete file from storage
    await document_storage.delete_document(document.file_id, document.category)

    # Delete database record
    await db.delete(document)
    await db.commit()

    return {"message": "Document deleted successfully"}


@router.get("/documents/search/{query}")
async def search_documents(
    query: str,
    category: Optional[str] = None,
    limit: int = 10,
    db: AsyncSession = Depends(get_db)
):
    """
    Search documents by text content
    """
    try:
        documents = await knowledge_base.search_documents(db, query, category, limit)

        return {
            "query": query,
            "results": [_document_to_schema(doc) for doc in documents],
            "total": len(documents)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@router.get("/knowledge-base/summary", response_model=KnowledgeBaseSummaryResponse)
async def get_knowledge_base_summary(db: AsyncSession = Depends(get_db)):
    """
    Get knowledge base statistics
    """
    try:
        summary = await knowledge_base.get_knowledge_base_summary(db)
        return KnowledgeBaseSummaryResponse(**summary)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get summary: {str(e)}")


# ============= Helper Functions =============

def _task_to_schema(task: Task, load_relationships: bool = False) -> TaskSchema:
    """Convert SQLAlchemy Task model to Pydantic TaskSchema.
    
    Important: Relationships (comments, attachments) must be eager-loaded in the
    query using selectinload() to avoid greenlet errors in async context.
    
    Args:
        task: SQLAlchemy Task instance with eager-loaded relationships
        load_relationships: Legacy parameter, kept for compatibility
    
    Returns:
        TaskSchema with all fields including comments and attachments
    """
    # Access relationships - they MUST be eager-loaded in the query
    attachments = [att.url for att in task.attachments] if hasattr(task, 'attachments') and task.attachments else []
    comments = [
        CommentSchema(
            id=comment.id,
            text=comment.text,
            author=comment.author,
            createdAt=comment.created_at.isoformat() if comment.created_at else datetime.utcnow().isoformat()
        ) for comment in task.comments
    ] if hasattr(task, 'comments') and task.comments else []
    
    # Handle potential None values for timestamps
    created_at = task.created_at if task.created_at else datetime.utcnow()
    updated_at = task.updated_at if task.updated_at else datetime.utcnow()
    
    return TaskSchema(
        id=task.id,
        title=task.title,
        status=task.status,
        assignee=task.assignee,
        startDate=task.start_date,
        dueDate=task.due_date,
        valueStream=task.value_stream,
        description=task.description,
        notes=task.notes,
        attachments=attachments,
        comments=comments,
        createdAt=created_at.isoformat(),
        updatedAt=updated_at.isoformat()
    )


def _create_task_from_data(task_data: dict) -> Task:
    """Create a Task model instance from dictionary data"""
    now = datetime.utcnow()
    return Task(
        id=task_data["id"],
        title=task_data["title"],
        status=task_data["status"],
        assignee=task_data["assignee"],
        start_date=task_data.get("startDate"),
        due_date=task_data.get("dueDate"),
        value_stream=task_data.get("valueStream"),
        description=task_data.get("description"),
        created_at=now,
        updated_at=now
    )


def _shortcut_to_schema(shortcut: ShortcutConfig) -> ShortcutConfigSchema:
    """Convert SQLAlchemy ShortcutConfig to Pydantic schema"""
    created_at = shortcut.created_at if shortcut.created_at else datetime.utcnow()
    updated_at = shortcut.updated_at if shortcut.updated_at else datetime.utcnow()

    return ShortcutConfigSchema(
        id=shortcut.id,
        category=shortcut.category,
        action=shortcut.action,
        key=shortcut.key,
        modifiers=shortcut.modifiers if shortcut.modifiers else [],
        enabled=shortcut.enabled,
        description=shortcut.description,
        user_id=shortcut.user_id,
        is_default=shortcut.is_default,
        createdAt=created_at.isoformat(),
        updatedAt=updated_at.isoformat()
    )


def _shortcut_to_dict(shortcut: ShortcutConfig) -> dict:
    """Convert ShortcutConfig to dictionary for export"""
    return {
        "id": shortcut.id,
        "category": shortcut.category,
        "action": shortcut.action,
        "key": shortcut.key,
        "modifiers": shortcut.modifiers if shortcut.modifiers else [],
        "enabled": shortcut.enabled,
        "description": shortcut.description,
        "user_id": shortcut.user_id,
        "is_default": shortcut.is_default
    }


async def seed_default_shortcuts(db: AsyncSession):
    """Seed database with default shortcuts"""
    defaults = get_default_shortcuts()

    for shortcut_data in defaults:
        shortcut = ShortcutConfig(
            id=shortcut_data["id"],
            category=shortcut_data["category"],
            action=shortcut_data["action"],
            key=shortcut_data["key"],
            modifiers=shortcut_data["modifiers"],
            enabled=shortcut_data["enabled"],
            description=shortcut_data["description"],
            user_id=None,
            is_default=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db.add(shortcut)

    await db.commit()


def _document_to_schema(document: Document) -> DocumentSchema:
    """Convert SQLAlchemy Document model to Pydantic DocumentSchema"""
    created_at = document.created_at if document.created_at else datetime.utcnow()
    updated_at = document.updated_at if document.updated_at else datetime.utcnow()

    return DocumentSchema(
        id=document.id,
        file_id=document.file_id,
        original_filename=document.original_filename,
        file_extension=document.file_extension,
        mime_type=document.mime_type,
        file_hash=document.file_hash,
        size_bytes=document.size_bytes,
        storage_path=document.storage_path,
        category=document.category,
        text_preview=document.text_preview,
        page_count=document.page_count,
        task_id=document.task_id,
        inference_history_id=document.inference_history_id,
        created_at=created_at.isoformat(),
        updated_at=updated_at.isoformat()
    )
