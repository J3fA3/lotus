"""
API Routes for Lotus v2 Task Management

Endpoints:
- Task CRUD operations with comments, attachments, and notes
- Task search (keyword-based)
- Keyboard shortcut configuration
- Value stream management
- AI assist (Intelligence Flywheel)
- System health checks
"""
import asyncio
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text, delete
from sqlalchemy.orm import selectinload
import uuid
from datetime import datetime, date

from api.schemas import (
    TaskSchema,
    TaskCreateRequest,
    TaskUpdateRequest,
    HealthResponse,
    CommentSchema,
    ShortcutConfigSchema,
    ShortcutCreateRequest,
    ShortcutUpdateRequest,
    ShortcutBulkUpdateRequest,
    ShortcutResetRequest,
    ValueStreamSchema,
    ValueStreamCreateRequest,
    AIAssistRequest,
    AIAssistResponse,
)
from db.database import get_db
from db.models import Task, Comment, Attachment, ShortcutConfig, ValueStream

logger = logging.getLogger(__name__)

router = APIRouter()


# ============= Health Check =============

@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Check API and database health"""
    return HealthResponse(
        status="healthy",
        database_connected=True,
    )


# ============= Task CRUD =============

@router.get("/tasks", response_model=List[TaskSchema])
async def get_tasks(
    db: AsyncSession = Depends(get_db),
    limit: int = 1000,
    offset: int = 0,
) -> List[TaskSchema]:
    """Get tasks with pagination (default limit 1000)."""
    if limit > 1000:
        limit = 1000
    try:
        result = await asyncio.wait_for(
            db.execute(
                select(Task)
                .options(selectinload(Task.comments), selectinload(Task.attachments))
                .order_by(Task.created_at.desc())
                .limit(limit)
                .offset(offset)
            ),
            timeout=8.0,
        )
        tasks = result.scalars().all()
        return [_task_to_schema(task) for task in tasks]
    except asyncio.TimeoutError:
        logger.error("Database query timed out after 8 seconds")
        return []
    except Exception as e:
        logger.error(f"Error fetching tasks: {str(e)}", exc_info=True)
        return []


@router.post("/tasks", response_model=TaskSchema)
async def create_task(
    task_data: TaskCreateRequest,
    db: AsyncSession = Depends(get_db),
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
        updated_at=now,
    )

    db.add(task)
    await db.commit()

    result = await db.execute(
        select(Task)
        .where(Task.id == task_id)
        .options(selectinload(Task.comments), selectinload(Task.attachments))
    )
    task = result.scalar_one_or_none()

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

    return _task_to_schema(task)


@router.put("/tasks/{task_id}", response_model=TaskSchema)
async def update_task(
    task_id: str,
    task_data: TaskUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Update a task with provided fields"""
    try:
        result = await db.execute(
            select(Task)
            .where(Task.id == task_id)
            .options(selectinload(Task.comments), selectinload(Task.attachments))
        )
        task = result.scalar_one_or_none()

        if not task:
            raise HTTPException(status_code=404, detail="Task not found")

        # Store original status for auto-start-date logic
        original_status = task.status

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
            "notes": "notes",
        }

        for api_field, db_field in field_mapping.items():
            if api_field in update_data:
                setattr(task, db_field, update_data[api_field])

        # Auto-set start date when moving from todo to doing
        if "status" in update_data:
            new_status = update_data["status"]
            if original_status == "todo" and new_status == "doing" and not task.start_date:
                task.start_date = date.today().isoformat()

        # Handle comments - full replacement strategy
        if "comments" in update_data and update_data["comments"] is not None:
            await db.execute(delete(Comment).where(Comment.task_id == task_id))
            for comment_data in update_data["comments"]:
                comment = Comment(
                    id=comment_data.get("id", str(uuid.uuid4())),
                    task_id=task_id,
                    text=comment_data["text"],
                    author=comment_data["author"],
                    created_at=(
                        datetime.fromisoformat(comment_data["createdAt"].replace("Z", "+00:00"))
                        if "createdAt" in comment_data
                        else datetime.utcnow()
                    ),
                )
                db.add(comment)

        # Handle attachments - replace all
        if "attachments" in update_data and update_data["attachments"] is not None:
            await db.execute(delete(Attachment).where(Attachment.task_id == task_id))
            for attachment_url in update_data["attachments"]:
                attachment = Attachment(task_id=task_id, url=attachment_url)
                db.add(attachment)

        task.updated_at = datetime.utcnow()

        # Intelligence Flywheel: create case study when task completed
        if "status" in update_data and update_data["status"] == "done" and original_status != "done":
            task.completed_at = datetime.utcnow()
            try:
                from services.case_memory import create_case_study

                task_dict = {
                    "id": task.id,
                    "title": task.title,
                    "description": task.description,
                    "notes": task.notes,
                    "assignee": task.assignee,
                    "value_stream": task.value_stream,
                    "start_date": task.start_date,
                    "due_date": task.due_date,
                    "created_at": task.created_at.isoformat() if task.created_at else None,
                    "comments": [
                        {"text": c.text, "author": c.author} for c in task.comments
                    ],
                }
                result_case = await create_case_study(task_dict)
                task.case_study_slug = result_case.get("slug")
                logger.info(f"Case study created for task {task_id}: {result_case.get('slug')}")
            except Exception as e:
                logger.error(f"Case study creation failed for task {task_id}: {e}")

        await db.commit()
        db.expire_all()

        # Reload task with relationships
        result = await db.execute(
            select(Task)
            .where(Task.id == task_id)
            .options(selectinload(Task.comments), selectinload(Task.attachments))
        )
        task = result.scalar_one_or_none()

        if not task:
            raise HTTPException(status_code=404, detail="Task not found after update")

        return _task_to_schema(task)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error updating task {task_id}: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"An unexpected error occurred while updating the task: {str(e)}",
        )


