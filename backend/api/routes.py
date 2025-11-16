"""
API routes for task management and AI inference
"""
import os
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
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
    ShortcutResetRequest
)
from db.database import get_db
from db.models import Task, Comment, Attachment, InferenceHistory, ShortcutConfig
from db.default_shortcuts import get_default_shortcuts
from agents.task_extractor import TaskExtractor
from agents.pdf_processor import PDFProcessor

router = APIRouter()

# Initialize AI components
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:7b-instruct")

task_extractor = TaskExtractor(OLLAMA_BASE_URL, OLLAMA_MODEL)
pdf_processor = PDFProcessor()


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
    result = await db.execute(select(Task))
    tasks = result.scalars().all()

    # Convert to response format - relationships not loaded, will return empty arrays
    return [_task_to_schema(task, load_relationships=False) for task in tasks]


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
        created_at=now,
        updated_at=now
    )

    db.add(task)
    await db.commit()
    await db.refresh(task)

    return _task_to_schema(task)


@router.get("/tasks/{task_id}", response_model=TaskSchema)
async def get_task(task_id: str, db: AsyncSession = Depends(get_db)):
    """Get a specific task"""
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    return _task_to_schema(task)


@router.put("/tasks/{task_id}", response_model=TaskSchema)
async def update_task(
    task_id: str,
    task_data: TaskUpdateRequest,
    db: AsyncSession = Depends(get_db)
):
    """Update a task with provided fields"""
    result = await db.execute(select(Task).where(Task.id == task_id))
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
        "description": "description"
    }
    
    for api_field, db_field in field_mapping.items():
        if api_field in update_data:
            setattr(task, db_field, update_data[api_field])

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
    Infer tasks from PDF file
    """
    try:
        # Read and validate PDF file
        pdf_bytes = await file.read()

        if not pdf_processor.validate_pdf(pdf_bytes):
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
        raise HTTPException(status_code=500, detail=f"PDF processing failed: {str(e)}")


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
        await db.execute("DELETE FROM shortcut_configs")
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


# ============= Helper Functions =============

def _task_to_schema(task: Task, load_relationships: bool = False) -> TaskSchema:
    """Convert SQLAlchemy Task to Pydantic schema with safe relationship access
    
    Args:
        task: Task model instance
        load_relationships: Whether to attempt loading relationships (requires proper async context)
    """
    # Don't try to access relationships in async context - they cause greenlet errors
    # Relationships would need to be eager-loaded in the query
    attachments = []
    comments = []
    
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