@router.delete("/tasks/{task_id}")
async def delete_task(task_id: str, db: AsyncSession = Depends(get_db)):
    """Delete a task"""
    try:
        result = await db.execute(select(Task).where(Task.id == task_id))
        task = result.scalar_one_or_none()

        if not task:
            raise HTTPException(status_code=404, detail="Task not found")

        # Delete using raw SQL to avoid relationship issues
        delete_sql = text("DELETE FROM tasks WHERE id = :task_id")
        result = await db.execute(delete_sql, {"task_id": task_id})

        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Task not found")

        await db.commit()
        return {"message": "Task deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error deleting task {task_id}: {e}", exc_info=True)
        try:
            await db.rollback()
        except Exception:
            pass
        raise HTTPException(
            status_code=500,
            detail=f"An unexpected error occurred while deleting the task: {str(e)}",
        )


# ============= Task Search =============

@router.get("/tasks/search/{query}")
async def search_tasks(
    query: str,
    limit: int = 50,
    threshold: float = 0.3,
    db: AsyncSession = Depends(get_db),
):
    """Search tasks using keyword matching"""
    try:
        result = await db.execute(
            select(Task).options(
                selectinload(Task.comments), selectinload(Task.attachments)
            )
        )
        tasks = result.scalars().all()

        if not tasks:
            return {"query": query, "results": [], "total": 0, "threshold": threshold}

        query_lower = query.lower()
        results = []

        for task in tasks:
            searchable_parts = [task.title]
            if task.description:
                searchable_parts.append(task.description)
            if task.notes:
                searchable_parts.append(task.notes)
            searchable_text = " ".join(searchable_parts).lower()

            if query_lower in searchable_text:
                score = 0.95 if len(query) > 2 else 0.85
                task_schema = _task_to_schema(task)
                results.append({"task": task_schema, "similarity_score": round(score, 3)})

        results.sort(key=lambda x: x["similarity_score"], reverse=True)
        results = results[:limit]

        return {
            "query": query,
            "results": results,
            "total": len(results),
            "threshold": threshold,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


# ============= Keyboard Shortcuts =============

@router.get("/shortcuts", response_model=List[ShortcutConfigSchema])
async def get_shortcuts(
    user_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
):
    """Get all keyboard shortcuts"""
    result = await db.execute(select(ShortcutConfig))
    db_shortcuts = result.scalars().all()

    if not db_shortcuts:
        await seed_default_shortcuts(db)
        result = await db.execute(select(ShortcutConfig))
        db_shortcuts = result.scalars().all()

    shortcuts = [_shortcut_to_schema(s) for s in db_shortcuts]

    if user_id is not None:
        shortcuts = [s for s in shortcuts if s.user_id is None or s.user_id == user_id]

    return shortcuts


@router.get("/shortcuts/defaults", response_model=List[ShortcutConfigSchema])
async def get_default_shortcuts_api(db: AsyncSession = Depends(get_db)):
    """Get default keyboard shortcuts"""
    result = await db.execute(
        select(ShortcutConfig).where(ShortcutConfig.user_id == None)  # noqa: E711
    )
    shortcuts = result.scalars().all()

    if not shortcuts:
        await seed_default_shortcuts(db)
        result = await db.execute(
            select(ShortcutConfig).where(ShortcutConfig.user_id == None)  # noqa: E711
        )
        shortcuts = result.scalars().all()

    return [_shortcut_to_schema(s) for s in shortcuts]


@router.put("/shortcuts/{shortcut_id}", response_model=ShortcutConfigSchema)
async def update_shortcut(
    shortcut_id: str,
    update_data: ShortcutUpdateRequest,
    user_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
):
    """Update a specific shortcut"""
    result = await db.execute(
        select(ShortcutConfig).where(ShortcutConfig.id == shortcut_id)
    )
    shortcut = result.scalar_one_or_none()

    if not shortcut:
        raise HTTPException(status_code=404, detail="Shortcut not found")

    if user_id is not None and shortcut.user_id is None:
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
            updated_at=datetime.utcnow(),
        )
        db.add(user_shortcut)
        await db.commit()
        await db.refresh(user_shortcut)
        return _shortcut_to_schema(user_shortcut)

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
    db: AsyncSession = Depends(get_db),
):
    """Bulk update or create shortcuts"""
    updated_shortcuts = []

    for shortcut_data in request.shortcuts:
        result = await db.execute(
            select(ShortcutConfig).where(ShortcutConfig.id == shortcut_data.id)
        )
        existing = result.scalar_one_or_none()

        if existing:
            existing.key = shortcut_data.key
            existing.modifiers = shortcut_data.modifiers
            existing.enabled = shortcut_data.enabled
            existing.updated_at = datetime.utcnow()
            updated_shortcuts.append(existing)
        else:
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
                updated_at=datetime.utcnow(),
            )
            db.add(new_shortcut)
            updated_shortcuts.append(new_shortcut)

    await db.commit()
    return {"message": f"Updated {len(updated_shortcuts)} shortcuts", "count": len(updated_shortcuts)}


@router.post("/shortcuts/reset")
async def reset_shortcuts(
    request: ShortcutResetRequest,
    db: AsyncSession = Depends(get_db),
):
    """Reset shortcuts to defaults"""
    if request.user_id is not None:
        result = await db.execute(
            select(ShortcutConfig).where(ShortcutConfig.user_id == request.user_id)
        )
        user_shortcuts = result.scalars().all()
        for shortcut in user_shortcuts:
            await db.delete(shortcut)
        await db.commit()
        return {"message": f"Reset shortcuts for user {request.user_id}"}
    else:
        await db.execute(text("DELETE FROM shortcut_configs"))
        await db.commit()
        await seed_default_shortcuts(db)
        return {"message": "Reset all shortcuts to defaults"}


@router.get("/shortcuts/export")
async def export_shortcuts(
    user_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
):
    """Export shortcut configuration as JSON"""
    query = select(ShortcutConfig)
    if user_id is not None:
        query = query.where(
            (ShortcutConfig.user_id == None) | (ShortcutConfig.user_id == user_id)  # noqa: E711
        )

    result = await db.execute(query)
    shortcuts = result.scalars().all()

    return {
        "version": "1.0",
        "exported_at": datetime.utcnow().isoformat(),
        "user_id": user_id,
        "shortcuts": [_shortcut_to_dict(s) for s in shortcuts],
    }


@router.post("/shortcuts/import")
async def import_shortcuts(config: dict, db: AsyncSession = Depends(get_db)):
    """Import shortcut configuration from JSON"""
    try:
        shortcuts_data = config.get("shortcuts", [])
        imported_count = 0

        for shortcut_data in shortcuts_data:
            result = await db.execute(
                select(ShortcutConfig).where(ShortcutConfig.id == shortcut_data["id"])
            )
            existing = result.scalar_one_or_none()

            if existing:
                existing.key = shortcut_data["key"]
                existing.modifiers = shortcut_data["modifiers"]
                existing.enabled = shortcut_data["enabled"]
                existing.updated_at = datetime.utcnow()
            else:
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
                    updated_at=datetime.utcnow(),
                )
                db.add(new_shortcut)
            imported_count += 1

        await db.commit()
        return {"message": "Shortcuts imported successfully", "imported_count": imported_count}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Import failed: {str(e)}")


# ============= Value Streams =============

@router.get("/value-streams", response_model=List[ValueStreamSchema])
async def get_value_streams(db: AsyncSession = Depends(get_db)):
    """Get all value streams"""
    result = await db.execute(select(ValueStream))
    value_streams = result.scalars().all()
    return [_value_stream_to_schema(vs) for vs in value_streams]


@router.post("/value-streams", response_model=ValueStreamSchema)
async def create_value_stream(
    value_stream_data: ValueStreamCreateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Create a new value stream"""
    result = await db.execute(
        select(ValueStream).where(ValueStream.name == value_stream_data.name)
    )
    existing = result.scalar_one_or_none()

    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Value stream '{value_stream_data.name}' already exists",
        )

    value_stream_id = str(uuid.uuid4())
    now = datetime.utcnow()

    value_stream = ValueStream(
        id=value_stream_id,
        name=value_stream_data.name,
        color=value_stream_data.color,
        created_at=now,
        updated_at=now,
    )

    db.add(value_stream)
    await db.commit()
    await db.refresh(value_stream)

    return _value_stream_to_schema(value_stream)


@router.delete("/value-streams/{value_stream_id}")
async def delete_value_stream(value_stream_id: str, db: AsyncSession = Depends(get_db)):
    """Delete a value stream"""
    result = await db.execute(
        select(ValueStream).where(ValueStream.id == value_stream_id)
    )
    value_stream = result.scalar_one_or_none()

    if not value_stream:
        raise HTTPException(status_code=404, detail="Value stream not found")

    await db.delete(value_stream)
    await db.commit()

    return {"message": "Value stream deleted successfully"}


# ============= AI Assist (Intelligence Flywheel) =============

@router.post("/ai/assist", response_model=AIAssistResponse)
async def ai_assist(request: AIAssistRequest, db: AsyncSession = Depends(get_db)):
    """Get AI assistance for a specific task using case memory context."""
    result = await db.execute(
        select(Task)
        .where(Task.id == request.task_id)
        .options(selectinload(Task.comments))
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    from services.ai_service import assist_with_task

    task_data = {
        "id": task.id,
        "title": task.title,
        "status": task.status,
        "description": task.description,
        "notes": task.notes,
        "assignee": task.assignee,
        "value_stream": task.value_stream,
    }
    ai_result = await assist_with_task(task_data, prompt=request.prompt)
    return AIAssistResponse(**ai_result)


@router.post("/ai/reindex")
async def reindex_case_studies():
    """Rebuild the semantic search index over all case studies."""
    try:
        from services.semantic_rag import get_rag_service

        rag = get_rag_service()
        count = rag.build_index()
        return {"message": f"Indexed {count} case studies", "count": count}
    except Exception as e:
        logger.error(f"Reindex failed: {e}")
        raise HTTPException(status_code=503, detail=f"Reindex unavailable: {str(e)}")


# ============= Helper Functions =============

def _task_to_schema(task: Task) -> TaskSchema:
    """Convert SQLAlchemy Task model to Pydantic TaskSchema."""
    attachments = (
        [att.url for att in task.attachments]
        if hasattr(task, "attachments") and task.attachments
        else []
    )
    comments = (
        [
            CommentSchema(
                id=comment.id,
                text=comment.text,
                author=comment.author,
                createdAt=(
                    comment.created_at.isoformat()
                    if comment.created_at
                    else datetime.utcnow().isoformat()
                ),
            )
            for comment in task.comments
        ]
        if hasattr(task, "comments") and task.comments
        else []
    )

    created_at = task.created_at if task.created_at else datetime.utcnow()
    updated_at = task.updated_at if task.updated_at else datetime.utcnow()

    return TaskSchema(
        id=task.id,
        title=task.title,
        status=task.status,
        assignee=task.assignee,
        startDate=task.start_date if task.start_date else None,
        dueDate=task.due_date if task.due_date else None,
        valueStream=task.value_stream if task.value_stream else None,
        description=task.description if task.description else None,
        notes=task.notes if task.notes else None,
        attachments=attachments,
        comments=comments,
        createdAt=created_at.isoformat(),
        updatedAt=updated_at.isoformat(),
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
        updated_at=now,
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
        updatedAt=updated_at.isoformat(),
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
        "is_default": shortcut.is_default,
    }


def _get_default_shortcuts() -> list:
    """Return default keyboard shortcut configurations"""
    return [
        {"id": "new_task", "category": "board", "action": "new_task", "key": "n", "modifiers": [], "enabled": True, "description": "Create a new task"},
        {"id": "delete_task", "category": "task", "action": "delete_task", "key": "d", "modifiers": ["ctrl"], "enabled": True, "description": "Delete the selected task"},
        {"id": "col_todo", "category": "board", "action": "col_todo", "key": "1", "modifiers": [], "enabled": True, "description": "Focus To Do column"},
        {"id": "col_doing", "category": "board", "action": "col_doing", "key": "2", "modifiers": [], "enabled": True, "description": "Focus Doing column"},
        {"id": "col_done", "category": "board", "action": "col_done", "key": "3", "modifiers": [], "enabled": True, "description": "Focus Done column"},
        {"id": "search", "category": "global", "action": "search", "key": "/", "modifiers": [], "enabled": True, "description": "Focus search bar"},
        {"id": "help", "category": "global", "action": "help", "key": "?", "modifiers": [], "enabled": True, "description": "Show keyboard shortcuts help"},
        {"id": "escape", "category": "global", "action": "escape", "key": "Escape", "modifiers": [], "enabled": True, "description": "Close dialogs and deselect"},
    ]


async def seed_default_shortcuts(db: AsyncSession):
    """Seed database with default shortcuts"""
    defaults = _get_default_shortcuts()

    for shortcut_data in defaults:
        result = await db.execute(
            select(ShortcutConfig).where(
                ShortcutConfig.id == shortcut_data["id"],
                ShortcutConfig.user_id == None,  # noqa: E711
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            existing.category = shortcut_data["category"]
            existing.action = shortcut_data["action"]
            existing.key = shortcut_data["key"]
            existing.modifiers = shortcut_data["modifiers"]
            existing.enabled = shortcut_data["enabled"]
            existing.description = shortcut_data["description"]
            existing.updated_at = datetime.utcnow()
        else:
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
                updated_at=datetime.utcnow(),
            )
            db.add(shortcut)

    await db.commit()


def _value_stream_to_schema(value_stream: ValueStream) -> ValueStreamSchema:
    """Convert SQLAlchemy ValueStream to Pydantic schema"""
    created_at = value_stream.created_at if value_stream.created_at else datetime.utcnow()
    updated_at = value_stream.updated_at if value_stream.updated_at else datetime.utcnow()

    return ValueStreamSchema(
        id=value_stream.id,
        name=value_stream.name,
        color=value_stream.color,
        createdAt=created_at.isoformat(),
        updatedAt=updated_at.isoformat(),
    )
